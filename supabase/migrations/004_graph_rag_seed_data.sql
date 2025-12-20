-- ============================================================================
-- Graph RAG Seed Data - Extended Maritime Ontology
-- ============================================================================
-- This migration adds comprehensive seed data for:
-- 1. Extended symptom catalog (maritime-specific)
-- 2. Common equipment aliases
-- 3. Standard fault codes
-- ============================================================================

-- ============================================================================
-- EXTENDED SYMPTOM CATALOG
-- ============================================================================

-- Additional maritime-specific symptoms
INSERT INTO symptom_catalog (symptom_code, canonical_name, category, equipment_class, description)
VALUES
    -- Fluid Systems
    ('LEAK_WATER', 'Water Leak', 'fluid', ARRAY['plumbing', 'hvac', 'hull'], 'Water leaking from system or component'),
    ('LEAK_HYDRAULIC', 'Hydraulic Fluid Leak', 'fluid', ARRAY['hydraulic', 'steering', 'stabilizer'], 'Hydraulic fluid leaking from system'),
    ('CONTAMINATION', 'Fluid Contamination', 'fluid', ARRAY['engine', 'hydraulic', 'fuel'], 'Foreign material in fluid system'),
    ('AIR_IN_SYSTEM', 'Air in System', 'fluid', ARRAY['fuel', 'hydraulic', 'cooling'], 'Air pockets causing system issues'),

    -- Electrical
    ('SHORT_CIRCUIT', 'Short Circuit', 'electrical', ARRAY['electrical', 'navigation', 'communication'], 'Electrical short detected'),
    ('GROUND_FAULT', 'Ground Fault', 'electrical', ARRAY['electrical', 'generator'], 'Ground fault in electrical system'),
    ('VOLTAGE_DROP', 'Voltage Drop', 'electrical', ARRAY['electrical', 'battery'], 'Voltage below normal operating range'),
    ('VOLTAGE_HIGH', 'High Voltage', 'electrical', ARRAY['electrical', 'generator'], 'Voltage above normal operating range'),
    ('BATTERY_LOW', 'Low Battery', 'electrical', ARRAY['battery', 'electrical'], 'Battery charge critically low'),
    ('BREAKER_TRIP', 'Breaker Trip', 'electrical', ARRAY['electrical', 'generator'], 'Circuit breaker tripped'),

    -- Mechanical
    ('MISALIGNMENT', 'Misalignment', 'mechanical', ARRAY['propulsion', 'pump', 'generator'], 'Shaft or coupling misalignment'),
    ('BEARING_WEAR', 'Bearing Wear', 'mechanical', ARRAY['engine', 'pump', 'winch'], 'Bearing showing signs of wear'),
    ('SEAL_FAILURE', 'Seal Failure', 'mechanical', ARRAY['engine', 'pump', 'hydraulic'], 'Seal damaged or failing'),
    ('BELT_WEAR', 'Belt Wear', 'mechanical', ARRAY['engine', 'generator', 'hvac'], 'Drive belt worn or damaged'),
    ('CHAIN_WEAR', 'Chain Wear', 'mechanical', ARRAY['anchor', 'steering'], 'Chain showing wear or stretch'),

    -- Performance
    ('LOSS_OF_POWER', 'Power Loss', 'performance', ARRAY['engine', 'generator', 'thruster'], 'Reduced power output'),
    ('SPEED_FLUCTUATION', 'Speed Fluctuation', 'performance', ARRAY['engine', 'generator', 'pump'], 'Inconsistent speed or RPM'),
    ('EFFICIENCY_DROP', 'Efficiency Drop', 'performance', ARRAY['engine', 'hvac', 'watermaker'], 'Reduced operational efficiency'),
    ('RESPONSE_SLOW', 'Slow Response', 'performance', ARRAY['steering', 'thruster', 'hydraulic'], 'Delayed response to commands'),

    -- Hull & Structural
    ('CAVITATION', 'Cavitation', 'structural', ARRAY['propeller', 'pump'], 'Cavitation damage detected'),
    ('FOULING', 'Biofouling', 'structural', ARRAY['hull', 'propeller', 'sea chest'], 'Marine growth on surfaces'),
    ('DELAMINATION', 'Delamination', 'structural', ARRAY['hull', 'deck'], 'Layer separation in composite'),
    ('OSMOSIS', 'Osmotic Blistering', 'structural', ARRAY['hull'], 'Osmotic blisters in hull'),

    -- Navigation & Safety
    ('GPS_LOSS', 'GPS Signal Loss', 'navigation', ARRAY['navigation', 'gps'], 'GPS signal lost or degraded'),
    ('RADAR_INTERFERENCE', 'Radar Interference', 'navigation', ARRAY['radar', 'navigation'], 'Radar showing interference'),
    ('ALARM_FALSE', 'False Alarm', 'safety', ARRAY['safety', 'fire', 'bilge'], 'System triggering false alarms'),
    ('SENSOR_FAULT', 'Sensor Fault', 'instrumentation', ARRAY['engine', 'navigation', 'safety'], 'Sensor reading incorrectly'),

    -- HVAC Specific
    ('REFRIGERANT_LOW', 'Low Refrigerant', 'hvac', ARRAY['hvac', 'refrigeration'], 'Refrigerant level low'),
    ('FREEZE_UP', 'Evaporator Freeze', 'hvac', ARRAY['hvac', 'refrigeration'], 'Evaporator coil frozen'),
    ('POOR_COOLING', 'Poor Cooling', 'hvac', ARRAY['hvac'], 'Inadequate cooling output'),
    ('POOR_HEATING', 'Poor Heating', 'hvac', ARRAY['hvac', 'boiler'], 'Inadequate heating output'),

    -- Watermaker Specific
    ('HIGH_SALINITY', 'High Salinity', 'watermaker', ARRAY['watermaker'], 'Product water salinity too high'),
    ('MEMBRANE_FOULING', 'Membrane Fouling', 'watermaker', ARRAY['watermaker'], 'RO membrane fouled'),
    ('LOW_PRODUCTION', 'Low Production', 'watermaker', ARRAY['watermaker'], 'Below normal water production')
ON CONFLICT (symptom_code) DO NOTHING;

-- Extended symptom aliases
INSERT INTO symptom_aliases (symptom_code, alias_text)
VALUES
    -- Leak variations
    ('LEAK_WATER', 'water leak'),
    ('LEAK_WATER', 'leaking water'),
    ('LEAK_WATER', 'water dripping'),
    ('LEAK_WATER', 'seawater ingress'),
    ('LEAK_HYDRAULIC', 'hydraulic leak'),
    ('LEAK_HYDRAULIC', 'leaking hydraulic'),
    ('LEAK_HYDRAULIC', 'hydraulic oil leak'),

    -- Electrical variations
    ('SHORT_CIRCUIT', 'short'),
    ('SHORT_CIRCUIT', 'shorted'),
    ('SHORT_CIRCUIT', 'electrical short'),
    ('GROUND_FAULT', 'ground fault'),
    ('GROUND_FAULT', 'earth fault'),
    ('GROUND_FAULT', 'earth leakage'),
    ('VOLTAGE_DROP', 'voltage low'),
    ('VOLTAGE_DROP', 'low voltage'),
    ('VOLTAGE_DROP', 'undervoltage'),
    ('BATTERY_LOW', 'battery dead'),
    ('BATTERY_LOW', 'battery flat'),
    ('BATTERY_LOW', 'low battery'),
    ('BREAKER_TRIP', 'tripped breaker'),
    ('BREAKER_TRIP', 'breaker tripped'),
    ('BREAKER_TRIP', 'breaker keeps tripping'),

    -- Mechanical variations
    ('MISALIGNMENT', 'out of alignment'),
    ('MISALIGNMENT', 'shaft misaligned'),
    ('BEARING_WEAR', 'bad bearing'),
    ('BEARING_WEAR', 'worn bearing'),
    ('BEARING_WEAR', 'bearing noise'),
    ('SEAL_FAILURE', 'seal leak'),
    ('SEAL_FAILURE', 'blown seal'),
    ('SEAL_FAILURE', 'seal worn'),
    ('BELT_WEAR', 'belt worn'),
    ('BELT_WEAR', 'belt slipping'),
    ('BELT_WEAR', 'belt cracked'),

    -- Performance variations
    ('LOSS_OF_POWER', 'no power'),
    ('LOSS_OF_POWER', 'power loss'),
    ('LOSS_OF_POWER', 'lost power'),
    ('LOSS_OF_POWER', 'underpowered'),
    ('SPEED_FLUCTUATION', 'speed hunting'),
    ('SPEED_FLUCTUATION', 'surging'),
    ('SPEED_FLUCTUATION', 'rpm fluctuating'),
    ('RESPONSE_SLOW', 'sluggish'),
    ('RESPONSE_SLOW', 'delayed response'),

    -- Hull variations
    ('FOULING', 'marine growth'),
    ('FOULING', 'barnacles'),
    ('FOULING', 'growth on hull'),
    ('CAVITATION', 'prop cavitation'),
    ('CAVITATION', 'cavitating'),

    -- HVAC variations
    ('REFRIGERANT_LOW', 'needs gas'),
    ('REFRIGERANT_LOW', 'low on refrigerant'),
    ('REFRIGERANT_LOW', 'needs freon'),
    ('POOR_COOLING', 'not cooling'),
    ('POOR_COOLING', 'ac not working'),
    ('POOR_COOLING', 'air con weak'),
    ('FREEZE_UP', 'iced up'),
    ('FREEZE_UP', 'frozen coil'),

    -- Watermaker variations
    ('HIGH_SALINITY', 'salty water'),
    ('HIGH_SALINITY', 'water salty'),
    ('HIGH_SALINITY', 'bad water quality'),
    ('MEMBRANE_FOULING', 'membrane dirty'),
    ('MEMBRANE_FOULING', 'membrane blocked'),
    ('LOW_PRODUCTION', 'low output'),
    ('LOW_PRODUCTION', 'making less water'),

    -- Existing symptom additional aliases
    ('OVERHEAT', 'getting hot'),
    ('OVERHEAT', 'temperature alarm'),
    ('OVERHEAT', 'cooling problem'),
    ('VIBRATION', 'rough running'),
    ('VIBRATION', 'out of balance'),
    ('NOISE', 'rattling'),
    ('NOISE', 'banging'),
    ('NOISE', 'clunking'),
    ('NOISE', 'humming'),
    ('SMOKE', 'exhaust smoke'),
    ('SMOKE', 'burning smell'),
    ('NO_START', 'dead'),
    ('NO_START', 'cranks but wont start'),
    ('NO_START', 'no crank'),
    ('STALLING', 'dies'),
    ('STALLING', 'hunting'),
    ('LEAK_OIL', 'dripping oil'),
    ('LEAK_OIL', 'oil on deck'),
    ('LEAK_FUEL', 'smell of diesel'),
    ('LEAK_FUEL', 'fuel smell')
ON CONFLICT (symptom_code, alias_text_lower) DO NOTHING;

-- ============================================================================
-- STANDARD EQUIPMENT NAMES (Template for yacht-specific population)
-- ============================================================================
-- Note: Equipment is yacht-specific, but we provide SQL templates
-- that can be customized per yacht during onboarding.

-- Sample equipment template (to be run per yacht with specific yacht_id)
-- This is commented out as it needs yacht_id parameter:
/*
INSERT INTO equipment (yacht_id, canonical_name, display_name, system_type, oem, model)
VALUES
    -- Propulsion
    ('YOUR_YACHT_ID', 'port_main_engine', 'Port Main Engine', 'PROPULSION', 'MTU', '16V 4000 M93L'),
    ('YOUR_YACHT_ID', 'stbd_main_engine', 'Starboard Main Engine', 'PROPULSION', 'MTU', '16V 4000 M93L'),
    ('YOUR_YACHT_ID', 'port_gearbox', 'Port Gearbox', 'PROPULSION', 'ZF', 'ZF 9050'),
    ('YOUR_YACHT_ID', 'stbd_gearbox', 'Starboard Gearbox', 'PROPULSION', 'ZF', 'ZF 9050'),

    -- Generators
    ('YOUR_YACHT_ID', 'generator_1', 'Generator 1', 'ELECTRICAL', 'Caterpillar', 'C18'),
    ('YOUR_YACHT_ID', 'generator_2', 'Generator 2', 'ELECTRICAL', 'Caterpillar', 'C18'),
    ('YOUR_YACHT_ID', 'generator_3', 'Generator 3', 'ELECTRICAL', 'Caterpillar', 'C18'),

    -- HVAC
    ('YOUR_YACHT_ID', 'hvac_main', 'Main HVAC System', 'HVAC', 'Marine Air', 'VDT'),
    ('YOUR_YACHT_ID', 'chiller_1', 'Chiller 1', 'HVAC', 'Carrier', '30XA'),
    ('YOUR_YACHT_ID', 'chiller_2', 'Chiller 2', 'HVAC', 'Carrier', '30XA'),

    -- Watermaker
    ('YOUR_YACHT_ID', 'watermaker_1', 'Watermaker 1', 'PLUMBING', 'Sea Recovery', 'Aqua Whisper'),
    ('YOUR_YACHT_ID', 'watermaker_2', 'Watermaker 2', 'PLUMBING', 'Sea Recovery', 'Aqua Whisper'),

    -- Thrusters
    ('YOUR_YACHT_ID', 'bow_thruster', 'Bow Thruster', 'PROPULSION', 'Veth', 'VZ-500'),
    ('YOUR_YACHT_ID', 'stern_thruster', 'Stern Thruster', 'PROPULSION', 'Veth', 'VZ-400'),

    -- Stabilizers
    ('YOUR_YACHT_ID', 'stabilizer_port', 'Port Stabilizer', 'HYDRAULIC', 'Quantum', 'MAG'),
    ('YOUR_YACHT_ID', 'stabilizer_stbd', 'Starboard Stabilizer', 'HYDRAULIC', 'Quantum', 'MAG')
;
*/

-- ============================================================================
-- COMMON EQUIPMENT ALIAS PATTERNS
-- ============================================================================
-- These are common aliases that apply across most yachts.
-- Run after equipment is populated with actual equipment IDs.

-- Template function to add standard aliases for equipment
CREATE OR REPLACE FUNCTION add_standard_equipment_aliases(
    p_yacht_id UUID,
    p_equipment_id UUID,
    p_canonical_name TEXT,
    p_display_name TEXT,
    p_oem TEXT DEFAULT NULL,
    p_model TEXT DEFAULT NULL
) RETURNS VOID AS $$
DECLARE
    v_aliases TEXT[];
BEGIN
    -- Build alias array based on canonical name patterns
    v_aliases := ARRAY[p_canonical_name, p_display_name];

    -- Add OEM variations if provided
    IF p_oem IS NOT NULL THEN
        v_aliases := v_aliases || p_oem;
        IF p_model IS NOT NULL THEN
            v_aliases := v_aliases || (p_oem || ' ' || p_model);
        END IF;
    END IF;

    -- Add common abbreviations based on canonical name
    IF p_canonical_name LIKE '%main_engine%' THEN
        v_aliases := v_aliases || ARRAY['ME', 'Main Engine', 'Main'];
        IF p_canonical_name LIKE 'port%' THEN
            v_aliases := v_aliases || ARRAY['Port ME', 'Port Main', 'P/S ME', 'PME'];
        ELSIF p_canonical_name LIKE 'stbd%' OR p_canonical_name LIKE 'starboard%' THEN
            v_aliases := v_aliases || ARRAY['Stbd ME', 'Starboard Main', 'S/B ME', 'SME'];
        END IF;
    END IF;

    IF p_canonical_name LIKE '%generator%' THEN
        v_aliases := v_aliases || ARRAY['Gen', 'Genset'];
        IF p_canonical_name LIKE '%1%' THEN
            v_aliases := v_aliases || ARRAY['Gen 1', 'Generator 1', 'Gen #1', 'G1'];
        ELSIF p_canonical_name LIKE '%2%' THEN
            v_aliases := v_aliases || ARRAY['Gen 2', 'Generator 2', 'Gen #2', 'G2'];
        ELSIF p_canonical_name LIKE '%3%' THEN
            v_aliases := v_aliases || ARRAY['Gen 3', 'Generator 3', 'Gen #3', 'G3'];
        END IF;
    END IF;

    IF p_canonical_name LIKE '%gearbox%' THEN
        v_aliases := v_aliases || ARRAY['Gearbox', 'Transmission', 'GB'];
        IF p_canonical_name LIKE 'port%' THEN
            v_aliases := v_aliases || ARRAY['Port Gearbox', 'Port GB', 'Port Trans'];
        ELSIF p_canonical_name LIKE 'stbd%' OR p_canonical_name LIKE 'starboard%' THEN
            v_aliases := v_aliases || ARRAY['Stbd Gearbox', 'Starboard GB', 'Stbd Trans'];
        END IF;
    END IF;

    IF p_canonical_name LIKE '%watermaker%' THEN
        v_aliases := v_aliases || ARRAY['WM', 'Water Maker', 'RO System', 'Desalinator'];
    END IF;

    IF p_canonical_name LIKE '%bow_thruster%' THEN
        v_aliases := v_aliases || ARRAY['Bow Thruster', 'BT', 'Fwd Thruster', 'Forward Thruster'];
    END IF;

    IF p_canonical_name LIKE '%stern_thruster%' THEN
        v_aliases := v_aliases || ARRAY['Stern Thruster', 'ST', 'Aft Thruster'];
    END IF;

    IF p_canonical_name LIKE '%stabilizer%' THEN
        v_aliases := v_aliases || ARRAY['Stabilizer', 'Stab', 'Fin'];
        IF p_canonical_name LIKE 'port%' THEN
            v_aliases := v_aliases || ARRAY['Port Stabilizer', 'Port Stab', 'Port Fin'];
        ELSIF p_canonical_name LIKE 'stbd%' OR p_canonical_name LIKE 'starboard%' THEN
            v_aliases := v_aliases || ARRAY['Stbd Stabilizer', 'Starboard Stab', 'Stbd Fin'];
        END IF;
    END IF;

    IF p_canonical_name LIKE '%chiller%' THEN
        v_aliases := v_aliases || ARRAY['Chiller', 'AC Chiller'];
    END IF;

    IF p_canonical_name LIKE '%hvac%' THEN
        v_aliases := v_aliases || ARRAY['HVAC', 'Air Conditioning', 'AC', 'A/C'];
    END IF;

    -- Insert all aliases
    INSERT INTO entity_aliases (yacht_id, entity_type, canonical_id, alias_text, source)
    SELECT p_yacht_id, 'equipment'::entity_type, p_equipment_id, unnest(v_aliases), 'auto'
    ON CONFLICT (yacht_id, entity_type, alias_text_lower) DO NOTHING;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- STANDARD FAULT CODES
-- ============================================================================
-- Common fault codes across yacht equipment

-- Template for yacht-specific fault codes
/*
INSERT INTO faults (yacht_id, fault_code, canonical_name, severity, category, description)
VALUES
    -- Engine faults
    ('YOUR_YACHT_ID', 'E001', 'High Coolant Temperature', 'high', 'engine', 'Engine coolant temperature exceeded threshold'),
    ('YOUR_YACHT_ID', 'E002', 'Low Oil Pressure', 'critical', 'engine', 'Engine oil pressure below minimum'),
    ('YOUR_YACHT_ID', 'E003', 'High Exhaust Temperature', 'high', 'engine', 'Exhaust temperature exceeded threshold'),
    ('YOUR_YACHT_ID', 'E004', 'Overspeed', 'critical', 'engine', 'Engine RPM exceeded maximum'),
    ('YOUR_YACHT_ID', 'E005', 'Fuel Filter Blocked', 'medium', 'engine', 'Primary fuel filter differential pressure high'),

    -- Generator faults
    ('YOUR_YACHT_ID', 'G001', 'Generator Overload', 'high', 'electrical', 'Generator load exceeded capacity'),
    ('YOUR_YACHT_ID', 'G002', 'Frequency Out of Range', 'high', 'electrical', 'Generator frequency deviation'),
    ('YOUR_YACHT_ID', 'G003', 'Voltage Out of Range', 'high', 'electrical', 'Generator voltage deviation'),

    -- HVAC faults
    ('YOUR_YACHT_ID', 'H001', 'High Head Pressure', 'medium', 'hvac', 'Condenser pressure too high'),
    ('YOUR_YACHT_ID', 'H002', 'Low Suction Pressure', 'medium', 'hvac', 'Evaporator pressure too low'),
    ('YOUR_YACHT_ID', 'H003', 'Compressor Fault', 'high', 'hvac', 'Compressor protection tripped')
;
*/

-- ============================================================================
-- HELPER: Fuzzy symptom matching function
-- ============================================================================

-- Function for fuzzy symptom matching (handles typos, partial matches)
CREATE OR REPLACE FUNCTION match_symptom_fuzzy(
    p_input_text TEXT,
    p_min_similarity FLOAT DEFAULT 0.4
) RETURNS TABLE (
    symptom_code TEXT,
    canonical_name TEXT,
    similarity_score FLOAT,
    matched_alias TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        sc.symptom_code,
        sc.canonical_name,
        similarity(sa.alias_text_lower, LOWER(p_input_text)) AS similarity_score,
        sa.alias_text AS matched_alias
    FROM symptom_aliases sa
    JOIN symptom_catalog sc ON sa.symptom_code = sc.symptom_code
    WHERE similarity(sa.alias_text_lower, LOWER(p_input_text)) >= p_min_similarity
    ORDER BY similarity_score DESC
    LIMIT 5;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- COMMENT BLOCKS
-- ============================================================================

COMMENT ON FUNCTION add_standard_equipment_aliases IS 'Automatically generates common equipment aliases based on canonical name patterns';
COMMENT ON FUNCTION match_symptom_fuzzy IS 'Fuzzy matches input text against symptom aliases using trigram similarity';

-- ============================================================================
-- QUERY HELPER VIEWS
-- ============================================================================

-- View: Equipment with all aliases for quick lookup
CREATE OR REPLACE VIEW v_equipment_aliases AS
SELECT
    e.id,
    e.yacht_id,
    e.canonical_name,
    e.display_name,
    e.oem,
    e.model,
    e.system_type,
    e.location,
    ARRAY_AGG(DISTINCT ea.alias_text) FILTER (WHERE ea.alias_text IS NOT NULL) AS aliases
FROM equipment e
LEFT JOIN entity_aliases ea ON ea.canonical_id = e.id AND ea.entity_type = 'equipment'
GROUP BY e.id, e.yacht_id, e.canonical_name, e.display_name, e.oem, e.model, e.system_type, e.location;

-- View: Parts with all aliases
CREATE OR REPLACE VIEW v_parts_aliases AS
SELECT
    p.id,
    p.yacht_id,
    p.canonical_name,
    p.display_name,
    p.manufacturer,
    p.part_number,
    p.oem_part_number,
    ARRAY_AGG(DISTINCT ea.alias_text) FILTER (WHERE ea.alias_text IS NOT NULL) AS aliases
FROM parts p
LEFT JOIN entity_aliases ea ON ea.canonical_id = p.id AND ea.entity_type = 'part'
GROUP BY p.id, p.yacht_id, p.canonical_name, p.display_name, p.manufacturer, p.part_number, p.oem_part_number;

-- View: Symptom quick lookup with all aliases
CREATE OR REPLACE VIEW v_symptom_lookup AS
SELECT
    sc.symptom_code,
    sc.canonical_name,
    sc.category,
    sc.equipment_class,
    sc.description,
    ARRAY_AGG(DISTINCT sa.alias_text) FILTER (WHERE sa.alias_text IS NOT NULL) AS aliases
FROM symptom_catalog sc
LEFT JOIN symptom_aliases sa ON sa.symptom_code = sc.symptom_code
GROUP BY sc.symptom_code, sc.canonical_name, sc.category, sc.equipment_class, sc.description;

-- View: Graph statistics per yacht
CREATE OR REPLACE VIEW v_graph_stats AS
SELECT
    gn.yacht_id,
    COUNT(DISTINCT gn.id) AS total_nodes,
    COUNT(DISTINCT ge.id) AS total_edges,
    COUNT(DISTINCT CASE WHEN gn.node_type = 'equipment' THEN gn.id END) AS equipment_nodes,
    COUNT(DISTINCT CASE WHEN gn.node_type = 'part' THEN gn.id END) AS part_nodes,
    COUNT(DISTINCT CASE WHEN gn.node_type = 'fault' THEN gn.id END) AS fault_nodes,
    COUNT(DISTINCT CASE WHEN gn.node_type = 'symptom' THEN gn.id END) AS symptom_nodes,
    COUNT(DISTINCT CASE WHEN gn.canonical_id IS NOT NULL THEN gn.id END) AS resolved_nodes,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN gn.canonical_id IS NOT NULL THEN gn.id END) / NULLIF(COUNT(DISTINCT gn.id), 0), 2) AS resolution_rate_pct
FROM graph_nodes gn
LEFT JOIN graph_edges ge ON ge.yacht_id = gn.yacht_id
GROUP BY gn.yacht_id;

-- View: Extraction status summary
CREATE OR REPLACE VIEW v_extraction_status AS
SELECT
    yacht_id,
    graph_extraction_status,
    COUNT(*) AS chunk_count,
    SUM(extracted_entity_count) AS total_entities,
    SUM(extracted_relationship_count) AS total_relationships,
    AVG(extracted_entity_count) AS avg_entities_per_chunk,
    AVG(extracted_relationship_count) AS avg_relationships_per_chunk
FROM document_chunks
GROUP BY yacht_id, graph_extraction_status;

-- ============================================================================
-- GRANT PERMISSIONS (for anon/authenticated roles)
-- ============================================================================

-- Views are read-only, safe to expose
GRANT SELECT ON v_equipment_aliases TO anon, authenticated;
GRANT SELECT ON v_parts_aliases TO anon, authenticated;
GRANT SELECT ON v_symptom_lookup TO anon, authenticated;
GRANT SELECT ON v_graph_stats TO anon, authenticated;
GRANT SELECT ON v_extraction_status TO anon, authenticated;
