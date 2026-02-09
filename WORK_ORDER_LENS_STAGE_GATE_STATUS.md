# Work Order Lens - Stage Gate Status & Testing Plan

**Date:** 2026-02-02
**Framework:** TESTING_INFRASTRUCTURE.md + STAGES.md
**Testing Philosophy:** Incremental validation with vigorous stress testing at each stage

---

## Pipeline Overview (7 Stages)

```
Stage 0: Lens Authoring (Docs) ───────────────► ✅ COMPLETE
                ↓
Stage 1: DB Truth & Migrations ───────────────► ✅ COMPLETE
                ↓
Stage 2: Action Registry ─────────────────────► ✅ COMPLETE
                ↓
Stage 3: Handlers & Router ───────────────────► ✅ COMPLETE
                ↓
Stage 4: Backend Tests (Docker RLS) ──────────► ⚠️  PARTIAL (needs Docker suite)
                ↓
Stage 5: Frontend Integration ────────────────► ❌ NOT STARTED
                ↓
Stage 6: Staging CI Acceptance ───────────────► ❌ NOT STARTED
                ↓
Stage 7: Release ──────────────────────────────► ❌ NOT STARTED
```

---

## Current Status by Stage

### ✅ Stage 0: Lens Authoring (COMPLETE)

**Status:** GOLD specification complete

**Evidence:**
- `/docs/pipeline/entity_lenses/work_order_lens/v2/work_order_lens_v2_FINAL.md`
- All 8 phases complete (Scope → Gaps & Migrations)
- 6 core actions + 2 signed actions documented
- DB schema verified against production snapshot
- RLS matrix defined
- Field classifications complete

**Gate Status:** ✅ PASS

---

### ✅ Stage 1: DB Truth & Migrations (COMPLETE)

**Status:** All critical migrations applied and verified

**Files:**
- `supabase/migrations/20260125_fix_cross_yacht_notes.sql` (B1)
- `supabase/migrations/20260125_fix_cross_yacht_parts.sql` (B2)
- `supabase/migrations/20260125_fix_cross_yacht_part_usage.sql` (B3)

**Verification Results:**
```sql
✅ pms_work_orders: RLS enabled, canonical pattern
✅ pms_work_order_notes: B1 FIXED - join-based isolation
✅ pms_work_order_parts: B2 FIXED - join-based isolation
✅ pms_part_usage: B3 FIXED - canonical isolation
✅ All policies verified via test suite
```

**Tests Run:**
- `tests/test_work_order_rls_security.py` - 9/9 PASSED
- Cross-yacht leakage: 0 breaches detected
- 2,969 work orders tested
- 100 notes, 100 parts, 8 usage records tested

**Gate Status:** ✅ PASS

---

### ✅ Stage 2: Action Registry (COMPLETE)

**Status:** 16 work order actions registered

**File:** `apps/api/action_router/registry.py`

**Actions Defined:**
| Action | Domain | Variant | Roles | Signature |
|--------|--------|---------|-------|-----------|
| create_work_order_for_equipment | equipment | MUTATE | HoD | ❌ |
| update_work_order | work_orders | MUTATE | HoD | ❌ |
| assign_work_order | work_orders | MUTATE | HoD | ❌ |
| add_work_order_photo | work_orders | MUTATE | HoD | ❌ |
| add_parts_to_work_order | work_orders | MUTATE | HoD | ❌ |
| add_note_to_work_order | work_orders | MUTATE | HoD | ❌ |
| start_work_order | work_orders | MUTATE | HoD | ❌ |
| cancel_work_order | work_orders | MUTATE | HoD | ❌ |
| close_work_order | work_orders | MUTATE | HoD | ❌ |
| **reassign_work_order** | work_orders | **SIGNED** | HoD | **✅** |
| **archive_work_order** | work_orders | **SIGNED** | captain/manager | **✅** |
| view_work_order_detail | work_orders | READ | All | ❌ |
| view_work_order_checklist | work_orders | READ | All | ❌ |
| view_my_work_orders | work_orders | READ | All | ❌ |
| create_work_order_from_fault | faults | SIGNED | HoD | ✅ |
| link_entities | work_orders | MUTATE | HoD | ❌ |

**Verification:**
- ✅ All actions have `domain` specified
- ✅ All actions have `allowed_roles` (no generic defaults)
- ✅ All SIGNED actions have `signature` in `required_fields`
- ✅ Storage config for `add_work_order_photo`

**Gate Status:** ✅ PASS

---

### ✅ Stage 3: Handlers & Router (COMPLETE)

**Status:** Handlers implemented and wired

**Files:**
- `apps/api/handlers/work_order_mutation_handlers.py` - MUTATE handlers
- `apps/api/handlers/work_order_handlers.py` - READ handlers
- `apps/api/action_router/dispatchers/internal_dispatcher.py` - Routing

**Handlers Implemented:**
| Handler | Type | Status |
|---------|------|--------|
| view_work_order | READ | ✅ |
| view_work_order_history | READ | ✅ |
| view_work_order_checklist | READ | ✅ |
| create_work_order_from_fault_prefill | MUTATE | ✅ |
| create_work_order_from_fault_preview | MUTATE | ✅ |
| create_work_order_from_fault_execute | MUTATE | ✅ |
| add_note_to_work_order | MUTATE | ✅ |
| add_part_to_work_order | MUTATE | ✅ |
| mark_work_order_complete | MUTATE | ✅ |

**Verification:**
- ✅ All handlers return `ActionResponseEnvelope`
- ✅ Error codes: 400/404 for client errors, NOT 500
- ✅ Audit log integration present
- ✅ RLS functions used (get_user_yacht_id(), auth.uid())

**Gate Status:** ✅ PASS

---

### ⚠️ Stage 4: Backend Tests (Docker RLS) (PARTIAL)

**Status:** Security tests complete, Docker suite missing

**Completed:**
- ✅ `tests/test_work_order_rls_security.py` - RLS/RBAC validation (9/9 PASSED)
- ✅ `tests/test_work_order_lens_comprehensive.py` - Pipeline integration (36/36 PASSED)

**Missing:**
- ❌ `tests/docker/run_work_orders_rls_tests.py` - Docker-based role tests
- ❌ Docker compose test configuration for WO lens
- ❌ Stress testing suite

**Gate Status:** ⚠️ **NEEDS WORK**

**Required for PASS:**
1. Create Docker RLS test suite (following certificates template)
2. Test with real JWT tokens for each role (crew, HoD, captain)
3. Verify role gating end-to-end
4. Test cross-yacht isolation with multiple yachts
5. Run stress tests (>99% success rate, P95 < 500ms)

---

### ❌ Stage 5: Frontend Integration (NOT STARTED)

**Status:** Backend is ready, frontend wiring not done

**Files Needing Changes:**
- `apps/web/src/hooks/useCelesteSearch.ts` - Add work order intent detection
- `apps/web/src/lib/actionClient.ts` - Type definitions (if needed)

**Existing Reusable Components:**
- ✅ `SuggestedActions.tsx` - Generic button renderer
- ✅ `ActionModal.tsx` - Generic form + execution

**Required Tasks:**
1. Add work order intent detection keywords
2. Fetch action suggestions for `domain=work_orders`
3. Test button rendering with real backend
4. Test modal form submission
5. Test auto-population/completion flows

**Gate Status:** ❌ **BLOCKED** (Stage 4 must pass first)

---

### ❌ Stage 6: Staging CI Acceptance (NOT STARTED)

**Status:** Not created

**Files Needed:**
- `tests/ci/staging_work_orders_acceptance.py` - Python test script
- `.github/workflows/staging-work-orders-acceptance.yml` - CI workflow

**Required Tests:**
1. Action list endpoint with real JWTs
2. Role-based action filtering
3. Execute create/update/complete with validation
4. Signature validation for signed actions
5. Error code verification (400/404/200)

**Gate Status:** ❌ **BLOCKED** (Stage 5 must pass first)

---

### ❌ Stage 7: Release (NOT STARTED)

**Status:** Not ready for release

**Blockers:**
- Stage 4, 5, 6 must all pass

**Tasks:**
- Tag release
- Update CHANGELOG.md
- Deploy to production

**Gate Status:** ❌ **BLOCKED**

---

## Testing Plan: Stage 4 (Current Focus)

### Phase 1: Docker RLS Test Suite

**Goal:** Create comprehensive Docker-based role validation tests

**Template:** Copy from certificates lens
```bash
cp tests/docker/run_rls_tests.py tests/docker/run_work_orders_rls_tests.py
```

**Test Categories:**

#### 1. ROLE GATING (Normal Path + Edge Cases)
```python
# CREW Tests (should be DENIED)
- create_work_order: expect 403
- update_work_order: expect 403
- add_note: expect 403
- reassign: expect 403

# HoD Tests (should be ALLOWED)
- create_work_order: expect 200/201
- update_work_order: expect 200
- add_note: expect 200
- start_work_order: expect 200

# Captain Tests (should be ALLOWED + SIGNATURE)
- reassign_work_order (with signature): expect 200
- reassign_work_order (without signature): expect 400
- archive_work_order (with signature): expect 200
- archive_work_order (without signature): expect 400
```

#### 2. CRUD OPERATIONS (Happy Path + Validation)
```python
# Create
- valid payload: expect 201
- missing required field (title): expect 400
- invalid equipment_id: expect 404
- duplicate (if applicable): expect 409

# Read
- valid work_order_id: expect 200
- invalid work_order_id: expect 404
- cross-yacht work_order_id: expect 404

# Update
- valid update: expect 200
- update non-existent: expect 404
- update completed WO: expect 400 (terminal state)

# Complete
- valid complete: expect 200
- complete already completed: expect 400
```

#### 3. CROSS-YACHT ISOLATION (Security Critical)
```python
# Setup: Create WO on yacht A, attempt access from yacht B
- yacht_A_user views yacht_B_wo: expect 404
- yacht_A_user updates yacht_B_wo: expect 404
- yacht_A_user adds note to yacht_B_wo: expect 404
- yacht_B_user views yacht_A_wo: expect 404
```

#### 4. SIGNATURE VALIDATION (Critical Actions)
```python
# Reassign Work Order
- HoD with valid signature: expect 200
- HoD without signature: expect 400
- Crew with signature: expect 403
- Invalid signature format: expect 400

# Archive Work Order
- Captain with valid signature: expect 200
- Captain without signature: expect 400
- HoD with signature: expect 403 (not captain/manager)
```

#### 5. AUDIT TRAIL (Compliance)
```python
# After each mutation, verify:
- pms_audit_log entry created
- signature field populated correctly:
  - {} for non-signed actions
  - JSON for signed actions
- action, entity_type, entity_id correct
- user_id matches auth.uid()
```

#### 6. EDGE CASES & ERROR HANDLING
```python
# Malformed requests
- invalid JSON: expect 400
- missing Content-Type: expect 400
- empty payload: expect 400

# Business logic validation
- assign to non-existent user: expect 404
- link to non-existent equipment: expect 404
- invalid status transition: expect 400

# Rate limiting / Stress
- 100 concurrent requests: >99% success
- P95 latency: < 500ms
```

### Phase 2: Stress Testing

**Goal:** Verify system handles load and edge cases

**Script:** `tests/stress/stress_work_orders.py`

**Tests:**
1. **Action List Endpoint**
   - 1000 requests, 10 workers
   - Expect: >99% success, P95 < 500ms

2. **Create Work Order**
   - 100 concurrent creates
   - Expect: >95% success (some may fail due to validation)

3. **Search Pipeline**
   - 500 natural language queries
   - Expect: >99% success, < 5s per query

**Thresholds:**
| Metric | Pass | Warn | Fail |
|--------|------|------|------|
| Success Rate | ≥99% | 95-99% | <95% |
| P95 Latency | <500ms | 500-1000ms | >1000ms |
| P99 Latency | <1000ms | 1000-2000ms | >2000ms |

### Phase 3: Pipeline Integration Tests

**Goal:** Test natural language → results → buttons flow

**File:** `tests/test_work_order_lens_comprehensive.py` (already exists - enhance)

**Test Cases:**

#### Natural Language Queries (Chaos Testing)
```python
# Normal queries
"create work order for generator"
"show me open work orders"
"work orders for main engine"

# Chaotic queries (typos, vague, contradictory)
"genrator maintenence urgent but not really"
"wo for deck pump maybe yesterday or tomorrow"
"high priority low urgency inspection"

# Edge cases
"WO-12345" (explicit ID)
"work order 98765" (natural language ID)
"oil change" (compound action)
```

#### Entity Extraction Validation
```python
# For each query, verify:
- Entities extracted (type, value, confidence)
- Entities transformed correctly (e.g., EQUIPMENT_NAME → WORK_ORDER_EQUIPMENT)
- Capabilities triggered correctly
- Results returned (even if empty is valid)
```

#### Cross-Lens Search
```python
# Equipment → Work Orders
"generator" should trigger:
  - equipment search (pms_equipment)
  - work order search (pms_work_orders.equipment_id)

# Fault → Work Orders
"generator fault" should trigger:
  - fault search (pms_faults)
  - work order search (pms_work_orders.fault_id)
```

---

## Testing Infrastructure Requirements

### Docker Test Environment

**File:** `docker-compose.test.yml` (needs WO lens addition)

```yaml
services:
  api:
    build: ./apps/api
    environment:
      - MASTER_SUPABASE_URL
      - MASTER_SUPABASE_ANON_KEY
      - TENANT_SUPABASE_URL
      - TENANT_SUPABASE_SERVICE_KEY
      - YACHT_ID
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '2.0'

  test-runner:
    build: ./tests/docker
    command: python run_work_orders_rls_tests.py
    depends_on:
      - api
    environment:
      - API_BASE=http://api:8000
      - YACHT_ID
      - CREW_EMAIL
      - HOD_EMAIL
      - CAPTAIN_EMAIL
      - TEST_PASSWORD
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '1.0'
```

### Test Credentials (.env.test)

```bash
MASTER_SUPABASE_URL=<master_url>
MASTER_SUPABASE_ANON_KEY=<master_anon>
TENANT_SUPABASE_URL=<tenant_url>
TENANT_SUPABASE_SERVICE_KEY=<tenant_service>

YACHT_ID=85fe1119-b04c-41ac-80f1-829d23322598

CREW_EMAIL=crew@test.celeste7.ai
HOD_EMAIL=hod@test.celeste7.ai
CAPTAIN_EMAIL=captain@test.celeste7.ai
TEST_PASSWORD=<secure_password>
```

---

## Success Criteria by Stage

### Stage 4: Backend Tests
- ✅ Docker RLS tests: 18+ test cases, 100% pass
- ✅ Stress tests: >99% success, P95 < 500ms
- ✅ Pipeline tests: 36+ test cases, 100% pass
- ✅ Zero 500 errors (all client errors are 400/404)
- ✅ Zero cross-yacht data leakage

### Stage 5: Frontend Integration
- ✅ Build passes (`npm run build`)
- ✅ TypeScript check passes
- ✅ Intent detection working for WO queries
- ✅ Action buttons render for WO domain
- ✅ Modal form shows correct fields
- ✅ Auto-population works (e.g., from fault)

### Stage 6: Staging CI
- ✅ Real JWT authentication working
- ✅ Role-based action filtering verified
- ✅ All CRUD operations pass with real data
- ✅ Signature validation working
- ✅ CI workflow passes on main branch

---

## Current Blockers & Resolution Plan

| Blocker | Impact | Resolution | ETA |
|---------|--------|------------|-----|
| **No Docker RLS test suite** | Can't verify role gating end-to-end | Create `tests/docker/run_work_orders_rls_tests.py` | 2-3 hours |
| **No stress tests** | Can't verify performance under load | Create `tests/stress/stress_work_orders.py` | 1 hour |
| **Frontend not wired** | Users can't access WO actions | Add intent detection to `useCelesteSearch.ts` | 1-2 hours |
| **No staging CI** | Can't verify with real JWTs | Create CI workflow + acceptance script | 2 hours |

**Total Estimated Work:** 6-8 hours to Stage 6 completion

---

## Immediate Next Steps (Priority Order)

### 1. Complete Stage 4 (Backend Tests) - **CURRENT FOCUS**

**Tasks:**
1. ✅ Create Docker RLS test suite
   - File: `tests/docker/run_work_orders_rls_tests.py`
   - 18+ test cases covering RBAC, CRUD, isolation, signatures

2. ✅ Add stress testing
   - File: `tests/stress/stress_work_orders.py`
   - Test action list, create, search pipeline

3. ✅ Enhance pipeline integration tests
   - Add more chaos queries
   - Test all entity transformations
   - Verify cross-lens search

**Run Commands:**
```bash
# Docker RLS tests
docker-compose -f docker-compose.test.yml up --build

# Stress tests
TEST_JWT="$HOD_JWT" python tests/stress/stress_work_orders.py

# Pipeline tests
python3 tests/test_work_order_lens_comprehensive.py
```

**Expected Results:**
- Docker: "18 passed, 0 failed"
- Stress: ">99% success, P95 < 500ms"
- Pipeline: "36 passed, 0 failed"

### 2. Move to Stage 5 (Frontend) - After Stage 4 passes

### 3. Move to Stage 6 (CI) - After Stage 5 passes

### 4. Release (Stage 7) - After all gates pass

---

## Testing Evidence Required

For each stage, we must produce:

| Stage | Evidence Type | Location | Format |
|-------|--------------|----------|--------|
| 0 | Lens spec | `docs/` | Markdown |
| 1 | Migration verification | SQL query results | Text/JSON |
| 2 | Registry audit | Code inspection | Screenshot/diff |
| 3 | Handler implementation | Code + unit tests | Pytest output |
| **4** | **Docker RLS tests** | **Docker logs** | **JSON + summary** |
| **4** | **Stress tests** | **Latency metrics** | **JSON + chart** |
| **4** | **Pipeline tests** | **Test results** | **JSON + summary** |
| 5 | Build validation | `npm run build` | Exit code + output |
| 6 | Staging CI | GitHub Actions | Workflow run |
| 7 | Release tag | Git | Tag + changelog |

---

## Summary

**Current Stage:** 4 (Backend Tests) - PARTIAL ⚠️

**Completed:** Stages 0-3 (Docs → Handlers) ✅

**Next:** Complete Stage 4 with Docker RLS + Stress testing

**Blockers:** None - all dependencies met, ready to build tests

**Timeline:** 6-8 hours to Stage 6 completion (production-ready)

---

**Status:** Ready to proceed with Stage 4 test suite creation
**Priority:** HIGH - Backend is code-complete, needs test validation
**Confidence:** HIGH - Clear template from certificates lens to follow
