#!/usr/bin/env python3
"""
Generate a test JWT token for staging testing.
Uses the JWT secret to create a valid token.
"""
import os
import sys
import jwt
from datetime import datetime, timedelta

# Configuration
JWT_SECRET = os.getenv("TENANT_1_SUPABASE_JWT_SECRET")
USER_ID = "a35cad0b-02ff-4287-b6e4-17c96fa6a424"
USER_EMAIL = "x@alex-short.com"
ROLE = "authenticated"
SUPABASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"

if not JWT_SECRET:
    print("Error: TENANT_1_SUPABASE_JWT_SECRET not set")
    sys.exit(1)

# Create JWT payload
now = datetime.utcnow()
exp = now + timedelta(hours=24)

payload = {
    "aud": "authenticated",
    "exp": int(exp.timestamp()),
    "iat": int(now.timestamp()),
    "iss": SUPABASE_URL + "/auth/v1",
    "sub": USER_ID,
    "email": USER_EMAIL,
    "phone": "",
    "app_metadata": {
        "provider": "email",
        "providers": ["email"]
    },
    "user_metadata": {},
    "role": ROLE,
    "aal": "aal1",
    "amr": [{"method": "password", "timestamp": int(now.timestamp())}],
    "session_id": "test-session-" + now.strftime("%Y%m%d%H%M%S")
}

# Generate token
token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")

print(f"Generated JWT for user: {USER_EMAIL}")
print(f"User ID: {USER_ID}")
print(f"Role: {ROLE}")
print(f"Expires: {exp.isoformat()}")
print()
print("Token:")
print(token)
print()
print("Export commands:")
print(f"export TEST_JWT='{token}'")
print(f"export CAPTAIN_JWT='{token}'")
