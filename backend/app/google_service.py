"""
Google Workspace Service for ARYA.
Provides integration with Gmail, Google Calendar, and Google Tasks via Google APIs.
Handles OAuth2 credentials and token refresh.
"""

import os
import json
import httpx
from typing import Dict, Any, List, Optional

CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), "..", "google_credentials.json")
TOKENS_PATH = os.path.join(os.path.dirname(__file__), "..", "google_tokens.json")


def is_google_connected() -> bool:
    """Check if Google OAuth tokens exist."""
    return os.path.exists(TOKENS_PATH) or "GOOGLE_ACCESS_TOKEN" in os.environ


def _get_access_token() -> Optional[str]:
    """Retrieve active access token or refresh if expired."""
    if "GOOGLE_ACCESS_TOKEN" in os.environ:
        return os.environ["GOOGLE_ACCESS_TOKEN"]

    if os.path.exists(TOKENS_PATH):
        try:
            with open(TOKENS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("access_token")
        except Exception as exc:
            print(f"[GOOGLE] Error reading tokens: {exc}")
    return None


def get_unread_emails(max_results: int = 5) -> Dict[str, Any]:
    """Fetch unread messages from Gmail inbox."""
    token = _get_access_token()
    if not token:
        return {
            "success": False,
            "connected": False,
            "message": "Google Account not linked yet. Please complete OAuth setup using google_credentials.json.",
            "emails": []
        }

    headers = {"Authorization": f"Bearer {token}"}
    url = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
    params = {"q": "is:unread", "maxResults": max_results}

    try:
        resp = httpx.get(url, headers=headers, params=params, timeout=6.0)
        data = resp.json()
        messages = data.get("messages", [])

        email_list = []
        for msg in messages:
            msg_id = msg.get("id")
            detail_url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}"
            detail_resp = httpx.get(detail_url, headers=headers, timeout=6.0)
            detail = detail_resp.json()

            headers_list = detail.get("payload", {}).get("headers", [])
            subject = next((h["value"] for h in headers_list if h["name"].lower() == "subject"), "No Subject")
            sender = next((h["value"] for h in headers_list if h["name"].lower() == "from"), "Unknown Sender")
            snippet = detail.get("snippet", "")

            email_list.append({
                "id": msg_id,
                "subject": subject,
                "sender": sender,
                "snippet": snippet
            })

        return {
            "success": True,
            "connected": True,
            "count": len(email_list),
            "emails": email_list
        }
    except Exception as exc:
        return {"success": False, "connected": True, "error": str(exc), "emails": []}


def get_calendar_events(days: int = 1) -> Dict[str, Any]:
    """Fetch upcoming Google Calendar events."""
    token = _get_access_token()
    if not token:
        return {
            "success": False,
            "connected": False,
            "message": "Google Account not linked yet. Please complete OAuth setup.",
            "events": []
        }

    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    time_min = now.isoformat()
    time_max = (now + timedelta(days=days)).isoformat()

    headers = {"Authorization": f"Bearer {token}"}
    url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
    params = {
        "timeMin": time_min,
        "timeMax": time_max,
        "singleEvents": "true",
        "orderBy": "startTime"
    }

    try:
        resp = httpx.get(url, headers=headers, params=params, timeout=6.0)
        data = resp.json()
        items = data.get("items", [])

        events = []
        for item in items:
            start = item.get("start", {}).get("dateTime") or item.get("start", {}).get("date")
            events.append({
                "summary": item.get("summary", "Untitled Event"),
                "start": start,
                "location": item.get("location", ""),
                "description": item.get("description", "")
            })

        return {
            "success": True,
            "connected": True,
            "count": len(events),
            "events": events
        }
    except Exception as exc:
        return {"success": False, "connected": True, "error": str(exc), "events": []}
