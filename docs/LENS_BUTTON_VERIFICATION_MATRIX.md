# LENS BUTTON VERIFICATION MATRIX

**Last Updated:** 2026-02-26 (Agent Verification Pass)
**Status:** CRITICAL GAPS IDENTIFIED - See Implementation Status Below
**Yacht ID (Test):** 85fe1119-b04c-41ac-80f1-829d23322598
**Tenant DB:** https://vzsohavtuotocgrfkfyd.supabase.co

---

## Test Users

| Role | Email | Password |
|------|-------|----------|
| Captain/HoD | x@alex-short.com | Password2! |
| HoD Test | hod.test@alex-short.com | Password2! |
| Crew | crew.test@alex-short.com | Password2! |

---

## WORK ORDERS LENS

**Route:** `/work-orders`
**Entity Type:** `pms_work_orders`
**Playwright Spec:** `tests/e2e/fragmented-routes/work-orders.spec.ts`

### Known-Good IDs

| ID | wo_number | Title | Status |
|----|-----------|-------|--------|
| `2531d846-5753-4faa-a549-20a6dc2ade73` | - | Main Engine Starboard oil change | completed |
| `30ec33c7-48f4-4047-b32d-eacd602e74d6` | WO-TEST-68DB4A | Main Engine fuel injector replacement | planned |
| `b36238da-b0fa-4815-883c-0be61fc190d0` | - | Main Engine Port 500-hour service | in_progress |

### Buttons & Actions

| Button | action_name | Roles | Test Status |
|--------|-------------|-------|-------------|
| Update Status | `update_work_order_status` | assigned_to or HOD | PENDING |
| Assign to Crew | `assign_work_order` | HOD | PENDING |
| Add Progress Note | `add_work_order_note` | assigned_to or HOD | PENDING |
| Link Equipment | `link_equipment_to_wo` | HOD | PENDING |
| Complete Work Order | `complete_work_order` | assigned_to or HOD | PENDING |
| Close/Cancel | `close_work_order` | HOD | PENDING |

---

## FAULTS LENS

**Route:** `/faults`
**Entity Type:** `pms_faults`
**Playwright Spec:** `tests/e2e/fragmented-routes/faults.spec.ts`

### Known-Good IDs

| ID | Title | Status | Severity |
|----|-------|--------|----------|
| `e9f058f8-4814-4228-aba4-7e66f9cb3430` | Test fault report | open | medium |
| `77b3ac41-ab1c-4b69-8dfc-26e392251e54` | Test fault report | open | medium |
| `bc6cc3aa-4087-4145-88f6-5bf5315e764b` | Debug test | open | medium |

### Buttons & Actions

| Button | action_name | Roles | Test Status |
|--------|-------------|-------|-------------|
| Update Severity | `update_fault_severity` | chief_engineer, captain, manager | PENDING |
| Assign Fault | `assign_fault` | chief_engineer, captain, manager | PENDING |
| Add Fault Note | `add_fault_note` | all crew | PENDING |
| Link to Work Order | `link_fault_to_work_order` | chief_engineer, captain, manager | PENDING |
| Resolve Fault | `resolve_fault` | assigned_to or HOD | PENDING |
| Reopen Fault | `reopen_fault` | chief_engineer, captain, manager | PENDING |

---

## EQUIPMENT LENS

**Route:** `/equipment`
**Entity Type:** `pms_equipment`
**Playwright Spec:** `tests/e2e/fragmented-routes/equipment.spec.ts`

### Known-Good IDs

| ID | Name | Status |
|----|------|--------|
| `b2a9c2dd-645a-44f4-9a74-b4d2e149ca8c` | Watermaker 1 | operational |
| `8e91e289-a156-444c-b315-88c0a06c9492` | STATUS-TEST-maintenance-c0b2 | maintenance |
| `04c518e6-c61f-42fe-a7b2-4cd69a0505ce` | STATUS-TEST-operational-4525 | operational |

### Buttons & Actions

| Button | action_name | Roles | Test Status |
|--------|-------------|-------|-------------|
| Update Status | `update_equipment_status` | engineer+ | PENDING |
| Add Note | `add_equipment_note` | all crew | PENDING |
| Attach Photo/Document | `attach_file_to_equipment` | all crew | PENDING |
| Create Work Order | `create_work_order_for_equipment` | engineer+ | PENDING |
| Link Part | `link_part_to_equipment` | engineer+ | PENDING |
| Flag Attention | `flag_equipment_attention` | engineer+ | PENDING |
| Decommission | `decommission_equipment` | captain, manager (SIGNED) | PENDING |

---

## INVENTORY LENS (Parts)

**Route:** `/inventory`
**Entity Type:** `pms_parts`
**Playwright Spec:** `tests/e2e/fragmented-routes/inventory.spec.ts`

### Known-Good IDs

| ID | Part Number | Name | Qty |
|----|-------------|------|-----|
| `f7913ad1-6832-4169-b816-4538c8b7a417` | FLT-0033-146 | Fuel Filter Generator | 5 |
| `2f452e3b-bf3e-464e-82d5-7d0bc849e6c0` | PMP-0018-280 | Raw Water Pump Seal Kit | 4 |
| `c7ac473c-cf02-4241-b901-42d322fc6920` | ELC-0053-760 | Navigation Light Bulb 12V 25W | 5 |

### Buttons & Actions

| Button | action_name | Roles | Test Status |
|--------|-------------|-------|-------------|
| Use Part for Work Order | `record_part_consumption` | deckhand, bosun, eto, chief_engineer, captain, manager | PENDING |
| Adjust Stock Count | `adjust_stock_quantity` | captain, manager (SIGNED if large) | PENDING |
| Add to Shopping List | `add_to_shopping_list` | most crew | PENDING |
| Transfer Between Locations | `transfer_parts` | bosun, eto, chief_engineer, captain, manager | PENDING |
| Write Off Part | `write_off_part` | captain, manager (SIGNED) | PENDING |

---

## RECEIVING LENS

**Route:** `/receiving`
**Entity Type:** `pms_receiving_events`
**Playwright Spec:** `tests/e2e/fragmented-routes/receiving.spec.ts`

### Known-Good IDs

| ID | Receiving Number | Status |
|----|------------------|--------|
| `bc096e3c-a5a6-4299-ba6d-7fa69b71726f` | RCV-2026-001 | completed |
| `64c321c9-01e5-4648-b0c1-b1f29afea714` | RCV-2026-002 | completed |
| `05c0aade-451b-4038-a4ac-2cc045461aef` | RCV-2026-003 | completed |

### Buttons & Actions

| Button | action_name | Roles | Test Status |
|--------|-------------|-------|-------------|
| Start Receiving Event | `start_receiving_event` | all crew | PENDING |
| Add Line Item | `add_line_item` | receiver or HOD | PENDING |
| Complete Receiving | `complete_receiving_event` | receiver or HOD | PENDING |
| Report Discrepancy | `report_discrepancy` | all crew | PENDING |
| Verify Line Item | `verify_line_item` | HOD only | PENDING |

---

## SHOPPING LIST LENS

**Route:** `/shopping-list`
**Entity Type:** `pms_shopping_list_items`
**Playwright Spec:** `tests/e2e/fragmented-routes/shopping-list.spec.ts`

### Known-Good IDs

| ID | Part Name | Status |
|----|-----------|--------|
| `693eae41-0873-4de5-85e9-f5c659d47863` | HOD Test Part 1769620245 | approved |
| `b9067c7b-2661-4d3b-9fb8-eada598d68c6` | Test Part 1770666500560 | candidate |
| `14f5c09a-77e3-437b-b271-044db9d95421` | Reject Test 1770666545118 | candidate |

### Buttons & Actions

| Button | action_name | Roles | Test Status |
|--------|-------------|-------|-------------|
| Create Item | `create_shopping_list_item` | all crew | PENDING |
| Approve Item | `approve_shopping_list_item` | HOD | PENDING |
| Reject Item | `reject_shopping_list_item` | HOD | PENDING |
| Promote to Part | `promote_candidate_to_part` | engineers | PENDING |

---

## CERTIFICATES LENS

**Route:** `/certificates`
**Entity Type:** `pms_vessel_certificates`
**Playwright Spec:** `tests/e2e/fragmented-routes/certificates.spec.ts`

### Known-Good IDs

| ID | Certificate Name | Status |
|----|------------------|--------|
| `ea34bee1-0a8b-41dd-a9fa-2d270bb0beea` | Lloyds Register Class (Renewed) | valid |
| `fdd53619-89c6-46b1-8e9f-4211e3c16fae` | SOLAS Safety Certificate | valid |
| `31ee8205-8838-4c8e-ad7d-b404663110c7` | Lloyds Register Class | superseded |

### Buttons & Actions

| Button | action_name | Roles | Test Status |
|--------|-------------|-------|-------------|
| Create Vessel Certificate | `create_vessel_certificate` | HOD, manager | PENDING |
| Update Certificate | `update_certificate` | HOD, manager | PENDING |
| Supersede Certificate | `supersede_certificate` | captain, manager (SIGNED) | PENDING |
| Link Document | `link_document_to_certificate` | HOD, manager | PENDING |

---

## DOCUMENTS LENS

**Route:** `/documents`
**Entity Type:** `doc_metadata`
**Playwright Spec:** `tests/e2e/fragmented-routes/documents.spec.ts`

### Known-Good IDs

| ID | Filename | Doc Type |
|----|----------|----------|
| `aaa37821-f794-4eeb-a6bf-90ced563422f` | Link_Error_linkerr-1772054606608-mz92yj.pdf | - |
| `5633f722-c425-4abd-85c9-0bb9af7fa541` | staging-doc-1769699777.pdf | - |
| `a39b99e4-eb07-49af-b0fb-e72e1b6a8918` | read-test-1769746885.pdf | - |

### Buttons & Actions

| Button | action_name | Roles | Test Status |
|--------|-------------|-------|-------------|
| Upload Document | `upload_document` | all crew | PENDING |
| Update Document | `update_document` | HOD | PENDING |
| Add Tags | `add_document_tags` | HOD | PENDING |
| Link to Equipment | `link_document_to_equipment` | HOD | PENDING |
| Delete Document | `delete_document` | captain, manager (SIGNED) | PENDING |
| Get Document URL | `get_document_url` | all crew | PENDING |

---

## SECURITY TESTS (ALL LENSES)

| Test | Status |
|------|--------|
| Cross-yacht isolation (Yacht A user cannot see Yacht B data) | PENDING |
| Role restriction (Junior cannot perform HOD actions) | PENDING |
| Signed action requires signature payload | PENDING |

---

## PROGRESS TRACKER (Agent-Verified 2026-02-26)

| Lens | Spec Actions | Implemented | Missing | Blockers | Status |
|------|--------------|-------------|---------|----------|--------|
| work-orders | 6 | 6 | 0 | B1-B5 (RLS, signatures) | ⚠️ PARTIAL |
| faults | 10 | 2 | 8 | B1-B7 (RLS, UI gaps) | ❌ CRITICAL GAP |
| equipment | 7 | 0 | 7 | B1-B11 (no spec actions) | ❌ CRITICAL GAP |
| inventory | 9 | 6 | 3 | B1-B4 (RLS, hardcoded) | ⚠️ PARTIAL |
| receiving | 6 | 5 | 1 | None | ✅ SHIPPABLE |
| shopping-list | 6 | 3 | 3 | B1-B6 (role visibility) | ⚠️ PARTIAL |
| certificates | 4 | 0 | 4 | Not verified | ❌ NOT VERIFIED |
| documents | 6 | 0 | 6 | Not verified | ❌ NOT VERIFIED |

---

## DETAILED FINDINGS BY LENS

### Work Orders (⚠️ PARTIAL)
**Agent ID:** ae06a44

**Implemented Actions (6/6):**
- ✅ Start Work Order
- ✅ Update/Edit Work Order
- ✅ Complete Work Order (Mark Complete)
- ✅ Add Note (in NotesSection)
- ⚠️ Reassign Work Order (NO signature capture)
- ⚠️ Archive Work Order (NO signature capture)

**Critical Blockers:**
- B1: `pms_work_order_notes` RLS `USING (true)` - cross-yacht data leakage
- B2: `pms_work_order_parts` RLS `USING (true)` - cross-yacht data leakage
- B3: `pms_part_usage` RLS `USING (true)` - cross-yacht data leakage
- B4: `cascade_wo_status_to_fault()` trigger NOT deployed
- B5: Signature hooks not wired for Reassign/Archive (spec requires SIGNED)

### Faults (❌ CRITICAL GAP)
**Agent ID:** a0468d8

**Implemented Actions (2/10):**
- ✅ View fault detail (read-only)
- ⚠️ Create Work Order from Fault (partial - no signature flow)

**Missing Actions (8/10):**
- ❌ Report Fault (no UI)
- ❌ Acknowledge Fault (no hook)
- ❌ Update Fault (no hook)
- ❌ Close Fault (no hook)
- ❌ Reopen Fault (no hook)
- ❌ Mark False Alarm (no hook)
- ❌ Add Fault Note (no hook)
- ❌ Add Fault Photo (no hook)

**Critical Blockers:**
- B1: `pms_faults` RLS missing INSERT/UPDATE/DELETE policies
- B2: `pms_notes` RLS missing INSERT/UPDATE policies
- B3: Storage bucket `pms-discrepancy-photos` missing write policies
- B4-B7: No action hooks exist for 8 actions

### Equipment (❌ CRITICAL GAP)
**Agent ID:** a80a1ab

**Implemented Actions (0/7):** NONE SPEC-COMPLIANT

UI implements 3 buttons but NONE match spec action names:
- "Report Fault" → calls `report_fault` (NOT in spec)
- "Create Work Order" → uses actionClient (not spec endpoint)
- "Schedule Maintenance" → placeholder toast only

**Missing Spec Actions (7/7):**
- ❌ update_equipment_status
- ❌ add_equipment_note
- ❌ attach_file_to_equipment
- ❌ create_work_order_for_equipment
- ❌ link_part_to_equipment
- ❌ flag_equipment_attention
- ❌ decommission_equipment (SIGNED)

### Inventory (⚠️ PARTIAL)
**Agent ID:** abe3790

**Implemented Actions (6/9):**
- ✅ record_part_consumption (Use Part)
- ✅ receive_parts (Receive Stock)
- ✅ transfer_parts (Transfer)
- ⚠️ adjust_stock_quantity (no signature UI)
- ⚠️ write_off_part (no signature UI)
- ✅ add_to_shopping_list

**Missing Actions (3/9):**
- ❌ create_part (no UI button)
- ❌ view_part_history (no UI)
- ❌ view_compatible_equipment (no UI)

**Critical Issues:**
- B1: `pms_inventory_transactions` RLS DISABLED
- Hardcoded values: quantity=1, location='default', reason='Write off'

### Receiving (✅ SHIPPABLE)
**Agent ID:** a1e307e

**Implemented Actions (5/6):**
- ✅ start_receiving_event
- ✅ add_line_item
- ✅ complete_receiving_event
- ✅ report_discrepancy
- ✅ verify_line_item (HoD only - properly gated)

**Missing (1/6):**
- view_receiving_photos (read-only, not critical)

**NO BLOCKERS** - Ready for E2E testing

### Shopping List (⚠️ PARTIAL)
**Agent ID:** a5afc6a

**Implemented Actions (3/6):**
- ✅ approve_shopping_list_item (HOD)
- ✅ reject_shopping_list_item (HOD)
- ✅ promote_candidate_to_part (Engineers)

**Missing Actions (3/6):**
- ❌ create_shopping_list_item (no UI)
- ❌ view_item_history (no UI)
- ❌ link_to_work_order (no navigation)

**Issues:**
- B4: Role-based visibility not enforced - buttons shown by status, not user role
- B5: Missing role permission checks in handlers

---

## FIX LIST (Agent-Generated)

| Issue | Lens | Severity | Description | Fix Status |
|-------|------|----------|-------------|------------|
| B1 | work-orders | CRITICAL | RLS `USING (true)` on 3 tables - cross-yacht leakage | BLOCKED |
| B5 | work-orders | HIGH | No signature capture for Reassign/Archive | NEEDS FIX |
| B1-B3 | faults | CRITICAL | RLS missing mutation policies | BLOCKED |
| B4-B7 | faults | CRITICAL | No action hooks for 8 actions | NEEDS DEV |
| B1-B11 | equipment | CRITICAL | 0/7 spec actions implemented | NEEDS DEV |
| B1 | inventory | CRITICAL | Transactions RLS DISABLED | BLOCKED |
| B4 | shopping-list | MEDIUM | Role visibility mismatch | NEEDS FIX |

---

## BUTTON TESTER AGENT RESULTS (2026-02-26)

### Receiving ✅ READY FOR E2E
**Agent ID:** af2fa3f
- **5/5 buttons PASS**
- All action names correct
- Role gates via ACTION_REGISTRY
- HoD-only button (Verify Line Item) correctly conditional
- Feature flag guard in place

### Shopping List ❌ NOT READY FOR E2E
**Agent ID:** a95ff71
- **3/3 implemented, 3/3 missing**
- CRITICAL: Role-based button visibility NOT implemented
- Buttons shown by status, not user role (isHOD() unused)
- Backend will reject but poor UX
- Missing: Create Item, View History, Link to WO

### Inventory ❌ NOT READY FOR E2E
**Agent ID:** a94357c
- **6/6 buttons wired, but 2 action name mismatches**
- CRITICAL: `adjust_stock` should be `adjust_stock_quantity` (line 157)
- CRITICAL: `add_part_to_shopping_list` should be `create_shopping_list_item` (line 171)
- CRITICAL: No signature UI for adjust_stock_quantity/write_off_part
- ALL VALUES HARDCODED: quantity=1, location='default'

### Work Orders ⚠️ PARTIAL
**Agent ID:** a212120
- **4/6 buttons PASS, 2/6 FAIL**
- ✅ Start Work Order, Mark Complete, Edit, Log Hours
- ❌ Reassign: No signature capture (uses assign_work_order not reassign_work_order)
- ❌ Archive: Passes empty signature {} instead of capturing
- Hooks support signatures but modals don't collect them

---

## FIX LIST (Agent-Generated)

| Issue | Lens | Severity | Description | Fix Status |
|-------|------|----------|-------------|------------|
| B1 | work-orders | CRITICAL | RLS `USING (true)` on 3 tables - cross-yacht leakage | BLOCKED |
| B5 | work-orders | HIGH | No signature capture for Reassign/Archive | NEEDS FIX |
| SIG-1 | work-orders | HIGH | ReassignModal uses assign_work_order not reassign_work_order | NEEDS FIX |
| SIG-2 | work-orders | HIGH | ArchiveModal passes {} signature | NEEDS FIX |
| B1-B3 | faults | CRITICAL | RLS missing mutation policies | BLOCKED |
| B4-B7 | faults | CRITICAL | No action hooks for 8 actions | NEEDS DEV |
| B1-B11 | equipment | CRITICAL | 0/7 spec actions implemented | NEEDS DEV |
| B1 | inventory | CRITICAL | Transactions RLS DISABLED | BLOCKED |
| ACT-1 | inventory | CRITICAL | Action name: adjust_stock → adjust_stock_quantity | NEEDS FIX |
| ACT-2 | inventory | CRITICAL | Action name: add_part_to_shopping_list → create_shopping_list_item | NEEDS FIX |
| SIG-3 | inventory | HIGH | No signature UI for adjust_stock_quantity | NEEDS FIX |
| SIG-4 | inventory | HIGH | No signature UI for write_off_part | NEEDS FIX |
| HARD-1 | inventory | MEDIUM | All quantities hardcoded to 1 | NEEDS FIX |
| B4 | shopping-list | MEDIUM | Role visibility mismatch - buttons show to all | NEEDS FIX |

---

## RECOMMENDED TEST PRIORITY

1. **Receiving** - ✅ READY NOW - test all 5 buttons
2. **Work Orders** - ⚠️ Test 4 buttons (skip Reassign/Archive until fixed)
3. **Shopping List** - ⚠️ Test with HOD user only (backend enforces roles)
4. **Inventory** - ❌ Fix action names first, then test
5. **Faults** - ❌ Skip until hooks implemented
6. **Equipment** - ❌ Skip until spec actions implemented
