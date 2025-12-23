#!/usr/bin/env python3
"""
Analyze V3 Audit Failures to Extract Pattern Library
=====================================================
Extracts failure clusters for pattern-led testing.
"""

import json
from collections import defaultdict
from typing import Dict, List, Tuple

def load_results(path: str) -> List[Dict]:
    """Load JSONL results."""
    results = []
    with open(path) as f:
        for line in f:
            results.append(json.loads(line))
    return results


def analyze_collisions(results: List[Dict]) -> Dict:
    """Analyze action collision patterns."""
    collision_pairs = defaultdict(list)

    for r in results:
        if "action_collision" in r["scoring_outcome"]["failure_mode_tags"]:
            exp = r["expected"]["primary_action_canonical"]
            pred = r["manual_judgement"]["router"]["predicted_primary_action"]
            collision_pairs[(exp, pred)].append({
                "id": r["id"],
                "query": r["query"],
                "matched_verb": r["manual_judgement"]["router"].get("matched_verb"),
            })

    return dict(collision_pairs)


def analyze_false_negatives(results: List[Dict]) -> Dict:
    """Analyze false negative patterns (verb_prefix_mismatch)."""
    fn_patterns = defaultdict(list)

    for r in results:
        if r["scoring_outcome"]["is_false_negative"]:
            query = r["query"]
            exp_action = r["expected"]["primary_action_canonical"]

            # Categorize by first token
            first_token = query.strip().split()[0].lower() if query.strip() else ""

            fn_patterns[first_token].append({
                "id": r["id"],
                "query": query,
                "expected_action": exp_action,
            })

    return dict(fn_patterns)


def analyze_entity_misses(results: List[Dict]) -> Dict:
    """Analyze entity extraction misses."""
    entity_miss_types = defaultdict(int)
    miss_examples = defaultdict(list)

    for r in results:
        if r["scoring_outcome"]["entity_misses"] > 0:
            expected = r["expected"].get("expected_entities", [])
            extracted_values = {e["raw_value"].lower() for e in r["manual_judgement"]["entities"]}

            for exp_entity in expected:
                value_hint = exp_entity.get("value_hint", "").lower()
                if value_hint and value_hint not in extracted_values:
                    etype = exp_entity.get("type", "unknown")
                    entity_miss_types[etype] += 1
                    if len(miss_examples[etype]) < 5:
                        miss_examples[etype].append({
                            "id": r["id"],
                            "query": r["query"][:60],
                            "missed": value_hint,
                        })

    return {
        "counts": dict(entity_miss_types),
        "examples": dict(miss_examples),
    }


def extract_pattern_library(results: List[Dict]) -> Dict:
    """
    Extract pattern library from failure analysis.

    Returns structured patterns for suite generation.
    """
    collisions = analyze_collisions(results)
    fn_patterns = analyze_false_negatives(results)
    entity_misses = analyze_entity_misses(results)

    # Group collisions by verb ambiguity
    verb_collisions = defaultdict(list)
    for (exp, pred), cases in collisions.items():
        for case in cases:
            verb = case.get("matched_verb", "unknown")
            verb_collisions[verb].append({
                "expected": exp,
                "predicted": pred,
                "query": case["query"],
            })

    # Identify noise prefix patterns from FN
    noise_prefixes = []
    for token, cases in fn_patterns.items():
        if token in ["so", "ok", "well", "right", "basically", "actually", "hey", "um", "fw:", "re:", "the"]:
            noise_prefixes.append({
                "prefix": token,
                "count": len(cases),
                "examples": [c["query"][:50] for c in cases[:3]],
            })

    # Identify verb recognition failures
    unrecognized_verbs = []
    for token, cases in fn_patterns.items():
        if token not in ["so", "ok", "well", "right", "basically", "actually", "hey", "um", "fw:", "re:", "the"]:
            # Check if it looks like a verb
            if len(cases) >= 2:
                unrecognized_verbs.append({
                    "verb": token,
                    "count": len(cases),
                    "expected_actions": list(set(c["expected_action"] for c in cases)),
                    "examples": [c["query"][:50] for c in cases[:3]],
                })

    return {
        "collision_clusters": {
            "by_verb": dict(verb_collisions),
            "top_pairs": sorted(
                [(k, len(v)) for k, v in collisions.items()],
                key=lambda x: -x[1]
            )[:15],
        },
        "fn_patterns": {
            "noise_prefixes": noise_prefixes,
            "unrecognized_verbs": sorted(unrecognized_verbs, key=lambda x: -x["count"]),
        },
        "entity_extraction": entity_misses,
        "summary": {
            "total_collisions": sum(len(v) for v in collisions.values()),
            "total_fn": sum(len(v) for v in fn_patterns.values()),
            "collision_verb_count": len(verb_collisions),
            "noise_prefix_count": len(noise_prefixes),
            "unrecognized_verb_count": len(unrecognized_verbs),
        }
    }


def main():
    results = load_results("manual_audit_v3_results.jsonl")

    print("=" * 70)
    print("V3 AUDIT FAILURE ANALYSIS")
    print("=" * 70)

    pattern_lib = extract_pattern_library(results)

    print("\n## COLLISION CLUSTERS BY VERB ##")
    for verb, cases in sorted(pattern_lib["collision_clusters"]["by_verb"].items(),
                               key=lambda x: -len(x[1]))[:10]:
        print(f"\n  Verb: '{verb}' ({len(cases)} collisions)")
        # Show unique expected→predicted pairs
        pairs = defaultdict(int)
        for c in cases:
            pairs[(c["expected"], c["predicted"])] += 1
        for (exp, pred), count in sorted(pairs.items(), key=lambda x: -x[1])[:3]:
            print(f"    {exp} → {pred}: {count}")

    print("\n\n## TOP COLLISION PAIRS ##")
    for (exp, pred), count in pattern_lib["collision_clusters"]["top_pairs"]:
        print(f"  {exp} → {pred}: {count}")

    print("\n\n## FALSE NEGATIVE PATTERNS ##")
    print("\n  Noise Prefixes:")
    for p in pattern_lib["fn_patterns"]["noise_prefixes"]:
        print(f"    '{p['prefix']}': {p['count']} cases")
        for ex in p["examples"]:
            print(f"      - {ex}")

    print("\n  Unrecognized Verbs:")
    for v in pattern_lib["fn_patterns"]["unrecognized_verbs"][:10]:
        print(f"    '{v['verb']}': {v['count']} cases → {v['expected_actions']}")

    print("\n\n## ENTITY EXTRACTION MISSES ##")
    for etype, count in sorted(pattern_lib["entity_extraction"]["counts"].items(),
                                key=lambda x: -x[1]):
        print(f"  {etype}: {count} misses")

    print("\n\n## SUMMARY ##")
    for k, v in pattern_lib["summary"].items():
        print(f"  {k}: {v}")

    # Save pattern library for suite generation
    with open("pattern_library.json", "w") as f:
        json.dump(pattern_lib, f, indent=2)

    print("\n\nPattern library saved to pattern_library.json")


if __name__ == "__main__":
    main()
