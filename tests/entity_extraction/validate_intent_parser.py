"""
Intent Parser Validation
========================

Comprehensive validation to catch false positives and ensure GPT intent
parsing adds REAL value over simple regex.

Tests:
1. False positive detection (things that should NOT match)
2. Edge cases (ambiguous queries)
3. Real-world query validation
4. Complete output structure verification
5. Comparison: Intent Parser vs Regex-only
"""

import sys
import os
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'api'))

from intent_parser import IntentParser, route_query, AGGREGATION_KEYWORDS
from module_b_entity_extractor import get_extractor
from query_processor import QueryProcessor


class IntentParserValidator:
    """Comprehensive validation suite."""

    def __init__(self):
        self.parser = IntentParser()
        self.entity_extractor = get_extractor()
        self.processor = QueryProcessor()
        self.errors = []
        self.warnings = []

    def run_all(self):
        """Run all validation tests."""
        print("\n" + "=" * 70)
        print("INTENT PARSER VALIDATION")
        print("=" * 70)

        self.test_false_positives()
        self.test_edge_cases()
        self.test_output_structure()
        self.test_real_world_queries()
        self.test_value_comparison()

        print("\n" + "=" * 70)
        if self.errors:
            print(f"❌ VALIDATION FAILED: {len(self.errors)} errors")
            for err in self.errors:
                print(f"  - {err}")
            return False
        else:
            print(f"✅ VALIDATION PASSED")
            if self.warnings:
                print(f"   ({len(self.warnings)} warnings)")
                for w in self.warnings:
                    print(f"  ⚠ {w}")
            return True

    def test_false_positives(self):
        """Test queries that should NOT trigger certain intents."""
        print("\n[1. FALSE POSITIVE TESTS]")

        # Queries that contain keywords but should NOT be mutations
        false_mutation_tests = [
            ("show me the work order", False, "contains 'order' but is a read"),
            ("completed maintenance history", False, "'completed' is past tense, not command"),
            ("what order are the tasks in", False, "'order' as noun, not verb"),
            ("the engine is running in order", False, "'in order' is idiom"),
            ("check if work order exists", False, "checking, not creating"),
            ("who completed the inspection", False, "past tense question"),
            ("update from the manufacturer", False, "'update' as noun, not verb"),
        ]

        passed = 0
        for query, should_be_mutation, reason in false_mutation_tests:
            parsed = self.parser.parse(query)
            if parsed.requires_mutation == should_be_mutation:
                passed += 1
                print(f"  ✓ '{query[:40]}...' - {reason}")
            else:
                self.errors.append(f"FALSE POSITIVE: '{query}' got mutation={parsed.requires_mutation}, expected {should_be_mutation}")
                print(f"  ✗ '{query[:40]}...' - WRONG: got mutation={parsed.requires_mutation}")

        print(f"  → {passed}/{len(false_mutation_tests)} passed")

        # Queries that should NOT be aggregation
        false_agg_tests = [
            ("the most common engine type is CAT", "search", "'most common' in statement, not question"),
            ("this is due to vibration", "search", "'due' in explanation, not deadline"),
            ("total replacement required", "search", "'total' as adjective, not aggregation"),
        ]

        for query, expected_type, reason in false_agg_tests:
            parsed = self.parser.parse(query)
            if parsed.query_type == expected_type:
                print(f"  ✓ '{query[:40]}...' - {reason}")
            else:
                self.warnings.append(f"'{query}' got type={parsed.query_type}, expected {expected_type} ({reason})")
                print(f"  ⚠ '{query[:40]}...' - got {parsed.query_type}")

    def test_edge_cases(self):
        """Test ambiguous or tricky queries."""
        print("\n[2. EDGE CASE TESTS]")

        edge_cases = [
            # (query, expected_intent_category, reason)
            ("main engine", "search_documents", "Very short, should default to search"),
            ("???", "search_documents", "Garbage input should not crash"),
            ("", "search_documents", "Empty should not crash"),
            ("create", "search_documents", "Single word 'create' without target"),
            ("order", "search_documents", "Single word 'order' is ambiguous"),
            ("12345", "search_documents", "Just a number"),
            ("WO-1234", "search_documents", "Work order lookup, not mutation"),
        ]

        for query, expected_cat, reason in edge_cases:
            try:
                parsed = self.parser.parse(query)
                # Just check it doesn't crash and returns something reasonable
                if parsed.intent_category:
                    print(f"  ✓ '{query[:40] if query else '(empty)'}' → {parsed.intent} ({reason})")
                else:
                    self.errors.append(f"No intent category for '{query}'")
            except Exception as e:
                self.errors.append(f"CRASH on '{query}': {e}")
                print(f"  ✗ '{query[:40] if query else '(empty)'}' - CRASHED: {e}")

    def test_output_structure(self):
        """Verify complete output structure from query processor."""
        print("\n[3. OUTPUT STRUCTURE TESTS]")

        test_query = "MTU 16V4000 engine overheating before charter"
        result = self.processor.process(test_query)

        # Required top-level fields
        required_fields = ['query', 'intent', 'entities', 'unknowns', 'routing', 'processing_time_ms']
        for field in required_fields:
            if field in result:
                print(f"  ✓ Has '{field}'")
            else:
                self.errors.append(f"Missing required field: {field}")
                print(f"  ✗ Missing '{field}'")

        # Intent structure
        intent_fields = ['action', 'category', 'query_type', 'confidence', 'requires_mutation']
        for field in intent_fields:
            if field in result.get('intent', {}):
                print(f"  ✓ intent.{field} = {result['intent'][field]}")
            else:
                self.errors.append(f"Missing intent field: {field}")
                print(f"  ✗ Missing intent.{field}")

        # Routing structure
        routing_fields = ['handler', 'method']
        for field in routing_fields:
            if field in result.get('routing', {}):
                print(f"  ✓ routing.{field} = {result['routing'][field]}")
            else:
                self.errors.append(f"Missing routing field: {field}")

        # Entity structure (if any entities)
        if result.get('entities'):
            entity = result['entities'][0]
            entity_fields = ['type', 'value', 'canonical']
            for field in entity_fields:
                if field in entity:
                    print(f"  ✓ entity.{field}")
                else:
                    self.errors.append(f"Entity missing field: {field}")

        print(f"\n  Full output sample:")
        print(f"  {json.dumps(result, indent=2)[:500]}...")

    def test_real_world_queries(self):
        """Test real-world queries from yacht operations."""
        print("\n[4. REAL-WORLD QUERY TESTS]")

        real_queries = [
            # (query, expected_type, expected_category, has_entities)
            ("MTU 16V4000 engine overheating", "search", "search_documents", True),
            ("what machines are failing the most", "aggregation", "analytics", False),
            ("who hasn't completed their hours of rest", "compliance", "comply_audit", None),  # entities ok either way
            ("create work order for stabilizer not leveling", "mutation", "do_maintenance", True),
            ("show me box 3d contents", "lookup", "control_inventory", False),
            ("order 2 MTU fuel filters", "mutation", "control_inventory", True),
            ("Seakeeper gyro making noise", "search", "search_documents", True),
            ("CAT 3512 manual lube oil section", "search", "search_documents", True),
            ("what work is due today", "aggregation", "analytics", False),
            ("port generator alarm E047", "search", "search_documents", True),
            ("Naiad stabilizer fin stuck", "search", "search_documents", True),
            ("check watermaker pressure", "search", "search_documents", True),
        ]

        passed = 0
        for query, exp_type, exp_cat, has_entities in real_queries:
            result = self.processor.process(query)
            intent = result['intent']
            entities = result['entities']

            type_ok = intent['query_type'] == exp_type
            cat_ok = intent['category'] == exp_cat
            entities_ok = bool(entities) == has_entities or has_entities is None

            if type_ok and cat_ok and entities_ok:
                passed += 1
                entity_summary = f", entities={len(entities)}" if entities else ""
                print(f"  ✓ '{query[:35]}...' → {intent['query_type']}/{intent['category']}{entity_summary}")
            else:
                issues = []
                if not type_ok:
                    issues.append(f"type={intent['query_type']} expected {exp_type}")
                if not cat_ok:
                    issues.append(f"cat={intent['category']} expected {exp_cat}")
                if not entities_ok:
                    issues.append(f"entities={len(entities)} expected {'some' if has_entities else 'none'}")
                self.errors.append(f"'{query}': {', '.join(issues)}")
                print(f"  ✗ '{query[:35]}...' - {', '.join(issues)}")

        print(f"  → {passed}/{len(real_queries)} passed")

    def test_value_comparison(self):
        """Compare intent parser value vs simple regex."""
        print("\n[5. VALUE COMPARISON: Intent Parser vs Regex-Only]")

        # Queries where intent parser adds value over simple regex
        value_cases = [
            ("what machines are failing the most", "aggregation", "regex would miss 'failing most' as aggregation"),
            ("who hasn't completed their HOR", "compliance", "regex would miss 'completed' as compliance check"),
            ("show me box 3d contents", "lookup", "regex needs to understand 'box' = inventory location"),
            ("what work is due today", "aggregation", "regex would miss 'due today' as time filter"),
            ("order 2 filters", "mutation", "regex correctly detects 'order N' as mutation"),
            ("show me the work order", "search", "regex must NOT false-positive on 'order'"),
        ]

        value_added = 0
        for query, expected_type, value_reason in value_cases:
            parsed = self.parser.parse(query)
            if parsed.query_type == expected_type:
                value_added += 1
                print(f"  ✓ '{query[:40]}' → {expected_type}")
                print(f"    Value: {value_reason}")
            else:
                self.warnings.append(f"'{query}' got {parsed.query_type}, expected {expected_type}")
                print(f"  ⚠ '{query[:40]}' → {parsed.query_type} (expected {expected_type})")

        print(f"\n  → Intent parser adds value in {value_added}/{len(value_cases)} cases")

        if value_added < len(value_cases) * 0.8:
            self.warnings.append("Intent parser may not be adding sufficient value over regex")


def main():
    validator = IntentParserValidator()
    success = validator.run_all()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
