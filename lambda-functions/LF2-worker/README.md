# LF2 — Dining Concierge Worker (SQS → OpenSearch/DynamoDB → SES)

This repository contains **LF2**, the *worker Lambda* for the NYU Dining Concierge system.

LF2 consumes dining requests from **SQS (Q1)**, fetches restaurant IDs from **OpenSearch**, loads full restaurant details from **DynamoDB**, and sends recommendations to the user via **Amazon SES**.

> ✅ **Public repo safe:** This README uses **placeholders only**. Do **NOT** commit real emails, endpoints, usernames, or passwords. Store them in **Lambda environment variables**.

---

## Architecture Context

S3 (Frontend) → API Gateway → LF0 → Lex → LF1 → **SQS (Q1)** → **LF2** → OpenSearch + DynamoDB → SES (Email)

LF2 is responsible for the highlighted section.

---

## What LF2 Does

For each SQS message:

1. **Dedupes** the message using a DynamoDB table (`lf2-processed`) *(optional but recommended)*.
2. Parses the JSON payload (location/cuisine/date/time/party size/email).
3. Queries **OpenSearch** for restaurant IDs matching the cuisine.
4. Picks up to **3 random restaurants**.
5. Batch-gets full details from **DynamoDB** (`yelp-restaurants`).
6. Formats an email body and sends it via **SES**.
7. Saves the user’s last search state to DynamoDB (`user-state`) *(optional/extra credit)*.
8. Marks the message as processed.

---

## Repo Structure (Suggested)

```
lambda-functions/
  LF2/
    lambda_function.py
    README.md
```

---

## Input: SQS Message Format

LF2 expects the **SQS message body** to be JSON.

### Example
```json
{
  "email": "recipient@example.com",
  "cuisine": "Indian",
  "location": "Manhattan",
  "date": "2026-03-01",
  "time": "19:00",
  "party_size": "2",
  "previous_search": false
}
```

### Supported Keys
- `email` *(required)* — recipient email address
- `cuisine` *(optional)* — defaults to `"Indian"`
- `location` *(optional)* — defaults to `"Manhattan"`
- `date` *(optional)* — defaults to `"Today"`
- `time` *(optional)* — defaults to `"7 PM"`
- `party_size` *(optional)* — defaults to `"2"`
- `previous_search` *(optional boolean)* — changes email wording

> If your LF1 uses different key names, update LF2’s parsing accordingly.

---

## DynamoDB Tables

### 1) Restaurants Table (required)
- **Table name:** `yelp-restaurants` *(default via `TABLE_NAME`)*
- **Partition key:** `business_id` (String)

**Minimum attributes recommended per item**
- `business_id` (String) — Yelp business id (PK)
- `name` (String)
- `address` (String)
- `rating` (Number)
- `reviews` (Number) *(or rename in code if your table uses `review_count`)*
- `zip` (String) *(optional)*
- `cuisine` (String) *(recommended for fallback/querying)*
- `insertedAtTimestamp` (String)

LF2 currently batch-reads these attributes:
- `name`, `address`, `rating`, `reviews`

So make sure those fields exist in DynamoDB (or adjust `ddb_batch_get_by_ids()`).

### 2) Processed Messages Table (optional, recommended)
- **Table name:** `lf2-processed` *(default via `PROCESSED_TABLE`)*
- **Partition key:** `messageId` (String)

Used to avoid duplicate emails when Lambda retries.

### 3) State Memory Table (optional / extra credit)
- **Table name:** `user-state` *(default via `STATE_TABLE`)*
- **Partition key:** `userId` (String)

Stores:
- `lastCuisine`, `lastLocation`, `updatedAt`

---

## OpenSearch Setup (Create LAST — Cost Risk)

- **Endpoint:** set via `OPENSEARCH_ENDPOINT`
- **Index:** `restaurants` *(default via `OPENSEARCH_INDEX`)*

LF2 queries by cuisine using:
- `term` query on field `Cuisine`
- returns `_source.RestaurantID`

### Expected Document Shape
```json
{
  "RestaurantID": "some-yelp-business-id",
  "Cuisine": "Indian"
}
```

> **Important:** `term` queries are case-sensitive depending on mapping. Keep cuisine values consistent (e.g., Title Case) or use a keyword field.

### Auth
This implementation uses **Basic Auth** via:
- `OS_MASTER_USER`
- `OS_MASTER_PASS`

If your domain uses IAM SigV4 instead, you must replace the OpenSearch request signing logic.

---

## Environment Variables (Lambda Configuration)

Set these in **AWS Lambda → Configuration → Environment variables**.

| Variable | Example (placeholder) | Required | Notes |
|---|---|---:|---|
| `TABLE_NAME` | `yelp-restaurants` | ✅ | Restaurants DynamoDB table |
| `SENDER_EMAIL` | `verified-sender@example.com` | ✅ | Must be verified in SES |
| `PROCESSED_TABLE` | `lf2-processed` | Optional | Dedupe table |
| `STATE_TABLE` | `user-state` | Optional | State memory table |
| `MAX_SCAN_ITEMS` | `300` | Optional | Reserved for fallback patterns |
| `OPENSEARCH_ENDPOINT` | `https://search-xxxx.us-east-1.es.amazonaws.com` | ✅* | Required if using OpenSearch |
| `OPENSEARCH_INDEX` | `restaurants` | Optional | Default: `restaurants` |
| `OS_MASTER_USER` | `admin` | ✅* | Required if using Basic Auth |
| `OS_MASTER_PASS` | `change-me` | ✅* | Required if using Basic Auth |

\* Required only if you are using OpenSearch in LF2.

---

## IAM Permissions (LF2 Execution Role)

Attach permissions for:

### SQS (needed when triggered by SQS)
- `sqs:ReceiveMessage`
- `sqs:DeleteMessage`
- `sqs:GetQueueAttributes`
- `sqs:ChangeMessageVisibility`

### DynamoDB (required)
- `dynamodb:GetItem`
- `dynamodb:BatchGetItem`
- `dynamodb:PutItem` *(for processed/state tables)*
- `dynamodb:UpdateItem` *(optional)*
- `dynamodb:Query` *(optional)*
- `dynamodb:Scan` *(optional; avoid in production)*

### SES (required)
- `ses:SendEmail`
- `ses:SendRawEmail`

### OpenSearch (required if using OpenSearch)
- `es:ESHttpGet`
- `es:ESHttpPost`

> Best practice: scope resources to your specific Queue ARN, Table ARNs, SES identity, and OpenSearch domain.

---

## SES Notes (Common Gotcha)

If SES is in **Sandbox**:
- The **sender** must be verified.
- The **recipient** must also be verified.

Move out of sandbox if your class allows it; otherwise verify both emails.

---

## Deploy & Test

### 1) Upload code
Upload `lambda_function.py` to the LF2 Lambda.

### 2) Configure trigger
Add **SQS trigger** to LF2:
- queue: `Q1`

### 3) Send a test message to Q1
Use SQS Console → *Send and receive messages*:

```json
{"email":"recipient@example.com","cuisine":"Chinese","location":"Manhattan","date":"Today","time":"7 PM","party_size":"4"}
```

### 4) Verify logs
Check **CloudWatch Logs** for:
- message parsed
- OpenSearch hits returned
- DynamoDB batch-get results
- SES send success

---

## Public Repo Safety Checklist ✅

- [ ] No real `SENDER_EMAIL` committed
- [ ] No `OPENSEARCH_ENDPOINT` committed
- [ ] No `OS_MASTER_USER/OS_MASTER_PASS` committed
- [ ] `.env` is gitignored
- [ ] README uses placeholders only

### Recommended Files

Create `.env.example` (safe to commit):
```env
TABLE_NAME=yelp-restaurants
SENDER_EMAIL=verified-sender@example.com
PROCESSED_TABLE=lf2-processed
STATE_TABLE=user-state
OPENSEARCH_ENDPOINT=https://search-xxxx.us-east-1.es.amazonaws.com
OPENSEARCH_INDEX=restaurants
OS_MASTER_USER=admin
OS_MASTER_PASS=change-me
```

Add to `.gitignore`:
```gitignore
.env
*.pem
*.key
```

---

## Troubleshooting

### “Email address not verified”
- Verify sender in SES
- If sandbox, verify recipient too

### SQS trigger not firing
- Confirm trigger is attached to LF2
- Confirm LF2 role has SQS permissions
- Confirm messages are visible (not stuck due to visibility timeout)

### OpenSearch errors (401/403)
- Check endpoint starts with `https://`
- Check Basic Auth vars are set
- Ensure OpenSearch security is configured to allow that user
- Confirm index name matches `OPENSEARCH_INDEX`

### DynamoDB KeyError (missing fields)
If you see KeyError for `name/address/rating/reviews`, your table schema differs.
Update `ddb_batch_get_by_ids()` to match your stored attribute names.

---

## Cost Note (Important)

**Create OpenSearch LAST** and delete it after the demo to avoid ongoing charges.
Use minimal settings (single node, dev/test, single AZ) per assignment guidance.
