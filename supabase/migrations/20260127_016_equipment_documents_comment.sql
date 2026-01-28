-- ============================================================================
-- MIGRATION: 20260127_016_equipment_documents_comment.sql
-- PURPOSE: Add comments to pms_equipment_documents table for documentation
-- LENS: Equipment Lens v2
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pms_equipment_documents') THEN
        RAISE NOTICE 'pms_equipment_documents table does not exist - skipping comments';
        RETURN;
    END IF;

    -- Table comment
    COMMENT ON TABLE public.pms_equipment_documents IS
        'Equipment document attachments with storage references. Part of Equipment Lens v2.';

    -- Column comments
    COMMENT ON COLUMN public.pms_equipment_documents.id IS 'Primary key';
    COMMENT ON COLUMN public.pms_equipment_documents.yacht_id IS 'Yacht isolation FK';
    COMMENT ON COLUMN public.pms_equipment_documents.equipment_id IS 'FK to pms_equipment';
    COMMENT ON COLUMN public.pms_equipment_documents.document_id IS 'Optional FK to doc_metadata for centralized document management';
    COMMENT ON COLUMN public.pms_equipment_documents.storage_path IS 'Full bucket path: {yacht_id}/equipment/{equipment_id}/{filename}';
    COMMENT ON COLUMN public.pms_equipment_documents.filename IS 'UUID-based filename in storage';
    COMMENT ON COLUMN public.pms_equipment_documents.original_filename IS 'User-provided original filename';
    COMMENT ON COLUMN public.pms_equipment_documents.mime_type IS 'Detected MIME type';
    COMMENT ON COLUMN public.pms_equipment_documents.file_size IS 'File size in bytes';
    COMMENT ON COLUMN public.pms_equipment_documents.document_type IS 'Classification: manual, photo, certificate, diagram, warranty, general';
    COMMENT ON COLUMN public.pms_equipment_documents.description IS 'User-provided description';
    COMMENT ON COLUMN public.pms_equipment_documents.tags IS 'Array of user tags for filtering';
    COMMENT ON COLUMN public.pms_equipment_documents.uploaded_by IS 'User who uploaded the document';
    COMMENT ON COLUMN public.pms_equipment_documents.uploaded_at IS 'Timestamp of upload';

    RAISE NOTICE 'SUCCESS: Comments added to pms_equipment_documents';
END $$;

-- Also add comments to pms_equipment_hours_log
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pms_equipment_hours_log') THEN
        RETURN;
    END IF;

    COMMENT ON TABLE public.pms_equipment_hours_log IS
        'Equipment running hours log. Hours must be monotonically increasing. Part of Equipment Lens v2.';

    COMMENT ON COLUMN public.pms_equipment_hours_log.hours IS 'Cumulative running hours (not delta). Must be >= previous value.';
    COMMENT ON COLUMN public.pms_equipment_hours_log.source IS 'How hours were recorded: manual, meter, import';
    COMMENT ON COLUMN public.pms_equipment_hours_log.recorded_by IS 'User who recorded the hours';
END $$;

-- Also add comments to pms_equipment_status_log
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pms_equipment_status_log') THEN
        RETURN;
    END IF;

    COMMENT ON TABLE public.pms_equipment_status_log IS
        'Equipment status change history for audit trail. Part of Equipment Lens v2.';

    COMMENT ON COLUMN public.pms_equipment_status_log.work_order_id IS 'Work order that caused this status change (if any)';
    COMMENT ON COLUMN public.pms_equipment_status_log.reason IS 'Optional reason for status change';
END $$;

DO $$
BEGIN
    RAISE NOTICE 'SUCCESS: Equipment Lens v2 documentation comments added';
END $$;
