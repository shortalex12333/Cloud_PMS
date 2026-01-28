# Equipment Lens v2 - Architecture & API Reference

**Status**: Production (deployed 2026-01-27)
**Tag**: `equipment-lens-v2`
**Commit**: 40f7e5f

---

## Overview

Equipment Lens v2 provides equipment lifecycle management with status tracking, work order integration, document management, and signature-required decommissioning.

### Key Features

- **Status Management**: 8-value status enum with validation rules
- **OOS Validation**: `out_of_service` requires linked work order
- **Archive Workflow**: Reversible archive via status (not soft delete)
- **Decommission Flow**: SIGNED action with prepare/execute pattern
- **Document Management**: Image attachments with inline comments
- **Storage Validation**: Scoped paths for equipment documents

---

## Status Enum (8 Values)

Equipment status is managed via the `pms_equipment.status` column with the following constraint:

### Status Values

| Status | Type | Description | Validation Rules | Reversible? |
|--------|------|-------------|------------------|-------------|
| **operational** | Working | Equipment functioning normally | Default for new equipment | Yes |
| **degraded** | Working | Reduced performance but functional | - | Yes |
| **failed** | Not Working | Equipment not functioning | - | Yes |
| **maintenance** | Not Working | Undergoing scheduled/unscheduled maintenance | - | Yes |
| **out_of_service** | Not Working | **OOS requires WO linkage** | Must have linked OPEN or IN_PROGRESS work order | Yes |
| **in_service** | Working | Default state after restoration | Target status for `restore_archived_equipment` | Yes |
| **archived** | Archived | Equipment archived (reversible) | Can be restored via SIGNED action | Yes (captain only) |
| **decommissioned** | Terminal | Permanently decommissioned | Requires SIGNED action with reason | **No** |

### Status Transitions

```
operational ←→ degraded ←→ failed
      ↓            ↓         ↓
   maintenance ← - - - - - -┘
      ↓
out_of_service (requires WO)
      ↓
   archived (captain signature)
      ↓
decommissioned (TERMINAL - captain signature + replacement)
```

### Validation Rules

#### Out-of-Service Validation
```python
# Setting status to out_of_service requires work_order_id
if to_status == "out_of_service":
    if not work_order_id:
        return 400 "work_order_id required for out_of_service status"

    # Work order must be OPEN or IN_PROGRESS
    wo = db.get_work_order(work_order_id)
    if wo.status not in ["open", "in_progress"]:
        return 400 "Work order must be OPEN or IN_PROGRESS"
```

#### Archive/Restore
```python
# Archive: Set status to 'archived' (no deleted_at)
archive_equipment(equipment_id):
    db.update(status="archived")

# Restore: Set status to 'in_service' (requires captain signature)
restore_archived_equipment(equipment_id, signature):
    if equipment.status != "archived":
        return 400 "Equipment must be archived to restore"
    db.update(status="in_service")
```

#### Decommission
```python
# Decommission: SIGNED action with prepare/execute pattern
decommission_and_replace_equipment(equipment_id, reason, replacement_name, signature):
    # Prepare phase returns confirmation_token
    # Execute phase validates token + creates replacement + sets status
    db.update(status="decommissioned")  # TERMINAL
```

---

## Actions

### 1. set_equipment_status

**Action ID**: `set_equipment_status`
**Variant**: MUTATE
**Endpoint**: `POST /v1/equipment/set-status`

**Allowed Roles**: engineer, eto, chief_engineer, chief_officer, purser, captain, manager

**Required Fields**:
- `yacht_id` (UUID)
- `equipment_id` (UUID)
- `to_status` (string - must be one of 8 enum values)
- `work_order_id` (UUID - required only if `to_status == "out_of_service"`)

**Validation**:
- `to_status` must be valid enum value
- If `to_status == "out_of_service"`, must provide `work_order_id` for OPEN/IN_PROGRESS WO
- User must have write permission on equipment (RLS enforced)

**Example**:
```bash
curl -X POST https://pipeline-core.int.celeste7.ai/v1/equipment/set-status \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "yacht_id": "...",
    "equipment_id": "...",
    "to_status": "out_of_service",
    "work_order_id": "..."
  }'
```

**Response**:
```json
{
  "status": "success",
  "equipment_id": "...",
  "new_status": "out_of_service",
  "updated_at": "2026-01-27T..."
}
```

---

### 2. attach_image_with_comment

**Action ID**: `attach_image_with_comment`
**Variant**: MUTATE
**Endpoint**: `POST /v1/equipment/attach-image`

**Allowed Roles**: engineer, eto, chief_engineer, chief_officer, chief_steward, purser, captain, manager

**Required Fields**:
- `yacht_id` (UUID)
- `equipment_id` (UUID)
- `file` (string - storage path)
- `comment` (string - inline comment for the image)

**Storage Path Format**:
```
{yacht_id}/equipment/{equipment_id}/{filename}
```

**Invalid Paths**:
- ❌ `documents/{yacht_id}/equipment/...` (no "documents/" prefix)
- ❌ `{other_yacht_id}/equipment/...` (wrong yacht_id)

**Validation**:
- Storage path must match pattern `{yacht_id}/equipment/{equipment_id}/*`
- Path must NOT start with `documents/`
- `comment` field is stored in `pms_equipment_documents.comment` column

**Example**:
```bash
curl -X POST https://pipeline-core.int.celeste7.ai/v1/equipment/attach-image \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "yacht_id": "...",
    "equipment_id": "...",
    "file": "85fe1119-b04c-41ac-80f1-829d23322598/equipment/abc123/manual.pdf",
    "comment": "Engine manual page 42 - oil filter replacement"
  }'
```

**Response**:
```json
{
  "status": "success",
  "document_id": "...",
  "storage_path": "85fe1119.../equipment/abc123/manual.pdf",
  "comment": "Engine manual page 42...",
  "created_at": "2026-01-27T..."
}
```

---

### 3. decommission_and_replace_equipment

**Action ID**: `decommission_and_replace_equipment`
**Variant**: SIGNED
**Endpoint**: `POST /v1/equipment/decommission-replace`

**Allowed Roles**: captain, manager (signature required)

**Required Fields**:
- `yacht_id` (UUID)
- `equipment_id` (UUID)
- `reason` (string - justification for decommissioning)
- `replacement_name` (string - name for replacement equipment)
- `replacement_manufacturer` (string, optional)
- `replacement_model_number` (string, optional)

**Workflow**: Prepare/Execute Pattern

#### Prepare Phase
```bash
curl -X POST https://pipeline-core.int.celeste7.ai/v1/equipment/decommission-replace \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "prepare",
    "yacht_id": "...",
    "equipment_id": "...",
    "reason": "End of life - excessive wear",
    "replacement_name": "New Main Engine"
  }'
```

**Response**:
```json
{
  "status": "pending_signature",
  "confirmation_token": "tok_abc123xyz...",
  "action_summary": "Decommission equipment XYZ and create replacement 'New Main Engine'",
  "expires_at": "2026-01-27T12:15:00Z"
}
```

#### Execute Phase (with Signature)
```bash
curl -X POST https://pipeline-core.int.celeste7.ai/v1/equipment/decommission-replace \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "execute",
    "confirmation_token": "tok_abc123xyz...",
    "signature": {
      "pin": "1234",
      "totp": "567890",
      "reason": "Equipment beyond repair"
    }
  }'
```

**Response**:
```json
{
  "status": "success",
  "decommissioned_equipment_id": "...",
  "replacement_equipment_id": "...",
  "audit_log_id": "...",
  "signature_verified": true,
  "completed_at": "2026-01-27T12:14:32Z"
}
```

**Validation**:
- Equipment must exist and belong to yacht
- User must have captain or manager role
- PIN + TOTP must be valid for user
- Confirmation token must not be expired
- Replacement equipment is created with `status='operational'`
- Original equipment status set to `decommissioned` (TERMINAL)

---

## Database Schema

### pms_equipment Table

```sql
CREATE TABLE pms_equipment (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES yachts(id),
    name TEXT NOT NULL,
    system_type TEXT,
    status TEXT NOT NULL DEFAULT 'operational'
        CHECK (status IN (
            'operational',
            'degraded',
            'failed',
            'maintenance',
            'out_of_service',  -- NEW: requires WO
            'in_service',      -- NEW: default restored state
            'archived',        -- NEW: reversible archive
            'decommissioned'   -- TERMINAL
        )),
    parent_equipment_id UUID REFERENCES pms_equipment(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID,
    updated_by UUID
);
```

### pms_equipment_documents Table

```sql
CREATE TABLE pms_equipment_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES yachts(id),
    equipment_id UUID NOT NULL REFERENCES pms_equipment(id),
    storage_path TEXT NOT NULL,
    comment TEXT,  -- NEW: inline comment for images
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID
);
```

---

## Migrations

### Migration 017: is_hod() Purser Addition

**File**: `supabase/migrations/20260127_017_update_is_hod_add_purser.sql`

```sql
CREATE OR REPLACE FUNCTION public.is_hod(p_user_id uuid, p_yacht_id uuid)
RETURNS BOOLEAN AS $$
DECLARE
    v_role text;
BEGIN
    SELECT role INTO v_role
    FROM public.auth_users_profiles
    WHERE id = p_user_id AND yacht_id = p_yacht_id;

    RETURN v_role IN (
        'chief_engineer',
        'chief_officer',
        'captain',
        'purser',  -- ADDED
        'manager'
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;
```

**Reason**: Purser is a senior HOD role on yachts

---

### Migration 018: Comment Column

**File**: `supabase/migrations/20260127_018_add_comment_column.sql`

```sql
ALTER TABLE public.pms_equipment_documents
ADD COLUMN IF NOT EXISTS comment TEXT;

COMMENT ON COLUMN public.pms_equipment_documents.comment IS
    'Inline comment for image attachments (attach_image_with_comment action)';
```

**Reason**: Fixes material drift - spec requires `comment` field (not `description`)

---

### Migration 019: Status Constraint Update

**File**: `supabase/migrations/20260127_019_update_status_constraint.sql`

```sql
ALTER TABLE public.pms_equipment
DROP CONSTRAINT IF EXISTS pms_equipment_status_check;

ALTER TABLE public.pms_equipment
ADD CONSTRAINT pms_equipment_status_check CHECK (
    status IN (
        'operational',
        'degraded',
        'failed',
        'maintenance',
        'out_of_service',  -- NEW
        'in_service',      -- NEW
        'archived',        -- NEW
        'decommissioned'
    )
);
```

**Reason**: Enable status-based archive workflow and OOS validation

---

## RLS Policies

Equipment tables enforce yacht isolation via Row Level Security:

```sql
-- pms_equipment: users can only see equipment from their yacht
CREATE POLICY "yacht_isolation" ON pms_equipment
    FOR SELECT
    USING (yacht_id = get_user_yacht_id(auth.uid()));

-- HOD can update equipment
CREATE POLICY "hod_can_update" ON pms_equipment
    FOR UPDATE
    USING (
        yacht_id = get_user_yacht_id(auth.uid())
        AND is_hod(auth.uid(), yacht_id)
    );
```

---

## Testing

### Test Coverage

- **15 JWT Personas**: crew, deckhand, steward, engineer, eto, chief_engineer, chief_officer, chief_steward, purser, captain, manager, inactive, expired, wrong_yacht, mixed_role
- **OOS Validation**: Tests status change requires valid work order
- **Decommission Flow**: Tests prepare → execute with signature
- **Storage Paths**: Tests valid/invalid path formats
- **RLS Policies**: Tests yacht isolation enforcement

### Running Tests

```bash
# Set environment variables
export TENANT_1_SUPABASE_URL="https://..."
export TENANT_1_SUPABASE_SERVICE_KEY="..."
export TEST_YACHT_ID="..."
export CREW_JWT="..."
export CHIEF_ENGINEER_JWT="..."
export CAPTAIN_JWT="..."
# ... (all 15 JWT personas)

# Run acceptance tests
pytest apps/api/tests/test_equipment_lens_v2_acceptance.py -v

# Run handler tests
pytest apps/api/tests/test_equipment_lens_v2.py -v
```

**Note**: All secrets must be provided via environment variables (no hardcoded values)

---

## API Reference

### Base URL
- **Production**: `https://pipeline-core.int.celeste7.ai`
- **Local**: `http://localhost:8000`

### Authentication
All requests require JWT Bearer token:
```
Authorization: Bearer eyJhbGci...
```

### Error Responses

| Code | Meaning | Example |
|------|---------|---------|
| 400 | Bad Request | Missing required field, invalid status value |
| 403 | Forbidden | User lacks permission (role-gated) |
| 404 | Not Found | Equipment not found or wrong yacht |
| 409 | Conflict | OOS without work order, invalid status transition |
| 500 | Internal Error | Database error (should never happen in production) |

---

## Material Drifts Fixed

### 1. Comment Column Drift ✅

**Problem**: Handler was using `description` field, spec required `comment` field

**Solution**:
- Created migration 018 to add `comment` column
- Updated `attach_image_with_comment` handler to use `comment` field
- Verified in production (line 2073 of equipment_handlers.py)

### 2. Archive Mechanism Drift ✅

**Problem**: Code used soft delete (`deleted_at`), spec required status-only

**Solution**:
- Created migration 019 for 8-value status constraint
- Rewrote `archive_equipment` to set `status='archived'`
- Rewrote `restore_archived_equipment` to flip `status='in_service'` (SIGNED)
- Removed all `deleted_at` references

---

## Deployment Checklist

- ✅ Migrations 017-019 applied to production
- ✅ Handlers deployed (commit 40f7e5f)
- ✅ Actions registered in registry.py
- ✅ RLS policies active
- ✅ Test coverage: 11/11 acceptance tests passing
- ✅ Material drifts fixed
- ✅ Storage path validation working
- ✅ OOS→WO validation enforced
- ✅ Changelog updated
- ✅ Git tag created

---

## Contact & Support

**Deployment Date**: 2026-01-27
**Status**: Production Ready ✅
**Tag**: `equipment-lens-v2`

For questions or issues, refer to:
- Changelog: `CHANGELOG.md`
- Test Suite: `apps/api/tests/test_equipment_lens_v2_acceptance.py`
- Handlers: `apps/api/handlers/equipment_handlers.py`
- Migrations: `supabase/migrations/20260127_01*.sql`
