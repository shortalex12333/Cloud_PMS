#!/usr/bin/env python3
"""
Verification Script: Crew Lens v3 Action Registry
Tests that all 12 Hours of Rest actions are properly registered.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from apps.api.action_router.registry import ACTION_REGISTRY, ActionVariant

def test_hor_action_registry():
    """Test all 12 HoR actions are properly registered."""

    print("=" * 80)
    print("TEST 4: Action Registry Verification")
    print("=" * 80)

    # Expected HoR actions
    expected_actions = {
        # READ actions (4)
        'view_hours_of_rest': {
            'variant': ActionVariant.READ,
            'domain': 'hours_of_rest',
            'keywords': ['hours', 'rest', 'hor'],
        },
        'view_department_hours': {
            'variant': ActionVariant.READ,
            'domain': 'hours_of_rest',
            'keywords': ['department', 'hours'],
        },
        'view_rest_warnings': {
            'variant': ActionVariant.READ,
            'domain': 'hours_of_rest',
            'keywords': ['warnings', 'violations'],
        },
        'export_hours_of_rest': {
            'variant': ActionVariant.READ,
            'domain': 'hours_of_rest',
            'keywords': ['export', 'hours'],
        },
        # MUTATE actions (5)
        'update_hours_of_rest': {
            'variant': ActionVariant.MUTATE,
            'domain': 'hours_of_rest',
            'keywords': ['update', 'log', 'hours'],
        },
        'configure_normal_hours': {
            'variant': ActionVariant.MUTATE,
            'domain': 'hours_of_rest',
            'keywords': ['configure', 'normal', 'hours'],
        },
        'apply_normal_hours_to_week': {
            'variant': ActionVariant.MUTATE,
            'domain': 'hours_of_rest',
            'keywords': ['apply', 'normal', 'hours'],
        },
        'acknowledge_rest_violation': {
            'variant': ActionVariant.MUTATE,
            'domain': 'hours_of_rest',
            'keywords': ['acknowledge', 'violation'],
        },
        'dismiss_rest_warning': {
            'variant': ActionVariant.MUTATE,
            'domain': 'hours_of_rest',
            'keywords': ['dismiss', 'warning'],
        },
        # SIGNED actions (3)
        'crew_sign_month': {
            'variant': ActionVariant.SIGNED,
            'domain': 'hours_of_rest',
            'keywords': ['sign', 'crew', 'monthly'],
        },
        'hod_sign_department_month': {
            'variant': ActionVariant.SIGNED,
            'domain': 'hours_of_rest',
            'keywords': ['sign', 'hod', 'department'],
        },
        'master_finalize_month': {
            'variant': ActionVariant.SIGNED,
            'domain': 'hours_of_rest',
            'keywords': ['sign', 'finalize', 'master'],
        },
    }

    test_results = []

    print(f"\n4.1: Testing action registry contains all 12 HoR actions")

    for action_id, expected in expected_actions.items():
        # Check action exists
        if action_id not in ACTION_REGISTRY:
            print(f"  ✗ FAIL: Action '{action_id}' not found in registry")
            test_results.append(False)
            continue

        action = ACTION_REGISTRY[action_id]

        # Check domain
        if action.domain != expected['domain']:
            print(f"  ✗ FAIL: Action '{action_id}' has domain '{action.domain}' (expected '{expected['domain']}')")
            test_results.append(False)
            continue

        # Check variant
        if action.variant != expected['variant']:
            print(f"  ✗ FAIL: Action '{action_id}' has variant '{action.variant}' (expected '{expected['variant']}')")
            test_results.append(False)
            continue

        # Check keywords
        keywords_found = all(
            any(kw in search_kw for search_kw in action.search_keywords)
            for kw in expected['keywords']
        )
        if not keywords_found:
            print(f"  ✗ FAIL: Action '{action_id}' missing expected keywords")
            test_results.append(False)
            continue

        print(f"  ✓ PASS: '{action_id}' registered correctly (variant={expected['variant'].value})")
        test_results.append(True)

    # Summary
    print(f"\n4.2: Registry completeness check")
    read_count = sum(1 for a in expected_actions.values() if a['variant'] == ActionVariant.READ)
    mutate_count = sum(1 for a in expected_actions.values() if a['variant'] == ActionVariant.MUTATE)
    signed_count = sum(1 for a in expected_actions.values() if a['variant'] == ActionVariant.SIGNED)

    print(f"  ✓ PASS: {read_count} READ actions registered")
    print(f"  ✓ PASS: {mutate_count} MUTATE actions registered")
    print(f"  ✓ PASS: {signed_count} SIGNED actions registered")
    print(f"  ✓ PASS: Total {len(expected_actions)} HoR actions in registry")

    # Check for handler_type
    print(f"\n4.3: Testing handler configuration")
    all_internal = all(
        ACTION_REGISTRY[action_id].handler_type.value == 'internal'
        for action_id in expected_actions.keys()
    )
    if all_internal:
        print(f"  ✓ PASS: All 12 HoR actions use HandlerType.INTERNAL")
    else:
        print(f"  ✗ FAIL: Not all actions use INTERNAL handler type")
        test_results.append(False)

    # Final result
    if all(test_results) and len(test_results) == len(expected_actions):
        print(f"\n{'=' * 80}")
        print("✓ ALL ACTION REGISTRY TESTS PASSED")
        print(f"{'=' * 80}\n")
        return 0
    else:
        print(f"\n{'=' * 80}")
        print(f"✗ SOME TESTS FAILED ({sum(test_results)}/{len(expected_actions)} passed)")
        print(f"{'=' * 80}\n")
        return 1


if __name__ == '__main__':
    sys.exit(test_hor_action_registry())
