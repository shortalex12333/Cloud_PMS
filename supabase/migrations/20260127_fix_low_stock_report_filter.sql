-- Migration: Fix v_low_stock_report to exclude parts with min_level=0
-- Date: 2026-01-27
-- Issue: Parts with min_level=0 should not appear in low stock report
-- Doctrine: Only parts with reorder thresholds (min_level > 0) should trigger alerts

-- Drop and recreate v_low_stock_report with corrected WHERE clause
DROP VIEW IF EXISTS public.v_low_stock_report;

CREATE VIEW public.v_low_stock_report AS
SELECT
    ps.part_id,
    ps.yacht_id,
    ps.part_name,
    ps.part_number,
    ps.is_critical,
    ps.on_hand,
    ps.min_level,
    ps.reorder_multiple,
    ps.location,
    ps.category,
    ps.department,
    -- Derived flags
    CASE WHEN ps.on_hand = 0 THEN true ELSE false END AS is_out_of_stock,
    CASE WHEN ps.min_level > 0 AND ps.on_hand <= ps.min_level THEN true ELSE false END AS is_low_stock,
    -- Suggested order qty: round_up(max(min_level - on_hand, 1), reorder_multiple)
    CASE
        WHEN ps.min_level > 0 AND ps.on_hand < ps.min_level THEN
            CEIL(GREATEST(ps.min_level - ps.on_hand, 1)::numeric / GREATEST(ps.reorder_multiple, 1)) * GREATEST(ps.reorder_multiple, 1)
        ELSE 0
    END::INTEGER AS suggested_order_qty,
    -- Urgency
    CASE
        WHEN ps.on_hand = 0 THEN 'critical'
        WHEN ps.min_level > 0 AND ps.on_hand <= ps.min_level * 0.5 THEN 'high'
        WHEN ps.min_level > 0 AND ps.on_hand <= ps.min_level THEN 'medium'
        ELSE 'low'
    END AS urgency
FROM public.pms_part_stock ps
WHERE ps.min_level > 0 AND ps.on_hand <= ps.min_level  -- FIXED: Only parts with reorder thresholds
ORDER BY
    ps.is_critical DESC NULLS LAST,
    ps.on_hand = 0 DESC,
    ps.on_hand ASC;

GRANT SELECT ON public.v_low_stock_report TO authenticated;
GRANT SELECT ON public.v_low_stock_report TO service_role;

-- Add comment explaining the filter
COMMENT ON VIEW public.v_low_stock_report IS
    'Low stock report for parts that need reordering. '
    'Only includes parts with min_level > 0 (tracked for reorders). '
    'Parts with min_level=0 are not tracked and excluded from this report.';
