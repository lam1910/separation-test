#!/usr/bin/env python3
"""
Six Degrees of Separation — Wikidata Edition
Find a connection between any two Wikidata entities.

Modes:
  - Bidirectional BFS: expands whichever frontier is smaller, guarantees
    the shortest path.
  - DFS: explores one path at a time down to MAX_DEPTH before
    backtracking, returns the first path found (not necessarily shortest).
  - Hub-biased bidirectional search: expands the most-connected candidates
    first (by Wikidata sitelink count) instead of by depth, trading the
    shortest-path guarantee for fewer expansions on well-connected inputs.
Each expansion fetches all meaningful neighbours of an entity via SPARQL.
"""
from search_algo import bidirectional_bfs, dfs, hub_biased_bfs, MAX_DEPTH
from search_algo.hub_bfs import MAX_EXPANSIONS
from sparql import search_entity

_cache: dict = {}

MODES = {
    "1": ("Bidirectional BFS (shortest path)", bidirectional_bfs, f"max {MAX_DEPTH - 1} degrees"),
    "2": ("DFS (first path found)", dfs, f"max {MAX_DEPTH - 1} degrees"),
    "3": (
        "Hub-biased bidirectional search (chase well-connected entities)",
        hub_biased_bfs,
        f"max {MAX_EXPANSIONS} expansions/side, no shortest-path guarantee",
    ),
}


# ── UI helpers ───────────────────────────────────────────────────────────────

def pick_mode() -> tuple:
    print("Search mode:")
    for key, (label, _, _) in MODES.items():
        print(f"  [{key}] {label}")

    while True:
        choice = input(f"  Choose [1-{len(MODES)}] (default 1): ").strip() or "1"
        if choice in MODES:
            return MODES[choice]
        print("  Invalid — try again.")


def pick_entity(prompt: str) -> tuple | None:
    raw = input(prompt).strip()
    if not raw:
        return None

    print(f"  Searching Wikidata for '{raw}' …")
    try:
        hits = search_entity(raw)
    except Exception as e:
        print(f"  Error: {e}")
        return None

    if not hits:
        print("  No results found.")
        return None

    for i, h in enumerate(hits, 1):
        desc = (h.get("description") or "")[:72]
        name = h.get("label", h["id"])
        print(f"  [{i}] {name}  ({h['id']})")
        if desc:
            print(f"       {desc}")

    while True:
        try:
            idx = int(input(f"  Choose [1–{len(hits)}] or 0 to cancel: ").strip())
            if idx == 0:
                return None
            if 1 <= idx <= len(hits):
                h = hits[idx - 1]
                return h["id"], h.get("label", h["id"])
        except (ValueError, KeyboardInterrupt):
            pass
        print("  Invalid — try again.")


def show_path(path: list, start_label: str, end_label: str) -> None:
    n = len(path) - 1
    print(f"\n{'━' * 65}")
    print(f"  Found path — {n} degree{'s' if n != 1 else ''} of separation!")
    print(f"{'━' * 65}\n")

    for i, (eid, label, via) in enumerate(path):
        name = label or (start_label if i == 0 else end_label if i == len(path) - 1 else eid)
        if i == 0:
            print(f"  ◉  {name}  [{eid}]")
        else:
            is_last = i == len(path) - 1
            marker = "◎" if is_last else "●"
            print(f"  │")
            print(f"  │  ── {via} ──")
            print(f"  │")
            print(f"  {marker}  {name}  [{eid}]")
    print()


# ── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    print("╔" + "═" * 63 + "╗")
    print("║     SIX DEGREES OF SEPARATION  ·  WIKIDATA EDITION           ║")
    print("╚" + "═" * 63 + "╝")
    print("\nConnect any two Wikidata entities (people, places, works …)\n")

    try:
        mode_label, search_fn, mode_limit = pick_mode()
        print()

        start = pick_entity("Start: ")
        if not start:
            return
        start_id, start_label = start
        print(f"  ✓  {start_label} ({start_id})\n")

        end = pick_entity("End:   ")
        if not end:
            return
        end_id, end_label = end
        print(f"  ✓  {end_label} ({end_id})\n")

        if start_id == end_id:
            print("Same entity — 0 degrees of separation.")
            return

        print(f"Searching for path: {start_label}  →  {end_label}")
        print(f"Strategy: {mode_label}, {mode_limit}\n")

        path = search_fn(start_id, end_id, _cache)

        if path:
            show_path(path, start_label, end_label)
        else:
            print(f"\nNo path found ({mode_limit}).")
            print("Tip: try more famous / well-connected entities.")

    except KeyboardInterrupt:
        print("\n\nStopped.")


if __name__ == "__main__":
    main()
