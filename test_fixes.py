#!/usr/bin/env python3
"""
Quick test script to verify SQL fixes before deploying to Render.

Tests:
1. Smart pattern matching ("MID 128" should find "MID 128 SID 001")
2. Domain grouping (results should be grouped by capability)
3. Metadata tagging (results should have _capability field)
"""

import os
import sys
from supabase import create_client

# Add api directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))

from pipeline_v1 import Pipeline

# Configuration
SUPABASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
SUPABASE_KEY = os.environ.get(
    "SUPABASE_SERVICE_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY"
)
TEST_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"


def test_pattern_matching():
    """Test smart pattern matching."""
    print("\n" + "="*60)
    print("TEST 1: Smart Pattern Matching")
    print("="*60)

    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    pipeline = Pipeline(client, TEST_YACHT_ID)

    test_queries = [
        ("MID 128", "Should find 'MID 128 SID 001'"),
        ("turbo gasket", "Should find 'Turbocharger Gasket Set'"),
        ("fuel filter", "Should find parts with 'Fuel' and 'Filter'"),
        ("fault 001", "Should find 'Fault 001'"),
    ]

    for query, expected in test_queries:
        print(f"\nQuery: '{query}'")
        print(f"Expected: {expected}")

        response = pipeline.search(query, limit=5)

        if response.success:
            print(f"✓ Found {response.total_count} results")
            if response.total_count > 0:
                # Show first result
                first = response.results[0]
                name = first.get('name') or first.get('code') or first.get('title', 'N/A')
                print(f"  First result: {name}")
        else:
            print(f"✗ Error: {response.error}")


def test_domain_grouping():
    """Test domain grouping."""
    print("\n" + "="*60)
    print("TEST 2: Domain Grouping")
    print("="*60)

    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    pipeline = Pipeline(client, TEST_YACHT_ID)

    # Query that should hit multiple domains
    query = "MTU fuel"
    print(f"\nQuery: '{query}'")
    print("Expected: Results grouped by parts, equipment, etc.")

    response = pipeline.search(query, limit=20)

    if response.success:
        print(f"\n✓ Total results: {response.total_count}")

        # Check if results_by_domain exists
        if hasattr(response, 'results_by_domain') and response.results_by_domain:
            print(f"✓ Domain grouping present")
            print(f"\nDomains found:")
            for domain, data in response.results_by_domain.items():
                count = data.get('count', 0)
                capability = data.get('source_capability', 'unknown')
                print(f"  - {domain}: {count} results (from {capability})")
        else:
            print("✗ No domain grouping found")

        # Check metadata tagging
        print(f"\nMetadata tagging:")
        if response.total_count > 0:
            first = response.results[0]
            if '_capability' in first:
                print(f"  ✓ Results tagged with _capability: {first['_capability']}")
            else:
                print(f"  ✗ Results missing _capability metadata")
    else:
        print(f"✗ Error: {response.error}")


def test_multi_token_queries():
    """Test multi-token queries."""
    print("\n" + "="*60)
    print("TEST 3: Multi-Token Queries")
    print("="*60)

    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    pipeline = Pipeline(client, TEST_YACHT_ID)

    test_queries = [
        "main engine overheating",
        "fuel injector nozzle",
        "E122 main engine",
    ]

    for query in test_queries:
        print(f"\nQuery: '{query}'")

        response = pipeline.search(query, limit=5)

        if response.success:
            print(f"  ✓ Found {response.total_count} results")

            # Show domains hit
            if hasattr(response, 'results_by_domain'):
                domains = list(response.results_by_domain.keys())
                if domains:
                    print(f"  Domains: {', '.join(domains)}")
        else:
            print(f"  ✗ Error: {response.error}")


def main():
    """Run all tests."""
    print("="*60)
    print("CLOUD_PMS SQL FIXES - LOCAL TEST")
    print("="*60)

    try:
        test_pattern_matching()
        test_domain_grouping()
        test_multi_token_queries()

        print("\n" + "="*60)
        print("TESTS COMPLETE")
        print("="*60)
        print("\nIf all tests passed, you can deploy to Render:")
        print("  git add -A")
        print("  git commit -m 'feat: improve SQL matching and add domain grouping'")
        print("  git push origin pipeline_v1")

    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
