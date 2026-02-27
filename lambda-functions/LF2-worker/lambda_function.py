import json
import os
import random
import base64
from datetime import datetime

import boto3
import urllib3
from botocore.exceptions import ClientError

# ---------- Environment ----------
TABLE_NAME = os.getenv("TABLE_NAME", "yelp-restaurants")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")

PROCESSED_TABLE = os.getenv("PROCESSED_TABLE", "lf2-processed")
STATE_TABLE = os.getenv("STATE_TABLE", "user-state")

OPENSEARCH_ENDPOINT = os.getenv("OPENSEARCH_ENDPOINT")
OPENSEARCH_INDEX = os.getenv("OPENSEARCH_INDEX", "restaurants")
OS_MASTER_USER = os.getenv("OS_MASTER_USER")
OS_MASTER_PASS = os.getenv("OS_MASTER_PASS")

# ---------- AWS Clients ----------
dynamodb = boto3.resource("dynamodb")
ddb_client = boto3.client("dynamodb")
ses = boto3.client("ses")

table = dynamodb.Table(TABLE_NAME)
processed_table = dynamodb.Table(PROCESSED_TABLE) if PROCESSED_TABLE else None
state_table = dynamodb.Table(STATE_TABLE) if STATE_TABLE else None

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
    if not sample:
        return "Sorry — we couldn’t find matching restaurants right now."
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
    except ClientError as e:
        print(f"Dedupe get_item error: {e}")
        return False

def mark_processed(message_id: str):
    if not processed_table:
        return
    try:
        processed_table.put_item(
            Item={"messageId": message_id, "processedAt": datetime.utcnow().isoformat()}
        )
    except ClientError as e:
        print(f"Dedupe put_item error: {e}")

def save_user_state(email: str, cuisine: str, location: str):
    if not state_table or not email:
        return
    try:
        state_table.put_item(
            Item={
                "userId": email,
                "lastCuisine": cuisine,
                "lastLocation": location,
                "updatedAt": datetime.utcnow().isoformat(),
            }
        )
    except ClientError as e:
        print(f"State put_item error: {e}")

def load_user_state(email: str):
    if not state_table or not email:
        return None
    try:
        resp = state_table.get_item(Key={"userId": email})
        return resp.get("Item")
    except ClientError as e:
        print(f"State get_item error: {e}")
        return None

# ---------- SES ----------
def send_email(to_email: str, subject: str, body_text: str):
    if not SENDER_EMAIL:
        raise RuntimeError("Missing SENDER_EMAIL env var")
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
    if not OPENSEARCH_ENDPOINT:
        return []

    url = f"{OPENSEARCH_ENDPOINT.rstrip('/')}/{OPENSEARCH_INDEX}/_search"

    query = {
        "size": pool_size,
        "_source": ["RestaurantID"],
        "query": {"term": {"Cuisine": cuisine_value}}
    }

    headers = {"Content-Type": "application/json"}
    if OS_MASTER_USER and OS_MASTER_PASS:
        headers["Authorization"] = _basic_auth_header(OS_MASTER_USER, OS_MASTER_PASS)

    resp = http.request("GET", url, body=json.dumps(query).encode(), headers=headers)

    if resp.status >= 300:
        print(f"OpenSearch error {resp.status}: {resp.data[:200]}")
        return []

    try:
        data = json.loads(resp.data.decode())
    except Exception as e:
        print(f"OpenSearch JSON parse error: {e}")
        return []

    hits = data.get("hits", {}).get("hits", [])
    ids = []
    for h in hits:
        src = h.get("_source") or {}
        rid = src.get("RestaurantID")
        if rid:
            ids.append(rid)

    return list(set(ids))

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
        try:
            result.append({
                "name": it["name"]["S"],
                "address": it["address"]["S"],
                "rating": float(it["rating"]["N"]),
                "reviews": int(it["reviews"]["N"])
            })
        except KeyError as e:
            print(f"DynamoDB item missing expected field {e}. Keys: {list(it.keys())}")

    return result

# ---------- Lambda Handler ----------
def lambda_handler(event, context):

    for record in event.get("Records", []):

        message_id = record.get("messageId", "unknown")

        if already_processed(message_id):
            print(f"Skipping already processed messageId={message_id}")
            continue

        body = parse_record_body(record)

        email = first_present(body, ["email", "Email"])
        if not email:
            print(f"Missing email; cannot send recommendation. body keys={list(body.keys())}")
            continue


        use_last = bool(body.get("useLastSearch", body.get("use_last_search", False)))

        raw_cuisine = first_present(body, ["cuisine", "Cuisine"], "Indian")
        location = first_present(body, ["location", "Location"], "Manhattan")

        date = first_present(body, ["date", "Date"], "Today")
        time_slot = first_present(body, ["time", "Time"], "7 PM")
        people = first_present(body, ["party_size", "partySize", "PartySize"], "2")

        # ---------- Load previous state ----------
        if use_last:
            st = load_user_state(email)
            if st:
                raw_cuisine = st.get("lastCuisine", raw_cuisine)
                location = st.get("lastLocation", location)
            else:
                print("useLastSearch=true but no state found; using defaults/message values.")

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

        cuisine_title = str(raw_cuisine).title()
        subject = f"{cuisine_title} Restaurant Recommendations"

        # ---------- Email Formatting ----------
        if use_last:
            body_text = (
                "Hello,\n\n"
                "Thanks for using the Dining Concierge service.\n\n"
                "Based on your most recent search, here are my recommendations:\n\n"
                f"Cuisine: {cuisine_title}\n"
                f"Location: {location}\n\n"
                f"Here are my recommendations for {cuisine_title} cuisine:\n"
                "--------------------------------------------------\n"
                f"{restaurant_text}\n"
                "--------------------------------------------------\n\n"
                "Enjoy your meal!\n\n"
                "Best regards,\n"
                "Dining Concierge Team\n"
            )
        else:
            body_text = (
                "Hello,\n\n"
                "Thanks for using the Dining Concierge service.\n\n"
                "Here are the details of your request:\n"
                f"Location: {location}\n"
                f"Date: {date}\n"
                f"Time: {time_slot}\n"
                f"Party Size: {people}\n"
                f"Cuisine: {cuisine_title}\n\n"
                f"Here are my recommendations for {cuisine_title} cuisine:\n"
                "--------------------------------------------------\n"
                f"{restaurant_text}\n"
                "--------------------------------------------------\n\n"
                "Enjoy your meal!\n\n"
                "Best regards,\n"
                "Dining Concierge Team\n"
            )

        # ---------- Send Email ----------
        try:
            send_email(email, subject, body_text)
        except ClientError as e:
            print(f"SES send_email failed: {e}")
            continue
        save_user_state(email, cuisine_title, location)

        mark_processed(message_id)

    return {"statusCode": 200, "body": json.dumps("LF2 processed")}
