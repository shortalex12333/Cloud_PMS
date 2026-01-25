-- ============================================================================
-- MIGRATION: Add Performance Indexes for Certificate Queries
-- ============================================================================
-- PROBLEM: Certificate tables lack indexes for common query patterns
-- SOLUTION: Add indexes for yacht isolation, expiration queries, status filtering
-- SEVERITY: P2 - Performance Enhancement
-- LENS: Certificate Lens v2
-- DATE: 2026-01-25
-- ============================================================================

BEGIN;

-- =============================================================================
-- STEP 1: Yacht isolation indexes (critical for RLS performance)
-- =============================================================================
CREATE INDEX IF NOT EXISTS idx_vessel_certs_yacht
ON pms_vessel_certificates(yacht_id);

CREATE INDEX IF NOT EXISTS idx_crew_certs_yacht
ON pms_crew_certificates(yacht_id);

-- =============================================================================
-- STEP 2: Unique constraint on certificate number per yacht/type
-- Prevents duplicate certificate numbers within a yacht
-- =============================================================================
CREATE UNIQUE INDEX IF NOT EXISTS ux_vessel_cert_number
ON pms_vessel_certificates(yacht_id, certificate_type, certificate_number)
WHERE certificate_number IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS ux_crew_cert_number
ON pms_crew_certificates(yacht_id, person_name, certificate_type, certificate_number)
WHERE certificate_number IS NOT NULL;

-- =============================================================================
-- STEP 3: Expiration query indexes
-- Supports "Find Expiring Certificates" scenario
-- =============================================================================
CREATE INDEX IF NOT EXISTS ix_vessel_cert_expiry
ON pms_vessel_certificates(expiry_date)
WHERE expiry_date IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_crew_cert_expiry
ON pms_crew_certificates(expiry_date)
WHERE expiry_date IS NOT NULL;

-- Composite for yacht-scoped expiration queries (most common)
CREATE INDEX IF NOT EXISTS ix_vessel_cert_yacht_expiry
ON pms_vessel_certificates(yacht_id, expiry_date)
WHERE status != 'superseded' AND expiry_date IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_crew_cert_yacht_expiry
ON pms_crew_certificates(yacht_id, expiry_date)
WHERE expiry_date IS NOT NULL;

-- =============================================================================
-- STEP 4: Status filtering indexes
-- Supports filtering by status (valid, due_soon, expired, superseded)
-- =============================================================================
CREATE INDEX IF NOT EXISTS ix_vessel_cert_yacht_status
ON pms_vessel_certificates(yacht_id, status);

-- =============================================================================
-- STEP 5: Document lookup indexes
-- Supports "View Certificate Document" scenario
-- =============================================================================
CREATE INDEX IF NOT EXISTS idx_vessel_certs_doc
ON pms_vessel_certificates(document_id)
WHERE document_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_crew_certs_doc
ON pms_crew_certificates(document_id)
WHERE document_id IS NOT NULL;

-- =============================================================================
-- STEP 6: Person lookup for crew certificates
-- Supports crew member certificate listing
-- =============================================================================
CREATE INDEX IF NOT EXISTS idx_crew_certs_person
ON pms_crew_certificates(person_node_id)
WHERE person_node_id IS NOT NULL;

-- =============================================================================
-- STEP 7: Verification
-- =============================================================================
DO $$
DECLARE
    vessel_idx_count INTEGER;
    crew_idx_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO vessel_idx_count
    FROM pg_indexes
    WHERE tablename = 'pms_vessel_certificates'
      AND indexname LIKE '%vessel_cert%';

    SELECT COUNT(*) INTO crew_idx_count
    FROM pg_indexes
    WHERE tablename = 'pms_crew_certificates'
      AND indexname LIKE '%crew_cert%';

    IF vessel_idx_count < 5 THEN
        RAISE WARNING 'Expected at least 5 vessel certificate indexes, found %', vessel_idx_count;
    END IF;

    IF crew_idx_count < 5 THEN
        RAISE WARNING 'Expected at least 5 crew certificate indexes, found %', crew_idx_count;
    END IF;

    RAISE NOTICE 'SUCCESS: Certificate indexes created (vessel: %, crew: %)', vessel_idx_count, crew_idx_count;
END $$;

COMMIT;

-- =============================================================================
-- ROLLBACK SCRIPT (run separately if needed)
-- =============================================================================
-- BEGIN;
-- DROP INDEX IF EXISTS idx_vessel_certs_yacht;
-- DROP INDEX IF EXISTS idx_crew_certs_yacht;
-- DROP INDEX IF EXISTS ux_vessel_cert_number;
-- DROP INDEX IF EXISTS ux_crew_cert_number;
-- DROP INDEX IF EXISTS ix_vessel_cert_expiry;
-- DROP INDEX IF EXISTS ix_crew_cert_expiry;
-- DROP INDEX IF EXISTS ix_vessel_cert_yacht_expiry;
-- DROP INDEX IF EXISTS ix_crew_cert_yacht_expiry;
-- DROP INDEX IF EXISTS ix_vessel_cert_yacht_status;
-- DROP INDEX IF EXISTS idx_vessel_certs_doc;
-- DROP INDEX IF EXISTS idx_crew_certs_doc;
-- DROP INDEX IF EXISTS idx_crew_certs_person;
-- COMMIT;
