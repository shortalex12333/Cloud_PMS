-- ============================================================================
-- MIGRATION: Create WO Status → Fault Status Cascade Trigger
-- ============================================================================
-- PROBLEM: When Work Order status changes, linked Fault status should update
--          - WO completed → Fault resolved
--          - WO cancelled → Fault returned to open
--          - WO in_progress → Fault investigating
-- SOLUTION: Create trigger function and trigger on pms_work_orders
-- SEVERITY: HIGH - Required for Complete WO and Archive WO actions
-- ============================================================================

BEGIN;

-- =============================================================================
-- STEP 1: Create the cascade function
-- =============================================================================
CREATE OR REPLACE FUNCTION public.cascade_wo_status_to_fault()
RETURNS TRIGGER AS $$
BEGIN
    -- Only cascade if:
    -- 1. Work order has a linked fault (fault_id IS NOT NULL)
    -- 2. Status actually changed
    IF NEW.fault_id IS NOT NULL AND OLD.status IS DISTINCT FROM NEW.status THEN
        CASE NEW.status
            -- WO in_progress → Fault investigating
            WHEN 'in_progress' THEN
                UPDATE pms_faults
                SET
                    status = 'investigating',
                    updated_at = NOW()
                WHERE id = NEW.fault_id
                AND yacht_id = NEW.yacht_id
                AND status = 'open';  -- Only transition from open

            -- WO completed → Fault resolved
            WHEN 'completed' THEN
                UPDATE pms_faults
                SET
                    status = 'resolved',
                    resolved_at = NOW(),
                    resolved_by = NEW.completed_by,
                    updated_at = NOW()
                WHERE id = NEW.fault_id
                AND yacht_id = NEW.yacht_id
                AND status IN ('open', 'investigating', 'work_ordered');

            -- WO cancelled/deferred → Fault returned to open
            WHEN 'cancelled' THEN
                UPDATE pms_faults
                SET
                    status = 'open',
                    resolved_at = NULL,
                    resolved_by = NULL,
                    updated_at = NOW()
                WHERE id = NEW.fault_id
                AND yacht_id = NEW.yacht_id
                AND status IN ('investigating', 'work_ordered');

            WHEN 'deferred' THEN
                -- Deferred means work is postponed, fault stays investigating
                UPDATE pms_faults
                SET
                    status = 'investigating',
                    updated_at = NOW()
                WHERE id = NEW.fault_id
                AND yacht_id = NEW.yacht_id
                AND status = 'work_ordered';

            ELSE
                -- No cascade for other status values
                NULL;
        END CASE;

        -- Log the cascade action (optional, for debugging)
        RAISE NOTICE 'Cascaded WO % status (% → %) to Fault %',
            NEW.id, OLD.status, NEW.status, NEW.fault_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION public.cascade_wo_status_to_fault IS
    'Cascade Work Order status changes to linked Fault (WO-First Doctrine)';

-- =============================================================================
-- STEP 2: Drop existing trigger if exists
-- =============================================================================
DROP TRIGGER IF EXISTS trg_wo_status_cascade_to_fault ON pms_work_orders;

-- =============================================================================
-- STEP 3: Create the trigger
-- =============================================================================
CREATE TRIGGER trg_wo_status_cascade_to_fault
    AFTER UPDATE OF status ON pms_work_orders
    FOR EACH ROW
    WHEN (OLD.status IS DISTINCT FROM NEW.status)
    EXECUTE FUNCTION public.cascade_wo_status_to_fault();

COMMENT ON TRIGGER trg_wo_status_cascade_to_fault ON pms_work_orders IS
    'Automatically update linked fault status when work order status changes';

-- =============================================================================
-- STEP 4: Verification
-- =============================================================================
DO $$
DECLARE
    trigger_exists BOOLEAN;
    function_exists BOOLEAN;
BEGIN
    -- Check function exists
    SELECT EXISTS (
        SELECT 1 FROM pg_proc
        WHERE proname = 'cascade_wo_status_to_fault'
        AND pronamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
    ) INTO function_exists;

    IF NOT function_exists THEN
        RAISE EXCEPTION 'Migration verification failed: cascade_wo_status_to_fault function not found';
    END IF;

    -- Check trigger exists
    SELECT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgname = 'trg_wo_status_cascade_to_fault'
        AND tgrelid = 'pms_work_orders'::regclass
    ) INTO trigger_exists;

    IF NOT trigger_exists THEN
        RAISE EXCEPTION 'Migration verification failed: trg_wo_status_cascade_to_fault trigger not found';
    END IF;

    RAISE NOTICE 'SUCCESS: cascade_wo_status_to_fault trigger deployed';
END $$;

COMMIT;

-- =============================================================================
-- TEST CASES (run manually after migration)
-- =============================================================================
--
-- Test 1: WO completion cascades to fault
-- UPDATE pms_work_orders SET status = 'completed', completed_by = auth.uid(), completed_at = NOW()
-- WHERE id = '[test_wo_id]' AND fault_id IS NOT NULL;
-- SELECT status FROM pms_faults WHERE id = '[linked_fault_id]'; -- Should be 'resolved'
--
-- Test 2: WO cancellation returns fault to open
-- UPDATE pms_work_orders SET status = 'cancelled' WHERE id = '[test_wo_id]';
-- SELECT status FROM pms_faults WHERE id = '[linked_fault_id]'; -- Should be 'open'

-- =============================================================================
-- ROLLBACK SCRIPT (run separately if needed)
-- =============================================================================
-- BEGIN;
-- DROP TRIGGER IF EXISTS trg_wo_status_cascade_to_fault ON pms_work_orders;
-- DROP FUNCTION IF EXISTS public.cascade_wo_status_to_fault();
-- COMMIT;
