# Equipment Lens v2 - PHASE 4: ACTIONS

**Goal**: Document → Tests → Code → Verify — backend defines actions, signatures, and RLS; no UI authority.

**Lens**: Equipment

**Date**: 2026-01-27

---

## PURPOSE

Phase 4 defines all Equipment Lens actions with complete specifications:
- Field classifications
- Registry entries
- Gating rules
- Storage configuration

---

## ACTION OVERVIEW

| # | Action ID | Variant | Tables Written | Signed |
|---|-----------|---------|----------------|--------|
| 1 | `update_equipment_status` | MUTATE | pms_equipment, pms_audit_log | NO |
| 2 | `add_equipment_note` | MUTATE | pms_notes, pms_audit_log | NO |
| 3 | `attach_file_to_equipment` | MUTATE | pms_attachments, pms_audit_log, storage.objects | NO |
| 4 | `create_work_order_for_equipment` | MUTATE | pms_work_orders, (pms_faults), pms_audit_log | NO |
| 5 | `link_part_to_equipment` | MUTATE | pms_equipment_parts_bom, pms_audit_log | NO |
| 6 | `flag_equipment_attention` | MUTATE | pms_equipment, pms_audit_log | NO |
| 7 | `decommission_equipment` | SIGNED | pms_equipment, pms_audit_log | **YES** |

---

## ACTION 1: `update_equipment_status`

### Purpose
Change equipment operational status (operational, degraded, failed, maintenance).

### Allowed Roles
```python
["engineer", "eto", "chief_engineer", "chief_officer", "captain", "manager"]
```

### Field Classification

| Field | Table.Column | Classification | Source |
|-------|--------------|----------------|--------|
| `equipment_id` | pms_equipment.id | CONTEXT | From focused equipment |
| `status` | pms_equipment.status | REQUIRED | User dropdown |
| `attention_reason` | pms_equipment.attention_reason | OPTIONAL | User text if status=failed/degraded |
| `clear_attention` | (form flag) | OPTIONAL | Checkbox if status=operational |
| `attention_flag` | pms_equipment.attention_flag | BACKEND_AUTO | Derived from status |
| `attention_updated_at` | pms_equipment.attention_updated_at | BACKEND_AUTO | NOW() if flag changes |
| `updated_at` | pms_equipment.updated_at | BACKEND_AUTO | NOW() |
| `updated_by` | pms_equipment.updated_by | BACKEND_AUTO | auth.uid() |

### Business Rules

1. Status `failed` or `degraded` → automatically sets `attention_flag = true`
2. Status `operational` with `clear_attention = true` → clears `attention_flag`
3. Status `decommissioned` → blocked (use decommission_equipment action instead)
4. Cannot change status if current status is `decommissioned` (terminal)

### Registry Entry

```python
"update_equipment_status": ActionDefinition(
    action_id="update_equipment_status",
    label="Update Status",
    endpoint="/v1/equipment/update-status",
    handler_type=HandlerType.INTERNAL,
    method="POST",
    allowed_roles=["engineer", "eto", "chief_engineer", "chief_officer", "captain", "manager"],
    required_fields=["equipment_id", "status"],
    optional_fields=["attention_reason", "clear_attention"],
    domain="equipment",
    variant=ActionVariant.MUTATE,
    search_keywords=["status", "update", "mark", "change", "failed", "operational", "degraded", "maintenance"],
),
```

### Gating

| Type | Confirmation Required |
|------|----------------------|
| STATE_CHANGING | YES if status=failed/degraded |

### Request Contract

```json
{
  "action": "update_equipment_status",
  "context": {
    "yacht_id": "uuid",
    "equipment_id": "uuid"
  },
  "payload": {
    "status": "failed",
    "attention_reason": "Alternator bearing failure - oil leak detected"
  }
}
```

### Response Contract

```json
{
  "success": true,
  "data": {
    "equipment_id": "uuid",
    "old_status": "operational",
    "new_status": "failed",
    "attention_flag": true,
    "attention_reason": "Alternator bearing failure - oil leak detected"
  },
  "audit_id": "uuid"
}
```

### Ledger Entry

```json
{
  "entity_type": "equipment",
  "entity_id": "equipment_uuid",
  "action": "update_equipment_status",
  "old_values": {
    "status": "operational",
    "attention_flag": false
  },
  "new_values": {
    "status": "failed",
    "attention_flag": true,
    "attention_reason": "Alternator bearing failure"
  },
  "signature": {}
}
```

### Notification Trigger

If `new_status = 'failed'` AND `criticality IN ('high', 'critical')`:
- Create notification for `chief_engineer`
- Level: `critical` if criticality=critical, else `warning`
- Topic: `equipment_critical_failure` or `equipment_failure`

---

## ACTION 2: `add_equipment_note`

### Purpose
Add observation, handover, or inspection note to equipment record.

### Allowed Roles
```python
["deckhand", "steward", "chef", "engineer", "eto", "chief_engineer",
 "chief_officer", "chief_steward", "purser", "captain", "manager"]
```
*(All crew can add notes)*

### Field Classification

| Field | Table.Column | Classification | Source |
|-------|--------------|----------------|--------|
| `id` | pms_notes.id | BACKEND_AUTO | gen_random_uuid() |
| `yacht_id` | pms_notes.yacht_id | BACKEND_AUTO | public.get_user_yacht_id() |
| `equipment_id` | pms_notes.equipment_id | CONTEXT | From focused equipment |
| `text` | pms_notes.text | REQUIRED | User text input |
| `note_type` | pms_notes.note_type | OPTIONAL | User dropdown, default: 'observation' |
| `requires_ack` | pms_notes.requires_ack | OPTIONAL | Checkbox, default: false |
| `metadata` | pms_notes.metadata | BACKEND_AUTO | Session context |
| `created_by` | pms_notes.created_by | BACKEND_AUTO | auth.uid() |
| `created_at` | pms_notes.created_at | BACKEND_AUTO | NOW() |

### Note Types

| Type | When to Use |
|------|-------------|
| `observation` | General observation (default) |
| `handover` | Shift handover information |
| `inspection` | Scheduled inspection note |
| `maintenance` | Maintenance activity record |
| `issue` | Problem report |

### Registry Entry

```python
"add_equipment_note": ActionDefinition(
    action_id="add_equipment_note",
    label="Add Note",
    endpoint="/v1/equipment/add-note",
    handler_type=HandlerType.INTERNAL,
    method="POST",
    allowed_roles=["deckhand", "steward", "chef", "engineer", "eto", "chief_engineer",
                   "chief_officer", "chief_steward", "purser", "captain", "manager"],
    required_fields=["equipment_id", "text"],
    optional_fields=["note_type", "requires_ack"],
    domain="equipment",
    variant=ActionVariant.MUTATE,
    search_keywords=["note", "log", "record", "observation", "comment"],
),
```

### Gating

| Type | Confirmation Required |
|------|----------------------|
| STATE_CHANGING | NO |

### Notification Trigger

If `requires_ack = true`:
- Create notification for `chief_engineer`
- Level: `info`
- Topic: `equipment_note_requires_ack`
- CTA: Navigate to equipment + note

---

## ACTION 3: `attach_file_to_equipment`

### Purpose
Upload photo or document to equipment record.

### Allowed Roles
```python
["deckhand", "steward", "chef", "engineer", "eto", "chief_engineer",
 "chief_officer", "chief_steward", "purser", "captain", "manager"]
```
*(All crew can attach files)*

### Field Classification

| Field | Table.Column | Classification | Source |
|-------|--------------|----------------|--------|
| `id` | pms_attachments.id | BACKEND_AUTO | gen_random_uuid() |
| `yacht_id` | pms_attachments.yacht_id | BACKEND_AUTO | public.get_user_yacht_id() |
| `entity_type` | pms_attachments.entity_type | BACKEND_AUTO | 'equipment' |
| `entity_id` | pms_attachments.entity_id | CONTEXT | From focused equipment |
| `file` | (upload) | REQUIRED | User file selection |
| `filename` | pms_attachments.filename | BACKEND_AUTO | UUID-based |
| `original_filename` | pms_attachments.original_filename | BACKEND_AUTO | From upload |
| `mime_type` | pms_attachments.mime_type | BACKEND_AUTO | Detected |
| `file_size` | pms_attachments.file_size | BACKEND_AUTO | From upload |
| `storage_path` | pms_attachments.storage_path | BACKEND_AUTO | Computed path |
| `description` | pms_attachments.description | OPTIONAL | User text |
| `tags` | pms_attachments.tags | OPTIONAL | User tags |
| `uploaded_by` | pms_attachments.uploaded_by | BACKEND_AUTO | auth.uid() |
| `uploaded_at` | pms_attachments.uploaded_at | BACKEND_AUTO | NOW() |

### Storage Configuration

```python
ACTION_STORAGE_CONFIG["attach_file_to_equipment"] = {
    "bucket": "documents",
    "path_template": "{yacht_id}/equipment/{equipment_id}/{filename}",
    "writable_prefixes": ["{yacht_id}/equipment/"],
    "confirmation_required": True,
    "max_file_size_mb": 25,
    "allowed_mime_types": [
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "video/mp4",
        "video/quicktime",
        "application/pdf"
    ],
}
```

### Registry Entry

```python
"attach_file_to_equipment": ActionDefinition(
    action_id="attach_file_to_equipment",
    label="Attach Photo/Document",
    endpoint="/v1/equipment/attach-file",
    handler_type=HandlerType.INTERNAL,
    method="POST",
    allowed_roles=["deckhand", "steward", "chef", "engineer", "eto", "chief_engineer",
                   "chief_officer", "chief_steward", "purser", "captain", "manager"],
    required_fields=["equipment_id", "file"],
    optional_fields=["description", "tags"],
    domain="equipment",
    variant=ActionVariant.MUTATE,
    search_keywords=["photo", "picture", "upload", "attach", "document", "image", "file"],
),
```

### Gating

| Type | Confirmation Required |
|------|----------------------|
| STATE_CHANGING | YES (show path preview) |

---

## ACTION 4: `create_work_order_for_equipment`

### Purpose
Create a new work order for equipment maintenance/repair. This is an **escape hatch** to Work Order Lens.

### Allowed Roles
```python
["engineer", "eto", "chief_engineer", "chief_officer", "captain", "manager"]
```

### Field Classification

| Field | Table.Column | Classification | Source |
|-------|--------------|----------------|--------|
| `equipment_id` | pms_work_orders.equipment_id | CONTEXT | From focused equipment |
| `title` | pms_work_orders.title | REQUIRED | User text |
| `description` | pms_work_orders.description | OPTIONAL | User text |
| `type` | pms_work_orders.type | REQUIRED | User dropdown |
| `priority` | pms_work_orders.priority | REQUIRED | User dropdown |
| `assigned_to` | pms_work_orders.assigned_to | OPTIONAL | User dropdown |
| `due_date` | pms_work_orders.due_date | OPTIONAL | User date picker |
| `fault_severity` | (form field for fault) | CONDITIONAL | Required if type=corrective/breakdown |

### Work Order Types

| Type | Fault Created | Use Case |
|------|---------------|----------|
| `scheduled` | NO | Planned maintenance |
| `preventive` | NO | Routine preventive work |
| `corrective` | **YES** | Fixing discovered issue |
| `breakdown` | **YES** | Emergency repair |
| `unplanned` | NO | Ad-hoc non-fault work |

### WO-First Doctrine

When type is `corrective` or `breakdown`:
1. Work order is created first
2. Fault is auto-created with provided severity
3. Fault is linked to WO via `work_order_id`
4. User provides `fault_severity` (not derived from WO priority)

### Registry Entry

```python
"create_work_order_for_equipment": ActionDefinition(
    action_id="create_work_order_for_equipment",
    label="Create Work Order",
    endpoint="/v1/equipment/create-work-order",
    handler_type=HandlerType.INTERNAL,
    method="POST",
    allowed_roles=["engineer", "eto", "chief_engineer", "chief_officer", "captain", "manager"],
    required_fields=["equipment_id", "title", "type", "priority"],
    optional_fields=["description", "assigned_to", "due_date", "fault_severity"],
    domain="equipment",
    variant=ActionVariant.MUTATE,
    search_keywords=["work order", "job", "task", "maintenance", "repair", "wo", "fix"],
),
```

### Gating

| Type | Confirmation Required |
|------|----------------------|
| STATE_CHANGING | YES |

### Escape Behavior

After WO creation:
- Return WO ID in response
- UI offers navigation to WO Lens
- Equipment breadcrumb maintained

---

## ACTION 5: `link_part_to_equipment`

### Purpose
Add a part to equipment's Bill of Materials (BOM).

### Allowed Roles
```python
["engineer", "eto", "chief_engineer", "captain", "manager"]
```

### Field Classification

| Field | Table.Column | Classification | Source |
|-------|--------------|----------------|--------|
| `id` | pms_equipment_parts_bom.id | BACKEND_AUTO | gen_random_uuid() |
| `yacht_id` | pms_equipment_parts_bom.yacht_id | BACKEND_AUTO | public.get_user_yacht_id() |
| `equipment_id` | pms_equipment_parts_bom.equipment_id | CONTEXT | From focused equipment |
| `part_id` | pms_equipment_parts_bom.part_id | REQUIRED | User selection (Part search) |
| `quantity_required` | pms_equipment_parts_bom.quantity_required | OPTIONAL | User number, default: 1 |
| `notes` | pms_equipment_parts_bom.notes | OPTIONAL | User text |
| `created_at` | pms_equipment_parts_bom.created_at | BACKEND_AUTO | NOW() |

### Registry Entry

```python
"link_part_to_equipment": ActionDefinition(
    action_id="link_part_to_equipment",
    label="Link Part to BOM",
    endpoint="/v1/equipment/link-part",
    handler_type=HandlerType.INTERNAL,
    method="POST",
    allowed_roles=["engineer", "eto", "chief_engineer", "captain", "manager"],
    required_fields=["equipment_id", "part_id"],
    optional_fields=["quantity_required", "notes"],
    domain="equipment",
    variant=ActionVariant.MUTATE,
    search_keywords=["part", "bom", "link", "add part", "spare"],
),
```

### Duplicate Handling

If `(equipment_id, part_id)` already exists:
- Return 409 Conflict
- Message: "Part already linked to this equipment"

---

## ACTION 6: `flag_equipment_attention`

### Purpose
Manually set or clear the attention flag with reason.

### Allowed Roles
```python
["engineer", "eto", "chief_engineer", "chief_officer", "captain", "manager"]
```

### Field Classification

| Field | Table.Column | Classification | Source |
|-------|--------------|----------------|--------|
| `equipment_id` | pms_equipment.id | CONTEXT | From focused equipment |
| `attention_flag` | pms_equipment.attention_flag | REQUIRED | User toggle |
| `attention_reason` | pms_equipment.attention_reason | CONDITIONAL | Required if setting true |
| `attention_updated_at` | pms_equipment.attention_updated_at | BACKEND_AUTO | NOW() |
| `updated_at` | pms_equipment.updated_at | BACKEND_AUTO | NOW() |
| `updated_by` | pms_equipment.updated_by | BACKEND_AUTO | auth.uid() |

### Registry Entry

```python
"flag_equipment_attention": ActionDefinition(
    action_id="flag_equipment_attention",
    label="Flag/Clear Attention",
    endpoint="/v1/equipment/flag-attention",
    handler_type=HandlerType.INTERNAL,
    method="POST",
    allowed_roles=["engineer", "eto", "chief_engineer", "chief_officer", "captain", "manager"],
    required_fields=["equipment_id", "attention_flag"],
    optional_fields=["attention_reason"],
    domain="equipment",
    variant=ActionVariant.MUTATE,
    search_keywords=["attention", "flag", "highlight", "mark", "urgent"],
),
```

---

## ACTION 7: `decommission_equipment` (SIGNED)

### Purpose
Permanently remove equipment from active service. This is a **terminal state** that cannot be reversed.

### Allowed Roles
```python
["captain", "manager"]  # Requires signature
```

### Field Classification

| Field | Table.Column | Classification | Source |
|-------|--------------|----------------|--------|
| `equipment_id` | pms_equipment.id | CONTEXT | From focused equipment |
| `reason` | pms_equipment.deletion_reason | REQUIRED | User text |
| `replacement_equipment_id` | (audit field) | OPTIONAL | User selection |
| `signature` | pms_audit_log.signature | REQUIRED | User signature payload |
| `status` | pms_equipment.status | BACKEND_AUTO | 'decommissioned' |
| `deleted_at` | pms_equipment.deleted_at | BACKEND_AUTO | NOW() |
| `deleted_by` | pms_equipment.deleted_by | BACKEND_AUTO | auth.uid() |

### Signature Payload Schema

```json
{
  "user_id": "uuid",
  "role_at_signing": "captain|manager",
  "signature_type": "decommission_equipment",
  "reason": "string",
  "equipment_id": "uuid",
  "replacement_equipment_id": "uuid|null",
  "signature_hash": "sha256:base64...",
  "signed_at": "2026-01-27T14:00:00Z"
}
```

### Registry Entry

```python
"decommission_equipment": ActionDefinition(
    action_id="decommission_equipment",
    label="Decommission Equipment",
    endpoint="/v1/equipment/decommission",
    handler_type=HandlerType.INTERNAL,
    method="POST",
    allowed_roles=["captain", "manager"],
    required_fields=["equipment_id", "reason", "signature"],
    optional_fields=["replacement_equipment_id"],
    domain="equipment",
    variant=ActionVariant.SIGNED,
    search_keywords=["decommission", "remove", "retire", "dispose", "scrap"],
),
```

### Gating

| Type | Confirmation Required |
|------|----------------------|
| **GATED** | ALWAYS + signature modal |

### Pre-conditions

1. Equipment must exist and not be already decommissioned
2. User must have captain or manager role
3. Signature payload must be complete and valid

### Post-conditions

1. Equipment status = 'decommissioned'
2. Equipment remains in database (soft delete)
3. All future queries can filter: `WHERE status != 'decommissioned'`
4. Historical queries include it
5. Audit log contains FULL signature JSON (not empty {})

### Terminal State Enforcement

Any attempt to change status from 'decommissioned':
- Return 400 Bad Request
- Message: "Cannot change status from 'decommissioned'. This is a terminal state."

---

## ACTION GATING SUMMARY

| Action | Gating Class | Confirmation | Signature |
|--------|--------------|--------------|-----------|
| `update_equipment_status` | STATE_CHANGING | If status=failed/degraded | NO |
| `add_equipment_note` | STATE_CHANGING | NO | NO |
| `attach_file_to_equipment` | STATE_CHANGING | YES (path preview) | NO |
| `create_work_order_for_equipment` | STATE_CHANGING | YES | NO |
| `link_part_to_equipment` | STATE_CHANGING | NO | NO |
| `flag_equipment_attention` | STATE_CHANGING | NO | NO |
| `decommission_equipment` | **GATED** | ALWAYS | **YES** |

---

## NEXT PHASE

Proceed to **PHASE 5: SCENARIOS** to:
- Define complete user journey scenarios
- Include success and failure paths
- Document expected HTTP responses
- Specify notification triggers

---

**END OF PHASE 4**
