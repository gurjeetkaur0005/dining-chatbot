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

PROCESSED_TABLE = os.getenv("PROCESSED_TABLE", "lf2-processed")  # dedupe table
MAX_SCAN_ITEMS = int(os.getenv("MAX_SCAN_ITEMS", "300"))  # fallback only

STATE_TABLE = os.getenv("STATE_TABLE", "user-state")  # stores lastCuisine + lastLocation for userId=email

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

# urllib3 client for OpenSearch calls
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

    if isinstance(obj, dict) and "body" in obj:
        inner = obj.get("body")
        if isinstance(inner, str):
            try:
                inner_obj = json.loads(inner)
                if isinstance(inner_obj, dict):
                    return inner_obj
            except json.JSONDecodeError:
                pass
    return obj if isinstance(obj, dict) else {}

def normalize_cuisine_variants(raw):
    raw = (raw or "").strip()
    if not raw:
        raw = "Indian"
    return list({
        raw,
        raw.lower(),
        raw.upper(),
        raw.title(),
        " ".join(w.capitalize() for w in raw.split())
    })

def format_restaurants(sample):
    lines = []
    for i, r in enumerate(sample, 1):
        name = r.get("name", "Unknown")
        address = r.get("address", "Unknown address")
        rating = r.get("rating", 0)
        reviews = r.get("reviews", r.get("review_count", 0))
        lines.append(f"{i}. {name} — {address} (Rating: {rating}, {reviews} reviews)")
    return "\n".join(lines)

# ---------- Dedupe ----------
def already_processed(message_id: str) -> bool:
    if not processed_table:
        return False
    try:
        resp = processed_table.get_item(Key={"messageId": message_id})
        return "Item" in resp
    except ClientError as e:
        print("Dedupe get_item failed:", e)
        return False

def mark_processed(message_id: str):
    if not processed_table:
        return
    try:
        processed_table.put_item(
            Item={"messageId": message_id, "processedAt": datetime.utcnow().isoformat()},
            ConditionExpression="attribute_not_exists(messageId)"
        )
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") != "ConditionalCheckFailedException":
            print("Dedupe put_item failed:", e)

# ---------- State Memory  ----------
def save_user_state(email: str, cuisine: str, location: str):
    """
    Saves last search (cuisine + location) for returning user.
    userId = email
    """
    if not state_table:
        return
    try:
        state_table.put_item(
            Item={
                "userId": email,
                "lastCuisine": cuisine,
                "lastLocation": location,
                "updatedAt": datetime.utcnow().isoformat()
            }
        )
        print(f"State saved for {email}: {cuisine}, {location}")
    except ClientError as e:
        print("State put_item failed:", e)

# ---------- SES ----------
def send_email(to_email: str, subject: str, body_text: str):
    if not SENDER_EMAIL:
        raise RuntimeError("Missing SENDER_EMAIL env var (must be verified in SES).")

    ses.send_email(
        Source=SENDER_EMAIL,
        Destination={"ToAddresses": [to_email]},
        Message={
            "Subject": {"Data": subject, "Charset": "UTF-8"},
            "Body": {"Text": {"Data": body_text, "Charset": "UTF-8"}}
        }
    )

# ---------- OpenSearch ----------
def _basic_auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("utf-8")
    return f"Basic {token}"

def os_search_ids_by_cuisine(cuisine_value: str, pool_size: int = 50):
    """
    Returns a list of RestaurantIDs from OpenSearch for the given cuisine.
    Requires FGAC master user basic auth.
    """
    if not OPENSEARCH_ENDPOINT:
        raise RuntimeError("Missing OPENSEARCH_ENDPOINT env var.")
    if not (OS_MASTER_USER and OS_MASTER_PASS):
        raise RuntimeError("Missing OS_MASTER_USER / OS_MASTER_PASS env vars.")

    url = f"{OPENSEARCH_ENDPOINT}/{OPENSEARCH_INDEX}/_search"
    # ✅ Cuisine is mapped as keyword already
    query = {
        "size": pool_size,
        "_source": ["RestaurantID", "Cuisine"],
        "query": {"term": {"Cuisine": cuisine_value}}
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": _basic_auth_header(OS_MASTER_USER, OS_MASTER_PASS)
    }

    resp = http.request(
        "GET",
        url,
        body=json.dumps(query).encode("utf-8"),
        headers=headers
    )

    if resp.status >= 400:
        raise RuntimeError(
            f"OpenSearch error {resp.status}: {resp.data[:200].decode('utf-8', 'ignore')}"
        )

    data = json.loads(resp.data.decode("utf-8"))
    hits = data.get("hits", {}).get("hits", [])
    print("OpenSearch hits:", len(hits))
    if hits:
        print("OpenSearch first hit _source:", hits[0].get("_source"))

    ids = []
    for h in hits:
        src = h.get("_source", {})
        rid = src.get("RestaurantID")
        if rid:
            ids.append(rid)

    return list(set(ids))

# ---------- DynamoDB ----------
def ddb_batch_get_by_ids(ids):
    """
    BatchGet by business_id (partition key).
    """
    if not ids:
        return []

    keys = [{"business_id": {"S": rid}} for rid in ids]
    resp = ddb_client.batch_get_item(
        RequestItems={TABLE_NAME: {"Keys": keys}}
    )
    items = resp.get("Responses", {}).get(TABLE_NAME, [])

    out = []
    for it in items:
        out.append({
            "business_id": it.get("business_id", {}).get("S"),
            "name": it.get("name", {}).get("S"),
            "address": it.get("address", {}).get("S"),
            "rating": float(it.get("rating", {}).get("N", "0")),
            "reviews": int(it.get("reviews", {}).get("N", it.get("review_count", {}).get("N", "0"))),
            "zip": it.get("zip", {}).get("S", ""),
            "cuisine": it.get("cuisine", {}).get("S", "")
        })
    return out

# Fallback (only if OpenSearch returns nothing)
def limited_scan_by_cuisine(cuisine_value, limit=300):
    resp = table.scan(
        FilterExpression=Attr("cuisine").eq(cuisine_value),
        Limit=limit
    )
    return resp.get("Items", [])

# ---------- Lambda Handler ----------
def lambda_handler(event, context):
    records = event.get("Records", [])
    print(f"LF2 received {len(records)} record(s)")

    for record in records:
        message_id = record.get("messageId") or record.get("messageID") or "unknown"

        if message_id != "unknown" and already_processed(message_id):
            print(f"Skipping duplicate messageId={message_id}")
            continue

        body = parse_record_body(record)

        email = first_present(body, ["email", "Email", "user_email"])
        if not email:
            print("Missing email; skipping record:", body)
            continue

        raw_cuisine = first_present(body, ["cuisine", "Cuisine", "food", "food_type"], "Indian")
        location = first_present(body, ["location", "Location", "city"], "Manhattan")
        date = first_present(body, ["date", "Date"], "Today")
        time_slot = first_present(body, ["time", "time_slot", "Time"], "7 PM")
        people = str(first_present(body, ["party_size", "PartySize", "people", "guests"], "2"))

        if isinstance(date, str) and date.strip().lower() == "today":
            date = datetime.now().strftime("%B %d, %Y")

        # ---------- MAIN: OpenSearch -> IDs -> DynamoDB ----------
        restaurants = []
        matched_cuisine = None

        for cv in normalize_cuisine_variants(raw_cuisine):
            cuisine_for_os = cv.title()

            try:
                ids_pool = os_search_ids_by_cuisine(cuisine_for_os, pool_size=50)
            except Exception as e:
                print("OpenSearch query failed:", str(e))
                ids_pool = []

            if ids_pool:
                picked_ids = random.sample(ids_pool, min(3, len(ids_pool)))
                print("Picked IDs:", picked_ids)

                restaurants = ddb_batch_get_by_ids(picked_ids)
                restaurants = [
                    r for r in restaurants
                    if (r.get("rating", 0) or 0) > 0 and (r.get("reviews", 0) or 0) > 0
                ]
                if restaurants:
                    matched_cuisine = cv
                    break

        # ---------- FALLBACK: DynamoDB scan ----------
        if not restaurants:
            print("Falling back to DynamoDB scan...")
            for cv in normalize_cuisine_variants(raw_cuisine):
                items = limited_scan_by_cuisine(cv, limit=MAX_SCAN_ITEMS)
                items = [
                    r for r in items
                    if (r.get("rating", 0) or 0) > 0 and (r.get("reviews", r.get("review_count", 0)) or 0) > 0
                ]
                if items:
                    restaurants = random.sample(items, min(3, len(items)))
                    matched_cuisine = cv
                    break

        display_cuisine = (matched_cuisine or raw_cuisine).title()

        if not restaurants:
            restaurant_text = f"Sorry, no suitable {display_cuisine} restaurants were found at this time."
        else:
            restaurant_text = format_restaurants(restaurants)

        subject = f"{display_cuisine} Restaurant Recommendations"
        body_text = (
            "Dear Guest,\n\n"
            "Thank you for using the Dining Concierge service.\n\n"
            "Your request details:\n"
            f"Location: {location}\n"
            f"Date: {date}\n"
            f"Time: {time_slot}\n"
            f"Party Size: {people}\n\n"
            f"Recommended {display_cuisine} Restaurants:\n"
            "--------------------------------------------------\n"
            f"{restaurant_text}\n"
            "--------------------------------------------------\n\n"
            "We hope you enjoy your dining experience.\n\n"
            "Best regards,\n"
            "Dining Concierge Team\n"
        )

        try:
            send_email(email, subject, body_text)
            print(f"Email sent to {email} for messageId={message_id}")

            save_user_state(email=email, cuisine=display_cuisine, location=location)

            if message_id != "unknown":
                mark_processed(message_id)

        except ClientError as e:
            print(f"SES error for messageId={message_id}:", e.response["Error"]["Message"])
            raise

    return {"statusCode": 200, "body": json.dumps("LF2 processed")}
