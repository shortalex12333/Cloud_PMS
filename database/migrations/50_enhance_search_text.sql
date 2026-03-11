-- Migration 50: Enhance search_text with synonyms for better trigram matching
-- Description: Appends object-type-specific aliases to search_text to improve
--              recall for common query variations (e.g., "show WOs" -> matches work_order)
--
-- Problem Addressed:
--   - Lens Accuracy is 46.2% but Recall@3 is only 13.2%
--   - Queries like "show WOs", "defects", "spares" don't match because
--     search_text lacks common aliases for object types
--
-- Approach:
--   - Preserve existing search_text content
--   - Append type-specific synonyms as a suffix
--   - Use a marker to prevent duplicate appends on re-runs
--
-- Dependencies: 01_create_search_index.sql
-- Safe to re-run: Yes (uses idempotent marker check)
--
-- Post-migration:
--   - Rows will need re-embedding (handled by embedding_worker)
--   - Consider running: UPDATE search_index SET embedding_status = 'pending'
--     WHERE object_type IN (...) to trigger re-processing

-- =============================================================================
-- SYNONYM DEFINITIONS (inline for migration portability)
-- =============================================================================

-- Create a temporary function to hold synonym mappings
CREATE OR REPLACE FUNCTION get_search_synonyms(p_object_type TEXT)
RETURNS TEXT
LANGUAGE plpgsql
IMMUTABLE
AS $$
BEGIN
    RETURN CASE p_object_type
        WHEN 'work_order' THEN 'work order WO task job maintenance repair service PM preventive maintenance corrective scheduled'
        WHEN 'fault' THEN 'fault defect issue problem failure breakdown malfunction incident report damage error'
        WHEN 'certificate' THEN 'certificate cert document doc credential license licence permit compliance expiring renewal valid flag state'
        WHEN 'equipment' THEN 'equipment machine unit asset device machinery system component gear apparatus'
        WHEN 'part' THEN 'part spare component item consumable supply replacement piece'
        WHEN 'inventory' THEN 'inventory stock parts spares supplies onboard quantity storage warehouse location'
        WHEN 'email' THEN 'email mail message correspondence communication inbox'
        WHEN 'hours_of_rest' THEN 'hours of rest rest hours crew rest MLC compliance violation fatigue work hours schedule rest period maritime labour'
        WHEN 'receiving' THEN 'receiving delivery shipment package arrival receipt incoming inbound cargo consignment'
        WHEN 'handover' THEN 'handover handover note changeover turnover shift transition brief briefing watch'
        WHEN 'handover_item' THEN 'handover handover item handover note changeover turnover shift note transition item'
        WHEN 'shopping_list' THEN 'shopping list shopping wish list wishlist to order requisition request needed purchase request'
        WHEN 'shopping_item' THEN 'shopping item shopping wish list item requisition item purchase request to order needed'
        WHEN 'warranty' THEN 'warranty guarantee claim coverage manufacturer warranty'
        WHEN 'document' THEN 'document doc file PDF manual specification drawing attachment'
        WHEN 'supplier' THEN 'supplier vendor manufacturer provider company contact'
        WHEN 'purchase_order' THEN 'purchase order PO order procurement buy purchasing'
        WHEN 'work_order_note' THEN 'work order note WO note note comment update remark log entry'
        WHEN 'note' THEN 'note comment remark annotation memo'
        ELSE NULL
    END;
END;
$$;

-- =============================================================================
-- IDEMPOTENT SYNONYM APPENDER
-- =============================================================================

-- Function to safely append synonyms without duplicating
CREATE OR REPLACE FUNCTION append_search_synonyms(
    p_existing_text TEXT,
    p_object_type TEXT
)
RETURNS TEXT
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    v_synonyms TEXT;
    v_marker TEXT := ' [ALIASES:';
    v_result TEXT;
BEGIN
    -- Get synonyms for this object type
    v_synonyms := get_search_synonyms(p_object_type);

    -- If no synonyms defined, return original text
    IF v_synonyms IS NULL THEN
        RETURN p_existing_text;
    END IF;

    -- Check if already enhanced (idempotent check)
    IF p_existing_text IS NOT NULL AND p_existing_text LIKE '%' || v_marker || '%' THEN
        RETURN p_existing_text;
    END IF;

    -- Build result: existing_text + marker + synonyms
    IF p_existing_text IS NULL OR TRIM(p_existing_text) = '' THEN
        v_result := v_synonyms || v_marker || p_object_type || ']';
    ELSE
        v_result := TRIM(p_existing_text) || ' ' || v_synonyms || v_marker || p_object_type || ']';
    END IF;

    -- Truncate if too long (max 12000 chars as per projection_worker)
    IF LENGTH(v_result) > 12000 THEN
        v_result := LEFT(v_result, 12000);
    END IF;

    RETURN v_result;
END;
$$;

-- =============================================================================
-- MIGRATION: Enhance search_text for all object types
-- =============================================================================

-- Count rows that will be affected (for verification)
DO $$
DECLARE
    v_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_count
    FROM search_index
    WHERE search_text IS NULL
       OR search_text NOT LIKE '%[ALIASES:%]';

    RAISE NOTICE 'Rows to enhance: %', v_count;
END;
$$;

-- Perform the update in batches to avoid long locks
-- Batch 1: work_order and work_order_note (most common queries)
UPDATE search_index
SET search_text = append_search_synonyms(search_text, object_type),
    updated_at = NOW()
WHERE object_type IN ('work_order', 'work_order_note')
  AND (search_text IS NULL OR search_text NOT LIKE '%[ALIASES:%]');

-- Batch 2: fault, certificate, equipment
UPDATE search_index
SET search_text = append_search_synonyms(search_text, object_type),
    updated_at = NOW()
WHERE object_type IN ('fault', 'certificate', 'equipment')
  AND (search_text IS NULL OR search_text NOT LIKE '%[ALIASES:%]');

-- Batch 3: part, inventory, receiving
UPDATE search_index
SET search_text = append_search_synonyms(search_text, object_type),
    updated_at = NOW()
WHERE object_type IN ('part', 'inventory', 'receiving')
  AND (search_text IS NULL OR search_text NOT LIKE '%[ALIASES:%]');

-- Batch 4: shopping_item, shopping_list, email
UPDATE search_index
SET search_text = append_search_synonyms(search_text, object_type),
    updated_at = NOW()
WHERE object_type IN ('shopping_item', 'shopping_list', 'email')
  AND (search_text IS NULL OR search_text NOT LIKE '%[ALIASES:%]');

-- Batch 5: hours_of_rest, handover, handover_item
UPDATE search_index
SET search_text = append_search_synonyms(search_text, object_type),
    updated_at = NOW()
WHERE object_type IN ('hours_of_rest', 'handover', 'handover_item')
  AND (search_text IS NULL OR search_text NOT LIKE '%[ALIASES:%]');

-- Batch 6: document, supplier, purchase_order, warranty, note
UPDATE search_index
SET search_text = append_search_synonyms(search_text, object_type),
    updated_at = NOW()
WHERE object_type IN ('document', 'supplier', 'purchase_order', 'warranty', 'note')
  AND (search_text IS NULL OR search_text NOT LIKE '%[ALIASES:%]');

-- =============================================================================
-- VERIFICATION
-- =============================================================================

-- Verify the migration worked
DO $$
DECLARE
    v_enhanced INTEGER;
    v_total INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_enhanced
    FROM search_index
    WHERE search_text LIKE '%[ALIASES:%]';

    SELECT COUNT(*) INTO v_total
    FROM search_index;

    RAISE NOTICE 'Enhanced rows: % / % total (%.1f%%)',
        v_enhanced, v_total, (v_enhanced::NUMERIC / NULLIF(v_total, 0) * 100);
END;
$$;

-- =============================================================================
-- OPTIONAL: Queue for re-embedding (uncomment to trigger embedding refresh)
-- =============================================================================

-- This will cause embedding_worker to re-process all enhanced rows
-- Uncomment if you want fresh embeddings that include the synonyms
--
-- UPDATE search_index
-- SET embedding_status = 'pending'
-- WHERE search_text LIKE '%[ALIASES:%]'
--   AND embedding_status = 'indexed';

-- =============================================================================
-- GRANTS
-- =============================================================================

-- Grant execute on helper functions to service role
GRANT EXECUTE ON FUNCTION get_search_synonyms(TEXT) TO service_role;
GRANT EXECUTE ON FUNCTION append_search_synonyms(TEXT, TEXT) TO service_role;

-- =============================================================================
-- COMMENTS
-- =============================================================================

COMMENT ON FUNCTION get_search_synonyms IS
'Returns space-separated synonyms/aliases for a given object_type.
Used by search_text enhancement to improve trigram matching for common query variations.
Example: "work_order" returns "work order WO task job maintenance repair..."';

COMMENT ON FUNCTION append_search_synonyms IS
'Idempotently appends type-specific synonyms to search_text.
Uses [ALIASES:type] marker to prevent duplicate appends on re-runs.
Preserves existing search_text content.';
