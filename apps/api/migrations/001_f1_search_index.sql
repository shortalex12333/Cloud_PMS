-- ============================================================================
-- F1 Search - search_index Table Migration
-- ============================================================================
--
-- Run this in Supabase SQL Editor.
--
-- Creates:
-- 1. Extensions (vector, pg_trgm)
-- 2. search_index table with hybrid search columns
-- 3. Indexes (trigram, FTS, RLS, HNSW vector)
-- 4. RLS policies (org_id + yacht_id scoped)
-- 5. hyper_search RPC (single round-trip, RRF fusion)
-- 6. Upsert trigger for parts table
--
-- See: apps/api/docs/F1_SEARCH/DB_HYBRID_SEARCH_SPEC.md
-- ============================================================================

-- ============================================================================
-- 1. EXTENSIONS (Idempotent)
-- ============================================================================

create extension if not exists vector;
create extension if not exists pg_trgm;

-- ============================================================================
-- 2. SEARCH_INDEX TABLE
-- ============================================================================
--
-- Unified search surface for all searchable objects.
-- Columns:
--   object_type: 'part', 'work_order', 'document', 'manual', etc.
--   object_id: UUID of the source record
--   org_id: Organization UUID (REQUIRED for RLS)
--   yacht_id: Optional yacht UUID for yacht-scoped queries
--   search_text: Concatenated searchable text
--   tsv: Auto-generated tsvector for FTS
--   embedding: 384-dim vector (populated by async job, NOT trigger)
--   payload: Minimal JSONB for display (name, category, etc.)
--   embedding_version: Track embedding model version for re-embedding
-- ============================================================================

create table if not exists search_index (
    id bigint generated always as identity primary key,
    object_type text not null,
    object_id uuid not null,
    org_id uuid not null,
    yacht_id uuid,
    search_text text not null,
    tsv tsvector generated always as (to_tsvector('english', coalesce(search_text, ''))) stored,
    embedding vector(384),
    payload jsonb default '{}'::jsonb,
    embedding_version smallint default 1,
    updated_at timestamptz default now(),

    -- Unique constraint on (object_type, object_id) to enable upsert
    unique(object_type, object_id)
);

-- Add comment for documentation
comment on table search_index is 'F1 Search unified search surface. See apps/api/docs/F1_SEARCH/DB_HYBRID_SEARCH_SPEC.md';
comment on column search_index.embedding is 'Computed by async job, NOT by trigger. 384-dim vector.';
comment on column search_index.embedding_version is 'Track model version for re-embedding on model upgrades.';

-- ============================================================================
-- 3. INDEXES
-- ============================================================================

-- Trigram index for similarity/fuzzy search
create index if not exists ix_search_text_trgm
    on search_index using gin (search_text gin_trgm_ops);

-- Full-text search index on generated tsvector
create index if not exists ix_search_tsv
    on search_index using gin (tsv);

-- RLS optimization: org_id + object_type for filtered scans
create index if not exists ix_search_rls
    on search_index (org_id, object_type);

-- HNSW vector index for approximate nearest neighbor search
-- Parameters: m=16 (connections per node), ef_construction=64 (build quality)
create index if not exists ix_search_vector
    on search_index using hnsw (embedding vector_cosine_ops)
    with (m = 16, ef_construction = 64);

-- Yacht-scoped index for multi-tenant yacht queries
create index if not exists ix_search_yacht
    on search_index (org_id, yacht_id)
    where yacht_id is not null;

-- ============================================================================
-- 4. ROW LEVEL SECURITY (RLS)
-- ============================================================================
--
-- SECURITY: Uses JWT claims, NOT auth.users lookup.
-- Reason: auth.users lookup harms planner selectivity and breaks in replicas.
--
-- Claims format: current_setting('request.jwt.claims', true)::jsonb
-- Expected claims: org_id (required), yacht_id (optional)
-- ============================================================================

alter table search_index enable row level security;

-- Drop existing policy if present (idempotent)
drop policy if exists search_index_select on search_index;

-- Create select policy: User can only read rows from their org + optional yacht
create policy search_index_select on search_index for select using (
    org_id = (current_setting('request.jwt.claims', true)::jsonb ->> 'org_id')::uuid
    and (
        yacht_id is null
        or yacht_id = nullif(
            (current_setting('request.jwt.claims', true)::jsonb ->> 'yacht_id'),
            ''
        )::uuid
    )
);

-- Service role bypass for admin operations
drop policy if exists search_index_service_select on search_index;
create policy search_index_service_select on search_index for select
    to service_role using (true);

-- Insert/Update/Delete policies for service role only
drop policy if exists search_index_service_insert on search_index;
create policy search_index_service_insert on search_index for insert
    to service_role with check (true);

drop policy if exists search_index_service_update on search_index;
create policy search_index_service_update on search_index for update
    to service_role using (true);

drop policy if exists search_index_service_delete on search_index;
create policy search_index_service_delete on search_index for delete
    to service_role using (true);

-- ============================================================================
-- 5. HYPER_SEARCH RPC (Single Round-Trip, RRF Fusion)
-- ============================================================================
--
-- SECURITY: Uses SECURITY INVOKER (NOT DEFINER) to enforce RLS.
-- If you use SECURITY DEFINER, you bypass RLS - that's a bug, not a feature.
--
-- Fusion: Reciprocal Rank Fusion (RRF)
--   fused_score = Σ 1.0/(rrf_k + rank)
--   where rrf_k = 60 (default)
--
-- Sub-searches:
--   - trigram: similarity(search_text, query_text), LIMIT 50
--   - fts: ts_rank(tsv, websearch_to_tsquery), LIMIT 50
--   - vec: 1 - (embedding <=> query_embedding), LIMIT 100
--
-- Returns top page_limit results with ranks and component scores.
-- ============================================================================

create or replace function hyper_search(
    query_text text,
    query_embedding vector(384),
    filter_org_id uuid,
    filter_yacht_id uuid default null,
    rrf_k int default 60,
    page_limit int default 20
) returns table (
    object_type text,
    object_id uuid,
    payload jsonb,
    fused_score double precision,
    ranks jsonb,
    components jsonb
) security invoker language sql as $$
    select
        object_type,
        object_id,
        payload,
        (
            coalesce(1.0 / (rrf_k + trigram_rank), 0) +
            coalesce(1.0 / (rrf_k + fts_rank), 0) +
            coalesce(1.0 / (rrf_k + vector_rank), 0)
        ) as fused_score,
        jsonb_build_object(
            'trigram', trigram_rank,
            'fts', fts_rank,
            'vector', vector_rank
        ) as ranks,
        jsonb_build_object(
            'trigram', trigram_score,
            'fts', fts_score,
            'vector', vector_sim
        ) as components
    from (
        with
        -- Trigram similarity search (fuzzy matching)
        trigram as (
            select
                object_type,
                object_id,
                similarity(search_text, query_text) as trigram_score,
                row_number() over (order by similarity(search_text, query_text) desc) as trigram_rank
            from search_index
            where org_id = filter_org_id
                and (filter_yacht_id is null or yacht_id = filter_yacht_id)
                and search_text % query_text  -- Trigram similarity operator
            limit 50
        ),

        -- Full-text search (keyword matching)
        fts as (
            select
                object_type,
                object_id,
                ts_rank(tsv, websearch_to_tsquery('english', query_text)) as fts_score,
                row_number() over (
                    order by ts_rank(tsv, websearch_to_tsquery('english', query_text)) desc
                ) as fts_rank
            from search_index
            where org_id = filter_org_id
                and (filter_yacht_id is null or yacht_id = filter_yacht_id)
                and tsv @@ websearch_to_tsquery('english', query_text)
            limit 50
        ),

        -- Vector similarity search (semantic matching)
        vec as (
            select
                object_type,
                object_id,
                1 - (embedding <=> query_embedding) as vector_sim,
                row_number() over (order by embedding <=> query_embedding asc) as vector_rank
            from search_index
            where org_id = filter_org_id
                and (filter_yacht_id is null or yacht_id = filter_yacht_id)
                and embedding is not null
                and query_embedding is not null  -- Skip if no embedding provided
            order by embedding <=> query_embedding asc
            limit 100
        )

        -- Union all results and aggregate
        select
            coalesce(t.object_type, f.object_type, v.object_type) as object_type,
            coalesce(t.object_id, f.object_id, v.object_id) as object_id,
            coalesce(si.payload, '{}'::jsonb) as payload,
            min(t.trigram_rank) as trigram_rank,
            min(f.fts_rank) as fts_rank,
            min(v.vector_rank) as vector_rank,
            max(t.trigram_score) as trigram_score,
            max(f.fts_score) as fts_score,
            max(v.vector_sim) as vector_sim
        from (
            select object_type, object_id from trigram
            union
            select object_type, object_id from fts
            union
            select object_type, object_id from vec
        ) u
        left join trigram t using (object_type, object_id)
        left join fts f using (object_type, object_id)
        left join vec v using (object_type, object_id)
        left join search_index si using (object_type, object_id)
        group by 1, 2, 3
    ) s
    order by fused_score desc
    limit page_limit;
$$;

-- Add function comment
comment on function hyper_search is 'F1 Search hybrid search with RRF fusion. SECURITY INVOKER enforces RLS.';

-- ============================================================================
-- 6. UPSERT TRIGGER FOR PARTS TABLE
-- ============================================================================
--
-- CRITICAL: Do NOT compute embeddings in trigger.
-- Trigger only upserts text + payload. Embeddings computed by async job.
--
-- Why: External API calls in triggers stall writes and cause timeouts.
-- ============================================================================

create or replace function upsert_search_index_parts()
returns trigger language plpgsql as $$
begin
    insert into search_index(
        object_type,
        object_id,
        org_id,
        yacht_id,
        search_text,
        payload,
        updated_at
    )
    values (
        'part',
        new.id,
        new.org_id,
        new.yacht_id,
        -- Concatenate searchable fields
        coalesce(new.name, '') || ' ' ||
        coalesce(new.description, '') || ' ' ||
        coalesce(new.part_number, '') || ' ' ||
        coalesce(new.manufacturer, '') || ' ' ||
        coalesce(new.category, ''),
        -- Minimal payload for display
        jsonb_build_object(
            'name', new.name,
            'part_number', new.part_number,
            'manufacturer', new.manufacturer,
            'category', new.category,
            'location', new.location
        ),
        now()
    )
    on conflict (object_type, object_id)
    do update set
        search_text = excluded.search_text,
        payload = excluded.payload,
        updated_at = now();

    return null;  -- AFTER trigger, return value ignored
end;
$$;

-- Drop existing trigger if present (idempotent)
drop trigger if exists trg_parts_search_index on pms_parts;

-- Create trigger on parts table
-- Note: Adjust table name if your parts table has a different name
create trigger trg_parts_search_index
    after insert or update on pms_parts
    for each row execute function upsert_search_index_parts();

-- Add trigger comment
comment on function upsert_search_index_parts is 'Upserts part data to search_index. Does NOT compute embeddings - that is done by async job.';

-- ============================================================================
-- 7. VERIFICATION QUERIES
-- ============================================================================
--
-- Run these after migration to verify setup:
--
-- -- Check table exists and has correct structure
-- \d search_index
--
-- -- Check indexes exist
-- select indexname from pg_indexes where tablename = 'search_index';
--
-- -- Check RLS is enabled
-- select relname, relrowsecurity from pg_class where relname = 'search_index';
--
-- -- Check function exists
-- select proname from pg_proc where proname = 'hyper_search';
--
-- -- Test hyper_search (replace with real org_id)
-- explain analyze
-- select * from hyper_search(
--     '3512C',                              -- query_text
--     NULL,                                 -- query_embedding (NULL until embeddings ready)
--     'your-org-uuid-here'::uuid,           -- filter_org_id
--     NULL,                                 -- filter_yacht_id
--     60,                                   -- rrf_k
--     20                                    -- page_limit
-- );
--
-- -- Check trigger exists
-- select tgname from pg_trigger where tgname = 'trg_parts_search_index';
-- ============================================================================

-- Notify completion
do $$
begin
    raise notice 'F1 Search migration completed successfully';
    raise notice 'Extensions: vector, pg_trgm';
    raise notice 'Table: search_index';
    raise notice 'Indexes: ix_search_text_trgm, ix_search_tsv, ix_search_rls, ix_search_vector, ix_search_yacht';
    raise notice 'RLS: Enabled with org_id + yacht_id policies';
    raise notice 'RPC: hyper_search (SECURITY INVOKER)';
    raise notice 'Trigger: trg_parts_search_index on pms_parts';
end $$;
