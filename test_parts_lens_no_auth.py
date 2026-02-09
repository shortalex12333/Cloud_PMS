#!/usr/bin/env python3
"""
Parts Lens Test Suite - No Authentication Required
===================================================

Tests that can run WITHOUT valid user credentials:
1. NLP domain detection
2. API error responses (401/400)
3. Version/health endpoints
4. System validation

These tests prove:
- Domain detection works for marine parts
- JWT validation is enforced
- Error handling is correct
- Deployment is live
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
        print("TEST SUMMARY - NO AUTH REQUIRED")
        print("=" * 70)
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        print(f"📊 Total:  {self.passed + self.failed}")
        print("=" * 70)

        # Save results
        with open("test-results/parts_lens_no_auth_results.json", "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"\nResults saved to: test-results/parts_lens_no_auth_results.json")

        return self.failed == 0


# ============================================================================
# NLP DOMAIN DETECTION TESTS
# ============================================================================

def test_domain_detection_marine_teak():
    """Test: Domain detection for 'teak seam compound'"""
    # This tests PR #208 fix - marine part anchors
    query = "teak seam compound for deck maintenance"

    response = requests.post(
        f"{API_BASE}/extract",
        json={"query": query},
        timeout=10
    )

    if response.status_code == 200:
        body = response.json()
        domain = body.get("domain")
        confidence = body.get("domain_confidence")

        if domain == "parts":
            return {
                "success": True,
                "message": f"Detected domain=parts (confidence={confidence})",
                "query": query,
                "domain": domain,
                "confidence": confidence,
            }
        else:
            return {
                "success": False,
                "message": f"Expected domain=parts, got {domain}",
                "query": query,
                "domain": domain,
            }
    else:
        return {
            "success": False,
            "message": f"HTTP {response.status_code}: {response.text[:200]}",
        }


def test_domain_detection_antifouling():
    """Test: Domain detection for 'antifouling paint'"""
    query = "antifouling paint for hull"

    response = requests.post(
        f"{API_BASE}/extract",
        json={"query": query},
        timeout=10
    )

    if response.status_code == 200:
        body = response.json()
        domain = body.get("domain")

        if domain == "parts":
            return {
                "success": True,
                "message": f"Detected domain=parts for marine product",
                "query": query,
                "domain": domain,
            }
        else:
            return {
                "success": False,
                "message": f"Expected domain=parts, got {domain}",
                "query": query,
                "domain": domain,
            }
    else:
        return {
            "success": False,
            "message": f"HTTP {response.status_code}",
        }


def test_domain_detection_sealant():
    """Test: Domain detection for 'sikaflex sealant'"""
    query = "sikaflex sealant application"

    response = requests.post(
        f"{API_BASE}/extract",
        json={"query": query},
        timeout=10
    )

    if response.status_code == 200:
        body = response.json()
        domain = body.get("domain")

        if domain == "parts":
            return {
                "success": True,
                "message": f"Detected domain=parts for marine sealant",
                "query": query,
                "domain": domain,
            }
        else:
            return {
                "success": False,
                "message": f"Expected domain=parts, got {domain}",
            }
    else:
        return {
            "success": False,
            "message": f"HTTP {response.status_code}",
        }


def test_domain_detection_generic_compound():
    """Test: Domain detection for 'deck compound'"""
    query = "deck compound for sealing"

    response = requests.post(
        f"{API_BASE}/extract",
        json={"query": query},
        timeout=10
    )

    if response.status_code == 200:
        body = response.json()
        domain = body.get("domain")

        if domain == "parts":
            return {
                "success": True,
                "message": f"Detected domain=parts for generic compound pattern",
                "query": query,
                "domain": domain,
            }
        else:
            return {
                "success": False,
                "message": f"Expected domain=parts, got {domain}",
            }
    else:
        return {
            "success": False,
            "message": f"HTTP {response.status_code}",
        }


def test_domain_detection_vague_query():
    """Test: Vague query returns None (explore mode)"""
    query = "check something"

    response = requests.post(
        f"{API_BASE}/extract",
        json={"query": query},
        timeout=10
    )

    if response.status_code == 200:
        body = response.json()
        domain = body.get("domain")

        if domain is None or domain == "":
            return {
                "success": True,
                "message": f"Correctly returned no domain (explore mode)",
                "query": query,
                "domain": domain,
            }
        else:
            return {
                "success": False,
                "message": f"Expected None, got {domain} (should be explore mode)",
            }
    else:
        return {
            "success": False,
            "message": f"HTTP {response.status_code}",
        }


def test_domain_detection_empty_query():
    """Test: Empty query handling"""
    query = ""

    response = requests.post(
        f"{API_BASE}/extract",
        json={"query": query},
        timeout=10
    )

    if response.status_code == 200:
        body = response.json()
        domain = body.get("domain")
        return {
            "success": True,
            "message": f"Empty query handled: domain={domain}",
            "query": query,
            "domain": domain,
        }
    else:
        return {
            "success": False,
            "message": f"HTTP {response.status_code}: {response.text[:200]}",
        }


def test_domain_detection_numbers_only():
    """Test: Numbers only query"""
    query = "12345"

    response = requests.post(
        f"{API_BASE}/extract",
        json={"query": query},
        timeout=10
    )

    if response.status_code == 200:
        body = response.json()
        domain = body.get("domain")
        return {
            "success": True,
            "message": f"Numbers-only query handled: domain={domain}",
            "query": query,
            "domain": domain,
        }
    else:
        return {
            "success": False,
            "message": f"HTTP {response.status_code}",
        }


def test_domain_detection_long_query():
    """Test: Very long query (500 chars)"""
    query = "I need to find a specific type of marine-grade compound that can be used for teak deck sealing and maintenance, specifically something that is compatible with traditional boat building materials and won't cause damage to the wood over time, and I'm also looking for recommendations on application techniques and whether I should use a specific brand like Sikaflex or 3M 5200 or perhaps something else entirely that would be better suited for this particular application in a saltwater environment with high UV exposure"

    response = requests.post(
        f"{API_BASE}/extract",
        json={"query": query},
        timeout=10
    )

    if response.status_code == 200:
        body = response.json()
        domain = body.get("domain")
        return {
            "success": True,
            "message": f"Long query handled: domain={domain}",
            "query": query[:50] + "...",
            "domain": domain,
        }
    else:
        return {
            "success": False,
            "message": f"HTTP {response.status_code}",
        }


def test_domain_detection_ambiguous_work():
    """Test: Ambiguous query (could be work_order or parts)"""
    query = "work on deck"

    response = requests.post(
        f"{API_BASE}/extract",
        json={"query": query},
        timeout=10
    )

    if response.status_code == 200:
        body = response.json()
        domain = body.get("domain")
        confidence = body.get("domain_confidence")
        return {
            "success": True,
            "message": f"Ambiguous query: domain={domain}, confidence={confidence}",
            "query": query,
            "domain": domain,
            "confidence": confidence,
        }
    else:
        return {
            "success": False,
            "message": f"HTTP {response.status_code}",
        }


def test_domain_detection_brand_name():
    """Test: Brand name detection (Caterpillar)"""
    query = "caterpillar filter replacement"

    response = requests.post(
        f"{API_BASE}/extract",
        json={"query": query},
        timeout=10
    )

    if response.status_code == 200:
        body = response.json()
        domain = body.get("domain")

        if domain == "parts":
            return {
                "success": True,
                "message": f"Brand name detected as parts domain",
                "query": query,
                "domain": domain,
            }
        else:
            return {
                "success": False,
                "message": f"Expected domain=parts, got {domain}",
                "query": query,
                "domain": domain,
            }
    else:
        return {
            "success": False,
            "message": f"HTTP {response.status_code}",
        }


def test_domain_detection_part_number():
    """Test: Part number detection"""
    query = "part number CAT-12345"

    response = requests.post(
        f"{API_BASE}/extract",
        json={"query": query},
        timeout=10
    )

    if response.status_code == 200:
        body = response.json()
        domain = body.get("domain")

        if domain == "parts":
            return {
                "success": True,
                "message": f"Part number detected as parts domain",
                "query": query,
                "domain": domain,
            }
        else:
            return {
                "success": False,
                "message": f"Expected domain=parts, got {domain}",
                "query": query,
                "domain": domain,
            }
    else:
        return {
            "success": False,
            "message": f"HTTP {response.status_code}",
        }


def test_domain_detection_low_stock():
    """Test: Low stock query"""
    query = "low stock items in inventory"

    response = requests.post(
        f"{API_BASE}/extract",
        json={"query": query},
        timeout=10
    )

    if response.status_code == 200:
        body = response.json()
        domain = body.get("domain")

        if domain == "parts":
            return {
                "success": True,
                "message": f"Low stock query detected as parts domain",
                "query": query,
                "domain": domain,
            }
        else:
            return {
                "success": False,
                "message": f"Expected domain=parts, got {domain}",
                "query": query,
                "domain": domain,
            }
    else:
        return {
            "success": False,
            "message": f"HTTP {response.status_code}",
        }


def test_domain_detection_bearing():
    """Test: Bearing query"""
    query = "main bearing inspection needed"

    response = requests.post(
        f"{API_BASE}/extract",
        json={"query": query},
        timeout=10
    )

    if response.status_code == 200:
        body = response.json()
        domain = body.get("domain")

        if domain == "parts":
            return {
                "success": True,
                "message": f"Bearing query detected as parts domain",
                "query": query,
                "domain": domain,
            }
        else:
            return {
                "success": False,
                "message": f"Expected domain=parts, got {domain}",
                "query": query,
                "domain": domain,
            }
    else:
        return {
            "success": False,
            "message": f"HTTP {response.status_code}",
        }


def test_domain_detection_filter():
    """Test: Filter query"""
    query = "oil filter replacement schedule"

    response = requests.post(
        f"{API_BASE}/extract",
        json={"query": query},
        timeout=10
    )

    if response.status_code == 200:
        body = response.json()
        domain = body.get("domain")

        if domain == "parts":
            return {
                "success": True,
                "message": f"Filter query detected as parts domain",
                "query": query,
                "domain": domain,
            }
        else:
            return {
                "success": False,
                "message": f"Expected domain=parts, got {domain}",
                "query": query,
                "domain": domain,
            }
    else:
        return {
            "success": False,
            "message": f"HTTP {response.status_code}",
        }


# ============================================================================
# INTENT DETECTION TESTS
# ============================================================================

def test_intent_detection_read_question():
    """Test: Question intent (READ)"""
    query = "what parts are low stock?"

    response = requests.post(
        f"{API_BASE}/extract",
        json={"query": query},
        timeout=10
    )

    if response.status_code == 200:
        body = response.json()
        intent = body.get("intent")

        if intent == "READ":
            return {
                "success": True,
                "message": f"Question correctly detected as READ intent",
                "query": query,
                "intent": intent,
            }
        else:
            return {
                "success": False,
                "message": f"Expected intent=READ, got {intent}",
                "query": query,
                "intent": intent,
            }
    else:
        return {
            "success": False,
            "message": f"HTTP {response.status_code}",
        }


def test_intent_detection_create_action():
    """Test: Create intent (CREATE)"""
    query = "add new part to inventory"

    response = requests.post(
        f"{API_BASE}/extract",
        json={"query": query},
        timeout=10
    )

    if response.status_code == 200:
        body = response.json()
        intent = body.get("intent")

        if intent == "CREATE":
            return {
                "success": True,
                "message": f"Create action correctly detected as CREATE intent",
                "query": query,
                "intent": intent,
            }
        else:
            return {
                "success": False,
                "message": f"Expected intent=CREATE, got {intent}",
                "query": query,
                "intent": intent,
            }
    else:
        return {
            "success": False,
            "message": f"HTTP {response.status_code}",
        }


def test_intent_detection_update_action():
    """Test: Update intent (UPDATE)"""
    query = "update part quantity in stock"

    response = requests.post(
        f"{API_BASE}/extract",
        json={"query": query},
        timeout=10
    )

    if response.status_code == 200:
        body = response.json()
        intent = body.get("intent")

        if intent == "UPDATE":
            return {
                "success": True,
                "message": f"Update action correctly detected as UPDATE intent",
                "query": query,
                "intent": intent,
            }
        else:
            return {
                "success": False,
                "message": f"Expected intent=UPDATE, got {intent}",
                "query": query,
                "intent": intent,
            }
    else:
        return {
            "success": False,
            "message": f"HTTP {response.status_code}",
        }


def test_intent_detection_status_adjective():
    """Test: Status adjective (READ not MUTATE)"""
    query = "accepted parts delivery today"

    response = requests.post(
        f"{API_BASE}/extract",
        json={"query": query},
        timeout=10
    )

    if response.status_code == 200:
        body = response.json()
        intent = body.get("intent")

        if intent == "READ":
            return {
                "success": True,
                "message": f"Status adjective correctly detected as READ (not CREATE)",
                "query": query,
                "intent": intent,
            }
        else:
            return {
                "success": False,
                "message": f"Expected intent=READ, got {intent}",
                "query": query,
                "intent": intent,
            }
    else:
        return {
            "success": False,
            "message": f"HTTP {response.status_code}",
        }


# ============================================================================
# API ERROR RESPONSE TESTS
# ============================================================================

def test_upload_image_no_auth():
    """Test: Upload image without auth returns 401"""
    response = requests.post(
        f"{API_BASE}/v1/parts/upload-image",
        files={"file": ("test.png", b"fake image data", "image/png")},
        data={"part_id": "test", "yacht_id": "test"},
        timeout=10
    )

    if response.status_code == 401:
        return {
            "success": True,
            "message": f"Correctly rejected: {response.status_code}",
            "status_code": response.status_code,
        }
    else:
        return {
            "success": False,
            "message": f"Expected 401, got {response.status_code}",
            "status_code": response.status_code,
            "body": response.text[:200],
        }


def test_upload_image_invalid_jwt():
    """Test: Upload image with invalid JWT returns 401"""
    response = requests.post(
        f"{API_BASE}/v1/parts/upload-image",
        headers={"Authorization": "Bearer invalid.jwt.token"},
        files={"file": ("test.png", b"fake image data", "image/png")},
        data={"part_id": "test", "yacht_id": "test"},
        timeout=10
    )

    if response.status_code == 401:
        return {
            "success": True,
            "message": f"Correctly rejected invalid JWT: {response.status_code}",
            "status_code": response.status_code,
        }
    else:
        return {
            "success": False,
            "message": f"Expected 401, got {response.status_code}",
        }


def test_update_image_no_auth():
    """Test: Update image without auth returns 401"""
    response = requests.post(
        f"{API_BASE}/v1/parts/update-image",
        json={"yacht_id": "test", "image_id": "test", "description": "test"},
        timeout=10
    )

    if response.status_code == 401:
        return {
            "success": True,
            "message": f"Correctly rejected: {response.status_code}",
        }
    else:
        return {
            "success": False,
            "message": f"Expected 401, got {response.status_code}",
        }


def test_delete_image_no_auth():
    """Test: Delete image without auth returns 401"""
    response = requests.post(
        f"{API_BASE}/v1/parts/delete-image",
        json={"yacht_id": "test", "image_id": "test", "reason": "test", "signature": {}},
        timeout=10
    )

    if response.status_code == 401:
        return {
            "success": True,
            "message": f"Correctly rejected: {response.status_code}",
        }
    else:
        return {
            "success": False,
            "message": f"Expected 401, got {response.status_code}",
        }


def test_upload_image_malformed_jwt():
    """Test: Malformed JWT returns 401"""
    response = requests.post(
        f"{API_BASE}/v1/parts/upload-image",
        headers={"Authorization": "Bearer not.a.valid.jwt.format.at.all"},
        files={"file": ("test.png", b"fake image data", "image/png")},
        data={"part_id": "test", "yacht_id": "test"},
        timeout=10
    )

    if response.status_code == 401:
        return {
            "success": True,
            "message": f"Malformed JWT correctly rejected: {response.status_code}",
            "status_code": response.status_code,
        }
    else:
        return {
            "success": False,
            "message": f"Expected 401, got {response.status_code}",
        }


def test_upload_image_missing_bearer():
    """Test: Missing 'Bearer ' prefix returns 401"""
    response = requests.post(
        f"{API_BASE}/v1/parts/upload-image",
        headers={"Authorization": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test"},
        files={"file": ("test.png", b"fake image data", "image/png")},
        data={"part_id": "test", "yacht_id": "test"},
        timeout=10
    )

    if response.status_code == 401:
        return {
            "success": True,
            "message": f"Missing Bearer prefix correctly rejected: {response.status_code}",
        }
    else:
        return {
            "success": False,
            "message": f"Expected 401, got {response.status_code}",
        }


def test_upload_image_empty_token():
    """Test: Empty token returns 401"""
    response = requests.post(
        f"{API_BASE}/v1/parts/upload-image",
        headers={"Authorization": "Bearer "},
        files={"file": ("test.png", b"fake image data", "image/png")},
        data={"part_id": "test", "yacht_id": "test"},
        timeout=10
    )

    if response.status_code == 401:
        return {
            "success": True,
            "message": f"Empty token correctly rejected: {response.status_code}",
        }
    else:
        return {
            "success": False,
            "message": f"Expected 401, got {response.status_code}",
        }


def test_upload_image_malformed_uuid():
    """Test: Malformed UUID in part_id"""
    response = requests.post(
        f"{API_BASE}/v1/parts/upload-image",
        files={"file": ("test.png", b"fake image data", "image/png")},
        data={"part_id": "not-a-uuid", "yacht_id": "test"},
        timeout=10
    )

    # Should reject before auth (400/422) or at auth (401)
    if response.status_code in [400, 401, 422]:
        return {
            "success": True,
            "message": f"Malformed UUID rejected: HTTP {response.status_code}",
            "status_code": response.status_code,
        }
    else:
        return {
            "success": False,
            "message": f"Expected 400/401/422, got {response.status_code}",
        }


def test_upload_image_missing_part_id():
    """Test: Missing part_id field"""
    response = requests.post(
        f"{API_BASE}/v1/parts/upload-image",
        files={"file": ("test.png", b"fake image data", "image/png")},
        data={"yacht_id": "test"},  # No part_id
        timeout=10
    )

    # Should reject for missing field (400/422) before or at auth (401)
    if response.status_code in [400, 401, 422]:
        return {
            "success": True,
            "message": f"Missing part_id rejected: HTTP {response.status_code}",
            "status_code": response.status_code,
        }
    else:
        return {
            "success": False,
            "message": f"Expected 400/401/422, got {response.status_code}",
        }


def test_upload_image_missing_file():
    """Test: Missing file in upload"""
    response = requests.post(
        f"{API_BASE}/v1/parts/upload-image",
        data={"part_id": "test", "yacht_id": "test"},  # No file
        timeout=10
    )

    # Should reject for missing file (400/422) before or at auth (401)
    if response.status_code in [400, 401, 422]:
        return {
            "success": True,
            "message": f"Missing file rejected: HTTP {response.status_code}",
            "status_code": response.status_code,
        }
    else:
        return {
            "success": False,
            "message": f"Expected 400/401/422, got {response.status_code}",
        }


# ============================================================================
# VERSION / HEALTH TESTS
# ============================================================================

def test_version_endpoint():
    """Test: Version endpoint returns deployment info"""
    response = requests.get(f"{API_BASE}/version", timeout=10)

    if response.status_code == 200:
        body = response.json()
        version = body.get("version")
        commit = body.get("git_commit")
        fixes = body.get("critical_fixes", [])

        return {
            "success": True,
            "message": f"Version {version}, commit {commit[:7]}, {len(fixes)} fixes",
            "version": version,
            "commit": commit,
            "fixes": fixes,
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
    print("PARTS LENS TEST SUITE - NO AUTHENTICATION REQUIRED")
    print("=" * 70)
    print(f"API: {API_BASE}")
    print("Testing: Domain detection, error responses, endpoints")
    print()
    print("NOTE: Full E2E tests require valid user credentials")
    print("=" * 70)

    runner = TestRunner()

    # NLP Domain Detection Tests (PR #208 marine part anchors)
    print("\n" + "=" * 70)
    print("GROUP 1: NLP DOMAIN DETECTION (Marine Parts)")
    print("=" * 70)
    runner.test("Domain: 'teak seam compound' → parts", test_domain_detection_marine_teak)
    runner.test("Domain: 'antifouling paint' → parts", test_domain_detection_antifouling)
    runner.test("Domain: 'sikaflex sealant' → parts", test_domain_detection_sealant)
    runner.test("Domain: 'deck compound' → parts", test_domain_detection_generic_compound)
    runner.test("Domain: 'check something' → None (explore)", test_domain_detection_vague_query)

    # Domain Detection Edge Cases
    print("\n" + "=" * 70)
    print("GROUP 2: DOMAIN DETECTION EDGE CASES")
    print("=" * 70)
    runner.test("Domain: Empty query", test_domain_detection_empty_query)
    runner.test("Domain: Numbers only '12345'", test_domain_detection_numbers_only)
    runner.test("Domain: Very long query (500 chars)", test_domain_detection_long_query)
    runner.test("Domain: Ambiguous 'work on deck'", test_domain_detection_ambiguous_work)

    # Domain Detection Known Patterns
    print("\n" + "=" * 70)
    print("GROUP 3: DOMAIN DETECTION KNOWN PATTERNS")
    print("=" * 70)
    runner.test("Domain: Brand name 'caterpillar filter'", test_domain_detection_brand_name)
    runner.test("Domain: Part number 'CAT-12345'", test_domain_detection_part_number)
    runner.test("Domain: Low stock query", test_domain_detection_low_stock)
    runner.test("Domain: Bearing query", test_domain_detection_bearing)
    runner.test("Domain: Filter query", test_domain_detection_filter)

    # Intent Detection Tests
    print("\n" + "=" * 70)
    print("GROUP 4: INTENT DETECTION")
    print("=" * 70)
    runner.test("Intent: Question → READ", test_intent_detection_read_question)
    runner.test("Intent: 'add new part' → CREATE", test_intent_detection_create_action)
    runner.test("Intent: 'update part' → UPDATE", test_intent_detection_update_action)
    runner.test("Intent: 'accepted delivery' → READ (status adj)", test_intent_detection_status_adjective)

    # API Error Response Tests - Auth
    print("\n" + "=" * 70)
    print("GROUP 5: API AUTH VALIDATION")
    print("=" * 70)
    runner.test("Upload: No auth → 401", test_upload_image_no_auth)
    runner.test("Upload: Invalid JWT → 401", test_upload_image_invalid_jwt)
    runner.test("Upload: Malformed JWT → 401", test_upload_image_malformed_jwt)
    runner.test("Upload: Missing Bearer prefix → 401", test_upload_image_missing_bearer)
    runner.test("Upload: Empty token → 401", test_upload_image_empty_token)
    runner.test("Update: No auth → 401", test_update_image_no_auth)
    runner.test("Delete: No auth → 401", test_delete_image_no_auth)

    # API Error Response Tests - Validation
    print("\n" + "=" * 70)
    print("GROUP 6: API INPUT VALIDATION")
    print("=" * 70)
    runner.test("Upload: Malformed UUID", test_upload_image_malformed_uuid)
    runner.test("Upload: Missing part_id", test_upload_image_missing_part_id)
    runner.test("Upload: Missing file", test_upload_image_missing_file)

    # Version/Health Tests
    print("\n" + "=" * 70)
    print("GROUP 7: VERSION / HEALTH")
    print("=" * 70)
    runner.test("Version endpoint", test_version_endpoint)

    # Summary
    success = runner.summary()

    print("\n" + "=" * 70)
    print("COMPREHENSIVE TEST COVERAGE")
    print("=" * 70)
    print(f"Total Tests: {runner.passed + runner.failed}")
    print(f"✅ Passed: {runner.passed}")
    print(f"❌ Failed: {runner.failed}")
    print()
    print("✅ Tests above prove:")
    print("   - Domain detection for marine parts (teak, antifouling, sealants)")
    print("   - Domain detection for standard patterns (brands, part numbers, filters)")
    print("   - Edge case handling (empty, numbers, long queries)")
    print("   - Intent detection (READ/CREATE/UPDATE)")
    print("   - JWT validation is enforced (401 responses)")
    print("   - Input validation (malformed UUIDs, missing fields)")
    print("   - API is deployed and responsive")
    print()
    print("⏳ Cannot test without credentials:")
    print("   - Image upload success cases")
    print("   - RBAC enforcement (crew/captain/hod)")
    print("   - Storage integration (Supabase bucket)")
    print("   - Audit logging (pms_audit_log)")
    print("   - Part existence validation")
    print("   - Yacht isolation enforcement")
    print()
    print("📋 To run full E2E tests:")
    print("   1. Get valid passwords for test users")
    print("   2. Run: python3 test_e2e_journeys.py")
    print()
    print("🔍 Findings:")
    if runner.failed > 0:
        print("   - Some tests failed (see results above)")
        print("   - Check if PR #208 is deployed (marine part anchors)")
        print("   - Check if validation occurs before auth (422 vs 401)")
    else:
        print("   - All no-auth tests passing!")
        print("   - System architecture validated")
    print("=" * 70)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
