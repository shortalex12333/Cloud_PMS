# MVP EXECUTION SLICE

**Date:** 2026-01-22
**Purpose:** Definitive scope for MVP - exactly what ships first
**Status:** Build This First - No Additions Without Approval

---

## DEFINITION OF MVP

**MVP = Minimum Viable Product for yacht crew to:**
1. Report and diagnose faults
2. Create and execute work orders
3. Track parts inventory
4. Order parts (shopping list + purchase requests)
5. Hand over shift information

**NOT in MVP:**
- Complex predictive analytics
- Fleet-wide management
- Third-party integrations
- Advanced compliance reporting

---

## CANONICAL MVP ACTION LIST (47 actions)

Build these actions **exactly as specified** in ACTION_IO_MATRIX.md.

### FAULT CLUSTER (7 actions)

| Action | Handler | Schema Ready | Priority |
|--------|---------|--------------|----------|
| view_fault | ✅ Implemented | ✅ Yes | **P0** |
| diagnose_fault | ✅ Implemented | ⚠️ Use metadata | **P0** |
| add_fault_note | ✅ Implemented | ⚠️ Use metadata | **P0** |
| add_fault_photo | ✅ Implemented | ✅ Yes (attachments) | **P0** |
| create_work_order_from_fault | ✅ Implemented | ✅ Yes | **P0** |
| view_fault_history | ✅ Implemented | ✅ Yes (audit_log) | P1 |
| add_to_handover | ✅ Implemented | ✅ Yes | **P0** |

**Stubbed for MVP:**
- report_fault (handler missing - use simplified form)
- resolve_fault (low priority - Chief only)
- close_fault (low priority - archive action)
- defer_fault (low priority - rare use case)

---

### WORK ORDER CLUSTER (9 actions)

| Action | Handler | Schema Ready | Priority |
|--------|---------|--------------|----------|
| view_work_order | ✅ Implemented | ✅ Yes | **P0** |
| create_work_order | ✅ Implemented | ✅ Yes | **P0** |
| assign_work_order | ✅ Implemented | ✅ Yes | **P0** |
| add_wo_note | ✅ Implemented | ✅ Yes (wo_notes) | **P0** |
| add_wo_photo | ✅ Implemented | ✅ Yes (attachments) | **P0** |
| add_wo_part | ✅ Implemented | ✅ Yes (wo_parts) | **P0** |
| view_work_order_history | ✅ Implemented | ✅ Yes (audit_log) | P1 |
| view_work_order_checklist | ✅ Implemented | ✅ Yes | P1 |
| mark_work_order_complete | ✅ Implemented | ✅ Yes | **P0** |

**Stubbed for MVP:**
- start_work_order (use status transition only, no explicit columns)
- add_wo_hours (use metadata or stub - time tracking not critical MVP)
- remove_wo_part (low priority - rarely used)
- reopen_work_order (low priority - edge case)
- cancel_work_order (low priority - use status change)

---

### INVENTORY/PARTS CLUSTER (6 actions)

| Action | Handler | Schema Ready | Priority |
|--------|---------|--------------|----------|
| view_inventory_item | ✅ Implemented | ✅ Yes | **P0** |
| log_part_usage | ✅ Implemented | ✅ Yes (part_usage) | **P0** |
| view_part_location | ✅ Implemented | ✅ Yes | P1 |
| view_part_usage | ✅ Implemented | ✅ Yes (part_usage) | P1 |
| add_to_shopping_list | ✅ Implemented | ❌ **P0 MIGRATION** | **P0** |
| view_stock_levels | ⚠️ Partial | ✅ Yes | P1 |

**Stubbed for MVP:**
- adjust_inventory (requires signature, lower priority)
- restock_part (requires receiving session)
- remove_from_shopping_list (low priority - rare)
- flag_low_stock (system action, not user-initiated)
- scan_part_barcode (mobile feature, post-MVP)

---

### PURCHASING CLUSTER (5 actions)

| Action | Handler | Schema Ready | Priority |
|--------|---------|--------------|----------|
| create_purchase_request | ✅ Implemented | ❌ **P0 MIGRATION** | **P0** |
| add_item_to_purchase | ✅ Implemented | ❌ **P0 MIGRATION** | **P0** |
| approve_purchase | ✅ Implemented | ❌ **P0 MIGRATION** | **P0** |
| track_delivery | ⚠️ Partial | ✅ Yes | P1 |
| log_delivery_received | ✅ Implemented | ❌ **P0 MIGRATION** | **P0** |

**Stubbed for MVP:**
- update_purchase_status (manual status change, low priority)
- upload_invoice (document management, post-MVP)
- create_purchase_order (use create_purchase_request instead)
- mark_po_ordered (requires migration, low priority)
- receive_items (requires receiving_sessions table - post-MVP)
- check_in_item (requires receiving_sessions table - post-MVP)
- commit_session (requires receiving_sessions table - post-MVP)
- cancel_session (requires receiving_sessions table - post-MVP)

---

### EQUIPMENT CLUSTER (5 actions)

| Action | Handler | Schema Ready | Priority |
|--------|---------|--------------|----------|
| view_equipment | ✅ Implemented | ✅ Yes | **P0** |
| view_maintenance_history | ✅ Implemented | ✅ Yes (audit_log) | P1 |
| view_equipment_parts | ✅ Implemented | ✅ Yes | P1 |
| view_linked_faults | ✅ Implemented | ✅ Yes | P1 |
| view_equipment_manual | ✅ Implemented | ⚠️ Use attachments | P1 |

**Stubbed for MVP:**
- add_equipment (admin function, low priority)
- update_equipment (admin function, low priority)
- change_equipment_status (requires careful validation)
- decommission_equipment (requires signature, rare)
- link_equipment_to_manual (document management, post-MVP)
- add_equipment_note (low priority)

---

### HANDOVER CLUSTER (5 actions)

| Action | Handler | Schema Ready | Priority |
|--------|---------|--------------|----------|
| add_to_handover | ✅ Implemented | ✅ Yes | **P0** |
| add_document_to_handover | ✅ Implemented | ⚠️ Use attachments | P1 |
| edit_handover_section | ✅ Implemented | ✅ Yes | P1 |
| export_handover | ✅ Implemented | ✅ Yes | P1 |
| regenerate_handover_summary | ✅ Implemented | ✅ Yes | P1 |

**Stubbed for MVP:**
- add_document_section_to_handover (document mgmt, post-MVP)
- add_note (general handover - use add_to_handover instead)
- acknowledge_handover (low priority - optional action)
- generate_summary (AI - use regenerate_handover_summary)

---

### CHECKLIST CLUSTER (3 actions)

| Action | Handler | Schema Ready | Priority |
|--------|---------|--------------|----------|
| view_checklist | ✅ Implemented | ✅ Yes | P1 |
| mark_checklist_item_complete | ✅ Implemented | ✅ Yes | P1 |
| add_checklist_photo | ✅ Implemented | ✅ Yes (attachments) | P1 |

**Stubbed for MVP:**
- create_checklist (admin function)
- add_checklist_item (admin function)
- skip_checklist_item (low priority)
- complete_checklist (requires signature, post-MVP)
- add_checklist_note (low priority)

---

### DOCUMENT CLUSTER (2 actions)

| Action | Handler | Schema Ready | Priority |
|--------|---------|--------------|----------|
| view_manual_section | ✅ Implemented | ⚠️ Use attachments | P1 |
| view_related_docs | ⚠️ Partial | ⚠️ Use attachments | P1 |

**Stubbed for MVP:**
- upload_document (admin function, post-MVP)
- link_document_to_equipment (post-MVP)
- search_documents (full-text search, post-MVP)
- view_document_section (post-MVP)

---

### SEARCH & LIST ACTIONS (4 actions)

| Action | Handler | Schema Ready | Priority |
|--------|---------|--------------|----------|
| search | ✅ Implemented | ✅ Yes | **P0** |
| list_work_orders | ✅ Implemented | ✅ Yes | **P0** |
| list_faults | ✅ Implemented | ✅ Yes | **P0** |
| list_parts | ✅ Implemented | ✅ Yes | **P0** |

---

### ATTACHMENT ACTIONS (1 action)

| Action | Handler | Schema Ready | Priority |
|--------|---------|--------------|----------|
| add_photo | ✅ Implemented | ✅ Yes (attachments) | **P0** |

**Stubbed for MVP:**
- remove_photo (low priority - rarely used)
- upload_photo (mobile-specific, use add_photo)
- view_attachments (implicit in entity detail)

---

## MVP ACTION COUNT SUMMARY

**Total MVP Actions:** 47
- P0 (Must Ship): 32 actions
- P1 (Nice to Have): 15 actions
- Stubbed (Disabled): 24 actions

**Implementation Status:**
- Handlers Implemented: 42 actions (89%)
- Schema Ready: 38 actions (81%)
- Need P0 Migration: 5 actions (11%)

---

## P0 SCHEMA MIGRATIONS (MUST BE DONE NOW)

These migrations block MVP launch. **Do these first.**

### 1. Shopping List Items Table ⚠️ CRITICAL

**Blocks:** add_to_shopping_list, purchasing flow

```sql
CREATE TABLE IF NOT EXISTS public.shopping_list_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id),
    part_id UUID NOT NULL REFERENCES public.pms_parts(id),
    quantity_requested INTEGER NOT NULL DEFAULT 1,
    priority TEXT CHECK (priority IN ('low', 'normal', 'high', 'urgent')) DEFAULT 'normal',
    notes TEXT,
    requested_by UUID NOT NULL,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status TEXT CHECK (status IN ('pending', 'ordered', 'cancelled')) DEFAULT 'pending',
    purchase_order_id UUID REFERENCES public.pms_purchase_orders(id),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_at TIMESTAMPTZ,
    updated_by UUID,

    deleted_at TIMESTAMPTZ,
    deleted_by UUID,
    deletion_reason TEXT
);

CREATE INDEX idx_shopping_list_yacht_status ON shopping_list_items(yacht_id, status) WHERE deleted_at IS NULL;
CREATE INDEX idx_shopping_list_part ON shopping_list_items(part_id);
ALTER TABLE shopping_list_items ENABLE ROW LEVEL SECURITY;
```

**Priority:** 🔴 P0 - CRITICAL

---

### 2. Purchase Order Items Table ⚠️ CRITICAL

**Blocks:** create_purchase_request, add_item_to_purchase

```sql
CREATE TABLE IF NOT EXISTS public.purchase_order_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id),
    purchase_order_id UUID NOT NULL REFERENCES public.pms_purchase_orders(id) ON DELETE CASCADE,
    part_id UUID REFERENCES public.pms_parts(id),
    description TEXT NOT NULL,
    quantity_ordered INTEGER NOT NULL,
    quantity_received INTEGER DEFAULT 0,
    unit_price NUMERIC(12,2),
    total_price NUMERIC(12,2),
    notes TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_at TIMESTAMPTZ,
    updated_by UUID,

    deleted_at TIMESTAMPTZ,
    deleted_by UUID
);

CREATE INDEX idx_po_items_purchase_order ON purchase_order_items(purchase_order_id);
CREATE INDEX idx_po_items_part ON purchase_order_items(part_id);
ALTER TABLE purchase_order_items ENABLE ROW LEVEL SECURITY;
```

**Priority:** 🔴 P0 - CRITICAL

---

### 3. Purchase Order Tracking Columns ⚠️ CRITICAL

**Blocks:** approve_purchase, log_delivery_received

```sql
ALTER TABLE public.pms_purchase_orders
ADD COLUMN IF NOT EXISTS approved_by UUID,
ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS approval_notes TEXT,
ADD COLUMN IF NOT EXISTS received_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS received_by UUID,
ADD COLUMN IF NOT EXISTS receiving_notes TEXT;

COMMENT ON COLUMN pms_purchase_orders.approved_by IS 'HOD who approved PO';
COMMENT ON COLUMN pms_purchase_orders.approved_at IS 'Approval timestamp';
COMMENT ON COLUMN pms_purchase_orders.received_at IS 'Delivery received timestamp';
COMMENT ON COLUMN pms_purchase_orders.received_by IS 'User who confirmed receipt';
```

**Priority:** 🔴 P0 - CRITICAL

---

## P1 SCHEMA MIGRATIONS (Nice to Have, Not Blocking)

These improve quality of life but are NOT required for MVP launch.

### 4. Fault Diagnosis Columns

**Improves:** diagnose_fault (currently uses metadata JSONB)

```sql
ALTER TABLE public.pms_faults
ADD COLUMN IF NOT EXISTS diagnosis TEXT,
ADD COLUMN IF NOT EXISTS diagnosis_notes TEXT,
ADD COLUMN IF NOT EXISTS diagnosed_by UUID,
ADD COLUMN IF NOT EXISTS diagnosed_at TIMESTAMPTZ;
```

**Priority:** 🟡 P1 - Can use metadata for MVP

---

### 5. Documents Table

**Enables:** Document management features

**Priority:** 🟡 P1 - Use pms_attachments for MVP

---

### 6. Receiving Sessions Table

**Enables:** Multi-step receiving flow

**Priority:** 🟡 P1 - Use direct commit for MVP (simplified flow)

---

## STUBBED/DISABLED ACTIONS FOR MVP

These actions are **registered in the registry** but **not functional** for MVP. Show them in UI as disabled/greyed or hide completely.

### Fault Cluster (4 stubbed)
- report_fault
- resolve_fault
- close_fault
- defer_fault

### Work Order Cluster (5 stubbed)
- start_work_order
- add_wo_hours
- remove_wo_part
- reopen_work_order
- cancel_work_order

### Inventory Cluster (5 stubbed)
- adjust_inventory
- restock_part
- remove_from_shopping_list
- flag_low_stock
- scan_part_barcode

### Purchasing Cluster (8 stubbed)
- update_purchase_status
- upload_invoice
- create_purchase_order
- mark_po_ordered
- receive_items
- check_in_item
- commit_session
- cancel_session

### Equipment Cluster (6 stubbed)
- add_equipment
- update_equipment
- change_equipment_status
- decommission_equipment
- link_equipment_to_manual
- add_equipment_note

### Handover Cluster (4 stubbed)
- add_document_section_to_handover
- add_note (general handover)
- acknowledge_handover
- generate_summary

### Checklist Cluster (4 stubbed)
- create_checklist
- add_checklist_item
- skip_checklist_item
- complete_checklist
- add_checklist_note

### Document Cluster (3 stubbed)
- upload_document
- link_document_to_equipment
- search_documents

### Attachment Actions (2 stubbed)
- remove_photo
- upload_photo

**Total Stubbed:** 41 actions

**UI Treatment Options:**
1. **Hide completely** (recommended for MVP)
2. Show as disabled with "Coming Soon" tooltip
3. Show in "More ▾" dropdown but disabled

**Recommendation:** Hide completely for MVP. Reduces cognitive load.

---

## MVP BOUNDARY ENFORCEMENT

### What Goes in MVP
✅ Core fault/WO/inventory workflows
✅ Basic handover functionality
✅ Simple purchasing flow (shopping list → PO)
✅ View actions (equipment, parts, manuals)
✅ Photo attachments
✅ Basic checklists

### What Stays Out of MVP
❌ Advanced purchasing (receiving sessions, invoice uploads)
❌ Document management system
❌ Predictive analytics
❌ Fleet-wide reporting
❌ Compliance automation
❌ Third-party integrations
❌ Offline mode
❌ Push notifications
❌ Bulk actions
❌ Advanced time tracking

---

## MIGRATION EXECUTION ORDER

**Week 1:**
1. ✅ Deploy shopping_list_items table
2. ✅ Deploy purchase_order_items table
3. ✅ Add PO tracking columns
4. ✅ Test purchasing flow end-to-end

**Week 2:**
5. ✅ Deploy P1 migrations (if time permits)
6. ✅ Update handlers to use new tables
7. ✅ Integration tests

**Week 3:**
8. ✅ Frontend implementation (47 MVP actions)
9. ✅ End-to-end testing
10. ✅ MVP launch

---

## SUCCESS CRITERIA

### MVP is ready to ship when:
- [ ] All 32 P0 actions implemented and tested
- [ ] P0 schema migrations deployed
- [ ] Frontend implements 4-segment action layout
- [ ] Situation state machine functional
- [ ] RAG suggestions working (assistive only)
- [ ] Signature flow working (tap accept)
- [ ] RLS enforced on all queries
- [ ] Audit log written for all MUTATE actions
- [ ] Zero crashes on core workflows

### MVP does NOT need:
- [ ] P1 actions (nice to have, not blocking)
- [ ] P1 schema migrations (can use workarounds)
- [ ] Stubbed actions (explicitly disabled)
- [ ] Advanced features (post-MVP)

---

## RISK MITIGATION

### High Risk (Could Block Launch)
1. **P0 migrations fail** → Test thoroughly in staging first
2. **RLS policy errors** → Comprehensive permission tests
3. **Signature flow breaks** → Fallback to no-signature for MVP (risk acceptable)

### Medium Risk (Workarounds Available)
4. **RAG prefill fails** → Users enter manually (UX degraded but functional)
5. **Audit log missing** → Cannot launch (mandatory for accountability)
6. **Performance issues** → Optimize after launch (if not critical)

### Low Risk (Post-MVP)
7. **Missing P1 actions** → Expected, not blocking
8. **Document management incomplete** → Use basic attachments

---

## POST-MVP ROADMAP (Not Now)

**Phase 2 (After MVP Launch):**
- Receiving sessions (multi-step PO receiving)
- Document management (dedicated pms_documents table)
- Time tracking (work_order_time_log table)
- Fault notes table (better than metadata)
- Equipment decommissioning
- Advanced checklists (signature required)

**Phase 3 (Future):**
- Predictive analytics
- Fleet-wide reporting
- Compliance automation
- Third-party integrations
- Offline mode
- PIN/biometric signatures

---

**Build the 47 MVP actions. Ship. Iterate.**
