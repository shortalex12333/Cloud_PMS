-- SQL FOUNDATION: ACTUAL QUERIES GENERATED
-- ==========================================
-- This is what gets executed for each search

======================================================================
-- ENTITY: EQUIPMENT_NAME = 'Generator'
======================================================================

-- WAVE 0

-- Query 1: pms_equipment.name.EXACT
SELECT id, name, code, manufacturer, serial_number, system_type, location
FROM pms_equipment
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND name = 'GENERATOR'
LIMIT 50;

-- Query 2: graph_nodes.label.EXACT
SELECT id, label, normalized_label, node_type, properties
FROM graph_nodes
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND label = 'GENERATOR'
LIMIT 50;

-- WAVE 1

-- Query 3: pms_equipment.name.ILIKE
SELECT id, name, code, manufacturer, serial_number, system_type, location
FROM pms_equipment
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND name ILIKE '%Generator%'
LIMIT 50;

-- Query 4: graph_nodes.label.ILIKE
SELECT id, label, normalized_label, node_type, properties
FROM graph_nodes
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND label ILIKE '%Generator%'
LIMIT 50;

-- WAVE 2

-- Query 5: pms_equipment.name.TRIGRAM
SELECT id, name, code, manufacturer, serial_number, system_type, location, similarity(name, 'generator') AS sim_score
FROM pms_equipment
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND similarity(name, 'generator') >= $3
ORDER BY sim_score DESC
LIMIT 50;

-- Query 6: graph_nodes.label.TRIGRAM
SELECT id, label, normalized_label, node_type, properties, similarity(label, 'generator') AS sim_score
FROM graph_nodes
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND similarity(label, 'generator') >= $3
ORDER BY sim_score DESC
LIMIT 50;

-- TOTAL: 6 queries for EQUIPMENT_NAME


======================================================================
-- ENTITY: PART_NUMBER = 'ENG-0008-103'
======================================================================

-- WAVE 0

-- Query 1: pms_parts.part_number.EXACT
SELECT id, part_number, name, manufacturer, category, description
FROM pms_parts
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND part_number = 'ENG-0008-103'
LIMIT 50;

-- WAVE 1

-- Query 2: pms_parts.part_number.ILIKE
SELECT id, part_number, name, manufacturer, category, description
FROM pms_parts
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND part_number ILIKE '%ENG-0008-103%'
LIMIT 50;

-- TOTAL: 2 queries for PART_NUMBER


======================================================================
-- ENTITY: FAULT_CODE = 'E047'
======================================================================

-- WAVE 0

-- Query 1: pms_faults.fault_code.EXACT
SELECT id, fault_code, title, severity, description
FROM pms_faults
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND fault_code = 'E047'
LIMIT 50;

-- Query 2: search_fault_code_catalog.code.EXACT
SELECT id, code, name, severity, symptoms, causes
FROM search_fault_code_catalog
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND code = 'E047'
LIMIT 50;

-- WAVE 1

-- Query 3: pms_faults.fault_code.ILIKE
SELECT id, fault_code, title, severity, description
FROM pms_faults
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND fault_code ILIKE '%E047%'
LIMIT 50;

-- Query 4: search_fault_code_catalog.code.ILIKE
SELECT id, code, name, severity, symptoms, causes
FROM search_fault_code_catalog
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND code ILIKE '%E047%'
LIMIT 50;

-- Query 5: search_fault_code_catalog.name.ILIKE
SELECT id, code, name, severity, symptoms, causes
FROM search_fault_code_catalog
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND name ILIKE '%E047%'
LIMIT 50;

-- TOTAL: 5 queries for FAULT_CODE


======================================================================
-- ENTITY: SUPPLIER_NAME = 'Marine'
======================================================================

-- WAVE 1

-- Query 1: pms_suppliers.name.ILIKE
SELECT id, name, contact_name, email, phone
FROM pms_suppliers
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND name ILIKE '%Marine%'
LIMIT 50;

-- WAVE 2

-- Query 2: pms_suppliers.name.TRIGRAM
SELECT id, name, contact_name, email, phone, similarity(name, 'marine') AS sim_score
FROM pms_suppliers
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND similarity(name, 'marine') >= $3
ORDER BY sim_score DESC
LIMIT 50;

-- TOTAL: 2 queries for SUPPLIER_NAME

