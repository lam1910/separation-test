from concurrent.futures import ThreadPoolExecutor, as_completed

from sparql import get_neighbors
from .utils import _merge


MAX_DEPTH = 6  # 5 degrees = 6 nodes in path
MAX_WORKERS = 5  # concurrent SPARQL requests per frontier expansion

# Path element: (entity_id, entity_label, via_relation)
# The origin node has via_relation = "".

def bidirectional_bfs(start_id: str, end_id: str, prev_path: dict) -> list | None:
    """
    Bidirectional BFS on the Wikidata entity graph.
    Alternates between forward (start→) and backward (end→) frontiers,
    always expanding whichever is smaller. Nodes within a frontier are
    independent, so they're fetched concurrently via a thread pool —
    SPARQL requests are I/O-bound and dominated by network latency.
    Returns the merged path or None if unreachable within MAX_DEPTH.
    """
    if start_id == end_id:
        return [(start_id, "", "")]

    # entity_id → path from that origin to entity_id
    f_paths: dict = {start_id: [(start_id, "", "")]}
    b_paths: dict = {end_id: [(end_id, "", "")]}
    f_frontier: list = [start_id]
    b_frontier: list = [end_id]

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        for _ in range(MAX_DEPTH):
            if not f_frontier and not b_frontier:
                break

            expand_forward = bool(f_frontier) and (
                    not b_frontier or len(f_frontier) <= len(b_frontier)
            )

            frontier = f_frontier if expand_forward else b_frontier
            visited = f_paths if expand_forward else b_paths
            other = b_paths if expand_forward else f_paths
            arrow = "→" if expand_forward else "←"

            futures = {
                pool.submit(get_neighbors, entity_id, prev_path): entity_id
                for entity_id in frontier
            }

            new_frontier: list = []
            meeting: list | None = None
            for done, future in enumerate(as_completed(futures), start=1):
                entity_id = futures[future]
                path = visited[entity_id]
                print(
                    f"  [{arrow}] {entity_id} "
                    f"(depth {len(path)}, {done}/{len(frontier)} done)        ",
                    end="\r",
                    flush=True,
                )
                try:
                    neighbors = future.result()
                except Exception as e:
                    print(f"\n  Warning: Could not expand {entity_id}: {e}")
                    continue

                for nid, nlabel, rel in neighbors:
                    if nid in visited:
                        continue
                    new_path = path + [(nid, nlabel, rel)]
                    visited[nid] = new_path
                    new_frontier.append(nid)

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

            if expand_forward:
                f_frontier = new_frontier
            else:
                b_frontier = new_frontier

    return None