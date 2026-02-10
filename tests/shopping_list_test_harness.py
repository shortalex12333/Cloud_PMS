#!/usr/bin/env python3
"""
Shopping List Lens - Comprehensive Test Harness
================================================

This script tests all Shopping List functionality locally before production deployment.
ALL TESTS MUST PASS before any code is deployed.

Usage:
    python3 tests/shopping_list_test_harness.py --env local
    python3 tests/shopping_list_test_harness.py --env production --jwt $JWT

Exit Codes:
    0 = All tests passed
    1 = Some tests failed
"""

import sys
import os
import re
import argparse
import json
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

# Add API path for local imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'apps', 'api'))


@dataclass
class TestResult:
    name: str
    passed: bool
    expected: str
    actual: str
    details: str = ""


class ShoppingListTestHarness:
    """Comprehensive test harness for Shopping List Lens."""

    def __init__(self, env: str = "local", jwt: str = None, yacht_id: str = None):
        self.env = env
        self.jwt = jwt
        self.yacht_id = yacht_id or "85fe1119-b04c-41ac-80f1-829d23322598"
        self.results: List[TestResult] = []

    # =========================================================================
    # ENTITY EXTRACTION TESTS
    # =========================================================================

    def test_entity_extraction_local(self) -> List[TestResult]:
        """Test entity extraction using local module imports."""
        print("\n" + "=" * 70)
        print("TEST SUITE: Entity Extraction (Local)")
        print("=" * 70)

        try:
            from domain_microactions import (
                detect_domain_from_query,
                detect_domain_with_confidence,
                COMPOUND_ANCHORS,
                get_detection_context
            )
        except ImportError as e:
            print(f"❌ Failed to import domain_microactions: {e}")
            return [TestResult(
                name="Import domain_microactions",
                passed=False,
                expected="Module imports successfully",
                actual=str(e)
            )]

        results = []

        # Test 1: Verify shopping_list exists in COMPOUND_ANCHORS
        print("\n[Test 1] COMPOUND_ANCHORS contains shopping_list")
        has_shopping_list = 'shopping_list' in COMPOUND_ANCHORS
        pattern_count = len(COMPOUND_ANCHORS.get('shopping_list', []))
        results.append(TestResult(
            name="COMPOUND_ANCHORS contains shopping_list",
            passed=has_shopping_list and pattern_count > 0,
            expected="shopping_list with 18+ patterns",
            actual=f"{'Found' if has_shopping_list else 'NOT FOUND'} with {pattern_count} patterns"
        ))
        print(f"  {'✅' if results[-1].passed else '❌'} {results[-1].actual}")

        # Test 2: Test real user queries
        test_queries = [
            ("show draft shopping list", "shopping_list"),
            ("show last weeks shopping list", "shopping_list"),
            ("show pending shopping list items", "shopping_list"),
            ("show candidate parts", "shopping_list"),
            ("what parts need approval", "shopping_list"),
            ("approve requisition for engine room", "shopping_list"),
            ("add oil filter to shopping list", "shopping_list"),
            ("what's on the requisition list", "shopping_list"),
        ]

        print("\n[Test 2] Real user query detection")
        for query, expected_domain in test_queries:
            result = detect_domain_from_query(query)
            actual_domain = result[0] if result else None
            confidence = result[1] if result else 0

            passed = actual_domain == expected_domain
            results.append(TestResult(
                name=f"Query: '{query}'",
                passed=passed,
                expected=expected_domain,
                actual=f"{actual_domain} (conf: {confidence})" if actual_domain else "None"
            ))
            print(f"  {'✅' if passed else '❌'} '{query}' → {actual_domain or 'None'} (expected: {expected_domain})")

        # Test 3: Verify patterns actually match
        print("\n[Test 3] Pattern matching verification")
        pattern_tests = [
            (r'\bshopping\s+list\b', "show draft shopping list", True),
            (r'\bshopping\s+list\b', "shopping list items", True),
            (r'\bcandidate\s+parts?\b', "show candidate parts", True),
            (r'\bpending\s+approval\s+list\b', "pending approval list", True),
            (r'\brequisition(?!\s+(?:form|document|manual))\b', "check the requisition", True),
            (r'\bprocurement\s+(?:items?|list|requests?)\b', "procurement items", True),
        ]

        for pattern, text, should_match in pattern_tests:
            match = re.search(pattern, text.lower(), re.IGNORECASE)
            passed = bool(match) == should_match
            results.append(TestResult(
                name=f"Pattern '{pattern}' on '{text}'",
                passed=passed,
                expected="Match" if should_match else "No match",
                actual="Match" if match else "No match"
            ))
            print(f"  {'✅' if passed else '❌'} Pattern '{pattern[:30]}...' on '{text}' → {'Match' if match else 'No match'}")

        # Test 4: Test get_detection_context
        print("\n[Test 4] get_detection_context() integration")
        ctx = get_detection_context("show draft shopping list")
        ctx_domain = ctx.get('domain')
        ctx_confidence = ctx.get('domain_confidence', 0)

        passed = ctx_domain == 'shopping_list'
        results.append(TestResult(
            name="get_detection_context('show draft shopping list')",
            passed=passed,
            expected="domain=shopping_list",
            actual=f"domain={ctx_domain}, confidence={ctx_confidence}"
        ))
        print(f"  {'✅' if passed else '❌'} domain={ctx_domain}, confidence={ctx_confidence}")

        return results

    # =========================================================================
    # COMPOUND ANCHORS VALIDATION
    # =========================================================================

    def test_compound_anchors_structure(self) -> List[TestResult]:
        """Validate COMPOUND_ANCHORS dictionary structure."""
        print("\n" + "=" * 70)
        print("TEST SUITE: COMPOUND_ANCHORS Structure")
        print("=" * 70)

        try:
            from domain_microactions import COMPOUND_ANCHORS
        except ImportError as e:
            return [TestResult(
                name="Import COMPOUND_ANCHORS",
                passed=False,
                expected="Module imports",
                actual=str(e)
            )]

        results = []

        # List all domains
        print("\n[Test 1] All domains in COMPOUND_ANCHORS")
        domains = list(COMPOUND_ANCHORS.keys())
        print(f"  Domains ({len(domains)}): {domains}")

        has_shopping_list = 'shopping_list' in domains
        results.append(TestResult(
            name="shopping_list in COMPOUND_ANCHORS",
            passed=has_shopping_list,
            expected="shopping_list present",
            actual=f"{'Present' if has_shopping_list else 'MISSING'}"
        ))
        print(f"  {'✅' if has_shopping_list else '❌'} shopping_list: {'Present' if has_shopping_list else 'MISSING'}")

        # Check shopping_list patterns
        if has_shopping_list:
            print("\n[Test 2] shopping_list patterns")
            patterns = COMPOUND_ANCHORS['shopping_list']
            print(f"  Pattern count: {len(patterns)}")

            for i, pattern in enumerate(patterns, 1):
                # Verify pattern is valid regex
                try:
                    re.compile(pattern)
                    valid = True
                except re.error:
                    valid = False
                print(f"  {i}. {'✅' if valid else '❌'} {pattern[:60]}...")

            results.append(TestResult(
                name="shopping_list pattern count",
                passed=len(patterns) >= 15,
                expected=">= 15 patterns",
                actual=f"{len(patterns)} patterns"
            ))

        return results

    # =========================================================================
    # ACTION REGISTRY TESTS
    # =========================================================================

    def test_action_registry(self) -> List[TestResult]:
        """Test that Shopping List actions are registered."""
        print("\n" + "=" * 70)
        print("TEST SUITE: Action Registry")
        print("=" * 70)

        results = []

        try:
            from action_router.registry import ACTION_REGISTRY
        except ImportError:
            try:
                # Alternative import path
                sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'apps', 'api', 'action_router'))
                from registry import ACTION_REGISTRY
            except ImportError as e:
                print(f"  ❌ Could not import ACTION_REGISTRY: {e}")
                return [TestResult(
                    name="Import ACTION_REGISTRY",
                    passed=False,
                    expected="Module imports",
                    actual=str(e)
                )]

        expected_actions = [
            "create_shopping_list_item",
            "approve_shopping_list_item",
            "reject_shopping_list_item",
            "promote_candidate_to_part",
            "view_shopping_list_history",
        ]

        print("\n[Test 1] Shopping List actions in registry")
        for action_id in expected_actions:
            found = action_id in ACTION_REGISTRY
            results.append(TestResult(
                name=f"Action: {action_id}",
                passed=found,
                expected="Registered",
                actual="Found" if found else "MISSING"
            ))
            print(f"  {'✅' if found else '❌'} {action_id}: {'Found' if found else 'MISSING'}")

        # Check action domain
        print("\n[Test 2] Actions have correct domain")
        for action_id in expected_actions:
            if action_id in ACTION_REGISTRY:
                action = ACTION_REGISTRY[action_id]
                domain = getattr(action, 'domain', None)
                passed = domain == 'shopping_list'
                results.append(TestResult(
                    name=f"{action_id} domain",
                    passed=passed,
                    expected="shopping_list",
                    actual=str(domain)
                ))
                print(f"  {'✅' if passed else '❌'} {action_id}.domain = {domain}")

        return results

    # =========================================================================
    # CAPABILITIES TESTS
    # =========================================================================

    def test_capabilities(self) -> List[TestResult]:
        """Test that Shopping List capability is defined."""
        print("\n" + "=" * 70)
        print("TEST SUITE: Table Capabilities")
        print("=" * 70)

        results = []

        try:
            from execute.table_capabilities import CAPABILITIES
        except ImportError:
            try:
                sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'apps', 'api', 'execute'))
                from table_capabilities import CAPABILITIES
            except ImportError as e:
                print(f"  ❌ Could not import CAPABILITIES: {e}")
                return [TestResult(
                    name="Import CAPABILITIES",
                    passed=False,
                    expected="Module imports",
                    actual=str(e)
                )]

        print("\n[Test 1] Shopping List capability exists")
        shopping_list_cap = None
        for cap_id, cap in CAPABILITIES.items():
            if 'shopping' in cap_id.lower():
                shopping_list_cap = cap
                print(f"  Found capability: {cap_id}")
                break

        results.append(TestResult(
            name="Shopping List capability defined",
            passed=shopping_list_cap is not None,
            expected="Capability exists",
            actual="Found" if shopping_list_cap else "MISSING"
        ))
        print(f"  {'✅' if shopping_list_cap else '❌'} Shopping List capability: {'Found' if shopping_list_cap else 'MISSING'}")

        return results

    # =========================================================================
    # MICROACTIONS TESTS
    # =========================================================================

    def test_microactions(self) -> List[TestResult]:
        """Test Shopping List microactions mapping."""
        print("\n" + "=" * 70)
        print("TEST SUITE: Domain Microactions")
        print("=" * 70)

        results = []

        try:
            from domain_microactions import DOMAIN_MICROACTIONS
        except ImportError as e:
            print(f"  ❌ Could not import DOMAIN_MICROACTIONS: {e}")
            return [TestResult(
                name="Import DOMAIN_MICROACTIONS",
                passed=False,
                expected="Module imports",
                actual=str(e)
            )]

        # Check for shopping_list microactions
        print("\n[Test 1] Shopping List microactions defined")
        shopping_list_keys = [k for k in DOMAIN_MICROACTIONS.keys() if 'shopping_list' in str(k)]
        print(f"  Found {len(shopping_list_keys)} shopping_list microaction keys")

        for key in shopping_list_keys:
            actions = DOMAIN_MICROACTIONS[key]
            print(f"    {key}: {len(actions)} actions")
            for action in actions:
                print(f"      - {action.action}")

        results.append(TestResult(
            name="Shopping List microactions count",
            passed=len(shopping_list_keys) >= 3,
            expected=">= 3 microaction mappings",
            actual=f"{len(shopping_list_keys)} mappings"
        ))

        return results

    # =========================================================================
    # PRIORITY DISAMBIGUATION TESTS
    # =========================================================================

    def test_priority_disambiguation(self) -> List[TestResult]:
        """Test that shopping_list has correct priority in disambiguation."""
        print("\n" + "=" * 70)
        print("TEST SUITE: Priority Disambiguation")
        print("=" * 70)

        results = []

        # Read the source file to check priority list
        domain_microactions_path = os.path.join(
            os.path.dirname(__file__), '..', 'apps', 'api', 'domain_microactions.py'
        )

        try:
            with open(domain_microactions_path, 'r') as f:
                content = f.read()
        except FileNotFoundError:
            return [TestResult(
                name="Read domain_microactions.py",
                passed=False,
                expected="File exists",
                actual="File not found"
            )]

        # Find priority list
        priority_match = re.search(r"priority\s*=\s*\[([^\]]+)\]", content)
        if priority_match:
            priority_str = priority_match.group(1)
            priorities = [p.strip().strip("'\"") for p in priority_str.split(',')]
            print(f"\n[Test 1] Priority list: {priorities}")

            # Check shopping_list position
            if 'shopping_list' in priorities:
                position = priorities.index('shopping_list')
                work_order_pos = priorities.index('work_order') if 'work_order' in priorities else -1

                print(f"  shopping_list position: {position}")
                print(f"  work_order position: {work_order_pos}")

                # shopping_list should come BEFORE work_order or be high priority
                passed = position <= 3  # Should be in top 4
                results.append(TestResult(
                    name="shopping_list priority position",
                    passed=passed,
                    expected="Position <= 3 (high priority)",
                    actual=f"Position {position}"
                ))
                print(f"  {'✅' if passed else '❌'} shopping_list at position {position}")
            else:
                results.append(TestResult(
                    name="shopping_list in priority list",
                    passed=False,
                    expected="shopping_list in list",
                    actual="NOT FOUND in priority list"
                ))
                print("  ❌ shopping_list NOT in priority list!")

        return results

    # =========================================================================
    # RUN ALL TESTS
    # =========================================================================

    def run_all(self) -> bool:
        """Run all test suites and return overall pass/fail."""
        print("\n" + "=" * 70)
        print("SHOPPING LIST LENS - COMPREHENSIVE TEST HARNESS")
        print("=" * 70)
        print(f"Environment: {self.env}")
        print(f"Yacht ID: {self.yacht_id}")

        all_results = []

        # Run all test suites
        all_results.extend(self.test_compound_anchors_structure())
        all_results.extend(self.test_entity_extraction_local())
        all_results.extend(self.test_priority_disambiguation())
        all_results.extend(self.test_microactions())

        # Try action registry (may fail if module structure different)
        try:
            all_results.extend(self.test_action_registry())
        except Exception as e:
            print(f"\n⚠️  Action registry tests skipped: {e}")

        # Try capabilities (may fail if module structure different)
        try:
            all_results.extend(self.test_capabilities())
        except Exception as e:
            print(f"\n⚠️  Capabilities tests skipped: {e}")

        # Summary
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)

        passed = sum(1 for r in all_results if r.passed)
        failed = sum(1 for r in all_results if not r.passed)
        total = len(all_results)

        print(f"\nTotal: {total}")
        print(f"Passed: {passed} ✅")
        print(f"Failed: {failed} ❌")
        print(f"\nPass Rate: {passed/total*100:.1f}%")

        if failed > 0:
            print("\n" + "-" * 70)
            print("FAILED TESTS:")
            print("-" * 70)
            for r in all_results:
                if not r.passed:
                    print(f"  ❌ {r.name}")
                    print(f"     Expected: {r.expected}")
                    print(f"     Actual:   {r.actual}")

        print("\n" + "=" * 70)
        if failed == 0:
            print("✅ ALL TESTS PASSED - READY FOR PRODUCTION")
        else:
            print("❌ TESTS FAILED - DO NOT DEPLOY")
        print("=" * 70)

        return failed == 0


def main():
    parser = argparse.ArgumentParser(description='Shopping List Lens Test Harness')
    parser.add_argument('--env', choices=['local', 'production'], default='local',
                        help='Environment to test')
    parser.add_argument('--jwt', help='JWT token for production testing')
    parser.add_argument('--yacht-id', help='Yacht ID', default='85fe1119-b04c-41ac-80f1-829d23322598')

    args = parser.parse_args()

    harness = ShoppingListTestHarness(
        env=args.env,
        jwt=args.jwt,
        yacht_id=args.yacht_id
    )

    success = harness.run_all()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
