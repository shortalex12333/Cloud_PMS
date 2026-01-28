-- Migration: V1 Show Related - Add related_text columns for surface facts
-- Feature: P1 Show Related - Calculated text for explainability (seeds future embeddings)
-- Date: 2026-01-28
-- Phase: V1 (MVP) - FK-only retrieval, no vectors yet
-- Idempotent: Safe to rerun; checks if columns exist before adding

-- =============================================================================
-- PURPOSE
-- =============================================================================
-- Adds related_text TEXT column to key tables:
--   - Concatenated surface facts for explainability in Show Related
--   - Seeds future embeddings (Phase 2)
--   - NOT used for ranking in V1; FK-only ordering
--
-- Tables:
--   1. pms_work_orders.related_text
--   2. pms_equipment.related_text
--   3. pms_faults.related_text
--   4. pms_work_order_notes.related_text
--   5. pms_attachments.related_text
--   6. doc_metadata.description (future embedding source)
-- =============================================================================

-- =============================================================================
-- TABLE 1: pms_work_orders
-- =============================================================================
-- Template: title | description | completion_notes | equipment: {name, manufacturer, model, system_type}

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'pms_work_orders'
          AND column_name = 'related_text'
    ) THEN
        ALTER TABLE public.pms_work_orders
        ADD COLUMN related_text TEXT;

        RAISE NOTICE 'Added column: pms_work_orders.related_text';
    ELSE
        RAISE NOTICE 'Column pms_work_orders.related_text already exists, skipping';
    END IF;
END $$;

COMMENT ON COLUMN pms_work_orders.related_text IS
'Surface facts for Show Related: title | description | completion_notes | equipment context. Populated by trigger/batch. Seeds future embedding (Phase 2). Added 2026-01-28.';

-- =============================================================================
-- TABLE 2: pms_equipment
-- =============================================================================
-- Template: name | manufacturer | model | location | system_type

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'pms_equipment'
          AND column_name = 'related_text'
    ) THEN
        ALTER TABLE public.pms_equipment
        ADD COLUMN related_text TEXT;

        RAISE NOTICE 'Added column: pms_equipment.related_text';
    ELSE
        RAISE NOTICE 'Column pms_equipment.related_text already exists, skipping';
    END IF;
END $$;

COMMENT ON COLUMN pms_equipment.related_text IS
'Surface facts for Show Related: name | manufacturer | model | location | system_type. Populated by trigger/batch. Seeds future embedding (Phase 2). Added 2026-01-28.';

-- =============================================================================
-- TABLE 3: pms_faults
-- =============================================================================
-- Template: title | description | (fault_code if present)
-- Note: No diagnosis column exists (confirmed via schema inspection)

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'pms_faults'
          AND column_name = 'related_text'
    ) THEN
        ALTER TABLE public.pms_faults
        ADD COLUMN related_text TEXT;

        RAISE NOTICE 'Added column: pms_faults.related_text';
    ELSE
        RAISE NOTICE 'Column pms_faults.related_text already exists, skipping';
    END IF;
END $$;

COMMENT ON COLUMN pms_faults.related_text IS
'Surface facts for Show Related: title | description. Populated by trigger/batch. Seeds future embedding (Phase 2). Added 2026-01-28.';

-- =============================================================================
-- TABLE 4: pms_work_order_notes
-- =============================================================================
-- Template: note_text (capped at 200 chars) + equipment context via work_order JOIN
-- Note: No deleted_at column exists on this table (confirmed)

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'pms_work_order_notes'
          AND column_name = 'related_text'
    ) THEN
        ALTER TABLE public.pms_work_order_notes
        ADD COLUMN related_text TEXT;

        RAISE NOTICE 'Added column: pms_work_order_notes.related_text';
    ELSE
        RAISE NOTICE 'Column pms_work_order_notes.related_text already exists, skipping';
    END IF;
END $$;

COMMENT ON COLUMN pms_work_order_notes.related_text IS
'Surface facts for Show Related: note_text (≤200 chars) + equipment context. Populated by trigger/batch. Seeds future embedding (Phase 2). Added 2026-01-28.';

-- =============================================================================
-- TABLE 5: pms_attachments
-- =============================================================================
-- Template: filename | description
-- Note: This table HAS description column (confirmed) - good for embedding

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'pms_attachments'
          AND column_name = 'related_text'
    ) THEN
        ALTER TABLE public.pms_attachments
        ADD COLUMN related_text TEXT;

        RAISE NOTICE 'Added column: pms_attachments.related_text';
    ELSE
        RAISE NOTICE 'Column pms_attachments.related_text already exists, skipping';
    END IF;
END $$;

COMMENT ON COLUMN pms_attachments.related_text IS
'Surface facts for Show Related: filename | description. Populated by trigger/batch. Seeds future embedding (Phase 2). Added 2026-01-28.';

-- =============================================================================
-- TABLE 6: doc_metadata.description
-- =============================================================================
-- Note: doc_metadata lacks description column (confirmed via schema inspection)
-- This column is ESSENTIAL for meaningful doc embeddings in Phase 2
-- Until populated, doc ranking remains FK-only

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'doc_metadata'
          AND column_name = 'description'
    ) THEN
        ALTER TABLE public.doc_metadata
        ADD COLUMN description TEXT;

        RAISE NOTICE 'Added column: doc_metadata.description';
    ELSE
        RAISE NOTICE 'Column doc_metadata.description already exists, skipping';
    END IF;
END $$;

COMMENT ON COLUMN doc_metadata.description IS
'Human-readable description for manuals/documents. Required for meaningful embeddings. Template: system | topics | key procedures. Backfill manually or via OCR summary. Added 2026-01-28.';

-- =============================================================================
-- VERIFICATION
-- =============================================================================

DO $$
DECLARE
    column_count INT;
BEGIN
    SELECT COUNT(*) INTO column_count
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND (
        (table_name = 'pms_work_orders' AND column_name = 'related_text') OR
        (table_name = 'pms_equipment' AND column_name = 'related_text') OR
        (table_name = 'pms_faults' AND column_name = 'related_text') OR
        (table_name = 'pms_work_order_notes' AND column_name = 'related_text') OR
        (table_name = 'pms_attachments' AND column_name = 'related_text') OR
        (table_name = 'doc_metadata' AND column_name = 'description')
      );

    IF column_count = 6 THEN
        RAISE NOTICE 'Verification passed: All 6 V1 columns created (5 related_text + 1 description)';
    ELSE
        RAISE WARNING 'Expected 6 columns, found %', column_count;
    END IF;
END $$;

-- =============================================================================
-- V1 BACKFILL (Populate related_text from existing data)
-- =============================================================================
-- Run these UPDATE statements AFTER migration to populate related_text columns
-- These are one-time backfills; future updates handled by triggers/batch (Phase 3)

-- Backfill pms_work_orders (without equipment context - simpler for V1)
-- Full context with equipment JOIN done in Phase 2 batch

UPDATE pms_work_orders
SET related_text = CONCAT_WS(' | ',
    title,
    NULLIF(description, ''),
    NULLIF(completion_notes, '')
)
WHERE related_text IS NULL
  AND deleted_at IS NULL;

-- Backfill pms_equipment
UPDATE pms_equipment
SET related_text = CONCAT_WS(' | ',
    name,
    CASE WHEN manufacturer IS NOT NULL THEN 'manufacturer: ' || manufacturer END,
    CASE WHEN model IS NOT NULL THEN 'model: ' || model END,
    CASE WHEN location IS NOT NULL THEN 'location: ' || location END,
    CASE WHEN system_type IS NOT NULL THEN 'system: ' || system_type END
)
WHERE related_text IS NULL
  AND deleted_at IS NULL;

-- Backfill pms_faults
UPDATE pms_faults
SET related_text = CONCAT_WS(' | ',
    title,
    NULLIF(description, '')
)
WHERE related_text IS NULL
  AND deleted_at IS NULL;

-- Backfill pms_work_order_notes (cap at 200 chars)
UPDATE pms_work_order_notes
SET related_text = LEFT(note_text, 200)
WHERE related_text IS NULL;

-- Backfill pms_attachments (has description column)
UPDATE pms_attachments
SET related_text = CONCAT_WS(' | ',
    filename,
    NULLIF(description, '')
)
WHERE related_text IS NULL
  AND deleted_at IS NULL;

-- doc_metadata.description: NOT backfilled automatically
-- Requires manual curation or OCR extraction (future task)

-- =============================================================================
-- ROLLBACK (if needed)
-- =============================================================================
-- ALTER TABLE pms_work_orders DROP COLUMN IF EXISTS related_text;
-- ALTER TABLE pms_equipment DROP COLUMN IF EXISTS related_text;
-- ALTER TABLE pms_faults DROP COLUMN IF EXISTS related_text;
-- ALTER TABLE pms_work_order_notes DROP COLUMN IF EXISTS related_text;
-- ALTER TABLE pms_attachments DROP COLUMN IF EXISTS related_text;
-- ALTER TABLE doc_metadata DROP COLUMN IF EXISTS description;

-- =============================================================================
-- NEXT PHASES
-- =============================================================================
-- Phase 2: Add search_embedding (vector) and embedding_updated_at (timestamptz)
-- Phase 3: Add watchdog/batch to regenerate embeddings on update
-- =============================================================================

-- Migration complete
-- V1 related_text columns ready for FK-only Show Related
