import json
import random
import requests
from requests.auth import HTTPBasicAuth

OPENSEARCH_ENDPOINT = "https://search-domain1-6ikn37etifnsbylwp627rmwiy4.us-east-1.es.amazonaws.com"
INDEX = "restaurants"

MASTER_USER = "hk3677"
MASTER_PASS = "wwwww"

MAX_DOCS = 1000       
BATCH_SIZE = 200      

auth = HTTPBasicAuth(MASTER_USER, MASTER_PASS)
headers = {"Content-Type": "application/x-ndjson"}


def bulk_send(batch):
    """
    Bulk indexes documents into OpenSearch.
    Each doc has: RestaurantID, Cuisine
    Doc id = business_id (so duplicates overwrite, not duplicate)
    """
    lines = []
    for r in batch:
        rid = r["business_id"]
        doc = {
            "RestaurantID": rid,
            "Cuisine": r.get("cuisine", "")
        }
        lines.append(json.dumps({"index": {"_index": INDEX, "_id": rid}}))
        lines.append(json.dumps(doc))

    payload = "\n".join(lines) + "\n"
    url = f"{OPENSEARCH_ENDPOINT}/_bulk"

    resp = requests.post(url, auth=auth, data=payload, headers=headers, timeout=60)
    resp.raise_for_status()

    out = resp.json()
    if out.get("errors"):
        for item in out.get("items", []):
            action = item.get("index", {})
            if "error" in action:
                raise RuntimeError(f"Bulk indexing error: {action['error']}")
        raise RuntimeError("Bulk indexing returned errors=True but no error details found.")

    return len(batch)


def main():

    with open("yelp_data_full.json", "r") as f:
        data = json.load(f)

    random.shuffle(data)

    picked = []
    seen = set()
    for r in data:
        bid = r.get("business_id")
        if not bid or bid in seen:
            continue
        seen.add(bid)
        picked.append(r)
        if len(picked) >= MAX_DOCS:
            break

    if not picked:
        raise RuntimeError("No restaurants found in yelp_data_full.json")

    
    total = 0
    for i in range(0, len(picked), BATCH_SIZE):
        batch = picked[i:i + BATCH_SIZE]
        total += bulk_send(batch)
        print(f"Indexed {total}/{len(picked)}")

    print("✅ Done! Bulk upload completed.")


if __name__ == "__main__":
    main()
