-- Add unique constraint on certificate_number per yacht
-- This prevents duplicate certificate numbers within the same yacht

-- Vessel certificates: unique per yacht
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pms_vessel_certificates') THEN
        IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE constraint_name = 'pms_vessel_certificates_yacht_cert_num_unique') THEN
            EXECUTE 'ALTER TABLE pms_vessel_certificates ADD CONSTRAINT pms_vessel_certificates_yacht_cert_num_unique UNIQUE (yacht_id, certificate_number)';
            RAISE NOTICE 'Added unique constraint to pms_vessel_certificates';
        END IF;
    ELSE
        RAISE NOTICE 'pms_vessel_certificates table does not exist - skipping';
    END IF;
END $$;

-- Crew certificates: unique per yacht
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pms_crew_certificates') THEN
        IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE constraint_name = 'pms_crew_certificates_yacht_cert_num_unique') THEN
            EXECUTE 'ALTER TABLE pms_crew_certificates ADD CONSTRAINT pms_crew_certificates_yacht_cert_num_unique UNIQUE (yacht_id, certificate_number)';
            RAISE NOTICE 'Added unique constraint to pms_crew_certificates';
        END IF;
    ELSE
        RAISE NOTICE 'pms_crew_certificates table does not exist - skipping';
    END IF;
END $$;
