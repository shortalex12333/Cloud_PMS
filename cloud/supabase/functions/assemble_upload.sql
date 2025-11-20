-- ============================================================================
-- CelesteOS Upload Complete Helper Function
-- ============================================================================
-- This function handles the completion of a chunked upload
-- It can be called from n8n or directly from the API
-- ============================================================================

CREATE OR REPLACE FUNCTION complete_chunked_upload(
  upload_session_uuid UUID,
  final_storage_path TEXT DEFAULT NULL
)
RETURNS TABLE (
  document_id UUID,
  sha256 TEXT,
  status TEXT,
  message TEXT
) AS $$
DECLARE
  session_record RECORD;
  doc_id UUID;
  expected_sha256 TEXT;
  computed_sha256 TEXT;
  all_chunks_verified BOOLEAN;
BEGIN
  -- Get session details
  SELECT * INTO session_record
  FROM upload_sessions
  WHERE id = upload_session_uuid AND status = 'in_progress';

  IF session_record IS NULL THEN
    RAISE EXCEPTION 'Upload session not found or already completed';
  END IF;

  -- Verify all chunks uploaded
  IF session_record.chunks_uploaded < session_record.total_chunks THEN
    RAISE EXCEPTION 'Not all chunks uploaded: % of % chunks completed',
      session_record.chunks_uploaded, session_record.total_chunks;
  END IF;

  -- Verify all chunks have status 'verified'
  SELECT NOT EXISTS (
    SELECT 1 FROM upload_chunks
    WHERE upload_session_id = upload_session_uuid
    AND status != 'verified'
  ) INTO all_chunks_verified;

  IF NOT all_chunks_verified THEN
    RAISE EXCEPTION 'Some chunks failed verification';
  END IF;

  -- Set default storage path if not provided
  IF final_storage_path IS NULL THEN
    final_storage_path := session_record.yacht_id::text || '/documents/' || session_record.file_sha256;
  END IF;

  -- Create document record
  -- Note: Actual file assembly happens externally (n8n Code node or worker)
  -- This function just creates the DB record once assembly is confirmed
  INSERT INTO documents (
    yacht_id,
    sha256,
    original_filename,
    file_size,
    mime_type,
    source_type,
    source_path,
    nas_path,
    storage_bucket,
    storage_path,
    document_type,
    processing_status
  ) VALUES (
    session_record.yacht_id,
    session_record.file_sha256,
    session_record.filename,
    session_record.file_size,
    session_record.mime_type,
    session_record.source_type,
    session_record.source_path,
    session_record.nas_path,
    'yacht-documents',
    final_storage_path,
    session_record.document_type,
    'pending'  -- Will be picked up by indexing pipeline
  ) RETURNING id INTO doc_id;

  -- Mark session as complete
  UPDATE upload_sessions
  SET status = 'completed', completed_at = NOW()
  WHERE id = upload_session_uuid;

  -- Log completion
  INSERT INTO pipeline_logs (
    yacht_id,
    document_id,
    upload_session_id,
    pipeline_stage,
    log_level,
    message,
    details
  ) VALUES (
    session_record.yacht_id,
    doc_id,
    upload_session_uuid,
    'upload',
    'info',
    'Upload completed successfully',
    jsonb_build_object(
      'filename', session_record.filename,
      'file_size', session_record.file_size,
      'total_chunks', session_record.total_chunks
    )
  );

  -- Return result
  RETURN QUERY SELECT
    doc_id,
    session_record.file_sha256,
    'success'::TEXT,
    'Document created successfully'::TEXT;

EXCEPTION
  WHEN OTHERS THEN
    -- Log error
    INSERT INTO pipeline_logs (
      yacht_id,
      upload_session_id,
      pipeline_stage,
      log_level,
      message,
      error_code,
      stack_trace
    ) VALUES (
      session_record.yacht_id,
      upload_session_uuid,
      'upload',
      'error',
      SQLERRM,
      SQLSTATE,
      SQLERRM
    );

    -- Mark session as failed
    UPDATE upload_sessions
    SET status = 'failed', error_message = SQLERRM
    WHERE id = upload_session_uuid;

    -- Re-raise exception
    RAISE;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION complete_chunked_upload IS 'Completes a chunked file upload by creating document record and marking session complete';


-- ============================================================================
-- Helper function to get upload session status
-- ============================================================================

CREATE OR REPLACE FUNCTION get_upload_status(upload_session_uuid UUID)
RETURNS TABLE (
  upload_id UUID,
  status TEXT,
  total_chunks INTEGER,
  chunks_uploaded INTEGER,
  chunks_verified INTEGER,
  progress_percent INTEGER,
  can_complete BOOLEAN
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    us.id,
    us.status,
    us.total_chunks,
    us.chunks_uploaded,
    (SELECT COUNT(*) FROM upload_chunks WHERE upload_session_id = us.id AND status = 'verified')::INTEGER,
    CASE
      WHEN us.total_chunks > 0 THEN (us.chunks_uploaded * 100 / us.total_chunks)::INTEGER
      ELSE 0
    END,
    (us.chunks_uploaded = us.total_chunks AND us.status = 'in_progress')
  FROM upload_sessions us
  WHERE us.id = upload_session_uuid;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_upload_status IS 'Returns current status of an upload session';
