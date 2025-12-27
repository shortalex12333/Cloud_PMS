-- ============================================================================
-- ENTITY RESOLUTION SYSTEM
-- Manually reviewed and cleaned alias tables + resolver functions
-- ============================================================================
-- Deploy to Supabase via SQL Editor or psql
-- ============================================================================

-- Enable pg_trgm extension for fuzzy matching
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ============================================================================
-- PART 1: ALIAS TABLES
-- ============================================================================

-- 1.1 Equipment Aliases
CREATE TABLE IF NOT EXISTS public.equipment_aliases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
    equipment_id UUID REFERENCES equipment(id) ON DELETE CASCADE,
    alias TEXT NOT NULL,
    alias_type TEXT DEFAULT 'manual' CHECK (alias_type IN ('manual', 'learned', 'llm_generated')),
    confidence FLOAT DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (yacht_id, LOWER(alias))
);

CREATE INDEX IF NOT EXISTS idx_equipment_aliases_yacht ON equipment_aliases(yacht_id);
CREATE INDEX IF NOT EXISTS idx_equipment_aliases_trgm ON equipment_aliases USING gin (alias gin_trgm_ops);

-- 1.2 Symptom Aliases (global, not yacht-specific)
CREATE TABLE IF NOT EXISTS public.symptom_aliases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symptom_code TEXT NOT NULL,  -- e.g., 'OVERHEAT', 'VIBRATION'
    alias TEXT NOT NULL,
    alias_type TEXT DEFAULT 'manual',
    confidence FLOAT DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (LOWER(alias))
);

CREATE INDEX IF NOT EXISTS idx_symptom_aliases_trgm ON symptom_aliases USING gin (alias gin_trgm_ops);

-- 1.3 Part Aliases
CREATE TABLE IF NOT EXISTS public.part_aliases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
    part_id UUID REFERENCES parts(id) ON DELETE CASCADE,
    alias TEXT NOT NULL,
    alias_type TEXT DEFAULT 'manual',
    confidence FLOAT DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (yacht_id, LOWER(alias))
);

CREATE INDEX IF NOT EXISTS idx_part_aliases_yacht ON part_aliases(yacht_id);
CREATE INDEX IF NOT EXISTS idx_part_aliases_trgm ON part_aliases USING gin (alias gin_trgm_ops);

-- ============================================================================
-- PART 2: RESOLVER FUNCTIONS
-- ============================================================================

-- 2.1 Resolve Equipment
CREATE OR REPLACE FUNCTION public.resolve_equipment(
    query_text TEXT,
    p_yacht_id UUID,
    match_limit INT DEFAULT 5,
    min_similarity FLOAT DEFAULT 0.3
)
RETURNS TABLE (
    equipment_id UUID,
    equipment_name TEXT,
    match_type TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql SECURITY DEFINER STABLE
AS $$
BEGIN
    RETURN QUERY
    WITH all_matches AS (
        -- Exact alias match (highest priority)
        SELECT ea.equipment_id, e.name AS equipment_name,
               'alias_exact'::TEXT AS match_type, 1.0::FLOAT AS similarity, 1 AS priority
        FROM equipment_aliases ea
        JOIN equipment e ON ea.equipment_id = e.id
        WHERE ea.yacht_id = p_yacht_id AND LOWER(ea.alias) = LOWER(query_text)

        UNION ALL

        -- Exact name match
        SELECT e.id, e.name, 'name_exact', 1.0, 2
        FROM equipment e
        WHERE e.yacht_id = p_yacht_id AND LOWER(e.name) = LOWER(query_text)

        UNION ALL

        -- Fuzzy alias match
        SELECT ea.equipment_id, e.name, 'alias_fuzzy',
               similarity(LOWER(ea.alias), LOWER(query_text))::FLOAT, 3
        FROM equipment_aliases ea
        JOIN equipment e ON ea.equipment_id = e.id
        WHERE ea.yacht_id = p_yacht_id
          AND similarity(LOWER(ea.alias), LOWER(query_text)) >= min_similarity

        UNION ALL

        -- Fuzzy name match
        SELECT e.id, e.name, 'name_fuzzy',
               similarity(LOWER(e.name), LOWER(query_text))::FLOAT, 4
        FROM equipment e
        WHERE e.yacht_id = p_yacht_id
          AND similarity(LOWER(e.name), LOWER(query_text)) >= min_similarity

        UNION ALL

        -- Manufacturer/model match
        SELECT e.id, e.name, 'manufacturer_model',
            GREATEST(
                COALESCE(similarity(LOWER(e.manufacturer), LOWER(query_text)), 0),
                COALESCE(similarity(LOWER(e.model), LOWER(query_text)), 0)
            )::FLOAT, 5
        FROM equipment e
        WHERE e.yacht_id = p_yacht_id
          AND (similarity(LOWER(COALESCE(e.manufacturer, '')), LOWER(query_text)) >= min_similarity
               OR similarity(LOWER(COALESCE(e.model, '')), LOWER(query_text)) >= min_similarity)
    )
    SELECT DISTINCT ON (am.equipment_id)
           am.equipment_id, am.equipment_name, am.match_type, am.similarity
    FROM all_matches am
    ORDER BY am.equipment_id, am.priority, am.similarity DESC
    LIMIT match_limit;
END;
$$;

-- 2.2 Resolve Symptom (returns symptom code)
CREATE OR REPLACE FUNCTION public.resolve_symptom_alias(
    p_alias_text TEXT
)
RETURNS TEXT
LANGUAGE plpgsql SECURITY DEFINER STABLE
AS $$
DECLARE
    v_symptom_code TEXT;
BEGIN
    -- Exact match first
    SELECT symptom_code INTO v_symptom_code
    FROM symptom_aliases
    WHERE LOWER(alias) = LOWER(p_alias_text)
    ORDER BY confidence DESC
    LIMIT 1;

    IF v_symptom_code IS NOT NULL THEN
        RETURN v_symptom_code;
    END IF;

    -- Fuzzy match
    SELECT symptom_code INTO v_symptom_code
    FROM symptom_aliases
    WHERE similarity(LOWER(alias), LOWER(p_alias_text)) >= 0.4
    ORDER BY similarity(LOWER(alias), LOWER(p_alias_text)) DESC, confidence DESC
    LIMIT 1;

    RETURN v_symptom_code;
END;
$$;

-- 2.3 Unified Entity Alias Resolver (for Cloud_PMS compatibility)
CREATE OR REPLACE FUNCTION public.resolve_entity_alias(
    p_yacht_id UUID,
    p_entity_type TEXT,
    p_alias_text TEXT
)
RETURNS TEXT
LANGUAGE plpgsql SECURITY DEFINER STABLE
AS $$
DECLARE
    v_result TEXT;
BEGIN
    IF p_entity_type = 'equipment' THEN
        SELECT equipment_id::TEXT INTO v_result
        FROM public.resolve_equipment(p_alias_text, p_yacht_id, 1, 0.4)
        LIMIT 1;

    ELSIF p_entity_type = 'part' THEN
        -- Exact alias match
        SELECT pa.part_id::TEXT INTO v_result
        FROM part_aliases pa
        WHERE pa.yacht_id = p_yacht_id AND LOWER(pa.alias) = LOWER(p_alias_text)
        LIMIT 1;

        -- Fallback to fuzzy
        IF v_result IS NULL THEN
            SELECT pa.part_id::TEXT INTO v_result
            FROM part_aliases pa
            WHERE pa.yacht_id = p_yacht_id
              AND similarity(LOWER(pa.alias), LOWER(p_alias_text)) >= 0.4
            ORDER BY similarity(LOWER(pa.alias), LOWER(p_alias_text)) DESC
            LIMIT 1;
        END IF;

    ELSIF p_entity_type = 'fault' OR p_entity_type = 'fault_code' THEN
        -- Fault codes are typically looked up directly, not via alias
        -- Return the normalized code
        v_result := UPPER(REPLACE(p_alias_text, ' ', ''));
    END IF;

    RETURN v_result;
END;
$$;

-- Grant permissions
GRANT EXECUTE ON FUNCTION public.resolve_equipment TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.resolve_symptom_alias TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.resolve_entity_alias TO authenticated, service_role;

-- ============================================================================
-- PART 3: SEED DATA - MANUALLY REVIEWED ALIASES
-- ============================================================================
-- These are GENERIC aliases that do NOT assume specific equipment brands
-- They only resolve when the yacht's equipment inventory matches
-- ============================================================================

-- SYMPTOM ALIASES (Global - not yacht-specific)
-- These map user language to symptom codes

INSERT INTO symptom_aliases (symptom_code, alias, alias_type, confidence) VALUES
-- Vibration
('VIBRATION', 'vibration', 'manual', 1.0),
('VIBRATION', 'vibrating', 'manual', 1.0),
('VIBRATION', 'shaking', 'manual', 0.95),
('VIBRATION', 'shudder', 'manual', 0.9),
('VIBRATION', 'shuddering', 'manual', 0.9),
('VIBRATION', 'rough running', 'manual', 0.85),
('VIBRATION', 'wobble', 'manual', 0.8),
('VIBRATION', 'resonance', 'manual', 0.75),

-- Overheating
('OVERHEAT', 'overheating', 'manual', 1.0),
('OVERHEAT', 'overheat', 'manual', 1.0),
('OVERHEAT', 'running hot', 'manual', 0.95),
('OVERHEAT', 'high temp', 'manual', 0.9),
('OVERHEAT', 'high temperature', 'manual', 0.9),
('OVERHEAT', 'thermal alarm', 'manual', 0.85),
('OVERHEAT', 'temp alarm', 'manual', 0.85),
('OVERHEAT', 'hot', 'manual', 0.7),

-- Leak
('LEAK', 'leak', 'manual', 1.0),
('LEAK', 'leaking', 'manual', 1.0),
('LEAK', 'drip', 'manual', 0.9),
('LEAK', 'dripping', 'manual', 0.9),
('LEAK', 'seepage', 'manual', 0.85),
('LEAK', 'seeping', 'manual', 0.85),
('LEAK', 'water ingress', 'manual', 0.8),
('LEAK', 'weeping', 'manual', 0.75),

-- Noise
('NOISE', 'noise', 'manual', 1.0),
('NOISE', 'noisy', 'manual', 1.0),
('NOISE', 'loud', 'manual', 0.8),
('NOISE', 'grinding', 'manual', 0.95),
('NOISE', 'squealing', 'manual', 0.9),
('NOISE', 'knocking', 'manual', 0.9),
('NOISE', 'banging', 'manual', 0.85),
('NOISE', 'rattling', 'manual', 0.85),
('NOISE', 'clicking', 'manual', 0.8),
('NOISE', 'whining', 'manual', 0.85),
('NOISE', 'unusual sound', 'manual', 0.8),
('NOISE', 'strange noise', 'manual', 0.85),

-- Smoke
('SMOKE', 'smoke', 'manual', 1.0),
('SMOKE', 'smoking', 'manual', 1.0),
('SMOKE', 'black smoke', 'manual', 0.95),
('SMOKE', 'white smoke', 'manual', 0.95),
('SMOKE', 'blue smoke', 'manual', 0.95),
('SMOKE', 'exhaust smoke', 'manual', 0.9),
('SMOKE', 'fumes', 'manual', 0.8),
('SMOKE', 'burning smell', 'manual', 0.75),

-- Pressure Issues
('LOW_PRESSURE', 'low pressure', 'manual', 1.0),
('LOW_PRESSURE', 'pressure drop', 'manual', 0.95),
('LOW_PRESSURE', 'no pressure', 'manual', 0.9),
('LOW_PRESSURE', 'losing pressure', 'manual', 0.9),
('LOW_PRESSURE', 'pressure loss', 'manual', 0.9),
('LOW_PRESSURE', 'oil pressure low', 'manual', 0.85),
('LOW_PRESSURE', 'fuel pressure low', 'manual', 0.85),

-- Starting Issues
('START_FAILURE', 'wont start', 'manual', 1.0),
('START_FAILURE', 'will not start', 'manual', 1.0),
('START_FAILURE', 'not starting', 'manual', 1.0),
('START_FAILURE', 'hard start', 'manual', 0.85),
('START_FAILURE', 'slow crank', 'manual', 0.8),
('START_FAILURE', 'no crank', 'manual', 0.9),
('START_FAILURE', 'cranks but wont start', 'manual', 0.9),

-- Electrical
('ELECTRICAL', 'electrical fault', 'manual', 1.0),
('ELECTRICAL', 'electrical problem', 'manual', 0.95),
('ELECTRICAL', 'short circuit', 'manual', 0.9),
('ELECTRICAL', 'tripped breaker', 'manual', 0.85),
('ELECTRICAL', 'blown fuse', 'manual', 0.85),
('ELECTRICAL', 'no power', 'manual', 0.8),
('ELECTRICAL', 'power loss', 'manual', 0.8)

ON CONFLICT (LOWER(alias)) DO UPDATE SET
    symptom_code = EXCLUDED.symptom_code,
    confidence = EXCLUDED.confidence;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

DO $$
DECLARE
    eq_alias_count INT;
    sym_alias_count INT;
BEGIN
    SELECT COUNT(*) INTO eq_alias_count FROM equipment_aliases;
    SELECT COUNT(*) INTO sym_alias_count FROM symptom_aliases;

    RAISE NOTICE '=== ENTITY RESOLUTION SETUP COMPLETE ===';
    RAISE NOTICE 'Equipment aliases: %', eq_alias_count;
    RAISE NOTICE 'Symptom aliases: %', sym_alias_count;
    RAISE NOTICE '';
    RAISE NOTICE 'Functions created:';
    RAISE NOTICE '  - resolve_equipment(query_text, p_yacht_id, ...)';
    RAISE NOTICE '  - resolve_symptom_alias(p_alias_text)';
    RAISE NOTICE '  - resolve_entity_alias(p_yacht_id, p_entity_type, p_alias_text)';
END $$;
