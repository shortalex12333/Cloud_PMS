# Lens → Tables → Buttons Matrix

**Generated**: 2026-03-02
**Purpose**: Unified reference mapping each Entity Lens to its database tables and UI action buttons
**Use Case**: Parallel testing via fragmented routes - each route URL is a test entry point

---

## Quick Reference Summary

| Lens | Primary Table | Total Tables | Actions | RLS Status |
|------|--------------|--------------|---------|------------|
| Work Orders | `pms_work_orders` | 11 | 8 | ⚠️ B1-B3 blockers |
| Faults | `pms_faults` | 5 | 10 | ⚠️ B1 blocker |
| Equipment | `pms_equipment` | 5+ | 7 | ✅ Ready |
| Parts/Inventory | `pms_parts`, `pms_inventory_stock` | 8+ | 9 | ⚠️ Two versions |
| Receiving | `pms_receiving_events` | 10 | 6 | ✅ Ready |
| Shopping List | `pms_shopping_list_items` | 7 | 5 | ✅ Ready |
| Certificates | `pms_vessel_certificates`, `pms_crew_certificates` | 8 | 5 | ⚠️ B1-B2 blockers |
| Documents | `doc_metadata` | 3 | 6 | ✅ Ready |

---

## 1. Work Orders Lens

### Primary Table
| Table | Columns | yacht_id | RLS Status |
|-------|---------|----------|------------|
| `pms_work_orders` | 29 | ✅ | ✅ Canonical |

### Joined Tables (Read)
| Table | Purpose | FK |
|-------|---------|-----|
| `pms_equipment` | Equipment details | `equipment_id` |
| `pms_faults` | Linked fault | `fault_id` |
| `auth_users_profiles` | Assignee names | `assigned_to`, `created_by` |
| `yacht_registry` | Yacht validation | `yacht_id` |

### Mutation Tables (Write)
| Table | yacht_id | RLS Status | Operations |
|-------|----------|------------|------------|
| `pms_work_orders` | ✅ | ✅ | INSERT, UPDATE |
| `pms_work_order_checklist` | ✅ | ⚠️ Mixed | INSERT, UPDATE |
| `pms_work_order_notes` | ❌ | ❌ **B1** | INSERT |
| `pms_work_order_parts` | ❌ | ❌ **B2** | INSERT |
| `pms_work_order_history` | ✅ | ✅ | INSERT |
| `pms_part_usage` | ✅ | ❌ **B3** | INSERT |
| `pms_audit_log` | ✅ | ✅ | INSERT |

### Buttons / Actions
| # | Button Label | action_name | Signature | Tables Written |
|---|--------------|-------------|-----------|----------------|
| 1 | Create Work Order | `create_work_order` | NO | work_orders, audit |
| 2 | Update Work Order | `update_work_order` | NO | work_orders, audit |
| 3 | Complete Work Order | `complete_work_order` | NO (confirm) | work_orders, history, part_usage, faults (trigger) |
| 4 | Add Note | `add_work_order_note` | NO | notes, audit |
| 5 | Reassign Work Order | `reassign_work_order` | **YES** | work_orders, audit |
| 6 | Archive Work Order | `archive_work_order` | **YES** | work_orders, audit, faults (trigger) |
| 7 | Add Parts | `add_parts_to_work_order` | NO | work_order_parts |
| 8 | Log Part Usage | `log_part_usage` | NO | part_usage, parts |

---

## 2. Faults Lens

### Primary Table
| Table | Columns | yacht_id | RLS Status |
|-------|---------|----------|------------|
| `pms_faults` | 19 | ✅ | ⚠️ SELECT only (B1) |

### Joined Tables (Read)
| Table | Purpose | FK |
|-------|---------|-----|
| `pms_equipment` | Equipment reference | `equipment_id` |
| `pms_work_orders` | Linked WO | `work_order_id` |
| `pms_notes` | Fault notes | `fault_id` |
| `pms_attachments` | Photos | `entity_id` |

### Mutation Tables (Write)
| Table | yacht_id | RLS Status | Operations |
|-------|----------|------------|------------|
| `pms_faults` | ✅ | ⚠️ **B1** (SELECT only) | INSERT, UPDATE |
| `pms_notes` | ✅ | ⚠️ **B2** | INSERT |
| `pms_attachments` | ✅ | ⚠️ **B3** | INSERT |
| `pms_work_orders` | ✅ | ✅ | INSERT (from fault) |
| `pms_audit_log` | ✅ | ✅ | INSERT |

### Buttons / Actions
| # | Button Label | action_name | Signature | Tables Written |
|---|--------------|-------------|-----------|----------------|
| 1 | Report Fault | `report_fault` | NO | faults, audit |
| 2 | Acknowledge Fault | `acknowledge_fault` | NO | faults, audit |
| 3 | Close Fault | `close_fault` | NO | faults, audit |
| 4 | Update Fault | `update_fault` | NO | faults, audit |
| 5 | Reopen Fault | `reopen_fault` | NO | faults, audit |
| 6 | Mark False Alarm | `mark_fault_false_alarm` | NO | faults, audit |
| 7 | Add Note | `add_fault_note` | NO | notes, audit |
| 8 | Add Photo | `add_fault_photo` | NO | attachments, audit |
| 9 | Create WO from Fault | `create_work_order_from_fault` | **YES** | work_orders, faults, audit |
| 10 | View Detail | `view_fault_detail` | — (read) | — |

---

## 3. Equipment Lens

### Primary Table
| Table | Columns | yacht_id | RLS Status |
|-------|---------|----------|------------|
| `pms_equipment` | 24 | ✅ | ✅ Canonical |

### Joined Tables (Read)
| Table | Purpose | FK |
|-------|---------|-----|
| `pms_equipment_parts_bom` | Parts BOM | `equipment_id` |
| `pms_notes` | Equipment notes | `equipment_id` |
| `pms_attachments` | Photos/docs | `entity_id` |
| `pms_audit_log` | History | `entity_id` |

### Mutation Tables (Write)
| Table | yacht_id | RLS Status | Operations |
|-------|----------|------------|------------|
| `pms_equipment` | ✅ | ✅ | UPDATE |
| `pms_notes` | ✅ | ⚠️ | INSERT |
| `pms_attachments` | ✅ | ⚠️ | INSERT |
| `pms_work_orders` | ✅ | ✅ | INSERT (escape) |
| `pms_equipment_parts_bom` | ✅ | ✅ | INSERT |
| `pms_audit_log` | ✅ | ✅ | INSERT |

### Buttons / Actions
| # | Button Label | action_name | Signature | Tables Written |
|---|--------------|-------------|-----------|----------------|
| 1 | Update Status | `update_equipment_status` | NO | equipment, audit |
| 2 | Add Note | `add_equipment_note` | NO | notes, audit |
| 3 | Attach Photo | `attach_file_to_equipment` | NO | attachments, audit |
| 4 | Create Work Order | `create_work_order_for_equipment` | NO | work_orders, audit |
| 5 | Link Part | `link_part_to_equipment` | NO | equipment_parts_bom, audit |
| 6 | Flag Attention | `flag_equipment_attention` | NO | equipment, audit |
| 7 | Decommission | `decommission_equipment` | **YES** | equipment, audit |

---

## 4. Parts / Inventory Lens

### Primary Tables (Two-Tier Model)
| Table | Purpose | yacht_id | RLS Status |
|-------|---------|----------|------------|
| `pms_parts` | Part master catalog | ✅ | ✅ |
| `pms_inventory_stock` | Per-location stock | ✅ | ✅ |
| `pms_inventory_transactions` | Append-only ledger | ✅ | ⚠️ |

### Joined Tables (Read)
| Table | Purpose | FK |
|-------|---------|-----|
| `pms_equipment_parts_bom` | Equipment compatibility | `part_id` |
| `pms_work_orders` | WO context | `work_order_id` |
| `pms_part_locations` | Location normalization | `primary_location_id` |
| `pms_shopping_list_items` | Procurement link | `part_id` |

### Mutation Tables (Write)
| Table | yacht_id | RLS Status | Operations |
|-------|----------|------------|------------|
| `pms_parts` | ✅ | ✅ | INSERT, UPDATE |
| `pms_inventory_stock` | ✅ | ✅ | INSERT, UPDATE |
| `pms_inventory_transactions` | ✅ | ⚠️ | INSERT (append-only) |
| `pms_part_usage` | ✅ | ⚠️ | INSERT (append-only) |
| `pms_shopping_list_items` | ✅ | ✅ | INSERT |
| `pms_audit_log` | ✅ | ✅ | INSERT |

### Buttons / Actions
| # | Button Label | action_name | Signature | Tables Written |
|---|--------------|-------------|-----------|----------------|
| 1 | Log Usage | `consume_part` / `record_part_consumption` | NO | part_usage, parts, transactions, audit |
| 2 | Count Stock | `adjust_stock_quantity` | CONDITIONAL | parts, transactions, audit |
| 3 | Add to Shopping List | `add_to_shopping_list` | NO | shopping_list_items, audit |
| 4 | Receive Parts | `receive_part` | NO | parts, transactions, audit |
| 5 | Transfer Parts | `transfer_part` | NO | transactions (x2), audit |
| 6 | Write Off | `write_off_part` | **YES** | parts, transactions, audit |
| 7 | Create Part | `create_part` | NO | parts, audit |
| 8 | Deactivate Part | `deactivate_part` | **YES** | parts (soft delete), audit |
| 9 | Reverse Transaction | `reverse_transaction` | **YES** | transactions, parts, audit |

---

## 5. Receiving Lens

### Primary Table
| Table | Columns | yacht_id | RLS Status |
|-------|---------|----------|------------|
| `pms_receiving_events` | 21 | ✅ | ✅ Canonical |

### Joined Tables (Read)
| Table | Purpose | FK |
|-------|---------|-----|
| `pms_receiving_line_items` | Line items | `receiving_event_id` |
| `pms_orders` | PO reference | `order_id` |
| `pms_parts` | Stock levels | `part_id` |
| `pms_shopping_list_items` | Shopping link | `shopping_list_item_id` |
| `pms_equipment` | Install target | `installed_to_equipment_id` |
| `pms_work_orders` | WO install | `installed_to_work_order_id` |
| `auth_users_profiles` | User names | `received_by`, `verified_by` |

### Mutation Tables (Write)
| Table | yacht_id | RLS Status | Operations |
|-------|----------|------------|------------|
| `pms_receiving_events` | ✅ | ✅ | INSERT, UPDATE |
| `pms_receiving_line_items` | ✅ | ✅ | INSERT, UPDATE |
| `pms_parts` | ✅ | ✅ | UPDATE (qty) |
| `pms_shopping_list_items` | ✅ | ✅ | UPDATE, INSERT |
| `pms_audit_log` | ✅ | ✅ | INSERT |

### Buttons / Actions
| # | Button Label | action_name | Signature | Tables Written |
|---|--------------|-------------|-----------|----------------|
| 1 | Start Receiving | `start_receiving_event` | NO | events, audit |
| 2 | Add Item | `add_line_item` | NO | line_items, audit |
| 3 | Accept | `complete_receiving_event` | NO | events, parts, shopping_list, audit |
| 4 | Reject | `report_discrepancy` | NO | events, shopping_list, audit |
| 5 | Verify Line Item | `verify_line_item` | NO | line_items, audit |
| 6 | View Photos | `view_receiving_photos` | — (read) | — |

---

## 6. Shopping List Lens

### Primary Table
| Table | Columns | yacht_id | RLS Status |
|-------|---------|----------|------------|
| `pms_shopping_list_items` | 45 | ✅ | ✅ Canonical |

### State Machine
```
candidate → under_review → approved → ordered → partially_fulfilled → fulfilled → installed
                        ↘ rejected (terminal)
```

### Joined Tables (Read)
| Table | Purpose | FK |
|-------|---------|-----|
| `pms_shopping_list_state_history` | Audit trail | `shopping_list_item_id` |
| `pms_orders` | PO status | `order_id` |
| `pms_work_orders` | Source WO | `source_work_order_id` |
| `pms_parts` | Part catalog | `part_id` |
| `pms_equipment` | Install target | `installed_to_equipment_id` |

### Mutation Tables (Write)
| Table | yacht_id | RLS Status | Operations |
|-------|----------|------------|------------|
| `pms_shopping_list_items` | ✅ | ✅ | INSERT, UPDATE |
| `pms_shopping_list_state_history` | ✅ | ✅ | INSERT (via trigger) |
| `pms_parts` | ✅ | ✅ | INSERT (promotion) |
| `pms_audit_log` | ✅ | ✅ | INSERT |

### Buttons / Actions
| # | Button Label | action_name | Signature | Tables Written |
|---|--------------|-------------|-----------|----------------|
| 1 | Add Item | `create_shopping_list_item` | NO | items, history, audit |
| 2 | Mark Ordered | `approve_shopping_list_item` | NO | items, history, audit |
| 3 | Approve | `approve_shopping_list_item` | NO | items, history, audit |
| 4 | Reject | `reject_shopping_list_item` | NO | items, history, audit |
| 5 | Promote to Catalog | `promote_candidate_to_part` | NO | parts, items, audit |

---

## 7. Certificates Lens

### Primary Tables (Dual Entity)
| Table | Purpose | yacht_id | RLS Status |
|-------|---------|----------|------------|
| `pms_vessel_certificates` | Vessel compliance | ✅ | ❌ **B1** (no RLS) |
| `pms_crew_certificates` | Crew qualifications | ✅ | ⚠️ **B2** (partial) |

### Joined Tables (Read)
| Table | Purpose | FK |
|-------|---------|-----|
| `doc_metadata` | Linked documents | `document_id` |
| `yacht_registry` | Yacht validation | `yacht_id` |
| `auth_users_profiles` | User lookup | Various |
| `auth_users_roles` | Role validation | `user_id` |

### Mutation Tables (Write)
| Table | yacht_id | RLS Status | Operations |
|-------|----------|------------|------------|
| `pms_vessel_certificates` | ✅ | ❌ **B1** | INSERT, UPDATE, DELETE |
| `pms_crew_certificates` | ✅ | ⚠️ **B2** | INSERT, UPDATE, DELETE |
| `doc_metadata` | ✅ | ✅ | INSERT, UPDATE |
| `storage.objects` | ✅ | ⚠️ **B5** | INSERT, DELETE |
| `pms_audit_log` | ✅ | ✅ | INSERT |

### Buttons / Actions
| # | Button Label | action_name | Signature | Tables Written |
|---|--------------|-------------|-----------|----------------|
| 1 | Create Vessel Cert | `create_vessel_certificate` | NO | vessel_certs, audit |
| 2 | Create Crew Cert | `create_crew_certificate` | NO | crew_certs, audit |
| 3 | Renew Certificate | `update_certificate` | NO | certs, audit |
| 4 | Link Document | `link_document_to_certificate` | NO | certs, audit |
| 5 | Supersede Certificate | `supersede_certificate` | **YES** | certs (status), audit |

---

## 8. Documents Lens

### Primary Table
| Table | Columns | yacht_id | RLS Status |
|-------|---------|----------|------------|
| `doc_metadata` | 21 | ✅ | ✅ Canonical |

### Storage Integration
| Component | Path Pattern |
|-----------|--------------|
| Bucket | `documents` |
| Storage Path | `{yacht_id}/documents/{doc_id}/{filename}` |

### Mutation Tables (Write)
| Table | yacht_id | RLS Status | Operations |
|-------|----------|------------|------------|
| `doc_metadata` | ✅ | ✅ | INSERT, UPDATE, DELETE |
| `storage.objects` | ✅ | ✅ | INSERT, DELETE |
| `pms_audit_log` | ✅ | ✅ | INSERT |

### Buttons / Actions
| # | Button Label | action_name | Signature | Tables Written |
|---|--------------|-------------|-----------|----------------|
| 1 | Upload | `upload_document` | NO | doc_metadata, storage, audit |
| 2 | Update Metadata | `update_document` | NO | doc_metadata, audit |
| 3 | Add Tags | `add_document_tags` | NO | doc_metadata, audit |
| 4 | Link to Equipment | `link_document_to_equipment` | NO | doc_metadata, audit |
| 5 | Delete Document | `delete_document` | **YES** | doc_metadata, storage, audit |
| 6 | Get URL | `get_document_url` | — (read) | — |

---

## Cross-Lens Relationships

### Shared Tables
| Table | Lenses Using It |
|-------|-----------------|
| `pms_audit_log` | ALL (immutable audit trail) |
| `pms_equipment` | Work Orders, Faults, Equipment, Parts, Receiving, Documents |
| `pms_parts` | Parts, Work Orders, Receiving, Shopping List |
| `pms_work_orders` | Work Orders, Faults, Equipment, Parts, Shopping List |
| `doc_metadata` | Documents, Certificates |
| `pms_notes` | Work Orders, Faults, Equipment |
| `pms_attachments` | Faults, Equipment |

### Escape Hatches (Cross-Lens Navigation)
| From Lens | To Lens | Trigger |
|-----------|---------|---------|
| Work Orders | Equipment | Click `equipment_id` |
| Work Orders | Faults | Click `fault_id` |
| Faults | Equipment | Click `equipment_id` |
| Faults | Work Orders | Click `work_order_id` or create WO |
| Equipment | Work Orders | Create WO from equipment |
| Equipment | Parts | Click part in BOM |
| Parts | Shopping List | Add to shopping list |
| Receiving | Parts | Click `part_id` |
| Receiving | Shopping List | Click shopping list item |
| Shopping List | Work Orders | Click source WO |
| Shopping List | Parts | Click part / promote |
| Certificates | Documents | Click `document_id` |
| Documents | Equipment | Click `equipment_ids[]` |

---

## RLS Blockers Summary

| ID | Table | Issue | Impact | Migration |
|----|-------|-------|--------|-----------|
| **B1** | `pms_work_order_notes` | `USING(true)` - cross-yacht leakage | WO Add Note blocked | `20260125_001` |
| **B2** | `pms_work_order_parts` | `USING(true)` - cross-yacht leakage | WO Add Parts blocked | `20260125_002` |
| **B3** | `pms_part_usage` | `USING(true)` - cross-yacht leakage | Complete WO blocked | `20260125_003` |
| **B4** | `pms_work_orders` | Missing cascade trigger | Complete/Archive cascade | `20260125_004` |
| **B1** | `pms_faults` | SELECT-only RLS | All fault mutations blocked | `20260127_001` |
| **B2** | `pms_notes` (faults) | Missing INSERT/UPDATE | Add Fault Note blocked | `20260127_002` |
| **B3** | `pms_attachments` (faults) | Missing storage write | Add Fault Photo blocked | `20260127_003` |
| **B1** | `pms_vessel_certificates` | No RLS policies | All vessel cert ops blocked | `20260125_007` |
| **B2** | `pms_crew_certificates` | Partial RLS | Crew cert INSERT/UPDATE blocked | `20260125_006` |

---

## Signature-Required Actions

| Lens | Action | Required Role |
|------|--------|---------------|
| Work Orders | `reassign_work_order` | HoD |
| Work Orders | `archive_work_order` | Captain, HoD |
| Faults | `create_work_order_from_fault` | HoD |
| Equipment | `decommission_equipment` | Captain, Manager |
| Parts | `write_off_part` | Manager |
| Parts | `deactivate_part` | HoD |
| Parts | `reverse_transaction` | Manager |
| Certificates | `supersede_certificate` | Captain, Manager |
| Documents | `delete_document` | Manager |

---

## Testing Entry Points (Fragmented Routes)

| Lens | Route Pattern | Button Test Pattern |
|------|---------------|---------------------|
| Work Orders | `/work-orders/[id]` | Direct button click tests |
| Faults | `/faults/[id]` | Direct button click tests |
| Equipment | `/equipment/[id]` | Direct button click tests |
| Parts | `/parts/[id]` or `/inventory/[id]` | Direct button click tests |
| Receiving | `/receiving/[id]` | Direct button click tests |
| Shopping List | `/shopping-list/[id]` | Direct button click tests |
| Certificates | `/certificates/vessel/[id]` | Direct button click tests |
| Documents | `/documents/[id]` | Direct button click tests |

---

**END OF DOCUMENT**
