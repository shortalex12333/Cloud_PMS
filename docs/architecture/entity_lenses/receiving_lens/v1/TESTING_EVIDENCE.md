# Receiving Lens v1 - Testing Evidence

**Date**: 2026-01-28
**Status**: ✅ READY FOR TESTING

---

## DB Gates - ALL PASSED ✅

### Gate 1: RLS Enabled
```
relname                   | relrowsecurity
--------------------------+----------------
doc_metadata              | t
pms_entity_links          | t
pms_receiving             | t
pms_receiving_documents   | t
pms_receiving_extractions | t
pms_receiving_items       | t
```
**Result**: ✅ 6/6 tables have RLS enabled

### Gate 2: RLS Policies
**21 policies** created for receiving tables:
- `pms_receiving`: 4 policies (select_yacht, insert_hod, update_hod, service_role)
- `pms_receiving_items`: 4 policies
- `pms_receiving_documents`: 3 policies
- `pms_receiving_extractions`: 3 policies
- `pms_entity_links`: 7 policies

**Result**: ✅ All tables deny-by-default with yacht-scoped SELECT, HOD+ INSERT/UPDATE

### Gate 3: Storage Policies
**15 policies** for receiving storage:
- `hod_insert_yacht_documents`, `hod_update_yacht_documents`, `manager_delete_yacht_documents`
- `crew_insert_receiving_images`, `crew_select_receiving_images`
- `hod_insert_receiving_images`, `hod_update_receiving_images`, `hod_delete_receiving_images`
- Service role bypass policies

**Result**: ✅ Storage isolation enforced at RLS level

### Gate 4: Schema Verification
**pms_receiving table**:
- Status CHECK: `draft`, `in_review`, `accepted`, `rejected` ✓
- `received_by UUID NOT NULL` column ✓
- `created_by UUID` column ✓
- 5 indexes created (yacht_date, yacht_status, yacht_vendor_ref, work_order) ✓
- Foreign key cascades to yacht_registry ✓

**Result**: ✅ Schema matches specification exactly

### Gate 5: Comment Column
```sql
SELECT column_name, data_type FROM information_schema.columns
WHERE table_name='pms_receiving_documents' AND column_name='comment';

column_name | data_type
------------+-----------
comment     | text
```
**Result**: ✅ Comment column exists

### Gate 6: Signature Invariant
```sql
SELECT COUNT(*) FROM pms_audit_log WHERE entity_type='receiving' AND signature IS NULL;

null_signatures
-----------------
0
```
**Result**: ✅ No NULL signatures (constraint enforced)

---

## Implementation Summary

### Files Created

**Database Migrations (8 files)**:
```
supabase/migrations/
├── 20260128_101_receiving_helpers_if_missing.sql (Helper verification)
├── 20260128_102_receiving_tables.sql (4 tables)
├── 20260128_103_receiving_checks.sql (Status/quantity constraints)
├── 20260128_104_receiving_rls.sql (RLS policies)
├── 20260128_105_receiving_indexes.sql (11 indexes)
├── 20260128_111_documents_storage_policies_receiving.sql (Documents bucket)
├── 20260128_112_receiving_images_storage_policies.sql (pms-receiving-images bucket)
└── 20260128_113_doc_metadata_receiving_rls.sql (doc_metadata verification)
```

**Backend Code**:
```
apps/api/
├── handlers/receiving_handlers.py (860 lines, 10 actions)
├── action_router/registry.py (+250 lines, 10 action definitions)
└── action_router/dispatchers/internal_dispatcher.py (+120 lines, 10 wrappers)
```

**Test Files**:
```
apps/api/tests/test_receiving_lens_v1_acceptance.py (8 test scenarios)
tests/stress/stress_receiving_actions.py (Stress test with P50/P95/P99 metrics)
```

---

## Test Plan

### Acceptance Tests (8 Scenarios)

1. **Extraction Advisory Only**
   - `extract_receiving_candidates` writes to `pms_receiving_extractions`
   - No auto-mutation of `pms_receiving` or `pms_receiving_items`
   - User must explicitly call `update_receiving_fields` or `add_receiving_item`

2. **Storage Path Validation**
   - Path starting with `documents/` → 400 INVALID_STORAGE_PATH
   - Canonical path `{yacht_id}/receiving/{receiving_id}/{filename}` → 200

3. **Signed Acceptance (Prepare → Execute)**
   - Prepare mode returns `confirmation_token` and `proposed_changes`
   - Execute without signature → 400 SIGNATURE_REQUIRED
   - Execute with PIN+TOTP → 200, status='accepted', signed audit

4. **Role/RLS Enforcement**
   - Crew mutation → 403
   - HOD (chief_engineer, purser, chief_officer) → 200
   - Captain/Manager can sign

5. **Reject Receiving**
   - Sets `status='rejected'` and stores reason in audit

6. **View History Returns Audit Trail**
   - Returns receiving header with `received_by_name`, `received_by_role`
   - Returns documents with comments
   - Returns complete audit trail

7. **Cross-Yacht Isolation**
   - `wrong_yacht` JWT cannot access records (RLS filters)

8. **Update After Acceptance Fails**
   - 400 ALREADY_ACCEPTED

### Stress Test Metrics

**Configuration**:
- 50 concurrent requests
- 10 actions per type (create, add_item, update, view)

**Expected Thresholds**:
- P50 latency: < 500ms
- P95 latency: < 2000ms
- P99 latency: < 5000ms
- **Zero 500s** (critical requirement)
- Success rate: > 95%

**Output**: JSON file with:
- Status code distribution
- Action distribution
- Latency percentiles
- Error details (if any)

---

## Run Commands

### 1. Export Environment Variables
```bash
export TENANT_1_SUPABASE_URL='https://vzsohavtuotocgrfkfyd.supabase.co'
export TENANT_1_SUPABASE_SERVICE_KEY='<service_key>'
export TEST_YACHT_ID='85fe1119-b04c-41ac-80f1-829d23322598'
export API_BASE_URL='https://pipeline-core.int.celeste7.ai'

# 15 JWTs (generate using your JWT generator)
export CREW_JWT="..."
export DECKHAND_JWT="..."
export STEWARD_JWT="..."
export ENGINEER_JWT="..."
export ETO_JWT="..."
export CHIEF_ENGINEER_JWT="..."
export CHIEF_OFFICER_JWT="..."
export CHIEF_STEWARD_JWT="..."
export PURSER_JWT="..."
export CAPTAIN_JWT="..."
export MANAGER_JWT="..."
export INACTIVE_JWT="..."
export EXPIRED_JWT="..."
export WRONG_YACHT_JWT="..."
export MIXED_ROLE_JWT="..."
```

### 2. Run Acceptance Tests
```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS
pytest apps/api/tests/test_receiving_lens_v1_acceptance.py -v --tb=short
```

### 3. Run Stress Test
```bash
OUTPUT_JSON=receiving-stress.json TEST_JWT="$CHIEF_ENGINEER_JWT" \
  python tests/stress/stress_receiving_actions.py
```

### 4. Verify Results
```bash
# Check acceptance test results
cat receiving-stress.json | jq '.summary'

# Check for 500s
cat receiving-stress.json | jq '.summary.server_errors'

# Expected: 0
```

---

## Evidence Bundle for PR

### Required Artifacts

1. **DB Gate Outputs** ✅
   - RLS enabled (6/6 tables)
   - 21 policies created
   - 15 storage policies
   - Schema verification
   - Comment column exists
   - Signature invariant (0 nulls)

2. **Migration Success Logs** ✅
   - All 8 migrations applied without errors
   - Verification notices confirm success

3. **Acceptance Test Results** ⏳
   - 8/8 tests passing
   - All role permutations tested
   - Cross-yacht isolation verified
   - Storage path validation confirmed

4. **Stress Test Results** ⏳
   - P50/P95/P99 latencies
   - Zero 500s confirmed
   - Success rate > 95%
   - Status code distribution

5. **Sample Signed Acceptance** ⏳
   - Request with PIN+TOTP payload
   - Response with signature_verified=true
   - Audit log entry with non-NULL signature
   - Metadata includes: source, lens, action, entity_id, session_id, ip_address

---

## Deployment Checklist

- ✅ Migrations applied to staging
- ✅ DB gates passed
- ✅ Handlers implemented (10 actions)
- ✅ Registry updated
- ✅ Dispatcher wired
- ⏳ Acceptance tests passing
- ⏳ Stress test passing (zero 500s)
- ⏳ Sample signed acceptance documented
- ⏳ Evidence bundle complete
- ⏳ PR created
- ⏳ Render deploy triggered
- ⏳ Canary monitoring (30-60 min)

---

## Next Steps

### Automated Test Execution (RECOMMENDED)

**Quick Start**: See `QUICKSTART_TESTING.md` for 3-step guide.

1. **Generate 15 JWTs** using existing generator
   ```bash
   bash tests/generate_jwt_exports.sh  # Shows template export commands
   ```

2. **Run automated test suite** (acceptance + stress + evidence generation)
   ```bash
   bash tests/run_receiving_evidence.sh
   ```
   - Validates all JWTs are set
   - Runs 8 acceptance test scenarios
   - Runs stress test (50 concurrent requests)
   - Generates evidence summary
   - Checks for zero 500s
   - Saves results to JSON

3. **Create PR** with evidence bundle
   - Use template in `PR_TEMPLATE.md`
   - Include stress test results JSON
   - Deploy to production via Render webhook

### Manual Steps (Alternative)

1. **Generate 15 JWTs** using existing generator
2. **Run acceptance tests** and capture output
   ```bash
   pytest apps/api/tests/test_receiving_lens_v1_acceptance.py -v --tb=short
   ```
3. **Run stress test** and verify zero 500s
   ```bash
   OUTPUT_JSON=receiving-stress.json TEST_JWT="$CHIEF_ENGINEER_JWT" \
     python tests/stress/stress_receiving_actions.py
   ```
4. **Capture sample signed acceptance** request/response
5. **Assemble evidence bundle** for PR
6. **Create PR** with complete evidence
7. **Deploy to production** via Render webhook
8. **Canary monitor** for 30-60 minutes

---

## Helper Scripts Created

- `tests/run_receiving_evidence.sh` - Orchestrated test runner (validates env, runs tests, generates summary)
- `tests/generate_jwt_exports.sh` - JWT export helper (shows template commands for 15 personas)
- `docs/.../QUICKSTART_TESTING.md` - 3-step quick start guide
- `docs/.../PR_TEMPLATE.md` - Pre-filled PR description ready to use

---

**Status**: Implementation complete, DB gates passed, test automation ready. **Next: Generate JWTs and run tests.**
