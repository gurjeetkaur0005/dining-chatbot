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
        "Access-Control-Allow-Origin": "*",  # OK for HW demo
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Methods": "OPTIONS,POST,GET",
    }


def get_source_ip(event) -> str:
    """
    REST API: event.requestContext.identity.sourceIp
    HTTP API: event.requestContext.http.sourceIp
    """
    rc = event.get("requestContext") or {}
    ip = None

    # REST API shape
    ident = rc.get("identity") or {}
    ip = ident.get("sourceIp")

    # HTTP API shape fallback
    if not ip:
        http = rc.get("http") or {}
        ip = http.get("sourceIp")

    return ip or "unknown-ip"


def stable_session_id(event) -> str:
    """
    Stable per client (no need to change chat.js).
    Hash keeps it short & Lex-safe.
    """
    ip = get_source_ip(event)
    return hashlib.md5(ip.encode("utf-8")).hexdigest()


def extract_user_text(body: dict) -> str:
    """
    Your chat.js sends:
    {
      "messages": [
        { "type":"unstructured", "unstructured": { "text":"hi" } }
      ]
    }
    """
    msgs = body.get("messages")
    if isinstance(msgs, list) and msgs:
        m0 = msgs[0] if isinstance(msgs[0], dict) else {}
        un = m0.get("unstructured") or {}
        if isinstance(un, dict):
            t = un.get("text")
            if isinstance(t, str) and t.strip():
                return t.strip()

        # fallback if some other format appears
        c = m0.get("content")
        if isinstance(c, str) and c.strip():
            return c.strip()

    # extra fallbacks (just in case)
    for k in ["message", "text", "input", "inputText", "utterance"]:
        v = body.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()

    return ""


def lambda_handler(event, context):
    # Helpful logs (keep for debugging; you can remove later)
    print("EVENT:", json.dumps(event))
    print("BODY_RAW:", event.get("body"))

    # Preflight
    if event.get("httpMethod") == "OPTIONS":
        return {"statusCode": 200, "headers": cors_headers(), "body": ""}

    try:
        body_raw = event.get("body") or "{}"
        body = json.loads(body_raw)

        user_text = extract_user_text(body)
        if not user_text:
            raise ValueError(f"Could not extract user text from body: {body}")

        # Stable session across turns without changing chat.js
        session_id = stable_session_id(event)

        # Call Lex
        resp = lex.recognize_text(
            botId=BOT_ID,
            botAliasId=BOT_ALIAS_ID,
            localeId=LOCALE_ID,
            sessionId=session_id,
            text=user_text
        )
        print("LEX_RESP:", json.dumps(resp))

        # Collect Lex reply text
        reply_text = "Sorry, I couldn't understand that."
        if resp.get("messages"):
            reply_text = " ".join(
                [m.get("content", "") for m in resp["messages"] if m.get("content")]
            ).strip() or reply_text

        # Respond in UI-expected format (your chat.js reads response.data.messages[])
        response_obj = {
            "messages": [
                {"type": "unstructured", "unstructured": {"text": reply_text}}
            ]
        }

        return {
            "statusCode": 200,
            "headers": cors_headers(),
            "body": json.dumps(response_obj)
        }

    except Exception as e:
        print("ERROR:", str(e))
        return {
            "statusCode": 500,
            "headers": cors_headers(),
            "body": json.dumps({"error": str(e)})
        }