-- Migration 007: Facet Registry
-- Governance table for filter facets - controls which facets are promoted to indexed columns

-- 1) Create facet registry table
CREATE TABLE IF NOT EXISTS facet_registry (
    id SERIAL PRIMARY KEY,
    facet_key TEXT NOT NULL,
    domain TEXT NOT NULL,  -- 'inventory', 'document', 'work_order', etc.
    data_type TEXT NOT NULL DEFAULT 'text',  -- 'text', 'int', 'date', 'boolean'
    storage TEXT NOT NULL DEFAULT 'jsonb',  -- 'jsonb', 'generated', 'typed'
    promoted BOOLEAN NOT NULL DEFAULT FALSE,
    index_type TEXT,  -- 'btree', 'gin', 'brin', NULL
    index_name TEXT,  -- name of the index if created
    usage_30d_pct NUMERIC(5,2) DEFAULT 0,
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(domain, facet_key)
);

-- 2) Seed initial facets

-- Inventory facets
INSERT INTO facet_registry (domain, facet_key, data_type, promoted, index_type, storage) VALUES
    ('inventory', 'make', 'text', TRUE, 'btree', 'jsonb'),
    ('inventory', 'status', 'text', TRUE, 'btree', 'jsonb'),
    ('inventory', 'category', 'text', FALSE, NULL, 'jsonb'),
    ('inventory', 'location', 'text', FALSE, NULL, 'jsonb')
ON CONFLICT (domain, facet_key) DO NOTHING;

-- Document facets
INSERT INTO facet_registry (domain, facet_key, data_type, promoted, index_type, storage) VALUES
    ('document', 'doc_type', 'text', TRUE, 'btree', 'jsonb'),
    ('document', 'revision_date', 'date', TRUE, 'brin', 'jsonb'),
    ('document', 'system', 'text', FALSE, NULL, 'jsonb')
ON CONFLICT (domain, facet_key) DO NOTHING;

-- Work order facets
INSERT INTO facet_registry (domain, facet_key, data_type, promoted, index_type, storage) VALUES
    ('work_order', 'status', 'text', TRUE, 'btree', 'jsonb'),
    ('work_order', 'priority', 'text', TRUE, 'btree', 'jsonb'),
    ('work_order', 'due_date', 'date', TRUE, 'btree', 'jsonb'),
    ('work_order', 'assigned_to', 'text', FALSE, NULL, 'jsonb')
ON CONFLICT (domain, facet_key) DO NOTHING;

-- 3) Create expression indexes for promoted facets
-- These allow fast filtering on filters->>'key' without scanning

-- Inventory indexes
CREATE INDEX IF NOT EXISTS ix_filters_make
    ON search_index ((filters->>'make'))
    WHERE filters->>'make' IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_filters_inv_status
    ON search_index ((filters->>'status'))
    WHERE object_type = 'inventory' AND filters->>'status' IS NOT NULL;

-- Document indexes
CREATE INDEX IF NOT EXISTS ix_filters_doc_type
    ON search_index ((filters->>'doc_type'))
    WHERE object_type = 'document' AND filters->>'doc_type' IS NOT NULL;

-- Work order indexes
CREATE INDEX IF NOT EXISTS ix_filters_wo_status
    ON search_index ((filters->>'status'))
    WHERE object_type = 'work_order' AND filters->>'status' IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_filters_wo_priority
    ON search_index ((filters->>'priority'))
    WHERE object_type = 'work_order' AND filters->>'priority' IS NOT NULL;

-- 4) Update index_name in registry for reference
UPDATE facet_registry SET index_name = 'ix_filters_make' WHERE domain = 'inventory' AND facet_key = 'make';
UPDATE facet_registry SET index_name = 'ix_filters_inv_status' WHERE domain = 'inventory' AND facet_key = 'status';
UPDATE facet_registry SET index_name = 'ix_filters_doc_type' WHERE domain = 'document' AND facet_key = 'doc_type';
UPDATE facet_registry SET index_name = 'ix_filters_wo_status' WHERE domain = 'work_order' AND facet_key = 'status';
UPDATE facet_registry SET index_name = 'ix_filters_wo_priority' WHERE domain = 'work_order' AND facet_key = 'priority';

-- 5) Add GIN index on filters jsonb for non-promoted facets (if not exists)
CREATE INDEX IF NOT EXISTS ix_filters_gin ON search_index USING GIN (filters);

-- 6) Function to update usage stats (call weekly from cron)
CREATE OR REPLACE FUNCTION update_facet_usage()
RETURNS void AS $$
BEGIN
    -- This would be updated from search_query_logs analysis
    -- For now, just update the updated_at timestamp
    UPDATE facet_registry SET updated_at = NOW();
END;
$$ LANGUAGE plpgsql;

COMMENT ON TABLE facet_registry IS 'Governance table for search filter facets. Controls which facets are promoted to indexed columns for performance.';
