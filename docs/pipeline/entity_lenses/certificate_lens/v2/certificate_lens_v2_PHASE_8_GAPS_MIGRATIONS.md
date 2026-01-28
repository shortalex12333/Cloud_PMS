# Certificate Lens v2 - Phase 8: Gaps & Migrations
**Status**: MIGRATIONS COMPLETE
**Date**: 2026-01-25

---

## PURPOSE

This phase documents all gaps between current state and required state, and provides ready-to-deploy migration SQL.

---

# BLOCKERS CONSOLIDATED

| ID | Description | Severity | Tables Affected | Resolution |
|----|-------------|----------|-----------------|------------|
| **B1** | `pms_vessel_certificates` has NO RLS policies | CRITICAL | pms_vessel_certificates | Migration 007 |
| **B2** | Crew cert INSERT/UPDATE/DELETE pending | MEDIUM | pms_crew_certificates | Deploy existing 006 |
| **B3** | No CHECK constraint on `status` column | LOW | Both | Optional migration |
| **B4** | No expiration status trigger | LOW | Both | Optional migration |
| **B5** | Storage bucket missing INSERT/UPDATE/DELETE | MEDIUM | storage.objects | Migration 011 |

**Note**: Service role bypasses RLS automatically - no explicit policies needed.

---

# GAP ANALYSIS

## Critical Gaps (Must Fix)

| Gap | Current State | Required State | Impact |
|-----|---------------|----------------|--------|
| G1 | No RLS on vessel certs | Full RLS with role-based access | Security: cross-yacht data exposure |
| G2 | Crew cert policies pending | Deploy INSERT/UPDATE/DELETE | Functionality: cannot create crew certs |

## Medium Gaps (Should Fix)

| Gap | Current State | Required State | Impact |
|-----|---------------|----------------|--------|
| G3 | No unique constraint on (yacht_id, type, number) | Prevent duplicate cert numbers | Data integrity |
| G4 | No indexes on expiry_date | Indexed for expiration queries | Performance |

## Low Gaps (Optional)

| Gap | Current State | Required State | Impact |
|-----|---------------|----------------|--------|
| G5 | Status values not DB-enforced | CHECK constraint | Data integrity |
| G6 | No auto-status trigger | Trigger updates status based on expiry | Automation |
| G7 | No `updated_at` column on cert tables | Add column with trigger | Audit trail |

---

# ACTION → BLOCKER MAPPING

| Action | Blocked By | Can Deploy After |
|--------|------------|------------------|
| `create_vessel_certificate` | B1 | Migration 007 |
| `create_crew_certificate` | B2 | Migration 006 deployed |
| `update_certificate` (vessel) | B1 | Migration 007 |
| `update_certificate` (crew) | B2 | Migration 006 deployed |
| `supersede_certificate` | B1 | Migration 007 |
| `link_document` (vessel) | B1 | Migration 007 |
| `link_document` (crew) | B2 | Migration 006 deployed |
| `view_certificate_history` | - | ✅ READY NOW |

---

# MIGRATION 007: Vessel Certificates RLS (CRITICAL - P0)

**File**: `20260125_007_vessel_certificates_rls.sql`

```sql
-- ============================================================================
-- MIGRATION: Add RLS Policies to pms_vessel_certificates
-- ============================================================================
-- PROBLEM: pms_vessel_certificates has NO RLS policies
--          This allows any authenticated user to potentially access
--          all yachts' vessel certificates (CRITICAL security gap)
-- SOLUTION: Enable RLS and add proper yacht-scoped policies with role checks
-- SEVERITY: P0 - CRITICAL Security Fix
-- ============================================================================

BEGIN;

-- =============================================================================
-- STEP 1: Enable Row Level Security
-- =============================================================================
ALTER TABLE pms_vessel_certificates ENABLE ROW LEVEL SECURITY;

-- =============================================================================
-- STEP 2: SELECT policy - All authenticated crew can view own yacht's certs
-- =============================================================================
CREATE POLICY "crew_select_own_yacht_vessel_certs"
ON pms_vessel_certificates
FOR SELECT TO authenticated
USING (yacht_id = public.get_user_yacht_id());

-- =============================================================================
-- STEP 3: INSERT policy - HOD roles only (using boolean helper)
-- =============================================================================
CREATE POLICY "hod_insert_vessel_certs"
ON pms_vessel_certificates
FOR INSERT TO authenticated
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
    AND is_hod(auth.uid(), public.get_user_yacht_id())
);

-- =============================================================================
-- STEP 4: UPDATE policy - HOD roles only (using boolean helper)
-- =============================================================================
CREATE POLICY "hod_update_vessel_certs"
ON pms_vessel_certificates
FOR UPDATE TO authenticated
USING (yacht_id = public.get_user_yacht_id())
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
    AND is_hod(auth.uid(), public.get_user_yacht_id())
);

-- =============================================================================
-- STEP 5: DELETE policy - Manager only (using boolean helper)
-- =============================================================================
CREATE POLICY "manager_delete_vessel_certs"
ON pms_vessel_certificates
FOR DELETE TO authenticated
USING (
    yacht_id = public.get_user_yacht_id()
    AND is_manager()
);

-- =============================================================================
-- NOTE: Service role bypasses RLS automatically - no explicit policy needed
-- =============================================================================

-- =============================================================================
-- STEP 6: Verification
-- =============================================================================
DO $$
DECLARE
    rls_enabled BOOLEAN;
    policy_count INTEGER;
BEGIN
    -- Check RLS enabled
    SELECT relrowsecurity INTO rls_enabled
    FROM pg_class
    WHERE relname = 'pms_vessel_certificates';

    IF NOT rls_enabled THEN
        RAISE EXCEPTION 'RLS not enabled on pms_vessel_certificates';
    END IF;

    -- Check policy count
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE tablename = 'pms_vessel_certificates';

    IF policy_count < 4 THEN
        RAISE EXCEPTION 'Expected at least 4 policies, found %', policy_count;
    END IF;

    RAISE NOTICE 'SUCCESS: pms_vessel_certificates RLS configured with % policies', policy_count;
END $$;

COMMIT;

-- =============================================================================
-- ROLLBACK SCRIPT (run separately if needed)
-- =============================================================================
-- BEGIN;
-- DROP POLICY IF EXISTS "crew_select_own_yacht_vessel_certs" ON pms_vessel_certificates;
-- DROP POLICY IF EXISTS "hod_insert_vessel_certs" ON pms_vessel_certificates;
-- DROP POLICY IF EXISTS "hod_update_vessel_certs" ON pms_vessel_certificates;
-- DROP POLICY IF EXISTS "manager_delete_vessel_certs" ON pms_vessel_certificates;
-- ALTER TABLE pms_vessel_certificates DISABLE ROW LEVEL SECURITY;
-- COMMIT;
```

---

# MIGRATION 008: Certificate Status Constraint (P2)

**File**: `20260125_008_certificate_status_constraint.sql`

```sql
-- ============================================================================
-- MIGRATION: Add CHECK constraint on status column
-- ============================================================================
-- PROBLEM: Status column accepts any text value
-- SOLUTION: Add CHECK constraint to enforce valid status values
-- SEVERITY: P2 - Data Integrity Enhancement
-- ============================================================================

BEGIN;

-- =============================================================================
-- STEP 1: Add CHECK constraint to vessel certificates
-- =============================================================================
ALTER TABLE pms_vessel_certificates
ADD CONSTRAINT chk_vessel_cert_status
CHECK (status = ANY (ARRAY['valid', 'due_soon', 'expired', 'superseded']));

-- =============================================================================
-- STEP 2: Verification
-- =============================================================================
DO $$
BEGIN
    -- Try to insert invalid status (should fail)
    BEGIN
        INSERT INTO pms_vessel_certificates (
            yacht_id, certificate_type, certificate_name,
            issuing_authority, status
        ) VALUES (
            '00000000-0000-0000-0000-000000000000',
            'test', 'test', 'test', 'invalid_status'
        );
        RAISE EXCEPTION 'CHECK constraint not working';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'SUCCESS: CHECK constraint is enforcing valid status values';
    END;
END $$;

COMMIT;

-- =============================================================================
-- ROLLBACK
-- =============================================================================
-- ALTER TABLE pms_vessel_certificates DROP CONSTRAINT IF EXISTS chk_vessel_cert_status;
```

---

# MIGRATION 009: Certificate Expiration Trigger (P3)

**File**: `20260125_009_certificate_expiration_trigger.sql`

```sql
-- ============================================================================
-- MIGRATION: Auto-update certificate status based on expiry_date
-- ============================================================================
-- PROBLEM: Status must be manually updated when certificates expire
-- SOLUTION: Trigger to automatically set status based on expiry_date
-- SEVERITY: P3 - Automation Enhancement
-- ============================================================================

BEGIN;

-- =============================================================================
-- STEP 1: Create status update function
-- =============================================================================
CREATE OR REPLACE FUNCTION public.update_certificate_status()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    -- Skip if no expiry date
    IF NEW.expiry_date IS NULL THEN
        -- Keep existing status or default to valid
        NEW.status := COALESCE(NEW.status, 'valid');
        RETURN NEW;
    END IF;

    -- Don't override 'superseded' status
    IF NEW.status = 'superseded' THEN
        RETURN NEW;
    END IF;

    -- Set status based on expiry_date
    IF NEW.expiry_date <= current_date THEN
        NEW.status := 'expired';
    ELSIF NEW.expiry_date <= current_date + INTERVAL '30 days' THEN
        NEW.status := 'due_soon';
    ELSE
        NEW.status := 'valid';
    END IF;

    RETURN NEW;
END;
$$;

-- =============================================================================
-- STEP 2: Create trigger on vessel certificates
-- =============================================================================
DROP TRIGGER IF EXISTS trg_vessel_cert_status ON pms_vessel_certificates;
CREATE TRIGGER trg_vessel_cert_status
    BEFORE INSERT OR UPDATE OF expiry_date
    ON pms_vessel_certificates
    FOR EACH ROW
    EXECUTE FUNCTION public.update_certificate_status();

-- =============================================================================
-- STEP 3: Update existing records
-- =============================================================================
UPDATE pms_vessel_certificates
SET status = CASE
    WHEN expiry_date IS NULL THEN 'valid'
    WHEN status = 'superseded' THEN 'superseded'
    WHEN expiry_date <= current_date THEN 'expired'
    WHEN expiry_date <= current_date + INTERVAL '30 days' THEN 'due_soon'
    ELSE 'valid'
END
WHERE status NOT IN ('superseded');

-- =============================================================================
-- STEP 4: Verification
-- =============================================================================
DO $$
DECLARE
    expired_count INTEGER;
    due_soon_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO expired_count
    FROM pms_vessel_certificates
    WHERE expiry_date <= current_date
      AND status = 'expired';

    SELECT COUNT(*) INTO due_soon_count
    FROM pms_vessel_certificates
    WHERE expiry_date > current_date
      AND expiry_date <= current_date + INTERVAL '30 days'
      AND status = 'due_soon';

    RAISE NOTICE 'Status update complete: % expired, % due_soon', expired_count, due_soon_count;
END $$;

COMMIT;

-- =============================================================================
-- ROLLBACK
-- =============================================================================
-- DROP TRIGGER IF EXISTS trg_vessel_cert_status ON pms_vessel_certificates;
-- DROP FUNCTION IF EXISTS public.update_certificate_status();
```

---

# MIGRATION 010: Certificate Indexes (P2)

**File**: `20260125_010_certificate_indexes.sql`

```sql
-- ============================================================================
-- MIGRATION: Add performance indexes for certificate queries
-- ============================================================================

BEGIN;

-- Yacht isolation index (critical for RLS performance)
CREATE INDEX IF NOT EXISTS idx_vessel_certs_yacht
ON pms_vessel_certificates(yacht_id);

CREATE INDEX IF NOT EXISTS idx_crew_certs_yacht
ON pms_crew_certificates(yacht_id);

-- Expiration queries
CREATE INDEX IF NOT EXISTS idx_vessel_certs_expiry
ON pms_vessel_certificates(yacht_id, expiry_date)
WHERE status != 'superseded';

CREATE INDEX IF NOT EXISTS idx_crew_certs_expiry
ON pms_crew_certificates(yacht_id, expiry_date);

-- Document lookups
CREATE INDEX IF NOT EXISTS idx_vessel_certs_doc
ON pms_vessel_certificates(document_id)
WHERE document_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_crew_certs_doc
ON pms_crew_certificates(document_id)
WHERE document_id IS NOT NULL;

-- Person lookups for crew
CREATE INDEX IF NOT EXISTS idx_crew_certs_person
ON pms_crew_certificates(person_node_id)
WHERE person_node_id IS NOT NULL;

-- Unique constraint on certificate number per type per yacht
CREATE UNIQUE INDEX IF NOT EXISTS ux_vessel_cert_number
ON pms_vessel_certificates(yacht_id, certificate_type, certificate_number)
WHERE certificate_number IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS ux_crew_cert_number
ON pms_crew_certificates(yacht_id, person_name, certificate_type, certificate_number)
WHERE certificate_number IS NOT NULL;

COMMIT;
```

---

# MIGRATION 012: doc_metadata Write RLS (P1)

**File**: `20260125_012_doc_metadata_write_rls.sql`

```sql
-- ============================================================================
-- MIGRATION: Add Write Policies to doc_metadata
-- ============================================================================
-- Required for certificate document upload flow
-- ============================================================================

BEGIN;

-- Enable RLS (idempotent)
ALTER TABLE doc_metadata ENABLE ROW LEVEL SECURITY;

-- DROP existing if re-running
DROP POLICY IF EXISTS "crew_insert_doc_metadata" ON doc_metadata;
DROP POLICY IF EXISTS "hod_update_doc_metadata" ON doc_metadata;
DROP POLICY IF EXISTS "manager_delete_doc_metadata" ON doc_metadata;

-- INSERT: Authenticated users can create rows for their yacht
CREATE POLICY "crew_insert_doc_metadata" ON doc_metadata
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id = COALESCE(jwt_yacht_id(), public.get_user_yacht_id())
    );

-- UPDATE: HOD can update document metadata
CREATE POLICY "hod_update_doc_metadata" ON doc_metadata
    FOR UPDATE TO authenticated
    USING (
        yacht_id = COALESCE(jwt_yacht_id(), public.get_user_yacht_id())
    )
    WITH CHECK (
        yacht_id = COALESCE(jwt_yacht_id(), public.get_user_yacht_id())
        AND is_hod(auth.uid(), public.get_user_yacht_id())
    );

-- DELETE: Manager only
CREATE POLICY "manager_delete_doc_metadata" ON doc_metadata
    FOR DELETE TO authenticated
    USING (
        yacht_id = COALESCE(jwt_yacht_id(), public.get_user_yacht_id())
        AND is_manager()
    );

COMMIT;
```

---

# DEPLOYMENT CHECKLIST

## Pre-Deployment
- [ ] Backup production database
- [ ] Verify helper functions exist: `get_user_yacht_id()`, `is_hod()`, `is_manager()`
- [ ] Test migrations on staging

## Migration Order
1. [ ] Deploy `20260125_006_fix_crew_certificates_rls.sql` (enables RLS + policies, resolves B2)
2. [ ] Deploy `20260125_007_vessel_certificates_rls.sql` (resolves B1)
3. [ ] Deploy `20260125_011_documents_storage_write_policies.sql` (resolves B5)
4. [ ] Deploy `20260125_012_doc_metadata_write_rls.sql` (resolves B6)
5. [ ] Deploy `20260125_010_certificate_indexes.sql` (performance)
6. [ ] Deploy `20260125_008_certificate_status_constraint.sql` (optional)
7. [ ] Deploy `20260125_009_certificate_expiration_trigger.sql` (optional)

## Post-Deployment Verification

### Certificate Tables RLS
```sql
-- 1. Verify RLS enabled on all tables
SELECT relname, relrowsecurity
FROM pg_class
WHERE relname IN ('pms_vessel_certificates', 'pms_crew_certificates', 'doc_metadata');
-- All should show TRUE

-- 2. Verify certificate policies exist
SELECT tablename, policyname
FROM pg_policies
WHERE tablename IN ('pms_vessel_certificates', 'pms_crew_certificates')
ORDER BY tablename, policyname;
-- Should show 4+ policies per table

-- 3. Test yacht isolation
SELECT COUNT(*) FROM pms_vessel_certificates WHERE yacht_id = 'other-yacht-uuid';
-- Should return 0 (RLS blocks cross-yacht access)

-- 4. Test role enforcement (as deckhand)
INSERT INTO pms_vessel_certificates (yacht_id, certificate_type, certificate_name, issuing_authority)
VALUES (get_user_yacht_id(), 'test', 'test', 'test');
-- Should fail with RLS violation
```

### Storage Policies
```sql
-- 5. Verify storage write policies
SELECT policyname FROM pg_policies
WHERE schemaname = 'storage' AND tablename = 'objects'
  AND policyname IN (
    'hod_insert_yacht_documents',
    'hod_update_yacht_documents',
    'manager_delete_yacht_documents'
  );
-- Should return 3 rows
```

### doc_metadata Policies
```sql
-- 6. Verify doc_metadata write policies
SELECT policyname FROM pg_policies
WHERE tablename = 'doc_metadata'
  AND policyname IN (
    'crew_insert_doc_metadata',
    'hod_update_doc_metadata',
    'manager_delete_doc_metadata'
  );
-- Should return 3 rows
```

### Indexes
```sql
-- 7. Verify indexes created
SELECT indexname FROM pg_indexes
WHERE tablename IN ('pms_vessel_certificates', 'pms_crew_certificates')
  AND indexname LIKE 'ix_%' OR indexname LIKE 'ux_%' OR indexname LIKE 'idx_%';
-- Should show 10+ indexes
```

---

# BLOCKER RESOLUTION STATUS

| ID | Status | Migration | Deployed |
|----|--------|-----------|----------|
| B1 | 🔧 FIX READY | 20260125_007 | ❌ Not yet |
| B2 | 🔧 FIX READY | 20260125_006 | ❌ Not yet |
| B5 | 🔧 FIX READY | 20260125_011 | ❌ Not yet |
| B6 | 🔧 FIX READY | 20260125_012 | ❌ Not yet |
| B3 | 📝 OPTIONAL | 20260125_008 | ❌ Not yet |
| B4 | 📝 OPTIONAL | 20260125_009 | ❌ Not yet |

---

# RISK ASSESSMENT

## If B1 Not Deployed
- **Risk**: All authenticated users can see/modify all yachts' vessel certificates
- **Impact**: Critical security violation, compliance failure
- **Mitigation**: Deploy 007 immediately, verify isolation

## If B2 Not Deployed
- **Risk**: Officers cannot create/update crew certificates
- **Impact**: Functionality blocked, manual workarounds needed
- **Mitigation**: Deploy 006, test officer workflows

## Deployment Risk
- **Risk**: Migrations could lock tables during ALTER
- **Mitigation**: Deploy during low-traffic period, monitor locks
- **Rollback**: Each migration includes rollback script

---

**GAPS & MIGRATIONS STATUS**: ✅ COMPLETE - Ready for FINAL compilation

---

**END OF PHASE 8**
