# EventBridge Scheduler (LF2 Worker)

## Purpose
Run **LF2** automatically every minute so it can poll **SQS (Q1)** and process restaurant suggestion requests without manual invocation.

## Schedule
- Service: **Amazon EventBridge Scheduler**
- Schedule type: **Rate-based**
- Expression: `rate(1 minute)`
- State: **Enabled**
- Action after completion: **NONE**

## Target
- Target API: **AWS Lambda → Invoke**
- Target function: **LF2**
- Input (payload):
```json
{ "source": "scheduler", "job": "poll-q1" }
```

## Retry Policy
- Retry: **Enabled**
- Maximum event age: **5 minutes**
- Retry attempts: **2**

## Dead-Letter Queue (DLQ) (Recommended)
- DLQ Type: **Standard SQS queue**
- DLQ Name: `lf2-scheduler-dlq`
- Purpose: Stores failed invocations if Scheduler cannot deliver to LF2.

> Note: Do **NOT** use the main request queue **Q1** as the DLQ.

## Permissions
- Execution role: **Create new role for this schedule**
- Required permission:
  - `lambda:InvokeFunction` on LF2

## Verification
1. **Lambda → LF2 → Monitor**
   - Invocations increase approximately **1 per minute**
   - Success rate ~ **100%**
2. **CloudWatch Logs**
   - Log entries show repeated `START RequestId` events every minute.
3. **SQS Q1**
   - Messages decrease to **0** after LF2 processes and deletes them (no duplicates).
