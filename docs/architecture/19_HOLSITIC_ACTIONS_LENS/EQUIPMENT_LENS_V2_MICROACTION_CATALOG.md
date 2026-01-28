# Equipment Lens v2 - Microaction Catalog

**Purpose**: Holistic view of all Equipment Lens v2 microactions with triggers, validation rules, side effects, and workflow context.

**Total Actions**: 17 (3 new in v2, 14 existing)

---

## Microaction Information Template

For each microaction, we capture:

| Dimension | Description |
|-----------|-------------|
| **Identification** | action_id, label, variant (READ/MUTATE/SIGNED) |
| **Access Control** | allowed_roles, authentication requirements |
| **Interface** | endpoint, method, required_fields, optional_fields |
| **Triggers** | User scenarios: When/why would this action be used? |
| **Preconditions** | State requirements before action can execute |
| **Validation Rules** | Business logic constraints and checks |
| **Side Effects** | Database writes, state transitions, related entity updates |
| **Related Actions** | Workflow context (what comes before/after) |
| **Success States** | What success looks like (200 response, state changes) |
| **Error States** | Common failure modes (400/403/404/409/500) |
| **UI Surfacing** | Where in UI users see/trigger this action |
| **Examples** | Sample request/response payloads |

---

## NEW Equipment Lens v2 Actions (3)

### 1. set_equipment_status

**Identification**
- **action_id**: `set_equipment_status`
- **label**: "Set Equipment Status"
- **variant**: MUTATE

**Access Control**
- **allowed_roles**: engineer, eto, chief_engineer, chief_officer, purser, captain, manager
- **auth**: JWT Bearer token required

**Interface**
- **endpoint**: `POST /v1/equipment/set-status`
- **required_fields**:
  - `yacht_id` (UUID)
  - `equipment_id` (UUID)
  - `to_status` (enum: 8 values)
  - `work_order_id` (UUID - conditional: required if to_status='out_of_service')
- **optional_fields**:
  - `reason` (string)

**Triggers**
- Equipment breaks down → set to 'failed'
- Equipment undergoing maintenance → set to 'maintenance'
- Equipment performance drops → set to 'degraded'
- Equipment taken OOS for work → set to 'out_of_service' (requires WO link)
- Equipment returned to service → set to 'operational' or 'in_service'
- Equipment temporarily shelved → set to 'archived'
- Equipment permanently retired → set to 'decommissioned' (use decommission_and_replace instead)

**Preconditions**
- Equipment exists in database
- Equipment belongs to user's yacht (RLS enforced)
- User has write permission (HOD+ role)
- If setting to OOS: work order must exist and be OPEN or IN_PROGRESS

**Validation Rules**
1. **OOS Validation**:
   ```python
   if to_status == "out_of_service":
       require work_order_id
       work_order.status must be in ["open", "in_progress"]
       work_order.equipment_id must match equipment_id
   ```
2. **Status Enum**: Must be one of 8 values
3. **Yacht Isolation**: equipment.yacht_id must equal user's yacht_id

**Side Effects**
- `pms_equipment.status` updated
- `pms_equipment.updated_at` timestamp updated
- `pms_equipment.updated_by` set to user_id
- If OOS: equipment linked to work order (implicit relationship)
- Audit log entry created (if configured)

**Related Actions**
- **Before**: Often preceded by `flag_equipment_attention` or `create_work_order_for_equipment`
- **After**: May trigger `add_equipment_note` (to document reason) or `record_equipment_hours`
- **Alternative**: `decommission_and_replace_equipment` for terminal decommissioning

**Success States**
- **200 OK**: Status updated successfully
- Response includes:
  - `equipment_id`
  - `new_status`
  - `updated_at`

**Error States**
- **400 Bad Request**:
  - Invalid status value
  - OOS without work_order_id
  - Work order not OPEN/IN_PROGRESS
- **403 Forbidden**: User lacks permission (crew role attempting write)
- **404 Not Found**: Equipment not found or wrong yacht
- **409 Conflict**: Invalid status transition (business rule violation)

**UI Surfacing**
- **Equipment Detail Page**: Status dropdown with current status highlighted
- **Equipment Card**: Quick status change button
- **Work Order Detail**: "Mark Equipment OOS" button
- **Maintenance Dashboard**: Bulk status update for multiple equipment

**Example**
```bash
# Set equipment to out_of_service
curl -X POST https://pipeline-core.int.celeste7.ai/v1/equipment/set-status \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
    "equipment_id": "abc-123",
    "to_status": "out_of_service",
    "work_order_id": "wo-456"
  }'

# Response
{
  "status": "success",
  "equipment_id": "abc-123",
  "new_status": "out_of_service",
  "updated_at": "2026-01-27T12:00:00Z"
}
```

---

### 2. attach_image_with_comment

**Identification**
- **action_id**: `attach_image_with_comment`
- **label**: "Attach Image with Comment"
- **variant**: MUTATE

**Access Control**
- **allowed_roles**: engineer, eto, chief_engineer, chief_officer, chief_steward, purser, captain, manager
- **auth**: JWT Bearer token required

**Interface**
- **endpoint**: `POST /v1/equipment/attach-image`
- **required_fields**:
  - `yacht_id` (UUID)
  - `equipment_id` (UUID)
  - `file` (string - storage path)
  - `comment` (string - inline comment)
- **optional_fields**:
  - `document_type` (string)

**Triggers**
- Engineer takes photo of damaged equipment → attach with failure notes
- Maintenance completion → attach "before/after" photos with description
- Equipment inspection → attach photos with compliance notes
- Installation documentation → attach manual pages with annotations
- Warranty claim → attach photos of defect with detailed comment

**Preconditions**
- Equipment exists in database
- File already uploaded to storage (this action links existing file)
- Storage path matches pattern: `{yacht_id}/equipment/{equipment_id}/{filename}`
- User has write permission on equipment

**Validation Rules**
1. **Storage Path Pattern**:
   ```python
   # Valid
   "85fe1119.../equipment/abc123/manual.pdf"

   # Invalid
   "documents/85fe1119.../equipment/abc123/manual.pdf"  # no documents/ prefix
   "other-yacht/equipment/abc123/manual.pdf"  # wrong yacht
   "85fe1119.../equipment/xyz/manual.pdf"  # wrong equipment_id
   "85fe1119.../equipment/abc123/nested/file.pdf"  # no nesting
   ```

2. **Comment Required**: Cannot be empty or null
3. **Yacht Isolation**: Path must start with user's yacht_id

**Side Effects**
- New row in `pms_equipment_documents` table
- Fields set:
  - `equipment_id`
  - `storage_path`
  - `comment` (NEW in v2)
  - `created_by`
  - `created_at`
- Document visible in equipment's document list
- Storage file linked to equipment entity

**Related Actions**
- **Before**: File uploaded to storage (separate upload action/API)
- **After**: `link_document_to_equipment` (if additional metadata needed)
- **Alternative**: `attach_file_to_equipment` (older action without comment field)

**Success States**
- **200 OK**: Document linked successfully
- Response includes:
  - `document_id`
  - `storage_path`
  - `comment`
  - `created_at`

**Error States**
- **400 Bad Request**:
  - Invalid storage path pattern
  - Storage path starts with "documents/"
  - Missing comment field
  - Comment empty
- **403 Forbidden**: User lacks permission
- **404 Not Found**: Equipment not found or file doesn't exist in storage
- **409 Conflict**: Document already linked (duplicate storage_path)

**UI Surfacing**
- **Equipment Detail Page**: "Add Document" button with comment field
- **Photo Gallery**: Tap photo → add comment modal
- **Mobile App**: Camera capture → immediate comment entry
- **Work Order Detail**: "Attach Equipment Photo" with description

**Example**
```bash
curl -X POST https://pipeline-core.int.celeste7.ai/v1/equipment/attach-image \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
    "equipment_id": "abc-123",
    "file": "85fe1119-b04c-41ac-80f1-829d23322598/equipment/abc-123/oil_leak.jpg",
    "comment": "Oil leak discovered during routine inspection. Starboard side gasket failure."
  }'

# Response
{
  "status": "success",
  "document_id": "doc-789",
  "storage_path": "85fe1119.../equipment/abc-123/oil_leak.jpg",
  "comment": "Oil leak discovered during routine inspection...",
  "created_at": "2026-01-27T12:00:00Z"
}
```

---

### 3. decommission_and_replace_equipment

**Identification**
- **action_id**: `decommission_and_replace_equipment`
- **label**: "Decommission & Replace Equipment"
- **variant**: SIGNED (requires PIN + TOTP)

**Access Control**
- **allowed_roles**: captain, manager (signature authority only)
- **auth**: JWT Bearer token + signature (PIN + TOTP)

**Interface**
- **endpoint**: `POST /v1/equipment/decommission-replace`
- **required_fields**:
  - `yacht_id` (UUID)
  - `equipment_id` (UUID)
  - `reason` (string)
  - `replacement_name` (string)
  - `mode` (enum: "prepare" or "execute")
  - `signature` (object - only for execute mode)
    - `pin` (string)
    - `totp` (string)
    - `reason` (string)
- **optional_fields**:
  - `replacement_manufacturer` (string)
  - `replacement_model_number` (string)
  - `confirmation_token` (string - required for execute mode)

**Triggers**
- Equipment reaches end of life → decommission and order replacement
- Equipment beyond economic repair → retire and replace
- Equipment obsolete → decommission and upgrade to new model
- Equipment destroyed (fire/accident) → document loss and create replacement placeholder
- Regulatory requirement → replace outdated equipment

**Preconditions**
- Equipment exists and belongs to yacht
- User is captain or manager (signature authority)
- Equipment not already decommissioned
- User's PIN and TOTP configured in system

**Validation Rules**
1. **Two-Phase Commit** (Prepare → Execute):
   ```python
   # Phase 1: Prepare
   POST /decommission-replace {"mode": "prepare", ...}
   → Returns confirmation_token (expires in 5 minutes)

   # Phase 2: Execute
   POST /decommission-replace {
       "mode": "execute",
       "confirmation_token": "tok_...",
       "signature": {"pin": "...", "totp": "...", "reason": "..."}
   }
   → Validates signature, executes decommission + create replacement
   ```

2. **Signature Validation**:
   - PIN must match user's stored PIN (bcrypt hash)
   - TOTP must be valid for current 30-second window
   - Signature reason required (audit trail)

3. **Replacement Creation**:
   - Inherits system_type from original
   - Status set to 'operational'
   - No parent_equipment_id initially
   - Created by same user

**Side Effects**
- **Original Equipment**:
  - `status` set to `decommissioned` (TERMINAL - irreversible)
  - `updated_at` timestamp
  - `updated_by` set to user_id
- **New Equipment**:
  - New row in `pms_equipment` table
  - `name` from `replacement_name`
  - `manufacturer` from `replacement_manufacturer` (if provided)
  - `status` = `operational`
  - `yacht_id` = original equipment's yacht_id
- **Audit Log**:
  - Entry in `pms_audit_log` table
  - `action` = "decommission_and_replace_equipment"
  - `signature` = JSON with PIN hash + TOTP validation result
  - `metadata` = {original_id, replacement_id, reason}
  - **INVARIANT**: signature column NEVER NULL for SIGNED actions

**Related Actions**
- **Before**: Often preceded by `flag_equipment_attention`, `add_equipment_note` documenting failure
- **After**: May trigger `link_part_to_equipment` (transfer spare parts), `assign_parent_equipment` (if in hierarchy)
- **Alternative**: `archive_equipment` for reversible removal

**Success States**
- **Prepare Phase (200 OK)**:
  ```json
  {
    "status": "pending_signature",
    "confirmation_token": "tok_abc123...",
    "action_summary": "Decommission equipment ABC and create replacement 'New Engine'",
    "expires_at": "2026-01-27T12:05:00Z"
  }
  ```

- **Execute Phase (200 OK)**:
  ```json
  {
    "status": "success",
    "decommissioned_equipment_id": "abc-123",
    "replacement_equipment_id": "new-456",
    "audit_log_id": "audit-789",
    "signature_verified": true,
    "completed_at": "2026-01-27T12:04:32Z"
  }
  ```

**Error States**
- **400 Bad Request**:
  - Invalid mode (not "prepare" or "execute")
  - Missing reason or replacement_name
  - Invalid confirmation_token (expired/malformed)
  - Invalid PIN or TOTP
- **403 Forbidden**: User not captain/manager
- **404 Not Found**: Equipment not found
- **409 Conflict**: Equipment already decommissioned
- **422 Unprocessable**: Signature validation failed (wrong PIN/TOTP)

**UI Surfacing**
- **Equipment Detail Page**: "Decommission & Replace" button (captain only)
- **Equipment List**: Bulk action for multiple decommissions
- **Maintenance Dashboard**: "End of Life Equipment" section with decommission workflow
- **Signature Modal**: PIN + TOTP entry with reason text area

**Example**
```bash
# Phase 1: Prepare
curl -X POST https://pipeline-core.int.celeste7.ai/v1/equipment/decommission-replace \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "prepare",
    "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
    "equipment_id": "abc-123",
    "reason": "End of life - excessive wear beyond repair",
    "replacement_name": "Main Engine - Starboard (New)",
    "replacement_manufacturer": "Caterpillar",
    "replacement_model_number": "C32 ACERT"
  }'

# Response (prepare)
{
  "status": "pending_signature",
  "confirmation_token": "tok_j8x9k2m5n7p1q4r6",
  "action_summary": "Decommission 'Main Engine - Starboard' and create replacement 'Main Engine - Starboard (New)'",
  "expires_at": "2026-01-27T12:05:00Z"
}

# Phase 2: Execute (with signature)
curl -X POST https://pipeline-core.int.celeste7.ai/v1/equipment/decommission-replace \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "execute",
    "confirmation_token": "tok_j8x9k2m5n7p1q4r6",
    "signature": {
      "pin": "1234",
      "totp": "567890",
      "reason": "Equipment beyond economic repair after 12 years service"
    }
  }'

# Response (execute)
{
  "status": "success",
  "decommissioned_equipment_id": "abc-123",
  "replacement_equipment_id": "new-456",
  "audit_log_id": "audit-789",
  "signature_verified": true,
  "completed_at": "2026-01-27T12:04:32Z"
}
```

---

## Existing Equipment Actions (14)

### 4. create_equipment

**Identification**
- **action_id**: `create_equipment`
- **variant**: MUTATE

**Triggers**: Add new equipment to yacht inventory, equipment installation, equipment transfer from shore

**Preconditions**: User has HOD+ role, yacht_id valid

**Validation Rules**: Name required, yacht_id must match user's yacht (RLS)

**Side Effects**: New row in pms_equipment, status='operational'

**Related Actions**: After: assign_parent_equipment, link_document_to_equipment

---

### 5. update_equipment_status

**Identification**
- **action_id**: `update_equipment_status`
- **variant**: MUTATE

**Note**: **DEPRECATED** - Use `set_equipment_status` instead (Equipment Lens v2)

**Triggers**: Same as set_equipment_status

**Difference**: May not have OOS validation or 8-value constraint enforcement

---

### 6. archive_equipment

**Identification**
- **action_id**: `archive_equipment`
- **variant**: MUTATE

**Triggers**: Equipment temporarily removed from service (storage), seasonal equipment (jet skis in winter)

**Validation Rules**: Equipment must not be decommissioned

**Side Effects**:
- **Equipment Lens v2**: Sets `status='archived'` (no deleted_at)
- Reversible via `restore_archived_equipment`

**Related Actions**: After: restore_archived_equipment

---

### 7. restore_archived_equipment

**Identification**
- **action_id**: `restore_archived_equipment`
- **variant**: SIGNED (requires captain signature)

**Triggers**: Bring archived equipment back into service

**Preconditions**: Equipment status must be 'archived'

**Validation Rules**: Only captain/manager can restore, signature required

**Side Effects**: Sets `status='in_service'`

**Related Actions**: Before: archive_equipment

---

### 8. decommission_equipment

**Identification**
- **action_id**: `decommission_equipment`
- **variant**: SIGNED

**Note**: Simpler version without replacement creation

**Triggers**: Permanently retire equipment without immediate replacement

**Difference from decommission_and_replace**: Does not create replacement equipment

---

### 9. assign_parent_equipment

**Identification**
- **action_id**: `assign_parent_equipment`
- **variant**: MUTATE

**Triggers**: Create equipment hierarchy (e.g., "Oil Filter" → parent: "Main Engine")

**Validation Rules**: Parent must belong to same yacht, no circular references

**Side Effects**: Sets `parent_equipment_id`, enables hierarchical views

---

### 10. record_equipment_hours

**Identification**
- **action_id**: `record_equipment_hours`
- **variant**: MUTATE

**Triggers**: Log running hours for engines, generators, HVAC systems

**Validation Rules**: Hours must be monotonically increasing

**Side Effects**: New row in pms_equipment_hours, triggers maintenance scheduling

---

### 11. add_equipment_note

**Identification**
- **action_id**: `add_equipment_note`
- **variant**: MUTATE

**Triggers**: Document observations, maintenance notes, historical context

**Side Effects**: New row in pms_equipment_notes

---

### 12. flag_equipment_attention

**Identification**
- **action_id**: `flag_equipment_attention`
- **variant**: MUTATE

**Triggers**: Mark equipment for captain/HOD review, urgent issues

**Side Effects**: Sets attention flag, may trigger notifications

---

### 13. create_work_order_for_equipment

**Identification**
- **action_id**: `create_work_order_for_equipment`
- **variant**: MUTATE

**Triggers**: Equipment needs maintenance/repair

**Side Effects**: Creates work order linked to equipment, enables OOS status transition

---

### 14. link_part_to_equipment

**Identification**
- **action_id**: `link_part_to_equipment`
- **variant**: MUTATE

**Triggers**: Associate spare part with equipment, parts inventory management

**Side Effects**: Creates relationship in pms_equipment_parts table

---

### 15. attach_file_to_equipment

**Identification**
- **action_id**: `attach_file_to_equipment`
- **variant**: MUTATE

**Note**: **DEPRECATED** in favor of `attach_image_with_comment` (Equipment Lens v2)

**Difference**: Does not support inline comment field

---

### 16. link_document_to_equipment

**Identification**
- **action_id**: `link_document_to_equipment`
- **variant**: MUTATE

**Triggers**: Link existing document (manual, certificate) to equipment

**Difference from attach_image_with_comment**: For pre-existing documents, not new uploads

---

### 17. get_open_faults_for_equipment

**Identification**
- **action_id**: `get_open_faults_for_equipment`
- **variant**: READ

**Triggers**: View all unresolved issues for equipment

**Side Effects**: None (read-only)

**UI Surfacing**: Equipment detail page "Open Faults" tab

---

### 18. get_related_entities_for_equipment (Show Related)

**Identification**
- **action_id**: `get_related_entities_for_equipment`
- **variant**: READ

**Triggers**: View equipment's work orders, parts, documents, child equipment

**Side Effects**: None (read-only)

**UI Surfacing**: Equipment detail page "Related" tab, grouped by entity type

---

## Suggested Information Architecture

I recommend creating a **structured catalog format** with the following approaches:

### Option A: Markdown Table (Quick Reference)

```markdown
| Action ID | Variant | Roles | Triggers | Preconditions | Validation Rules | Side Effects |
|-----------|---------|-------|----------|---------------|------------------|--------------|
| set_equipment_status | MUTATE | HOD+ | Status change | Equipment exists | OOS→WO | Update status |
```

**Pros**: Quick scan, comparison across actions
**Cons**: Hard to capture detailed information

---

### Option B: Detailed Per-Action Pages (This Document)

Each action gets full treatment with all 12 dimensions.

**Pros**: Complete information, examples included, searchable
**Cons**: Lengthy, harder to compare actions

---

### Option C: JSON/YAML Structured Data

```yaml
actions:
  - action_id: set_equipment_status
    variant: MUTATE
    allowed_roles: [chief_engineer, captain, ...]
    triggers:
      - scenario: "Equipment breaks down"
        intent: "Mark as failed"
      - scenario: "OOS for maintenance"
        intent: "Link to work order"
    preconditions:
      - equipment_exists: true
      - user_has_write: true
    validation_rules:
      - rule: "OOS requires work order"
        logic: "if to_status='out_of_service' then work_order_id required"
```

**Pros**: Machine-readable, can generate docs/tests/UI from it
**Cons**: Requires tooling to make human-readable

---

### Option D: Interactive Decision Tree

```
Equipment needs attention
  ├─ Can it be repaired?
  │   ├─ Yes → create_work_order_for_equipment
  │   │   └─ Mark OOS → set_equipment_status (out_of_service)
  │   └─ No → Is it end of life?
  │       ├─ Yes → decommission_and_replace_equipment (SIGNED)
  │       └─ No → flag_equipment_attention
  └─ Just documenting → add_equipment_note
```

**Pros**: Shows workflow context, decision support
**Cons**: Hard to maintain, doesn't show all dimensions

---

## My Recommendation

**Hybrid Approach**:

1. **Master Catalog** (this document): Full detailed information for each action
2. **Quick Reference Matrix**: Table with key dimensions for comparison
3. **Workflow Diagrams**: Visual decision trees for common scenarios
4. **Structured Data**: YAML source of truth that generates docs + tests

Would you like me to:
1. Create the Quick Reference Matrix (all 17 actions in table format)?
2. Create Workflow Diagrams showing decision trees?
3. Generate YAML structured data for all actions?
4. Something else?
