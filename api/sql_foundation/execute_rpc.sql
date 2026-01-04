-- EXECUTE RPC: Run UNION ALL queries in Postgres
-- ================================================
-- Deploy this to Supabase to enable single-call execution.
--
-- Usage:
--   SELECT * FROM search_union(
--     '85fe1119-b04c-41ac-80f1-829d23322598',  -- yacht_id
--     'Generator',                              -- search_term
--     ARRAY['pms_equipment', 'graph_nodes'],    -- tables
--     'ILIKE'                                   -- operator: EXACT, ILIKE, TRIGRAM
--   );

-- Drop if exists
DROP FUNCTION IF EXISTS search_union(uuid, text, text[], text);

CREATE OR REPLACE FUNCTION search_union(
    p_yacht_id uuid,
    p_search_term text,
    p_tables text[],
    p_operator text DEFAULT 'ILIKE'
)
RETURNS TABLE (
    _source text,
    id uuid,
    name text,
    match_value text
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_sql text := '';
    v_table text;
    v_first boolean := true;
    v_search text;
BEGIN
    -- Prepare search term based on operator
    CASE p_operator
        WHEN 'EXACT' THEN
            v_search := upper(p_search_term);
        WHEN 'ILIKE' THEN
            v_search := '%' || p_search_term || '%';
        WHEN 'TRIGRAM' THEN
            v_search := lower(p_search_term);
        ELSE
            v_search := '%' || p_search_term || '%';
    END CASE;

    -- Build UNION ALL query dynamically
    FOREACH v_table IN ARRAY p_tables
    LOOP
        IF NOT v_first THEN
            v_sql := v_sql || ' UNION ALL ';
        END IF;
        v_first := false;

        CASE v_table
            WHEN 'pms_equipment' THEN
                CASE p_operator
                    WHEN 'EXACT' THEN
                        v_sql := v_sql || format(
                            'SELECT %L::text, id, name, name FROM pms_equipment WHERE yacht_id = %L AND upper(name) = %L LIMIT 20',
                            v_table, p_yacht_id, v_search
                        );
                    WHEN 'TRIGRAM' THEN
                        v_sql := v_sql || format(
                            'SELECT %L::text, id, name, name FROM pms_equipment WHERE yacht_id = %L AND similarity(name, %L) >= 0.3 LIMIT 20',
                            v_table, p_yacht_id, v_search
                        );
                    ELSE
                        v_sql := v_sql || format(
                            'SELECT %L::text, id, name, name FROM pms_equipment WHERE yacht_id = %L AND name ILIKE %L LIMIT 20',
                            v_table, p_yacht_id, v_search
                        );
                END CASE;

            WHEN 'graph_nodes' THEN
                CASE p_operator
                    WHEN 'EXACT' THEN
                        v_sql := v_sql || format(
                            'SELECT %L::text, id, label, label FROM graph_nodes WHERE yacht_id = %L AND upper(label) = %L LIMIT 20',
                            v_table, p_yacht_id, v_search
                        );
                    WHEN 'TRIGRAM' THEN
                        v_sql := v_sql || format(
                            'SELECT %L::text, id, label, label FROM graph_nodes WHERE yacht_id = %L AND similarity(label, %L) >= 0.3 LIMIT 20',
                            v_table, p_yacht_id, v_search
                        );
                    ELSE
                        v_sql := v_sql || format(
                            'SELECT %L::text, id, label, label FROM graph_nodes WHERE yacht_id = %L AND label ILIKE %L LIMIT 20',
                            v_table, p_yacht_id, v_search
                        );
                END CASE;

            WHEN 'pms_parts' THEN
                CASE p_operator
                    WHEN 'EXACT' THEN
                        v_sql := v_sql || format(
                            'SELECT %L::text, id, name, name FROM pms_parts WHERE yacht_id = %L AND (upper(name) = %L OR upper(part_number) = %L) LIMIT 20',
                            v_table, p_yacht_id, v_search, v_search
                        );
                    ELSE
                        v_sql := v_sql || format(
                            'SELECT %L::text, id, name, name FROM pms_parts WHERE yacht_id = %L AND (name ILIKE %L OR part_number ILIKE %L) LIMIT 20',
                            v_table, p_yacht_id, v_search, v_search
                        );
                END CASE;

            WHEN 'pms_faults' THEN
                CASE p_operator
                    WHEN 'EXACT' THEN
                        v_sql := v_sql || format(
                            'SELECT %L::text, id, title, fault_code FROM pms_faults WHERE yacht_id = %L AND upper(fault_code) = %L LIMIT 20',
                            v_table, p_yacht_id, v_search
                        );
                    ELSE
                        v_sql := v_sql || format(
                            'SELECT %L::text, id, title, fault_code FROM pms_faults WHERE yacht_id = %L AND (fault_code ILIKE %L OR title ILIKE %L) LIMIT 20',
                            v_table, p_yacht_id, v_search, v_search
                        );
                END CASE;

            WHEN 'pms_suppliers' THEN
                v_sql := v_sql || format(
                    'SELECT %L::text, id, name, name FROM pms_suppliers WHERE yacht_id = %L AND name ILIKE %L LIMIT 20',
                    v_table, p_yacht_id, v_search
                );

            WHEN 'symptom_aliases' THEN
                CASE p_operator
                    WHEN 'EXACT' THEN
                        v_sql := v_sql || format(
                            'SELECT %L::text, id, alias, symptom_code FROM symptom_aliases WHERE yacht_id = %L AND upper(symptom_code) = %L LIMIT 20',
                            v_table, p_yacht_id, v_search
                        );
                    ELSE
                        v_sql := v_sql || format(
                            'SELECT %L::text, id, alias, symptom_code FROM symptom_aliases WHERE yacht_id = %L AND (alias ILIKE %L OR symptom_code ILIKE %L) LIMIT 20',
                            v_table, p_yacht_id, v_search, v_search
                        );
                END CASE;

            WHEN 'pms_work_orders' THEN
                v_sql := v_sql || format(
                    'SELECT %L::text, id, title, status FROM pms_work_orders WHERE yacht_id = %L AND title ILIKE %L LIMIT 20',
                    v_table, p_yacht_id, v_search
                );

            WHEN 'search_fault_code_catalog' THEN
                CASE p_operator
                    WHEN 'EXACT' THEN
                        v_sql := v_sql || format(
                            'SELECT %L::text, id, name, code FROM search_fault_code_catalog WHERE yacht_id = %L AND upper(code) = %L LIMIT 20',
                            v_table, p_yacht_id, v_search
                        );
                    ELSE
                        v_sql := v_sql || format(
                            'SELECT %L::text, id, name, code FROM search_fault_code_catalog WHERE yacht_id = %L AND (code ILIKE %L OR name ILIKE %L) LIMIT 20',
                            v_table, p_yacht_id, v_search, v_search
                        );
                END CASE;

            ELSE
                -- Skip unknown tables
                v_first := true;  -- Reset so next table doesn't get extra UNION ALL
        END CASE;
    END LOOP;

    -- Add overall limit
    IF v_sql != '' THEN
        v_sql := v_sql || ' LIMIT 50';
        RETURN QUERY EXECUTE v_sql;
    END IF;
END;
$$;

-- Grant execute to authenticated users
GRANT EXECUTE ON FUNCTION search_union(uuid, text, text[], text) TO authenticated;
GRANT EXECUTE ON FUNCTION search_union(uuid, text, text[], text) TO service_role;

-- Example usage:
-- SELECT * FROM search_union(
--     '85fe1119-b04c-41ac-80f1-829d23322598'::uuid,
--     'Generator',
--     ARRAY['pms_equipment', 'graph_nodes'],
--     'ILIKE'
-- );
