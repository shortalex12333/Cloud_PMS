# Inventory Lens - Baseline State

**Date**: 2026-02-08
**Engineer**: Claude (6-hour focused session)
**Objective**: Complete Inventory Lens implementation with hard evidence

---

## Current State Summary

### ✅ What's Working

1. **Action Registry** (`action_router/registry.py`):
   - `check_stock_level`: READ action, allowed_roles includes crew ✅
   - `log_part_usage`: MUTATE action, allowed_roles = ["engineer", "eto", "chief_engineer", "chief_officer", "captain", "manager"] ✅
   - Domain correctly set to "parts" ✅
   - ActionVariant.MUTATE correctly set ✅

2. **/v2/search** (`routes/orchestrated_search_routes.py`):
   - Returns context metadata ✅
   - Returns role-filtered actions array ✅
   - Normalizes inventory→parts ✅
   - Evidence: PR #167 merged

### ❌ What's Broken

1. **Missing Role Validation in Execution** (`routes/p0_actions_routes.py`):
   - Has `FAULT_LENS_ROLES` dictionary (lines 705-720)
   - Has `PART_LENS_SIGNED_ROLES` dictionary (lines 721-724)
   - **MISSING**: No `INVENTORY_LENS_ROLES` dictionary for standard MUTATE actions
   - Result: `log_part_usage` executes without role check
   - Security Risk: Crew can execute inventory mutations

2. **Incomplete /v1/search** (`microaction_service.py`):
   - Already has context + actions (from previous work)
   - Need to verify inventory→parts normalization is consistent

3. **Incomplete /search** (`pipeline_service.py`):
   - Uses `action_surfacing` module which already normalizes inventory→parts
   - Need to verify full parity

4. **Domain Detection Issue** (`orchestration/term_classifier.py`):
   - "oil filter" classified as work_orders instead of parts
   - Missing part-specific keywords
   - Need to add common part names to DOMAIN_KEYWORDS

5. **Capability Mapping** (`prepare/capability_composer.py`):
   - Need to verify inventory capabilities are properly mapped
   - STOCK_QUERY, LOW_STOCK, OUT_OF_STOCK should map to inventory tables

---

## Detailed Findings

### Finding 1: Missing Role Enforcement

**File**: `apps/api/routes/p0_actions_routes.py`

**Current Code** (lines 705-724):
```python
# Define allowed roles for each action (Fault Lens v1 - Phase 7)
FAULT_LENS_ROLES = {
    "report_fault": ["crew", "chief_engineer", "chief_officer", "captain"],
    "add_fault_photo": ["crew", "chief_engineer", "chief_officer", "captain"],
    # ... 10 more fault actions
}

# PART LENS SIGNED ACTIONS - STRICT role enforcement (captain/manager only)
PART_LENS_SIGNED_ROLES = {
    "adjust_stock_quantity": ["chief_engineer", "captain", "manager"],
}
```

**Problem**: No inventory MUTATE actions in either dictionary

**Actions Affected**:
- `log_part_usage` - crew can execute (should be 403)
- `consume_part` - crew can execute (should be 403)
- `receive_part` - crew can execute (should be 403)
- `transfer_part` - crew can execute (should be 403)
- `add_to_shopping_list` - crew can execute (should be 403)
- `order_part` - crew can execute (should be 403)

**Evidence**: E2E test showed crew got HTTP 400 (INSUFFICIENT_STOCK) instead of HTTP 403 (INSUFFICIENT_PERMISSIONS)

### Finding 2: Domain Detection

**File**: `apps/api/orchestration/term_classifier.py`

**Problem**: Query "oil filter" classified as domain="work_orders"

**Current DOMAIN_KEYWORDS** (sample):
```python
DOMAIN_KEYWORDS = {
    "parts": [
        "part", "parts", "inventory", "stock", "spare", "component",
        # Missing: specific part types like "oil filter", "bearing", "gasket"
    ],
    "work_orders": [
        "work order", "wo", "job", "task", "maintenance",
        "filter" # <-- This might be causing oil filter to match work_orders
    ]
}
```

**Impact**:
- Parts queries may return incorrect domain
- Action suggestions may be wrong
- User experience suffers

---

## Test Evidence Location

All E2E evidence from previous session:
- `test_artifacts/inventory/e2e_evidence/EVIDENCE_LOG.md`
- `test_artifacts/inventory/e2e_evidence/run_comprehensive_e2e.sh`
- Response JSON files for each test

Current Test Results:
- 6 PASS / 2 FAIL
- Failures: Both related to missing role validation

---

## Next Steps (In Order)

1. **[CRITICAL]** Add `INVENTORY_LENS_ROLES` dictionary to p0_actions_routes.py
2. **[CRITICAL]** Add role validation logic after PART_LENS_SIGNED_ROLES
3. **[HIGH]** Add part-specific keywords to term_classifier.py
4. **[MEDIUM]** Verify all 3 search endpoints have context + actions parity
5. **[MEDIUM]** Verify capability mappings for inventory
6. **[LOW]** Run comprehensive test suite and document evidence
7. **[LOW]** Create final REPORT.md

---

## Acceptance Criteria

### Security (CRITICAL)
- [ ] Crew cannot execute log_part_usage (must return 403)
- [ ] HOD can execute log_part_usage (must return 200/404)
- [ ] All inventory MUTATE actions gated by role
- [ ] Registry and runtime enforcement match

### Search Endpoints (HIGH)
- [ ] /v1/search returns context + actions for parts queries
- [ ] /v2/search returns context + actions for parts queries
- [ ] /search returns context + actions for parts queries
- [ ] All 3 normalize inventory→parts consistently

### Domain Detection (MEDIUM)
- [ ] "oil filter" classified as parts (not work_orders)
- [ ] "parts low in stock" classified as parts
- [ ] Common part names (bearing, gasket, seal) classified as parts

### Docker Fast Loop (HIGH)
- [ ] All role gating tests pass
- [ ] 4xx mapping correct (not 500)
- [ ] Anon vs service REST invariant maintained
- [ ] No OOM kills or exit code 137

---

## Files to Modify

1. `apps/api/routes/p0_actions_routes.py` - Add INVENTORY_LENS_ROLES
2. `apps/api/orchestration/term_classifier.py` - Add part keywords
3. `apps/api/prepare/capability_composer.py` - Verify mappings
4. `apps/api/test_artifacts/inventory/finish_line/run_comprehensive_tests.sh` - New test suite

Files to Verify (No Changes Needed):
- `apps/api/action_router/registry.py` - Already correct ✅
- `apps/api/routes/orchestrated_search_routes.py` - Already fixed ✅
- `apps/api/microaction_service.py` - Verify context + actions present
- `apps/api/pipeline_service.py` - Verify fusion normalization
- `apps/api/action_surfacing.py` - Verify inventory→parts normalization

---

## Timeline (6 Hours)

- **Hour 1**: Baseline documentation + fix role validation (CRITICAL)
- **Hour 2**: Fix domain detection + verify search endpoints
- **Hour 3**: Create comprehensive local test suite
- **Hour 4**: Run tests and capture evidence (all 3 endpoints × 2 roles)
- **Hour 5**: Docker fast loop + action execution tests
- **Hour 6**: Final REPORT.md with diffs, evidence, and recommendations

---

**Status**: Baseline complete, ready to begin fixes
