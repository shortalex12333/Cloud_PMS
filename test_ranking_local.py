#!/usr/bin/env python3
"""
Local Ranking Test (No API needed)
===================================

Tests ranking logic directly against sample data.
Demonstrates all RAG-enhanced features.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))

from execute.result_ranker import (
    rank_results,
    create_scoring_context,
    score_result,
    ScoreComponents
)


def test_ranking():
    """Test ranking system with sample data."""
    print("=" * 80)
    print("LOCAL RANKING TEST - RAG-Enhanced Features")
    print("=" * 80)

    # Test 1: Proximity Bonus
    print("\n[Test 1: Proximity Bonus]")
    print("Query: 'fuel filter MTU'")

    entities = [
        {"type": "PART", "value": "fuel filter", "confidence": 0.9},
        {"type": "MANUFACTURER", "value": "MTU", "confidence": 0.85}
    ]

    results = [
        {
            "_source_table": "pms_parts",
            "_capability": "part_by_part_number_or_name",
            "part_number": "ENG-0008-103",
            "name": "MTU fuel filter",  # Close proximity
            "description": "Compatible with MTU 12V series",
            "manufacturer": "MTU"
        },
        {
            "_source_table": "pms_parts",
            "_capability": "part_by_part_number_or_name",
            "part_number": "ENG-0009-201",
            "name": "Marine equipment catalog",  # Scattered
            "description": "Complete listing including fuel filter options for MTU and other manufacturers",
            "manufacturer": "Various"
        }
    ]

    context = create_scoring_context("fuel filter MTU", entities)
    ranked = rank_results(results, context)

    for i, result in enumerate(ranked):
        sc = result.get('score_components', {})
        print(f"\n  [{i+1}] {result.get('name')} = {result.get('_score', 0)} points")
        print(f"      Match: {sc.get('match_mode', 'UNKNOWN')} ({sc.get('match_tier', 0)})")
        print(f"      Conjunction: +{sc.get('conjunction_bonus', 0)}")
        print(f"      Proximity: +{sc.get('proximity_bonus', 0)} ⭐")
        print(f"      Intent Prior: {sc.get('intent_table_prior', 0):+d}")
        print(f"      Matched: {', '.join(sc.get('matched_entities', []))}")

    # Test 2: Catalog Detection
    print("\n" + "=" * 80)
    print("[Test 2: Catalog/TOC Penalty]")
    print("Query: 'MTU manual'")

    entities_manual = [
        {"type": "MANUFACTURER", "value": "MTU", "confidence": 0.9}
    ]

    results_catalog = [
        {
            "_source_table": "search_document_chunks",
            "_capability": "documents_search",
            "id": "1",
            "title": "Table of Contents",  # Should get -150 penalty
            "content": "Chapter 1: Introduction\nChapter 2: Specifications"
        },
        {
            "_source_table": "search_document_chunks",
            "_capability": "documents_search",
            "id": "2",
            "title": "MTU Engine Specifications",
            "content": "Step 1: Install the fuel filter\nStep 2: Check pressure"  # Procedural content
        },
        {
            "_source_table": "pms_parts",
            "_capability": "part_by_part_number_or_name",
            "part_number": "MTU-001",
            "name": "Parts Catalog",  # Should get catalog penalty
            "description": "Complete parts listing"
        }
    ]

    context_manual = create_scoring_context("MTU manual", entities_manual)
    ranked_catalog = rank_results(results_catalog, context_manual)

    for i, result in enumerate(ranked_catalog):
        sc = result.get('score_components', {})
        name = result.get('title') or result.get('name', 'Unknown')
        print(f"\n  [{i+1}] {name} = {result.get('_score', 0)} points")
        print(f"      Match: {sc.get('match_mode', 'UNKNOWN')} ({sc.get('match_tier', 0)})")
        print(f"      Intent Prior: {sc.get('intent_table_prior', 0):+d}")
        print(f"      Catalog Penalty: -{sc.get('catalog_penalty', 0)} ⭐")
        print(f"      Noise Penalty: -{sc.get('noise_penalty', 0)}")

    # Test 3: Intent-Table Priors
    print("\n" + "=" * 80)
    print("[Test 3: Intent-Table Priors]")

    test_cases = [
        ("MTU document manual", "Documents should be boosted +150"),
        ("check inventory engine room", "Inventory should be boosted +150"),
        ("diagnose fault E122", "Faults should be boosted +150"),
    ]

    for query, expected in test_cases:
        print(f"\nQuery: '{query}'")
        print(f"Expected: {expected}")

        entities_test = [{"value": "test", "confidence": 0.9}]
        context_test = create_scoring_context(query, entities_test)

        print(f"  Intent signals: {context_test.intent_signals}")
        print(f"  Is vague: {context_test.is_vague}")
        print(f"  Is diagnostic: {context_test.is_diagnostic}")

    # Test 4: Match Mode Hierarchy
    print("\n" + "=" * 80)
    print("[Test 4: Match Mode Hierarchy]")

    results_match = [
        {
            "_source_table": "search_fault_code_catalog",
            "_capability": "fault_by_fault_code",
            "code": "E122",  # Exact ID match
            "name": "Fuel pressure fault",
            "score_components": {"code_match": 1.0}
        },
        {
            "_source_table": "pms_parts",
            "_capability": "part_by_part_number_or_name",
            "part_number": "FUEL-001",
            "name": "Fuel filter E122 compatible",  # Text match only
            "description": "Works with E122 fault codes"
        }
    ]

    entities_fault = [{"value": "E122", "confidence": 0.9}]
    context_fault = create_scoring_context("fault E122", entities_fault)
    ranked_match = rank_results(results_match, context_fault)

    for i, result in enumerate(ranked_match):
        sc = result.get('score_components', {})
        name = result.get('name', 'Unknown')
        print(f"\n  [{i+1}] {name} = {result.get('_score', 0)} points")
        print(f"      Match Mode: {sc.get('match_mode', 'UNKNOWN')} ⭐")
        print(f"      Match Tier: {sc.get('match_tier', 0)} points")
        print(f"      Intent Prior: {sc.get('intent_table_prior', 0):+d}")

    # Test 5: Diagnostic Detection
    print("\n" + "=" * 80)
    print("[Test 5: Diagnostic Query Detection]")

    diagnostic_queries = [
        "main engine overheating again",
        "stern thruster making noise",
        "generator won't start"
    ]

    for query in diagnostic_queries:
        entities_diag = [{"value": "engine", "confidence": 0.9}]
        context_diag = create_scoring_context(query, entities_diag)
        print(f"\nQuery: '{query}'")
        print(f"  Is diagnostic: {context_diag.is_diagnostic} ⭐")
        print(f"  Intent signals: {context_diag.intent_signals}")

    print("\n" + "=" * 80)
    print("✅ All local ranking tests completed!")
    print("=" * 80)


if __name__ == "__main__":
    test_ranking()
