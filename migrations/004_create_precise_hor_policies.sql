-- ============================================================================
-- MIGRATION: Create Precise RLS Policies for pms_hours_of_rest
-- Date: 2026-01-30
-- Purpose: Deny-by-default with precise role-based access
-- ============================================================================

-- Security Model:
-- - Self-only mutations: Crew can only INSERT/UPDATE own records
-- - HOD department reads: HOD can SELECT department crew (read-only, no mutations)
-- - Captain yacht reads: Captain can SELECT all yacht crew (read-only, no mutations)
-- - No DELETE: Deletes denied for all users (audit preservation)

BEGIN;

-- ============================================================================
-- POLICY 1: SELECT (Read Access)
-- ============================================================================

-- Who can SELECT:
-- - Self: Always (user_id = auth.uid())
-- - HOD: Department crew on same yacht (is_hod() AND is_same_department())
-- - Captain/Manager: All yacht crew (is_captain())

CREATE POLICY pms_hours_of_rest_select ON pms_hours_of_rest
    FOR SELECT
    USING (
        -- Yacht isolation (mandatory for all)
        yacht_id = current_setting('app.current_yacht_id', TRUE)::UUID
        AND (
            -- Self-access
            user_id = auth.uid()
            OR
            -- HOD department access
            (public.is_hod() AND public.is_same_department(user_id))
            OR
            -- Captain/Manager yacht-wide access
            public.is_captain()
        )
    );

COMMENT ON POLICY pms_hours_of_rest_select ON pms_hours_of_rest IS
    'Read access: self-only, HOD department-gated, Captain yacht-wide';

-- ============================================================================
-- POLICY 2: INSERT (Create Records)
-- ============================================================================

-- Who can INSERT:
-- - Self ONLY: user_id must equal auth.uid()
-- - yacht_id must equal current yacht
-- - HOD/Captain CANNOT insert for crew (crew must create own records)

CREATE POLICY pms_hours_of_rest_insert ON pms_hours_of_rest
    FOR INSERT
    WITH CHECK (
        yacht_id = current_setting('app.current_yacht_id', TRUE)::UUID
        AND user_id = auth.uid()
    );

COMMENT ON POLICY pms_hours_of_rest_insert ON pms_hours_of_rest IS
    'Create access: self-only (crew must create own HoR records)';

-- ============================================================================
-- POLICY 3: UPDATE (Modify Records)
-- ============================================================================

-- Who can UPDATE:
-- - Self ONLY: Can only update own records
-- - HOD/Captain CANNOT update daily entries (mutations via pms_hor_monthly_signoffs)

CREATE POLICY pms_hours_of_rest_update ON pms_hours_of_rest
    FOR UPDATE
    USING (
        yacht_id = current_setting('app.current_yacht_id', TRUE)::UUID
        AND user_id = auth.uid()
    )
    WITH CHECK (
        yacht_id = current_setting('app.current_yacht_id', TRUE)::UUID
        AND user_id = auth.uid()
    );

COMMENT ON POLICY pms_hours_of_rest_update ON pms_hours_of_rest IS
    'Update access: self-only (HOD/Captain cannot edit crew daily entries)';

-- ============================================================================
-- POLICY 4: DELETE (Denied for All)
-- ============================================================================

-- NO DELETE POLICY = deny all deletes
-- HoR records are audit trail, must be preserved for regulatory compliance
-- If soft delete needed, use UPDATE to set is_active = FALSE (future enhancement)

COMMENT ON TABLE pms_hours_of_rest IS
    'No DELETE policy: All HoR records preserved for audit trail (ILO/STCW compliance)';

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Verify policies created
DO $$
DECLARE
    policy_count INT;
    expected_policies TEXT[] := ARRAY['pms_hours_of_rest_select', 'pms_hours_of_rest_insert', 'pms_hours_of_rest_update'];
    policy_name TEXT;
BEGIN
    -- Count policies
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE tablename = 'pms_hours_of_rest';

    IF policy_count != 3 THEN
        RAISE WARNING 'Expected 3 policies, found %', policy_count;
    END IF;

    -- Verify each expected policy exists
    FOREACH policy_name IN ARRAY expected_policies
    LOOP
        PERFORM 1 FROM pg_policies
        WHERE tablename = 'pms_hours_of_rest'
            AND policyname = policy_name;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'Policy % not found', policy_name;
        END IF;
    END LOOP;

    RAISE NOTICE 'All precise RLS policies successfully created (3 policies)';
    RAISE NOTICE 'Policy model: deny-by-default, self-only mutations, HOD/Captain read-only';
END $$;

COMMIT;
