# Certificate Lens v2 - Phase 7: RLS & Security Matrix
**Status**: MATRIX COMPLETE
**Date**: 2026-01-25

---

## PURPOSE

This phase documents the exact RLS policies from production migrations and identifies gaps between deployed and required security.

---

# RLS STATUS OVERVIEW

| Table | RLS Enabled | SELECT | INSERT | UPDATE | DELETE | Status |
|-------|-------------|--------|--------|--------|--------|--------|
| `pms_vessel_certificates` | ❌ NO | ❌ NONE | ❌ NONE | ❌ NONE | ❌ NONE | **BLOCKER B1** |
| `pms_crew_certificates` | ⚠️ CHECK | ✅ Deployed | ⏳ Pending | ⏳ Pending | ⏳ Pending | **Blocker B2** |
| `doc_metadata` | YES | ✅ Deployed | ⏳ Pending | ⏳ Pending | ⏳ Pending | **Blocker B6** |
| `pms_audit_log` | YES | ✅ Deployed | ✅ Deployed | ❌ N/A | ❌ N/A | OK |

**CRITICAL**: Migration 006 must include `ALTER TABLE pms_crew_certificates ENABLE ROW LEVEL SECURITY;` as Step 1.

**CRITICAL**: Migration 012 adds INSERT/UPDATE/DELETE to doc_metadata for certificate document upload flow.

---

# TABLE: `pms_vessel_certificates`

## DEPLOYED POLICIES

**Status**: ❌ **NO POLICIES FOUND IN MIGRATIONS**

This is a critical security gap. The table may have:
- RLS disabled entirely (any authenticated user can access any yacht's data)
- Or RLS enabled but no policies (all access blocked)

**Verification Query**:
```sql
SELECT relrowsecurity
FROM pg_class
WHERE relname = 'pms_vessel_certificates';
-- If false: RLS disabled
-- If true with no policies: all access blocked
```

## PROPOSED POLICIES (Migration Required)

### P1: SELECT - All Crew Can View Own Yacht
```sql
CREATE POLICY "crew_select_own_yacht_vessel_certs"
ON pms_vessel_certificates
FOR SELECT TO authenticated
USING (yacht_id = public.get_user_yacht_id());
```

### P2: INSERT - HOD Only
```sql
CREATE POLICY "hod_insert_vessel_certs"
ON pms_vessel_certificates
FOR INSERT TO authenticated
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
    AND is_hod(auth.uid(), public.get_user_yacht_id())
);
```

### P3: UPDATE - HOD Only
```sql
CREATE POLICY "hod_update_vessel_certs"
ON pms_vessel_certificates
FOR UPDATE TO authenticated
USING (yacht_id = public.get_user_yacht_id())
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
    AND is_hod(auth.uid(), public.get_user_yacht_id())
);
```

### P4: DELETE - Manager Only
```sql
CREATE POLICY "manager_delete_vessel_certs"
ON pms_vessel_certificates
FOR DELETE TO authenticated
USING (
    yacht_id = public.get_user_yacht_id()
    AND is_manager()
);
```

**Note**: Service role automatically bypasses RLS. No explicit policy needed.

---

# TABLE: `pms_crew_certificates`

## DEPLOYED POLICIES (From Migration History)

### SELECT - Yacht Scope
```sql
-- Source: (existing, pre-migration)
CREATE POLICY "crew_select_own_yacht_crew_certificates"
ON pms_crew_certificates
FOR SELECT TO authenticated
USING (yacht_id = public.get_user_yacht_id());
```
**Status**: ✅ DEPLOYED

## PENDING POLICIES (Migration 20260125_006)

### INSERT - Officers Only
```sql
-- Source: 20260125_006_fix_crew_certificates_rls.sql
CREATE POLICY "officers_insert_crew_certificates"
ON pms_crew_certificates
FOR INSERT TO authenticated
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
    AND get_user_role() = ANY (ARRAY[
        'captain'::text,
        'chief_engineer'::text,
        'purser'::text,
        'manager'::text
    ])
);
```
**Status**: ⏳ PENDING DEPLOY

### UPDATE - Officers Only
```sql
-- Source: 20260125_006_fix_crew_certificates_rls.sql
CREATE POLICY "officers_update_crew_certificates"
ON pms_crew_certificates
FOR UPDATE TO authenticated
USING (yacht_id = public.get_user_yacht_id())
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
    AND get_user_role() = ANY (ARRAY[
        'captain'::text,
        'chief_engineer'::text,
        'purser'::text,
        'manager'::text
    ])
);
```
**Status**: ⏳ PENDING DEPLOY

### DELETE - Managers Only
```sql
-- Source: 20260125_006_fix_crew_certificates_rls.sql
CREATE POLICY "managers_delete_crew_certificates"
ON pms_crew_certificates
FOR DELETE TO authenticated
USING (
    yacht_id = public.get_user_yacht_id()
    AND is_manager()
);
```
**Status**: ⏳ PENDING DEPLOY

---

# TABLE: `doc_metadata`

## DEPLOYED POLICIES

### SELECT - Mixed Pattern (USING COALESCE)
```sql
-- Source: existing migration
CREATE POLICY "Users can view documents"
ON doc_metadata
FOR SELECT TO public
USING (yacht_id = COALESCE(jwt_yacht_id(), get_user_yacht_id()));
```
**Note**: Uses COALESCE of two functions - legacy pattern.
**Status**: ✅ DEPLOYED (but non-canonical)

### INSERT - Yacht Scope
```sql
CREATE POLICY "System can insert documents"
ON doc_metadata
FOR INSERT TO public
WITH CHECK (yacht_id = get_user_yacht_id());
```
**Status**: ✅ DEPLOYED

### ALL - Managers
```sql
CREATE POLICY "Managers can manage documents"
ON doc_metadata
FOR ALL TO public
USING ((yacht_id = jwt_yacht_id()) AND is_manager());
```
**Status**: ✅ DEPLOYED

### Service Role
```sql
CREATE POLICY "Service role full access documents"
ON doc_metadata
FOR ALL TO service_role
USING (true);
```
**Status**: ✅ DEPLOYED

---

# TABLE: `pms_audit_log`

## DEPLOYED POLICIES

### SELECT - Yacht Scope
```sql
CREATE POLICY "crew_select_own_yacht_audit"
ON pms_audit_log
FOR SELECT TO authenticated
USING (yacht_id = public.get_user_yacht_id());
```
**Status**: ✅ DEPLOYED

### INSERT - Yacht Scope
```sql
CREATE POLICY "system_insert_audit"
ON pms_audit_log
FOR INSERT TO authenticated
WITH CHECK (yacht_id = public.get_user_yacht_id());
```
**Status**: ✅ DEPLOYED

**Note**: Audit log is append-only. No UPDATE/DELETE policies.

---

# ROLE × ACTION MATRIX

| Role | View Vessel | Create Vessel | Update Vessel | Supersede Vessel | Delete Vessel |
|------|-------------|---------------|---------------|------------------|---------------|
| deckhand | ✅ | ❌ | ❌ | ❌ | ❌ |
| steward | ✅ | ❌ | ❌ | ❌ | ❌ |
| chef | ✅ | ❌ | ❌ | ❌ | ❌ |
| engineer | ✅ | ❌ | ❌ | ❌ | ❌ |
| chief_officer | ✅ | ✅ | ✅ | ❌ | ❌ |
| chief_engineer | ✅ | ✅ | ✅ | ✅ (signed) | ❌ |
| purser | ✅ | ✅ | ✅ | ❌ | ❌ |
| captain | ✅ | ✅ | ✅ | ✅ (signed) | ✅ |
| manager | ✅ | ✅ | ✅ | ✅ (signed) | ✅ |

| Role | View Crew | Create Crew | Update Crew | Delete Crew |
|------|-----------|-------------|-------------|-------------|
| deckhand | ✅ | ❌ | ❌ | ❌ |
| steward | ✅ | ❌ | ❌ | ❌ |
| chef | ✅ | ❌ | ❌ | ❌ |
| engineer | ✅ | ❌ | ❌ | ❌ |
| chief_officer | ✅ | ❌ | ❌ | ❌ |
| chief_engineer | ✅ | ✅ | ✅ | ❌ |
| purser | ✅ | ✅ | ✅ | ❌ |
| captain | ✅ | ✅ | ✅ | ✅ |
| manager | ✅ | ✅ | ✅ | ✅ |

---

# STORAGE RLS (Bucket: `documents`)

## Path Convention
```
documents/{yacht_id}/certificates/{certificate_id}/{filename}
```

**Note**: `storage.foldername(name)` is 1-indexed, so `[1]` extracts the yacht_id from this path.

## Storage Policies (Supabase Storage)

### SELECT
```sql
-- Authenticated users can view their yacht's files
CREATE POLICY "Users view yacht documents"
ON storage.objects
FOR SELECT TO authenticated
USING (
    bucket_id = 'documents'
    AND (storage.foldername(name))[1] = (
        SELECT yacht_id::text FROM auth_users_profiles WHERE id = auth.uid()
    )
);
```
**Status**: ✅ Deployed

### INSERT
```sql
-- HOD can upload to their yacht's path
CREATE POLICY "HOD upload yacht documents"
ON storage.objects
FOR INSERT TO authenticated
WITH CHECK (
    bucket_id = 'documents'
    AND (storage.foldername(name))[1] = (
        SELECT yacht_id::text FROM auth_users_profiles WHERE id = auth.uid()
    )
    AND is_hod(auth.uid(), (
        SELECT yacht_id FROM auth_users_profiles WHERE id = auth.uid()
    ))
);
```
**Status**: ⏳ Migration 011 needed

### UPDATE
```sql
-- HOD can update their yacht's files
CREATE POLICY "HOD update yacht documents"
ON storage.objects
FOR UPDATE TO authenticated
USING (
    bucket_id = 'documents'
    AND (storage.foldername(name))[1] = (
        SELECT yacht_id::text FROM auth_users_profiles WHERE id = auth.uid()
    )
)
WITH CHECK (
    bucket_id = 'documents'
    AND is_hod(auth.uid(), (
        SELECT yacht_id FROM auth_users_profiles WHERE id = auth.uid()
    ))
);
```
**Status**: ⏳ Migration 011 needed

### DELETE
```sql
-- Manager only can delete yacht documents
CREATE POLICY "Manager delete yacht documents"
ON storage.objects
FOR DELETE TO authenticated
USING (
    bucket_id = 'documents'
    AND (storage.foldername(name))[1] = (
        SELECT yacht_id::text FROM auth_users_profiles WHERE id = auth.uid()
    )
    AND is_manager()
);
```
**Status**: ⏳ Migration 011 needed

---

# SECURITY BOUNDARIES

## Yacht Isolation
- **Enforced By**: `yacht_id = public.get_user_yacht_id()` in every policy
- **Applies To**: All certificate tables, doc_metadata, audit_log
- **Risk If Missing**: Cross-yacht data leakage (users see other yacht's certificates)

## Role-Based Access
- **Enforced By**: `is_hod(auth.uid(), yacht_id)` for INSERT/UPDATE, `is_manager()` for DELETE
- **Applies To**: Write operations
- **Best Practice**: Use boolean helpers (`is_hod()`, `is_manager()`) over string comparisons
- **Risk If Missing**: Unauthorized crew can create/modify certificates

## Signature Requirements
- **Enforced By**: Application code (not RLS)
- **Applies To**: supersede_certificate action
- **Risk If Missing**: Unauthorized supersession without accountability

---

# GAP ANALYSIS

| Gap ID | Table | Issue | Severity | Migration Required |
|--------|-------|-------|----------|-------------------|
| **B1** | pms_vessel_certificates | No RLS policies | CRITICAL | 20260125_007 |
| **B2** | pms_crew_certificates | RLS enable + INSERT/UPDATE/DELETE | MEDIUM | 20260125_006 |
| **B5** | storage.objects | Missing INSERT/UPDATE/DELETE | MEDIUM | 20260125_011 |
| **B6** | doc_metadata | Missing INSERT/UPDATE/DELETE | MEDIUM | 20260125_012 |
| **G1** | doc_metadata | Mixed RLS pattern (COALESCE) | LOW | Future cleanup |

**Note**: Service role bypasses RLS automatically - no explicit policy needed on any table.

---

# MIGRATION PRIORITY

| Priority | Migration | Tables | Policies |
|----------|-----------|--------|----------|
| **P0** | 20260125_007_vessel_certificates_rls.sql | pms_vessel_certificates | SELECT, INSERT, UPDATE, DELETE |
| **P1** | 20260125_006_fix_crew_certificates_rls.sql | pms_crew_certificates | ENABLE RLS + INSERT, UPDATE, DELETE |
| **P1** | 20260125_011_documents_storage_write_policies.sql | storage.objects | INSERT, UPDATE, DELETE |
| **P1** | 20260125_012_doc_metadata_write_rls.sql | doc_metadata | ENABLE RLS + INSERT, UPDATE, DELETE |
| **P2** | 20260125_010_certificate_indexes.sql | *_certificates | Performance indexes |

---

# VERIFICATION QUERIES

## Check RLS Enabled
```sql
SELECT
    relname AS table_name,
    relrowsecurity AS rls_enabled
FROM pg_class
WHERE relname IN ('pms_vessel_certificates', 'pms_crew_certificates', 'doc_metadata', 'pms_audit_log');
```

## List Policies
```sql
SELECT
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual,
    with_check
FROM pg_policies
WHERE tablename IN ('pms_vessel_certificates', 'pms_crew_certificates')
ORDER BY tablename, policyname;
```

## Test Cross-Yacht Isolation
```sql
-- As user from Yacht A, try to read Yacht B's certificates
SET LOCAL request.jwt.claim.sub = 'user-from-yacht-a-uuid';
SELECT COUNT(*) FROM pms_vessel_certificates WHERE yacht_id = 'yacht-b-uuid';
-- Should return 0 (RLS blocks)
```

---

**RLS MATRIX STATUS**: ✅ COMPLETE - Proceed to Phase 8

---

**END OF PHASE 7**
