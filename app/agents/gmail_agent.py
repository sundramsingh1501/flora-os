"""
Flora OS — Gmail Agent
Reads emails from the last 24h, categorizes, summarizes,
extracts action items, and generates reply drafts.
NEVER sends emails automatically.
"""

import base64
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from app.services.ai_service import generate_json, generate
from app.utils.logger import get_logger

logger = get_logger("agents.gmail")

_CATEGORIES = ["interview", "assessment", "rejection", "offer", "general"]

# Only fetch job-pipeline emails
_JOB_EMAIL_QUERY = (
    "interview OR assessment OR "
    "\"take-home\" OR \"coding test\" OR \"technical test\" OR \"online test\" OR "
    "\"aptitude test\" OR HackerRank OR CodeSignal OR "
    "rejection OR unfortunately OR \"not moving forward\" OR \"not selected\" OR "
    "\"application status\" OR shortlisted OR \"next steps\" OR \"job offer\" OR "
    "\"offer letter\" OR \"pleased to inform\" OR \"selected for\""
)


def _build_gmail_service(access_token: str, refresh_token: str, token_expiry: Optional[datetime] = None):
    """Build an authenticated Gmail API client."""
    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
    )
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def _decode_body(payload: dict) -> str:
    """Extract plain text body from a Gmail message payload."""
    body = ""
    if payload.get("body", {}).get("data"):
        body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")
    elif payload.get("parts"):
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
                break
    # Strip excessive whitespace
    body = re.sub(r"\s{3,}", "\n\n", body).strip()
    return body[:3000]  # limit to 3000 chars for AI processing


def _get_header(headers: list[dict], name: str) -> str:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def fetch_and_process_emails(
    access_token: str,
    refresh_token: str,
    user_id: int,
    hours_back: int = 24,
) -> list[dict]:
    """
    Fetch emails from the last `hours_back` hours and process them with AI.
    Returns a list of processed email dicts.
    """
    try:
        service = _build_gmail_service(access_token, refresh_token)
        after_ts = int((datetime.now(timezone.utc) - timedelta(hours=hours_back)).timestamp())

        results = service.users().messages().list(
            userId="me",
            q=f"after:{after_ts} ({_JOB_EMAIL_QUERY})",
            maxResults=50,
        ).execute()

        message_ids = [m["id"] for m in results.get("messages", [])]
        logger.info("GmailAgent: found %s emails for user_id=%s", len(message_ids), user_id)

        processed = []
        for msg_id in message_ids:
            try:
                msg = service.users().messages().get(
                    userId="me", id=msg_id, format="full"
                ).execute()
                processed_email = _process_email(msg, user_id)
                if processed_email:
                    processed.append(processed_email)
            except Exception as exc:
                logger.warning("Failed to process email %s: %s", msg_id, exc)

        return processed

    except Exception as exc:
        logger.error("GmailAgent fetch failed for user_id=%s: %s", user_id, exc)
        return []


def _process_email(msg: dict, user_id: int) -> Optional[dict]:
    """Run AI analysis on a single Gmail message."""
    headers = msg.get("payload", {}).get("headers", [])
    subject = _get_header(headers, "Subject") or "(No Subject)"
    sender_raw = _get_header(headers, "From") or ""
    date_str = _get_header(headers, "Date") or ""
    msg_id = msg.get("id", "")

    # Parse sender
    sender_match = re.match(r"^(.*?)\s*<(.+)>$", sender_raw.strip())
    if sender_match:
        sender_name = sender_match.group(1).strip().strip('"')
        sender_email = sender_match.group(2).strip()
    else:
        sender_name = ""
        sender_email = sender_raw.strip()

    body = _decode_body(msg.get("payload", {}))

    if not body and not subject:
        return None

    # AI analysis
    analysis = generate_json(
        f"""Analyze this job-related email and return a JSON object.

Subject: {subject}
From: {sender_raw}
Body (first 1500 chars):
{body[:1500]}

Return JSON with these exact keys:
{{
  "summary": "<2-3 sentence summary: what company, what role, what they want>",
  "category": "<one of: interview, assessment, rejection, offer, general>",
  "importance": "<one of: urgent, normal, low>",
  "action_items": ["<specific action required, e.g. Complete HackerRank test by June 30>"],
  "needs_reply": <true or false>,
  "reply_draft": "<if needs_reply is true, write a concise professional reply draft, else empty string>"
}}"""
    )

    if not analysis:
        return None

    # Received timestamp
    received_at = None
    try:
        internal_date = msg.get("internalDate")
        if internal_date:
            received_at = datetime.fromtimestamp(int(internal_date) / 1000, tz=timezone.utc)
    except Exception:
        pass

    return {
        "user_id": user_id,
        "gmail_message_id": msg_id,
        "subject": subject,
        "sender_name": sender_name,
        "sender_email": sender_email,
        "summary": analysis.get("summary", ""),
        "action_items": analysis.get("action_items", []),
        "reply_draft": analysis.get("reply_draft", ""),
        "category": analysis.get("category", "general"),
        "importance": analysis.get("importance", "normal"),
        "received_at": received_at,
    }


def run(user_id: int, gmail_connection: Optional[dict]) -> dict:
    """
    Main Gmail agent entrypoint.
    Returns dict with processed emails and a summary.
    """
    if not gmail_connection or not gmail_connection.get("is_active"):
        return {"emails": [], "summary": "Gmail not connected.", "connected": False}

    access_token = gmail_connection.get("access_token")
    refresh_token = gmail_connection.get("refresh_token")

    if not access_token or not refresh_token:
        return {"emails": [], "summary": "Gmail credentials missing.", "connected": False}

    emails = fetch_and_process_emails(access_token, refresh_token, user_id)

    urgent = [e for e in emails if e.get("importance") == "urgent"]
    needs_action = [e for e in emails if e.get("action_items")]

    if emails:
        summary = generate(
            f"You received {len(emails)} emails in the last 24 hours. "
            f"{len(urgent)} are urgent. {len(needs_action)} need action. "
            f"Write a 2-sentence executive summary of the email activity."
        )
    else:
        summary = "No new emails in the last 24 hours."

    return {
        "emails": emails,
        "summary": summary,
        "connected": True,
        "total": len(emails),
        "urgent_count": len(urgent),
        "action_count": len(needs_action),
    }
