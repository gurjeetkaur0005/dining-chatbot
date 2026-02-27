# LF3 — Stateful Recommendation Lambda (Extra Credit)

## Overview

LF3 is an optional Lambda function that enables stateful behavior for the Dining Concierge chatbot.  
It retrieves the user's previous dining preferences and provides recommendations automatically when the user returns.

---

## Purpose

This function implements the extra credit requirement by remembering past dining searches.

When invoked, LF3:

1. Retrieves stored user preferences from DynamoDB
2. Uses the saved cuisine and location
3. Generates restaurant recommendations
4. Returns suggestions without asking the user again

---

## Data Source

User preferences are stored in a DynamoDB table.

**Example stored fields:**

- UserID (Primary Key)
- Location
- Cuisine
- DiningTime
- NumberOfPeople
- Timestamp

---

## AWS Services Used

- Amazon DynamoDB — Stores user search history
- AWS Lambda — Processes recommendations
- Amazon OpenSearch — Retrieves restaurant IDs by cuisine
- Amazon SES — Sends recommendations via email (optional)

---

## Data Flow

```
User returns → LF3 → DynamoDB → OpenSearch → DynamoDB → Response / Email
```

---

## DynamoDB Table

**Table Name:** user-search-history

Each entry stores the user's last dining request.

---

## Invocation

LF3 may be triggered:

- From LF0 (API Lambda)
- From the chatbot when a returning user is detected
- Manually for testing

---

## Output

Provides restaurant suggestions based on the user's previous search preferences.

---

## Notes

- This component is optional and implemented only for extra credit
- If no previous search exists, the chatbot proceeds normally
- Improves user experience by enabling personalized recommendations
