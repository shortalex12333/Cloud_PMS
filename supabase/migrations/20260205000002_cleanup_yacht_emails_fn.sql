-- One-time cleanup function for stale email data
CREATE OR REPLACE FUNCTION cleanup_yacht_emails(p_yacht_id UUID)
RETURNS TABLE (deleted_messages BIGINT, deleted_threads BIGINT, deleted_extractions BIGINT)
LANGUAGE plpgsql SECURITY DEFINER
AS $$
DECLARE
    v_messages BIGINT;
    v_threads BIGINT;
    v_extractions BIGINT;
BEGIN
    -- Delete extraction results first (FK constraint)
    DELETE FROM email_extraction_results WHERE yacht_id = p_yacht_id;
    GET DIAGNOSTICS v_extractions = ROW_COUNT;
    
    -- Delete messages  
    DELETE FROM email_messages WHERE yacht_id = p_yacht_id;
    GET DIAGNOSTICS v_messages = ROW_COUNT;
    
    -- Delete threads
    DELETE FROM email_threads WHERE yacht_id = p_yacht_id;
    GET DIAGNOSTICS v_threads = ROW_COUNT;
    
    RETURN QUERY SELECT v_messages, v_threads, v_extractions;
END;
$$;

GRANT EXECUTE ON FUNCTION cleanup_yacht_emails TO service_role;
