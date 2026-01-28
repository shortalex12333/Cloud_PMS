# Phase 0: Gap Analysis - Shopping List Lens

**Date**: 2026-01-28
**Analyst**: Senior Full Stack Engineer
**Status**: ✅ COMPLETE

---

# EXECUTIVE SUMMARY

The Shopping List Lens is approximately **25% complete** - significantly less than initially estimated.

**Current State**: STAGE 1.5 (Design + Partial DB)
- ✅ Design complete (lens spec exists)
- ✅ Database tables exist in production
- ⚠️ Only 1 of 5 handlers implemented (and has bugs)
- ❌ Zero tests
- ❌ No feature flags
- ❌ No frontend integration
- ❌ Not production-ready

**Critical Finding**: The existing `add_to_shopping_list_execute` handler uses WRONG table name (`shopping_list` instead of `pms_shopping_list_items`) and has incorrect field mappings. This handler will FAIL if called.

---

# DETAILED GAP ANALYSIS

## 1. DATABASE SCHEMA ✅ (100% Complete)

### ✅ Table: `pms_shopping_list_items`
**Status**: EXISTS in production
**Row Count**: 34 rows
**Columns**: 45 (matches spec exactly)

#### Schema Verification:
| Component | Spec | Production | Match |
|-----------|------|------------|-------|
| Columns | 45 | 45 | ✅ |
| Status CHECK | 7 values | 7 values | ✅ |
| Source Type CHECK | 6 values | 6 values | ✅ |
| Urgency CHECK | 4 values | 4 values | ✅ |
| Quantity CHECKs | 5 constraints | 5 constraints | ✅ |
| Foreign Keys | 7 FKs | 7 FKs | ✅ |
| Indexes | 12 | 12 | ✅ |

#### RLS Policies: ✅ CANONICAL
- ✅ SELECT: All authenticated users (yacht-scoped)
- ✅ INSERT: All users (status='candidate', yacht-scoped)
- ✅ UPDATE: HoD only (using `is_hod()` helper)
- ✅ Service role bypass

#### Triggers: ✅ COMPLETE
- ✅ `trg_enforce_shopping_list_edit_rules` (BEFORE UPDATE)
- ✅ `trg_log_shopping_list_state_change` (AFTER INSERT/UPDATE)

**VERDICT**: ✅ Database is production-ready, no changes needed

---

### ✅ Table: `pms_shopping_list_state_history`
**Status**: EXISTS in production
**Row Count**: 36 rows
**Columns**: 13 (matches spec exactly)

#### Schema Verification:
| Component | Spec | Production | Match |
|-----------|------|------------|-------|
| Columns | 13 | 13 | ✅ |
| Foreign Keys | 4 FKs | 4 FKs | ✅ |
| Indexes | 5 | 5 | ✅ |
| CASCADE on shopping_list_item | YES | YES | ✅ |

#### RLS Policies: ✅ CANONICAL
- ✅ SELECT: All authenticated users (yacht-scoped)
- ✅ INSERT: Service role only (auto-populated by trigger)

**VERDICT**: ✅ State history table is production-ready

---

### Database Functions

#### ✅ `log_shopping_list_state_change()`
**Status**: Exists (referenced by triggers)
**Purpose**: Auto-log state transitions to history table

#### ✅ `enforce_shopping_list_edit_rules()`
**Status**: Exists (referenced by trigger)
**Purpose**: Enforce state machine transitions

**VERDICT**: ✅ All database functions exist

---

## 2. BACKEND IMPLEMENTATION ❌ (20% Complete)

### Registry Status: ⚠️ PARTIAL (1 of 5 actions)

#### ✅ Registered Action:
**File**: `apps/api/action_router/registry.py`

```python
"add_to_shopping_list": ActionDefinition(
    action_id="add_to_shopping_list",
    label="Add to Shopping List",
    endpoint="/v1/parts/shopping-list/add",
    handler_type=HandlerType.INTERNAL,
    method="POST",
    allowed_roles=["deckhand", "bosun", "eto", "chief_engineer", "chief_officer", "captain", "manager"],
    search_keywords=["add", "shopping", "list", "order", "request", "part", "buy", "purchase", "need", "reorder"],
    # ... domain, variant, etc.
)
```

**Issues**:
- ❌ Wrong endpoint: `/v1/parts/shopping-list/add` (should be `/v1/actions/execute`)
- ❌ Too many roles: includes "deckhand", "bosun", "eto" (should be standard crew roles)
- ⚠️ Missing required_fields definition

#### ❌ Missing Actions (4 of 5):
1. ❌ `approve_shopping_list_item` - NOT registered
2. ❌ `reject_shopping_list_item` - NOT registered
3. ❌ `promote_candidate_to_part` - NOT registered
4. ❌ `view_shopping_list_history` - NOT registered

---

### Handler Status: ❌ CRITICAL BUGS (1 of 5 implemented)

#### ⚠️ Implemented Handler: `add_to_shopping_list_execute`
**File**: `apps/api/handlers/purchasing_mutation_handlers.py`
**Line**: 390-530

**CRITICAL BUGS**:

1. **❌ WRONG TABLE NAME**
   ```python
   # Current (WRONG):
   await self.db.table("shopping_list").insert({...})

   # Should be:
   await self.db.table("pms_shopping_list_items").insert({...})
   ```
   **Impact**: Handler will FAIL with "table does not exist" error

2. **❌ WRONG FIELD NAMES**
   ```python
   # Current (WRONG):
   "requested_by": user_id,
   "requested_by_name": user["name"],
   "requested_by_role": user["role"],

   # Should be:
   "created_by": user_id,
   "source_type": "manual_add",  # Required field, missing
   # No requested_by_* fields in schema
   ```

3. **❌ MISSING REQUIRED FIELDS**
   - `source_type` (NOT NULL) - not set
   - `is_candidate_part` (NOT NULL, default=false) - should be set explicitly
   - `updated_at` (NOT NULL, default=now()) - missing

4. **❌ WRONG AUDIT LOG TABLE**
   ```python
   # Current (WRONG):
   await self.db.table("audit_log").insert({...})

   # Should be:
   await self.db.table("pms_audit_log").insert({...})
   ```

5. **❌ INCOMPLETE VALIDATION**
   - No validation for `part_name` (required even if part_id provided)
   - No validation for quantity > 0 (has CHECK constraint)
   - No check for part_id existence if provided

**VERDICT**: ❌ Handler WILL NOT WORK - needs complete rewrite

---

#### ❌ Missing Handlers (4 of 5):

From docstring (lines 11-14), these are PLANNED but NOT IMPLEMENTED:
```python
# Handlers:
# - add_to_shopping_list_execute: Add item to shopping list  ✅ (but broken)
# - approve_shopping_item_execute: Approve shopping list item  ❌ NOT FOUND
# - reject_shopping_item_execute: Reject shopping list item    ❌ NOT FOUND
# - update_shopping_list_execute: Update shopping list item    ❌ NOT FOUND
# - delete_shopping_item_execute: Remove shopping list item    ❌ NOT FOUND
```

**Search Results**:
```bash
$ grep -n "def.*shopping" purchasing_mutation_handlers.py
390:    async def add_to_shopping_list_execute(

# Only 1 method found
```

**VERDICT**: ❌ 4 of 5 handlers missing entirely

---

### Dispatcher Status: ❌ NOT INTEGRATED

**File**: `apps/api/action_router/dispatchers/internal_dispatcher.py`

**Search Result**:
```bash
$ grep "shopping" internal_dispatcher.py
607:    item_result = supabase.table("pms_shopping_list_items").select(
621:    result = supabase.table("pms_shopping_list_items").delete().eq(
```

**Analysis**: Only raw SQL queries found (lines 607, 621), no dispatcher routing for shopping list actions.

**Expected** (not present):
```python
elif action_id == "create_shopping_list_item":
    handler = ShoppingListHandlers(supabase_client)
    result = await handler.create_item_execute(entity_id, yacht_id, payload)
```

**VERDICT**: ❌ No dispatcher integration

---

## 3. TESTS ❌ (0% Complete)

### Docker RLS Tests: ❌ NOT FOUND
**Expected File**: `tests/docker/shopping_list_rls_tests.py`
**Status**: Does not exist

**Search Result**:
```bash
$ find tests -name "*shopping*" -type f
# No results
```

**Required Tests** (18):
- Role & CRUD: 8 tests (CREW/HOD/ENGINEER permissions)
- Isolation: 4 tests (cross-yacht, anon access)
- Edge Cases: 6 tests (404, 400, 409, terminal states)

**VERDICT**: ❌ Zero tests exist

---

### Staging CI Acceptance: ❌ NOT FOUND
**Expected File**: `tests/ci/staging_shopping_list_acceptance.py`
**Status**: Does not exist

**Expected Tests** (10):
- Suggestions & context gating: 3 tests
- CRUD flow with real JWTs: 4 tests
- Edge cases: 3 tests

**VERDICT**: ❌ Zero CI tests exist

---

### CI Workflow: ❌ NOT FOUND
**Expected File**: `.github/workflows/staging-shopping-list-acceptance.yml`
**Status**: Does not exist

**Search Result**:
```bash
$ grep -r "shopping" .github/workflows/*.yml
# No results
```

**VERDICT**: ❌ No CI workflow configured

---

### Stress Tests: ❌ NOT FOUND
**Expected File**: `tests/stress/shopping_list_actions_stress.py`
**Status**: Does not exist

**Required**:
- Create stress (80 concurrent)
- Approve stress (40 concurrent)
- Read stress (100 concurrent)
- 0×500 requirement

**VERDICT**: ❌ No stress tests exist

---

## 4. FEATURE FLAGS ❌ (0% Complete)

### Feature Flag Definition: ❌ NOT FOUND
**Expected**: `SHOPPING_LIST_V1_ENABLED` environment variable

**Search Result**:
```bash
$ grep -r "SHOPPING_LIST.*ENABLED" apps/api
# No results
```

**VERDICT**: ❌ No feature flags implemented

---

### Fail-Closed Behavior: ❌ NOT IMPLEMENTED
**Expected**: Return 503 when feature flag is OFF

**Status**: No feature flag checks in code

**VERDICT**: ❌ No fail-closed behavior

---

## 5. FRONTEND INTEGRATION ❌ (0% Complete)

### Search Hook: ❌ NOT INTEGRATED
**File**: `apps/web/src/hooks/useCelesteSearch.ts`

**Search Result**:
```bash
$ grep "shopping" apps/web/src/hooks/useCelesteSearch.ts
# No results
```

**Expected**: Intent detection for shopping list queries

**VERDICT**: ❌ No search integration

---

### Action Modal: ❌ NOT INTEGRATED
**File**: `apps/web/src/components/actions/ActionModal.tsx`

**Expected**: Dynamic form fields for shopping list actions

**VERDICT**: ❌ No modal integration (not checked, but follows from no registry)

---

### Suggested Actions: ❌ NOT INTEGRATED
**Expected**: Shopping list actions appear in suggestions

**VERDICT**: ❌ No UI integration

---

## 6. DEPLOYMENT ❌ (0% Complete)

### Canary Deployment: ❌ NOT DONE
**Status**: No evidence of canary testing

**VERDICT**: ❌ Never deployed to canary

---

### Production Rollout: ❌ NOT DONE
**Status**: Feature not in production

**VERDICT**: ❌ Not production-ready

---

# CRITICAL FINDINGS

## 🚨 Blocker #1: Broken Handler
**Impact**: HIGH
**Description**: The only implemented handler (`add_to_shopping_list_execute`) uses wrong table name and will fail with "table does not exist" error.

**Evidence**:
```python
# Line 460 in purchasing_mutation_handlers.py
await self.db.table("shopping_list").insert({...})  # ❌ WRONG

# Correct table name from DB:
pms_shopping_list_items  # ✅ CORRECT
```

**Resolution**: Complete rewrite of handler required

---

## 🚨 Blocker #2: Missing Core Actions
**Impact**: HIGH
**Description**: 4 of 5 core actions are not implemented at all.

**Missing**:
- `approve_shopping_list_item` (HoD approval flow)
- `reject_shopping_list_item` (HoD rejection)
- `promote_candidate_to_part` (Add to parts catalog)
- `view_shopping_list_history` (State timeline)

**Resolution**: Implement 4 missing handlers

---

## 🚨 Blocker #3: Zero Test Coverage
**Impact**: CRITICAL
**Description**: No tests exist. Cannot prove:
- RLS works correctly
- Role gating is enforced
- 0×500 requirement
- Edge cases handled

**Resolution**: Write 38+ tests (Docker + CI + Stress)

---

## 🚨 Blocker #4: No Production Safeguards
**Impact**: HIGH
**Description**: No feature flags, no fail-closed behavior, no canary testing.

**Resolution**: Implement feature flags + canary plan

---

# EFFORT ESTIMATE

## Original Estimate: 20-30 hours
**Revised Estimate**: 25-35 hours

**Breakdown**:
| Phase | Original | Revised | Reason |
|-------|----------|---------|--------|
| Phase 0 | 1-2h | ✅ 2h | Gap analysis (DONE) |
| Phase 1 | 2-4h | ~~0h~~ | ✅ DB already complete |
| Phase 2 | 4-6h | 6-8h | Rewrite 1 handler + add 4 new |
| Phase 3 | 3-4h | 4-5h | Write 18 Docker RLS tests |
| Phase 4 | 2-3h | 3-4h | Write 10 CI acceptance tests |
| Phase 5 | 1-2h | 2h | Feature flags + fail-closed |
| Phase 6 | 4-6h | 5-7h | Frontend (no shortcuts) |
| Phase 7 | 2-3h | 3h | Stress tests |
| Phase 8 | 24-48h | 24-48h | Canary (unchanged) |
| **TOTAL** | **20-30h** | **25-35h** | +5h due to handler bugs |

---

# NEXT STEPS

## Immediate Actions (Phase 1 - Now Phase 2)

Since the database is complete, we skip directly to **Phase 2: Backend Implementation**.

### Step 1: Fix Existing Handler (1 hour)
- Rewrite `add_to_shopping_list_execute` with correct table/field names
- Add proper validation
- Fix audit log

### Step 2: Implement Missing Handlers (5-7 hours)
1. `create_shopping_list_item` (replace broken add_to_shopping_list)
2. `approve_shopping_list_item`
3. `reject_shopping_list_item`
4. `promote_candidate_to_part`
5. `view_shopping_list_history`

### Step 3: Update Registry (1 hour)
- Replace `add_to_shopping_list` with `create_shopping_list_item`
- Add 4 new actions
- Fix allowed_roles
- Fix endpoint paths

### Step 4: Dispatcher Integration (30 minutes)
- Add routing for all 5 actions

---

# COMPARISON TO SPEC

## Lens Spec (`shopping_list_lens_v1_FINAL.md`)
**Status**: "v1 - PRODUCTION READY"
**Blockers**: "✅ None - Shopping List Lens is fully shippable"

## Reality Check: ❌ FALSE
**Actual Status**: "v0.25 - DESIGN + PARTIAL DB ONLY"
**Actual Blockers**:
1. ❌ Broken handler (wrong table name)
2. ❌ 4 of 5 handlers missing
3. ❌ Zero tests
4. ❌ No feature flags
5. ❌ No frontend
6. ❌ No deployment

**Gap**: Spec claims "production ready" but implementation is 25% complete.

---

# FILES TO CREATE/MODIFY

## Phase 2: Backend (8 files)
1. ✏️ `apps/api/handlers/shopping_list_handlers.py` (NEW)
2. ✏️ `apps/api/action_router/registry.py` (MODIFY)
3. ✏️ `apps/api/action_router/dispatchers/internal_dispatcher.py` (MODIFY)
4. 🗑️ `apps/api/handlers/purchasing_mutation_handlers.py` (DELETE broken handler)

## Phase 3: Docker Tests (1 file)
5. ✏️ `tests/docker/shopping_list_rls_tests.py` (NEW)

## Phase 4: CI Tests (2 files)
6. ✏️ `tests/ci/staging_shopping_list_acceptance.py` (NEW)
7. ✏️ `.github/workflows/staging-shopping-list-acceptance.yml` (NEW)

## Phase 5: Feature Flags (2 files)
8. ✏️ `apps/api/config.py` (MODIFY - add flag)
9. ✏️ `docs/pipeline/shopping_list_lens/SHOPPING_LIST_FEATURE_FLAGS.md` (NEW)

## Phase 6: Frontend (3 files)
10. ✏️ `apps/web/src/hooks/useCelesteSearch.ts` (MODIFY)
11. ✏️ `apps/web/src/components/actions/ActionModal.tsx` (MODIFY)
12. ✏️ `apps/web/src/components/shopping-list/ShoppingListDetail.tsx` (NEW)

## Phase 7: Stress Tests (1 file)
13. ✏️ `tests/stress/shopping_list_actions_stress.py` (NEW)

## Phase 8: Evidence (3 files)
14. ✏️ `docs/evidence/shopping_list/docker_rls_results.txt` (NEW)
15. ✏️ `docs/evidence/shopping_list/ci_acceptance_results.txt` (NEW)
16. ✏️ `docs/evidence/shopping_list/stress_results.txt` (NEW)

**Total**: 16 files (9 new, 5 modified, 1 deleted, 1 fixed)

---

# CONCLUSION

The Shopping List Lens has a solid database foundation (100% complete) but virtually no backend implementation (20% complete with critical bugs), zero tests, and no deployment infrastructure.

**Recommendation**: Proceed with Phase 2 (Backend Implementation) immediately. The database is production-ready; all effort should focus on handlers, tests, and deployment.

**Risk Level**: 🟡 MEDIUM
- Database is solid (low risk)
- Handler bugs are fixable (medium risk)
- No test coverage (high risk if we skip testing)

**Confidence in Estimate**: 🟢 HIGH
- Database inspection complete
- Handler bugs documented
- Scope well-defined

---

**PHASE 0 STATUS**: ✅ COMPLETE
**NEXT PHASE**: Phase 2 - Backend Implementation (Phase 1 skipped - DB already done)

---

END OF GAP ANALYSIS
