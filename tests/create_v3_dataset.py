#!/usr/bin/env python3
"""
Create V3 Dataset with Label Corrections
=========================================
Fixes:
1. "hey show me the um manual" cases → should_trigger_action: true
2. Validates "check" cases remain as negative controls (router fix needed)
"""

import json
import re
from typing import Dict, List

# Pattern A: Cases that SHOULD trigger but are mislabeled
RELABEL_TO_TRUE_PATTERNS = [
    # "hey show me the um manual for X" should trigger show_manual_section
    (r"^hey\s+show\s+me\s+the\s+um\s+manual", "show_manual_section"),
]

# Pattern B: "check" without inventory context should NOT trigger
# These are correctly labeled as false in dataset, but router is wrong
# We don't change dataset labels, we fix the router

def should_relabel_to_true(query: str) -> tuple:
    """Check if query should be relabeled to trigger=true."""
    query_lower = query.lower().strip()
    for pattern, action in RELABEL_TO_TRUE_PATTERNS:
        if re.match(pattern, query_lower):
            return True, action
    return False, None


def create_v3_dataset(input_path: str, output_path: str) -> Dict:
    """Create V3 dataset with corrected labels."""
    with open(input_path) as f:
        dataset = json.load(f)

    cases = dataset["cases"]
    corrections = []

    for case in cases:
        query = case["query"]
        original_trigger = case["expected"]["should_trigger_action"]
        original_action = case["expected"]["primary_action"]

        should_fix, new_action = should_relabel_to_true(query)

        if should_fix and not original_trigger:
            # Relabel this case
            corrections.append({
                "id": case["id"],
                "query": query,
                "original": {
                    "should_trigger_action": original_trigger,
                    "primary_action": original_action,
                },
                "corrected": {
                    "should_trigger_action": True,
                    "primary_action": new_action,
                }
            })

            case["expected"]["should_trigger_action"] = True
            case["expected"]["primary_action"] = new_action

    # Update metadata
    dataset["metadata"] = dataset.get("metadata", {})
    dataset["metadata"]["version"] = "3.0"
    dataset["metadata"]["corrections_applied"] = len(corrections)
    dataset["metadata"]["correction_types"] = [
        "hey_show_manual_relabel"
    ]

    # Write corrected dataset
    with open(output_path, 'w') as f:
        json.dump(dataset, f, indent=2)

    # Write correction log
    with open("v3_corrections_log.json", 'w') as f:
        json.dump({
            "total_corrections": len(corrections),
            "corrections": corrections
        }, f, indent=2)

    print(f"V3 Dataset created: {output_path}")
    print(f"Total corrections: {len(corrections)}")

    return {
        "total_cases": len(cases),
        "corrections": len(corrections),
        "correction_details": corrections
    }


if __name__ == "__main__":
    result = create_v3_dataset(
        "stress_test_dataset_v2.json",
        "stress_test_dataset_v3.json"
    )

    print("\nCorrections applied:")
    for c in result["correction_details"]:
        print(f"  {c['id']}: {c['query'][:50]}...")
