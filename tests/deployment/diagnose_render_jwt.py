"""
Render JWT Diagnostic Tool

Run this in Render Shell to identify which secret validates the test JWT.

Usage in Render Shell:
    python3 diagnose_render_jwt.py
"""

import os
import jwt
import json

# Test JWT from qvzmkaamzaqxpzbewjxe.supabase.co
TEST_JWT = "eyJhbGciOiJIUzI1NiIsImtpZCI6IjE3UGY4ZUVPVnFXZXlmRGIiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL3F2em1rYWFtemFxeHB6YmV3anhlLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiI1N2U4MmY3OC0wYTJkLTRhN2MtYTQyOC02Mjg3NjIxZDA2YzUiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzcwNjU3ODgyLCJpYXQiOjE3NzA2NTQyODIsImVtYWlsIjoiY3Jldy50ZXN0QGFsZXgtc2hvcnQuY29tIiwicGhvbmUiOiIiLCJhcHBfbWV0YWRhdGEiOnsicHJvdmlkZXIiOiJlbWFpbCIsInByb3ZpZGVycyI6WyJlbWFpbCJdfSwidXNlcl9tZXRhZGF0YSI6eyJlbWFpbF92ZXJpZmllZCI6dHJ1ZX0sInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiYWFsIjoiYWFsMSIsImFtciI6W3sibWV0aG9kIjoicGFzc3dvcmQiLCJ0aW1lc3RhbXAiOjE3NzA2NTQyODJ9XSwic2Vzc2lvbl9pZCI6ImVjNTZiZjE0LWRmYzItNDBhMS1iYzQyLTAzOWRmYTg5ZTUyMyIsImlzX2Fub255bW91cyI6ZmFsc2V9.4TbK_FEuw54Be8qpPwyVmG7pdIDCJ_-p47s6g2Hvqrc"

def main():
    print("=" * 80)
    print("RENDER JWT SECRET DIAGNOSTIC")
    print("=" * 80)

    # Show environment config
    print("\nEnvironment Variables:")
    print("-" * 80)

    env_vars = {
        "MASTER_SUPABASE_JWT_SECRET": os.getenv("MASTER_SUPABASE_JWT_SECRET"),
        "TENANT_SUPABASE_JWT_SECRET": os.getenv("TENANT_SUPABASE_JWT_SECRET"),
        "yTEST_YACHT_001_SUPABASE_JWT_SECRET": os.getenv("yTEST_YACHT_001_SUPABASE_JWT_SECRET"),
        "SUPABASE_JWT_SECRET": os.getenv("SUPABASE_JWT_SECRET"),
    }

    urls = {
        "MASTER_SUPABASE_URL": os.getenv("MASTER_SUPABASE_URL"),
        "yTEST_YACHT_001_SUPABASE_URL": os.getenv("yTEST_YACHT_001_SUPABASE_URL"),
    }

    for name, value in env_vars.items():
        if value:
            print(f"{name}: {value[:10]}...{value[-10:]} ({len(value)} chars)")
        else:
            print(f"{name}: Not set")

    print("\nURLs:")
    for name, value in urls.items():
        if value:
            print(f"{name}: {value}")
        else:
            print(f"{name}: Not set")

    # Decode JWT to show issuer
    print("\n" + "=" * 80)
    print("TEST JWT INFO")
    print("=" * 80)

    try:
        import base64
        parts = TEST_JWT.split('.')
        payload = parts[1]
        payload += '=' * (4 - len(payload) % 4)
        decoded_payload = json.loads(base64.urlsafe_b64decode(payload))

        print(f"\nIssuer: {decoded_payload.get('iss')}")
        print(f"Email: {decoded_payload.get('email')}")
        print(f"User ID: {decoded_payload.get('sub')}")
    except Exception as e:
        print(f"Could not decode JWT: {e}")

    # Test each secret
    print("\n" + "=" * 80)
    print("TESTING EACH SECRET")
    print("=" * 80)

    valid_secrets = []

    for name, secret in env_vars.items():
        if not secret:
            print(f"\n{name}: ⚠️  Not set")
            continue

        print(f"\n{name}:")

        try:
            decoded = jwt.decode(
                TEST_JWT,
                secret,
                algorithms=["HS256"],
                options={"verify_aud": False}
            )
            print(f"  ✅ VALID SIGNATURE")
            print(f"  User: {decoded.get('email')}")
            print(f"  Issuer: {decoded.get('iss')}")
            valid_secrets.append(name)

        except jwt.InvalidSignatureError:
            print(f"  ❌ Invalid signature")
        except jwt.ExpiredSignatureError:
            print(f"  ⚠️  Expired (but signature would be valid)")
            valid_secrets.append((name, "expired"))
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")

    # Results and recommendations
    print("\n" + "=" * 80)
    print("DIAGNOSIS")
    print("=" * 80)

    if not valid_secrets:
        print("\n❌ NO VALID SECRETS FOUND")
        print("\n🔧 FIX REQUIRED:")
        print("   1. Go to https://supabase.com/dashboard")
        print("   2. Select qvzmkaamzaqxpzbewjxe project")
        print("   3. Settings → API → Copy 'JWT Secret' (NOT anon key or service key)")
        print("   4. In Render: Set MASTER_SUPABASE_JWT_SECRET = <that JWT secret>")
        print("   5. Redeploy")

    elif "yTEST_YACHT_001_SUPABASE_JWT_SECRET" in [s if isinstance(s, str) else s[0] for s in valid_secrets]:
        if "MASTER_SUPABASE_JWT_SECRET" not in [s if isinstance(s, str) else s[0] for s in valid_secrets]:
            print("\n⚠️  CONFIGURATION MISMATCH")
            print(f"\n   Valid secrets found: {[s if isinstance(s, str) else s[0] for s in valid_secrets]}")
            print("\n   yTEST_YACHT_001_SUPABASE_JWT_SECRET validates the JWT")
            print("   But API prioritizes MASTER_SUPABASE_JWT_SECRET (which is invalid)")
            print("\n🔧 FIX:")
            print("   In Render: Copy yTEST_YACHT_001_SUPABASE_JWT_SECRET value")
            print("              to MASTER_SUPABASE_JWT_SECRET")
            print("   Then: Redeploy")
        else:
            print("\n✅ CONFIGURATION CORRECT")
            print(f"\n   Valid secrets: {[s if isinstance(s, str) else s[0] for s in valid_secrets]}")
            print("   MASTER_SUPABASE_JWT_SECRET validates correctly")
            print("\n⚠️  If you're still getting errors, check:")
            print("   1. JWT hasn't expired")
            print("   2. No whitespace in MASTER_SUPABASE_JWT_SECRET value")
            print("   3. Service has been redeployed after env var changes")

    elif "MASTER_SUPABASE_JWT_SECRET" in [s if isinstance(s, str) else s[0] for s in valid_secrets]:
        print("\n✅ CONFIGURATION CORRECT")
        print(f"\n   Valid secrets: {[s if isinstance(s, str) else s[0] for s in valid_secrets]}")
        print("   MASTER_SUPABASE_JWT_SECRET validates correctly")

    else:
        print(f"\n⚠️  Valid secrets found: {valid_secrets}")
        print("   But MASTER_SUPABASE_JWT_SECRET is invalid")
        print("\n🔧 FIX: Update MASTER_SUPABASE_JWT_SECRET to match JWT issuer project")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
