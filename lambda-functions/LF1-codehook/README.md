# Dining Concierge – AWS Lambda (Lex + SQS Integration)

## Overview

This AWS Lambda function serves as the fulfillment backend for an **Amazon Lex V2 chatbot**.

It collects restaurant reservation details from users and:

- Validates input
- Enforces Manhattan-only support
- Rejects past dates
- Sends structured messages to **Amazon SQS**
- Closes the conversation once fulfilled

It also supports an **Extra Credit feature** that allows users to reuse their last search.

---

## Architecture

User → Amazon Lex → AWS Lambda → Amazon SQS → (Downstream Processor)

---

## Features

### 1. Slot Validation
- Ensures all required slots are filled
- Rejects past dates
- Validates Manhattan-only location
- Ensures valid email collection

### 2. Manhattan Restriction
Currently supports:
- **Manhattan only**

Any other location triggers slot re-elicitation.

### 3. Extra Credit – Reuse Last Search

Intent: `UseLastSearchIntent`

- Collects Email
- Sends SQS message with:
  ```json
  {
    "email": "...",
    "useLastSearch": true
  }
  ```

---

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SQS_QUEUE_URL` | URL of the target SQS queue | ✅ Yes |
| `SQS_REGION` | AWS region of the SQS queue | Optional (default: us-east-1) |

Example:

```bash
SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/123456789012/restaurant-queue
SQS_REGION=us-east-1
```

---

## Required IAM Permissions

Lambda execution role must allow:

```json
{
  "Effect": "Allow",
  "Action": [
    "sqs:SendMessage"
  ],
  "Resource": "arn:aws:sqs:*:*:*"
}
```

---

## Supported Lex Intents

### 1️⃣ Dining Intent (Main Booking Flow)

Required Slots:
- Location
- Cuisine
- Date
- Time
- PartySize
- Email

Behavior:
- Validates all slots
- Rejects past dates
- Enforces Manhattan-only
- Sends structured payload to SQS
- Closes conversation

---

### 2️⃣ UseLastSearchIntent (Extra Credit)

Required Slot:
- Email

Behavior:
- Sends payload with `useLastSearch = true`
- Closes conversation

---

## SQS Message Format

### Normal Booking

```json
{
  "email": "user@example.com",
  "cuisine": "Italian",
  "location": "Manhattan",
  "date": "2026-03-10",
  "time": "19:00",
  "party_size": "4",
  "useLastSearch": false
}
```

### Reuse Last Search

```json
{
  "email": "user@example.com",
  "useLastSearch": true
}
```

---

## Validation Rules

### Date Validation
- Must follow `YYYY-MM-DD`
- Cannot be a past date

### Location Validation
- Only `"Manhattan"` is accepted
- Case-insensitive comparison

---

## Deployment Instructions

### Step 1: Create Lambda Function
- Runtime: Python 3.9+
- Paste the provided code

### Step 2: Configure Environment Variables
Add:
- `SQS_QUEUE_URL`
- `SQS_REGION` (optional)

### Step 3: Attach IAM Role
Grant SQS `SendMessage` permission.

### Step 4: Connect to Amazon Lex
- Add Lambda as Fulfillment Code Hook
- Enable Lambda invocation for intents

---

## Error Handling

The function:
- Re-elicits invalid or missing slots
- Throws error if SQS_QUEUE_URL is not configured
- Logs Lex events and SQS message IDs to CloudWatch

---

## Helper Functions Overview

| Function | Purpose |
|----------|----------|
| `get_slot_value()` | Extract interpreted slot values |
| `elicit_slot()` | Ask user to re-enter a slot |
| `close()` | Close conversation with fulfillment |
| `send_to_sqs()` | Send message to SQS |
| `title_case_cuisine()` | Normalize cuisine formatting |

---

## Example User Flow

User: I want Italian food  
Bot: What location?  
User: Manhattan  
Bot: What date?  
User: Yesterday  
Bot: The date cannot be in the past. Please enter a future date.  
...  
Bot: Thanks! You're all set. You'll receive restaurant recommendations shortly.

---

## Future Enhancements

- Add time validation (no past times on same day)
- Add party size numeric validation
- Support multiple NYC boroughs
- Add DynamoDB to store last searches
- Add SES integration for email recommendations
- Add OpenSearch for real-time restaurant lookup

---

## Logging & Monitoring

- Lex events logged via `print`
- SQS message IDs logged for traceability
- Monitor in CloudWatch Logs

---

## Author
Vandana Rawat
Dining Concierge – Cloud Computing Project

---

## License

For academic and development use.