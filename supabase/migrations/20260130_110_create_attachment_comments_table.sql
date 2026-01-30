-- =====================================================
-- Migration: Create Attachment Comments Table
-- Created: 2026-01-30
-- Purpose: Enable threaded comments on attachments with department-based RLS
--          to prevent non-technical crew from overwriting technical notes
-- =====================================================

-- Create attachment comments table
CREATE TABLE IF NOT EXISTS public.pms_attachment_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL,
    attachment_id UUID NOT NULL REFERENCES public.pms_attachments(id) ON DELETE CASCADE,

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

    -- Department context (cached from user at creation time)
    author_department VARCHAR(100),

    -- Threading support (for future nested replies)
    parent_comment_id UUID REFERENCES public.pms_attachment_comments(id) ON DELETE CASCADE,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Constraints
    CONSTRAINT chk_comment_not_empty CHECK (LENGTH(TRIM(comment)) > 0),
    CONSTRAINT chk_valid_department CHECK (
        author_department IS NULL OR author_department IN (
            'technical', 'deck', 'interior', 'galley', 'engineering', 'bridge'
        )
    )
);

-- Indexes for performance
CREATE INDEX idx_attachment_comments_attachment_id ON public.pms_attachment_comments(attachment_id);
CREATE INDEX idx_attachment_comments_yacht_id ON public.pms_attachment_comments(yacht_id);
CREATE INDEX idx_attachment_comments_created_at ON public.pms_attachment_comments(created_at DESC);
CREATE INDEX idx_attachment_comments_deleted_at ON public.pms_attachment_comments(deleted_at) WHERE deleted_at IS NULL;
CREATE INDEX idx_attachment_comments_parent ON public.pms_attachment_comments(parent_comment_id) WHERE parent_comment_id IS NOT NULL;
CREATE INDEX idx_attachment_comments_department ON public.pms_attachment_comments(author_department);

-- =====================================================
-- RLS Policies
-- =====================================================

ALTER TABLE public.pms_attachment_comments ENABLE ROW LEVEL SECURITY;

-- SELECT: Users can read comments if they have access to the yacht
CREATE POLICY "attachment_comments_select"
ON public.pms_attachment_comments
FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM public.auth_users_roles aur
        WHERE aur.user_id = auth.uid()
        AND aur.yacht_id = pms_attachment_comments.yacht_id
    )
    AND deleted_at IS NULL  -- Hide soft-deleted comments
);

-- INSERT: Users can create comments on attachments they have access to
-- Department is captured at creation time for enforcement
CREATE POLICY "attachment_comments_insert"
ON public.pms_attachment_comments
FOR INSERT
WITH CHECK (
    -- User belongs to yacht
    EXISTS (
        SELECT 1 FROM public.auth_users_roles aur
        WHERE aur.user_id = auth.uid()
        AND aur.yacht_id = pms_attachment_comments.yacht_id
    )
    -- User has access to the attachment's entity
    AND EXISTS (
        SELECT 1 FROM public.pms_attachments att
        WHERE att.id = pms_attachment_comments.attachment_id
        AND att.yacht_id = pms_attachment_comments.yacht_id
    )
    -- created_by must be current user
    AND created_by = auth.uid()
);

-- UPDATE: Users can ONLY edit their OWN comments
-- UNLESS they're in the same department as the original author
-- This prevents non-technical crew from overwriting technical notes
CREATE POLICY "attachment_comments_update"
ON public.pms_attachment_comments
FOR UPDATE
USING (
    -- User belongs to yacht
    EXISTS (
        SELECT 1 FROM public.auth_users_roles aur
        WHERE aur.user_id = auth.uid()
        AND aur.yacht_id = pms_attachment_comments.yacht_id
    )
    AND deleted_at IS NULL  -- Can't edit deleted comments
    AND (
        -- Can edit own comments
        created_by = auth.uid()
        OR
        -- OR user is in same department as author (for corrections)
        EXISTS (
            SELECT 1 FROM public.auth_users_roles aur
            WHERE aur.user_id = auth.uid()
            AND aur.yacht_id = pms_attachment_comments.yacht_id
            AND (
                -- Technical departments can edit technical comments
                (aur.role IN ('chief_engineer', 'technical_crew')
                 AND pms_attachment_comments.author_department = 'technical')
                OR
                -- Engineering can edit engineering comments
                (aur.role IN ('chief_engineer', 'engineer')
                 AND pms_attachment_comments.author_department = 'engineering')
            )
        )
        OR
        -- OR user is admin/chief engineer (can moderate all)
        EXISTS (
            SELECT 1 FROM public.auth_users_roles aur
            WHERE aur.user_id = auth.uid()
            AND aur.yacht_id = pms_attachment_comments.yacht_id
            AND aur.role IN ('admin', 'chief_engineer')
        )
    )
)
WITH CHECK (
    -- updated_by must be current user
    updated_by = auth.uid()
);

-- DELETE (Soft Delete): Similar rules to UPDATE
-- Users can soft-delete their own comments or admins can moderate
CREATE POLICY "attachment_comments_delete"
ON public.pms_attachment_comments
FOR UPDATE  -- Soft delete is an UPDATE operation
USING (
    -- User belongs to yacht
    EXISTS (
        SELECT 1 FROM public.auth_users_roles aur
        WHERE aur.user_id = auth.uid()
        AND aur.yacht_id = pms_attachment_comments.yacht_id
    )
    AND deleted_at IS NULL  -- Not already deleted
    AND (
        -- Can delete own comments
        created_by = auth.uid()
        OR
        -- OR user is admin/chief engineer (can moderate)
        EXISTS (
            SELECT 1 FROM public.auth_users_roles aur
            WHERE aur.user_id = auth.uid()
            AND aur.yacht_id = pms_attachment_comments.yacht_id
            AND aur.role IN ('admin', 'chief_engineer')
        )
    )
)
WITH CHECK (
    -- Must be setting deleted_at and deleted_by
    deleted_at IS NOT NULL
    AND deleted_by = auth.uid()
);

-- =====================================================
-- Helper Function: Get Entity Department
-- =====================================================
-- Determines the department context of an attachment based on its entity
CREATE OR REPLACE FUNCTION public.get_attachment_entity_department(p_attachment_id UUID)
RETURNS VARCHAR(100)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_entity_type VARCHAR(50);
    v_entity_id UUID;
    v_department VARCHAR(100);
BEGIN
    -- Get entity type and ID from attachment
    SELECT entity_type, entity_id
    INTO v_entity_type, v_entity_id
    FROM public.pms_attachments
    WHERE id = p_attachment_id;

    IF v_entity_type IS NULL THEN
        RETURN NULL;
    END IF;

    -- Get department based on entity type
    CASE v_entity_type
        WHEN 'work_order' THEN
            SELECT department INTO v_department
            FROM public.pms_work_orders
            WHERE id = v_entity_id;

        WHEN 'fault' THEN
            -- Faults typically inherit from equipment's system
            SELECT s.department INTO v_department
            FROM public.pms_faults f
            JOIN public.pms_equipment e ON f.equipment_id = e.id
            JOIN public.pms_systems s ON e.system_id = s.id
            WHERE f.id = v_entity_id;

        WHEN 'equipment' THEN
            SELECT s.department INTO v_department
            FROM public.pms_equipment e
            JOIN public.pms_systems s ON e.system_id = s.id
            WHERE e.id = v_entity_id;

        ELSE
            v_department := 'technical';  -- Default for other entity types
    END CASE;

    RETURN v_department;
END;
$$;

-- =====================================================
-- Trigger: Auto-populate Department on Insert
-- =====================================================
CREATE OR REPLACE FUNCTION public.trg_populate_comment_department()
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
        WHEN v_user_role IN ('chief_engineer', 'engineer', 'technical_crew') THEN 'technical'
        WHEN v_user_role IN ('captain', 'officer', 'deckhand') THEN 'deck'
        WHEN v_user_role IN ('chief_steward', 'stewardess') THEN 'interior'
        WHEN v_user_role = 'chef' THEN 'galley'
        ELSE 'technical'  -- Default
    END;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_populate_comment_department_before_insert
BEFORE INSERT ON public.pms_attachment_comments
FOR EACH ROW
EXECUTE FUNCTION public.trg_populate_comment_department();

-- =====================================================
-- Comments and Documentation
-- =====================================================
COMMENT ON TABLE public.pms_attachment_comments IS
'Threaded comments on attachments with department-based RLS.
Prevents non-technical crew from overwriting technical notes.
Created 2026-01-30 for Work Order Lens V2 Embeddings Phase 2.';

COMMENT ON COLUMN public.pms_attachment_comments.author_department IS
'Department cached at creation time for RLS enforcement.
Prevents privilege escalation via role changes.';

COMMENT ON FUNCTION public.get_attachment_entity_department IS
'Helper function to determine department context from attachment entity chain.';
