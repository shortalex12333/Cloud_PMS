# E2E Test Issues Analysis
## Date: 2026-01-30

## Test Results Summary
- **Status**: 6/7 tests failing
- **Root Causes**: 2 distinct issues found

---

## Issue #1: Backend Action Filtering Logic

### Problem
Backend returns wrong actions for role-based filtering:

**Chief Engineer Gets**:
```
['adjust_stock_quantity', 'receive_part', 'generate_part_labels', 'request_label_output', 'view_part_details']
```

**Chief Engineer Should Get**:
```
['view_part_details', 'receive_part', 'consume_part']
```

**Captain Gets**:
```
['adjust_stock_quantity', 'receive_part', 'generate_part_labels', 'request_label_output', 'view_part_details']
```

**Captain Should Get**:
```
['view_part_details', 'receive_part', 'consume_part', 'write_off_part', 'adjust_stock_quantity']
```

### Root Causes

#### 1. Stock Context Filtering (Out of Stock)
**File**: `apps/api/routes/part_routes.py` lines 328-368

The code filters out these actions if `is_out_of_stock = True`:
- `consume_part` (can't consume if out of stock)
- `transfer_part` (can't transfer if out of stock)
- `write_off_part` (can't write off if out of stock)

**Test Part**: `fa10ad48-5f51-41ee-9ef3-c2127e77b06a`
**Likely Status**: Out of stock (on_hand = 0)

**Fix Options**:
1. Update test to use a part with stock > 0
2. Add stock to the test part in setup
3. Remove the out-of-stock filter for `write_off_part` (you CAN write off items you don't have - accounting correction)

#### 2. Role Permissions Don't Match Security Model
**File**: `apps/api/action_router/registry.py`

**Current allowed_roles**:
- `adjust_stock_quantity` (SIGNED): `["bosun", "eto", "chief_engineer", "chief_officer", "captain", "manager"]`
- `write_off_part` (SIGNED): `["chief_engineer", "chief_officer", "captain", "manager"]`

**Expected Security Model** (from test documentation):
- READ actions: All roles
- MUTATE actions: Chief Engineer+ (deckhand, bosun, eto, chief_engineer, chief_officer, captain, manager)
- SIGNED actions: Captain+ only (captain, manager)

**Fix Required**: Update allowed_roles for SIGNED variant actions to Captain+ only:
```python
# Line 1775 - adjust_stock_quantity
allowed_roles=["captain", "manager"],  # Currently includes chief_engineer

# Line 1847 - write_off_part
allowed_roles=["captain", "manager"],  # Currently includes chief_engineer, chief_officer
```

---

## Issue #2: Frontend Search Not Rendering Results

### Problem
**UI State**: Shows "Searching..." but no entity cards or action buttons appear
**Test Impact**: `page.waitForSelector('[data-entity-type="part"]')` times out after 5000ms

### Evidence
From error-context.md:
```yaml
- generic [ref=e20]: Searching…
```

No part cards, no action buttons rendered.

### Possible Causes
1. Frontend search/entity extraction not triggering
2. Search query "Engine Oil Filter" not matching any parts
3. Frontend waiting for backend response that never completes
4. Entity card rendering logic broken

### Investigation Needed
1. Check frontend search implementation
2. Verify part name in database matches "Engine Oil Filter"
3. Check browser console for JavaScript errors
4. Verify frontend is calling `/v1/parts/suggestions` endpoint

---

## Recommended Fix Order

### Phase 1: Backend Fixes (Immediate)
1. **Fix role permissions** for SIGNED actions:
   - Update `adjust_stock_quantity` allowed_roles to `["captain", "manager"]`
   - Update `write_off_part` allowed_roles to `["captain", "manager"]`

2. **Fix test data** - either:
   - Update stock for test part `fa10ad48-5f51-41ee-9ef3-c2127e77b06a` to have `on_hand > 0`
   - OR use a different test part that has stock
   - OR remove out-of-stock filter for `write_off_part` (accounting correction use case)

### Phase 2: Frontend Investigation (Required before tests pass)
1. Investigate why search results aren't rendering
2. Fix entity card rendering logic
3. Verify action button rendering from backend suggestions

---

## Files to Modify

### Backend
- `apps/api/action_router/registry.py` (lines 1775, 1847)
- `apps/api/routes/part_routes.py` (optional: line 367-368 for write_off logic)
- `.env.e2e.local` or global setup (to ensure test part has stock)

### Frontend (Investigation Needed)
- Search/entity extraction logic
- Part card rendering component
- Action button rendering component

---

## Expected Test Results After Fixes

### After Backend Fixes Only
- **crew**: ✅ PASS (backend returns correct actions)
- **chief_engineer**: ⚠️ Still FAIL (UI not rendering)
- **captain**: ⚠️ Still FAIL (UI not rendering)

### After Backend + Frontend Fixes
- **All tests**: ✅ PASS
