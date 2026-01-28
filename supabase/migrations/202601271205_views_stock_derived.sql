-- Migration: 20260127_205_views_stock_derived.sql
-- Purpose: Create views for derived stock calculations (Part Lens v2)
-- Defensive: Skip if required tables/columns don't exist
-- Column mapping: pms_parts uses quantity_minimum, quantity_reorder, storage_location

DO $$
BEGIN
    -- Check if pms_parts table exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pms_parts' AND table_schema = 'public') THEN
        RAISE NOTICE 'pms_parts table does not exist - skipping stock views';
        RETURN;
    END IF;

    -- v_part_stock_status view
    -- Uses actual pms_parts columns: quantity_minimum, quantity_reorder, storage_location
    -- is_critical and department don't exist in pms_parts, so we use defaults
    EXECUTE '
        CREATE OR REPLACE VIEW v_part_stock_status AS
        SELECT
            p.id AS part_id,
            p.yacht_id,
            p.name AS part_name,
            p.part_number,
            false AS is_critical,
            COALESCE(p.quantity_minimum, 0) AS min_level,
            GREATEST(COALESCE(p.quantity_reorder, 1), 1) AS reorder_multiple,
            p.category,
            NULL::TEXT AS department,
            COALESCE(p.quantity_on_hand, 0) AS on_hand_qty,
            p.storage_location AS location,
            CASE WHEN COALESCE(p.quantity_on_hand, 0) = 0 THEN true ELSE false END AS is_out_of_stock,
            CASE WHEN COALESCE(p.quantity_minimum, 0) > 0
                  AND COALESCE(p.quantity_on_hand, 0) <= COALESCE(p.quantity_minimum, 0)
                 THEN true ELSE false END AS is_low_stock,
            CASE WHEN COALESCE(p.quantity_minimum, 0) > 0
                  AND COALESCE(p.quantity_on_hand, 0) < COALESCE(p.quantity_minimum, 0)
                 THEN CEIL(GREATEST(COALESCE(p.quantity_minimum, 0) - COALESCE(p.quantity_on_hand, 0), 1)::numeric
                          / GREATEST(COALESCE(p.quantity_reorder, 1), 1))
                      * GREATEST(COALESCE(p.quantity_reorder, 1), 1)
                 ELSE 0 END::INTEGER AS suggested_order_qty,
            CASE WHEN COALESCE(p.quantity_on_hand, 0) = 0 THEN ''critical''
                 WHEN COALESCE(p.quantity_minimum, 0) > 0
                  AND COALESCE(p.quantity_on_hand, 0) <= COALESCE(p.quantity_minimum, 0) * 0.5 THEN ''high''
                 WHEN COALESCE(p.quantity_minimum, 0) > 0
                  AND COALESCE(p.quantity_on_hand, 0) <= COALESCE(p.quantity_minimum, 0) THEN ''medium''
                 ELSE ''low'' END AS urgency
        FROM pms_parts p
    ';

    EXECUTE 'GRANT SELECT ON v_part_stock_status TO authenticated';
    EXECUTE 'GRANT SELECT ON v_part_stock_status TO service_role';

    -- v_low_stock_report view
    EXECUTE '
        CREATE OR REPLACE VIEW v_low_stock_report AS
        SELECT part_id, yacht_id, part_name, part_number, is_critical, on_hand_qty,
               min_level, reorder_multiple, suggested_order_qty, urgency, category, department, location
        FROM v_part_stock_status
        WHERE is_low_stock = true OR is_out_of_stock = true
        ORDER BY is_critical DESC, urgency = ''critical'' DESC, urgency = ''high'' DESC, suggested_order_qty DESC
    ';

    EXECUTE 'GRANT SELECT ON v_low_stock_report TO authenticated';
    EXECUTE 'GRANT SELECT ON v_low_stock_report TO service_role';

    RAISE NOTICE 'SUCCESS: Stock derived views created';
END $$;

-- v_stock_from_transactions and v_stock_reconciliation require pms_inventory_stock
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pms_inventory_stock' AND table_schema = 'public') THEN
        RAISE NOTICE 'pms_inventory_stock table does not exist - skipping transaction views';
        RETURN;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pms_inventory_transactions' AND table_schema = 'public') THEN
        RAISE NOTICE 'pms_inventory_transactions table does not exist - skipping transaction views';
        RETURN;
    END IF;

    EXECUTE '
        CREATE OR REPLACE VIEW v_stock_from_transactions AS
        SELECT
            s.yacht_id, s.part_id, s.location,
            SUM(t.quantity_change) AS derived_on_hand_qty,
            COUNT(*) AS transaction_count,
            MIN(t.created_at) AS first_transaction,
            MAX(t.created_at) AS last_transaction
        FROM pms_inventory_stock s
        LEFT JOIN pms_inventory_transactions t ON s.id = t.stock_id
        GROUP BY s.yacht_id, s.part_id, s.location
    ';

    EXECUTE 'GRANT SELECT ON v_stock_from_transactions TO authenticated';
    EXECUTE 'GRANT SELECT ON v_stock_from_transactions TO service_role';

    EXECUTE '
        CREATE OR REPLACE VIEW v_stock_reconciliation AS
        SELECT
            s.yacht_id, s.part_id, p.name AS part_name, p.part_number,
            s.quantity AS actual_qty,
            COALESCE(t.derived_on_hand_qty, 0) AS derived_qty,
            s.quantity - COALESCE(t.derived_on_hand_qty, 0) AS discrepancy,
            CASE WHEN s.quantity = COALESCE(t.derived_on_hand_qty, 0) THEN ''OK'' ELSE ''MISMATCH'' END AS status
        FROM pms_inventory_stock s
        JOIN pms_parts p ON s.part_id = p.id AND s.yacht_id = p.yacht_id
        LEFT JOIN v_stock_from_transactions t ON s.part_id = t.part_id AND s.yacht_id = t.yacht_id AND s.location = t.location
    ';

    EXECUTE 'GRANT SELECT ON v_stock_reconciliation TO authenticated';
    EXECUTE 'GRANT SELECT ON v_stock_reconciliation TO service_role';

    RAISE NOTICE 'SUCCESS: Stock transaction views created';
END $$;
