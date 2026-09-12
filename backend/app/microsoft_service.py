"""
Microsoft Graph API Service for ARYA.
Provides integration with Outlook Mail, Outlook Calendar, and Microsoft To-Do.
"""

import os
import json
import httpx
from typing import Dict, Any, List, Optional

TOKENS_PATH = os.path.join(os.path.dirname(__file__), "..", "microsoft_tokens.json")


def is_microsoft_connected() -> bool:
    """Check if Microsoft Graph OAuth tokens exist."""
    return os.path.exists(TOKENS_PATH) or "MICROSOFT_ACCESS_TOKEN" in os.environ


def _get_access_token() -> Optional[str]:
    """Retrieve active MS Graph access token."""
    if "MICROSOFT_ACCESS_TOKEN" in os.environ:
        return os.environ["MICROSOFT_ACCESS_TOKEN"]

    if os.path.exists(TOKENS_PATH):
        try:
            with open(TOKENS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("access_token")
        except Exception as exc:
            print(f"[MICROSOFT] Error reading tokens: {exc}")
    return None


def get_outlook_emails(max_results: int = 5) -> Dict[str, Any]:
    """Fetch unread emails from Outlook."""
    token = _get_access_token()
    if not token:
        return {
            "success": False,
            "connected": False,
            "message": "Microsoft Account not linked yet. Configure MICROSOFT_ACCESS_TOKEN in backend/.env.",
            "emails": []
        }

    headers = {"Authorization": f"Bearer {token}"}
    url = "https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages"
    params = {"$filter": "isRead eq false", "$top": max_results}

    try:
        resp = httpx.get(url, headers=headers, params=params, timeout=6.0)
        data = resp.json()
        items = data.get("value", [])

        email_list = []
        for item in items:
            email_list.append({
                "subject": item.get("subject", "No Subject"),
                "sender": item.get("from", {}).get("emailAddress", {}).get("name", "Unknown"),
                "snippet": item.get("bodyPreview", "")
            })

        return {"success": True, "connected": True, "count": len(email_list), "emails": email_list}
    except Exception as exc:
        return {"success": False, "connected": True, "error": str(exc), "emails": []}


def get_outlook_calendar(days: int = 1) -> Dict[str, Any]:
    """Fetch upcoming Outlook Calendar events."""
    token = _get_access_token()
    if not token:
        return {
            "success": False,
            "connected": False,
            "message": "Microsoft Account not linked yet.",
            "events": []
        }

    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    start_dt = now.isoformat()
    end_dt = (now + timedelta(days=days)).isoformat()

    headers = {"Authorization": f"Bearer {token}"}
    url = "https://graph.microsoft.com/v1.0/me/calendarView"
    params = {"startDateTime": start_dt, "endDateTime": end_dt}

    try:
        resp = httpx.get(url, headers=headers, params=params, timeout=6.0)
        data = resp.json()
        items = data.get("value", [])

        events = []
        for item in items:
            events.append({
                "summary": item.get("subject", "Untitled Event"),
                "start": item.get("start", {}).get("dateTime", ""),
                "location": item.get("location", {}).get("displayName", "")
            })

        return {"success": True, "connected": True, "count": len(events), "events": events}
    except Exception as exc:
        return {"success": False, "connected": True, "error": str(exc), "events": []}
