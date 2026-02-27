# LF2 Scheduler Configuration

## Overview

LF2 is a background worker Lambda that processes dining requests from the SQS queue (Q1).  
It is triggered automatically using Amazon EventBridge on a fixed schedule.

## Schedule

- Service: Amazon EventBridge (CloudWatch Events)
- Trigger Type: Scheduled rule
- Expression: `rate(1 minute)`
- State: Enabled

## Purpose

Each invocation:

1. Polls the SQS queue (Q1)
2. Processes pending requests
3. Sends restaurant recommendations via SES
4. Deletes processed messages
5. Exits if no messages are available

## Configuration Steps

1. Open AWS Console → EventBridge → Rules
2. Create a new rule (Schedule)
3. Choose rate-based schedule: 1 minute
4. Set target as the LF2 Lambda function
5. Enable the rule

## Notes

- Enables asynchronous processing independent of the chatbot
- Requires permission to invoke Lambda (`lambda:InvokeFunction`)
- Execution and errors can be monitored via CloudWatch Logs
