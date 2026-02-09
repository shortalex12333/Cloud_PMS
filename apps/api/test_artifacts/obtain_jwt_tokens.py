#!/usr/bin/env python3
"""
Obtain fresh JWT tokens for crew and HOD test users.
Saves tokens to scratchpad for use in test scripts.
"""
import requests
import json
import os

# Master Supabase URL for authentication
MASTER_SUPABASE_URL = "https://erbgbecyovxybflpkhvt.supabase.co"
MASTER_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVyYmdiZWN5b3Z4eWJmbHBraHZ0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzY3OTE2MTcsImV4cCI6MjA1MjM2NzYxN30.DUIf8wgTVEyuH66BQ6W-4A9SmXHbEj_83hrnD5z4Pgg"

# Test users
TEST_USERS = {
    "crew": {
        "email": "crew.test@alex-short.com",
        "password": "test123456"
    },
    "hod": {
        "email": "hod.test@alex-short.com",
        "password": "test123456"
    }
}

def get_jwt_token(email, password):
    """Get JWT token from Supabase auth."""
    url = f"{MASTER_SUPABASE_URL}/auth/v1/token?grant_type=password"
    headers = {
        "apikey": MASTER_ANON_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "email": email,
        "password": password
    }

    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()

def main():
    tokens = {}

    for role, creds in TEST_USERS.items():
        try:
            print(f"Obtaining JWT for {role}...")
            result = get_jwt_token(creds["email"], creds["password"])
            tokens[role] = result
            print(f"✓ {role}: {result['access_token'][:20]}...")
        except Exception as e:
            print(f"✗ {role}: {e}")
            tokens[role] = {"error": str(e)}

    # Save to scratchpad
    output_path = "/private/tmp/claude/-Volumes-Backup-CELESTE/c98cc619-82ab-402f-91a6-c868af22a09a/scratchpad/test_user_tokens.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(tokens, f, indent=2)

    print(f"\n✓ Tokens saved to: {output_path}")

if __name__ == "__main__":
    main()
