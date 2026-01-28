-- ============================================================================
-- MIGRATION: Add Performance Indexes for Certificate Queries
-- ============================================================================
-- PROBLEM: Certificate tables lack indexes for common query patterns
-- SOLUTION: Add indexes for yacht isolation, expiration queries, status filtering
-- SEVERITY: P2 - Performance Enhancement
-- LENS: Certificate Lens v2
-- DATE: 2026-01-25
-- ============================================================================

-- Vessel certificate indexes (skip if table doesn't exist)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pms_vessel_certificates') THEN
        RAISE NOTICE 'pms_vessel_certificates table does not exist - skipping indexes';
    ELSE
        EXECUTE 'CREATE INDEX IF NOT EXISTS idx_vessel_certs_yacht ON pms_vessel_certificates(yacht_id)';
        EXECUTE 'CREATE UNIQUE INDEX IF NOT EXISTS ux_vessel_cert_number ON pms_vessel_certificates(yacht_id, certificate_type, certificate_number) WHERE certificate_number IS NOT NULL';
        EXECUTE 'CREATE INDEX IF NOT EXISTS ix_vessel_cert_expiry ON pms_vessel_certificates(expiry_date) WHERE expiry_date IS NOT NULL';
        EXECUTE 'CREATE INDEX IF NOT EXISTS ix_vessel_cert_yacht_expiry ON pms_vessel_certificates(yacht_id, expiry_date) WHERE status != ''superseded'' AND expiry_date IS NOT NULL';
        EXECUTE 'CREATE INDEX IF NOT EXISTS ix_vessel_cert_yacht_status ON pms_vessel_certificates(yacht_id, status)';
        EXECUTE 'CREATE INDEX IF NOT EXISTS idx_vessel_certs_doc ON pms_vessel_certificates(document_id) WHERE document_id IS NOT NULL';
        RAISE NOTICE 'SUCCESS: Vessel certificate indexes created';
    END IF;
END $$;

-- Crew certificate indexes (skip if table doesn't exist)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pms_crew_certificates') THEN
        RAISE NOTICE 'pms_crew_certificates table does not exist - skipping indexes';
    ELSE
        EXECUTE 'CREATE INDEX IF NOT EXISTS idx_crew_certs_yacht ON pms_crew_certificates(yacht_id)';
        EXECUTE 'CREATE UNIQUE INDEX IF NOT EXISTS ux_crew_cert_number ON pms_crew_certificates(yacht_id, person_name, certificate_type, certificate_number) WHERE certificate_number IS NOT NULL';
        EXECUTE 'CREATE INDEX IF NOT EXISTS ix_crew_cert_expiry ON pms_crew_certificates(expiry_date) WHERE expiry_date IS NOT NULL';
        EXECUTE 'CREATE INDEX IF NOT EXISTS ix_crew_cert_yacht_expiry ON pms_crew_certificates(yacht_id, expiry_date) WHERE expiry_date IS NOT NULL';
        EXECUTE 'CREATE INDEX IF NOT EXISTS idx_crew_certs_doc ON pms_crew_certificates(document_id) WHERE document_id IS NOT NULL';
        EXECUTE 'CREATE INDEX IF NOT EXISTS idx_crew_certs_person ON pms_crew_certificates(person_node_id) WHERE person_node_id IS NOT NULL';
        RAISE NOTICE 'SUCCESS: Crew certificate indexes created';
    END IF;
END $$;
