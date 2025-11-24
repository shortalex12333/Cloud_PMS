-- ============================================
-- PREDICTIVE ENGINE MVP2 - DATABASE TRIGGERS
-- ============================================
-- These triggers fire events to n8n when data changes
-- Requires: pg_net extension for HTTP calls
-- ============================================

-- Enable pg_net extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS pg_net;

-- ============================================
-- CONFIGURATION
-- ============================================
-- Set the webhook URL (change in production)
DO $$
BEGIN
  PERFORM set_config('app.predictive_webhook_url',
    'https://api.celeste7.ai/webhook/internal/predictive-event',
    false);
END $$;

-- ============================================
-- 1. FAULTS TRIGGER
-- Fires on: INSERT (new fault)
-- ============================================
CREATE OR REPLACE FUNCTION notify_predictive_fault_created()
RETURNS TRIGGER AS $$
DECLARE
  webhook_url TEXT := 'https://api.celeste7.ai/webhook/internal/predictive-event';
BEGIN
  -- Only fire if equipment_id is present
  IF NEW.equipment_id IS NOT NULL THEN
    PERFORM net.http_post(
      url := webhook_url,
      headers := '{"Content-Type": "application/json"}'::jsonb,
      body := jsonb_build_object(
        'event', 'fault_created',
        'equipment_id', NEW.equipment_id,
        'yacht_id', NEW.yacht_id,
        'fault_id', NEW.id,
        'fault_code', NEW.fault_code,
        'severity', NEW.severity
      )::text
    );
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS trg_predictive_fault_created ON faults;
CREATE TRIGGER trg_predictive_fault_created
  AFTER INSERT ON faults
  FOR EACH ROW
  EXECUTE FUNCTION notify_predictive_fault_created();

-- ============================================
-- 2. FAULTS RESOLVED TRIGGER
-- Fires on: UPDATE (status → resolved)
-- ============================================
CREATE OR REPLACE FUNCTION notify_predictive_fault_resolved()
RETURNS TRIGGER AS $$
DECLARE
  webhook_url TEXT := 'https://api.celeste7.ai/webhook/internal/predictive-event';
BEGIN
  IF NEW.equipment_id IS NOT NULL
     AND OLD.status != 'resolved'
     AND NEW.status = 'resolved' THEN
    PERFORM net.http_post(
      url := webhook_url,
      headers := '{"Content-Type": "application/json"}'::jsonb,
      body := jsonb_build_object(
        'event', 'fault_resolved',
        'equipment_id', NEW.equipment_id,
        'yacht_id', NEW.yacht_id,
        'fault_id', NEW.id
      )::text
    );
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS trg_predictive_fault_resolved ON faults;
CREATE TRIGGER trg_predictive_fault_resolved
  AFTER UPDATE ON faults
  FOR EACH ROW
  EXECUTE FUNCTION notify_predictive_fault_resolved();

-- ============================================
-- 3. WORK ORDERS TRIGGER (INSERT)
-- Fires on: INSERT (new work order)
-- ============================================
CREATE OR REPLACE FUNCTION notify_predictive_wo_created()
RETURNS TRIGGER AS $$
DECLARE
  webhook_url TEXT := 'https://api.celeste7.ai/webhook/internal/predictive-event';
BEGIN
  IF NEW.equipment_id IS NOT NULL THEN
    PERFORM net.http_post(
      url := webhook_url,
      headers := '{"Content-Type": "application/json"}'::jsonb,
      body := jsonb_build_object(
        'event', 'wo_created',
        'equipment_id', NEW.equipment_id,
        'yacht_id', NEW.yacht_id,
        'work_order_id', NEW.id,
        'type', NEW.type
      )::text
    );
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS trg_predictive_wo_created ON work_orders;
CREATE TRIGGER trg_predictive_wo_created
  AFTER INSERT ON work_orders
  FOR EACH ROW
  EXECUTE FUNCTION notify_predictive_wo_created();

-- ============================================
-- 4. WORK ORDERS TRIGGER (UPDATE)
-- Fires on: UPDATE (status changes, overdue detection)
-- ============================================
CREATE OR REPLACE FUNCTION notify_predictive_wo_updated()
RETURNS TRIGGER AS $$
DECLARE
  webhook_url TEXT := 'https://api.celeste7.ai/webhook/internal/predictive-event';
  event_name TEXT;
BEGIN
  IF NEW.equipment_id IS NULL THEN
    RETURN NEW;
  END IF;

  -- Determine event type
  IF OLD.status != 'completed' AND NEW.status = 'completed' THEN
    event_name := 'wo_completed';
  ELSIF OLD.due_date >= CURRENT_DATE AND NEW.due_date < CURRENT_DATE THEN
    event_name := 'wo_overdue';
  ELSIF OLD.status IS DISTINCT FROM NEW.status THEN
    event_name := 'wo_updated';
  ELSE
    RETURN NEW; -- No relevant change
  END IF;

  PERFORM net.http_post(
    url := webhook_url,
    headers := '{"Content-Type": "application/json"}'::jsonb,
    body := jsonb_build_object(
      'event', event_name,
      'equipment_id', NEW.equipment_id,
      'yacht_id', NEW.yacht_id,
      'work_order_id', NEW.id,
      'old_status', OLD.status,
      'new_status', NEW.status
    )::text
  );

  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS trg_predictive_wo_updated ON work_orders;
CREATE TRIGGER trg_predictive_wo_updated
  AFTER UPDATE ON work_orders
  FOR EACH ROW
  EXECUTE FUNCTION notify_predictive_wo_updated();

-- ============================================
-- 5. NOTES TRIGGER
-- Fires on: INSERT (new note with equipment_id)
-- ============================================
CREATE OR REPLACE FUNCTION notify_predictive_note_added()
RETURNS TRIGGER AS $$
DECLARE
  webhook_url TEXT := 'https://api.celeste7.ai/webhook/internal/predictive-event';
BEGIN
  -- Only fire if equipment_id is present
  IF NEW.equipment_id IS NOT NULL THEN
    PERFORM net.http_post(
      url := webhook_url,
      headers := '{"Content-Type": "application/json"}'::jsonb,
      body := jsonb_build_object(
        'event', 'note_added',
        'equipment_id', NEW.equipment_id,
        'yacht_id', NEW.yacht_id,
        'note_id', NEW.id,
        'note_type', NEW.note_type
      )::text
    );
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS trg_predictive_note_added ON notes;
CREATE TRIGGER trg_predictive_note_added
  AFTER INSERT ON notes
  FOR EACH ROW
  EXECUTE FUNCTION notify_predictive_note_added();

-- ============================================
-- 6. PARTS USAGE TRIGGER
-- Fires on: UPDATE (quantity decreased)
-- ============================================
CREATE OR REPLACE FUNCTION notify_predictive_part_used()
RETURNS TRIGGER AS $$
DECLARE
  webhook_url TEXT := 'https://api.celeste7.ai/webhook/internal/predictive-event';
BEGIN
  -- Only fire if quantity decreased and equipment_id exists
  IF NEW.equipment_id IS NOT NULL
     AND NEW.quantity < OLD.quantity THEN
    PERFORM net.http_post(
      url := webhook_url,
      headers := '{"Content-Type": "application/json"}'::jsonb,
      body := jsonb_build_object(
        'event', 'part_used',
        'equipment_id', NEW.equipment_id,
        'yacht_id', NEW.yacht_id,
        'part_id', NEW.id,
        'quantity_used', OLD.quantity - NEW.quantity
      )::text
    );
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS trg_predictive_part_used ON parts;
CREATE TRIGGER trg_predictive_part_used
  AFTER UPDATE ON parts
  FOR EACH ROW
  EXECUTE FUNCTION notify_predictive_part_used();

-- ============================================
-- OVERDUE CHECKER (CRON JOB)
-- Run daily to catch work orders that became overdue
-- ============================================
CREATE OR REPLACE FUNCTION check_overdue_work_orders()
RETURNS void AS $$
DECLARE
  webhook_url TEXT := 'https://api.celeste7.ai/webhook/internal/predictive-event';
  wo RECORD;
BEGIN
  FOR wo IN
    SELECT id, equipment_id, yacht_id
    FROM work_orders
    WHERE due_date < CURRENT_DATE
      AND status NOT IN ('completed', 'cancelled')
      AND equipment_id IS NOT NULL
      AND (metadata->>'overdue_notified')::boolean IS NOT TRUE
  LOOP
    PERFORM net.http_post(
      url := webhook_url,
      headers := '{"Content-Type": "application/json"}'::jsonb,
      body := jsonb_build_object(
        'event', 'wo_overdue',
        'equipment_id', wo.equipment_id,
        'yacht_id', wo.yacht_id,
        'work_order_id', wo.id
      )::text
    );

    -- Mark as notified to prevent duplicate events
    UPDATE work_orders
    SET metadata = COALESCE(metadata, '{}'::jsonb) || '{"overdue_notified": true}'::jsonb
    WHERE id = wo.id;
  END LOOP;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Schedule with pg_cron (if available):
-- SELECT cron.schedule('check-overdue-daily', '0 6 * * *', 'SELECT check_overdue_work_orders()');

-- ============================================
-- HELPER: Disable triggers temporarily
-- ============================================
CREATE OR REPLACE FUNCTION disable_predictive_triggers()
RETURNS void AS $$
BEGIN
  ALTER TABLE faults DISABLE TRIGGER trg_predictive_fault_created;
  ALTER TABLE faults DISABLE TRIGGER trg_predictive_fault_resolved;
  ALTER TABLE work_orders DISABLE TRIGGER trg_predictive_wo_created;
  ALTER TABLE work_orders DISABLE TRIGGER trg_predictive_wo_updated;
  ALTER TABLE notes DISABLE TRIGGER trg_predictive_note_added;
  ALTER TABLE parts DISABLE TRIGGER trg_predictive_part_used;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION enable_predictive_triggers()
RETURNS void AS $$
BEGIN
  ALTER TABLE faults ENABLE TRIGGER trg_predictive_fault_created;
  ALTER TABLE faults ENABLE TRIGGER trg_predictive_fault_resolved;
  ALTER TABLE work_orders ENABLE TRIGGER trg_predictive_wo_created;
  ALTER TABLE work_orders ENABLE TRIGGER trg_predictive_wo_updated;
  ALTER TABLE notes ENABLE TRIGGER trg_predictive_note_added;
  ALTER TABLE parts ENABLE TRIGGER trg_predictive_part_used;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- GRANT PERMISSIONS
-- ============================================
-- Grant execute to service role for n8n access
GRANT EXECUTE ON FUNCTION notify_predictive_fault_created() TO service_role;
GRANT EXECUTE ON FUNCTION notify_predictive_fault_resolved() TO service_role;
GRANT EXECUTE ON FUNCTION notify_predictive_wo_created() TO service_role;
GRANT EXECUTE ON FUNCTION notify_predictive_wo_updated() TO service_role;
GRANT EXECUTE ON FUNCTION notify_predictive_note_added() TO service_role;
GRANT EXECUTE ON FUNCTION notify_predictive_part_used() TO service_role;
GRANT EXECUTE ON FUNCTION check_overdue_work_orders() TO service_role;
GRANT EXECUTE ON FUNCTION disable_predictive_triggers() TO service_role;
GRANT EXECUTE ON FUNCTION enable_predictive_triggers() TO service_role;
