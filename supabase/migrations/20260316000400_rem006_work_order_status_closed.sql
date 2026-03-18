-- =============================================================================
-- REM-006: Add 'closed' value to work_order_status enum
-- Date: 2026-03-16
-- Context: update_equipment_status fails with 22P02 because a DB trigger on
--          pms_equipment cascades equipment status changes to related work orders
--          by setting their status to 'closed', which is not in the enum.
-- =============================================================================

-- ⚠ TRANSACTION RESTRICTION:
--   ALTER TYPE ... ADD VALUE cannot run inside a multi-statement transaction
--   in Postgres < 12. In Supabase SQL Editor this auto-commits and works fine.
--   In CI migration pipelines that wrap in BEGIN/COMMIT, this MUST run as its
--   own migration file (already done — this file contains only this statement).

ALTER TYPE work_order_status ADD VALUE IF NOT EXISTS 'closed';

-- STEP 2: Verify
-- SELECT enumlabel FROM pg_enum
-- WHERE enumtypid = 'work_order_status'::regtype AND enumlabel = 'closed';
