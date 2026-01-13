-- ================================================================================
-- MIGRATION: Add Storage RLS Policy for Documents Bucket
-- ================================================================================
-- Problem: Authenticated users cannot access files in 'documents' bucket
-- Root Cause: No RLS policy exists for 'documents' bucket
-- Impact: createSignedUrl() fails with "Object not found"
--
-- Fix: Add RLS policy allowing users to read files in their yacht folder
-- ================================================================================

-- Add RLS policy for documents bucket
-- Allow authenticated users to read files in their yacht's folder

-- Drop policy if it exists (idempotent)
DROP POLICY IF EXISTS "Users read yacht documents" ON storage.objects;

-- Create the policy
CREATE POLICY "Users read yacht documents"
ON storage.objects
FOR SELECT
TO authenticated
USING (
  bucket_id = 'documents'
  AND (storage.foldername(name))[1] = (
    SELECT yacht_id::text
    FROM auth_users_profiles
    WHERE id = auth.uid()
  )
);

-- Verify policy was created
DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM pg_policies
    WHERE schemaname = 'storage'
      AND tablename = 'objects'
      AND policyname = 'Users read yacht documents'
  ) THEN
    RAISE NOTICE '✅ Storage RLS policy created successfully';
  ELSE
    RAISE EXCEPTION '❌ Failed to create storage RLS policy';
  END IF;
END $$;

-- ================================================================================
-- NOTES
-- ================================================================================
-- This policy enforces yacht isolation at the storage bucket level:
-- - Users can only read files in folders matching their yacht_id
-- - Path format: documents/{yacht_id}/category/file.pdf
-- - First folder name must match user's yacht_id from auth_users_profiles
--
-- Why this is secure:
-- 1. auth.uid() returns authenticated user's ID from JWT
-- 2. auth_users_profiles lookup gets user's yacht_id
-- 3. storage.foldername(name)[1] extracts first folder from path
-- 4. Policy blocks access if folder != user's yacht
--
-- Why Supabase console worked but app didn't:
-- - Dashboard uses service_role (bypasses RLS)
-- - App uses authenticated JWT (respects RLS)
-- - Without this policy, all authenticated requests were blocked
-- ================================================================================
