# AWS Lambda – Basic Lex Response Handler

## Overview

This AWS Lambda function returns a static response message indicating that the service is still under development.

It is designed to be used with **Amazon Lex (non-proxy integration)** and returns a properly formatted Lex response object.

---

## Function Code

```python
import json

def lambda_handler(event, context):
    # Non-proxy integration: return ONLY the response object
    return {
        "messages": [
            {
                "type": "unstructured",
                "unstructured": {
                    "text": "I’m still under development. Please come back later."
                }
            }
        ]
    }
```

---

## Purpose

This function:

- Acts as a placeholder backend for an Amazon Lex bot
- Returns a static message to users
- Can be used during development before implementing full business logic

---

## Response Format

The function returns a Lex-compatible response object:

```json
{
  "messages": [
    {
      "type": "unstructured",
      "unstructured": {
        "text": "I’m still under development. Please come back later."
      }
    }
  ]
}
```

### Key Notes:
- Designed for **non-proxy Lambda integration**
- Returns **only** the response body (no statusCode or headers)
- Compatible with Lex V2 message format

---

## Deployment Instructions

1. Create a new AWS Lambda function.
2. Use Python 3.x runtime.
3. Paste the function code into the Lambda editor.
4. Configure the Lambda function as a fulfillment or code hook in Amazon Lex.
5. Test using the Lex test console.

---

## Future Improvements

You can extend this function to:

- Parse `event` input from Lex
- Handle different intents
- Integrate with:
  - DynamoDB
  - OpenSearch
  - SQS
  - SES
  - External APIs
- Return dynamic responses

---

## Example Use Case

This function is ideal for:

- Initial bot scaffolding
- Testing Lex-Lambda connectivity
- Placeholder responses during development
- Staging environments

---

## Author

Vandana Rawat
Net ID vr2645

---

## License

This project is for educational and development purposes.