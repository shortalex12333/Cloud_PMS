# Equipment Lens v2 - DB Field Classification Reference

**Goal**: Document → Tests → Code → Verify — backend defines actions, signatures, and RLS; no UI authority.

**Lens**: Equipment

**Date**: 2026-01-27

---

## PURPOSE

This document provides the authoritative field classification for all tables written by Equipment Lens actions. Each field is marked as:

- **REQUIRED**: User must provide (form field, mandatory)
- **OPTIONAL**: User may provide (form field, not mandatory)
- **CONTEXT**: Auto-populated from focused entity or extracted entities
- **BACKEND_AUTO**: Set by backend (FK, RLS, timestamps, computed values)

This ensures minimum viable execution while maximizing auto-population efficiency.

---

## TABLE: `pms_equipment`

### Full Column Reference

| Column | Type | Nullable | Classification | Auto-populate From | Notes |
|--------|------|----------|----------------|-------------------|-------|
| `id` | uuid | NOT NULL | BACKEND_AUTO | gen_random_uuid() | PK |
| `yacht_id` | uuid | NOT NULL | BACKEND_AUTO | get_user_yacht_id() | RLS |
| `parent_id` | uuid | YES | OPTIONAL | - | User selects parent |
| `name` | text | NOT NULL | REQUIRED | - | User enters |
| `code` | text | YES | OPTIONAL | - | User enters |
| `description` | text | YES | OPTIONAL | query_text | From search query |
| `location` | text | YES | OPTIONAL | - | User enters |
| `manufacturer` | text | YES | OPTIONAL | - | User enters |
| `model` | text | YES | OPTIONAL | - | User enters |
| `serial_number` | text | YES | OPTIONAL | - | User enters |
| `installed_date` | date | YES | OPTIONAL | - | User selects |
| `criticality` | enum | YES | OPTIONAL | - | User selects, default: medium |
| `system_type` | text | YES | OPTIONAL | - | User selects |
| `status` | text | YES | BACKEND_AUTO | - | Default: operational |
| `attention_flag` | boolean | YES | BACKEND_AUTO | - | Default: false |
| `attention_reason` | text | YES | CONTEXT | query_text | From status context |
| `attention_updated_at` | timestamptz | YES | BACKEND_AUTO | NOW() | On flag change |
| `metadata` | jsonb | YES | BACKEND_AUTO | {} | Session context |
| `created_at` | timestamptz | NOT NULL | BACKEND_AUTO | NOW() | |
| `updated_at` | timestamptz | NOT NULL | BACKEND_AUTO | NOW() | Trigger |
| `updated_by` | uuid | YES | BACKEND_AUTO | auth.uid() | |
| `deleted_at` | timestamptz | YES | BACKEND_AUTO | - | Soft delete |
| `deleted_by` | uuid | YES | BACKEND_AUTO | auth.uid() | |
| `deletion_reason` | text | YES | CONTEXT | - | For decommission |

### Minimum for `update_equipment_status`

| Field | Required | Source |
|-------|----------|--------|
| `equipment_id` | ✅ | CONTEXT (focused or lookup) |
| `status` | ✅ | REQUIRED (user or extracted) |
| `attention_reason` | ⚪ | OPTIONAL (auto from query if status=failed/degraded) |

---

## TABLE: `pms_notes`

### Full Column Reference

| Column | Type | Nullable | Classification | Auto-populate From | Notes |
|--------|------|----------|----------------|-------------------|-------|
| `id` | uuid | NOT NULL | BACKEND_AUTO | gen_random_uuid() | PK |
| `yacht_id` | uuid | NOT NULL | BACKEND_AUTO | get_user_yacht_id() | RLS |
| `equipment_id` | uuid | YES | CONTEXT | focused_equipment | FK |
| `fault_id` | uuid | YES | CONTEXT | - | If from fault |
| `work_order_id` | uuid | YES | CONTEXT | - | If from WO |
| `text` | text | NOT NULL | REQUIRED | query_text (residual) | Note content |
| `note_type` | text | YES | OPTIONAL | - | Default: observation |
| `requires_ack` | boolean | YES | OPTIONAL | - | Default: false |
| `attachments` | jsonb | YES | OPTIONAL | - | Inline refs |
| `metadata` | jsonb | YES | BACKEND_AUTO | {} | Session |
| `created_by` | uuid | NOT NULL | BACKEND_AUTO | auth.uid() | |
| `created_at` | timestamptz | NOT NULL | BACKEND_AUTO | NOW() | |
| `updated_at` | timestamptz | NOT NULL | BACKEND_AUTO | NOW() | |

### Minimum for `add_equipment_note`

| Field | Required | Source |
|-------|----------|--------|
| `equipment_id` | ✅ | CONTEXT (focused equipment) |
| `text` | ✅ | REQUIRED (user input or query residual) |
| `note_type` | ⚪ | OPTIONAL (default: observation) |
| `requires_ack` | ⚪ | OPTIONAL (default: false) |

---

## TABLE: `pms_attachments`

### Full Column Reference

| Column | Type | Nullable | Classification | Auto-populate From | Notes |
|--------|------|----------|----------------|-------------------|-------|
| `id` | uuid | NOT NULL | BACKEND_AUTO | gen_random_uuid() | PK |
| `yacht_id` | uuid | NOT NULL | BACKEND_AUTO | get_user_yacht_id() | RLS |
| `entity_type` | text | NOT NULL | BACKEND_AUTO | 'equipment' | Fixed |
| `entity_id` | uuid | NOT NULL | CONTEXT | focused_equipment | FK |
| `filename` | text | NOT NULL | BACKEND_AUTO | UUID + ext | Generated |
| `original_filename` | text | NOT NULL | BACKEND_AUTO | from upload | |
| `mime_type` | text | NOT NULL | BACKEND_AUTO | detected | |
| `file_size` | bigint | NOT NULL | BACKEND_AUTO | from upload | |
| `storage_path` | text | NOT NULL | BACKEND_AUTO | computed | {yacht}/{entity}/{file} |
| `description` | text | YES | OPTIONAL | query_text | User or auto |
| `tags` | text[] | YES | OPTIONAL | - | User enters |
| `metadata` | jsonb | YES | BACKEND_AUTO | {} | |
| `uploaded_by` | uuid | NOT NULL | BACKEND_AUTO | auth.uid() | |
| `uploaded_at` | timestamptz | NOT NULL | BACKEND_AUTO | NOW() | |
| `created_at` | timestamptz | NOT NULL | BACKEND_AUTO | NOW() | |

### Minimum for `attach_file_to_equipment`

| Field | Required | Source |
|-------|----------|--------|
| `equipment_id` (entity_id) | ✅ | CONTEXT (focused equipment) |
| `file` | ✅ | REQUIRED (user upload) |
| `description` | ⚪ | OPTIONAL (auto from query) |
| `tags` | ⚪ | OPTIONAL |

---

## TABLE: `pms_work_orders`

### Full Column Reference (relevant fields)

| Column | Type | Nullable | Classification | Auto-populate From | Notes |
|--------|------|----------|----------------|-------------------|-------|
| `id` | uuid | NOT NULL | BACKEND_AUTO | gen_random_uuid() | PK |
| `yacht_id` | uuid | NOT NULL | BACKEND_AUTO | get_user_yacht_id() | RLS |
| `wo_number` | text | NOT NULL | BACKEND_AUTO | computed | WO-YYYY-NNNN |
| `equipment_id` | uuid | YES | CONTEXT | focused_equipment | FK |
| `title` | text | NOT NULL | REQUIRED | query_text | |
| `description` | text | YES | OPTIONAL | query_text | Expanded |
| `type` | text | NOT NULL | REQUIRED | - | User selects |
| `priority` | text | NOT NULL | REQUIRED | - | User selects |
| `status` | text | NOT NULL | BACKEND_AUTO | 'draft' | Default |
| `assigned_to` | uuid | YES | OPTIONAL | - | User selects |
| `due_date` | date | YES | OPTIONAL | - | User selects |
| `created_by` | uuid | NOT NULL | BACKEND_AUTO | auth.uid() | |
| `created_at` | timestamptz | NOT NULL | BACKEND_AUTO | NOW() | |
| `updated_at` | timestamptz | NOT NULL | BACKEND_AUTO | NOW() | |

### Minimum for `create_work_order_for_equipment`

| Field | Required | Source |
|-------|----------|--------|
| `equipment_id` | ✅ | CONTEXT (focused equipment) |
| `title` | ✅ | REQUIRED (auto from query) |
| `type` | ✅ | REQUIRED (user selects: scheduled/corrective/breakdown/preventive) |
| `priority` | ✅ | REQUIRED (user selects: routine/important/critical/emergency) |
| `description` | ⚪ | OPTIONAL (auto from query) |
| `assigned_to` | ⚪ | OPTIONAL |
| `due_date` | ⚪ | OPTIONAL |
| `fault_severity` | CONDITIONAL | Required if type=corrective/breakdown |

---

## TABLE: `pms_faults` (auto-created from WO)

### Full Column Reference (relevant fields)

| Column | Type | Nullable | Classification | Auto-populate From | Notes |
|--------|------|----------|----------------|-------------------|-------|
| `id` | uuid | NOT NULL | BACKEND_AUTO | gen_random_uuid() | PK |
| `yacht_id` | uuid | NOT NULL | BACKEND_AUTO | get_user_yacht_id() | RLS |
| `fault_code` | text | NOT NULL | BACKEND_AUTO | computed | FLT-YYYY-NNNN |
| `equipment_id` | uuid | YES | CONTEXT | from WO | FK |
| `work_order_id` | uuid | YES | CONTEXT | created WO | FK |
| `title` | text | NOT NULL | CONTEXT | from WO title | |
| `severity` | text | NOT NULL | REQUIRED | fault_severity field | |
| `status` | text | NOT NULL | BACKEND_AUTO | 'open' | Default |
| `detected_at` | timestamptz | NOT NULL | BACKEND_AUTO | NOW() | |
| `detected_by` | uuid | NOT NULL | BACKEND_AUTO | auth.uid() | |
| `created_at` | timestamptz | NOT NULL | BACKEND_AUTO | NOW() | |

---

## TABLE: `pms_equipment_parts_bom`

### Full Column Reference

| Column | Type | Nullable | Classification | Auto-populate From | Notes |
|--------|------|----------|----------------|-------------------|-------|
| `id` | uuid | NOT NULL | BACKEND_AUTO | gen_random_uuid() | PK |
| `yacht_id` | uuid | NOT NULL | BACKEND_AUTO | get_user_yacht_id() | RLS |
| `equipment_id` | uuid | NOT NULL | CONTEXT | focused_equipment | FK |
| `part_id` | uuid | NOT NULL | REQUIRED | part_lookup | FK, user selects |
| `quantity_required` | integer | YES | OPTIONAL | - | Default: 1 |
| `notes` | text | YES | OPTIONAL | - | |
| `created_at` | timestamptz | NOT NULL | BACKEND_AUTO | NOW() | |

### Minimum for `link_part_to_equipment`

| Field | Required | Source |
|-------|----------|--------|
| `equipment_id` | ✅ | CONTEXT (focused equipment) |
| `part_id` | ✅ | REQUIRED (user searches/selects part) |
| `quantity_required` | ⚪ | OPTIONAL (default: 1) |
| `notes` | ⚪ | OPTIONAL |

---

## TABLE: `pms_audit_log`

### Full Column Reference

| Column | Type | Nullable | Classification | Auto-populate From | Notes |
|--------|------|----------|----------------|-------------------|-------|
| `id` | uuid | NOT NULL | BACKEND_AUTO | gen_random_uuid() | PK |
| `yacht_id` | uuid | NOT NULL | BACKEND_AUTO | get_user_yacht_id() | RLS |
| `entity_type` | text | NOT NULL | BACKEND_AUTO | 'equipment' | Fixed per lens |
| `entity_id` | uuid | NOT NULL | BACKEND_AUTO | from action | |
| `action` | text | NOT NULL | BACKEND_AUTO | action_id | |
| `actor_user_id` | uuid | YES | BACKEND_AUTO | auth.uid() | NO FK to MASTER |
| `actor_role` | text | YES | BACKEND_AUTO | get_user_role() | |
| `old_values` | jsonb | YES | BACKEND_AUTO | from record | |
| `new_values` | jsonb | YES | BACKEND_AUTO | from payload | |
| `signature` | jsonb | NOT NULL | BACKEND_AUTO | {} or JSON | **NEVER NULL** |
| `payload_snapshot` | jsonb | YES | BACKEND_AUTO | minimal context | |
| `created_at` | timestamptz | NOT NULL | BACKEND_AUTO | NOW() | |

### Signature Rule

| Action Type | Signature Value |
|-------------|-----------------|
| Non-signed (most) | `'{}'::jsonb` |
| Signed (decommission) | Full signature JSON payload |

**Invariant**: `signature` is NEVER NULL.

---

## TABLE: `pms_notifications`

### Full Column Reference

| Column | Type | Nullable | Classification | Auto-populate From | Notes |
|--------|------|----------|----------------|-------------------|-------|
| `id` | uuid | NOT NULL | BACKEND_AUTO | gen_random_uuid() | PK |
| `yacht_id` | uuid | NOT NULL | BACKEND_AUTO | get_user_yacht_id() | RLS |
| `user_id` | uuid | NOT NULL | BACKEND_AUTO | role_lookup | NO FK to MASTER |
| `topic` | text | NOT NULL | BACKEND_AUTO | from trigger | |
| `source` | text | NOT NULL | BACKEND_AUTO | 'equipment' | |
| `source_id` | uuid | NOT NULL | BACKEND_AUTO | equipment_id | |
| `title` | text | NOT NULL | BACKEND_AUTO | computed | |
| `body` | text | YES | BACKEND_AUTO | computed | |
| `level` | text | NOT NULL | BACKEND_AUTO | from trigger | info/warning/critical |
| `cta_action_id` | text | YES | BACKEND_AUTO | from trigger | |
| `cta_payload` | jsonb | YES | BACKEND_AUTO | from context | |
| `status` | text | NOT NULL | BACKEND_AUTO | 'pending' | |
| `send_after` | timestamptz | NOT NULL | BACKEND_AUTO | NOW() | |
| `sent_at` | timestamptz | YES | BACKEND_AUTO | - | |
| `read_at` | timestamptz | YES | BACKEND_AUTO | - | User action |
| `dismissed_at` | timestamptz | YES | BACKEND_AUTO | - | User action |
| `created_at` | timestamptz | NOT NULL | BACKEND_AUTO | NOW() | |
| `updated_at` | timestamptz | NOT NULL | BACKEND_AUTO | NOW() | |

**Note**: Notifications are entirely BACKEND_AUTO. User only interacts via mark read/dismissed.

---

## SUMMARY: MINIMUM FIELDS PER ACTION

| Action | Minimum to Execute | Auto-populated |
|--------|-------------------|----------------|
| `update_equipment_status` | equipment_id, status | yacht_id, attention_*, updated_* |
| `add_equipment_note` | equipment_id, text | yacht_id, note_type, created_* |
| `attach_file_to_equipment` | equipment_id, file | yacht_id, filename, path, uploaded_* |
| `create_work_order_for_equipment` | equipment_id, title, type, priority | yacht_id, wo_number, status, created_* |
| `link_part_to_equipment` | equipment_id, part_id | yacht_id, quantity, created_at |
| `flag_equipment_attention` | equipment_id, attention_flag | yacht_id, attention_*, updated_* |
| `decommission_equipment` | equipment_id, reason, signature | yacht_id, status, deleted_* |

---

## FIELD AUTO-POPULATION SOURCES

| Source | Description | Example Fields |
|--------|-------------|----------------|
| `auth_context` | From JWT/session | yacht_id, user_id, role |
| `focused_equipment` | Currently focused entity | equipment_id |
| `equipment` entity | Extracted from query | equipment_id (via lookup) |
| `status` entity | Extracted from query | status |
| `query_text` | Original user query | title, description, attention_reason |
| `part` entity | Extracted from query | part_id (via lookup) |
| `gen_random_uuid()` | PostgreSQL function | id columns |
| `NOW()` | PostgreSQL function | timestamp columns |
| `computed` | Business logic | wo_number, fault_code, storage_path |

---

**END OF DB FIELD CLASSIFICATION REFERENCE**
