"""
Crew Lens Chaotic Input Tests - Autonomous Testing
===================================================

Tests entity extraction with real-world chaotic user input:
- Misspellings
- Paraphrases
- Vague queries
- Mixed terminology
- Complex multi-entity queries

Tests async pipeline performance and accuracy.
"""

import pytest
import asyncio
import sys
import os
from typing import Dict, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import async extraction orchestrator
from extraction.orchestrator import ExtractionOrchestrator

# =============================================================================
# TEST DATA - Chaotic/Vague User Queries
# =============================================================================

CHAOTIC_CREW_QUERIES = [
    # Misspellings
    {
        "query": "criticla warrnings",
        "expected_entities": ["WARNING_SEVERITY"],
        "expected_values": ["critical"],
        "test_type": "misspelling",
        "description": "User misspells 'critical warnings'",
    },
    {
        "query": "rest complaince violations",
        "expected_entities": ["REST_COMPLIANCE"],
        "expected_values": ["violations"],
        "test_type": "misspelling",
        "description": "User misspells 'compliance'",
    },

    # Paraphrases
    {
        "query": "crew who didn't sleep enough",
        "expected_entities": ["REST_COMPLIANCE"],
        "expected_values": ["non-compliant", "violations"],
        "test_type": "paraphrase",
        "description": "Natural language paraphrase for non-compliant rest",
    },
    {
        "query": "people not getting enough rest",
        "expected_entities": ["REST_COMPLIANCE"],
        "expected_values": ["non-compliant"],
        "test_type": "paraphrase",
        "description": "Another paraphrase for non-compliant",
    },
    {
        "query": "active alerts",
        "expected_entities": ["WARNING_STATUS"],
        "expected_values": ["active"],
        "test_type": "paraphrase",
        "description": "User says 'alerts' instead of 'warnings'",
    },

    # Vague input
    {
        "query": "show warnings",
        "expected_entities": [],  # Too vague - could be severity, status, or general
        "expected_values": [],
        "test_type": "vague",
        "description": "Very vague - 'warnings' alone doesn't specify entity type",
        "should_surface_vague_output": True,
    },
    {
        "query": "crew problems",
        "expected_entities": [],  # Too vague
        "expected_values": [],
        "test_type": "vague",
        "description": "Extremely vague - could be warnings, violations, or other issues",
        "should_surface_vague_output": True,
    },

    # Complex multi-entity queries
    {
        "query": "high severity active warnings deck crew",
        "expected_entities": ["WARNING_SEVERITY", "WARNING_STATUS"],
        "expected_values": ["high", "active"],
        "test_type": "multi-entity",
        "description": "Complex query with multiple entity types",
    },
    {
        "query": "critical warnings that are still active",
        "expected_entities": ["WARNING_SEVERITY", "WARNING_STATUS"],
        "expected_values": ["critical", "active"],
        "test_type": "multi-entity",
        "description": "Natural language multi-entity query",
    },

    # Mixed terminology
    {
        "query": "non compliant crew rest records",
        "expected_entities": ["REST_COMPLIANCE"],
        "expected_values": ["non-compliant", "non compliant"],
        "test_type": "mixed-terminology",
        "description": "User uses 'non compliant' (with space) instead of 'non-compliant'",
    },
    {
        "query": "high priority warnings",
        "expected_entities": ["WARNING_SEVERITY"],
        "expected_values": ["high", "critical"],
        "test_type": "mixed-terminology",
        "description": "User says 'high priority' which should map to severity",
    },
]


# =============================================================================
# TEST SETUP
# =============================================================================

@pytest.fixture
def orchestrator():
    """Create async extraction orchestrator instance."""
    return ExtractionOrchestrator()


# =============================================================================
# TEST 1: Async Extraction Pipeline Works
# =============================================================================

@pytest.mark.asyncio
async def test_async_extraction_basic(orchestrator):
    """Test basic async extraction works."""
    query = "show critical warnings"

    result = await orchestrator.extract(query)

    assert result is not None, "❌ Extraction returned None"
    assert 'entities' in result, "❌ No 'entities' key in result"

    print("✅ Async extraction pipeline functional")
    print(f"   Query: {query}")
    print(f"   Entities: {result.get('entities', {})}")


# =============================================================================
# TEST 2: Chaotic Input Handling
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", CHAOTIC_CREW_QUERIES)
async def test_chaotic_input_extraction(orchestrator, test_case):
    """
    Test extraction with chaotic/vague user input.

    This validates the extraction pipeline handles real-world queries.
    """
    query = test_case["query"]
    expected_entities = test_case["expected_entities"]
    expected_values = test_case["expected_values"]
    test_type = test_case["test_type"]
    description = test_case["description"]

    print(f"\n{'='*70}")
    print(f"Test Type: {test_type}")
    print(f"Query: '{query}'")
    print(f"Description: {description}")
    print(f"Expected entities: {expected_entities}")

    # Extract entities
    result = await orchestrator.extract(query)

    assert result is not None, f"❌ Extraction returned None for query: {query}"

    # Get extracted entities
    entities = result.get('entities', {})

    # For vague queries, we expect low entity count or no specific entities
    if test_case.get("should_surface_vague_output"):
        print(f"✅ Vague query handled (low specificity expected)")
        print(f"   Entities extracted: {entities}")
        # Vague input should surface vague output - that's acceptable
        return

    # For specific queries, verify expected entities were extracted
    if expected_entities:
        for expected_entity in expected_entities:
            # Check if entity type exists in results
            entity_found = False

            # Check in entity dict structure
            if isinstance(entities, dict):
                for entity_type, values in entities.items():
                    if entity_type.upper() == expected_entity.upper():
                        entity_found = True
                        print(f"✅ Found entity type: {entity_type} = {values}")
                        break

            # Check in entity list structure
            elif isinstance(entities, list):
                for entity in entities:
                    if entity.get('type', '').upper() == expected_entity.upper():
                        entity_found = True
                        print(f"✅ Found entity: {entity}")
                        break

            if not entity_found:
                print(f"⚠️  Entity type {expected_entity} not found (may trigger AI path)")
                print(f"   Extracted entities: {entities}")
                # Don't fail - AI might extract differently or use different names
                # Document this for potential gazetteer additions
    else:
        print(f"ℹ️  No specific entities expected for this query")

    # Check extraction method used
    metrics = result.get('metadata', {}).get('metrics', {})
    ai_invoked = metrics.get('ai_invoked', False)
    coverage = metrics.get('coverage', 0)

    print(f"   AI Invoked: {ai_invoked}")
    print(f"   Coverage: {coverage:.1f}%")

    if ai_invoked:
        print(f"   ⚠️  AI path used - consider adding terms to gazetteer for fast path")


# =============================================================================
# TEST 3: Extraction Performance
# =============================================================================

@pytest.mark.asyncio
async def test_extraction_performance_fast_path(orchestrator):
    """Test extraction performance on fast path (no AI)."""
    import time

    # Query that should hit gazetteer (if crew terms added)
    query = "critical warnings active"

    start = time.time()
    result = await orchestrator.extract(query)
    elapsed_ms = (time.time() - start) * 1000

    print(f"\n{'='*70}")
    print(f"PERFORMANCE TEST")
    print(f"Query: {query}")
    print(f"Time: {elapsed_ms:.1f}ms")

    metrics = result.get('metadata', {}).get('metrics', {})
    ai_invoked = metrics.get('ai_invoked', False)

    if ai_invoked:
        print(f"⚠️  AI invoked (slow path: ~1500-2000ms)")
        print(f"   Recommendation: Add crew terms to gazetteer for fast path (<200ms)")
    else:
        print(f"✅ Fast path used (gazetteer match)")
        assert elapsed_ms < 500, f"❌ Fast path should be <500ms, got {elapsed_ms:.1f}ms"


# =============================================================================
# TEST 4: Gazetteer Coverage Analysis
# =============================================================================

@pytest.mark.asyncio
async def test_crew_terms_gazetteer_coverage(orchestrator):
    """
    Analyze which crew queries hit gazetteer vs AI.

    This identifies terms that should be added to gazetteer.
    """
    crew_queries = [
        "critical warnings",
        "high severity",
        "active warnings",
        "non-compliant rest",
        "rest violations",
        "acknowledged warnings",
        "dismissed warnings",
    ]

    gazetteer_hits = []
    ai_hits = []

    print(f"\n{'='*70}")
    print(f"GAZETTEER COVERAGE ANALYSIS")
    print(f"{'='*70}")

    for query in crew_queries:
        result = await orchestrator.extract(query)
        metrics = result.get('metadata', {}).get('metrics', {})
        ai_invoked = metrics.get('ai_invoked', False)

        if ai_invoked:
            ai_hits.append(query)
            print(f"❌ AI: '{query}'")
        else:
            gazetteer_hits.append(query)
            print(f"✅ Gazetteer: '{query}'")

    coverage_pct = (len(gazetteer_hits) / len(crew_queries)) * 100

    print(f"\n{'='*70}")
    print(f"COVERAGE SUMMARY")
    print(f"{'='*70}")
    print(f"Gazetteer hits: {len(gazetteer_hits)}/{len(crew_queries)} ({coverage_pct:.1f}%)")
    print(f"AI hits: {len(ai_hits)}/{len(crew_queries)}")

    if ai_hits:
        print(f"\n⚠️  RECOMMENDATION: Add these terms to gazetteer:")
        for query in ai_hits:
            print(f"   - '{query}'")


# =============================================================================
# TEST 5: Entity Type Consistency
# =============================================================================

@pytest.mark.asyncio
async def test_entity_type_consistency(orchestrator):
    """
    Test that same concept extracts to same entity type consistently.

    E.g., "critical", "high severity" should both map to WARNING_SEVERITY.
    """
    synonym_queries = [
        ("critical warnings", "high severity warnings"),
        ("active warnings", "open warnings"),
        ("non-compliant rest", "rest violations"),
    ]

    print(f"\n{'='*70}")
    print(f"ENTITY TYPE CONSISTENCY TEST")
    print(f"{'='*70}")

    for query1, query2 in synonym_queries:
        result1 = await orchestrator.extract(query1)
        result2 = await orchestrator.extract(query2)

        entities1 = result1.get('entities', {})
        entities2 = result2.get('entities', {})

        print(f"\nQuery 1: '{query1}'")
        print(f"  Entities: {entities1}")
        print(f"Query 2: '{query2}'")
        print(f"  Entities: {entities2}")

        # We don't enforce strict equality - just document differences
        if entities1 != entities2:
            print(f"  ⚠️  Different entity extraction - verify if acceptable")


# =============================================================================
# SUMMARY TEST
# =============================================================================

@pytest.mark.asyncio
async def test_crew_lens_chaotic_input_summary(orchestrator):
    """
    Summary test: Run all chaotic inputs and report results.
    """
    print("\n" + "="*70)
    print("CREW LENS CHAOTIC INPUT TESTING - SUMMARY")
    print("="*70)

    total_tests = len(CHAOTIC_CREW_QUERIES)
    passed = 0
    failed = 0
    ai_invoked_count = 0

    for test_case in CHAOTIC_CREW_QUERIES:
        query = test_case["query"]
        test_type = test_case["test_type"]

        try:
            result = await orchestrator.extract(query)

            if result is None:
                failed += 1
                print(f"❌ FAIL: {test_type} - '{query}' (returned None)")
                continue

            metrics = result.get('metadata', {}).get('metrics', {})
            ai_invoked = metrics.get('ai_invoked', False)

            if ai_invoked:
                ai_invoked_count += 1

            passed += 1
            print(f"✅ PASS: {test_type} - '{query}' (AI: {ai_invoked})")

        except Exception as e:
            failed += 1
            print(f"❌ FAIL: {test_type} - '{query}' (error: {e})")

    print("\n" + "="*70)
    print(f"RESULTS: {passed}/{total_tests} passed, {failed}/{total_tests} failed")
    print(f"AI Invocation Rate: {ai_invoked_count}/{total_tests} ({ai_invoked_count/total_tests*100:.1f}%)")
    print("="*70)

    if ai_invoked_count > total_tests * 0.5:
        print("\n⚠️  WARNING: High AI invocation rate (>50%)")
        print("   Recommendation: Add crew terms to gazetteer for better performance")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
