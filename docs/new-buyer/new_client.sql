-- ============================================================
-- NEW CLIENT ONBOARDING
-- ============================================================
-- Run in: Master Supabase SQL Editor (qvzmkaamzaqxpzbewjxe)
--
-- Before running:
--   1. Fill in the 5 values marked EDIT below
--   2. Run the entire script
--   3. Copy yacht_id + yacht_id_hash from the output
--   4. Build the DMG with those values
--
-- The yacht_id (UUID) and yacht_id_hash (SHA-256) are
-- auto-generated. Never set these manually.
-- ============================================================

DO $$
DECLARE
    v_yacht_id  TEXT := gen_random_uuid()::text;
    v_2fa_code  TEXT := lpad(floor(random() * 1000000)::text, 6, '0');
BEGIN

    -- ===================== EDIT THESE 5 VALUES =====================

    INSERT INTO fleet_registry (
        yacht_id,
        yacht_id_hash,
        yacht_name,
        yacht_model,
        buyer_name,
        buyer_email,
        tenant_supabase_url
    ) VALUES (
        v_yacht_id,
        encode(digest(v_yacht_id, 'sha256'), 'hex'),
        'M/Y VESSEL_NAME',                      -- 1. Yacht display name
        'Builder Model',                         -- 2. e.g. Benetti Oasis 40M
        'Buyer Full Name',                       -- 3. Captain or owner name
        'buyer@example.com',                     -- 4. Must be valid email
        'https://vzsohavtuotocgrfkfyd.supabase.co'  -- 5. Always this (multi-tenant)
    );

    -- ===================== END EDIT ================================

    -- Pre-seed installation 2FA code
    INSERT INTO installation_2fa_codes (
        yacht_id,
        code_hash,
        email_sent_to,
        purpose,
        expires_at,
        verified,
        attempts,
        max_attempts
    ) VALUES (
        v_yacht_id,
        encode(digest(v_2fa_code, 'sha256'), 'hex'),
        (SELECT buyer_email FROM fleet_registry WHERE yacht_id = v_yacht_id),
        'installation',
        NOW() + INTERVAL '7 days',
        false,
        0,
        5
    );

    RAISE NOTICE '';
    RAISE NOTICE '╔══════════════════════════════════════╗';
    RAISE NOTICE '║        CLIENT ONBOARDED              ║';
    RAISE NOTICE '╠══════════════════════════════════════╣';
    RAISE NOTICE '║  yacht_id:      %', v_yacht_id;
    RAISE NOTICE '║  yacht_id_hash: %', encode(digest(v_yacht_id, 'sha256'), 'hex');
    RAISE NOTICE '║  2FA code:      %', v_2fa_code;
    RAISE NOTICE '╠══════════════════════════════════════╣';
    RAISE NOTICE '║  NEXT STEPS:                         ║';
    RAISE NOTICE '║  1. Copy yacht_id above              ║';
    RAISE NOTICE '║  2. Build DMG (needs service key)    ║';
    RAISE NOTICE '║  3. Send DMG + 2FA code to buyer     ║';
    RAISE NOTICE '╚══════════════════════════════════════╝';
END $$;

-- Verify insertion
SELECT yacht_id, yacht_id_hash, yacht_name, buyer_name, buyer_email, active, created_at
FROM fleet_registry
ORDER BY created_at DESC
LIMIT 1;
