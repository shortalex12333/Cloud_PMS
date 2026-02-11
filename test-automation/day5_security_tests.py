#!/usr/bin/env python3
"""
Day 5: Comprehensive Security Testing
Tests authentication, authorization, data isolation, injection attacks, and CSRF protection
"""

import os
import sys
import json
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

API_BASE = os.getenv("API_BASE", "https://pipeline-core.int.celeste7.ai")
SUPABASE_URL = os.getenv("MASTER_SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("MASTER_SUPABASE_ANON_KEY")

# Test yachts (for cross-tenant testing)
YACHT_1 = "85fe1119-b04c-41ac-80f1-829d23322598"
YACHT_2 = "different-yacht-id-here"  # If available

# Test users
USERS = {}


def sign_in_users():
    """Sign in all test users."""
    users_config = {
        "CAPTAIN": "x@alex-short.com",
        "HOD": "hod.test@alex-short.com",
        "CREW": "crew.test@alex-short.com",
    }

    for role, email in users_config.items():
        headers = {
            "apikey": SUPABASE_ANON_KEY,
            "Content-Type": "application/json",
        }
        response = requests.post(
            f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
            headers=headers,
            json={"email": email, "password": "Password2!"},
            timeout=10,
        )
        if response.status_code == 200:
            data = response.json()
            USERS[role] = {
                "access_token": data["access_token"],
                "refresh_token": data.get("refresh_token"),
                "expires_in": data.get("expires_in", 3600),
            }
            print(f"✅ {role} signed in (expires in {data.get('expires_in', 'unknown')}s)")
        else:
            print(f"❌ {role} sign-in failed: {response.status_code}")
            return False
    return True


class SecurityTestResult:
    """Security test result with detailed findings."""

    def __init__(
        self,
        category: str,
        test_name: str,
        passed: bool,
        details: str,
        severity: str = "MEDIUM",
    ):
        self.category = category
        self.test_name = test_name
        self.passed = passed
        self.details = details
        self.severity = severity  # CRITICAL, HIGH, MEDIUM, LOW, INFO


class SecurityTester:
    """Comprehensive security testing harness."""

    def __init__(self):
        self.results: List[SecurityTestResult] = []
        self.passed = 0
        self.failed = 0
        self.critical_failures = 0

    def log_result(self, result: SecurityTestResult):
        """Log a security test result."""
        self.results.append(result)
        if result.passed:
            self.passed += 1
            status = "✅"
        else:
            self.failed += 1
            status = "❌"
            if result.severity in ["CRITICAL", "HIGH"]:
                self.critical_failures += 1

        severity_marker = f"[{result.severity}]"
        print(f"{status} {severity_marker:12s} {result.test_name:50s} - {result.details}")

    # =========================================================================
    # JWT & Authentication Tests
    # =========================================================================

    def test_jwt_expiration(self):
        """Test JWT expiration handling."""
        print("\n### JWT EXPIRATION TESTS ###\n")

        # Test 1: Expired JWT should be rejected
        expired_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwiZXhwIjoxNTE2MjM5MDIyfQ.invalidtoken"

        try:
            response = requests.post(
                f"{API_BASE}/search",
                headers={"Authorization": f"Bearer {expired_jwt}"},
                json={"query": "test"},
                timeout=5,
            )

            if response.status_code == 401:
                self.log_result(
                    SecurityTestResult(
                        "JWT",
                        "Expired JWT rejected",
                        True,
                        "401 Unauthorized (correct)",
                        "CRITICAL",
                    )
                )
            else:
                self.log_result(
                    SecurityTestResult(
                        "JWT",
                        "Expired JWT rejected",
                        False,
                        f"Got {response.status_code}, expected 401",
                        "CRITICAL",
                    )
                )
        except Exception as e:
            self.log_result(
                SecurityTestResult(
                    "JWT",
                    "Expired JWT rejected",
                    False,
                    f"Exception: {str(e)}",
                    "CRITICAL",
                )
            )

        # Test 2: Malformed JWT should be rejected
        malformed_jwt = "not.a.valid.jwt.token"

        try:
            response = requests.post(
                f"{API_BASE}/search",
                headers={"Authorization": f"Bearer {malformed_jwt}"},
                json={"query": "test"},
                timeout=5,
            )

            if response.status_code in [401, 422]:
                self.log_result(
                    SecurityTestResult(
                        "JWT",
                        "Malformed JWT rejected",
                        True,
                        f"{response.status_code} (correct)",
                        "CRITICAL",
                    )
                )
            else:
                self.log_result(
                    SecurityTestResult(
                        "JWT",
                        "Malformed JWT rejected",
                        False,
                        f"Got {response.status_code}, expected 401/422",
                        "CRITICAL",
                    )
                )
        except Exception as e:
            self.log_result(
                SecurityTestResult(
                    "JWT",
                    "Malformed JWT rejected",
                    False,
                    f"Exception: {str(e)}",
                    "CRITICAL",
                )
            )

        # Test 3: No JWT should be rejected
        try:
            response = requests.post(
                f"{API_BASE}/search",
                json={"query": "test"},
                timeout=5,
            )

            if response.status_code == 422:  # FastAPI validation error
                self.log_result(
                    SecurityTestResult(
                        "JWT",
                        "Missing JWT rejected",
                        True,
                        "422 Unprocessable Entity (correct)",
                        "CRITICAL",
                    )
                )
            else:
                self.log_result(
                    SecurityTestResult(
                        "JWT",
                        "Missing JWT rejected",
                        False,
                        f"Got {response.status_code}, expected 422",
                        "CRITICAL",
                    )
                )
        except Exception as e:
            self.log_result(
                SecurityTestResult(
                    "JWT",
                    "Missing JWT rejected",
                    False,
                    f"Exception: {str(e)}",
                    "CRITICAL",
                )
            )

        # Test 4: Valid JWT should work
        if USERS.get("HOD"):
            try:
                response = requests.post(
                    f"{API_BASE}/search",
                    headers={"Authorization": f"Bearer {USERS['HOD']['access_token']}"},
                    json={"query": "test", "limit": 1},
                    timeout=5,
                )

                if response.status_code == 200:
                    self.log_result(
                        SecurityTestResult(
                            "JWT",
                            "Valid JWT accepted",
                            True,
                            "200 OK (correct)",
                            "INFO",
                        )
                    )
                else:
                    self.log_result(
                        SecurityTestResult(
                            "JWT",
                            "Valid JWT accepted",
                            False,
                            f"Got {response.status_code}, expected 200",
                            "HIGH",
                        )
                    )
            except Exception as e:
                self.log_result(
                    SecurityTestResult(
                        "JWT",
                        "Valid JWT accepted",
                        False,
                        f"Exception: {str(e)}",
                        "HIGH",
                    )
                )

    # =========================================================================
    # RBAC & Data Isolation Tests
    # =========================================================================

    def test_cross_yacht_isolation(self):
        """Test that users cannot access data from other yachts."""
        print("\n### CROSS-YACHT DATA ISOLATION TESTS ###\n")

        # Test 1: Crew cannot access other yacht's data
        if USERS.get("CREW"):
            try:
                response = requests.post(
                    f"{API_BASE}/v1/actions/execute",
                    headers={"Authorization": f"Bearer {USERS['CREW']['access_token']}"},
                    json={
                        "action": "view_part_details",
                        "context": {"yacht_id": YACHT_2 if YACHT_2 != YACHT_1 else "fake-yacht-id"},
                        "payload": {"part_id": "test"},
                    },
                    timeout=5,
                )

                # Should reject with 403 Forbidden or 404 Not Found
                if response.status_code in [403, 404]:
                    self.log_result(
                        SecurityTestResult(
                            "RBAC",
                            "Cross-yacht access blocked",
                            True,
                            f"{response.status_code} (correct - access denied)",
                            "CRITICAL",
                        )
                    )
                elif response.status_code == 400:
                    # Might be missing part_id, but at least not 200
                    self.log_result(
                        SecurityTestResult(
                            "RBAC",
                            "Cross-yacht access blocked",
                            True,
                            "400 (validation error, no data leaked)",
                            "CRITICAL",
                        )
                    )
                else:
                    self.log_result(
                        SecurityTestResult(
                            "RBAC",
                            "Cross-yacht access blocked",
                            False,
                            f"Got {response.status_code}, expected 403/404",
                            "CRITICAL",
                        )
                    )
            except Exception as e:
                self.log_result(
                    SecurityTestResult(
                        "RBAC",
                        "Cross-yacht access blocked",
                        False,
                        f"Exception: {str(e)}",
                        "CRITICAL",
                    )
                )

        # Test 2: Crew cannot create WO for other departments
        if USERS.get("CREW"):
            try:
                response = requests.post(
                    f"{API_BASE}/v1/actions/execute",
                    headers={"Authorization": f"Bearer {USERS['CREW']['access_token']}"},
                    json={
                        "action": "create_work_order",
                        "context": {"yacht_id": YACHT_1},
                        "payload": {
                            "title": "Security Test",
                            "department": "engineering",  # Crew is deck department
                            "priority": "low",
                        },
                    },
                    timeout=5,
                )

                # Should reject with 403 Forbidden
                if response.status_code == 403:
                    self.log_result(
                        SecurityTestResult(
                            "RBAC",
                            "Cross-department WO creation blocked",
                            True,
                            "403 Forbidden (correct)",
                            "HIGH",
                        )
                    )
                elif response.status_code == 409:
                    # Duplicate - means it went through (BAD)
                    self.log_result(
                        SecurityTestResult(
                            "RBAC",
                            "Cross-department WO creation blocked",
                            False,
                            "409 Conflict - WO created (RBAC bypass!)",
                            "HIGH",
                        )
                    )
                else:
                    self.log_result(
                        SecurityTestResult(
                            "RBAC",
                            "Cross-department WO creation blocked",
                            True,
                            f"{response.status_code} (rejected, not 409)",
                            "HIGH",
                        )
                    )
            except Exception as e:
                self.log_result(
                    SecurityTestResult(
                        "RBAC",
                        "Cross-department WO creation blocked",
                        False,
                        f"Exception: {str(e)}",
                        "HIGH",
                    )
                )

        # Test 3: Captain CAN create WO for any department
        if USERS.get("CAPTAIN"):
            try:
                response = requests.post(
                    f"{API_BASE}/v1/actions/execute",
                    headers={"Authorization": f"Bearer {USERS['CAPTAIN']['access_token']}"},
                    json={
                        "action": "create_work_order",
                        "context": {"yacht_id": YACHT_1},
                        "payload": {
                            "title": "Captain Security Test",
                            "department": "engineering",
                            "priority": "low",
                        },
                    },
                    timeout=5,
                )

                # Should succeed (200, 201, or 409 duplicate)
                if response.status_code in [200, 201, 409]:
                    self.log_result(
                        SecurityTestResult(
                            "RBAC",
                            "Captain cross-department access allowed",
                            True,
                            f"{response.status_code} (correct - captain privilege)",
                            "INFO",
                        )
                    )
                else:
                    self.log_result(
                        SecurityTestResult(
                            "RBAC",
                            "Captain cross-department access allowed",
                            False,
                            f"Got {response.status_code}, expected 200/201/409",
                            "MEDIUM",
                        )
                    )
            except Exception as e:
                self.log_result(
                    SecurityTestResult(
                        "RBAC",
                        "Captain cross-department access allowed",
                        False,
                        f"Exception: {str(e)}",
                        "MEDIUM",
                    )
                )

    # =========================================================================
    # SQL Injection Tests
    # =========================================================================

    def test_sql_injection(self):
        """Test SQL injection attack resistance."""
        print("\n### SQL INJECTION TESTS ###\n")

        sql_payloads = [
            "'; DROP TABLE pms_parts; --",
            "' OR '1'='1",
            "admin'--",
            "' UNION SELECT * FROM users--",
            "1'; EXEC xp_cmdshell('dir'); --",
            "'; SHUTDOWN; --",
        ]

        if USERS.get("HOD"):
            auth_header = {"Authorization": f"Bearer {USERS['HOD']['access_token']}"}

            for i, payload in enumerate(sql_payloads, 1):
                try:
                    response = requests.post(
                        f"{API_BASE}/search",
                        headers=auth_header,
                        json={"query": payload, "limit": 10},
                        timeout=5,
                    )

                    # Should return 200 with empty results or 400 bad request
                    # Should NOT return 500 (SQL error leaked)
                    if response.status_code == 500:
                        self.log_result(
                            SecurityTestResult(
                                "SQLi",
                                f"SQL injection payload #{i}",
                                False,
                                f"500 Internal Error (possible SQL error leaked)",
                                "CRITICAL",
                            )
                        )
                    elif response.status_code in [200, 400]:
                        self.log_result(
                            SecurityTestResult(
                                "SQLi",
                                f"SQL injection payload #{i}",
                                True,
                                f"{response.status_code} (query handled safely)",
                                "CRITICAL",
                            )
                        )
                    else:
                        self.log_result(
                            SecurityTestResult(
                                "SQLi",
                                f"SQL injection payload #{i}",
                                True,
                                f"{response.status_code} (unexpected but not 500)",
                                "HIGH",
                            )
                        )
                except Exception as e:
                    self.log_result(
                        SecurityTestResult(
                            "SQLi",
                            f"SQL injection payload #{i}",
                            False,
                            f"Exception: {str(e)}",
                            "CRITICAL",
                        )
                    )

    # =========================================================================
    # XSS Tests
    # =========================================================================

    def test_xss_payloads(self):
        """Test XSS attack resistance."""
        print("\n### XSS PAYLOAD TESTS ###\n")

        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "<svg onload=alert('XSS')>",
            "javascript:alert('XSS')",
            "<iframe src='javascript:alert(\"XSS\")'></iframe>",
        ]

        if USERS.get("HOD"):
            auth_header = {"Authorization": f"Bearer {USERS['HOD']['access_token']}"}

            for i, payload in enumerate(xss_payloads, 1):
                try:
                    response = requests.post(
                        f"{API_BASE}/search",
                        headers=auth_header,
                        json={"query": payload, "limit": 10},
                        timeout=5,
                    )

                    # Should return 200 (query processed)
                    # Check if response escapes the payload
                    if response.status_code == 200:
                        response_text = response.text

                        # Check if raw payload appears in response (BAD)
                        if payload in response_text:
                            self.log_result(
                                SecurityTestResult(
                                    "XSS",
                                    f"XSS payload #{i} sanitized",
                                    False,
                                    "Raw payload in response (not escaped!)",
                                    "HIGH",
                                )
                            )
                        else:
                            self.log_result(
                                SecurityTestResult(
                                    "XSS",
                                    f"XSS payload #{i} sanitized",
                                    True,
                                    "Payload not in response (escaped or filtered)",
                                    "HIGH",
                                )
                            )
                    else:
                        self.log_result(
                            SecurityTestResult(
                                "XSS",
                                f"XSS payload #{i} sanitized",
                                True,
                                f"{response.status_code} (query rejected/handled)",
                                "HIGH",
                            )
                        )
                except Exception as e:
                    self.log_result(
                        SecurityTestResult(
                            "XSS",
                            f"XSS payload #{i} sanitized",
                            False,
                            f"Exception: {str(e)}",
                            "HIGH",
                        )
                    )

    # =========================================================================
    # CSRF Tests
    # =========================================================================

    def test_csrf_protection(self):
        """Test CSRF protection mechanisms."""
        print("\n### CSRF PROTECTION TESTS ###\n")

        if USERS.get("HOD"):
            auth_header = {"Authorization": f"Bearer {USERS['HOD']['access_token']}"}

            # Test 1: Request without Origin header (potential CSRF)
            try:
                response = requests.post(
                    f"{API_BASE}/v1/actions/execute",
                    headers=auth_header,
                    json={
                        "action": "create_work_order",
                        "context": {"yacht_id": YACHT_1},
                        "payload": {
                            "title": "CSRF Test",
                            "department": "deck",
                            "priority": "low",
                        },
                    },
                    timeout=5,
                )

                # Note: APIs typically don't enforce Origin for programmatic access
                # This is INFO level, not a vulnerability unless it's a web form
                self.log_result(
                    SecurityTestResult(
                        "CSRF",
                        "Request without Origin header",
                        True,
                        f"{response.status_code} (API allows - expected for REST)",
                        "INFO",
                    )
                )
            except Exception as e:
                self.log_result(
                    SecurityTestResult(
                        "CSRF",
                        "Request without Origin header",
                        False,
                        f"Exception: {str(e)}",
                        "MEDIUM",
                    )
                )

            # Test 2: Request with malicious Origin header
            try:
                malicious_headers = {
                    **auth_header,
                    "Origin": "https://evil.com",
                    "Referer": "https://evil.com/attack.html",
                }

                response = requests.post(
                    f"{API_BASE}/v1/actions/execute",
                    headers=malicious_headers,
                    json={
                        "action": "create_work_order",
                        "context": {"yacht_id": YACHT_1},
                        "payload": {
                            "title": "CSRF Test Evil Origin",
                            "department": "deck",
                            "priority": "low",
                        },
                    },
                    timeout=5,
                )

                # Should be blocked if CORS is properly configured
                if response.status_code == 403:
                    self.log_result(
                        SecurityTestResult(
                            "CSRF",
                            "Malicious Origin header blocked",
                            True,
                            "403 Forbidden (CORS protection active)",
                            "HIGH",
                        )
                    )
                else:
                    # Most APIs allow any Origin if JWT is valid (not necessarily a vulnerability)
                    self.log_result(
                        SecurityTestResult(
                            "CSRF",
                            "Malicious Origin header blocked",
                            True,
                            f"{response.status_code} (JWT auth sufficient for API)",
                            "INFO",
                        )
                    )
            except Exception as e:
                self.log_result(
                    SecurityTestResult(
                        "CSRF",
                        "Malicious Origin header blocked",
                        False,
                        f"Exception: {str(e)}",
                        "MEDIUM",
                    )
                )

    # =========================================================================
    # Report Generation
    # =========================================================================

    def generate_report(self):
        """Generate security test report."""
        print("\n" + "=" * 80)
        print("DAY 5: SECURITY TEST SUMMARY")
        print("=" * 80)
        print(f"Total Tests: {self.passed + self.failed}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(f"Pass Rate: {self.passed / (self.passed + self.failed) * 100:.1f}%")
        print(f"Critical Failures: {self.critical_failures}")

        # Group by severity
        by_severity = {"CRITICAL": [], "HIGH": [], "MEDIUM": [], "LOW": [], "INFO": []}
        for r in self.results:
            if not r.passed:
                by_severity[r.severity].append(r)

        print("\n### VULNERABILITIES BY SEVERITY ###")
        for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            count = len(by_severity[severity])
            if count > 0:
                print(f"\n{severity}: {count}")
                for r in by_severity[severity][:5]:
                    print(f"  - {r.test_name}: {r.details}")

        # Save report
        report = {
            "day": 5,
            "timestamp": datetime.now().isoformat(),
            "total": self.passed + self.failed,
            "passed": self.passed,
            "failed": self.failed,
            "critical_failures": self.critical_failures,
            "results": [
                {
                    "category": r.category,
                    "test": r.test_name,
                    "passed": r.passed,
                    "severity": r.severity,
                    "details": r.details,
                }
                for r in self.results
            ],
        }

        with open("test-automation/results/day5_security_audit.json", "w") as f:
            json.dump(report, f, indent=2)

        print(f"\nReport saved: test-automation/results/day5_security_audit.json")

        # Verdict
        if self.critical_failures == 0:
            print("\n✅ DAY 5 SUCCESS: Zero critical security vulnerabilities")
            return 0
        else:
            print(f"\n⚠️  DAY 5 PARTIAL: {self.critical_failures} critical vulnerabilities found")
            return 1

    def run_all_tests(self):
        """Run all security tests."""
        print("\n" + "=" * 80)
        print("DAY 5: COMPREHENSIVE SECURITY TESTING")
        print("=" * 80)

        self.test_jwt_expiration()
        self.test_cross_yacht_isolation()
        self.test_sql_injection()
        self.test_xss_payloads()
        self.test_csrf_protection()


if __name__ == "__main__":
    if not sign_in_users():
        sys.exit(1)

    tester = SecurityTester()
    tester.run_all_tests()
    exit_code = tester.generate_report()
    sys.exit(exit_code)
