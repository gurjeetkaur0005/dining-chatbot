# LF2 — Suggestions Worker Lambda

## Overview

LF2 is a background worker Lambda function that processes dining requests from the SQS queue and sends restaurant recommendations via email.

This function is decoupled from the chatbot and runs periodically using an EventBridge (CloudWatch) schedule.

---

## Responsibilities

When invoked, LF2 performs the following steps:

1. Retrieves a message from the SQS queue (Q1)
2. Extracts user preferences (cuisine, location, dining time, number of people, email)
3. Queries OpenSearch to obtain restaurant IDs matching the requested cuisine
4. Fetches detailed restaurant information from DynamoDB
5. Formats restaurant suggestions into a readable message
6. Sends the recommendations via Amazon SES
7. Deletes the processed message from the queue

---

## Input Source

- **Amazon SQS Queue:** Q1  
- Messages are pushed by LF1 (Lex Code Hook Lambda)  
- Each message contains dining preferences collected during conversation  

### Example Message

```json
{
  "Location": "Manhattan",
  "Cuisine": "Japanese",
  "DiningTime": "7:00 PM",
  "People": "2",
  "Email": "user@example.com"
}
```

---

## AWS Services Used

- Amazon SQS — Queue (Q1)
- Amazon OpenSearch Service — Restaurant index
- Amazon DynamoDB — `yelp-restaurants` table
- Amazon SES — Email delivery
- Amazon EventBridge — Scheduled trigger (runs every minute)
- AWS Lambda — Serverless compute for background processing

---

## Data Flow

```
Lex Bot → LF1 → SQS Q1 → LF2 → OpenSearch → DynamoDB → SES → User Email
```

---

## DynamoDB Table

**Table Name:** `yelp-restaurants`

Fields used:

- business_id (Primary Key)
- name
- address
- rating
- zip_code
- coordinates
- number_of_reviews
- insertedAtTimestamp

DynamoDB stores full restaurant details scraped from Yelp.

---

## OpenSearch Index

- **Index Name:** restaurants  
- **Type:** Restaurant  
- Stored fields:
  - RestaurantID
  - Cuisine  

OpenSearch is used to quickly retrieve restaurant IDs based on cuisine.  
Detailed information is then fetched from DynamoDB.

---

## Email Output (Example)

```
Hello! Here are my Japanese restaurant suggestions for 2 people, today at 7:00 PM:

1. Sushi Nakazawa — 23 Commerce St
2. Jin Ramen — 3183 Broadway
3. Nikko — 1280 Amsterdam Ave

Enjoy your meal!
```

---

## Trigger Configuration

LF2 is invoked automatically using EventBridge:

- Schedule: Every 1 minute
- Purpose: Poll the queue and process pending requests
- This enables asynchronous processing independent of the chatbot

---

## Environment Requirements

The Lambda function requires IAM permissions for:

- SQS (ReceiveMessage, DeleteMessage)
- DynamoDB (GetItem / Query)
- OpenSearch (HTTP access)
- SES (SendEmail)
- CloudWatch Logs

---

## Deployment Notes

- Ensure SES sender email address is verified
- OpenSearch domain must be accessible from Lambda
- Queue visibility timeout should exceed Lambda execution time
- DynamoDB table must be populated with restaurant data
- OpenSearch index must be created and populated before running LF2

---

## Failure Handling

- If no messages are available, the function exits gracefully
- If an error occurs, the message remains in the queue for retry
- Failed executions can be monitored through CloudWatch Logs
