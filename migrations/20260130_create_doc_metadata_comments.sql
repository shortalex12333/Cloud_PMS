-- =====================================================
-- Migration: Create Document Comments Table
-- Created: 2026-01-30
-- Pattern: Mirrors pms_attachment_comments for Document Lens
-- Scope: Document-level comments only (MVP)
-- =====================================================

-- Drop if exists for idempotency
DROP TABLE IF EXISTS public.doc_metadata_comments CASCADE;

CREATE TABLE public.doc_metadata_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL,
    document_id UUID NOT NULL REFERENCES public.doc_metadata(id) ON DELETE CASCADE,

    -- Comment content
    comment TEXT NOT NULL,

    -- Author tracking
    created_by UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Edit tracking
    updated_by UUID,
    updated_at TIMESTAMPTZ,

    -- Soft delete
    deleted_by UUID,
    deleted_at TIMESTAMPTZ,

    -- Department context (cached at creation for RLS)
    author_department VARCHAR(100),

    -- Threading support (future: page-level comments)
    parent_comment_id UUID REFERENCES public.doc_metadata_comments(id) ON DELETE CASCADE,

    -- Metadata (extensible)
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Constraints
    CONSTRAINT chk_comment_not_empty CHECK (LENGTH(TRIM(comment)) > 0),
    CONSTRAINT chk_valid_department CHECK (
        author_department IS NULL OR author_department IN (
            'technical', 'deck', 'interior', 'galley', 'engineering', 'bridge'
        )
    )
);

-- =====================================================
-- Indexes
-- =====================================================

-- Primary lookup: comments for a document
CREATE INDEX idx_doc_comments_document_id
    ON public.doc_metadata_comments(document_id);

-- Yacht isolation
CREATE INDEX idx_doc_comments_yacht_id
    ON public.doc_metadata_comments(yacht_id);

-- Chronological ordering
CREATE INDEX idx_doc_comments_created_at
    ON public.doc_metadata_comments(created_at DESC);

-- Active comments only (soft delete filter)
CREATE INDEX idx_doc_comments_active
    ON public.doc_metadata_comments(document_id, created_at)
    WHERE deleted_at IS NULL;

-- Threading (future use)
CREATE INDEX idx_doc_comments_parent
    ON public.doc_metadata_comments(parent_comment_id)
    WHERE parent_comment_id IS NOT NULL;

-- =====================================================
-- RLS Policies
-- =====================================================

ALTER TABLE public.doc_metadata_comments ENABLE ROW LEVEL SECURITY;

-- SELECT: Users can read comments if they have access to yacht
CREATE POLICY "doc_comments_select"
ON public.doc_metadata_comments
FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM public.auth_users_roles aur
        WHERE aur.user_id = auth.uid()
        AND aur.yacht_id = doc_metadata_comments.yacht_id
    )
    AND deleted_at IS NULL
);

-- INSERT: Users can create comments on documents they can access
CREATE POLICY "doc_comments_insert"
ON public.doc_metadata_comments
FOR INSERT
WITH CHECK (
    EXISTS (
        SELECT 1 FROM public.auth_users_roles aur
        WHERE aur.user_id = auth.uid()
        AND aur.yacht_id = doc_metadata_comments.yacht_id
    )
    AND EXISTS (
        SELECT 1 FROM public.doc_metadata doc
        WHERE doc.id = doc_metadata_comments.document_id
        AND doc.yacht_id = doc_metadata_comments.yacht_id
        AND doc.deleted_at IS NULL
    )
    AND created_by = auth.uid()
);

-- UPDATE: Users can edit own comments OR admins
CREATE POLICY "doc_comments_update"
ON public.doc_metadata_comments
FOR UPDATE
USING (
    EXISTS (
        SELECT 1 FROM public.auth_users_roles aur
        WHERE aur.user_id = auth.uid()
        AND aur.yacht_id = doc_metadata_comments.yacht_id
    )
    AND deleted_at IS NULL
    AND (
        created_by = auth.uid()
        OR EXISTS (
            SELECT 1 FROM public.auth_users_roles aur
            WHERE aur.user_id = auth.uid()
            AND aur.yacht_id = doc_metadata_comments.yacht_id
            AND aur.role IN ('admin', 'captain', 'chief_engineer', 'manager')
        )
    )
)
WITH CHECK (
    updated_by = auth.uid()
);

-- DELETE: Soft delete only via UPDATE (no hard delete policy)

-- =====================================================
-- Trigger: Auto-populate Department from User Role
-- =====================================================

CREATE OR REPLACE FUNCTION public.trg_populate_doc_comment_department()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_user_role VARCHAR(100);
BEGIN
    -- Get user's primary role for this yacht
    SELECT role INTO v_user_role
    FROM public.auth_users_roles
    WHERE user_id = NEW.created_by
    AND yacht_id = NEW.yacht_id
    LIMIT 1;

    -- Map role to department
    NEW.author_department := CASE
        WHEN v_user_role IN ('chief_engineer', 'engineer', 'technical_crew') THEN 'engineering'
        WHEN v_user_role IN ('captain', 'first_officer', 'officer', 'deckhand') THEN 'deck'
        WHEN v_user_role IN ('chief_steward', 'stewardess', 'purser') THEN 'interior'
        WHEN v_user_role = 'chef' THEN 'galley'
        WHEN v_user_role IN ('manager', 'admin') THEN 'bridge'
        ELSE 'technical'
    END;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_populate_doc_comment_department_before_insert
    ON public.doc_metadata_comments;

CREATE TRIGGER trg_populate_doc_comment_department_before_insert
BEFORE INSERT ON public.doc_metadata_comments
FOR EACH ROW
EXECUTE FUNCTION public.trg_populate_doc_comment_department();

-- =====================================================
-- Table Comment
-- =====================================================

COMMENT ON TABLE public.doc_metadata_comments IS
'Document-level comments for Document Lens v2.
MVP scope: Document-level only. Future: page/section-specific comments.
Mirrors pms_attachment_comments pattern.
Created 2026-01-30.';

-- =====================================================
-- Verification
-- =====================================================

DO $$
BEGIN
    -- Verify table exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = 'doc_metadata_comments'
    ) THEN
        RAISE EXCEPTION 'Migration failed: doc_metadata_comments table not created';
    END IF;

    -- Verify RLS is enabled
    IF NOT EXISTS (
        SELECT 1 FROM pg_tables
        WHERE schemaname = 'public'
        AND tablename = 'doc_metadata_comments'
        AND rowsecurity = true
    ) THEN
        RAISE EXCEPTION 'Migration failed: RLS not enabled on doc_metadata_comments';
    END IF;

    RAISE NOTICE 'Migration successful: doc_metadata_comments table created with RLS';
END $$;
