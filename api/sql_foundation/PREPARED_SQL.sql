-- QUERY PLANNER: Prepared SQL with Variants
-- ==========================================
-- Shows: OR within variants, AND across entities

======================================================================
-- TEST: Single entity - Generator
-- Entities: [('EQUIPMENT_NAME', 'Generator 1')]
-- Tiers: [(1, ['pms_equipment', 'graph_nodes'])]
-- SQL count: 2
======================================================================

-- Tier 1 Wave 0: 2 tables
(SELECT 'pms_equipment' AS _source, id, name, code, manufacturer, serial_number
FROM pms_equipment
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND name = 'GENERATOR 1'
LIMIT 20)
UNION ALL
(SELECT 'graph_nodes' AS _source, id, label, normalized_label, node_type, properties
FROM graph_nodes
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND label = 'GENERATOR 1'
LIMIT 20)
LIMIT 50;

-- Tier 1 Wave 1: 2 tables
(SELECT 'pms_equipment' AS _source, id, name, code, manufacturer, serial_number
FROM pms_equipment
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND (name ILIKE 'Generator 1' OR name ILIKE '%Generator 1%')
LIMIT 20)
UNION ALL
(SELECT 'graph_nodes' AS _source, id, label, normalized_label, node_type, properties
FROM graph_nodes
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND (label ILIKE 'Generator 1' OR label ILIKE '%Generator 1%')
LIMIT 20)
LIMIT 50;

======================================================================
-- TEST: Multi-entity - Part + Manufacturer
-- Entities: [('PART_NAME', 'fuel filter'), ('MANUFACTURER', 'MTU')]
-- Tiers: [(1, ['pms_parts']), (2, ['pms_suppliers'])]
-- SQL count: 2
======================================================================

-- Tier 1 Wave 1: 1 tables
(SELECT 'pms_parts' AS _source, id, part_number, name, manufacturer, category
FROM pms_parts
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND (name ILIKE 'fuel filter' OR name ILIKE '%fuel filter%') AND (manufacturer ILIKE 'MTU' OR manufacturer ILIKE '%MTU%')
LIMIT 20)
LIMIT 50;

-- Tier 2 Wave 1: 1 tables
(SELECT 'pms_suppliers' AS _source, id, name, contact_name, email, phone
FROM pms_suppliers
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND (name ILIKE 'MTU' OR name ILIKE '%MTU%')
LIMIT 20)
LIMIT 50;

======================================================================
-- TEST: Fault + Symptom
-- Entities: [('FAULT_CODE', 'E047'), ('SYMPTOM', 'overheating')]
-- Tiers: [(1, ['pms_faults', 'search_fault_code_catalog', 'symptom_aliases'])]
-- SQL count: 2
======================================================================

-- Tier 1 Wave 0: 3 tables
(SELECT 'pms_faults' AS _source, id, fault_code, title, severity, description
FROM pms_faults
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND fault_code = 'E047'
LIMIT 20)
UNION ALL
(SELECT 'search_fault_code_catalog' AS _source, id, code, name, severity, symptoms
FROM search_fault_code_catalog
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND code = 'E047'
LIMIT 20)
UNION ALL
(SELECT 'symptom_aliases' AS _source, id, alias, symptom_code
FROM symptom_aliases
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND symptom_code = 'OVERHEATING'
LIMIT 20)
LIMIT 50;

-- Tier 1 Wave 1: 3 tables
(SELECT 'pms_faults' AS _source, id, fault_code, title, severity, description
FROM pms_faults
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND (fault_code ILIKE 'E047' OR fault_code ILIKE '%E047%') AND (title ILIKE 'overheating' OR title ILIKE '%overheating%')
LIMIT 20)
UNION ALL
(SELECT 'search_fault_code_catalog' AS _source, id, code, name, severity, symptoms
FROM search_fault_code_catalog
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND (code ILIKE 'E047' OR code ILIKE '%E047%') AND (name ILIKE 'E047' OR name ILIKE '%E047%')
LIMIT 20)
UNION ALL
(SELECT 'symptom_aliases' AS _source, id, alias, symptom_code
FROM symptom_aliases
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND (alias ILIKE '85fe1119-b04c-41ac-80f1-829d23322598'0 OR alias ILIKE '85fe1119-b04c-41ac-80f1-829d23322598'1)
LIMIT 20)
LIMIT 50;
