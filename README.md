# 🍽️ Dining Concierge Chatbot — Serverless AWS Application

## Overview

The Dining Concierge Chatbot is a fully serverless, cloud‑native application built on AWS.  
It allows users to request restaurant recommendations in Manhattan via a conversational interface powered by Amazon Lex. Recommendations are generated using Yelp data and delivered by email.

The system demonstrates an end‑to‑end event‑driven architecture integrating multiple AWS services including API Gateway, Lambda, SQS, DynamoDB, OpenSearch, SES, and S3.

---

## ✨ Key Features

- Conversational chatbot interface (Amazon Lex V2)
- Restaurant recommendations for Manhattan by cuisine
- Email delivery of suggestions via Amazon SES
- Event‑driven processing using SQS queues
- Scalable serverless architecture (AWS Lambda)
- Search optimization using Amazon OpenSearch
- Persistent storage with DynamoDB
- “Use Last Search” feature (state memory — extra credit)
- Static frontend hosted on Amazon S3

---

## 🏗️ Architecture

Frontend (S3 Website)  
→ API Gateway  
→ Lex Proxy Lambda  
→ Amazon Lex V2  
→ Fulfillment Lambda  
→ SQS (Q1)  
→ Worker Lambda (LF2)  
→ OpenSearch + DynamoDB  
→ Amazon SES (Email)

Optional:  
LF3 State Trigger → DynamoDB (user-state) → SQS → LF2

---

## 🧩 AWS Services Used

| Service | Purpose |
|----------|---------|
| Amazon S3 | Static website hosting |
| API Gateway | HTTP endpoint for chatbot |
| AWS Lambda | Backend compute (multiple functions) |
| Amazon Lex V2 | Natural language chatbot |
| Amazon SQS | Asynchronous message queue |
| Amazon DynamoDB | Restaurant data + state storage |
| Amazon OpenSearch | Fast cuisine‑based search |
| Amazon SES | Email delivery |

---

## 📦 Data Pipeline

### Yelp Data Collection

Restaurant data is collected using the Yelp API across multiple cuisines in Manhattan.

Steps:

1. Scrape restaurants for 10 cuisines
2. Store full records in DynamoDB (`yelp-restaurants`)
3. Index RestaurantID + Cuisine in OpenSearch (`restaurants` index)

This separation enables efficient search while retaining full metadata.

---

## ⚙️ Core Components

### 1) Frontend (S3)

- Static web app for user interaction
- Sends chat messages to API Gateway
- Displays responses from Lex

---

### 2) Lex Proxy Lambda

- Receives requests from API Gateway
- Forwards text to Amazon Lex V2
- Returns chatbot responses to frontend
- Maintains session using client IP hash

---

### 3) Lex Fulfillment Lambda

Validates user inputs:

- Location (Manhattan only)
- Cuisine (predefined list)
- Date (future only)
- Time
- Party size
- Email

Once valid, sends request to SQS.

Supports extra credit intent:

➡️ **UseLastSearchIntent** — reuses previous search using email only.

---

### 4) LF2 — Suggestions Worker

Triggered by SQS messages.

Responsibilities:

1. Retrieve cuisine (or last search)
2. Query OpenSearch for restaurant IDs
3. Fetch full details from DynamoDB
4. Select recommendations randomly
5. Send formatted email via SES
6. Save last search to `user-state`
7. Deduplicate processed messages

---

### 5) LF3 — State Trigger (Extra Credit)

Allows users to request recommendations based on their previous search.

Flow:

Client → LF3 → DynamoDB (`user-state`) → SQS → LF2 → Email

LF3 does not generate recommendations itself.

---

## 🗄️ DynamoDB Tables

### yelp-restaurants
Stores complete restaurant information.

Primary Key: `business_id`

### user-state
Stores last search per user.

Primary Key: `userId` (email)

### lf2-processed
Prevents duplicate processing of SQS messages.

Primary Key: `messageId`

---

## 🔍 OpenSearch Index

Index Name: `restaurants`

Stored fields per document:

- RestaurantID
- Cuisine

Used for fast retrieval of candidate restaurants by cuisine.

---

## ✉️ Email Output

Users receive an email containing:

- Requested cuisine
- Location
- Suggested restaurants (name, address, rating)
- Booking details (if provided)

---

## 🚀 Deployment Steps (High‑Level)

1. Collect Yelp data and populate DynamoDB
2. Index cuisine data into OpenSearch
3. Create SQS queue (Q1)
4. Deploy Lambda functions:
   - Lex Proxy
   - Fulfillment Lambda
   - LF2 Worker
   - LF3 (optional)
5. Configure Amazon Lex intents and slots
6. Set up SES verified email
7. Deploy frontend to S3
8. Connect API Gateway to Lambda

---

## 🧪 Testing

### Chatbot Flow

1. Open frontend website
2. Start conversation
3. Provide required details
4. Receive confirmation message
5. Check email for recommendations

### Last Search Feature

Provide only email → system reuses saved preferences.

---

## 📁 Repository Structure

```
frontend/                # Static website files
yelp-scripts/            # Data collection & indexing scripts
LF2-worker/              # Suggestions worker Lambda
LF3-state/               # Last-search trigger Lambda
lex-fulfillment/         # Lex fulfillment function
lex-proxy/               # API Gateway → Lex bridge
README.md                # Project documentation
```

---

## 🎯 Learning Outcomes

This project demonstrates:

- Serverless system design
- Event-driven architectures
- Cloud integration across services
- Conversational AI deployment
- Scalable backend processing
- Data ingestion and search pipelines

---

## 👩‍💻 Author

**Vandana Rawat**
**Gurjeet Kaur**  
NYU Tandon School of Engineering  
Master’s in Computer Science

---

## 📄 License

This project is developed for educational purposes.

