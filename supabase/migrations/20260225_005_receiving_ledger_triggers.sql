-- ============================================================================
-- MIGRATION: 20260225_005_receiving_ledger_triggers.sql
-- PURPOSE: Add state history tracking triggers for Receiving records
-- REQUIREMENT: RECV-05 - Receiving needs state history tracking (LAW 22 compliant)
-- DATE: 2026-02-25
-- ============================================================================
-- RATIONALE: Track all status changes for Receiving records in pms_audit_log
--            for audit trail and ledger requirements. Fires on INSERT and UPDATE.
--
-- Tracked Events:
--   1. receiving_created - New receiving record created
--   2. receiving_status_change - Status transitions (draft -> in_review -> accepted/rejected)
--   3. receiving_accepted - SIGNED acceptance event (immutable ledger entry)
--   4. receiving_item_added - Line item added to receiving
-- ============================================================================

BEGIN;

-- ============================================================================
-- FUNCTION: track_receiving_state_change
-- PURPOSE: Track status changes and acceptance events for receiving records
-- ============================================================================
CREATE OR REPLACE FUNCTION public.track_receiving_state_change()
RETURNS TRIGGER AS $$
DECLARE
    v_user_id UUID;
    v_action TEXT;
BEGIN
    -- Get user ID from record columns or JWT claims
    v_user_id := COALESCE(
        NEW.received_by,
        NEW.created_by,
        NULLIF(current_setting('request.jwt.claims', true)::json->>'sub', '')::UUID
    );

    -- =========================================================================
    -- Track INSERT (new record created)
    -- =========================================================================
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
            'receiving_created',
            'receiving',
            NEW.id,
            v_user_id,
            NULL,
            jsonb_build_object(
                'status', NEW.status,
                'vendor_name', NEW.vendor_name,
                'vendor_reference', NEW.vendor_reference,
                'received_date', NEW.received_date,
                'received_by', NEW.received_by,
                'currency', NEW.currency,
                'total', NEW.total
            ),
            jsonb_build_object(
                'user_id', v_user_id,
                'trigger_name', TG_NAME,
                'source', 'trigger',
                'timestamp', NOW()
            ),
            NOW()
        );

        RETURN NEW;
    END IF;

    -- =========================================================================
    -- Track UPDATE operations
    -- =========================================================================
    IF TG_OP = 'UPDATE' THEN

        -- ---------------------------------------------------------------------
        -- Track status changes (draft -> in_review -> accepted/rejected)
        -- ---------------------------------------------------------------------
        IF OLD.status IS DISTINCT FROM NEW.status THEN
            -- Special handling for 'accepted' status - this is a SIGNED event
            IF NEW.status = 'accepted' THEN
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
                    'receiving_accepted',  -- SIGNED action
                    'receiving',
                    NEW.id,
                    v_user_id,
                    jsonb_build_object(
                        'status', OLD.status,
                        'total', OLD.total,
                        'subtotal', OLD.subtotal,
                        'tax_total', OLD.tax_total
                    ),
                    jsonb_build_object(
                        'status', NEW.status,
                        'vendor_name', NEW.vendor_name,
                        'vendor_reference', NEW.vendor_reference,
                        'received_date', NEW.received_date,
                        'total', NEW.total,
                        'subtotal', NEW.subtotal,
                        'tax_total', NEW.tax_total,
                        'currency', NEW.currency,
                        'accepted_by', v_user_id,
                        'accepted_at', NOW()
                    ),
                    jsonb_build_object(
                        'user_id', v_user_id,
                        'trigger_name', TG_NAME,
                        'source', 'trigger',
                        'timestamp', NOW(),
                        'signed', true,
                        'signature_type', 'acceptance',
                        'transition', OLD.status || ' -> ' || NEW.status
                    ),
                    NOW()
                );
            ELSE
                -- Regular status change (not acceptance)
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
                    'receiving_status_change',
                    'receiving',
                    NEW.id,
                    v_user_id,
                    jsonb_build_object(
                        'status', OLD.status,
                        'total', OLD.total
                    ),
                    jsonb_build_object(
                        'status', NEW.status,
                        'total', NEW.total,
                        'previous_status', OLD.status,
                        'new_status', NEW.status
                    ),
                    jsonb_build_object(
                        'user_id', v_user_id,
                        'trigger_name', TG_NAME,
                        'source', 'trigger',
                        'timestamp', NOW(),
                        'transition', OLD.status || ' -> ' || NEW.status
                    ),
                    NOW()
                );
            END IF;
        END IF;

        -- ---------------------------------------------------------------------
        -- Track financial changes (when totals are updated)
        -- ---------------------------------------------------------------------
        IF (OLD.total IS DISTINCT FROM NEW.total) AND OLD.status = NEW.status THEN
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
                'receiving_financial_update',
                'receiving',
                NEW.id,
                v_user_id,
                jsonb_build_object(
                    'subtotal', OLD.subtotal,
                    'tax_total', OLD.tax_total,
                    'total', OLD.total,
                    'currency', OLD.currency
                ),
                jsonb_build_object(
                    'subtotal', NEW.subtotal,
                    'tax_total', NEW.tax_total,
                    'total', NEW.total,
                    'currency', NEW.currency
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

    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- FUNCTION: track_receiving_item_changes
-- PURPOSE: Track line item additions and modifications
-- ============================================================================
CREATE OR REPLACE FUNCTION public.track_receiving_item_changes()
RETURNS TRIGGER AS $$
DECLARE
    v_user_id UUID;
    v_yacht_id UUID;
BEGIN
    -- Get yacht_id from the item
    v_yacht_id := NEW.yacht_id;

    -- Get user ID from JWT claims
    v_user_id := NULLIF(current_setting('request.jwt.claims', true)::json->>'sub', '')::UUID;

    -- =========================================================================
    -- Track INSERT (new item added)
    -- =========================================================================
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
            v_yacht_id,
            'receiving_item_added',
            'receiving_item',
            NEW.id,
            v_user_id,
            NULL,
            jsonb_build_object(
                'receiving_id', NEW.receiving_id,
                'part_id', NEW.part_id,
                'description', NEW.description,
                'quantity_expected', NEW.quantity_expected,
                'quantity_received', NEW.quantity_received,
                'unit_price', NEW.unit_price,
                'currency', NEW.currency
            ),
            jsonb_build_object(
                'user_id', v_user_id,
                'trigger_name', TG_NAME,
                'source', 'trigger',
                'timestamp', NOW()
            ),
            NOW()
        );

        RETURN NEW;
    END IF;

    -- =========================================================================
    -- Track UPDATE (quantity adjustments)
    -- =========================================================================
    IF TG_OP = 'UPDATE' THEN
        IF OLD.quantity_received IS DISTINCT FROM NEW.quantity_received THEN
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
                v_yacht_id,
                'receiving_item_adjusted',
                'receiving_item',
                NEW.id,
                v_user_id,
                jsonb_build_object(
                    'quantity_received', OLD.quantity_received,
                    'quantity_expected', OLD.quantity_expected
                ),
                jsonb_build_object(
                    'quantity_received', NEW.quantity_received,
                    'quantity_expected', NEW.quantity_expected,
                    'adjustment', NEW.quantity_received - OLD.quantity_received
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
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- DROP EXISTING TRIGGERS (defensive - if any)
-- ============================================================================
DROP TRIGGER IF EXISTS receiving_state_history_trigger ON pms_receiving;
DROP TRIGGER IF EXISTS receiving_item_history_trigger ON pms_receiving_items;

-- ============================================================================
-- CREATE TRIGGERS
-- ============================================================================
CREATE TRIGGER receiving_state_history_trigger
    AFTER INSERT OR UPDATE ON pms_receiving
    FOR EACH ROW
    EXECUTE FUNCTION track_receiving_state_change();

CREATE TRIGGER receiving_item_history_trigger
    AFTER INSERT OR UPDATE ON pms_receiving_items
    FOR EACH ROW
    EXECUTE FUNCTION track_receiving_item_changes();

-- ============================================================================
-- COMMENTS
-- ============================================================================
COMMENT ON TRIGGER receiving_state_history_trigger ON pms_receiving IS
    'Tracks state changes for Receiving records in pms_audit_log for RECV-05 compliance. Fires on INSERT and UPDATE, recording status transitions and acceptance events with full before/after values.';

COMMENT ON TRIGGER receiving_item_history_trigger ON pms_receiving_items IS
    'Tracks line item changes for Receiving records in pms_audit_log. Fires on INSERT and UPDATE for item additions and quantity adjustments.';

COMMENT ON FUNCTION track_receiving_state_change() IS
    'Trigger function for Receiving audit logging. Records:
     - receiving_created: New receiving record creation
     - receiving_status_change: Status transitions (draft/in_review/accepted/rejected)
     - receiving_accepted: SIGNED acceptance event (immutable ledger entry)
     - receiving_financial_update: Total/subtotal changes
     Logs to pms_audit_log for RECV-05 compliance requirement.';

COMMENT ON FUNCTION track_receiving_item_changes() IS
    'Trigger function for Receiving item audit logging. Records:
     - receiving_item_added: New line item added
     - receiving_item_adjusted: Quantity adjustments
     Logs to pms_audit_log for RECV-05 compliance.';

COMMIT;

-- ============================================================================
-- VERIFICATION QUERY (for manual testing)
-- ============================================================================
-- Run after migration to verify triggers are installed:
--
-- SELECT
--     tgname as trigger_name,
--     tgtype,
--     tgenabled,
--     pg_get_triggerdef(oid) as definition
-- FROM pg_trigger
-- WHERE tgrelid IN ('pms_receiving'::regclass, 'pms_receiving_items'::regclass)
--   AND tgname LIKE '%history_trigger';
--
-- Verify audit entries:
-- SELECT * FROM pms_audit_log
-- WHERE entity_type IN ('receiving', 'receiving_item')
-- ORDER BY created_at DESC LIMIT 10;
