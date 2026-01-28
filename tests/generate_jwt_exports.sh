#!/bin/bash
# ============================================================================
# JWT Export Helper for Receiving Lens v1 Testing
# ============================================================================
# Purpose: Generate export commands for 15 JWT personas
# Usage: Run your JWT generator, then copy output here
# ============================================================================

cat << 'EOF'
============================================================================
JWT Export Commands for Receiving Lens v1 Testing
============================================================================

You need to generate 15 JWTs using your existing JWT generator.
Once generated, export them using the commands below.

Required personas:
1. CREW_JWT         - Basic crew member (read-only)
2. DECKHAND_JWT     - Deck crew
3. STEWARD_JWT      - Interior crew
4. ENGINEER_JWT     - Engineering crew
5. ETO_JWT          - Electrical Technical Officer
6. CHIEF_ENGINEER_JWT - HOD (Head of Department)
7. CHIEF_OFFICER_JWT  - HOD
8. CHIEF_STEWARD_JWT  - HOD
9. PURSER_JWT         - HOD
10. CAPTAIN_JWT       - Senior officer (can sign)
11. MANAGER_JWT       - Shore-based manager (can sign)
12. INACTIVE_JWT      - Inactive user (should be denied)
13. EXPIRED_JWT       - Expired token (should be denied)
14. WRONG_YACHT_JWT   - User from different yacht (RLS should filter)
15. MIXED_ROLE_JWT    - User with mixed roles (for edge case testing)

============================================================================
Template Export Commands
============================================================================

# Supabase and API config
export TENANT_1_SUPABASE_URL='https://vzsohavtuotocgrfkfyd.supabase.co'
export TENANT_1_SUPABASE_SERVICE_KEY='<your_service_key_here>'
export TEST_YACHT_ID='85fe1119-b04c-41ac-80f1-829d23322598'
export API_BASE_URL='https://pipeline-core.int.celeste7.ai'

# JWT personas (replace <token> with actual JWT)
export CREW_JWT="<generate_and_paste_token_here>"
export DECKHAND_JWT="<generate_and_paste_token_here>"
export STEWARD_JWT="<generate_and_paste_token_here>"
export ENGINEER_JWT="<generate_and_paste_token_here>"
export ETO_JWT="<generate_and_paste_token_here>"
export CHIEF_ENGINEER_JWT="<generate_and_paste_token_here>"
export CHIEF_OFFICER_JWT="<generate_and_paste_token_here>"
export CHIEF_STEWARD_JWT="<generate_and_paste_token_here>"
export PURSER_JWT="<generate_and_paste_token_here>"
export CAPTAIN_JWT="<generate_and_paste_token_here>"
export MANAGER_JWT="<generate_and_paste_token_here>"
export INACTIVE_JWT="<generate_and_paste_token_here>"
export EXPIRED_JWT="<generate_and_paste_token_here>"
export WRONG_YACHT_JWT="<generate_and_paste_token_here>"
export MIXED_ROLE_JWT="<generate_and_paste_token_here>"

============================================================================
After exporting, verify with:
============================================================================

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

============================================================================
Then run the test suite:
============================================================================

bash tests/run_receiving_evidence.sh

============================================================================
EOF
