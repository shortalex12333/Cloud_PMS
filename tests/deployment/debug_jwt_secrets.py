"""
JWT Secret Debug Tool

Tests JWT validation with different secrets to identify which one matches.
Useful for diagnosing JWT signature validation issues.
"""

import os
import json
import jwt
import sys


def test_jwt_with_secrets():
    """Test JWT with different configured secrets"""

    # Load test JWT
    try:
        with open('test-jwts.json', 'r') as f:
            tokens = json.load(f)
            token = tokens['CREW']['jwt']
            email = tokens['CREW']['email']
    except FileNotFoundError:
        print("❌ test-jwts.json not found. Run: python3 get_test_jwts.py")
        return False

    print("="*80)
    print("JWT SECRET DEBUG TOOL")
    print("="*80)
    print(f"Testing JWT for: {email}")
    print("="*80)

    # Get secrets from environment
    secrets = {
        "MASTER_SUPABASE_JWT_SECRET": os.getenv("MASTER_SUPABASE_JWT_SECRET"),
        "TENANT_SUPABASE_JWT_SECRET": os.getenv("TENANT_SUPABASE_JWT_SECRET"),
        "TENNANT_SUPABASE_JWT_SECRET": os.getenv("TENNANT_SUPABASE_JWT_SECRET"),  # Typo fallback
        "yTEST_YACHT_001_SUPABASE_JWT_SECRET": os.getenv("yTEST_YACHT_001_SUPABASE_JWT_SECRET"),
        "SUPABASE_JWT_SECRET": os.getenv("SUPABASE_JWT_SECRET"),
    }

    valid_secrets = []

    # Test each secret
    for name, secret in secrets.items():
        print(f"\nTesting {name}...")

        if not secret:
            print(f"   ⚠️  Not set")
            continue

        print(f"   Secret: {secret[:10]}...{secret[-10:]} ({len(secret)} chars)")

        try:
            decoded = jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
                options={"verify_aud": False}
            )

            print(f"   ✅ VALID SIGNATURE")
            print(f"   User: {decoded.get('email')}")
            print(f"   User ID: {decoded.get('sub')}")
            print(f"   Issuer: {decoded.get('iss')}")

            valid_secrets.append(name)

        except jwt.InvalidSignatureError:
            print(f"   ❌ Invalid signature")
        except jwt.ExpiredSignatureError:
            print(f"   ⚠️  Expired (but signature would be valid)")
            valid_secrets.append(name)
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    if valid_secrets:
        print(f"\n✅ Valid secrets found: {len(valid_secrets)}")
        for name in valid_secrets:
            print(f"   - {name}")

        if "MASTER_SUPABASE_JWT_SECRET" in valid_secrets:
            print("\n✅ MASTER_SUPABASE_JWT_SECRET matches (preferred)")
        elif "yTEST_YACHT_001_SUPABASE_JWT_SECRET" in valid_secrets:
            print(f"\n⚠️  yTEST_YACHT_001_SUPABASE_JWT_SECRET matches")
            print(f"   This is a TENANT secret, but API prefers MASTER")
            print(f"\n   FIX: Copy yTEST_YACHT_001_SUPABASE_JWT_SECRET value to MASTER_SUPABASE_JWT_SECRET")
        else:
            print(f"\n⚠️  WARNING: MASTER_SUPABASE_JWT_SECRET not valid")
            print(f"   API will use: {valid_secrets[0]}")
    else:
        print("\n❌ NO VALID SECRETS FOUND")
        print("\nPossible Issues:")
        print("1. Test JWT from different Supabase project than configured secrets")
        print("2. Whitespace/formatting issues in environment variables")
        print("3. Wrong JWT secret copied from Supabase dashboard")
        print("\nNext Steps:")
        print("1. Decode JWT to see issuer: python3 -c 'import base64, json; parts=\"$(cat test-jwts.json | jq -r .CREW.jwt)\".split(\".\"); print(json.loads(base64.urlsafe_b64decode(parts[1] + \"===\")))'")
        print("2. Get JWT secret from that project's Supabase dashboard")
        print("3. Set MASTER_SUPABASE_JWT_SECRET to that value in Render")

    print("="*80)

    return len(valid_secrets) > 0


def decode_jwt_header(token):
    """Decode JWT to show issuer info"""
    import base64

    try:
        parts = token.split('.')
        payload = parts[1]
        payload += '=' * (4 - len(payload) % 4)
        decoded = json.loads(base64.urlsafe_b64decode(payload))

        print("\nJWT Payload Info:")
        print(f"  Issuer: {decoded.get('iss')}")
        print(f"  Email: {decoded.get('email')}")
        print(f"  User ID: {decoded.get('sub')}")
        print(f"  Issued: {decoded.get('iat')}")
        print(f"  Expires: {decoded.get('exp')}")

    except Exception as e:
        print(f"  Could not decode: {e}")


def main():
    print("\n" + "="*80)
    print("ENVIRONMENT VARIABLES")
    print("="*80)

    env_vars = [
        "MASTER_SUPABASE_JWT_SECRET",
        "TENANT_SUPABASE_JWT_SECRET",
        "yTEST_YACHT_001_SUPABASE_JWT_SECRET",
        "SUPABASE_JWT_SECRET",
        "MASTER_SUPABASE_URL",
        "yTEST_YACHT_001_SUPABASE_URL",
    ]

    for var in env_vars:
        value = os.getenv(var)
        if value:
            if "SECRET" in var or "KEY" in var:
                print(f"{var}: {value[:10]}...{value[-10:]} ({len(value)} chars)")
            else:
                print(f"{var}: {value}")
        else:
            print(f"{var}: Not set")

    print("\n")

    # Test JWTs
    success = test_jwt_with_secrets()

    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
