# AWS Lambda – Lex Proxy Response Handler (API Gateway Integration)

## Overview

This AWS Lambda function acts as a **proxy between API Gateway and Amazon Lex V2**.

It:

* Receives chat messages from a frontend (e.g., `chat.js`)
* Extracts user text safely
* Generates a stable session ID per client
* Sends the message to Amazon Lex V2
* Returns a Lex-compatible response format expected by the frontend

This implementation supports **REST API and HTTP API Gateway proxy integration**.

---

## Function Code

```python
import json
import os
import hashlib
import boto3

lex = boto3.client("lexv2-runtime")

BOT_ID = os.environ["BOT_ID"]
BOT_ALIAS_ID = os.environ["BOT_ALIAS_ID"]
LOCALE_ID = os.environ.get("LOCALE_ID", "en_US")

def cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Methods": "OPTIONS,POST,GET",
    }

def get_source_ip(event):
    rc = event.get("requestContext") or {}
    ident = rc.get("identity") or {}
    ip = ident.get("sourceIp")

    if not ip:
        http = rc.get("http") or {}
        ip = http.get("sourceIp")

    return ip or "unknown-ip"

def stable_session_id(event):
    ip = get_source_ip(event)
    return hashlib.md5(ip.encode("utf-8")).hexdigest()

def extract_user_text(body):
    msgs = body.get("messages")
    if isinstance(msgs, list) and msgs:
        m0 = msgs[0] if isinstance(msgs[0], dict) else {}
        un = m0.get("unstructured") or {}
        if isinstance(un, dict):
            t = un.get("text")
            if isinstance(t, str) and t.strip():
                return t.strip()

        c = m0.get("content")
        if isinstance(c, str) and c.strip():
            return c.strip()

    for k in ["message", "text", "input", "inputText", "utterance"]:
        v = body.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()

    return ""

def lambda_handler(event, context):

    if event.get("httpMethod") == "OPTIONS":
        return {"statusCode": 200, "headers": cors_headers(), "body": ""}

    try:
        body_raw = event.get("body") or "{}"
        body = json.loads(body_raw)

        user_text = extract_user_text(body)
        if not user_text:
            raise ValueError("User text not found")

        session_id = stable_session_id(event)

        resp = lex.recognize_text(
            botId=BOT_ID,
            botAliasId=BOT_ALIAS_ID,
            localeId=LOCALE_ID,
            sessionId=session_id,
            text=user_text
        )

        reply_text = "Sorry, I couldn't understand that."
        if resp.get("messages"):
            reply_text = " ".join(
                [m.get("content", "") for m in resp["messages"] if m.get("content")]
            ).strip() or reply_text

        response_obj = {
            "messages": [
                {
                    "type": "unstructured",
                    "unstructured": {"text": reply_text}
                }
            ]
        }

        return {
            "statusCode": 200,
            "headers": cors_headers(),
            "body": json.dumps(response_obj)
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": cors_headers(),
            "body": json.dumps({"error": str(e)})
        }
```

---

## Purpose

This function:

* Acts as a backend bridge between frontend UI and Amazon Lex
* Supports API Gateway proxy integration
* Maintains stable sessions using hashed client IP
* Handles CORS for browser-based clients
* Returns responses in the format expected by `chat.js`

---

## Environment Variables

Configure the following variables in Lambda:

| Variable       | Description               |
| -------------- | ------------------------- |
| `BOT_ID`       | Amazon Lex V2 Bot ID      |
| `BOT_ALIAS_ID` | Lex Bot Alias ID          |
| `LOCALE_ID`    | Locale (default: `en_US`) |

---

## Input Format (From Frontend)

Expected request body:

```json
{
  "messages": [
    {
      "type": "unstructured",
      "unstructured": {
        "text": "Hello"
      }
    }
  ]
}
```

---

## Response Format (To Frontend)

```json
{
  "messages": [
    {
      "type": "unstructured",
      "unstructured": {
        "text": "Hello! How can I help you?"
      }
    }
  ]
}
```

### Key Notes:

* Designed for **API Gateway proxy integration**
* Returns `statusCode`, `headers`, and `body`
* Includes CORS headers
* Maintains conversation state using sessionId

---

## Session Handling

The function:

1. Extracts client IP from:

   * `requestContext.identity.sourceIp` (REST API)
   * `requestContext.http.sourceIp` (HTTP API)

2. Hashes the IP using MD5

3. Uses the hash as `sessionId` in Lex

This allows:

* Stable conversation across multiple turns
* No changes required in frontend code
* Lex-safe session IDs

---

## Deployment Instructions

1. Create an Amazon Lex V2 bot and publish an alias.
2. Create a Lambda function (Python 3.x runtime).
3. Add required environment variables.
4. Attach IAM permission for:

   * `lex:RecognizeText`
5. Connect Lambda to API Gateway (Proxy Integration).
6. Update frontend endpoint to API Gateway URL.

---

## Required IAM Permission

Attach to Lambda execution role:

```json
{
  "Effect": "Allow",
  "Action": "lex:RecognizeText",
  "Resource": "*"
}
```

---

## Future Improvements

You can extend this function to:

* Use JWT-based session IDs instead of IP hashing
* Add structured logging
* Handle different intent-specific responses
* Integrate with:

  * DynamoDB
  * OpenSearch
  * SQS
  * SES
* Implement authentication and rate limiting

---

## Example Use Case

This function is ideal for:

* Full-stack chatbot projects
* Cloud Computing coursework
* Serverless architecture demonstrations
* Production-ready API Gateway + Lex integrations

---

## Author

Vandana Rawat
Net ID: vr2645

NYU Tandon School of Engineering

---