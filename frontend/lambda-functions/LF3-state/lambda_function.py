import json
import os
import boto3
from botocore.exceptions import ClientError

# ---------- AWS Clients ----------
dynamodb = boto3.resource("dynamodb")
sqs = boto3.client("sqs")

# ---------- Environment ----------
STATE_TABLE = os.getenv("STATE_TABLE", "user-state")
QUEUE_URL = os.getenv("QUEUE_URL")

state_table = dynamodb.Table(STATE_TABLE)

# ---------- Lambda Handler ----------
def lambda_handler(event, context):


    user_id = event.get("userId") or event.get("email")

    if not user_id:
        return {"statusCode": 400, "body": json.dumps("Missing userId/email")}

    if not QUEUE_URL:
        return {"statusCode": 500, "body": json.dumps("Missing QUEUE_URL env var")}

    try:

        resp = state_table.get_item(Key={"userId": user_id})
        item = resp.get("Item")

        if not item:
            return {"statusCode": 404, "body": json.dumps("No saved state found for this user")}

        last_cuisine = item.get("lastCuisine", "Indian")
        last_location = item.get("lastLocation", "Manhattan")

        payload = {
            "email": user_id,
            "useLastSearch": True,
            "location": last_location,
            "cuisine": last_cuisine
        }

        # ---------- Send to SQS (Q1) ----------
        sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps(payload),
            MessageAttributes={
                "mode": {"StringValue": "useLastSearch", "DataType": "String"}
            }
        )

        return {
            "statusCode": 200,
            "body": json.dumps({
                "sentToQueue": True,
                "message": "Last-search recommendation request sent to queue"
            })
        }

    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps(str(e))}
