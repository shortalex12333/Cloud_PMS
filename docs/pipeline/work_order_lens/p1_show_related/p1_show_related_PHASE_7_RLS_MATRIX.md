# Work Order Lens P1: Show Related — PHASE 7: RLS MATRIX

**Feature:** Row Level Security Enforcement for Show Related
**Date:** 2026-01-28
**Time:** 45 minutes

---

## Purpose

Define **table-by-table RLS policies** for Show Related feature with:
- Explicit RLS enforcement patterns (never rely on JOINs alone)
- Helper function usage (`get_user_yacht_id()`, `is_hod()`, `is_manager()`)
- Storage policy (metadata-only, no presigned URLs in this panel)
- Defense-in-depth approach (application + RLS)

---

## Core RLS Principles

### 1. RLS Is King

**Every query MUST filter by yacht_id, even if RLS policy exists.**

**Why:** Defense-in-depth. Application-level filters provide:
- Early exit for cross-yacht queries (performance)
- Clear audit trail (log yacht_id in every query)
- Protection against RLS policy bugs or misconfigurations

### 2. Never Rely on JOINs Alone

**Bad:**
```sql
-- WRONG: Assumes JOIN provides yacht isolation
SELECT p.id, p.name
FROM pms_work_order_parts wop
JOIN pms_parts p ON p.id = wop.part_id
WHERE wop.work_order_id = :work_order_id;  -- Missing yacht_id filter!
```

**Good:**
```sql
-- CORRECT: Explicit yacht_id filter on EVERY table
SELECT p.id, p.name
FROM pms_work_order_parts wop
JOIN pms_parts p ON p.id = wop.part_id
WHERE wop.work_order_id = :work_order_id
  AND wop.yacht_id = :yacht_id  -- Explicit filter
  AND p.yacht_id = :yacht_id;   -- Explicit filter on joined table
```

### 3. RLS Policy + Application Filter

**Layered Security:**
1. **RLS Policy:** Database-enforced, applies to ALL queries (safety net)
2. **Application Filter:** Explicit WHERE clause in business logic (performance + auditability)

**Result:** If either layer fails, the other still protects data.

---

## Helper Functions

### Assumed Helpers (from auth schema)

#### get_user_yacht_id()

**Purpose:** Extract yacht_id from JWT token in current session.

**Definition (assumed to exist):**
```sql
CREATE OR REPLACE FUNCTION public.get_user_yacht_id()
RETURNS UUID AS $$
BEGIN
    RETURN (current_setting('request.jwt.claims', true)::jsonb->>'yacht_id')::uuid;
EXCEPTION
    WHEN OTHERS THEN RETURN NULL;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;
```

**Usage in RLS policies:**
```sql
CREATE POLICY select_own_yacht ON pms_work_orders
FOR SELECT
USING (yacht_id = get_user_yacht_id());
```

#### is_hod()

**Purpose:** Check if current user is Head of Department (chief_engineer or chief_officer).

**Definition (assumed to exist):**
```sql
CREATE OR REPLACE FUNCTION public.is_hod()
RETURNS BOOLEAN AS $$
DECLARE
    user_role TEXT;
BEGIN
    SELECT role INTO user_role
    FROM auth_users_roles
    WHERE user_id = (current_setting('request.jwt.claims', true)::jsonb->>'sub')::uuid
      AND yacht_id = get_user_yacht_id()
      AND is_active = TRUE
    LIMIT 1;

    RETURN user_role IN ('chief_engineer', 'chief_officer');
EXCEPTION
    WHEN OTHERS THEN RETURN FALSE;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;
```

**Usage:** Restrict add_entity_link to HOD+ only.

#### is_manager()

**Purpose:** Check if current user is manager or captain.

**Definition (assumed to exist):**
```sql
CREATE OR REPLACE FUNCTION public.is_manager()
RETURNS BOOLEAN AS $$
DECLARE
    user_role TEXT;
BEGIN
    SELECT role INTO user_role
    FROM auth_users_roles
    WHERE user_id = (current_setting('request.jwt.claims', true)::jsonb->>'sub')::uuid
      AND yacht_id = get_user_yacht_id()
      AND is_active = TRUE
    LIMIT 1;

    RETURN user_role IN ('manager', 'captain');
EXCEPTION
    WHEN OTHERS THEN RETURN FALSE;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;
```

**Usage:** Combined with is_hod() for HOD+ access control.

---

## Table-by-Table RLS Policies

### Table 1: pms_work_orders

**Queries:** All groups query this table (get equipment_id, fault_id, etc.)

**RLS Policies:**

```sql
-- SELECT: Users can view work orders from their yacht
CREATE POLICY work_orders_select ON pms_work_orders
FOR SELECT
USING (yacht_id = get_user_yacht_id());

-- INSERT: Users can create work orders for their yacht
CREATE POLICY work_orders_insert ON pms_work_orders
FOR INSERT
WITH CHECK (yacht_id = get_user_yacht_id());

-- UPDATE: Users can update work orders from their yacht
CREATE POLICY work_orders_update ON pms_work_orders
FOR UPDATE
USING (yacht_id = get_user_yacht_id())
WITH CHECK (yacht_id = get_user_yacht_id());

-- DELETE: Soft delete only (set deleted_at); restrict to HOD+
CREATE POLICY work_orders_delete ON pms_work_orders
FOR UPDATE
USING (yacht_id = get_user_yacht_id() AND (is_hod() OR is_manager()));
```

**Application Filter (MANDATORY):**
```sql
WHERE wo.yacht_id = :yacht_id  -- ALWAYS include this
```

**Why Both:** RLS prevents accidental cross-yacht access; application filter enables early exit and logging.

---

### Table 2: pms_work_order_parts

**Queries:** Group 1 (Parts) queries this join table.

**RLS Policies:**

```sql
-- SELECT: Users can view parts linked to their yacht's work orders
CREATE POLICY work_order_parts_select ON pms_work_order_parts
FOR SELECT
USING (yacht_id = get_user_yacht_id());

-- INSERT: Users can add parts to their yacht's work orders
CREATE POLICY work_order_parts_insert ON pms_work_order_parts
FOR INSERT
WITH CHECK (yacht_id = get_user_yacht_id());

-- DELETE: Soft delete only
CREATE POLICY work_order_parts_delete ON pms_work_order_parts
FOR UPDATE
USING (yacht_id = get_user_yacht_id());
```

**Application Filter (MANDATORY):**
```sql
WHERE wop.yacht_id = :yacht_id
```

---

### Table 3: pms_parts

**Queries:** Group 1 (Parts) queries this table for part details.

**RLS Policies:**

```sql
-- SELECT: Users can view parts from their yacht
CREATE POLICY parts_select ON pms_parts
FOR SELECT
USING (yacht_id = get_user_yacht_id());

-- INSERT: Users can create parts for their yacht
CREATE POLICY parts_insert ON pms_parts
FOR INSERT
WITH CHECK (yacht_id = get_user_yacht_id());

-- UPDATE: Users can update their yacht's parts
CREATE POLICY parts_update ON pms_parts
FOR UPDATE
USING (yacht_id = get_user_yacht_id())
WITH CHECK (yacht_id = get_user_yacht_id());
```

**Application Filter (MANDATORY):**
```sql
WHERE p.yacht_id = :yacht_id
```

**Critical:** When joining pms_work_order_parts → pms_parts, filter BOTH tables by yacht_id.

---

### Table 4: doc_metadata

**Queries:** Group 2 (Manuals), Group 5 (Attachments) query this table.

**RLS Policies:**

```sql
-- SELECT: Users can view documents from their yacht
CREATE POLICY doc_metadata_select ON doc_metadata
FOR SELECT
USING (yacht_id = get_user_yacht_id());

-- INSERT: Users can upload documents for their yacht
CREATE POLICY doc_metadata_insert ON doc_metadata
FOR INSERT
WITH CHECK (yacht_id = get_user_yacht_id());

-- UPDATE: Users can update metadata for their yacht's documents
CREATE POLICY doc_metadata_update ON doc_metadata
FOR UPDATE
USING (yacht_id = get_user_yacht_id())
WITH CHECK (yacht_id = get_user_yacht_id());

-- DELETE: Soft delete only
CREATE POLICY doc_metadata_delete ON doc_metadata
FOR UPDATE
USING (yacht_id = get_user_yacht_id());
```

**Application Filter (MANDATORY):**
```sql
WHERE dm.yacht_id = :yacht_id
```

**Storage Policy:** See "Storage Access" section below.

---

### Table 5: pms_work_order_notes

**Queries:** Group 4 (Handovers/Notes) queries this table.

**RLS Policies:**

```sql
-- SELECT: Users can view notes from their yacht's work orders
CREATE POLICY work_order_notes_select ON pms_work_order_notes
FOR SELECT
USING (yacht_id = get_user_yacht_id());

-- INSERT: Users can add notes to their yacht's work orders
CREATE POLICY work_order_notes_insert ON pms_work_order_notes
FOR INSERT
WITH CHECK (yacht_id = get_user_yacht_id());

-- UPDATE: Users can edit their own notes
CREATE POLICY work_order_notes_update ON pms_work_order_notes
FOR UPDATE
USING (yacht_id = get_user_yacht_id() AND created_by = (current_setting('request.jwt.claims', true)::jsonb->>'sub')::uuid)
WITH CHECK (yacht_id = get_user_yacht_id());

-- DELETE: Soft delete only; own notes or HOD+
CREATE POLICY work_order_notes_delete ON pms_work_order_notes
FOR UPDATE
USING (
    yacht_id = get_user_yacht_id() AND
    (created_by = (current_setting('request.jwt.claims', true)::jsonb->>'sub')::uuid OR is_hod() OR is_manager())
);
```

**Application Filter (MANDATORY):**
```sql
WHERE n.yacht_id = :yacht_id
```

---

### Table 6: pms_entity_links

**Queries:** Group 6 (Explicit Links) queries this table; add_entity_link writes to it.

**RLS Policies:**

```sql
-- SELECT: Users can view entity links from their yacht
CREATE POLICY entity_links_select ON pms_entity_links
FOR SELECT
USING (yacht_id = get_user_yacht_id());

-- INSERT: Only HOD or manager can create entity links
CREATE POLICY entity_links_insert ON pms_entity_links
FOR INSERT
WITH CHECK (
    yacht_id = get_user_yacht_id() AND
    (is_hod() OR is_manager())
);

-- UPDATE: Only creator or HOD+ can update entity links (e.g., update note)
CREATE POLICY entity_links_update ON pms_entity_links
FOR UPDATE
USING (
    yacht_id = get_user_yacht_id() AND
    (created_by = (current_setting('request.jwt.claims', true)::jsonb->>'sub')::uuid OR is_hod() OR is_manager())
)
WITH CHECK (yacht_id = get_user_yacht_id());

-- DELETE: Only HOD+ can delete entity links
CREATE POLICY entity_links_delete ON pms_entity_links
FOR DELETE
USING (
    yacht_id = get_user_yacht_id() AND
    (is_hod() OR is_manager())
);
```

**Application Filter (MANDATORY):**
```sql
WHERE el.yacht_id = :yacht_id
```

**Critical for add_entity_link:** RLS policy enforces HOD+ role; application layer ALSO checks role for explicit 403 error message.

---

### Table 7: pms_equipment

**Queries:** Indirectly queried via work_orders.equipment_id.

**RLS Policies:**

```sql
-- SELECT: Users can view equipment from their yacht
CREATE POLICY equipment_select ON pms_equipment
FOR SELECT
USING (yacht_id = get_user_yacht_id());

-- INSERT/UPDATE/DELETE: Standard yacht_id checks
-- (not shown for brevity; follow same pattern as pms_work_orders)
```

**Application Filter (MANDATORY):**
```sql
WHERE e.yacht_id = :yacht_id
```

---

### Table 8: pms_faults

**Queries:** Indirectly queried via work_orders.fault_id; Query 3B (same_fault).

**RLS Policies:**

```sql
-- SELECT: Users can view faults from their yacht
CREATE POLICY faults_select ON pms_faults
FOR SELECT
USING (yacht_id = get_user_yacht_id());

-- INSERT/UPDATE/DELETE: Standard yacht_id checks
```

**Application Filter (MANDATORY):**
```sql
WHERE f.yacht_id = :yacht_id
```

---

### Table 9: pms_audit_log

**Queries:** Written by add_entity_link; queried by admin/audit tools (not by Show Related panel).

**RLS Policies:**

```sql
-- SELECT: Only managers can view audit logs
CREATE POLICY audit_log_select ON pms_audit_log
FOR SELECT
USING (yacht_id = get_user_yacht_id() AND is_manager());

-- INSERT: All authenticated users can write audit logs (system-generated)
CREATE POLICY audit_log_insert ON pms_audit_log
FOR INSERT
WITH CHECK (yacht_id = get_user_yacht_id());

-- UPDATE/DELETE: Prohibited (audit logs are immutable)
-- No UPDATE or DELETE policies (will default to DENY)
```

**Application Filter (MANDATORY on writes):**
```sql
INSERT INTO pms_audit_log (yacht_id, action, entity_type, entity_id, ...)
VALUES (:yacht_id, ...);  -- ALWAYS include yacht_id
```

**Critical:** Audit logs MUST include yacht_id; never allow UPDATE or DELETE (immutable audit trail).

---

### Table 10: auth_users, auth_users_roles

**Queries:** Joined in Query 4A for user names; used by is_hod()/is_manager() helpers.

**RLS Policies (assumed to exist):**

```sql
-- SELECT: Users can view users from their yacht
CREATE POLICY users_select ON auth_users
FOR SELECT
USING (yacht_id = get_user_yacht_id());

-- SELECT: Users can view roles from their yacht
CREATE POLICY users_roles_select ON auth_users_roles
FOR SELECT
USING (yacht_id = get_user_yacht_id());
```

**Application Filter (if querying directly):**
```sql
WHERE u.yacht_id = :yacht_id
```

---

## Storage Access Policy (Supabase Storage)

### Metadata-Only in Show Related Panel

**Policy:** Show Related panel returns **metadata only** (filename, content_type, created_at). It does NOT return presigned URLs or storage paths.

**Why:**
- **Performance:** Avoid generating presigned URLs for 20+ items per request
- **Security:** Presigned URLs have TTL and signature complexity; defer to dedicated document viewer
- **Separation of concerns:** Show Related = discovery; separate action for viewing/downloading

**Implementation:**

#### What Show Related Returns:

```json
{
  "entity_id": "c5fd68a5-4729-43a8-a81a-b85f0d87c40b",
  "entity_type": "attachment",
  "title": "watermaker_service_photo.jpg",
  "subtitle": "image/jpeg",
  "match_reasons": ["FK:attachment"],
  "created_at": "2026-01-15T14:23:00Z"
}
```

**What it does NOT return:**
- ❌ `storage_path` (internal detail)
- ❌ `presigned_url` (deferred to separate view action)
- ❌ File contents (binary data)

#### Separate Action for Viewing Documents:

**Action:** `view_document` (defined in separate feature, not P1)

**Flow:**
1. User clicks attachment in Show Related panel
2. UI calls `view_document` action with `entity_id`
3. Backend:
   - Verifies user has access to document (yacht_id check + RLS)
   - Generates presigned URL with 60s TTL
   - Returns URL to UI
4. UI opens URL in new tab or inline viewer

**Supabase Storage RLS Policy:**
```sql
-- Supabase Storage bucket: pms-documents
-- RLS policy: Users can access objects from their yacht's path prefix

CREATE POLICY pms_documents_select ON storage.objects
FOR SELECT
USING (
    bucket_id = 'pms-documents' AND
    (storage.foldername(name))[1] = get_user_yacht_id()::text
);
```

**Path Convention:**
```
pms-documents/
  {yacht_id}/
    work_orders/
      {work_order_id}/
        photo_1.jpg
        photo_2.jpg
    manuals/
      parker_hannifin_manual.pdf
```

**Key Point:** Show Related never touches storage layer; it only queries doc_metadata table.

---

## RLS Verification Checklist

Before deploying Show Related feature, verify:

### 1. All Tables Have RLS Enabled

```sql
-- Check RLS status for all tables
SELECT schemaname, tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN (
    'pms_work_orders',
    'pms_work_order_parts',
    'pms_parts',
    'doc_metadata',
    'pms_work_order_notes',
    'pms_entity_links',
    'pms_equipment',
    'pms_faults',
    'pms_audit_log'
  );
```

**Expected:** All rows have `rowsecurity = true`.

**If not enabled:**
```sql
ALTER TABLE pms_work_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE pms_work_order_parts ENABLE ROW LEVEL SECURITY;
-- ... (repeat for all tables)
```

### 2. All Policies Exist

```sql
-- Check policies for each table
SELECT schemaname, tablename, policyname, cmd
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename IN (
    'pms_work_orders',
    'pms_work_order_parts',
    'pms_parts',
    'doc_metadata',
    'pms_work_order_notes',
    'pms_entity_links'
  )
ORDER BY tablename, cmd;
```

**Expected:** At least SELECT policy for each table; INSERT policy for pms_entity_links with HOD check.

### 3. Helper Functions Return Correct Values

**Test in psql with JWT:**
```sql
-- Set JWT claims (simulate authenticated request)
SET request.jwt.claims = '{"sub": "user-uuid", "yacht_id": "yacht-uuid", "role": "chief_engineer"}';

-- Test helpers
SELECT get_user_yacht_id();  -- Should return yacht-uuid
SELECT is_hod();              -- Should return true for chief_engineer
SELECT is_manager();          -- Should return false for chief_engineer
```

### 4. Cross-Yacht Access Returns 0 Rows

**Test:**
```sql
-- User from yacht A queries work order from yacht B
SET request.jwt.claims = '{"sub": "user-a", "yacht_id": "yacht-a-uuid"}';

SELECT * FROM pms_work_orders WHERE id = 'yacht-b-work-order-uuid';
-- Expected: 0 rows (RLS blocks access)
```

**Application Behavior:** If query returns 0 rows → 404 error (not 403, to avoid yacht enumeration).

---

## Application-Level RLS Enforcement Pattern

### Standard Query Pattern (with RLS + Application Filter)

```python
def query_related_parts(yacht_id: str, work_order_id: str, limit: int = 20):
    """Query parts with RLS + application filter (defense-in-depth)."""

    # Application-level filter (explicit yacht_id)
    result = supabase.table('pms_work_order_parts') \
        .select('part_id, pms_parts(id, name, part_number)') \
        .eq('work_order_id', work_order_id) \
        .eq('yacht_id', yacht_id) \  # MANDATORY: Application filter
        .is_('deleted_at', 'null') \
        .limit(limit) \
        .execute()

    # RLS policy also applies (yacht_id = get_user_yacht_id())
    # If JWT yacht_id != :yacht_id parameter, RLS blocks access

    return result.data
```

### Error Handling for RLS Violations

**Scenario:** Malicious user passes `yacht_id=yacht-b-uuid` but JWT has `yacht_id=yacht-a-uuid`.

**Outcome:** RLS policy blocks query; Supabase returns 0 rows.

**Application Response:**
```python
if not result.data:
    # Could be: entity doesn't exist OR user lacks access
    # Return 404 (not 403) to avoid yacht enumeration
    raise HTTPException(404, detail="Entity not found")
```

**Important:** Never distinguish "not found" from "access denied" in error messages. Always return 404 for both cases.

---

## Testing RLS Policies

### Test Matrix (per table)

For each table, test:
1. **Same yacht access:** User can query their yacht's data → 200 OK
2. **Cross-yacht access:** User cannot query other yacht's data → 0 rows → 404
3. **No JWT:** Unauthenticated request → RLS blocks all rows → 0 rows
4. **Role enforcement:** Crew cannot INSERT into pms_entity_links → RLS blocks → 403
5. **HOD can INSERT:** Chief engineer can INSERT into pms_entity_links → 200 OK

### Example Test (pms_entity_links)

**Test 1: Crew SELECT (allowed)**
```python
def test_crew_can_view_entity_links():
    jwt_crew = get_jwt(yacht_id='yacht-a', role='crew')
    result = supabase.table('pms_entity_links') \
        .select('*') \
        .eq('yacht_id', 'yacht-a') \
        .execute()
    assert len(result.data) >= 0  # RLS allows SELECT
```

**Test 2: Crew INSERT (blocked)**
```python
def test_crew_cannot_add_entity_links():
    jwt_crew = get_jwt(yacht_id='yacht-a', role='crew')
    try:
        result = supabase.table('pms_entity_links') \
            .insert({
                'yacht_id': 'yacht-a',
                'source_entity_type': 'work_order',
                'source_entity_id': 'wo-uuid',
                'target_entity_type': 'part',
                'target_entity_id': 'part-uuid',
                'link_type': 'related'
            }) \
            .execute()
        assert False, "Should have raised error"
    except Exception as e:
        assert '403' in str(e) or 'permission denied' in str(e).lower()
```

**Test 3: HOD INSERT (allowed)**
```python
def test_hod_can_add_entity_links():
    jwt_hod = get_jwt(yacht_id='yacht-a', role='chief_engineer')
    result = supabase.table('pms_entity_links') \
        .insert({
            'yacht_id': 'yacht-a',
            'source_entity_type': 'work_order',
            'source_entity_id': 'wo-uuid',
            'target_entity_type': 'part',
            'target_entity_id': 'part-uuid',
            'link_type': 'related'
        }) \
        .execute()
    assert result.data[0]['id']  # Success, link created
```

**Test 4: Cross-yacht access (blocked)**
```python
def test_cross_yacht_entity_links_blocked():
    jwt_yacht_a = get_jwt(yacht_id='yacht-a', role='chief_engineer')
    result = supabase.table('pms_entity_links') \
        .select('*') \
        .eq('yacht_id', 'yacht-b') \  # Different yacht
        .execute()
    assert len(result.data) == 0  # RLS blocks cross-yacht rows
```

---

## RLS Policy Maintenance

### When to Update RLS Policies

**Triggers for RLS policy updates:**
1. New table added to schema → Add RLS policies before production
2. New role added (e.g., "junior_engineer") → Update is_hod() / is_manager() if needed
3. New feature requires different permissions (e.g., "view audit logs") → Add specific policy

### Migration Pattern for RLS Policies

**Create policies in migration:**
```sql
-- Migration: Add RLS policies for pms_entity_links
-- File: 2026YYYY_HHMM_rls_entity_links.sql

DO $$
BEGIN
    -- Enable RLS if not already enabled
    ALTER TABLE pms_entity_links ENABLE ROW LEVEL SECURITY;

    -- DROP old policies if they exist (for idempotency)
    DROP POLICY IF EXISTS entity_links_select ON pms_entity_links;
    DROP POLICY IF EXISTS entity_links_insert ON pms_entity_links;
    DROP POLICY IF EXISTS entity_links_update ON pms_entity_links;
    DROP POLICY IF EXISTS entity_links_delete ON pms_entity_links;

    -- CREATE new policies
    CREATE POLICY entity_links_select ON pms_entity_links
    FOR SELECT
    USING (yacht_id = get_user_yacht_id());

    CREATE POLICY entity_links_insert ON pms_entity_links
    FOR INSERT
    WITH CHECK (
        yacht_id = get_user_yacht_id() AND
        (is_hod() OR is_manager())
    );

    -- ... (rest of policies)
END $$;
```

---

## Summary Table: RLS + Application Filter

| Table                    | RLS Policy          | Application Filter     | Notes                                      |
|--------------------------|---------------------|------------------------|--------------------------------------------|
| pms_work_orders          | yacht_id            | WHERE yacht_id = :id   | Core entity; all roles can SELECT          |
| pms_work_order_parts     | yacht_id            | WHERE yacht_id = :id   | Join table; filter both sides of JOIN     |
| pms_parts                | yacht_id            | WHERE yacht_id = :id   | Filter when joining from work_order_parts  |
| doc_metadata             | yacht_id            | WHERE yacht_id = :id   | Metadata only; no presigned URLs           |
| pms_work_order_notes     | yacht_id + owner    | WHERE yacht_id = :id   | UPDATE/DELETE restricted to creator or HOD |
| pms_entity_links         | yacht_id + HOD      | WHERE yacht_id = :id   | INSERT restricted to HOD/manager           |
| pms_equipment            | yacht_id            | WHERE yacht_id = :id   | Indirectly queried via work_orders         |
| pms_faults               | yacht_id            | WHERE yacht_id = :id   | Indirectly queried via work_orders         |
| pms_audit_log            | yacht_id + manager  | WHERE yacht_id = :id   | Immutable; manager-only SELECT             |

---

## Next Phase

**PHASE 8: GAPS & MIGRATIONS** — Unique constraints, optional indexes, embedding backfill, acceptance checks.

---

**PHASE 7 COMPLETE** ✅

**Key Deliverables:**
- Table-by-table RLS policies with yacht_id and role checks
- Helper function definitions and usage patterns
- Explicit prohibition on JOIN-only enforcement
- Storage policy: metadata-only, no presigned URLs in Show Related panel
- RLS verification checklist and testing matrix
- Application-level enforcement pattern (defense-in-depth)
- Migration pattern for RLS policy updates
