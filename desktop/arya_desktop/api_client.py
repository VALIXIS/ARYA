"""
api_client.py
-------------
Small HTTP client for talking to the ARYA FastAPI backend.
"""

import requests

from arya_desktop.config import BACKEND_BASE_URL


class ApiClient:
    """Simple wrapper around the ARYA backend API."""

    def __init__(self, base_url: str = BACKEND_BASE_URL):
        self.base_url = base_url.rstrip("/")

    def get(self, path: str):
        """Send a GET request and return decoded JSON."""
        response = requests.get(f"{self.base_url}{path}", timeout=20)
        response.raise_for_status()
        return response.json()

    def post(self, path: str, payload: dict):
        """Send a POST request and return decoded JSON."""
        response = requests.post(f"{self.base_url}{path}", json=payload, timeout=60)
        response.raise_for_status()
        return response.json()

    def send_chat_message(self, message: str) -> str:
        """Send a chat message to the backend."""
        from arya_desktop import settings_store
        settings = settings_store.load_settings()
        response_length = settings.get("response_length", "Brief")
        data = self.post("/chat", {"message": message, "response_length": response_length})
        return data.get("reply", "")

    def get_tasks(self):
        """Load tasks from the backend."""
        return self.get("/tasks")

    def get_goals(self):
        """Load goals from the backend."""
        return self.get("/goals")

    def get_memories(self):
        """Load memories from the backend."""
        return self.get("/memories")

    def get_profile(self):
        """Load the user profile from the backend."""
        return self.get("/profile")

    def get_news(self):
        """Load AI and technology news from the backend."""
        return self.get("/news")
