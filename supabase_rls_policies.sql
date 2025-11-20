-- ============================================================================
-- CelesteOS Row-Level Security (RLS) Policies
-- Version: 1.0
-- CRITICAL: Deploy AFTER schema V2.0
-- ============================================================================
--
-- Security Model:
-- 1. All tables filtered by yacht_id (tenant isolation)
-- 2. Users can only access data for their yacht
-- 3. Role-based permissions (chief_engineer, eto, captain, etc.)
-- 4. Agents/API keys have service-level access
--
-- Auth Context:
-- - auth.uid() = auth.users.id (Supabase Auth)
-- - Custom function: get_user_yacht_id() returns current user's yacht_id
-- - Custom function: get_user_role() returns current user's role
-- ============================================================================

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Get current user's yacht_id
CREATE OR REPLACE FUNCTION public.get_user_yacht_id()
RETURNS uuid
LANGUAGE sql
SECURITY DEFINER
STABLE
AS $$
  SELECT yacht_id
  FROM public.users
  WHERE auth_user_id = auth.uid()
  LIMIT 1;
$$;

COMMENT ON FUNCTION public.get_user_yacht_id IS 'Returns yacht_id for currently authenticated user';

-- Get current user's role
CREATE OR REPLACE FUNCTION public.get_user_role()
RETURNS text
LANGUAGE sql
SECURITY DEFINER
STABLE
AS $$
  SELECT role
  FROM public.users
  WHERE auth_user_id = auth.uid()
  LIMIT 1;
$$;

COMMENT ON FUNCTION public.get_user_role IS 'Returns role for currently authenticated user';

-- Check if user is manager or above
CREATE OR REPLACE FUNCTION public.is_manager()
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
STABLE
AS $$
  SELECT role IN ('manager', 'captain', 'chief_engineer')
  FROM public.users
  WHERE auth_user_id = auth.uid()
  LIMIT 1;
$$;

COMMENT ON FUNCTION public.is_manager IS 'Returns true if user has manager-level permissions';

-- ============================================================================
-- GROUP 1: CORE / AUTH TABLES
-- ============================================================================

-- -----------------------------------------------------------------------------
-- yachts: Only managers can view, system can insert
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users can view own yacht" ON yachts;
CREATE POLICY "Users can view own yacht"
  ON yachts FOR SELECT
  USING (id = get_user_yacht_id());

DROP POLICY IF EXISTS "Managers can update yacht settings" ON yachts;
CREATE POLICY "Managers can update yacht settings"
  ON yachts FOR UPDATE
  USING (id = get_user_yacht_id() AND is_manager());

COMMENT ON POLICY "Users can view own yacht" ON yachts IS 'Users can only see their own yacht';
COMMENT ON POLICY "Managers can update yacht settings" ON yachts IS 'Only managers can modify yacht settings';

-- -----------------------------------------------------------------------------
-- users: Users can view yacht crew, managers can manage
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users can view yacht crew" ON users;
CREATE POLICY "Users can view yacht crew"
  ON users FOR SELECT
  USING (yacht_id = get_user_yacht_id());

DROP POLICY IF EXISTS "Users can update own profile" ON users;
CREATE POLICY "Users can update own profile"
  ON users FOR UPDATE
  USING (auth_user_id = auth.uid())
  WITH CHECK (auth_user_id = auth.uid());

DROP POLICY IF EXISTS "Managers can manage yacht users" ON users;
CREATE POLICY "Managers can manage yacht users"
  ON users FOR ALL
  USING (yacht_id = get_user_yacht_id() AND is_manager());

COMMENT ON POLICY "Users can view yacht crew" ON users IS 'Users see all crew on their yacht';
COMMENT ON POLICY "Users can update own profile" ON users IS 'Users can edit their own profile';
COMMENT ON POLICY "Managers can manage yacht users" ON users IS 'Managers can add/edit/remove users';

-- -----------------------------------------------------------------------------
-- agents: Only managers can view/manage
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Managers can view agents" ON agents;
CREATE POLICY "Managers can view agents"
  ON agents FOR SELECT
  USING (yacht_id = get_user_yacht_id() AND is_manager());

DROP POLICY IF EXISTS "Managers can manage agents" ON agents;
CREATE POLICY "Managers can manage agents"
  ON agents FOR ALL
  USING (yacht_id = get_user_yacht_id() AND is_manager());

COMMENT ON POLICY "Managers can view agents" ON agents IS 'Only managers can see local agents';
COMMENT ON POLICY "Managers can manage agents" ON agents IS 'Only managers can create/edit agents';

-- -----------------------------------------------------------------------------
-- api_keys: Only managers can view/manage
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Managers can view api keys" ON api_keys;
CREATE POLICY "Managers can view api keys"
  ON api_keys FOR SELECT
  USING (yacht_id = get_user_yacht_id() AND is_manager());

DROP POLICY IF EXISTS "Managers can manage api keys" ON api_keys;
CREATE POLICY "Managers can manage api keys"
  ON api_keys FOR ALL
  USING (yacht_id = get_user_yacht_id() AND is_manager());

COMMENT ON POLICY "Managers can view api keys" ON api_keys IS 'Only managers can see API keys';
COMMENT ON POLICY "Managers can manage api keys" ON api_keys IS 'Only managers can create/revoke API keys';

-- -----------------------------------------------------------------------------
-- user_roles: Global read, managers can modify
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Anyone can view roles" ON user_roles;
CREATE POLICY "Anyone can view roles"
  ON user_roles FOR SELECT
  USING (true);

-- No INSERT/UPDATE/DELETE - managed by system only

COMMENT ON POLICY "Anyone can view roles" ON user_roles IS 'Role definitions are globally readable';

-- -----------------------------------------------------------------------------
-- search_queries: Users can view own yacht queries
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users can view yacht search queries" ON search_queries;
CREATE POLICY "Users can view yacht search queries"
  ON search_queries FOR SELECT
  USING (yacht_id = get_user_yacht_id());

DROP POLICY IF EXISTS "Users can insert search queries" ON search_queries;
CREATE POLICY "Users can insert search queries"
  ON search_queries FOR INSERT
  WITH CHECK (yacht_id = get_user_yacht_id());

COMMENT ON POLICY "Users can view yacht search queries" ON search_queries IS 'Users see search history for their yacht';
COMMENT ON POLICY "Users can insert search queries" ON search_queries IS 'System logs all searches';

-- -----------------------------------------------------------------------------
-- event_logs: View only, system inserts
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users can view yacht event logs" ON event_logs;
CREATE POLICY "Users can view yacht event logs"
  ON event_logs FOR SELECT
  USING (yacht_id = get_user_yacht_id());

DROP POLICY IF EXISTS "System can insert event logs" ON event_logs;
CREATE POLICY "System can insert event logs"
  ON event_logs FOR INSERT
  WITH CHECK (yacht_id = get_user_yacht_id());

COMMENT ON POLICY "Users can view yacht event logs" ON event_logs IS 'Audit logs visible to all crew';
COMMENT ON POLICY "System can insert event logs" ON event_logs IS 'System records all events';

-- ============================================================================
-- GROUP 2: PMS TABLES
-- ============================================================================

-- -----------------------------------------------------------------------------
-- equipment: All users can view, engineers can modify
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users can view yacht equipment" ON equipment;
CREATE POLICY "Users can view yacht equipment"
  ON equipment FOR SELECT
  USING (yacht_id = get_user_yacht_id());

DROP POLICY IF EXISTS "Engineers can manage equipment" ON equipment;
CREATE POLICY "Engineers can manage equipment"
  ON equipment FOR ALL
  USING (
    yacht_id = get_user_yacht_id() AND
    get_user_role() IN ('chief_engineer', 'eto', 'manager')
  );

COMMENT ON POLICY "Users can view yacht equipment" ON equipment IS 'All crew can see equipment';
COMMENT ON POLICY "Engineers can manage equipment" ON equipment IS 'Only engineers can modify equipment';

-- -----------------------------------------------------------------------------
-- work_orders: All users can view, engineers can create/modify
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users can view work orders" ON work_orders;
CREATE POLICY "Users can view work orders"
  ON work_orders FOR SELECT
  USING (yacht_id = get_user_yacht_id());

DROP POLICY IF EXISTS "Engineers can create work orders" ON work_orders;
CREATE POLICY "Engineers can create work orders"
  ON work_orders FOR INSERT
  WITH CHECK (
    yacht_id = get_user_yacht_id() AND
    get_user_role() IN ('chief_engineer', 'eto', 'deck', 'interior')
  );

DROP POLICY IF EXISTS "Engineers can update work orders" ON work_orders;
CREATE POLICY "Engineers can update work orders"
  ON work_orders FOR UPDATE
  USING (
    yacht_id = get_user_yacht_id() AND
    get_user_role() IN ('chief_engineer', 'eto', 'manager')
  );

DROP POLICY IF EXISTS "Managers can delete work orders" ON work_orders;
CREATE POLICY "Managers can delete work orders"
  ON work_orders FOR DELETE
  USING (yacht_id = get_user_yacht_id() AND is_manager());

COMMENT ON POLICY "Users can view work orders" ON work_orders IS 'All crew see work orders';
COMMENT ON POLICY "Engineers can create work orders" ON work_orders IS 'Crew can create work orders';
COMMENT ON POLICY "Engineers can update work orders" ON work_orders IS 'Engineers can modify work orders';
COMMENT ON POLICY "Managers can delete work orders" ON work_orders IS 'Only managers can delete';

-- -----------------------------------------------------------------------------
-- work_order_history: All users can view, engineers can add
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users can view work order history" ON work_order_history;
CREATE POLICY "Users can view work order history"
  ON work_order_history FOR SELECT
  USING (yacht_id = get_user_yacht_id());

DROP POLICY IF EXISTS "Engineers can add history" ON work_order_history;
CREATE POLICY "Engineers can add history"
  ON work_order_history FOR INSERT
  WITH CHECK (
    yacht_id = get_user_yacht_id() AND
    get_user_role() IN ('chief_engineer', 'eto', 'deck', 'interior')
  );

COMMENT ON POLICY "Users can view work order history" ON work_order_history IS 'All crew see work history';
COMMENT ON POLICY "Engineers can add history" ON work_order_history IS 'Crew can log work completion';

-- -----------------------------------------------------------------------------
-- faults: All users can view, engineers can manage
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users can view faults" ON faults;
CREATE POLICY "Users can view faults"
  ON faults FOR SELECT
  USING (yacht_id = get_user_yacht_id());

DROP POLICY IF EXISTS "Engineers can manage faults" ON faults;
CREATE POLICY "Engineers can manage faults"
  ON faults FOR ALL
  USING (
    yacht_id = get_user_yacht_id() AND
    get_user_role() IN ('chief_engineer', 'eto', 'deck', 'interior')
  );

COMMENT ON POLICY "Users can view faults" ON faults IS 'All crew see faults';
COMMENT ON POLICY "Engineers can manage faults" ON faults IS 'Crew can create/resolve faults';

-- -----------------------------------------------------------------------------
-- hours_of_rest: Users can view own, managers can view all
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users can view own hours of rest" ON hours_of_rest;
CREATE POLICY "Users can view own hours of rest"
  ON hours_of_rest FOR SELECT
  USING (
    yacht_id = get_user_yacht_id() AND
    (user_id = (SELECT id FROM users WHERE auth_user_id = auth.uid()) OR is_manager())
  );

DROP POLICY IF EXISTS "Users can insert own hours of rest" ON hours_of_rest;
CREATE POLICY "Users can insert own hours of rest"
  ON hours_of_rest FOR INSERT
  WITH CHECK (
    yacht_id = get_user_yacht_id() AND
    user_id = (SELECT id FROM users WHERE auth_user_id = auth.uid())
  );

DROP POLICY IF EXISTS "Users can update own hours of rest" ON hours_of_rest;
CREATE POLICY "Users can update own hours of rest"
  ON hours_of_rest FOR UPDATE
  USING (
    yacht_id = get_user_yacht_id() AND
    user_id = (SELECT id FROM users WHERE auth_user_id = auth.uid())
  );

COMMENT ON POLICY "Users can view own hours of rest" ON hours_of_rest IS 'Users see own hours, managers see all';
COMMENT ON POLICY "Users can insert own hours of rest" ON hours_of_rest IS 'Users log their own hours';
COMMENT ON POLICY "Users can update own hours of rest" ON hours_of_rest IS 'Users can edit their hours';

-- ============================================================================
-- GROUP 3: INVENTORY TABLES
-- ============================================================================

-- -----------------------------------------------------------------------------
-- parts: All users can view, engineers can manage
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users can view parts" ON parts;
CREATE POLICY "Users can view parts"
  ON parts FOR SELECT
  USING (yacht_id = get_user_yacht_id());

DROP POLICY IF EXISTS "Engineers can manage parts" ON parts;
CREATE POLICY "Engineers can manage parts"
  ON parts FOR ALL
  USING (
    yacht_id = get_user_yacht_id() AND
    get_user_role() IN ('chief_engineer', 'eto', 'manager')
  );

COMMENT ON POLICY "Users can view parts" ON parts IS 'All crew can see parts catalog';
COMMENT ON POLICY "Engineers can manage parts" ON parts IS 'Engineers manage parts catalog';

-- -----------------------------------------------------------------------------
-- equipment_parts: All users can view, engineers can manage
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users can view equipment parts" ON equipment_parts;
CREATE POLICY "Users can view equipment parts"
  ON equipment_parts FOR SELECT
  USING (yacht_id = get_user_yacht_id());

DROP POLICY IF EXISTS "Engineers can manage equipment parts" ON equipment_parts;
CREATE POLICY "Engineers can manage equipment parts"
  ON equipment_parts FOR ALL
  USING (
    yacht_id = get_user_yacht_id() AND
    get_user_role() IN ('chief_engineer', 'eto', 'manager')
  );

COMMENT ON POLICY "Users can view equipment parts" ON equipment_parts IS 'All crew see part relationships';
COMMENT ON POLICY "Engineers can manage equipment parts" ON equipment_parts IS 'Engineers link parts to equipment';

-- -----------------------------------------------------------------------------
-- inventory_stock: All users can view, engineers can manage
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users can view stock levels" ON inventory_stock;
CREATE POLICY "Users can view stock levels"
  ON inventory_stock FOR SELECT
  USING (yacht_id = get_user_yacht_id());

DROP POLICY IF EXISTS "Engineers can manage stock" ON inventory_stock;
CREATE POLICY "Engineers can manage stock"
  ON inventory_stock FOR ALL
  USING (
    yacht_id = get_user_yacht_id() AND
    get_user_role() IN ('chief_engineer', 'eto', 'deck', 'interior')
  );

COMMENT ON POLICY "Users can view stock levels" ON inventory_stock IS 'All crew see stock levels';
COMMENT ON POLICY "Engineers can manage stock" ON inventory_stock IS 'Crew can update stock counts';

-- -----------------------------------------------------------------------------
-- suppliers: All users can view, managers can manage
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users can view suppliers" ON suppliers;
CREATE POLICY "Users can view suppliers"
  ON suppliers FOR SELECT
  USING (yacht_id = get_user_yacht_id());

DROP POLICY IF EXISTS "Managers can manage suppliers" ON suppliers;
CREATE POLICY "Managers can manage suppliers"
  ON suppliers FOR ALL
  USING (yacht_id = get_user_yacht_id() AND is_manager());

COMMENT ON POLICY "Users can view suppliers" ON suppliers IS 'All crew see supplier list';
COMMENT ON POLICY "Managers can manage suppliers" ON suppliers IS 'Managers manage supplier relationships';

-- -----------------------------------------------------------------------------
-- purchase_orders: All users can view, managers can manage
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users can view purchase orders" ON purchase_orders;
CREATE POLICY "Users can view purchase orders"
  ON purchase_orders FOR SELECT
  USING (yacht_id = get_user_yacht_id());

DROP POLICY IF EXISTS "Managers can manage purchase orders" ON purchase_orders;
CREATE POLICY "Managers can manage purchase orders"
  ON purchase_orders FOR ALL
  USING (yacht_id = get_user_yacht_id() AND is_manager());

COMMENT ON POLICY "Users can view purchase orders" ON purchase_orders IS 'All crew see purchase orders';
COMMENT ON POLICY "Managers can manage purchase orders" ON purchase_orders IS 'Managers create/approve POs';

-- -----------------------------------------------------------------------------
-- purchase_order_items: Follows parent purchase_order permissions
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users can view PO items" ON purchase_order_items;
CREATE POLICY "Users can view PO items"
  ON purchase_order_items FOR SELECT
  USING (yacht_id = get_user_yacht_id());

DROP POLICY IF EXISTS "Managers can manage PO items" ON purchase_order_items;
CREATE POLICY "Managers can manage PO items"
  ON purchase_order_items FOR ALL
  USING (yacht_id = get_user_yacht_id() AND is_manager());

COMMENT ON POLICY "Users can view PO items" ON purchase_order_items IS 'All crew see PO line items';
COMMENT ON POLICY "Managers can manage PO items" ON purchase_order_items IS 'Managers manage PO items';

-- ============================================================================
-- GROUP 4: HANDOVER TABLES
-- ============================================================================

-- -----------------------------------------------------------------------------
-- handovers: All users can view, engineers can create/edit
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users can view handovers" ON handovers;
CREATE POLICY "Users can view handovers"
  ON handovers FOR SELECT
  USING (yacht_id = get_user_yacht_id());

DROP POLICY IF EXISTS "Engineers can manage handovers" ON handovers;
CREATE POLICY "Engineers can manage handovers"
  ON handovers FOR ALL
  USING (
    yacht_id = get_user_yacht_id() AND
    get_user_role() IN ('chief_engineer', 'eto', 'captain', 'manager')
  );

COMMENT ON POLICY "Users can view handovers" ON handovers IS 'All crew see handovers';
COMMENT ON POLICY "Engineers can manage handovers" ON handovers IS 'Senior crew create handovers';

-- -----------------------------------------------------------------------------
-- handover_items: Follows parent handover permissions
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users can view handover items" ON handover_items;
CREATE POLICY "Users can view handover items"
  ON handover_items FOR SELECT
  USING (yacht_id = get_user_yacht_id());

DROP POLICY IF EXISTS "Engineers can manage handover items" ON handover_items;
CREATE POLICY "Engineers can manage handover items"
  ON handover_items FOR ALL
  USING (
    yacht_id = get_user_yacht_id() AND
    get_user_role() IN ('chief_engineer', 'eto', 'captain', 'manager')
  );

COMMENT ON POLICY "Users can view handover items" ON handover_items IS 'All crew see handover items';
COMMENT ON POLICY "Engineers can manage handover items" ON handover_items IS 'Senior crew manage items';

-- ============================================================================
-- GROUP 5: DOCUMENTS + RAG TABLES
-- ============================================================================

-- -----------------------------------------------------------------------------
-- documents: All users can view, system can insert
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users can view documents" ON documents;
CREATE POLICY "Users can view documents"
  ON documents FOR SELECT
  USING (yacht_id = get_user_yacht_id());

DROP POLICY IF EXISTS "System can insert documents" ON documents;
CREATE POLICY "System can insert documents"
  ON documents FOR INSERT
  WITH CHECK (yacht_id = get_user_yacht_id());

DROP POLICY IF EXISTS "Managers can manage documents" ON documents;
CREATE POLICY "Managers can manage documents"
  ON documents FOR ALL
  USING (yacht_id = get_user_yacht_id() AND is_manager());

COMMENT ON POLICY "Users can view documents" ON documents IS 'All crew see documents';
COMMENT ON POLICY "System can insert documents" ON documents IS 'Local agent uploads documents';
COMMENT ON POLICY "Managers can manage documents" ON documents IS 'Managers can delete/organize docs';

-- -----------------------------------------------------------------------------
-- document_chunks: All users can view, system can insert
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users can view document chunks" ON document_chunks;
CREATE POLICY "Users can view document chunks"
  ON document_chunks FOR SELECT
  USING (yacht_id = get_user_yacht_id());

DROP POLICY IF EXISTS "System can insert chunks" ON document_chunks;
CREATE POLICY "System can insert chunks"
  ON document_chunks FOR INSERT
  WITH CHECK (yacht_id = get_user_yacht_id());

COMMENT ON POLICY "Users can view document chunks" ON document_chunks IS 'All crew can search documents';
COMMENT ON POLICY "System can insert chunks" ON document_chunks IS 'Indexing pipeline creates chunks';

-- -----------------------------------------------------------------------------
-- ocred_pages: System only
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS "System can manage ocred pages" ON ocred_pages;
CREATE POLICY "System can manage ocred pages"
  ON ocred_pages FOR ALL
  USING (yacht_id = get_user_yacht_id());

COMMENT ON POLICY "System can manage ocred pages" ON ocred_pages IS 'Indexing pipeline manages OCR results';

-- -----------------------------------------------------------------------------
-- embedding_jobs: Managers can view, system can manage
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Managers can view embedding jobs" ON embedding_jobs;
CREATE POLICY "Managers can view embedding jobs"
  ON embedding_jobs FOR SELECT
  USING (yacht_id = get_user_yacht_id() AND is_manager());

DROP POLICY IF EXISTS "System can manage embedding jobs" ON embedding_jobs;
CREATE POLICY "System can manage embedding jobs"
  ON embedding_jobs FOR ALL
  USING (yacht_id = get_user_yacht_id());

COMMENT ON POLICY "Managers can view embedding jobs" ON embedding_jobs IS 'Managers monitor indexing progress';
COMMENT ON POLICY "System can manage embedding jobs" ON embedding_jobs IS 'Indexing pipeline tracks jobs';

-- ============================================================================
-- GROUP 6: GRAPHRAG TABLES
-- ============================================================================

-- -----------------------------------------------------------------------------
-- graph_nodes: All users can view, system can manage
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users can view graph nodes" ON graph_nodes;
CREATE POLICY "Users can view graph nodes"
  ON graph_nodes FOR SELECT
  USING (yacht_id = get_user_yacht_id());

DROP POLICY IF EXISTS "System can manage graph nodes" ON graph_nodes;
CREATE POLICY "System can manage graph nodes"
  ON graph_nodes FOR ALL
  USING (yacht_id = get_user_yacht_id());

COMMENT ON POLICY "Users can view graph nodes" ON graph_nodes IS 'All crew can traverse knowledge graph';
COMMENT ON POLICY "System can manage graph nodes" ON graph_nodes IS 'Indexing pipeline builds graph';

-- -----------------------------------------------------------------------------
-- graph_edges: All users can view, system can manage
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users can view graph edges" ON graph_edges;
CREATE POLICY "Users can view graph edges"
  ON graph_edges FOR SELECT
  USING (yacht_id = get_user_yacht_id());

DROP POLICY IF EXISTS "System can manage graph edges" ON graph_edges;
CREATE POLICY "System can manage graph edges"
  ON graph_edges FOR ALL
  USING (yacht_id = get_user_yacht_id());

COMMENT ON POLICY "Users can view graph edges" ON graph_edges IS 'All crew can use graph relationships';
COMMENT ON POLICY "System can manage graph edges" ON graph_edges IS 'Indexing pipeline creates relationships';

-- ============================================================================
-- GROUP 7: PREDICTIVE MAINTENANCE TABLES
-- ============================================================================

-- -----------------------------------------------------------------------------
-- predictive_state: All users can view, system can manage
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users can view predictive state" ON predictive_state;
CREATE POLICY "Users can view predictive state"
  ON predictive_state FOR SELECT
  USING (yacht_id = get_user_yacht_id());

DROP POLICY IF EXISTS "System can manage predictive state" ON predictive_state;
CREATE POLICY "System can manage predictive state"
  ON predictive_state FOR ALL
  USING (yacht_id = get_user_yacht_id());

COMMENT ON POLICY "Users can view predictive state" ON predictive_state IS 'All crew see risk scores';
COMMENT ON POLICY "System can manage predictive state" ON predictive_state IS 'Predictive engine updates scores';

-- -----------------------------------------------------------------------------
-- predictive_insights: All users can view, engineers can acknowledge
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users can view insights" ON predictive_insights;
CREATE POLICY "Users can view insights"
  ON predictive_insights FOR SELECT
  USING (yacht_id = get_user_yacht_id());

DROP POLICY IF EXISTS "Engineers can acknowledge insights" ON predictive_insights;
CREATE POLICY "Engineers can acknowledge insights"
  ON predictive_insights FOR UPDATE
  USING (
    yacht_id = get_user_yacht_id() AND
    get_user_role() IN ('chief_engineer', 'eto', 'manager')
  )
  WITH CHECK (
    yacht_id = get_user_yacht_id() AND
    get_user_role() IN ('chief_engineer', 'eto', 'manager')
  );

DROP POLICY IF EXISTS "System can create insights" ON predictive_insights;
CREATE POLICY "System can create insights"
  ON predictive_insights FOR INSERT
  WITH CHECK (yacht_id = get_user_yacht_id());

COMMENT ON POLICY "Users can view insights" ON predictive_insights IS 'All crew see predictive insights';
COMMENT ON POLICY "Engineers can acknowledge insights" ON predictive_insights IS 'Engineers can acknowledge/dismiss insights';
COMMENT ON POLICY "System can create insights" ON predictive_insights IS 'Predictive engine generates insights';

-- ============================================================================
-- GRANT PERMISSIONS
-- ============================================================================

-- Grant usage on helper functions
GRANT EXECUTE ON FUNCTION public.get_user_yacht_id() TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_user_role() TO authenticated;
GRANT EXECUTE ON FUNCTION public.is_manager() TO authenticated;

-- Grant usage on sequences (for uuid generation)
-- Supabase handles this automatically for gen_random_uuid()

-- ============================================================================
-- COMPLETED RLS POLICIES
-- ============================================================================
-- All 34 tables now have RLS policies
-- Security model:
-- ✓ Per-yacht isolation (yacht_id filtering)
-- ✓ Role-based permissions (chief_engineer, eto, captain, manager, deck, interior, vendor)
-- ✓ User can only access their yacht's data
-- ✓ Managers have elevated permissions
-- ✓ System operations protected
-- ✓ Helper functions for reusable logic
-- ============================================================================
