-- GraphRAG RPC Stubs (Work Order Lens E2E unblock)
--
-- Purpose: Provide minimal, safe-by-default implementations for RPC functions
-- that the GraphRAG query service expects. These stubs avoid runtime errors
-- in Docker/E2E environments where full vector/alias infra may not be present.
-- They are deny-by-default and return no rows/NULLs so search falls back to
-- lexical paths without causing 500s.

-- match_documents(filter jsonb, match_count int, query_embedding vector)
-- Returns an empty result set by default (no table dependency to avoid failures)
create or replace function public.match_documents(
    filter jsonb,
    match_count int,
    query_embedding vector
)
returns table (
    id uuid,
    document_id uuid,
    content text,
    section_title text,
    page_number integer,
    storage_path text,
    similarity double precision
) as $$
    -- Safe default: return zero rows; caller should handle empty set gracefully
    select
        null::uuid as id,
        null::uuid as document_id,
        null::text as content,
        null::text as section_title,
        null::int as page_number,
        null::text as storage_path,
        0.0::double precision as similarity
    where false;
$$ language sql stable security definer;

comment on function public.match_documents(jsonb, int, vector)
    is 'Stubbed vector match RPC for GraphRAG; returns no rows by default.';


-- resolve_entity_alias(p_yacht_id uuid, p_entity_type text, p_alias_text text)
-- Returns canonical_id for alias if available; NULL otherwise (safe default)
create or replace function public.resolve_entity_alias(
    p_yacht_id uuid,
    p_entity_type text,
    p_alias_text text
)
returns uuid
language plpgsql
security definer
as $$
declare
    v_canonical uuid;
begin
    -- Safe default: try best-effort lookup in graph_nodes if available; otherwise NULL
    begin
        execute $$
            select gn.canonical_id
            from graph_nodes gn
            where gn.yacht_id = $1
              and gn.node_type = $2
              and (gn.label ilike $3 or gn.canonical ilike $3)
            limit 1
        $$ into v_canonical
        using p_yacht_id, p_entity_type, '%' || coalesce(p_alias_text, '') || '%';
        return v_canonical;
    exception when undefined_table or undefined_column then
        -- Table/column not present in this environment; return NULL
        return null;
    end;
end;$$;

comment on function public.resolve_entity_alias(uuid, text, text)
    is 'Best-effort alias resolver; returns canonical_id or NULL (safe default).';


-- resolve_symptom_alias(p_alias_text text)
-- Returns a canonical symptom code or NULL (safe default)
create or replace function public.resolve_symptom_alias(
    p_alias_text text
)
returns text
language plpgsql
security definer
as $$
begin
    -- Safe default: no-op resolver
    return null;
end;$$;

comment on function public.resolve_symptom_alias(text)
    is 'Stubbed symptom alias resolver; returns NULL by default.';

