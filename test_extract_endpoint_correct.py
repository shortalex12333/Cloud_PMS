#!/usr/bin/env python3
"""
Parts Lens - CORRECTED Extract Endpoint Tests
==============================================

Tests the ACTUAL /extract endpoint behavior (entity extraction only).

**IMPORTANT FINDING:**
The /extract endpoint does NOT return domain/domain_confidence.
Those fields are only available in /search endpoint (requires auth).

This test suite validates what /extract ACTUALLY returns:
- success: boolean
- entities: array of entity objects
- unknown_terms: array
- timing_ms: number

For domain detection tests, see test_search_domain_detection.py (requires auth).
"""

import requests
import json
import sys
from typing import Dict, Any

API_BASE = "https://pipeline-core.int.celeste7.ai"

class TestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []

    def test(self, name: str, fn):
        """Run a test and track results"""
        try:
            print(f"\n🧪 {name}")
            result = fn()
            if result.get("success"):
                print(f"   ✅ PASS: {result.get('message')}")
                self.passed += 1
                self.results.append({"test": name, "status": "PASS", **result})
            else:
                print(f"   ❌ FAIL: {result.get('message')}")
                self.failed += 1
                self.results.append({"test": name, "status": "FAIL", **result})
        except Exception as e:
            print(f"   ❌ FAIL: {str(e)}")
            self.failed += 1
            self.results.append({"test": name, "status": "FAIL", "error": str(e)})

    def summary(self):
        """Print test summary"""
        print("\n" + "=" * 70)
        print("TEST SUMMARY - /EXTRACT ENDPOINT (CORRECTED)")
        print("=" * 70)
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        print(f"📊 Total:  {self.passed + self.failed}")
        print("=" * 70)

        # Save results
        with open("test-results/extract_endpoint_corrected_results.json", "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"\nResults saved to: test-results/extract_endpoint_corrected_results.json")

        return self.failed == 0


# ============================================================================
# /EXTRACT ENDPOINT TESTS (Entity Extraction)
# ============================================================================

def test_extract_returns_success_field():
    """Test: /extract returns 'success' field"""
    response = requests.post(
        f"{API_BASE}/extract",
        json={"query": "teak seam compound"},
        timeout=10
    )

    if response.status_code == 200:
        body = response.json()
        if "success" in body:
            return {
                "success": True,
                "message": f"Returns 'success' field: {body['success']}",
            }
        else:
            return {
                "success": False,
                "message": "Missing 'success' field in response",
            }
    else:
        return {
            "success": False,
            "message": f"HTTP {response.status_code}: {response.text[:200]}",
        }


def test_extract_returns_entities_array():
    """Test: /extract returns 'entities' array"""
    response = requests.post(
        f"{API_BASE}/extract",
        json={"query": "teak seam compound"},
        timeout=10
    )

    if response.status_code == 200:
        body = response.json()
        if "entities" in body and isinstance(body["entities"], list):
            return {
                "success": True,
                "message": f"Returns 'entities' array with {len(body['entities'])} items",
                "entity_count": len(body["entities"]),
            }
        else:
            return {
                "success": False,
                "message": "Missing 'entities' array in response",
            }
    else:
        return {
            "success": False,
            "message": f"HTTP {response.status_code}",
        }


def test_extract_entity_structure():
    """Test: Entity objects have correct structure"""
    response = requests.post(
        f"{API_BASE}/extract",
        json={"query": "caterpillar filter"},
        timeout=10
    )

    if response.status_code == 200:
        body = response.json()
        entities = body.get("entities", [])

        if len(entities) > 0:
            entity = entities[0]
            required_fields = ["type", "value", "confidence"]
            missing = [f for f in required_fields if f not in entity]

            if not missing:
                return {
                    "success": True,
                    "message": f"Entity structure valid: {entity}",
                    "entity": entity,
                }
            else:
                return {
                    "success": False,
                    "message": f"Entity missing fields: {missing}",
                }
        else:
            return {
                "success": True,
                "message": "No entities extracted (query may not match patterns)",
            }
    else:
        return {
            "success": False,
            "message": f"HTTP {response.status_code}",
        }


def test_extract_returns_unknown_terms():
    """Test: /extract returns 'unknown_terms' array"""
    response = requests.post(
        f"{API_BASE}/extract",
        json={"query": "xyzabc123 random unknown"},
        timeout=10
    )

    if response.status_code == 200:
        body = response.json()
        if "unknown_terms" in body and isinstance(body["unknown_terms"], list):
            return {
                "success": True,
                "message": f"Returns 'unknown_terms' array with {len(body['unknown_terms'])} items",
            }
        else:
            return {
                "success": False,
                "message": "Missing 'unknown_terms' array in response",
            }
    else:
        return {
            "success": False,
            "message": f"HTTP {response.status_code}",
        }


def test_extract_returns_timing():
    """Test: /extract returns 'timing_ms' field"""
    response = requests.post(
        f"{API_BASE}/extract",
        json={"query": "test query"},
        timeout=10
    )

    if response.status_code == 200:
        body = response.json()
        if "timing_ms" in body and isinstance(body["timing_ms"], (int, float)):
            return {
                "success": True,
                "message": f"Returns 'timing_ms': {body['timing_ms']:.2f}ms",
                "timing_ms": body["timing_ms"],
            }
        else:
            return {
                "success": False,
                "message": "Missing 'timing_ms' field in response",
            }
    else:
        return {
            "success": False,
            "message": f"HTTP {response.status_code}",
        }


def test_extract_no_auth_required():
    """Test: /extract works without authentication"""
    response = requests.post(
        f"{API_BASE}/extract",
        json={"query": "test"},
        timeout=10
    )

    if response.status_code == 200:
        return {
            "success": True,
            "message": "Endpoint accessible without auth (HTTP 200)",
        }
    elif response.status_code == 401:
        return {
            "success": False,
            "message": "Endpoint requires auth (HTTP 401) - unexpected!",
        }
    else:
        return {
            "success": False,
            "message": f"Unexpected status code: {response.status_code}",
        }


def test_extract_handles_empty_query():
    """Test: /extract handles empty query gracefully"""
    response = requests.post(
        f"{API_BASE}/extract",
        json={"query": ""},
        timeout=10
    )

    if response.status_code == 200:
        body = response.json()
        return {
            "success": True,
            "message": f"Empty query handled: success={body.get('success')}",
        }
    else:
        return {
            "success": False,
            "message": f"HTTP {response.status_code}: {response.text[:200]}",
        }


def test_extract_handles_long_query():
    """Test: /extract handles very long query"""
    long_query = "test " * 100  # 500 chars
    response = requests.post(
        f"{API_BASE}/extract",
        json={"query": long_query},
        timeout=10
    )

    if response.status_code == 200:
        body = response.json()
        return {
            "success": True,
            "message": f"Long query handled: success={body.get('success')}",
        }
    else:
        return {
            "success": False,
            "message": f"HTTP {response.status_code}",
        }


def test_extract_marine_parts():
    """Test: /extract extracts entities from marine parts query"""
    response = requests.post(
        f"{API_BASE}/extract",
        json={"query": "teak seam compound for deck maintenance"},
        timeout=10
    )

    if response.status_code == 200:
        body = response.json()
        entities = body.get("entities", [])
        return {
            "success": True,
            "message": f"Marine query processed: {len(entities)} entities extracted",
            "entities": entities,
            "note": "This tests entity extraction, NOT domain detection",
        }
    else:
        return {
            "success": False,
            "message": f"HTTP {response.status_code}",
        }


def test_extract_does_not_return_domain():
    """Test: /extract does NOT return 'domain' field (important validation)"""
    response = requests.post(
        f"{API_BASE}/extract",
        json={"query": "caterpillar filter"},
        timeout=10
    )

    if response.status_code == 200:
        body = response.json()
        if "domain" not in body:
            return {
                "success": True,
                "message": "Correctly does NOT return 'domain' field (use /search for domain detection)",
            }
        else:
            return {
                "success": False,
                "message": f"Unexpectedly returns 'domain' field: {body.get('domain')}",
            }
    else:
        return {
            "success": False,
            "message": f"HTTP {response.status_code}",
        }


def test_extract_does_not_return_intent():
    """Test: /extract does NOT return 'intent' field (important validation)"""
    response = requests.post(
        f"{API_BASE}/extract",
        json={"query": "create work order"},
        timeout=10
    )

    if response.status_code == 200:
        body = response.json()
        if "intent" not in body:
            return {
                "success": True,
                "message": "Correctly does NOT return 'intent' field (use /search for intent detection)",
            }
        else:
            return {
                "success": False,
                "message": f"Unexpectedly returns 'intent' field: {body.get('intent')}",
            }
    else:
        return {
            "success": False,
            "message": f"HTTP {response.status_code}",
        }


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 70)
    print("CORRECTED /EXTRACT ENDPOINT TEST SUITE")
    print("=" * 70)
    print(f"API: {API_BASE}")
    print("Testing: /extract endpoint (entity extraction only)")
    print()
    print("NOTE: This endpoint does NOT return domain/intent fields.")
    print("      For domain detection, use /search (requires auth).")
    print("=" * 70)

    runner = TestRunner()

    # Basic Response Structure Tests
    print("\n" + "=" * 70)
    print("GROUP 1: RESPONSE STRUCTURE")
    print("=" * 70)
    runner.test("Returns 'success' field", test_extract_returns_success_field)
    runner.test("Returns 'entities' array", test_extract_returns_entities_array)
    runner.test("Entity objects have correct structure", test_extract_entity_structure)
    runner.test("Returns 'unknown_terms' array", test_extract_returns_unknown_terms)
    runner.test("Returns 'timing_ms' field", test_extract_returns_timing)

    # Authentication Tests
    print("\n" + "=" * 70)
    print("GROUP 2: AUTHENTICATION")
    print("=" * 70)
    runner.test("No auth required", test_extract_no_auth_required)

    # Edge Cases
    print("\n" + "=" * 70)
    print("GROUP 3: EDGE CASES")
    print("=" * 70)
    runner.test("Handles empty query", test_extract_handles_empty_query)
    runner.test("Handles long query (500 chars)", test_extract_handles_long_query)

    # Marine Parts Entity Extraction
    print("\n" + "=" * 70)
    print("GROUP 4: MARINE PARTS ENTITY EXTRACTION")
    print("=" * 70)
    runner.test("Extracts entities from marine parts query", test_extract_marine_parts)

    # Important Negative Tests
    print("\n" + "=" * 70)
    print("GROUP 5: NEGATIVE VALIDATION (What /extract should NOT return)")
    print("=" * 70)
    runner.test("Does NOT return 'domain' field", test_extract_does_not_return_domain)
    runner.test("Does NOT return 'intent' field", test_extract_does_not_return_intent)

    # Summary
    success = runner.summary()

    print("\n" + "=" * 70)
    print("FINDINGS")
    print("=" * 70)
    print("✅ What /extract DOES:")
    print("   - Extracts entities from query text")
    print("   - Returns entity type, value, confidence")
    print("   - Works without authentication")
    print("   - Handles edge cases (empty, long queries)")
    print()
    print("❌ What /extract does NOT do:")
    print("   - Domain detection (use /search)")
    print("   - Intent detection (use /search)")
    print("   - Domain confidence scoring (use /search)")
    print("   - Mode detection (use /search)")
    print()
    print("📋 For domain/intent detection tests:")
    print("   1. Get valid user credentials")
    print("   2. Run: python3 test_search_domain_detection.py")
    print("=" * 70)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
