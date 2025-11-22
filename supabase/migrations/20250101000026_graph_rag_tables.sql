-- ============================================================================
-- GRAPH RAG TABLES
-- ============================================================================
-- Explicit graph tables for GraphRAG - relationship discovery, pattern analysis
-- Node types: equipment, faults, parts, manuals/docs, work_orders, predictive_insights
-- Edge types: equipment↔fault, equipment↔part, work_order↔equipment, manual↔equipment, predictive↔equipment

-- GRAPH NODES TABLE
CREATE TABLE IF NOT EXISTS public.graph_nodes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- Node identification
    node_type TEXT NOT NULL CHECK (node_type IN (
        'equipment', 'part', 'fault', 'doc_chunk', 'document',
        'work_order', 'handover_item', 'predictive_insight', 'supplier'
    )),
    node_key TEXT NOT NULL,                  -- Unique key within type (e.g., equipment code)

    -- Reference to source table
    ref_table TEXT NOT NULL,                 -- 'equipment', 'parts', 'faults', 'document_chunks', etc.
    ref_id UUID NOT NULL,                    -- ID in ref_table

    -- Node properties
    label TEXT NOT NULL,                     -- Display label
    properties JSONB DEFAULT '{}'::jsonb,    -- Additional node properties

    -- Embedding for semantic graph queries
    embedding vector(1536),                  -- OpenAI ada-002 dimension

    -- Status
    is_active BOOLEAN DEFAULT true,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Unique constraint
    CONSTRAINT unique_node_ref UNIQUE (yacht_id, ref_table, ref_id)
);

COMMENT ON TABLE public.graph_nodes IS 'Graph nodes for GraphRAG - represents entities in knowledge graph';
COMMENT ON COLUMN public.graph_nodes.node_type IS 'Type of entity this node represents';
COMMENT ON COLUMN public.graph_nodes.node_key IS 'Unique business key within node_type (e.g., equipment code ME1)';
COMMENT ON COLUMN public.graph_nodes.ref_table IS 'Source table this node mirrors';
COMMENT ON COLUMN public.graph_nodes.embedding IS 'Vector embedding for semantic graph search';

-- GRAPH EDGES TABLE
CREATE TABLE IF NOT EXISTS public.graph_edges (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- Edge endpoints
    from_node_id UUID NOT NULL REFERENCES public.graph_nodes(id) ON DELETE CASCADE,
    to_node_id UUID NOT NULL REFERENCES public.graph_nodes(id) ON DELETE CASCADE,

    -- Edge classification
    edge_type TEXT NOT NULL CHECK (edge_type IN (
        -- Equipment relationships
        'PARENT_OF', 'CHILD_OF', 'RELATED_TO',
        -- Fault relationships
        'HAS_FAULT', 'CAUSED_BY', 'LEADS_TO',
        -- Part relationships
        'USES_PART', 'COMPATIBLE_WITH', 'REPLACED_BY',
        -- Document relationships
        'MENTIONED_IN', 'DOCUMENTED_BY', 'REFERS_TO',
        -- Work order relationships
        'REQUIRES_WO', 'RESOLVED_BY', 'TRIGGERED_BY',
        -- Handover relationships
        'INCLUDED_IN',
        -- Predictive relationships
        'PREDICTED_FOR', 'SIMILAR_TO', 'CORRELATED_WITH'
    )),

    -- Edge properties
    weight NUMERIC(5,4) DEFAULT 1.0,         -- Edge weight for traversal algorithms
    confidence NUMERIC(3,2),                 -- Confidence score for inferred edges
    properties JSONB DEFAULT '{}'::jsonb,    -- Additional edge properties

    -- Source of edge
    source TEXT DEFAULT 'system' CHECK (source IN ('system', 'user', 'inferred', 'imported')),

    -- Status
    is_active BOOLEAN DEFAULT true,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Prevent duplicate edges
    CONSTRAINT unique_edge UNIQUE (from_node_id, to_node_id, edge_type)
);

COMMENT ON TABLE public.graph_edges IS 'Graph edges for GraphRAG - relationships between entities';
COMMENT ON COLUMN public.graph_edges.edge_type IS 'Type of relationship between nodes';
COMMENT ON COLUMN public.graph_edges.weight IS 'Edge weight for graph algorithms (PageRank, etc.)';
COMMENT ON COLUMN public.graph_edges.confidence IS 'Confidence score for ML-inferred edges';

-- Indexes for graph_nodes
CREATE INDEX IF NOT EXISTS idx_graph_nodes_yacht_id ON public.graph_nodes(yacht_id);
CREATE INDEX IF NOT EXISTS idx_graph_nodes_type ON public.graph_nodes(yacht_id, node_type);
CREATE INDEX IF NOT EXISTS idx_graph_nodes_key ON public.graph_nodes(yacht_id, node_type, node_key);
CREATE INDEX IF NOT EXISTS idx_graph_nodes_ref ON public.graph_nodes(ref_table, ref_id);
CREATE INDEX IF NOT EXISTS idx_graph_nodes_label_gin ON public.graph_nodes USING gin (label gin_trgm_ops);

-- Vector index for semantic graph search
CREATE INDEX IF NOT EXISTS idx_graph_nodes_embedding ON public.graph_nodes
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Indexes for graph_edges
CREATE INDEX IF NOT EXISTS idx_graph_edges_yacht_id ON public.graph_edges(yacht_id);
CREATE INDEX IF NOT EXISTS idx_graph_edges_from ON public.graph_edges(from_node_id);
CREATE INDEX IF NOT EXISTS idx_graph_edges_to ON public.graph_edges(to_node_id);
CREATE INDEX IF NOT EXISTS idx_graph_edges_type ON public.graph_edges(yacht_id, edge_type);
CREATE INDEX IF NOT EXISTS idx_graph_edges_bidirectional ON public.graph_edges(from_node_id, to_node_id);

-- Composite index for graph traversal queries
CREATE INDEX IF NOT EXISTS idx_graph_edges_traverse ON public.graph_edges(from_node_id, edge_type, to_node_id)
    WHERE is_active = true;

-- Verification
DO $$
BEGIN
    RAISE NOTICE '✓ Migration 026 Complete - Created graph_nodes and graph_edges tables for GraphRAG';
END $$;
