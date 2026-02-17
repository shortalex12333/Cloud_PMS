-- ============================================================================
-- LEDGER TRIGGERS
-- Auto-insert into ledger_events when source tables are modified
-- Run this in Supabase SQL Editor: https://supabase.com/dashboard/project/vzsohavtuotocgrfkfyd/sql/new
-- ============================================================================

-- Drop existing triggers if they exist
DROP TRIGGER IF EXISTS trg_ledger_pms_work_orders ON pms_work_orders;
DROP FUNCTION IF EXISTS fn_ledger_pms_work_orders();

-- ============================================================================
-- TRIGGER FUNCTION: pms_work_orders → ledger_events
-- ============================================================================
CREATE OR REPLACE FUNCTION fn_ledger_pms_work_orders()
RETURNS TRIGGER AS $$
DECLARE
    v_user_id uuid;
    v_event_type text;
    v_action text;
    v_entity_id uuid;
    v_yacht_id uuid;
    v_proof_hash text;
BEGIN
    -- Determine event type and action based on operation
    IF TG_OP = 'INSERT' THEN
        v_event_type := 'create';
        v_action := 'work_order_created';
        v_user_id := NEW.created_by;
        v_entity_id := NEW.id;
        v_yacht_id := NEW.yacht_id;
    ELSIF TG_OP = 'UPDATE' THEN
        v_event_type := 'update';
        v_action := 'work_order_updated';
        v_user_id := COALESCE(NEW.updated_by, NEW.created_by);
        v_entity_id := NEW.id;
        v_yacht_id := NEW.yacht_id;

        -- Specific action detection
        IF OLD.status IS DISTINCT FROM NEW.status THEN
            v_action := 'status_changed';
            v_event_type := 'status_change';
        END IF;
        IF OLD.assigned_to IS DISTINCT FROM NEW.assigned_to THEN
            v_action := 'work_order_reassigned';
            v_event_type := 'assignment';
        END IF;
        IF NEW.completed_at IS NOT NULL AND OLD.completed_at IS NULL THEN
            v_action := 'work_order_completed';
        END IF;
    ELSIF TG_OP = 'DELETE' THEN
        v_event_type := 'delete';
        v_action := 'work_order_deleted';
        v_user_id := COALESCE(OLD.deleted_by, OLD.updated_by, OLD.created_by);
        v_entity_id := OLD.id;
        v_yacht_id := OLD.yacht_id;
    END IF;

    -- Skip if no user_id (system operations)
    IF v_user_id IS NULL THEN
        RETURN COALESCE(NEW, OLD);
    END IF;

    -- Generate simple proof hash
    v_proof_hash := encode(
        sha256(
            (v_yacht_id::text || v_user_id::text || v_entity_id::text || v_action || now()::text)::bytea
        ),
        'hex'
    );

    -- Insert ledger event
    INSERT INTO ledger_events (
        yacht_id,
        user_id,
        event_type,
        entity_type,
        entity_id,
        action,
        proof_hash,
        metadata
    ) VALUES (
        v_yacht_id,
        v_user_id,
        v_event_type,
        'pms_work_orders',
        v_entity_id,
        v_action,
        v_proof_hash,
        jsonb_build_object(
            'title', COALESCE(NEW.title, OLD.title),
            'status', COALESCE(NEW.status, OLD.status),
            'old_status', CASE WHEN TG_OP = 'UPDATE' THEN OLD.status ELSE NULL END
        )
    );

    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Attach trigger
CREATE TRIGGER trg_ledger_pms_work_orders
    AFTER INSERT OR UPDATE OR DELETE ON pms_work_orders
    FOR EACH ROW
    EXECUTE FUNCTION fn_ledger_pms_work_orders();


-- ============================================================================
-- TRIGGER FUNCTION: pms_work_order_notes → ledger_events
-- Columns: id, work_order_id, note_text, note_type, created_by, created_at
-- ============================================================================
DROP TRIGGER IF EXISTS trg_ledger_pms_work_order_notes ON pms_work_order_notes;
DROP FUNCTION IF EXISTS fn_ledger_pms_work_order_notes();

CREATE OR REPLACE FUNCTION fn_ledger_pms_work_order_notes()
RETURNS TRIGGER AS $$
DECLARE
    v_yacht_id uuid;
    v_proof_hash text;
BEGIN
    -- Get yacht_id from parent work order
    SELECT yacht_id INTO v_yacht_id
    FROM pms_work_orders
    WHERE id = NEW.work_order_id;

    -- Skip if no yacht found
    IF v_yacht_id IS NULL THEN
        RETURN NEW;
    END IF;

    v_proof_hash := encode(
        sha256((v_yacht_id::text || NEW.created_by::text || NEW.id::text || 'add_note' || now()::text)::bytea),
        'hex'
    );

    INSERT INTO ledger_events (
        yacht_id,
        user_id,
        event_type,
        entity_type,
        entity_id,
        action,
        proof_hash,
        metadata
    ) VALUES (
        v_yacht_id,
        NEW.created_by,
        'create',
        'pms_work_order_notes',
        NEW.id,
        'add_note',
        v_proof_hash,
        jsonb_build_object(
            'work_order_id', NEW.work_order_id,
            'note_preview', left(NEW.note_text, 100),
            'note_type', NEW.note_type
        )
    );

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER trg_ledger_pms_work_order_notes
    AFTER INSERT ON pms_work_order_notes
    FOR EACH ROW
    EXECUTE FUNCTION fn_ledger_pms_work_order_notes();


-- ============================================================================
-- TRIGGER FUNCTION: pms_checklist_items → ledger_events
-- Columns: id, yacht_id, checklist_id, description, is_completed, completed_by, created_by
-- ============================================================================
DROP TRIGGER IF EXISTS trg_ledger_pms_checklist_items ON pms_checklist_items;
DROP FUNCTION IF EXISTS fn_ledger_pms_checklist_items();

CREATE OR REPLACE FUNCTION fn_ledger_pms_checklist_items()
RETURNS TRIGGER AS $$
DECLARE
    v_proof_hash text;
    v_action text;
    v_user_id uuid;
BEGIN
    IF TG_OP = 'INSERT' THEN
        v_action := 'add_checklist_item';
        v_user_id := NEW.created_by;
    ELSIF TG_OP = 'UPDATE' AND NEW.is_completed = true AND (OLD.is_completed = false OR OLD.is_completed IS NULL) THEN
        v_action := 'mark_checklist_item_complete';
        v_user_id := COALESCE(NEW.completed_by, NEW.updated_by, NEW.created_by);
    ELSE
        v_action := 'update_checklist_item';
        v_user_id := COALESCE(NEW.updated_by, NEW.created_by);
    END IF;

    -- Skip if no user
    IF v_user_id IS NULL THEN
        RETURN NEW;
    END IF;

    v_proof_hash := encode(
        sha256((NEW.yacht_id::text || v_user_id::text || NEW.id::text || v_action || now()::text)::bytea),
        'hex'
    );

    INSERT INTO ledger_events (
        yacht_id,
        user_id,
        event_type,
        entity_type,
        entity_id,
        action,
        proof_hash,
        metadata
    ) VALUES (
        NEW.yacht_id,
        v_user_id,
        CASE WHEN TG_OP = 'INSERT' THEN 'create' ELSE 'update' END,
        'pms_checklist_items',
        NEW.id,
        v_action,
        v_proof_hash,
        jsonb_build_object(
            'checklist_id', NEW.checklist_id,
            'description', left(NEW.description, 100),
            'is_completed', NEW.is_completed
        )
    );

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER trg_ledger_pms_checklist_items
    AFTER INSERT OR UPDATE ON pms_checklist_items
    FOR EACH ROW
    EXECUTE FUNCTION fn_ledger_pms_checklist_items();


-- ============================================================================
-- VERIFICATION
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE '✅ Ledger triggers installed:';
    RAISE NOTICE '   - trg_ledger_pms_work_orders';
    RAISE NOTICE '   - trg_ledger_pms_work_order_notes';
    RAISE NOTICE '   - trg_ledger_pms_checklist_items';
END $$;
