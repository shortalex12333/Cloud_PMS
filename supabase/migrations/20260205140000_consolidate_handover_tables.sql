-- =============================================================================
-- MIGRATION: Consolidate Handover Tables
-- =============================================================================
-- Date: 2026-02-05
-- Purpose: Simplify handover schema from 8+ tables to 2 tables
--
-- BEFORE: handovers, handover_items, pms_handover, handover_drafts,
--         handover_exports, handover_signoffs, handover_buckets,
--         role_handover_buckets, plus 4 backup tables
--
-- AFTER:  handover_items (draft notes) + handover_exports (exported + signoff)
--
-- =============================================================================

BEGIN;

-- =============================================================================
-- STEP 1: Add columns to handover_items (draft notes table)
-- =============================================================================

-- Add category (was only in pms_handover)
ALTER TABLE handover_items
ADD COLUMN IF NOT EXISTS category TEXT;

-- Add is_critical flag
ALTER TABLE handover_items
ADD COLUMN IF NOT EXISTS is_critical BOOLEAN DEFAULT false;

-- Add requires_action flag
ALTER TABLE handover_items
ADD COLUMN IF NOT EXISTS requires_action BOOLEAN DEFAULT false;

-- Add action_summary for describing what action is needed
ALTER TABLE handover_items
ADD COLUMN IF NOT EXISTS action_summary TEXT;

-- Add risk_tags array for categorization
ALTER TABLE handover_items
ADD COLUMN IF NOT EXISTS risk_tags TEXT[];

-- Add entity_url for direct links in exports
ALTER TABLE handover_items
ADD COLUMN IF NOT EXISTS entity_url TEXT;

-- Make handover_id nullable (we're removing parent container concept)
ALTER TABLE handover_items
ALTER COLUMN handover_id DROP NOT NULL;

-- Drop FK constraint to handovers table
ALTER TABLE handover_items
DROP CONSTRAINT IF EXISTS handover_items_handover_id_fkey;

-- =============================================================================
-- STEP 2: Add signoff columns to handover_exports
-- =============================================================================

-- Add department column (for filtering by role)
ALTER TABLE handover_exports
ADD COLUMN IF NOT EXISTS department TEXT;

-- Add outgoing signoff columns
ALTER TABLE handover_exports
ADD COLUMN IF NOT EXISTS outgoing_user_id UUID;

ALTER TABLE handover_exports
ADD COLUMN IF NOT EXISTS outgoing_role TEXT;

ALTER TABLE handover_exports
ADD COLUMN IF NOT EXISTS outgoing_signed_at TIMESTAMPTZ;

ALTER TABLE handover_exports
ADD COLUMN IF NOT EXISTS outgoing_notes TEXT;

-- Add incoming signoff columns
ALTER TABLE handover_exports
ADD COLUMN IF NOT EXISTS incoming_user_id UUID;

ALTER TABLE handover_exports
ADD COLUMN IF NOT EXISTS incoming_role TEXT;

ALTER TABLE handover_exports
ADD COLUMN IF NOT EXISTS incoming_signed_at TIMESTAMPTZ;

ALTER TABLE handover_exports
ADD COLUMN IF NOT EXISTS incoming_notes TEXT;

ALTER TABLE handover_exports
ADD COLUMN IF NOT EXISTS incoming_acknowledged_critical BOOLEAN DEFAULT false;

-- Add signoff_complete flag
ALTER TABLE handover_exports
ADD COLUMN IF NOT EXISTS signoff_complete BOOLEAN DEFAULT false;

-- Make draft_id nullable (we're removing handover_drafts)
ALTER TABLE handover_exports
ALTER COLUMN draft_id DROP NOT NULL;

-- Drop FK constraint to handover_drafts
ALTER TABLE handover_exports
DROP CONSTRAINT IF EXISTS handover_exports_draft_id_fkey;

-- =============================================================================
-- STEP 3: Migrate signoff data from handover_signoffs to handover_exports
-- =============================================================================

-- Copy signoff data to matching exports (by draft_id)
UPDATE handover_exports e
SET
    outgoing_user_id = s.outgoing_user_id,
    outgoing_role = s.outgoing_role,
    outgoing_signed_at = s.outgoing_signed_at,
    outgoing_notes = s.outgoing_notes,
    incoming_user_id = s.incoming_user_id,
    incoming_role = s.incoming_role,
    incoming_signed_at = s.incoming_signed_at,
    incoming_notes = s.incoming_notes,
    incoming_acknowledged_critical = s.incoming_acknowledged_critical,
    signoff_complete = s.signoff_complete
FROM handover_signoffs s
WHERE e.draft_id = s.draft_id;

-- =============================================================================
-- STEP 4: Create new indexes for added columns
-- =============================================================================

-- Index for category filtering
CREATE INDEX IF NOT EXISTS idx_handover_items_category
ON handover_items(yacht_id, category)
WHERE deleted_at IS NULL;

-- Index for critical items
CREATE INDEX IF NOT EXISTS idx_handover_items_critical
ON handover_items(yacht_id, is_critical)
WHERE is_critical = true AND deleted_at IS NULL;

-- Index for requires_action items
CREATE INDEX IF NOT EXISTS idx_handover_items_action
ON handover_items(yacht_id, requires_action)
WHERE requires_action = true AND deleted_at IS NULL;

-- Index for exports by department
CREATE INDEX IF NOT EXISTS idx_handover_exports_department
ON handover_exports(yacht_id, department);

-- Index for exports awaiting signoff
CREATE INDEX IF NOT EXISTS idx_handover_exports_signoff
ON handover_exports(yacht_id, signoff_complete)
WHERE signoff_complete = false;

-- =============================================================================
-- STEP 5: Drop FK constraints from tables being dropped
-- =============================================================================

-- Drop FK from handover_signoffs to handover_drafts
ALTER TABLE handover_signoffs
DROP CONSTRAINT IF EXISTS handover_signoffs_draft_id_fkey;

-- Drop any other FKs to handover_drafts
ALTER TABLE handover_draft_items
DROP CONSTRAINT IF EXISTS handover_draft_items_draft_id_fkey;

ALTER TABLE handover_draft_items
DROP CONSTRAINT IF EXISTS handover_draft_items_section_id_fkey;

ALTER TABLE handover_draft_sections
DROP CONSTRAINT IF EXISTS handover_draft_sections_draft_id_fkey;

ALTER TABLE handover_draft_edits
DROP CONSTRAINT IF EXISTS handover_draft_edits_draft_id_fkey;

ALTER TABLE handover_draft_edits
DROP CONSTRAINT IF EXISTS handover_draft_edits_draft_item_id_fkey;

-- =============================================================================
-- STEP 6: Drop views that depend on tables being dropped
-- =============================================================================

DROP VIEW IF EXISTS v_handover_export_items CASCADE;
DROP VIEW IF EXISTS v_handover_draft_complete CASCADE;
DROP VIEW IF EXISTS v_handover_signoffs CASCADE;

-- =============================================================================
-- STEP 7: Drop unused tables
-- =============================================================================

-- Drop backup tables (pollution)
DROP TABLE IF EXISTS _bkp_dash_handover_items CASCADE;
DROP TABLE IF EXISTS _bkp_dash_handover_records CASCADE;
DROP TABLE IF EXISTS _bkp_handover_entries CASCADE;
DROP TABLE IF EXISTS _bkp_handover_sources CASCADE;

-- Drop draft workflow tables (not used in code)
DROP TABLE IF EXISTS handover_draft_edits CASCADE;
DROP TABLE IF EXISTS handover_draft_items CASCADE;
DROP TABLE IF EXISTS handover_draft_sections CASCADE;
DROP TABLE IF EXISTS handover_signoffs CASCADE;
DROP TABLE IF EXISTS handover_drafts CASCADE;

-- Drop bucket config tables (hardcode 8 buckets in app)
DROP TABLE IF EXISTS role_handover_buckets CASCADE;
DROP TABLE IF EXISTS handover_buckets CASCADE;

-- Drop parent container table (items are standalone now)
DROP TABLE IF EXISTS handovers CASCADE;

-- Drop quick-add table (merged concept into handover_items)
DROP TABLE IF EXISTS pms_handover CASCADE;

-- =============================================================================
-- STEP 8: Create simplified unified view for exports
-- =============================================================================

CREATE OR REPLACE VIEW v_handover_export_items AS
SELECT
    hi.id,
    hi.yacht_id,
    hi.entity_type,
    hi.entity_id,
    COALESCE(hi.summary, '') as summary_text,
    hi.section,
    hi.category,
    hi.priority,
    hi.status,
    hi.is_critical,
    hi.requires_action,
    hi.action_summary,
    hi.risk_tags,
    hi.entity_url,
    hi.added_by,
    hi.created_at as added_at,
    hi.acknowledged_by,
    hi.acknowledged_at,
    hi.metadata,
    'handover_items' as source_table
FROM handover_items hi
WHERE hi.deleted_at IS NULL;

-- =============================================================================
-- STEP 9: Add comment documentation
-- =============================================================================

COMMENT ON TABLE handover_items IS
'Draft handover items - notes users submit before export. Supports view/edit/delete until exported.';

COMMENT ON TABLE handover_exports IS
'Exported handover documents with signoff tracking. Files stored in handover-exports bucket.';

COMMENT ON COLUMN handover_items.category IS
'Item category: urgent, in_progress, completed, watch, fyi';

COMMENT ON COLUMN handover_items.is_critical IS
'Flag for critical items requiring immediate attention';

COMMENT ON COLUMN handover_items.requires_action IS
'Flag for items requiring follow-up action';

COMMENT ON COLUMN handover_items.risk_tags IS
'Array of risk tags: Safety_Critical, Compliance_Critical, Guest_Impacting, Cost_Impacting, Operational_Debt, Informational';

COMMENT ON COLUMN handover_exports.department IS
'Department filter: Command, Engineering, ETO_AVIT, Deck, Interior, Galley, Security, Admin_Compliance';

COMMENT ON COLUMN handover_exports.signoff_complete IS
'True when both outgoing and incoming users have signed';

COMMIT;
