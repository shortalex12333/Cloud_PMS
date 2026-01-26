-- Add unique constraint on certificate_number per yacht
-- This prevents duplicate certificate numbers within the same yacht

-- Vessel certificates: unique per yacht
ALTER TABLE pms_vessel_certificates
ADD CONSTRAINT pms_vessel_certificates_yacht_cert_num_unique
UNIQUE (yacht_id, certificate_number);

-- Crew certificates: unique per yacht
ALTER TABLE pms_crew_certificates
ADD CONSTRAINT pms_crew_certificates_yacht_cert_num_unique
UNIQUE (yacht_id, certificate_number);
