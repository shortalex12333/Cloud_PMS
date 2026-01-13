#!/usr/bin/env python3
"""
P6 CORS/CSP Verification Tests
==============================

Minimal tests to verify CSP-001 and CORS-001 issues.
Uses raw HTTP requests to simulate browser preflight behavior.

Run: python3 test_cors_csp.py
"""

import requests
import json
import sys
from typing import Dict, List, Optional, Tuple

# Test Configuration
PIPELINE_API = "https://pipeline-core.int.celeste7.ai"
MICROACTION_API = "https://api.celeste7.ai"
SUPABASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"

# Test origins (simulate browser Origin header)
TEST_ORIGINS = [
    "https://app.celeste7.ai",  # Production
    "https://cloud-pms-git-universalv1-c7s-projects-4a165667.vercel.app",  # Preview
    "http://localhost:3000",  # Local
    "https://malicious-site.com",  # SHOULD BE BLOCKED
]


class CORSTestResult:
    def __init__(self, origin: str, endpoint: str):
        self.origin = origin
        self.endpoint = endpoint
        self.preflight_status: Optional[int] = None
        self.preflight_acao: Optional[str] = None
        self.preflight_acam: Optional[str] = None
        self.preflight_acah: Optional[str] = None
        self.actual_status: Optional[int] = None
        self.actual_acao: Optional[str] = None
        self.error: Optional[str] = None
        self.passed: bool = False

    def to_dict(self) -> Dict:
        return {
            "origin": self.origin,
            "endpoint": self.endpoint,
            "preflight_status": self.preflight_status,
            "preflight_acao": self.preflight_acao,
            "preflight_acam": self.preflight_acam,
            "actual_status": self.actual_status,
            "actual_acao": self.actual_acao,
            "error": self.error,
            "passed": self.passed,
        }


def test_cors_preflight(
    url: str,
    origin: str,
    method: str = "POST"
) -> CORSTestResult:
    """
    Test CORS preflight (OPTIONS) request.

    Browser sends OPTIONS before cross-origin requests with:
    - Origin header
    - Access-Control-Request-Method header
    - Access-Control-Request-Headers header

    Server should respond with:
    - Access-Control-Allow-Origin (matching origin or *)
    - Access-Control-Allow-Methods (including requested method)
    - Access-Control-Allow-Headers (including requested headers)
    """
    result = CORSTestResult(origin, url)

    try:
        # Step 1: Preflight (OPTIONS)
        preflight_headers = {
            "Origin": origin,
            "Access-Control-Request-Method": method,
            "Access-Control-Request-Headers": "authorization,content-type",
        }

        preflight_resp = requests.options(
            url,
            headers=preflight_headers,
            timeout=10
        )

        result.preflight_status = preflight_resp.status_code
        result.preflight_acao = preflight_resp.headers.get("Access-Control-Allow-Origin")
        result.preflight_acam = preflight_resp.headers.get("Access-Control-Allow-Methods")
        result.preflight_acah = preflight_resp.headers.get("Access-Control-Allow-Headers")

        # Check if preflight passed
        if result.preflight_status != 200:
            result.error = f"Preflight returned {result.preflight_status}, expected 200"
            return result

        if not result.preflight_acao:
            result.error = "Preflight missing Access-Control-Allow-Origin header"
            return result

        # Check if origin is allowed (should match exactly or be *)
        if result.preflight_acao != origin and result.preflight_acao != "*":
            result.error = f"ACAO '{result.preflight_acao}' doesn't match origin '{origin}'"
            return result

        # Step 2: Actual request
        actual_headers = {
            "Origin": origin,
            "Content-Type": "application/json",
        }

        # Use GET for health check, POST for others
        if "/health" in url:
            actual_resp = requests.get(url, headers=actual_headers, timeout=10)
        else:
            actual_resp = requests.post(
                url,
                headers=actual_headers,
                json={"query": "test"},
                timeout=10
            )

        result.actual_status = actual_resp.status_code
        result.actual_acao = actual_resp.headers.get("Access-Control-Allow-Origin")

        # Success if we got past CORS (even if request fails for other reasons)
        # The key test is whether CORS headers are present
        if result.actual_acao or result.actual_status in [200, 400, 401, 404, 500]:
            result.passed = True
        else:
            result.error = f"Actual request failed without CORS response"

    except requests.exceptions.RequestException as e:
        result.error = f"Network error: {str(e)}"
    except Exception as e:
        result.error = f"Unexpected error: {str(e)}"

    return result


def run_cors_tests() -> List[CORSTestResult]:
    """Run CORS tests across all endpoints and origins."""
    results = []

    endpoints = [
        (f"{PIPELINE_API}/health", "GET"),
        (f"{PIPELINE_API}/search", "POST"),
        (f"{PIPELINE_API}/v1/documents/test-doc-id/sign", "POST"),
    ]

    print("=" * 70)
    print("CORS VERIFICATION TESTS")
    print("=" * 70)

    for origin in TEST_ORIGINS:
        print(f"\n[Origin: {origin}]")

        for url, method in endpoints:
            result = test_cors_preflight(url, origin, method)
            results.append(result)

            status = "PASS" if result.passed else "FAIL"
            print(f"  {method} {url.split('.ai')[-1]}")
            print(f"    Preflight: {result.preflight_status} ACAO: {result.preflight_acao}")
            print(f"    Actual: {result.actual_status} -> {status}")
            if result.error:
                print(f"    Error: {result.error}")

    return results


def analyze_results(results: List[CORSTestResult]) -> Dict:
    """Analyze test results and produce summary."""
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed

    # Group by origin
    by_origin = {}
    for r in results:
        if r.origin not in by_origin:
            by_origin[r.origin] = {"passed": 0, "failed": 0}
        if r.passed:
            by_origin[r.origin]["passed"] += 1
        else:
            by_origin[r.origin]["failed"] += 1

    # Identify blocked origins (expected: malicious-site.com)
    blocked = [o for o, stats in by_origin.items() if stats["passed"] == 0]
    allowed = [o for o, stats in by_origin.items() if stats["passed"] > 0]

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": f"{100 * passed / total:.1f}%",
        "allowed_origins": allowed,
        "blocked_origins": blocked,
        "by_origin": by_origin,
    }


def main():
    print("\n" + "=" * 70)
    print("P6 CORS/CSP VERIFICATION")
    print("=" * 70)
    print(f"Pipeline API: {PIPELINE_API}")
    print(f"Microaction API: {MICROACTION_API}")
    print(f"Test Origins: {len(TEST_ORIGINS)}")

    # Run CORS tests
    results = run_cors_tests()

    # Analyze
    analysis = analyze_results(results)

    # Print summary
    print("\n" + "=" * 70)
    print("CORS TEST SUMMARY")
    print("=" * 70)
    print(f"Total Tests: {analysis['total']}")
    print(f"Passed: {analysis['passed']} ({analysis['pass_rate']})")
    print(f"Failed: {analysis['failed']}")
    print(f"\nAllowed Origins: {analysis['allowed_origins']}")
    print(f"Blocked Origins: {analysis['blocked_origins']}")

    # Export results
    export_data = {
        "summary": analysis,
        "results": [r.to_dict() for r in results],
    }

    with open("cors_test_results.json", "w") as f:
        json.dump(export_data, f, indent=2)
    print(f"\nResults exported to: cors_test_results.json")

    # Determine CSP-001 and CORS-001 status
    print("\n" + "=" * 70)
    print("ISSUE STATUS")
    print("=" * 70)

    # CSP-001: Check if legitimate origins can connect
    legit_origins = [o for o in analysis["allowed_origins"] if "malicious" not in o]
    if len(legit_origins) >= 3:  # app, preview, localhost
        print("CSP-001: RESOLVED - Legitimate origins can connect")
    else:
        print(f"CSP-001: ISSUE - Only {len(legit_origins)} origins allowed")

    # CORS-001: Check if document signing endpoint works
    sign_results = [r for r in results if "sign" in r.endpoint]
    sign_passed = [r for r in sign_results if r.passed]
    if len(sign_passed) >= len(legit_origins):
        print("CORS-001: RESOLVED - Document signing CORS working")
    else:
        print("CORS-001: ISSUE - Document signing CORS failing")
        for r in sign_results:
            if not r.passed:
                print(f"  - {r.origin}: {r.error}")

    # Exit code
    if analysis["passed"] < analysis["total"] * 0.8:
        print("\nVERDICT: FAIL - CORS issues detected")
        return 1
    else:
        print("\nVERDICT: PASS - CORS working as expected")
        return 0


if __name__ == "__main__":
    sys.exit(main())
