import json
import os
import boto3
from botocore.exceptions import ClientError
from datetime import datetime

dynamodb = boto3.resource("dynamodb")
sqs = boto3.client("sqs")

STATE_TABLE = os.getenv("STATE_TABLE", "user-state")
QUEUE_URL = os.getenv("QUEUE_URL")

state_table = dynamodb.Table(STATE_TABLE)

def lambda_handler(event, context):
    # Accept either userId or email
    user_id = event.get("userId") or event.get("email")
    if not user_id:
        return {"statusCode": 400, "body": json.dumps("Missing userId/email")}

    if not QUEUE_URL:
        return {"statusCode": 500, "body": json.dumps("Missing QUEUE_URL env var")}

    try:
        # Read last saved state
        resp = state_table.get_item(Key={"userId": user_id})
        item = resp.get("Item")
        if not item:
            return {"statusCode": 404, "body": json.dumps("No saved state found for this user")}

        now = datetime.now()

        payload = {
            "email": user_id,
            "location": item.get("lastLocation", "Manhattan"),
            "cuisine": item.get("lastCuisine", "Indian"),
            "date": now.strftime("%B %d, %Y"),  # e.g., February 27, 2026
            "time": now.strftime("%I:%M %p"),   # e.g., 02:35 PM
            "party_size": "2"
        }

        # Send to Q1 (LF2 will process)
        sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps(payload)
        )

        return {"statusCode": 200, "body": json.dumps({"sentToQueue": True, "payload": payload})}

    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps(str(e))}
