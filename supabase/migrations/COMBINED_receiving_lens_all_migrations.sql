-- ============================================================================
-- MIGRATION: 20260128_101_receiving_helpers_if_missing.sql
-- PURPOSE: Verify canonical helpers exist for Receiving Lens v1
-- LENS: Receiving Lens v1
-- DATE: 2026-01-28
-- ============================================================================
-- REQUIRED HELPERS:
--   - public.is_hod(user_id, yacht_id)
--   - public.is_manager(user_id, yacht_id)
--   - public.get_user_yacht_id()
-- ============================================================================

DO $$
BEGIN
    -- Verify is_hod exists
    IF NOT EXISTS (
        SELECT 1 FROM pg_proc
        WHERE proname = 'is_hod'
          AND pronamespace = 'public'::regnamespace
    ) THEN
        RAISE EXCEPTION 'BLOCKER: public.is_hod() function missing - required for Receiving Lens RLS';
    END IF;

    -- Verify is_manager exists
    IF NOT EXISTS (
        SELECT 1 FROM pg_proc
        WHERE proname = 'is_manager'
          AND pronamespace = 'public'::regnamespace
    ) THEN
        RAISE EXCEPTION 'BLOCKER: public.is_manager() function missing - required for SIGNED actions';
    END IF;

    -- Verify get_user_yacht_id exists
    IF NOT EXISTS (
        SELECT 1 FROM pg_proc
        WHERE proname = 'get_user_yacht_id'
          AND pronamespace = 'public'::regnamespace
    ) THEN
        RAISE EXCEPTION 'BLOCKER: public.get_user_yacht_id() function missing - required for yacht isolation';
    END IF;

    RAISE NOTICE 'SUCCESS: All required helpers exist for Receiving Lens v1';
END $$;
-- ============================================================================
-- MIGRATION: 20260128_102_receiving_tables.sql
-- PURPOSE: Create Receiving Lens v1 tables
-- LENS: Receiving Lens v1
-- DATE: 2026-01-28
-- ============================================================================
-- TABLES:
--   1. pms_receiving (header)
--   2. pms_receiving_items (line items)
--   3. pms_receiving_documents (photos/PDFs linked to receiving)
--   4. pms_receiving_extractions (advisory OCR/extraction results)
-- ============================================================================

BEGIN;

-- ============================================================================
-- TABLE 1: pms_receiving (header)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.pms_receiving (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES public.yacht_registry(id) ON DELETE CASCADE,

    -- Vendor information
    vendor_name TEXT,
    vendor_reference TEXT,  -- invoice number, AWB, packing slip number

    -- Receipt metadata
    received_date DATE NOT NULL DEFAULT CURRENT_DATE,
    received_by UUID NOT NULL,  -- Who received/created this record
    status TEXT NOT NULL DEFAULT 'draft',

    -- Financial fields (set at acceptance)
    currency TEXT,
    subtotal NUMERIC(14,2),
    tax_total NUMERIC(14,2),
    total NUMERIC(14,2),

    -- Optional linkages
    linked_work_order_id UUID,  -- FK to pms_work_orders if exists
    notes TEXT,
    properties JSONB,

    -- Audit
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,  -- Same as received_by typically

    -- Status constraint (added in next migration)
    CONSTRAINT pms_receiving_status_check CHECK (
        status IN ('draft', 'in_review', 'accepted', 'rejected')
    )
);

COMMENT ON TABLE public.pms_receiving IS 'Receiving Lens v1: Header records for received invoices, packages, documents';
COMMENT ON COLUMN public.pms_receiving.vendor_reference IS 'Invoice number, AWB, packing slip, or other vendor reference';
COMMENT ON COLUMN public.pms_receiving.status IS 'Draft → in_review → accepted/rejected';
COMMENT ON COLUMN public.pms_receiving.properties IS 'Additional metadata (session_id, extracted_confidence, etc.)';

-- ============================================================================
-- TABLE 2: pms_receiving_items (line items)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.pms_receiving_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES public.yacht_registry(id) ON DELETE CASCADE,
    receiving_id UUID NOT NULL REFERENCES public.pms_receiving(id) ON DELETE CASCADE,

    -- Part linkage
    part_id UUID,  -- FK to pms_parts if exists

    -- Item details
    description TEXT,
    quantity_expected NUMERIC(12,2),
    quantity_received NUMERIC(12,2) NOT NULL DEFAULT 0,

    -- Pricing
    unit_price NUMERIC(14,4),
    currency TEXT,

    -- Metadata
    properties JSONB,

    -- Audit
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Quantity constraint (non-negative)
    CONSTRAINT pms_receiving_items_qty_check CHECK (quantity_received >= 0)
);

COMMENT ON TABLE public.pms_receiving_items IS 'Receiving Lens v1: Line items for received goods';
COMMENT ON COLUMN public.pms_receiving_items.description IS 'Part name or description; required if part_id is null';
COMMENT ON COLUMN public.pms_receiving_items.quantity_expected IS 'Expected quantity from PO/order; null if ad-hoc';
COMMENT ON COLUMN public.pms_receiving_items.quantity_received IS 'Actual quantity received';

-- ============================================================================
-- TABLE 3: pms_receiving_documents (attachments)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.pms_receiving_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES public.yacht_registry(id) ON DELETE CASCADE,
    receiving_id UUID NOT NULL REFERENCES public.pms_receiving(id) ON DELETE CASCADE,

    -- Document linkage
    document_id UUID NOT NULL,  -- FK to doc_metadata

    -- Document metadata
    doc_type TEXT,  -- 'invoice', 'packing_slip', 'photo'
    comment TEXT,   -- inline comment about this attachment

    -- Audit
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.pms_receiving_documents IS 'Receiving Lens v1: Photos and PDFs attached to receiving records';
COMMENT ON COLUMN public.pms_receiving_documents.document_id IS 'Foreign key to doc_metadata.id';
COMMENT ON COLUMN public.pms_receiving_documents.doc_type IS 'Document type: invoice, packing_slip, photo';
COMMENT ON COLUMN public.pms_receiving_documents.comment IS 'Inline comment from attach_receiving_image_with_comment action';

-- ============================================================================
-- TABLE 4: pms_receiving_extractions (advisory OCR results)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.pms_receiving_extractions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES public.yacht_registry(id) ON DELETE CASCADE,
    receiving_id UUID NOT NULL REFERENCES public.pms_receiving(id) ON DELETE CASCADE,

    -- Extraction source
    source_document_id UUID NOT NULL,  -- FK to doc_metadata

    -- Extraction results (advisory only)
    payload JSONB NOT NULL,  -- {vendor_name, total, line_items: [], confidences: {}, flags: []}

    -- Audit
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.pms_receiving_extractions IS 'Receiving Lens v1: Advisory OCR/extraction results (non-authoritative)';
COMMENT ON COLUMN public.pms_receiving_extractions.payload IS 'Extracted fields with confidence scores; advisory only - handlers must not auto-apply';
COMMENT ON COLUMN public.pms_receiving_extractions.source_document_id IS 'Document that was scanned/extracted';

COMMIT;

DO $$
BEGIN
    RAISE NOTICE 'SUCCESS: Receiving Lens v1 tables created (pms_receiving, pms_receiving_items, pms_receiving_documents, pms_receiving_extractions)';
END $$;
-- ============================================================================
-- MIGRATION: 20260128_103_receiving_checks.sql
-- PURPOSE: Add check constraints and validation rules for Receiving Lens v1
-- LENS: Receiving Lens v1
-- DATE: 2026-01-28
-- ============================================================================
-- CONSTRAINTS:
--   1. pms_receiving.status enum (draft, in_review, accepted, rejected)
--   2. pms_receiving_items.quantity_received >= 0
--   3. At least one of description or part_id must be present
-- ============================================================================

BEGIN;

-- ============================================================================
-- Constraint already added in table creation, but verify it exists
-- ============================================================================
DO $$
BEGIN
    -- Verify status constraint exists on pms_receiving
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'pms_receiving'::regclass
          AND conname = 'pms_receiving_status_check'
    ) THEN
        ALTER TABLE pms_receiving
        ADD CONSTRAINT pms_receiving_status_check CHECK (
            status IN ('draft', 'in_review', 'accepted', 'rejected')
        );
        RAISE NOTICE 'Added pms_receiving.status CHECK constraint';
    ELSE
        RAISE NOTICE 'pms_receiving.status CHECK constraint already exists';
    END IF;

    -- Verify quantity constraint exists on pms_receiving_items
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'pms_receiving_items'::regclass
          AND conname = 'pms_receiving_items_qty_check'
    ) THEN
        ALTER TABLE pms_receiving_items
        ADD CONSTRAINT pms_receiving_items_qty_check CHECK (quantity_received >= 0);
        RAISE NOTICE 'Added pms_receiving_items.quantity_received CHECK constraint';
    ELSE
        RAISE NOTICE 'pms_receiving_items.quantity_received CHECK constraint already exists';
    END IF;

    RAISE NOTICE 'SUCCESS: All check constraints verified for Receiving Lens v1';
END $$;

COMMIT;
-- ============================================================================
-- MIGRATION: 20260128_104_receiving_rls.sql
-- PURPOSE: Enable RLS and create policies for Receiving Lens v1
-- LENS: Receiving Lens v1
-- DATE: 2026-01-28
-- ============================================================================
-- POLICIES:
--   - Deny-by-default RLS on all receiving tables
--   - SELECT: yacht-scoped for all crew
--   - INSERT/UPDATE: HOD+ only, yacht-scoped
--   - Service role bypass
-- ============================================================================

BEGIN;

-- ============================================================================
-- ENABLE RLS
-- ============================================================================
ALTER TABLE pms_receiving ENABLE ROW LEVEL SECURITY;
ALTER TABLE pms_receiving_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE pms_receiving_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE pms_receiving_extractions ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- TABLE: pms_receiving
-- ============================================================================
DROP POLICY IF EXISTS "receiving_select_yacht" ON pms_receiving;
DROP POLICY IF EXISTS "receiving_insert_hod" ON pms_receiving;
DROP POLICY IF EXISTS "receiving_update_hod" ON pms_receiving;
DROP POLICY IF EXISTS "receiving_service_role" ON pms_receiving;

-- SELECT: All crew can view their yacht's receiving records
CREATE POLICY "receiving_select_yacht"
ON pms_receiving
FOR SELECT TO authenticated
USING (yacht_id = public.get_user_yacht_id());

-- INSERT: HOD+ can create receiving records
CREATE POLICY "receiving_insert_hod"
ON pms_receiving
FOR INSERT TO authenticated
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
    AND public.is_hod(auth.uid(), public.get_user_yacht_id())
);

-- UPDATE: HOD+ can update receiving records
CREATE POLICY "receiving_update_hod"
ON pms_receiving
FOR UPDATE TO authenticated
USING (
    yacht_id = public.get_user_yacht_id()
    AND public.is_hod(auth.uid(), public.get_user_yacht_id())
)
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
);

-- Service role bypass
CREATE POLICY "receiving_service_role"
ON pms_receiving
FOR ALL TO service_role
USING (true) WITH CHECK (true);

-- ============================================================================
-- TABLE: pms_receiving_items
-- ============================================================================
DROP POLICY IF EXISTS "receiving_items_select_yacht" ON pms_receiving_items;
DROP POLICY IF EXISTS "receiving_items_insert_hod" ON pms_receiving_items;
DROP POLICY IF EXISTS "receiving_items_update_hod" ON pms_receiving_items;
DROP POLICY IF EXISTS "receiving_items_service_role" ON pms_receiving_items;

-- SELECT: All crew can view their yacht's line items
CREATE POLICY "receiving_items_select_yacht"
ON pms_receiving_items
FOR SELECT TO authenticated
USING (yacht_id = public.get_user_yacht_id());

-- INSERT: HOD+ can add line items
CREATE POLICY "receiving_items_insert_hod"
ON pms_receiving_items
FOR INSERT TO authenticated
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
    AND public.is_hod(auth.uid(), public.get_user_yacht_id())
);

-- UPDATE: HOD+ can update line items
CREATE POLICY "receiving_items_update_hod"
ON pms_receiving_items
FOR UPDATE TO authenticated
USING (
    yacht_id = public.get_user_yacht_id()
    AND public.is_hod(auth.uid(), public.get_user_yacht_id())
)
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
);

-- Service role bypass
CREATE POLICY "receiving_items_service_role"
ON pms_receiving_items
FOR ALL TO service_role
USING (true) WITH CHECK (true);

-- ============================================================================
-- TABLE: pms_receiving_documents
-- ============================================================================
DROP POLICY IF EXISTS "receiving_documents_select_yacht" ON pms_receiving_documents;
DROP POLICY IF EXISTS "receiving_documents_insert_hod" ON pms_receiving_documents;
DROP POLICY IF EXISTS "receiving_documents_service_role" ON pms_receiving_documents;

-- SELECT: All crew can view their yacht's documents
CREATE POLICY "receiving_documents_select_yacht"
ON pms_receiving_documents
FOR SELECT TO authenticated
USING (yacht_id = public.get_user_yacht_id());

-- INSERT: HOD+ can attach documents
CREATE POLICY "receiving_documents_insert_hod"
ON pms_receiving_documents
FOR INSERT TO authenticated
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
    AND public.is_hod(auth.uid(), public.get_user_yacht_id())
);

-- Service role bypass
CREATE POLICY "receiving_documents_service_role"
ON pms_receiving_documents
FOR ALL TO service_role
USING (true) WITH CHECK (true);

-- ============================================================================
-- TABLE: pms_receiving_extractions
-- ============================================================================
DROP POLICY IF EXISTS "receiving_extractions_select_yacht" ON pms_receiving_extractions;
DROP POLICY IF EXISTS "receiving_extractions_insert_hod" ON pms_receiving_extractions;
DROP POLICY IF EXISTS "receiving_extractions_service_role" ON pms_receiving_extractions;

-- SELECT: All crew can view their yacht's extraction results
CREATE POLICY "receiving_extractions_select_yacht"
ON pms_receiving_extractions
FOR SELECT TO authenticated
USING (yacht_id = public.get_user_yacht_id());

-- INSERT: HOD+ can create extraction records (via extract_receiving_candidates)
CREATE POLICY "receiving_extractions_insert_hod"
ON pms_receiving_extractions
FOR INSERT TO authenticated
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
    AND public.is_hod(auth.uid(), public.get_user_yacht_id())
);

-- Service role bypass
CREATE POLICY "receiving_extractions_service_role"
ON pms_receiving_extractions
FOR ALL TO service_role
USING (true) WITH CHECK (true);

COMMIT;

-- ============================================================================
-- VERIFICATION
-- ============================================================================
DO $$
DECLARE
    rls_count INTEGER;
    policy_count INTEGER;
BEGIN
    -- Verify RLS enabled
    SELECT COUNT(*) INTO rls_count
    FROM pg_class
    WHERE relname IN ('pms_receiving', 'pms_receiving_items', 'pms_receiving_documents', 'pms_receiving_extractions')
      AND relrowsecurity = true;

    IF rls_count != 4 THEN
        RAISE EXCEPTION 'RLS not enabled on all Receiving tables (expected 4, got %)', rls_count;
    END IF;

    -- Verify policy count
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE tablename IN ('pms_receiving', 'pms_receiving_items', 'pms_receiving_documents', 'pms_receiving_extractions');

    RAISE NOTICE 'SUCCESS: RLS enabled on 4 tables, % policies created', policy_count;
END $$;
-- ============================================================================
-- MIGRATION: 20260128_105_receiving_indexes.sql
-- PURPOSE: Create performance indexes for Receiving Lens v1
-- LENS: Receiving Lens v1
-- DATE: 2026-01-28
-- ============================================================================
-- INDEXES:
--   - Primary lookups: yacht_id + received_date, yacht_id + status
--   - Foreign keys: receiving_id, document_id
--   - Search fields: vendor_reference
-- ============================================================================

BEGIN;

-- ============================================================================
-- TABLE: pms_receiving
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_receiving_yacht_date
    ON pms_receiving(yacht_id, received_date DESC);

CREATE INDEX IF NOT EXISTS idx_receiving_yacht_status
    ON pms_receiving(yacht_id, status);

CREATE INDEX IF NOT EXISTS idx_receiving_yacht_vendor_ref
    ON pms_receiving(yacht_id, vendor_reference);

CREATE INDEX IF NOT EXISTS idx_receiving_work_order
    ON pms_receiving(linked_work_order_id)
    WHERE linked_work_order_id IS NOT NULL;

-- ============================================================================
-- TABLE: pms_receiving_items
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_receiving_items_yacht_receiving
    ON pms_receiving_items(yacht_id, receiving_id);

CREATE INDEX IF NOT EXISTS idx_receiving_items_yacht_part
    ON pms_receiving_items(yacht_id, part_id)
    WHERE part_id IS NOT NULL;

-- ============================================================================
-- TABLE: pms_receiving_documents
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_receiving_documents_yacht_receiving
    ON pms_receiving_documents(yacht_id, receiving_id);

CREATE INDEX IF NOT EXISTS idx_receiving_documents_yacht_doctype
    ON pms_receiving_documents(yacht_id, doc_type)
    WHERE doc_type IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_receiving_documents_document_id
    ON pms_receiving_documents(document_id);

-- ============================================================================
-- TABLE: pms_receiving_extractions
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_receiving_extractions_yacht_receiving
    ON pms_receiving_extractions(yacht_id, receiving_id);

CREATE INDEX IF NOT EXISTS idx_receiving_extractions_source_doc
    ON pms_receiving_extractions(source_document_id);

COMMIT;

DO $$
DECLARE
    index_count INTEGER;
BEGIN
    -- Count indexes created
    SELECT COUNT(*) INTO index_count
    FROM pg_indexes
    WHERE schemaname = 'public'
      AND tablename IN ('pms_receiving', 'pms_receiving_items', 'pms_receiving_documents', 'pms_receiving_extractions')
      AND indexname LIKE 'idx_receiving%';

    RAISE NOTICE 'SUCCESS: Created/verified % indexes for Receiving Lens v1', index_count;
END $$;
-- ============================================================================
-- MIGRATION: 20260128_111_documents_storage_policies_receiving.sql
-- PURPOSE: Verify storage policies for 'documents' bucket (Receiving Lens v1)
-- LENS: Receiving Lens v1
-- DATE: 2026-01-28
-- ============================================================================
-- STORAGE PATHS:
--   - PDFs: {yacht_id}/receiving/{receiving_id}/{filename}
--   - Bucket: documents
-- POLICIES:
--   - INSERT: HOD+ for yacht path
--   - UPDATE: HOD+ for yacht path
--   - DELETE: Manager only for yacht path
-- NOTE: These policies should already exist from Certificate Lens v2
-- ============================================================================

DO $$
DECLARE
    policy_count INTEGER;
BEGIN
    -- Check if required storage policies exist
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE schemaname = 'storage'
      AND tablename = 'objects'
      AND policyname IN (
          'hod_insert_yacht_documents',
          'hod_update_yacht_documents',
          'manager_delete_yacht_documents'
      );

    IF policy_count < 3 THEN
        RAISE WARNING 'BLOCKER: Missing storage policies for documents bucket (found % of 3). Run 202601251011_documents_storage_write_policies.sql', policy_count;
        RAISE EXCEPTION 'Storage policies missing for documents bucket - Receiving Lens requires these for PDF upload';
    END IF;

    RAISE NOTICE 'SUCCESS: Storage policies verified for documents bucket (% policies found)', policy_count;
    RAISE NOTICE '  - Receiving Lens can upload PDFs to {yacht_id}/receiving/{receiving_id}/{filename}';
END $$;
-- ============================================================================
-- MIGRATION: 20260128_112_receiving_images_storage_policies.sql
-- PURPOSE: Create storage policies for 'pms-receiving-images' bucket
-- LENS: Receiving Lens v1
-- DATE: 2026-01-28
-- ============================================================================
-- STORAGE PATHS:
--   - Photos: {yacht_id}/receiving/{receiving_id}/{filename}
--   - Bucket: pms-receiving-images
-- POLICIES:
--   - INSERT: HOD+ for yacht path
--   - UPDATE: HOD+ for yacht path
--   - DELETE: Manager only for yacht path
--   - SELECT: All crew for yacht path
-- ============================================================================

BEGIN;

-- ============================================================================
-- STEP 1: Ensure bucket exists (informational - buckets created via UI/API)
-- ============================================================================
-- NOTE: Buckets are created via Supabase Storage UI or API
-- This migration assumes 'pms-receiving-images' bucket exists
-- If not, handler will fail with 404 bucket error

-- ============================================================================
-- STEP 2: DROP existing policies for idempotency
-- ============================================================================
DROP POLICY IF EXISTS "hod_insert_receiving_images" ON storage.objects;
DROP POLICY IF EXISTS "hod_update_receiving_images" ON storage.objects;
DROP POLICY IF EXISTS "manager_delete_receiving_images" ON storage.objects;
DROP POLICY IF EXISTS "crew_select_receiving_images" ON storage.objects;

-- ============================================================================
-- STEP 3: SELECT policy - All crew can view their yacht's receiving images
-- ============================================================================
CREATE POLICY "crew_select_receiving_images"
ON storage.objects
FOR SELECT TO authenticated
USING (
    bucket_id = 'pms-receiving-images'
    AND (storage.foldername(name))[1] = (
        SELECT yacht_id::text FROM auth_users_profiles WHERE id = auth.uid()
    )
);

-- ============================================================================
-- STEP 4: INSERT policy - HOD can upload to their yacht's receiving path
-- ============================================================================
-- Path convention: pms-receiving-images/{yacht_id}/receiving/{receiving_id}/{filename}
-- storage.foldername(name) is 1-indexed, so [1] extracts yacht_id
-- ============================================================================
CREATE POLICY "hod_insert_receiving_images"
ON storage.objects
FOR INSERT TO authenticated
WITH CHECK (
    bucket_id = 'pms-receiving-images'
    AND (storage.foldername(name))[1] = (
        SELECT yacht_id::text FROM auth_users_profiles WHERE id = auth.uid()
    )
    AND public.is_hod(auth.uid(), (
        SELECT yacht_id FROM auth_users_profiles WHERE id = auth.uid()
    ))
);

-- ============================================================================
-- STEP 5: UPDATE policy - HOD can update their yacht's receiving images
-- ============================================================================
CREATE POLICY "hod_update_receiving_images"
ON storage.objects
FOR UPDATE TO authenticated
USING (
    bucket_id = 'pms-receiving-images'
    AND (storage.foldername(name))[1] = (
        SELECT yacht_id::text FROM auth_users_profiles WHERE id = auth.uid()
    )
)
WITH CHECK (
    bucket_id = 'pms-receiving-images'
    AND (storage.foldername(name))[1] = (
        SELECT yacht_id::text FROM auth_users_profiles WHERE id = auth.uid()
    )
    AND public.is_hod(auth.uid(), (
        SELECT yacht_id FROM auth_users_profiles WHERE id = auth.uid()
    ))
);

-- ============================================================================
-- STEP 6: DELETE policy - Manager only can delete yacht receiving images
-- ============================================================================
CREATE POLICY "manager_delete_receiving_images"
ON storage.objects
FOR DELETE TO authenticated
USING (
    bucket_id = 'pms-receiving-images'
    AND (storage.foldername(name))[1] = (
        SELECT yacht_id::text FROM auth_users_profiles WHERE id = auth.uid()
    )
    AND public.is_manager(auth.uid(), public.get_user_yacht_id())
);

COMMIT;

-- ============================================================================
-- VERIFICATION
-- ============================================================================
DO $$
DECLARE
    policy_count INTEGER;
BEGIN
    -- Check policy count for pms-receiving-images bucket
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE tablename = 'objects'
      AND schemaname = 'storage'
      AND policyname LIKE '%receiving_images%';

    IF policy_count < 4 THEN
        RAISE WARNING 'Expected 4 policies for pms-receiving-images bucket, found %', policy_count;
    END IF;

    RAISE NOTICE 'SUCCESS: Storage policies for pms-receiving-images bucket created (% policies)', policy_count;
    RAISE NOTICE '  - Path format: {yacht_id}/receiving/{receiving_id}/{filename}';
    RAISE NOTICE '  - SELECT: All crew (yacht-scoped)';
    RAISE NOTICE '  - INSERT/UPDATE: HOD+ (yacht-scoped)';
    RAISE NOTICE '  - DELETE: Manager only';
END $$;
-- ============================================================================
-- MIGRATION: 20260128_113_doc_metadata_receiving_rls.sql
-- PURPOSE: Verify doc_metadata RLS policies exist for Receiving Lens v1
-- LENS: Receiving Lens v1
-- DATE: 2026-01-28
-- ============================================================================
-- REQUIRED POLICIES:
--   - crew_insert_doc_metadata (INSERT for authenticated, yacht-scoped)
--   - hod_update_doc_metadata (UPDATE for HOD, yacht-scoped)
--   - manager_delete_doc_metadata (DELETE for manager only)
-- NOTE: These should already exist from Certificate Lens v2
-- ============================================================================

DO $$
DECLARE
    policy_count INTEGER;
    rls_enabled BOOLEAN;
BEGIN
    -- Check if doc_metadata table exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'doc_metadata'
          AND table_schema = 'public'
    ) THEN
        RAISE WARNING 'doc_metadata table does not exist - skipping migration';
        RETURN;
    END IF;

    -- Verify RLS is enabled
    SELECT relrowsecurity INTO rls_enabled
    FROM pg_class
    WHERE relname = 'doc_metadata'
      AND relnamespace = 'public'::regnamespace;

    IF NOT rls_enabled THEN
        RAISE EXCEPTION 'BLOCKER: RLS not enabled on doc_metadata table';
    END IF;

    -- Check required policies exist
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE tablename = 'doc_metadata'
      AND policyname IN (
          'crew_insert_doc_metadata',
          'hod_update_doc_metadata',
          'manager_delete_doc_metadata'
      );

    IF policy_count < 3 THEN
        RAISE WARNING 'BLOCKER: Missing doc_metadata policies (found % of 3). Run 202601251012_doc_metadata_write_rls.sql', policy_count;
        RAISE EXCEPTION 'doc_metadata policies missing - Receiving Lens requires these for document linkage';
    END IF;

    RAISE NOTICE 'SUCCESS: doc_metadata RLS verified (RLS enabled, % policies found)', policy_count;
    RAISE NOTICE '  - Receiving Lens can link documents via attach_receiving_image_with_comment';
END $$;
