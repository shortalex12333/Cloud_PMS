# Receiving Lens v1 - Quick Start Testing Guide

**Status**: 🚀 READY TO TEST
**Date**: 2026-01-28

---

## Current State

✅ **Implementation Complete**:
- 8 migrations applied to staging DB
- All 6 DB gates passed
- 10 handlers implemented (860 lines)
- Registry and dispatcher wired
- Acceptance tests ready (8 scenarios)
- Stress test ready
- Evidence documentation ready

⏳ **Pending**: JWT generation and test execution

---

## Quick Start (3 Steps)

### Step 1: Generate and Export JWTs (5 minutes)

Use your existing JWT generator to create 15 tokens for different personas.

**Helper script**:
```bash
bash tests/generate_jwt_exports.sh
```

This will show you the template export commands. Copy them to a file like `~/.receiving_test_env` and fill in the actual tokens.

**Required personas**:
1. `CREW_JWT` - Basic crew (read-only)
2. `DECKHAND_JWT` - Deck crew
3. `STEWARD_JWT` - Interior crew
4. `ENGINEER_JWT` - Engineering crew
5. `ETO_JWT` - Electrical Technical Officer
6. `CHIEF_ENGINEER_JWT` - HOD (can mutate)
7. `CHIEF_OFFICER_JWT` - HOD (can mutate)
8. `CHIEF_STEWARD_JWT` - HOD (can mutate)
9. `PURSER_JWT` - HOD (can mutate)
10. `CAPTAIN_JWT` - Senior officer (can sign)
11. `MANAGER_JWT` - Shore-based manager (can sign)
12. `INACTIVE_JWT` - Inactive user (should be denied)
13. `EXPIRED_JWT` - Expired token (should be denied)
14. `WRONG_YACHT_JWT` - Different yacht (RLS should filter)
15. `MIXED_ROLE_JWT` - Mixed roles (edge case)

**Once generated, source the file**:
```bash
source ~/.receiving_test_env
```

### Step 2: Run Automated Test Suite (5-10 minutes)

Run the orchestrated test runner:
```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS
bash tests/run_receiving_evidence.sh
```

**What it does**:
1. ✓ Validates all 15 JWTs are set
2. ✓ Runs acceptance tests (8 scenarios)
3. ✓ Runs stress test (50 concurrent requests)
4. ✓ Generates evidence summary
5. ✓ Checks for zero 500s
6. ✓ Saves results to JSON

**Expected output**:
```
✅ ALL TESTS PASSED

Next steps:
1. Review stress test results: receiving-stress-YYYYMMDD-HHMMSS.json
2. Capture sample signed acceptance (see TESTING_EVIDENCE.md)
3. Create PR with evidence bundle
4. Deploy to production
5. Canary monitor for 30-60 minutes
```

### Step 3: Create PR with Evidence (2 minutes)

Use the pre-filled PR template:
```bash
cat docs/architecture/entity_lenses/receiving_lens/v1/PR_TEMPLATE.md
```

**Update the placeholders**:
- Stress test results (total requests, success rate, latencies)
- Any specific observations from testing

**Files to include in PR**:
- All 8 migration files
- Handler file (860 lines)
- Registry updates
- Dispatcher updates
- Test files (acceptance + stress)
- Evidence documentation
- Stress test results JSON

---

## Manual Testing (Optional)

If you want to manually verify specific scenarios:

### Test 1: Create Receiving
```bash
curl -X POST "$API_BASE_URL/v1/actions/execute" \
  -H "Authorization: Bearer $CHIEF_ENGINEER_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "create_receiving",
    "context": {"yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"},
    "payload": {
      "vendor_reference": "INV-12345",
      "received_date": "2026-01-28",
      "vendor_name": "Marine Supplies Inc"
    }
  }'
```

### Test 2: View History (with received_by info)
```bash
curl -X POST "$API_BASE_URL/v1/actions/execute" \
  -H "Authorization: Bearer $CREW_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "view_receiving_history",
    "context": {"yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"},
    "payload": {
      "receiving_id": "<receiving_id_from_step_1>"
    }
  }'
```

**Expected response includes**:
- `received_by_name`: Full name of creator
- `received_by_role`: Role of creator (e.g., "chief_engineer")
- Complete audit trail
- Documents with comments

### Test 3: Signed Acceptance (Prepare → Execute)

**Prepare**:
```bash
curl -X POST "$API_BASE_URL/v1/actions/execute" \
  -H "Authorization: Bearer $CAPTAIN_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "accept_receiving",
    "context": {"yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"},
    "payload": {
      "receiving_id": "<receiving_id>",
      "mode": "prepare"
    }
  }'
```

**Execute** (with signature):
```bash
curl -X POST "$API_BASE_URL/v1/actions/execute" \
  -H "Authorization: Bearer $CAPTAIN_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "accept_receiving",
    "context": {"yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"},
    "payload": {
      "receiving_id": "<receiving_id>",
      "mode": "execute",
      "confirmation_token": "<token_from_prepare>",
      "signature": {
        "pin": "1234",
        "totp": "123456",
        "ip_address": "192.168.1.1"
      }
    }
  }'
```

**Verify in audit log**:
```sql
SELECT
  entity_type,
  action,
  signature,
  metadata->>'source' as source,
  metadata->>'lens' as lens,
  metadata->>'session_id' as session_id
FROM pms_audit_log
WHERE entity_type = 'receiving'
  AND entity_id = '<receiving_id>'
ORDER BY created_at DESC;
```

---

## Troubleshooting

### Issue: "TEST_JWT environment variable not set"
**Fix**: Make sure you've sourced the environment file:
```bash
source ~/.receiving_test_env
```

### Issue: Acceptance test fails on extraction advisory
**Check**: Verify that `extract_receiving_candidates` does NOT auto-mutate:
```sql
-- Should return 1 record (extraction result only)
SELECT COUNT(*) FROM pms_receiving_extractions WHERE receiving_id = '<id>';

-- Should return 0 (no auto-created items)
SELECT COUNT(*) FROM pms_receiving_items WHERE receiving_id = '<id>';
```

### Issue: Storage path validation fails
**Check**: Ensure path does NOT start with `documents/`:
- ✗ Bad: `documents/85fe.../receiving/...`
- ✓ Good: `85fe.../receiving/...`

### Issue: RLS denies access
**Check**:
1. JWT is for correct yacht: `TEST_YACHT_ID=85fe1119-b04c-41ac-80f1-829d23322598`
2. User has correct role (HOD+ for mutations)
3. RLS policies are enabled: `SELECT relname, relrowsecurity FROM pg_class WHERE relname LIKE 'pms_receiving%'`

### Issue: Stress test shows 500s
**Debug**:
1. Check API logs for error details
2. Verify DB migrations applied correctly
3. Check for handler bugs in `receiving_handlers.py`
4. Run single request manually to isolate issue

---

## Success Criteria

Before creating PR, ensure:

- ✅ All 15 JWTs generated and tested
- ✅ Acceptance tests: 8/8 passing
- ✅ Stress test: Zero 500s
- ✅ Success rate: > 95%
- ✅ P50 latency: < 500ms
- ✅ P95 latency: < 2000ms
- ✅ P99 latency: < 5000ms
- ✅ DB gates: 6/6 passed
- ✅ Evidence bundle complete

---

## Deployment

Once tests pass:

1. **Create PR** using template in `PR_TEMPLATE.md`
2. **Get approval** from code reviewers
3. **Merge to main**
4. **Deploy to production**:
   ```bash
   curl -X POST "https://api.render.com/deploy/srv-d5fr5hre5dus73d3gdn0?key=Dcmb-n4O_M0"
   ```
5. **Canary monitor** on test yacht `85fe1119-b04c-41ac-80f1-829d23322598` for 30-60 minutes
6. **Monitor production logs** for 500s, RLS violations, or unexpected errors

---

## Files Reference

### Test Files
- `tests/run_receiving_evidence.sh` - Orchestrated test runner
- `tests/generate_jwt_exports.sh` - JWT export helper
- `apps/api/tests/test_receiving_lens_v1_acceptance.py` - 8 acceptance tests
- `tests/stress/stress_receiving_actions.py` - Stress test with metrics

### Documentation
- `docs/architecture/entity_lenses/receiving_lens/v1/TESTING_EVIDENCE.md` - Complete evidence bundle
- `docs/architecture/entity_lenses/receiving_lens/v1/PR_TEMPLATE.md` - PR description template
- `docs/architecture/entity_lenses/receiving_lens/v1/QUICKSTART_TESTING.md` - This file

### Implementation
- `supabase/migrations/20260128_10*.sql` - 8 migration files
- `apps/api/handlers/receiving_handlers.py` - 10 action handlers (860 lines)
- `apps/api/action_router/registry.py` - Action definitions
- `apps/api/action_router/dispatchers/internal_dispatcher.py` - Dispatcher wiring

---

**Ready to test!** 🚀

Run `bash tests/generate_jwt_exports.sh` to get started.
