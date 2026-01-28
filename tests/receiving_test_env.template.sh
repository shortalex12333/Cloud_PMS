#!/bin/bash
# ============================================================================
# Receiving Lens v1 - Test Environment Variables
# ============================================================================
# Instructions:
# 1. Copy this file: cp receiving_test_env.template.sh receiving_test_env.sh
# 2. Fill in all JWT tokens using your JWT generator
# 3. Fill in TENANT_1_SUPABASE_SERVICE_KEY
# 4. Source the file: source tests/receiving_test_env.sh
# 5. Run tests: bash tests/run_receiving_evidence.sh
# ============================================================================

# Supabase and API Configuration
export TENANT_1_SUPABASE_URL='https://vzsohavtuotocgrfkfyd.supabase.co'
export TENANT_1_SUPABASE_SERVICE_KEY='<PASTE_YOUR_SERVICE_KEY_HERE>'
export TEST_YACHT_ID='85fe1119-b04c-41ac-80f1-829d23322598'
export API_BASE_URL='https://pipeline-core.int.celeste7.ai'

# ============================================================================
# JWT Personas (Generate using your JWT generator)
# ============================================================================

# Crew Roles (Read-only)
export CREW_JWT="<PASTE_TOKEN_HERE>"
export DECKHAND_JWT="<PASTE_TOKEN_HERE>"
export STEWARD_JWT="<PASTE_TOKEN_HERE>"
export ENGINEER_JWT="<PASTE_TOKEN_HERE>"
export ETO_JWT="<PASTE_TOKEN_HERE>"

# HOD Roles (Can mutate)
export CHIEF_ENGINEER_JWT="<PASTE_TOKEN_HERE>"
export CHIEF_OFFICER_JWT="<PASTE_TOKEN_HERE>"
export CHIEF_STEWARD_JWT="<PASTE_TOKEN_HERE>"
export PURSER_JWT="<PASTE_TOKEN_HERE>"

# Senior Roles (Can sign)
export CAPTAIN_JWT="<PASTE_TOKEN_HERE>"
export MANAGER_JWT="<PASTE_TOKEN_HERE>"

# Edge Cases (For negative testing)
export INACTIVE_JWT="<PASTE_TOKEN_HERE>"
export EXPIRED_JWT="<PASTE_TOKEN_HERE>"
export WRONG_YACHT_JWT="<PASTE_TOKEN_HERE>"
export MIXED_ROLE_JWT="<PASTE_TOKEN_HERE>"

# ============================================================================
# Verification
# ============================================================================

echo "Environment variables loaded for Receiving Lens v1 testing"
echo ""
echo "Supabase URL: $TENANT_1_SUPABASE_URL"
echo "API Base URL: $API_BASE_URL"
echo "Test Yacht ID: $TEST_YACHT_ID"
echo ""
echo "Checking JWT exports..."

[ -n "$CREW_JWT" ] && echo "✓ CREW_JWT" || echo "✗ CREW_JWT missing"
[ -n "$DECKHAND_JWT" ] && echo "✓ DECKHAND_JWT" || echo "✗ DECKHAND_JWT missing"
[ -n "$STEWARD_JWT" ] && echo "✓ STEWARD_JWT" || echo "✗ STEWARD_JWT missing"
[ -n "$ENGINEER_JWT" ] && echo "✓ ENGINEER_JWT" || echo "✗ ENGINEER_JWT missing"
[ -n "$ETO_JWT" ] && echo "✓ ETO_JWT" || echo "✗ ETO_JWT missing"
[ -n "$CHIEF_ENGINEER_JWT" ] && echo "✓ CHIEF_ENGINEER_JWT" || echo "✗ CHIEF_ENGINEER_JWT missing"
[ -n "$CHIEF_OFFICER_JWT" ] && echo "✓ CHIEF_OFFICER_JWT" || echo "✗ CHIEF_OFFICER_JWT missing"
[ -n "$CHIEF_STEWARD_JWT" ] && echo "✓ CHIEF_STEWARD_JWT" || echo "✗ CHIEF_STEWARD_JWT missing"
[ -n "$PURSER_JWT" ] && echo "✓ PURSER_JWT" || echo "✗ PURSER_JWT missing"
[ -n "$CAPTAIN_JWT" ] && echo "✓ CAPTAIN_JWT" || echo "✗ CAPTAIN_JWT missing"
[ -n "$MANAGER_JWT" ] && echo "✓ MANAGER_JWT" || echo "✗ MANAGER_JWT missing"
[ -n "$INACTIVE_JWT" ] && echo "✓ INACTIVE_JWT" || echo "✗ INACTIVE_JWT missing"
[ -n "$EXPIRED_JWT" ] && echo "✓ EXPIRED_JWT" || echo "✗ EXPIRED_JWT missing"
[ -n "$WRONG_YACHT_JWT" ] && echo "✓ WRONG_YACHT_JWT" || echo "✗ WRONG_YACHT_JWT missing"
[ -n "$MIXED_ROLE_JWT" ] && echo "✓ MIXED_ROLE_JWT" || echo "✗ MIXED_ROLE_JWT missing"

echo ""
echo "Ready to run tests: bash tests/run_receiving_evidence.sh"
