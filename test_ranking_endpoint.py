#!/usr/bin/env python3
"""
End-to-End Ranking Test
=======================

Tests the full pipeline with new ranking system against Render deployment.

Demonstrates:
1. Proximity bonus (entities close together)
2. Catalog/TOC detection (penalize list-only results)
3. Intent-table priors (boost relevant domains)
4. Diagnostic detection (handovers > manuals > parts)
5. Match mode hierarchy (EXACT_ID > EXACT_TEXT > FUZZY)
"""

import requests
import json
from typing import Dict, List, Any

# Render endpoint
ENDPOINT = "https://celeste-microactions.onrender.com"

# Test yacht ID
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"


def test_query(query: str, expected_behavior: str = "") -> Dict[str, Any]:
    """Execute test query and analyze ranking."""
    print(f"\n{'='*80}")
    print(f"QUERY: {query}")
    if expected_behavior:
        print(f"EXPECTED: {expected_behavior}")
    print('='*80)

    url = f"{ENDPOINT}/v1/pipeline/search"
    payload = {
        "yacht_id": YACHT_ID,
        "query": query
    }

    try:
        response = requests.post(url, json=payload, timeout=30)

        if not response.ok:
            print(f"❌ Error: {response.status_code}")
            return {}

        data = response.json()

        # Display results
        results = data.get('results', [])
        print(f"\n✅ Found {len(results)} results")

        # Show top 5 with score breakdown
        for i, result in enumerate(results[:5]):
            score_comp = result.get('score_components', {})

            print(f"\n[{i+1}] Score: {result.get('_score', 0)}")
            print(f"    Source: {result.get('_source_table', 'unknown')} ({result.get('_capability', 'unknown')})")

            # Show name/title
            name = result.get('name') or result.get('title') or result.get('code') or '(no name)'
            print(f"    Name: {name[:60]}")

            # Score breakdown
            if score_comp:
                print(f"    Breakdown:")
                print(f"      Match: {score_comp.get('match_mode', 'UNKNOWN')} ({score_comp.get('match_tier', 0)})")
                print(f"      Conjunction: +{score_comp.get('conjunction_bonus', 0)}")
                print(f"      Proximity: +{score_comp.get('proximity_bonus', 0)}")
                print(f"      Intent Prior: {score_comp.get('intent_table_prior', 0):+d}")
                print(f"      Catalog Penalty: -{score_comp.get('catalog_penalty', 0)}")
                print(f"      Noise Penalty: -{score_comp.get('noise_penalty', 0)}")

                matched = score_comp.get('matched_entities', [])
                if matched:
                    print(f"      Matched entities: {', '.join(matched[:3])}")

        # Show domain grouping
        results_by_domain = data.get('results_by_domain', {})
        if results_by_domain:
            print(f"\n📊 Results by Domain:")
            for domain, info in results_by_domain.items():
                count = info.get('count', 0)
                print(f"    {domain}: {count} results")

        return data

    except Exception as e:
        print(f"❌ Exception: {e}")
        return {}


def main():
    """Run comprehensive ranking tests."""
    print("""
╔════════════════════════════════════════════════════════════════════════╗
║                   RANKING SYSTEM E2E TESTS                             ║
║                  Enhanced with RAG Techniques                          ║
╚════════════════════════════════════════════════════════════════════════╝
""")

    # Test 1: Vague query (should treat all domains equally)
    test_query(
        query="fuel filter MTU",
        expected_behavior="Vague query → All domains treated equally (parts, inventory, documents)"
    )

    # Test 2: Explicit manual intent (should boost documents domain)
    test_query(
        query="MTU document manual",
        expected_behavior="Manual intent → Documents domain boosted +150, parts penalty -50"
    )

    # Test 3: Diagnostic query (should prioritize handovers > manual > parts)
    test_query(
        query="main engine overheating again",
        expected_behavior="Diagnostic query → Handovers +150, Documents +100, Parts +50"
    )

    # Test 4: Inventory intent
    test_query(
        query="check inventory in engine room",
        expected_behavior="Inventory intent → Inventory domain +150, parts +50"
    )

    # Test 5: Parts ordering intent
    test_query(
        query="order fuel filter for main engine",
        expected_behavior="Part intent → Parts domain +150, inventory +80"
    )

    # Test 6: Fault code query (exact ID match)
    test_query(
        query="fault code E122",
        expected_behavior="Exact fault code → EXACT_ID match (1000 points), faults domain +150"
    )

    # Test 7: Multi-word proximity test
    test_query(
        query="MID 128 SID 001",
        expected_behavior="Multi-token query → Smart pattern %MID%128%SID%001%, proximity bonus for clustered entities"
    )

    # Test 8: Part number exact match
    test_query(
        query="ENG-0008-103",
        expected_behavior="Exact part number → EXACT_ID match (1000 points), parts domain"
    )

    print(f"\n{'='*80}")
    print("✅ All ranking tests completed!")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
