# Autonomous Production Readiness Plan

**Start:** 2026-02-10
**End:** 2026-02-17
**Goal:** All lenses functional, zero 404s, zero client mismatches, full E2E passing

---

## Methodology

1. **Audit First** - Map every endpoint, every client usage, every code path
2. **Test Locally** - Run full test suite locally before ANY deployment
3. **Fix in Batches** - Group related fixes, single deployment per batch
4. **Verify Production** - Automated validation after each deployment
5. **No Back-and-Forth** - Work autonomously, report daily summary only

---

## Day 1: Complete System Audit

### Task 1.1: Client Consistency Audit
Find ALL Supabase client mismatches across the codebase:
```bash
# Find all get_supabase_client vs get_tenant_client usage
grep -rn "get_supabase_client\|get_tenant_client" apps/api/routes/ --include="*.py"
```

**Expected Output:** List of every file with client type, identify mismatches.

### Task 1.2: Route Registration Audit
Verify every route is properly registered:
```bash
# List all routers and their prefixes
grep -rn "APIRouter\|include_router" apps/api/ --include="*.py"
```

### Task 1.3: Missing Endpoint Audit
Find endpoints referenced in frontend but missing in backend:
```bash
# Frontend API calls
grep -rn "fetch\|axios" apps/web/src/ --include="*.ts" --include="*.tsx" | grep "pipeline-core"
```

### Task 1.4: Database Schema Audit
Verify all tables exist and have correct RLS policies.

### Deliverable: `AUDIT_REPORT.md` with all issues categorized by severity.

---

## Day 2: Local Test Infrastructure

### Task 2.1: Create Comprehensive Test Suite
```python
# tests/full_system_test.py
- Test every lens entity extraction
- Test every endpoint returns 200/expected errors
- Test RBAC for all roles (CREW, HOD, CAPTAIN)
- Test client consistency (same data from inbox/detail)
```

### Task 2.2: Mock Data Setup
Create seed data that exercises all code paths:
- Work orders in all states
- Emails with/without attachments
- Parts with stock levels
- Shopping list items in all states

### Task 2.3: Run Full Local Test
```bash
python tests/full_system_test.py --env local
```

**Exit Criteria:** 100% pass rate locally.

---

## Day 3: Fix All Client Mismatches

### Task 3.1: Standardize Client Usage
Every route file should use `get_tenant_client(auth['tenant_key_alias'])`.

Files to audit and fix:
- [ ] routes/email.py
- [ ] routes/fault_routes.py
- [ ] routes/certificate_routes.py
- [ ] routes/context_navigation_routes.py
- [ ] routes/hours_of_rest_routes.py
- [ ] routes/p0_actions_routes.py
- [ ] routes/related_routes.py
- [ ] routes/triggers_routes.py

### Task 3.2: Create Single PR with All Fixes
One atomic commit with all client fixes.

### Task 3.3: Local Verification
Re-run full test suite. Must pass 100%.

---

## Day 4: Fix All Missing Endpoints

### Task 4.1: Implement Missing Routes
Based on Day 1 audit, implement any missing endpoints.

### Task 4.2: Fix 404 Errors
- Email thread detail
- Capabilities endpoint
- Any other 404s from audit

### Task 4.3: Local Verification
Full test suite must pass.

---

## Day 5: Entity Extraction Completeness

### Task 5.1: Audit All Lenses
Every lens must have:
- COMPOUND_ANCHORS patterns (domain_microactions.py)
- DOMAIN_KEYWORDS entries (term_classifier.py)
- Actions in registry

Lenses to verify:
- [ ] work_orders
- [ ] equipment
- [ ] parts/inventory
- [ ] documents
- [ ] faults
- [ ] shopping_list
- [ ] emails
- [ ] certificates
- [ ] hours_of_rest
- [ ] receiving

### Task 5.2: Test All Entity Extraction
```python
# Test every lens with 5+ real queries each
test_queries = {
    'work_orders': ['show work orders', 'pending tasks', ...],
    'shopping_list': ['shopping list', 'candidate parts', ...],
    # ... all lenses
}
```

### Task 5.3: Fix Any Gaps
Add missing patterns/keywords.

---

## Day 6: RBAC & Actions Completeness

### Task 6.1: Test All Role/Action Combinations
```
| Action | CREW | HOD | CAPTAIN | Expected |
|--------|------|-----|---------|----------|
| create_wo | ✓ | ✓ | ✓ | All can create |
| approve_wo | ✗ | ✓ | ✓ | HOD+ only |
| ... | | | | |
```

### Task 6.2: Verify Action Surfacing
For each lens, verify correct actions appear for each role.

### Task 6.3: Fix RBAC Gaps
Ensure consistent enforcement.

---

## Day 7: Production Deployment & Validation

### Task 7.1: Single Deployment
Merge all fixes to main. Single deployment with all changes.

### Task 7.2: Production Validation Script
```bash
#!/bin/bash
# Automated production validation
# Must pass 100% before sign-off

# 1. Auth check
# 2. All lenses entity extraction
# 3. All endpoints return expected status
# 4. Email detail loads
# 5. Actions surface correctly
# 6. No 500 errors
```

### Task 7.3: Final Report
Generate evidence report with all test results.

---

## Success Criteria (All Must Pass)

| Category | Metric | Target |
|----------|--------|--------|
| Entity Extraction | All lenses detect correctly | 100% |
| Endpoints | No unexpected 404s | 0 |
| Client Consistency | Inbox/Detail match | 100% |
| RBAC | Correct actions per role | 100% |
| Production Errors | 500 errors | 0 |

---

## Execution Rules

1. **No deployment until local tests pass 100%**
2. **Group fixes into logical batches (max 3 PRs)**
3. **Automated validation after each deployment**
4. **If any failure: stop, investigate, fix, re-test**
5. **Daily summary only - no questions**

---

## Tools & Scripts

All scripts will be created in `/tests/` and committed to repo:
- `tests/full_system_test.py` - Complete local test suite
- `tests/client_audit.py` - Find client mismatches
- `tests/endpoint_audit.py` - Find missing endpoints
- `tests/production_validation.sh` - Post-deploy validation

---

**Status:** Ready to execute Day 1
