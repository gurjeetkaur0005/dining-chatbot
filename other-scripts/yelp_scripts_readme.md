# Dining Chatbot - Yelp Restaurant Data Scripts

This repository contains Python scripts to fetch restaurant data from the Yelp API, store it locally, and upload it to an Amazon DynamoDB table. The data covers multiple cuisine types in Manhattan, NY, with a focus on avoiding duplicate entries.

---

## Folder Structure

```
dining-chatbot/
├── other-scripts/
│   ├── yelp_scraper.py           # Script to fetch restaurant data from Yelp API
│   ├── upload_yelp_to_dynamo.py # Script to upload JSON data to DynamoDB
│   └── yelp_data_full.json       # Fetched restaurant data in JSON format
├── README.md                     # This file
```

---

## Scripts

### 1. `yelp_scraper.py`

- Fetches restaurants from the Yelp API by cuisine type and ZIP code.
- Ensures each cuisine has a target number of unique restaurants (200+).
- Avoids duplicates by tracking `business_id`.
- Saves all fetched restaurants in `yelp_data_full.json`.

**Cuisines fetched:**
Italian, Chinese, Mexican, Indian, Japanese, Thai, Korean, French, Mediterranean, American

**Example Output Summary:**

| Cuisine        | Total Unique Restaurants Fetched |
|----------------|--------------------------------|
| Italian        | 200                            |
| Chinese        | 388                            |
| Mexican        | 365                            |
| Indian         | 308                            |
| Japanese       | 347                            |
| Thai           | 211                            |
| Korean         | 201                            |
| French         | 310                            |
| Mediterranean  | 277                            |
| American       | 242                            |

**Overall total unique restaurants fetched:** 2,849

**How to Run:**

```bash
# Install dependencies
pip install requests python-dotenv

# Make sure your .env file has your Yelp API key
YELP_API_KEY=your_yelp_api_key_here

# Run the scraper
python other-scripts/yelp_scraper.py
```

---

### 2. `upload_yelp_to_dynamo.py`

- Reads `yelp_data_full.json` and uploads the data to the `yelp-restaurants` DynamoDB table.
- Converts float numbers to `Decimal` (required by DynamoDB).
- Uses `business_id` as the primary key to avoid duplicates.
- Supports batch uploads for efficiency.

**How to Run:**

```bash
# Install boto3
pip install boto3

# Run the uploader
python other-scripts/upload_yelp_to_dynamo.py
```

**Output Example:**

```
Uploaded 100/2849 items...
Uploaded 200/2849 items...
...
✅ Uploaded 2849 items to DynamoDB!
```

---

## Requirements

- Python 3.8+
- `requests`
- `python-dotenv`
- `boto3`
- AWS credentials configured for DynamoDB access

---

## Notes

- The scraper respects Yelp API rate limits by adding a short delay between requests.
- DynamoDB table must already exist with `business_id` as the primary key.
- All restaurant data includes:
  - `business_id`, `name`, `cuisine`, `address`, `coordinates`, `reviews`, `rating`, `zip`, `insertedAtTimestamp`

---

## License

This project is for educational purposes.

