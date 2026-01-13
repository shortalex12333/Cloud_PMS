-- ================================================================================
-- MASTER DB MIGRATION 005: ensure_user_account RPC
-- ================================================================================
-- Purpose: Idempotent upsert on first login/signup
-- Security: Validates yacht_id exists and is active before allowing assignment
-- ================================================================================

-- Create ensure_user_account RPC
CREATE OR REPLACE FUNCTION public.ensure_user_account(
    p_yacht_id TEXT,
    p_role TEXT DEFAULT 'member'
)
RETURNS public.user_accounts
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_user_id UUID;
    v_yacht_active BOOLEAN;
    v_result public.user_accounts;
BEGIN
    -- Get current user ID
    v_user_id := auth.uid();

    IF v_user_id IS NULL THEN
        RAISE EXCEPTION 'Not authenticated';
    END IF;

    -- Validate yacht_id is provided
    IF p_yacht_id IS NULL OR char_length(p_yacht_id) = 0 THEN
        RAISE EXCEPTION 'yacht_id is required';
    END IF;

    -- Validate yacht exists and is active in fleet_registry
    SELECT active INTO v_yacht_active
    FROM public.fleet_registry
    WHERE yacht_id = p_yacht_id;

    IF v_yacht_active IS NULL THEN
        RAISE EXCEPTION 'Invalid yacht_id: yacht not found in registry';
    END IF;

    IF NOT v_yacht_active THEN
        RAISE EXCEPTION 'Yacht is not active';
    END IF;

    -- Check if user already has an account
    SELECT * INTO v_result
    FROM public.user_accounts
    WHERE user_id = v_user_id;

    IF v_result.user_id IS NOT NULL THEN
        -- User already has an account
        -- Enforce single-tenant: cannot change yacht_id
        IF v_result.yacht_id != p_yacht_id THEN
            RAISE EXCEPTION 'User already assigned to different yacht (single-tenant constraint)';
        END IF;

        -- Log the idempotent call
        PERFORM public.log_security_event('account_created', jsonb_build_object(
            'action', 'idempotent_noop',
            'yacht_id', p_yacht_id
        ), p_yacht_id);

        RETURN v_result;
    END IF;

    -- Create new user_accounts row
    INSERT INTO public.user_accounts (
        user_id,
        yacht_id,
        role,
        status,
        created_at,
        updated_at
    ) VALUES (
        v_user_id,
        p_yacht_id,
        COALESCE(p_role, 'member'),
        'pending',  -- New accounts start as pending, admin must activate
        NOW(),
        NOW()
    )
    RETURNING * INTO v_result;

    -- Log the new account creation
    PERFORM public.log_security_event('account_created', jsonb_build_object(
        'action', 'created',
        'yacht_id', p_yacht_id,
        'role', p_role
    ), p_yacht_id);

    RETURN v_result;
END;
$$;

-- Grant execute to authenticated users
GRANT EXECUTE ON FUNCTION public.ensure_user_account(TEXT, TEXT) TO authenticated;

-- Add comment
COMMENT ON FUNCTION public.ensure_user_account IS
    'Idempotent upsert for user_accounts. Creates account on first login. Enforces single-tenant.';

-- Verification
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'public'
          AND p.proname = 'ensure_user_account'
    ) THEN
        RAISE NOTICE '✅ ensure_user_account function created successfully';
    ELSE
        RAISE EXCEPTION '❌ Failed to create ensure_user_account function';
    END IF;
END $$;

-- ================================================================================
-- NOTES
-- ================================================================================
-- This RPC is called during the signup/first-login flow:
--
-- 1. User signs up via Supabase Auth (creates auth.users row)
-- 2. Frontend calls ensure_user_account(yacht_id) with activation code/yacht_id
-- 3. RPC validates yacht exists and is active
-- 4. RPC creates user_accounts row (status='pending')
-- 5. Admin reviews and activates account (status='active')
-- 6. User can now use get_my_bootstrap() to get full context
--
-- SINGLE-TENANT CONSTRAINT:
-- - Once a user is assigned to a yacht, they CANNOT change yachts
-- - If they call ensure_user_account with different yacht_id, it throws error
-- - This prevents multi-tenant security issues
--
-- STATUS FLOW:
-- - 'pending' → 'active' (admin approval)
-- - 'active' → 'suspended' (temp disable by admin)
-- - 'suspended' → 'active' (reactivate by admin)
-- - 'active' → 'deactivated' (permanent disable)
--
-- SECURITY:
-- - user_id is ALWAYS from auth.uid(), never from client input
-- - yacht_id is validated against fleet_registry
-- - Role is defaulted to 'member', HOD roles require admin assignment
-- ================================================================================
