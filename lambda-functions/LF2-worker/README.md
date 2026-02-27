# LF2 — Dining Concierge Worker Lambda

LF2 is the **worker Lambda** in the Dining Concierge pipeline. It consumes requests from **SQS (Q1)**, fetches restaurant suggestions from **OpenSearch** (or DynamoDB fallback), pulls full restaurant details from **DynamoDB**, and sends the final recommendations to the user via **Amazon SES**.

---

## What LF2 Does (End-to-End)

1. **Triggered by SQS** (and optionally by an EventBridge schedule that “pokes” the queue).
2. Reads 1+ messages from **Q1**.
3. For each message, extracts:
   - `cuisine`, `location`, `date`, `time`, `partySize`, `email`
4. Finds candidate restaurants:
   - **Primary**: query **OpenSearch** for the given cuisine (randomized selection)
   - **Fallback**: query **DynamoDB** by cuisine if OpenSearch is not available
5. Loads full restaurant records from **DynamoDB** (`yelp-restaurants`).
6. Formats a friendly email body with **3 restaurant recommendations**.
7. Sends the email using **SES**.
8. Deletes the message from SQS only after success (so failed messages can retry).

---

## Repository Location

Recommended folder structure:

```
lambda-functions/
  LF2/
    lambda_function.py
    requirements.txt
    README.md
```

---

## AWS Resources LF2 Depends On

### 1) SQS
- Queue name: `Q1`

LF2 receives messages in this queue and deletes them after processing.

### 2) DynamoDB
- Table name: `yelp-restaurants`
- Partition key: `business_id` (String)

**Minimum attributes to store per restaurant**
- `business_id` (PK)
- `name`
- `address`
- `coordinates` (optional)
- `rating`
- `review_count` (or `reviews`)
- `zip`
- `cuisine`
- `insertedAtTimestamp`

### 3) OpenSearch (Create LAST — cost risk)
- Domain endpoint: `https://...es.amazonaws.com` (or OpenSearch endpoint)
- Index: `restaurants`

**Suggested indexed fields**
- `RestaurantID` (same as Yelp `business_id`)
- `Cuisine`

LF2 queries OpenSearch by cuisine and then uses returned IDs to fetch details from DynamoDB.

### 4) Amazon SES
- Sender email must be **verified in SES**
- In SES Sandbox: recipient emails must also be verified (unless you request production access)

---

## Message Format in Q1

LF2 expects the SQS message body to be JSON, for example:

```json
{
  "location": "Manhattan",
  "cuisine": "Indian",
  "date": "2026-03-01",
  "time": "19:00",
  "partySize": "2",
  "email": "someone@example.com"
}
```

> If your LF1 uses a different key naming, update LF2 parsing accordingly.

---

## Environment Variables

Set these on the LF2 Lambda configuration:

| Name | Example | Required | Notes |
|------|---------|----------|------|
| `TABLE_NAME` | `yelp-restaurants` | ✅ | DynamoDB table |
| `SENDER_EMAIL` | `your-verified-sender@domain.com` | ✅ | Verified in SES |
| `OPENSEARCH_ENDPOINT` | `https://search-xxxx.us-east-1.es.amazonaws.com` | Optional | If missing, LF2 uses DynamoDB fallback |
| `OPENSEARCH_INDEX` | `restaurants` | Optional | Default: restaurants |
| `OS_MASTER_USER` | `admin` | Optional | Only if using basic auth |
| `OS_MASTER_PASSWORD` | `...` | Optional | Only if using basic auth |
| `AWS_REGION` | `us-east-1` | Optional | Defaults to Lambda region |

---

## IAM Permissions (LF2 Execution Role)

Attach a policy that allows:

### SQS
- `sqs:ReceiveMessage`
- `sqs:DeleteMessage`
- `sqs:GetQueueAttributes`
- `sqs:ChangeMessageVisibility`

### DynamoDB
- `dynamodb:GetItem`
- `dynamodb:BatchGetItem`
- `dynamodb:Query`
- `dynamodb:Scan` *(avoid if you can, but OK for fallback/testing)*

### SES
- `ses:SendEmail`
- `ses:SendRawEmail`

### OpenSearch (if used)
- `es:ESHttpGet`
- `es:ESHttpPost`

> In class projects, you can scope resources to your specific Queue ARN, Table ARN, SES identity ARN, and OpenSearch domain ARN.

---

## Deploying LF2

### Option A — Zip upload (simple)
1. Put your code in `lambda_function.py`
2. If dependencies are needed (e.g., `urllib3` is already available; `requests` usually is not), package them:
   - `pip install -r requirements.txt -t .`
   - zip the folder and upload to Lambda

### Option B — Container image (advanced)
Not required for the assignment unless your team chose containers.

---

## Testing LF2

### 1) Send a test message into Q1
Using AWS Console → SQS → Send and receive messages:

```json
{"location":"Manhattan","cuisine":"Chinese","date":"2026-03-01","time":"19:00","partySize":"4","email":"you@example.com"}
```

### 2) Invoke LF2
If LF2 is configured as an SQS trigger, it will run automatically.

### 3) Check logs
CloudWatch Logs → Log group for LF2

Look for:
- message received
- restaurants selected
- SES send response
- message deleted

---

## Common Issues & Fixes

### SES: “Email address not verified”
- Verify `SENDER_EMAIL` in SES
- If SES is in sandbox, verify the recipient email too

### SQS trigger not firing
- Confirm Lambda trigger is attached to Q1
- Check Lambda has permissions to read SQS
- Ensure messages are visible (not stuck due to visibility timeout)

### OpenSearch 403 / auth failures
- If using fine-grained access control, confirm master user/pass
- Ensure LF2 role can access domain OR use signed requests (IAM-based)
- Confirm endpoint includes `https://`

### DynamoDB empty results
- Confirm `TABLE_NAME`
- Confirm items exist (scan table in console)
- Confirm cuisine values match your query exactly (case/spacing)

---

## Cost Safety Notes (Important)

- **Create OpenSearch last** and delete after demo.
- Keep domain minimal: **1 data node, t3.small.search, 1-AZ dev/test**.
- Don’t enable standby nodes or multi-AZ.

---

## Done Checklist

- [ ] Q1 exists and has messages arriving from LF1
- [ ] `yelp-restaurants` is populated (1000+ items, 5 cuisines)
- [ ] LF2 has environment variables set
- [ ] LF2 IAM role has SQS + DynamoDB + SES permissions
- [ ] SES sender verified (recipient verified if sandbox)
- [ ] LF2 sends email and deletes SQS message
- [ ] OpenSearch created last (optional but required by assignment spec)

