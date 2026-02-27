# LF2 — Suggestions Worker Lambda (SQS → OpenSearch/DynamoDB → SES)

## Overview
LF2 is the **queue worker** for the Dining Concierge application. It is triggered by **SQS (Q1)** and sends restaurant recommendations to the user via **Amazon SES**. It queries **OpenSearch** to get random restaurant IDs for a cuisine, then fetches full restaurant details from **DynamoDB**.

LF2 also supports **Extra Credit State Memory** by saving the user’s last search (**cuisine + location**) in a DynamoDB table and allowing “recommend based on last search” behavior.

---

## What LF2 Does (High-Level)
For each SQS message:

1. Reads request from SQS message body
2. (Optional) If `useLastSearch=true`, loads last search from `user-state`
3. Queries OpenSearch index `restaurants` for matching cuisine to get RestaurantIDs
4. Randomly picks up to 3 RestaurantIDs
5. Uses DynamoDB BatchGetItem on `yelp-restaurants` to fetch name/address/rating/reviews
6. Formats email content (two formats supported)
7. Sends email via Amazon SES
8. Saves latest state to `user-state` (extra credit)
9. Writes messageId to dedupe table (`lf2-processed`) to avoid reprocessing

---

## Architecture Flow
SQS (Q1) → LF2 → OpenSearch (RestaurantID + Cuisine) → DynamoDB (restaurant details) → SES (email)

---

## AWS Services Used
- AWS Lambda (LF2)
- Amazon SQS (Q1 trigger)
- Amazon OpenSearch Service (index `restaurants`)
- Amazon DynamoDB (`yelp-restaurants`, `lf2-processed`, `user-state`)
- Amazon SES (email sending)

---

## Input Message Format (SQS)

### Normal request (fresh search)
```json
{
  "email": "gk2845@nyu.edu",
  "location": "Manhattan",
  "cuisine": "Indian",
  "date": "Today",
  "time": "7 PM",
  "party_size": "2"
}
```

### Extra credit: Recommend using last search
Send `useLastSearch` (camelCase) or `use_last_search` (snake_case):

```json
{
  "email": "gk2845@nyu.edu",
  "useLastSearch": true
}
```

LF2 will load `lastCuisine` and `lastLocation` from the `user-state` table for this email and use those values to generate recommendations.

---

## Email Output Formats

### 1) Normal request email
Includes request details (location/date/time/party size) + recommendations.

### 2) Previous search email (`useLastSearch=true`)
Includes “Based on your most recent search…” + cuisine/location + recommendations.

---

## Environment Variables

| Variable | Required | Example | Description |
|----------|----------|---------|-------------|
| TABLE_NAME | Yes | yelp-restaurants | DynamoDB restaurants table |
| SENDER_EMAIL | Yes | gk2845@nyu.edu | Verified SES sender email |
| PROCESSED_TABLE | Yes | lf2-processed | DynamoDB dedupe table (messageId PK) |
| STATE_TABLE | Yes | user-state | DynamoDB state table (userId PK) |
| OPENSEARCH_ENDPOINT | Yes | https://search-...amazonaws.com | OpenSearch domain endpoint |
| OPENSEARCH_INDEX | Yes | restaurants | OpenSearch index name |
| OS_MASTER_USER | Yes* | gk2845 | Master user for basic auth |
| OS_MASTER_PASS | Yes* | ******** | Master password |

*Required if OpenSearch uses fine-grained access control (FGAC).

---

## DynamoDB Tables

### yelp-restaurants
Stores full restaurant metadata.
Minimum fields used by LF2:
- business_id (Partition Key)
- name
- address
- rating
- reviews

### lf2-processed (dedupe)
Prevents processing same SQS message multiple times.
- Partition Key: messageId (String)
- processedAt (ISO timestamp)

### user-state (extra credit)
Stores last search per user.
- Partition Key: userId (String) = user email
- lastCuisine
- lastLocation
- updatedAt

---

## Triggers
- Primary: SQS Q1 trigger (recommended)
- Optional: EventBridge schedule (if used, ensure it does not conflict with SQS trigger)

---

## Testing

### Option A — Send a message to Q1 (recommended)
SQS → Q1 → Send message → paste JSON body from the examples above.

Then verify:
- LF2 CloudWatch logs show execution
- Email arrives via SES

### Option B — Lambda test event
You can also test LF2 using an SQS-style test event with Records, but SQS console test is simplest.

---

## Notes / Expected Behavior
- Recommendations will vary each run because restaurants are randomly selected.
- If OpenSearch fails or returns empty, recommendations may be empty.
- State memory saves only cuisine + location (meets extra credit requirement).

---

## Folder Contents
```
LF2-worker/
├── lambda_function.py
├── requirements.txt
├── scheduler.md
└── README.md
```
