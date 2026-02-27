import json
import os
import random
import base64
from datetime import datetime

import boto3
import urllib3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr

# ---------- Environment ----------
TABLE_NAME = os.getenv("TABLE_NAME", "yelp-restaurants")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")

PROCESSED_TABLE = os.getenv("PROCESSED_TABLE", "lf2-processed")
STATE_TABLE = os.getenv("STATE_TABLE", "user-state")

MAX_SCAN_ITEMS = int(os.getenv("MAX_SCAN_ITEMS", "300"))

OPENSEARCH_ENDPOINT = os.getenv("OPENSEARCH_ENDPOINT")
OPENSEARCH_INDEX = os.getenv("OPENSEARCH_INDEX", "restaurants")
OS_MASTER_USER = os.getenv("OS_MASTER_USER")
OS_MASTER_PASS = os.getenv("OS_MASTER_PASS")

# ---------- AWS Clients ----------
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)
processed_table = dynamodb.Table(PROCESSED_TABLE) if PROCESSED_TABLE else None
state_table = dynamodb.Table(STATE_TABLE) if STATE_TABLE else None

ddb_client = boto3.client("dynamodb")
ses = boto3.client("ses")

http = urllib3.PoolManager(cert_reqs="CERT_REQUIRED")

# ---------- Helpers ----------
def first_present(d: dict, keys, default=None):
    for k in keys:
        v = d.get(k)
        if v is not None and str(v).strip() != "":
            return v
    return default

def parse_record_body(record):
    raw = record.get("body", "")
    try:
        obj = json.loads(raw) if isinstance(raw, str) else raw
    except json.JSONDecodeError:
        obj = {}
    return obj if isinstance(obj, dict) else {}

def normalize_cuisine_variants(raw):
    raw = (raw or "").strip()
    return list({raw, raw.lower(), raw.upper(), raw.title()})

def format_restaurants(sample):
    lines = []
    for i, r in enumerate(sample, 1):
        lines.append(
            f"{i}. {r.get('name')} — {r.get('address')} "
            f"(Rating: {r.get('rating')}, {r.get('reviews')} reviews)"
        )
    return "\n".join(lines)

# ---------- Dedupe ----------
def already_processed(message_id: str) -> bool:
    if not processed_table:
        return False
    try:
        resp = processed_table.get_item(Key={"messageId": message_id})
        return "Item" in resp
    except ClientError:
        return False

def mark_processed(message_id: str):
    if not processed_table:
        return
    processed_table.put_item(
        Item={
            "messageId": message_id,
            "processedAt": datetime.utcnow().isoformat()
        }
    )

def save_user_state(email: str, cuisine: str, location: str):
    if not state_table:
        return
    state_table.put_item(
        Item={
            "userId": email,
            "lastCuisine": cuisine,
            "lastLocation": location,
            "updatedAt": datetime.utcnow().isoformat()
        }
    )

# ---------- SES ----------
def send_email(to_email: str, subject: str, body_text: str):
    ses.send_email(
        Source=SENDER_EMAIL,
        Destination={"ToAddresses": [to_email]},
        Message={
            "Subject": {"Data": subject},
            "Body": {"Text": {"Data": body_text}}
        }
    )

# ---------- OpenSearch ----------
def _basic_auth_header(user, password):
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"

def os_search_ids_by_cuisine(cuisine_value, pool_size=50):
    url = f"{OPENSEARCH_ENDPOINT}/{OPENSEARCH_INDEX}/_search"

    query = {
        "size": pool_size,
        "_source": ["RestaurantID"],
        "query": {"term": {"Cuisine": cuisine_value}}
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": _basic_auth_header(OS_MASTER_USER, OS_MASTER_PASS)
    }

    resp = http.request(
        "GET", url,
        body=json.dumps(query).encode(),
        headers=headers
    )

    data = json.loads(resp.data.decode())
    hits = data.get("hits", {}).get("hits", [])

    return list({h["_source"]["RestaurantID"] for h in hits})

# ---------- DynamoDB ----------
def ddb_batch_get_by_ids(ids):
    if not ids:
        return []

    keys = [{"business_id": {"S": rid}} for rid in ids]

    resp = ddb_client.batch_get_item(
        RequestItems={TABLE_NAME: {"Keys": keys}}
    )

    items = resp.get("Responses", {}).get(TABLE_NAME, [])

    result = []
    for it in items:
        result.append({
            "name": it["name"]["S"],
            "address": it["address"]["S"],
            "rating": float(it["rating"]["N"]),
            "reviews": int(it["reviews"]["N"])
        })
    return result

# ---------- Lambda Handler ----------
def lambda_handler(event, context):

    records = event.get("Records", [])

    for record in records:
        message_id = record.get("messageId", "unknown")

        if already_processed(message_id):
            continue

        body = parse_record_body(record)

        email = first_present(body, ["email"])
        raw_cuisine = first_present(body, ["cuisine"], "Indian")
        location = first_present(body, ["location"], "Manhattan")

        date = first_present(body, ["date"], "Today")
        time_slot = first_present(body, ["time"], "7 PM")
        people = first_present(body, ["party_size"], "2")

        is_previous = body.get("previous_search", False)

        # ---------- Get Restaurants ----------
        restaurants = []

        for cv in normalize_cuisine_variants(raw_cuisine):
            ids = os_search_ids_by_cuisine(cv.title())
            if ids:
                picked = random.sample(ids, min(3, len(ids)))
                restaurants = ddb_batch_get_by_ids(picked)
                if restaurants:
                    break

        restaurant_text = format_restaurants(restaurants)

        subject = f"{raw_cuisine.title()} Restaurant Recommendations"

        # ---------- Email Formatting ----------
        if is_previous:
            body_text = (
                "Dear Guest,\n\n"
                "Thank you for using the Dining Concierge service.\n\n"
                "Based on your previous search, here are some recommended restaurants.\n\n"
                f"Location: {location}\n\n"
                f"Recommended {raw_cuisine.title()} Restaurants:\n"
                "--------------------------------------------------\n"
                f"{restaurant_text}\n"
                "--------------------------------------------------\n\n"
                "We hope you enjoy your dining experience.\n\n"
                "Best regards,\n"
                "Dining Concierge Team\n"
            )
        else:
            body_text = (
                "Dear Guest,\n\n"
                "Thank you for using the Dining Concierge service.\n\n"
                "Your request details:\n"
                f"Location: {location}\n"
                f"Date: {date}\n"
                f"Time: {time_slot}\n"
                f"Party Size: {people}\n\n"
                f"Recommended {raw_cuisine.title()} Restaurants:\n"
                "--------------------------------------------------\n"
                f"{restaurant_text}\n"
                "--------------------------------------------------\n\n"
                "We hope you enjoy your dining experience.\n\n"
                "Best regards,\n"
                "Dining Concierge Team\n"
            )

        # ---------- Send Email ----------
        send_email(email, subject, body_text)

        save_user_state(email, raw_cuisine.title(), location)

        mark_processed(message_id)

    return {"statusCode": 200, "body": json.dumps("LF2 processed")}
