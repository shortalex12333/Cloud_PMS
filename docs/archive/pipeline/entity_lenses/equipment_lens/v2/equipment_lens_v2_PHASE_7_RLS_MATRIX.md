# Equipment Lens v2 - PHASE 7: RLS MATRIX

**Goal**: Document → Tests → Code → Verify — backend defines actions, signatures, and RLS; no UI authority.

**Lens**: Equipment

**Date**: 2026-01-27

---

## PURPOSE

Phase 7 documents all Row Level Security policies:
- Current deployed policies
- Role mapping
- Verification queries
- Gap analysis

---

## RLS PHILOSOPHY

### Core Principles

1. **Deny by default**: No access unless explicitly granted
2. **Yacht isolation**: All queries filtered by `get_user_yacht_id()`
3. **Role-based writes**: Mutations gated by role helpers
4. **Service role bypass**: Backend operations use service role when needed

### Canonical Helpers

```sql
-- Yacht isolation
public.get_user_yacht_id() → UUID

-- Role detection
public.get_user_role() → TEXT

-- Boolean helpers (preferred for RLS)
public.is_hod(user_id UUID, yacht_id UUID) → BOOLEAN
public.is_manager() → BOOLEAN
```

---

## TABLE: `pms_equipment`

### Current Deployed Policies

```sql
-- 1. SELECT: All authenticated users can view their yacht's equipment
CREATE POLICY "Users can view yacht equipment"
ON pms_equipment
FOR SELECT
TO public
USING (yacht_id = public.get_user_yacht_id());

-- 2. ALL: Engineers can manage equipment (INSERT, UPDATE, DELETE)
CREATE POLICY "Engineers can manage equipment"
ON pms_equipment
FOR ALL
TO public
USING (
    yacht_id = public.get_user_yacht_id()
    AND public.get_user_role() = ANY (ARRAY[
        'engineer'::text,
        'eto'::text,
        'chief_engineer'::text,
        'chief_officer'::text,
        'captain'::text,
        'manager'::text
    ])
);

-- 3. Service role bypass
CREATE POLICY "Service role full access equipment"
ON pms_equipment
FOR ALL
TO service_role
USING (true);
```

### Policy Matrix

| Operation | Crew | Engineer | ETO | Chief Eng | Chief Off | Captain | Manager | Service |
|-----------|------|----------|-----|-----------|-----------|---------|---------|---------|
| SELECT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| INSERT | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| UPDATE | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| DELETE | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

**Note**: DELETE is blocked by `no_hard_delete_equipment` trigger regardless of RLS. Soft delete (UPDATE deleted_at) is the only path.

### RLS Status

```sql
SELECT relname, relrowsecurity, relforcerowsecurity
FROM pg_class
WHERE relname = 'pms_equipment';
-- Expected: relrowsecurity = true
```

---

## TABLE: `pms_equipment_parts_bom`

### Current Deployed Policies

```sql
-- 1. SELECT: All authenticated users can view
CREATE POLICY "Users can view equipment parts"
ON pms_equipment_parts_bom
FOR SELECT
TO public
USING (yacht_id = public.get_user_yacht_id());

-- 2. ALL: Engineers can manage
CREATE POLICY "Engineers can manage equipment parts"
ON pms_equipment_parts_bom
FOR ALL
TO public
USING (
    yacht_id = public.get_user_yacht_id()
    AND public.get_user_role() = ANY (ARRAY[
        'engineer'::text,
        'eto'::text,
        'chief_engineer'::text,
        'captain'::text,
        'manager'::text
    ])
);

-- 3. Service role bypass
CREATE POLICY "Service role full access equipment_parts"
ON pms_equipment_parts_bom
FOR ALL
TO service_role
USING (true);
```

### Policy Matrix

| Operation | Crew | Engineer | ETO | Chief Eng | Chief Off | Captain | Manager | Service |
|-----------|------|----------|-----|-----------|-----------|---------|---------|---------|
| SELECT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| INSERT | ❌ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ |
| UPDATE | ❌ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ |
| DELETE | ❌ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ |

**Note**: Chief Officer excluded from parts management (deck focus, not engineering).

---

## TABLE: `pms_notes`

### Required Policies

```sql
-- 1. SELECT: All authenticated users can view notes for their yacht
CREATE POLICY "Users can view yacht notes"
ON pms_notes
FOR SELECT
TO public
USING (yacht_id = public.get_user_yacht_id());

-- 2. INSERT: All crew can add notes
CREATE POLICY "Crew can add notes"
ON pms_notes
FOR INSERT
TO public
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
);

-- 3. UPDATE: Only author or HOD can update
CREATE POLICY "Author or HOD can update notes"
ON pms_notes
FOR UPDATE
TO public
USING (
    yacht_id = public.get_user_yacht_id()
    AND (
        created_by = auth.uid()
        OR public.is_hod(auth.uid(), public.get_user_yacht_id())
    )
);

-- 4. DELETE: Only manager can delete
CREATE POLICY "Manager can delete notes"
ON pms_notes
FOR DELETE
TO public
USING (
    yacht_id = public.get_user_yacht_id()
    AND public.is_manager()
);

-- 5. Service role bypass
CREATE POLICY "Service role full access notes"
ON pms_notes
FOR ALL
TO service_role
USING (true);
```

### RLS Status: ⚠️ VERIFY

```sql
SELECT relrowsecurity FROM pg_class WHERE relname = 'pms_notes';
```

---

## TABLE: `pms_attachments`

### Required Policies

```sql
-- 1. SELECT: All authenticated users can view
CREATE POLICY "Users can view yacht attachments"
ON pms_attachments
FOR SELECT
TO public
USING (yacht_id = public.get_user_yacht_id());

-- 2. INSERT: All crew can upload
CREATE POLICY "Crew can upload attachments"
ON pms_attachments
FOR INSERT
TO public
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
);

-- 3. UPDATE: Only uploader or HOD can update metadata
CREATE POLICY "Uploader or HOD can update attachments"
ON pms_attachments
FOR UPDATE
TO public
USING (
    yacht_id = public.get_user_yacht_id()
    AND (
        uploaded_by = auth.uid()
        OR public.is_hod(auth.uid(), public.get_user_yacht_id())
    )
);

-- 4. DELETE: Only manager can delete
CREATE POLICY "Manager can delete attachments"
ON pms_attachments
FOR DELETE
TO public
USING (
    yacht_id = public.get_user_yacht_id()
    AND public.is_manager()
);

-- 5. Service role bypass
CREATE POLICY "Service role full access attachments"
ON pms_attachments
FOR ALL
TO service_role
USING (true);
```

### RLS Status: ⚠️ VERIFY

```sql
SELECT relrowsecurity FROM pg_class WHERE relname = 'pms_attachments';
```

---

## TABLE: `pms_audit_log`

### Required Policies

```sql
-- 1. SELECT: All authenticated users can view their yacht's audit entries
CREATE POLICY "Users can view yacht audit log"
ON pms_audit_log
FOR SELECT
TO public
USING (yacht_id = public.get_user_yacht_id());

-- 2. INSERT: Backend only (via service role or internal functions)
-- No direct INSERT policy for public role
-- Audit writes happen through handlers with SECURITY DEFINER functions

-- 3. UPDATE: NEVER (audit is immutable)
-- No UPDATE policy

-- 4. DELETE: NEVER (audit is immutable)
-- No DELETE policy

-- 5. Service role for backend writes
CREATE POLICY "Service role can write audit log"
ON pms_audit_log
FOR INSERT
TO service_role
WITH CHECK (true);
```

### RLS Status: ⚠️ VERIFY

```sql
SELECT relrowsecurity FROM pg_class WHERE relname = 'pms_audit_log';
```

---

## STORAGE: `documents` Bucket

### Required Policies

```sql
-- 1. SELECT: Yacht-scoped read
CREATE POLICY "Yacht users can read their documents"
ON storage.objects
FOR SELECT
TO public
USING (
    bucket_id = 'documents'
    AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
);

-- 2. INSERT: All crew can upload to their yacht path
CREATE POLICY "Crew can upload yacht documents"
ON storage.objects
FOR INSERT
TO public
WITH CHECK (
    bucket_id = 'documents'
    AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
);

-- 3. UPDATE: HOD can update
CREATE POLICY "HOD can update yacht documents"
ON storage.objects
FOR UPDATE
TO public
USING (
    bucket_id = 'documents'
    AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
    AND public.is_hod(auth.uid(), public.get_user_yacht_id())
);

-- 4. DELETE: Manager only
CREATE POLICY "Manager can delete yacht documents"
ON storage.objects
FOR DELETE
TO public
USING (
    bucket_id = 'documents'
    AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
    AND public.is_manager()
);
```

### Storage Path Validation

Equipment files must follow path pattern:
```
{yacht_id}/equipment/{equipment_id}/{filename}
```

RLS policy extracts `yacht_id` from path using `storage.foldername(name)[1]`.

---

## ROLE-TO-ACTION MAPPING

### Registry `allowed_roles` vs RLS

| Action | Registry allowed_roles | RLS Policy |
|--------|------------------------|------------|
| `update_equipment_status` | engineer, eto, chief_engineer, chief_officer, captain, manager | "Engineers can manage equipment" |
| `add_equipment_note` | all crew | "Crew can add notes" |
| `attach_file_to_equipment` | all crew | "Crew can upload attachments" + storage policy |
| `create_work_order_for_equipment` | engineer, eto, chief_engineer, chief_officer, captain, manager | pms_work_orders RLS |
| `link_part_to_equipment` | engineer, eto, chief_engineer, captain, manager | "Engineers can manage equipment parts" |
| `flag_equipment_attention` | engineer, eto, chief_engineer, chief_officer, captain, manager | "Engineers can manage equipment" |
| `decommission_equipment` | captain, manager | "Engineers can manage equipment" + handler validation |

### Alignment Check

**Rule**: Registry `allowed_roles` MUST be a subset of RLS-allowed roles.

| Action | Registry | RLS | Aligned |
|--------|----------|-----|---------|
| update_equipment_status | 6 roles | 6 roles | ✅ |
| add_equipment_note | 11 roles | all crew | ✅ |
| attach_file_to_equipment | 11 roles | all crew | ✅ |
| link_part_to_equipment | 5 roles | 5 roles | ✅ |
| decommission_equipment | 2 roles | 6 roles | ✅ (handler adds restriction) |

---

## VERIFICATION QUERIES

### 1. RLS Enabled Check

```sql
SELECT relname, relrowsecurity
FROM pg_class
WHERE relname IN (
    'pms_equipment',
    'pms_equipment_parts_bom',
    'pms_notes',
    'pms_attachments',
    'pms_audit_log'
);
-- All should show relrowsecurity = true
```

### 2. Policy List

```sql
SELECT tablename, policyname, cmd, roles
FROM pg_policies
WHERE tablename IN (
    'pms_equipment',
    'pms_equipment_parts_bom',
    'pms_notes',
    'pms_attachments',
    'pms_audit_log'
)
ORDER BY tablename, policyname;
```

### 3. Yacht Isolation Test

```sql
-- As user from Yacht A, attempt to see Yacht B equipment
SET LOCAL role = 'authenticated';
SET LOCAL request.jwt.claims = '{"sub": "user-yacht-a-uuid"}';

SELECT COUNT(*) FROM pms_equipment WHERE yacht_id = 'yacht-b-uuid';
-- Expected: 0 (RLS blocks)
```

### 4. Role Gating Test

```sql
-- As deckhand, attempt to update equipment
SET LOCAL request.jwt.claims = '{"sub": "deckhand-uuid", "role": "deckhand"}';

UPDATE pms_equipment SET status = 'failed' WHERE id = 'some-equipment-uuid';
-- Expected: 0 rows affected (RLS blocks)
```

### 5. Storage Policy Test

```sql
-- Verify storage policies exist
SELECT policyname
FROM pg_policies
WHERE schemaname = 'storage'
  AND tablename = 'objects'
  AND policyname ILIKE '%yacht%' OR policyname ILIKE '%equipment%';
```

---

## GAP ANALYSIS

### Confirmed Deployed

| Table | RLS Enabled | Policies |
|-------|-------------|----------|
| pms_equipment | ✅ | ✅ 3 policies |
| pms_equipment_parts_bom | ✅ | ✅ 3 policies |

### Needs Verification

| Table | RLS Enabled | Policies | Action |
|-------|-------------|----------|--------|
| pms_notes | ⚠️ VERIFY | ⚠️ VERIFY | Run verification query |
| pms_attachments | ⚠️ VERIFY | ⚠️ VERIFY | Run verification query |
| pms_audit_log | ⚠️ VERIFY | ⚠️ VERIFY | Run verification query |
| storage.objects (documents) | ⚠️ VERIFY | ⚠️ VERIFY | Run verification query |

---

## HELPER FUNCTION VERIFICATION

### Required Helpers

```sql
-- Check helpers exist
SELECT proname, prorettype::regtype
FROM pg_proc
WHERE proname IN ('get_user_yacht_id', 'get_user_role', 'is_hod', 'is_manager');

-- Expected output:
-- get_user_yacht_id | uuid
-- get_user_role     | text
-- is_hod            | boolean
-- is_manager        | boolean
```

---

## NEXT PHASE

Proceed to **PHASE 8: GAPS & MIGRATIONS** to:
- Consolidate all identified gaps
- Define migration scripts
- Prioritize deployment order

---

**END OF PHASE 7**
