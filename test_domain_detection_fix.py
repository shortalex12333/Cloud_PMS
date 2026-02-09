#!/usr/bin/env python3
"""
Test Domain Detection Fix for Shopping List
============================================
Tests that shopping_list queries now correctly classify to shopping_list domain.
"""

import sys
sys.path.insert(0, 'apps/api')

from domain_microactions import detect_domain_with_confidence

# Test queries that should classify to shopping_list
TEST_QUERIES = [
    "shopping list",
    "show me candidate parts on shopping list",
    "procurement items",
    "MTU coolant requisition",
    "parts requisition list",
    "requested parts",
    "pending approvals shopping list",
    "candidate parts",
    "buy list",
    "spare parts list",
]

print("=" * 70)
print("DOMAIN DETECTION FIX TEST")
print("=" * 70)
print()
print("Testing shopping_list domain detection...")
print()

passed = 0
failed = 0

for query in TEST_QUERIES:
    domain, confidence = detect_domain_with_confidence(query)

    if domain == "shopping_list":
        status = "✅ PASS"
        passed += 1
    else:
        status = f"❌ FAIL (got: {domain})"
        failed += 1

    print(f"{status} | Query: \"{query}\"")
    print(f"         Domain: {domain}, Confidence: {confidence:.2f}")
    print()

print("=" * 70)
print(f"RESULTS: {passed} passed, {failed} failed")
print("=" * 70)

if failed == 0:
    print("✅ All tests passed! Shopping list domain detection is working.")
    sys.exit(0)
else:
    print(f"❌ {failed} tests failed. Domain detection needs more work.")
    sys.exit(1)
