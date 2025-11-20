-- ============================================================================
-- Migration: Documents Metadata Table RLS Policies
-- Version: 20250101000010
-- Description: Row-Level Security for documents table (metadata records)
-- ============================================================================
--
-- CRITICAL: These policies enforce yacht-based isolation for document metadata
--
-- Requirements:
-- 1. SELECT: Users can ONLY see documents from their yacht
-- 2. INSERT: Service role (ingestion) can insert new documents
-- 3. UPDATE: Service role (indexing) can update processing fields
-- 4. DELETE: Service role only (no user deletion)
--
-- The documents table was created in migration 20250101000001 (initial_schema_v2.sql)
-- This migration ONLY adds RLS policies specific to storage operations
-- ============================================================================

-- NOTE: RLS is already enabled on documents table from migration 002
-- This migration adds ADDITIONAL policies specific to storage/ingestion workflow

-- ============================================================================
-- POLICY: SELECT (Read Access)
-- Already exists from migration 002: "Users can view documents"
-- Verifying it matches storage requirements
-- ============================================================================

-- This policy already exists from RLS migration 002:
-- CREATE POLICY "Users can view documents"
--   ON documents FOR SELECT
--   USING (yacht_id = get_user_yacht_id());

-- No changes needed - this policy correctly enforces yacht isolation

-- ============================================================================
-- POLICY: INSERT (Ingestion Service)
-- Already exists from migration 002: "System can insert documents"
-- Verifying it allows service_role
-- ============================================================================

-- This policy already exists from RLS migration 002:
-- CREATE POLICY "System can insert documents"
--   ON documents FOR INSERT
--   WITH CHECK (yacht_id = get_user_yacht_id());

-- This policy is TOO RESTRICTIVE for service_role ingestion
-- Service role needs to insert documents for ANY yacht
-- Let's add a specific policy for service_role

DROP POLICY IF EXISTS "Service role can insert documents" ON documents;

CREATE POLICY "Service role can insert documents"
ON documents
FOR INSERT
TO service_role
WITH CHECK (true);  -- Service role can insert for any yacht

COMMENT ON POLICY "Service role can insert documents" ON documents IS
  'Service role (n8n ingestion) can insert document metadata for any yacht';

-- ============================================================================
-- POLICY: UPDATE (Indexing Service)
-- Service role can update indexed status and embedding job fields
-- ============================================================================

-- Existing policy from migration 002 allows managers to manage documents
-- We need to ensure service_role can update processing fields

DROP POLICY IF EXISTS "Service role can update document processing" ON documents;

CREATE POLICY "Service role can update document processing"
ON documents
FOR UPDATE
TO service_role
USING (true)
WITH CHECK (true);

COMMENT ON POLICY "Service role can update document processing" ON documents IS
  'Service role (indexing pipeline) can update processing fields (indexed, indexed_at)';

-- ============================================================================
-- POLICY: DELETE (Service Role Only)
-- Existing "Managers can manage documents" policy from migration 002
-- Adding explicit service_role delete policy
-- ============================================================================

-- Managers can delete (existing policy from migration 002)
-- Adding service_role explicit permission

DROP POLICY IF EXISTS "Service role can delete documents" ON documents;

CREATE POLICY "Service role can delete documents"
ON documents
FOR DELETE
TO service_role
USING (true);

COMMENT ON POLICY "Service role can delete documents" ON documents IS
  'Service role can delete document metadata records';

-- ============================================================================
-- ADDITIONAL HELPER: Document access by storage_path
-- Function to check if user can access document by storage_path
-- ============================================================================

CREATE OR REPLACE FUNCTION public.can_access_document_by_path(doc_storage_path text)
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
STABLE
AS $$
  -- Check if user's yacht_id matches the yacht_id in documents table
  SELECT EXISTS (
    SELECT 1
    FROM documents d
    WHERE d.storage_path = doc_storage_path
      AND d.yacht_id = get_user_yacht_id()
  );
$$;

COMMENT ON FUNCTION public.can_access_document_by_path IS
  'Check if authenticated user can access document by storage_path';

GRANT EXECUTE ON FUNCTION public.can_access_document_by_path(text) TO authenticated;

-- ============================================================================
-- VERIFICATION QUERIES (run separately to test)
-- ============================================================================

-- List all policies on documents table:
-- SELECT policyname, permissive, roles, cmd
-- FROM pg_policies
-- WHERE schemaname = 'public' AND tablename = 'documents'
-- ORDER BY policyname;

-- Expected policies (from migration 002 + this migration):
-- 1. "Users can view documents" (SELECT, authenticated) - from migration 002
-- 2. "System can insert documents" (INSERT, authenticated) - from migration 002
-- 3. "Managers can manage documents" (ALL, authenticated) - from migration 002
-- 4. "Service role can insert documents" (INSERT, service_role) - NEW
-- 5. "Service role can update document processing" (UPDATE, service_role) - NEW
-- 6. "Service role can delete documents" (DELETE, service_role) - NEW

-- Test document access:
-- SELECT * FROM documents WHERE yacht_id = get_user_yacht_id();
-- Should only return documents from user's yacht
