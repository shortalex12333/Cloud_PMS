# Shopping List Lens v1 - Engineer Handoff Document

**Date**: 2026-01-28
**Status**: ✅ Production Deployed & Documented
**For**: Next engineer continuing Shopping List Lens work

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

**Shopping List Lens v1** is a comprehensive procurement request management system with role-based approval workflows. It enables crew to request items, HoD to approve/reject requests, and engineers to promote approved candidates to the permanent parts catalog.

**Key Achievements**:
- ✅ **5 microactions** for complete shopping list workflow
- ✅ **Role-based access control** (CREW create, HOD approve/reject, ENGINEER promote)
- ✅ **Defense-in-depth security** (3 layers: Router, Handlers, RLS)
- ✅ **27/27 tests passing** (18 Docker RLS + 9 Staging Acceptance)
- ✅ **0×500 requirement met** (zero 5xx errors)
- ✅ **Production ready** with comprehensive testing
- ✅ **Full documentation** including flowcharts and catalogs

### The 5 Shopping List Actions

1. **create_shopping_list_item** (MUTATE)
   - Any authenticated user can request items
   - Required: item_name, quantity, source_type, is_candidate_part
   - Optional: manufacturer, model_number, urgency, estimated_cost
   - Creates item in 'candidate' status

2. **approve_shopping_list_item** (MUTATE)
   - HOD only (chief_engineer, chief_officer, captain, manager, purser)
   - Sets status='approved', quantity_approved
   - Records approved_by and approved_at timestamps
   - Terminal state for procurement

3. **reject_shopping_list_item** (MUTATE)
   - HOD only (chief_engineer, chief_officer, captain, manager, purser)
   - Sets rejected_at, rejected_by, rejection_reason
   - Status remains 'candidate' (rejection marked by rejected_at field)
   - Terminal state (blocked from procurement)

4. **promote_candidate_to_part** (MUTATE)
   - Engineer only (chief_engineer, engineer, manager)
   - Requires is_candidate_part=true and status='approved'
   - Creates new entry in pms_parts_catalog
   - Links via promoted_to_part_id
   - Makes item available for future work orders

5. **view_shopping_list_item_history** (READ)
   - All authenticated users
   - Returns state change history from pms_shopping_list_item_state_history
   - Audit trail for all status transitions

### Sprint Results

**Starting Point**: 83% pass rate (15/18 tests)
- 3 failures: CREW could approve/reject/promote (should be 403)

**Ending Point**: 100% pass rate (27/27 tests)
- ✅ 18/18 Docker RLS tests passing
- ✅ 9/9 Staging acceptance tests passing
- ✅ 0×500 requirement met (zero 5xx errors)

**Time Investment**: 6-hour sprint + 30 minutes hardening

---

## Architecture Overview

### State Machine

```
┌───────────┐
│ candidate │ ← Default status (all new items)
└─────┬─────┘
      │
      ├──→ APPROVE ──→ approved (terminal, can be promoted)
      │                  └──→ PROMOTE ──→ approved + promoted_to_part_id
      │
      └──→ REJECT ──→ candidate + rejected_at (pseudo-terminal)
```

**Key State Rules**:
- **candidate**: Initial state, only CREW who created can modify
- **approved**: Terminal state set by HOD, ready for procurement
- **rejected**: Pseudo-terminal (status='candidate' but rejected_at IS NOT NULL)
- **promoted**: Extended state (status='approved' but promoted_to_part_id set)

### Role Hierarchy

```
crew/deckhand/steward         → Create only
    ↓
engineer/eto                  → Create + Promote
    ↓
chief_officer/purser          → Create + Approve + Reject (HOD)
    ↓
chief_engineer                → Create + Approve + Reject + Promote (HOD + Engineer)
    ↓
captain/manager               → Full access (all actions)
```

### Defense-in-Depth Security (3 Layers)

**Layer 1: Router** (`apps/api/main.py`)
- Action definitions enforce `allowed_roles`
- First line of defense before handler invocation
- Example: `"allowed_roles": ["chief_engineer", "chief_officer", "captain", "manager", "purser"]`

**Layer 2: Handlers** (`apps/api/handlers/shopping_list_handlers.py`)
- Explicit role checks using `is_hod()` and `is_engineer()` RPCs
- **Critical**: Handlers use service keys which BYPASS RLS
- Must explicitly call Supabase RPCs to check roles
- Returns 403 with descriptive error messages

**Layer 3: Database (RLS Policies)**
- Blocks direct SQL access (PostgREST)
- 4 role-specific UPDATE policies on pms_shopping_list_items
- Yacht isolation enforcement via `get_user_yacht_id()`
- Proven: 0 rows updated when CREW attempts approve/reject/promote via SQL

**Why All 3 Layers?**
```
Scenario 1: User accesses API
  → Router checks allowed_roles ✓
  → Handler checks is_hod()/is_engineer() ✓
  → Result: CREW blocked at layers 1+2

Scenario 2: User attempts direct SQL via PostgREST
  → RLS policies block at database level ✓
  → Result: 0 rows updated

Scenario 3: Handler uses service key (bypasses RLS)
  → Handler must explicitly check roles ✓
  → Result: 403 returned if not authorized
```

### Backend Authority Principle

**UI renders only what backend returns**:
- `GET /v1/actions/list?domain=shopping_list` returns different actions per role
- CREW sees: `create_shopping_list_item` only
- HOD sees: `create`, `approve`, `reject`
- ENGINEER sees: `create`, `promote`
- Frontend NEVER decides permissions - always defers to backend

---

## Files Created/Modified

### Location: `/docs/architecture/20_SHOPPING_LIST_LENS/`

All comprehensive documentation in this folder.

### Created Files (3 Core Docs)

1. **SHOPPING_LIST_LENS_V1.md**
   - Complete architecture reference
   - 5 actions with detailed specifications
   - Database schema (pms_shopping_list_items, state_history)
   - Security architecture (3-layer defense-in-depth)
   - State machine documentation
   - API reference (endpoints, auth, responses)
   - Testing infrastructure overview
   - Deployment checklist

2. **SHOPPING_LIST_LENS_V1_MICROACTION_CATALOG.md**
   - 5 actions cataloged with 12 dimensions each:
     - Identification, Access Control, Interface
     - Triggers, Preconditions, Validation Rules
     - Side Effects, Related Actions
     - Success States, Error States
     - UI Surfacing, Examples
   - Role Permission Matrix table
   - Field Reference tables
   - Complete curl examples with request/response pairs

3. **SHOPPING_LIST_LENS_V1_FLOWCHARTS.md**
   - 6 visual flowcharts (Mermaid syntax):
     - Master Journey Map
     - Create Shopping List Item Flow
     - Approve Shopping List Item Flow
     - Reject Shopping List Item Flow
     - Promote Candidate to Part Flow
     - Role Permission Matrix
   - 4 complete user journey examples
   - Field requirement summary table
   - State machine diagram

4. **SHOPPING_LIST_LENS_V1_ENGINEER_HANDOFF.md**
   - This document

### Pipeline Evidence Files

Location: `/docs/pipeline/shopping_list_lens/`

1. **PHASE3_DOCKER_RLS_RESULTS.md**
   - Complete RLS policy DDL
   - Handler role check code snippets
   - SQL denial proofs (0 rows updated)
   - Full Docker test output (18/18 passing)

2. **PHASE4_STAGING_ACCEPTANCE_RESULTS.md**
   - Complete HTTP request/response transcripts
   - Action list filtering proofs (CREW vs HOD)
   - Backend authority principle validation
   - Full staging test output (9/9 passing)

### Modified Files (7)

1. **supabase/migrations/20260128_shopping_list_rls_fix.sql**
   - Dropped 5 overly permissive RLS policies
   - Created 4 new role-specific UPDATE policies:
     - `crew_update_own_candidate_items` (CREW can edit own items if candidate)
     - `hod_approve_shopping_items` (HOD can approve)
     - `hod_reject_shopping_items` (HOD can reject)
     - `engineer_promote_shopping_items` (ENGINEER can promote)

2. **apps/api/handlers/shopping_list_handlers.py**
   - **Line 367-380**: Added `is_hod()` check to `approve_shopping_list_item`
   - **Line 592-605**: Added `is_hod()` check to `reject_shopping_list_item`
   - **Line 772-785**: Added `is_engineer()` check to `promote_candidate_to_part`
   - All return 403 with descriptive messages if role check fails

3. **tests/docker/run_shopping_list_rls_tests.py**
   - New comprehensive Docker test suite
   - 18 tests: 8 Role & CRUD + 4 Isolation + 6 Edge cases
   - Uses Docker environment with API at http://api:8000
   - Verifies RLS + handler role checks

4. **tests/docker/Dockerfile.test**
   - Added `run_shopping_list_rls_tests.py` to Docker image
   - Enables Docker-based RLS validation

5. **tests/ci/staging_shopping_list_acceptance.py**
   - New staging acceptance test suite
   - 9 tests: Action list filtering + CREW ops + HOD ops + ENGINEER ops
   - Runs against production API (https://api.celeste7.ai)
   - Validates backend authority principle

6. **docker-compose.test.yml**
   - Added resource limits to prevent OOM:
     - api: 2GB memory, 2.0 CPUs
     - test-runner: 1GB memory, 1.0 CPUs
   - Prevents exit code 137 (SIGKILL) issues

7. **docs/pipeline/TESTING_INFRASTRUCTURE.md**
   - Added Section 9: Exit Code 137 & Resource Management
   - OOM vs manual kill diagnosis
   - Resource hardening strategies
   - Post-mortem checklist

---

## Database Changes

### RLS Helper Functions (Pre-existing)

Shopping List Lens uses existing SECURITY DEFINER functions:

**Function 1: is_hod()**
```sql
CREATE OR REPLACE FUNCTION public.is_hod(p_user_id uuid, p_yacht_id uuid)
RETURNS BOOLEAN AS $$
DECLARE
    v_role text;
BEGIN
    SELECT role INTO v_role
    FROM public.auth_users_roles
    WHERE user_id = p_user_id AND yacht_id = p_yacht_id;

    RETURN v_role IN (
        'chief_engineer',
        'chief_officer',
        'captain',
        'manager',
        'purser'  -- Senior HOD role
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;
```

**Function 2: is_engineer()**
```sql
CREATE OR REPLACE FUNCTION public.is_engineer(p_user_id uuid, p_yacht_id uuid)
RETURNS BOOLEAN AS $$
DECLARE
    v_role text;
BEGIN
    SELECT role INTO v_role
    FROM public.auth_users_roles
    WHERE user_id = p_user_id AND yacht_id = p_yacht_id;

    RETURN v_role IN (
        'chief_engineer',
        'engineer',
        'manager'
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;
```

**Function 3: get_user_yacht_id()**
```sql
CREATE OR REPLACE FUNCTION public.get_user_yacht_id()
RETURNS UUID AS $$
BEGIN
    -- Extracts yacht_id from JWT claims
    RETURN NULLIF(current_setting('request.jwt.claims', true)::json->>'yacht_id', '')::uuid;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;
```

---

### Migration: RLS Policy Fix

**File**: `supabase/migrations/20260128_shopping_list_rls_fix.sql`

**Purpose**: Replace overly permissive RLS policies with role-specific policies

**Changes**:

**Step 1: Drop Old Policies**
```sql
DROP POLICY IF EXISTS "crew_update_shopping" ON pms_shopping_list_items;
DROP POLICY IF EXISTS "hod_update_shopping" ON pms_shopping_list_items;
DROP POLICY IF EXISTS "manager_all_shopping" ON pms_shopping_list_items;
DROP POLICY IF EXISTS "enable_update_for_users_based_on_user_id" ON pms_shopping_list_items;
DROP POLICY IF EXISTS "enable_update_for_authenticated_users_based_on_yacht_id" ON pms_shopping_list_items;
```

**Step 2: Create New Role-Specific Policies**

**Policy 1: CREW Update Own Candidate Items**
```sql
CREATE POLICY "crew_update_own_candidate_items"
ON pms_shopping_list_items
FOR UPDATE
TO authenticated
USING (
    yacht_id = public.get_user_yacht_id()
    AND created_by = auth.uid()
    AND status = 'candidate'
)
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
    AND status = 'candidate'
);
```
- CREW can only edit items they created
- Only if status is still 'candidate'
- Yacht isolation enforced

**Policy 2: HOD Approve Items**
```sql
CREATE POLICY "hod_approve_shopping_items"
ON pms_shopping_list_items
FOR UPDATE
TO authenticated
USING (
    yacht_id = public.get_user_yacht_id()
    AND public.is_hod(auth.uid(), public.get_user_yacht_id())
    AND (
        status IN ('candidate', 'under_review', 'approved')
        OR approved_by IS NOT NULL
    )
)
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
);
```
- Only HOD can approve
- Allows setting approved_by and approved_at
- Yacht isolation enforced

**Policy 3: HOD Reject Items**
```sql
CREATE POLICY "hod_reject_shopping_items"
ON pms_shopping_list_items
FOR UPDATE
TO authenticated
USING (
    yacht_id = public.get_user_yacht_id()
    AND public.is_hod(auth.uid(), public.get_user_yacht_id())
    AND (
        status IN ('candidate', 'under_review')
        OR rejected_by IS NOT NULL
    )
)
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
);
```
- Only HOD can reject
- Allows setting rejected_at, rejected_by, rejection_reason
- Yacht isolation enforced

**Policy 4: ENGINEER Promote Items**
```sql
CREATE POLICY "engineer_promote_shopping_items"
ON pms_shopping_list_items
FOR UPDATE
TO authenticated
USING (
    yacht_id = public.get_user_yacht_id()
    AND public.is_engineer(auth.uid(), public.get_user_yacht_id())
    AND (
        is_candidate_part = true
        OR promoted_by IS NOT NULL
    )
)
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
);
```
- Only ENGINEER can promote
- Only if is_candidate_part=true
- Allows setting promoted_to_part_id, promoted_by, promoted_at
- Yacht isolation enforced

**SQL Denial Proof** (from PHASE3 evidence):
```sql
-- Set JWT context to CREW role
SET ROLE authenticated;
SET request.jwt.claims = '{"sub": "crew-user-id", "yacht_id": "yacht-123", "role": "crew"}';

-- Attempt approve (RLS blocks)
UPDATE pms_shopping_list_items
SET status = 'approved', approved_by = 'crew-user-id', approved_at = NOW()
WHERE id = 'item-456';
-- Result: 0 rows updated ✓

-- Attempt reject (RLS blocks)
UPDATE pms_shopping_list_items
SET rejected_at = NOW(), rejected_by = 'crew-user-id', rejection_reason = 'test'
WHERE id = 'item-456';
-- Result: 0 rows updated ✓

-- Attempt promote (RLS blocks)
UPDATE pms_shopping_list_items
SET promoted_to_part_id = 'part-789', promoted_by = 'crew-user-id'
WHERE id = 'item-456';
-- Result: 0 rows updated ✓
```

---

## API Endpoints

### Base URLs
- **Production**: `https://api.celeste7.ai`
- **Staging**: `https://api-staging.celeste7.ai`
- **Local**: `http://localhost:8000`

### Authentication
All requests require JWT Bearer token:
```bash
curl -H "Authorization: Bearer $JWT" \
     -H "Content-Type: application/json" \
     ...
```

---

### Endpoint 1: Create Shopping List Item

**Action ID**: `create_shopping_list_item`
**Endpoint**: `POST /v1/actions/execute`
**Variant**: MUTATE
**Roles**: All authenticated users

**Request**:
```json
{
  "action": "create_shopping_list_item",
  "context": {
    "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"
  },
  "payload": {
    "item_name": "Hydraulic Oil Filter",
    "quantity": 12,
    "source_type": "wo",
    "is_candidate_part": true,
    "manufacturer": "Parker",
    "model_number": "926170",
    "urgency": "normal_priority",
    "estimated_cost": 324.50,
    "item_description": "Main hydraulic system filter replacement"
  }
}
```

**Response (200 OK)**:
```json
{
  "status": "success",
  "data": {
    "id": "288ee9e6-2e3c-43d5-9e01-83a04f2d5d26",
    "item_name": "Hydraulic Oil Filter",
    "quantity": 12,
    "status": "candidate",
    "source_type": "wo",
    "is_candidate_part": true,
    "manufacturer": "Parker",
    "model_number": "926170",
    "urgency": "normal_priority",
    "estimated_cost": 324.50,
    "created_at": "2026-01-28T12:00:00Z",
    "created_by": "user-uuid"
  }
}
```

**Errors**:
- 400: Invalid item_name length, quantity out of range, invalid source_type
- 401: Not authenticated
- 403: Missing yacht_id in JWT claims

---

### Endpoint 2: Approve Shopping List Item

**Action ID**: `approve_shopping_list_item`
**Endpoint**: `POST /v1/actions/execute`
**Variant**: MUTATE
**Roles**: HOD only (chief_engineer, chief_officer, captain, manager, purser)

**Request**:
```json
{
  "action": "approve_shopping_list_item",
  "context": {
    "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"
  },
  "payload": {
    "item_id": "288ee9e6-2e3c-43d5-9e01-83a04f2d5d26",
    "quantity_approved": 12,
    "notes": "Approved for Q1 maintenance cycle"
  }
}
```

**Response (200 OK)**:
```json
{
  "status": "success",
  "data": {
    "id": "288ee9e6-2e3c-43d5-9e01-83a04f2d5d26",
    "status": "approved",
    "quantity_approved": 12,
    "approved_by": "hod-user-uuid",
    "approved_at": "2026-01-28T12:05:00Z",
    "notes": "Approved for Q1 maintenance cycle"
  }
}
```

**Errors**:
- 400: Item already approved/rejected, invalid quantity_approved
- 403: User not HOD (returns descriptive message)
- 404: Item not found or wrong yacht

**Error Message Example (403)**:
```json
{
  "status": "error",
  "error_code": "FORBIDDEN",
  "detail": "Only HoD (chief engineer, chief officer, captain, manager) can approve shopping list items"
}
```

---

### Endpoint 3: Reject Shopping List Item

**Action ID**: `reject_shopping_list_item`
**Endpoint**: `POST /v1/actions/execute`
**Variant**: MUTATE
**Roles**: HOD only (chief_engineer, chief_officer, captain, manager, purser)

**Request**:
```json
{
  "action": "reject_shopping_list_item",
  "context": {
    "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"
  },
  "payload": {
    "item_id": "288ee9e6-2e3c-43d5-9e01-83a04f2d5d26",
    "rejection_reason": "Over budget - use existing stock instead",
    "notes": "Inventory shows 8 units available in storage"
  }
}
```

**Response (200 OK)**:
```json
{
  "status": "success",
  "data": {
    "id": "288ee9e6-2e3c-43d5-9e01-83a04f2d5d26",
    "status": "candidate",
    "rejected_at": "2026-01-28T12:05:00Z",
    "rejected_by": "hod-user-uuid",
    "rejection_reason": "Over budget - use existing stock instead",
    "notes": "Inventory shows 8 units available in storage"
  }
}
```

**Errors**:
- 400: Item already rejected/approved, missing rejection_reason
- 403: User not HOD (returns descriptive message)
- 404: Item not found or wrong yacht

**Note**: Status remains 'candidate', rejection indicated by rejected_at field

---

### Endpoint 4: Promote Candidate to Part

**Action ID**: `promote_candidate_to_part`
**Endpoint**: `POST /v1/actions/execute`
**Variant**: MUTATE
**Roles**: Engineers only (chief_engineer, engineer, manager)

**Request**:
```json
{
  "action": "promote_candidate_to_part",
  "context": {
    "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"
  },
  "payload": {
    "item_id": "288ee9e6-2e3c-43d5-9e01-83a04f2d5d26",
    "part_name": "Hydraulic Oil Filter - Parker 926170",
    "part_number": "PARKER-926170",
    "manufacturer": "Parker Hannifin",
    "model_number": "926170",
    "description": "Main hydraulic system filter - 12 micron rating",
    "category": "filters"
  }
}
```

**Response (200 OK)**:
```json
{
  "status": "success",
  "data": {
    "shopping_list_item_id": "288ee9e6-2e3c-43d5-9e01-83a04f2d5d26",
    "status": "approved",
    "promoted_to_part_id": "part-uuid-123",
    "promoted_by": "engineer-user-uuid",
    "promoted_at": "2026-01-28T12:10:00Z",
    "new_part": {
      "id": "part-uuid-123",
      "part_name": "Hydraulic Oil Filter - Parker 926170",
      "part_number": "PARKER-926170",
      "manufacturer": "Parker Hannifin",
      "created_at": "2026-01-28T12:10:00Z"
    }
  }
}
```

**Errors**:
- 400: Item not candidate part, not approved, missing part_name/part_number
- 403: User not engineer (returns descriptive message)
- 404: Item not found or wrong yacht
- 409: Part number already exists in catalog

**Error Message Example (403)**:
```json
{
  "status": "error",
  "error_code": "FORBIDDEN",
  "detail": "Only engineers (chief engineer, ETO, engineer, manager) can promote candidates to parts catalog"
}
```

---

### Endpoint 5: View Shopping List Item History

**Action ID**: `view_shopping_list_item_history`
**Endpoint**: `POST /v1/actions/execute`
**Variant**: READ
**Roles**: All authenticated users

**Request**:
```json
{
  "action": "view_shopping_list_item_history",
  "context": {
    "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"
  },
  "payload": {
    "item_id": "288ee9e6-2e3c-43d5-9e01-83a04f2d5d26"
  }
}
```

**Response (200 OK)**:
```json
{
  "status": "success",
  "data": {
    "item_id": "288ee9e6-2e3c-43d5-9e01-83a04f2d5d26",
    "history": [
      {
        "from_status": null,
        "to_status": "candidate",
        "changed_by": "crew-user-uuid",
        "changed_at": "2026-01-28T12:00:00Z",
        "notes": "Item created"
      },
      {
        "from_status": "candidate",
        "to_status": "approved",
        "changed_by": "hod-user-uuid",
        "changed_at": "2026-01-28T12:05:00Z",
        "notes": "Approved for Q1 maintenance cycle"
      },
      {
        "from_status": "approved",
        "to_status": "promoted",
        "changed_by": "engineer-user-uuid",
        "changed_at": "2026-01-28T12:10:00Z",
        "notes": "Promoted to parts catalog as PARKER-926170"
      }
    ]
  }
}
```

**Errors**:
- 404: Item not found or wrong yacht

---

## Testing Infrastructure

### Test Files

1. **tests/docker/run_shopping_list_rls_tests.py**
   - Comprehensive Docker RLS validation
   - 18 tests total:
     - 8 Role & CRUD tests (CREW, HOD, ENGINEER operations)
     - 4 Isolation tests (anonymous, cross-yacht, yacht filtering)
     - 6 Edge case tests (validation, double operations)
   - Runs in Docker environment with API at http://api:8000
   - Uses 3 test users: crew, hod, engineer (HOD doubles as engineer)

2. **tests/ci/staging_shopping_list_acceptance.py**
   - Production API acceptance tests
   - 9 tests total:
     - Action list filtering (CREW vs HOD)
     - CREW operations (create=200, approve/reject/promote=403)
     - HOD operations (approve=200, reject=200)
     - ENGINEER operations (promote=200)
   - Runs against staging/production API
   - Validates backend authority principle

### Test Users

**Docker Environment** (docker-compose.test.yml):
```bash
CREW_EMAIL=crew.test@alex-short.com
HOD_EMAIL=hod.test@alex-short.com  # role: chief_engineer
ENGINEER_EMAIL=hod.test@alex-short.com  # Same user (chief_engineer has both permissions)
TEST_PASSWORD=Password2!
```

**Staging/Production**:
- Same users as Docker environment
- JWT tokens obtained via MASTER Supabase auth

### Running Docker Tests

```bash
# Terminal 1: Start Docker environment
docker-compose -f docker-compose.test.yml up --build

# Terminal 2: Run tests
docker exec -it <test-runner-container> python3 /app/run_shopping_list_rls_tests.py

# Or inline environment:
MASTER_SUPABASE_URL="..." \
TENANT_SUPABASE_URL="..." \
YACHT_ID="..." \
API_BASE="http://api:8000" \
python3 tests/docker/run_shopping_list_rls_tests.py
```

**Expected Output**:
```
================================================================================
TEST SUMMARY
================================================================================

  [PASS] CREW create_shopping_list_item
  [PASS] CREW approve_shopping_list_item denied (403)
  [PASS] CREW reject_shopping_list_item denied (403)
  [PASS] CREW promote_candidate_to_part denied (403)
  [PASS] HOD create_shopping_list_item
  [PASS] HOD approve_shopping_list_item (200)
  [PASS] HOD reject_shopping_list_item (200)
  [PASS] ENGINEER promote_candidate_to_part (200)
  [PASS] Anonymous read denied (401)
  [PASS] Anonymous mutate denied (401)
  [PASS] Cross-yacht mutate denied (403)
  [PASS] Read items yacht-filtered
  [PASS] Invalid quantity returns 400
  [PASS] Approve non-existent returns 404
  [PASS] Double reject denied (400)
  [PASS] Promote non-candidate returns 400
  [PASS] Invalid source_type returns 400
  [PASS] View history non-existent returns 404

Total: 18/18 passed
Failed: 0
5xx errors: 0

✅ All Shopping List Lens Docker tests passed.
✅ 0×500 requirement met (no 5xx errors)
```

### Running Staging Tests

```bash
# Set staging API URL
export STAGING_API_BASE=https://api.celeste7.ai

# Run staging acceptance tests
python3 tests/ci/staging_shopping_list_acceptance.py
```

**Expected Output**:
```
================================================================================
TEST SUMMARY
================================================================================
  ✅ PASS: CREW action list filtering
  ✅ PASS: HOD action list filtering
  ✅ PASS: CREW create item (288ee9e6-2e3c-43d5-9e01-83a04f2d5d26)
  ✅ PASS: CREW approve blocked (403)
  ✅ PASS: CREW reject blocked (403)
  ✅ PASS: CREW promote blocked (403)
  ✅ PASS: HOD approve (200)
  ✅ PASS: HOD reject (200)
  ✅ PASS: ENGINEER promote (200)

Total: 9/9 passed

✅ 0×500 requirement met (no 5xx errors)
```

### Test Evidence Files

**Location**: `/tmp/`

1. `/tmp/shopping_list_docker_rls_FINAL.txt` - Docker test results (18/18)
2. `/tmp/staging_shopping_list_acceptance_FINAL.txt` - Staging results (9/9)
3. `/tmp/shopping_list_sprint_complete.md` - Complete sprint report

---

## Documentation Deliverables

All files in `/docs/architecture/20_SHOPPING_LIST_LENS/`:

### 1. Architecture Documentation

**SHOPPING_LIST_LENS_V1.md**
- Complete technical reference
- 5 actions with detailed specs
- Database schema, state machine, security layers
- For: Backend engineers implementing features

### 2. Microaction Catalog

**SHOPPING_LIST_LENS_V1_MICROACTION_CATALOG.md**
- 5 actions with 12 information dimensions each
- Identification, Access Control, Interface, Triggers, Preconditions
- Validation Rules, Side Effects, Related Actions
- Success States, Error States, UI Surfacing, Examples
- For: Product managers, QA engineers, frontend engineers

### 3. Visual Flowcharts

**SHOPPING_LIST_LENS_V1_FLOWCHARTS.md**
- 6 Mermaid flowcharts showing all decision paths:
  - Master Journey Map (role-gated paths)
  - Create Flow (validation checks)
  - Approve Flow (HOD workflow)
  - Reject Flow (HOD workflow)
  - Promote Flow (Engineer workflow)
  - Role Permission Matrix
- 4 complete user journey examples
- Field requirement summary table
- State machine diagram
- For: Frontend engineers, UI/UX designers, QA

### 4. This Document

**SHOPPING_LIST_LENS_V1_ENGINEER_HANDOFF.md**
- Complete context for next engineer
- What was built, how it works, how to continue
- For: Next engineer on the project

### Pipeline Evidence Documents

**Location**: `/docs/pipeline/shopping_list_lens/`

1. **PHASE3_DOCKER_RLS_RESULTS.md**
   - RLS policy DDL
   - Handler role check code
   - SQL denial proofs
   - Docker test transcripts

2. **PHASE4_STAGING_ACCEPTANCE_RESULTS.md**
   - HTTP request/response transcripts
   - Action list filtering proofs
   - Backend authority validation

---

## How to Continue Work

### If You Need to Add a New Action

1. **Define the Action**:
   - Add to `apps/api/action_router/registry.py`
   - Set `action_id`, `label`, `variant` (READ/MUTATE/SIGNED)
   - Define `allowed_roles`, `required_fields`, `endpoint`

2. **Implement Handler**:
   - Add to `apps/api/handlers/shopping_list_handlers.py`
   - Follow naming: `_action_name_adapter(handlers: ShoppingListHandlers)`
   - **Critical**: Add explicit role checks if using service key
   - Return to `get_shopping_list_handlers()` dictionary

3. **Create RLS Policy** (if needed):
   - Create migration in `supabase/migrations/`
   - Use `SECURITY DEFINER` helpers (is_hod, is_engineer)
   - Test with SQL denial proof

4. **Add Tests**:
   - Docker test in `tests/docker/run_shopping_list_rls_tests.py`
   - Staging test in `tests/ci/staging_shopping_list_acceptance.py`
   - Test all roles (CREW, HOD, ENGINEER)
   - Verify 403 responses for unauthorized roles

5. **Update Documentation**:
   - Add to microaction catalog
   - Create flowchart if complex
   - Update engineer handoff

### If You Need to Modify State Machine

**Current states**: candidate → approved/rejected (terminal), approved → promoted

**To add new state**:

1. **Database**:
   ```sql
   -- Check if status column needs updating (currently only 'candidate' and 'approved')
   -- Most state is tracked via timestamp fields (rejected_at, promoted_at)
   ```

2. **Handler Logic**:
   - Update validation in relevant handlers
   - Add new timestamp/reference fields if needed
   - Update state transition logic

3. **RLS Policies**:
   - Update USING clauses to account for new state
   - Test SQL denial proofs

4. **Documentation**:
   - Update state machine diagram in FLOWCHARTS.md
   - Update action catalog preconditions
   - Update architecture docs

### If You Need to Add New Role Check

Example: Add "chief_steward can approve food-related items"

1. **Handler Logic** (`shopping_list_handlers.py`):
   ```python
   # Check if item is food-related
   if item.category == "food":
       # Allow chief_steward in addition to HOD
       is_chief_steward = self.db.rpc("is_chief_steward", {
           "p_user_id": user_id,
           "p_yacht_id": yacht_id
       }).execute()

       if not (is_hod_result.data or is_chief_steward.data):
           return 403
   ```

2. **RLS Policy Update**:
   ```sql
   -- Add chief_steward to approve policy for food items
   CREATE POLICY "chief_steward_approve_food_items" ...
   ```

3. **Tests**:
   - Add chief_steward JWT persona
   - Test approve food item (200)
   - Test approve non-food item (403)

4. **Documentation**:
   - Update role permission matrix
   - Update approve flowchart
   - Update catalog access control

### If You Need to Debug Production Issues

**Check Logs**:
```bash
# Render logs (production API)
# Look for:
# - "Non-HoD attempted approve" → Role check failed
# - "Only HoD can approve shopping list items" → Expected 403
# - "Item not found" → Wrong yacht or doesn't exist
```

**Common Issues**:

1. **CREW Getting 200 Instead of 403**:
   - Check handler has explicit `is_hod()` or `is_engineer()` check
   - RLS policies protect direct SQL, but handlers use service keys
   - Handler MUST explicitly check roles

2. **Items Not Appearing in List**:
   - Check yacht_id in JWT matches item yacht_id
   - Check RLS SELECT policies allow read access
   - Check item not rejected (rejected_at IS NULL for active candidates)

3. **Approve/Reject Failing**:
   - Check item status='candidate'
   - Check rejected_at IS NULL (can't approve rejected items)
   - Check user has HOD role via `is_hod()`

4. **Promote Failing**:
   - Check is_candidate_part=true
   - Check status='approved'
   - Check user has engineer role via `is_engineer()`
   - Check part_number doesn't already exist (409 conflict)

---

## Quick Reference

### Key Files

| File | Purpose | Location |
|------|---------|----------|
| shopping_list_handlers.py | Handler implementations | apps/api/handlers/ |
| registry.py | Action definitions | apps/api/action_router/ |
| 20260128_shopping_list_rls_fix.sql | RLS policies | supabase/migrations/ |
| run_shopping_list_rls_tests.py | Docker tests | tests/docker/ |
| staging_shopping_list_acceptance.py | Staging tests | tests/ci/ |

### Key Concepts

| Concept | Description |
|---------|-------------|
| **State Machine** | candidate → approved/rejected (terminal), approved can be promoted |
| **Role Hierarchy** | CREW (create) → ENGINEER (promote) → HOD (approve/reject) → captain/manager (all) |
| **Defense-in-Depth** | 3 layers: Router (allowed_roles) → Handler (is_hod/is_engineer) → Database (RLS) |
| **Backend Authority** | UI renders only actions returned by /v1/actions/list (filtered by role) |
| **Service Key Bypass** | Handlers use service keys which BYPASS RLS - must explicitly check roles |
| **0×500 Requirement** | Zero 5xx errors in tests - 500 is always a failure |
| **Expected 4xx** | Client errors (403, 404, 400) are PASS when explicitly asserted |

### Test Credentials

**Test Users** (Production/Staging):
- crew.test@alex-short.com (crew role)
- hod.test@alex-short.com (chief_engineer role - has both HOD and engineer permissions)

**Test Yacht**: `85fe1119-b04c-41ac-80f1-829d23322598` (yTEST_YACHT_001)

**Supabase Instances**:
- MASTER: `qvzmkaamzaqxpzbewjxe.supabase.co` (auth/user lookup)
- TENANT: `vzsohavtuotocgrfkfyd.supabase.co` (yacht data)

### Commits

**Shopping List Lens v1** commits pushed to main:

1. `4c3b051` - Add explicit role checks to Shopping List handlers
2. `612fc23` - Add Shopping List RLS Docker tests (18/18 passing)
3. `3959d1a` - Add staging acceptance tests (9/9 passing)
4. `5ddb2b3` - Document Shopping List Lens test evidence (Phases 3 & 4)
5. `31d32bb` - Harden test infrastructure to prevent OOM kills (exit 137)

### Production Status

- **Status**: ✅ Production Ready (100% tests passing)
- **API**: https://api.celeste7.ai
- **Tests**: 27/27 passing (18 Docker + 9 Staging)
- **5xx Errors**: 0 (0×500 requirement met)
- **Actions**: All 5 registered and working

---

## Contact Points

### Code Locations

**Handlers**: `/apps/api/handlers/shopping_list_handlers.py`
- Lines 367-380: approve role check
- Lines 592-605: reject role check
- Lines 772-785: promote role check

**Registry**: `/apps/api/action_router/registry.py`
- Shopping list action definitions

**Migration**: `/supabase/migrations/20260128_shopping_list_rls_fix.sql`
- 4 RLS policies for role-based access

**Tests**:
- `/tests/docker/run_shopping_list_rls_tests.py` (18 tests)
- `/tests/ci/staging_shopping_list_acceptance.py` (9 tests)

### Documentation Locations

**All docs in**: `/docs/architecture/20_SHOPPING_LIST_LENS/`

Files:
1. SHOPPING_LIST_LENS_V1.md
2. SHOPPING_LIST_LENS_V1_MICROACTION_CATALOG.md
3. SHOPPING_LIST_LENS_V1_FLOWCHARTS.md
4. SHOPPING_LIST_LENS_V1_ENGINEER_HANDOFF.md (this file)

**Evidence docs in**: `/docs/pipeline/shopping_list_lens/`

Files:
1. PHASE3_DOCKER_RLS_RESULTS.md
2. PHASE4_STAGING_ACCEPTANCE_RESULTS.md

---

## Summary for Next Engineer

**What You're Getting**:
- ✅ Fully tested Shopping List Lens v1 with 5 actions
- ✅ Complete handler implementations with role checks
- ✅ Database RLS policies applied and verified
- ✅ Comprehensive test suite (27/27 passing)
- ✅ Full documentation (architecture, flowcharts, catalog)
- ✅ Production-ready with 0×500 met
- ✅ Infrastructure hardened (resource limits)

**What Works**:
- All 5 shopping list actions registered
- Role-based permissions enforced (3-layer defense)
- CREW can create items
- HOD can approve/reject items
- ENGINEER can promote candidates to parts catalog
- RLS policies block unauthorized SQL access
- Handler role checks block unauthorized API access
- Backend authority principle validated
- Yacht isolation enforced

**What's Next** (if you need to extend):
- Add bulk operations (approve multiple items at once)
- Add purchase order integration (link approved items to PO)
- Add vendor management (suggest vendors for parts)
- Add cost approval workflows (require captain signature for >$X items)
- Add item prioritization/sorting (by urgency, estimated_cost)
- Add item search/filtering (by status, source_type, is_candidate_part)
- Add notifications (notify crew when item approved/rejected)

**Start Here**:
1. Read `SHOPPING_LIST_LENS_V1.md` for architecture
2. Review `SHOPPING_LIST_LENS_V1_FLOWCHARTS.md` for visual understanding
3. Run Docker tests locally to verify everything works
4. Check production API to see actions in action
5. Review this handoff document when making changes

---

**Document Created**: 2026-01-28
**Engineer Handoff**: Complete ✅
**Shopping List Lens v1**: Production Ready 🚀
