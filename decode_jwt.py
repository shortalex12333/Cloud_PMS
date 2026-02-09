#!/usr/bin/env python3
import json
import base64
import sys

if len(sys.argv) < 2:
    print("Usage: decode_jwt.py <jwt_token>")
    sys.exit(1)

jwt = sys.argv[1]
parts = jwt.split('.')

if len(parts) >= 2:
    # Add padding if necessary
    payload = parts[1]
    padding = len(payload) % 4
    if padding:
        payload += '=' * (4 - padding)

    try:
        decoded = base64.urlsafe_b64decode(payload)
        data = json.loads(decoded)
        print(json.dumps({
            'user_id': data.get('sub'),
            'email': data.get('email'),
            'role': data.get('role'),
            'app_metadata': data.get('app_metadata', {}),
            'user_metadata': data.get('user_metadata', {})
        }, indent=2))
    except Exception as e:
        print(f"Error: {e}")
else:
    print("Invalid JWT")
