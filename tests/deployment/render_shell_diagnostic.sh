#!/bin/bash
# Run this in Render Shell to diagnose JWT secret mismatch
#
# Usage:
#   1. Go to Render service → Shell
#   2. Run: bash render_shell_diagnostic.sh

echo "================================================================================"
echo "RENDER JWT SECRET DIAGNOSTIC"
echo "================================================================================"

echo ""
echo "Environment Variables:"
echo "----------------------"

if [ -n "$MASTER_SUPABASE_JWT_SECRET" ]; then
    echo "MASTER_SUPABASE_JWT_SECRET: ${MASTER_SUPABASE_JWT_SECRET:0:10}...${MASTER_SUPABASE_JWT_SECRET: -10} (${#MASTER_SUPABASE_JWT_SECRET} chars)"
else
    echo "MASTER_SUPABASE_JWT_SECRET: Not set"
fi

if [ -n "$TENANT_SUPABASE_JWT_SECRET" ]; then
    echo "TENANT_SUPABASE_JWT_SECRET: ${TENANT_SUPABASE_JWT_SECRET:0:10}...${TENANT_SUPABASE_JWT_SECRET: -10} (${#TENANT_SUPABASE_JWT_SECRET} chars)"
else
    echo "TENANT_SUPABASE_JWT_SECRET: Not set"
fi

if [ -n "$yTEST_YACHT_001_SUPABASE_JWT_SECRET" ]; then
    echo "yTEST_YACHT_001_SUPABASE_JWT_SECRET: ${yTEST_YACHT_001_SUPABASE_JWT_SECRET:0:10}...${yTEST_YACHT_001_SUPABASE_JWT_SECRET: -10} (${#yTEST_YACHT_001_SUPABASE_JWT_SECRET} chars)"
else
    echo "yTEST_YACHT_001_SUPABASE_JWT_SECRET: Not set"
fi

echo ""
echo "URLs:"
echo "-----"
echo "MASTER_SUPABASE_URL: $MASTER_SUPABASE_URL"
echo "yTEST_YACHT_001_SUPABASE_URL: $yTEST_YACHT_001_SUPABASE_URL"

echo ""
echo "================================================================================"
echo "TESTING JWT VALIDATION WITH EACH SECRET"
echo "================================================================================"

# Test JWT (replace with actual JWT)
TEST_JWT="eyJhbGciOiJIUzI1NiIsImtpZCI6IjE3UGY4ZUVPVnFXZXlmRGIiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL3F2em1rYWFtemFxeHB6YmV3anhlLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiI1N2U4MmY3OC0wYTJkLTRhN2MtYTQyOC02Mjg3NjIxZDA2YzUiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzcwNjU3ODgyLCJpYXQiOjE3NzA2NTQyODIsImVtYWlsIjoiY3Jldy50ZXN0QGFsZXgtc2hvcnQuY29tIiwicGhvbmUiOiIiLCJhcHBfbWV0YWRhdGEiOnsicHJvdmlkZXIiOiJlbWFpbCIsInByb3ZpZGVycyI6WyJlbWFpbCJdfSwidXNlcl9tZXRhZGF0YSI6eyJlbWFpbF92ZXJpZmllZCI6dHJ1ZX0sInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiYWFsIjoiYWFsMSIsImFtciI6W3sibWV0aG9kIjoicGFzc3dvcmQiLCJ0aW1lc3RhbXAiOjE3NzA2NTQyODJ9XSwic2Vzc2lvbl9pZCI6ImVjNTZiZjE0LWRmYzItNDBhMS1iYzQyLTAzOWRmYTg5ZTUyMyIsImlzX2Fub255bW91cyI6ZmFsc2V9.4TbK_FEuw54Be8qpPwyVmG7pdIDCJ_-p47s6g2Hvqrc"

python3 << 'PYTHON_SCRIPT'
import os
import jwt
import sys

test_jwt = os.getenv("TEST_JWT")
if not test_jwt:
    print("ERROR: TEST_JWT not set")
    sys.exit(1)

secrets = {
    "MASTER_SUPABASE_JWT_SECRET": os.getenv("MASTER_SUPABASE_JWT_SECRET"),
    "TENANT_SUPABASE_JWT_SECRET": os.getenv("TENANT_SUPABASE_JWT_SECRET"),
    "yTEST_YACHT_001_SUPABASE_JWT_SECRET": os.getenv("yTEST_YACHT_001_SUPABASE_JWT_SECRET"),
}

print("\nTesting JWT validation with each secret...\n")

valid_secrets = []

for name, secret in secrets.items():
    if not secret:
        print(f"{name}: Not set")
        continue

    try:
        decoded = jwt.decode(test_jwt, secret, algorithms=["HS256"], options={"verify_aud": False})
        print(f"✅ {name}: VALID")
        print(f"   User: {decoded.get('email')}")
        print(f"   Issuer: {decoded.get('iss')}")
        valid_secrets.append(name)
    except jwt.InvalidSignatureError:
        print(f"❌ {name}: Invalid signature")
    except jwt.ExpiredSignatureError:
        print(f"⚠️  {name}: Expired (but signature valid)")
        valid_secrets.append(name)
    except Exception as e:
        print(f"❌ {name}: Error - {str(e)}")
    print()

print("="*80)
print("RESULT")
print("="*80)

if valid_secrets:
    print(f"\n✅ Valid secrets: {', '.join(valid_secrets)}")

    if "yTEST_YACHT_001_SUPABASE_JWT_SECRET" in valid_secrets and "MASTER_SUPABASE_JWT_SECRET" not in valid_secrets:
        print("\n⚠️  FIX REQUIRED:")
        print("   yTEST_YACHT_001_SUPABASE_JWT_SECRET has the correct value")
        print("   But API uses MASTER_SUPABASE_JWT_SECRET (priority 1)")
        print("\n   ACTION: Copy yTEST_YACHT_001_SUPABASE_JWT_SECRET value to MASTER_SUPABASE_JWT_SECRET")
    elif "MASTER_SUPABASE_JWT_SECRET" in valid_secrets:
        print("\n✅ Configuration correct - MASTER_SUPABASE_JWT_SECRET matches")
else:
    print("\n❌ NO VALID SECRETS")
    print("\n   ACTION: Get JWT secret from qvzmkaamzaqxpzbewjxe Supabase project")
    print("           and set MASTER_SUPABASE_JWT_SECRET to that value")

PYTHON_SCRIPT

echo ""
echo "================================================================================"
