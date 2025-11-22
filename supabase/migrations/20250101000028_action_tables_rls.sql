-- ============================================================================
-- RLS POLICIES FOR ACTION-SUPPORTING TABLES
-- ============================================================================
-- All user-facing tables enforce yacht_id isolation
-- Service role has full access for backend operations

-- ============================================================================
-- ENABLE RLS ON ALL TABLES
-- ============================================================================

ALTER TABLE public.equipment ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.work_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.work_order_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.faults ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.handover_drafts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.handover_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.handover_exports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.parts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.stock_locations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.stock_levels ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.suppliers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.purchase_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.purchase_order_lines ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.graph_nodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.graph_edges ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.predictive_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.predictive_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.action_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.search_queries ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- HELPER FUNCTION: Get user's yacht_id from JWT
-- ============================================================================

CREATE OR REPLACE FUNCTION public.get_user_yacht_id()
RETURNS UUID
LANGUAGE sql
SECURITY DEFINER
STABLE
AS $$
    SELECT COALESCE(
        (auth.jwt() ->> 'yacht_id')::UUID,
        (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid())
    );
$$;

COMMENT ON FUNCTION public.get_user_yacht_id() IS 'Returns yacht_id from JWT claims or user_profiles';

-- ============================================================================
-- EQUIPMENT POLICIES
-- ============================================================================

DROP POLICY IF EXISTS "Users can view own yacht equipment" ON public.equipment;
CREATE POLICY "Users can view own yacht equipment"
    ON public.equipment FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

DROP POLICY IF EXISTS "Users can manage own yacht equipment" ON public.equipment;
CREATE POLICY "Users can manage own yacht equipment"
    ON public.equipment FOR ALL TO authenticated
    USING (yacht_id = public.get_user_yacht_id())
    WITH CHECK (yacht_id = public.get_user_yacht_id());

DROP POLICY IF EXISTS "Service role full access to equipment" ON public.equipment;
CREATE POLICY "Service role full access to equipment"
    ON public.equipment FOR ALL TO service_role
    USING (true) WITH CHECK (true);

-- ============================================================================
-- WORK ORDERS POLICIES
-- ============================================================================

DROP POLICY IF EXISTS "Users can view own yacht work orders" ON public.work_orders;
CREATE POLICY "Users can view own yacht work orders"
    ON public.work_orders FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

DROP POLICY IF EXISTS "Users can manage own yacht work orders" ON public.work_orders;
CREATE POLICY "Users can manage own yacht work orders"
    ON public.work_orders FOR ALL TO authenticated
    USING (yacht_id = public.get_user_yacht_id())
    WITH CHECK (yacht_id = public.get_user_yacht_id());

DROP POLICY IF EXISTS "Service role full access to work orders" ON public.work_orders;
CREATE POLICY "Service role full access to work orders"
    ON public.work_orders FOR ALL TO service_role
    USING (true) WITH CHECK (true);

-- ============================================================================
-- WORK ORDER HISTORY POLICIES
-- ============================================================================

DROP POLICY IF EXISTS "Users can view own yacht WO history" ON public.work_order_history;
CREATE POLICY "Users can view own yacht WO history"
    ON public.work_order_history FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

DROP POLICY IF EXISTS "Users can create WO history" ON public.work_order_history;
CREATE POLICY "Users can create WO history"
    ON public.work_order_history FOR INSERT TO authenticated
    WITH CHECK (yacht_id = public.get_user_yacht_id());

DROP POLICY IF EXISTS "Service role full access to WO history" ON public.work_order_history;
CREATE POLICY "Service role full access to WO history"
    ON public.work_order_history FOR ALL TO service_role
    USING (true) WITH CHECK (true);

-- ============================================================================
-- NOTES POLICIES
-- ============================================================================

DROP POLICY IF EXISTS "Users can view own yacht notes" ON public.notes;
CREATE POLICY "Users can view own yacht notes"
    ON public.notes FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

DROP POLICY IF EXISTS "Users can manage own yacht notes" ON public.notes;
CREATE POLICY "Users can manage own yacht notes"
    ON public.notes FOR ALL TO authenticated
    USING (yacht_id = public.get_user_yacht_id())
    WITH CHECK (yacht_id = public.get_user_yacht_id());

DROP POLICY IF EXISTS "Service role full access to notes" ON public.notes;
CREATE POLICY "Service role full access to notes"
    ON public.notes FOR ALL TO service_role
    USING (true) WITH CHECK (true);

-- ============================================================================
-- FAULTS POLICIES
-- ============================================================================

DROP POLICY IF EXISTS "Users can view own yacht faults" ON public.faults;
CREATE POLICY "Users can view own yacht faults"
    ON public.faults FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

DROP POLICY IF EXISTS "Users can manage own yacht faults" ON public.faults;
CREATE POLICY "Users can manage own yacht faults"
    ON public.faults FOR ALL TO authenticated
    USING (yacht_id = public.get_user_yacht_id())
    WITH CHECK (yacht_id = public.get_user_yacht_id());

DROP POLICY IF EXISTS "Service role full access to faults" ON public.faults;
CREATE POLICY "Service role full access to faults"
    ON public.faults FOR ALL TO service_role
    USING (true) WITH CHECK (true);

-- ============================================================================
-- HANDOVER POLICIES
-- ============================================================================

DROP POLICY IF EXISTS "Users can view own yacht handovers" ON public.handover_drafts;
CREATE POLICY "Users can view own yacht handovers"
    ON public.handover_drafts FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

DROP POLICY IF EXISTS "Users can manage own yacht handovers" ON public.handover_drafts;
CREATE POLICY "Users can manage own yacht handovers"
    ON public.handover_drafts FOR ALL TO authenticated
    USING (yacht_id = public.get_user_yacht_id())
    WITH CHECK (yacht_id = public.get_user_yacht_id());

DROP POLICY IF EXISTS "Service role full access to handovers" ON public.handover_drafts;
CREATE POLICY "Service role full access to handovers"
    ON public.handover_drafts FOR ALL TO service_role
    USING (true) WITH CHECK (true);

-- Handover items
DROP POLICY IF EXISTS "Users can view own yacht handover items" ON public.handover_items;
CREATE POLICY "Users can view own yacht handover items"
    ON public.handover_items FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

DROP POLICY IF EXISTS "Users can manage own yacht handover items" ON public.handover_items;
CREATE POLICY "Users can manage own yacht handover items"
    ON public.handover_items FOR ALL TO authenticated
    USING (yacht_id = public.get_user_yacht_id())
    WITH CHECK (yacht_id = public.get_user_yacht_id());

DROP POLICY IF EXISTS "Service role full access to handover items" ON public.handover_items;
CREATE POLICY "Service role full access to handover items"
    ON public.handover_items FOR ALL TO service_role
    USING (true) WITH CHECK (true);

-- Handover exports
DROP POLICY IF EXISTS "Users can view own yacht handover exports" ON public.handover_exports;
CREATE POLICY "Users can view own yacht handover exports"
    ON public.handover_exports FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

DROP POLICY IF EXISTS "Users can create handover exports" ON public.handover_exports;
CREATE POLICY "Users can create handover exports"
    ON public.handover_exports FOR INSERT TO authenticated
    WITH CHECK (yacht_id = public.get_user_yacht_id());

DROP POLICY IF EXISTS "Service role full access to handover exports" ON public.handover_exports;
CREATE POLICY "Service role full access to handover exports"
    ON public.handover_exports FOR ALL TO service_role
    USING (true) WITH CHECK (true);

-- ============================================================================
-- INVENTORY POLICIES (parts, stock, suppliers, POs)
-- ============================================================================

-- Parts
DROP POLICY IF EXISTS "Users can view own yacht parts" ON public.parts;
CREATE POLICY "Users can view own yacht parts"
    ON public.parts FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

DROP POLICY IF EXISTS "Users can manage own yacht parts" ON public.parts;
CREATE POLICY "Users can manage own yacht parts"
    ON public.parts FOR ALL TO authenticated
    USING (yacht_id = public.get_user_yacht_id())
    WITH CHECK (yacht_id = public.get_user_yacht_id());

DROP POLICY IF EXISTS "Service role full access to parts" ON public.parts;
CREATE POLICY "Service role full access to parts"
    ON public.parts FOR ALL TO service_role
    USING (true) WITH CHECK (true);

-- Stock locations
DROP POLICY IF EXISTS "Users can view own yacht stock locations" ON public.stock_locations;
CREATE POLICY "Users can view own yacht stock locations"
    ON public.stock_locations FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

DROP POLICY IF EXISTS "Users can manage own yacht stock locations" ON public.stock_locations;
CREATE POLICY "Users can manage own yacht stock locations"
    ON public.stock_locations FOR ALL TO authenticated
    USING (yacht_id = public.get_user_yacht_id())
    WITH CHECK (yacht_id = public.get_user_yacht_id());

DROP POLICY IF EXISTS "Service role full access to stock locations" ON public.stock_locations;
CREATE POLICY "Service role full access to stock locations"
    ON public.stock_locations FOR ALL TO service_role
    USING (true) WITH CHECK (true);

-- Stock levels
DROP POLICY IF EXISTS "Users can view own yacht stock levels" ON public.stock_levels;
CREATE POLICY "Users can view own yacht stock levels"
    ON public.stock_levels FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

DROP POLICY IF EXISTS "Users can manage own yacht stock levels" ON public.stock_levels;
CREATE POLICY "Users can manage own yacht stock levels"
    ON public.stock_levels FOR ALL TO authenticated
    USING (yacht_id = public.get_user_yacht_id())
    WITH CHECK (yacht_id = public.get_user_yacht_id());

DROP POLICY IF EXISTS "Service role full access to stock levels" ON public.stock_levels;
CREATE POLICY "Service role full access to stock levels"
    ON public.stock_levels FOR ALL TO service_role
    USING (true) WITH CHECK (true);

-- Suppliers
DROP POLICY IF EXISTS "Users can view own yacht suppliers" ON public.suppliers;
CREATE POLICY "Users can view own yacht suppliers"
    ON public.suppliers FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

DROP POLICY IF EXISTS "Users can manage own yacht suppliers" ON public.suppliers;
CREATE POLICY "Users can manage own yacht suppliers"
    ON public.suppliers FOR ALL TO authenticated
    USING (yacht_id = public.get_user_yacht_id())
    WITH CHECK (yacht_id = public.get_user_yacht_id());

DROP POLICY IF EXISTS "Service role full access to suppliers" ON public.suppliers;
CREATE POLICY "Service role full access to suppliers"
    ON public.suppliers FOR ALL TO service_role
    USING (true) WITH CHECK (true);

-- Purchase orders
DROP POLICY IF EXISTS "Users can view own yacht POs" ON public.purchase_orders;
CREATE POLICY "Users can view own yacht POs"
    ON public.purchase_orders FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

DROP POLICY IF EXISTS "Users can manage own yacht POs" ON public.purchase_orders;
CREATE POLICY "Users can manage own yacht POs"
    ON public.purchase_orders FOR ALL TO authenticated
    USING (yacht_id = public.get_user_yacht_id())
    WITH CHECK (yacht_id = public.get_user_yacht_id());

DROP POLICY IF EXISTS "Service role full access to POs" ON public.purchase_orders;
CREATE POLICY "Service role full access to POs"
    ON public.purchase_orders FOR ALL TO service_role
    USING (true) WITH CHECK (true);

-- Purchase order lines
DROP POLICY IF EXISTS "Users can view own yacht PO lines" ON public.purchase_order_lines;
CREATE POLICY "Users can view own yacht PO lines"
    ON public.purchase_order_lines FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

DROP POLICY IF EXISTS "Users can manage own yacht PO lines" ON public.purchase_order_lines;
CREATE POLICY "Users can manage own yacht PO lines"
    ON public.purchase_order_lines FOR ALL TO authenticated
    USING (yacht_id = public.get_user_yacht_id())
    WITH CHECK (yacht_id = public.get_user_yacht_id());

DROP POLICY IF EXISTS "Service role full access to PO lines" ON public.purchase_order_lines;
CREATE POLICY "Service role full access to PO lines"
    ON public.purchase_order_lines FOR ALL TO service_role
    USING (true) WITH CHECK (true);

-- ============================================================================
-- GRAPH RAG POLICIES
-- ============================================================================

DROP POLICY IF EXISTS "Users can view own yacht graph nodes" ON public.graph_nodes;
CREATE POLICY "Users can view own yacht graph nodes"
    ON public.graph_nodes FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

DROP POLICY IF EXISTS "Service role full access to graph nodes" ON public.graph_nodes;
CREATE POLICY "Service role full access to graph nodes"
    ON public.graph_nodes FOR ALL TO service_role
    USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Users can view own yacht graph edges" ON public.graph_edges;
CREATE POLICY "Users can view own yacht graph edges"
    ON public.graph_edges FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

DROP POLICY IF EXISTS "Service role full access to graph edges" ON public.graph_edges;
CREATE POLICY "Service role full access to graph edges"
    ON public.graph_edges FOR ALL TO service_role
    USING (true) WITH CHECK (true);

-- ============================================================================
-- PREDICTIVE & ANALYTICS POLICIES
-- ============================================================================

DROP POLICY IF EXISTS "Users can view own yacht predictive state" ON public.predictive_state;
CREATE POLICY "Users can view own yacht predictive state"
    ON public.predictive_state FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

DROP POLICY IF EXISTS "Service role full access to predictive state" ON public.predictive_state;
CREATE POLICY "Service role full access to predictive state"
    ON public.predictive_state FOR ALL TO service_role
    USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Users can view own yacht predictive history" ON public.predictive_history;
CREATE POLICY "Users can view own yacht predictive history"
    ON public.predictive_history FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

DROP POLICY IF EXISTS "Service role full access to predictive history" ON public.predictive_history;
CREATE POLICY "Service role full access to predictive history"
    ON public.predictive_history FOR ALL TO service_role
    USING (true) WITH CHECK (true);

-- Action logs (users can only view their yacht's logs)
DROP POLICY IF EXISTS "Users can view own yacht action logs" ON public.action_logs;
CREATE POLICY "Users can view own yacht action logs"
    ON public.action_logs FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

DROP POLICY IF EXISTS "Service role full access to action logs" ON public.action_logs;
CREATE POLICY "Service role full access to action logs"
    ON public.action_logs FOR ALL TO service_role
    USING (true) WITH CHECK (true);

-- Search queries (users can only view their own queries)
DROP POLICY IF EXISTS "Users can view own search queries" ON public.search_queries;
CREATE POLICY "Users can view own search queries"
    ON public.search_queries FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id() AND (user_id = auth.uid() OR user_id IS NULL));

DROP POLICY IF EXISTS "Users can create search queries" ON public.search_queries;
CREATE POLICY "Users can create search queries"
    ON public.search_queries FOR INSERT TO authenticated
    WITH CHECK (yacht_id = public.get_user_yacht_id());

DROP POLICY IF EXISTS "Service role full access to search queries" ON public.search_queries;
CREATE POLICY "Service role full access to search queries"
    ON public.search_queries FOR ALL TO service_role
    USING (true) WITH CHECK (true);

-- Verification
DO $$
DECLARE
    policy_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE schemaname = 'public';

    RAISE NOTICE '✓ Migration 028 Complete - Created RLS policies for all action tables (total policies: %)', policy_count;
END $$;
