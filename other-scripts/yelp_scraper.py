import requests
import json
from datetime import datetime
import time
from dotenv import load_dotenv
import os

# Load Yelp API key from .env
load_dotenv()
API_KEY = os.getenv("YELP_API_KEY")
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

BASE_URL = "https://api.yelp.com/v3/businesses/search"

# Define cuisines and zip codes
CUISINES = [
    "Italian", "Chinese", "Mexican", "Indian", "Japanese",
    "Thai", "Korean", "French", "Mediterranean", "American"
]

ZIP_CODES = [
    "10001", "10002", "10003", "10004", "10005", "10009", "10010", "10011", 
    "10012", "10013", "10014", "10016", "10018", "10019", "10021", "10022",
    "10023", "10025", "10026", "10028", "10029", "10036"
]

LIMIT_PER_REQUEST = 50  
TARGET_PER_CUISINE = 200  

all_restaurants = []
seen_business_ids = set()

def fetch_restaurants(cuisine, zip_code):
    """Fetch restaurants of a specific cuisine and zip code, avoiding duplicates."""
    restaurants = []
    offset = 0
    while len(restaurants) < TARGET_PER_CUISINE:
        params = {
            "term": f"{cuisine} restaurant",
            "location": f"Manhattan, NY {zip_code}",
            "limit": LIMIT_PER_REQUEST,
            "offset": offset
        }
        response = requests.get(BASE_URL, headers=HEADERS, params=params)
        data = response.json()
        businesses = data.get("businesses", [])

        if not businesses:
            break

        for b in businesses:
            if b["id"] not in seen_business_ids:
                restaurants.append({
                    "business_id": b["id"],
                    "name": b["name"],
                    "cuisine": cuisine,
                    "address": " ".join(b["location"]["display_address"]),
                    "coordinates": b["coordinates"],
                    "reviews": b.get("review_count", 0),
                    "rating": b.get("rating", 0),
                    "zip": b["location"].get("zip_code", ""),
                    "insertedAtTimestamp": datetime.utcnow().isoformat()
                })
                seen_business_ids.add(b["id"])

            if len(restaurants) >= TARGET_PER_CUISINE:
                break

        offset += LIMIT_PER_REQUEST
        time.sleep(0.5) 

    return restaurants

for cuisine in CUISINES:
    cuisine_count = 0
    print(f"Fetching {cuisine} restaurants...")
    for zip_code in ZIP_CODES:
        fetched = fetch_restaurants(cuisine, zip_code)
        all_restaurants.extend(fetched)
        cuisine_count += len(fetched)
        if cuisine_count >= TARGET_PER_CUISINE:
            break  
    print(f"Total unique {cuisine} restaurants fetched: {cuisine_count}")

with open("yelp_data_full.json", "w") as f:
    json.dump(all_restaurants, f, indent=2)

print(f"Total unique restaurants fetched overall: {len(all_restaurants)}")


