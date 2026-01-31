-- ============================================================================
-- MIGRATION: 20260130_109_seed_receiving_test_data.sql
-- PURPOSE: Seed test data for receiving E2E tests
-- LENS: Receiving Lens v1
-- DATE: 2026-01-30
-- ============================================================================
-- RATIONALE: E2E tests search for "Racor receiving" but no test data exists.
--            This migration creates sample receiving records for test yacht.
-- ============================================================================

BEGIN;

-- ============================================================================
-- SEED TEST RECEIVING DATA
-- ============================================================================

-- Insert test receiving records for test yacht
-- Test yacht ID: 85fe1119-b04c-41ac-80f1-829d23322598
-- HOD user (received_by): 89b1262c-ff59-4591-b954-757cdf3d609d (hod.tenant@alex-short.com)

DO $$
DECLARE
    v_test_yacht_id UUID := '85fe1119-b04c-41ac-80f1-829d23322598';
    v_hod_user_id UUID := '89b1262c-ff59-4591-b954-757cdf3d609d';
    v_receiving_1 UUID := gen_random_uuid();
    v_receiving_2 UUID := gen_random_uuid();
    v_receiving_3 UUID := gen_random_uuid();
BEGIN
    -- Only seed if test yacht exists and has no receiving records yet
    IF EXISTS (
        SELECT 1 FROM yacht_profiles WHERE id = v_test_yacht_id
    ) AND NOT EXISTS (
        SELECT 1 FROM pms_receiving WHERE yacht_id = v_test_yacht_id AND vendor_name = 'Racor'
    ) THEN

        -- Receiving 1: Racor - Draft status
        INSERT INTO pms_receiving (
            id,
            yacht_id,
            vendor_name,
            vendor_reference,
            received_date,
            received_by,
            status,
            currency,
            subtotal,
            tax_total,
            total,
            notes,
            created_at,
            updated_at
        ) VALUES (
            v_receiving_1,
            v_test_yacht_id,
            'Racor',
            'PO-2024-RACOR-001',
            CURRENT_DATE - INTERVAL '7 days',
            v_hod_user_id,
            'draft',
            'USD',
            1250.00,
            125.00,
            1375.00,
            'Fuel filters and separator elements - Q1 2024 order',
            NOW() - INTERVAL '7 days',
            NOW() - INTERVAL '7 days'
        );

        -- Receiving 2: Racor - In Review status
        INSERT INTO pms_receiving (
            id,
            yacht_id,
            vendor_name,
            vendor_reference,
            received_date,
            received_by,
            status,
            currency,
            subtotal,
            tax_total,
            total,
            notes,
            created_at,
            updated_at
        ) VALUES (
            v_receiving_2,
            v_test_yacht_id,
            'Racor',
            'PO-2024-RACOR-002',
            CURRENT_DATE - INTERVAL '3 days',
            v_hod_user_id,
            'in_review',
            'USD',
            850.00,
            85.00,
            935.00,
            'Replacement filter housings',
            NOW() - INTERVAL '3 days',
            NOW() - INTERVAL '3 days'
        );

        -- Receiving 3: Racor - Accepted status
        INSERT INTO pms_receiving (
            id,
            yacht_id,
            vendor_name,
            vendor_reference,
            received_date,
            received_by,
            status,
            currency,
            subtotal,
            tax_total,
            total,
            notes,
            created_at,
            updated_at
        ) VALUES (
            v_receiving_3,
            v_test_yacht_id,
            'Racor',
            'PO-2024-RACOR-003',
            CURRENT_DATE - INTERVAL '14 days',
            v_hod_user_id,
            'accepted',
            'USD',
            2100.00,
            210.00,
            2310.00,
            'Annual fuel system maintenance parts - ACCEPTED',
            NOW() - INTERVAL '14 days',
            NOW() - INTERVAL '1 day'
        );

        -- Add line items for Receiving 1 (Draft)
        INSERT INTO pms_receiving_items (
            yacht_id,
            receiving_id,
            description,
            quantity_expected,
            quantity_received,
            unit_price,
            currency,
            created_at
        ) VALUES
        (
            v_test_yacht_id,
            v_receiving_1,
            'Racor Fuel Filter Element 2040PM (Primary)',
            10,
            10,
            45.00,
            'USD',
            NOW() - INTERVAL '7 days'
        ),
        (
            v_test_yacht_id,
            v_receiving_1,
            'Racor Fuel Filter Element 2040SM (Secondary)',
            10,
            10,
            55.00,
            'USD',
            NOW() - INTERVAL '7 days'
        ),
        (
            v_test_yacht_id,
            v_receiving_1,
            'Racor Turbine Series Fuel Water Separator',
            5,
            5,
            90.00,
            'USD',
            NOW() - INTERVAL '7 days'
        );

        -- Add line items for Receiving 2 (In Review)
        INSERT INTO pms_receiving_items (
            yacht_id,
            receiving_id,
            description,
            quantity_expected,
            quantity_received,
            unit_price,
            currency,
            created_at
        ) VALUES
        (
            v_test_yacht_id,
            v_receiving_2,
            'Racor Filter Housing Assembly 1000FH',
            2,
            2,
            425.00,
            'USD',
            NOW() - INTERVAL '3 days'
        );

        -- Add line items for Receiving 3 (Accepted)
        INSERT INTO pms_receiving_items (
            yacht_id,
            receiving_id,
            description,
            quantity_expected,
            quantity_received,
            unit_price,
            currency,
            created_at
        ) VALUES
        (
            v_test_yacht_id,
            v_receiving_3,
            'Racor Complete Fuel System Service Kit',
            3,
            3,
            700.00,
            'USD',
            NOW() - INTERVAL '14 days'
        );

        RAISE NOTICE 'SUCCESS: Seeded 3 Racor receiving records with line items for test yacht %', v_test_yacht_id;
    ELSE
        RAISE NOTICE 'SKIPPED: Test yacht not found or Racor receiving data already exists';
    END IF;
END $$;

COMMIT;

-- ============================================================================
-- VERIFICATION
-- ============================================================================
DO $$
DECLARE
    receiving_count INTEGER;
    items_count INTEGER;
    v_test_yacht_id UUID := '85fe1119-b04c-41ac-80f1-829d23322598';
BEGIN
    -- Verify receiving records exist
    SELECT COUNT(*) INTO receiving_count
    FROM pms_receiving
    WHERE yacht_id = v_test_yacht_id
      AND vendor_name = 'Racor';

    -- Verify line items exist
    SELECT COUNT(*) INTO items_count
    FROM pms_receiving_items
    WHERE yacht_id = v_test_yacht_id;

    RAISE NOTICE 'Verification: % Racor receiving records, % line items for test yacht',
        receiving_count, items_count;
END $$;
