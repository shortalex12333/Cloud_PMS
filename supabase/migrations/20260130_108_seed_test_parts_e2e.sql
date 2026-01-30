-- ============================================================================
-- E2E Test Data: Parts for Inventory Lens Testing
-- ============================================================================
-- Purpose: Add searchable test parts to production tenant for E2E tests
-- Yacht: MY Pandora (85fe1119-b04c-41ac-80f1-829d23322598)
-- ============================================================================

INSERT INTO public.pms_parts (
    id,
    yacht_id,
    name,
    part_number,
    description,
    category,
    quantity_on_hand,
    quantity_minimum,
    quantity_reorder,
    unit_of_measure,
    storage_location,
    unit_cost,
    currency,
    created_at,
    updated_at
) VALUES
-- Test Part 1: Engine Oil Filter (Consumable)
(
    '00000000-0000-4000-8000-000000000001',
    '85fe1119-b04c-41ac-80f1-829d23322598',
    'Engine Oil Filter',
    'TEST-PART-001',
    'Test oil filter for E2E testing - consumable',
    'Filters',
    25,
    5,
    10,
    'each',
    'Engine Room - Shelf A',
    45.00,
    'USD',
    NOW(),
    NOW()
),
-- Test Part 2: Hydraulic Pump Seal Kit (Low Stock)
(
    '00000000-0000-4000-8000-000000000002',
    '85fe1119-b04c-41ac-80f1-829d23322598',
    'Hydraulic Pump Seal Kit',
    'TEST-PART-002',
    'Test seal kit for E2E testing - low stock scenario',
    'Hydraulics',
    2,
    5,
    10,
    'kit',
    'Workshop - Cabinet B',
    125.50,
    'USD',
    NOW(),
    NOW()
),
-- Test Part 3: Spare Fuel Filter (Receivable)
(
    '00000000-0000-4000-8000-000000000003',
    '85fe1119-b04c-41ac-80f1-829d23322598',
    'Spare Fuel Filter',
    'TEST-PART-003',
    'Test fuel filter for E2E testing - receiving actions',
    'Filters',
    10,
    3,
    8,
    'each',
    'Engine Room - Shelf B',
    38.75,
    'USD',
    NOW(),
    NOW()
),
-- Test Part 4: Navigation Light Bulb (Transfer/Adjust)
(
    '00000000-0000-4000-8000-000000000004',
    '85fe1119-b04c-41ac-80f1-829d23322598',
    'Navigation Light Bulb',
    'TEST-PART-004',
    'Test bulb for E2E testing - transfer and adjust actions',
    'Electrical',
    15,
    10,
    20,
    'each',
    'Bridge - Storage Locker',
    12.00,
    'USD',
    NOW(),
    NOW()
),
-- Test Part 5: Stainless Steel Fasteners (Bulk Item)
(
    '00000000-0000-4000-8000-000000000005',
    '85fe1119-b04c-41ac-80f1-829d23322598',
    'Stainless Steel Fasteners M8',
    'TEST-PART-005',
    'Test fasteners for E2E testing - bulk items',
    'Hardware',
    500,
    100,
    200,
    'each',
    'Workshop - Hardware Bins',
    0.50,
    'USD',
    NOW(),
    NOW()
)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    part_number = EXCLUDED.part_number,
    description = EXCLUDED.description,
    category = EXCLUDED.category,
    quantity_on_hand = EXCLUDED.quantity_on_hand,
    quantity_minimum = EXCLUDED.quantity_minimum,
    quantity_reorder = EXCLUDED.quantity_reorder,
    unit_of_measure = EXCLUDED.unit_of_measure,
    storage_location = EXCLUDED.storage_location,
    unit_cost = EXCLUDED.unit_cost,
    currency = EXCLUDED.currency,
    updated_at = NOW();

-- ============================================================================
-- Verification
-- ============================================================================
DO $$
DECLARE
    test_parts_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO test_parts_count
    FROM public.pms_parts
    WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
    AND part_number LIKE 'TEST-PART-%';

    IF test_parts_count >= 5 THEN
        RAISE NOTICE 'E2E Test Parts: % parts seeded successfully for MY Pandora', test_parts_count;
    ELSE
        RAISE WARNING 'E2E Test Parts: Only % parts found (expected 5+)', test_parts_count;
    END IF;
END $$;
