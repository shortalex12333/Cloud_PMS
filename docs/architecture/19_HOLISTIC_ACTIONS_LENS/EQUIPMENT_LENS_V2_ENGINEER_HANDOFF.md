# Equipment Lens v2 - Engineer Handoff Document

**Date**: 2026-01-27
**Status**: ✅ Production Deployed & Documented
**For**: Next engineer continuing Equipment Lens work

---

## Table of Contents

1. [What Was Built](#what-was-built)
2. [Architecture Overview](#architecture-overview)
3. [Files Created/Modified](#files-createdmodified)
4. [Database Changes](#database-changes)
5. [API Endpoints](#api-endpoints)
6. [Testing Infrastructure](#testing-infrastructure)
7. [Documentation Deliverables](#documentation-deliverables)
8. [How to Continue Work](#how-to-continue-work)
9. [Quick Reference](#quick-reference)

---

## What Was Built

### Executive Summary

**Equipment Lens v2** is a comprehensive equipment lifecycle management system with 17 microactions covering creation, status management, documentation, archival, and decommissioning.

**Key Achievements**:
- ✅ **3 new actions** added to existing 14 equipment actions
- ✅ **Status-based workflow** with 8 enum values (replacing soft-delete pattern)
- ✅ **OOS validation** requiring work order linkage
- ✅ **SIGNED actions** with PIN+TOTP signature enforcement
- ✅ **Storage path validation** for equipment documents
- ✅ **Production deployed** with comprehensive testing
- ✅ **Full documentation** including flowcharts and catalogs

### The 3 New Actions (Equipment Lens v2)

1. **set_equipment_status** (MUTATE)
   - Set equipment status with validation rules
   - Special: Setting to `out_of_service` requires linked work order (OPEN/IN_PROGRESS)
   - Replaces older `update_equipment_status` action

2. **attach_image_with_comment** (MUTATE)
   - Attach documents with inline comments
   - Storage path validation enforced
   - Uses new `comment` column (not `description`)

3. **decommission_and_replace_equipment** (SIGNED)
   - Two-phase commit: PREPARE → EXECUTE
   - Requires captain signature (PIN + TOTP)
   - Creates replacement equipment atomically
   - Audit log signature invariant enforced

### Material Drifts Fixed

Two critical fixes were implemented to align code with specification:

**Drift 1: Comment Column**
- **Problem**: Handler was using `description` field
- **Spec**: Required `comment` field for image attachments
- **Fix**: Migration 018 added `pms_equipment_documents.comment` column
- **Handler updated**: Line 2073 in `equipment_handlers.py`

**Drift 2: Archive Mechanism**
- **Problem**: Code used soft delete (`deleted_at` column)
- **Spec**: Required status-based workflow (reversible)
- **Fix**: Migration 019 added 8-value status constraint
- **Handler updated**: Archive sets `status='archived'`, restore sets `status='in_service'`

---

## Architecture Overview

### Status Enum (8 Values)

Equipment lifecycle managed via `pms_equipment.status` column:

```
┌─────────────┐
│ operational │ ← Default for new equipment
└──────┬──────┘
       │
       ├──→ degraded ──→ failed
       ├──→ maintenance
       │
       ↓
┌─────────────────┐
│ out_of_service  │ ← Requires work order linkage
└──────┬──────────┘
       │
       ↓
┌─────────────┐
│ in_service  │ ← Default restored state
└──────┬──────┘
       │
       ↓
┌──────────┐
│ archived │ ← Reversible (captain signature required to restore)
└─────┬────┘
      │
      ↓
┌───────────────┐
│ decommissioned│ ← TERMINAL (irreversible)
└───────────────┘
```

### Validation Rules

#### OOS Validation
```python
if to_status == "out_of_service":
    # MUST provide work_order_id
    if not work_order_id:
        return 400 "work_order_id required for out_of_service status"

    # Work order MUST be OPEN or IN_PROGRESS
    work_order = db.get(work_order_id)
    if work_order.status not in ["open", "in_progress"]:
        return 400 "Work order must be OPEN or IN_PROGRESS"

    # Work order MUST belong to same equipment
    if work_order.equipment_id != equipment_id:
        return 400 "Work order equipment_id mismatch"
```

#### Storage Path Validation
```python
# VALID path format:
{yacht_id}/equipment/{equipment_id}/{filename}

# Examples:
✓ "85fe1119-b04c-41ac-80f1-829d23322598/equipment/abc-123/manual.pdf"

# INVALID patterns:
✗ "documents/85fe1119.../equipment/abc-123/manual.pdf"  # No documents/ prefix
✗ "other-yacht-id/equipment/abc-123/manual.pdf"         # Wrong yacht_id
✗ "85fe1119.../equipment/xyz-999/manual.pdf"            # Wrong equipment_id
✗ "85fe1119.../equipment/abc-123/nested/file.pdf"      # No nesting
```

#### Signature Validation (SIGNED Actions)
```python
# Two-phase pattern:
# 1. PREPARE: Generate confirmation_token (expires 5 min)
# 2. EXECUTE: Validate signature + commit

signature = {
    "pin": "1234",              # bcrypt validated
    "totp": "567890",           # TOTP 30-second window
    "reason": "Justification"   # Audit trail
}

# Audit log invariant:
# pms_audit_log.signature column NEVER NULL for SIGNED actions
```

### Role Permissions

```
crew/deckhand/steward         → READ only
    ↓
engineer/eto                  → READ + Basic MUTATE
    ↓
chief_engineer/chief_officer  → READ + MUTATE
chief_steward/purser          → (purser NEW in v2)
    ↓
captain/manager               → READ + MUTATE + SIGNED
```

**NEW in v2**: `purser` role added to HOD (Head of Department) permission level

---

## Files Created/Modified

### Location: `/docs/architecture/19_HOLISTIC_ACTIONS_LENS/`

All documentation moved to this folder per user request.

### Created Files (7)

1. **EQUIPMENT_LENS_V2.md**
   - Complete architecture reference
   - 8-value status enum documentation
   - All 3 new actions with examples
   - Database schema
   - Migrations 017-019 detailed
   - API reference (endpoints, auth, errors)

2. **EQUIPMENT_LENS_V2_MICROACTION_CATALOG.md**
   - 17 equipment actions cataloged
   - 12 information dimensions per action:
     - Identification, Access Control, Interface
     - Triggers, Preconditions, Validation Rules
     - Side Effects, Related Actions
     - Success States, Error States
     - UI Surfacing, Examples
   - Suggested formats (table, YAML, decision trees)

3. **EQUIPMENT_LENS_V2_FLOWCHARTS.md**
   - 6 visual flowcharts (Mermaid syntax):
     - Master Journey Map
     - Set Equipment Status Flow
     - Decommission & Replace Flow
     - Attach Image with Comment Flow
     - Archive/Restore Flow
     - Role Permission Matrix
   - 3 complete user journeys
   - Field requirement summary table

4. **EQUIPMENT_LENS_V2_PRODUCTION_CLEANUP.md**
   - Security cleanup report
   - All hardcoded secrets removed
   - Test files fixed to require env vars
   - 10 temporary files deleted
   - Production-grade checklist

5. **EQUIPMENT_LENS_V2_FINAL_VERIFICATION.md**
   - Production test results (11/11 passing)
   - Role detection verified (crew, chief_engineer, captain)
   - Action registry verified (all 3 actions present)
   - Database migrations verified

6. **EQUIPMENT_LENS_V2_ENGINEER_HANDOFF.md**
   - This document

7. **docs/evidence/EQUIPMENT_LENS_V2_PRODUCTION_CLEANUP.md**
   - Evidence bundle for production deployment

### Modified Files (5)

1. **apps/api/handlers/equipment_handlers.py**
   - Fixed line ~2073: Changed `description` to `comment` field
   - Fixed line ~1541: Archive uses `status='archived'` (not `deleted_at`)
   - Fixed line ~1619: Restore uses `status='in_service'`
   - All 18 handler functions verified

2. **apps/api/action_router/registry.py**
   - 3 new actions registered:
     - `set_equipment_status` (line ~795)
     - `attach_image_with_comment` (line ~799)
     - `decommission_and_replace_equipment` (line ~812)

3. **apps/api/tests/test_equipment_lens_v2_acceptance.py**
   - Removed hardcoded Supabase URL
   - Removed hardcoded service key
   - Removed hardcoded yacht ID
   - Added environment variable validation
   - Now requires 15 JWT personas from env vars

4. **apps/api/tests/test_equipment_lens_v2.py**
   - Removed hardcoded values
   - Added environment variable validation

5. **CHANGELOG.md**
   - Added Equipment Lens v2 release entry
   - Documented features, fixes, security improvements

### CI/CD Files (1)

1. **.github/workflows/equipment-lens-acceptance.yml**
   - 3 CI jobs:
     - Acceptance tests (15 JWT personas)
     - Migration verification (checks 017-019 applied)
     - Storage path validation tests
   - Auto-triggers on equipment file changes

---

## Database Changes

### Migration 017: Purser Role Addition

**File**: `supabase/migrations/20260127_017_update_is_hod_add_purser.sql`

**Purpose**: Add `purser` to `is_hod()` helper function

**Change**:
```sql
CREATE OR REPLACE FUNCTION public.is_hod(p_user_id uuid, p_yacht_id uuid)
RETURNS BOOLEAN AS $$
DECLARE
    v_role text;
BEGIN
    SELECT role INTO v_role
    FROM public.auth_users_roles  -- Note: roles in separate table
    WHERE user_id = p_user_id AND yacht_id = p_yacht_id;

    RETURN v_role IN (
        'chief_engineer',
        'chief_officer',
        'captain',
        'purser',  -- ← ADDED
        'manager'
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;
```

**Why**: Purser is a senior HOD role on yachts

**Used By**: RLS policies for write permissions on equipment

---

### Migration 018: Comment Column

**File**: `supabase/migrations/20260127_018_add_comment_column.sql`

**Purpose**: Add `comment` column to `pms_equipment_documents`

**Change**:
```sql
ALTER TABLE public.pms_equipment_documents
ADD COLUMN IF NOT EXISTS comment TEXT;

COMMENT ON COLUMN public.pms_equipment_documents.comment IS
    'Inline comment for image attachments (attach_image_with_comment action)';
```

**Why**: Fixes material drift - spec requires `comment` field, not `description`

**Used By**: `attach_image_with_comment` action

---

### Migration 019: Status Constraint Update

**File**: `supabase/migrations/20260127_019_update_status_constraint.sql`

**Purpose**: Update status constraint to 8 values

**Change**:
```sql
ALTER TABLE public.pms_equipment
DROP CONSTRAINT IF EXISTS pms_equipment_status_check;

ALTER TABLE public.pms_equipment
ADD CONSTRAINT pms_equipment_status_check CHECK (
    status IN (
        'operational',     -- Working normally
        'degraded',        -- Reduced performance
        'failed',          -- Not working
        'maintenance',     -- Under maintenance
        'out_of_service',  -- NEW: Requires WO linkage
        'in_service',      -- NEW: Default restored state
        'archived',        -- NEW: Reversible archive
        'decommissioned'   -- Terminal state
    )
);
```

**Why**: Enables status-based archive workflow (replaces soft delete)

**Used By**: All status management actions

---

### Database Architecture Notes

**User-Role Mapping**:
```sql
-- Roles stored in separate table (not in auth_users_profiles)
SELECT user_id, yacht_id, role
FROM auth_users_roles
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598';

-- Example results:
-- 18 captain users
-- 18 chief_engineer users
-- 17 crew users
```

**RLS (Row Level Security)**:
- 8 equipment tables have RLS enabled
- 33 policies enforce yacht isolation
- `get_user_yacht_id(auth.uid())` used in all policies
- Users can ONLY see/modify equipment from their yacht

**Audit Log Invariant**:
```sql
-- For all SIGNED actions:
SELECT signature FROM pms_audit_log
WHERE action IN ('decommission_and_replace_equipment', 'restore_archived_equipment');

-- Invariant: signature column NEVER NULL
-- Contains: {pin_valid: true, totp_valid: true, timestamp: "..."}
```

---

## API Endpoints

### Base URLs
- **Production**: `https://pipeline-core.int.celeste7.ai`
- **Local**: `http://localhost:8000`

### Authentication
All requests require JWT Bearer token:
```bash
curl -H "Authorization: Bearer $JWT" ...
```

### Endpoint 1: Set Equipment Status

**Action ID**: `set_equipment_status`
**Endpoint**: `POST /v1/equipment/set-status`
**Variant**: MUTATE
**Roles**: engineer, eto, chief_engineer, chief_officer, purser, captain, manager

**Request**:
```json
{
  "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
  "equipment_id": "abc-123",
  "to_status": "out_of_service",
  "work_order_id": "wo-456"  // Required if to_status = 'out_of_service'
}
```

**Response (200 OK)**:
```json
{
  "status": "success",
  "equipment_id": "abc-123",
  "new_status": "out_of_service",
  "updated_at": "2026-01-27T12:00:00Z"
}
```

**Errors**:
- 400: Invalid status, OOS without WO, WO not OPEN/IN_PROGRESS
- 403: User lacks permission (crew role)
- 404: Equipment not found or wrong yacht

---

### Endpoint 2: Attach Image with Comment

**Action ID**: `attach_image_with_comment`
**Endpoint**: `POST /v1/equipment/attach-image`
**Variant**: MUTATE
**Roles**: engineer, eto, chief_engineer, chief_officer, chief_steward, purser, captain, manager

**Request**:
```json
{
  "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
  "equipment_id": "abc-123",
  "file": "85fe1119-b04c-41ac-80f1-829d23322598/equipment/abc-123/oil_leak.jpg",
  "comment": "Oil leak discovered during routine inspection. Starboard side gasket failure."
}
```

**Response (200 OK)**:
```json
{
  "status": "success",
  "document_id": "doc-789",
  "storage_path": "85fe1119.../equipment/abc-123/oil_leak.jpg",
  "comment": "Oil leak discovered...",
  "created_at": "2026-01-27T12:00:00Z"
}
```

**Errors**:
- 400: Invalid storage path, missing comment, documents/ prefix
- 403: User lacks permission
- 404: Equipment or file not found
- 409: Document already linked

---

### Endpoint 3: Decommission & Replace

**Action ID**: `decommission_and_replace_equipment`
**Endpoint**: `POST /v1/equipment/decommission-replace`
**Variant**: SIGNED
**Roles**: captain, manager only

**Phase 1: PREPARE**
```json
{
  "mode": "prepare",
  "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
  "equipment_id": "abc-123",
  "reason": "End of life - excessive wear beyond repair",
  "replacement_name": "Main Engine - Starboard (New)",
  "replacement_manufacturer": "Caterpillar",
  "replacement_model_number": "C32 ACERT"
}
```

**Response (200 OK)**:
```json
{
  "status": "pending_signature",
  "confirmation_token": "tok_j8x9k2m5n7p1q4r6",
  "action_summary": "Decommission 'Main Engine - Starboard' and create replacement...",
  "expires_at": "2026-01-27T12:05:00Z"
}
```

**Phase 2: EXECUTE**
```json
{
  "mode": "execute",
  "confirmation_token": "tok_j8x9k2m5n7p1q4r6",
  "signature": {
    "pin": "1234",
    "totp": "567890",
    "reason": "Equipment beyond economic repair after 12 years service"
  }
}
```

**Response (200 OK)**:
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

**Errors**:
- 400: Invalid mode, expired token, missing fields
- 403: User not captain/manager
- 404: Equipment not found
- 409: Equipment already decommissioned
- 422: Invalid PIN or TOTP

---

## Testing Infrastructure

### Test Files

1. **apps/api/tests/test_equipment_lens_v2_acceptance.py**
   - Comprehensive acceptance tests
   - 15 JWT personas required
   - OOS validation, decommission flow, storage paths
   - RLS policy verification

2. **apps/api/tests/test_equipment_lens_v2.py**
   - Handler unit tests
   - Signature invariant tests
   - Status constraint tests

### Environment Variables Required

```bash
# Database
TENANT_1_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
TENANT_1_SUPABASE_SERVICE_KEY=eyJhbGci...
TEST_YACHT_ID=85fe1119-b04c-41ac-80f1-829d23322598

# API
API_BASE_URL=https://pipeline-core.int.celeste7.ai

# 15 JWT Personas
CREW_JWT=...
DECKHAND_JWT=...
STEWARD_JWT=...
ENGINEER_JWT=...
ETO_JWT=...
CHIEF_ENGINEER_JWT=...
CHIEF_OFFICER_JWT=...
CHIEF_STEWARD_JWT=...
PURSER_JWT=...
CAPTAIN_JWT=...
MANAGER_JWT=...
INACTIVE_JWT=...
EXPIRED_JWT=...
WRONG_YACHT_JWT=...
MIXED_ROLE_JWT=...
```

### Running Tests

```bash
# Set environment variables
export TENANT_1_SUPABASE_URL="..."
export TENANT_1_SUPABASE_SERVICE_KEY="..."
export TEST_YACHT_ID="..."
# ... (all 15 JWT personas)

# Run acceptance tests
cd apps/api
pytest tests/test_equipment_lens_v2_acceptance.py -v

# Run handler tests
pytest tests/test_equipment_lens_v2.py -v
```

### CI/CD

**Workflow**: `.github/workflows/equipment-lens-acceptance.yml`

**3 Jobs**:
1. **acceptance-tests**: Runs with 15 JWT personas from GitHub Secrets
2. **verify-migrations**: Checks migrations 017-019 applied
3. **verify-storage-validation**: Tests storage path logic

**Triggers**:
- Push to `main` branch
- Pull requests to `main`
- Changes to equipment handlers, migrations, or tests

---

## Documentation Deliverables

All files in `/docs/architecture/19_HOLISTIC_ACTIONS_LENS/`:

### 1. Architecture Documentation

**EQUIPMENT_LENS_V2.md**
- Complete technical reference
- Status enum, actions, database, API
- For: Backend engineers implementing features

### 2. Microaction Catalog

**EQUIPMENT_LENS_V2_MICROACTION_CATALOG.md**
- 17 actions with 12 information dimensions each
- Triggers, preconditions, validation rules
- For: Product managers, QA engineers, frontend engineers

### 3. Visual Flowcharts

**EQUIPMENT_LENS_V2_FLOWCHARTS.md**
- 6 Mermaid flowcharts showing all decision paths
- Role-gated journeys with field requirements
- For: Frontend engineers, UI/UX designers, QA

### 4. Production Cleanup Report

**EQUIPMENT_LENS_V2_PRODUCTION_CLEANUP.md**
- Security audit results
- No hardcoded secrets
- Production-grade checklist
- For: Security team, DevOps

### 5. Verification Report

**EQUIPMENT_LENS_V2_FINAL_VERIFICATION.md**
- Test results (11/11 passing)
- Production deployment evidence
- For: QA team, stakeholders

### 6. This Document

**EQUIPMENT_LENS_V2_ENGINEER_HANDOFF.md**
- Complete context for next engineer
- What was built, how it works, how to continue
- For: Next engineer on the project

---

## How to Continue Work

### If You Need to Add a New Action

1. **Define the Action**:
   - Add to `apps/api/action_router/registry.py`
   - Set `action_id`, `label`, `variant` (READ/MUTATE/SIGNED)
   - Define `allowed_roles`, `required_fields`, `endpoint`

2. **Implement Handler**:
   - Add to `apps/api/handlers/equipment_handlers.py`
   - Follow naming: `_action_name_adapter(handlers: EquipmentHandlers)`
   - Return to `get_equipment_handlers()` dictionary

3. **Register Dispatcher**:
   - Add to `apps/api/action_router/dispatchers/internal_dispatcher.py`
   - Create wrapper function calling handler

4. **Add Tests**:
   - Handler test in `test_equipment_lens_v2.py`
   - Acceptance test in `test_equipment_lens_v2_acceptance.py`
   - Test all 15 JWT personas for role gating

5. **Update Documentation**:
   - Add to microaction catalog
   - Create flowchart if complex
   - Update CHANGELOG.md

### If You Need to Modify Status Enum

**Current constraint**: 8 values (operational, degraded, failed, maintenance, out_of_service, in_service, archived, decommissioned)

**To add new status**:
1. Create migration:
   ```sql
   ALTER TABLE pms_equipment
   DROP CONSTRAINT pms_equipment_status_check;

   ALTER TABLE pms_equipment
   ADD CONSTRAINT pms_equipment_status_check CHECK (
       status IN (
           -- existing 8 values
           'new_status'  -- add here
       )
   );
   ```

2. Update documentation:
   - `EQUIPMENT_LENS_V2.md` status table
   - `EQUIPMENT_LENS_V2_FLOWCHARTS.md` status transitions
   - `EQUIPMENT_LENS_V2_MICROACTION_CATALOG.md` validation rules

3. Update handlers:
   - Add validation logic for new status
   - Update `set_equipment_status` if special rules needed

### If You Need to Add New Validation Rule

Example: Add "maintenance requires maintenance_plan_id"

1. **Handler Logic** (`equipment_handlers.py`):
   ```python
   if to_status == "maintenance":
       if not maintenance_plan_id:
           return {"status": "error", "error_code": "MAINTENANCE_PLAN_REQUIRED"}
   ```

2. **Utility Function** (`equipment_utils.py`):
   ```python
   def validate_maintenance_plan(db, plan_id, equipment_id):
       # Check plan exists, matches equipment, is active
       pass
   ```

3. **Tests**:
   - Test with and without maintenance_plan_id
   - Test with invalid plan_id

4. **Documentation**:
   - Update flowchart with new decision diamond
   - Update catalog with new precondition

### If You Need to Debug Production Issues

**Check Logs**:
```bash
# Render logs (production API)
# Check for 500 errors, handler exceptions

# Look for:
# - "OOS validation failed" → work order issue
# - "Storage path validation failed" → path format issue
# - "Signature validation failed" → PIN/TOTP issue
```

**Common Issues**:

1. **OOS Status Not Working**:
   - Check work order exists: `SELECT * FROM pms_work_orders WHERE id = '...'`
   - Check work order status: Must be 'open' or 'in_progress'
   - Check equipment match: `work_order.equipment_id == equipment_id`

2. **Attach Image Failing**:
   - Check path format: `{yacht_id}/equipment/{equipment_id}/{filename}`
   - Check for `documents/` prefix (invalid)
   - Check file exists in storage bucket

3. **Decommission Failing**:
   - Check user is captain/manager
   - Check PIN: `bcrypt.compare(pin, user.pin_hash)`
   - Check TOTP: 30-second window validation
   - Check confirmation_token not expired (5 min)

---

## Quick Reference

### Key Files

| File | Purpose | Location |
|------|---------|----------|
| equipment_handlers.py | Handler implementations | apps/api/handlers/ |
| equipment_utils.py | Validation utilities | apps/api/handlers/ |
| registry.py | Action definitions | apps/api/action_router/ |
| internal_dispatcher.py | Action dispatchers | apps/api/action_router/dispatchers/ |
| Migration 017 | Purser role | supabase/migrations/ |
| Migration 018 | Comment column | supabase/migrations/ |
| Migration 019 | Status constraint | supabase/migrations/ |

### Key Concepts

| Concept | Description |
|---------|-------------|
| **Status Enum** | 8 values: operational → degraded → failed → maintenance → out_of_service → in_service → archived → decommissioned |
| **OOS Validation** | Setting to `out_of_service` requires linked work order (OPEN/IN_PROGRESS) |
| **SIGNED Actions** | Two-phase: PREPARE → EXECUTE with PIN+TOTP signature |
| **Storage Paths** | Format: `{yacht_id}/equipment/{equipment_id}/{filename}` (no documents/ prefix) |
| **Material Drifts** | Fixed: comment column (not description), status-based archive (not deleted_at) |
| **RLS** | Row-level security enforces yacht isolation (33 policies across 8 tables) |

### Production Credentials

**Authentication**:
- MASTER Supabase: `qvzmkaamzaqxpzbewjxe.supabase.co` (auth)
- TENANT Supabase: `vzsohavtuotocgrfkfyd.supabase.co` (data)

**Test Users** (Production):
- crew.test@alex-short.com (crew role)
- hod.test@alex-short.com (chief_engineer role)
- captain.ci+1769556038@alex-short.com (captain role)

**Test Yacht**: `85fe1119-b04c-41ac-80f1-829d23322598`

### Git Tags

- **Tag**: `equipment-lens-v2`
- **Commit**: 40f7e5f
- **Push**: `git push origin equipment-lens-v2` (when ready)

### CI Status

- **Workflow**: `.github/workflows/equipment-lens-acceptance.yml`
- **Status**: Ready (needs GitHub Secrets configured)
- **Secrets**: 15 JWT personas (STAGING_CREW_JWT, STAGING_CHIEF_ENGINEER_JWT, etc.)

---

## Contact Points

### Code Locations

**Handlers**: `/apps/api/handlers/equipment_handlers.py` (lines 569-2400)
**Registry**: `/apps/api/action_router/registry.py` (lines 795-850)
**Tests**: `/apps/api/tests/test_equipment_lens_v2*.py`
**Migrations**: `/supabase/migrations/20260127_01*.sql`

### Documentation Locations

**All docs moved to**: `/docs/architecture/19_HOLISTIC_ACTIONS_LENS/`

Files in this folder:
1. EQUIPMENT_LENS_V2.md
2. EQUIPMENT_LENS_V2_MICROACTION_CATALOG.md
3. EQUIPMENT_LENS_V2_FLOWCHARTS.md
4. EQUIPMENT_LENS_V2_PRODUCTION_CLEANUP.md
5. EQUIPMENT_LENS_V2_FINAL_VERIFICATION.md
6. EQUIPMENT_LENS_V2_ENGINEER_HANDOFF.md (this file)

### Production Endpoints

- **API**: https://pipeline-core.int.celeste7.ai
- **Status**: ✅ Deployed (commit 40f7e5f)
- **Actions**: All 3 registered and verified (11/11 tests passing)

---

## Summary for Next Engineer

**What You're Getting**:
- ✅ Fully deployed Equipment Lens v2 with 3 new actions
- ✅ Complete handler implementations with validation
- ✅ Database migrations applied (017, 018, 019)
- ✅ Comprehensive test suite (15 JWT personas)
- ✅ Full documentation (architecture, flowcharts, catalog)
- ✅ Production-grade cleanup (no hardcoded secrets)
- ✅ CI/CD workflow ready

**What Works**:
- All 17 equipment actions registered
- Role-based permissions enforced
- OOS validation requiring work orders
- Two-phase SIGNED actions with PIN+TOTP
- Storage path validation
- Status-based archive (no soft delete)
- RLS policies enforcing yacht isolation

**What's Next** (if you need to extend):
- Add new equipment actions following patterns
- Extend status enum if needed
- Add more validation rules
- Integrate with frontend equipment pages
- Add bulk operations (multiple equipment at once)
- Add equipment import/export

**Start Here**:
1. Read `EQUIPMENT_LENS_V2.md` for architecture
2. Review `EQUIPMENT_LENS_V2_FLOWCHARTS.md` for visual understanding
3. Run tests locally to verify everything works
4. Check production API to see actions in action
5. Review this handoff document when making changes

---

**Document Created**: 2026-01-27
**Engineer Handoff**: Complete ✅
**Equipment Lens v2**: Production Ready 🚀
