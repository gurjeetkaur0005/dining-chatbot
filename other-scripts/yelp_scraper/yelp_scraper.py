import requests
import json
from datetime import datetime
import time

API_KEY = "YOUR_YELP_API_KEY"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}
BASE_URL = "https://api.yelp.com/v3/businesses/search"

CUISINES = ["Italian", "Chinese", "Mexican", "Indian", "Japanese"]
LOCATION = "Manhattan, NY"
LIMIT_PER_CUISINE = 200

all_restaurants = []

def fetch_restaurants(cuisine, location=LOCATION, limit=LIMIT_PER_CUISINE):
    restaurants = []
    offset = 0
    while len(restaurants) < limit:
        params = {
            "term": cuisine + " restaurant",
            "location": location,
            "limit": 50,  # max per request
            "offset": offset
        }
        response = requests.get(BASE_URL, headers=HEADERS, params=params)
        data = response.json()
        businesses = data.get("businesses", [])
        if not businesses:
            break
        for b in businesses:
            restaurants.append({
                "business_id": b["id"],
                "name": b["name"],
                "address": " ".join(b["location"]["display_address"]),
                "coordinates": b["coordinates"],
                "reviews": b.get("review_count", 0),
                "rating": b.get("rating", 0),
                "zip": b["location"].get("zip_code", ""),
                "insertedAtTimestamp": datetime.utcnow().isoformat()
            })
        offset += 50
        time.sleep(1)  # avoid hitting rate limits
    return restaurants[:limit]

# Fetch data for all cuisines
for cuisine in CUISINES:
    print(f"Fetching {cuisine} restaurants...")
    fetched = fetch_restaurants(cuisine)
    all_restaurants.extend(fetched)

# Save to JSON
with open("yelp_data.json", "w") as f:
    json.dump(all_restaurants, f, indent=2)

print(f"Saved {len(all_restaurants)} restaurants to yelp_data.json")
