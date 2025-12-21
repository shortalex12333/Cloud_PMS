"""
Intent Parser Tests
===================

Tests for the intent classification and routing system.
Validates that queries are correctly classified into 67 intents
and routed to the appropriate handler (Render vs n8n).
"""

import sys
import os

# Add parent directories to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'api'))

from intent_parser import IntentParser, route_query, INTENT_CATEGORIES, MUTATION_INTENTS


class IntentParserTests:
    """Test suite for intent parser."""

    def __init__(self):
        self.parser = IntentParser()
        self.passed = 0
        self.failed = 0
        self.errors = []

    def test(self, name: str, condition: bool, details: str = ""):
        """Record test result."""
        if condition:
            self.passed += 1
            print(f"  ✓ {name}")
        else:
            self.failed += 1
            self.errors.append(f"{name}: {details}")
            print(f"  ✗ {name}: {details}")

    def run_all(self):
        """Run all test suites."""
        print("\n" + "=" * 70)
        print("INTENT PARSER TEST SUITE")
        print("=" * 70)

        self.test_aggregation_queries()
        self.test_compliance_queries()
        self.test_mutation_queries()
        self.test_lookup_queries()
        self.test_search_queries()
        self.test_routing()
        self.test_intent_categories()

        print("\n" + "=" * 70)
        print(f"RESULTS: {self.passed} passed, {self.failed} failed")
        print("=" * 70)

        if self.failed > 0:
            print("\nFailed tests:")
            for err in self.errors:
                print(f"  - {err}")

        return self.failed == 0

    def test_aggregation_queries(self):
        """Test aggregation query classification."""
        print("\n[Aggregation Queries]")

        test_cases = [
            ("what machines are failing the most", "aggregation"),
            ("how many work orders are overdue", "aggregation"),
            ("show me the most common faults", "aggregation"),
            ("what work is due today", "aggregation"),
            ("which equipment has the most failures", "aggregation"),
        ]

        for query, expected_type in test_cases:
            parsed = self.parser.parse(query)
            self.test(
                f"'{query[:40]}...' → {expected_type}",
                parsed.query_type == expected_type,
                f"got {parsed.query_type}"
            )

    def test_compliance_queries(self):
        """Test compliance query classification."""
        print("\n[Compliance Queries]")

        test_cases = [
            ("who hasn't completed their hours of rest", "compliance"),
            ("show me HOR status", "compliance"),
            ("who is out of compliance", "compliance"),
            ("certificate expiry dates", "compliance"),
        ]

        for query, expected_type in test_cases:
            parsed = self.parser.parse(query)
            self.test(
                f"'{query[:40]}...' → {expected_type}",
                parsed.query_type == expected_type,
                f"got {parsed.query_type}"
            )

    def test_mutation_queries(self):
        """Test mutation query classification."""
        print("\n[Mutation Queries]")

        test_cases = [
            ("create work order for main engine", True),
            ("order 2 MTU fuel filters", True),
            ("add note to handover", True),
            ("update hours of rest for John", True),
            ("mark work order complete", True),
            # Non-mutations
            ("show me the work order", False),
            ("what is the main engine status", False),
        ]

        for query, requires_mutation in test_cases:
            parsed = self.parser.parse(query)
            self.test(
                f"'{query[:40]}...' mutation={requires_mutation}",
                parsed.requires_mutation == requires_mutation,
                f"got requires_mutation={parsed.requires_mutation}"
            )

    def test_lookup_queries(self):
        """Test lookup query classification."""
        print("\n[Lookup Queries]")

        test_cases = [
            ("show me box 3d contents", "lookup"),
            ("where is the oil filter", "lookup"),
            ("check stock of fuel filters", "lookup"),
            ("inventory for part 12345", "lookup"),
        ]

        for query, expected_type in test_cases:
            parsed = self.parser.parse(query)
            self.test(
                f"'{query[:40]}...' → {expected_type}",
                parsed.query_type == expected_type,
                f"got {parsed.query_type}"
            )

    def test_search_queries(self):
        """Test search query classification."""
        print("\n[Search Queries]")

        test_cases = [
            ("MTU 16V4000 engine overheating", "search"),
            ("Seakeeper manual", "search"),
            ("CAT 3512 lube oil section", "search"),
        ]

        for query, expected_type in test_cases:
            parsed = self.parser.parse(query)
            self.test(
                f"'{query[:40]}...' → {expected_type}",
                parsed.query_type == expected_type,
                f"got {parsed.query_type}"
            )

    def test_routing(self):
        """Test routing to correct handler."""
        print("\n[Routing]")

        # Mutations should go to n8n
        mutation_queries = [
            ("create work order for stabilizer", "n8n"),
            ("order part for generator", "n8n"),
        ]

        for query, expected_handler in mutation_queries:
            parsed = self.parser.parse(query)
            routing = route_query(parsed)
            self.test(
                f"'{query[:40]}...' → {expected_handler}",
                routing['handler'] == expected_handler,
                f"got {routing['handler']}"
            )

        # Non-mutations should go to render
        read_queries = [
            ("what machines are failing", "render"),
            ("show me box 3d contents", "render"),
            ("who hasn't completed HOR", "render"),
        ]

        for query, expected_handler in read_queries:
            parsed = self.parser.parse(query)
            routing = route_query(parsed)
            self.test(
                f"'{query[:40]}...' → {expected_handler}",
                routing['handler'] == expected_handler,
                f"got {routing['handler']}"
            )

    def test_intent_categories(self):
        """Test that intent categories are properly defined."""
        print("\n[Intent Categories]")

        # Count total intents
        total_intents = sum(len(intents) for intents in INTENT_CATEGORIES.values())
        self.test(
            f"Total intents defined ({total_intents})",
            total_intents >= 60,  # Should have 67 intents
            f"expected >= 60, got {total_intents}"
        )

        # Check expected categories exist
        expected_categories = [
            "fix_something",
            "do_maintenance",
            "manage_equipment",
            "control_inventory",
            "communicate_status",
            "comply_audit",
            "procure_suppliers",
            "analytics",
        ]

        for cat in expected_categories:
            self.test(
                f"Category '{cat}' exists",
                cat in INTENT_CATEGORIES,
                "category missing"
            )

        # Check mutation intents are defined
        self.test(
            f"Mutation intents defined ({len(MUTATION_INTENTS)})",
            len(MUTATION_INTENTS) >= 15,
            f"expected >= 15, got {len(MUTATION_INTENTS)}"
        )


def main():
    """Run all tests."""
    tests = IntentParserTests()
    success = tests.run_all()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
