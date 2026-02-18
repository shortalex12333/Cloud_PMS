-- ============================================================================
-- MIGRATION: 20260217000001_shopping_list_state_history.sql
-- PURPOSE: Add state history tracking trigger for shopping list items
-- REQUIREMENT: SHOP-05 - Shopping list needs state history tracking
-- DATE: 2026-02-17
-- ============================================================================
-- RATIONALE: Track all status changes for shopping list items in pms_audit_log
--            for audit trail and ledger requirements. Fires on INSERT and UPDATE.
-- ============================================================================

BEGIN;

-- ============================================================================
-- FUNCTION: track_shopping_list_state_change
-- PURPOSE: Track status changes for shopping list items in audit log
-- ============================================================================
CREATE OR REPLACE FUNCTION public.track_shopping_list_state_change()
RETURNS TRIGGER AS $$
DECLARE
    v_user_id UUID;
BEGIN
    -- Get user ID from updated_by/created_by or JWT claims
    v_user_id := COALESCE(
        NEW.updated_by,
        NEW.created_by,
        (current_setting('request.jwt.claims', true)::json->>'sub')::UUID
    );

    -- Track status changes on UPDATE
    IF TG_OP = 'UPDATE' AND OLD.status IS DISTINCT FROM NEW.status THEN
        INSERT INTO pms_audit_log (
            yacht_id,
            action,
            entity_type,
            entity_id,
            user_id,
            old_values,
            new_values,
            signature,
            created_at
        ) VALUES (
            NEW.yacht_id,
            'shopping_list_status_change',
            'shopping_list_item',
            NEW.id,
            v_user_id,
            jsonb_build_object(
                'status', OLD.status,
                'part_name', OLD.part_name,
                'quantity_requested', OLD.quantity_requested
            ),
            jsonb_build_object(
                'status', NEW.status,
                'part_name', NEW.part_name,
                'quantity_requested', NEW.quantity_requested
            ),
            jsonb_build_object(
                'user_id', v_user_id,
                'trigger_name', TG_NAME,
                'source', 'trigger',
                'timestamp', NOW()
            ),
            NOW()
        );
    END IF;

    -- Track creation on INSERT
    IF TG_OP = 'INSERT' THEN
        INSERT INTO pms_audit_log (
            yacht_id,
            action,
            entity_type,
            entity_id,
            user_id,
            old_values,
            new_values,
            signature,
            created_at
        ) VALUES (
            NEW.yacht_id,
            'shopping_list_item_created',
            'shopping_list_item',
            NEW.id,
            v_user_id,
            NULL,
            jsonb_build_object(
                'status', NEW.status,
                'part_name', NEW.part_name,
                'quantity_requested', NEW.quantity_requested,
                'source_type', NEW.source_type,
                'urgency', NEW.urgency
            ),
            jsonb_build_object(
                'user_id', v_user_id,
                'trigger_name', TG_NAME,
                'source', 'trigger',
                'timestamp', NOW()
            ),
            NOW()
        );
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- TRIGGER: shopping_list_state_history_trigger
-- PURPOSE: Fire on INSERT or UPDATE to track state changes
-- ============================================================================
DROP TRIGGER IF EXISTS shopping_list_state_history_trigger ON pms_shopping_list_items;

CREATE TRIGGER shopping_list_state_history_trigger
    AFTER INSERT OR UPDATE ON pms_shopping_list_items
    FOR EACH ROW
    EXECUTE FUNCTION track_shopping_list_state_change();

-- Add comment for documentation
COMMENT ON TRIGGER shopping_list_state_history_trigger ON pms_shopping_list_items IS
    'Tracks state changes for shopping list items in pms_audit_log for SHOP-05 compliance';

COMMENT ON FUNCTION track_shopping_list_state_change() IS
    'Trigger function to log shopping list item creation and status changes to pms_audit_log';

COMMIT;
