-- =============================================================================
-- SEED REALISTIC HOURS OF REST DATA
-- =============================================================================
-- Purpose: Create realistic test data for natural language search testing
-- Database: TENANT_1 (vzsohavtuotocgrfkfyd) for pms_hours_of_rest
-- Usage: psql $TENANT_1_DB_URL -f 02_seed_realistic_hor_data.sql
--
-- Data Created:
-- - 5 crew × 14 days = 70 HoR records
-- - Mix of compliant (11h) and non-compliant (9h, 8.5h)
-- - Different departments (deck vs engine)
-- - Different time periods (last week, this week, specific dates)
-- - Warnings for non-compliant records
-- =============================================================================

BEGIN;

\set TEST_YACHT_ID '85fe1119-b04c-41ac-80f1-829d23322598'
\set JOHN_DECK_ID 'a1111111-1111-1111-1111-111111111111'
\set SARAH_DECK_ID 'a2222222-2222-2222-2222-222222222222'
\set HOD_DECK_ID 'a3333333-3333-3333-3333-333333333333'
\set TOM_ENGINE_ID 'a4444444-4444-4444-4444-444444444444'
\set HOD_ENGINE_ID 'a5555555-5555-5555-5555-555555555555'

\echo '========================================================================'
\echo 'Seeding Realistic Hours of Rest Data'
\echo '========================================================================'

-- =============================================================================
-- JOHN (Deck Crew) - Mostly compliant, 1 violation
-- =============================================================================

\echo ''
\echo '--- John (Deck Crew) ---'

-- Last 2 weeks (14 days)
DO $$
DECLARE
    i INT;
    test_date DATE;
    rest_hours NUMERIC;
BEGIN
    FOR i IN 0..13 LOOP
        test_date := CURRENT_DATE - (14 - i);

        -- Non-compliant on Tuesday last week (day 7)
        IF i = 7 THEN
            rest_hours := 9.0;  -- Violation!
            RAISE NOTICE 'Day %: % - %.1f hours (NON-COMPLIANT)', i, test_date, rest_hours;
        ELSE
            rest_hours := 11.0;  -- Compliant
            RAISE NOTICE 'Day %: % - %.1f hours', i, test_date, rest_hours;
        END IF;

        INSERT INTO pms_hours_of_rest (
            yacht_id,
            user_id,
            record_date,
            rest_periods,
            total_rest_hours,
            total_work_hours,
            status,
            created_by,
            updated_by
        ) VALUES (
            :TEST_YACHT_ID,
            :JOHN_DECK_ID,
            test_date,
            jsonb_build_array(
                jsonb_build_object(
                    'start', '20:00',
                    'end', CASE WHEN rest_hours = 9.0 THEN '05:00' ELSE '07:00' END,
                    'hours', rest_hours
                )
            ),
            rest_hours,
            24.0 - rest_hours,
            'approved',
            :JOHN_DECK_ID,
            :JOHN_DECK_ID
        ) ON CONFLICT (yacht_id, user_id, record_date) DO UPDATE SET
            total_rest_hours = EXCLUDED.total_rest_hours,
            updated_at = NOW();
    END LOOP;
END $$;

-- =============================================================================
-- SARAH (Deck Crew) - 2 violations (more chaotic)
-- =============================================================================

\echo ''
\echo '--- Sarah (Deck Crew) ---'

DO $$
DECLARE
    i INT;
    test_date DATE;
    rest_hours NUMERIC;
BEGIN
    FOR i IN 0..13 LOOP
        test_date := CURRENT_DATE - (14 - i);

        -- Non-compliant on 2 days
        IF i = 5 OR i = 11 THEN
            rest_hours := 8.5;  -- Violation!
            RAISE NOTICE 'Day %: % - %.1f hours (NON-COMPLIANT)', i, test_date, rest_hours;
        ELSE
            rest_hours := 11.0;  -- Compliant
            RAISE NOTICE 'Day %: % - %.1f hours', i, test_date, rest_hours;
        END IF;

        INSERT INTO pms_hours_of_rest (
            yacht_id,
            user_id,
            record_date,
            rest_periods,
            total_rest_hours,
            total_work_hours,
            status,
            created_by,
            updated_by
        ) VALUES (
            :TEST_YACHT_ID,
            :SARAH_DECK_ID,
            test_date,
            jsonb_build_array(
                jsonb_build_object(
                    'start', '22:00',
                    'end', CASE WHEN rest_hours = 8.5 THEN '06:30' ELSE '09:00' END,
                    'hours', rest_hours
                )
            ),
            rest_hours,
            24.0 - rest_hours,
            'approved',
            :SARAH_DECK_ID,
            :SARAH_DECK_ID
        ) ON CONFLICT (yacht_id, user_id, record_date) DO UPDATE SET
            total_rest_hours = EXCLUDED.total_rest_hours,
            updated_at = NOW();
    END LOOP;
END $$;

-- =============================================================================
-- TOM (Engine Crew) - Mostly compliant
-- =============================================================================

\echo ''
\echo '--- Tom (Engine Crew) ---'

DO $$
DECLARE
    i INT;
    test_date DATE;
    rest_hours NUMERIC;
BEGIN
    FOR i IN 0..13 LOOP
        test_date := CURRENT_DATE - (14 - i);

        -- Non-compliant on 1 day
        IF i = 9 THEN
            rest_hours := 9.5;  -- Violation!
            RAISE NOTICE 'Day %: % - %.1f hours (NON-COMPLIANT)', i, test_date, rest_hours;
        ELSE
            rest_hours := 11.0;  -- Compliant
            RAISE NOTICE 'Day %: % - %.1f hours', i, test_date, rest_hours;
        END IF;

        INSERT INTO pms_hours_of_rest (
            yacht_id,
            user_id,
            record_date,
            rest_periods,
            total_rest_hours,
            total_work_hours,
            status,
            created_by,
            updated_by
        ) VALUES (
            :TEST_YACHT_ID,
            :TOM_ENGINE_ID,
            test_date,
            jsonb_build_array(
                jsonb_build_object(
                    'start', '21:00',
                    'end', CASE WHEN rest_hours = 9.5 THEN '06:30' ELSE '08:00' END,
                    'hours', rest_hours
                )
            ),
            rest_hours,
            24.0 - rest_hours,
            'approved',
            :TOM_ENGINE_ID,
            :TOM_ENGINE_ID
        ) ON CONFLICT (yacht_id, user_id, record_date) DO UPDATE SET
            total_rest_hours = EXCLUDED.total_rest_hours,
            updated_at = NOW();
    END LOOP;
END $$;

-- =============================================================================
-- CREATE REALISTIC WARNINGS (for non-compliant records)
-- =============================================================================

\echo ''
\echo '========================================================================'
\echo 'Creating Warnings for Non-Compliant Records'
\echo '========================================================================'

-- Note: Warnings are normally created by triggers/RPC, but we'll create manually for testing

-- John's violation (Tuesday last week)
INSERT INTO pms_crew_hours_warnings (
    yacht_id,
    user_id,
    warning_type,
    severity,
    record_date,
    message,
    violation_data,
    status,
    created_at
) VALUES (
    :TEST_YACHT_ID,
    :JOHN_DECK_ID,
    'DAILY_REST',
    'warning',
    CURRENT_DATE - 7,  -- Tuesday last week
    'Daily rest hours (9.0h) below minimum 10h requirement (ILO MLC 2006)',
    jsonb_build_object(
        'actual_hours', 9.0,
        'required_hours', 10.0,
        'deficit', 1.0,
        'regulation', 'ILO MLC 2006'
    ),
    'active',
    NOW()
) ON CONFLICT DO NOTHING;

-- Sarah's violations (2 days)
INSERT INTO pms_crew_hours_warnings (
    yacht_id,
    user_id,
    warning_type,
    severity,
    record_date,
    message,
    violation_data,
    status,
    created_at
) VALUES
(
    :TEST_YACHT_ID,
    :SARAH_DECK_ID,
    'DAILY_REST',
    'critical',  -- More severe
    CURRENT_DATE - 9,
    'Daily rest hours (8.5h) below minimum 10h requirement (ILO MLC 2006)',
    jsonb_build_object(
        'actual_hours', 8.5,
        'required_hours', 10.0,
        'deficit', 1.5,
        'regulation', 'ILO MLC 2006'
    ),
    'active',
    NOW()
),
(
    :TEST_YACHT_ID,
    :SARAH_DECK_ID,
    'DAILY_REST',
    'critical',
    CURRENT_DATE - 3,
    'Daily rest hours (8.5h) below minimum 10h requirement (ILO MLC 2006)',
    jsonb_build_object(
        'actual_hours', 8.5,
        'required_hours', 10.0,
        'deficit', 1.5,
        'regulation', 'ILO MLC 2006'
    ),
    'active',
    NOW()
) ON CONFLICT DO NOTHING;

-- Tom's violation
INSERT INTO pms_crew_hours_warnings (
    yacht_id,
    user_id,
    warning_type,
    severity,
    record_date,
    message,
    violation_data,
    status,
    created_at
) VALUES (
    :TEST_YACHT_ID,
    :TOM_ENGINE_ID,
    'DAILY_REST',
    'warning',
    CURRENT_DATE - 5,
    'Daily rest hours (9.5h) below minimum 10h requirement (ILO MLC 2006)',
    jsonb_build_object(
        'actual_hours', 9.5,
        'required_hours', 10.0,
        'deficit', 0.5,
        'regulation', 'ILO MLC 2006'
    ),
    'active',
    NOW()
) ON CONFLICT DO NOTHING;

-- =============================================================================
-- CREATE SAMPLE TEMPLATES
-- =============================================================================

\echo ''
\echo '========================================================================'
\echo 'Creating Sample Schedule Templates'
\echo '========================================================================'

-- 4-on-8-off Watch (Deck)
INSERT INTO pms_crew_normal_hours (
    yacht_id,
    user_id,
    schedule_name,
    description,
    schedule_template,
    is_active,
    applies_to,
    created_by
) VALUES (
    :TEST_YACHT_ID,
    :HOD_DECK_ID,
    '4-on-8-off Watch',
    'Standard 4 hours on, 8 hours off watch rotation for deck crew',
    jsonb_build_array(
        jsonb_build_object('day', 'monday', 'work_start', '00:00', 'work_end', '04:00', 'rest_hours', 8),
        jsonb_build_object('day', 'monday', 'work_start', '12:00', 'work_end', '16:00', 'rest_hours', 8),
        jsonb_build_object('day', 'tuesday', 'work_start', '00:00', 'work_end', '04:00', 'rest_hours', 8),
        jsonb_build_object('day', 'tuesday', 'work_start', '12:00', 'work_end', '16:00', 'rest_hours', 8)
    ),
    true,
    'normal',
    :HOD_DECK_ID
) ON CONFLICT DO NOTHING;

-- Day Work (Engine)
INSERT INTO pms_crew_normal_hours (
    yacht_id,
    user_id,
    schedule_name,
    description,
    schedule_template,
    is_active,
    applies_to,
    created_by
) VALUES (
    :TEST_YACHT_ID,
    :HOD_ENGINE_ID,
    'Day Work Schedule',
    'Standard day work 08:00-17:00 for engine crew',
    jsonb_build_array(
        jsonb_build_object('day', 'monday', 'work_start', '08:00', 'work_end', '17:00', 'rest_hours', 11),
        jsonb_build_object('day', 'tuesday', 'work_start', '08:00', 'work_end', '17:00', 'rest_hours', 11),
        jsonb_build_object('day', 'wednesday', 'work_start', '08:00', 'work_end', '17:00', 'rest_hours', 11)
    ),
    true,
    'normal',
    :HOD_ENGINE_ID
) ON CONFLICT DO NOTHING;

-- =============================================================================
-- VERIFICATION
-- =============================================================================

\echo ''
\echo '========================================================================'
\echo 'Data Seeding Complete - Verification'
\echo '========================================================================'

\echo ''
\echo '--- Hours of Rest Records by User ---'
SELECT
    CASE user_id
        WHEN :JOHN_DECK_ID THEN 'John (deck)'
        WHEN :SARAH_DECK_ID THEN 'Sarah (deck)'
        WHEN :TOM_ENGINE_ID THEN 'Tom (engine)'
    END as user,
    COUNT(*) as total_records,
    SUM(CASE WHEN is_daily_compliant THEN 1 ELSE 0 END) as compliant,
    SUM(CASE WHEN NOT is_daily_compliant THEN 1 ELSE 0 END) as non_compliant,
    ROUND(AVG(total_rest_hours), 2) as avg_rest_hours,
    MIN(record_date) as first_date,
    MAX(record_date) as last_date
FROM pms_hours_of_rest
WHERE yacht_id = :TEST_YACHT_ID
AND user_id IN (:JOHN_DECK_ID, :SARAH_DECK_ID, :TOM_ENGINE_ID)
GROUP BY user_id
ORDER BY user_id;

\echo ''
\echo '--- Warnings Summary ---'
SELECT
    CASE user_id
        WHEN :JOHN_DECK_ID THEN 'John (deck)'
        WHEN :SARAH_DECK_ID THEN 'Sarah (deck)'
        WHEN :TOM_ENGINE_ID THEN 'Tom (engine)'
    END as user,
    warning_type,
    severity,
    COUNT(*) as warning_count,
    status
FROM pms_crew_hours_warnings
WHERE yacht_id = :TEST_YACHT_ID
AND user_id IN (:JOHN_DECK_ID, :SARAH_DECK_ID, :TOM_ENGINE_ID)
GROUP BY user_id, warning_type, severity, status
ORDER BY user_id, severity DESC;

\echo ''
\echo '--- Templates Created ---'
SELECT
    schedule_name,
    description,
    CASE user_id
        WHEN :HOD_DECK_ID THEN 'HOD (deck)'
        WHEN :HOD_ENGINE_ID THEN 'HOD (engine)'
    END as created_by,
    is_active,
    applies_to
FROM pms_crew_normal_hours
WHERE yacht_id = :TEST_YACHT_ID
ORDER BY schedule_name;

\echo ''
\echo '========================================================================'
\echo 'Test Data Summary'
\echo '========================================================================'
\echo 'HoR Records: 42 (3 users × 14 days)'
\echo 'Compliant:   38 records (90%)'
\echo 'Violations:  4 records (10%)'
\echo ''
\echo 'Department Distribution:'
\echo '  Deck:   28 records (John: 14, Sarah: 14)'
\echo '  Engine: 14 records (Tom: 14)'
\echo ''
\echo 'Warnings:   4 active warnings'
\echo '  John (deck):   1 warning  (Tuesday last week, 9.0h)'
\echo '  Sarah (deck):  2 warnings (9 days ago + 3 days ago, 8.5h each)'
\echo '  Tom (engine):  1 warning  (5 days ago, 9.5h)'
\echo ''
\echo 'Templates:  2 schedules'
\echo '  Deck:   4-on-8-off Watch'
\echo '  Engine: Day Work Schedule'
\echo '========================================================================'

COMMIT;
