# SYSTEMATIC FIX PLAN - CelesteOS Microactions

**Created:** 2026-01-21
**Updated:** 2026-01-21 (Schema fixes complete)
**Current Health:** 64% (41/64 working) - **ALL CRITICAL ERRORS ELIMINATED**
**Target Health:** 90%+ (58/64 working)

## COMPLETION STATUS

✅ **Phase 1 COMPLETE**: Fixed RUNTIME_ERROR handlers
✅ **Phase 2 COMPLETE**: Fixed DB_ERROR handlers
📝 **Remaining**: 23 VALIDATION_ERROR (mostly missing test data)

---

## METHODOLOGY

1. **Group by Root Cause** - Fix similar issues together
2. **Fix in Priority Order** - Critical errors first, then validation
3. **Test After Each Group** - Verify fixes don't cause regressions
4. **Document Patterns** - Prevent future similar issues

---

## CATEGORIZED ISSUE LIST

### CATEGORY A: RUNTIME_ERROR (3 actions) - Priority: CRITICAL
**Root Cause:** Python handler crashes due to code bugs (likely column name mismatches)

| Action | Error Type | Likely Cause |
|--------|------------|--------------|
| view_equipment_parts | 500 | Column query error in pms_parts |
| view_equipment_manual | 500 | Column query error in documents |
| view_linked_equipment | 500 | Column query error in pms_equipment |

**Fix Strategy:**
1. Read the pms_equipment schema to verify column names
2. Read the documents schema to verify column names
3. Update handlers to use correct column names
4. Add try/except for resilience

---

### CATEGORY B: DB_ERROR (6 actions) - Priority: HIGH
**Root Cause:** Database table doesn't exist or column mismatch

| Action | Error Type | Table Involved | Likely Cause |
|--------|------------|----------------|--------------|
| suggest_parts | 500 | pms_faults | fault_number column issue |
| view_part_stock | 500 | pms_parts | Column names mismatch |
| view_part_location | 500 | pms_parts | Column names mismatch |
| scan_part_barcode | 500 | pms_parts | Column names mismatch |
| export_handover | 500 | handovers | Table may not exist |
| regenerate_handover_summary | 500 | handovers | Table may not exist |

**Fix Strategy:**
1. Verify pms_parts table has been deployed with correct schema
2. Check if "handovers" vs "handover" table name issue
3. Add try/except blocks to handle missing tables gracefully
4. Update column names to match actual schema

---

### CATEGORY C: VALIDATION_ERROR - Missing Test Data (14 actions) - Priority: MEDIUM
**Root Cause:** Test sends required fields but entity IDs don't exist in database

#### C1: Missing Handover Data (5 actions)
| Action | Required Field | Test Data Status |
|--------|----------------|------------------|
| add_document_to_handover | handover_id | NO handover exists |
| add_predictive_insight_to_handover | handover_id | NO handover exists |
| edit_handover_section | handover_id | NO handover exists |
| view_smart_summary | entity_id | Generic - needs valid entity |
| request_predictive_insight | entity_id | Generic - needs valid entity |

**Fix Strategy:** Update test-data-discovery.ts to create test handover

#### C2: Missing Compliance/Crew Data (4 actions)
| Action | Required Field | Test Data Status |
|--------|----------------|------------------|
| view_hours_of_rest | crew_id | NO crew_id in test data |
| update_hours_of_rest | crew_id | NO crew_id in test data |
| export_hours_of_rest | crew_id | NO crew_id in test data |
| tag_for_survey | equipment_id | Has equipment_id but handler may reject |

**Fix Strategy:**
- Update test to use user_id as crew_id (same person)
- Or create crew test data

#### C3: Missing Purchase Data (7 actions)
| Action | Required Field | Test Data Status |
|--------|----------------|------------------|
| create_purchase_request | title | Has title - check handler |
| add_item_to_purchase | purchase_request_id | NO purchase request exists |
| approve_purchase | purchase_request_id | NO purchase request exists |
| upload_invoice | purchase_request_id | NO purchase request exists |
| track_delivery | purchase_request_id | NO purchase request exists |
| log_delivery_received | purchase_request_id | NO purchase request exists |
| update_purchase_status | purchase_request_id | NO purchase request exists |

**Fix Strategy:**
- First fix create_purchase_request to work
- Then test creates a PR and uses that ID for subsequent tests
- Or add purchase_requests table migration

---

### CATEGORY D: VALIDATION_ERROR - Business Logic (5 actions) - Priority: LOW
**Root Cause:** Handler correctly rejects the payload (not a bug)

| Action | Rejection Reason | Is This a Bug? |
|--------|------------------|----------------|
| show_manual_section | "No manual available" | NO - Correct if no manual |
| create_work_order_from_fault | "Work order already exists" | NO - Duplicate prevention |
| log_part_usage | "Not enough stock" | NO - Stock validation |
| view_checklist | Missing checklist_id | MAYBE - Test data issue |
| update_worklist_progress | Missing worklist_item_id | MAYBE - Test data issue |

**Fix Strategy:**
- Create test data for checklist and worklist items
- These business logic rejections are correct behavior

---

### CATEGORY E: VALIDATION_ERROR - Test Payload Issues (4 actions) - Priority: LOW
**Root Cause:** Test payload format doesn't match handler expectations

| Action | Issue |
|--------|-------|
| view_document_section | Need valid document_id + section_id |
| open_vessel | Need valid vessel_id |

**Fix Strategy:** Update test payloads or test data discovery

---

## EXECUTION PLAN

### PHASE 1: Fix RUNTIME_ERROR (3 actions)
**Estimated Impact:** 50% → 55%

1. Read pms_equipment table schema
2. Read documents table schema (verify storage_path vs file_path)
3. Fix view_equipment_parts handler
4. Fix view_equipment_manual handler
5. Fix view_linked_equipment handler
6. Deploy and test

### PHASE 2: Fix DB_ERROR (6 actions)
**Estimated Impact:** 55% → 64%

1. Verify pms_parts column names are correct in ALL handlers
2. Fix suggest_parts (fault_number column)
3. Fix view_part_stock, view_part_location, scan_part_barcode
4. Check handovers vs handover table name
5. Add try/except to handover export handlers
6. Deploy and test

### PHASE 3: Update Test Data Discovery
**Estimated Impact:** 64% → 80%

1. Add handover creation to test-data-discovery.ts
2. Add checklist/checklist_item creation
3. Add purchase_request creation (if table exists)
4. Use user_id as crew_id for HoR tests
5. Test locally then deploy

### PHASE 4: Fix Remaining Validation Issues
**Estimated Impact:** 80% → 90%

1. Fix create_purchase_request handler
2. Fix view_checklist handler
3. Fix update_worklist_progress handler
4. Fix any remaining payload mismatches
5. Deploy and test

---

## TABLE SCHEMA VERIFICATION NEEDED

Before fixing, verify these table schemas exist in tenant DB:

| Table | Expected Columns | Status |
|-------|------------------|--------|
| pms_parts | quantity_on_hand, quantity_minimum, storage_location | VERIFY |
| pms_equipment | id, name, make, model, location, status | VERIFY |
| pms_faults | fault_number (not fault_code) | VERIFY |
| documents | storage_path (not file_path), category | VERIFY |
| handovers | id, yacht_id, status, metadata | VERIFY |
| handover | (alternative table name?) | CHECK |
| hours_of_rest | crew_id, date, rest_hours | VERIFY |
| purchase_requests | id, title, status | VERIFY |
| pms_checklist_items | id, checklist_id, yacht_id | VERIFY |

---

## REGRESSION PREVENTION

After each phase:
```bash
npx playwright test tests/e2e/diagnostic_baseline.spec.ts
```

Track progress:
| Phase | Before | After | Regression? |
|-------|--------|-------|-------------|
| 1     | 50%    | ?     | |
| 2     | ?      | ?     | |
| 3     | ?      | ?     | |
| 4     | ?      | ?     | |

---

## NEXT IMMEDIATE ACTION

**Start with Phase 1: Fix the 3 RUNTIME_ERROR handlers**

These are actual code bugs that cause 500 errors. Fixing them is highest priority because:
1. They indicate real bugs in production
2. They're blocking other tests
3. The fix is straightforward (column name corrections)
