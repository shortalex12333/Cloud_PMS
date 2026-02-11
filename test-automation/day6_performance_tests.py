#!/usr/bin/env python3
"""
Day 6: Performance Testing and Optimization Validation
Tests API performance under various load conditions and validates optimizations
"""

import os
import sys
import json
import time
import requests
import statistics
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple

API_BASE = os.getenv("API_BASE", "https://pipeline-core.int.celeste7.ai")
SUPABASE_URL = os.getenv("MASTER_SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("MASTER_SUPABASE_ANON_KEY")
YACHT_ID = os.getenv("YACHT_ID", "85fe1119-b04c-41ac-80f1-829d23322598")

# Global auth token
AUTH_TOKEN = None


def sign_in_hod():
    """Sign in as HOD user and cache token."""
    global AUTH_TOKEN

    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Content-Type": "application/json",
    }
    response = requests.post(
        f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
        headers=headers,
        json={"email": "hod.test@alex-short.com", "password": "Password2!"},
        timeout=10,
    )
    if response.status_code == 200:
        AUTH_TOKEN = response.json()["access_token"]
        print("✅ HOD signed in")
        return True
    else:
        print(f"❌ HOD sign-in failed: {response.status_code}")
        return False


class PerformanceTestResult:
    """Performance test result with detailed metrics."""

    def __init__(
        self,
        test_name: str,
        latencies: List[float],
        errors: int = 0,
        target_p95_ms: float = 2000,
    ):
        self.test_name = test_name
        self.latencies = sorted(latencies)
        self.errors = errors
        self.target_p95_ms = target_p95_ms

        if latencies:
            self.min_ms = min(latencies)
            self.max_ms = max(latencies)
            self.mean_ms = statistics.mean(latencies)
            self.median_ms = statistics.median(latencies)
            self.p50_ms = self.median_ms
            self.p75_ms = self._percentile(75)
            self.p90_ms = self._percentile(90)
            self.p95_ms = self._percentile(95)
            self.p99_ms = self._percentile(99)
            self.passed = self.p95_ms < target_p95_ms
        else:
            self.min_ms = 0
            self.max_ms = 0
            self.mean_ms = 0
            self.median_ms = 0
            self.p50_ms = 0
            self.p75_ms = 0
            self.p90_ms = 0
            self.p95_ms = 0
            self.p99_ms = 0
            self.passed = False

    def _percentile(self, p: float) -> float:
        """Calculate percentile from sorted latencies."""
        if not self.latencies:
            return 0
        k = (len(self.latencies) - 1) * (p / 100)
        f = int(k)
        c = f + 1
        if c >= len(self.latencies):
            return self.latencies[f]
        d0 = self.latencies[f] * (c - k)
        d1 = self.latencies[c] * (k - f)
        return d0 + d1


class PerformanceTester:
    """Performance testing harness."""

    def __init__(self):
        self.results: List[PerformanceTestResult] = []
        self.passed = 0
        self.failed = 0

    def log_result(self, result: PerformanceTestResult):
        """Log a performance test result."""
        self.results.append(result)

        status = "✅" if result.passed else "❌"
        target_marker = f"(target: <{result.target_p95_ms}ms)"

        print(f"\n{status} {result.test_name}")
        print(f"  Requests: {len(result.latencies)}")
        print(f"  Errors: {result.errors}")
        print(f"  Min: {result.min_ms:.1f}ms")
        print(f"  Mean: {result.mean_ms:.1f}ms")
        print(f"  Median: {result.median_ms:.1f}ms")
        print(f"  P75: {result.p75_ms:.1f}ms")
        print(f"  P90: {result.p90_ms:.1f}ms")
        print(f"  P95: {result.p95_ms:.1f}ms {target_marker}")
        print(f"  P99: {result.p99_ms:.1f}ms")
        print(f"  Max: {result.max_ms:.1f}ms")

        if result.passed:
            self.passed += 1
        else:
            self.failed += 1

    # =========================================================================
    # Individual Request Profiling
    # =========================================================================

    def test_single_request_baseline(self):
        """Baseline: Single request latency breakdown."""
        print("\n### BASELINE: SINGLE REQUEST PROFILING ###\n")

        auth_header = {"Authorization": f"Bearer {AUTH_TOKEN}"}

        print("Making single search request with timing breakdown...")

        start = time.time()
        response = requests.post(
            f"{API_BASE}/search",
            headers=auth_header,
            json={"query": "oil filter", "limit": 10},
            timeout=10,
        )
        total_latency = (time.time() - start) * 1000

        if response.status_code == 200:
            data = response.json()
            timing = data.get("timing_ms", {})

            print(f"\n✅ Request successful")
            print(f"  Total (measured): {total_latency:.1f}ms")
            print(f"  Total (API reported): {timing.get('total', 0):.1f}ms")
            print(f"  Embedding: {timing.get('embedding', 0):.1f}ms")
            print(f"  Fusion: {timing.get('fusion', 0):.1f}ms")
            print(f"  Network overhead: {(total_latency - timing.get('total', 0)):.1f}ms")

            # Check for bottlenecks
            embedding_ms = timing.get('embedding', 0)
            fusion_ms = timing.get('fusion', 0)

            if embedding_ms > 500:
                print(f"  ⚠️  Embedding is slow ({embedding_ms:.1f}ms > 500ms)")
            if fusion_ms > 1000:
                print(f"  ⚠️  Database fusion is slow ({fusion_ms:.1f}ms > 1000ms)")

        else:
            print(f"❌ Request failed: {response.status_code}")

    # =========================================================================
    # Sequential Requests (No Concurrency)
    # =========================================================================

    def test_sequential_requests(self, count: int = 10):
        """Test sequential requests to establish baseline without concurrency."""
        print(f"\n### SEQUENTIAL REQUESTS (N={count}) ###\n")

        auth_header = {"Authorization": f"Bearer {AUTH_TOKEN}"}
        latencies = []
        errors = 0

        for i in range(count):
            start = time.time()
            try:
                response = requests.post(
                    f"{API_BASE}/search",
                    headers=auth_header,
                    json={"query": f"test query {i}", "limit": 10},
                    timeout=10,
                )
                latency = (time.time() - start) * 1000
                latencies.append(latency)

                if response.status_code != 200:
                    errors += 1
                    print(f"  Request {i+1}/{count}: {response.status_code} ({latency:.1f}ms)")
            except Exception as e:
                errors += 1
                latency = (time.time() - start) * 1000
                print(f"  Request {i+1}/{count}: ERROR ({latency:.1f}ms) - {str(e)}")

        result = PerformanceTestResult(
            f"Sequential {count} requests",
            latencies,
            errors,
            target_p95_ms=1500,  # Should be <1.5s for sequential
        )
        self.log_result(result)

    # =========================================================================
    # Concurrent Requests (Low Load)
    # =========================================================================

    def test_concurrent_requests_low(self, workers: int = 5, num_requests: int = 20):
        """Test low concurrency (5 workers, 20 requests)."""
        print(f"\n### LOW CONCURRENCY ({workers} workers, {num_requests} requests) ###\n")

        auth_header = {"Authorization": f"Bearer {AUTH_TOKEN}"}
        latencies = []
        errors = 0

        def make_request(i):
            start = time.time()
            try:
                import requests as req
                response = req.post(
                    f"{API_BASE}/search",
                    headers=auth_header,
                    json={"query": f"concurrent test {i}", "limit": 10},
                    timeout=10,
                )
                latency = (time.time() - start) * 1000

                if response.status_code == 200:
                    return latency, None
                else:
                    return latency, f"Status {response.status_code}"
            except Exception as e:
                latency = (time.time() - start) * 1000
                return latency, str(e)

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(make_request, i) for i in range(num_requests)]

            for i, future in enumerate(as_completed(futures), 1):
                latency, error = future.result()
                latencies.append(latency)

                if error:
                    errors += 1
                    print(f"  Request {i}/{num_requests}: ERROR ({latency:.1f}ms) - {error}")
                else:
                    print(f"  Request {i}/{num_requests}: OK ({latency:.1f}ms)")

        result = PerformanceTestResult(
            f"Concurrent {num_requests} requests ({workers} workers)",
            latencies,
            errors,
            target_p95_ms=2000,  # Target <2s for low concurrency
        )
        self.log_result(result)

    # =========================================================================
    # Concurrent Requests (Medium Load) - Day 2 Scenario
    # =========================================================================

    def test_concurrent_requests_medium(self, workers: int = 10, num_requests: int = 30):
        """Test medium concurrency (10 workers, 30 requests) - Day 2 scenario."""
        print(f"\n### MEDIUM CONCURRENCY ({workers} workers, {num_requests} requests) ###\n")
        print("This replicates the Day 2 test that showed P95 = 8709ms")

        auth_header = {"Authorization": f"Bearer {AUTH_TOKEN}"}
        latencies = []
        errors = 0

        def make_request(i):
            start = time.time()
            try:
                import requests as req
                response = req.post(
                    f"{API_BASE}/search",
                    headers=auth_header,
                    json={"query": "oil filter", "limit": 10},
                    timeout=15,
                )
                latency = (time.time() - start) * 1000

                if response.status_code == 200:
                    return latency, None
                else:
                    return latency, f"Status {response.status_code}"
            except Exception as e:
                latency = (time.time() - start) * 1000
                return latency, str(e)

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(make_request, i) for i in range(num_requests)]

            for i, future in enumerate(as_completed(futures), 1):
                latency, error = future.result()
                latencies.append(latency)

                if error:
                    errors += 1

        result = PerformanceTestResult(
            f"Day 2 Reproduction: {num_requests} requests ({workers} workers)",
            latencies,
            errors,
            target_p95_ms=2000,  # TARGET: <2s (down from 8709ms)
        )
        self.log_result(result)

        # Compare to Day 2 baseline
        day2_p95 = 8709.4
        improvement = ((day2_p95 - result.p95_ms) / day2_p95) * 100

        print(f"\n  📊 Comparison to Day 2:")
        print(f"    Day 2 P95: {day2_p95:.1f}ms")
        print(f"    Current P95: {result.p95_ms:.1f}ms")
        if improvement > 0:
            print(f"    Improvement: {improvement:.1f}% faster ✅")
        else:
            print(f"    Regression: {abs(improvement):.1f}% slower ❌")

    # =========================================================================
    # Concurrent Requests (High Load)
    # =========================================================================

    def test_concurrent_requests_high(self, workers: int = 20, num_requests: int = 50):
        """Test high concurrency (20 workers, 50 requests)."""
        print(f"\n### HIGH CONCURRENCY ({workers} workers, {num_requests} requests) ###\n")

        auth_header = {"Authorization": f"Bearer {AUTH_TOKEN}"}
        latencies = []
        errors = 0

        def make_request(i):
            start = time.time()
            try:
                import requests as req
                response = req.post(
                    f"{API_BASE}/search",
                    headers=auth_header,
                    json={"query": f"stress test {i}", "limit": 10},
                    timeout=20,
                )
                latency = (time.time() - start) * 1000

                if response.status_code == 200:
                    return latency, None
                else:
                    return latency, f"Status {response.status_code}"
            except Exception as e:
                latency = (time.time() - start) * 1000
                return latency, str(e)

        print("Running high load test...")

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(make_request, i) for i in range(num_requests)]

            completed = 0
            for future in as_completed(futures):
                completed += 1
                latency, error = future.result()
                latencies.append(latency)

                if error:
                    errors += 1

                # Print progress every 10 requests
                if completed % 10 == 0:
                    print(f"  Progress: {completed}/{num_requests} requests completed")

        result = PerformanceTestResult(
            f"High load: {num_requests} requests ({workers} workers)",
            latencies,
            errors,
            target_p95_ms=3000,  # More lenient for high load
        )
        self.log_result(result)

    # =========================================================================
    # Sustained Load Test
    # =========================================================================

    def test_sustained_load(self, duration_sec: int = 30, workers: int = 5):
        """Test sustained load over time (e.g., 30 seconds)."""
        print(f"\n### SUSTAINED LOAD ({duration_sec}s, {workers} workers) ###\n")

        auth_header = {"Authorization": f"Bearer {AUTH_TOKEN}"}
        latencies = []
        errors = 0
        request_count = 0

        def make_request():
            start = time.time()
            try:
                response = requests.post(
                    f"{API_BASE}/search",
                    headers=auth_header,
                    json={"query": "sustained load test", "limit": 10},
                    timeout=10,
                )
                latency = (time.time() - start) * 1000

                if response.status_code == 200:
                    return latency, None
                else:
                    return latency, f"Status {response.status_code}"
            except Exception as e:
                latency = (time.time() - start) * 1000
                return latency, str(e)

        print(f"Running sustained load for {duration_sec} seconds...")
        start_time = time.time()
        end_time = start_time + duration_sec

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = []

            # Keep submitting requests until time is up
            while time.time() < end_time:
                future = executor.submit(make_request)
                futures.append(future)
                request_count += 1
                time.sleep(0.1)  # 10 RPS per worker

            # Wait for all to complete
            for i, future in enumerate(as_completed(futures), 1):
                latency, error = future.result()
                latencies.append(latency)

                if error:
                    errors += 1

                if i % 20 == 0:
                    print(f"  Progress: {i}/{request_count} requests completed")

        result = PerformanceTestResult(
            f"Sustained load {duration_sec}s ({workers} workers)",
            latencies,
            errors,
            target_p95_ms=2000,
        )
        self.log_result(result)

        throughput = len(latencies) / duration_sec
        print(f"\n  📈 Throughput: {throughput:.1f} requests/second")

    # =========================================================================
    # Report Generation
    # =========================================================================

    def generate_report(self):
        """Generate performance test report."""
        print("\n" + "=" * 80)
        print("DAY 6: PERFORMANCE TEST SUMMARY")
        print("=" * 80)

        print(f"Total Test Scenarios: {len(self.results)}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")

        if self.results:
            pass_rate = (self.passed / len(self.results)) * 100
            print(f"Pass Rate: {pass_rate:.1f}%")

        # Performance summary table
        print("\n### PERFORMANCE SUMMARY ###\n")
        print(f"{'Test':<50} {'P95 (ms)':<12} {'Target':<12} {'Status'}")
        print("-" * 90)

        for result in self.results:
            status = "✅ PASS" if result.passed else "❌ FAIL"
            print(
                f"{result.test_name:<50} {result.p95_ms:<12.1f} "
                f"<{result.target_p95_ms:<11.1f} {status}"
            )

        # Save detailed report
        report = {
            "day": 6,
            "timestamp": datetime.now().isoformat(),
            "total_scenarios": len(self.results),
            "passed": self.passed,
            "failed": self.failed,
            "results": [
                {
                    "test": r.test_name,
                    "requests": len(r.latencies),
                    "errors": r.errors,
                    "min_ms": r.min_ms,
                    "mean_ms": r.mean_ms,
                    "median_ms": r.median_ms,
                    "p75_ms": r.p75_ms,
                    "p90_ms": r.p90_ms,
                    "p95_ms": r.p95_ms,
                    "p99_ms": r.p99_ms,
                    "max_ms": r.max_ms,
                    "target_p95_ms": r.target_p95_ms,
                    "passed": r.passed,
                }
                for r in self.results
            ],
        }

        with open("test-automation/results/day6_performance_audit.json", "w") as f:
            json.dump(report, f, indent=2)

        print(f"\nReport saved: test-automation/results/day6_performance_audit.json")

        # Verdict
        if self.failed == 0:
            print("\n✅ DAY 6 SUCCESS: All performance targets met")
            return 0
        else:
            print(f"\n⚠️  DAY 6 PARTIAL: {self.failed} performance targets missed")
            return 1

    def run_all_tests(self):
        """Run all performance tests."""
        print("\n" + "=" * 80)
        print("DAY 6: COMPREHENSIVE PERFORMANCE TESTING")
        print("=" * 80)

        self.test_single_request_baseline()
        self.test_sequential_requests(count=10)
        self.test_concurrent_requests_low(workers=5, num_requests=20)
        self.test_concurrent_requests_medium(workers=10, num_requests=30)
        self.test_concurrent_requests_high(workers=20, num_requests=50)
        # self.test_sustained_load(duration_sec=30, workers=5)  # Optional: Comment out for faster testing


if __name__ == "__main__":
    if not sign_in_hod():
        sys.exit(1)

    tester = PerformanceTester()
    tester.run_all_tests()
    exit_code = tester.generate_report()
    sys.exit(exit_code)
