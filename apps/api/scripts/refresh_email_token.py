"""
Email Token Refresh Utility

Simple script to refresh expired Microsoft OAuth tokens.

Usage:
    python refresh_email_token.py <user_id> <yacht_id> [purpose]

Example:
    python refresh_email_token.py a35cad0b-02ff-4287-b6e4-17c96fa6a424 85fe1119-b04c-41ac-80f1-829d23322598 read
"""

import os
import sys
import json
import urllib.request
import urllib.parse
import ssl
from datetime import datetime, timedelta

# Configuration
TENANT_SUPABASE_URL = os.getenv(
    "yTEST_YACHT_001_SUPABASE_URL",
    "https://vzsohavtuotocgrfkfyd.supabase.co"
)
TENANT_SUPABASE_KEY = os.getenv(
    "yTEST_YACHT_001_SUPABASE_SERVICE_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY"
)

# Azure app IDs
AZURE_READ_APP_ID = os.getenv("AZURE_READ_APP_ID", "41f6dc82-8127-4330-97e0-c6b26e6aa967")
AZURE_READ_CLIENT_SECRET = os.getenv("AZURE_READ_CLIENT_SECRET", "")
AZURE_WRITE_APP_ID = os.getenv("AZURE_WRITE_APP_ID", "f0b8944b-8127-4f0f-8ed5-5487462df50c")
AZURE_WRITE_CLIENT_SECRET = os.getenv("AZURE_WRITE_CLIENT_SECRET", "")

TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"


def get_ssl_context():
    """Get SSL context (skip verification for local testing)."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def supabase_request(method: str, endpoint: str, data: dict = None) -> dict:
    """Make a request to Supabase REST API."""
    url = f"{TENANT_SUPABASE_URL}/rest/v1/{endpoint}"

    headers = {
        "apikey": TENANT_SUPABASE_KEY,
        "Authorization": f"Bearer {TENANT_SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

    if method == "GET":
        req = urllib.request.Request(url, headers=headers)
    else:
        body = json.dumps(data).encode() if data else None
        req = urllib.request.Request(url, data=body, headers=headers, method=method)

    with urllib.request.urlopen(req, context=get_ssl_context(), timeout=30) as response:
        return json.loads(response.read().decode())


def get_token(user_id: str, yacht_id: str, purpose: str) -> dict:
    """Get current token from database."""
    endpoint = f"auth_microsoft_tokens?user_id=eq.{user_id}&yacht_id=eq.{yacht_id}&token_purpose=eq.{purpose}&is_revoked=eq.false"
    result = supabase_request("GET", endpoint)
    return result[0] if result else None


def refresh_microsoft_token(refresh_token: str, purpose: str) -> dict:
    """Call Microsoft token endpoint to refresh the access token."""
    if purpose == "read":
        client_id = AZURE_READ_APP_ID
        client_secret = AZURE_READ_CLIENT_SECRET
    else:
        client_id = AZURE_WRITE_APP_ID
        client_secret = AZURE_WRITE_CLIENT_SECRET

    if not client_secret:
        raise ValueError(f"No client secret configured for {purpose} app. Set AZURE_{purpose.upper()}_CLIENT_SECRET")

    data = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }).encode()

    req = urllib.request.Request(TOKEN_URL, data=data)
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    with urllib.request.urlopen(req, context=get_ssl_context(), timeout=30) as response:
        return json.loads(response.read().decode())


def update_token_in_db(token_id: str, new_access_token: str, new_refresh_token: str, expires_in: int):
    """Update token in database."""
    expires_at = (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat()

    data = {
        "microsoft_access_token": new_access_token,
        "microsoft_refresh_token": new_refresh_token,
        "token_expires_at": expires_at,
        "updated_at": datetime.utcnow().isoformat(),
    }

    endpoint = f"auth_microsoft_tokens?id=eq.{token_id}"
    # Use PATCH for update
    url = f"{TENANT_SUPABASE_URL}/rest/v1/{endpoint}"
    headers = {
        "apikey": TENANT_SUPABASE_KEY,
        "Authorization": f"Bearer {TENANT_SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers=headers, method="PATCH")

    with urllib.request.urlopen(req, context=get_ssl_context(), timeout=30) as response:
        return json.loads(response.read().decode())


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    user_id = sys.argv[1]
    yacht_id = sys.argv[2]
    purpose = sys.argv[3] if len(sys.argv) > 3 else "read"

    print(f"Refreshing {purpose} token for user {user_id}...")

    # Get current token
    token = get_token(user_id, yacht_id, purpose)
    if not token:
        print(f"No {purpose} token found for this user/yacht")
        sys.exit(1)

    print(f"Found token ID: {token['id']}")
    print(f"Current expires_at: {token['token_expires_at']}")

    # Check if we have a refresh token
    refresh_token = token.get("microsoft_refresh_token")
    if not refresh_token or refresh_token.startswith("STUB"):
        print("WARNING: No valid refresh token (or STUB token). Cannot refresh.")
        print("User needs to re-authorize via OAuth flow.")
        sys.exit(1)

    # Refresh with Microsoft
    print("Calling Microsoft token endpoint...")
    try:
        new_tokens = refresh_microsoft_token(refresh_token, purpose)
    except Exception as e:
        print(f"Microsoft refresh failed: {e}")
        sys.exit(1)

    print(f"Got new access token (expires in {new_tokens.get('expires_in')} seconds)")

    # Update database
    print("Updating database...")
    update_token_in_db(
        token['id'],
        new_tokens['access_token'],
        new_tokens.get('refresh_token', refresh_token),  # Use old if not returned
        new_tokens['expires_in']
    )

    print("Token refreshed successfully!")
    print(f"New expires_at: {(datetime.utcnow() + timedelta(seconds=new_tokens['expires_in'])).isoformat()}")


if __name__ == "__main__":
    main()
