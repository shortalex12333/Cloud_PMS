# E002: TENANT DB REALITY

**Date:** 2026-01-21
**Phase:** 7 - System Reality Extraction
**Status:** COMPLETE

---

## Summary

Complete inventory of tables in TENANT database (vzsohavtuotocgrfkfyd) with columns, row counts, and presence confirmation.

**Key Finding:** All critical PMS tables exist. Some tables referenced in code handlers do NOT exist in the database.

---

## Tables Found: 22

### PMS Core Tables (8)

| Table | Rows | Columns |
|-------|------|---------|
| pms_equipment | 534 | id, yacht_id, parent_id, name, code, description, location, manufacturer, model, serial_number, installed_date, criticality, system_type, metadata, created_at, updated_at, attention_flag, attention_reason, attention_updated_at, updated_by, deleted_at, deleted_by, deletion_reason, status |
| pms_faults | 1575 | id, yacht_id, equipment_id, fault_code, title, description, severity, detected_at, resolved_at, resolved_by, work_order_id, metadata, created_at, updated_by, updated_at, deleted_at, deleted_by, deletion_reason, status |
| pms_work_orders | 2703 | id, yacht_id, equipment_id, title, description, type, priority, status, due_date, due_hours, last_completed_date, last_completed_hours, frequency, created_by, updated_by, metadata, created_at, updated_at, wo_number, deleted_at, deleted_by, deletion_reason, work_order_type, fault_id, assigned_to, completed_by, completed_at, completion_notes, vendor_contact_hash |
| pms_notes | 5 | id, yacht_id, equipment_id, work_order_id, fault_id, text, note_type, created_by, attachments, metadata, created_at, updated_at |
| pms_work_order_notes | 2631 | id, work_order_id, note_text, note_type, created_by, created_at, metadata |
| pms_parts | 532 | id, yacht_id, name, part_number, manufacturer, description, category, model_compatibility, metadata, created_at, updated_at, search_embedding, embedding_text, quantity_on_hand, minimum_quantity, unit, location, last_counted_at, last_counted_by |
| pms_audit_log | 109 | id, yacht_id, action, entity_type, entity_id, user_id, signature, old_values, new_values, created_at, metadata |
| pms_shopping_list_items | 35 | id, yacht_id, part_id, part_name, part_number, manufacturer, is_candidate_part, quantity_requested, quantity_approved, quantity_ordered, quantity_received, quantity_installed, unit, preferred_supplier, estimated_unit_price, status, source_type, source_work_order_id, source_receiving_id, source_notes, order_id, order_line_number, approved_by, approved_at, approval_notes, rejected_by, rejected_at, rejection_reason, fulfilled_at, installed_at, installed_to_equipment_id, urgency, required_by_date, created_by, created_at, updated_by, updated_at, deleted_at, deleted_by, deletion_reason, metadata, rejection_notes, candidate_promoted_to_part_id, promoted_by, promoted_at |

### Checklist Tables (2)

| Table | Rows | Columns |
|-------|------|---------|
| pms_checklists | 5 | id, yacht_id, name, description, checklist_type, ... |
| pms_checklist_items | 29 | id, yacht_id, checklist_id, description, instructions, ... |

### Auth/User Tables (3)

| Table | Rows | Columns |
|-------|------|---------|
| auth_users_profiles | 1 | id, yacht_id, email, name, is_active, metadata, created_at, updated_at |
| auth_users_roles | 1 | id, user_id, yacht_id, role, assigned_at, assigned_by, is_active, valid_from, valid_until |
| yacht_registry | 1 | id, name, imo, mmsi, flag_state, length_m, owner_ref, yacht_secret_hash, nas_root_path, status, metadata, created_at, updated_at |

### Document Tables (2)

| Table | Rows | Columns |
|-------|------|---------|
| documents | 2760 | id, yacht_id, filename, storage_path, mime_type, size_bytes, ... (21 total) |
| equipment | 534 | id, yacht_id, name, code, ... (10 total) - Note: Duplicate of pms_equipment? |

### Handover Tables (2)

| Table | Rows | Columns |
|-------|------|---------|
| handovers | 3 | id, yacht_id, ... (22 columns) |
| handover_items | 5 | id, yacht_id, ... (20 columns) |

### Email Tables (3)

| Table | Rows | Columns |
|-------|------|---------|
| email_threads | 1 | id, yacht_id, ... (17 columns) |
| email_messages | 2 | id, thread_id, ... (23 columns) |
| email_watchers | 1 | id, yacht_id, ... (21 columns) |

### Other Tables (2)

| Table | Rows | Columns |
|-------|------|---------|
| procurement_intents | 0 | (empty) |
| email_link_decisions | 0 | (empty) |

---

## Key Tables Status

| Table | Status | Required By |
|-------|--------|-------------|
| pms_equipment | EXISTS | Equipment actions |
| pms_work_orders | EXISTS | Work order actions |
| pms_faults | EXISTS | Fault actions |
| pms_notes | EXISTS | Note actions |
| documents | EXISTS | Document actions |
| pms_audit_log | EXISTS | Audit logging |
| email_threads | EXISTS | Email watcher |

---

## Tables NOT FOUND (Referenced in Code)

| Table | Referenced In | Impact |
|-------|---------------|--------|
| notes | internal_dispatcher.py:110 (add_note handler) | Handler will fail with FK error |
| attachments | internal_dispatcher.py:725 | Handler will fail |
| worklist_tasks | internal_dispatcher.py:1390 | Handler will fail |
| checklist_items | internal_dispatcher.py:1358 | Handler will fail |
| work_order_parts | internal_dispatcher.py:1168 | Handler will fail |
| vendors | migration files | Not critical - empty tables exist |

**Impact:** Actions that use these non-existent tables will fail at runtime with PostgreSQL errors.

---

## SQL Queries Used

### Query 1: Table existence check
```sql
-- Via Supabase PostgREST
SELECT * FROM {table_name} LIMIT 1;
-- Returns PGRST205 error if table doesn't exist
```

### Query 2: Row count
```sql
SELECT * FROM {table_name} LIMIT 0;
-- With count='exact' header returns row count
```

### Query 3: Column discovery
```sql
-- Inferred from first row keys
SELECT * FROM {table_name} LIMIT 1;
-- Column names from JSON response keys
```

---

## RLS Status

**Note:** RLS status cannot be directly queried via PostgREST with service_role key. The service_role key bypasses RLS by default.

Based on code analysis (yacht_validator.py), RLS is expected on:
- All pms_* tables (yacht_id filter)
- documents (yacht_id filter)
- handovers, handover_items (yacht_id filter)

---

## Observations

1. **Duplicate Equipment Table:** Both `pms_equipment` (534 rows) and `equipment` (534 rows) exist. Likely a legacy/migration artifact.

2. **Missing Tables:** Several tables referenced in code don't exist in production:
   - `notes` (but `pms_notes` exists)
   - `attachments`
   - `worklist_tasks`
   - `checklist_items` (but `pms_checklist_items` exists)

3. **Audit Log Volume:** Only 109 rows in pms_audit_log suggests audit logging is not comprehensively active.

4. **Test Data Present:** Single user, single yacht - this is a test/development tenant.

---

## Evidence Files

| File | Description |
|------|-------------|
| `phase7_step2_output.json` | Full table probe results |

---

**Document:** E002_TENANT_DB_TRUTH.md
**Completed:** 2026-01-21
