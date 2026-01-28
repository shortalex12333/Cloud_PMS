-- Shopping List RLS Policy Fix - Enforce Role-Based Access
-- Date: 2026-01-28
-- Issue: CREW can approve/reject/promote due to overly permissive UPDATE policies
-- Fix: Drop broad policies, add role-specific UPDATE policies

-- =============================================================================
-- PHASE 1: Clean up overlapping/redundant policies
-- =============================================================================

-- Drop overly permissive UPDATE policies
DROP POLICY IF EXISTS "crew_update_shopping" ON pms_shopping_list_items;
DROP POLICY IF EXISTS "Users can create shopping list items" ON pms_shopping_list_items; -- redundant
DROP POLICY IF EXISTS "Users can view shopping list items for their yacht" ON pms_shopping_list_items; -- redundant

-- Keep these good policies:
-- ✅ "HOD can update shopping list items" - good but we'll replace with more specific
-- ✅ "crew_insert_shopping" - good INSERT policy
-- ✅ "operational_crew_insert_shopping" - good INSERT policy
-- ✅ "crew_select_own_yacht_shopping" - good SELECT policy
-- ✅ "Service role has full access to shopping list" - needed
-- ✅ "service_role_full_access_shopping" - needed
-- ✅ "service_role_shopping" - needed

-- Drop the broad HOD policy (we'll replace with specific ones)
DROP POLICY IF EXISTS "HOD can update shopping list items" ON pms_shopping_list_items;
DROP POLICY IF EXISTS "hod_update_shopping" ON pms_shopping_list_items;

-- =============================================================================
-- PHASE 2: Create role-specific UPDATE policies
-- =============================================================================

-- Policy 1: CREW can update their OWN items ONLY if status=candidate (before review)
CREATE POLICY "crew_update_own_candidate_items"
ON pms_shopping_list_items
FOR UPDATE
TO authenticated
USING (
    yacht_id = public.get_user_yacht_id()
    AND created_by = auth.uid()
    AND status = 'candidate'
)
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
    AND status = 'candidate'
);

-- Policy 2: HOD can approve items (transition to under_review or approved)
CREATE POLICY "hod_approve_shopping_items"
ON pms_shopping_list_items
FOR UPDATE
TO authenticated
USING (
    yacht_id = public.get_user_yacht_id()
    AND public.is_hod(auth.uid(), public.get_user_yacht_id())
    AND (
        -- Allow updating to under_review or approved status
        status IN ('candidate', 'under_review', 'approved')
        OR approved_by IS NOT NULL  -- Updating approval fields
    )
)
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
);

-- Policy 3: HOD can reject items (set rejected_at field)
CREATE POLICY "hod_reject_shopping_items"
ON pms_shopping_list_items
FOR UPDATE
TO authenticated
USING (
    yacht_id = public.get_user_yacht_id()
    AND public.is_hod(auth.uid(), public.get_user_yacht_id())
    AND (
        status IN ('candidate', 'under_review')
        OR rejected_by IS NOT NULL  -- Updating rejection fields
    )
)
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
);

-- Policy 4: ENGINEERS can promote candidates to parts (set promoted_by field)
CREATE POLICY "engineer_promote_shopping_items"
ON pms_shopping_list_items
FOR UPDATE
TO authenticated
USING (
    yacht_id = public.get_user_yacht_id()
    AND public.is_engineer(auth.uid(), public.get_user_yacht_id())
    AND (
        is_candidate_part = true
        OR promoted_by IS NOT NULL  -- Updating promotion fields
    )
)
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
);

-- =============================================================================
-- PHASE 3: Verification queries (commented out for migration)
-- =============================================================================

-- To verify policies after migration:
/*
-- 1. List all policies
SELECT
    policyname,
    cmd,
    roles,
    qual as "USING clause",
    with_check as "WITH CHECK clause"
FROM pg_policies
WHERE tablename = 'pms_shopping_list_items'
ORDER BY cmd, policyname;

-- 2. Test CREW can create (should work)
-- SET ROLE authenticated;
-- SET request.jwt.claims TO '{"sub": "crew-user-id", "yacht_id": "test-yacht-id"}';
-- INSERT INTO pms_shopping_list_items (id, yacht_id, part_name, quantity_requested, source_type, status, created_by, created_at, updated_at)
-- VALUES (gen_random_uuid(), get_user_yacht_id(), 'Test Part', 1, 'manual_add', 'candidate', auth.uid(), NOW(), NOW());

-- 3. Test CREW CANNOT approve (should fail with RLS error)
-- UPDATE pms_shopping_list_items SET status = 'approved', approved_by = auth.uid() WHERE id = '...';
-- Expected: 0 rows updated (blocked by RLS)

-- 4. Test HOD CAN approve (should work)
-- SET request.jwt.claims TO '{"sub": "hod-user-id", "yacht_id": "test-yacht-id", "role": "chief_engineer"}';
-- UPDATE pms_shopping_list_items SET status = 'approved', approved_by = auth.uid() WHERE id = '...';
-- Expected: 1 row updated

-- 5. Test ENGINEER CAN promote (should work)
-- SET request.jwt.claims TO '{"sub": "engineer-user-id", "yacht_id": "test-yacht-id", "role": "chief_engineer"}';
-- UPDATE pms_shopping_list_items SET promoted_by = auth.uid(), candidate_promoted_to_part_id = '...' WHERE id = '...';
-- Expected: 1 row updated
*/

-- =============================================================================
-- MIGRATION COMPLETE
-- =============================================================================

-- Expected test results after this migration:
-- ✅ CREW create_shopping_list_item: 200 OK
-- ✅ CREW approve_shopping_list_item: 403 (RLS blocks, returns 0 rows)
-- ✅ CREW reject_shopping_list_item: 403 (RLS blocks, returns 0 rows)
-- ✅ CREW promote_candidate_to_part: 403 (RLS blocks, returns 0 rows)
-- ✅ HOD approve_shopping_list_item: 200 OK
-- ✅ HOD reject_shopping_list_item: 200 OK
-- ✅ ENGINEER promote_candidate_to_part: 200 OK
