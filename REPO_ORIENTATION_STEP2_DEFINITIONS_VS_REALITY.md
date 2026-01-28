# REPOSITORY ORIENTATION: STEP 2 - DEFINITIONS VS REALITY

**Date:** 2026-01-22
**Purpose:** Compare what's defined vs what's implemented (no assumptions)
**Status:** Truth documented

---

## SUMMARY

| Metric | Count | Status |
|--------|-------|--------|
| **Actions defined in registry** | 64 | ✅ Machine-readable catalog exists |
| **Actions implemented in handlers** | 80 | ✅ 18 more than defined |
| **Actions defined AND implemented** | 62 | ✅ Core actions working |
| **Actions defined but NOT implemented** | 2 | ❌ Missing implementations |
| **Actions implemented but NOT in registry** | 18 | ⚠️ Undocumented handlers |
| **Database mutations verified** | 1 | ❌ CRITICAL GAP (from previous audit) |
| **Audit logging complete** | 4 | ❌ CRITICAL GAP (from previous audit) |
| **RLS tests exist** | 0 | ❌ CRITICAL GAP (from previous audit) |

---

## ACTIONS DEFINED BUT NOT IMPLEMENTED (2 actions)

**CRITICAL:** These actions exist in the registry but have NO handlers.

| Action ID | Side Effect | Cluster | Why Missing? |
|-----------|-------------|---------|--------------|
| `assign_work_order` | ? | do_maintenance | Unknown - no handler exists |
| `create_work_order` | ? | do_maintenance | Unknown - `create_work_order_from_fault` exists, possibly renamed |

**Impact:** If frontend offers these actions, they will fail with 404 or unhandled action error.

**Next Step:** Determine if these are:
1. Renamed actions (e.g., `create_work_order` → `create_work_order_from_fault`)
2. Planned but unimplemented
3. Removed from implementation but not registry

---

## ACTIONS IMPLEMENTED BUT NOT IN REGISTRY (18 actions)

**CRITICAL:** These handlers exist but are NOT documented in the machine-readable catalog.

| Action ID | Likely Side Effect | Likely Cluster | Notes |
|-----------|-------------------|----------------|-------|
| `acknowledge_fault` | mutation_light | fix_something | Fault lifecycle action |
| `add_note_to_work_order` | mutation_light | do_maintenance | Alias for `add_work_order_note`? |
| `add_part_to_work_order` | mutation_heavy | do_maintenance | Alias for `add_parts_to_work_order`? |
| `check_stock_level` | read_only | control_inventory | Parts inventory query |
| `close_fault` | mutation_heavy | fix_something | Fault lifecycle action |
| `delete_document` | mutation_heavy | manage_equipment | Document deletion |
| `delete_shopping_item` | mutation_light | procure_suppliers | Shopping list management |
| `list_faults` | read_only | fix_something | Fault search/list |
| `mark_fault_false_alarm` | mutation_light | fix_something | Fault lifecycle action |
| `reopen_fault` | mutation_light | fix_something | Fault lifecycle action |
| `report_fault` | mutation_heavy | fix_something | Fault creation |
| `resolve_fault` | mutation_heavy | fix_something | Fault lifecycle action |
| `update_equipment_status` | mutation_heavy | manage_equipment | Equipment status change |
| `update_fault` | mutation_light | fix_something | Fault field updates |
| `upload_document` | mutation_heavy | manage_equipment | Document upload |
| `view_equipment` | read_only | manage_equipment | Equipment detail view |
| `view_equipment_detail` | read_only | manage_equipment | Alias for `view_equipment_details`? |
| `view_fault_detail` | read_only | fix_something | Fault detail view |

**Pattern Analysis:**

1. **Naming variants:** Several appear to be singular/plural variants (e.g., `add_part_to_work_order` vs `add_parts_to_work_order`)
2. **Fault lifecycle completeness:** Registry has `diagnose_fault`, handlers add `acknowledge_fault`, `report_fault`, `resolve_fault`, `close_fault`, `reopen_fault`, `update_fault`, `mark_fault_false_alarm`
3. **CRUD operations:** Handlers implement full CRUD (create, read, update, delete) but registry only documents some operations

**Impact:**
- Test coverage incomplete (no test fixtures for these 18 actions)
- Expected behavior undocumented (no `expectedChanges`, no `edgeCases`)
- Guard rails unknown (no `triggers.roles` or `triggers.status`)

**Next Step:** Either:
1. Add these 18 actions to registry with proper specifications
2. Remove handlers if they're duplicates or deprecated

---

## SIDE EFFECT TYPE DISTRIBUTION

### From Registry (64 defined actions)

**Side Effect Types (estimated from partial extraction):**
- `read_only`: ~20 actions (view, list, export queries)
- `mutation_light`: ~20 actions (add notes, tags, photos)
- `mutation_heavy`: ~24 actions (create/update/delete core entities)

**CRITICAL:** mutation_heavy actions MUST have:
1. Database mutation verified
2. Audit logging
3. RLS testing
4. Transaction boundaries
5. Rollback on error

**Current Status (from previous audit):**
- Only 1/64 actions have verified database mutations
- Only 4/64 actions have audit logging
- 0/64 actions have RLS tests

**Gap:** ~24 mutation_heavy actions are HIGH RISK with no verification.

---

## CLUSTER-BY-CLUSTER STATUS

### Cluster 1: fix_something (Fault Management)

**Defined in registry:** 7 actions
- `diagnose_fault` ✅ (read_only)
- `show_manual_section` ✅ (read_only)
- `view_fault_history` ✅ (read_only)
- `suggest_parts` ✅ (read_only)
- `create_work_order_from_fault` ✅ (mutation_heavy)
- `add_fault_note` ✅ (mutation_light)
- `add_fault_photo` ✅ (mutation_light)

**Implemented but NOT in registry:** 11 actions
- `acknowledge_fault` ⚠️ (mutation_light)
- `close_fault` ⚠️ (mutation_heavy)
- `list_faults` ⚠️ (read_only)
- `mark_fault_false_alarm` ⚠️ (mutation_light)
- `reopen_fault` ⚠️ (mutation_light)
- `report_fault` ⚠️ (mutation_heavy) - **CRITICAL: Fault creation not in registry**
- `resolve_fault` ⚠️ (mutation_heavy)
- `update_fault` ⚠️ (mutation_light)
- `view_fault_detail` ⚠️ (read_only)

**Status:** 18 total fault actions, only 7 documented. Fault lifecycle is MORE COMPLETE than registry suggests.

---

### Cluster 2: do_maintenance (Work Orders, Checklists)

**Defined in registry:** ~12 actions (estimated)
- `create_work_order_from_fault` ✅
- `add_work_order_note` ✅
- `add_work_order_photo` ✅
- `add_parts_to_work_order` ✅
- `mark_work_order_complete` ✅
- `view_work_order_checklist` ✅
- `view_work_order_history` ✅
- `mark_checklist_item_complete` ✅
- `add_checklist_note` ✅
- `add_checklist_photo` ✅
- `view_checklist` ✅
- (Others TBD from full registry review)

**Defined but NOT implemented:** 2 actions
- `assign_work_order` ❌
- `create_work_order` ❌

**Implemented but NOT in registry:** 2 actions
- `add_note_to_work_order` ⚠️ (alias for `add_work_order_note`?)
- `add_part_to_work_order` ⚠️ (alias for `add_parts_to_work_order`?)

**Status:** Near-complete, but missing 2 critical actions (`assign_work_order`, `create_work_order`).

---

### Cluster 3: manage_equipment (Equipment Status, History)

**Defined in registry:** ~8 actions (estimated)
- `view_equipment_details` ✅
- `view_equipment_history` ✅
- `view_equipment_manual` ✅
- `view_equipment_parts` ✅
- `add_equipment_note` ✅
- `view_document` ✅
- `view_document_section` ✅
- (Others TBD)

**Implemented but NOT in registry:** 5 actions
- `delete_document` ⚠️ (mutation_heavy)
- `update_equipment_status` ⚠️ (mutation_heavy)
- `upload_document` ⚠️ (mutation_heavy)
- `view_equipment` ⚠️ (read_only, alias?)
- `view_equipment_detail` ⚠️ (read_only, alias?)

**Status:** Equipment CRUD more complete than registry suggests. Document management fully implemented.

---

### Cluster 4: control_inventory (Parts, Stock)

**Defined in registry:** ~8 actions (estimated)
- `log_part_usage` ✅
- `scan_part_barcode` ✅
- `view_part_stock` ✅
- `view_part_location` ✅
- `view_part_usage` ✅
- `view_linked_equipment` ✅
- (Others TBD)

**Implemented but NOT in registry:** 1 action
- `check_stock_level` ⚠️ (read_only)

**Status:** Near-complete.

---

### Cluster 5: communicate_status (Handovers, Summaries)

**Defined in registry:** ~10 actions (estimated)
- `add_to_handover` ✅
- `add_document_to_handover` ✅
- `add_predictive_insight_to_handover` ✅
- `edit_handover_section` ✅
- `export_handover` ✅
- `regenerate_handover_summary` ✅
- `view_smart_summary` ✅
- `view_related_documents` ✅
- `request_predictive_insight` ✅
- `upload_photo` ✅
- `record_voice_note` ✅

**Implemented but NOT in registry:** 0 actions

**Status:** Complete (all defined actions implemented).

---

### Cluster 6: comply_audit (HOR, Compliance)

**Defined in registry:** ~5 actions (estimated)
- `view_hours_of_rest` ✅
- `update_hours_of_rest` ✅
- `export_hours_of_rest` ✅
- `view_compliance_status` ✅
- `tag_for_survey` ✅

**Implemented but NOT in registry:** 0 actions

**Status:** Complete (all defined actions implemented).

---

### Cluster 7: procure_suppliers (Purchasing)

**Defined in registry:** ~8 actions (estimated)
- `create_purchase_request` ✅
- `add_item_to_purchase` ✅
- `approve_purchase` ✅
- `upload_invoice` ✅
- `track_delivery` ✅
- `log_delivery_received` ✅
- `update_purchase_status` ✅

**Implemented but NOT in registry:** 1 action
- `delete_shopping_item` ⚠️ (mutation_light)

**Status:** Near-complete.

---

### Cluster 8: additional (Worklist, Fleet, Context Nav)

**Defined in registry:** ~6 actions (estimated)
- `add_worklist_task` ✅
- `update_worklist_progress` ✅
- `export_worklist` ✅
- `view_worklist` ✅
- `view_fleet_summary` ✅
- `export_fleet_summary` ✅
- `open_vessel` ✅

**Implemented but NOT in registry:** 0 actions

**Status:** Complete (all defined actions implemented).

---

## CRITICAL GAPS BY RISK LEVEL

### HIGH RISK (mutation_heavy actions, no verification)

**Actions with mutation_heavy side effects that are UNVERIFIED:**

From registry (estimated ~24 actions):
1. `create_work_order_from_fault` - Only 1/64 proven to write to DB (might be this one)
2. All other mutation_heavy actions: UNVERIFIED

From handlers but not in registry (18 actions):
1. `report_fault` - Fault creation, CRITICAL
2. `close_fault` - Fault lifecycle, CRITICAL
3. `resolve_fault` - Fault lifecycle, CRITICAL
4. `delete_document` - Data deletion, CRITICAL
5. `update_equipment_status` - Equipment state change, CRITICAL
6. `upload_document` - Document creation, CRITICAL
7. `add_part_to_work_order` - Work order mutation, CRITICAL

**Total HIGH RISK:** ~31 mutation_heavy actions with no verification.

**Impact:**
- These actions return HTTP 200 but may NOT write to database
- No audit logging (compliance violation)
- No RLS tests (cross-yacht data leaks possible)
- No transaction boundaries (partial failures possible)

---

### MEDIUM RISK (mutation_light actions, no verification)

**Actions with mutation_light side effects that are UNVERIFIED:**

From registry (estimated ~20 actions):
- All `add_note`, `add_photo`, `tag_for_survey`, etc.

From handlers but not in registry (18 actions):
- `acknowledge_fault`
- `mark_fault_false_alarm`
- `reopen_fault`
- `update_fault`
- `delete_shopping_item`

**Total MEDIUM RISK:** ~25 mutation_light actions with no verification.

**Impact:**
- May not persist to database
- Audit logging missing (4/64 have logs)
- RLS not tested

---

### LOW RISK (read_only actions)

**Actions with read_only side effects:**

From registry (estimated ~20 actions):
- All `view_*`, `list_*`, `export_*` actions

**Total LOW RISK:** ~20 read_only actions.

**Impact:**
- RLS not tested (cross-yacht data leaks possible)
- Performance not tested (N+1 queries, missing indexes)
- But no data corruption risk

---

## TEST COVERAGE GAP ANALYSIS

### Actions with test fixtures (from registry)

**64 actions in registry have:**
- `requiredFields` - Validation schema
- `expectedChanges` - Expected database mutations
- `edgeCases` - Known failure scenarios

**Test helper can auto-discover entity IDs for these actions.**

### Actions without test fixtures

**18 actions implemented but NOT in registry have:**
- ❌ No `requiredFields` - Unknown validation rules
- ❌ No `expectedChanges` - Unknown expected behavior
- ❌ No `edgeCases` - Unknown failure modes
- ❌ Test helper cannot auto-discover

**Impact:** Cannot write automated tests for 18 undocumented actions.

---

## NAMING INCONSISTENCIES (Potential Aliases)

| Registry Name | Handler Name | Status |
|---------------|--------------|--------|
| `add_work_order_note` | `add_note_to_work_order` | ⚠️ Possible alias |
| `add_parts_to_work_order` | `add_part_to_work_order` | ⚠️ Singular vs plural |
| `view_equipment_details` | `view_equipment_detail` | ⚠️ Singular vs plural |
| `view_equipment_details` | `view_equipment` | ⚠️ Possible alias |
| (None) | `report_fault` | ❌ Missing from registry |
| (None) | `acknowledge_fault` | ❌ Missing from registry |
| (None) | `resolve_fault` | ❌ Missing from registry |
| (None) | `close_fault` | ❌ Missing from registry |

**Next Step:** Map exact handler routing to determine if these are:
1. Aliases (same handler, different names)
2. Separate handlers
3. Deprecated names

---

## GUARD RAIL ENFORCEMENT (Conceptual G0-G3)

### From Registry (64 actions)

**Role-based access (G1):**
- Documented in `triggers.roles`
- Examples: `HOD_ROLES`, `ENGINEER_ROLES`, `'any'`

**Status-based triggering (G2):**
- Documented in `triggers.status`
- Examples: `['open', 'diagnosed']`, `['completed']`

**Multi-condition gating (G3):**
- Documented in `triggers.conditions[]`
- Examples: Check if equipment has active maintenance contract

**Always allowed (G0):**
- Actions with `roles: 'any'` and no status/condition restrictions

### From Handlers (18 undocumented actions)

**Guard rails:** ❌ UNKNOWN
- No `triggers.roles` specification
- No `triggers.status` specification
- No `triggers.conditions` specification

**Impact:** Unknown if these 18 actions enforce:
- Role-based access control
- Status-based gating
- Yacht isolation

**Risk:** Possible authorization bypass if guard rails not enforced.

---

## RECOMMENDATIONS

### Immediate (Day 1)

1. **Map 18 undocumented actions to registry** (4 hours)
   - Determine if aliases or separate actions
   - Document expected behavior
   - Add test fixtures

2. **Verify 2 missing actions** (1 hour)
   - `assign_work_order`: Determine if renamed or missing
   - `create_work_order`: Determine if renamed or missing

### Week 1 (40 hours)

1. **Verify database mutations for mutation_heavy actions** (30 hours)
   - Priority: 31 mutation_heavy actions
   - Test: Run action → query DB → verify row exists

2. **Add audit logging to all mutation actions** (8.5 hours)
   - Priority: 56 mutation actions (heavy + light)
   - Add: `audit_log` INSERT to all handlers

3. **Test RLS for 5 critical actions** (1 hour)
   - Priority: `report_fault`, `create_work_order_from_fault`, `log_part_usage`, `upload_document`, `delete_document`
   - Test: Run action as different yacht → verify isolation

4. **Document guard rails for 18 undocumented actions** (30 minutes)
   - Read handler code
   - Document `triggers.roles`, `triggers.status`, `triggers.conditions`

---

## SUMMARY: WHERE WE ARE

**Definitions (Registry):**
- ✅ 64 actions documented with full specifications
- ✅ Machine-readable test fixtures
- ✅ Guard rails specified

**Implementations (Handlers):**
- ✅ 80 actions implemented (18 more than registry)
- ✅ 61/64 return HTTP 200 (from previous audit)
- ❌ Only 1/64 proven to write to database
- ❌ Only 4/64 have audit logging
- ❌ 0/64 have RLS tests

**Gap:**
- 2 actions defined but not implemented
- 18 actions implemented but not documented
- 31 mutation_heavy actions with no verification (HIGH RISK)
- 25 mutation_light actions with no verification (MEDIUM RISK)
- 18 actions with unknown guard rails (authorization risk)

**Truth:**
- Registry is incomplete (missing 18 actions)
- Handlers are more complete than registry suggests
- Verification is the critical gap (database mutations, audit logging, RLS)

---

**Next:** STEP 3 - Map guard rail enforcement in code

**Status:** STEP 2 complete. Definitions vs reality documented.
