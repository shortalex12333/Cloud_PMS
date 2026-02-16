-- ============================================================================
-- MIGRATION: 20260216_add_po_number_to_receiving.sql
-- PURPOSE: Add missing po_number column to pms_receiving table
-- FIX FOR: rpc_insert_receiving failing because it tries to insert po_number
--          but the column doesn't exist in the table
-- DATE: 2026-02-16
-- ============================================================================

BEGIN;

-- Add po_number column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'pms_receiving'
          AND column_name = 'po_number'
    ) THEN
        ALTER TABLE public.pms_receiving
        ADD COLUMN po_number TEXT;

        COMMENT ON COLUMN public.pms_receiving.po_number IS 'Purchase order number this receiving is linked to';

        RAISE NOTICE 'SUCCESS: Added po_number column to pms_receiving';
    ELSE
        RAISE NOTICE 'SKIPPED: po_number column already exists in pms_receiving';
    END IF;
END $$;

COMMIT;
