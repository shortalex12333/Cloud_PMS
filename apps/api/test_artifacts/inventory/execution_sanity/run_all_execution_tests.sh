#!/bin/bash
# Run all action execution sanity tests

echo "=========================================================================="
echo "ACTION EXECUTION SANITY TESTS"
echo "=========================================================================="
echo

# Test 1: Invalid part_id should return 400/404, not 500
echo "TEST 1: Invalid part_id handling"
echo "=========================================================================="
bash /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api/test_artifacts/inventory/execution_sanity/test_invalid_part_id.sh
echo
echo

# Test 2: Crew attempting MUTATE action should return 403
echo "TEST 2: Crew role gating (MUTATE action)"
echo "=========================================================================="
bash /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api/test_artifacts/inventory/execution_sanity/test_crew_mutate_forbidden.sh
echo
echo

# Test 3: HOD executing MUTATE action should return 200 or 404 (not 403)
echo "TEST 3: HOD role authorization (MUTATE action)"
echo "=========================================================================="
bash /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api/test_artifacts/inventory/execution_sanity/test_hod_mutate_allowed.sh
echo
echo

echo "=========================================================================="
echo "SUMMARY"
echo "=========================================================================="
echo "Test 1: Invalid part_id → 400/404 (not 500)"
echo "Test 2: Crew + MUTATE action → 403 (forbidden)"
echo "Test 3: HOD + MUTATE action → 200/404 (authorized)"
echo
echo "Response files saved to:"
echo "  - test_artifacts/inventory/execution_sanity/invalid_part_id_response.txt"
echo "  - test_artifacts/inventory/execution_sanity/crew_mutate_response.txt"
echo "  - test_artifacts/inventory/execution_sanity/hod_mutate_response.txt"
echo "=========================================================================="
