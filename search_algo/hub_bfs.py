import heapq
from concurrent.futures import ThreadPoolExecutor, as_completed

from sparql import get_neighbors
from .utils import _merge


MAX_EXPANSIONS = 300  # total node expansions allowed per direction
BEAM_SIZE = 5  # nodes expanded per round, taken from the priority queue's most-connected end
MAX_WORKERS = 5  # concurrent SPARQL requests per round

# Path element: (entity_id, entity_label, via_relation)
# The origin node has via_relation = "".


def hub_biased_bfs(start_id: str, end_id: str, prev_path: dict) -> list | None:
    """
    Bidirectional best-first search on the Wikidata entity graph, biased
    toward well-connected ("hub") entities instead of expanding strictly
    by depth like plain BFS.

    Each side keeps a max-heap of discovered-but-unexpanded entities keyed
    by Wikidata sitelink count (a free proxy for degree/notability, fetched
    alongside each neighbour). Every round pops the BEAM_SIZE most-connected
    entities and expands them concurrently. Rationale: in a small-world
    graph like Wikidata, well-connected entities are disproportionately
    likely to bridge to the other side, so chasing hubs first tends to
    reach a meeting point in fewer expansions than strict layer-by-layer
    BFS — at the cost of not guaranteeing the shortest path, and doing more
    SPARQL calls when a hub turns out to be a dead end.

    Returns the merged path or None if no meeting is found within
    MAX_EXPANSIONS expansions per side.
    """
    if start_id == end_id:
        return [(start_id, "", "")]

    # entity_id → path from that origin to entity_id
    f_paths: dict = {start_id: [(start_id, "", "")]}
    b_paths: dict = {end_id: [(end_id, "", "")]}
    # heap entries: (-sitelinks, entity_id) — negated so heapq pops the highest first
    f_heap: list = [(0, start_id)]
    b_heap: list = [(0, end_id)]
    f_expansions = 0
    b_expansions = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        while f_heap or b_heap:
            f_done = f_expansions >= MAX_EXPANSIONS
            b_done = b_expansions >= MAX_EXPANSIONS
            if f_done and b_done:
                break

            if f_heap and not f_done and (not b_heap or b_done or f_expansions <= b_expansions):
                expand_forward = True
            elif b_heap and not b_done:
                expand_forward = False
            else:
                break  # remaining side is capped or empty — nothing left to expand

            heap = f_heap if expand_forward else b_heap
            visited = f_paths if expand_forward else b_paths
            other = b_paths if expand_forward else f_paths
            arrow = "→" if expand_forward else "←"

            batch = []
            while heap and len(batch) < BEAM_SIZE:
                _neg_sitelinks, entity_id = heapq.heappop(heap)
                batch.append(entity_id)

            if not batch:
                continue

            if expand_forward:
                f_expansions += len(batch)
            else:
                b_expansions += len(batch)

            futures = {
                pool.submit(get_neighbors, entity_id, prev_path, True): entity_id
                for entity_id in batch
            }

            meeting: list | None = None
            for done, future in enumerate(as_completed(futures), start=1):
                entity_id = futures[future]
                path = visited[entity_id]
                print(
                    f"  [{arrow}] {entity_id} "
                    f"(depth {len(path)}, expansions {f_expansions + b_expansions})        ",
                    end="\r",
                    flush=True,
                )
                try:
                    neighbors = future.result()
                except Exception as e:
                    print(f"\n  Warning: Could not expand {entity_id}: {e}")
                    continue

                for nid, nlabel, rel, sitelinks in neighbors:
                    if nid in visited:
                        continue
                    new_path = path + [(nid, nlabel, rel)]
                    visited[nid] = new_path
                    heapq.heappush(heap, (-sitelinks, nid))

                    if nid in other:
                        fwd = new_path if expand_forward else other[nid]
                        bwd = other[nid] if expand_forward else new_path
                        meeting = _merge(fwd, bwd)
                        break
                if meeting:
                    break

            if meeting:
                print()
                return meeting

    return None