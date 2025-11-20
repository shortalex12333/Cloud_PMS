-- ============================================================================
-- PART 4: Demo Data and Triggers
-- ============================================================================

-- Insert demo yacht
INSERT INTO public.yachts (id, name, signature, status, nas_root_path)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'MY Demo Yacht',
    'demo-yacht-signature-123',
    'demo',
    '/demo/nas'
)
ON CONFLICT (id) DO UPDATE
SET
    name = EXCLUDED.name,
    signature = EXCLUDED.signature,
    status = EXCLUDED.status,
    updated_at = NOW();

-- Create triggers
DO $$
BEGIN
    CREATE TRIGGER on_auth_user_created
        AFTER INSERT ON auth.users
        FOR EACH ROW
        EXECUTE FUNCTION public.handle_new_user();
    RAISE NOTICE '✓ Created trigger: on_auth_user_created';
EXCEPTION
    WHEN insufficient_privilege THEN
        RAISE NOTICE '⚠ Insufficient privileges for trigger - create users manually';
    WHEN undefined_table THEN
        RAISE NOTICE '⚠ auth.users not accessible - normal in some setups';
    WHEN duplicate_object THEN
        RAISE NOTICE '✓ Trigger on_auth_user_created already exists';
    WHEN OTHERS THEN
        RAISE NOTICE '⚠ Could not create trigger: %', SQLERRM;
END $$;

DO $$
BEGIN
    CREATE TRIGGER on_auth_user_role_assign
        AFTER INSERT ON auth.users
        FOR EACH ROW
        EXECUTE FUNCTION public.handle_new_user_role();
    RAISE NOTICE '✓ Created trigger: on_auth_user_role_assign';
EXCEPTION
    WHEN insufficient_privilege THEN
        RAISE NOTICE '⚠ Insufficient privileges for role trigger';
    WHEN undefined_table THEN
        RAISE NOTICE '⚠ auth.users not accessible';
    WHEN duplicate_object THEN
        RAISE NOTICE '✓ Trigger on_auth_user_role_assign already exists';
    WHEN OTHERS THEN
        RAISE NOTICE '⚠ Could not create role trigger: %', SQLERRM;
END $$;

-- Final verification
DO $$
DECLARE
    yacht_count INTEGER;
    table_count INTEGER;
    policy_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_name IN ('yachts', 'user_profiles', 'user_roles', 'api_tokens', 'yacht_signatures');

    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE schemaname = 'public';

    SELECT COUNT(*) INTO yacht_count FROM public.yachts;

    RAISE NOTICE '';
    RAISE NOTICE '════════════════════════════════════════════════════════════';
    RAISE NOTICE '✓ SETUP COMPLETE - ALL 4 PARTS DONE';
    RAISE NOTICE '════════════════════════════════════════════════════════════';
    RAISE NOTICE 'Tables: % / 5', table_count;
    RAISE NOTICE 'RLS Policies: %', policy_count;
    RAISE NOTICE 'Yachts: %', yacht_count;
    RAISE NOTICE '';
    RAISE NOTICE 'Demo yacht ID: 00000000-0000-0000-0000-000000000001';
    RAISE NOTICE 'Demo signature: demo-yacht-signature-123';
    RAISE NOTICE '';
    RAISE NOTICE 'NEXT: Create user in Dashboard → Authentication → Users';
    RAISE NOTICE '════════════════════════════════════════════════════════════';
END $$;
