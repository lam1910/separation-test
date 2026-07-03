import time

import requests


WIKIDATA_API = "https://www.wikidata.org/w/api.php"
SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
HEADERS = {
    "User-Agent": "SixDegreesWikidata/1.0 (educational project)",
    "Accept": "application/json",
}

_session = requests.Session()
_session.headers.update(HEADERS)

NEIGHBORS_LIMIT = 50
# Properties to follow. Both directions are explored (outgoing + incoming).
FOLLOW_PROPS = [
    "P22",  # father
    "P25",  # mother
    "P26",  # spouse
    "P40",  # child
    "P184",  # doctoral advisor
    "P185",  # doctoral student
    "P69",  # educated at
    "P108",  # employer
    "P463",  # member of
    "P161",  # cast member
    "P57",  # director
    "P162",  # producer
    "P86",  # composer
    "P175",  # performer
    "P1344",  # participant of
    "P19",  # place of birth
    "P20",  # place of death
    "P166",  # award received
    "P527",  # has part
    "P361",  # part of
]


# ── Wikidata helpers ────────────────────────────────────────────────────────
def search_entity(query: str, limit: int = 5) -> list:
    params = {
        "action": "wbsearchentities",
        "search": query,
        "language": "en",
        "format": "json",
        "limit": limit,
        "type": "item",
    }
    resp = _session.get(WIKIDATA_API, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json().get("search", [])


def sparql_query(query: str) -> dict:
    for attempt in range(3):
        try:
            resp = _session.get(
                SPARQL_ENDPOINT,
                params={"query": query, "format": "json"},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            if hasattr(e, "response") and e.response.status_code == 429 and attempt < 2:
                wait = 5 * (2 ** attempt)
                print(f"\n  Rate limited — waiting {wait}s …", flush=True)
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("SPARQL query failed after retries")


def get_neighbors(entity_id: str, cache: dict, with_sitelinks: bool = False) -> list:
    """Return [(neighbor_id, neighbor_label, relation_label), …].

    With `with_sitelinks=True`, each tuple gets a 4th element: the
    neighbour's Wikidata sitelink count, a free proxy for how well
    connected/notable an entity is. It costs one extra OPTIONAL clause
    (no extra round trip) and is only requested by strategies that need
    it, e.g. hub-biased traversal — plain BFS/DFS leave it off.
    """
    cache_key = (entity_id, with_sitelinks)
    if cache_key in cache:
        return cache[cache_key]

    props = " ".join(f"wd:{p}" for p in FOLLOW_PROPS)
    sitelinks_select = " ?sitelinks" if with_sitelinks else ""
    sitelinks_clause = (
        "OPTIONAL { ?nb wikibase:sitelinks ?sitelinks }" if with_sitelinks else ""
    )
    query = f"""
SELECT DISTINCT ?nb ?nbLabel ?relLabel{sitelinks_select} WHERE {{
  {{
    wd:{entity_id} ?direct ?nb .
    ?rel wikibase:directClaim ?direct .
    VALUES ?rel {{ {props} }}
  }} UNION {{
    ?nb ?direct wd:{entity_id} .
    ?rel wikibase:directClaim ?direct .
    VALUES ?rel {{ {props} }}
  }}
  FILTER(STRSTARTS(STR(?nb), "http://www.wikidata.org/entity/Q"))
  FILTER(?nb != wd:{entity_id})
  {sitelinks_clause}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" }}
}}
LIMIT {NEIGHBORS_LIMIT}
"""
    data = sparql_query(query)
    result = []
    seen: set = set()
    for b in data["results"]["bindings"]:
        nid = b["nb"]["value"].split("/")[-1]
        if nid in seen:
            continue
        seen.add(nid)
        nlabel = b.get("nbLabel", {}).get("value", nid)
        rlabel = b.get("relLabel", {}).get("value", "connected to")
        if with_sitelinks:
            sitelinks = int(b.get("sitelinks", {}).get("value", 0) or 0)
            result.append((nid, nlabel, rlabel, sitelinks))
        else:
            result.append((nid, nlabel, rlabel))

    cache[cache_key] = result
    return result