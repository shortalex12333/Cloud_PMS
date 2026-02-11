#!/usr/bin/env python3
"""
Day 5: XSS Vulnerability Investigation
Detailed analysis of where XSS payloads appear in API responses
"""

import os
import json
import requests

API_BASE = os.getenv("API_BASE", "https://pipeline-core.int.celeste7.ai")
SUPABASE_URL = os.getenv("MASTER_SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("MASTER_SUPABASE_ANON_KEY")

def sign_in_hod():
    """Sign in as HOD user."""
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Content-Type": "application/json",
    }
    response = requests.post(
        f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
        headers=headers,
        json={"email": "hod.test@alex-short.com", "password": "Password2!"},
        timeout=10,
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    return None

def investigate_xss():
    """Investigate XSS vulnerability in detail."""
    token = sign_in_hod()
    if not token:
        print("❌ Failed to sign in")
        return

    auth_header = {"Authorization": f"Bearer {token}"}

    xss_payload = "<script>alert('XSS')</script>"

    print(f"\nTesting XSS payload: {xss_payload}")
    print("=" * 80)

    response = requests.post(
        f"{API_BASE}/search",
        headers=auth_header,
        json={"query": xss_payload, "limit": 10},
        timeout=5,
    )

    print(f"\nStatus Code: {response.status_code}")
    print(f"\nResponse Headers:")
    for key, value in response.headers.items():
        print(f"  {key}: {value}")

    print(f"\nResponse Body:")
    print("=" * 80)

    try:
        response_json = response.json()
        print(json.dumps(response_json, indent=2))

        # Check where the payload appears
        response_str = json.dumps(response_json)

        print("\n" + "=" * 80)
        print("XSS VULNERABILITY ANALYSIS")
        print("=" * 80)

        if xss_payload in response_str:
            print(f"⚠️  VULNERABLE: Raw XSS payload found in response!")
            print(f"\nSearching for payload occurrences...")

            # Find where it appears in the structure
            def find_payload_in_dict(obj, path=""):
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        new_path = f"{path}.{key}" if path else key
                        find_payload_in_dict(value, new_path)
                elif isinstance(obj, list):
                    for idx, item in enumerate(obj):
                        new_path = f"{path}[{idx}]"
                        find_payload_in_dict(item, new_path)
                elif isinstance(obj, str):
                    if xss_payload in obj:
                        print(f"  Found at: {path}")
                        print(f"  Value: {obj[:200]}...")

            find_payload_in_dict(response_json)

        else:
            print("✅ SAFE: XSS payload was escaped or filtered")

            # Check if it was escaped
            escaped_variants = [
                "&lt;script&gt;alert('XSS')&lt;/script&gt;",
                "<script>alert(\\'XSS\\')</script>",
                "\\u003cscript\\u003ealert('XSS')\\u003c/script\\u003e",
            ]

            for variant in escaped_variants:
                if variant in response_str:
                    print(f"  Escaped as: {variant}")
                    break

    except json.JSONDecodeError:
        print(response.text[:1000])

        if xss_payload in response.text:
            print("\n⚠️  VULNERABLE: Raw XSS payload in non-JSON response!")
        else:
            print("\n✅ SAFE: XSS payload not found in response")

if __name__ == "__main__":
    investigate_xss()
