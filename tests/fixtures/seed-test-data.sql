-- ============================================================================
-- TEST DATA SEEDING SCRIPT FOR E2E TESTS
-- ============================================================================
-- Yacht: 85fe1119-b04c-41ac-80f1-829d23322598 (TEST_YACHT_001)
-- Purpose: Seed parts, equipment, and other entities for E2E testing
-- ============================================================================

-- Ensure we're working with the correct yacht
\set yacht_id '85fe1119-b04c-41ac-80f1-829d23322598'

-- ============================================================================
-- 1. PARTS (Inventory Items)
-- ============================================================================

-- Fuel Filters (matching "fuel filter stock" query)
INSERT INTO parts (part_id, yacht_id, part_name, part_number, manufacturer, category, description, location, on_hand, min_stock, max_stock, unit_cost, unit, created_at, updated_at)
VALUES
  (gen_random_uuid(), :'yacht_id', 'Fuel Filter - Primary', 'FF-001', 'Mann-Filter', 'Filters', 'Primary fuel filter for main engine', 'Engine Room', 15, 5, 30, 45.99, 'EA', NOW(), NOW()),
  (gen_random_uuid(), :'yacht_id', 'Fuel Filter - Secondary', 'FF-002', 'Fleetguard', 'Filters', 'Secondary fuel filter for main engine', 'Engine Room', 12, 5, 25, 38.50, 'EA', NOW(), NOW()),
  (gen_random_uuid(), :'yacht_id', 'Fuel Water Separator Filter', 'FF-WS-003', 'Racor', 'Filters', 'Fuel water separator cartridge', 'Engine Room', 8, 3, 20, 125.00, 'EA', NOW(), NOW()),
  (gen_random_uuid(), :'yacht_id', 'Fuel Filter - Generator', 'FF-GEN-004', 'Caterpillar', 'Filters', 'Fuel filter for auxiliary generator', 'Generator Room', 6, 2, 15, 52.75, 'EA', NOW(), NOW()),
  (gen_random_uuid(), :'yacht_id', 'Fuel Pre-Filter Element', 'FF-PRE-005', 'Baldwin', 'Filters', 'Pre-filter element for fuel system', 'Engine Room', 10, 4, 20, 28.99, 'EA', NOW(), NOW()),
  (gen_random_uuid(), :'yacht_id', 'Fuel Filter Housing Gasket', 'FF-GSKT-006', 'OEM', 'Gaskets', 'O-ring gasket for fuel filter housing', 'Engine Room', 20, 10, 50, 3.25, 'EA', NOW(), NOW()),
  (gen_random_uuid(), :'yacht_id', 'Fuel Filter Wrench', 'FF-TOOL-007', 'Generic', 'Tools', 'Fuel filter removal wrench', 'Engine Room', 2, 1, 3, 18.50, 'EA', NOW(), NOW()),
  (gen_random_uuid(), :'yacht_id', 'Diesel Fuel Filter - High Flow', 'FF-HF-008', 'Donaldson', 'Filters', 'High flow fuel filter for diesel', 'Engine Room', 5, 2, 12, 89.99, 'EA', NOW(), NOW()),
  (gen_random_uuid(), :'yacht_id', 'Fuel Filter - Emergency Stock', 'FF-EMERG-009', 'Various', 'Filters', 'Emergency spare fuel filter', 'Emergency Locker', 3, 2, 8, 55.00, 'EA', NOW(), NOW()),
  (gen_random_uuid(), :'yacht_id', 'Fuel Filter Test Kit', 'FF-TEST-010', 'Test Equipment Inc', 'Testing', 'Fuel contamination test kit', 'Engine Room', 1, 1, 2, 145.00, 'KIT', NOW(), NOW())
ON CONFLICT (part_id) DO NOTHING;

-- Additional Parts (for search variety)
INSERT INTO parts (part_id, yacht_id, part_name, part_number, manufacturer, category, description, location, on_hand, min_stock, max_stock, unit_cost, unit, created_at, updated_at)
VALUES
  (gen_random_uuid(), :'yacht_id', 'Engine Oil Filter', 'OF-001', 'Mann-Filter', 'Filters', 'Oil filter for main engine', 'Engine Room', 8, 4, 20, 32.50, 'EA', NOW(), NOW()),
  (gen_random_uuid(), :'yacht_id', 'Air Filter Element', 'AF-001', 'Donaldson', 'Filters', 'Air filter for engine intake', 'Engine Room', 6, 3, 15, 68.75, 'EA', NOW(), NOW()),
  (gen_random_uuid(), :'yacht_id', 'Hydraulic Filter', 'HF-001', 'Parker', 'Filters', 'Hydraulic system filter', 'Hydraulic Room', 4, 2, 10, 95.00, 'EA', NOW(), NOW()),
  (gen_random_uuid(), :'yacht_id', 'Coolant Hose', 'CH-001', 'Gates', 'Hoses', 'Coolant hose for engine', 'Engine Room', 3, 1, 5, 45.00, 'EA', NOW(), NOW()),
  (gen_random_uuid(), :'yacht_id', 'V-Belt', 'VB-001', 'Goodyear', 'Belts', 'V-belt for alternator', 'Engine Room', 5, 2, 10, 25.50, 'EA', NOW(), NOW()),
  (gen_random_uuid(), :'yacht_id', 'Spark Plug', 'SP-001', 'NGK', 'Ignition', 'Spark plug for generator', 'Generator Room', 12, 8, 24, 8.75, 'EA', NOW(), NOW()),
  (gen_random_uuid(), :'yacht_id', 'Bearing - Shaft', 'BRG-001', 'SKF', 'Bearings', 'Shaft bearing for propulsion', 'Engine Room', 2, 1, 4, 285.00, 'EA', NOW(), NOW()),
  (gen_random_uuid(), :'yacht_id', 'Grease - Marine', 'GRS-001', 'Mobil', 'Lubricants', 'Marine grease cartridge', 'Engine Room', 10, 5, 20, 12.99, 'EA', NOW(), NOW()),
  (gen_random_uuid(), :'yacht_id', 'Zinc Anode', 'ZN-001', 'Marine Anodes', 'Anodes', 'Zinc anode for hull', 'Deck Locker', 8, 4, 15, 35.00, 'EA', NOW(), NOW()),
  (gen_random_uuid(), :'yacht_id', 'Impeller - Water Pump', 'IMP-001', 'Jabsco', 'Pumps', 'Impeller for seawater pump', 'Engine Room', 4, 2, 8, 78.50, 'EA', NOW(), NOW())
ON CONFLICT (part_id) DO NOTHING;

-- Parts with ZERO stock (for testing edge cases)
INSERT INTO parts (part_id, yacht_id, part_name, part_number, manufacturer, category, description, location, on_hand, min_stock, max_stock, unit_cost, unit, created_at, updated_at)
VALUES
  (gen_random_uuid(), :'yacht_id', 'Fuel Filter - Out of Stock', 'FF-OOS-001', 'Mann-Filter', 'Filters', 'Out of stock fuel filter', 'Engine Room', 0, 5, 30, 45.99, 'EA', NOW(), NOW()),
  (gen_random_uuid(), :'yacht_id', 'Emergency Fuel Filter - Low Stock', 'FF-LOW-002', 'Fleetguard', 'Filters', 'Low stock emergency filter', 'Emergency Locker', 1, 5, 25, 125.00, 'EA', NOW(), NOW())
ON CONFLICT (part_id) DO NOTHING;

-- ============================================================================
-- 2. EQUIPMENT (for equipment-related tests)
-- ============================================================================

INSERT INTO equipment (equipment_id, yacht_id, equipment_name, equipment_type, manufacturer, model, serial_number, location, installation_date, status, created_at, updated_at)
VALUES
  (gen_random_uuid(), :'yacht_id', 'Main Engine - Port', 'Engine', 'Caterpillar', 'C32 ACERT', 'CAT-PE-001', 'Engine Room', '2020-01-15', 'operational', NOW(), NOW()),
  (gen_random_uuid(), :'yacht_id', 'Main Engine - Starboard', 'Engine', 'Caterpillar', 'C32 ACERT', 'CAT-SE-001', 'Engine Room', '2020-01-15', 'operational', NOW(), NOW()),
  (gen_random_uuid(), :'yacht_id', 'Auxiliary Generator', 'Generator', 'Northern Lights', 'M1264', 'NL-GEN-001', 'Generator Room', '2020-02-10', 'operational', NOW(), NOW()),
  (gen_random_uuid(), :'yacht_id', 'Fuel Transfer Pump', 'Pump', 'Jabsco', 'FTP-100', 'JAB-FTP-001', 'Engine Room', '2020-03-05', 'operational', NOW(), NOW())
ON CONFLICT (equipment_id) DO NOTHING;

-- ============================================================================
-- 3. WORK ORDERS (for action button testing)
-- ============================================================================

INSERT INTO work_orders (work_order_id, yacht_id, work_order_number, title, description, status, priority, assigned_to, created_by, created_at, updated_at)
VALUES
  (gen_random_uuid(), :'yacht_id', 'WO-001', 'Replace Fuel Filters', 'Replace all fuel filters on main engines', 'pending', 'high', (SELECT user_id FROM user_accounts WHERE yacht_id = :'yacht_id' AND role = 'chief_engineer' LIMIT 1), (SELECT user_id FROM user_accounts WHERE yacht_id = :'yacht_id' AND role = 'chief_engineer' LIMIT 1), NOW(), NOW()),
  (gen_random_uuid(), :'yacht_id', 'WO-002', 'Fuel System Inspection', 'Inspect fuel system for contamination', 'in_progress', 'medium', (SELECT user_id FROM user_accounts WHERE yacht_id = :'yacht_id' AND role = 'chief_engineer' LIMIT 1), (SELECT user_id FROM user_accounts WHERE yacht_id = :'yacht_id' AND role = 'captain' LIMIT 1), NOW(), NOW())
ON CONFLICT (work_order_id) DO NOTHING;

-- ============================================================================
-- VALIDATION QUERIES
-- ============================================================================

-- Count parts
SELECT
  COUNT(*) AS total_parts,
  SUM(CASE WHEN part_name ILIKE '%fuel%' OR part_name ILIKE '%filter%' THEN 1 ELSE 0 END) AS fuel_filter_parts,
  SUM(CASE WHEN on_hand > 0 THEN 1 ELSE 0 END) AS parts_in_stock
FROM parts
WHERE yacht_id = :'yacht_id';

-- Show fuel filter parts
SELECT part_id, part_name, part_number, on_hand, location
FROM parts
WHERE yacht_id = :'yacht_id'
  AND (part_name ILIKE '%fuel%' OR part_name ILIKE '%filter%')
ORDER BY part_name
LIMIT 10;

-- ============================================================================
-- SUCCESS MESSAGE
-- ============================================================================

\echo '✅ Test data seeded successfully!'
\echo '✅ Run validation: tests/scripts/validate-local-setup.sh'
