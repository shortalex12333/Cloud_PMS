-- =====================================================
-- Migration: Create Entity-Based Attachment Storage Buckets
-- Created: 2026-01-30
-- Purpose: Organize attachment storage by entity type for better RLS alignment,
--          lifecycle management, and storage analytics
-- =====================================================

-- Create storage buckets for entity-specific attachments
-- Using entity-based buckets for RLS alignment and lifecycle management

-- Work Order Attachments Bucket
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'pms-work-order-attachments',
    'pms-work-order-attachments',
    false,  -- Private bucket, requires authentication
    52428800,  -- 50MB limit per file
    ARRAY[
        'image/jpeg', 'image/png', 'image/gif', 'image/webp',  -- Images
        'application/pdf',  -- PDFs
        'video/mp4', 'video/quicktime',  -- Videos
        'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  -- Word docs
        'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  -- Excel
        'text/plain', 'text/csv'  -- Text files
    ]
)
ON CONFLICT (id) DO NOTHING;

-- Fault Attachments Bucket
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'pms-fault-attachments',
    'pms-fault-attachments',
    false,
    52428800,  -- 50MB limit
    ARRAY[
        'image/jpeg', 'image/png', 'image/gif', 'image/webp',
        'application/pdf',
        'video/mp4', 'video/quicktime',
        'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'text/plain', 'text/csv'
    ]
)
ON CONFLICT (id) DO NOTHING;

-- Equipment Attachments Bucket (manuals, schematics, photos)
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'pms-equipment-attachments',
    'pms-equipment-attachments',
    false,
    104857600,  -- 100MB limit (technical docs can be large)
    ARRAY[
        'image/jpeg', 'image/png', 'image/gif', 'image/webp',
        'application/pdf',
        'video/mp4', 'video/quicktime',
        'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-powerpoint', 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'application/zip', 'application/x-rar-compressed',  -- Compressed manuals
        'text/plain', 'text/csv'
    ]
)
ON CONFLICT (id) DO NOTHING;

-- Checklist Attachments Bucket (evidence photos/docs)
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'pms-checklist-attachments',
    'pms-checklist-attachments',
    false,
    52428800,  -- 50MB limit
    ARRAY[
        'image/jpeg', 'image/png', 'image/gif', 'image/webp',
        'application/pdf',
        'video/mp4', 'video/quicktime',
        'text/plain'
    ]
)
ON CONFLICT (id) DO NOTHING;

-- =====================================================
-- RLS Policies for Storage Buckets
-- =====================================================

-- Work Order Attachments: Users can access if they belong to work order's yacht
CREATE POLICY "work_order_attachments_select"
ON storage.objects FOR SELECT
USING (
    bucket_id = 'pms-work-order-attachments'
    AND EXISTS (
        SELECT 1 FROM public.pms_work_orders wo
        WHERE wo.yacht_id = (storage.foldername(name))[1]::uuid
        AND wo.yacht_id IN (
            SELECT yacht_id FROM public.auth_users_roles
            WHERE user_id = auth.uid()
        )
    )
);

CREATE POLICY "work_order_attachments_insert"
ON storage.objects FOR INSERT
WITH CHECK (
    bucket_id = 'pms-work-order-attachments'
    AND EXISTS (
        SELECT 1 FROM public.auth_users_roles
        WHERE user_id = auth.uid()
        AND yacht_id = (storage.foldername(name))[1]::uuid
    )
);

CREATE POLICY "work_order_attachments_delete"
ON storage.objects FOR DELETE
USING (
    bucket_id = 'pms-work-order-attachments'
    AND EXISTS (
        SELECT 1 FROM public.auth_users_roles aur
        WHERE aur.user_id = auth.uid()
        AND aur.yacht_id = (storage.foldername(name))[1]::uuid
        AND aur.role IN ('admin', 'chief_engineer', 'technical_crew')
    )
);

-- Fault Attachments: Similar yacht-based access
CREATE POLICY "fault_attachments_select"
ON storage.objects FOR SELECT
USING (
    bucket_id = 'pms-fault-attachments'
    AND EXISTS (
        SELECT 1 FROM public.auth_users_roles
        WHERE user_id = auth.uid()
        AND yacht_id = (storage.foldername(name))[1]::uuid
    )
);

CREATE POLICY "fault_attachments_insert"
ON storage.objects FOR INSERT
WITH CHECK (
    bucket_id = 'pms-fault-attachments'
    AND EXISTS (
        SELECT 1 FROM public.auth_users_roles
        WHERE user_id = auth.uid()
        AND yacht_id = (storage.foldername(name))[1]::uuid
    )
);

CREATE POLICY "fault_attachments_delete"
ON storage.objects FOR DELETE
USING (
    bucket_id = 'pms-fault-attachments'
    AND EXISTS (
        SELECT 1 FROM public.auth_users_roles aur
        WHERE aur.user_id = auth.uid()
        AND aur.yacht_id = (storage.foldername(name))[1]::uuid
        AND aur.role IN ('admin', 'chief_engineer', 'technical_crew')
    )
);

-- Equipment Attachments: Similar yacht-based access
CREATE POLICY "equipment_attachments_select"
ON storage.objects FOR SELECT
USING (
    bucket_id = 'pms-equipment-attachments'
    AND EXISTS (
        SELECT 1 FROM public.auth_users_roles
        WHERE user_id = auth.uid()
        AND yacht_id = (storage.foldername(name))[1]::uuid
    )
);

CREATE POLICY "equipment_attachments_insert"
ON storage.objects FOR INSERT
WITH CHECK (
    bucket_id = 'pms-equipment-attachments'
    AND EXISTS (
        SELECT 1 FROM public.auth_users_roles
        WHERE user_id = auth.uid()
        AND yacht_id = (storage.foldername(name))[1]::uuid
    )
);

CREATE POLICY "equipment_attachments_delete"
ON storage.objects FOR DELETE
USING (
    bucket_id = 'pms-equipment-attachments'
    AND EXISTS (
        SELECT 1 FROM public.auth_users_roles aur
        WHERE aur.user_id = auth.uid()
        AND aur.yacht_id = (storage.foldername(name))[1]::uuid
        AND aur.role IN ('admin', 'chief_engineer', 'technical_crew')
    )
);

-- Checklist Attachments: Similar yacht-based access
CREATE POLICY "checklist_attachments_select"
ON storage.objects FOR SELECT
USING (
    bucket_id = 'pms-checklist-attachments'
    AND EXISTS (
        SELECT 1 FROM public.auth_users_roles
        WHERE user_id = auth.uid()
        AND yacht_id = (storage.foldername(name))[1]::uuid
    )
);

CREATE POLICY "checklist_attachments_insert"
ON storage.objects FOR INSERT
WITH CHECK (
    bucket_id = 'pms-checklist-attachments'
    AND EXISTS (
        SELECT 1 FROM public.auth_users_roles
        WHERE user_id = auth.uid()
        AND yacht_id = (storage.foldername(name))[1]::uuid
    )
);

CREATE POLICY "checklist_attachments_delete"
ON storage.objects FOR DELETE
USING (
    bucket_id = 'pms-checklist-attachments'
    AND EXISTS (
        SELECT 1 FROM public.auth_users_roles aur
        WHERE aur.user_id = auth.uid()
        AND aur.yacht_id = (storage.foldername(name))[1]::uuid
        AND aur.role IN ('admin', 'chief_engineer', 'technical_crew')
    )
);

-- =====================================================
-- Storage Path Convention
-- =====================================================
-- Paths follow pattern: {yacht_id}/{entity_id}/{filename}
-- Example: 123e4567-e89b-12d3-a456-426614174000/wo_001/leak_photo.jpg
--
-- Benefits:
-- 1. Easy bulk operations (delete all files for an entity)
-- 2. Clear ownership chain (yacht → entity → file)
-- 3. Supports RLS policies via path parsing
-- 4. Storage analytics by yacht/entity
-- =====================================================

COMMENT ON TABLE storage.buckets IS 'Entity-based attachment buckets created 2026-01-30 for Work Order Lens V2';
