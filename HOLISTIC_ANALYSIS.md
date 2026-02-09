# HOLISTIC SYSTEM ANALYSIS - MASTER/TENANT ARCHITECTURE ISSUES
**Date**: 2026-02-09
**Purpose**: Complete analysis of ALL issues related to MASTER/TENANT Supabase split before implementing fixes

---

## EXECUTIVE SUMMARY

The system uses a MASTER/TENANT Supabase architecture where:
- Users authenticate via MASTER Supabase (central auth server)
- Data operations happen on TENANT Supabase (per-yacht databases)

This creates fundamental issues with:
1. **RLS (Row Level Security)** - Policies fail when MASTER users don't exist in TENANT
2. **Foreign Key Constraints** - FK to auth.users fail when users exist in MASTER but not TENANT
3. **Action Registration Gaps** - Some actions defined but not routed
4. **RBAC Pattern Inconsistencies** - Multiple enforcement patterns across codebase
5. **Error Handling** - 500 errors returned for client errors (should be 4xx)

---

## 1. RLS ISSUES (get_user_db vs get_service_db)

### Root Cause
- `get_user_db(user_jwt)` creates client with user JWT → RLS enforced
- RLS policies use `public.get_user_yacht_id()` function
- Function queries: `SELECT yacht_id FROM auth_users_profiles WHERE id = auth.uid()`
- MASTER-authenticated users don't exist in TENANT `auth_users_profiles`
- Function returns NULL → RLS policy denies access → 401 Unauthorized

### Pattern
```python
# ❌ BROKEN with MASTER/TENANT:
db = get_user_db(user_jwt, yacht_id)
result = db.from_("pms_receiving").select("*").execute()
# FAILS: 401 Unauthorized because get_user_yacht_id() returns NULL

# ✅ FIXED with service role (safe when RBAC enforced at route):
db = get_service_db(yacht_id)
result = db.from_("pms_receiving").select("*").execute()
# SUCCESS: Service role bypasses RLS
```

### Instances Found

#### FIXED (8 handlers in receiving_handlers.py):
1. ✅ `_attach_receiving_image_with_comment_adapter` (line ~290)
2. ✅ `_extract_receiving_candidates_adapter` (line ~420)
3. ✅ `_update_receiving_fields_adapter` (line ~615)
4. ✅ `_add_receiving_item_adapter` (line ~750)
5. ✅ `_adjust_receiving_item_adapter` (line ~890)
6. ✅ `_link_invoice_document_adapter` (line ~1010)
7. ✅ `_accept_receiving_adapter` (line ~1120)
8. ✅ `_reject_receiving_adapter` (line ~1180)

#### REMAINING ISSUES:
1. ❌ **receiving_handlers.py:1250** - `_view_receiving_history_adapter` still uses `get_user_db`

#### Search Pattern Used:
```bash
grep -rn "get_user_db" /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api/handlers --include="*.py"
```

**Result**: 1 remaining usage (excluding db_client.py definition and tests)

---

## 2. FOREIGN KEY CONSTRAINT VIOLATIONS

### Root Cause
Tables have FK constraints to `auth.users(id)`:
```sql
created_by_user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE
```

MASTER-authenticated users don't exist in TENANT `auth.users` table → INSERT fails with FK violation

### All FK Constraints Found (34 total)

#### CRITICAL (User Attribution - Break Frequently):
1. ❌ **user_profiles.id** (PK FK) - Every user needs profile → BREAKS ON ONBOARDING
2. ❌ **user_roles.user_id** - Every user needs roles → BREAKS ON ONBOARDING
3. ❌ **user_roles.assigned_by** - When MASTER user assigns roles
4. ❌ **work_orders.created_by** - When MASTER user creates work order
5. ❌ **work_orders.assigned_to** - When work order assigned to MASTER user
6. ❌ **work_orders.completed_by** - When MASTER user completes work order
7. ❌ **work_orders.closed_by** - When MASTER user closes work order
8. ❌ **work_order_notes.created_by** - When MASTER user adds note
9. ❌ **signatures.user_id** - When MASTER user signs action (SIGNED workflows)
10. ❌ **audit_events.user_id** - FIXED in migration 20260209_001

#### HIGH PRIORITY (Frequently Used):
11. ❌ **faults.reported_by** - When MASTER user reports fault
12. ❌ **faults.resolved_by** - When MASTER user resolves fault
13. ❌ **parts.last_counted_by** - When MASTER user counts stock
14. ❌ **shopping_list_items.added_by** - When MASTER user adds shopping item
15. ❌ **part_usage.used_by** - When MASTER user uses part
16. ❌ **pms_part_usage_v2.used_by** - When MASTER user logs part usage
17. ❌ **user_bookmarks.added_by** - When MASTER user adds bookmark
18. ❌ **bookmark_items.added_by** - When MASTER user adds bookmark item
19. ❌ **navigation_contexts.created_by_user_id** - FIXED in migration 20260209_001
20. ❌ **user_added_relations.created_by_user_id** - FIXED in migration 20260209_001

#### MEDIUM PRIORITY (Less Frequent):
21. ❌ **api_tokens.user_id** - When MASTER user creates API token
22. ❌ **api_tokens.revoked_by** - When MASTER user revokes token
23. ❌ **work_order_history.created_by** - When MASTER user creates history entry
24. ❌ **auth_microsoft_tokens.user_id** - When MASTER user stores MS tokens
25. ❌ **email_cache.user_id** - When MASTER user caches emails
26. ❌ **email_links.accepted_by** - When MASTER user accepts email link
27. ❌ **email_links.modified_by** - When MASTER user modifies email link
28. ❌ **email_links.removed_by** - When MASTER user removes email link
29. ❌ **email_links.rejected_by** - When MASTER user rejects email link
30. ❌ **recent_activity.user_id** - When MASTER user activity tracked

### Migration Files Affected:
- `00000000000001_01_core_tables_v2_secure.sql` (5 FKs)
- `00000000000004_02_p0_actions_tables_REVISED.sql` (12 FKs)
- `00000000000006_03_add_accountability_columns.sql` (3 FKs)
- `00000000000010_04_trust_accountability_tables.sql` (4 FKs)
- `00000000000021_phase4_email_transport_layer.sql` (7 FKs)
- `00000000000024_email_rejected_state.sql` (1 FK)
- `20260115000000_context_navigation_tables.sql` (3 FKs) - 3 FIXED

### Search Pattern Used:
```bash
grep -rn "REFERENCES auth.users" /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/supabase/migrations --include="*.sql"
```

---

## 3. ACTION REGISTRATION ANALYSIS

### WORK_ORDER_LENS_ROLES (p0_actions_routes.py:779-805)

#### Actions Defined (21 total):
1. ✅ `view_work_order` - Has routing
2. ✅ `view_work_order_detail` - Has routing
3. ✅ `view_work_order_checklist` - Has routing (line 2413)
4. ✅ `view_work_order_history` - Has routing (line 2727)
5. ✅ `view_my_work_orders` - Needs verification
6. ✅ `list_work_orders` - Has routing (line 2152) - JUST ADDED
7. ✅ `update_work_order` - Has routing
8. ✅ `assign_work_order` - Has routing
9. ✅ `start_work_order` - Has routing
10. ✅ `cancel_work_order` - Has routing
11. ✅ `add_note_to_work_order` - Has routing (line 1013)
12. ✅ `add_part_to_work_order` - Has routing (line 1097)
13. ✅ `add_work_order_photo` - Has routing (line 2304)
14. ✅ `close_work_order` - Has routing
15. ✅ `create_work_order` - Has routing
16. ✅ `create_work_order_from_fault` - Has routing (line 1121)
17. ✅ `mark_work_order_complete` - Has routing (line 1109)
18. ✅ `reassign_work_order` - Has routing (line 1191)
19. ✅ `archive_work_order` - Has routing (line 1211)

### FAULT_LENS_ROLES (p0_actions_routes.py:752-757)
1. ✅ `report_fault` - Has routing (line 1558)
2. ✅ `add_fault_photo` - Has routing (line 1828)
3. ✅ `add_fault_note` - Has routing (line 2681)
4. ✅ `view_fault_detail` - Has routing (line 1858)
5. ✅ `view_fault_history` - Has routing (line 2659)

### PART_LENS_SIGNED_ROLES (p0_actions_routes.py:768-771)
1. ✅ `adjust_stock_quantity` - Has routing (line 1370)
2. ✅ `write_off_part` - Has routing (line 1393) - Handler-level RBAC

### Additional Actions Found (not in RBAC dicts):
- `view_equipment` (line 2605)
- `view_equipment_detail` (line 2624)
- `view_equipment_details` (line 2787)
- `view_equipment_history` (line 2809)
- `view_equipment_parts` (line 2832)
- `update_equipment_status` (line 2209)
- `suggest_parts` (line 2749)
- `export_worklist` (line 2500)

**TODO**: Verify if these actions need RBAC dictionary entries or if they use handler-level enforcement

---

## 4. RBAC PATTERN INCONSISTENCIES

### Three Different Enforcement Patterns Found:

#### Pattern 1: Dictionary-Based (Most Common)
```python
WORK_ORDER_LENS_ROLES = {
    "create_work_order": ["crew", "chief_engineer", "chief_officer", "captain", "manager"],
}

if action in WORK_ORDER_LENS_ROLES:
    if user_role not in WORK_ORDER_LENS_ROLES[action]:
        raise HTTPException(403, "Insufficient permissions")
```
**Location**: p0_actions_routes.py lines 779-805 (WORK_ORDER_LENS_ROLES)

#### Pattern 2: Handler-Level with RPC Call
```python
# In handler:
is_authorized = db.rpc("is_manager", {"user_id_param": user_id}).execute()
if not is_authorized.data:
    return {"error": "Only managers can write off parts"}
```
**Example**: `write_off_part` action (p0_actions_routes.py:1393)

#### Pattern 3: Department-Level RBAC
```python
# For create_work_order:
# crew allowed but department-level RBAC enforced in handler
"create_work_order": ["crew", "chief_engineer", "chief_officer", "captain", "manager"],
# Handler checks if crew member's department matches work order department
```
**Location**: create_work_order handler

### Issues:
1. **Inconsistent enforcement** - Some actions use dict, others use handler RPC
2. **Documentation gaps** - Comments don't always explain which pattern is used
3. **Testing complexity** - Different patterns require different test strategies

---

## 5. ERROR HANDLING ISSUES (500 → 4xx)

### Current State
The codebase has `map_postgrest_error()` utility (db_client.py:177) that properly maps PostgREST errors to standardized responses:
- 401/403/RLS violations → `RLS_DENIED` (handled)
- 404/not found → `NOT_FOUND` (handled)
- 409/duplicate → `CONFLICT` (handled)
- 400/invalid → `INVALID_REQUEST` (handled)

### Issues Found

#### 1. Receiving Handlers (receiving_handlers.py)
**Pattern**: All handlers use `map_postgrest_error()` correctly:
```python
try:
    db = get_service_db(yacht_id)
except Exception as e:
    logger.error(f"Failed to create database client: {e}")
    return map_postgrest_error(e, "DB_CLIENT_ERROR")  # ✅ CORRECT
```

**Status**: ✅ Error handling is good after RLS fixes

#### 2. Part Handlers (part_handlers.py)
**Issue**: Direct HTTPException with 500 on all errors:
```python
# Line 1535:
except Exception as e:
    logger.error(f"upload_part_image failed: {e}")
    raise HTTPException(status_code=500, detail=f"Failed to upload image: {str(e)}")  # ❌ WRONG
```

**Impact**: Image upload errors (validation, file size, etc.) return 500 instead of 400

**Files to Fix**:
- `part_handlers.py:1535` - upload_part_image
- `part_handlers.py:1598` - update_part_image

#### 3. Certificate Handlers (certificate_handlers.py)
**Pattern**: Generic INTERNAL_ERROR for all exceptions:
```python
# Lines 159, 235, 299, 343:
except Exception as e:
    logger.error(f"operation failed: {e}", exc_info=True)
    builder.set_error("INTERNAL_ERROR", str(e))  # ❌ Could be client error
    return builder.build()
```

**Issue**: Not distinguishing between client errors (404, 400) and server errors

#### 4. Action Router (action_router/router.py:504)
**Issue**: Generic 500 for action execution failures:
```python
raise HTTPException(
    status_code=500,  # ❌ WRONG - could be auth, validation, not found
    detail={
        "status": "error",
        ...
    }
)
```

#### 5. Action Response Schema (actions/action_response_schema.py:257)
**Issue**: Default status_code is 500:
```python
class ActionError(BaseModel):
    code: str
    message: str
    status_code: int = 500  # ❌ WRONG default - should infer from code
```

### Recommended Pattern
```python
from postgrest.exceptions import APIError
from handlers.db_client import map_postgrest_error

try:
    result = db.from_("table").select("*").execute()
except APIError as e:
    return map_postgrest_error(e, "OPERATION_FAILED")  # ✅ CORRECT - maps to proper status
except ValueError as e:
    # Client validation error
    return {"status": "error", "error_code": "VALIDATION_ERROR", "message": str(e)}
except Exception as e:
    # Truly unexpected error
    logger.error(f"Unexpected error: {e}", exc_info=True)
    return {"status": "error", "error_code": "INTERNAL_ERROR", "message": "Server error"}
```

### Files to Fix
1. ✅ **receiving_handlers.py** - Already uses map_postgrest_error correctly
2. ❌ **part_handlers.py** - Lines 1535, 1598 (image upload endpoints)
3. ❌ **certificate_handlers.py** - Lines 159, 235, 299, 343 (generic error handling)
4. ❌ **action_router/router.py** - Line 504 (generic 500 for action failures)
5. ❌ **actions/action_response_schema.py** - Line 257 (default status_code=500)

### Search Patterns Used:
```bash
# Find generic 500 returns:
grep -rn "(status_code.*500|HTTPException.*500)" apps/api --include="*.py"

# Find generic Exception catches:
grep -rn "except\s+(Exception|APIError)" apps/api/handlers --include="*.py" -A 3
```

### Impact Assessment
- **HIGH**: Part image upload (affects receiving workflow)
- **MEDIUM**: Certificate operations (less frequent but user-facing)
- **LOW**: Generic action router (specific handlers usually handle errors first)

---

## 6. COMPLETE LENS WORKFLOWS (For E2E Testing)

### Receiving Workflow
```
1. create_receiving [handler: create_receiving_adapter]
   → Creates receiving record (status: pending)
   → RBAC: chief_engineer, captain, manager

2. attach_receiving_image [handler: _attach_receiving_image_with_comment_adapter]
   → Uploads image to storage
   → Links image to receiving record
   → RBAC: chief_engineer, captain, manager
   → FIXED: Now uses get_service_db

3. extract_receiving_candidates [handler: _extract_receiving_candidates_adapter]
   → Calls AI to extract line items from image
   → Returns candidate items with quantities
   → RBAC: chief_engineer, captain, manager
   → FIXED: Now uses get_service_db

4. add_receiving_item [handler: _add_receiving_item_adapter]
   → Adds line item to receiving record
   → Links to part_id or creates new part
   → RBAC: chief_engineer, captain, manager
   → FIXED: Now uses get_service_db

5. adjust_receiving_item [handler: _adjust_receiving_item_adapter]
   → Updates quantity/price for line item
   → RBAC: chief_engineer, captain, manager
   → FIXED: Now uses get_service_db

6. link_invoice_document [handler: _link_invoice_document_adapter]
   → Attaches invoice document to receiving
   → RBAC: chief_engineer, captain, manager
   → FIXED: Now uses get_service_db

7. accept_receiving [handler: _accept_receiving_adapter] **SIGNED**
   → Finalizes receiving, updates inventory
   → Requires PIN+TOTP signature (captain/manager only)
   → RBAC: captain, manager
   → FIXED: Now uses get_service_db

8. reject_receiving [handler: _reject_receiving_adapter] **SIGNED**
   → Rejects receiving, no inventory update
   → Requires PIN+TOTP signature (captain/manager only)
   → RBAC: captain, manager
   → FIXED: Now uses get_service_db

9. view_receiving_history [handler: _view_receiving_history_adapter]
   → Views audit trail for receiving record
   → RBAC: all roles
   → ❌ ISSUE: Still uses get_user_db (line 1250)
```

### Work Order Workflow
```
1. create_work_order [SIGNED for HOD+, dept-RBAC for crew]
   → Creates work order with department, priority, description
   → crew: Can only create for their department
   → HOD+: Can create for any department
   → Requires signature

2. assign_work_order
   → Assigns to user_id
   → RBAC: chief_engineer, chief_officer, captain, manager
   → FK ISSUE: assigned_to references auth.users(id)

3. add_note_to_work_order
   → Adds progress note
   → RBAC: chief_engineer, chief_officer, captain, manager
   → FK ISSUE: created_by references auth.users(id)

4. add_part_to_work_order
   → Links part to work order
   → RBAC: chief_engineer, chief_officer, captain, manager

5. add_work_order_photo
   → Uploads photo to work order
   → RBAC: chief_engineer, chief_officer, captain, manager

6. mark_work_order_complete [SIGNED]
   → Marks as complete, requires signature
   → RBAC: chief_engineer, chief_officer, captain, manager
   → FK ISSUE: completed_by references auth.users(id)

7. close_work_order
   → Closes work order
   → RBAC: chief_engineer, chief_officer, captain, manager
   → FK ISSUE: closed_by references auth.users(id)
```

### Parts Workflow
```
1. check_stock_level
   → Views current stock quantity
   → RBAC: all roles

2. adjust_stock_quantity [SIGNED]
   → Manually adjusts stock (count, shrinkage, etc.)
   → Requires PIN+TOTP signature
   → RBAC: chief_engineer, captain, manager
   → FK ISSUE: signatures.user_id references auth.users(id)

3. write_off_part [SIGNED]
   → Writes off damaged/obsolete part
   → Requires PIN+TOTP signature + is_manager RPC check
   → RBAC: manager only (handler-level enforcement)
   → FK ISSUE: signatures.user_id references auth.users(id)

4. log_part_usage
   → Records part consumption (work order, maintenance, etc.)
   → RBAC: chief_engineer, chief_officer, captain, manager
   → FK ISSUE: used_by references auth.users(id)

5. add_to_shopping_list
   → Adds part to shopping list
   → RBAC: chief_engineer, chief_officer, captain, manager
   → FK ISSUE: added_by references auth.users(id)

6. upload_part_image
   → Uploads image for part
   → RBAC: chief_engineer, captain, manager
   → IMAGE UPLOAD FIX: multipart/form-data handling
```

### Fault Workflow
```
1. report_fault
   → Creates fault record
   → RBAC: crew, chief_engineer, chief_officer, captain
   → FK ISSUE: reported_by references auth.users(id)

2. add_fault_photo
   → Uploads photo to fault
   → RBAC: crew, chief_engineer, chief_officer, captain

3. add_fault_note
   → Adds note to fault
   → RBAC: crew, chief_engineer, chief_officer, captain

4. create_work_order_from_fault [SIGNED]
   → Creates work order linked to fault
   → Requires signature
   → RBAC: chief_engineer, chief_officer, captain, manager
   → FK ISSUE: work_orders.created_by references auth.users(id)

5. resolve_fault
   → Marks fault as resolved
   → RBAC: chief_engineer, chief_officer, captain
   → FK ISSUE: resolved_by references auth.users(id)
```

---

## 7. COMPREHENSIVE FIX PLAN

### Phase 1: Database Schema (Migration)
**File**: `supabase/migrations/20260209_002_remove_all_user_fk_constraints.sql`

Drop ALL FK constraints to `auth.users(id)`:
```sql
BEGIN;

-- Core user tables
ALTER TABLE public.user_profiles DROP CONSTRAINT IF EXISTS user_profiles_id_fkey;
ALTER TABLE public.user_roles DROP CONSTRAINT IF EXISTS user_roles_user_id_fkey;
ALTER TABLE public.user_roles DROP CONSTRAINT IF EXISTS user_roles_assigned_by_fkey;
ALTER TABLE public.api_tokens DROP CONSTRAINT IF EXISTS api_tokens_user_id_fkey;
ALTER TABLE public.api_tokens DROP CONSTRAINT IF EXISTS api_tokens_revoked_by_fkey;

-- Work order tables
ALTER TABLE public.work_orders DROP CONSTRAINT IF EXISTS work_orders_created_by_fkey;
ALTER TABLE public.work_orders DROP CONSTRAINT IF EXISTS work_orders_assigned_to_fkey;
ALTER TABLE public.work_orders DROP CONSTRAINT IF EXISTS work_orders_completed_by_fkey;
ALTER TABLE public.work_orders DROP CONSTRAINT IF EXISTS work_orders_closed_by_fkey;
ALTER TABLE public.work_order_notes DROP CONSTRAINT IF EXISTS work_order_notes_created_by_fkey;
ALTER TABLE public.work_order_history DROP CONSTRAINT IF EXISTS work_order_history_created_by_fkey;

-- Fault tables
ALTER TABLE public.faults DROP CONSTRAINT IF EXISTS faults_reported_by_fkey;
ALTER TABLE public.faults DROP CONSTRAINT IF EXISTS faults_resolved_by_fkey;

-- Part tables
ALTER TABLE public.parts DROP CONSTRAINT IF EXISTS parts_last_counted_by_fkey;
ALTER TABLE public.shopping_list_items DROP CONSTRAINT IF EXISTS shopping_list_items_added_by_fkey;
ALTER TABLE public.part_usage DROP CONSTRAINT IF EXISTS part_usage_used_by_fkey;
ALTER TABLE public.pms_part_usage_v2 DROP CONSTRAINT IF EXISTS pms_part_usage_v2_used_by_fkey;

-- Signature and audit tables
ALTER TABLE public.signatures DROP CONSTRAINT IF EXISTS signatures_user_id_fkey;
-- audit_events already fixed in 20260209_001

-- Bookmark tables
ALTER TABLE public.user_bookmarks DROP CONSTRAINT IF EXISTS user_bookmarks_added_by_fkey;
ALTER TABLE public.bookmark_items DROP CONSTRAINT IF EXISTS bookmark_items_added_by_fkey;

-- Email tables
ALTER TABLE public.auth_microsoft_tokens DROP CONSTRAINT IF EXISTS auth_microsoft_tokens_user_id_fkey;
ALTER TABLE public.email_cache DROP CONSTRAINT IF EXISTS email_cache_user_id_fkey;
ALTER TABLE public.email_links DROP CONSTRAINT IF EXISTS email_links_accepted_by_fkey;
ALTER TABLE public.email_links DROP CONSTRAINT IF EXISTS email_links_modified_by_fkey;
ALTER TABLE public.email_links DROP CONSTRAINT IF EXISTS email_links_removed_by_fkey;
ALTER TABLE public.email_links DROP CONSTRAINT IF EXISTS email_links_rejected_by_fkey;

-- Activity tracking
ALTER TABLE public.recent_activity DROP CONSTRAINT IF EXISTS recent_activity_user_id_fkey;

COMMIT;
```

### Phase 2: Application Code Fixes

#### 2.1 Fix Remaining RLS Issue
**File**: `apps/api/handlers/receiving_handlers.py:1250`
- Change `_view_receiving_history_adapter` to use `get_service_db`

#### 2.2 Error Handling Standardization
**Files**: All handler files in `apps/api/handlers/`

Pattern to implement:
```python
from postgrest.exceptions import APIError

try:
    result = db.from_("table").select("*").execute()
except APIError as e:
    # RLS/Permission errors
    if "Missing response" in str(e) or e.code == "204":
        return {"error": "Unauthorized - insufficient permissions", "status_code": 401}
    # Not found errors
    elif e.code == "PGRST116":
        return {"error": "Resource not found", "status_code": 404}
    # Other postgREST errors
    else:
        logger.error(f"PostgREST error: {e}")
        return {"error": "Database operation failed", "status_code": 500}
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    return {"error": "Internal server error", "status_code": 500}
```

#### 2.3 RBAC Pattern Consolidation
**File**: `apps/api/docs/RBAC_PATTERNS.md` (new documentation)

Document all three patterns and when to use each:
1. Dictionary-based (default for most actions)
2. Handler-level RPC (for complex role checks like is_manager)
3. Department-level (for actions like create_work_order)

### Phase 3: Comprehensive E2E Tests

#### 3.1 Receiving Workflow Test
**File**: `tests/e2e/test_receiving_complete_journey.py`

Test all 9 steps with:
- HOD role (success path)
- crew role (should fail RBAC)
- Invalid signatures (should fail on SIGNED actions)
- MASTER-authenticated users (should work after fixes)

#### 3.2 Work Order Workflow Test
**File**: `tests/e2e/test_work_order_complete_journey.py`

Test creation → assignment → completion → closure with:
- Department RBAC for crew
- HOD roles
- Signature validation
- FK constraint handling (no failures after migration)

#### 3.3 Parts Workflow Test
**File**: `tests/e2e/test_parts_complete_journey.py`

Test stock operations with:
- Signed actions (adjust, write-off)
- Image uploads
- Shopping list operations

#### 3.4 Fault Workflow Test
**File**: `tests/e2e/test_fault_complete_journey.py`

Test reporting → work order creation → resolution

---

## 8. IMPLEMENTATION CHECKLIST

### Pre-Implementation
- [x] Complete systematic analysis of ALL issues
- [x] Document ALL findings in HOLISTIC_ANALYSIS.md
- [ ] Review with user - get approval for approach
- [ ] Estimate testing requirements

### Implementation (ONE PR)
- [ ] Create migration 20260209_002_remove_all_user_fk_constraints.sql
- [ ] Fix remaining RLS issue (receiving_handlers.py:1250)
- [ ] Standardize error handling across all handlers
- [ ] Add RBAC pattern documentation
- [ ] Write comprehensive e2e tests (4 complete journeys)
- [ ] Run all tests locally
- [ ] Create single PR with all changes
- [ ] Deploy to staging
- [ ] Run e2e tests against staging
- [ ] Get user approval
- [ ] Deploy to production

### Post-Deployment Verification
- [ ] Monitor logs for 500 errors (should decrease)
- [ ] Monitor logs for FK violations (should be zero)
- [ ] Monitor logs for RLS errors (should be zero)
- [ ] Verify all lens workflows work with MASTER-authenticated users
- [ ] Confirm RBAC enforcement still working

---

## 9. RISK ASSESSMENT

### HIGH RISK
- **Dropping FK constraints**: Removes database-level referential integrity
  - **Mitigation**: Application-level validation, audit trails, e2e tests

### MEDIUM RISK
- **Changing error handling**: Could mask real issues if done incorrectly
  - **Mitigation**: Careful exception handling, maintain detailed logging

### LOW RISK
- **Fixing remaining RLS issue**: Pattern already proven in 8 other handlers
- **Adding documentation**: No code changes, just clarification

---

## 10. QUESTIONS FOR USER

1. **FK Constraint Removal**: Comfortable dropping ALL FK constraints to auth.users?
   - Alternative: Sync users from MASTER to TENANT (more complex)

2. **Migration Timing**: Should this be deployed as a hotfix or wait for next release?

3. **Testing Coverage**: Should e2e tests cover ALL lens workflows or just the ones with production errors?

4. **Error Handling**: Should we maintain 500 status for truly unexpected errors, or should we never return 500?

---

## CONCLUSION

This holistic analysis found:
- **1 remaining RLS issue** (get_user_db usage)
- **30+ FK constraints** that will break with MASTER/TENANT (3 already fixed)
- **Action registration complete** (list_work_orders was missing, now added)
- **RBAC patterns documented** (3 different patterns in use)
- **Error handling needs standardization** (500 → 4xx for client errors)

All issues can be fixed in ONE comprehensive PR with:
1. Database migration (drop FK constraints)
2. Code fix (1 handler)
3. Error handling standardization
4. Comprehensive e2e tests (4 lens journeys)

This approach ensures we understand the COMPLETE system holistically before making changes, avoiding the "merge every 5 minutes" problem.
