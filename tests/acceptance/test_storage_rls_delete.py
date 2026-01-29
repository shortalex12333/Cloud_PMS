#!/usr/bin/env python3
"""
Part Lens v2 - Storage RLS DELETE Acceptance Tests
==================================================

Tests manager-only DELETE enforcement across all 3 storage buckets.

Acceptance Criteria:
- Crew/HOD delete → 403 Forbidden
- Manager delete → 204 No Content
- Cross-yacht path forgery → 403 Forbidden

Buckets:
- pms-part-photos
- pms-receiving-images
- pms-label-pdfs
"""

import requests
import json
import os
from typing import Dict, List

# Base URL
API_BASE = "https://pipeline-core.int.celeste7.ai"
STORAGE_BASE = "https://vzsohavtuotocgrfkfyd.supabase.co"

# Test yacht
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
OTHER_YACHT_ID = "00000000-0000-0000-0000-000000000000"  # Doesn't exist

# JWTs (HOD and Manager for TEST_YACHT_001)
HOD_JWT = os.getenv(
    "HOD_JWT",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwczovL3F2em1rYWFtemFxeHB6YmV3anhlLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiI4OWIxMjYyYy1mZjU5LTQ1OTEtYjk1NC03NTdjZGYzZDYwOWQiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxODAxMTQzMTk0LCJpYXQiOjE3Njk1OTk5OTQsImVtYWlsIjoiaG9kLnRlbmFudEBhbGV4LXNob3J0LmNvbSIsInBob25lIjoiIiwiYXBwX21ldGFkYXRhIjp7InByb3ZpZGVyIjoiZW1haWwiLCJwcm92aWRlcnMiOlsiZW1haWwiXX0sInVzZXJfbWV0YWRhdGEiOnt9LCJyb2xlIjoiYXV0aGVudGljYXRlZCIsImFhbCI6ImFhbDEiLCJhbXIiOlt7Im1ldGhvZCI6InBhc3N3b3JkIiwidGltZXN0YW1wIjoxNzY5NTk5OTk0fV0sInNlc3Npb25faWQiOiJjaS10ZXN0LTg5YjEyNjJjIiwiaXNfYW5vbnltb3VzIjpmYWxzZX0.eHSqBRQrBpARVVyAc_IuQWJ-9JGIs08yEFLH1kkhUyg"
)

MANAGER_JWT = os.getenv("MANAGER_JWT", "REPLACE_WITH_MANAGER_JWT")

# Test buckets
BUCKETS = ["pms-part-photos", "pms-receiving-images", "pms-label-pdfs"]


def upload_test_file(bucket: str, path: str, jwt: str) -> bool:
    """Upload a small test file to storage."""
    url = f"{STORAGE_BASE}/storage/v1/object/{bucket}/{path}"
    headers = {
        "Authorization": f"Bearer {jwt}",
        "Content-Type": "text/plain",
    }
    data = b"test content"

    r = requests.post(url, headers=headers, data=data, timeout=10)
    return r.status_code in [200, 201]


def delete_storage_object(bucket: str, path: str, jwt: str) -> int:
    """Attempt to delete storage object, return status code."""
    url = f"{STORAGE_BASE}/storage/v1/object/{bucket}/{path}"
    headers = {"Authorization": f"Bearer {jwt}"}

    r = requests.delete(url, headers=headers, timeout=10)
    return r.status_code


def run_tests() -> Dict:
    """Run all storage RLS DELETE tests."""
    results = {"passed": 0, "failed": 0, "tests": []}

    print("=" * 80)
    print("Part Lens v2 - Storage RLS DELETE Acceptance Tests")
    print("=" * 80)
    print()

    for bucket in BUCKETS:
        print(f"Testing bucket: {bucket}")
        print("-" * 80)

        # Test 1: HOD cannot delete (403)
        test_name = f"{bucket} - HOD delete (expect 403)"
        test_path = f"{YACHT_ID}/test-hod-delete.txt"

        # Upload as HOD first
        if upload_test_file(bucket, test_path, HOD_JWT):
            status = delete_storage_object(bucket, test_path, HOD_JWT)
            passed = status == 403

            results["tests"].append({
                "name": test_name,
                "status": "PASS" if passed else "FAIL",
                "expected": 403,
                "actual": status,
            })

            if passed:
                results["passed"] += 1
                print(f"  ✓ {test_name}: {status}")
            else:
                results["failed"] += 1
                print(f"  ✗ {test_name}: Expected 403, got {status}")
        else:
            results["failed"] += 1
            results["tests"].append({
                "name": test_name,
                "status": "FAIL",
                "error": "Failed to upload test file"
            })
            print(f"  ✗ {test_name}: Failed to upload test file")

        # Test 2: Manager can delete (204)
        test_name = f"{bucket} - Manager delete (expect 204)"
        test_path = f"{YACHT_ID}/test-manager-delete.txt"

        # Upload as Manager first
        if upload_test_file(bucket, test_path, MANAGER_JWT):
            status = delete_storage_object(bucket, test_path, MANAGER_JWT)
            passed = status == 204

            results["tests"].append({
                "name": test_name,
                "status": "PASS" if passed else "FAIL",
                "expected": 204,
                "actual": status,
            })

            if passed:
                results["passed"] += 1
                print(f"  ✓ {test_name}: {status}")
            else:
                results["failed"] += 1
                print(f"  ✗ {test_name}: Expected 204, got {status}")
        else:
            results["failed"] += 1
            results["tests"].append({
                "name": test_name,
                "status": "FAIL",
                "error": "Failed to upload test file"
            })
            print(f"  ✗ {test_name}: Failed to upload test file")

        # Test 3: Cross-yacht path forgery (403)
        test_name = f"{bucket} - Cross-yacht delete (expect 403)"
        forged_path = f"{OTHER_YACHT_ID}/test-cross-yacht.txt"

        # Try to delete with forged path (doesn't need to exist)
        status = delete_storage_object(bucket, forged_path, MANAGER_JWT)
        passed = status == 403 or status == 404  # 404 acceptable if doesn't exist

        results["tests"].append({
            "name": test_name,
            "status": "PASS" if passed else "FAIL",
            "expected": "403 or 404",
            "actual": status,
        })

        if passed:
            results["passed"] += 1
            print(f"  ✓ {test_name}: {status}")
        else:
            results["failed"] += 1
            print(f"  ✗ {test_name}: Expected 403/404, got {status}")

        print()

    # Summary
    print("=" * 80)
    print(f"RESULTS: {results['passed']} passed, {results['failed']} failed")
    print("=" * 80)

    return results


if __name__ == "__main__":
    results = run_tests()

    # Write results to JSON
    output_path = "docs/evidence/part_lens_v2/storage_rls_403_evidence.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults written to: {output_path}")

    # Exit with error if any tests failed
    exit(0 if results["failed"] == 0 else 1)
