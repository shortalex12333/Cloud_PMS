-- ============================================================================
-- F1 Search Phase 3: Partitioning Pilot
-- ============================================================================
--
-- Makes search_index a partitioned table by org_id.
-- Attaches existing table as DEFAULT partition.
-- Creates one org-specific partition for pilot org.
--
-- Run during maintenance window (short lock when renaming/attaching).
-- ============================================================================

BEGIN;

-- 0) Drop IDENTITY from existing table (required before attaching as partition)
ALTER TABLE search_index ALTER COLUMN id DROP IDENTITY IF EXISTS;

-- 0b) Drop existing constraints that don't include org_id (must be recreated with org_id)
ALTER TABLE search_index DROP CONSTRAINT IF EXISTS search_index_pkey;
ALTER TABLE search_index DROP CONSTRAINT IF EXISTS search_index_object_type_object_id_key;

-- 0c) Add composite constraints that include org_id (required for partitioning)
ALTER TABLE search_index ADD PRIMARY KEY (id, org_id);
ALTER TABLE search_index ADD CONSTRAINT search_index_object_type_object_id_org_id_key
    UNIQUE (object_type, object_id, org_id);

-- 1) Rename current main table to become DEFAULT partition
ALTER TABLE search_index RENAME TO search_index_default;

-- 2) Create partitioned parent with identical structure (no IDENTITY, uses sequence)
CREATE SEQUENCE IF NOT EXISTS search_index_id_seq;

CREATE TABLE search_index (
    id                  bigint NOT NULL DEFAULT nextval('search_index_id_seq'),
    object_type         text NOT NULL,
    object_id           uuid NOT NULL,
    org_id              uuid NOT NULL,
    yacht_id            uuid,
    search_text         text NOT NULL,
    tsv                 tsvector GENERATED ALWAYS AS (to_tsvector('english', coalesce(search_text, ''))) STORED,
    embedding           vector(384),
    payload             jsonb DEFAULT '{}'::jsonb,
    embedding_version   smallint DEFAULT 1,
    popularity_score    double precision DEFAULT 0,
    updated_at          timestamptz DEFAULT now(),
    PRIMARY KEY (id, org_id),
    UNIQUE (object_type, object_id, org_id)
) PARTITION BY LIST (org_id);

-- 3) Attach existing table as DEFAULT partition
ALTER TABLE search_index ATTACH PARTITION search_index_default DEFAULT;

-- 4) Create dedicated partition for pilot org
CREATE TABLE search_index_pilot_org
    PARTITION OF search_index FOR VALUES IN ('85fe1119-b04c-41ac-80f1-829d23322598');

-- 5) Create partitioned indexes on parent (propagates/builds on all partitions)
CREATE INDEX IF NOT EXISTS ix_search_text_trgm_p ON search_index USING gin (search_text gin_trgm_ops);
CREATE INDEX IF NOT EXISTS ix_search_tsv_p       ON search_index USING gin (tsv);
CREATE INDEX IF NOT EXISTS ix_search_rls_p       ON search_index (org_id, object_type);
CREATE INDEX IF NOT EXISTS ix_search_vector_p    ON search_index USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=64);

-- 6) Move pilot org rows from DEFAULT to its partition
WITH moved AS (
    DELETE FROM search_index_default
    WHERE org_id = '85fe1119-b04c-41ac-80f1-829d23322598'::uuid
    RETURNING *
)
INSERT INTO search_index_pilot_org SELECT * FROM moved;

-- 7) Re-apply RLS on parent so all partitions inherit (idempotent)
ALTER TABLE search_index ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS search_index_select ON search_index;
CREATE POLICY search_index_select ON search_index
    FOR SELECT USING (
        org_id = (current_setting('request.jwt.claims', true)::jsonb ->> 'org_id')::uuid
        AND (yacht_id IS NULL OR yacht_id = nullif((current_setting('request.jwt.claims', true)::jsonb ->> 'yacht_id'), '')::uuid)
    );

COMMIT;
