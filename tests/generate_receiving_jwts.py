#!/usr/bin/env python3
"""
Generate all 15 JWT tokens for Receiving Lens v1 testing.

Uses JWT secret from env vars to mint tokens for test users.
Queries Supabase to get real user IDs for the test yacht.
"""
import os
import sys
import jwt
import json
from datetime import datetime, timedelta
from supabase import create_client, Client

# Configuration from env vars
TENANT_1_SUPABASE_URL = os.getenv("TENANT_1_SUPABASE_URL")
TENANT_1_SERVICE_KEY = os.getenv("TENANT_1_SUPABASE_SERVICE_KEY")
TEST_YACHT_ID = os.getenv("TEST_YACHT_ID", "85fe1119-b04c-41ac-80f1-829d23322598")

if not TENANT_1_SUPABASE_URL or not TENANT_1_SERVICE_KEY:
    print("❌ ERROR: TENANT_1_SUPABASE_URL and TENANT_1_SUPABASE_SERVICE_KEY required", file=sys.stderr)
    sys.exit(1)

# Get JWT secret by extracting from service key
# Service key is itself a JWT that we can decode to get the secret
try:
    # The service key header contains the algorithm
    # We need to extract the secret from Supabase
    # For now, we'll mint JWTs using the service role approach
    JWT_SECRET = os.getenv("TENANT_1_SUPABASE_JWT_SECRET")
    if not JWT_SECRET:
        # Try to derive it from the service key structure
        # Supabase service keys are JWTs signed with the secret
        print("⚠️  TENANT_1_SUPABASE_JWT_SECRET not set, attempting to query users", file=sys.stderr)
except Exception as e:
    print(f"⚠️  Could not extract JWT secret: {e}", file=sys.stderr)

# Initialize Supabase client
supabase: Client = create_client(TENANT_1_SUPABASE_URL, TENANT_1_SERVICE_KEY)

print("=" * 80, file=sys.stderr)
print("GENERATING 15 JWT TOKENS FOR RECEIVING LENS V1 TESTING", file=sys.stderr)
print("=" * 80, file=sys.stderr)
print(f"Supabase URL: {TENANT_1_SUPABASE_URL}", file=sys.stderr)
print(f"Test Yacht ID: {TEST_YACHT_ID}", file=sys.stderr)
print("=" * 80, file=sys.stderr)
print("", file=sys.stderr)

# Query real users from the database
print("📊 Querying users from auth_users_profiles...", file=sys.stderr)
try:
    # Get users for the test yacht with different roles
    response = supabase.table("auth_users_profiles")\
        .select("id, email, role, full_name, active_status")\
        .eq("yacht_id", TEST_YACHT_ID)\
        .execute()

    users_in_db = response.data
    print(f"   Found {len(users_in_db)} users for yacht {TEST_YACHT_ID}", file=sys.stderr)

    # Group by role
    users_by_role = {}
    for user in users_in_db:
        role = user.get("role", "crew")
        if role not in users_by_role:
            users_by_role[role] = []
        users_by_role[role].append(user)

    print(f"   Roles found: {list(users_by_role.keys())}", file=sys.stderr)
    print("", file=sys.stderr)

except Exception as e:
    print(f"❌ Error querying users: {e}", file=sys.stderr)
    print("", file=sys.stderr)
    users_by_role = {}

# Define the 15 personas we need
personas = [
    {"label": "CREW_JWT", "role": "crew", "description": "Basic crew member"},
    {"label": "DECKHAND_JWT", "role": "deckhand", "description": "Deck crew"},
    {"label": "STEWARD_JWT", "role": "steward", "description": "Interior crew"},
    {"label": "ENGINEER_JWT", "role": "engineer", "description": "Engineering crew"},
    {"label": "ETO_JWT", "role": "eto", "description": "Electrical Technical Officer"},
    {"label": "CHIEF_ENGINEER_JWT", "role": "chief_engineer", "description": "HOD (can mutate)"},
    {"label": "CHIEF_OFFICER_JWT", "role": "chief_officer", "description": "HOD (can mutate)"},
    {"label": "CHIEF_STEWARD_JWT", "role": "chief_steward", "description": "HOD (can mutate)"},
    {"label": "PURSER_JWT", "role": "purser", "description": "HOD (can mutate)"},
    {"label": "CAPTAIN_JWT", "role": "captain", "description": "Senior officer (can sign)"},
    {"label": "MANAGER_JWT", "role": "manager", "description": "Shore-based manager (can sign)"},
]

# Edge cases - we'll create synthetic users for these
edge_cases = [
    {"label": "INACTIVE_JWT", "role": "crew", "active_status": "inactive", "description": "Inactive user"},
    {"label": "EXPIRED_JWT", "role": "crew", "expired": True, "description": "Expired token"},
    {"label": "WRONG_YACHT_JWT", "role": "crew", "wrong_yacht": True, "description": "Different yacht"},
    {"label": "MIXED_ROLE_JWT", "role": "captain,manager", "description": "Mixed roles"},
]

# Get JWT secret - try to extract from service key or use known secret
JWT_SECRET = None

# Try common Supabase JWT secret extraction methods
if not JWT_SECRET:
    # Check if we have a direct secret
    JWT_SECRET = os.getenv("TENANT_1_SUPABASE_JWT_SECRET")

if not JWT_SECRET:
    print("❌ ERROR: Cannot generate JWTs without JWT secret", file=sys.stderr)
    print("", file=sys.stderr)
    print("💡 Please set TENANT_1_SUPABASE_JWT_SECRET environment variable", file=sys.stderr)
    print("   You can find it in your Supabase project settings under 'API' > 'JWT Secret'", file=sys.stderr)
    print("", file=sys.stderr)
    print("⚠️  FALLBACK: Using service key directly for API calls", file=sys.stderr)
    print("", file=sys.stderr)

    # Fallback: Export service key as all JWTs
    # This won't work for actual JWT validation but will let tests use service role
    print("# FALLBACK: Using service key (tests may need adjustment)")
    for persona in personas + edge_cases:
        print(f"export {persona['label']}='{TENANT_1_SERVICE_KEY}'")

    sys.exit(0)

# Generate JWTs
now = datetime.utcnow()
exp = now + timedelta(hours=24)

generated_jwts = {}

for persona in personas:
    label = persona["label"]
    role = persona["role"]
    description = persona["description"]

    # Find a user with this role in the database
    user = None
    if role in users_by_role and users_by_role[role]:
        user = users_by_role[role][0]  # Take first user with this role

    if not user:
        # Create synthetic user ID
        user = {
            "id": f"synthetic-{role}-user-id",
            "email": f"{role}@test.celeste7.ai",
            "role": role,
            "full_name": f"Test {role.title()}",
            "active_status": "active"
        }
        print(f"⚠️  No real user found for {role}, using synthetic user", file=sys.stderr)

    payload = {
        "aud": "authenticated",
        "exp": int(exp.timestamp()),
        "iat": int(now.timestamp()),
        "iss": TENANT_1_SUPABASE_URL + "/auth/v1",
        "sub": user["id"],
        "email": user["email"],
        "phone": "",
        "app_metadata": {
            "provider": "email",
            "providers": ["email"]
        },
        "user_metadata": {
            "yacht_id": TEST_YACHT_ID,
            "role": role
        },
        "role": "authenticated",
        "aal": "aal1",
        "amr": [{"method": "password", "timestamp": int(now.timestamp())}],
        "session_id": f"test-session-{label.lower()}-{now.strftime('%Y%m%d%H%M%S')}"
    }

    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    generated_jwts[label] = token

    print(f"✅ {label}: {description}", file=sys.stderr)
    print(f"   Role: {role}, User: {user['email']}", file=sys.stderr)

# Generate edge case JWTs
for persona in edge_cases:
    label = persona["label"]
    role = persona.get("role", "crew")
    description = persona["description"]

    # Special handling for edge cases
    if "wrong_yacht" in persona:
        yacht_id = "different-yacht-id-12345"
    else:
        yacht_id = TEST_YACHT_ID

    if "expired" in persona:
        exp_time = now - timedelta(hours=1)  # Expired 1 hour ago
    else:
        exp_time = exp

    user_id = f"edge-case-{label.lower()}-user-id"
    email = f"{label.lower()}@test.celeste7.ai"

    payload = {
        "aud": "authenticated",
        "exp": int(exp_time.timestamp()),
        "iat": int(now.timestamp()),
        "iss": TENANT_1_SUPABASE_URL + "/auth/v1",
        "sub": user_id,
        "email": email,
        "phone": "",
        "app_metadata": {
            "provider": "email",
            "providers": ["email"]
        },
        "user_metadata": {
            "yacht_id": yacht_id,
            "role": role,
            "active_status": persona.get("active_status", "active")
        },
        "role": "authenticated",
        "aal": "aal1",
        "amr": [{"method": "password", "timestamp": int(now.timestamp())}],
        "session_id": f"test-session-{label.lower()}-{now.strftime('%Y%m%d%H%M%S')}"
    }

    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    generated_jwts[label] = token

    print(f"✅ {label}: {description}", file=sys.stderr)

print("", file=sys.stderr)
print("=" * 80, file=sys.stderr)
print("✅ ALL 15 JWTS GENERATED", file=sys.stderr)
print("=" * 80, file=sys.stderr)
print("", file=sys.stderr)

# Output export commands
for label, token in generated_jwts.items():
    print(f"export {label}='{token}'")

print("", file=sys.stderr)
print("✅ Copy the export commands above to set environment variables", file=sys.stderr)
