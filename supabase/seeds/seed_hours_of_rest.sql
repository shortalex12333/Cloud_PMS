-- =============================================================================
-- HOURS OF REST - TEST DATA SEED
-- =============================================================================
-- Run on TENANT DB: https://vzsohavtuotocgrfkfyd.supabase.co
-- Target Yacht: 85fe1119-b04c-41ac-80f1-829d23322598
--
-- Creates:
--   - 5 crew member profiles
--   - 30 days of rest records per crew member
--   - Schedule templates
--   - Monthly signoff records
--   - Violation warnings
-- =============================================================================

-- Test configuration
DO $$
DECLARE
    v_yacht_id UUID := '85fe1119-b04c-41ac-80f1-829d23322598';
    v_captain_id UUID := 'b72c35ff-e309-4a19-a617-bfc706a78c0f';
    v_chief_eng_id UUID := '89b1262c-ff59-4591-b954-757cdf3d609d';
    v_deckhand_id UUID := '00000000-0000-4000-a000-000000000001';
    v_engineer_id UUID := '00000000-0000-4000-a000-000000000002';
    v_steward_id UUID := '00000000-0000-4000-a000-000000000003';
    v_current_date DATE := CURRENT_DATE;
    v_record_date DATE;
    v_day_offset INT;
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'SEEDING HOURS OF REST TEST DATA';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Yacht: %', v_yacht_id;
    RAISE NOTICE 'Date: %', v_current_date;
    RAISE NOTICE '';
END $$;

-- =============================================================================
-- 1. ENSURE CREW PROFILES EXIST
-- =============================================================================

INSERT INTO auth_users_profiles (user_id, yacht_id, email, display_name, created_at)
VALUES
    ('b72c35ff-e309-4a19-a617-bfc706a78c0f', '85fe1119-b04c-41ac-80f1-829d23322598', 'captain.tenant@alex-short.com', 'Captain Test', NOW()),
    ('89b1262c-ff59-4591-b954-757cdf3d609d', '85fe1119-b04c-41ac-80f1-829d23322598', 'hod.tenant@alex-short.com', 'Chief Engineer Test', NOW()),
    ('00000000-0000-4000-a000-000000000001', '85fe1119-b04c-41ac-80f1-829d23322598', 'deckhand.john@test.com', 'Deckhand John', NOW()),
    ('00000000-0000-4000-a000-000000000002', '85fe1119-b04c-41ac-80f1-829d23322598', 'engineer.sarah@test.com', 'Engineer Sarah', NOW()),
    ('00000000-0000-4000-a000-000000000003', '85fe1119-b04c-41ac-80f1-829d23322598', 'steward.alex@test.com', 'Steward Alex', NOW())
ON CONFLICT (user_id, yacht_id) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    email = EXCLUDED.email;

-- =============================================================================
-- 2. SCHEDULE TEMPLATES
-- =============================================================================

INSERT INTO pms_crew_normal_hours (yacht_id, template_name, description, schedule_template, is_default)
VALUES
    -- 4-on/8-off Watch System
    (
        '85fe1119-b04c-41ac-80f1-829d23322598',
        '4-on/8-off Watch System',
        'Standard rotating watch schedule - 12 hours work, 12 hours rest per day. MLC 2006 compliant.',
        '{
            "monday": [
                {"start": "00:00", "end": "04:00", "type": "work"},
                {"start": "04:00", "end": "08:00", "type": "rest"},
                {"start": "08:00", "end": "12:00", "type": "work"},
                {"start": "12:00", "end": "16:00", "type": "rest"},
                {"start": "16:00", "end": "20:00", "type": "work"},
                {"start": "20:00", "end": "00:00", "type": "rest"}
            ],
            "tuesday": [
                {"start": "00:00", "end": "04:00", "type": "rest"},
                {"start": "04:00", "end": "08:00", "type": "work"},
                {"start": "08:00", "end": "12:00", "type": "rest"},
                {"start": "12:00", "end": "16:00", "type": "work"},
                {"start": "16:00", "end": "20:00", "type": "rest"},
                {"start": "20:00", "end": "00:00", "type": "work"}
            ],
            "wednesday": [
                {"start": "00:00", "end": "04:00", "type": "work"},
                {"start": "04:00", "end": "08:00", "type": "rest"},
                {"start": "08:00", "end": "12:00", "type": "work"},
                {"start": "12:00", "end": "16:00", "type": "rest"},
                {"start": "16:00", "end": "20:00", "type": "work"},
                {"start": "20:00", "end": "00:00", "type": "rest"}
            ],
            "thursday": [
                {"start": "00:00", "end": "04:00", "type": "rest"},
                {"start": "04:00", "end": "08:00", "type": "work"},
                {"start": "08:00", "end": "12:00", "type": "rest"},
                {"start": "12:00", "end": "16:00", "type": "work"},
                {"start": "16:00", "end": "20:00", "type": "rest"},
                {"start": "20:00", "end": "00:00", "type": "work"}
            ],
            "friday": [
                {"start": "00:00", "end": "04:00", "type": "work"},
                {"start": "04:00", "end": "08:00", "type": "rest"},
                {"start": "08:00", "end": "12:00", "type": "work"},
                {"start": "12:00", "end": "16:00", "type": "rest"},
                {"start": "16:00", "end": "20:00", "type": "work"},
                {"start": "20:00", "end": "00:00", "type": "rest"}
            ],
            "saturday": [
                {"start": "00:00", "end": "04:00", "type": "rest"},
                {"start": "04:00", "end": "08:00", "type": "work"},
                {"start": "08:00", "end": "12:00", "type": "rest"},
                {"start": "12:00", "end": "16:00", "type": "work"},
                {"start": "16:00", "end": "20:00", "type": "rest"},
                {"start": "20:00", "end": "00:00", "type": "work"}
            ],
            "sunday": [
                {"start": "00:00", "end": "08:00", "type": "rest"},
                {"start": "08:00", "end": "12:00", "type": "work"},
                {"start": "12:00", "end": "20:00", "type": "rest"},
                {"start": "20:00", "end": "00:00", "type": "work"}
            ]
        }'::jsonb,
        true
    ),
    -- Day Worker
    (
        '85fe1119-b04c-41ac-80f1-829d23322598',
        'Day Worker',
        'Standard day shift - 08:00 to 18:00 work with weekends reduced. 14+ hours rest daily.',
        '{
            "monday": [{"start": "08:00", "end": "18:00", "type": "work"}],
            "tuesday": [{"start": "08:00", "end": "18:00", "type": "work"}],
            "wednesday": [{"start": "08:00", "end": "18:00", "type": "work"}],
            "thursday": [{"start": "08:00", "end": "18:00", "type": "work"}],
            "friday": [{"start": "08:00", "end": "18:00", "type": "work"}],
            "saturday": [{"start": "08:00", "end": "14:00", "type": "work"}],
            "sunday": []
        }'::jsonb,
        false
    ),
    -- Port Day
    (
        '85fe1119-b04c-41ac-80f1-829d23322598',
        'Port Day Schedule',
        'Reduced hours when in port - minimal watch requirements. 16+ hours rest daily.',
        '{
            "monday": [{"start": "09:00", "end": "17:00", "type": "work"}],
            "tuesday": [{"start": "09:00", "end": "17:00", "type": "work"}],
            "wednesday": [{"start": "09:00", "end": "17:00", "type": "work"}],
            "thursday": [{"start": "09:00", "end": "17:00", "type": "work"}],
            "friday": [{"start": "09:00", "end": "17:00", "type": "work"}],
            "saturday": [{"start": "09:00", "end": "12:00", "type": "work"}],
            "sunday": []
        }'::jsonb,
        false
    )
ON CONFLICT (yacht_id, template_name) DO UPDATE SET
    description = EXCLUDED.description,
    schedule_template = EXCLUDED.schedule_template;

-- =============================================================================
-- 3. DAILY REST RECORDS (30 days for each crew member)
-- =============================================================================

-- Function to generate rest records
CREATE OR REPLACE FUNCTION seed_hor_records()
RETURNS void AS $$
DECLARE
    v_yacht_id UUID := '85fe1119-b04c-41ac-80f1-829d23322598';
    v_crew_ids UUID[] := ARRAY[
        'b72c35ff-e309-4a19-a617-bfc706a78c0f',
        '89b1262c-ff59-4591-b954-757cdf3d609d',
        '00000000-0000-4000-a000-000000000001',
        '00000000-0000-4000-a000-000000000002',
        '00000000-0000-4000-a000-000000000003'
    ];
    v_crew_id UUID;
    v_record_date DATE;
    v_start_date DATE;
    v_rest_periods JSONB;
    v_total_rest DECIMAL;
    v_is_compliant BOOLEAN;
    v_day_offset INT;

    -- Compliant rest patterns (10+ hours)
    v_compliant_1 JSONB := '[{"start": "22:00", "end": "06:00"}, {"start": "13:00", "end": "15:00"}]';  -- 10h
    v_compliant_2 JSONB := '[{"start": "21:00", "end": "07:00"}]';  -- 10h
    v_compliant_3 JSONB := '[{"start": "23:00", "end": "06:00"}, {"start": "12:00", "end": "15:00"}]';  -- 10h

    -- Non-compliant rest patterns (<10 hours)
    v_violation_1 JSONB := '[{"start": "23:00", "end": "06:00"}, {"start": "14:00", "end": "15:00"}]';  -- 8h
    v_violation_2 JSONB := '[{"start": "00:00", "end": "06:00"}]';  -- 6h (severe)
    v_violation_3 JSONB := '[{"start": "22:00", "end": "06:00"}, {"start": "13:00", "end": "14:00"}]';  -- 9h
BEGIN
    v_start_date := date_trunc('month', CURRENT_DATE)::date;

    FOREACH v_crew_id IN ARRAY v_crew_ids LOOP
        FOR v_day_offset IN 0..29 LOOP
            v_record_date := v_start_date + v_day_offset;

            -- Skip future dates
            IF v_record_date > CURRENT_DATE THEN
                EXIT;
            END IF;

            -- 80% compliant, 20% non-compliant
            IF v_day_offset % 5 = 0 THEN
                -- Non-compliant day
                CASE v_day_offset % 3
                    WHEN 0 THEN v_rest_periods := v_violation_1; v_total_rest := 8.0;
                    WHEN 1 THEN v_rest_periods := v_violation_2; v_total_rest := 6.0;
                    ELSE v_rest_periods := v_violation_3; v_total_rest := 9.0;
                END CASE;
                v_is_compliant := false;
            ELSE
                -- Compliant day
                CASE v_day_offset % 3
                    WHEN 0 THEN v_rest_periods := v_compliant_1; v_total_rest := 10.0;
                    WHEN 1 THEN v_rest_periods := v_compliant_2; v_total_rest := 10.0;
                    ELSE v_rest_periods := v_compliant_3; v_total_rest := 10.0;
                END CASE;
                v_is_compliant := true;
            END IF;

            -- Insert rest record
            INSERT INTO pms_hours_of_rest (
                yacht_id, user_id, record_date, rest_periods,
                total_rest_hours, is_daily_compliant, is_weekly_compliant,
                notes
            )
            VALUES (
                v_yacht_id, v_crew_id, v_record_date, v_rest_periods,
                v_total_rest, v_is_compliant, true,
                CASE WHEN v_is_compliant
                    THEN 'Auto-seeded test data - compliant'
                    ELSE 'Auto-seeded test data - VIOLATION'
                END
            )
            ON CONFLICT (yacht_id, user_id, record_date) DO UPDATE SET
                rest_periods = EXCLUDED.rest_periods,
                total_rest_hours = EXCLUDED.total_rest_hours,
                is_daily_compliant = EXCLUDED.is_daily_compliant,
                notes = EXCLUDED.notes;

            -- Create warning for violations
            IF NOT v_is_compliant THEN
                INSERT INTO pms_crew_hours_warnings (
                    yacht_id, user_id, warning_type, severity, status,
                    record_date, violation_details, message
                )
                VALUES (
                    v_yacht_id, v_crew_id, 'DAILY_REST',
                    CASE WHEN v_total_rest < 8 THEN 'high' ELSE 'medium' END,
                    'active',
                    v_record_date,
                    jsonb_build_object(
                        'required_hours', 10,
                        'actual_hours', v_total_rest,
                        'shortfall', 10 - v_total_rest
                    ),
                    format('Daily rest violation: %sh (minimum 10h required)', v_total_rest)
                )
                ON CONFLICT (yacht_id, user_id, record_date, warning_type) DO UPDATE SET
                    severity = EXCLUDED.severity,
                    violation_details = EXCLUDED.violation_details,
                    message = EXCLUDED.message;
            END IF;
        END LOOP;
    END LOOP;

    RAISE NOTICE 'Rest records seeded successfully';
END;
$$ LANGUAGE plpgsql;

-- Execute seeding
SELECT seed_hor_records();

-- Cleanup
DROP FUNCTION IF EXISTS seed_hor_records();

-- =============================================================================
-- 4. MONTHLY SIGNOFFS
-- =============================================================================

-- Last month - finalized signoffs
INSERT INTO pms_hor_monthly_signoffs (yacht_id, user_id, year_month, status, crew_signature, hod_signature, master_signature)
SELECT
    '85fe1119-b04c-41ac-80f1-829d23322598',
    user_id,
    to_char(date_trunc('month', CURRENT_DATE) - interval '1 month', 'YYYY-MM'),
    'finalized',
    jsonb_build_object(
        'signed_at', (CURRENT_TIMESTAMP - interval '5 days')::text,
        'ip_address', '192.168.1.100'
    ),
    jsonb_build_object(
        'signed_at', (CURRENT_TIMESTAMP - interval '3 days')::text,
        'signed_by', '89b1262c-ff59-4591-b954-757cdf3d609d',
        'ip_address', '192.168.1.101'
    ),
    jsonb_build_object(
        'signed_at', (CURRENT_TIMESTAMP - interval '1 day')::text,
        'signed_by', 'b72c35ff-e309-4a19-a617-bfc706a78c0f',
        'ip_address', '192.168.1.102'
    )
FROM unnest(ARRAY[
    'b72c35ff-e309-4a19-a617-bfc706a78c0f'::uuid,
    '89b1262c-ff59-4591-b954-757cdf3d609d'::uuid,
    '00000000-0000-4000-a000-000000000001'::uuid,
    '00000000-0000-4000-a000-000000000002'::uuid,
    '00000000-0000-4000-a000-000000000003'::uuid
]) AS user_id
ON CONFLICT (yacht_id, user_id, year_month) DO UPDATE SET
    status = EXCLUDED.status,
    crew_signature = EXCLUDED.crew_signature,
    hod_signature = EXCLUDED.hod_signature,
    master_signature = EXCLUDED.master_signature;

-- Current month - draft signoffs
INSERT INTO pms_hor_monthly_signoffs (yacht_id, user_id, year_month, status)
SELECT
    '85fe1119-b04c-41ac-80f1-829d23322598',
    user_id,
    to_char(CURRENT_DATE, 'YYYY-MM'),
    'draft'
FROM unnest(ARRAY[
    'b72c35ff-e309-4a19-a617-bfc706a78c0f'::uuid,
    '89b1262c-ff59-4591-b954-757cdf3d609d'::uuid,
    '00000000-0000-4000-a000-000000000001'::uuid,
    '00000000-0000-4000-a000-000000000002'::uuid,
    '00000000-0000-4000-a000-000000000003'::uuid
]) AS user_id
ON CONFLICT (yacht_id, user_id, year_month) DO UPDATE SET
    status = EXCLUDED.status;

-- =============================================================================
-- VERIFICATION
-- =============================================================================

-- Count records
SELECT
    'pms_hours_of_rest' as table_name,
    count(*) as record_count
FROM pms_hours_of_rest
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'

UNION ALL

SELECT
    'pms_crew_hours_warnings' as table_name,
    count(*) as record_count
FROM pms_crew_hours_warnings
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'

UNION ALL

SELECT
    'pms_crew_normal_hours' as table_name,
    count(*) as record_count
FROM pms_crew_normal_hours
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'

UNION ALL

SELECT
    'pms_hor_monthly_signoffs' as table_name,
    count(*) as record_count
FROM pms_hor_monthly_signoffs
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598';

-- Show sample records
SELECT
    u.display_name,
    h.record_date,
    h.total_rest_hours,
    h.is_daily_compliant,
    h.notes
FROM pms_hours_of_rest h
JOIN auth_users_profiles u ON h.user_id = u.user_id AND h.yacht_id = u.yacht_id
WHERE h.yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
ORDER BY h.record_date DESC, u.display_name
LIMIT 20;

-- Show active warnings
SELECT
    u.display_name,
    w.record_date,
    w.warning_type,
    w.severity,
    w.status,
    w.message
FROM pms_crew_hours_warnings w
JOIN auth_users_profiles u ON w.user_id = u.user_id AND w.yacht_id = u.yacht_id
WHERE w.yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND w.status = 'active'
ORDER BY w.record_date DESC, u.display_name
LIMIT 20;
