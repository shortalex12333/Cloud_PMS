-- TRIGRAM SEARCH FUNCTION
-- Enables fuzzy text matching via pg_trgm extension
-- Used by SQL Foundation Wave 2

-- Ensure extension is enabled
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Generic trigram search function for any table/column
CREATE OR REPLACE FUNCTION search_trigram(
    p_table_name TEXT,
    p_column_name TEXT,
    p_yacht_id UUID,
    p_search_term TEXT,
    p_threshold FLOAT DEFAULT 0.3,
    p_limit INT DEFAULT 50
)
RETURNS TABLE (
    id UUID,
    similarity_score FLOAT,
    matched_value TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    query TEXT;
BEGIN
    -- Validate table name (whitelist)
    IF p_table_name NOT IN (
        'pms_parts', 'pms_equipment', 'pms_faults', 'pms_suppliers',
        'pms_work_orders', 'graph_nodes', 'symptom_aliases'
    ) THEN
        RAISE EXCEPTION 'Invalid table name: %', p_table_name;
    END IF;

    -- Build and execute dynamic query
    query := format(
        'SELECT id, similarity(%I, $1) as similarity_score, %I as matched_value
         FROM %I
         WHERE yacht_id = $2
           AND similarity(%I, $1) >= $3
         ORDER BY similarity(%I, $1) DESC
         LIMIT $4',
        p_column_name, p_column_name, p_table_name, p_column_name, p_column_name
    );

    RETURN QUERY EXECUTE query
    USING p_search_term, p_yacht_id, p_threshold, p_limit;
END;
$$;

-- Specific trigram search for parts (name column)
CREATE OR REPLACE FUNCTION search_parts_trigram(
    p_yacht_id UUID,
    p_search_term TEXT,
    p_threshold FLOAT DEFAULT 0.3
)
RETURNS TABLE (
    id UUID,
    part_number TEXT,
    name TEXT,
    manufacturer TEXT,
    similarity_score FLOAT
)
LANGUAGE sql
SECURITY DEFINER
AS $$
    SELECT
        id,
        part_number,
        name,
        manufacturer,
        similarity(name, p_search_term) as similarity_score
    FROM pms_parts
    WHERE yacht_id = p_yacht_id
      AND similarity(name, p_search_term) >= p_threshold
    ORDER BY similarity(name, p_search_term) DESC
    LIMIT 50;
$$;

-- Specific trigram search for equipment (name column)
CREATE OR REPLACE FUNCTION search_equipment_trigram(
    p_yacht_id UUID,
    p_search_term TEXT,
    p_threshold FLOAT DEFAULT 0.3
)
RETURNS TABLE (
    id UUID,
    code TEXT,
    name TEXT,
    manufacturer TEXT,
    system_type TEXT,
    similarity_score FLOAT
)
LANGUAGE sql
SECURITY DEFINER
AS $$
    SELECT
        id,
        code,
        name,
        manufacturer,
        system_type,
        similarity(name, p_search_term) as similarity_score
    FROM pms_equipment
    WHERE yacht_id = p_yacht_id
      AND similarity(name, p_search_term) >= p_threshold
    ORDER BY similarity(name, p_search_term) DESC
    LIMIT 50;
$$;

-- Specific trigram search for faults (title column)
CREATE OR REPLACE FUNCTION search_faults_trigram(
    p_yacht_id UUID,
    p_search_term TEXT,
    p_threshold FLOAT DEFAULT 0.3
)
RETURNS TABLE (
    id UUID,
    fault_code TEXT,
    title TEXT,
    severity TEXT,
    similarity_score FLOAT
)
LANGUAGE sql
SECURITY DEFINER
AS $$
    SELECT
        id,
        fault_code,
        title,
        severity,
        similarity(title, p_search_term) as similarity_score
    FROM pms_faults
    WHERE yacht_id = p_yacht_id
      AND similarity(title, p_search_term) >= p_threshold
    ORDER BY similarity(title, p_search_term) DESC
    LIMIT 50;
$$;

-- Specific trigram search for symptom aliases
CREATE OR REPLACE FUNCTION search_symptoms_trigram(
    p_yacht_id UUID,
    p_search_term TEXT,
    p_threshold FLOAT DEFAULT 0.3
)
RETURNS TABLE (
    id UUID,
    alias TEXT,
    symptom_code TEXT,
    similarity_score FLOAT
)
LANGUAGE sql
SECURITY DEFINER
AS $$
    SELECT
        id,
        alias,
        symptom_code,
        similarity(alias, p_search_term) as similarity_score
    FROM symptom_aliases
    WHERE yacht_id = p_yacht_id
      AND similarity(alias, p_search_term) >= p_threshold
    ORDER BY similarity(alias, p_search_term) DESC
    LIMIT 50;
$$;

-- Specific trigram search for graph nodes (label column)
CREATE OR REPLACE FUNCTION search_graph_nodes_trigram(
    p_yacht_id UUID,
    p_search_term TEXT,
    p_threshold FLOAT DEFAULT 0.3
)
RETURNS TABLE (
    id UUID,
    label TEXT,
    node_type TEXT,
    similarity_score FLOAT
)
LANGUAGE sql
SECURITY DEFINER
AS $$
    SELECT
        id,
        label,
        node_type,
        similarity(label, p_search_term) as similarity_score
    FROM graph_nodes
    WHERE yacht_id = p_yacht_id
      AND similarity(label, p_search_term) >= p_threshold
    ORDER BY similarity(label, p_search_term) DESC
    LIMIT 50;
$$;

-- Grant execute to service role
GRANT EXECUTE ON FUNCTION search_trigram TO service_role;
GRANT EXECUTE ON FUNCTION search_parts_trigram TO service_role;
GRANT EXECUTE ON FUNCTION search_equipment_trigram TO service_role;
GRANT EXECUTE ON FUNCTION search_faults_trigram TO service_role;
GRANT EXECUTE ON FUNCTION search_symptoms_trigram TO service_role;
GRANT EXECUTE ON FUNCTION search_graph_nodes_trigram TO service_role;
