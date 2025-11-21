-- ============================================================================
-- Graph RAG Schema for CelesteOS
-- ============================================================================
-- This migration creates the canonical entity tables, alias resolution,
-- graph edges, and maintenance facts persistence layer.
--
-- Run with: supabase db push
-- ============================================================================

-- ============================================================================
-- ENUMS
-- ============================================================================

-- Entity types for the knowledge graph
CREATE TYPE entity_type AS ENUM (
    'equipment',
    'part',
    'fault',
    'symptom',
    'supplier',
    'document',
    'work_order',
    'handover_item',
    'person',
    'location',
    'system'
);

-- Edge types for relationships
CREATE TYPE edge_type AS ENUM (
    'USES_PART',
    'HAS_FAULT',
    'HAS_SYMPTOM',
    'MENTIONED_IN',
    'REFERS_TO',
    'COMPATIBLE_WITH',
    'RELATED_TO',
    'HAS_WORK_ORDER',
    'SUPPLIED_BY',
    'LOCATED_IN',
    'PART_OF',
    'REPLACED_BY',
    'REQUIRES_TOOL',
    'HAS_MAINTENANCE'
);

-- System types (for equipment categorization)
CREATE TYPE system_type AS ENUM (
    'PROPULSION',
    'ELECTRICAL',
    'HVAC',
    'NAVIGATION',
    'SAFETY',
    'DECK',
    'INTERIOR',
    'PLUMBING',
    'FUEL',
    'HYDRAULIC',
    'COMMUNICATION',
    'ANCHOR',
    'TENDER',
    'OTHER'
);

-- Maintenance action types
CREATE TYPE maintenance_action AS ENUM (
    'inspect',
    'replace',
    'clean',
    'service',
    'lubricate',
    'calibrate',
    'test',
    'adjust',
    'overhaul'
);

-- Extraction status for tracking
CREATE TYPE extraction_status AS ENUM (
    'pending',
    'processing',
    'success',
    'failed',
    'empty',
    'partial'
);

-- ============================================================================
-- CANONICAL ENTITY TABLES
-- ============================================================================

-- Equipment: Main engines, generators, pumps, etc.
CREATE TABLE IF NOT EXISTS equipment (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL,
    canonical_name TEXT NOT NULL,
    display_name TEXT,
    oem TEXT,
    model TEXT,
    serial_number TEXT,
    system_type system_type DEFAULT 'OTHER',
    location TEXT,
    parent_equipment_id UUID REFERENCES equipment(id),
    properties JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(yacht_id, canonical_name)
);

-- Parts: Components, consumables, spares
CREATE TABLE IF NOT EXISTS parts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL,
    canonical_name TEXT NOT NULL,
    display_name TEXT,
    manufacturer TEXT,
    part_number TEXT,
    oem_part_number TEXT,
    category TEXT,
    unit_of_measure TEXT,
    min_stock_level INT,
    current_stock INT DEFAULT 0,
    properties JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(yacht_id, canonical_name)
);

-- Faults: Error codes, failure modes
CREATE TABLE IF NOT EXISTS faults (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL,
    fault_code TEXT NOT NULL,
    canonical_name TEXT NOT NULL,
    severity TEXT CHECK (severity IN ('critical', 'high', 'medium', 'low', 'info')),
    category TEXT,
    description TEXT,
    resolution_steps TEXT[],
    properties JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(yacht_id, fault_code)
);

-- Symptom Catalog: Standardized symptoms
CREATE TABLE IF NOT EXISTS symptom_catalog (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symptom_code TEXT NOT NULL UNIQUE,
    canonical_name TEXT NOT NULL,
    category TEXT,
    equipment_class TEXT[],  -- Which equipment types this applies to
    related_fault_codes TEXT[],
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Suppliers: Vendors, manufacturers
CREATE TABLE IF NOT EXISTS suppliers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL,
    canonical_name TEXT NOT NULL,
    display_name TEXT,
    contact_email TEXT,
    contact_phone TEXT,
    website TEXT,
    categories TEXT[],
    properties JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(yacht_id, canonical_name)
);

-- ============================================================================
-- ALIAS RESOLUTION TABLES
-- ============================================================================

-- Entity Aliases: Maps text labels to canonical entities
CREATE TABLE IF NOT EXISTS entity_aliases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL,
    entity_type entity_type NOT NULL,
    canonical_id UUID NOT NULL,  -- References the appropriate canonical table
    alias_text TEXT NOT NULL,
    alias_text_lower TEXT GENERATED ALWAYS AS (LOWER(alias_text)) STORED,
    confidence FLOAT DEFAULT 1.0,
    source TEXT,  -- 'manual', 'extracted', 'inferred'
    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(yacht_id, entity_type, alias_text_lower)
);

-- Symptom Aliases: Maps symptom phrases to symptom codes
CREATE TABLE IF NOT EXISTS symptom_aliases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symptom_code TEXT NOT NULL REFERENCES symptom_catalog(symptom_code),
    alias_text TEXT NOT NULL,
    alias_text_lower TEXT GENERATED ALWAYS AS (LOWER(alias_text)) STORED,
    confidence FLOAT DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(symptom_code, alias_text_lower)
);

-- ============================================================================
-- GRAPH NODES & EDGES
-- ============================================================================

-- Graph Nodes: All extracted entities (before canonical resolution)
CREATE TABLE IF NOT EXISTS graph_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL,
    node_type entity_type NOT NULL,
    ref_table TEXT,  -- 'document_chunks', 'equipment', 'parts', etc.
    ref_id UUID,  -- Reference to source record
    label TEXT NOT NULL,
    canonical_id UUID,  -- Resolved canonical entity ID (nullable until resolved)
    properties JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Index for fast lookups
    CONSTRAINT unique_node_per_chunk UNIQUE(yacht_id, ref_id, label, node_type)
);

-- Graph Edges: Relationships between entities
CREATE TABLE IF NOT EXISTS graph_edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL,
    edge_type edge_type NOT NULL,
    from_node_id UUID REFERENCES graph_nodes(id) ON DELETE CASCADE,
    to_node_id UUID REFERENCES graph_nodes(id) ON DELETE CASCADE,
    from_label TEXT NOT NULL,  -- Denormalized for query performance
    to_label TEXT NOT NULL,
    from_canonical_id UUID,  -- Resolved canonical entity (nullable)
    to_canonical_id UUID,
    source_chunk_id UUID,  -- Where this relationship was extracted from
    confidence FLOAT DEFAULT 1.0,
    properties JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Prevent duplicate edges
    CONSTRAINT unique_edge UNIQUE(yacht_id, edge_type, from_label, to_label, source_chunk_id)
);

-- ============================================================================
-- MAINTENANCE FACTS
-- ============================================================================

-- Maintenance Templates: Extracted maintenance requirements
CREATE TABLE IF NOT EXISTS maintenance_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL,
    equipment_id UUID REFERENCES equipment(id),
    part_id UUID REFERENCES parts(id),
    source_chunk_id UUID NOT NULL,  -- Where this was extracted from

    -- Maintenance details
    interval_hours INT,
    interval_days INT,
    interval_description TEXT,
    action maintenance_action,
    action_description TEXT,

    -- Context
    conditions TEXT[],  -- When this maintenance applies
    tools_required TEXT[],
    estimated_duration_hours FLOAT,

    -- Raw extraction for debugging
    raw_extraction JSONB,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Index for equipment lookups
    CONSTRAINT unique_maintenance_per_chunk UNIQUE(source_chunk_id, equipment_id, part_id, action)
);

-- ============================================================================
-- DOCUMENT CHUNKS EXTENSIONS
-- ============================================================================

-- Add columns to document_chunks for richer metadata
-- (Run as ALTER if table already exists)

DO $$
BEGIN
    -- Add extraction status tracking
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'document_chunks' AND column_name = 'graph_extraction_status') THEN
        ALTER TABLE document_chunks ADD COLUMN graph_extraction_status extraction_status DEFAULT 'pending';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'document_chunks' AND column_name = 'graph_extraction_errors') THEN
        ALTER TABLE document_chunks ADD COLUMN graph_extraction_errors TEXT[];
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'document_chunks' AND column_name = 'extracted_entity_count') THEN
        ALTER TABLE document_chunks ADD COLUMN extracted_entity_count INT DEFAULT 0;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'document_chunks' AND column_name = 'extracted_relationship_count') THEN
        ALTER TABLE document_chunks ADD COLUMN extracted_relationship_count INT DEFAULT 0;
    END IF;

    -- Add chunk metadata for navigation
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'document_chunks' AND column_name = 'page_number') THEN
        ALTER TABLE document_chunks ADD COLUMN page_number INT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'document_chunks' AND column_name = 'section_title') THEN
        ALTER TABLE document_chunks ADD COLUMN section_title TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'document_chunks' AND column_name = 'section_path') THEN
        ALTER TABLE document_chunks ADD COLUMN section_path TEXT[];
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'document_chunks' AND column_name = 'system_tag') THEN
        ALTER TABLE document_chunks ADD COLUMN system_tag system_type;
    END IF;
END $$;

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- Equipment lookups
CREATE INDEX IF NOT EXISTS idx_equipment_yacht ON equipment(yacht_id);
CREATE INDEX IF NOT EXISTS idx_equipment_system ON equipment(yacht_id, system_type);
CREATE INDEX IF NOT EXISTS idx_equipment_oem ON equipment(yacht_id, oem);

-- Parts lookups
CREATE INDEX IF NOT EXISTS idx_parts_yacht ON parts(yacht_id);
CREATE INDEX IF NOT EXISTS idx_parts_number ON parts(yacht_id, part_number);

-- Faults lookups
CREATE INDEX IF NOT EXISTS idx_faults_yacht ON faults(yacht_id);
CREATE INDEX IF NOT EXISTS idx_faults_code ON faults(yacht_id, fault_code);

-- Entity aliases for fast resolution
CREATE INDEX IF NOT EXISTS idx_entity_aliases_lookup ON entity_aliases(yacht_id, entity_type, alias_text_lower);
CREATE INDEX IF NOT EXISTS idx_symptom_aliases_lookup ON symptom_aliases(alias_text_lower);

-- Graph nodes
CREATE INDEX IF NOT EXISTS idx_graph_nodes_yacht ON graph_nodes(yacht_id);
CREATE INDEX IF NOT EXISTS idx_graph_nodes_type ON graph_nodes(yacht_id, node_type);
CREATE INDEX IF NOT EXISTS idx_graph_nodes_label ON graph_nodes(yacht_id, label);
CREATE INDEX IF NOT EXISTS idx_graph_nodes_canonical ON graph_nodes(yacht_id, canonical_id) WHERE canonical_id IS NOT NULL;

-- Graph edges
CREATE INDEX IF NOT EXISTS idx_graph_edges_yacht ON graph_edges(yacht_id);
CREATE INDEX IF NOT EXISTS idx_graph_edges_type ON graph_edges(yacht_id, edge_type);
CREATE INDEX IF NOT EXISTS idx_graph_edges_from ON graph_edges(from_node_id);
CREATE INDEX IF NOT EXISTS idx_graph_edges_to ON graph_edges(to_node_id);
CREATE INDEX IF NOT EXISTS idx_graph_edges_from_canonical ON graph_edges(from_canonical_id) WHERE from_canonical_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_graph_edges_to_canonical ON graph_edges(to_canonical_id) WHERE to_canonical_id IS NOT NULL;

-- Maintenance templates
CREATE INDEX IF NOT EXISTS idx_maintenance_yacht ON maintenance_templates(yacht_id);
CREATE INDEX IF NOT EXISTS idx_maintenance_equipment ON maintenance_templates(equipment_id);
CREATE INDEX IF NOT EXISTS idx_maintenance_part ON maintenance_templates(part_id);

-- Document chunks extraction status
CREATE INDEX IF NOT EXISTS idx_chunks_extraction_status ON document_chunks(graph_extraction_status)
    WHERE graph_extraction_status != 'success';

-- ============================================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE equipment ENABLE ROW LEVEL SECURITY;
ALTER TABLE parts ENABLE ROW LEVEL SECURITY;
ALTER TABLE faults ENABLE ROW LEVEL SECURITY;
ALTER TABLE suppliers ENABLE ROW LEVEL SECURITY;
ALTER TABLE entity_aliases ENABLE ROW LEVEL SECURITY;
ALTER TABLE graph_nodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE graph_edges ENABLE ROW LEVEL SECURITY;
ALTER TABLE maintenance_templates ENABLE ROW LEVEL SECURITY;

-- RLS Policies: Users can only access their yacht's data
CREATE POLICY equipment_yacht_isolation ON equipment
    FOR ALL USING (yacht_id = (current_setting('app.current_yacht_id', true))::uuid);

CREATE POLICY parts_yacht_isolation ON parts
    FOR ALL USING (yacht_id = (current_setting('app.current_yacht_id', true))::uuid);

CREATE POLICY faults_yacht_isolation ON faults
    FOR ALL USING (yacht_id = (current_setting('app.current_yacht_id', true))::uuid);

CREATE POLICY suppliers_yacht_isolation ON suppliers
    FOR ALL USING (yacht_id = (current_setting('app.current_yacht_id', true))::uuid);

CREATE POLICY entity_aliases_yacht_isolation ON entity_aliases
    FOR ALL USING (yacht_id = (current_setting('app.current_yacht_id', true))::uuid);

CREATE POLICY graph_nodes_yacht_isolation ON graph_nodes
    FOR ALL USING (yacht_id = (current_setting('app.current_yacht_id', true))::uuid);

CREATE POLICY graph_edges_yacht_isolation ON graph_edges
    FOR ALL USING (yacht_id = (current_setting('app.current_yacht_id', true))::uuid);

CREATE POLICY maintenance_templates_yacht_isolation ON maintenance_templates
    FOR ALL USING (yacht_id = (current_setting('app.current_yacht_id', true))::uuid);

-- symptom_catalog is global (no yacht_id), so no RLS needed

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function to resolve an alias to its canonical entity
CREATE OR REPLACE FUNCTION resolve_entity_alias(
    p_yacht_id UUID,
    p_entity_type entity_type,
    p_alias_text TEXT
) RETURNS UUID AS $$
DECLARE
    v_canonical_id UUID;
BEGIN
    SELECT canonical_id INTO v_canonical_id
    FROM entity_aliases
    WHERE yacht_id = p_yacht_id
      AND entity_type = p_entity_type
      AND alias_text_lower = LOWER(p_alias_text)
    ORDER BY confidence DESC
    LIMIT 1;

    RETURN v_canonical_id;
END;
$$ LANGUAGE plpgsql;

-- Function to resolve a symptom phrase to symptom code
CREATE OR REPLACE FUNCTION resolve_symptom_alias(
    p_alias_text TEXT
) RETURNS TEXT AS $$
DECLARE
    v_symptom_code TEXT;
BEGIN
    SELECT symptom_code INTO v_symptom_code
    FROM symptom_aliases
    WHERE alias_text_lower = LOWER(p_alias_text)
    ORDER BY confidence DESC
    LIMIT 1;

    RETURN v_symptom_code;
END;
$$ LANGUAGE plpgsql;

-- Function to get equipment with all its relationships
CREATE OR REPLACE FUNCTION get_equipment_graph(
    p_yacht_id UUID,
    p_equipment_id UUID
) RETURNS TABLE (
    relationship edge_type,
    related_type entity_type,
    related_label TEXT,
    related_canonical_id UUID,
    confidence FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ge.edge_type,
        gn.node_type,
        gn.label,
        gn.canonical_id,
        ge.confidence
    FROM graph_edges ge
    JOIN graph_nodes gn ON ge.to_node_id = gn.id
    WHERE ge.yacht_id = p_yacht_id
      AND ge.from_canonical_id = p_equipment_id

    UNION ALL

    SELECT
        ge.edge_type,
        gn.node_type,
        gn.label,
        gn.canonical_id,
        ge.confidence
    FROM graph_edges ge
    JOIN graph_nodes gn ON ge.from_node_id = gn.id
    WHERE ge.yacht_id = p_yacht_id
      AND ge.to_canonical_id = p_equipment_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- SEED DATA: Common symptoms
-- ============================================================================

INSERT INTO symptom_catalog (symptom_code, canonical_name, category, equipment_class, description)
VALUES
    ('OVERHEAT', 'Overheating', 'thermal', ARRAY['engine', 'generator', 'hvac'], 'Temperature exceeds normal operating range'),
    ('VIBRATION', 'Abnormal Vibration', 'mechanical', ARRAY['engine', 'pump', 'generator'], 'Excessive or unusual vibration detected'),
    ('NOISE', 'Abnormal Noise', 'mechanical', ARRAY['engine', 'pump', 'generator', 'hvac'], 'Unusual sounds during operation'),
    ('LEAK_OIL', 'Oil Leak', 'fluid', ARRAY['engine', 'generator', 'hydraulic'], 'Oil leaking from component'),
    ('LEAK_COOLANT', 'Coolant Leak', 'fluid', ARRAY['engine', 'hvac'], 'Coolant leaking from system'),
    ('LEAK_FUEL', 'Fuel Leak', 'fluid', ARRAY['engine', 'generator', 'fuel'], 'Fuel leaking from system'),
    ('LOW_PRESSURE', 'Low Pressure', 'pressure', ARRAY['engine', 'hydraulic', 'fuel'], 'Pressure below normal operating range'),
    ('HIGH_PRESSURE', 'High Pressure', 'pressure', ARRAY['engine', 'hydraulic', 'fuel'], 'Pressure above normal operating range'),
    ('NO_START', 'Failure to Start', 'operational', ARRAY['engine', 'generator'], 'Equipment fails to start'),
    ('STALLING', 'Stalling/Shutdown', 'operational', ARRAY['engine', 'generator'], 'Unexpected shutdown during operation'),
    ('SMOKE', 'Smoke Emission', 'exhaust', ARRAY['engine', 'generator'], 'Visible smoke from exhaust or component'),
    ('CORROSION', 'Corrosion', 'degradation', ARRAY['hull', 'deck', 'piping'], 'Visible corrosion or rust'),
    ('WEAR', 'Excessive Wear', 'degradation', ARRAY['engine', 'pump', 'winch'], 'Component shows signs of excessive wear')
ON CONFLICT (symptom_code) DO NOTHING;

-- Seed symptom aliases
INSERT INTO symptom_aliases (symptom_code, alias_text)
VALUES
    ('OVERHEAT', 'overheating'),
    ('OVERHEAT', 'running hot'),
    ('OVERHEAT', 'too hot'),
    ('OVERHEAT', 'high temperature'),
    ('OVERHEAT', 'temp high'),
    ('VIBRATION', 'vibrating'),
    ('VIBRATION', 'shaking'),
    ('VIBRATION', 'excessive vibration'),
    ('NOISE', 'noisy'),
    ('NOISE', 'loud'),
    ('NOISE', 'grinding'),
    ('NOISE', 'knocking'),
    ('NOISE', 'squealing'),
    ('LEAK_OIL', 'oil leak'),
    ('LEAK_OIL', 'leaking oil'),
    ('LEAK_COOLANT', 'coolant leak'),
    ('LEAK_COOLANT', 'leaking coolant'),
    ('LEAK_COOLANT', 'antifreeze leak'),
    ('LEAK_FUEL', 'fuel leak'),
    ('LEAK_FUEL', 'leaking fuel'),
    ('LEAK_FUEL', 'diesel leak'),
    ('LOW_PRESSURE', 'low pressure'),
    ('LOW_PRESSURE', 'pressure low'),
    ('LOW_PRESSURE', 'pressure drop'),
    ('HIGH_PRESSURE', 'high pressure'),
    ('HIGH_PRESSURE', 'pressure high'),
    ('NO_START', 'wont start'),
    ('NO_START', 'will not start'),
    ('NO_START', 'not starting'),
    ('NO_START', 'fails to start'),
    ('STALLING', 'stalling'),
    ('STALLING', 'cuts out'),
    ('STALLING', 'shuts down'),
    ('STALLING', 'stops running'),
    ('SMOKE', 'smoking'),
    ('SMOKE', 'black smoke'),
    ('SMOKE', 'white smoke'),
    ('SMOKE', 'blue smoke')
ON CONFLICT (symptom_code, alias_text_lower) DO NOTHING;

-- ============================================================================
-- DONE
-- ============================================================================

COMMENT ON TABLE equipment IS 'Canonical equipment entities for the yacht';
COMMENT ON TABLE parts IS 'Canonical parts/components for the yacht';
COMMENT ON TABLE faults IS 'Canonical fault codes and failure modes';
COMMENT ON TABLE symptom_catalog IS 'Global symptom catalog (shared across yachts)';
COMMENT ON TABLE entity_aliases IS 'Maps text variations to canonical entities';
COMMENT ON TABLE graph_nodes IS 'Extracted entity mentions from documents';
COMMENT ON TABLE graph_edges IS 'Relationships between entities';
COMMENT ON TABLE maintenance_templates IS 'Extracted maintenance requirements';
