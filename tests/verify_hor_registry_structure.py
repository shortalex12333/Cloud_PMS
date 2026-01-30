#!/usr/bin/env python3
"""
Verification Script: Crew Lens v3 Action Registry Structure
Tests that all 12 Hours of Rest actions exist in registry.py source.
"""

import re
import sys

def test_hor_registry_structure():
    """Test all 12 HoR actions are in the registry.py source."""

    print("=" * 80)
    print("TEST 4: Action Registry Source Verification")
    print("=" * 80)

    registry_file = 'apps/api/action_router/registry.py'

    # Read registry file
    with open(registry_file, 'r') as f:
        content = f.read()

    # Expected HoR actions
    expected_actions = [
        'view_hours_of_rest',
        'view_department_hours',
        'view_rest_warnings',
        'export_hours_of_rest',
        'update_hours_of_rest',
        'configure_normal_hours',
        'apply_normal_hours_to_week',
        'acknowledge_rest_violation',
        'dismiss_rest_warning',
        'crew_sign_month',
        'hod_sign_department_month',
        'master_finalize_month',
    ]

    test_results = []

    print(f"\n4.1: Checking registry.py contains all 12 HoR action definitions")

    for action_id in expected_actions:
        # Check if action_id exists as a key
        pattern = rf'"{action_id}":\s*ActionDefinition\('
        match = re.search(pattern, content)

        if match:
            print(f"  ✓ PASS: '{action_id}' definition found")
            test_results.append(True)
        else:
            print(f"  ✗ FAIL: '{action_id}' definition NOT found")
            test_results.append(False)

    # Check for domain="hours_of_rest"
    print(f"\n4.2: Checking all actions use domain='hours_of_rest'")

    hor_domain_count = len(re.findall(r'domain="hours_of_rest"', content))
    print(f"  Found {hor_domain_count} actions with domain='hours_of_rest'")

    if hor_domain_count >= 12:
        print(f"  ✓ PASS: At least 12 HoR actions have correct domain")
        test_results.append(True)
    else:
        print(f"  ✗ FAIL: Expected at least 12, found {hor_domain_count}")
        test_results.append(False)

    # Check for ActionVariant types
    print(f"\n4.3: Checking action variants")

    read_pattern = r'"(?:view_hours_of_rest|view_department_hours|view_rest_warnings|export_hours_of_rest)".*?variant=ActionVariant\.READ'
    mutate_pattern = r'"(?:update_hours_of_rest|configure_normal_hours|apply_normal_hours_to_week|acknowledge_rest_violation|dismiss_rest_warning)".*?variant=ActionVariant\.MUTATE'
    signed_pattern = r'"(?:crew_sign_month|hod_sign_department_month|master_finalize_month)".*?variant=ActionVariant\.SIGNED'

    read_count = len(re.findall(read_pattern, content, re.DOTALL))
    mutate_count = len(re.findall(mutate_pattern, content, re.DOTALL))
    signed_count = len(re.findall(signed_pattern, content, re.DOTALL))

    print(f"  Found {read_count} READ actions (expected 4)")
    print(f"  Found {mutate_count} MUTATE actions (expected 5)")
    print(f"  Found {signed_count} SIGNED actions (expected 3)")

    if read_count >= 4 and mutate_count >= 5 and signed_count >= 3:
        print(f"  ✓ PASS: All action variants present")
        test_results.append(True)
    else:
        print(f"  ✗ FAIL: Action variant counts incorrect")
        test_results.append(False)

    # Check for HandlerType.INTERNAL
    print(f"\n4.4: Checking handler type configuration")

    internal_count = 0
    for action_id in expected_actions:
        pattern = rf'"{action_id}".*?handler_type=HandlerType\.INTERNAL'
        if re.search(pattern, content, re.DOTALL):
            internal_count += 1

    print(f"  Found {internal_count}/12 actions with HandlerType.INTERNAL")

    if internal_count >= 12:
        print(f"  ✓ PASS: All HoR actions use INTERNAL handler")
        test_results.append(True)
    else:
        print(f"  ✗ FAIL: Expected 12, found {internal_count}")
        test_results.append(False)

    # Final result
    print(f"\n{'=' * 80}")
    if all(test_results):
        print("✓ ALL ACTION REGISTRY STRUCTURE TESTS PASSED")
        print(f"{'=' * 80}\n")
        return 0
    else:
        passed = sum(test_results)
        total = len(test_results)
        print(f"✗ SOME TESTS FAILED ({passed}/{total} passed)")
        print(f"{'=' * 80}\n")
        return 1


if __name__ == '__main__':
    sys.exit(test_hor_registry_structure())
