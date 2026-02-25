-- Migration: 20260225_001_trigram_search_functions
-- LAW 20: Universal Trigram Execution
--
-- Creates fuzzy search functions using pg_trgm for typo-tolerant search.
-- Misspellings like "mantenance" will now find "maintenance".
--
-- Prerequisites: pg_trgm extension (already enabled in 00_enable_extensions.sql)

-- ============================================================================
-- Set trigram similarity threshold (default is 0.3)
-- ============================================================================
-- SET pg_trgm.similarity_threshold = 0.3;

-- ============================================================================
-- PARTS FUZZY SEARCH
-- Searches across part_name, part_number, description, manufacturer, category
-- ============================================================================
CREATE OR REPLACE FUNCTION search_parts_fuzzy(
    p_yacht_id UUID,
    p_query TEXT,
    p_threshold FLOAT DEFAULT 0.3,
    p_limit INT DEFAULT 20
)
RETURNS TABLE (
    part_id UUID,
    part_name TEXT,
    part_number TEXT,
    manufacturer TEXT,
    category TEXT,
    location TEXT,
    description TEXT,
    on_hand INT,
    similarity FLOAT
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id AS part_id,
        p.name AS part_name,
        p.part_number,
        p.manufacturer,
        p.category,
        p.location,
        p.description,
        p.quantity_on_hand AS on_hand,
        GREATEST(
            similarity(COALESCE(p.name, ''), p_query),
            similarity(COALESCE(p.part_number, ''), p_query),
            similarity(COALESCE(p.description, ''), p_query),
            similarity(COALESCE(p.manufacturer, ''), p_query),
            similarity(COALESCE(p.category, ''), p_query)
        ) AS similarity
    FROM pms_parts p
    WHERE p.yacht_id = p_yacht_id
      AND (
          similarity(COALESCE(p.name, ''), p_query) > p_threshold
          OR similarity(COALESCE(p.part_number, ''), p_query) > p_threshold
          OR similarity(COALESCE(p.description, ''), p_query) > p_threshold
          OR similarity(COALESCE(p.manufacturer, ''), p_query) > p_threshold
          OR similarity(COALESCE(p.category, ''), p_query) > p_threshold
          -- Also check word similarity for multi-word queries
          OR strict_word_similarity(p_query, COALESCE(p.name, '')) > p_threshold
          OR strict_word_similarity(p_query, COALESCE(p.description, '')) > p_threshold
      )
    ORDER BY similarity DESC
    LIMIT p_limit;
END;
$$;

-- Grant execute to authenticated users
GRANT EXECUTE ON FUNCTION search_parts_fuzzy(UUID, TEXT, FLOAT, INT) TO authenticated;
GRANT EXECUTE ON FUNCTION search_parts_fuzzy(UUID, TEXT, FLOAT, INT) TO service_role;

-- ============================================================================
-- EQUIPMENT FUZZY SEARCH
-- ============================================================================
CREATE OR REPLACE FUNCTION search_equipment_fuzzy(
    p_yacht_id UUID,
    p_query TEXT,
    p_threshold FLOAT DEFAULT 0.3,
    p_limit INT DEFAULT 20
)
RETURNS TABLE (
    equipment_id UUID,
    equipment_name TEXT,
    serial_number TEXT,
    manufacturer TEXT,
    equipment_type TEXT,
    model TEXT,
    location TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    SELECT
        e.id AS equipment_id,
        e.name AS equipment_name,
        e.serial_number,
        e.manufacturer,
        e.equipment_type,
        e.model,
        e.location,
        GREATEST(
            similarity(COALESCE(e.name, ''), p_query),
            similarity(COALESCE(e.serial_number, ''), p_query),
            similarity(COALESCE(e.manufacturer, ''), p_query),
            similarity(COALESCE(e.equipment_type, ''), p_query),
            similarity(COALESCE(e.model, ''), p_query)
        ) AS similarity
    FROM pms_equipment e
    WHERE e.yacht_id = p_yacht_id
      AND (
          similarity(COALESCE(e.name, ''), p_query) > p_threshold
          OR similarity(COALESCE(e.serial_number, ''), p_query) > p_threshold
          OR similarity(COALESCE(e.manufacturer, ''), p_query) > p_threshold
          OR similarity(COALESCE(e.equipment_type, ''), p_query) > p_threshold
          OR similarity(COALESCE(e.model, ''), p_query) > p_threshold
          OR strict_word_similarity(p_query, COALESCE(e.name, '')) > p_threshold
      )
    ORDER BY similarity DESC
    LIMIT p_limit;
END;
$$;

GRANT EXECUTE ON FUNCTION search_equipment_fuzzy(UUID, TEXT, FLOAT, INT) TO authenticated;
GRANT EXECUTE ON FUNCTION search_equipment_fuzzy(UUID, TEXT, FLOAT, INT) TO service_role;

-- ============================================================================
-- WORK ORDERS FUZZY SEARCH
-- ============================================================================
CREATE OR REPLACE FUNCTION search_work_orders_fuzzy(
    p_yacht_id UUID,
    p_query TEXT,
    p_threshold FLOAT DEFAULT 0.3,
    p_limit INT DEFAULT 20
)
RETURNS TABLE (
    work_order_id UUID,
    work_order_number TEXT,
    title TEXT,
    description TEXT,
    status TEXT,
    priority TEXT,
    assigned_to_name TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    SELECT
        wo.id AS work_order_id,
        wo.wo_number AS work_order_number,
        wo.title,
        wo.description,
        wo.status,
        wo.priority,
        wo.assigned_to_name,
        GREATEST(
            similarity(COALESCE(wo.title, ''), p_query),
            similarity(COALESCE(wo.description, ''), p_query),
            similarity(COALESCE(wo.wo_number, ''), p_query)
        ) AS similarity
    FROM pms_work_orders wo
    WHERE wo.yacht_id = p_yacht_id
      AND (
          similarity(COALESCE(wo.title, ''), p_query) > p_threshold
          OR similarity(COALESCE(wo.description, ''), p_query) > p_threshold
          OR similarity(COALESCE(wo.wo_number, ''), p_query) > p_threshold
          OR strict_word_similarity(p_query, COALESCE(wo.title, '')) > p_threshold
          OR strict_word_similarity(p_query, COALESCE(wo.description, '')) > p_threshold
      )
    ORDER BY similarity DESC
    LIMIT p_limit;
END;
$$;

GRANT EXECUTE ON FUNCTION search_work_orders_fuzzy(UUID, TEXT, FLOAT, INT) TO authenticated;
GRANT EXECUTE ON FUNCTION search_work_orders_fuzzy(UUID, TEXT, FLOAT, INT) TO service_role;

-- ============================================================================
-- DOCUMENTS FUZZY SEARCH
-- ============================================================================
CREATE OR REPLACE FUNCTION search_documents_fuzzy(
    p_yacht_id UUID,
    p_query TEXT,
    p_threshold FLOAT DEFAULT 0.3,
    p_limit INT DEFAULT 20
)
RETURNS TABLE (
    id UUID,
    filename TEXT,
    description TEXT,
    doc_type TEXT,
    content_type TEXT,
    created_at TIMESTAMPTZ,
    similarity FLOAT
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    SELECT
        d.id,
        d.filename,
        d.description,
        d.doc_type,
        d.content_type,
        d.created_at,
        GREATEST(
            similarity(COALESCE(d.filename, ''), p_query),
            similarity(COALESCE(d.description, ''), p_query),
            similarity(COALESCE(d.doc_type, ''), p_query)
        ) AS similarity
    FROM doc_metadata d
    WHERE d.yacht_id = p_yacht_id
      AND d.deleted_at IS NULL
      AND (
          similarity(COALESCE(d.filename, ''), p_query) > p_threshold
          OR similarity(COALESCE(d.description, ''), p_query) > p_threshold
          OR similarity(COALESCE(d.doc_type, ''), p_query) > p_threshold
          OR strict_word_similarity(p_query, COALESCE(d.filename, '')) > p_threshold
          OR strict_word_similarity(p_query, COALESCE(d.description, '')) > p_threshold
      )
    ORDER BY similarity DESC
    LIMIT p_limit;
END;
$$;

GRANT EXECUTE ON FUNCTION search_documents_fuzzy(UUID, TEXT, FLOAT, INT) TO authenticated;
GRANT EXECUTE ON FUNCTION search_documents_fuzzy(UUID, TEXT, FLOAT, INT) TO service_role;

-- ============================================================================
-- SHOPPING LIST ITEMS FUZZY SEARCH
-- ============================================================================
CREATE OR REPLACE FUNCTION search_shopping_list_fuzzy(
    p_yacht_id UUID,
    p_query TEXT,
    p_threshold FLOAT DEFAULT 0.3,
    p_limit INT DEFAULT 20
)
RETURNS TABLE (
    shopping_list_item_id UUID,
    part_name TEXT,
    part_number TEXT,
    manufacturer TEXT,
    notes TEXT,
    status TEXT,
    quantity INT,
    similarity FLOAT
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    SELECT
        s.id AS shopping_list_item_id,
        s.part_name,
        s.part_number,
        s.manufacturer,
        s.notes,
        s.status,
        s.quantity,
        GREATEST(
            similarity(COALESCE(s.part_name, ''), p_query),
            similarity(COALESCE(s.part_number, ''), p_query),
            similarity(COALESCE(s.manufacturer, ''), p_query),
            similarity(COALESCE(s.notes, ''), p_query)
        ) AS similarity
    FROM pms_shopping_list_items s
    WHERE s.yacht_id = p_yacht_id
      AND (
          similarity(COALESCE(s.part_name, ''), p_query) > p_threshold
          OR similarity(COALESCE(s.part_number, ''), p_query) > p_threshold
          OR similarity(COALESCE(s.manufacturer, ''), p_query) > p_threshold
          OR similarity(COALESCE(s.notes, ''), p_query) > p_threshold
          OR strict_word_similarity(p_query, COALESCE(s.part_name, '')) > p_threshold
      )
    ORDER BY similarity DESC
    LIMIT p_limit;
END;
$$;

GRANT EXECUTE ON FUNCTION search_shopping_list_fuzzy(UUID, TEXT, FLOAT, INT) TO authenticated;
GRANT EXECUTE ON FUNCTION search_shopping_list_fuzzy(UUID, TEXT, FLOAT, INT) TO service_role;

-- ============================================================================
-- Fallback function for parts (in case table schema differs)
-- This uses a slightly different approach with % operator
-- ============================================================================
CREATE OR REPLACE FUNCTION search_parts_trigram_fallback(
    p_yacht_id UUID,
    p_query TEXT,
    p_threshold FLOAT DEFAULT 0.3,
    p_limit INT DEFAULT 20
)
RETURNS TABLE (
    id UUID,
    name TEXT,
    part_number TEXT,
    manufacturer TEXT,
    category TEXT,
    location TEXT,
    description TEXT,
    quantity_on_hand INT,
    similarity FLOAT
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    -- Set the threshold for the % operator
    PERFORM set_limit(p_threshold);

    RETURN QUERY
    SELECT
        p.id,
        p.name,
        p.part_number,
        p.manufacturer,
        p.category,
        p.location,
        p.description,
        p.quantity_on_hand,
        GREATEST(
            similarity(COALESCE(p.name, ''), p_query),
            similarity(COALESCE(p.part_number, ''), p_query),
            similarity(COALESCE(p.description, ''), p_query)
        ) AS similarity
    FROM pms_parts p
    WHERE p.yacht_id = p_yacht_id
      AND (
          COALESCE(p.name, '') % p_query
          OR COALESCE(p.part_number, '') % p_query
          OR COALESCE(p.description, '') % p_query
          OR COALESCE(p.manufacturer, '') % p_query
          OR COALESCE(p.category, '') % p_query
      )
    ORDER BY similarity DESC
    LIMIT p_limit;
END;
$$;

GRANT EXECUTE ON FUNCTION search_parts_trigram_fallback(UUID, TEXT, FLOAT, INT) TO authenticated;
GRANT EXECUTE ON FUNCTION search_parts_trigram_fallback(UUID, TEXT, FLOAT, INT) TO service_role;

-- ============================================================================
-- Create GIN indexes for trigram if not exists
-- These dramatically speed up fuzzy searches
-- ============================================================================

-- Parts table indexes
CREATE INDEX IF NOT EXISTS idx_pms_parts_name_trgm
    ON pms_parts USING gin (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_pms_parts_description_trgm
    ON pms_parts USING gin (description gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_pms_parts_part_number_trgm
    ON pms_parts USING gin (part_number gin_trgm_ops);

-- Equipment table indexes
CREATE INDEX IF NOT EXISTS idx_pms_equipment_name_trgm
    ON pms_equipment USING gin (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_pms_equipment_serial_number_trgm
    ON pms_equipment USING gin (serial_number gin_trgm_ops);

-- Work orders table indexes
CREATE INDEX IF NOT EXISTS idx_pms_work_orders_title_trgm
    ON pms_work_orders USING gin (title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_pms_work_orders_description_trgm
    ON pms_work_orders USING gin (description gin_trgm_ops);

-- Documents table indexes
CREATE INDEX IF NOT EXISTS idx_doc_metadata_filename_trgm
    ON doc_metadata USING gin (filename gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_doc_metadata_description_trgm
    ON doc_metadata USING gin (description gin_trgm_ops);

-- Shopping list indexes
CREATE INDEX IF NOT EXISTS idx_pms_shopping_list_items_part_name_trgm
    ON pms_shopping_list_items USING gin (part_name gin_trgm_ops);

-- ============================================================================
-- Add comment for documentation
-- ============================================================================
COMMENT ON FUNCTION search_parts_fuzzy IS 'LAW 20: Fuzzy search for parts using pg_trgm. Handles misspellings like "mantenance" -> "maintenance"';
COMMENT ON FUNCTION search_equipment_fuzzy IS 'LAW 20: Fuzzy search for equipment using pg_trgm';
COMMENT ON FUNCTION search_work_orders_fuzzy IS 'LAW 20: Fuzzy search for work orders using pg_trgm';
COMMENT ON FUNCTION search_documents_fuzzy IS 'LAW 20: Fuzzy search for documents using pg_trgm';
COMMENT ON FUNCTION search_shopping_list_fuzzy IS 'LAW 20: Fuzzy search for shopping list items using pg_trgm';
