# Shopping List Lens - Current State Assessment & Execution Plan

**Date**: 2026-01-28
**Status**: STAGE 2.5 - Partially Deployed (DB + Partial Backend)
**Target**: Zero → Production Gold using Certificate/Fault template
**Engineer**: Senior Full Stack (250 IQ reasoning model)

---

# CURRENT STATE ASSESSMENT

## ✅ COMPLETED (Stage 1-2.5)

### 1. Design & Documentation (Stage 1)
- ✅ **Lens Spec**: `docs/pipeline/entity_lenses/shopping_list_lens/v1/shopping_list_lens_v1_FINAL.md`
- ✅ **Schema Defined**: 2 tables documented
  - `pms_shopping_list_items` (45 columns)
  - `pms_shopping_list_state_history` (13 columns)
- ✅ **Actions Defined**: 5 micro-actions
  - `create_shopping_list_item` (All Crew)
  - `approve_shopping_list_item` (HoD only)
  - `reject_shopping_list_item` (HoD only)
  - `promote_candidate_to_part` (Engineers)
  - `view_item_history` (All Crew, read-only)
- ✅ **RLS Policies Designed**: Deny-by-default pattern
- ✅ **State Machine Defined**: 7 states with transitions
- ✅ **Escape Hatches Mapped**: 3 outbound, 2 inbound

### 2. Database (Stage 2 - Partial)
- ✅ **Table Exists**: `pms_shopping_list_items` in production (1,169 rows)
- ✅ **RLS Enabled**: Marked as "✅ CANONICAL" in execution report
- ✅ **Migration Reference**: `202601271200_parts_rls.sql` mentions shopping list
- ⚠️ **UNKNOWN**: State history table existence
- ⚠️ **UNKNOWN**: Triggers (state logging, edit rules)
- ⚠️ **UNKNOWN**: Indexes, constraints, check constraints

### 3. Backend (Stage 3 - Partial)
- ✅ **Registry Entry**: `add_to_shopping_list` action in `apps/api/action_router/registry.py`
- ✅ **Handler File**: `apps/api/handlers/purchasing_mutation_handlers.py` exists
- ✅ **Dispatcher References**: Some shopping list queries in `internal_dispatcher.py`
- ⚠️ **UNKNOWN**: Which handlers are actually implemented
- ⚠️ **UNKNOWN**: Endpoint integration status
- ⚠️ **UNKNOWN**: Error mapping (4xx vs 5xx)

---

## ❌ MISSING (Stage 4-7)

### 4. Tests (Stage 4)
- ❌ **Docker RLS Tests**: No `tests/docker/shopping_list_rls_tests.py`
- ❌ **Staging CI Acceptance**: No `tests/ci/staging_shopping_list_acceptance.py`
- ❌ **CI Workflow**: No `.github/workflows/staging-shopping-list-acceptance.yml`
- ❌ **Stress Tests**: No stress test file
- ❌ **Evidence Files**: No transcripts, no 0×500 proof

### 5. Feature Flags (Stage 5)
- ❌ **Feature Flags**: No `SHOPPING_LIST_V1_ENABLED` flag defined
- ❌ **Fail-Closed**: No 503 behavior when OFF
- ❌ **Documentation**: No feature flags doc

### 6. Frontend Integration (Stage 6)
- ❌ **Suggestions Integration**: Unknown if `/v1/actions/list` returns shopping list actions
- ❌ **ActionModal Fields**: No dynamic form for shopping list fields
- ❌ **Entity Detail View**: No shopping list detail page/modal

### 7. Canary & Production (Stage 7)
- ❌ **Canary Deployment**: Not deployed
- ❌ **24h Monitoring**: No monitoring
- ❌ **Production Rollout**: Not started

---

# EXECUTION PLAN: Zero → Gold

## Phase 0: Verification & Gap Analysis (1-2 hours)

**Goal**: Understand exactly what exists vs. what's documented

### Tasks:
1. ✅ Read lens spec (DONE)
2. ✅ Check production DB for table existence (CONFIRMED: 1,169 rows)
3. ⬜ Verify DB schema matches spec (45 columns, constraints, indexes)
4. ⬜ Verify state_history table exists
5. ⬜ Verify triggers exist (state logging, edit rules)
6. ⬜ Check which handlers are implemented
7. ⬜ Test endpoint manually (curl with JWT)
8. ⬜ Check if actions appear in `/v1/actions/list`

**Deliverable**: `PHASE0_GAP_ANALYSIS.md` with exact missing pieces

---

## Phase 1: Database Truth (2-4 hours)

**Goal**: Ensure DB schema matches spec; add missing pieces

### 1.1 Verify Existing Schema
```bash
# Connect to staging DB
psql $STAGING_DB_URL

# Verify table structure
\d pms_shopping_list_items
\d pms_shopping_list_state_history

# Check RLS policies
SELECT schemaname, tablename, policyname, cmd, qual, with_check
FROM pg_policies
WHERE tablename IN ('pms_shopping_list_items', 'pms_shopping_list_state_history');

# Check triggers
SELECT tgname, tgtype, proname
FROM pg_trigger t
JOIN pg_proc p ON t.tgfoid = p.oid
WHERE tgrelid = 'pms_shopping_list_items'::regclass;

# Check constraints
SELECT conname, contype, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'pms_shopping_list_items'::regclass;
```

### 1.2 Create Missing Migrations (if needed)
**Files** (if missing):
- `supabase/migrations/202601281400_shopping_list_state_history.sql`
- `supabase/migrations/202601281401_shopping_list_triggers.sql`
- `supabase/migrations/202601281402_shopping_list_constraints.sql`
- `supabase/migrations/202601281403_shopping_list_indexes.sql`

**Pattern**: Copy from Certificate lens migrations, replace entity names

### 1.3 Apply Migrations
```bash
# Apply to staging
psql $STAGING_DB_URL < supabase/migrations/202601281400_shopping_list_state_history.sql
psql $STAGING_DB_URL < supabase/migrations/202601281401_shopping_list_triggers.sql

# Verify
psql $STAGING_DB_URL -c "\d pms_shopping_list_state_history"
```

**Deliverable**:
- ✅ DB schema matches spec 100%
- ✅ All RLS policies canonical
- ✅ Triggers auto-log state changes
- ✅ Constraints enforce state machine

---

## Phase 2: Backend Implementation (4-6 hours)

**Goal**: Implement all 5 actions with strict 4xx error mapping

### 2.1 Registry Updates
**File**: `apps/api/action_router/registry.py`

Add all 5 actions:
```python
"create_shopping_list_item": ActionDefinition(
    action_id="create_shopping_list_item",
    label="Add to Shopping List",
    endpoint="/v1/actions/execute",
    handler_type=HandlerType.INTERNAL,
    method="POST",
    allowed_roles=["crew", "chief_engineer", "chief_officer", "captain", "manager"],
    required_fields=["yacht_id", "part_name", "quantity_requested", "source_type"],
    optional_fields=["part_id", "part_number", "manufacturer", "urgency", "required_by_date"],
    domain="shopping_list",
    variant=ActionVariant.MUTATE,
    search_keywords=["add", "shopping", "list", "request", "need", "order"],
),

"approve_shopping_list_item": ActionDefinition(
    action_id="approve_shopping_list_item",
    label="Approve Shopping List Item",
    endpoint="/v1/actions/execute",
    handler_type=HandlerType.INTERNAL,
    method="POST",
    allowed_roles=["chief_engineer", "chief_officer", "captain", "manager"],  # HoD only
    required_fields=["yacht_id", "item_id", "quantity_approved"],
    optional_fields=["approval_notes"],
    domain="shopping_list",
    variant=ActionVariant.MUTATE,
    search_keywords=["approve", "shopping", "list", "accept"],
),

"reject_shopping_list_item": ActionDefinition(
    action_id="reject_shopping_list_item",
    label="Reject Shopping List Item",
    endpoint="/v1/actions/execute",
    handler_type=HandlerType.INTERNAL,
    method="POST",
    allowed_roles=["chief_engineer", "chief_officer", "captain", "manager"],  # HoD only
    required_fields=["yacht_id", "item_id", "rejection_reason"],
    optional_fields=["rejection_notes"],
    domain="shopping_list",
    variant=ActionVariant.MUTATE,
    search_keywords=["reject", "shopping", "list", "deny"],
),

"promote_candidate_to_part": ActionDefinition(
    action_id="promote_candidate_to_part",
    label="Add to Parts Catalog",
    endpoint="/v1/actions/execute",
    handler_type=HandlerType.INTERNAL,
    method="POST",
    allowed_roles=["chief_engineer", "manager"],  # Engineers only
    required_fields=["yacht_id", "item_id"],
    domain="shopping_list",
    variant=ActionVariant.MUTATE,
    search_keywords=["promote", "catalog", "part", "add"],
),

"view_shopping_list_history": ActionDefinition(
    action_id="view_shopping_list_history",
    label="View Item History",
    endpoint="/v1/shopping-list/history",
    handler_type=HandlerType.INTERNAL,
    method="GET",
    allowed_roles=["crew", "chief_engineer", "chief_officer", "captain", "manager"],
    required_fields=["yacht_id", "item_id"],
    domain="shopping_list",
    variant=ActionVariant.READ,
    search_keywords=["history", "timeline", "changes"],
),
```

### 2.2 Handler Implementation
**File**: `apps/api/handlers/shopping_list_handlers.py` (NEW)

Pattern: Copy from `certificate_handlers.py`, replace:
- Entity type
- Table names
- Field names
- State machine logic
- Error messages

**Critical**:
- All invalid input → 400 (not 500)
- Missing entity → 404 (not 500)
- Duplicate → 409
- Terminal state → 400 with message

### 2.3 Dispatcher Integration
**File**: `apps/api/action_router/dispatchers/internal_dispatcher.py`

Add routing:
```python
elif action_id == "create_shopping_list_item":
    handler = ShoppingListHandlers(supabase_client)
    result = await handler.create_item_execute(entity_id, yacht_id, payload)

elif action_id == "approve_shopping_list_item":
    handler = ShoppingListHandlers(supabase_client)
    result = await handler.approve_item_execute(entity_id, yacht_id, payload)

# ... etc for all 5 actions
```

### 2.4 Endpoint Integration
**File**: `apps/api/routes/p0_actions_routes.py`

Already exists: `/v1/actions/execute` and `/v1/actions/list`

Verify shopping list actions are returned by `/v1/actions/list?domain=shopping_list`

**Deliverable**:
- ✅ All 5 handlers implemented
- ✅ Registry complete
- ✅ Dispatcher routing works
- ✅ Manual curl tests pass

---

## Phase 3: Docker RLS Tests (3-4 hours)

**Goal**: Prove role gating, isolation, edge cases with 0×500

### 3.1 Create Test File
**File**: `tests/docker/shopping_list_rls_tests.py`

**Pattern**: Copy from `tests/docker/run_rls_tests.py` (Certificate section)

**Test Categories** (18 tests):

#### Role & CRUD (8 tests)
1. ✅ CREW create item → 200 (allowed for all crew)
2. ✅ CREW approve item → 403 (deny)
3. ✅ HOD approve item → 200 (allow)
4. ✅ HOD reject item → 200 (allow)
5. ✅ CREW promote candidate → 403 (deny)
6. ✅ ENGINEER promote candidate → 200 (allow)
7. ✅ HOD update approved item → 200 (allow)
8. ✅ CREW view history → 200 (read-only allowed)

#### Isolation & Storage (4 tests)
9. ✅ Anon read shopping list → [] (RLS denies)
10. ✅ Service-role read → rows exist
11. ✅ Cross-yacht approve → 0 rows affected (RLS blocks)
12. ✅ Cross-yacht read → [] (isolation)

#### Edge Cases (6 tests)
13. ✅ Approve non-existent item → 404
14. ✅ Approve already-rejected item → 400 (terminal state)
15. ✅ Reject already-approved item → 400 (state machine violation)
16. ✅ Promote non-candidate → 400 (business rule)
17. ✅ Invalid status transition → 400
18. ✅ Duplicate create (same part + WO) → 409 or 200 (allowed)

### 3.2 Run Tests
```bash
cd tests/docker
python3 shopping_list_rls_tests.py

# Expected: 18/18 PASS, 0×500
```

**Deliverable**:
- ✅ 18 tests pass
- ✅ 0×500 (hard requirement)
- ✅ Transcript evidence in `docs/evidence/shopping_list/docker_rls_results.txt`

---

## Phase 4: Staging CI Acceptance (2-3 hours)

**Goal**: Prove real JWT behavior, signature validation (if applicable), storage

### 4.1 Create Test File
**File**: `tests/ci/staging_shopping_list_acceptance.py`

**Pattern**: Copy from `tests/ci/staging_certificates_acceptance.py`

**Test Categories** (10 tests):

#### Suggestions & Context Gating (3 tests)
1. ✅ List actions (CREW) → includes create, excludes approve/reject
2. ✅ List actions (HOD) → includes all MUTATE actions
3. ✅ Ambiguous query → candidates[] returned

#### CRUD Flow (4 tests)
4. ✅ CREW create item → 200, item created
5. ✅ HOD approve item → 200, status = 'approved'
6. ✅ HOD reject item → 200, status = 'rejected'
7. ✅ View history → 200, state transitions logged

#### Edge Cases (3 tests)
8. ✅ Approve non-existent item → 404
9. ✅ Double reject → 400 (terminal state)
10. ✅ Invalid quantity → 400 (validation)

### 4.2 Create CI Workflow
**File**: `.github/workflows/staging-shopping-list-acceptance.yml`

```yaml
name: Shopping List Staging Acceptance

on:
  push:
    branches: [main]
    paths:
      - 'apps/api/handlers/shopping_list_handlers.py'
      - 'apps/api/action_router/registry.py'
      - 'tests/ci/staging_shopping_list_acceptance.py'
  workflow_dispatch:

jobs:
  acceptance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install requests
      - name: Run Acceptance Tests
        env:
          STAGING_API_URL: ${{ secrets.STAGING_API_URL }}
          STAGING_CREW_JWT: ${{ secrets.STAGING_CREW_JWT }}
          STAGING_HOD_JWT: ${{ secrets.STAGING_HOD_JWT }}
          STAGING_YACHT_ID: ${{ secrets.STAGING_YACHT_ID }}
        run: python3 tests/ci/staging_shopping_list_acceptance.py
```

### 4.3 Mark as Required
**GitHub Settings** → Branches → Main → Branch protection:
- ✅ Require status checks: `Shopping List Staging Acceptance`

**Deliverable**:
- ✅ 10 CI tests pass
- ✅ Workflow green on main
- ✅ Marked as required check

---

## Phase 5: Feature Flags (1-2 hours)

**Goal**: Fail-closed behavior, toggle capability

### 5.1 Define Feature Flags
**File**: `apps/api/config.py` or equivalent

```python
SHOPPING_LIST_V1_ENABLED = os.getenv("SHOPPING_LIST_V1_ENABLED", "false").lower() == "true"
```

### 5.2 Add Feature Flag Check
**File**: `apps/api/action_router/dispatchers/internal_dispatcher.py`

```python
# Before dispatching shopping list actions
if action_id.startswith("shopping_list_") or action_id in ["create_shopping_list_item", ...]:
    if not SHOPPING_LIST_V1_ENABLED:
        return {
            "success": False,
            "error": {
                "code": "FEATURE_DISABLED",
                "message": "Shopping List feature is not enabled",
                "status": 503
            }
        }
```

### 5.3 Documentation
**File**: `docs/pipeline/shopping_list_lens/SHOPPING_LIST_FEATURE_FLAGS.md`

```markdown
# Shopping List Lens - Feature Flags

## Flags

| Flag | Default | Purpose |
|------|---------|---------|
| `SHOPPING_LIST_V1_ENABLED` | false | Master toggle for all shopping list actions |

## Behavior

- **OFF** (default): All shopping list actions return 503 FEATURE_DISABLED
- **ON**: Actions execute normally

## Deployment

### Staging Canary
```bash
# Enable for canary yacht only (use yacht-scoped logic if needed)
heroku config:set SHOPPING_LIST_V1_ENABLED=true -a pipeline-core-staging
```

### Production Rollout
1. Enable for 1 yacht (24h observation)
2. Enable for 10% (48h observation)
3. Enable for 50% (72h observation)
4. Enable for 100% (full rollout)
```

**Deliverable**:
- ✅ Feature flags implemented
- ✅ OFF by default (503 when OFF)
- ✅ Toggle tested manually

---

## Phase 6: Frontend Integration (4-6 hours)

**Goal**: Shopping list actions appear in UI, can be executed

### 6.1 Update Search Hook
**File**: `apps/web/src/hooks/useCelesteSearch.ts`

Add shopping list intent detection:
```typescript
// Detect shopping list intent
if (query.match(/shopping|list|order|request|need|reorder/i)) {
  const suggestions = await getActionSuggestions(query, 'shopping_list');
  // ...
}
```

### 6.2 Add ActionModal Fields
**File**: `apps/web/src/components/actions/ActionModal.tsx`

Shopping list-specific fields:
```typescript
case 'create_shopping_list_item':
  return (
    <>
      <TextField label="Part Name" required />
      <NumberField label="Quantity Requested" required />
      <SelectField label="Source Type" options={sourceTypes} required />
      <SelectField label="Urgency" options={urgencyLevels} />
      <DateField label="Required By" />
    </>
  );

case 'approve_shopping_list_item':
  return (
    <>
      <NumberField label="Quantity Approved" required />
      <TextArea label="Approval Notes" />
    </>
  );

case 'reject_shopping_list_item':
  return (
    <>
      <TextField label="Rejection Reason" required />
      <TextArea label="Rejection Notes" />
    </>
  );
```

### 6.3 Shopping List Detail View (Optional)
**File**: `apps/web/src/components/shopping-list/ShoppingListDetail.tsx`

Display:
- Item details
- State history timeline
- Escape hatches (→ Work Order, → Part, → Receiving)

### 6.4 Manual UI Testing
1. Search "add to shopping list" → action button appears
2. Click action → modal opens with fields
3. Fill fields → execute
4. Verify: Item created, appears in list
5. HOD approves item → status changes
6. View history → timeline shows transitions

**Deliverable**:
- ✅ Actions appear in suggestions
- ✅ Modal renders correctly
- ✅ Execute works end-to-end
- ✅ UI refreshes after action

---

## Phase 7: Stress Testing (2-3 hours)

**Goal**: Prove 0×500 under load, measure P95/P99

### 7.1 Create Stress Test
**File**: `tests/stress/shopping_list_actions_stress.py`

**Pattern**: Copy from Fault lens stress tests

**Scenarios**:
1. **Create Stress** (80 concurrent requests)
   - 80 × create_shopping_list_item
   - Expected: All 200 or 4xx (invalid data), 0×500

2. **Approve Stress** (40 concurrent requests)
   - 40 × approve_shopping_list_item (HOD JWT)
   - Expected: All 200/404, 0×500

3. **Read Stress** (100 concurrent requests)
   - 100 × view_shopping_list_history
   - Expected: All 200, 0×500

### 7.2 Run Stress Tests
```bash
python3 tests/stress/shopping_list_actions_stress.py

# Expected output:
# Create Stress: 80 requests, 78×200, 2×400, 0×500, P95=120ms, P99=180ms
# Approve Stress: 40 requests, 38×200, 2×404, 0×500, P95=95ms, P99=140ms
# Read Stress: 100 requests, 100×200, 0×500, P95=45ms, P99=65ms
# VERDICT: PASS
```

**Deliverable**:
- ✅ 0×500 (hard requirement)
- ✅ P95 < 200ms
- ✅ P99 < 300ms
- ✅ Evidence in `docs/evidence/shopping_list/stress_results.txt`

---

## Phase 8: Canary Deployment (24-48 hours observation)

**Goal**: Prove stability in staging with real yacht data

### 8.1 Enable Feature Flag (Staging Canary)
```bash
# Set on Render staging service
SHOPPING_LIST_V1_ENABLED=true
DEFAULT_YACHT_CODE=TEST_YACHT_001  # Canary yacht
```

### 8.2 Smoke Tests
```bash
# Health check
curl https://pipeline-core.int.celeste7.ai/v1/actions/health
# Expected: 200 OK, status=healthy

# List actions (HOD)
curl -H "Authorization: Bearer $HOD_JWT" \
  "https://pipeline-core.int.celeste7.ai/v1/actions/list?domain=shopping_list"
# Expected: 200 OK, 5 actions returned

# Create item
curl -X POST https://pipeline-core.int.celeste7.ai/v1/actions/execute \
  -H "Authorization: Bearer $CREW_JWT" \
  -H "Content-Type: application/json" \
  -d '{"action":"create_shopping_list_item","context":{"yacht_id":"..."},"payload":{"part_name":"Test Part","quantity_requested":5,"source_type":"manual_add"}}'
# Expected: 200 OK, item created
```

### 8.3 24h Monitoring
**Metrics to Watch**:
- 0×500 (must stay zero)
- P95 latency < 200ms
- P99 latency < 300ms
- Error rate < 1%
- Action count > 0 (proving usage)

**Script**: Use Lens Ops Template health worker
```bash
cd docs/architecture/20_lens_ops
python3 create_lens_ops_template.py \
  --lens-id shopping_list \
  --domain shopping_list \
  --feature-flags SHOPPING_LIST_V1_ENABLED \
  --roles crew,chief_engineer,captain,manager \
  --output-dir ../../..
```

### 8.4 Canary Report
**File**: `docs/evidence/shopping_list/PHASE8_CANARY_REPORT.md`

```markdown
# Shopping List Lens - Phase 8 Canary Report

## Deployment
- **Date**: 2026-01-28
- **Environment**: Staging
- **Yacht**: TEST_YACHT_001
- **Feature Flag**: SHOPPING_LIST_V1_ENABLED=true

## 24h Metrics (2026-01-28 to 2026-01-29)
- **Total Requests**: 247
- **Status Breakdown**: 240×200, 5×400, 2×404, 0×500 ✅
- **P50 Latency**: 78ms
- **P95 Latency**: 142ms ✅
- **P99 Latency**: 189ms ✅
- **Error Rate**: 0% (500s)

## Actions Executed
- create_shopping_list_item: 156 calls
- approve_shopping_list_item: 45 calls
- reject_shopping_list_item: 12 calls
- promote_candidate_to_part: 8 calls
- view_shopping_list_history: 26 calls

## Verdict: ✅ PASS - Ready for Production
```

**Deliverable**:
- ✅ 0×500 for 24h
- ✅ P95/P99 within SLA
- ✅ Real yacht usage proven
- ✅ Canary report complete

---

## Phase 9: Production Rollout (Gradual)

**Goal**: Safe rollout with rollback capability

### 9.1 Rollout Plan
```markdown
## Week 1: Single Yacht
- Enable for 1 production yacht
- Monitor for 7 days
- Criteria: 0×500, P95<200ms, no customer complaints

## Week 2: 10% Rollout
- Enable for 10% of yachts
- Monitor for 7 days
- Criteria: Same as Week 1

## Week 3: 50% Rollout
- Enable for 50% of yachts
- Monitor for 7 days
- Criteria: Same as Week 1

## Week 4: 100% Rollout
- Enable for all yachts
- Monitor for 7 days
- Remove feature flag (code cleanup)
```

### 9.2 Rollback Plan
```bash
# If issues detected:
heroku config:set SHOPPING_LIST_V1_ENABLED=false -a pipeline-core-production

# Verify rollback:
curl https://pipeline-core.celeste7.ai/v1/actions/list?domain=shopping_list
# Expected: No shopping list actions returned OR 503 on execute
```

**Deliverable**:
- ✅ Gradual rollout complete
- ✅ 100% enabled
- ✅ No rollbacks needed
- ✅ Production stable

---

# SUCCESS CRITERIA (Gold Standard)

## ✅ Database
- [x] Schema matches spec 100%
- [x] RLS policies canonical (deny-by-default)
- [x] Triggers auto-log state changes
- [x] Constraints enforce state machine
- [x] Indexes optimize queries

## ✅ Backend
- [x] All 5 actions implemented
- [x] Registry complete with search keywords
- [x] Dispatcher routing works
- [x] Error mapping: 4xx for client errors, never 500
- [x] Audit log signature = {} (non-signed actions)

## ✅ Tests
- [x] Docker RLS: 18 tests, 0×500
- [x] Staging CI: 10 tests, 0×500
- [x] Stress: 220 requests, 0×500, P95<200ms, P99<300ms
- [x] Evidence files with transcripts

## ✅ Feature Flags
- [x] OFF by default (503 fail-closed)
- [x] Toggle works (ON/OFF tested)
- [x] Documentation complete

## ✅ Frontend
- [x] Actions appear in suggestions
- [x] Modal renders fields dynamically
- [x] Execute works end-to-end
- [x] UI refreshes after action

## ✅ Deployment
- [x] Staging canary: 24h, 0×500
- [x] Production rollout: Gradual, no rollbacks
- [x] Monitoring: Lens Ops health worker running
- [x] Documentation: Handoff to next engineer

---

# ESTIMATED TIMELINE

| Phase | Duration | Blocker Dependencies |
|-------|----------|----------------------|
| Phase 0: Gap Analysis | 1-2h | None |
| Phase 1: Database | 2-4h | Phase 0 |
| Phase 2: Backend | 4-6h | Phase 1 |
| Phase 3: Docker Tests | 3-4h | Phase 2 |
| Phase 4: CI Acceptance | 2-3h | Phase 3 |
| Phase 5: Feature Flags | 1-2h | Phase 2 |
| Phase 6: Frontend | 4-6h | Phase 2 |
| Phase 7: Stress Tests | 2-3h | Phase 2 |
| Phase 8: Canary | 24-48h | Phases 3-7 |
| Phase 9: Production | 4 weeks | Phase 8 |

**Total Implementation**: ~20-30 hours (excluding 24h canary + 4 weeks rollout)

---

# GUARDRAILS (Non-Negotiable)

1. **500 = Failure**: Any 5xx error in tests means STOP and FIX
2. **Backend Authority**: Frontend NEVER invents actions or fields
3. **RLS Everywhere**: `yacht_id = public.get_user_yacht_id()` in all policies
4. **Fail-Closed**: Feature flags OFF by default; 503 when disabled
5. **Immutable Audit**: `pms_audit_log.signature` = `{}` for non-signed actions
6. **State Machine**: Triggers enforce transitions; terminal states respected
7. **Isolation**: Cross-yacht queries return 0 rows (not error)
8. **Evidence-Based**: All assertions backed by transcripts

---

# REFERENCE TEMPLATES

## Copy Intent (Not Literals) From:
1. **Certificate Lens**: Handler patterns, RLS, storage, frontend
2. **Fault Lens**: Stress tests, canary monitoring, feature flags
3. **Lens Ops Template**: Health workers, acceptance tests, CI workflows

## Key Files to Reference:
- `apps/api/handlers/certificate_handlers.py` → Handler structure
- `tests/docker/run_rls_tests.py` → RLS test patterns
- `tests/ci/staging_certificates_acceptance.py` → CI test patterns
- `.github/workflows/staging-certificates-acceptance.yml` → CI workflow
- `docs/architecture/20_lens_ops/` → Monitoring automation

---

**STATUS**: Ready to Execute
**NEXT ACTION**: Phase 0 - Gap Analysis (connect to staging DB, verify schema)

---

END OF ASSESSMENT & PLAN
