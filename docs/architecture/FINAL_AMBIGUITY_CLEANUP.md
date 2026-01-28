# FINAL AMBIGUITY CLEANUP

**Date:** 2026-01-22
**Purpose:** Resolve last naming/contract ambiguities before code freeze
**Status:** Canonical Decisions - Implement Exactly As Specified

---

## PURPOSE

This document resolves all remaining ambiguities identified in ACTION_RECONCILIATION.md. After this, **zero architectural questions remain**.

---

## SECTION 1: NAMING RESOLUTION (Canonical Names)

These actions have multiple names across registry/handlers/docs. **Use the canonical name everywhere.**

### 1.1 Inventory Adjustment

**Variants Found:**
- Registry: `edit_inventory_quantity`
- Handlers: (not implemented)
- Docs: `adjust_inventory`

**CANONICAL NAME:** `adjust_inventory`

**Resolution:**
- ✅ Update registry: `edit_inventory_quantity` → `adjust_inventory`
- ✅ Handler name: `adjust_inventory_execute`
- ✅ Docs already correct

**Rationale:** "Adjust" is standard inventory terminology. "Edit" is too generic.

---

### 1.2 Purchase Request Creation

**Variants Found:**
- Registry: `create_reorder`, `create_purchase_request`
- Handlers: `create_purchase_request_execute`
- Docs: `create_purchase_order`

**CANONICAL NAME:** `create_purchase_request`

**Resolution:**
- ✅ Remove registry: `create_reorder` (duplicate)
- ✅ Keep registry: `create_purchase_request`
- ✅ Update docs: `create_purchase_order` → `create_purchase_request`
- ✅ Handler already correct

**Rationale:** "Purchase Request" distinguishes from "Purchase Order". Request → Approval → Order → Delivery.

---

### 1.3 Related Documents View

**Variants Found:**
- Registry: `view_related_docs`
- Handlers: `view_related_documents_execute`
- Docs: (not documented)

**CANONICAL NAME:** `view_related_docs`

**Resolution:**
- ✅ Registry already correct
- ✅ Update handler: `view_related_documents_execute` → `view_related_docs_execute`
- ✅ Add to docs: `view_related_docs`

**Rationale:** Shorter name, consistent with other "view_X" actions.

---

### 1.4 Add Parts to Work Order

**Variants Found:**
- Registry: `add_parts_to_work_order`
- Handlers: `add_part_to_work_order_execute`
- Docs: `add_wo_part`

**CANONICAL NAME:** `add_wo_part`

**Resolution:**
- ✅ Update registry: `add_parts_to_work_order` → `add_wo_part`
- ✅ Update handler: `add_part_to_work_order_execute` → `add_wo_part_execute`
- ✅ Docs already correct

**Rationale:** Shorter, matches pattern `add_wo_note`, `add_wo_photo`, `add_wo_hours`.

---

### 1.5 Complete Work Order

**Variants Found:**
- Registry: `mark_work_order_complete`
- Handlers: `mark_work_order_complete_execute`
- Docs: `complete_work_order`

**CANONICAL NAME:** `complete_work_order`

**Resolution:**
- ✅ Update registry: `mark_work_order_complete` → `complete_work_order`
- ✅ Update handler: `mark_work_order_complete_execute` → `complete_work_order_execute`
- ✅ Docs already correct

**Rationale:** Action is "complete", not "mark as complete". Simpler verb.

---

### 1.6 Add Work Order Note

**Variants Found:**
- Registry: `add_work_order_note`
- Handlers: `add_note_to_work_order_execute`
- Docs: `add_wo_note`

**CANONICAL NAME:** `add_wo_note`

**Resolution:**
- ✅ Update registry: `add_work_order_note` → `add_wo_note`
- ✅ Update handler: `add_note_to_work_order_execute` → `add_wo_note_execute`
- ✅ Docs already correct

**Rationale:** Consistent with `add_wo_part`, `add_wo_photo`, `add_wo_hours`.

---

### 1.7 Approve Purchase

**Variants Found:**
- Registry: `approve_purchase`
- Handlers: `approve_purchase_execute`
- Docs: `approve_purchase_order`

**CANONICAL NAME:** `approve_purchase`

**Resolution:**
- ✅ Registry already correct
- ✅ Handler already correct
- ✅ Update docs: `approve_purchase_order` → `approve_purchase`

**Rationale:** Shorter, matches registry/handler naming.

---

### 1.8 View Equipment

**Variants Found:**
- Registry: `view_equipment`
- Handlers: `view_equipment`, `view_equipment_details_execute`
- Docs: `view_equipment_history`

**CANONICAL NAME:** `view_equipment`

**Resolution:**
- ✅ Registry already correct
- ✅ Handler already correct (`view_equipment`)
- ✅ Remove handler: `view_equipment_details_execute` (duplicate)
- ✅ Separate action: `view_equipment_history` (different from `view_equipment`)

**Rationale:** `view_equipment` = entity detail. `view_equipment_history` = audit log.

---

## NAMING RESOLUTION SUMMARY

| Old Name (Registry/Handler/Docs) | Canonical Name | Update Required |
|-----------------------------------|----------------|-----------------|
| edit_inventory_quantity | adjust_inventory | Registry |
| create_reorder | create_purchase_request | Registry (remove) |
| view_related_documents | view_related_docs | Handler |
| add_parts_to_work_order | add_wo_part | Registry + Handler |
| mark_work_order_complete | complete_work_order | Registry + Handler |
| add_work_order_note | add_wo_note | Registry + Handler |
| approve_purchase_order | approve_purchase | Docs |
| view_equipment_details | view_equipment | Handler (remove duplicate) |

**Action Items:**
- [ ] Update action_registry.py with canonical names
- [ ] Rename handler functions to match canonical names
- [ ] Update ACTION_IO_MATRIX.md with canonical names
- [ ] Update ENTITY_ACTION_SURFACING.md with canonical names

---

## SECTION 2: HANDLER CONTRACT GAPS

These handlers exist but lack clear contracts. Flag as incomplete until contracts defined.

### 2.1 Handlers Missing Reads/Writes Contract

**Handler:** `check_stock_level_execute`
- **Reads:** ⚠️ Not specified in ACTION_IO_MATRIX
- **Writes:** ⚠️ Not specified in ACTION_IO_MATRIX
- **Ledger:** ⚠️ Not specified
- **Audit:** ⚠️ Not specified

**Resolution:**
```
Reads: pms_parts(id, quantity_on_hand, quantity_minimum)
Writes: None (read-only)
Ledger: No
Audit: No
```

---

**Handler:** `order_part_execute`
- **Reads:** ⚠️ Not specified in ACTION_IO_MATRIX
- **Writes:** ⚠️ Not specified in ACTION_IO_MATRIX
- **Ledger:** ⚠️ Not specified
- **Audit:** ⚠️ Not specified

**Resolution:**
```
Reads: pms_parts(id, name, part_number)
Writes: shopping_list_items(+id, +part_id, +quantity_requested, +requested_by, +created_at)
Ledger: Yes - shopping_list_item_added
Audit: Yes (MUTATE action)
```

---

**Handler:** `show_manual_section_execute`
- **Reads:** ⚠️ Not specified in ACTION_IO_MATRIX
- **Writes:** ⚠️ Not specified in ACTION_IO_MATRIX
- **Ledger:** ⚠️ Not specified
- **Audit:** ⚠️ Not specified

**Resolution:**
```
Reads: pms_attachments(entity_type='document', storage_path) OR RAG search chunks
Writes: None (read-only)
Ledger: No
Audit: No
```

---

**Handler:** `view_linked_equipment_execute`
- **Reads:** ⚠️ Not specified in ACTION_IO_MATRIX
- **Writes:** ⚠️ Not specified in ACTION_IO_MATRIX
- **Ledger:** ⚠️ Not specified
- **Audit:** ⚠️ Not specified

**Resolution:**
```
Reads: pms_equipment(id, name, status), pms_parts(id, equipment_id)
Writes: None (read-only)
Ledger: No
Audit: No
```

---

**Handler:** `view_document_execute`
- **Reads:** ⚠️ Not specified in ACTION_IO_MATRIX
- **Writes:** ⚠️ Not specified in ACTION_IO_MATRIX
- **Ledger:** ⚠️ Not specified
- **Audit:** ⚠️ Not specified

**Resolution:**
```
Reads: pms_attachments(entity_type='document', storage_path) OR pms_documents (if table exists)
Writes: None (read-only)
Ledger: No
Audit: No
```

---

### 2.2 Handlers with Ambiguous Mutation Type

**Handler:** `add_to_handover_prefill` + `add_to_handover_execute`
- **Question:** Is this MUTATE_LOW or MUTATE_MEDIUM?
- **Resolution:** MUTATE_LOW (no signature required, informational action)
- **Audit:** Yes (still write audit log for accountability)

---

**Handler:** `log_part_usage_execute`
- **Question:** Is this MUTATE_MEDIUM or MUTATE_HIGH?
- **Resolution:** MUTATE_MEDIUM (physical inventory change, but reversible via restock)
- **Signature:** No (not required for MVP - crew logs usage frequently)
- **Audit:** Yes (mandatory for inventory audit trail)

---

**Handler:** `approve_purchase_execute`
- **Question:** Is this MUTATE_MEDIUM or MUTATE_HIGH?
- **Resolution:** MUTATE_MEDIUM (requires signature, commits budget, but cancellable before order placed)
- **Signature:** Yes (HOD approval required)
- **Audit:** Yes (financial accountability)

---

## SECTION 3: MISSING HANDLER REGISTRATIONS

These handlers exist in code but are NOT registered in action_registry.py. **Register them now.**

### 3.1 List Actions (4 handlers)

**Handlers:**
- `list_work_orders`
- `list_parts`
- `list_faults`
- `list_equipment`

**Action to Register:**
```python
# READ: List work orders
registry.register(Action(
    action_id="list_work_orders",
    label="List Work Orders",
    variant=ActionVariant.READ,
    domain="work_orders",
    entity_types=["work_order"],
    ui=ActionUI(primary=False, icon="list"),
    execution=ActionExecution(handler="list_work_orders"),
    description="List all work orders for yacht"
))
```

Repeat for `list_parts`, `list_faults`, `list_equipment`.

---

### 3.2 Receiving/Shopping Actions (2 handlers)

**Handlers:**
- `commit_receiving_session_execute`
- `add_to_shopping_list_execute`

**Action to Register:**
```python
# MUTATE: Add to shopping list
registry.register(Action(
    action_id="add_to_shopping_list",
    label="Add to Shopping List",
    variant=ActionVariant.MUTATE,
    domain="inventory",
    entity_types=["part", "inventory_item"],
    ui=ActionUI(dropdown_only=True, icon="shopping-cart"),
    execution=ActionExecution(handler="add_to_shopping_list"),
    mutation=ActionMutation(
        requires_signature=False,
        preview_diff=False,
        confirmation_message="Add part to shopping list"
    ),
    audit=ActionAudit(level=AuditLevel.BASIC),
    description="Add part to shopping list"
))

# MUTATE: Commit receiving session
registry.register(Action(
    action_id="commit_receiving_session",
    label="Commit Receiving",
    variant=ActionVariant.MUTATE,
    domain="purchasing",
    entity_types=["purchase", "receiving_session"],
    ui=ActionUI(dropdown_only=True, icon="check-circle"),
    execution=ActionExecution(handler="commit_receiving_session"),
    mutation=ActionMutation(
        requires_signature=True,
        preview_diff=True,
        confirmation_message="Confirm receipt and update inventory"
    ),
    audit=ActionAudit(level=AuditLevel.FULL),
    description="Commit receiving session and update inventory"
))
```

---

### 3.3 Manual/Document Actions (3 handlers)

**Handlers:**
- `show_manual_section_execute`
- `view_document_execute`
- `view_document_section_execute`

**Action to Register:**
```python
# READ: Show manual section
registry.register(Action(
    action_id="show_manual_section",
    label="Show Manual",
    variant=ActionVariant.READ,
    domain="manual",
    entity_types=["document", "manual_section", "document_chunk"],
    ui=ActionUI(primary=False, icon="book"),
    execution=ActionExecution(handler="show_manual_section"),
    description="Display manual section"
))
```

---

## SECTION 4: LAST BLOCKERS CHECKLIST

**Before code freeze, ensure:**

### Registry
- [ ] All canonical names updated in action_registry.py
- [ ] All implemented handlers registered
- [ ] No duplicate action IDs
- [ ] All MVP actions have `entity_types` specified

### Handlers
- [ ] All handler functions renamed to canonical names
- [ ] All handlers follow standard structure (permission check, state validation, transaction, audit log)
- [ ] All MUTATE handlers write to pms_audit_log
- [ ] All handlers specified in ACTION_IO_MATRIX have contracts defined

### Docs
- [ ] ACTION_IO_MATRIX.md updated with canonical names
- [ ] ENTITY_ACTION_SURFACING.md updated with canonical names
- [ ] MVP_EXECUTION_SLICE.md references only canonical names
- [ ] No orphaned action references (docs mention actions not in registry)

### Database
- [ ] P0 migrations SQL scripts written and tested
- [ ] Migration deployment order documented
- [ ] Rollback scripts prepared
- [ ] RLS policies tested on all new tables

### Frontend
- [ ] Action surfacing implementation matches GROUPING_LOCK.md
- [ ] Situation state machine implemented
- [ ] RAG suggestions rendered correctly (yellow banner, dismissible)
- [ ] Signature flow implemented (tap accept)

### Backend
- [ ] All MVP handlers implemented (47 actions)
- [ ] Permission checks enforced
- [ ] Audit log writing verified
- [ ] RLS enforced on all queries

---

## SECTION 5: FINAL CANONICAL ACTION LIST (MVP)

**These 47 actions are canonical for MVP. Build exactly these.**

### Fault (7)
1. view_fault
2. diagnose_fault
3. add_fault_note
4. add_fault_photo
5. create_work_order_from_fault
6. view_fault_history
7. add_to_handover

### Work Order (9)
8. view_work_order
9. create_work_order
10. assign_work_order
11. add_wo_note
12. add_wo_photo
13. add_wo_part
14. view_work_order_history
15. view_work_order_checklist
16. complete_work_order

### Inventory (6)
17. view_inventory_item
18. log_part_usage
19. view_part_location
20. view_part_usage
21. add_to_shopping_list
22. view_stock_levels

### Purchasing (5)
23. create_purchase_request
24. add_item_to_purchase
25. approve_purchase
26. track_delivery
27. log_delivery_received

### Equipment (5)
28. view_equipment
29. view_maintenance_history
30. view_equipment_parts
31. view_linked_faults
32. view_equipment_manual

### Handover (5)
33. add_to_handover
34. add_document_to_handover
35. edit_handover_section
36. export_handover
37. regenerate_handover_summary

### Checklist (3)
38. view_checklist
39. mark_checklist_item_complete
40. add_checklist_photo

### Document (2)
41. view_manual_section
42. view_related_docs

### Search/List (4)
43. search
44. list_work_orders
45. list_faults
46. list_parts

### Attachment (1)
47. add_photo

**Total: 47 actions**

---

## SECTION 6: IMMEDIATE ACTION ITEMS

**Engineering must do these NOW:**

### Backend Team (Priority 1)
1. ✅ Update action_registry.py with all canonical names (2 hours)
2. ✅ Rename handler functions to match canonical names (1 hour)
3. ✅ Register missing handlers (list actions, shopping, manual) (2 hours)
4. ✅ Add contracts to ACTION_IO_MATRIX for gap handlers (1 hour)
5. ✅ Write P0 migration scripts (shopping_list, po_items, PO columns) (3 hours)
6. ✅ Deploy P0 migrations to staging (1 hour)

**Estimated:** 10 hours (1-2 days)

---

### Frontend Team (Priority 1)
1. ✅ Update all action references to canonical names (1 hour)
2. ✅ Implement 4-segment action layout (8 hours)
3. ✅ Implement situation state machine (4 hours)
4. ✅ Implement RAG suggestion banners (2 hours)
5. ✅ Implement signature flow (tap accept) (3 hours)

**Estimated:** 18 hours (2-3 days)

---

### QA Team (Priority 2)
1. ✅ Test action surfacing (max 3 primary, correct grouping)
2. ✅ Test situation transitions (IDLE → CANDIDATE → ACTIVE → COMMIT → COOLDOWN)
3. ✅ Test RAG suggestions (never auto-execute)
4. ✅ Test signature flow (tap accept works)
5. ✅ Test P0 migrations (rollback if needed)

**Estimated:** 12 hours (1-2 days)

---

## SECTION 7: DEFINITION OF "ZERO AMBIGUITY"

**Architecture has zero ambiguity when:**

✅ Every action has ONE canonical name (no variants)
✅ Every action in registry has corresponding handler
✅ Every handler has corresponding registry entry
✅ Every action has defined reads/writes/ledger/audit contract
✅ Every entity type has defined action surfacing rules
✅ Every situation transition is specified
✅ Every RAG interaction is bounded (suggest/prefill only)
✅ Every schema gap has migration spec or resolution

**Status after this document:**
- Canonical names: ✅ RESOLVED (8 naming conflicts resolved)
- Handler contracts: ✅ RESOLVED (5 gaps filled)
- Missing registrations: ✅ RESOLVED (9 handlers to register)
- Ambiguous mutation types: ✅ RESOLVED (3 clarified)
- MVP action list: ✅ FINALIZED (47 actions)

**Zero architectural questions remain. Build.**

---

## APPENDIX: QUICK REFERENCE

### Canonical Name Mapping
```
edit_inventory_quantity → adjust_inventory
create_reorder → create_purchase_request (remove duplicate)
view_related_documents → view_related_docs
add_parts_to_work_order → add_wo_part
mark_work_order_complete → complete_work_order
add_work_order_note → add_wo_note
approve_purchase_order → approve_purchase
view_equipment_details → view_equipment (remove duplicate)
```

### Handler Registration Priority
```
P0 (Register Now):
- list_work_orders, list_parts, list_faults, list_equipment
- add_to_shopping_list
- commit_receiving_session
- show_manual_section
- view_document

P1 (Can Wait):
- view_document_section
- view_linked_equipment
```

### Schema Migration Priority
```
P0 (Deploy This Week):
- shopping_list_items table
- purchase_order_items table
- PO tracking columns (approved_at, received_at, etc.)

P1 (Post-MVP):
- pms_documents table
- receiving_sessions table
- fault diagnosis columns
```

---

**All ambiguity eliminated. Code freeze ready.**
