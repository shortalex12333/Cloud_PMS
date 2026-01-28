#!/usr/bin/env python3
"""
Generate fresh JWTs via password-grant against MASTER Supabase.

This eliminates iat/nbf clock skew issues by minting tokens with current timestamps.
Required environment variables:
- MASTER_SUPABASE_URL
- MASTER_SUPABASE_SERVICE_KEY
- STAGING_CREW_EMAIL
- STAGING_HOD_EMAIL
- STAGING_CAPTAIN_EMAIL
- STAGING_USER_PASSWORD
"""
import os
import sys
import requests
from typing import Dict, Optional


def password_grant_jwt(
    supabase_url: str,
    email: str,
    password: str
) -> Optional[str]:
    """
    Authenticate via password grant and return JWT.

    Returns None if authentication fails.
    """
    url = f"{supabase_url}/auth/v1/token?grant_type=password"

    payload = {
        "email": email,
        "password": password
    }

    headers = {
        "Content-Type": "application/json",
        "apikey": os.getenv("MASTER_SUPABASE_SERVICE_KEY", "")
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            return data.get("access_token")
        else:
            print(f"❌ Auth failed for {email}: {response.status_code}", file=sys.stderr)
            print(f"   Response: {response.text}", file=sys.stderr)
            return None

    except Exception as e:
        print(f"❌ Error authenticating {email}: {e}", file=sys.stderr)
        return None


def main():
    # Required environment variables
    required_vars = [
        "MASTER_SUPABASE_URL",
        "MASTER_SUPABASE_SERVICE_KEY",
        "STAGING_CREW_EMAIL",
        "STAGING_HOD_EMAIL",
        "STAGING_CAPTAIN_EMAIL",
        "STAGING_USER_PASSWORD"
    ]

    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        print(f"❌ Missing required environment variables: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    supabase_url = os.getenv("MASTER_SUPABASE_URL")
    password = os.getenv("STAGING_USER_PASSWORD")

    users = [
        {
            "email": os.getenv("STAGING_CREW_EMAIL"),
            "label": "CREW_JWT",
            "role": "crew"
        },
        {
            "email": os.getenv("STAGING_HOD_EMAIL"),
            "label": "HOD_JWT",
            "role": "chief_engineer"
        },
        {
            "email": os.getenv("STAGING_CAPTAIN_EMAIL"),
            "label": "CAPTAIN_JWT",
            "role": "captain"
        }
    ]

    print("=" * 80, file=sys.stderr)
    print("GENERATING FRESH JWTs VIA PASSWORD GRANT (MASTER)", file=sys.stderr)
    print("=" * 80, file=sys.stderr)
    print(file=sys.stderr)

    jwts: Dict[str, str] = {}
    failed = []

    for user in users:
        email = user["email"]
        label = user["label"]
        role = user["role"]

        print(f"🔐 Authenticating {role}: {email}", file=sys.stderr)

        jwt_token = password_grant_jwt(supabase_url, email, password)

        if jwt_token:
            jwts[label] = jwt_token
            print(f"   ✅ Got JWT ({len(jwt_token)} chars)", file=sys.stderr)
        else:
            failed.append(email)
            print(f"   ❌ Authentication failed", file=sys.stderr)

        print(file=sys.stderr)

    if failed:
        print(f"❌ Failed to authenticate: {', '.join(failed)}", file=sys.stderr)
        sys.exit(1)

    print("=" * 80, file=sys.stderr)
    print("✅ ALL JWTS GENERATED SUCCESSFULLY", file=sys.stderr)
    print("=" * 80, file=sys.stderr)
    print(file=sys.stderr)

    # Export as GitHub Actions environment variables
    # Write to GITHUB_ENV if in CI, otherwise print export commands
    github_env = os.getenv("GITHUB_ENV")

    if github_env:
        print(f"📝 Writing to GITHUB_ENV: {github_env}", file=sys.stderr)
        with open(github_env, "a") as f:
            for label, token in jwts.items():
                f.write(f"{label}={token}\n")
                print(f"   {label}=<JWT>", file=sys.stderr)
    else:
        print("💡 Export commands (run in shell):", file=sys.stderr)
        print(file=sys.stderr)
        for label, token in jwts.items():
            print(f"export {label}='{token}'")

    print(file=sys.stderr)
    print("✅ JWTs ready for tests", file=sys.stderr)


if __name__ == "__main__":
    main()
