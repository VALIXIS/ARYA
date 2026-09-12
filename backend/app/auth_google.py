"""
Google OAuth Authorization Helper for ARYA.
Run this script once after adding `google_credentials.json` to complete OAuth login.
"""

import os
import json

CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), "..", "google_credentials.json")
TOKENS_PATH = os.path.join(os.path.dirname(__file__), "..", "google_tokens.json")

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/tasks"
]


def run_oauth_flow():
    """Run interactive OAuth2 flow."""
    if not os.path.exists(CREDENTIALS_PATH):
        print(f"❌ Error: Could not find google_credentials.json at:\n   {os.path.abspath(CREDENTIALS_PATH)}")
        print("\nPlease follow the instructions to download google_credentials.json from Google Cloud Console and place it in the backend directory.")
        return

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
        creds = flow.run_local_server(port=0)

        token_data = {
            "access_token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": creds.scopes
        }

        with open(TOKENS_PATH, "w", encoding="utf-8") as f:
            json.dump(token_data, f, indent=2)

        print("✅ Google Account successfully linked to ARYA!")
        print(f"   Tokens saved securely to: {os.path.abspath(TOKENS_PATH)}")

    except ImportError:
        print("Installing google-auth-oauthlib package...")
        os.system("pip install google-auth-oauthlib google-api-python-client")
        print("Please re-run this script!")
    except Exception as exc:
        print(f"❌ OAuth Flow Error: {exc}")


if __name__ == "__main__":
    run_oauth_flow()
