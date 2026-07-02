import time

from sparql import get_neighbors
from .utils import _merge


RATE_LIMIT_DELAY = 0.25  # seconds between SPARQL requests
MAX_DEPTH = 6  # 5 degrees = 6 nodes in path

# Path element: (entity_id, entity_label, via_relation)
# The origin node has via_relation = "".

def bidirectional_bfs(start_id: str, end_id: str, prev_path: dict) -> list | None:
    """
    Bidirectional BFS on the Wikidata entity graph.
    Alternates between forward (start→) and backward (end→) frontiers,
    always expanding whichever is smaller.
    Returns the merged path or None if unreachable within MAX_DEPTH.
    """
    if start_id == end_id:
        return [(start_id, "", "")]

    # entity_id → path from that origin to entity_id
    f_paths: dict = {start_id: [(start_id, "", "")]}
    b_paths: dict = {end_id: [(end_id, "", "")]}
    f_frontier: list = [start_id]
    b_frontier: list = [end_id]

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

        new_frontier: list = []
        for entity_id in frontier:
            path = visited[entity_id]
            print(
                f"  [{arrow}] {entity_id} "
                f"(depth {len(path)}, frontier size {len(frontier)})        ",
                end="\r",
                flush=True,
            )
            try:
                neighbors = get_neighbors(entity_id, prev_path)
                time.sleep(RATE_LIMIT_DELAY)
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
                    print()
                    fwd = new_path if expand_forward else other[nid]
                    bwd = other[nid] if expand_forward else new_path
                    return _merge(fwd, bwd)

        if expand_forward:
            f_frontier = new_frontier
        else:
            b_frontier = new_frontier

    return None