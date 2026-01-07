#!/usr/bin/env python3
"""Test Render deployment endpoint."""

import requests
import json
import time

RENDER_URL = "https://celeste-microactions.onrender.com"
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"

def test_health():
    """Test health endpoint."""
    print("Testing /health endpoint...")
    try:
        response = requests.get(f"{RENDER_URL}/health", timeout=10)
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            print(f"  Response: {response.json()}")
            return True
    except Exception as e:
        print(f"  Error: {e}")
    return False

def test_search(query, description):
    """Test search endpoint."""
    print(f"\n{'='*60}")
    print(f"Testing: {description}")
    print(f"Query: '{query}'")
    print(f"{'='*60}")

    try:
        payload = {
            "query": query,
            "yacht_id": YACHT_ID,
            "limit": 10
        }

        response = requests.post(
            f"{RENDER_URL}/search",
            json=payload,
            timeout=30
        )

        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()

            print(f"Success: {data.get('success')}")
            print(f"Total results: {data.get('total_count', 0)}")

            # Check for domain grouping
            if 'results_by_domain' in data:
                domains = data['results_by_domain']
                print(f"\n✅ Domain grouping present!")
                print(f"Domains found: {list(domains.keys())}")

                for domain, info in domains.items():
                    count = info.get('count', 0)
                    capability = info.get('source_capability', 'unknown')
                    print(f"  - {domain}: {count} results (from {capability})")

                    # Show first result from each domain
                    if info.get('results') and len(info['results']) > 0:
                        first = info['results'][0]
                        name = first.get('name') or first.get('code') or first.get('title', 'N/A')
                        print(f"      Example: {name}")
            else:
                print("⚠️  No domain grouping found")

            # Check timing
            timing = data.get('timing_ms', {})
            total = timing.get('total', 0)
            print(f"\nTiming: {total:.0f}ms total")

            return True
        else:
            print(f"Error: {response.text}")
            return False

    except Exception as e:
        print(f"Exception: {e}")
        return False

def main():
    print("="*60)
    print("RENDER DEPLOYMENT TEST")
    print("="*60)

    # Test 1: Health check
    if not test_health():
        print("\n❌ Health check failed - deployment may still be in progress")
        print("Wait 2-3 minutes and try again")
        return

    print("\n✅ Health check passed - testing search endpoints...\n")
    time.sleep(2)

    # Test 2: Multi-word fault code
    test_search("MID 128", "Multi-word fault code (smart pattern matching)")

    time.sleep(1)

    # Test 3: Multi-word part search
    test_search("fuel filter", "Multi-word part search")

    time.sleep(1)

    # Test 4: Multi-domain query
    test_search("MTU fuel", "Multi-domain query (should hit parts + equipment)")

    time.sleep(1)

    # Test 5: Equipment search
    test_search("main engine", "Equipment search")

    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)

if __name__ == "__main__":
    main()
