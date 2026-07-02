import time

from sparql import get_neighbors


RATE_LIMIT_DELAY = 0.25  # seconds between SPARQL requests
MAX_DEPTH = 6  # 5 degrees = 6 nodes in path

# Path element: (entity_id, entity_label, via_relation)
# The origin node has via_relation = "".

def dfs(start_id: str, end_id: str, prev_path: dict) -> list | None:
    """
    Depth-first search on the Wikidata entity graph.
    Explores one path at a time down to MAX_DEPTH before backtracking.
    Returns the first path found or None if unreachable within MAX_DEPTH.
    """
    if start_id == end_id:
        return [(start_id, "", "")]

    # stack of (path_so_far, ids_visited_on_this_path)
    stack: list = [([(start_id, "", "")], {start_id})]

    while stack:
        path, visited = stack.pop()
        current_id = path[-1][0]

        print(
            f"  [→] {current_id} (depth {len(path)}, stack size {len(stack)})        ",
            end="\r",
            flush=True,
        )

        if len(path) >= MAX_DEPTH:
            continue

        try:
            neighbors = get_neighbors(current_id, prev_path)
            time.sleep(RATE_LIMIT_DELAY)
        except Exception as e:
            print(f"\n  Warning: Could not expand {current_id}: {e}")
            continue

        for nid, nlabel, rel in neighbors:
            if nid in visited:
                continue
            new_path = path + [(nid, nlabel, rel)]

            if nid == end_id:
                print()
                return new_path

            stack.append((new_path, visited | {nid}))

    return None