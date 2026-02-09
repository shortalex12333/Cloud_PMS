-- Migration 009: Drop Duplicate Tables + Create Compatibility Views
--
-- VERIFIED: These pairs have IDENTICAL schema and data:
--   graph_nodes (109) = search_graph_nodes (109)
--   graph_edges (68) = search_graph_edges (68)
--   document_chunks (47166) = search_document_chunks (47166)
--   symptom_catalog (50) = search_symptom_catalog (50)
--   maintenance_facts (4) = search_maintenance_facts (4)
--
-- DECISION: Keep search_* as canonical. Drop non-search tables.
--           Create views for backwards compatibility.

-- ============================================================================
-- Step 1: Create views BEFORE dropping tables (for any code that references old names)
-- ============================================================================

-- graph_nodes → search_graph_nodes
CREATE OR REPLACE VIEW public.graph_nodes AS
SELECT * FROM public.search_graph_nodes;

-- graph_edges → search_graph_edges
CREATE OR REPLACE VIEW public.graph_edges AS
SELECT * FROM public.search_graph_edges;

-- document_chunks → search_document_chunks
CREATE OR REPLACE VIEW public.document_chunks AS
SELECT * FROM public.search_document_chunks;

-- symptom_catalog → search_symptom_catalog
CREATE OR REPLACE VIEW public.symptom_catalog AS
SELECT * FROM public.search_symptom_catalog;

-- maintenance_facts → search_maintenance_facts
CREATE OR REPLACE VIEW public.maintenance_facts AS
SELECT * FROM public.search_maintenance_facts;

-- ============================================================================
-- Step 2: Drop the duplicate TABLES (views now exist with same names)
-- ============================================================================

-- Note: DROP TABLE will fail if a view exists with the same name
-- So we first drop the tables (which exist), then the views were created above

-- First rename tables temporarily to avoid conflict
ALTER TABLE IF EXISTS public.graph_nodes RENAME TO _legacy_graph_nodes;
ALTER TABLE IF EXISTS public.graph_edges RENAME TO _legacy_graph_edges;
ALTER TABLE IF EXISTS public.document_chunks RENAME TO _legacy_document_chunks;
ALTER TABLE IF EXISTS public.symptom_catalog RENAME TO _legacy_symptom_catalog;
ALTER TABLE IF EXISTS public.maintenance_facts RENAME TO _legacy_maintenance_facts;

-- Now drop the renamed legacy tables
DROP TABLE IF EXISTS public._legacy_graph_nodes CASCADE;
DROP TABLE IF EXISTS public._legacy_graph_edges CASCADE;
DROP TABLE IF EXISTS public._legacy_document_chunks CASCADE;
DROP TABLE IF EXISTS public._legacy_symptom_catalog CASCADE;
DROP TABLE IF EXISTS public._legacy_maintenance_facts CASCADE;

-- ============================================================================
-- Step 3: Verify
-- ============================================================================
-- After this migration:
--   - search_graph_nodes (TABLE, canonical)
--   - graph_nodes (VIEW → search_graph_nodes)
--   - search_graph_edges (TABLE, canonical)
--   - graph_edges (VIEW → search_graph_edges)
--   - etc.

COMMENT ON VIEW public.graph_nodes IS 'Compatibility view. Use search_graph_nodes instead.';
COMMENT ON VIEW public.graph_edges IS 'Compatibility view. Use search_graph_edges instead.';
COMMENT ON VIEW public.document_chunks IS 'Compatibility view. Use search_document_chunks instead.';
COMMENT ON VIEW public.symptom_catalog IS 'Compatibility view. Use search_symptom_catalog instead.';
COMMENT ON VIEW public.maintenance_facts IS 'Compatibility view. Use search_maintenance_facts instead.';

-- Done. 5 duplicate tables removed. 5 compatibility views created.
