-- Drop pms_handover table that should have been dropped in consolidation migration
-- This table was replaced by handover_items with the consolidation migration
-- but it still exists in the tenant DB

BEGIN;

-- Drop the legacy table
DROP TABLE IF EXISTS pms_handover CASCADE;

COMMIT;

-- Verification query (run separately):
-- SELECT table_name FROM information_schema.tables
-- WHERE table_schema = 'public' AND table_name LIKE '%handover%';
