-- BBWS: BIAS-BUCKETED WAVE SEARCH
-- ================================
-- Actual SQL that would be executed

======================================================================
-- ENTITY: EQUIPMENT_NAME = 'Generator'
-- Tiers: ["T1:['pms_equipment', 'graph_nodes']"]
-- Queries: 3
======================================================================

-- Tier 1 Wave 0
(SELECT 'pms_equipment' AS _source, id, name AS _match_col
FROM pms_equipment
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND name = 'GENERATOR'
LIMIT 20)
UNION ALL
(SELECT 'graph_nodes' AS _source, id, label AS _match_col
FROM graph_nodes
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND label = 'GENERATOR'
LIMIT 20)
LIMIT 50;

-- Tier 1 Wave 1
(SELECT 'pms_equipment' AS _source, id, name AS _match_col
FROM pms_equipment
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND name ILIKE '%Generator%'
LIMIT 20)
UNION ALL
(SELECT 'graph_nodes' AS _source, id, label AS _match_col
FROM graph_nodes
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND label ILIKE '%Generator%'
LIMIT 20)
LIMIT 50;

-- Tier 1 Wave 2
(SELECT 'pms_equipment' AS _source, id, name AS _match_col
FROM pms_equipment
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND similarity(name, 'generator') >= 0.3
LIMIT 20)
UNION ALL
(SELECT 'graph_nodes' AS _source, id, label AS _match_col
FROM graph_nodes
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND similarity(label, 'generator') >= 0.3
LIMIT 20)
LIMIT 50;

======================================================================
-- ENTITY: PART_NUMBER = 'ENG-0008-103'
-- Tiers: ["T1:['pms_parts']"]
-- Queries: 2
======================================================================

-- Tier 1 Wave 0
(SELECT 'pms_parts' AS _source, id, part_number AS _match_col
FROM pms_parts
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND part_number = 'ENG-0008-103'
LIMIT 20)
LIMIT 50;

-- Tier 1 Wave 1
(SELECT 'pms_parts' AS _source, id, part_number AS _match_col
FROM pms_parts
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND part_number ILIKE '%ENG-0008-103%'
LIMIT 20)
LIMIT 50;

======================================================================
-- ENTITY: FAULT_CODE = 'E047'
-- Tiers: ["T1:['pms_faults', 'search_fault_code_catalog']"]
-- Queries: 2
======================================================================

-- Tier 1 Wave 0
(SELECT 'pms_faults' AS _source, id, fault_code AS _match_col
FROM pms_faults
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND fault_code = 'E047'
LIMIT 20)
UNION ALL
(SELECT 'search_fault_code_catalog' AS _source, id, name AS _match_col
FROM search_fault_code_catalog
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND code = 'E047'
LIMIT 20)
LIMIT 50;

-- Tier 1 Wave 1
(SELECT 'pms_faults' AS _source, id, fault_code AS _match_col
FROM pms_faults
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND fault_code ILIKE '%E047%'
LIMIT 20)
UNION ALL
(SELECT 'search_fault_code_catalog' AS _source, id, name AS _match_col
FROM search_fault_code_catalog
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND name ILIKE '%E047%'
LIMIT 20)
LIMIT 50;

======================================================================
-- ENTITY: SUPPLIER_NAME = 'Marine'
-- Tiers: ["T1:['pms_suppliers']"]
-- Queries: 2
======================================================================

-- Tier 1 Wave 1
(SELECT 'pms_suppliers' AS _source, id, name AS _match_col
FROM pms_suppliers
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND name ILIKE '%Marine%'
LIMIT 20)
LIMIT 50;

-- Tier 1 Wave 2
(SELECT 'pms_suppliers' AS _source, id, name AS _match_col
FROM pms_suppliers
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND similarity(name, 'marine') >= 0.3
LIMIT 20)
LIMIT 50;

======================================================================
-- ENTITY: SYMPTOM = 'shaking'
-- Tiers: ["T1:['pms_faults', 'symptom_aliases']"]
-- Queries: 3
======================================================================

-- Tier 1 Wave 0
(SELECT 'symptom_aliases' AS _source, id, symptom_code AS _match_col
FROM symptom_aliases
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND symptom_code = 'SHAKING'
LIMIT 20)
LIMIT 50;

-- Tier 1 Wave 1
(SELECT 'pms_faults' AS _source, id, title AS _match_col
FROM pms_faults
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND title ILIKE '%shaking%'
LIMIT 20)
UNION ALL
(SELECT 'symptom_aliases' AS _source, id, symptom_code AS _match_col
FROM symptom_aliases
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND alias ILIKE '%shaking%'
LIMIT 20)
LIMIT 50;

-- Tier 1 Wave 2
(SELECT 'pms_faults' AS _source, id, title AS _match_col
FROM pms_faults
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND similarity(title, 'shaking') >= 0.3
LIMIT 20)
UNION ALL
(SELECT 'symptom_aliases' AS _source, id, symptom_code AS _match_col
FROM symptom_aliases
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND similarity(alias, 'shaking') >= 0.3
LIMIT 20)
LIMIT 50;
