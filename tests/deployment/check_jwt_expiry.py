"""
JWT Expiry Checker

Decodes JWT tokens and checks their expiration status.
"""

import json
import base64
from datetime import datetime, timezone
import sys


def decode_jwt(token):
    """Decode JWT and return payload"""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None

        payload = parts[1]
        # Add padding if needed
        payload += '=' * (4 - len(payload) % 4)

        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)

    except Exception as e:
        print(f"Error decoding JWT: {e}")
        return None


def check_expiry(payload):
    """Check if JWT is expired"""
    if not payload or 'exp' not in payload:
        return None, None

    exp_timestamp = payload['exp']
    exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
    now = datetime.now(timezone.utc)

    is_expired = now > exp_datetime
    time_diff = exp_datetime - now

    return is_expired, time_diff


def format_time_diff(time_diff):
    """Format time difference as human-readable string"""
    total_seconds = abs(time_diff.total_seconds())

    if total_seconds < 60:
        return f"{int(total_seconds)} seconds"
    elif total_seconds < 3600:
        minutes = int(total_seconds / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    elif total_seconds < 86400:
        hours = int(total_seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''}"
    else:
        days = int(total_seconds / 86400)
        return f"{days} day{'s' if days != 1 else ''}"


def main():
    print("\n" + "="*80)
    print("JWT EXPIRY CHECKER")
    print("="*80)

    try:
        with open('test-jwts.json', 'r') as f:
            tokens = json.load(f)
    except FileNotFoundError:
        print("\n❌ test-jwts.json not found")
        print("\nRun: python3 get_test_jwts.py")
        return 1

    all_valid = True

    for role, data in tokens.items():
        print(f"\n{role} ({data['email']}):")

        payload = decode_jwt(data['jwt'])
        if not payload:
            print("  ❌ Could not decode JWT")
            all_valid = False
            continue

        is_expired, time_diff = check_expiry(payload)

        if is_expired is None:
            print("  ⚠️  No expiration timestamp found")
            continue

        if is_expired:
            print(f"  ❌ EXPIRED {format_time_diff(time_diff)} ago")
            all_valid = False
        else:
            print(f"  ✅ Valid for {format_time_diff(time_diff)}")

        # Show issuer
        if 'iss' in payload:
            print(f"  Issuer: {payload['iss']}")

    print("\n" + "="*80)

    if not all_valid:
        print("\n⚠️  Some tokens are expired. Run: python3 get_test_jwts.py")
        return 1

    print("\n✅ All tokens valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
