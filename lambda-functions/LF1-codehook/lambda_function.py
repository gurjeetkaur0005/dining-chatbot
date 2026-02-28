from datetime import datetime
import os
import json
import boto3

# ==============================
# SQS CONFIG
# ==============================

SQS_QUEUE_URL = os.environ.get("SQS_QUEUE_URL", "")
SQS_REGION = os.environ.get("SQS_REGION", "us-east-1")

sqs = boto3.client("sqs", region_name=SQS_REGION)

ALLOWED_LOCATION = "Manhattan"

# ==============================
# CUISINE VALIDATION
# ==============================

# Exact allowed cuisines (normalized to lowercase)
ALLOWED_CUISINES = [
    "italian",
    "chinese",
    "mexican",
    "indian",
    "japanese",
    "thai",
    "korean",
    "french",
    "mediterranean",
    "american"
]

def normalize_text(s: str) -> str:
    """Lowercase + strip + collapse internal whitespace."""
    if s is None:
        return ""
    return " ".join(s.strip().lower().split())

def cuisine_display_list() -> str:
    """Pretty list for user messages."""
    return ", ".join([c.title() for c in ALLOWED_CUISINES])

# ==============================
# HELPERS
# ==============================

def title_case_cuisine(cuisine: str) -> str:
    return cuisine.strip().title()


def send_to_sqs(payload: dict) -> str:
    if not SQS_QUEUE_URL or SQS_QUEUE_URL.startswith("PLACEHOLDER"):
        raise ValueError("SQS_QUEUE_URL is not set to a real queue URL.")

    resp = sqs.send_message(
        QueueUrl=SQS_QUEUE_URL,
        MessageBody=json.dumps(payload)
    )
    return resp["MessageId"]


def get_slot_value(event, slot_name: str):
    slots = event.get("sessionState", {}).get("intent", {}).get("slots", {}) or {}
    slot = slots.get(slot_name)
    if not slot:
        return None
    return (slot.get("value") or {}).get("interpretedValue")


def elicit_slot(event, slot_to_elicit: str, message: str):
    session_state = event["sessionState"]
    intent = session_state["intent"]

    return {
        "sessionState": {
            "dialogAction": {
                "type": "ElicitSlot",
                "slotToElicit": slot_to_elicit
            },
            "intent": intent
        },
        "messages": [
            {
                "contentType": "PlainText",
                "content": message
            }
        ]
    }


def close(event, message: str, fulfillment_state: str = "Fulfilled"):
    session_state = event["sessionState"]
    intent = session_state["intent"]
    intent["state"] = fulfillment_state

    return {
        "sessionState": {
            "dialogAction": {
                "type": "Close"
            },
            "intent": intent
        },
        "messages": [
            {
                "contentType": "PlainText",
                "content": message
            }
        ]
    }


# ==============================
# LAMBDA HANDLER
# ==============================

def lambda_handler(event, context):

    print("LEX EVENT:", json.dumps(event))

    intent_name = event.get("sessionState", {}).get("intent", {}).get("name", "")

    # ==============================
    # EXTRA CREDIT: Use Last Search
    # ==============================
    if intent_name == "UseLastSearchIntent":

        email = get_slot_value(event, "Email")

        if not email:
            return elicit_slot(event, "Email", "What's your email?")

        payload = {
            "email": email,
            "useLastSearch": True
        }

        msg_id = send_to_sqs(payload)
        print("SQS messageId:", msg_id)

        return close(
            event,
            "Got it — using your last search. You'll receive recommendations shortly."
        )

    # ==============================
    # NORMAL BOOKING FLOW
    # ==============================

    location = get_slot_value(event, "Location")
    cuisine = get_slot_value(event, "Cuisine")
    date = get_slot_value(event, "Date")
    time = get_slot_value(event, "Time")
    party_size = get_slot_value(event, "PartySize")
    email = get_slot_value(event, "Email")

    # Enforce Manhattan only
    if location:
        normalized_location = normalize_text(location)
        if normalized_location != normalize_text(ALLOWED_LOCATION):
            return elicit_slot(
                event,
                "Location",
                "Please enter a valid location. Currently, only Manhattan is supported."
            )

    # ✅ Enforce allowed cuisines only
    if cuisine:
        normalized_cuisine = normalize_text(cuisine)
        if normalized_cuisine not in ALLOWED_CUISINES:
            return elicit_slot(
                event,
                "Cuisine",
                f"Please select cuisine only from: {cuisine_display_list()}."
            )

    # Reject past dates (e.g., yesterday)
    if date:
        try:
            requested_date = datetime.strptime(date, "%Y-%m-%d").date()
            today = datetime.utcnow().date()

            if requested_date < today:
                return elicit_slot(
                    event,
                    "Date",
                    "The date cannot be in the past. Please enter a future date."
                )
        except Exception:
            return elicit_slot(
                event,
                "Date",
                "Invalid date format. Please enter a valid date."
            )

    # Guard against early fulfillment
    required_slots = [
        ("Location", location),
        ("Cuisine", cuisine),
        ("Date", date),
        ("Time", time),
        ("PartySize", party_size),
        ("Email", email)
    ]

    missing = [slot_name for slot_name, value in required_slots if not value]

    if missing:
        # Better UX when Cuisine missing
        if missing[0] == "Cuisine":
            return elicit_slot(
                event,
                "Cuisine",
                f"Please select a cuisine from: {cuisine_display_list()}."
            )

        return elicit_slot(
            event,
            missing[0],
            f"Please provide {missing[0]}."
        )

    # ==============================
    # BUILD NORMAL PAYLOAD
    # ==============================

    payload = {
        "email": email,
        "cuisine": title_case_cuisine(cuisine),
        "location": ALLOWED_LOCATION,
        "date": date,
        "time": time,
        "party_size": str(party_size),
        "useLastSearch": False
    }

    msg_id = send_to_sqs(payload)
    print("SQS messageId:", msg_id)

    return close(
        event,
        "Thanks! You're all set. You'll receive restaurant recommendations shortly."
    )