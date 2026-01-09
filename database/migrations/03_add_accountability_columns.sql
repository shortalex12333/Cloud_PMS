-- Migration: 03_add_accountability_columns
-- =============================================================================
-- Add Accountability & Inventory Columns to Existing Tables
-- =============================================================================
--
-- PURPOSE: Enable trust through transparency and accountability
--
-- TABLES MODIFIED:
--   1. pms_parts - Add inventory tracking with accountability
--   2. pms_work_orders - Add completion tracking with signatures
--
-- TRUST PRINCIPLES:
--   - Every stock count has WHO counted WHEN (accountability)
--   - Every WO completion has WHO signed off WHEN (accountability)
--   - Link work orders to originating faults (transparency)
--
-- USER REQUIREMENT:
--   "trust will be the reason for our slowest adoption of users"
--   → No "black box" - every change must show WHO did WHAT WHEN
--
-- =============================================================================

-- =============================================================================
-- 1. ADD INVENTORY TRACKING TO pms_parts
-- =============================================================================

-- Current state: pms_parts has name, part_number, category, manufacturer
-- Missing: quantity_on_hand, last_counted_by (accountability!)

ALTER TABLE public.pms_parts
ADD COLUMN IF NOT EXISTS quantity_on_hand INTEGER NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS minimum_quantity INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS unit TEXT DEFAULT 'ea',
ADD COLUMN IF NOT EXISTS location TEXT,
ADD COLUMN IF NOT EXISTS last_counted_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS last_counted_by UUID REFERENCES auth.users(id);

-- Trust-focused comments
COMMENT ON COLUMN public.pms_parts.quantity_on_hand IS
'Current stock level. Updated by pms_part_usage log (never directly modified).';

COMMENT ON COLUMN public.pms_parts.minimum_quantity IS
'Reorder threshold. When quantity_on_hand <= minimum_quantity, triggers low stock warning.';

COMMENT ON COLUMN public.pms_parts.unit IS
'Unit of measurement (ea, kg, L, m, etc). For transparency in stock reporting.';

COMMENT ON COLUMN public.pms_parts.location IS
'Physical location on yacht (e.g., "Storeroom A - Shelf 3"). For finding parts quickly.';

COMMENT ON COLUMN public.pms_parts.last_counted_at IS
'ACCOUNTABILITY: When was stock last physically counted. Shows freshness of quantity_on_hand.';

COMMENT ON COLUMN public.pms_parts.last_counted_by IS
'ACCOUNTABILITY: WHO counted stock. Links to auth.users. For trust: users know who verified stock levels.';

-- Index for low stock warnings (performance)
CREATE INDEX IF NOT EXISTS idx_pms_parts_low_stock
ON public.pms_parts(yacht_id, quantity_on_hand, minimum_quantity)
WHERE quantity_on_hand <= minimum_quantity;

COMMENT ON INDEX idx_pms_parts_low_stock IS
'Fast lookup of low stock items for check_stock_level action and inventory warnings.';

-- =============================================================================
-- 2. ADD COMPLETION TRACKING TO pms_work_orders
-- =============================================================================

-- Current state: pms_work_orders has created_by, updated_by
-- Missing: fault_id (link to trigger), completed_by (accountability!), assigned_to

ALTER TABLE public.pms_work_orders
ADD COLUMN IF NOT EXISTS fault_id UUID REFERENCES public.pms_faults(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS assigned_to UUID REFERENCES auth.users(id),
ADD COLUMN IF NOT EXISTS completed_by UUID REFERENCES auth.users(id),
ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS completion_notes TEXT;

-- Trust-focused comments
COMMENT ON COLUMN public.pms_work_orders.fault_id IS
'TRANSPARENCY: Link to originating fault (for create_work_order_from_fault action). Shows WHY this WO was created.';

COMMENT ON COLUMN public.pms_work_orders.assigned_to IS
'ACCOUNTABILITY: WHO is responsible for this work. Shows clear ownership.';

COMMENT ON COLUMN public.pms_work_orders.completed_by IS
'ACCOUNTABILITY: WHO signed off on completion. Links to auth.users. Critical for trust: "I did this work".';

COMMENT ON COLUMN public.pms_work_orders.completed_at IS
'ACCOUNTABILITY: WHEN was work completed. Timestamp of signature.';

COMMENT ON COLUMN public.pms_work_orders.completion_notes IS
'TRANSPARENCY: WHAT was done. Required field for mark_work_order_complete action. Min 10 characters. Shows work performed.';

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_pms_work_orders_fault
ON public.pms_work_orders(fault_id)
WHERE fault_id IS NOT NULL;

COMMENT ON INDEX idx_pms_work_orders_fault IS
'Fast lookup of work orders created from specific fault (for duplicate detection).';

CREATE INDEX IF NOT EXISTS idx_pms_work_orders_assigned
ON public.pms_work_orders(assigned_to)
WHERE status NOT IN ('completed', 'closed', 'cancelled');

COMMENT ON INDEX idx_pms_work_orders_assigned IS
'Fast lookup of active work orders assigned to user (for "my work orders" view).';

CREATE INDEX IF NOT EXISTS idx_pms_work_orders_completed_by
ON public.pms_work_orders(completed_by, completed_at DESC)
WHERE completed_by IS NOT NULL;

COMMENT ON INDEX idx_pms_work_orders_completed_by IS
'Fast lookup of work completed by user (for accountability reports).';

-- =============================================================================
-- VALIDATION
-- =============================================================================

-- Verify columns were added
DO $$
BEGIN
    -- Check pms_parts columns
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'pms_parts'
        AND column_name = 'quantity_on_hand'
    ) THEN
        RAISE EXCEPTION 'Failed to add quantity_on_hand to pms_parts';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'pms_parts'
        AND column_name = 'last_counted_by'
    ) THEN
        RAISE EXCEPTION 'Failed to add last_counted_by to pms_parts';
    END IF;

    -- Check pms_work_orders columns
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'pms_work_orders'
        AND column_name = 'completed_by'
    ) THEN
        RAISE EXCEPTION 'Failed to add completed_by to pms_work_orders';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'pms_work_orders'
        AND column_name = 'fault_id'
    ) THEN
        RAISE EXCEPTION 'Failed to add fault_id to pms_work_orders';
    END IF;

    RAISE NOTICE 'Migration 03_add_accountability_columns completed successfully';
END $$;

-- =============================================================================
-- SUMMARY
-- =============================================================================

/*
CHANGES MADE:

pms_parts (6 new columns):
  + quantity_on_hand     - Current stock (updated by pms_part_usage)
  + minimum_quantity     - Reorder threshold
  + unit                 - ea, kg, L, etc
  + location             - Physical location on yacht
  + last_counted_at      - ACCOUNTABILITY: When stock was counted
  + last_counted_by      - ACCOUNTABILITY: Who counted stock

pms_work_orders (5 new columns):
  + fault_id             - TRANSPARENCY: Link to originating fault
  + assigned_to          - ACCOUNTABILITY: Who is responsible
  + completed_by         - ACCOUNTABILITY: Who signed off
  + completed_at         - ACCOUNTABILITY: When completed
  + completion_notes     - TRANSPARENCY: What was done

TRUST IMPACT:
  - Stock counting: Users know WHO verified stock WHEN
  - WO completion: Users know WHO did work WHEN and WHAT they did
  - Fault linkage: Users know WHY work order was created
  - NO "black box" - complete transparency

NEXT MIGRATION: 04_trust_accountability_tables.sql
  - Create pms_audit_log (complete audit trail)
  - Create pms_part_usage (inventory deduction transparency)
  - Create pms_work_order_notes (communication visibility)
  - Create pms_handover (shift accountability)
*/
