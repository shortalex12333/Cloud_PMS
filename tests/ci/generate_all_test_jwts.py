#!/usr/bin/env python3
"""
Generate JWT tokens for all test users with different roles.
"""
import os
import sys
import jwt
from datetime import datetime, timedelta

JWT_SECRET = os.getenv("TENANT_1_SUPABASE_JWT_SECRET")
SUPABASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"

if not JWT_SECRET:
    print("Error: TENANT_1_SUPABASE_JWT_SECRET not set")
    sys.exit(1)

# Users with different roles
users = [
    {
        "id": "d5873b1f-5f62-4e3e-bc78-e03978aec5ba",
        "email": "hod.tenant@alex-short.com",
        "role": "chief_engineer",
        "label": "HOD"
    },
    {
        "id": "5af9d61d-9b2e-4db4-a54c-a3c95eec70e5",
        "email": "captain.tenant@alex-short.com",
        "role": "captain",
        "label": "CAPTAIN"
    },
    {
        "id": "6d807a66-955c-49c4-b767-8a6189c2f422",
        "email": "crew.tenant@alex-short.com",
        "role": "crew",
        "label": "CREW"
    }
]

now = datetime.utcnow()
exp = now + timedelta(hours=24)

print("=" * 60)
print("GENERATING TEST JWTs FOR ALL ROLES")
print("=" * 60)
print()

export_commands = []

for user in users:
    payload = {
        "aud": "authenticated",
        "exp": int(exp.timestamp()),
        "iat": int(now.timestamp()),
        "iss": SUPABASE_URL + "/auth/v1",
        "sub": user["id"],
        "email": user["email"],
        "phone": "",
        "app_metadata": {
            "provider": "email",
            "providers": ["email"]
        },
        "user_metadata": {},
        "role": "authenticated",
        "aal": "aal1",
        "amr": [{"method": "password", "timestamp": int(now.timestamp())}],
        "session_id": f"test-session-{user['label'].lower()}-{now.strftime('%Y%m%d%H%M%S')}"
    }

    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")

    print(f"{user['label']} ({user['role']})")
    print(f"  Email: {user['email']}")
    print(f"  User ID: {user['id']}")
    print(f"  Token: {token[:50]}...")
    print()

    export_commands.append(f"export {user['label']}_JWT='{token}'")

print("=" * 60)
print("EXPORT COMMANDS")
print("=" * 60)
for cmd in export_commands:
    print(cmd)

print()
print("# All in one line:")
print(" && ".join(export_commands))
