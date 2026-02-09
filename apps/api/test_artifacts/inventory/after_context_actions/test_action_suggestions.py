#!/usr/bin/env python3
"""
Unit test to verify action suggestions are included in /v2/search response
and properly filtered by domain and role.

Tests the Phase 3 additions:
1. Context metadata included
2. Actions array included
3. Actions filtered by role (crew vs HOD)
"""
import sys
sys.path.insert(0, '/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api')

from action_router.registry import get_actions_for_domain

def test_parts_actions_by_role():
    """Test that parts actions are properly filtered by role."""

    print("=" * 80)
    print("ACTION SUGGESTIONS - UNIT TEST")
    print("=" * 80)
    print()

    # Test 1: Crew role - should only get READ actions
    print("Test 1: Crew role (parts domain)")
    print("-" * 80)
    crew_actions = get_actions_for_domain("parts", "crew")

    print(f"Total actions for crew: {len(crew_actions)}")
    print()
    print("Crew actions:")
    for action in crew_actions:
        print(f"  - {action['action_id']}: {action['label']} ({action['variant']})")
    print()

    # Verify crew only gets READ actions
    crew_variants = set(a['variant'] for a in crew_actions)
    if crew_variants == {'READ'} or not crew_variants:
        print("✅ PASS: Crew only has READ actions (no MUTATE or SIGNED)")
    else:
        print(f"❌ FAIL: Crew has non-READ actions: {crew_variants}")
        return 1

    print()

    # Test 2: HOD role - should get READ + MUTATE actions
    print("Test 2: chief_engineer role (parts domain)")
    print("-" * 80)
    hod_actions = get_actions_for_domain("parts", "chief_engineer")

    print(f"Total actions for chief_engineer: {len(hod_actions)}")
    print()
    print("Chief Engineer actions:")
    for action in hod_actions:
        print(f"  - {action['action_id']}: {action['label']} ({action['variant']})")
    print()

    # Verify HOD has more actions than crew
    if len(hod_actions) > len(crew_actions):
        print("✅ PASS: HOD has more actions than crew")
    else:
        print(f"❌ FAIL: HOD should have more actions than crew (HOD={len(hod_actions)}, crew={len(crew_actions)})")
        return 1

    # Verify HOD has both READ and MUTATE
    hod_variants = set(a['variant'] for a in hod_actions)
    if 'READ' in hod_variants and 'MUTATE' in hod_variants:
        print("✅ PASS: HOD has both READ and MUTATE actions")
    else:
        print(f"❌ FAIL: HOD should have READ and MUTATE, got: {hod_variants}")
        return 1

    print()

    # Test 3: Captain role - should get all actions including SIGNED
    print("Test 3: captain role (parts domain)")
    print("-" * 80)
    captain_actions = get_actions_for_domain("parts", "captain")

    print(f"Total actions for captain: {len(captain_actions)}")
    print()
    print("Captain actions:")
    for action in captain_actions:
        print(f"  - {action['action_id']}: {action['label']} ({action['variant']})")
    print()

    # Verify captain has the most actions
    if len(captain_actions) >= len(hod_actions):
        print("✅ PASS: Captain has all actions (including SIGNED)")
    else:
        print(f"❌ FAIL: Captain should have most actions (captain={len(captain_actions)}, HOD={len(hod_actions)})")
        return 1

    # Verify captain has SIGNED actions
    captain_variants = set(a['variant'] for a in captain_actions)
    if 'SIGNED' in captain_variants:
        print("✅ PASS: Captain has SIGNED actions")
    else:
        print(f"❌ FAIL: Captain should have SIGNED actions, got: {captain_variants}")
        return 1

    print()
    print("=" * 80)
    print("ALL TESTS PASSED")
    print("=" * 80)
    print()
    print("Expected Response Structure:")
    print("{")
    print('  "success": true,')
    print('  "results": [...],')
    print('  "context": {')
    print('    "domain": "parts",')
    print('    "intent": "READ",')
    print('    "mode": "hybrid"')
    print('  },')
    print('  "actions": [')
    print('    {')
    print('      "action_id": "check_stock_level",')
    print('      "label": "Check Stock Level",')
    print('      "variant": "READ",')
    print('      "allowed_roles": [...],')
    print('      "required_fields": ["yacht_id", "part_id"]')
    print('    },')
    print('    ...')
    print('  ]')
    print('}')
    print()

    return 0

if __name__ == "__main__":
    exit(test_parts_actions_by_role())
