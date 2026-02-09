-- Migration: Fix f1_cache_invalidate trigger - Remove org_id reference
-- Date: 2026-02-09
-- Issue: log_part_usage failed with "record 'new' has no field 'org_id'"
-- Root Cause: f1_cache_invalidate() trigger tried to access NEW.org_id
--             but pms_parts table has NO org_id column (uses yacht_id)

-- Fix: Remove org_id from cache invalidation notification
-- Impact: Fixes inventory log_part_usage action for all elevated roles
-- Risk: LOW - removes reference to non-existent field
-- Deployed: 2026-02-09 17:22 UTC (applied directly to fix production)

CREATE OR REPLACE FUNCTION public.f1_cache_invalidate()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- Send cache invalidation notification
    -- FIXED: Remove org_id reference, use yacht_id only
    PERFORM pg_notify(
        'f1_cache_invalidate',
        json_build_object(
            'yacht_id', NEW.yacht_id,
            'object_type', TG_ARGV[0],
            'object_id', NEW.id,
            'ts', extract(epoch FROM now())
        )::text
    );

    RETURN NEW;
END;
$function$;

-- Verification:
-- 1. Test log_part_usage with HOD role should no longer get org_id error
-- 2. Cache invalidation notifications should still work
-- 3. Search results should update after inventory changes

-- Before (BROKEN):
--   json_build_object(
--       'org_id', COALESCE(NEW.org_id, NEW.yacht_id),  -- ❌ NEW.org_id doesn't exist
--       'yacht_id', NEW.yacht_id,
--       ...
--   )

-- After (FIXED):
--   json_build_object(
--       'yacht_id', NEW.yacht_id,  -- ✅ Use yacht_id only
--       ...
--   )
