-- ============================================================================
-- Migration: Initial Schema V2.0
-- Version: 20250101000001
-- Description: Create all 34 tables with proper auth integration and security
--
-- CRITICAL: This migration assumes:
-- - pgvector extension is enabled (run 20250101000000_enable_pgvector.sql first)
-- - Supabase Auth is configured (auth.users table exists)
-- - Using OpenAI Text-Embedding-3-Small (1536 dimensions)
-- ============================================================================

-- ============================================================================
-- GROUP 1: CORE / AUTH TABLES (9 tables)
-- ============================================================================

-- -----------------------------------------------------------------------------
-- yachts: Each superyacht in the system
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS yachts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  yacht_secret_hash text NOT NULL CHECK (yacht_secret_hash ~ '^\$2[aby]\$'),
  imo_number text UNIQUE,
  mmsi text,
  flag_state text,
  year_built integer,
  length_meters numeric,
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'archived')),
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_yachts_status ON yachts(status);
COMMENT ON TABLE yachts IS 'Superyachts registered in CelesteOS';
COMMENT ON COLUMN yachts.yacht_secret_hash IS 'bcrypt hash for agent authentication (HMAC)';

-- Enable RLS
ALTER TABLE yachts ENABLE ROW LEVEL SECURITY;

-- -----------------------------------------------------------------------------
-- users: Business users linked to Supabase Auth
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  auth_user_id uuid UNIQUE NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  email text UNIQUE NOT NULL,
  name text NOT NULL,
  role text NOT NULL CHECK (role IN ('chief_engineer', 'eto', 'captain', 'deck', 'interior', 'manager', 'vendor')),
  avatar_url text,
  phone text,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX idx_users_auth_user_id ON users(auth_user_id);
CREATE INDEX idx_users_yacht_id ON users(yacht_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
COMMENT ON TABLE users IS 'Business users (crew) linked to Supabase Auth';
COMMENT ON COLUMN users.auth_user_id IS 'Foreign key to auth.users(id) - Supabase Auth integration';

-- Enable RLS
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- -----------------------------------------------------------------------------
-- agents: Local Mac Studio/Mini devices for NAS ingestion
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  name text NOT NULL,
  agent_secret_hash text NOT NULL CHECK (agent_secret_hash ~ '^\$2[aby]\$'),
  device_info jsonb DEFAULT '{}'::jsonb,
  last_seen_at timestamptz,
  is_active boolean DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_agents_yacht_id ON agents(yacht_id);
CREATE INDEX idx_agents_is_active ON agents(is_active);
COMMENT ON TABLE agents IS 'Local Mac devices for NAS scanning and document upload';
COMMENT ON COLUMN agents.agent_secret_hash IS 'bcrypt hash for HMAC authentication';

-- Enable RLS
ALTER TABLE agents ENABLE ROW LEVEL SECURITY;

-- -----------------------------------------------------------------------------
-- api_keys: API keys for automation (n8n, workflows)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS api_keys (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  key_prefix text NOT NULL CHECK (key_prefix ~ '^sk_(live|test)_[a-z0-9]{4,8}$'),
  hashed_key text NOT NULL UNIQUE CHECK (hashed_key ~ '^\$2[aby]\$'),
  name text NOT NULL,
  scopes text[] DEFAULT '{}',
  created_by uuid REFERENCES users(id) ON DELETE SET NULL,
  expires_at timestamptz,
  last_used_at timestamptz,
  is_active boolean DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_api_keys_yacht_id ON api_keys(yacht_id);
CREATE UNIQUE INDEX idx_api_keys_hashed_key ON api_keys(hashed_key);
CREATE INDEX idx_api_keys_is_active ON api_keys(is_active);
COMMENT ON TABLE api_keys IS 'API keys for service authentication (n8n, automation)';
COMMENT ON COLUMN api_keys.hashed_key IS 'bcrypt hash of API key for validation';

-- Enable RLS
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;

-- -----------------------------------------------------------------------------
-- user_roles: Role definitions and permissions
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_roles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  role_name text UNIQUE NOT NULL,
  display_name text NOT NULL,
  description text,
  permissions jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX idx_user_roles_role_name ON user_roles(role_name);
COMMENT ON TABLE user_roles IS 'Role definitions (chief_engineer, eto, etc.)';

-- Enable RLS
ALTER TABLE user_roles ENABLE ROW LEVEL SECURITY;

-- -----------------------------------------------------------------------------
-- search_queries: Search history and analytics
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS search_queries (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  user_id uuid REFERENCES users(id) ON DELETE SET NULL,
  query_text text NOT NULL,
  filters jsonb DEFAULT '{}'::jsonb,
  result_count integer,
  clicked_document_id uuid,
  execution_time_ms integer,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_search_queries_yacht_id ON search_queries(yacht_id);
CREATE INDEX idx_search_queries_user_id ON search_queries(user_id);
CREATE INDEX idx_search_queries_created_at ON search_queries(created_at);
COMMENT ON TABLE search_queries IS 'Search history for analytics and improvements';

-- Enable RLS
ALTER TABLE search_queries ENABLE ROW LEVEL SECURITY;

-- -----------------------------------------------------------------------------
-- event_logs: Audit trail for all operations
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS event_logs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  user_id uuid REFERENCES users(id) ON DELETE SET NULL,
  event_type text NOT NULL,
  table_name text,
  record_id uuid,
  action text NOT NULL CHECK (action IN ('INSERT', 'UPDATE', 'DELETE', 'SELECT')),
  old_data jsonb,
  new_data jsonb,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_event_logs_yacht_id ON event_logs(yacht_id);
CREATE INDEX idx_event_logs_user_id ON event_logs(user_id);
CREATE INDEX idx_event_logs_event_type ON event_logs(event_type);
CREATE INDEX idx_event_logs_created_at ON event_logs(created_at);
COMMENT ON TABLE event_logs IS 'Comprehensive audit trail for compliance and debugging';

-- Enable RLS
ALTER TABLE event_logs ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- GROUP 2: PMS TABLES (5 tables)
-- ============================================================================

-- -----------------------------------------------------------------------------
-- equipment: All yacht equipment/machinery
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS equipment (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  name text NOT NULL,
  equipment_type text NOT NULL,
  manufacturer text,
  model text,
  serial_number text,
  installation_date date,
  location text,
  parent_equipment_id uuid REFERENCES equipment(id) ON DELETE SET NULL,
  maintenance_interval_hours integer,
  current_hours numeric DEFAULT 0,
  last_maintenance_at timestamptz,
  next_maintenance_due timestamptz,
  status text DEFAULT 'operational' CHECK (status IN ('operational', 'maintenance', 'fault', 'decommissioned')),
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_equipment_yacht_id ON equipment(yacht_id);
CREATE INDEX idx_equipment_type ON equipment(equipment_type);
CREATE INDEX idx_equipment_status ON equipment(status);
CREATE INDEX idx_equipment_parent ON equipment(parent_equipment_id);
CREATE INDEX idx_equipment_next_maintenance ON equipment(next_maintenance_due);
COMMENT ON TABLE equipment IS 'All yacht equipment and machinery';

-- Enable RLS
ALTER TABLE equipment ENABLE ROW LEVEL SECURITY;

-- -----------------------------------------------------------------------------
-- work_orders: Maintenance and repair tasks
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS work_orders (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  equipment_id uuid REFERENCES equipment(id) ON DELETE SET NULL,
  title text NOT NULL,
  description text,
  work_type text NOT NULL CHECK (work_type IN ('preventive', 'corrective', 'inspection', 'upgrade', 'emergency')),
  priority text NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'critical')),
  status text NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'in_progress', 'completed', 'cancelled')),
  assigned_to uuid REFERENCES users(id) ON DELETE SET NULL,
  created_by uuid REFERENCES users(id) ON DELETE SET NULL,
  scheduled_start timestamptz,
  scheduled_end timestamptz,
  actual_start timestamptz,
  actual_end timestamptz,
  estimated_hours numeric,
  actual_hours numeric,
  parts_required jsonb DEFAULT '[]'::jsonb,
  tags text[] DEFAULT '{}',
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_work_orders_yacht_id ON work_orders(yacht_id);
CREATE INDEX idx_work_orders_equipment_id ON work_orders(equipment_id);
CREATE INDEX idx_work_orders_status ON work_orders(status);
CREATE INDEX idx_work_orders_assigned_to ON work_orders(assigned_to);
CREATE INDEX idx_work_orders_priority ON work_orders(priority);
CREATE INDEX idx_work_orders_created_at ON work_orders(created_at);
COMMENT ON TABLE work_orders IS 'Maintenance and repair work orders';

-- Enable RLS
ALTER TABLE work_orders ENABLE ROW LEVEL SECURITY;

-- -----------------------------------------------------------------------------
-- work_order_history: Audit trail for work order changes
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS work_order_history (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  work_order_id uuid NOT NULL REFERENCES work_orders(id) ON DELETE CASCADE,
  changed_by uuid REFERENCES users(id) ON DELETE SET NULL,
  field_changed text,
  old_value text,
  new_value text,
  notes text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_work_order_history_yacht_id ON work_order_history(yacht_id);
CREATE INDEX idx_work_order_history_work_order_id ON work_order_history(work_order_id);
CREATE INDEX idx_work_order_history_created_at ON work_order_history(created_at);
COMMENT ON TABLE work_order_history IS 'Change history for work orders';

-- Enable RLS
ALTER TABLE work_order_history ENABLE ROW LEVEL SECURITY;

-- -----------------------------------------------------------------------------
-- faults: Equipment faults and failures
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS faults (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  equipment_id uuid REFERENCES equipment(id) ON DELETE SET NULL,
  title text NOT NULL,
  description text,
  severity text NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
  status text NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'acknowledged', 'resolved', 'false_alarm')),
  detected_at timestamptz NOT NULL DEFAULT now(),
  detected_by uuid REFERENCES users(id) ON DELETE SET NULL,
  acknowledged_at timestamptz,
  acknowledged_by uuid REFERENCES users(id) ON DELETE SET NULL,
  resolved_at timestamptz,
  resolved_by uuid REFERENCES users(id) ON DELETE SET NULL,
  work_order_id uuid REFERENCES work_orders(id) ON DELETE SET NULL,
  root_cause text,
  resolution_notes text,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_faults_yacht_id ON faults(yacht_id);
CREATE INDEX idx_faults_equipment_id ON faults(equipment_id);
CREATE INDEX idx_faults_status ON faults(status);
CREATE INDEX idx_faults_severity ON faults(severity);
CREATE INDEX idx_faults_detected_at ON faults(detected_at);
COMMENT ON TABLE faults IS 'Equipment faults and failures';

-- Enable RLS
ALTER TABLE faults ENABLE ROW LEVEL SECURITY;

-- -----------------------------------------------------------------------------
-- hours_of_rest: Crew hours tracking for MLC compliance
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS hours_of_rest (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  date date NOT NULL,
  rest_period_start timestamptz NOT NULL,
  rest_period_end timestamptz NOT NULL,
  hours_rested numeric NOT NULL,
  is_compliant boolean DEFAULT true,
  notes text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(user_id, date, rest_period_start)
);

CREATE INDEX idx_hours_of_rest_yacht_id ON hours_of_rest(yacht_id);
CREATE INDEX idx_hours_of_rest_user_id ON hours_of_rest(user_id);
CREATE INDEX idx_hours_of_rest_date ON hours_of_rest(date);
COMMENT ON TABLE hours_of_rest IS 'Crew rest hours for MLC 2006 compliance';

-- Enable RLS
ALTER TABLE hours_of_rest ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- GROUP 3: INVENTORY TABLES (7 tables)
-- ============================================================================

-- -----------------------------------------------------------------------------
-- parts: Spare parts catalog
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS parts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  part_number text NOT NULL,
  name text NOT NULL,
  description text,
  manufacturer text,
  supplier_part_number text,
  unit_of_measure text DEFAULT 'EA',
  unit_cost numeric,
  reorder_level integer DEFAULT 1,
  reorder_quantity integer DEFAULT 1,
  category text,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(yacht_id, part_number)
);

CREATE INDEX idx_parts_yacht_id ON parts(yacht_id);
CREATE INDEX idx_parts_part_number ON parts(part_number);
CREATE INDEX idx_parts_category ON parts(category);
COMMENT ON TABLE parts IS 'Spare parts catalog';

-- Enable RLS
ALTER TABLE parts ENABLE ROW LEVEL SECURITY;

-- -----------------------------------------------------------------------------
-- equipment_parts: Link equipment to required parts
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS equipment_parts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  equipment_id uuid NOT NULL REFERENCES equipment(id) ON DELETE CASCADE,
  part_id uuid NOT NULL REFERENCES parts(id) ON DELETE CASCADE,
  quantity_required integer DEFAULT 1,
  is_critical boolean DEFAULT false,
  notes text,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(equipment_id, part_id)
);

CREATE INDEX idx_equipment_parts_yacht_id ON equipment_parts(yacht_id);
CREATE INDEX idx_equipment_parts_equipment_id ON equipment_parts(equipment_id);
CREATE INDEX idx_equipment_parts_part_id ON equipment_parts(part_id);
COMMENT ON TABLE equipment_parts IS 'Equipment to parts mapping';

-- Enable RLS
ALTER TABLE equipment_parts ENABLE ROW LEVEL SECURITY;

-- -----------------------------------------------------------------------------
-- inventory_stock: Current stock levels
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS inventory_stock (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  part_id uuid NOT NULL REFERENCES parts(id) ON DELETE CASCADE,
  location text NOT NULL,
  quantity_on_hand integer NOT NULL DEFAULT 0,
  quantity_reserved integer DEFAULT 0,
  last_counted_at timestamptz,
  last_counted_by uuid REFERENCES users(id) ON DELETE SET NULL,
  notes text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(part_id, location)
);

CREATE INDEX idx_inventory_stock_yacht_id ON inventory_stock(yacht_id);
CREATE INDEX idx_inventory_stock_part_id ON inventory_stock(part_id);
CREATE INDEX idx_inventory_stock_location ON inventory_stock(location);
COMMENT ON TABLE inventory_stock IS 'Current inventory stock levels by location';

-- Enable RLS
ALTER TABLE inventory_stock ENABLE ROW LEVEL SECURITY;

-- -----------------------------------------------------------------------------
-- suppliers: Supplier/vendor information
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS suppliers (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  name text NOT NULL,
  contact_name text,
  email text,
  phone text,
  address text,
  website text,
  notes text,
  is_active boolean DEFAULT true,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_suppliers_yacht_id ON suppliers(yacht_id);
CREATE INDEX idx_suppliers_is_active ON suppliers(is_active);
COMMENT ON TABLE suppliers IS 'Supplier and vendor information';

-- Enable RLS
ALTER TABLE suppliers ENABLE ROW LEVEL SECURITY;

-- -----------------------------------------------------------------------------
-- purchase_orders: Purchase orders for parts
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS purchase_orders (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  po_number text NOT NULL,
  supplier_id uuid REFERENCES suppliers(id) ON DELETE SET NULL,
  status text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'submitted', 'approved', 'received', 'cancelled')),
  order_date date NOT NULL DEFAULT CURRENT_DATE,
  expected_delivery_date date,
  actual_delivery_date date,
  total_amount numeric,
  currency text DEFAULT 'USD',
  created_by uuid REFERENCES users(id) ON DELETE SET NULL,
  approved_by uuid REFERENCES users(id) ON DELETE SET NULL,
  notes text,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(yacht_id, po_number)
);

CREATE INDEX idx_purchase_orders_yacht_id ON purchase_orders(yacht_id);
CREATE INDEX idx_purchase_orders_supplier_id ON purchase_orders(supplier_id);
CREATE INDEX idx_purchase_orders_status ON purchase_orders(status);
CREATE INDEX idx_purchase_orders_order_date ON purchase_orders(order_date);
COMMENT ON TABLE purchase_orders IS 'Purchase orders for parts and supplies';

-- Enable RLS
ALTER TABLE purchase_orders ENABLE ROW LEVEL SECURITY;

-- -----------------------------------------------------------------------------
-- purchase_order_items: Line items for purchase orders
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS purchase_order_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  purchase_order_id uuid NOT NULL REFERENCES purchase_orders(id) ON DELETE CASCADE,
  part_id uuid REFERENCES parts(id) ON DELETE SET NULL,
  description text NOT NULL,
  quantity integer NOT NULL,
  unit_price numeric NOT NULL,
  total_price numeric NOT NULL,
  received_quantity integer DEFAULT 0,
  notes text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_purchase_order_items_yacht_id ON purchase_order_items(yacht_id);
CREATE INDEX idx_purchase_order_items_po_id ON purchase_order_items(purchase_order_id);
CREATE INDEX idx_purchase_order_items_part_id ON purchase_order_items(part_id);
COMMENT ON TABLE purchase_order_items IS 'Purchase order line items';

-- Enable RLS
ALTER TABLE purchase_order_items ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- GROUP 4: HANDOVER TABLES (2 tables)
-- ============================================================================

-- -----------------------------------------------------------------------------
-- handovers: Shift handover reports
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS handovers (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  handover_date date NOT NULL DEFAULT CURRENT_DATE,
  shift text NOT NULL CHECK (shift IN ('day', 'night', 'morning', 'evening')),
  created_by uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  acknowledged_by uuid REFERENCES users(id) ON DELETE SET NULL,
  acknowledged_at timestamptz,
  summary text,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_handovers_yacht_id ON handovers(yacht_id);
CREATE INDEX idx_handovers_handover_date ON handovers(handover_date);
CREATE INDEX idx_handovers_created_by ON handovers(created_by);
COMMENT ON TABLE handovers IS 'Shift handover reports';

-- Enable RLS
ALTER TABLE handovers ENABLE ROW LEVEL SECURITY;

-- -----------------------------------------------------------------------------
-- handover_items: Individual items in handover reports
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS handover_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  handover_id uuid NOT NULL REFERENCES handovers(id) ON DELETE CASCADE,
  item_type text NOT NULL CHECK (item_type IN ('equipment_status', 'fault', 'work_completed', 'upcoming_work', 'note')),
  equipment_id uuid REFERENCES equipment(id) ON DELETE SET NULL,
  fault_id uuid REFERENCES faults(id) ON DELETE SET NULL,
  work_order_id uuid REFERENCES work_orders(id) ON DELETE SET NULL,
  description text NOT NULL,
  priority text CHECK (priority IN ('low', 'medium', 'high', 'critical')),
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_handover_items_yacht_id ON handover_items(yacht_id);
CREATE INDEX idx_handover_items_handover_id ON handover_items(handover_id);
CREATE INDEX idx_handover_items_item_type ON handover_items(item_type);
COMMENT ON TABLE handover_items IS 'Individual items in handover reports';

-- Enable RLS
ALTER TABLE handover_items ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- GROUP 5: DOCUMENTS + RAG TABLES (4 tables)
-- ============================================================================

-- -----------------------------------------------------------------------------
-- documents: Document metadata
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS documents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  sha256 char(64) NOT NULL CHECK (sha256 ~ '^[a-f0-9]{64}$'),
  filename text NOT NULL,
  file_path text NOT NULL,
  file_size_bytes bigint,
  mime_type text,
  source_type text NOT NULL CHECK (source_type IN ('nas', 'email', 'manual_upload', 'api')),
  category text,
  tags text[] DEFAULT '{}',
  indexed boolean DEFAULT false,
  indexed_at timestamptz,
  page_count integer,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(yacht_id, sha256)
);

CREATE INDEX idx_documents_yacht_id ON documents(yacht_id);
CREATE INDEX idx_documents_sha256 ON documents(sha256);
CREATE INDEX idx_documents_indexed ON documents(indexed);
CREATE INDEX idx_documents_source_type ON documents(source_type);
CREATE INDEX idx_documents_category ON documents(category);
CREATE INDEX idx_documents_tags ON documents USING GIN(tags);
COMMENT ON TABLE documents IS 'Document metadata and file references';
COMMENT ON COLUMN documents.sha256 IS 'SHA256 hash for deduplication and integrity (NOT authentication)';

-- Enable RLS
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- -----------------------------------------------------------------------------
-- document_chunks: Text chunks with embeddings for RAG
-- CRITICAL: Using 1536 dimensions for OpenAI Text-Embedding-3-Small
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS document_chunks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  chunk_index integer NOT NULL,
  text text NOT NULL,
  embedding vector(1536),
  page_number integer,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(document_id, chunk_index)
);

CREATE INDEX idx_document_chunks_yacht_id ON document_chunks(yacht_id);
CREATE INDEX idx_document_chunks_document_id ON document_chunks(document_id);

-- pgvector index for semantic search (cosine similarity)
-- CRITICAL: This index is essential for fast vector search
CREATE INDEX idx_document_chunks_embedding ON document_chunks
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

COMMENT ON TABLE document_chunks IS 'Document text chunks with embeddings for semantic search';
COMMENT ON COLUMN document_chunks.embedding IS 'OpenAI Text-Embedding-3-Small (1536 dimensions)';

-- Enable RLS
ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;

-- -----------------------------------------------------------------------------
-- ocred_pages: OCR results for document pages
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ocred_pages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  page_number integer NOT NULL,
  ocr_text text,
  ocr_confidence numeric,
  ocr_engine text,
  processed_at timestamptz NOT NULL DEFAULT now(),
  metadata jsonb DEFAULT '{}'::jsonb,
  UNIQUE(document_id, page_number)
);

CREATE INDEX idx_ocred_pages_yacht_id ON ocred_pages(yacht_id);
CREATE INDEX idx_ocred_pages_document_id ON ocred_pages(document_id);
COMMENT ON TABLE ocred_pages IS 'OCR text extraction results per page';

-- Enable RLS
ALTER TABLE ocred_pages ENABLE ROW LEVEL SECURITY;

-- -----------------------------------------------------------------------------
-- embedding_jobs: Track document indexing progress
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS embedding_jobs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
  chunks_total integer,
  chunks_processed integer DEFAULT 0,
  error_message text,
  started_at timestamptz,
  completed_at timestamptz,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_embedding_jobs_yacht_id ON embedding_jobs(yacht_id);
CREATE INDEX idx_embedding_jobs_document_id ON embedding_jobs(document_id);
CREATE INDEX idx_embedding_jobs_status ON embedding_jobs(status);
COMMENT ON TABLE embedding_jobs IS 'Document indexing job tracker';

-- Enable RLS
ALTER TABLE embedding_jobs ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- GROUP 6: GRAPHRAG TABLES (2 tables)
-- ============================================================================

-- -----------------------------------------------------------------------------
-- graph_nodes: Knowledge graph entities
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS graph_nodes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  entity_type text NOT NULL,
  entity_name text NOT NULL,
  description text,
  source_document_ids uuid[] DEFAULT '{}',
  properties jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(yacht_id, entity_type, entity_name)
);

CREATE INDEX idx_graph_nodes_yacht_id ON graph_nodes(yacht_id);
CREATE INDEX idx_graph_nodes_entity_type ON graph_nodes(entity_type);
CREATE INDEX idx_graph_nodes_entity_name ON graph_nodes(entity_name);
COMMENT ON TABLE graph_nodes IS 'Knowledge graph entities (equipment, parts, procedures)';

-- Enable RLS
ALTER TABLE graph_nodes ENABLE ROW LEVEL SECURITY;

-- -----------------------------------------------------------------------------
-- graph_edges: Knowledge graph relationships
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS graph_edges (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  from_node_id uuid NOT NULL REFERENCES graph_nodes(id) ON DELETE CASCADE,
  to_node_id uuid NOT NULL REFERENCES graph_nodes(id) ON DELETE CASCADE,
  relationship_type text NOT NULL,
  weight numeric DEFAULT 1.0,
  properties jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(from_node_id, to_node_id, relationship_type)
);

CREATE INDEX idx_graph_edges_yacht_id ON graph_edges(yacht_id);
CREATE INDEX idx_graph_edges_from_node ON graph_edges(from_node_id);
CREATE INDEX idx_graph_edges_to_node ON graph_edges(to_node_id);
CREATE INDEX idx_graph_edges_relationship_type ON graph_edges(relationship_type);
COMMENT ON TABLE graph_edges IS 'Knowledge graph relationships between entities';

-- Enable RLS
ALTER TABLE graph_edges ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- GROUP 7: PREDICTIVE MAINTENANCE TABLES (2 tables)
-- ============================================================================

-- -----------------------------------------------------------------------------
-- predictive_state: Equipment health predictions
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS predictive_state (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  equipment_id uuid NOT NULL REFERENCES equipment(id) ON DELETE CASCADE,
  risk_score numeric CHECK (risk_score >= 0 AND risk_score <= 1),
  predicted_failure_date date,
  confidence numeric CHECK (confidence >= 0 AND confidence <= 1),
  contributing_factors jsonb DEFAULT '{}'::jsonb,
  last_calculated_at timestamptz NOT NULL DEFAULT now(),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(equipment_id)
);

CREATE INDEX idx_predictive_state_yacht_id ON predictive_state(yacht_id);
CREATE INDEX idx_predictive_state_equipment_id ON predictive_state(equipment_id);
CREATE INDEX idx_predictive_state_risk_score ON predictive_state(risk_score);
COMMENT ON TABLE predictive_state IS 'Equipment health risk scores and predictions';

-- Enable RLS
ALTER TABLE predictive_state ENABLE ROW LEVEL SECURITY;

-- -----------------------------------------------------------------------------
-- predictive_insights: Predictive maintenance recommendations
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS predictive_insights (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  equipment_id uuid REFERENCES equipment(id) ON DELETE CASCADE,
  insight_type text NOT NULL CHECK (insight_type IN ('anomaly', 'trend', 'recommendation', 'alert')),
  severity text NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
  title text NOT NULL,
  description text,
  recommended_action text,
  acknowledged_at timestamptz,
  acknowledged_by uuid REFERENCES users(id) ON DELETE SET NULL,
  dismissed_at timestamptz,
  dismissed_by uuid REFERENCES users(id) ON DELETE SET NULL,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_predictive_insights_yacht_id ON predictive_insights(yacht_id);
CREATE INDEX idx_predictive_insights_equipment_id ON predictive_insights(equipment_id);
CREATE INDEX idx_predictive_insights_insight_type ON predictive_insights(insight_type);
CREATE INDEX idx_predictive_insights_severity ON predictive_insights(severity);
CREATE INDEX idx_predictive_insights_acknowledged_at ON predictive_insights(acknowledged_at);
COMMENT ON TABLE predictive_insights IS 'AI-generated maintenance insights and recommendations';

-- Enable RLS
ALTER TABLE predictive_insights ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- SCHEMA VERIFICATION
-- ============================================================================
-- Run this query to verify all tables were created:
-- SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;
-- Expected: 34 tables
