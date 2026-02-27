# LF3 — Last Search Recommendation Trigger (State → SQS)

## Overview
LF3 implements the **Extra Credit: State Memory** feature for the Dining Concierge application.

It retrieves a user's **last search (cuisine + location)** from a DynamoDB table (`user-state`) and sends a request to the SQS queue (Q1). The worker Lambda (LF2) then generates recommendations based on that saved state and emails them to the user.

LF3 itself does NOT query OpenSearch or send email — it only triggers the recommendation workflow.

---

## What LF3 Does (High-Level)
1. Accepts a request containing `userId` or `email`
2. Reads last search from DynamoDB table `user-state`
3. Builds a payload with `useLastSearch = true`
4. Sends the payload to SQS queue Q1
5. Returns a confirmation response

---

## Architecture Flow
Client → LF3 → DynamoDB (`user-state`) → SQS (Q1) → LF2 → OpenSearch + DynamoDB → SES (email)

---

## AWS Services Used
- AWS Lambda (LF3)
- Amazon DynamoDB (`user-state` table)
- Amazon SQS (Q1 queue)

---

## Input Event Format

LF3 accepts either `userId` or `email`:

```json
{
  "email": "gk2845@nyu.edu"
}
```

or

```json
{
  "userId": "gk2845@nyu.edu"
}
```

The value must match the partition key stored in the `user-state` table.

---

## Output Response

Successful request:

```json
{
  "sentToQueue": true,
  "message": "Last-search recommendation request sent to queue"
}
```

If no saved state exists:

```json
"No saved state found for this user"
```

---

## Payload Sent to SQS (Q1)

LF3 sends this message to Q1 for LF2 to process:

```json
{
  "email": "gk2845@nyu.edu",
  "useLastSearch": true,
  "location": "Manhattan",
  "cuisine": "Indian"
}
```

LF2 uses `useLastSearch=true` to load the latest state and generate recommendations.

---

## Environment Variables

| Variable | Required | Example | Description |
|----------|----------|---------|-------------|
| STATE_TABLE | Yes | user-state | DynamoDB table storing last searches |
| QUEUE_URL | Yes | https://sqs.../Q1 | URL of SQS queue Q1 |

---

## DynamoDB Table: user-state

Partition Key: `userId` (String) — typically the user's email

Example item:

```json
{
  "userId": "gk2845@nyu.edu",
  "lastCuisine": "Indian",
  "lastLocation": "Manhattan",
  "updatedAt": "2026-02-27T02:12:36Z"
}
```

---

## IAM Permissions Required

LF3 execution role must allow:

### DynamoDB
- `dynamodb:GetItem` on `user-state`

### SQS
- `sqs:SendMessage` on Q1

---

## Testing

### Lambda Console Test Event

```json
{
  "email": "gk2845@nyu.edu"
}
```

Then verify:

- LF3 returns success response
- Message appears in SQS Q1
- LF2 processes message
- Recommendation email is received

---

## Notes

- LF3 only triggers recommendations; it does not generate them.
- The email content and restaurant selection are handled entirely by LF2.
- This design keeps the recommendation system modular and decoupled from the chatbot.

---

## Folder Contents

```
LF3-state/
├── lambda_function.py
├── requirements.txt
└── README.md
```
