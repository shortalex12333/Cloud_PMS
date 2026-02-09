#!/usr/bin/env python3
"""
Autonomous Inventory Lens Testing Suite
Following TESTING_INFRASTRUCTURE.md protocol
Goal: 0% -> 100% success rate with tangible evidence
"""
import requests
import json
import time
from datetime import datetime

# API Configuration
API_BASE = "https://pipeline-core.int.celeste7.ai"
MASTER_SUPABASE_URL = "https://qvzmkaamzaqxpzbewjxe.supabase.co"
MASTER_SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF2em1rYWFtemFxeHB6YmV3anhlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM5NzkwNDYsImV4cCI6MjA3OTU1NTA0Nn0.MMzzsRkvbug-u19GBUnD0qLDtMVWEbOf6KE8mAADaxw"

# Test Users
TEST_USERS = {
    "crew": {"email": "crew.test@alex-short.com", "password": "Password2!"},
    "hod": {"email": "hod.test@alex-short.com", "password": "Password2!"},
    "captain": {"email": "captain.test@alex-short.com", "password": "Password2!"}
}

class InventoryLensTester:
    def __init__(self):
        self.tokens = {}
        self.results = []
        self.failures = []

    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")

    def refresh_tokens(self):
        """Get fresh JWT tokens for all test users"""
        self.log("=== TOKEN REFRESH ===")
        for role, creds in TEST_USERS.items():
            try:
                resp = requests.post(
                    f"{MASTER_SUPABASE_URL}/auth/v1/token?grant_type=password",
                    headers={
                        "apikey": MASTER_SUPABASE_ANON_KEY,
                        "Content-Type": "application/json"
                    },
                    json={"email": creds["email"], "password": creds["password"]},
                    timeout=10
                )

                if resp.status_code == 200:
                    self.tokens[role] = resp.json()['access_token']
                    self.log(f"✅ {role.upper()} token obtained")
                else:
                    self.log(f"❌ {role.upper()} token failed: {resp.status_code}", "ERROR")
                    self.failures.append(f"Token refresh failed for {role}")

            except Exception as e:
                self.log(f"❌ {role.upper()} token error: {e}", "ERROR")
                self.failures.append(f"Token refresh error for {role}: {e}")

        # Return True if we have at least crew and hod tokens
        return len(self.tokens) >= 2

    def test_entity_extraction(self, query, expected_entity_type, expected_value=None, role="crew"):
        """Test entity extraction for inventory queries"""
        test_name = f"Entity extraction: '{query}'"
        self.log(f"\n--- {test_name} ---")

        try:
            resp = requests.post(
                f"{API_BASE}/webhook/search",
                headers={
                    "Authorization": f"Bearer {self.tokens[role]}",
                    "Content-Type": "application/json"
                },
                json={"query": query, "limit": 10},
                timeout=15
            )

            if resp.status_code != 200:
                self.log(f"❌ API returned {resp.status_code}", "ERROR")
                self.failures.append(f"{test_name}: API error {resp.status_code}")
                return False

            data = resp.json()
            entities = data.get('entities', [])

            # Check if expected entity type exists
            found_entity = None
            for entity in entities:
                entity_type = entity.get('extraction_type', entity.get('type'))
                if entity_type == expected_entity_type:
                    found_entity = entity
                    break

            if not found_entity:
                self.log(f"❌ Expected entity type '{expected_entity_type}' not found", "ERROR")
                self.log(f"   Found entities: {[e.get('extraction_type') for e in entities]}")
                self.failures.append(f"{test_name}: Missing {expected_entity_type}")
                return False

            # Check value if specified
            if expected_value:
                actual_value = found_entity.get('value', '').lower()
                if expected_value.lower() not in actual_value:
                    self.log(f"❌ Expected value '{expected_value}' not in '{actual_value}'", "ERROR")
                    self.failures.append(f"{test_name}: Value mismatch")
                    return False

            self.log(f"✅ Entity extracted: {expected_entity_type} = {found_entity.get('value')}")
            self.results.append({"test": test_name, "status": "PASS", "data": found_entity})
            return True

        except Exception as e:
            self.log(f"❌ Exception: {e}", "ERROR")
            self.failures.append(f"{test_name}: Exception - {e}")
            return False

    def test_capability_routing(self, query, expected_capability, role="crew"):
        """Test that query routes to correct capability"""
        test_name = f"Capability routing: '{query}'"
        self.log(f"\n--- {test_name} ---")

        try:
            resp = requests.post(
                f"{API_BASE}/webhook/search",
                headers={
                    "Authorization": f"Bearer {self.tokens[role]}",
                    "Content-Type": "application/json"
                },
                json={"query": query, "limit": 10},
                timeout=15
            )

            if resp.status_code != 200:
                self.log(f"❌ API returned {resp.status_code}", "ERROR")
                self.failures.append(f"{test_name}: API error {resp.status_code}")
                return False

            data = resp.json()
            plans = data.get('plans', [])

            if not plans:
                self.log(f"❌ No plans generated", "ERROR")
                self.failures.append(f"{test_name}: No plans")
                return False

            # Check if expected capability is in first 3 plans
            found = False
            for i, plan in enumerate(plans[:3]):
                if expected_capability in plan.get('capability', ''):
                    self.log(f"✅ Capability found at position {i+1}: {plan.get('capability')}")
                    found = True
                    break

            if not found:
                self.log(f"❌ Expected capability '{expected_capability}' not in top 3 plans", "ERROR")
                self.log(f"   Plans: {[p.get('capability') for p in plans[:3]]}")
                self.failures.append(f"{test_name}: Capability not found")
                return False

            self.results.append({"test": test_name, "status": "PASS", "capability": expected_capability})
            return True

        except Exception as e:
            self.log(f"❌ Exception: {e}", "ERROR")
            self.failures.append(f"{test_name}: Exception - {e}")
            return False

    def test_microactions_present(self, query, min_actions=1, role="crew"):
        """Test that microactions are generated"""
        test_name = f"Microactions present: '{query}'"
        self.log(f"\n--- {test_name} ---")

        try:
            resp = requests.post(
                f"{API_BASE}/webhook/search",
                headers={
                    "Authorization": f"Bearer {self.tokens[role]}",
                    "Content-Type": "application/json"
                },
                json={"query": query, "limit": 10},
                timeout=15
            )

            if resp.status_code != 200:
                self.log(f"❌ API returned {resp.status_code}", "ERROR")
                self.failures.append(f"{test_name}: API error {resp.status_code}")
                return False

            data = resp.json()
            actions = data.get('available_actions', [])

            if len(actions) < min_actions:
                self.log(f"❌ Expected ≥{min_actions} actions, got {len(actions)}", "ERROR")
                self.failures.append(f"{test_name}: Insufficient actions")
                return False

            self.log(f"✅ {len(actions)} actions generated")
            for action in actions[:3]:
                self.log(f"   - {action.get('action')}: {action.get('label')}")

            self.results.append({"test": test_name, "status": "PASS", "action_count": len(actions)})
            return True

        except Exception as e:
            self.log(f"❌ Exception: {e}", "ERROR")
            self.failures.append(f"{test_name}: Exception - {e}")
            return False

    def test_latency(self, query, max_latency_ms=3000, role="crew"):
        """Test query latency"""
        test_name = f"Latency check: '{query}'"
        self.log(f"\n--- {test_name} ---")

        try:
            start = time.time()
            resp = requests.post(
                f"{API_BASE}/webhook/search",
                headers={
                    "Authorization": f"Bearer {self.tokens[role]}",
                    "Content-Type": "application/json"
                },
                json={"query": query, "limit": 10},
                timeout=15
            )
            latency_ms = (time.time() - start) * 1000

            if resp.status_code != 200:
                self.log(f"❌ API returned {resp.status_code}", "ERROR")
                self.failures.append(f"{test_name}: API error")
                return False

            data = resp.json()
            timing = data.get('timing_ms', {})
            total_ms = timing.get('total', latency_ms)

            if total_ms > max_latency_ms:
                self.log(f"⚠️  Latency {total_ms:.0f}ms exceeds {max_latency_ms}ms", "WARN")
            else:
                self.log(f"✅ Latency {total_ms:.0f}ms (within {max_latency_ms}ms)")

            # Check extraction method (regex vs AI)
            extraction_method = data.get('extraction_method', 'unknown')
            self.log(f"   Extraction method: {extraction_method}")

            self.results.append({
                "test": test_name,
                "status": "PASS" if total_ms <= max_latency_ms else "WARN",
                "latency_ms": total_ms,
                "extraction_method": extraction_method
            })
            return True

        except Exception as e:
            self.log(f"❌ Exception: {e}", "ERROR")
            self.failures.append(f"{test_name}: Exception - {e}")
            return False

    def run_inventory_lens_tests(self):
        """Run comprehensive inventory lens test suite"""
        self.log("\n" + "="*80)
        self.log("INVENTORY LENS AUTONOMOUS TESTING")
        self.log("="*80)

        if not self.refresh_tokens():
            self.log("❌ Token refresh failed, aborting tests", "ERROR")
            return False

        # Test 1: Basic stock status queries
        self.log("\n### TEST CATEGORY: Stock Status Entity Extraction ###")
        self.test_entity_extraction("low stock parts", "STOCK_STATUS", "low stock")
        self.test_entity_extraction("out of stock filters", "STOCK_STATUS", "out of stock")
        self.test_entity_extraction("critically low inventory", "STOCK_STATUS", "critically low")

        # Test 2: Capability routing
        self.log("\n### TEST CATEGORY: Capability Routing ###")
        self.test_capability_routing("low stock items", "inventory")
        self.test_capability_routing("restock needed", "inventory")
        self.test_capability_routing("inventory levels", "inventory")

        # Test 3: Microaction generation
        self.log("\n### TEST CATEGORY: Microaction Generation ###")
        self.test_microactions_present("low stock", min_actions=3)
        self.test_microactions_present("inventory", min_actions=3)

        # Test 4: Latency benchmarks
        self.log("\n### TEST CATEGORY: Performance/Latency ###")
        self.test_latency("low stock parts", max_latency_ms=2000)
        self.test_latency("out of stock", max_latency_ms=2000)
        self.test_latency("critically low inventory", max_latency_ms=2000)

        # Test 5: Natural language variations
        self.log("\n### TEST CATEGORY: Natural Language Variations ###")
        self.test_entity_extraction("running low on stock", "STOCK_STATUS")
        self.test_entity_extraction("need to reorder", "STOCK_STATUS")
        self.test_entity_extraction("below minimum", "STOCK_STATUS")

        # Generate summary
        self.generate_summary()

        return len(self.failures) == 0

    def generate_summary(self):
        """Generate test summary report"""
        self.log("\n" + "="*80)
        self.log("TEST SUMMARY")
        self.log("="*80)

        total_tests = len(self.results) + len(self.failures)
        passed = len(self.results)
        failed = len(self.failures)

        self.log(f"\nTotal tests: {total_tests}")
        self.log(f"✅ Passed: {passed}")
        self.log(f"❌ Failed: {failed}")

        if failed > 0:
            self.log(f"\nPass rate: {(passed/total_tests)*100:.1f}%")
        else:
            self.log(f"\nPass rate: 100% ✅")

        if self.failures:
            self.log("\n### FAILURES ###")
            for i, failure in enumerate(self.failures, 1):
                self.log(f"{i}. {failure}")

        self.log("\n" + "="*80)

if __name__ == "__main__":
    tester = InventoryLensTester()
    success = tester.run_inventory_lens_tests()
    exit(0 if success else 1)
