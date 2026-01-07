# Action to Table Mapping

**Version:** 1.0
**Date:** 2025-11-21
**Total Actions:** 67

---

## Quick Reference Table

| # | action_name | primary_table | secondary_tables | workflow_archetype | audit_required |
|---|-------------|---------------|------------------|-------------------|----------------|
| **FIX_SOMETHING Cluster (8 actions)** |
| 1 | diagnose_fault | faults | fault_embeddings, documents, equipment | RAG | No |
| 2 | show_manual_section | documents | - | VIEW | No |
| 3 | view_fault_history | faults | - | VIEW | No |
| 4 | suggest_parts | parts | fault_parts_suggestions, equipment_parts | VIEW | No |
| 5 | create_work_order_from_fault | work_orders | faults, audit_logs | CREATE | Yes (MEDIUM) |
| 6 | add_fault_note | fault_notes | audit_logs | CREATE | Yes (LOW) |
| 7 | add_fault_photo | fault_attachments | audit_logs | CREATE | Yes (LOW) |
| 8 | edit_fault_details | faults | audit_logs | UPDATE | Yes (MEDIUM) |
| **DO_MAINTENANCE Cluster (10 actions)** |
| 9 | create_work_order | work_orders | audit_logs | CREATE | Yes (MEDIUM) |
| 10 | view_work_order_history | work_orders | - | VIEW | No |
| 11 | mark_work_order_complete | work_orders | audit_logs, parts | UPDATE | Yes (MEDIUM) |
| 12 | add_work_order_note | work_order_notes | audit_logs | CREATE | Yes (LOW) |
| 13 | add_work_order_photo | work_order_attachments | audit_logs | CREATE | Yes (LOW) |
| 14 | add_parts_to_work_order | work_order_parts | parts, audit_logs | LINKING | Yes (MEDIUM) |
| 15 | view_work_order_checklist | work_order_checklists | checklist_items | VIEW | No |
| 16 | assign_work_order | work_orders | users, audit_logs | UPDATE | Yes (MEDIUM) |
| 17 | edit_work_order_details | work_orders | audit_logs | UPDATE | Yes (MEDIUM) |
| 18 | approve_work_order | work_orders | audit_logs, notifications | UPDATE | Yes (MEDIUM) |
| **MANAGE_EQUIPMENT Cluster (8 actions)** |
| 19 | view_equipment_details | equipment | - | VIEW | No |
| 20 | view_equipment_history | equipment_history | work_orders, faults | VIEW | No |
| 21 | view_equipment_parts | equipment_parts | parts | VIEW | No |
| 22 | view_linked_faults | faults | equipment | VIEW | No |
| 23 | view_equipment_manual | documents | equipment | VIEW | No |
| 24 | add_equipment_note | equipment_notes | audit_logs | CREATE | Yes (LOW) |
| 25 | edit_equipment_details | equipment | audit_logs, notifications | UPDATE | Yes (HIGH*) |
| 26 | scan_equipment_barcode | equipment | - | VIEW | No |
| **CONTROL_INVENTORY Cluster (8 actions)** |
| 27 | view_part_stock | parts | - | VIEW | No |
| 28 | order_part | part_orders | audit_logs | CREATE | Yes (MEDIUM) |
| 29 | view_part_location | parts | - | VIEW | No |
| 30 | view_part_usage | part_usage_log | work_orders | VIEW | No |
| 31 | log_part_usage | part_usage_log | parts, work_orders, audit_logs | UPDATE | Yes (MEDIUM) |
| 32 | scan_part_barcode | parts | - | VIEW | No |
| 33 | view_linked_equipment | equipment_parts | equipment | VIEW | No |
| 34 | edit_part_quantity | parts | audit_logs | UPDATE | Yes (MEDIUM) |
| **COMMUNICATE_STATUS Cluster (11 actions)** |
| 35 | add_to_handover | handover_items | handovers, audit_logs | LINKING | Yes (LOW) |
| 36 | add_document_to_handover | handover_documents | handovers, documents | LINKING | Yes (LOW) |
| 37 | add_predictive_insight_to_handover | handover_insights | handovers, ai_insights | LINKING | Yes (LOW) |
| 38 | edit_handover_section | handover_sections | audit_logs | UPDATE | Yes (LOW) |
| 39 | export_handover | handovers | - | EXPORT | Yes (LOW) |
| 40 | regenerate_handover_summary | handovers | ai_summaries | UPDATE | No |
| 41 | view_document | documents | - | VIEW | No |
| 42 | view_related_documents | documents | faults, equipment | VIEW | No |
| 43 | view_document_section | documents | - | VIEW | No |
| 44 | edit_note | notes | audit_logs | UPDATE | Yes (LOW) |
| 45 | delete_item | multiple | audit_logs | UPDATE | Yes (MEDIUM) |
| **COMPLY_AUDIT Cluster (5 actions)** |
| 46 | view_hours_of_rest | hours_of_rest | users | VIEW | No |
| 47 | update_hours_of_rest | hours_of_rest | audit_logs | UPDATE | Yes (MEDIUM) |
| 48 | export_hours_of_rest | hours_of_rest | - | EXPORT | Yes (LOW) |
| 49 | view_compliance_status | compliance_records | hours_of_rest | VIEW | No |
| 50 | tag_for_survey | work_items | audit_logs | UPDATE | Yes (LOW) |
| **PROCURE_SUPPLIERS Cluster (9 actions)** |
| 51 | create_purchase_request | purchase_requests | purchase_request_items, audit_logs | CREATE | Yes (MEDIUM) |
| 52 | add_item_to_purchase | purchase_request_items | purchase_requests, audit_logs | UPDATE | Yes (LOW) |
| 53 | approve_purchase | purchase_requests | audit_logs, notifications | UPDATE | Yes (MEDIUM) |
| 54 | upload_invoice | invoices | purchase_requests, audit_logs | CREATE | Yes (MEDIUM) |
| 55 | track_delivery | deliveries | purchase_requests | VIEW | No |
| 56 | log_delivery_received | deliveries | parts, purchase_requests, audit_logs | UPDATE | Yes (MEDIUM) |
| 57 | update_purchase_status | purchase_requests | audit_logs | UPDATE | Yes (LOW) |
| 58 | edit_purchase_details | purchase_requests | purchase_request_items, audit_logs | UPDATE | Yes (MEDIUM) |
| 59 | edit_invoice_amount | invoices | audit_logs, notifications | UPDATE | Yes (HIGH) |
| **CHECKLIST Cluster (4 actions)** |
| 60 | view_checklist | checklists | checklist_items | VIEW | No |
| 61 | mark_checklist_item_complete | checklist_items | audit_logs | UPDATE | Yes (LOW) |
| 62 | add_checklist_note | checklist_notes | audit_logs | CREATE | Yes (LOW) |
| 63 | add_checklist_photo | checklist_attachments | audit_logs | CREATE | Yes (LOW) |
| **SHIPYARD/REFIT Cluster (4 actions)** |
| 64 | view_worklist | worklists | work_items | VIEW | No |
| 65 | add_worklist_task | work_items | audit_logs | CREATE | Yes (MEDIUM) |
| 66 | update_worklist_progress | work_items | audit_logs | UPDATE | Yes (LOW) |
| 67 | export_worklist | worklists | - | EXPORT | Yes (LOW) |

**Note:** * = HIGH severity only if `serial_number` changed, otherwise MEDIUM

---

## Tables by Entity Domain

### Work Orders
| Table | Purpose | Primary Key |
|-------|---------|-------------|
| `work_orders` | Main work order records | id (UUID) |
| `work_order_parts` | Link table: WOs ↔ parts used | id |
| `work_order_notes` | Notes attached to WOs | id |
| `work_order_attachments` | Photos/docs attached to WOs | id |
| `work_order_checklists` | Procedural checklists | id |
| `checklist_items` | Individual checklist items | id |

### Faults
| Table | Purpose | Primary Key |
|-------|---------|-------------|
| `faults` | Fault/alarm records | id |
| `fault_notes` | Notes on faults | id |
| `fault_attachments` | Photos/evidence | id |
| `fault_embeddings` | Vector embeddings for RAG | id |
| `fault_parts_suggestions` | AI part suggestions | id |

### Equipment
| Table | Purpose | Primary Key |
|-------|---------|-------------|
| `equipment` | Equipment registry | id |
| `equipment_parts` | Link table: equipment ↔ compatible parts | id |
| `equipment_notes` | Notes on equipment | id |
| `equipment_history` | Maintenance history timeline | id |

### Parts/Inventory
| Table | Purpose | Primary Key |
|-------|---------|-------------|
| `parts` | Parts catalog/inventory | id |
| `part_orders` | Purchase orders for parts | id |
| `part_usage_log` | Usage history | id |

### Purchases
| Table | Purpose | Primary Key |
|-------|---------|-------------|
| `purchase_requests` | Purchase request headers | id |
| `purchase_request_items` | Line items on PR | id |
| `invoices` | Supplier invoices | id |
| `deliveries` | Delivery tracking | id |

### Handovers
| Table | Purpose | Primary Key |
|-------|---------|-------------|
| `handovers` | Handover reports | id |
| `handover_items` | Items linked to handover | id |
| `handover_sections` | Editable sections | id |
| `handover_documents` | Documents attached | id |
| `handover_insights` | AI insights added | id |

### Documents
| Table | Purpose | Primary Key |
|-------|---------|-------------|
| `documents` | Manuals, PDFs, docs | id |
| `document_sections` | Searchable sections | id |

### Compliance
| Table | Purpose | Primary Key |
|-------|---------|-------------|
| `hours_of_rest` | HOR entries | id |
| `compliance_records` | Compliance status | id |

### Shipyard
| Table | Purpose | Primary Key |
|-------|---------|-------------|
| `worklists` | Shipyard work lists | id |
| `work_items` | Individual yard tasks | id |

### Checklists
| Table | Purpose | Primary Key |
|-------|---------|-------------|
| `checklists` | Operational checklists | id |
| `checklist_items` | Checklist line items | id |
| `checklist_notes` | Notes on items | id |
| `checklist_attachments` | Photos on items | id |

### System
| Table | Purpose | Primary Key |
|-------|---------|-------------|
| `audit_logs` | All audit entries | id |
| `notifications` | Email notifications sent | id |
| `users` | User accounts | id |
| `yachts` | Yacht (tenant) records | id |
| `ai_summaries` | AI-generated content | id |
| `ai_insights` | Predictive insights | id |

---

## Workflow Archetype Distribution

| Archetype | Count | Actions |
|-----------|-------|---------|
| **VIEW** | 29 | show_manual_section, view_fault_history, suggest_parts, view_work_order_history, view_work_order_checklist, view_equipment_details, view_equipment_history, view_equipment_parts, view_linked_faults, view_equipment_manual, scan_equipment_barcode, view_part_stock, view_part_location, view_part_usage, scan_part_barcode, view_linked_equipment, view_document, view_related_documents, view_document_section, view_hours_of_rest, view_compliance_status, track_delivery, view_checklist, view_worklist + 5 more |
| **CREATE** | 10 | create_work_order_from_fault, add_fault_note, add_fault_photo, create_work_order, add_work_order_note, add_work_order_photo, add_equipment_note, order_part, create_purchase_request, upload_invoice, add_checklist_note, add_checklist_photo, add_worklist_task |
| **UPDATE** | 15 | edit_fault_details, mark_work_order_complete, assign_work_order, edit_work_order_details, approve_work_order, edit_equipment_details, log_part_usage, edit_part_quantity, edit_handover_section, regenerate_handover_summary, edit_note, delete_item, update_hours_of_rest, tag_for_survey, add_item_to_purchase, approve_purchase, log_delivery_received, update_purchase_status, edit_purchase_details, edit_invoice_amount, mark_checklist_item_complete, update_worklist_progress |
| **LINKING** | 8 | add_parts_to_work_order, add_to_handover, add_document_to_handover, add_predictive_insight_to_handover |
| **EXPORT** | 4 | export_handover, export_hours_of_rest, export_worklist |
| **RAG** | 1 | diagnose_fault |

---

## Join Tables Summary

| Join Table | Links | Cardinality |
|------------|-------|-------------|
| `work_order_parts` | work_orders ↔ parts | Many-to-Many |
| `equipment_parts` | equipment ↔ parts | Many-to-Many |
| `handover_items` | handovers ↔ (faults, work_orders, equipment, parts) | One-to-Many |
| `handover_documents` | handovers ↔ documents | Many-to-Many |
| `fault_parts_suggestions` | faults ↔ parts (AI suggested) | Many-to-Many |

---

## Audit Requirements Summary

| Audit Level | Action Count | Examples |
|-------------|--------------|----------|
| **HIGH** | 2 | edit_invoice_amount, edit_equipment_details (serial_number) |
| **MEDIUM** | 24 | All CREATE, UPDATE on critical entities |
| **LOW** | 16 | Add notes, photos, handover items |
| **None** | 25 | All VIEW, scan, suggest actions |

---

## Notification Triggers

| Action | Condition | Recipients |
|--------|-----------|------------|
| edit_invoice_amount | >$500 OR >10% change | Management |
| edit_equipment_details | serial_number changed | Management + HOD |
| approve_purchase | >$5,000 total | Management |
| delete_item | any completed WO | HOD |
| mark_work_order_complete | safety-critical WO | Captain |

---

**Last Updated:** 2025-11-21
