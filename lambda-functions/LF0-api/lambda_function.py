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
