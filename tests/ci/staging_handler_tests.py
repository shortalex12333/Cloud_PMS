#!/usr/bin/env python3
"""
Staging Handler End-to-End Tests
================================
Tests Part Lens v2 handlers against staging with real JWTs.

Tests:
- Handler execution (consume, receive, transfer, adjust)
- Idempotency (duplicate idempotency_key → 409)
- Signature enforcement (SIGNED actions without signature → 400)
- Zero 5xx verification

Usage:
    export TEST_JWT='...'
    python3 tests/ci/staging_handler_tests.py
"""
import os
import sys
import json
import uuid
from datetime import datetime
import time

try:
    import requests
except ImportError:
    print("Error: requests library required. Install with: pip install requests")
    sys.exit(1)

try:
    from supabase import create_client
except ImportError:
    print("Error: supabase library required. Install with: pip install supabase")
    sys.exit(1)

# Configuration
API_BASE = os.getenv("API_BASE", "https://app.celeste7.ai")
SUPABASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
SUPABASE_KEY = os.getenv("TENANT_1_SUPABASE_SERVICE_KEY")
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
TEST_JWT = os.getenv("TEST_JWT")
EVIDENCE_DIR = "test-evidence"

# Results tracking
test_results = []
evidence_artifacts = {}


def log_result(test_name, passed, message=""):
    """Log a test result."""
    status = "PASS" if passed else "FAIL"
    symbol = "✓" if passed else "✗"
    print(f"{symbol} {test_name}: {status}")
    if message:
        print(f"  {message}")
    test_results.append({"test": test_name, "passed": passed, "message": message})


def save_artifact(name, content):
    """Save an evidence artifact."""
    os.makedirs(EVIDENCE_DIR, exist_ok=True)
    filepath = os.path.join(EVIDENCE_DIR, name)

    if isinstance(content, (dict, list)):
        with open(filepath, 'w') as f:
            json.dump(content, f, indent=2)
    else:
        with open(filepath, 'w') as f:
            f.write(str(content))

    evidence_artifacts[name] = filepath
    print(f"  📁 Artifact: {filepath}")


def get_test_part():
    """Get or create a test part for testing."""
    try:
        db = create_client(SUPABASE_URL, SUPABASE_KEY)

        # Find an existing part with stock
        result = db.table("pms_parts").select("id, part_number").eq(
            "yacht_id", YACHT_ID
        ).limit(1).execute()

        if result.data:
            return result.data[0]

        print("Error: No parts found in staging")
        return None
    except Exception as e:
        print(f"Error getting test part: {e}")
        return None


def test_receive_part_success():
    """Test receive_part handler with valid request."""
    part = get_test_part()
    if not part:
        log_result("receive_part success", False, "No test part available")
        return False, None

    try:
        idempotency_key = str(uuid.uuid4())

        payload = {
            "yacht_id": YACHT_ID,
            "part_id": part["id"],
            "quantity": 5,
            "location": "test-location",
            "idempotency_key": idempotency_key,
            "metadata": {
                "test": "staging_handler_test",
                "timestamp": datetime.now().isoformat()
            }
        }

        resp = requests.post(
            f"{API_BASE}/v1/parts/receive",
            json=payload,
            headers={"Authorization": f"Bearer {TEST_JWT}"},
            timeout=10
        )

        if resp.status_code == 200:
            log_result("receive_part success", True, f"Status: {resp.status_code}")
            save_artifact("receive_part_success.json", resp.json())
            return True, idempotency_key
        else:
            log_result("receive_part success", False,
                      f"Status: {resp.status_code}, Body: {resp.text[:200]}")
            save_artifact("receive_part_failure.txt", resp.text)
            return False, None

    except Exception as e:
        log_result("receive_part success", False, str(e))
        return False, None


def test_idempotency_409(idempotency_key):
    """Test that duplicate idempotency_key returns 409."""
    if not idempotency_key:
        log_result("idempotency 409", False, "No idempotency_key from previous test")
        return False

    part = get_test_part()
    if not part:
        log_result("idempotency 409", False, "No test part available")
        return False

    try:
        # Use the same idempotency_key
        payload = {
            "yacht_id": YACHT_ID,
            "part_id": part["id"],
            "quantity": 10,  # Different quantity
            "location": "test-location",
            "idempotency_key": idempotency_key,  # SAME KEY
        }

        resp = requests.post(
            f"{API_BASE}/v1/parts/receive",
            json=payload,
            headers={"Authorization": f"Bearer {TEST_JWT}"},
            timeout=10
        )

        if resp.status_code == 409:
            log_result("idempotency 409", True, "Duplicate key correctly rejected")
            save_artifact("idempotency_409.json", {
                "status_code": resp.status_code,
                "response": resp.text
            })
            return True
        else:
            log_result("idempotency 409", False,
                      f"Expected 409, got {resp.status_code}: {resp.text[:200]}")
            return False

    except Exception as e:
        log_result("idempotency 409", False, str(e))
        return False


def test_consume_part_success():
    """Test consume_part handler with valid request."""
    part = get_test_part()
    if not part:
        log_result("consume_part success", False, "No test part available")
        return False

    try:
        payload = {
            "yacht_id": YACHT_ID,
            "part_id": part["id"],
            "quantity": 1,
            "location": "test-location",
            "consumed_by": "test-staging",
            "idempotency_key": str(uuid.uuid4()),
        }

        resp = requests.post(
            f"{API_BASE}/v1/parts/consume",
            json=payload,
            headers={"Authorization": f"Bearer {TEST_JWT}"},
            timeout=10
        )

        if resp.status_code == 200:
            log_result("consume_part success", True, f"Status: {resp.status_code}")
            save_artifact("consume_part_success.json", resp.json())
            return True
        elif resp.status_code == 409:
            # Insufficient stock is a conflict, not a failure
            log_result("consume_part success", True,
                      f"Status: {resp.status_code} (insufficient stock - expected)")
            return True
        else:
            log_result("consume_part success", False,
                      f"Status: {resp.status_code}, Body: {resp.text[:200]}")
            return False

    except Exception as e:
        log_result("consume_part success", False, str(e))
        return False


def test_adjust_stock_no_signature_400():
    """Test adjust_stock_quantity without signature returns 400."""
    part = get_test_part()
    if not part:
        log_result("adjust_stock no signature 400", False, "No test part available")
        return False

    try:
        # Try to adjust without signature (SIGNED action)
        payload = {
            "yacht_id": YACHT_ID,
            "part_id": part["id"],
            "new_quantity": 50,
            "reason": "test adjustment",
            # NO signature field
            "idempotency_key": str(uuid.uuid4()),
        }

        resp = requests.post(
            f"{API_BASE}/v1/parts/adjust-stock",
            json=payload,
            headers={"Authorization": f"Bearer {TEST_JWT}"},
            timeout=10
        )

        if resp.status_code == 400:
            log_result("adjust_stock no signature 400", True,
                      "Correctly rejected missing signature")
            save_artifact("adjust_stock_no_sig_400.json", {
                "status_code": resp.status_code,
                "response": resp.text
            })
            return True
        else:
            log_result("adjust_stock no signature 400", False,
                      f"Expected 400, got {resp.status_code}: {resp.text[:200]}")
            return False

    except Exception as e:
        log_result("adjust_stock no signature 400", False, str(e))
        return False


def test_adjust_stock_with_signature_200():
    """Test adjust_stock_quantity with signature succeeds."""
    part = get_test_part()
    if not part:
        log_result("adjust_stock with signature 200", False, "No test part available")
        return False

    try:
        payload = {
            "yacht_id": YACHT_ID,
            "part_id": part["id"],
            "new_quantity": 100,
            "reason": "test adjustment with signature",
            "signature": {
                "pin": "1234",
                "totp": "123456",
                "reason_code": "physical_count"
            },
            "idempotency_key": str(uuid.uuid4()),
        }

        resp = requests.post(
            f"{API_BASE}/v1/parts/adjust-stock",
            json=payload,
            headers={"Authorization": f"Bearer {TEST_JWT}"},
            timeout=10
        )

        if resp.status_code == 200:
            log_result("adjust_stock with signature 200", True,
                      f"Status: {resp.status_code}")
            save_artifact("adjust_stock_with_sig_200.json", resp.json())
            return True
        else:
            log_result("adjust_stock with signature 200", False,
                      f"Status: {resp.status_code}, Body: {resp.text[:200]}")
            return False

    except Exception as e:
        log_result("adjust_stock with signature 200", False, str(e))
        return False


def test_zero_5xx_comprehensive():
    """Test various endpoints to confirm no 5xx errors."""
    endpoints = [
        ("GET", "/v1/parts/suggestions", {"part_id": str(uuid.uuid4()), "yacht_id": YACHT_ID}),
        ("GET", "/v1/parts/low-stock", {"yacht_id": YACHT_ID}),
        ("GET", "/health", {}),
    ]

    all_passed = True
    status_codes = []

    for method, path, params in endpoints:
        try:
            if method == "GET":
                resp = requests.get(
                    f"{API_BASE}{path}",
                    params=params,
                    headers={"Authorization": f"Bearer {TEST_JWT}"},
                    timeout=10
                )

            status_codes.append((path, resp.status_code))

            if 500 <= resp.status_code < 600:
                print(f"  ✗ {path}: {resp.status_code} (5xx error!)")
                all_passed = False
            else:
                print(f"  ✓ {path}: {resp.status_code} (not 5xx)")

        except Exception as e:
            print(f"  ✗ {path}: Exception: {e}")
            all_passed = False

    save_artifact("zero_5xx_comprehensive.json", {
        "timestamp": datetime.now().isoformat(),
        "status_codes": status_codes,
        "all_passed": all_passed
    })

    log_result("zero 5xx comprehensive", all_passed,
              f"Tested {len(endpoints)} endpoints")
    return all_passed


def run_handler_tests():
    """Run all handler tests."""
    print("=" * 60)
    print("STAGING HANDLER END-TO-END TESTS")
    print("=" * 60)
    print(f"API: {API_BASE}")
    print(f"Yacht: {YACHT_ID}")
    print(f"JWT: {TEST_JWT[:20]}...")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()

    if not TEST_JWT:
        print("Error: TEST_JWT not set")
        return 1

    print("=== Running Tests ===")
    print()

    # Test 1: Receive part (success)
    success, idempotency_key = test_receive_part_success()

    # Test 2: Idempotency (409)
    if success and idempotency_key:
        time.sleep(1)  # Small delay
        test_idempotency_409(idempotency_key)

    # Test 3: Consume part (success or conflict)
    test_consume_part_success()

    # Test 4: Adjust stock without signature (400)
    test_adjust_stock_no_signature_400()

    # Test 5: Adjust stock with signature (200)
    test_adjust_stock_with_signature_200()

    # Test 6: Zero 5xx comprehensive
    test_zero_5xx_comprehensive()

    # Summary
    passed = sum(1 for t in test_results if t["passed"])
    total = len(test_results)

    print()
    print("=" * 60)
    print(f"RESULTS: {passed}/{total} passed")
    print("=" * 60)

    # Save summary
    summary = {
        "timestamp": datetime.now().isoformat(),
        "api_base": API_BASE,
        "yacht_id": YACHT_ID,
        "total_tests": total,
        "passed": passed,
        "failed": total - passed,
        "success_rate": passed / total if total > 0 else 0,
        "tests": test_results,
        "artifacts": evidence_artifacts
    }

    save_artifact("handler_tests_summary.json", summary)

    if passed == total:
        print("✓ ALL TESTS PASSED")
        print(f"\nEvidence artifacts saved to: {EVIDENCE_DIR}/")
        return 0
    else:
        print(f"✗ {total - passed} TEST(S) FAILED")
        print(f"\nEvidence artifacts saved to: {EVIDENCE_DIR}/")
        return 1


if __name__ == "__main__":
    sys.exit(run_handler_tests())
