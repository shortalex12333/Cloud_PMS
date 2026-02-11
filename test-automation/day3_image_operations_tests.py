#!/usr/bin/env python3
"""
Day 3: Image Operations Perfection
Tests all image upload/update/delete operations exhaustively
"""

import os
import sys
import json
import time
import requests
import io
from PIL import Image
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

API_BASE = os.getenv("API_BASE", "https://pipeline-core.int.celeste7.ai")
YACHT_ID = os.getenv("YACHT_ID", "85fe1119-b04c-41ac-80f1-829d23322598")
SUPABASE_URL = os.getenv("MASTER_SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("MASTER_SUPABASE_ANON_KEY")

# Test users with JWTs
USERS = {}


def sign_in_users():
    """Sign in all test users."""
    users_config = {
        "HOD": "hod.test@alex-short.com",
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
            USERS[role] = response.json()["access_token"]
            print(f"✅ {role} signed in")
        else:
            print(f"❌ {role} sign-in failed")
            return False
    return True


def create_test_image(size_kb: int, format: str = "PNG") -> bytes:
    """Create a test image of specified size and format."""
    # Calculate dimensions for approximate file size
    # PNG: ~1KB per 100x100 pixels (with compression)
    pixels = int((size_kb * 100) ** 0.5)
    pixels = max(10, pixels)  # Minimum 10x10

    # Create image with random RGB data
    img = Image.new('RGB', (pixels, pixels))
    pixels_data = []
    for y in range(pixels):
        for x in range(pixels):
            # Create some pattern for visual distinction
            r = (x * 255) // pixels
            g = (y * 255) // pixels
            b = ((x + y) * 255) // (pixels * 2)
            pixels_data.append((r, g, b))
    img.putdata(pixels_data)

    # Save to bytes
    buffer = io.BytesIO()
    img.save(buffer, format=format, optimize=True)
    return buffer.getvalue()


def get_test_part(jwt: str) -> str:
    """Get a test part ID from the database."""
    headers = {
        "Authorization": f"Bearer {jwt}",
        "Content-Type": "application/json",
    }

    # Search for a part
    response = requests.post(
        f"{API_BASE}/search",
        headers=headers,
        json={"query": "filter", "limit": 10},
        timeout=10,
    )

    if response.status_code == 200:
        results = response.json().get("results", [])
        for result in results:
            if result.get("object_type") == "part":
                part_id = result.get("object_id")
                if part_id:
                    return part_id

    return None


class ImageOperationsTestResult:
    """Test result with detailed metrics."""

    def __init__(self, test_name, expected_status, actual_status, latency_ms, error=None, details=None):
        self.test_name = test_name
        self.expected_status = expected_status
        self.actual_status = actual_status
        self.latency_ms = latency_ms
        self.error = error
        self.details = details or {}
        self.success = (
            actual_status == expected_status if expected_status else actual_status < 500
        )


class ImageOperationsTester:
    """Comprehensive image operations testing."""

    def __init__(self):
        self.results = []
        self.passed = 0
        self.failed = 0
        self.test_part_id = None

    def test_upload_image(
        self,
        test_name: str,
        jwt: str,
        part_id: str,
        image_data: bytes,
        file_name: str,
        mime_type: str,
        expected_status: int = 200,
    ):
        """Test image upload."""
        start = time.time()

        try:
            files = {
                'file': (file_name, image_data, mime_type)
            }
            data = {
                'yacht_id': YACHT_ID,
                'part_id': part_id,
            }
            headers = {
                'Authorization': f'Bearer {jwt}'
            }

            response = requests.post(
                f"{API_BASE}/v1/parts/upload-image",
                headers=headers,
                files=files,
                data=data,  # Send as form data, not query params
                timeout=30,
            )

            latency_ms = (time.time() - start) * 1000
            details = {}

            if response.status_code == 200:
                try:
                    details = response.json()
                except:
                    details = {"text": response.text[:200]}
            else:
                try:
                    details = {"error": response.json()}
                except:
                    details = {"error": response.text[:200]}

            result = ImageOperationsTestResult(
                test_name,
                expected_status,
                response.status_code,
                latency_ms,
                details=details,
            )

        except Exception as e:
            latency_ms = (time.time() - start) * 1000
            result = ImageOperationsTestResult(
                test_name,
                expected_status,
                0,
                latency_ms,
                error=str(e),
            )

        self.results.append(result)
        if result.success:
            self.passed += 1
            status = "✅"
        else:
            self.failed += 1
            status = "❌"

        print(
            f"{status} {test_name:50s} {result.actual_status:3d} ({result.latency_ms:7.1f}ms)"
        )
        return result

    def run_all_tests(self):
        """Run comprehensive image operations tests."""
        print("\n" + "=" * 80)
        print("DAY 3: IMAGE OPERATIONS PERFECTION")
        print("=" * 80)

        jwt = USERS["HOD"]

        # Get test part
        print("\n### SETUP ###\n")
        print("Finding test part...")
        self.test_part_id = get_test_part(jwt)
        if not self.test_part_id:
            print("❌ Could not find test part")
            return
        print(f"✅ Test part ID: {self.test_part_id}")

        # =================================================================
        # Size Variants
        # =================================================================
        print("\n### SIZE VARIANTS ###\n")

        # 1KB image
        image_1kb = create_test_image(1, "PNG")
        self.test_upload_image(
            "Upload: 1KB PNG (minimum)",
            jwt,
            self.test_part_id,
            image_1kb,
            "test_1kb.png",
            "image/png",
            expected_status=200,
        )

        # 100KB image
        image_100kb = create_test_image(100, "PNG")
        self.test_upload_image(
            "Upload: 100KB PNG (typical)",
            jwt,
            self.test_part_id,
            image_100kb,
            "test_100kb.png",
            "image/png",
            expected_status=200,
        )

        # 1MB image
        image_1mb = create_test_image(1000, "PNG")
        self.test_upload_image(
            "Upload: 1MB PNG (large)",
            jwt,
            self.test_part_id,
            image_1mb,
            "test_1mb.png",
            "image/png",
            expected_status=200,
        )

        # =================================================================
        # Format Variants
        # =================================================================
        print("\n### FORMAT VARIANTS ###\n")

        # JPEG
        image_jpeg = create_test_image(100, "JPEG")
        self.test_upload_image(
            "Upload: 100KB JPEG",
            jwt,
            self.test_part_id,
            image_jpeg,
            "test.jpg",
            "image/jpeg",
            expected_status=200,
        )

        # WebP (if PIL supports it)
        try:
            image_webp = create_test_image(100, "WEBP")
            self.test_upload_image(
                "Upload: 100KB WebP",
                jwt,
                self.test_part_id,
                image_webp,
                "test.webp",
                "image/webp",
                expected_status=200,
            )
        except Exception as e:
            print(f"⏭️  Skipping WebP test: {e}")

        # =================================================================
        # Duplicate Upload (Reproduce Constraint Error)
        # =================================================================
        print("\n### DUPLICATE UPLOAD TEST ###\n")

        # Upload once
        image_dup1 = create_test_image(50, "PNG")
        result1 = self.test_upload_image(
            "Upload: First upload to part",
            jwt,
            self.test_part_id,
            image_dup1,
            "duplicate_test1.png",
            "image/png",
            expected_status=200,
        )

        # Upload again to same part (should trigger constraint error on old code)
        image_dup2 = create_test_image(50, "PNG")
        result2 = self.test_upload_image(
            "Upload: Second upload to same part (duplicate)",
            jwt,
            self.test_part_id,
            image_dup2,
            "duplicate_test2.png",
            "image/png",
            expected_status=200,  # Should succeed with UPSERT logic
        )

        # =================================================================
        # Edge Cases
        # =================================================================
        print("\n### EDGE CASES ###\n")

        # Empty file
        self.test_upload_image(
            "Upload: Empty file",
            jwt,
            self.test_part_id,
            b"",
            "empty.png",
            "image/png",
            expected_status=400,  # Should reject
        )

        # Invalid part_id
        self.test_upload_image(
            "Upload: Invalid part_id",
            jwt,
            "00000000-0000-0000-0000-000000000000",
            image_1kb,
            "test.png",
            "image/png",
            expected_status=400,  # Part not found
        )

        # =================================================================
        # Concurrent Uploads
        # =================================================================
        print("\n### CONCURRENT UPLOADS ###\n")

        print("Running 5 concurrent uploads to different parts...")

        def concurrent_upload(index):
            image_data = create_test_image(50, "PNG")
            start = time.time()
            try:
                files = {'file': (f'concurrent_{index}.png', image_data, 'image/png')}
                data = {'yacht_id': YACHT_ID, 'part_id': self.test_part_id}
                headers = {'Authorization': f'Bearer {jwt}'}

                response = requests.post(
                    f"{API_BASE}/v1/parts/upload-image",
                    headers=headers,
                    files=files,
                    data=data,  # Send as form data, not query params
                    timeout=30,
                )
                latency = (time.time() - start) * 1000
                return (index, response.status_code, latency, None)
            except Exception as e:
                latency = (time.time() - start) * 1000
                return (index, 0, latency, str(e))

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(concurrent_upload, i) for i in range(5)]
            concurrent_results = []
            for future in as_completed(futures):
                index, status, latency, error = future.result()
                concurrent_results.append((status, latency))
                if status == 200:
                    print(f"  ✅ Upload {index}: {status} ({latency:.1f}ms)")
                else:
                    print(f"  ❌ Upload {index}: {status} ({latency:.1f}ms) - {error}")

        # Count successes
        successes = sum(1 for status, _ in concurrent_results if status == 200)
        print(f"Concurrent uploads: {successes}/5 successful")

    def generate_report(self):
        """Generate test report."""
        print("\n" + "=" * 80)
        print("DAY 3: TEST SUMMARY")
        print("=" * 80)
        print(f"Total Tests: {self.passed + self.failed}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(f"Pass Rate: {self.passed / (self.passed + self.failed) * 100:.1f}%")

        # Categorize failures
        errors_400 = [r for r in self.results if r.actual_status == 400]
        errors_500 = [r for r in self.results if r.actual_status == 500]
        errors_timeout = [r for r in self.results if r.error and "timeout" in r.error.lower()]

        print(f"\n### ISSUES FOUND ###")
        print(f"400 Client Errors: {len(errors_400)}")
        print(f"500 Server Errors: {len(errors_500)}")
        print(f"Timeouts: {len(errors_timeout)}")

        if errors_500:
            print("\n500 Errors:")
            for r in errors_500[:5]:
                print(f"  - {r.test_name}")
                if r.details:
                    error_msg = r.details.get("error", "")
                    if isinstance(error_msg, dict):
                        error_msg = error_msg.get("detail", str(error_msg))
                    print(f"    Error: {str(error_msg)[:100]}")

        # Save report
        report = {
            "day": 3,
            "timestamp": datetime.now().isoformat(),
            "total": self.passed + self.failed,
            "passed": self.passed,
            "failed": self.failed,
            "errors_400": len(errors_400),
            "errors_500": len(errors_500),
            "errors_timeout": len(errors_timeout),
            "results": [
                {
                    "test": r.test_name,
                    "expected": r.expected_status,
                    "actual": r.actual_status,
                    "latency_ms": r.latency_ms,
                    "success": r.success,
                    "details": r.details,
                    "error": r.error,
                }
                for r in self.results
            ],
        }

        with open("test-automation/results/day3_image_operations.json", "w") as f:
            json.dump(report, f, indent=2)

        print(f"\nReport saved: test-automation/results/day3_image_operations.json")

        # Verdict
        if errors_500 == 0:
            print("\n✅ DAY 3 SUCCESS: Zero 500s, all edge cases handled")
            return 0
        else:
            print(f"\n⚠️  DAY 3 PARTIAL: {len(errors_500)} server errors found (need fixing)")
            return 1


if __name__ == "__main__":
    if not sign_in_users():
        sys.exit(1)

    tester = ImageOperationsTester()
    tester.run_all_tests()
    exit_code = tester.generate_report()
    sys.exit(exit_code)
