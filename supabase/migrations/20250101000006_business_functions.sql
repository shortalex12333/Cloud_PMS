-- ============================================================================
-- Migration: Business Logic Functions
-- Version: 20250101000006
-- Description: Helper functions for common business operations
-- ============================================================================

-- ============================================================================
-- WORK ORDER FUNCTIONS
-- ============================================================================

-- Function to create work order with history entry
CREATE OR REPLACE FUNCTION public.create_work_order(
  p_equipment_id UUID,
  p_title TEXT,
  p_description TEXT,
  p_work_type TEXT,
  p_priority TEXT DEFAULT 'medium',
  p_assigned_to UUID DEFAULT NULL,
  p_scheduled_start TIMESTAMPTZ DEFAULT NULL,
  p_scheduled_end TIMESTAMPTZ DEFAULT NULL
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  user_yacht_id UUID;
  current_user_id UUID;
  new_work_order_id UUID;
BEGIN
  -- Get current user info
  SELECT id, yacht_id INTO current_user_id, user_yacht_id
  FROM public.users
  WHERE auth_user_id = auth.uid()
  LIMIT 1;

  IF user_yacht_id IS NULL THEN
    RAISE EXCEPTION 'User not found or not authenticated';
  END IF;

  -- Create work order
  INSERT INTO work_orders (
    yacht_id,
    equipment_id,
    title,
    description,
    work_type,
    priority,
    status,
    assigned_to,
    created_by,
    scheduled_start,
    scheduled_end
  ) VALUES (
    user_yacht_id,
    p_equipment_id,
    p_title,
    p_description,
    p_work_type,
    p_priority,
    'open',
    p_assigned_to,
    current_user_id,
    p_scheduled_start,
    p_scheduled_end
  ) RETURNING id INTO new_work_order_id;

  -- Create initial history entry
  INSERT INTO work_order_history (
    yacht_id,
    work_order_id,
    changed_by,
    field_changed,
    new_value,
    notes
  ) VALUES (
    user_yacht_id,
    new_work_order_id,
    current_user_id,
    'status',
    'open',
    'Work order created'
  );

  RETURN new_work_order_id;
END;
$$;

COMMENT ON FUNCTION public.create_work_order IS 'Create work order with automatic history tracking';
GRANT EXECUTE ON FUNCTION public.create_work_order TO authenticated;

-- ============================================================================
-- Function to update work order status with history
-- ============================================================================

CREATE OR REPLACE FUNCTION public.update_work_order_status(
  p_work_order_id UUID,
  p_new_status TEXT,
  p_notes TEXT DEFAULT NULL
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  user_yacht_id UUID;
  current_user_id UUID;
  old_status TEXT;
BEGIN
  -- Get current user info
  SELECT id, yacht_id INTO current_user_id, user_yacht_id
  FROM public.users
  WHERE auth_user_id = auth.uid()
  LIMIT 1;

  IF user_yacht_id IS NULL THEN
    RAISE EXCEPTION 'User not found or not authenticated';
  END IF;

  -- Get old status
  SELECT status INTO old_status
  FROM work_orders
  WHERE id = p_work_order_id AND yacht_id = user_yacht_id;

  IF old_status IS NULL THEN
    RAISE EXCEPTION 'Work order not found';
  END IF;

  -- Update status
  UPDATE work_orders
  SET status = p_new_status
  WHERE id = p_work_order_id AND yacht_id = user_yacht_id;

  -- Log history
  INSERT INTO work_order_history (
    yacht_id,
    work_order_id,
    changed_by,
    field_changed,
    old_value,
    new_value,
    notes
  ) VALUES (
    user_yacht_id,
    p_work_order_id,
    current_user_id,
    'status',
    old_status,
    p_new_status,
    p_notes
  );

  RETURN TRUE;
END;
$$;

COMMENT ON FUNCTION public.update_work_order_status IS 'Update work order status with automatic history logging';
GRANT EXECUTE ON FUNCTION public.update_work_order_status TO authenticated;

-- ============================================================================
-- INVENTORY FUNCTIONS
-- ============================================================================

-- Function to adjust inventory stock
CREATE OR REPLACE FUNCTION public.adjust_inventory_stock(
  p_part_id UUID,
  p_location TEXT,
  p_quantity_change INTEGER,
  p_notes TEXT DEFAULT NULL
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  user_yacht_id UUID;
  current_user_id UUID;
  current_quantity INTEGER;
  new_quantity INTEGER;
BEGIN
  -- Get current user info
  SELECT id, yacht_id INTO current_user_id, user_yacht_id
  FROM public.users
  WHERE auth_user_id = auth.uid()
  LIMIT 1;

  IF user_yacht_id IS NULL THEN
    RAISE EXCEPTION 'User not found or not authenticated';
  END IF;

  -- Get current quantity
  SELECT quantity_on_hand INTO current_quantity
  FROM inventory_stock
  WHERE part_id = p_part_id AND location = p_location AND yacht_id = user_yacht_id;

  IF current_quantity IS NULL THEN
    -- Create new stock record
    INSERT INTO inventory_stock (
      yacht_id,
      part_id,
      location,
      quantity_on_hand,
      last_counted_by,
      last_counted_at,
      notes
    ) VALUES (
      user_yacht_id,
      p_part_id,
      p_location,
      GREATEST(p_quantity_change, 0),
      current_user_id,
      now(),
      p_notes
    );
  ELSE
    -- Update existing stock record
    new_quantity := current_quantity + p_quantity_change;

    IF new_quantity < 0 THEN
      RAISE EXCEPTION 'Insufficient stock. Current: %, Requested: %', current_quantity, ABS(p_quantity_change);
    END IF;

    UPDATE inventory_stock
    SET
      quantity_on_hand = new_quantity,
      last_counted_by = current_user_id,
      last_counted_at = now(),
      notes = COALESCE(p_notes, notes)
    WHERE part_id = p_part_id AND location = p_location AND yacht_id = user_yacht_id;
  END IF;

  RETURN TRUE;
END;
$$;

COMMENT ON FUNCTION public.adjust_inventory_stock IS 'Adjust inventory stock levels with validation';
GRANT EXECUTE ON FUNCTION public.adjust_inventory_stock TO authenticated;

-- ============================================================================
-- EQUIPMENT FUNCTIONS
-- ============================================================================

-- Function to get equipment health score
CREATE OR REPLACE FUNCTION public.get_equipment_health(
  p_equipment_id UUID
)
RETURNS TABLE (
  equipment_name TEXT,
  risk_score NUMERIC,
  maintenance_due_in_days INTEGER,
  open_faults INTEGER,
  open_work_orders INTEGER,
  health_status TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
AS $$
DECLARE
  user_yacht_id UUID;
BEGIN
  -- Get current user's yacht_id
  SELECT yacht_id INTO user_yacht_id
  FROM public.users
  WHERE auth_user_id = auth.uid()
  LIMIT 1;

  IF user_yacht_id IS NULL THEN
    RETURN;
  END IF;

  RETURN QUERY
  SELECT
    e.name AS equipment_name,
    COALESCE(ps.risk_score, 0) AS risk_score,
    EXTRACT(DAY FROM (e.next_maintenance_due - now()))::INTEGER AS maintenance_due_in_days,
    (SELECT COUNT(*)::INTEGER FROM faults WHERE equipment_id = e.id AND status = 'open') AS open_faults,
    (SELECT COUNT(*)::INTEGER FROM work_orders WHERE equipment_id = e.id AND status IN ('open', 'in_progress')) AS open_work_orders,
    CASE
      WHEN COALESCE(ps.risk_score, 0) > 0.8 THEN 'critical'
      WHEN COALESCE(ps.risk_score, 0) > 0.6 THEN 'warning'
      WHEN COALESCE(ps.risk_score, 0) > 0.4 THEN 'caution'
      ELSE 'good'
    END AS health_status
  FROM equipment e
  LEFT JOIN predictive_state ps ON e.id = ps.equipment_id
  WHERE e.id = p_equipment_id AND e.yacht_id = user_yacht_id;
END;
$$;

COMMENT ON FUNCTION public.get_equipment_health IS 'Get comprehensive equipment health metrics';
GRANT EXECUTE ON FUNCTION public.get_equipment_health TO authenticated;

-- ============================================================================
-- DASHBOARD FUNCTIONS
-- ============================================================================

-- Function to get yacht statistics
CREATE OR REPLACE FUNCTION public.get_yacht_stats()
RETURNS TABLE (
  total_equipment INTEGER,
  operational_equipment INTEGER,
  equipment_in_fault INTEGER,
  open_work_orders INTEGER,
  overdue_work_orders INTEGER,
  critical_faults INTEGER,
  total_documents INTEGER,
  indexed_documents INTEGER,
  crew_count INTEGER
)
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
AS $$
DECLARE
  user_yacht_id UUID;
BEGIN
  -- Get current user's yacht_id
  SELECT yacht_id INTO user_yacht_id
  FROM public.users
  WHERE auth_user_id = auth.uid()
  LIMIT 1;

  IF user_yacht_id IS NULL THEN
    RETURN;
  END IF;

  RETURN QUERY
  SELECT
    (SELECT COUNT(*)::INTEGER FROM equipment WHERE yacht_id = user_yacht_id) AS total_equipment,
    (SELECT COUNT(*)::INTEGER FROM equipment WHERE yacht_id = user_yacht_id AND status = 'operational') AS operational_equipment,
    (SELECT COUNT(*)::INTEGER FROM equipment WHERE yacht_id = user_yacht_id AND status = 'fault') AS equipment_in_fault,
    (SELECT COUNT(*)::INTEGER FROM work_orders WHERE yacht_id = user_yacht_id AND status IN ('open', 'in_progress')) AS open_work_orders,
    (SELECT COUNT(*)::INTEGER FROM work_orders WHERE yacht_id = user_yacht_id AND status IN ('open', 'in_progress') AND scheduled_end < now()) AS overdue_work_orders,
    (SELECT COUNT(*)::INTEGER FROM faults WHERE yacht_id = user_yacht_id AND status = 'open' AND severity = 'critical') AS critical_faults,
    (SELECT COUNT(*)::INTEGER FROM documents WHERE yacht_id = user_yacht_id) AS total_documents,
    (SELECT COUNT(*)::INTEGER FROM documents WHERE yacht_id = user_yacht_id AND indexed = true) AS indexed_documents,
    (SELECT COUNT(*)::INTEGER FROM users WHERE yacht_id = user_yacht_id) AS crew_count;
END;
$$;

COMMENT ON FUNCTION public.get_yacht_stats IS 'Get yacht-wide statistics for dashboard';
GRANT EXECUTE ON FUNCTION public.get_yacht_stats TO authenticated;

-- ============================================================================
-- VALIDATION FUNCTIONS
-- ============================================================================

-- Function to validate bcrypt hash format
CREATE OR REPLACE FUNCTION public.is_valid_bcrypt_hash(hash TEXT)
RETURNS BOOLEAN
LANGUAGE plpgsql
IMMUTABLE
AS $$
BEGIN
  RETURN hash ~ '^\$2[aby]\$[0-9]{2}\$[./A-Za-z0-9]{53}$';
END;
$$;

COMMENT ON FUNCTION public.is_valid_bcrypt_hash IS 'Validate bcrypt hash format';
GRANT EXECUTE ON FUNCTION public.is_valid_bcrypt_hash TO authenticated;

-- Function to validate SHA256 hash format
CREATE OR REPLACE FUNCTION public.is_valid_sha256_hash(hash TEXT)
RETURNS BOOLEAN
LANGUAGE plpgsql
IMMUTABLE
AS $$
BEGIN
  RETURN hash ~ '^[a-f0-9]{64}$';
END;
$$;

COMMENT ON FUNCTION public.is_valid_sha256_hash IS 'Validate SHA256 hash format';
GRANT EXECUTE ON FUNCTION public.is_valid_sha256_hash TO authenticated;

-- ============================================================================
-- GRAPH TRAVERSAL FUNCTIONS
-- ============================================================================

-- Function to traverse knowledge graph
CREATE OR REPLACE FUNCTION public.traverse_graph(
  p_start_node_id UUID,
  p_max_depth INTEGER DEFAULT 2,
  p_relationship_types TEXT[] DEFAULT NULL
)
RETURNS TABLE (
  node_id UUID,
  entity_type TEXT,
  entity_name TEXT,
  depth INTEGER,
  path UUID[]
)
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
AS $$
DECLARE
  user_yacht_id UUID;
BEGIN
  -- Get current user's yacht_id
  SELECT yacht_id INTO user_yacht_id
  FROM public.users
  WHERE auth_user_id = auth.uid()
  LIMIT 1;

  IF user_yacht_id IS NULL THEN
    RETURN;
  END IF;

  -- Recursive graph traversal
  RETURN QUERY
  WITH RECURSIVE graph_traversal AS (
    -- Base case: start node
    SELECT
      gn.id AS node_id,
      gn.entity_type,
      gn.entity_name,
      0 AS depth,
      ARRAY[gn.id] AS path
    FROM graph_nodes gn
    WHERE gn.id = p_start_node_id AND gn.yacht_id = user_yacht_id

    UNION ALL

    -- Recursive case: follow edges
    SELECT
      gn.id AS node_id,
      gn.entity_type,
      gn.entity_name,
      gt.depth + 1 AS depth,
      gt.path || gn.id AS path
    FROM graph_traversal gt
    INNER JOIN graph_edges ge ON ge.from_node_id = gt.node_id
    INNER JOIN graph_nodes gn ON gn.id = ge.to_node_id
    WHERE
      gt.depth < p_max_depth
      AND NOT gn.id = ANY(gt.path)  -- Prevent cycles
      AND gn.yacht_id = user_yacht_id
      AND (p_relationship_types IS NULL OR ge.relationship_type = ANY(p_relationship_types))
  )
  SELECT * FROM graph_traversal
  ORDER BY depth, entity_name;
END;
$$;

COMMENT ON FUNCTION public.traverse_graph IS 'Traverse knowledge graph with max depth and relationship filtering';
GRANT EXECUTE ON FUNCTION public.traverse_graph TO authenticated;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- List all custom functions:
-- SELECT routine_name, routine_type
-- FROM information_schema.routines
-- WHERE routine_schema = 'public' AND routine_name NOT LIKE 'pg_%'
-- ORDER BY routine_name;
