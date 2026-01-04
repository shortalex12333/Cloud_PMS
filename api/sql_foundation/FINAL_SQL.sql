-- FINAL SQL GENERATION OUTPUT
-- ============================
-- Complete PREPARE → SQL pipeline
-- Key features:
--   OR within variants of same entity
--   AND across different entities
--   UNION ALL across tables in same tier+wave

======================================================================
-- QUERY: 'Generator 1'
-- ENTITIES: [('EQUIPMENT_NAME', 'Generator 1')]
-- Lane: GPT | Intent: search
-- SQL count: 2
======================================================================

-- Tier 1 EXACT: 2 tables
-- params[0] = yacht_id

(SELECT 'pms_equipment' AS _source, id, name, code, manufacturer, serial_number
FROM pms_equipment
WHERE yacht_id = $1
  AND name = $2
LIMIT 20)
UNION ALL
(SELECT 'graph_nodes' AS _source, id, label, normalized_label, node_type, properties
FROM graph_nodes
WHERE yacht_id = $1
  AND label = $3
LIMIT 20)
LIMIT 50;

-- Tier 1 ILIKE: 2 tables
-- params[0] = yacht_id

(SELECT 'pms_equipment' AS _source, id, name, code, manufacturer, serial_number
FROM pms_equipment
WHERE yacht_id = $1
  AND (name ILIKE $2 OR name ILIKE $3)
LIMIT 20)
UNION ALL
(SELECT 'graph_nodes' AS _source, id, label, normalized_label, node_type, properties
FROM graph_nodes
WHERE yacht_id = $1
  AND (label ILIKE $4 OR label ILIKE $5)
LIMIT 20)
LIMIT 50;

======================================================================
-- QUERY: 'fuel filter for MTU engine'
-- ENTITIES: [('PART_NAME', 'fuel filter'), ('MANUFACTURER', 'MTU')]
-- Lane: GPT | Intent: search
-- SQL count: 1
======================================================================

-- Tier 1 ILIKE: 3 tables
-- params[0] = yacht_id

(SELECT 'pms_parts' AS _source, id, part_number, name, manufacturer, category
FROM pms_parts
WHERE yacht_id = $1
  AND (name ILIKE $2 OR name ILIKE $3) AND (manufacturer ILIKE $4 OR manufacturer ILIKE $5)
LIMIT 20)
UNION ALL
(SELECT 'pms_equipment' AS _source, id, name, code, manufacturer, serial_number
FROM pms_equipment
WHERE yacht_id = $1
  AND (manufacturer ILIKE $6 OR manufacturer ILIKE $7)
LIMIT 20)
UNION ALL
(SELECT 'pms_suppliers' AS _source, id, name, contact_name, email, phone
FROM pms_suppliers
WHERE yacht_id = $1
  AND (name ILIKE $8 OR name ILIKE $9)
LIMIT 20)
LIMIT 50;

======================================================================
-- QUERY: 'fault E047 overheating'
-- ENTITIES: [('FAULT_CODE', 'E047'), ('SYMPTOM', 'overheating')]
-- Lane: NO_LLM | Intent: diagnose
-- SQL count: 2
======================================================================

-- Tier 1 EXACT: 3 tables
-- params[0] = yacht_id

(SELECT 'pms_faults' AS _source, id, fault_code, title, severity, description
FROM pms_faults
WHERE yacht_id = $1
  AND fault_code = $2
LIMIT 20)
UNION ALL
(SELECT 'search_fault_code_catalog' AS _source, id, code, name, severity, symptoms
FROM search_fault_code_catalog
WHERE yacht_id = $1
  AND code = $3
LIMIT 20)
UNION ALL
(SELECT 'symptom_aliases' AS _source, id, alias, symptom_code
FROM symptom_aliases
WHERE yacht_id = $1
  AND symptom_code = $4
LIMIT 20)
LIMIT 50;

-- Tier 1 ILIKE: 3 tables
-- params[0] = yacht_id

(SELECT 'pms_faults' AS _source, id, fault_code, title, severity, description
FROM pms_faults
WHERE yacht_id = $1
  AND (fault_code ILIKE $2 OR fault_code ILIKE $3) AND (title ILIKE $4 OR title ILIKE $5)
LIMIT 20)
UNION ALL
(SELECT 'search_fault_code_catalog' AS _source, id, code, name, severity, symptoms
FROM search_fault_code_catalog
WHERE yacht_id = $1
  AND (code ILIKE $6 OR code ILIKE $7) AND (name ILIKE $8 OR name ILIKE $9)
LIMIT 20)
UNION ALL
(SELECT 'symptom_aliases' AS _source, id, alias, symptom_code
FROM symptom_aliases
WHERE yacht_id = $1
  AND (alias ILIKE $10 OR alias ILIKE $11)
LIMIT 20)
LIMIT 50;

