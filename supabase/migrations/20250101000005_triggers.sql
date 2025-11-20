-- ============================================================================
-- Migration: Database Triggers
-- Version: 20250101000005
-- Description: Automated triggers for auth, timestamps, and audit logging
-- ============================================================================

-- ============================================================================
-- TRIGGER 1: Auto-create business users from Supabase Auth
-- ============================================================================

-- Function to create business user when auth user is created
CREATE OR REPLACE FUNCTION public.handle_new_auth_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  user_yacht_id UUID;
  user_name TEXT;
  user_role TEXT;
BEGIN
  -- Extract metadata from auth.users.raw_user_meta_data
  -- Expected format: {"yacht_id": "uuid", "name": "John Doe", "role": "engineer"}
  user_yacht_id := (NEW.raw_user_meta_data->>'yacht_id')::uuid;
  user_name := COALESCE(NEW.raw_user_meta_data->>'name', NEW.email);
  user_role := COALESCE(NEW.raw_user_meta_data->>'role', 'deck');

  -- Validate yacht_id exists
  IF user_yacht_id IS NULL THEN
    RAISE EXCEPTION 'yacht_id is required in user metadata';
  END IF;

  IF NOT EXISTS (SELECT 1 FROM public.yachts WHERE id = user_yacht_id) THEN
    RAISE EXCEPTION 'Invalid yacht_id: %', user_yacht_id;
  END IF;

  -- Validate role
  IF user_role NOT IN ('chief_engineer', 'eto', 'captain', 'manager', 'deck', 'interior', 'vendor') THEN
    RAISE EXCEPTION 'Invalid role: %', user_role;
  END IF;

  -- Create business user record
  INSERT INTO public.users (
    auth_user_id,
    yacht_id,
    email,
    name,
    role,
    avatar_url,
    phone,
    metadata
  ) VALUES (
    NEW.id,
    user_yacht_id,
    NEW.email,
    user_name,
    user_role,
    NEW.raw_user_meta_data->>'avatar_url',
    NEW.raw_user_meta_data->>'phone',
    COALESCE(NEW.raw_user_meta_data, '{}'::jsonb)
  );

  RETURN NEW;
END;
$$;

-- Create trigger on auth.users
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_new_auth_user();

COMMENT ON FUNCTION public.handle_new_auth_user IS 'Auto-create business user when Supabase Auth user is created. Requires yacht_id, name, role in raw_user_meta_data';

-- ============================================================================
-- TRIGGER 2: Auto-update updated_at timestamps
-- ============================================================================

-- Generic function to update updated_at column
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

-- Apply to all tables with updated_at column
-- Group 1: Core tables
CREATE TRIGGER set_updated_at BEFORE UPDATE ON yachts FOR EACH ROW EXECUTE FUNCTION handle_updated_at();
CREATE TRIGGER set_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION handle_updated_at();
CREATE TRIGGER set_updated_at BEFORE UPDATE ON agents FOR EACH ROW EXECUTE FUNCTION handle_updated_at();
CREATE TRIGGER set_updated_at BEFORE UPDATE ON api_keys FOR EACH ROW EXECUTE FUNCTION handle_updated_at();

-- Group 2: PMS tables
CREATE TRIGGER set_updated_at BEFORE UPDATE ON equipment FOR EACH ROW EXECUTE FUNCTION handle_updated_at();
CREATE TRIGGER set_updated_at BEFORE UPDATE ON work_orders FOR EACH ROW EXECUTE FUNCTION handle_updated_at();
CREATE TRIGGER set_updated_at BEFORE UPDATE ON faults FOR EACH ROW EXECUTE FUNCTION handle_updated_at();
CREATE TRIGGER set_updated_at BEFORE UPDATE ON hours_of_rest FOR EACH ROW EXECUTE FUNCTION handle_updated_at();

-- Group 3: Inventory tables
CREATE TRIGGER set_updated_at BEFORE UPDATE ON parts FOR EACH ROW EXECUTE FUNCTION handle_updated_at();
CREATE TRIGGER set_updated_at BEFORE UPDATE ON inventory_stock FOR EACH ROW EXECUTE FUNCTION handle_updated_at();
CREATE TRIGGER set_updated_at BEFORE UPDATE ON suppliers FOR EACH ROW EXECUTE FUNCTION handle_updated_at();
CREATE TRIGGER set_updated_at BEFORE UPDATE ON purchase_orders FOR EACH ROW EXECUTE FUNCTION handle_updated_at();

-- Group 4: Handover tables
CREATE TRIGGER set_updated_at BEFORE UPDATE ON handovers FOR EACH ROW EXECUTE FUNCTION handle_updated_at();

-- Group 5: Documents
CREATE TRIGGER set_updated_at BEFORE UPDATE ON documents FOR EACH ROW EXECUTE FUNCTION handle_updated_at();
CREATE TRIGGER set_updated_at BEFORE UPDATE ON embedding_jobs FOR EACH ROW EXECUTE FUNCTION handle_updated_at();

-- Group 6: GraphRAG
CREATE TRIGGER set_updated_at BEFORE UPDATE ON graph_nodes FOR EACH ROW EXECUTE FUNCTION handle_updated_at();

-- Group 7: Predictive
CREATE TRIGGER set_updated_at BEFORE UPDATE ON predictive_state FOR EACH ROW EXECUTE FUNCTION handle_updated_at();
CREATE TRIGGER set_updated_at BEFORE UPDATE ON predictive_insights FOR EACH ROW EXECUTE FUNCTION handle_updated_at();

COMMENT ON FUNCTION public.handle_updated_at IS 'Auto-update updated_at timestamp on row modifications';

-- ============================================================================
-- TRIGGER 3: Audit logging for critical tables
-- ============================================================================

-- Function to log changes to event_logs
CREATE OR REPLACE FUNCTION public.log_audit_event()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  user_yacht_id UUID;
  current_user_id UUID;
BEGIN
  -- Get current user's info
  SELECT id, yacht_id INTO current_user_id, user_yacht_id
  FROM public.users
  WHERE auth_user_id = auth.uid()
  LIMIT 1;

  -- For INSERT operations
  IF (TG_OP = 'INSERT') THEN
    INSERT INTO public.event_logs (
      yacht_id,
      user_id,
      event_type,
      table_name,
      record_id,
      action,
      new_data,
      metadata
    ) VALUES (
      COALESCE(NEW.yacht_id, user_yacht_id),
      current_user_id,
      TG_TABLE_NAME || '_created',
      TG_TABLE_NAME,
      NEW.id,
      'INSERT',
      to_jsonb(NEW),
      jsonb_build_object('triggered_at', now(), 'operation', TG_OP)
    );
    RETURN NEW;
  END IF;

  -- For UPDATE operations
  IF (TG_OP = 'UPDATE') THEN
    INSERT INTO public.event_logs (
      yacht_id,
      user_id,
      event_type,
      table_name,
      record_id,
      action,
      old_data,
      new_data,
      metadata
    ) VALUES (
      COALESCE(NEW.yacht_id, user_yacht_id),
      current_user_id,
      TG_TABLE_NAME || '_updated',
      TG_TABLE_NAME,
      NEW.id,
      'UPDATE',
      to_jsonb(OLD),
      to_jsonb(NEW),
      jsonb_build_object('triggered_at', now(), 'operation', TG_OP)
    );
    RETURN NEW;
  END IF;

  -- For DELETE operations
  IF (TG_OP = 'DELETE') THEN
    INSERT INTO public.event_logs (
      yacht_id,
      user_id,
      event_type,
      table_name,
      record_id,
      action,
      old_data,
      metadata
    ) VALUES (
      COALESCE(OLD.yacht_id, user_yacht_id),
      current_user_id,
      TG_TABLE_NAME || '_deleted',
      TG_TABLE_NAME,
      OLD.id,
      'DELETE',
      to_jsonb(OLD),
      jsonb_build_object('triggered_at', now(), 'operation', TG_OP)
    );
    RETURN OLD;
  END IF;

  RETURN NULL;
END;
$$;

-- Apply audit logging to critical tables
-- Note: Not all tables need audit logging (e.g., event_logs itself, search_queries)

-- PMS critical tables
CREATE TRIGGER audit_log AFTER INSERT OR UPDATE OR DELETE ON work_orders FOR EACH ROW EXECUTE FUNCTION log_audit_event();
CREATE TRIGGER audit_log AFTER INSERT OR UPDATE OR DELETE ON faults FOR EACH ROW EXECUTE FUNCTION log_audit_event();

-- Inventory critical tables
CREATE TRIGGER audit_log AFTER INSERT OR UPDATE OR DELETE ON purchase_orders FOR EACH ROW EXECUTE FUNCTION log_audit_event();
CREATE TRIGGER audit_log AFTER INSERT OR DELETE ON inventory_stock FOR EACH ROW EXECUTE FUNCTION log_audit_event();

-- User/Auth critical tables
CREATE TRIGGER audit_log AFTER INSERT OR UPDATE OR DELETE ON users FOR EACH ROW EXECUTE FUNCTION log_audit_event();
CREATE TRIGGER audit_log AFTER INSERT OR UPDATE OR DELETE ON agents FOR EACH ROW EXECUTE FUNCTION log_audit_event();
CREATE TRIGGER audit_log AFTER INSERT OR UPDATE OR DELETE ON api_keys FOR EACH ROW EXECUTE FUNCTION log_audit_event();

-- Equipment critical tables
CREATE TRIGGER audit_log AFTER INSERT OR UPDATE OR DELETE ON equipment FOR EACH ROW EXECUTE FUNCTION log_audit_event();

COMMENT ON FUNCTION public.log_audit_event IS 'Automatically log changes to critical tables in event_logs';

-- ============================================================================
-- TRIGGER 4: Work order status validation
-- ============================================================================

CREATE OR REPLACE FUNCTION public.validate_work_order_status()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  -- When status changes to 'in_progress', set actual_start if not set
  IF NEW.status = 'in_progress' AND OLD.status != 'in_progress' AND NEW.actual_start IS NULL THEN
    NEW.actual_start = now();
  END IF;

  -- When status changes to 'completed', set actual_end if not set
  IF NEW.status = 'completed' AND OLD.status != 'completed' AND NEW.actual_end IS NULL THEN
    NEW.actual_end = now();
  END IF;

  -- Prevent reopening completed work orders (business rule)
  IF OLD.status = 'completed' AND NEW.status != 'completed' THEN
    RAISE EXCEPTION 'Cannot reopen completed work order. Create a new work order instead.';
  END IF;

  RETURN NEW;
END;
$$;

CREATE TRIGGER validate_status BEFORE UPDATE ON work_orders FOR EACH ROW EXECUTE FUNCTION validate_work_order_status();

COMMENT ON FUNCTION public.validate_work_order_status IS 'Enforce business rules for work order status transitions';

-- ============================================================================
-- TRIGGER 5: Equipment hours tracking
-- ============================================================================

CREATE OR REPLACE FUNCTION public.update_equipment_hours()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  -- When work order is completed, add actual hours to equipment
  IF NEW.status = 'completed' AND OLD.status != 'completed' AND NEW.equipment_id IS NOT NULL AND NEW.actual_hours IS NOT NULL THEN
    UPDATE equipment
    SET
      current_hours = current_hours + NEW.actual_hours,
      last_maintenance_at = now(),
      next_maintenance_due = CASE
        WHEN maintenance_interval_hours IS NOT NULL
        THEN now() + (maintenance_interval_hours || ' hours')::interval
        ELSE next_maintenance_due
      END
    WHERE id = NEW.equipment_id;
  END IF;

  RETURN NEW;
END;
$$;

CREATE TRIGGER update_hours AFTER UPDATE ON work_orders FOR EACH ROW EXECUTE FUNCTION update_equipment_hours();

COMMENT ON FUNCTION public.update_equipment_hours IS 'Update equipment hours when work orders are completed';

-- ============================================================================
-- TRIGGER 6: Auto-create embedding jobs when documents are uploaded
-- ============================================================================

CREATE OR REPLACE FUNCTION public.create_embedding_job()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  -- Only create job for newly inserted documents that haven't been indexed
  IF NEW.indexed = false THEN
    INSERT INTO embedding_jobs (yacht_id, document_id, status, chunks_total, chunks_processed)
    VALUES (NEW.yacht_id, NEW.id, 'pending', 0, 0);
  END IF;

  RETURN NEW;
END;
$$;

CREATE TRIGGER on_document_inserted AFTER INSERT ON documents FOR EACH ROW EXECUTE FUNCTION create_embedding_job();

COMMENT ON FUNCTION public.create_embedding_job IS 'Automatically create embedding job when document is uploaded';

-- ============================================================================
-- TRIGGER 7: Mark document as indexed when embedding job completes
-- ============================================================================

CREATE OR REPLACE FUNCTION public.mark_document_indexed()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  -- When embedding job completes successfully, mark document as indexed
  IF NEW.status = 'completed' AND OLD.status != 'completed' THEN
    UPDATE documents
    SET
      indexed = true,
      indexed_at = now()
    WHERE id = NEW.document_id;
  END IF;

  RETURN NEW;
END;
$$;

CREATE TRIGGER on_job_completed AFTER UPDATE ON embedding_jobs FOR EACH ROW EXECUTE FUNCTION mark_document_indexed();

COMMENT ON FUNCTION public.mark_document_indexed IS 'Mark document as indexed when embedding job completes';

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- List all triggers
-- SELECT trigger_name, event_object_table, action_statement
-- FROM information_schema.triggers
-- WHERE trigger_schema = 'public'
-- ORDER BY event_object_table, trigger_name;
