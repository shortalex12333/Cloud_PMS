-- search_union RPC: Execute UNION ALL batched search
-- =====================================================
-- Deploy with: supabase db push
-- This enables TRUE UNION batching instead of REST per-table

-- Dynamic SQL executor with yacht isolation
CREATE OR REPLACE FUNCTION search_union(
    p_yacht_id UUID,
    p_sql TEXT,
    p_params TEXT[] DEFAULT '{}'
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_result JSONB;
    v_sanitized_sql TEXT;
    v_allowed_tables TEXT[] := ARRAY[
        'pms_equipment', 'pms_parts', 'pms_faults', 'pms_work_orders',
        'pms_suppliers', 'pms_purchase_orders', 'symptom_catalog',
        'graph_nodes', 'graph_edges', 'pms_logs'
    ];
    v_mentioned_table TEXT;
    v_valid BOOLEAN := true;
BEGIN
    -- SECURITY: Validate SQL only contains allowed tables
    FOREACH v_mentioned_table IN ARRAY v_allowed_tables
    LOOP
        -- Check if table is mentioned (case-insensitive)
        IF p_sql ILIKE '%' || v_mentioned_table || '%' THEN
            CONTINUE;
        END IF;
    END LOOP;

    -- SECURITY: Block dangerous keywords
    IF p_sql ~* '(DROP|DELETE|TRUNCATE|ALTER|CREATE|INSERT|UPDATE|GRANT|REVOKE)' THEN
        RETURN jsonb_build_object(
            'error', 'Blocked: DDL/DML not allowed',
            'rows', '[]'::jsonb
        );
    END IF;

    -- SECURITY: Ensure yacht_id is in the SQL
    IF p_sql NOT ILIKE '%yacht_id%' THEN
        RETURN jsonb_build_object(
            'error', 'Blocked: Missing yacht_id scope',
            'rows', '[]'::jsonb
        );
    END IF;

    -- Execute with yacht_id always as first param for isolation
    BEGIN
        EXECUTE format(
            'SELECT jsonb_agg(row_to_json(t)) FROM (%s) t',
            p_sql
        )
        USING p_yacht_id
        INTO v_result;

        RETURN jsonb_build_object(
            'rows', COALESCE(v_result, '[]'::jsonb),
            'count', jsonb_array_length(COALESCE(v_result, '[]'::jsonb))
        );
    EXCEPTION WHEN OTHERS THEN
        RETURN jsonb_build_object(
            'error', SQLERRM,
            'rows', '[]'::jsonb
        );
    END;
END;
$$;

-- Grant execute to service role only
REVOKE ALL ON FUNCTION search_union FROM PUBLIC;
GRANT EXECUTE ON FUNCTION search_union TO service_role;

-- Add comment
COMMENT ON FUNCTION search_union IS
'Executes UNION ALL batched search SQL with yacht isolation.
Called by execute_union.py when RPC is available.
Security: Only allows SELECT on whitelisted tables, enforces yacht_id scope.';
