# LF3 — Scheduler / Trigger Lambda (EventBridge → SQS/LF2)

This repository contains **LF3**, the *scheduler/trigger Lambda* for the NYU Dining Concierge system.

LF3 is designed to run on a fixed interval (typically **every 1 minute**) using **Amazon EventBridge Scheduler** (or EventBridge rule). Its job is to **kick off background processing** reliably without relying on user traffic.

> ✅ **Public repo safe:** This README uses **placeholders only**. Do **NOT** commit real AWS endpoints, emails, usernames, passwords, or account-specific ARNs.

---

## Where LF3 Fits in the Architecture

S3 (Frontend) → API Gateway → LF0 → Lex → LF1 → SQS(Q1) → LF2 → OpenSearch + DynamoDB → SES

LF3 is **out-of-band** and supports the worker pipeline by triggering processing on a schedule.

**Typical patterns used in class projects:**

### Pattern A (Recommended): LF3 triggers LF2 (direct invoke)
EventBridge Scheduler → **LF3** → Invoke **LF2**
- LF2 still reads from SQS and processes messages
- LF3 does *not* touch restaurant data

### Pattern B: LF3 polls SQS (lightweight) and invokes LF2 only if needed
EventBridge Scheduler → **LF3** → Check `ApproximateNumberOfMessages` on Q1 → Invoke LF2 if > 0

### Pattern C: LF3 replays requests (extra credit / state memory)
EventBridge Scheduler → **LF3** → Read `user-state` DynamoDB → Send “previous search” message(s) into Q1

> Your team should pick **one** pattern and keep it simple. Most graders are happy with Pattern A or B.

---

## What LF3 Does (Default Implementation)

When triggered by EventBridge:

1. Optionally checks whether Q1 has messages waiting (Pattern B).
2. Invokes LF2 (async) so LF2 can process queued requests.
3. Returns 200 to EventBridge.

LF3 should be **small** and **cheap**.

---

## Repo Structure (Suggested)

```
lambda-functions/
  LF3/
    lambda_function.py
    README.md
```

---

## EventBridge Scheduler Setup

### Schedule
- Frequency: **every 1 minute**

Example (EventBridge rule style):
- Rate expression: `rate(1 minute)`

EventBridge Scheduler (new UI) is also fine.

### Target
- Target: **LF3 Lambda ARN**
- Payload: optional (can be `{}`)

---

## Environment Variables

Set these in **AWS Lambda → Configuration → Environment variables**.

| Variable | Example (placeholder) | Required | Notes |
|---|---|---:|---|
| `QUEUE_URL` | `https://sqs.us-east-1.amazonaws.com/123456789012/Q1` | Optional | Needed for Pattern B/C |
| `LF2_FUNCTION_NAME` | `LF2` | Optional | Needed for Pattern A/B |
| `STATE_TABLE` | `user-state` | Optional | Needed for Pattern C |
| `AWS_REGION` | `us-east-1` | Optional | Defaults to Lambda region |

> Keep environment variables **as placeholders in the repo**. Real values go only in AWS.

---

## IAM Permissions (LF3 Execution Role)

Choose permissions based on your chosen pattern.

### Pattern A — Invoke LF2 only
- `lambda:InvokeFunction` on LF2

### Pattern B — Check SQS and invoke LF2
- `sqs:GetQueueAttributes` on Q1
- `lambda:InvokeFunction` on LF2

### Pattern C — Read state and enqueue messages
- `dynamodb:Scan` or `dynamodb:Query` on `user-state`
- `sqs:SendMessage` on Q1
- (optional) `lambda:InvokeFunction` on LF2

> Best practice: scope resources to the specific LF2 ARN / Queue ARN / Table ARN.

---

## Testing

### 1) Manual test invoke in Lambda console
- Create a test event:
```json
{}
```
- Run LF3
- Confirm in CloudWatch logs that it:
  - invoked LF2, or
  - checked Q1 and invoked LF2 when messages exist

### 2) End-to-end
- Send an SQS message into Q1 (from LF1 or manual)
- Wait for scheduler tick (1 minute)
- Confirm LF2 runs and sends email

---

## Common Issues & Fixes

### “AccessDeniedException” when invoking LF2
- Add `lambda:InvokeFunction` permission to LF3 role for the LF2 ARN

### Scheduler is not firing
- Confirm EventBridge schedule is **Enabled**
- Confirm correct target Lambda selected
- Check EventBridge “Invocations” and “FailedInvocations” metrics

### LF3 runs but LF2 doesn’t process messages
- Ensure LF2 has SQS trigger attached *or* LF2 code reads from SQS when invoked
- Confirm Q1 has messages and they are visible (not in-flight)

---

## Public Repo Safety Checklist ✅

- [ ] No real `QUEUE_URL` committed
- [ ] No real Lambda ARNs committed
- [ ] No account IDs committed
- [ ] README uses placeholders only
