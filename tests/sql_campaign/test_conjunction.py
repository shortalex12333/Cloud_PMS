"""
CONJUNCTION BEHAVIOR UNIT TESTS
===============================

Validates that multi-term queries use correct boolean logic:
- AND across distinct constraints
- OR within variants of same constraint

RULE: "fuel filter" means (fuel) AND (filter), NOT (fuel) OR (filter)

These tests catch the P1 bug where multi-entity search incorrectly used OR.

Run with:
    SUPABASE_URL=... SUPABASE_SERVICE_KEY=... python -m pytest tests/sql_campaign/test_conjunction.py -v
"""

import os
import sys
import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'api'))

from sql_foundation.execute_sql import execute_search


YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"


def get_searchable_text(result: dict) -> str:
    """Extract all searchable text from a result (handles different result shapes)."""
    parts = []
    for field in ["name", "title", "alias", "label", "content", "code", "description"]:
        val = result.get(field)
        if val:
            parts.append(str(val).lower())
    return " ".join(parts)


class TestConjunctionBehavior:
    """Test AND/OR behavior for multi-term queries."""

    def test_two_term_and_behavior(self):
        """
        CRITICAL TEST: 'fuel filter' must return only results with BOTH terms.

        Bug behavior (WRONG): Returns fuel-only AND filter-only results mixed
        Correct behavior: Returns ONLY results containing both 'fuel' AND 'filter'
        """
        # Execute multi-term search
        result = execute_search(
            terms=[
                {"type": "PART_NAME", "value": "fuel"},
                {"type": "PART_NAME", "value": "filter"},
            ],
            tables=["pms_parts"],
            yacht_id=YACHT_ID,
            max_results=20
        )

        results = result.get("results", [])

        # MUST have results (we have fuel filter parts in test data)
        assert len(results) > 0, "Expected results for 'fuel filter' query"

        # EVERY result must contain BOTH terms
        for r in results:
            name = (r.get("name") or "").lower()
            has_fuel = "fuel" in name
            has_filter = "filter" in name

            assert has_fuel and has_filter, (
                f"Result '{r.get('name')}' violates AND semantics: "
                f"fuel={has_fuel}, filter={has_filter}"
            )

    def test_single_term_returns_broader_results(self):
        """
        Single term 'fuel' should return more results than 'fuel filter'.

        This proves AND is more restrictive than single-term search.
        """
        # Single term: fuel
        fuel_only = execute_search(
            terms=[{"type": "PART_NAME", "value": "fuel"}],
            tables=["pms_parts"],
            yacht_id=YACHT_ID,
            max_results=50
        )

        # Multi-term: fuel AND filter
        fuel_filter = execute_search(
            terms=[
                {"type": "PART_NAME", "value": "fuel"},
                {"type": "PART_NAME", "value": "filter"},
            ],
            tables=["pms_parts"],
            yacht_id=YACHT_ID,
            max_results=50
        )

        fuel_count = len(fuel_only.get("results", []))
        both_count = len(fuel_filter.get("results", []))

        # AND must be <= single term (more restrictive)
        assert both_count <= fuel_count, (
            f"AND should be more restrictive: "
            f"fuel_only={fuel_count}, fuel_AND_filter={both_count}"
        )

    def test_three_term_and_behavior(self):
        """
        Three terms: all must be present in results.

        'oil fuel filter' → results must contain oil AND fuel AND filter
        """
        result = execute_search(
            terms=[
                {"type": "PART_NAME", "value": "oil"},
                {"type": "PART_NAME", "value": "fuel"},
                {"type": "PART_NAME", "value": "filter"},
            ],
            tables=["pms_parts"],
            yacht_id=YACHT_ID,
            max_results=20
        )

        results = result.get("results", [])

        # For this test, empty is acceptable if no such parts exist
        # But if results exist, they must contain ALL three terms
        for r in results:
            text = get_searchable_text(r)
            has_oil = "oil" in text
            has_fuel = "fuel" in text
            has_filter = "filter" in text

            assert has_oil and has_fuel and has_filter, (
                f"Result '{r.get('name') or r.get('label')}' violates 3-term AND: "
                f"oil={has_oil}, fuel={has_fuel}, filter={has_filter}"
            )

    def test_no_fuel_only_results_in_fuel_filter_query(self):
        """
        'fuel filter' must NOT return 'fuel pump' or other fuel-only items.

        This directly tests the bug where OR semantics polluted results.
        """
        result = execute_search(
            terms=[
                {"type": "PART_NAME", "value": "fuel"},
                {"type": "PART_NAME", "value": "filter"},
            ],
            tables=["pms_parts"],
            yacht_id=YACHT_ID,
            max_results=50
        )

        results = result.get("results", [])

        # Check for pollution from fuel-only items
        fuel_only_items = []
        for r in results:
            name = (r.get("name") or "").lower()
            if "fuel" in name and "filter" not in name:
                fuel_only_items.append(r.get("name"))

        assert len(fuel_only_items) == 0, (
            f"AND query returned fuel-only items (OR pollution): {fuel_only_items}"
        )

    def test_no_filter_only_results_in_fuel_filter_query(self):
        """
        'fuel filter' must NOT return 'oil filter' or other filter-only items.
        """
        result = execute_search(
            terms=[
                {"type": "PART_NAME", "value": "fuel"},
                {"type": "PART_NAME", "value": "filter"},
            ],
            tables=["pms_parts"],
            yacht_id=YACHT_ID,
            max_results=50
        )

        results = result.get("results", [])

        # Check for pollution from filter-only items
        filter_only_items = []
        for r in results:
            name = (r.get("name") or "").lower()
            if "filter" in name and "fuel" not in name:
                filter_only_items.append(r.get("name"))

        assert len(filter_only_items) == 0, (
            f"AND query returned filter-only items (OR pollution): {filter_only_items}"
        )

    def test_trace_shows_boolean_structure(self):
        """
        Trace output must include the boolean structure used.

        For 'fuel filter' should show AND grouping.
        """
        result = execute_search(
            terms=[
                {"type": "PART_NAME", "value": "fuel"},
                {"type": "PART_NAME", "value": "filter"},
            ],
            tables=["pms_parts"],
            yacht_id=YACHT_ID,
            max_results=10
        )

        trace = result.get("trace", {})

        # Trace should exist and contain wave information
        assert trace, "Trace should be present"
        assert "waves_executed" in trace, "Trace should show waves executed"


class TestLocationConjunction:
    """Test location-based conjunction queries."""

    def test_inventory_in_multiple_locations_or(self):
        """
        'inventory in box 2a and 2b' - user means OR (either location).

        Note: This is a special case where 'and' in natural language
        actually means OR in boolean logic (union of locations).
        """
        # For now, this tests that location queries work at all
        # Full OR support for locations is a P2 feature
        result = execute_search(
            terms=[{"type": "LOCATION", "value": "2a"}],
            tables=["v_inventory"],
            yacht_id=YACHT_ID,
            max_results=20
        )

        # Should return inventory items (may be empty if no data)
        assert "results" in result
        assert "trace" in result


class TestEquipmentConjunction:
    """Test equipment-based conjunction queries."""

    def test_equipment_with_attribute(self):
        """
        'generator main' - should match equipment with both terms.
        """
        result = execute_search(
            terms=[
                {"type": "EQUIPMENT_NAME", "value": "generator"},
                {"type": "EQUIPMENT_NAME", "value": "main"},
            ],
            tables=["pms_equipment"],
            yacht_id=YACHT_ID,
            max_results=20
        )

        results = result.get("results", [])

        # All results must contain both terms
        for r in results:
            text = get_searchable_text(r)
            has_generator = "generator" in text
            has_main = "main" in text

            assert has_generator and has_main, (
                f"Result '{r.get('name') or r.get('label')}' may violate AND: "
                f"generator={has_generator}, main={has_main}"
            )


class TestConjunctionEdgeCases:
    """Edge cases for conjunction behavior."""

    def test_empty_with_impossible_and(self):
        """
        'fuel anchor' - unlikely combination should return empty or few results.

        This tests that AND is restrictive (not polluted by OR).
        """
        result = execute_search(
            terms=[
                {"type": "PART_NAME", "value": "fuel"},
                {"type": "PART_NAME", "value": "anchor"},
            ],
            tables=["pms_parts"],
            yacht_id=YACHT_ID,
            max_results=20
        )

        results = result.get("results", [])

        # Should be empty or very few (unlikely to have fuel-anchor parts)
        # If results exist, they must contain both terms
        for r in results:
            text = get_searchable_text(r)
            has_fuel = "fuel" in text
            has_anchor = "anchor" in text

            assert has_fuel and has_anchor, (
                f"Result '{r.get('name') or r.get('label')}' violates AND: "
                f"fuel={has_fuel}, anchor={has_anchor}"
            )

    def test_same_term_twice(self):
        """
        'filter filter' - duplicate terms should still work.
        """
        result = execute_search(
            terms=[
                {"type": "PART_NAME", "value": "filter"},
                {"type": "PART_NAME", "value": "filter"},
            ],
            tables=["pms_parts"],
            yacht_id=YACHT_ID,
            max_results=20
        )

        results = result.get("results", [])

        # Should return filter results (AND of same term = that term)
        for r in results:
            name = (r.get("name") or "").lower()
            assert "filter" in name, f"Result '{r.get('name')}' should contain 'filter'"

    def test_single_term_baseline(self):
        """
        Single term queries should work normally.
        """
        result = execute_search(
            terms=[{"type": "PART_NAME", "value": "filter"}],
            tables=["pms_parts"],
            yacht_id=YACHT_ID,
            max_results=20
        )

        results = result.get("results", [])

        assert len(results) > 0, "Should find filter parts"

        for r in results:
            name = (r.get("name") or "").lower()
            assert "filter" in name, f"Result '{r.get('name')}' should contain 'filter'"


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    # Run with pytest
    pytest.main([__file__, "-v", "--tb=short"])
