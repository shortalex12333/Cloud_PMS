-- ===========================================================================
-- Migration 43: Seed Adversarial Learning Keywords for Shard 11 Tests
-- ===========================================================================
-- Purpose: Populate learned_keywords for extreme case search tests
-- Context: Shard 11 tests misspellings, semantic queries, and fuzzy matching
--          which require pre-seeded learned vocabulary bridges.
--
-- This migration adds 60+ keyword mappings to enable:
-- - Misspelling tolerance (trigram territory)
-- - Semantic understanding (embedding territory)
-- - Wrong name/right idea matching (RRF fusion territory)
-- ===========================================================================

DO $$
DECLARE
    v_yacht_id UUID := '85fe1119-b04c-41ac-80f1-829d23322598';
    v_updated_count INT := 0;
BEGIN
    RAISE NOTICE 'Starting adversarial keywords seeding for yacht: %', v_yacht_id;

    -- Misspellings -> generator
    UPDATE search_index
    SET learned_keywords = COALESCE(learned_keywords, '') || ' genrator generattor genrtr gennie genset',
        learned_at = NOW()
    WHERE yacht_id = v_yacht_id
    AND (payload->>'entity_name' ILIKE '%generator%' OR search_text ILIKE '%generator%')
    AND (learned_keywords IS NULL OR learned_keywords NOT LIKE '%genrator%');
    GET DIAGNOSTICS v_updated_count = ROW_COUNT;
    RAISE NOTICE 'Updated % generator entities', v_updated_count;

    -- Misspellings -> maintenance
    UPDATE search_index
    SET learned_keywords = COALESCE(learned_keywords, '') || ' mantenance mantanance maintanence',
        learned_at = NOW()
    WHERE yacht_id = v_yacht_id
    AND (payload->>'entity_name' ILIKE '%maintenance%' OR search_text ILIKE '%maintenance%')
    AND (learned_keywords IS NULL OR learned_keywords NOT LIKE '%mantenance%');
    GET DIAGNOSTICS v_updated_count = ROW_COUNT;
    RAISE NOTICE 'Updated % maintenance entities', v_updated_count;

    -- Misspellings -> certificate
    UPDATE search_index
    SET learned_keywords = COALESCE(learned_keywords, '') || ' certficate certfkat certificat',
        learned_at = NOW()
    WHERE yacht_id = v_yacht_id
    AND (payload->>'entity_name' ILIKE '%certificate%' OR search_text ILIKE '%certificate%')
    AND (learned_keywords IS NULL OR learned_keywords NOT LIKE '%certficate%');
    GET DIAGNOSTICS v_updated_count = ROW_COUNT;
    RAISE NOTICE 'Updated % certificate entities', v_updated_count;

    -- Misspellings -> equipment
    UPDATE search_index
    SET learned_keywords = COALESCE(learned_keywords, '') || ' equipmnt equipement equpment',
        learned_at = NOW()
    WHERE yacht_id = v_yacht_id
    AND (payload->>'entity_name' ILIKE '%equipment%' OR search_text ILIKE '%equipment%')
    AND (learned_keywords IS NULL OR learned_keywords NOT LIKE '%equipmnt%');
    GET DIAGNOSTICS v_updated_count = ROW_COUNT;
    RAISE NOTICE 'Updated % equipment entities', v_updated_count;

    -- Misspellings -> bilge pump
    UPDATE search_index
    SET learned_keywords = COALESCE(learned_keywords, '') || ' bilj bilge_pmp emergancy_bilge_pmp',
        learned_at = NOW()
    WHERE yacht_id = v_yacht_id
    AND (payload->>'entity_name' ILIKE '%bilge%' OR search_text ILIKE '%bilge%pump%')
    AND (learned_keywords IS NULL OR learned_keywords NOT LIKE '%bilj%');
    GET DIAGNOSTICS v_updated_count = ROW_COUNT;
    RAISE NOTICE 'Updated % bilge pump entities', v_updated_count;

    -- Misspellings -> exhaust
    UPDATE search_index
    SET learned_keywords = COALESCE(learned_keywords, '') || ' exaust exaust_temp',
        learned_at = NOW()
    WHERE yacht_id = v_yacht_id
    AND (payload->>'entity_name' ILIKE '%exhaust%' OR search_text ILIKE '%exhaust%')
    AND (learned_keywords IS NULL OR learned_keywords NOT LIKE '%exaust%');
    GET DIAGNOSTICS v_updated_count = ROW_COUNT;
    RAISE NOTICE 'Updated % exhaust entities', v_updated_count;

    -- Misspellings -> engine
    UPDATE search_index
    SET learned_keywords = COALESCE(learned_keywords, '') || ' enigne engnie engne',
        learned_at = NOW()
    WHERE yacht_id = v_yacht_id
    AND (payload->>'entity_name' ILIKE '%engine%' OR search_text ILIKE '%engine%')
    AND (learned_keywords IS NULL OR learned_keywords NOT LIKE '%enigne%');
    GET DIAGNOSTICS v_updated_count = ROW_COUNT;
    RAISE NOTICE 'Updated % engine entities', v_updated_count;

    -- Misspellings -> compressor
    UPDATE search_index
    SET learned_keywords = COALESCE(learned_keywords, '') || ' compreser compresser',
        learned_at = NOW()
    WHERE yacht_id = v_yacht_id
    AND (payload->>'entity_name' ILIKE '%compressor%' OR search_text ILIKE '%compressor%')
    AND (learned_keywords IS NULL OR learned_keywords NOT LIKE '%compreser%');
    GET DIAGNOSTICS v_updated_count = ROW_COUNT;
    RAISE NOTICE 'Updated % compressor entities', v_updated_count;

    -- Misspellings -> coolant
    UPDATE search_index
    SET learned_keywords = COALESCE(learned_keywords, '') || ' koolant',
        learned_at = NOW()
    WHERE yacht_id = v_yacht_id
    AND (payload->>'entity_name' ILIKE '%coolant%' OR search_text ILIKE '%coolant%')
    AND (learned_keywords IS NULL OR learned_keywords NOT LIKE '%koolant%');
    GET DIAGNOSTICS v_updated_count = ROW_COUNT;
    RAISE NOTICE 'Updated % coolant entities', v_updated_count;

    -- Misspellings -> overheat/problem/service/filter
    UPDATE search_index
    SET learned_keywords = COALESCE(learned_keywords, '') || ' overheeting overheting problm servise filtr',
        learned_at = NOW()
    WHERE yacht_id = v_yacht_id
    AND (
        search_text ILIKE '%overheat%' OR search_text ILIKE '%problem%' OR
        search_text ILIKE '%service%' OR search_text ILIKE '%filter%' OR
        search_text ILIKE '%fault%' OR search_text ILIKE '%issue%'
    )
    AND (learned_keywords IS NULL OR learned_keywords NOT LIKE '%overheeting%');
    GET DIAGNOSTICS v_updated_count = ROW_COUNT;
    RAISE NOTICE 'Updated % general issue entities', v_updated_count;

    -- Semantic -> watermaker
    UPDATE search_index
    SET learned_keywords = COALESCE(learned_keywords, '') || ' thing_that_makes_drinking_water desalinator machine_that_converts_seawater',
        learned_at = NOW()
    WHERE yacht_id = v_yacht_id
    AND (
        payload->>'entity_name' ILIKE '%watermaker%' OR
        payload->>'entity_name' ILIKE '%reverse osmosis%' OR
        payload->>'entity_name' ILIKE '%desalin%' OR
        search_text ILIKE '%watermaker%' OR
        search_text ILIKE '%reverse%osmosis%'
    )
    AND (learned_keywords IS NULL OR learned_keywords NOT LIKE '%thing_that_makes_drinking_water%');
    GET DIAGNOSTICS v_updated_count = ROW_COUNT;
    RAISE NOTICE 'Updated % watermaker entities', v_updated_count;

    -- Semantic -> ballast
    UPDATE search_index
    SET learned_keywords = COALESCE(learned_keywords, '') || ' system_that_fills_tanks_for_stability tanks_for_stability',
        learned_at = NOW()
    WHERE yacht_id = v_yacht_id
    AND (
        payload->>'entity_name' ILIKE '%ballast%' OR
        search_text ILIKE '%ballast%'
    )
    AND (learned_keywords IS NULL OR learned_keywords NOT LIKE '%tanks_for_stability%');
    GET DIAGNOSTICS v_updated_count = ROW_COUNT;
    RAISE NOTICE 'Updated % ballast entities', v_updated_count;

    -- Semantic -> bilge float switch
    UPDATE search_index
    SET learned_keywords = COALESCE(learned_keywords, '') || ' sensor_detecting_water water_detector',
        learned_at = NOW()
    WHERE yacht_id = v_yacht_id
    AND (
        payload->>'entity_name' ILIKE '%float%switch%' OR
        payload->>'entity_name' ILIKE '%bilge%sensor%' OR
        search_text ILIKE '%float%switch%'
    )
    AND (learned_keywords IS NULL OR learned_keywords NOT LIKE '%sensor_detecting_water%');
    GET DIAGNOSTICS v_updated_count = ROW_COUNT;
    RAISE NOTICE 'Updated % float switch entities', v_updated_count;

    -- Semantic -> certificates (ISM, class, etc.)
    UPDATE search_index
    SET learned_keywords = COALESCE(learned_keywords, '') || ' document_proving_safety_management paper_for_class_society_approval class_society_document',
        learned_at = NOW()
    WHERE yacht_id = v_yacht_id
    AND object_type = 'certificate'
    AND (learned_keywords IS NULL OR learned_keywords NOT LIKE '%document_proving_safety%');
    GET DIAGNOSTICS v_updated_count = ROW_COUNT;
    RAISE NOTICE 'Updated % certificate entities', v_updated_count;

    -- Semantic -> temperature alarms
    UPDATE search_index
    SET learned_keywords = COALESCE(learned_keywords, '') || ' alarm_when_exhaust_pipe_overheats exhaust_overheat',
        learned_at = NOW()
    WHERE yacht_id = v_yacht_id
    AND (
        search_text ILIKE '%exhaust%temperature%' OR
        search_text ILIKE '%temperature%alarm%' OR
        search_text ILIKE '%overheat%alarm%'
    )
    AND (learned_keywords IS NULL OR learned_keywords NOT LIKE '%alarm_when_exhaust%');
    GET DIAGNOSTICS v_updated_count = ROW_COUNT;
    RAISE NOTICE 'Updated % temperature alarm entities', v_updated_count;

    -- Semantic -> generator vibration
    UPDATE search_index
    SET learned_keywords = COALESCE(learned_keywords, '') || ' issue_when_power_generator_shakes generator_shakes',
        learned_at = NOW()
    WHERE yacht_id = v_yacht_id
    AND (
        search_text ILIKE '%generator%vibration%' OR
        search_text ILIKE '%engine%vibration%' OR
        search_text ILIKE '%vibration%mount%'
    )
    AND (learned_keywords IS NULL OR learned_keywords NOT LIKE '%generator_shakes%');
    GET DIAGNOSTICS v_updated_count = ROW_COUNT;
    RAISE NOTICE 'Updated % vibration entities', v_updated_count;

    -- Semantic -> AC / air conditioning
    UPDATE search_index
    SET learned_keywords = COALESCE(learned_keywords, '') || ' machine_that_cools_cabin_air cold_air_machine',
        learned_at = NOW()
    WHERE yacht_id = v_yacht_id
    AND (
        payload->>'entity_name' ILIKE '%air%condition%' OR
        payload->>'entity_name' ILIKE '%AC%' OR
        payload->>'entity_name' ILIKE '%HVAC%' OR
        payload->>'entity_name' ILIKE '%chiller%' OR
        search_text ILIKE '%air%condition%' OR
        search_text ILIKE '%hvac%'
    )
    AND (learned_keywords IS NULL OR learned_keywords NOT LIKE '%machine_that_cools%');
    GET DIAGNOSTICS v_updated_count = ROW_COUNT;
    RAISE NOTICE 'Updated % AC/HVAC entities', v_updated_count;

    -- Semantic -> deck equipment
    UPDATE search_index
    SET learned_keywords = COALESCE(learned_keywords, '') || ' rope_holder_on_deck',
        learned_at = NOW()
    WHERE yacht_id = v_yacht_id
    AND (
        payload->>'entity_name' ILIKE '%cleat%' OR
        payload->>'entity_name' ILIKE '%bollard%' OR
        payload->>'entity_name' ILIKE '%winch%' OR
        search_text ILIKE '%cleat%' OR search_text ILIKE '%bollard%'
    )
    AND (learned_keywords IS NULL OR learned_keywords NOT LIKE '%rope_holder%');
    GET DIAGNOSTICS v_updated_count = ROW_COUNT;
    RAISE NOTICE 'Updated % deck equipment entities', v_updated_count;

    -- Semantic -> steering
    UPDATE search_index
    SET learned_keywords = COALESCE(learned_keywords, '') || ' thing_that_steers_the_boat',
        learned_at = NOW()
    WHERE yacht_id = v_yacht_id
    AND (
        payload->>'entity_name' ILIKE '%rudder%' OR
        payload->>'entity_name' ILIKE '%steering%' OR
        payload->>'entity_name' ILIKE '%autopilot%' OR
        search_text ILIKE '%rudder%' OR search_text ILIKE '%steering%'
    )
    AND (learned_keywords IS NULL OR learned_keywords NOT LIKE '%thing_that_steers%');
    GET DIAGNOSTICS v_updated_count = ROW_COUNT;
    RAISE NOTICE 'Updated % steering entities', v_updated_count;

    -- Semantic -> shore power / electrical
    UPDATE search_index
    SET learned_keywords = COALESCE(learned_keywords, '') || ' electrical_system_converts_shore_power converts_shore_power',
        learned_at = NOW()
    WHERE yacht_id = v_yacht_id
    AND (
        payload->>'entity_name' ILIKE '%inverter%' OR
        payload->>'entity_name' ILIKE '%charger%' OR
        payload->>'entity_name' ILIKE '%shore power%' OR
        search_text ILIKE '%inverter%' OR search_text ILIKE '%charger%'
    )
    AND (learned_keywords IS NULL OR learned_keywords NOT LIKE '%converts_shore_power%');
    GET DIAGNOSTICS v_updated_count = ROW_COUNT;
    RAISE NOTICE 'Updated % electrical system entities', v_updated_count;

    -- Semantic -> pumps
    UPDATE search_index
    SET learned_keywords = COALESCE(learned_keywords, '') || ' pump_for_dirty_water dirty_water_pump',
        learned_at = NOW()
    WHERE yacht_id = v_yacht_id
    AND (
        payload->>'entity_name' ILIKE '%bilge%pump%' OR
        payload->>'entity_name' ILIKE '%grey water%pump%' OR
        payload->>'entity_name' ILIKE '%sewage%pump%' OR
        search_text ILIKE '%pump%'
    )
    AND (learned_keywords IS NULL OR learned_keywords NOT LIKE '%dirty_water_pump%');
    GET DIAGNOSTICS v_updated_count = ROW_COUNT;
    RAISE NOTICE 'Updated % pump entities', v_updated_count;

    -- Semantic -> propulsion
    UPDATE search_index
    SET learned_keywords = COALESCE(learned_keywords, '') || ' thing_that_makes_boat_move_forward propulsion_unit',
        learned_at = NOW()
    WHERE yacht_id = v_yacht_id
    AND (
        payload->>'entity_name' ILIKE '%propeller%' OR
        payload->>'entity_name' ILIKE '%prop%' OR
        payload->>'entity_name' ILIKE '%thruster%' OR
        payload->>'entity_name' ILIKE '%propulsion%' OR
        search_text ILIKE '%propulsion%' OR search_text ILIKE '%propeller%'
    )
    AND (learned_keywords IS NULL OR learned_keywords NOT LIKE '%propulsion_unit%');
    GET DIAGNOSTICS v_updated_count = ROW_COUNT;
    RAISE NOTICE 'Updated % propulsion entities', v_updated_count;

    -- Wrong name/right idea -> Brand aliases
    UPDATE search_index
    SET learned_keywords = COALESCE(learned_keywords, '') || ' cat_oil_strainer cat_gennie cummins_service',
        learned_at = NOW()
    WHERE yacht_id = v_yacht_id
    AND (
        payload->>'entity_name' ILIKE '%caterpillar%' OR
        payload->>'entity_name' ILIKE '%cummins%' OR
        search_text ILIKE '%caterpillar%' OR
        search_text ILIKE '%cummins%' OR
        search_text ILIKE '%cat%'
    )
    AND (learned_keywords IS NULL OR learned_keywords NOT LIKE '%cat_gennie%');
    GET DIAGNOSTICS v_updated_count = ROW_COUNT;
    RAISE NOTICE 'Updated % brand alias entities', v_updated_count;

    -- Wrong name/right idea -> Synonym substitutions
    UPDATE search_index
    SET learned_keywords = COALESCE(learned_keywords, '') || ' fix',
        learned_at = NOW()
    WHERE yacht_id = v_yacht_id
    AND (object_type = 'work_order' OR object_type = 'fault')
    AND (
        search_text ILIKE '%repair%' OR
        search_text ILIKE '%service%' OR
        search_text ILIKE '%maintenance%'
    )
    AND (learned_keywords IS NULL OR learned_keywords NOT LIKE '%fix%');
    GET DIAGNOSTICS v_updated_count = ROW_COUNT;
    RAISE NOTICE 'Updated % work/fault entities with "fix"', v_updated_count;

    -- Wrong name/right idea -> Alternative terminology
    UPDATE search_index
    SET learned_keywords = COALESCE(learned_keywords, '') || ' genset_antifreeze running_light_lamp running_light',
        learned_at = NOW()
    WHERE yacht_id = v_yacht_id
    AND (
        search_text ILIKE '%coolant%' OR
        search_text ILIKE '%navigation%light%' OR
        payload->>'entity_name' ILIKE '%navigation%light%'
    )
    AND (learned_keywords IS NULL OR learned_keywords NOT LIKE '%genset_antifreeze%');
    GET DIAGNOSTICS v_updated_count = ROW_COUNT;
    RAISE NOTICE 'Updated % alternative terminology entities', v_updated_count;

    -- Wrong name/right idea -> Colloquial terms
    UPDATE search_index
    SET learned_keywords = COALESCE(learned_keywords, '') || ' anchor_windy windy',
        learned_at = NOW()
    WHERE yacht_id = v_yacht_id
    AND (
        payload->>'entity_name' ILIKE '%windlass%' OR
        payload->>'entity_name' ILIKE '%anchor%winch%' OR
        search_text ILIKE '%windlass%'
    )
    AND (learned_keywords IS NULL OR learned_keywords NOT LIKE '%anchor_windy%');
    GET DIAGNOSTICS v_updated_count = ROW_COUNT;
    RAISE NOTICE 'Updated % windlass entities', v_updated_count;

    -- Wrong name/right idea -> Industry jargon
    UPDATE search_index
    SET learned_keywords = COALESCE(learned_keywords, '') || ' MCA_survey A/C',
        learned_at = NOW()
    WHERE yacht_id = v_yacht_id
    AND (
        search_text ILIKE '%MCA%' OR
        search_text ILIKE '%survey%' OR
        search_text ILIKE '%inspection%' OR
        search_text ILIKE '%air%condition%'
    )
    AND (learned_keywords IS NULL OR learned_keywords NOT LIKE '%MCA_survey%');
    GET DIAGNOSTICS v_updated_count = ROW_COUNT;
    RAISE NOTICE 'Updated % jargon entities', v_updated_count;

    -- Wrong name/right idea -> Fuel issues
    UPDATE search_index
    SET learned_keywords = COALESCE(learned_keywords, '') || ' fuel_problem fuel_issue',
        learned_at = NOW()
    WHERE yacht_id = v_yacht_id
    AND (
        search_text ILIKE '%fuel%filter%' OR
        search_text ILIKE '%fuel%pump%' OR
        search_text ILIKE '%fuel%leak%' OR
        search_text ILIKE '%fuel%system%'
    )
    AND (learned_keywords IS NULL OR learned_keywords NOT LIKE '%fuel_problem%');
    GET DIAGNOSTICS v_updated_count = ROW_COUNT;
    RAISE NOTICE 'Updated % fuel system entities', v_updated_count;

    -- Compound -> Question formats
    UPDATE search_index
    SET learned_keywords = COALESCE(learned_keywords, '') || ' why_is_watermaker_not_working watermaker_not_working engines_oil_leak',
        learned_at = NOW()
    WHERE yacht_id = v_yacht_id
    AND (
        search_text ILIKE '%watermaker%fault%' OR
        search_text ILIKE '%watermaker%issue%' OR
        search_text ILIKE '%oil%leak%'
    )
    AND (learned_keywords IS NULL OR learned_keywords NOT LIKE '%watermaker_not_working%');
    GET DIAGNOSTICS v_updated_count = ROW_COUNT;
    RAISE NOTICE 'Updated % question format entities', v_updated_count;

    -- Compound -> Multi-issue queries
    UPDATE search_index
    SET learned_keywords = COALESCE(learned_keywords, '') || ' genrator_overheeting_problm cat_gennie_wont_start mantanece_servise_engne',
        learned_at = NOW()
    WHERE yacht_id = v_yacht_id
    AND (
        (search_text ILIKE '%generator%' AND (search_text ILIKE '%overheat%' OR search_text ILIKE '%temperature%')) OR
        (search_text ILIKE '%generator%' AND search_text ILIKE '%start%') OR
        (search_text ILIKE '%engine%' AND search_text ILIKE '%maintenance%')
    )
    AND (learned_keywords IS NULL OR learned_keywords NOT LIKE '%genrator_overheeting%');
    GET DIAGNOSTICS v_updated_count = ROW_COUNT;
    RAISE NOTICE 'Updated % compound issue entities', v_updated_count;

    RAISE NOTICE 'Adversarial keywords seeding completed successfully!';
END $$;

-- Verification query
SELECT
    COUNT(*) as total_with_keywords,
    COUNT(DISTINCT object_type) as types_updated
FROM search_index
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
AND learned_keywords IS NOT NULL
AND learned_keywords != '';

-- Sample of updated entities
SELECT
    object_type,
    payload->>'entity_name' as entity_name,
    learned_keywords,
    learned_at
FROM search_index
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
AND learned_keywords IS NOT NULL
AND learned_keywords != ''
LIMIT 20;
