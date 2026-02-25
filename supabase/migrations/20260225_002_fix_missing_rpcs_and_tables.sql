-- Migration: 20260225_002_fix_missing_rpcs_and_tables.sql
-- Purpose: Fix missing RPCs, tables, and column mismatches for fuzzy search
-- Date: 2026-02-25
--
-- This migration addresses:
-- 1. Add missing pms_shopping_list_items table (referenced but never created)
-- 2. Add missing manufacturer and location columns to pms_parts table
-- 3. Add match_search_index RPC (exists in database/migrations but missing from supabase/migrations)
-- 4. Add missing GIN trigram indexes on pms_parts.manufacturer and pms_parts.location

-- ============================================================================
-- 1. CREATE pms_shopping_list_items TABLE (if not exists)
-- ============================================================================
-- This table is referenced by multiple RPC functions and RLS policies but was never created.
-- The shopping_list_items table (without pms_ prefix) exists, but pms_shopping_list_items does not.

CREATE TABLE IF NOT EXISTS public.pms_shopping_list_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- Part identification
    part_id UUID REFERENCES public.pms_parts(id) ON DELETE SET NULL,
    part_name TEXT NOT NULL,
    part_number TEXT,
    manufacturer TEXT,

    -- Request details
    quantity INT NOT NULL DEFAULT 1,
    quantity_requested NUMERIC DEFAULT 1,
    notes TEXT,
    urgency TEXT DEFAULT 'normal' CHECK (urgency IN ('low', 'normal', 'high', 'urgent')),
    source_type TEXT DEFAULT 'manual_add',
    source_notes TEXT,

    -- Status workflow
    status TEXT DEFAULT 'candidate' CHECK (status IN (
        'candidate', 'under_review', 'approved', 'rejected',
        'ordered', 'received', 'cancelled', 'promoted_to_part'
    )),

    -- Approval workflow
    approved_by UUID,
    approved_at TIMESTAMPTZ,
    rejected_by UUID,
    rejected_at TIMESTAMPTZ,
    rejection_reason TEXT,

    -- Part promotion (for is_candidate_part items)
    is_candidate_part BOOLEAN DEFAULT false,
    promoted_by UUID,
    promoted_at TIMESTAMPTZ,
    candidate_promoted_to_part_id UUID REFERENCES public.pms_parts(id) ON DELETE SET NULL,

    -- Request tracking
    requested_by UUID,
    requested_at TIMESTAMPTZ DEFAULT NOW(),

    -- Purchase order linking
    purchase_order_id UUID REFERENCES public.pms_purchase_orders(id) ON DELETE SET NULL,

    -- Accountability
    created_by UUID,
    updated_by UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Soft delete
    deleted_at TIMESTAMPTZ,
    deleted_by UUID,
    deletion_reason TEXT
);

-- Indexes for pms_shopping_list_items
CREATE INDEX IF NOT EXISTS idx_pms_shopping_list_items_yacht
    ON public.pms_shopping_list_items(yacht_id);
CREATE INDEX IF NOT EXISTS idx_pms_shopping_list_items_status
    ON public.pms_shopping_list_items(yacht_id, status) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_pms_shopping_list_items_urgency
    ON public.pms_shopping_list_items(yacht_id, urgency, created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_pms_shopping_list_items_part
    ON public.pms_shopping_list_items(part_id);

-- Enable RLS
ALTER TABLE public.pms_shopping_list_items ENABLE ROW LEVEL SECURITY;

-- Service role full access
DROP POLICY IF EXISTS "service_role_full_access_pms_shopping" ON public.pms_shopping_list_items;
CREATE POLICY "service_role_full_access_pms_shopping"
    ON public.pms_shopping_list_items FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Authenticated users can view their yacht's items
DROP POLICY IF EXISTS "crew_select_pms_shopping" ON public.pms_shopping_list_items;
CREATE POLICY "crew_select_pms_shopping"
    ON public.pms_shopping_list_items FOR SELECT
    TO authenticated
    USING (
        deleted_at IS NULL
        AND yacht_id = public.get_user_yacht_id()
    );

COMMENT ON TABLE public.pms_shopping_list_items IS
'Shopping list items for parts requisition workflow. Supports candidate parts, approval, and promotion to inventory.';

-- ============================================================================
-- 2. ADD MISSING COLUMNS TO pms_parts TABLE
-- ============================================================================
-- The search_parts_fuzzy function references manufacturer and location columns
-- that don't exist in the original pms_parts table definition.

DO $$
BEGIN
    -- Add manufacturer column if not exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'pms_parts'
          AND column_name = 'manufacturer'
    ) THEN
        ALTER TABLE public.pms_parts ADD COLUMN manufacturer TEXT;
        COMMENT ON COLUMN public.pms_parts.manufacturer IS 'Part manufacturer name';
        RAISE NOTICE 'Added manufacturer column to pms_parts';
    ELSE
        RAISE NOTICE 'manufacturer column already exists on pms_parts';
    END IF;

    -- Add location column if not exists (alias for storage_location in search context)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'pms_parts'
          AND column_name = 'location'
    ) THEN
        ALTER TABLE public.pms_parts ADD COLUMN location TEXT;
        COMMENT ON COLUMN public.pms_parts.location IS 'Part location (search-friendly alias for storage_location)';
        RAISE NOTICE 'Added location column to pms_parts';
    ELSE
        RAISE NOTICE 'location column already exists on pms_parts';
    END IF;
END $$;

-- Add trigram indexes on the new columns
CREATE INDEX IF NOT EXISTS idx_pms_parts_manufacturer_trgm
    ON public.pms_parts USING gin (manufacturer gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_pms_parts_location_trgm
    ON public.pms_parts USING gin (location gin_trgm_ops);

-- ============================================================================
-- 3. ADD match_search_index RPC
-- ============================================================================
-- This RPC exists in database/migrations/44_match_search_index_rpc.sql
-- but is missing from supabase/migrations

CREATE OR REPLACE FUNCTION public.match_search_index(
    p_yacht_id uuid,
    p_query_embedding vector(1536),
    p_match_threshold float DEFAULT 0.70,
    p_match_count int DEFAULT 20,
    p_object_type text DEFAULT NULL
)
RETURNS TABLE(
    object_type text,
    object_id uuid,
    search_text text,
    payload jsonb,
    similarity float
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT
        si.object_type,
        si.object_id,
        si.search_text,
        si.payload,
        (1 - (si.embedding_1536 <=> p_query_embedding))::float AS similarity
    FROM public.search_index si
    WHERE si.yacht_id = p_yacht_id
      AND si.embedding_1536 IS NOT NULL
      AND (p_object_type IS NULL OR si.object_type = p_object_type)
      AND (1 - (si.embedding_1536 <=> p_query_embedding)) >= p_match_threshold
    ORDER BY si.embedding_1536 <=> p_query_embedding
    LIMIT p_match_count;
$$;

-- Grant execute to authenticated users
GRANT EXECUTE ON FUNCTION public.match_search_index(uuid, vector(1536), float, int, text)
    TO authenticated;

-- Grant execute to service role for backend operations
GRANT EXECUTE ON FUNCTION public.match_search_index(uuid, vector(1536), float, int, text)
    TO service_role;

-- Add documentation
COMMENT ON FUNCTION public.match_search_index IS
'LAW 21: Vector similarity search on search_index table using embedding_1536 column.
Uses cosine similarity: 1 - (embedding_1536 <=> query_embedding).
Requires yacht_id for tenant isolation. Optional object_type filter.
Returns object_type, object_id, search_text, payload, and similarity score.';

-- ============================================================================
-- 4. ADD MISSING TRIGRAM INDEXES
-- ============================================================================
-- Some trigram indexes may be missing - ensure they exist

-- pms_parts additional indexes (manufacturer, location added above)
-- These should already exist from 20260225_001, but ensure they're present
CREATE INDEX IF NOT EXISTS idx_pms_parts_name_trgm
    ON public.pms_parts USING gin (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_pms_parts_description_trgm
    ON public.pms_parts USING gin (description gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_pms_parts_part_number_trgm
    ON public.pms_parts USING gin (part_number gin_trgm_ops);

-- pms_equipment indexes
CREATE INDEX IF NOT EXISTS idx_pms_equipment_name_trgm
    ON public.pms_equipment USING gin (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_pms_equipment_serial_number_trgm
    ON public.pms_equipment USING gin (serial_number gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_pms_equipment_manufacturer_trgm
    ON public.pms_equipment USING gin (manufacturer gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_pms_equipment_model_trgm
    ON public.pms_equipment USING gin (model gin_trgm_ops);

-- pms_work_orders indexes
CREATE INDEX IF NOT EXISTS idx_pms_work_orders_title_trgm
    ON public.pms_work_orders USING gin (title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_pms_work_orders_description_trgm
    ON public.pms_work_orders USING gin (description gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_pms_work_orders_wo_number_trgm
    ON public.pms_work_orders USING gin (wo_number gin_trgm_ops);

-- pms_shopping_list_items indexes
CREATE INDEX IF NOT EXISTS idx_pms_shopping_list_items_part_name_trgm
    ON public.pms_shopping_list_items USING gin (part_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_pms_shopping_list_items_part_number_trgm
    ON public.pms_shopping_list_items USING gin (part_number gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_pms_shopping_list_items_manufacturer_trgm
    ON public.pms_shopping_list_items USING gin (manufacturer gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_pms_shopping_list_items_notes_trgm
    ON public.pms_shopping_list_items USING gin (notes gin_trgm_ops);

-- doc_metadata indexes (for search_documents_fuzzy)
CREATE INDEX IF NOT EXISTS idx_doc_metadata_filename_trgm
    ON public.doc_metadata USING gin (filename gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_doc_metadata_description_trgm
    ON public.doc_metadata USING gin (description gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_doc_metadata_doc_type_trgm
    ON public.doc_metadata USING gin (doc_type gin_trgm_ops);

-- ============================================================================
-- 5. VERIFICATION
-- ============================================================================
DO $$
DECLARE
    v_table_exists BOOLEAN;
    v_function_exists BOOLEAN;
    v_manufacturer_exists BOOLEAN;
    v_location_exists BOOLEAN;
BEGIN
    -- Check pms_shopping_list_items table
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'pms_shopping_list_items'
    ) INTO v_table_exists;

    IF v_table_exists THEN
        RAISE NOTICE 'SUCCESS: pms_shopping_list_items table exists';
    ELSE
        RAISE WARNING 'FAILED: pms_shopping_list_items table was not created';
    END IF;

    -- Check match_search_index function
    SELECT EXISTS (
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'public' AND p.proname = 'match_search_index'
    ) INTO v_function_exists;

    IF v_function_exists THEN
        RAISE NOTICE 'SUCCESS: match_search_index function exists';
    ELSE
        RAISE WARNING 'FAILED: match_search_index function was not created';
    END IF;

    -- Check pms_parts.manufacturer column
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'pms_parts'
          AND column_name = 'manufacturer'
    ) INTO v_manufacturer_exists;

    IF v_manufacturer_exists THEN
        RAISE NOTICE 'SUCCESS: pms_parts.manufacturer column exists';
    ELSE
        RAISE WARNING 'FAILED: pms_parts.manufacturer column was not created';
    END IF;

    -- Check pms_parts.location column
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'pms_parts'
          AND column_name = 'location'
    ) INTO v_location_exists;

    IF v_location_exists THEN
        RAISE NOTICE 'SUCCESS: pms_parts.location column exists';
    ELSE
        RAISE WARNING 'FAILED: pms_parts.location column was not created';
    END IF;
END $$;
