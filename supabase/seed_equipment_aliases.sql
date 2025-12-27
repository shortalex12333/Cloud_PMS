-- ============================================================================
-- EQUIPMENT ALIAS SEEDING
-- Run this for a specific yacht to create aliases based on actual inventory
-- ============================================================================
-- Usage: Set the yacht_id below, then run this script
-- ============================================================================

-- SET YOUR YACHT ID HERE
-- Example: SET session_yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598';
DO $$
DECLARE
    v_yacht_id UUID := '85fe1119-b04c-41ac-80f1-829d23322598';  -- CHANGE THIS
    v_alias_count INT := 0;
BEGIN
    RAISE NOTICE 'Seeding equipment aliases for yacht: %', v_yacht_id;

    -- ========================================================================
    -- POSITIONAL ALIASES (Port/Starboard engines)
    -- These only create if equipment with matching location/code exists
    -- ========================================================================

    -- Port engine aliases
    INSERT INTO equipment_aliases (yacht_id, equipment_id, alias, alias_type, confidence)
    SELECT v_yacht_id, e.id, alias.val, 'manual', 1.0
    FROM equipment e
    CROSS JOIN (VALUES
        ('port engine'),
        ('port main'),
        ('port main engine'),
        ('ME1'),
        ('main engine 1'),
        ('engine 1')
    ) AS alias(val)
    WHERE e.yacht_id = v_yacht_id
      AND (
          LOWER(e.name) LIKE '%port%engine%'
          OR LOWER(e.name) LIKE '%engine%port%'
          OR LOWER(e.location) ILIKE '%port%'
          OR (LOWER(e.system_type) = 'propulsion' AND LOWER(e.code) LIKE '%1%')
      )
    ON CONFLICT (yacht_id, LOWER(alias)) DO NOTHING;

    -- Starboard engine aliases
    INSERT INTO equipment_aliases (yacht_id, equipment_id, alias, alias_type, confidence)
    SELECT v_yacht_id, e.id, alias.val, 'manual', 1.0
    FROM equipment e
    CROSS JOIN (VALUES
        ('starboard engine'),
        ('stbd engine'),
        ('starboard main'),
        ('stbd main'),
        ('ME2'),
        ('main engine 2'),
        ('engine 2')
    ) AS alias(val)
    WHERE e.yacht_id = v_yacht_id
      AND (
          LOWER(e.name) LIKE '%starboard%engine%'
          OR LOWER(e.name) LIKE '%stbd%engine%'
          OR LOWER(e.location) ILIKE '%starboard%'
          OR LOWER(e.location) ILIKE '%stbd%'
          OR (LOWER(e.system_type) = 'propulsion' AND LOWER(e.code) LIKE '%2%')
      )
    ON CONFLICT (yacht_id, LOWER(alias)) DO NOTHING;

    -- ========================================================================
    -- GENERATOR ALIASES (DG1, DG2, DG3)
    -- ========================================================================

    INSERT INTO equipment_aliases (yacht_id, equipment_id, alias, alias_type, confidence)
    SELECT v_yacht_id, e.id, alias.val, 'manual', 1.0
    FROM equipment e
    CROSS JOIN (VALUES
        ('generator 1'),
        ('gen 1'),
        ('genset 1'),
        ('DG1')
    ) AS alias(val)
    WHERE e.yacht_id = v_yacht_id
      AND LOWER(e.system_type) = 'electrical'
      AND (
          LOWER(e.name) LIKE '%generator%'
          OR LOWER(e.name) LIKE '%genset%'
      )
      AND (LOWER(e.code) LIKE '%1%' OR LOWER(e.name) LIKE '%1%')
    ON CONFLICT (yacht_id, LOWER(alias)) DO NOTHING;

    INSERT INTO equipment_aliases (yacht_id, equipment_id, alias, alias_type, confidence)
    SELECT v_yacht_id, e.id, alias.val, 'manual', 1.0
    FROM equipment e
    CROSS JOIN (VALUES
        ('generator 2'),
        ('gen 2'),
        ('genset 2'),
        ('DG2')
    ) AS alias(val)
    WHERE e.yacht_id = v_yacht_id
      AND LOWER(e.system_type) = 'electrical'
      AND (
          LOWER(e.name) LIKE '%generator%'
          OR LOWER(e.name) LIKE '%genset%'
      )
      AND (LOWER(e.code) LIKE '%2%' OR LOWER(e.name) LIKE '%2%')
    ON CONFLICT (yacht_id, LOWER(alias)) DO NOTHING;

    INSERT INTO equipment_aliases (yacht_id, equipment_id, alias, alias_type, confidence)
    SELECT v_yacht_id, e.id, alias.val, 'manual', 1.0
    FROM equipment e
    CROSS JOIN (VALUES
        ('generator 3'),
        ('gen 3'),
        ('genset 3'),
        ('DG3'),
        ('emergency generator'),
        ('emergency gen')
    ) AS alias(val)
    WHERE e.yacht_id = v_yacht_id
      AND LOWER(e.system_type) = 'electrical'
      AND (
          LOWER(e.name) LIKE '%generator%'
          OR LOWER(e.name) LIKE '%genset%'
          OR LOWER(e.name) LIKE '%emergency%'
      )
      AND (LOWER(e.code) LIKE '%3%' OR LOWER(e.name) LIKE '%3%' OR LOWER(e.name) LIKE '%emergency%')
    ON CONFLICT (yacht_id, LOWER(alias)) DO NOTHING;

    -- ========================================================================
    -- GENERIC EQUIPMENT TYPE ALIASES
    -- Only created if equipment of that type exists
    -- ========================================================================

    -- Watermaker
    INSERT INTO equipment_aliases (yacht_id, equipment_id, alias, alias_type, confidence)
    SELECT v_yacht_id, e.id, alias.val, 'manual', 1.0
    FROM equipment e
    CROSS JOIN (VALUES
        ('watermaker'),
        ('water maker'),
        ('desal'),
        ('desalinator'),
        ('reverse osmosis'),
        ('RO system')
    ) AS alias(val)
    WHERE e.yacht_id = v_yacht_id
      AND (
          LOWER(e.name) LIKE '%watermaker%'
          OR LOWER(e.name) LIKE '%water maker%'
          OR LOWER(e.name) LIKE '%desal%'
          OR LOWER(e.name) LIKE '%reverse osmosis%'
          OR LOWER(e.system_type) LIKE '%water%'
      )
    ON CONFLICT (yacht_id, LOWER(alias)) DO NOTHING;

    -- HVAC / Air Conditioning
    INSERT INTO equipment_aliases (yacht_id, equipment_id, alias, alias_type, confidence)
    SELECT v_yacht_id, e.id, alias.val, 'manual', 1.0
    FROM equipment e
    CROSS JOIN (VALUES
        ('AC'),
        ('A/C'),
        ('air conditioning'),
        ('air conditioner'),
        ('HVAC'),
        ('climate control'),
        ('chiller')
    ) AS alias(val)
    WHERE e.yacht_id = v_yacht_id
      AND (
          LOWER(e.name) LIKE '%hvac%'
          OR LOWER(e.name) LIKE '%air condition%'
          OR LOWER(e.name) LIKE '%chiller%'
          OR LOWER(e.system_type) ILIKE '%hvac%'
          OR LOWER(e.system_type) ILIKE '%climate%'
      )
    ON CONFLICT (yacht_id, LOWER(alias)) DO NOTHING;

    -- Stabilizers
    INSERT INTO equipment_aliases (yacht_id, equipment_id, alias, alias_type, confidence)
    SELECT v_yacht_id, e.id, alias.val, 'manual', 1.0
    FROM equipment e
    CROSS JOIN (VALUES
        ('stabilizers'),
        ('stabilizer'),
        ('stabs'),
        ('fin stabilizers'),
        ('roll stabilizer')
    ) AS alias(val)
    WHERE e.yacht_id = v_yacht_id
      AND (
          LOWER(e.name) LIKE '%stabiliz%'
          OR LOWER(e.system_type) LIKE '%stabiliz%'
      )
    ON CONFLICT (yacht_id, LOWER(alias)) DO NOTHING;

    -- Thrusters
    INSERT INTO equipment_aliases (yacht_id, equipment_id, alias, alias_type, confidence)
    SELECT v_yacht_id, e.id, alias.val, 'manual', 1.0
    FROM equipment e
    CROSS JOIN (VALUES
        ('bow thruster'),
        ('BT'),
        ('forward thruster')
    ) AS alias(val)
    WHERE e.yacht_id = v_yacht_id
      AND LOWER(e.name) LIKE '%bow%thruster%'
    ON CONFLICT (yacht_id, LOWER(alias)) DO NOTHING;

    INSERT INTO equipment_aliases (yacht_id, equipment_id, alias, alias_type, confidence)
    SELECT v_yacht_id, e.id, alias.val, 'manual', 1.0
    FROM equipment e
    CROSS JOIN (VALUES
        ('stern thruster'),
        ('ST'),
        ('aft thruster')
    ) AS alias(val)
    WHERE e.yacht_id = v_yacht_id
      AND (
          LOWER(e.name) LIKE '%stern%thruster%'
          OR LOWER(e.name) LIKE '%aft%thruster%'
      )
    ON CONFLICT (yacht_id, LOWER(alias)) DO NOTHING;

    -- ========================================================================
    -- MANUFACTURER-BASED ALIASES
    -- Only created for equipment that actually has that manufacturer
    -- NO ASSUMPTIONS - checks actual manufacturer field
    -- ========================================================================

    -- Caterpillar (only if yacht has CAT equipment)
    INSERT INTO equipment_aliases (yacht_id, equipment_id, alias, alias_type, confidence)
    SELECT v_yacht_id, e.id, alias.val, 'manual', 1.0
    FROM equipment e
    CROSS JOIN (VALUES
        ('CAT'),
        ('Cat'),
        ('Caterpillar')
    ) AS alias(val)
    WHERE e.yacht_id = v_yacht_id
      AND LOWER(e.manufacturer) LIKE '%caterpillar%'
    ON CONFLICT (yacht_id, LOWER(alias)) DO NOTHING;

    -- MTU (only if yacht has MTU equipment)
    INSERT INTO equipment_aliases (yacht_id, equipment_id, alias, alias_type, confidence)
    SELECT v_yacht_id, e.id, alias.val, 'manual', 1.0
    FROM equipment e
    CROSS JOIN (VALUES
        ('MTU'),
        ('mtu engine')
    ) AS alias(val)
    WHERE e.yacht_id = v_yacht_id
      AND LOWER(e.manufacturer) LIKE '%mtu%'
    ON CONFLICT (yacht_id, LOWER(alias)) DO NOTHING;

    -- ========================================================================
    -- COUNT AND REPORT
    -- ========================================================================

    SELECT COUNT(*) INTO v_alias_count
    FROM equipment_aliases
    WHERE yacht_id = v_yacht_id;

    RAISE NOTICE '=== EQUIPMENT ALIAS SEEDING COMPLETE ===';
    RAISE NOTICE 'Total aliases for yacht: %', v_alias_count;
END $$;

-- Show what was created
SELECT
    e.name AS equipment_name,
    e.manufacturer,
    e.system_type,
    COUNT(ea.id) AS alias_count,
    STRING_AGG(ea.alias, ', ' ORDER BY ea.alias) AS aliases
FROM equipment e
LEFT JOIN equipment_aliases ea ON e.id = ea.equipment_id
WHERE e.yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'  -- CHANGE THIS
GROUP BY e.id, e.name, e.manufacturer, e.system_type
HAVING COUNT(ea.id) > 0
ORDER BY COUNT(ea.id) DESC;
