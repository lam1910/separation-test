import time

import requests


WIKIDATA_API = "https://www.wikidata.org/w/api.php"
SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
HEADERS = {
    "User-Agent": "SixDegreesWikidata/1.0 (educational project)",
    "Accept": "application/json",
}

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
    resp = requests.get(WIKIDATA_API, params=params, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    return resp.json().get("search", [])


def sparql_query(query: str) -> dict:
    for attempt in range(3):
        try:
            resp = requests.get(
                SPARQL_ENDPOINT,
                params={"query": query, "format": "json"},
                headers=HEADERS,
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


def get_neighbors(entity_id: str, cache: dict) -> list:
    """Return [(neighbor_id, neighbor_label, relation_label), …]."""
    if entity_id in cache:
        return cache[entity_id]

    props = " ".join(f"wd:{p}" for p in FOLLOW_PROPS)
    query = f"""
SELECT DISTINCT ?nb ?nbLabel ?relLabel WHERE {{
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
        result.append((nid, nlabel, rlabel))

    cache[entity_id] = result
    return result