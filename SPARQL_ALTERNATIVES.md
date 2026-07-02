# Alternatives to SPARQL + Wikidata

Options for replacing the two things this project currently depends on:
`sparql/traverse.py`'s live SPARQL queries, and Wikidata as the data source.
The core requirement to replace is `get_neighbors(entity_id) -> [(id, label, relation)]`
plus an entity search/lookup.

## Live REST APIs (drop-in style, no local hosting)

| Tool | What it gives you | Fit for this project |
|---|---|---|
| **[TMDb API](https://developer.themoviedb.org/docs)** | Movies, actors, crew, cast credits — plain REST/JSON, generous free tier | Great if you narrow scope to a "six degrees of actors" style graph (classic Kevin Bacon problem). Very rich cast/crew edges, easy pagination, no query language to learn. |
| **[ConceptNet API](https://github.com/commonsense/conceptnet5/wiki/API)** | General concept graph (relatedness, part-of, is-a, etc.), REST/JSON | Broad coverage but edges are "common sense" relations rather than biographical/factual — less precise than Wikidata's `father`/`employer`/`educated at`. |
| **[Wikipedia REST/Action API (page links)](https://www.mediawiki.org/wiki/API:Links)** | Raw hyperlink graph between Wikipedia articles, plain JSON, no SPARQL | Closest like-for-like replacement — same entity coverage as Wikidata, but edges are just "linked from/to," not typed relationships. Traversal logic (BFS/DFS) barely changes. |
| **[DBpedia Lookup API](https://www.dbpedia-spotlight.org/api)** | Entity search via REST, backed by the same Wikipedia data as DBpedia | Only replaces entity search, not neighbor traversal (DBpedia's graph queries still go through SPARQL). |
| **[Google Knowledge Graph Search API](https://developers.google.com/knowledge-graph)** | Entity search + basic types/descriptions, REST/JSON | Not built for graph traversal — no "get related entities" endpoint, so it can't drive the BFS/DFS step on its own. |

## Local graph databases (import a dataset once, query locally — fast, no network dependency)

| Tool | What it gives you | Fit for this project |
|---|---|---|
| **[Neo4j](https://neo4j.com/) + Cypher** | Property graph DB; import a Wikidata JSON dump, DBpedia dump, or IMDB dataset once, then query locally | Best option if speed matters more than staying live/up-to-date. Removes all network latency and rate limits from the hot path. Cypher is far more ergonomic than SPARQL for "shortest path between two nodes" (built-in `shortestPath()`). |
| **[ArangoDB](https://www.arangodb.com/)** | Multi-model DB with native graph traversal | Similar tradeoffs to Neo4j; AQL traversal queries are also simpler than SPARQL for this use case. |
| **[Wikidata5m](https://deepgraphlearning.github.io/project/wikidata5m) / Wikidata truthy dumps** | Pre-extracted Wikidata entity-relation dataset, downloadable, load into any graph DB or even an in-memory adjacency list | Keeps Wikidata's rich relation types (father, employer, award, etc.) but removes the live SPARQL endpoint entirely — one-time ETL instead of per-query network calls. |
| **[YAGO](https://yago-knowledge.org/)** | Wikipedia/WordNet/GeoNames-derived knowledge base, downloadable dumps | Alternative structured KB to Wikidata; similar relation richness, different licensing/update cadence. |

## Notable prior art

- **[Six Degrees of Wikipedia](https://www.sixdegreesofwikipedia.com/)** — an existing open-source project solving exactly this problem over the Wikipedia link graph (not Wikidata/SPARQL). Worth reading their approach/source for a proven architecture before picking a tool above.

## Recommendation

- If you want to **stay live/always up-to-date** with minimal code changes: switch to the **Wikipedia link-graph REST API** — same traversal shape, no SPARQL, no query language.
- If you want **speed and don't mind periodic re-import**: pull a **Wikidata dump into Neo4j** and use Cypher's built-in shortest-path — this also directly solves the "DFS/BFS is slow" problem from earlier since there's no per-hop network call at all.
- If you're fine **narrowing the domain**: **TMDb** for an actor/movie-only graph is the easiest to integrate (simple REST, no ETL, no query language).