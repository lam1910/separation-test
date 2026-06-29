# Six Degrees of Separation — Wikidata Edition

Find the shortest connection between any two [Wikidata](https://www.wikidata.org) entities (people, places, works, organisations, …).

## How it works

Bidirectional BFS expands from both the start and end entities simultaneously, always growing the smaller frontier. Each expansion fetches the entity's neighbours via a SPARQL query to the Wikidata endpoint, following relationships such as family ties, employment, awards, and more. The two frontiers meet in the middle, keeping the search tractable even for deeply connected graphs.

## Requirements

- Python 3.11+
- `requests >= 2.28`

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

You will be prompted to search for a start entity and an end entity by name. Select from the Wikidata search results and the path (if one exists within 5 degrees) is printed.

## Project layout

```
main.py              # CLI entry point and UI helpers
search_algo/
  bfs.py             # Bidirectional BFS implementation
  utils.py           # Path-merge helper
sparql/
  traverse.py        # Wikidata API + SPARQL queries
requirements.txt
```

## Configuration

Two constants in `search_algo/bfs.py` control search behaviour:

| Constant | Default | Description |
|---|---|---|
| `MAX_DEPTH` | `6` | Maximum BFS depth (= 5 degrees of separation) |
| `RATE_LIMIT_DELAY` | `0.25` | Seconds between SPARQL requests |