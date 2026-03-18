-- Migration: Add yacht_id to pms_work_order_notes
-- 
-- The populate_yacht_id_from_work_order BEFORE trigger references NEW.yacht_id
-- but the column was missing. This caused all add_note_to_work_order inserts to fail.
-- The trigger auto-populates this from pms_work_orders on insert.

ALTER TABLE pms_work_order_notes 
ADD COLUMN IF NOT EXISTS yacht_id UUID;

-- Index for yacht-scoped queries
CREATE INDEX IF NOT EXISTS idx_pms_work_order_notes_yacht_id 
ON pms_work_order_notes(yacht_id);
