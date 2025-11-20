-- ============================================================================
-- CelesteOS Supabase Schema - MVP Foundation (CORRECTED)
-- Version: 2.0 - Auth Integration Fixed
-- DO NOT MODIFY WITHOUT APPROVAL
-- ============================================================================
--
-- Auth Architecture:
-- 1. Humans → Supabase Auth (auth.users) → users.auth_user_id → yacht_id
-- 2. Agents → agent_secret (bcrypt) → agents.yacht_id
-- 3. Services → API keys (bcrypt) → api_keys.yacht_id
--
-- See AUTH_INTEGRATION.md for complete documentation
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";  -- For bcrypt

-- ============================================================================
-- ENUMS
-- ============================================================================

-- Work order priority levels
CREATE TYPE work_order_priority AS ENUM (
  'routine',
  'important',
  'critical',
  'emergency'
);

-- Work order status
CREATE TYPE work_order_status AS ENUM (
  'planned',
  'in_progress',
  'completed',
  'deferred',
  'cancelled'
);

-- Work order type
CREATE TYPE work_order_type AS ENUM (
  'scheduled',
  'corrective',
  'unplanned',
  'preventive'
);

-- Fault severity
CREATE TYPE fault_severity AS ENUM (
  'low',
  'medium',
  'high',
  'critical'
);

-- Handover item source type (polymorphic)
CREATE TYPE handover_source_type AS ENUM (
  'fault',
  'work_order',
  'history',
  'document',
  'predictive',
  'note'
);

-- Graph node types
CREATE TYPE graph_node_type AS ENUM (
  'equipment',
  'part',
  'fault',
  'document_chunk',
  'work_order',
  'handover_item',
  'supplier'
);

-- Graph edge types
CREATE TYPE graph_edge_type AS ENUM (
  'USES_PART',
  'HAS_FAULT',
  'MENTIONED_IN',
  'REFERS_TO',
  'PARENT_OF',
  'CHILD_OF',
  'COMPATIBLE_WITH',
  'RELATED_TO',
  'USED_IN_WO',
  'DOCUMENTED_BY'
);

-- Equipment criticality
CREATE TYPE equipment_criticality AS ENUM (
  'low',
  'medium',
  'high',
  'critical'
);

-- ============================================================================
-- GROUP 1: CORE / AUTH / MULTI-YACHT ISOLATION
-- ============================================================================

-- Yachts table - each vessel using CelesteOS
CREATE TABLE yachts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  imo text,
  mmsi text,
  flag_state text,
  length_m numeric(10,2),
  owner_ref text,
  yacht_secret_hash text NOT NULL CHECK (yacht_secret_hash ~ '^\$2[aby]\$'),
  nas_root_path text,
  status text DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'demo')),
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE yachts IS 'Each yacht (vessel) using CelesteOS - tenant isolation root';
COMMENT ON COLUMN yachts.yacht_secret_hash IS 'bcrypt hash of master yacht secret - for deriving agent keys';

CREATE INDEX idx_yachts_status ON yachts(status);
ALTER TABLE yachts ENABLE ROW LEVEL SECURITY;

-- Users table - crew, managers, vendors
-- Links to Supabase auth.users via auth_user_id
CREATE TABLE users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  auth_user_id uuid UNIQUE NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  email text UNIQUE NOT NULL,
  name text NOT NULL,
  role text NOT NULL CHECK (role IN ('chief_engineer', 'eto', 'captain', 'deck', 'interior', 'manager', 'vendor')),
  is_active boolean DEFAULT true,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE users IS 'Business user records linked to Supabase Auth';
COMMENT ON COLUMN users.auth_user_id IS 'Links to auth.users(id) - enables JWT validation via JWT.sub';
COMMENT ON COLUMN users.role IS 'User role - determines permissions and access levels';

CREATE INDEX idx_users_yacht_id ON users(yacht_id);
CREATE INDEX idx_users_auth_user_id ON users(auth_user_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Agents table - local agent devices (Mac Studio/Mini)
CREATE TABLE agents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  name text NOT NULL,
  agent_secret_hash text NOT NULL CHECK (agent_secret_hash ~ '^\$2[aby]\$'),
  device_info jsonb DEFAULT '{}'::jsonb,
  last_seen_at timestamptz,
  is_active boolean DEFAULT true,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE agents IS 'Local agent devices (Mac Studio/Mini) for NAS ingestion';
COMMENT ON COLUMN agents.agent_secret_hash IS 'bcrypt hash of agent secret - used for HMAC verification';
COMMENT ON COLUMN agents.device_info IS 'Device metadata: OS, version, IP, hardware specs';

CREATE INDEX idx_agents_yacht_id ON agents(yacht_id);
CREATE INDEX idx_agents_is_active ON agents(is_active);
ALTER TABLE agents ENABLE ROW LEVEL SECURITY;

-- API keys table - for automation and external integrations
CREATE TABLE api_keys (
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
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE api_keys IS 'API keys for automation (n8n) and external integrations';
COMMENT ON COLUMN api_keys.hashed_key IS 'bcrypt hash of full API key';
COMMENT ON COLUMN api_keys.key_prefix IS 'First 8-12 chars for identification (e.g., sk_live_a1b2c3d4)';
COMMENT ON COLUMN api_keys.scopes IS 'Granted permissions (e.g., read:equipment, write:work_orders)';

CREATE INDEX idx_api_keys_yacht_id ON api_keys(yacht_id);
CREATE INDEX idx_api_keys_hashed_key ON api_keys(hashed_key);
CREATE INDEX idx_api_keys_is_active ON api_keys(is_active);
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;

-- User roles - for more granular RBAC if needed
CREATE TABLE user_roles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text UNIQUE NOT NULL,
  description text,
  permissions jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE user_roles IS 'Role definitions for RBAC';
ALTER TABLE user_roles ENABLE ROW LEVEL SECURITY;

-- Search queries - for analytics and crew pain index
CREATE TABLE search_queries (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  user_id uuid REFERENCES users(id) ON DELETE SET NULL,
  query_text text NOT NULL,
  interpreted_intent text,
  entities jsonb DEFAULT '{}'::jsonb,
  latency_ms integer,
  success boolean,
  created_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE search_queries IS 'User search history for analytics and crew pain index';
COMMENT ON COLUMN search_queries.entities IS 'Extracted entities from query (equipment, fault codes, etc)';

CREATE INDEX idx_search_queries_yacht_id ON search_queries(yacht_id);
CREATE INDEX idx_search_queries_user_id ON search_queries(user_id);
CREATE INDEX idx_search_queries_created_at ON search_queries(created_at);
CREATE INDEX idx_search_queries_intent ON search_queries(interpreted_intent);
ALTER TABLE search_queries ENABLE ROW LEVEL SECURITY;

-- Event logs - audit trail
CREATE TABLE event_logs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  user_id uuid REFERENCES users(id) ON DELETE SET NULL,
  event_type text NOT NULL,
  entity_type text,
  entity_id uuid,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE event_logs IS 'System-wide audit log for all actions';

CREATE INDEX idx_event_logs_yacht_id ON event_logs(yacht_id);
CREATE INDEX idx_event_logs_user_id ON event_logs(user_id);
CREATE INDEX idx_event_logs_event_type ON event_logs(event_type);
CREATE INDEX idx_event_logs_created_at ON event_logs(created_at);
ALTER TABLE event_logs ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- GROUP 2: PMS (PLANNED MAINTENANCE SYSTEM)
-- ============================================================================

-- Equipment - all systems, subsystems, components
CREATE TABLE equipment (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  parent_id uuid REFERENCES equipment(id) ON DELETE SET NULL,
  name text NOT NULL,
  code text,
  description text,
  location text,
  manufacturer text,
  model text,
  serial_number text,
  installed_date date,
  criticality equipment_criticality DEFAULT 'medium',
  system_type text,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE equipment IS 'Master list of all vessel equipment, systems, and components';
COMMENT ON COLUMN equipment.parent_id IS 'Parent equipment for hierarchical structure';
COMMENT ON COLUMN equipment.criticality IS 'Operational criticality level';

CREATE INDEX idx_equipment_yacht_id ON equipment(yacht_id);
CREATE INDEX idx_equipment_parent_id ON equipment(parent_id);
CREATE INDEX idx_equipment_code ON equipment(code);
CREATE INDEX idx_equipment_system_type ON equipment(system_type);
CREATE INDEX idx_equipment_criticality ON equipment(criticality);
ALTER TABLE equipment ENABLE ROW LEVEL SECURITY;

-- Work orders - scheduled and corrective maintenance
CREATE TABLE work_orders (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  equipment_id uuid REFERENCES equipment(id) ON DELETE SET NULL,
  title text NOT NULL,
  description text,
  type work_order_type NOT NULL DEFAULT 'scheduled',
  priority work_order_priority NOT NULL DEFAULT 'routine',
  status work_order_status NOT NULL DEFAULT 'planned',
  due_date date,
  due_hours integer,
  last_completed_date date,
  last_completed_hours integer,
  frequency jsonb,
  created_by uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  updated_by uuid REFERENCES users(id) ON DELETE SET NULL,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE work_orders IS 'Planned and corrective maintenance work orders';
COMMENT ON COLUMN work_orders.frequency IS 'Recurring schedule definition';
COMMENT ON COLUMN work_orders.due_hours IS 'Equipment running hours when maintenance is due';

CREATE INDEX idx_work_orders_yacht_id ON work_orders(yacht_id);
CREATE INDEX idx_work_orders_equipment_id ON work_orders(equipment_id);
CREATE INDEX idx_work_orders_status ON work_orders(status);
CREATE INDEX idx_work_orders_priority ON work_orders(priority);
CREATE INDEX idx_work_orders_due_date ON work_orders(due_date);
ALTER TABLE work_orders ENABLE ROW LEVEL SECURITY;

-- Work order history - execution logs, notes, timeline (COMBINED)
CREATE TABLE work_order_history (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  work_order_id uuid NOT NULL REFERENCES work_orders(id) ON DELETE CASCADE,
  equipment_id uuid REFERENCES equipment(id) ON DELETE SET NULL,
  completed_by uuid REFERENCES users(id) ON DELETE SET NULL,
  completed_at timestamptz,
  notes text,
  hours_logged integer,
  status_on_completion text,
  parts_used jsonb DEFAULT '[]'::jsonb,
  documents_used jsonb DEFAULT '[]'::jsonb,
  faults_related jsonb DEFAULT '[]'::jsonb,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE work_order_history IS 'Work order execution history - includes notes, parts used, timeline';
COMMENT ON COLUMN work_order_history.notes IS 'Free-form technician notes - indexed for RAG search';
COMMENT ON COLUMN work_order_history.parts_used IS 'Array of parts consumed during work order';

CREATE INDEX idx_work_order_history_yacht_id ON work_order_history(yacht_id);
CREATE INDEX idx_work_order_history_work_order_id ON work_order_history(work_order_id);
CREATE INDEX idx_work_order_history_equipment_id ON work_order_history(equipment_id);
CREATE INDEX idx_work_order_history_completed_at ON work_order_history(completed_at);
ALTER TABLE work_order_history ENABLE ROW LEVEL SECURITY;

-- Faults - fault events and codes
CREATE TABLE faults (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  equipment_id uuid NOT NULL REFERENCES equipment(id) ON DELETE CASCADE,
  fault_code text,
  title text NOT NULL,
  description text,
  severity fault_severity NOT NULL DEFAULT 'medium',
  detected_at timestamptz NOT NULL DEFAULT now(),
  resolved_at timestamptz,
  resolved_by uuid REFERENCES users(id) ON DELETE SET NULL,
  work_order_id uuid REFERENCES work_orders(id) ON DELETE SET NULL,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE faults IS 'Equipment fault events and diagnostic codes';
COMMENT ON COLUMN faults.fault_code IS 'OEM fault code (e.g., E047, SPN 123)';

CREATE INDEX idx_faults_yacht_id ON faults(yacht_id);
CREATE INDEX idx_faults_equipment_id ON faults(equipment_id);
CREATE INDEX idx_faults_fault_code ON faults(fault_code);
CREATE INDEX idx_faults_severity ON faults(severity);
CREATE INDEX idx_faults_detected_at ON faults(detected_at);
CREATE INDEX idx_faults_work_order_id ON faults(work_order_id);
ALTER TABLE faults ENABLE ROW LEVEL SECURITY;

-- Hours of rest - compliance tracking
CREATE TABLE hours_of_rest (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  date date NOT NULL,
  hours_worked numeric(5,2) NOT NULL,
  hours_of_rest numeric(5,2) NOT NULL,
  violations boolean DEFAULT false,
  notes text,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE hours_of_rest IS 'MLC hours of rest compliance records';

CREATE INDEX idx_hours_of_rest_yacht_id ON hours_of_rest(yacht_id);
CREATE INDEX idx_hours_of_rest_user_id ON hours_of_rest(user_id);
CREATE INDEX idx_hours_of_rest_date ON hours_of_rest(date);
CREATE UNIQUE INDEX idx_hours_of_rest_unique ON hours_of_rest(yacht_id, user_id, date);
ALTER TABLE hours_of_rest ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- GROUP 3: INVENTORY
-- ============================================================================

-- Parts - master list of spares and consumables
CREATE TABLE parts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  name text NOT NULL,
  part_number text,
  manufacturer text,
  description text,
  category text,
  model_compatibility jsonb DEFAULT '[]'::jsonb,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE parts IS 'Master parts catalog - spares and consumables';
COMMENT ON COLUMN parts.model_compatibility IS 'Compatible equipment models';

CREATE INDEX idx_parts_yacht_id ON parts(yacht_id);
CREATE INDEX idx_parts_part_number ON parts(part_number);
CREATE INDEX idx_parts_category ON parts(category);
ALTER TABLE parts ENABLE ROW LEVEL SECURITY;

-- Equipment parts - many-to-many relationship
CREATE TABLE equipment_parts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  equipment_id uuid NOT NULL REFERENCES equipment(id) ON DELETE CASCADE,
  part_id uuid NOT NULL REFERENCES parts(id) ON DELETE CASCADE,
  quantity_required integer DEFAULT 1,
  notes text,
  created_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE equipment_parts IS 'Many-to-many: which parts are used in which equipment';

CREATE INDEX idx_equipment_parts_yacht_id ON equipment_parts(yacht_id);
CREATE INDEX idx_equipment_parts_equipment_id ON equipment_parts(equipment_id);
CREATE INDEX idx_equipment_parts_part_id ON equipment_parts(part_id);
CREATE UNIQUE INDEX idx_equipment_parts_unique ON equipment_parts(equipment_id, part_id);
ALTER TABLE equipment_parts ENABLE ROW LEVEL SECURITY;

-- Inventory stock - current stock levels and locations
CREATE TABLE inventory_stock (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  part_id uuid NOT NULL REFERENCES parts(id) ON DELETE CASCADE,
  location text,
  quantity integer NOT NULL DEFAULT 0,
  min_quantity integer,
  max_quantity integer,
  reorder_quantity integer,
  last_counted_at timestamptz,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE inventory_stock IS 'Current inventory levels by location';
COMMENT ON COLUMN inventory_stock.location IS 'Physical storage location on vessel';

CREATE INDEX idx_inventory_stock_yacht_id ON inventory_stock(yacht_id);
CREATE INDEX idx_inventory_stock_part_id ON inventory_stock(part_id);
CREATE INDEX idx_inventory_stock_location ON inventory_stock(location);
ALTER TABLE inventory_stock ENABLE ROW LEVEL SECURITY;

-- Suppliers - vendors and OEMs
CREATE TABLE suppliers (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  name text NOT NULL,
  contact_name text,
  email text,
  phone text,
  address jsonb DEFAULT '{}'::jsonb,
  preferred boolean DEFAULT false,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE suppliers IS 'Vendors, OEMs, and service providers';

CREATE INDEX idx_suppliers_yacht_id ON suppliers(yacht_id);
CREATE INDEX idx_suppliers_preferred ON suppliers(preferred);
ALTER TABLE suppliers ENABLE ROW LEVEL SECURITY;

-- Purchase orders - procurement tracking
CREATE TABLE purchase_orders (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  supplier_id uuid REFERENCES suppliers(id) ON DELETE SET NULL,
  po_number text,
  status text DEFAULT 'draft',
  ordered_at timestamptz,
  received_at timestamptz,
  currency text DEFAULT 'USD',
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE purchase_orders IS 'Purchase order tracking';

CREATE INDEX idx_purchase_orders_yacht_id ON purchase_orders(yacht_id);
CREATE INDEX idx_purchase_orders_supplier_id ON purchase_orders(supplier_id);
CREATE INDEX idx_purchase_orders_status ON purchase_orders(status);
ALTER TABLE purchase_orders ENABLE ROW LEVEL SECURITY;

-- Purchase order items - line items
CREATE TABLE purchase_order_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  purchase_order_id uuid NOT NULL REFERENCES purchase_orders(id) ON DELETE CASCADE,
  part_id uuid REFERENCES parts(id) ON DELETE SET NULL,
  description text NOT NULL,
  quantity_ordered integer NOT NULL,
  quantity_received integer DEFAULT 0,
  unit_price numeric(12,2),
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE purchase_order_items IS 'Purchase order line items';

CREATE INDEX idx_purchase_order_items_yacht_id ON purchase_order_items(yacht_id);
CREATE INDEX idx_purchase_order_items_po_id ON purchase_order_items(purchase_order_id);
CREATE INDEX idx_purchase_order_items_part_id ON purchase_order_items(part_id);
ALTER TABLE purchase_order_items ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- GROUP 4: HANDOVER
-- ============================================================================

-- Handovers - shift/crew change documentation
CREATE TABLE handovers (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  period_start date,
  period_end date,
  title text NOT NULL,
  description text,
  created_by uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  status text DEFAULT 'draft',
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE handovers IS 'Crew handover documents';
COMMENT ON COLUMN handovers.description IS 'Auto-generated summary from included items';

CREATE INDEX idx_handovers_yacht_id ON handovers(yacht_id);
CREATE INDEX idx_handovers_status ON handovers(status);
CREATE INDEX idx_handovers_period ON handovers(period_start, period_end);
ALTER TABLE handovers ENABLE ROW LEVEL SECURITY;

-- Handover items - polymorphic links to sources
CREATE TABLE handover_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  handover_id uuid NOT NULL REFERENCES handovers(id) ON DELETE CASCADE,
  source_type handover_source_type NOT NULL,
  source_id uuid NOT NULL,
  summary text,
  detail text,
  importance text DEFAULT 'normal',
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE handover_items IS 'Items included in handover - polymorphic references';
COMMENT ON COLUMN handover_items.source_type IS 'Type of source: fault, work_order, history, document, predictive';
COMMENT ON COLUMN handover_items.source_id IS 'UUID of the source entity';

CREATE INDEX idx_handover_items_yacht_id ON handover_items(yacht_id);
CREATE INDEX idx_handover_items_handover_id ON handover_items(handover_id);
CREATE INDEX idx_handover_items_source ON handover_items(source_type, source_id);
ALTER TABLE handover_items ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- GROUP 5: DOCUMENTS + INDEXING (RAG)
-- ============================================================================

-- Documents - raw file metadata
CREATE TABLE documents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  source text NOT NULL,
  original_path text,
  filename text NOT NULL,
  content_type text,
  size_bytes bigint,
  sha256 char(64) NOT NULL CHECK (sha256 ~ '^[a-f0-9]{64}$'),
  storage_path text NOT NULL,
  equipment_ids uuid[] DEFAULT '{}',
  tags text[] DEFAULT '{}',
  indexed boolean DEFAULT false,
  indexed_at timestamptz,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE documents IS 'Raw document metadata - files from NAS, email, uploads';
COMMENT ON COLUMN documents.sha256 IS 'SHA256 hash for file integrity and deduplication (NOT for auth)';
COMMENT ON COLUMN documents.indexed IS 'Has this document been processed through indexing pipeline';

CREATE INDEX idx_documents_yacht_id ON documents(yacht_id);
CREATE INDEX idx_documents_sha256 ON documents(sha256);
CREATE INDEX idx_documents_indexed ON documents(indexed);
CREATE INDEX idx_documents_source ON documents(source);
CREATE INDEX idx_documents_equipment_ids ON documents USING gin(equipment_ids);
CREATE INDEX idx_documents_tags ON documents USING gin(tags);
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- Document chunks - chunked text with embeddings
CREATE TABLE document_chunks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  chunk_index integer NOT NULL,
  text text NOT NULL,
  page_number integer,
  embedding vector(1024),
  equipment_ids uuid[] DEFAULT '{}',
  fault_codes text[] DEFAULT '{}',
  tags text[] DEFAULT '{}',
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE document_chunks IS 'Chunked document text with vector embeddings for RAG';
COMMENT ON COLUMN document_chunks.embedding IS 'Vector embedding for semantic search';
COMMENT ON COLUMN document_chunks.text IS 'Chunk text content (250-800 tokens typically)';

CREATE INDEX idx_document_chunks_yacht_id ON document_chunks(yacht_id);
CREATE INDEX idx_document_chunks_document_id ON document_chunks(document_id);
CREATE INDEX idx_document_chunks_equipment_ids ON document_chunks USING gin(equipment_ids);
CREATE INDEX idx_document_chunks_fault_codes ON document_chunks USING gin(fault_codes);

-- pgvector index for similarity search
CREATE INDEX idx_document_chunks_embedding ON document_chunks
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;

-- OCR pages - optional intermediate OCR results
CREATE TABLE ocred_pages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  page_number integer NOT NULL,
  raw_text text,
  confidence numeric(5,2),
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE ocred_pages IS 'Intermediate OCR results before chunking';

CREATE INDEX idx_ocred_pages_yacht_id ON ocred_pages(yacht_id);
CREATE INDEX idx_ocred_pages_document_id ON ocred_pages(document_id);
ALTER TABLE ocred_pages ENABLE ROW LEVEL SECURITY;

-- Embedding jobs - track indexing pipeline progress
CREATE TABLE embedding_jobs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  document_id uuid REFERENCES documents(id) ON DELETE CASCADE,
  status text NOT NULL DEFAULT 'pending',
  error_message text,
  started_at timestamptz,
  completed_at timestamptz,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE embedding_jobs IS 'Indexing pipeline job tracking';

CREATE INDEX idx_embedding_jobs_yacht_id ON embedding_jobs(yacht_id);
CREATE INDEX idx_embedding_jobs_document_id ON embedding_jobs(document_id);
CREATE INDEX idx_embedding_jobs_status ON embedding_jobs(status);
ALTER TABLE embedding_jobs ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- GROUP 6: GRAPHRAG
-- ============================================================================

-- Graph nodes - entities in the knowledge graph
CREATE TABLE graph_nodes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  node_type graph_node_type NOT NULL,
  ref_table text NOT NULL,
  ref_id uuid NOT NULL,
  label text NOT NULL,
  properties jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE graph_nodes IS 'Knowledge graph nodes - entities from various tables';
COMMENT ON COLUMN graph_nodes.ref_table IS 'Source table name';
COMMENT ON COLUMN graph_nodes.ref_id IS 'Source entity ID';

CREATE INDEX idx_graph_nodes_yacht_id ON graph_nodes(yacht_id);
CREATE INDEX idx_graph_nodes_type ON graph_nodes(node_type);
CREATE INDEX idx_graph_nodes_ref ON graph_nodes(ref_table, ref_id);
CREATE INDEX idx_graph_nodes_properties ON graph_nodes USING gin(properties);
ALTER TABLE graph_nodes ENABLE ROW LEVEL SECURITY;

-- Graph edges - relationships between entities
CREATE TABLE graph_edges (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  from_node_id uuid NOT NULL REFERENCES graph_nodes(id) ON DELETE CASCADE,
  to_node_id uuid NOT NULL REFERENCES graph_nodes(id) ON DELETE CASCADE,
  edge_type graph_edge_type NOT NULL,
  weight numeric(10,4),
  properties jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE graph_edges IS 'Knowledge graph edges - relationships between entities';
COMMENT ON COLUMN graph_edges.weight IS 'Relationship strength/importance';

CREATE INDEX idx_graph_edges_yacht_id ON graph_edges(yacht_id);
CREATE INDEX idx_graph_edges_from ON graph_edges(from_node_id);
CREATE INDEX idx_graph_edges_to ON graph_edges(to_node_id);
CREATE INDEX idx_graph_edges_type ON graph_edges(edge_type);
CREATE INDEX idx_graph_edges_properties ON graph_edges USING gin(properties);
ALTER TABLE graph_edges ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- GROUP 7: PREDICTIVE MAINTENANCE
-- ============================================================================

-- Predictive state - current risk scores per equipment
CREATE TABLE predictive_state (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  equipment_id uuid NOT NULL REFERENCES equipment(id) ON DELETE CASCADE,
  risk_score numeric(5,4) NOT NULL CHECK (risk_score >= 0 AND risk_score <= 1),
  confidence numeric(5,4) CHECK (confidence >= 0 AND confidence <= 1),
  contributing_factors jsonb DEFAULT '{}'::jsonb,
  last_calculated_at timestamptz NOT NULL DEFAULT now(),
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE predictive_state IS 'Current predictive maintenance risk scores';
COMMENT ON COLUMN predictive_state.risk_score IS 'Failure risk score 0.00-1.00';
COMMENT ON COLUMN predictive_state.contributing_factors IS 'Signals contributing to risk score';

CREATE INDEX idx_predictive_state_yacht_id ON predictive_state(yacht_id);
CREATE INDEX idx_predictive_state_equipment_id ON predictive_state(equipment_id);
CREATE INDEX idx_predictive_state_risk_score ON predictive_state(risk_score);
CREATE UNIQUE INDEX idx_predictive_state_unique ON predictive_state(yacht_id, equipment_id);
ALTER TABLE predictive_state ENABLE ROW LEVEL SECURITY;

-- Predictive insights - explanation and recommendations
CREATE TABLE predictive_insights (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  equipment_id uuid NOT NULL REFERENCES equipment(id) ON DELETE CASCADE,
  insight_type text NOT NULL,
  title text NOT NULL,
  description text,
  recommendation text,
  severity text,
  acknowledged boolean DEFAULT false,
  acknowledged_by uuid REFERENCES users(id) ON DELETE SET NULL,
  acknowledged_at timestamptz,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE predictive_insights IS 'AI-generated predictive maintenance insights and recommendations';
COMMENT ON COLUMN predictive_insights.description IS 'Explanation of the insight';

CREATE INDEX idx_predictive_insights_yacht_id ON predictive_insights(yacht_id);
CREATE INDEX idx_predictive_insights_equipment_id ON predictive_insights(equipment_id);
CREATE INDEX idx_predictive_insights_severity ON predictive_insights(severity);
CREATE INDEX idx_predictive_insights_acknowledged ON predictive_insights(acknowledged);
ALTER TABLE predictive_insights ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- DATABASE FUNCTIONS & TRIGGERS
-- ============================================================================

-- Function to auto-create user record when Supabase auth.users created
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  -- This function should be called by a webhook or database trigger
  -- to create a business user record when auth.users is created
  -- Implementation depends on your onboarding flow
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION public.handle_new_user IS 'Placeholder for auto-creating users records from auth.users';

-- ============================================================================
-- COMPLETED SCHEMA V2.0
-- ============================================================================
-- Changes from V1.0:
-- ✓ Added auth_user_id to users table (links to auth.users)
-- ✓ Added agents table for local agent authentication
-- ✓ Added api_keys table for service authentication
-- ✓ Changed yacht signature to yacht_secret_hash (bcrypt)
-- ✓ Removed redundant yacht_signatures table
-- ✓ Added bcrypt constraints on all secret/hash fields
-- ✓ Added SHA256 constraint on documents.sha256 (file integrity only)
-- ✓ Proper foreign key cascades
-- ✓ Row-level security enabled on all tables
-- ✓ Comprehensive indexing
-- ✓ Auth integration documented in AUTH_INTEGRATION.md
-- ============================================================================
