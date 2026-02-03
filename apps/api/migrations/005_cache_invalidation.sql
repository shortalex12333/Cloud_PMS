-- ============================================================================
-- F1 Search Phase 3: Cache Invalidation via pg_notify
-- ============================================================================
--
-- Notifies on source table changes (parts, work_orders) so edge caches
-- evict tenant-scoped keys.
--
-- Listeners receive: {org_id, yacht_id, object_type, object_id, ts}
-- ============================================================================

-- 1) Notification function (generic; pass object_type as TG_ARGV[0])
CREATE OR REPLACE FUNCTION f1_cache_invalidate()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM pg_notify(
        'f1_cache_invalidate',
        json_build_object(
            'org_id', NEW.org_id,
            'yacht_id', NEW.yacht_id,
            'object_type', TG_ARGV[0],
            'object_id', NEW.id,
            'ts', extract(epoch FROM now())
        )::text
    );
    RETURN NULL;
END;
$$;

-- 2) Attach to source tables

-- Note: pms_parts uses yacht_id as org_id
DROP TRIGGER IF EXISTS trg_parts_cache_invalidate ON pms_parts;
CREATE TRIGGER trg_parts_cache_invalidate
    AFTER INSERT OR UPDATE OR DELETE ON pms_parts
    FOR EACH ROW
    EXECUTE FUNCTION f1_cache_invalidate('part');

-- Work orders (if table exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pms_work_orders') THEN
        DROP TRIGGER IF EXISTS trg_workorders_cache_invalidate ON pms_work_orders;
        CREATE TRIGGER trg_workorders_cache_invalidate
            AFTER INSERT OR UPDATE OR DELETE ON pms_work_orders
            FOR EACH ROW
            EXECUTE FUNCTION f1_cache_invalidate('work_order');
    END IF;
END $$;
