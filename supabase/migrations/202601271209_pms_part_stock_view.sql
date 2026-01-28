-- Migration: 20260127_209_pms_part_stock_view.sql
-- Purpose: Canonical pms_part_stock compatibility view (Part Lens v2)
-- Date: 2026-01-27
-- Author: Part Lens v2 Implementation
-- Defensive: Only uses columns that exist

-- ============================================================================
-- CONTEXT
-- ============================================================================
-- This view provides the canonical pms_part_stock interface expected by:
--   - Suggestions endpoint
--   - Handler guard checks (consume_part, transfer_part)
--   - Tests and downstream code
--
-- Source: Derives on_hand from pms_parts.quantity_on_hand (authoritative)
-- ============================================================================

DO $$
DECLARE
    has_quantity_on_hand BOOLEAN;
    has_min_level BOOLEAN;
    has_reorder_multiple BOOLEAN;
    has_location BOOLEAN;
    has_is_critical BOOLEAN;
    has_department BOOLEAN;
    has_category BOOLEAN;
    has_name BOOLEAN;
    has_part_number BOOLEAN;
    view_sql TEXT;
BEGIN
    -- Check if pms_parts exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pms_parts' AND table_schema = 'public') THEN
        RAISE NOTICE 'pms_parts table does not exist - skipping pms_part_stock view';
        RETURN;
    END IF;

    -- Check which columns exist
    SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'pms_parts' AND column_name = 'quantity_on_hand') INTO has_quantity_on_hand;
    SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'pms_parts' AND column_name = 'min_level') INTO has_min_level;
    SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'pms_parts' AND column_name = 'reorder_multiple') INTO has_reorder_multiple;
    SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'pms_parts' AND column_name = 'location') INTO has_location;
    SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'pms_parts' AND column_name = 'is_critical') INTO has_is_critical;
    SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'pms_parts' AND column_name = 'department') INTO has_department;
    SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'pms_parts' AND column_name = 'category') INTO has_category;
    SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'pms_parts' AND column_name = 'name') INTO has_name;
    SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'pms_parts' AND column_name = 'part_number') INTO has_part_number;

    -- Drop existing view
    DROP VIEW IF EXISTS pms_part_stock CASCADE;

    -- Build view dynamically based on available columns
    view_sql := 'CREATE VIEW pms_part_stock AS SELECT p.yacht_id, p.id AS part_id';

    -- on_hand
    IF has_quantity_on_hand THEN
        view_sql := view_sql || ', COALESCE(p.quantity_on_hand, 0) AS on_hand';
    ELSE
        view_sql := view_sql || ', 0 AS on_hand';
    END IF;

    -- min_level
    IF has_min_level THEN
        view_sql := view_sql || ', COALESCE(p.min_level, 0) AS min_level';
    ELSE
        view_sql := view_sql || ', 0 AS min_level';
    END IF;

    -- reorder_multiple
    IF has_reorder_multiple THEN
        view_sql := view_sql || ', COALESCE(p.reorder_multiple, 1) AS reorder_multiple';
    ELSE
        view_sql := view_sql || ', 1 AS reorder_multiple';
    END IF;

    -- location
    IF has_location THEN
        view_sql := view_sql || ', p.location';
    ELSE
        view_sql := view_sql || ', NULL::TEXT AS location';
    END IF;

    -- is_critical
    IF has_is_critical THEN
        view_sql := view_sql || ', COALESCE(p.is_critical, false) AS is_critical';
    ELSE
        view_sql := view_sql || ', false AS is_critical';
    END IF;

    -- department
    IF has_department THEN
        view_sql := view_sql || ', p.department';
    ELSE
        view_sql := view_sql || ', NULL::TEXT AS department';
    END IF;

    -- category
    IF has_category THEN
        view_sql := view_sql || ', p.category';
    ELSE
        view_sql := view_sql || ', NULL::TEXT AS category';
    END IF;

    -- part_name
    IF has_name THEN
        view_sql := view_sql || ', p.name AS part_name';
    ELSE
        view_sql := view_sql || ', NULL::TEXT AS part_name';
    END IF;

    -- part_number
    IF has_part_number THEN
        view_sql := view_sql || ', p.part_number';
    ELSE
        view_sql := view_sql || ', NULL::TEXT AS part_number';
    END IF;

    view_sql := view_sql || ' FROM pms_parts p';

    -- Execute the view creation
    EXECUTE view_sql;

    -- Grant access
    EXECUTE 'GRANT SELECT ON pms_part_stock TO authenticated';
    EXECUTE 'GRANT SELECT ON pms_part_stock TO service_role';

    RAISE NOTICE 'SUCCESS: pms_part_stock view created';
END $$;

-- Add comment (safe even if view doesn't exist)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.views WHERE table_name = 'pms_part_stock' AND table_schema = 'public') THEN
        EXECUTE 'COMMENT ON VIEW pms_part_stock IS ''Canonical view for Part Lens v2 - authoritative on_hand source for suggestions and handler guards''';
    END IF;
END $$;
