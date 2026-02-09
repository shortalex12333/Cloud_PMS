-- ============================================================================
-- Migration: 020_search_index_hard_tiers_and_vec1536.sql
-- Description: Add Hard Tiers columns and 1536-dim embedding support to search_index
-- Date: 2026-02-05
-- ============================================================================

-- Hard Tiers columns for deterministic ranking
ALTER TABLE public.search_index ADD COLUMN IF NOT EXISTS recency_ts TIMESTAMPTZ;
ALTER TABLE public.search_index ADD COLUMN IF NOT EXISTS ident_norm TEXT;

-- 1536-dim embedding columns (OpenAI text-embedding-3-small)
ALTER TABLE public.search_index ADD COLUMN IF NOT EXISTS embedding_1536 vector(1536);
ALTER TABLE public.search_index ADD COLUMN IF NOT EXISTS embedding_model TEXT;
ALTER TABLE public.search_index ADD COLUMN IF NOT EXISTS embedding_version INT;
ALTER TABLE public.search_index ADD COLUMN IF NOT EXISTS embedding_hash TEXT;

-- source_version for idempotent upserts
ALTER TABLE public.search_index ADD COLUMN IF NOT EXISTS source_version BIGINT DEFAULT 1;

COMMENT ON COLUMN public.search_index.recency_ts IS 'Canonical timestamp for Hard Tiers recency sorting (per-domain mapping)';
COMMENT ON COLUMN public.search_index.ident_norm IS 'Normalized identifier for exact ID matching (UPPER, no dashes/spaces)';
COMMENT ON COLUMN public.search_index.embedding_1536 IS 'OpenAI text-embedding-3-small 1536-dim vector';
COMMENT ON COLUMN public.search_index.embedding_model IS 'Model used to generate embedding (e.g., text-embedding-3-small)';
COMMENT ON COLUMN public.search_index.embedding_version IS 'Schema version for embedding (current: 3)';
COMMENT ON COLUMN public.search_index.embedding_hash IS 'SHA-256 hash of search_text for delta embedding';
COMMENT ON COLUMN public.search_index.source_version IS 'Monotonic version from source table for idempotent upserts';

-- ============================================================================
-- Indexes for Hard Tiers
-- ============================================================================

-- Recency index for ORDER BY recency_ts DESC
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_si_recency
    ON public.search_index (recency_ts DESC NULLS LAST);

-- ident_norm index for exact ID matching
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_si_ident_norm
    ON public.search_index (ident_norm)
    WHERE ident_norm IS NOT NULL;

-- Composite index for Hard Tiers ORDER BY
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_si_hard_tiers
    ON public.search_index (object_type, recency_ts DESC NULLS LAST, ident_norm)
    WHERE ident_norm IS NOT NULL;

-- ============================================================================
-- HNSW Index for 1536-dim vectors
-- ============================================================================

-- HNSW index for cosine similarity on 1536-dim embeddings
-- m=16, ef_construction=64 balances build time vs recall
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_si_vec1536_hnsw
    ON public.search_index
    USING hnsw (embedding_1536 vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- ============================================================================
-- Embedding delta tracking index
-- ============================================================================

-- Index for finding rows needing embedding
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_si_needs_embedding
    ON public.search_index (updated_at DESC)
    WHERE embedding_1536 IS NULL
       OR embedding_hash IS NULL
       OR embedding_version IS NULL
       OR embedding_version < 3;

-- ============================================================================
-- Learned preferences table for user/org term→domain affinity
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.search_term_domain_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    term_hash TEXT NOT NULL,           -- MD5 of normalized search term
    domain TEXT NOT NULL,              -- object_type
    user_id UUID,                      -- NULL = org-level stat
    org_id UUID NOT NULL,
    click_count INT DEFAULT 0,
    last_click_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (term_hash, domain, user_id, org_id)
);

COMMENT ON TABLE public.search_term_domain_stats IS 'Learned preferences: user click patterns for personalized ranking';

CREATE INDEX IF NOT EXISTS ix_stds_lookup
    ON public.search_term_domain_stats (org_id, term_hash, domain);
CREATE INDEX IF NOT EXISTS ix_stds_user_lookup
    ON public.search_term_domain_stats (user_id, term_hash, domain)
    WHERE user_id IS NOT NULL;

-- Enable RLS
ALTER TABLE public.search_term_domain_stats ENABLE ROW LEVEL SECURITY;

-- RLS policy: users can read/write their own org's stats
CREATE POLICY search_term_domain_stats_org_access ON public.search_term_domain_stats
    FOR ALL
    USING (org_id = (SELECT org_id FROM auth.users WHERE id = auth.uid()))
    WITH CHECK (org_id = (SELECT org_id FROM auth.users WHERE id = auth.uid()));

-- ============================================================================
-- NOTE: Do NOT drop legacy embedding column yet
-- Keep for backward compatibility until 95%+ coverage on embedding_1536
-- ============================================================================
