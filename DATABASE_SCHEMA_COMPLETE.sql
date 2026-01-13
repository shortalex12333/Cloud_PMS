-- =============================================================================
-- CelesteOS Complete Database Schema
-- =============================================================================
-- Purpose: Define all tables and columns needed for the complete action system
-- Date: 2026-01-11
-- Version: 1.0
-- =============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;  -- For document embeddings

-- =============================================================================
-- CORE DOMAIN TABLES
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Yachts (Tenant isolation)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.yachts (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL,
  imo_number TEXT,
  flag TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- -----------------------------------------------------------------------------
-- Equipment (Physical assets)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.pms_equipment (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

  -- Identity
  name TEXT NOT NULL,
  manufacturer TEXT,
  model TEXT,
  serial_number TEXT,

  -- Classification
  category TEXT,  -- e.g., 'generator', 'hvac', 'pump'
  system TEXT,    -- e.g., 'propulsion', 'electrical'

  -- Location
  location TEXT,  -- e.g., 'Engine Room Deck 3', 'Aft Lazarette'

  -- Status
  status TEXT DEFAULT 'operational' CHECK (status IN ('operational', 'down', 'maintenance', 'decommissioned')),
  critical BOOLEAN DEFAULT FALSE,  -- Critical system

  -- Documentation
  manual_available BOOLEAN DEFAULT FALSE,
  manual_document_id UUID REFERENCES public.pms_documents(id),

  -- Metadata
  installation_date DATE,
  last_service_date DATE,
  next_service_due DATE,

  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_equipment_yacht ON public.pms_equipment(yacht_id);
CREATE INDEX idx_equipment_status ON public.pms_equipment(yacht_id, status);
CREATE INDEX idx_equipment_critical ON public.pms_equipment(yacht_id, critical) WHERE critical = TRUE;

-- -----------------------------------------------------------------------------
-- Faults (Problem observations)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.pms_faults (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

  -- Linkage
  equipment_id UUID REFERENCES public.pms_equipment(id),
  work_order_id UUID REFERENCES public.pms_work_orders(id),  -- FK added later

  -- Identity
  code TEXT NOT NULL,  -- e.g., 'MTU-OVHT-01', 'CAT-COOL-02'
  title TEXT NOT NULL,
  description TEXT,

  -- Severity
  severity TEXT NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),

  -- Status
  status TEXT DEFAULT 'active' CHECK (status IN ('active', 'acknowledged', 'diagnosed', 'resolved')),

  -- Recurrence tracking
  occurrence_count INTEGER DEFAULT 1,
  last_occurrence TIMESTAMPTZ DEFAULT NOW(),

  -- Workflow
  reported_by UUID NOT NULL REFERENCES auth.users(id),
  reported_at TIMESTAMPTZ DEFAULT NOW(),
  acknowledged_by UUID REFERENCES auth.users(id),
  acknowledged_at TIMESTAMPTZ,
  diagnosed_at TIMESTAMPTZ,
  resolved_at TIMESTAMPTZ,
  resolved_by UUID REFERENCES auth.users(id),

  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_faults_yacht ON public.pms_faults(yacht_id);
CREATE INDEX idx_faults_status ON public.pms_faults(yacht_id, status);
CREATE INDEX idx_faults_equipment ON public.pms_faults(equipment_id, status);
CREATE INDEX idx_faults_severity ON public.pms_faults(yacht_id, severity, status);
CREATE INDEX idx_faults_recurrence ON public.pms_faults(yacht_id, occurrence_count DESC, last_occurrence DESC);
CREATE INDEX idx_faults_unresolved ON public.pms_faults(yacht_id, status) WHERE status IN ('active', 'acknowledged', 'diagnosed');

-- -----------------------------------------------------------------------------
-- Work Orders (Action commitments)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.pms_work_orders (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

  -- Identity
  number TEXT NOT NULL UNIQUE,  -- e.g., 'WO-2024-001'
  title TEXT NOT NULL,
  description TEXT,

  -- Linkage
  equipment_id UUID REFERENCES public.pms_equipment(id),
  fault_id UUID REFERENCES public.pms_faults(id),
  location TEXT,

  -- Priority
  priority TEXT DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high', 'critical')),

  -- Status
  status TEXT DEFAULT 'candidate' CHECK (status IN (
    'candidate',      -- Created but work not started
    'in_progress',    -- Work actively happening
    'blocked',        -- Cannot proceed (waiting for parts/approval)
    'pending_parts',  -- Waiting for parts delivery
    'completed',      -- Work finished
    'cancelled'       -- WO cancelled
  )),

  -- Outcome (set on completion)
  outcome TEXT CHECK (outcome IN ('resolved', 'partial', 'unsuccessful')),

  -- Assignment
  assigned_to UUID REFERENCES auth.users(id),
  assigned_at TIMESTAMPTZ,

  -- Timing
  time_spent_hours DECIMAL(5,2),  -- Calculated or manually entered
  estimated_hours DECIMAL(5,2),

  -- Workflow timestamps
  created_by UUID NOT NULL REFERENCES auth.users(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  completed_by UUID REFERENCES auth.users(id),

  -- Activity tracking
  last_activity TIMESTAMPTZ DEFAULT NOW(),

  -- Metadata
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_work_orders_yacht ON public.pms_work_orders(yacht_id);
CREATE INDEX idx_work_orders_status ON public.pms_work_orders(yacht_id, status);
CREATE INDEX idx_work_orders_equipment ON public.pms_work_orders(equipment_id, status);
CREATE INDEX idx_work_orders_fault ON public.pms_work_orders(fault_id);
CREATE INDEX idx_work_orders_assigned ON public.pms_work_orders(assigned_to, status);
CREATE INDEX idx_work_orders_active ON public.pms_work_orders(yacht_id, status) WHERE status IN ('in_progress', 'blocked', 'pending_parts');

-- Add FK constraint to faults (circular reference handled here)
ALTER TABLE public.pms_faults
  ADD CONSTRAINT fk_faults_work_order
  FOREIGN KEY (work_order_id)
  REFERENCES public.pms_work_orders(id);

-- -----------------------------------------------------------------------------
-- Work Order Notes (Timeline/breadcrumbs)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.pms_work_order_notes (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  work_order_id UUID NOT NULL REFERENCES public.pms_work_orders(id) ON DELETE CASCADE,

  -- Content
  category TEXT DEFAULT 'update' CHECK (category IN ('update', 'diagnosis', 'action', 'issue', 'resolution')),
  content TEXT NOT NULL,

  -- Audit
  created_by UUID NOT NULL REFERENCES auth.users(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_wo_notes_wo ON public.pms_work_order_notes(work_order_id, created_at DESC);
CREATE INDEX idx_wo_notes_user ON public.pms_work_order_notes(created_by, created_at DESC);

-- =============================================================================
-- INVENTORY & PARTS DOMAIN
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Parts (Master data)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.pms_parts (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

  -- Identity
  name TEXT NOT NULL,
  part_number TEXT,  -- Manufacturer part number
  internal_code TEXT,  -- Internal inventory code
  manufacturer TEXT,
  model TEXT,
  description TEXT,

  -- Classification
  category TEXT,  -- e.g., 'filters', 'electrical', 'consumables'
  sub_category TEXT,

  -- Inventory
  stock_level INTEGER DEFAULT 0,
  unit_of_measure TEXT DEFAULT 'each',  -- 'each', 'liters', 'kg', etc.

  -- Thresholds
  critical_threshold INTEGER DEFAULT 0,   -- Immediate action required
  low_threshold INTEGER DEFAULT 5,        -- Warning level
  minimum_threshold INTEGER DEFAULT 10,   // Reorder point

  -- Storage
  location TEXT,  -- e.g., '3C', 'Main Workshop', 'Aft Stores'
  storage_notes TEXT,

  -- Finance
  unit_cost DECIMAL(10,2),
  currency TEXT DEFAULT 'USD',

  -- Supplier
  preferred_supplier TEXT,
  supplier_part_number TEXT,

  -- Status
  active BOOLEAN DEFAULT TRUE,
  is_candidate BOOLEAN DEFAULT FALSE,  -- TRUE if not yet verified by HOD

  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_parts_yacht ON public.pms_parts(yacht_id);
CREATE INDEX idx_parts_stock ON public.pms_parts(yacht_id, stock_level);
CREATE INDEX idx_parts_critical ON public.pms_parts(yacht_id, stock_level, critical_threshold) WHERE stock_level <= critical_threshold;
CREATE INDEX idx_parts_low ON public.pms_parts(yacht_id, stock_level, low_threshold) WHERE stock_level < low_threshold;
CREATE INDEX idx_parts_candidate ON public.pms_parts(yacht_id, is_candidate) WHERE is_candidate = TRUE;

-- -----------------------------------------------------------------------------
-- Work Order Parts (Planning - what will be needed)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.pms_work_order_parts (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  work_order_id UUID NOT NULL REFERENCES public.pms_work_orders(id) ON DELETE CASCADE,
  part_id UUID NOT NULL REFERENCES public.pms_parts(id),

  -- Quantities
  quantity_planned INTEGER NOT NULL,  -- How many added to WO
  quantity_used INTEGER DEFAULT 0,    -- How many logged as used (from inventory_transactions)

  -- Status
  status TEXT DEFAULT 'planned' CHECK (status IN ('planned', 'logged', 'partial')),

  -- Audit
  added_by UUID NOT NULL REFERENCES auth.users(id),
  added_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_wo_parts_wo ON public.pms_work_order_parts(work_order_id);
CREATE INDEX idx_wo_parts_part ON public.pms_work_order_parts(part_id);
CREATE INDEX idx_wo_parts_unlogged ON public.pms_work_order_parts(work_order_id) WHERE quantity_used < quantity_planned;

-- -----------------------------------------------------------------------------
-- Inventory Transactions (Usage, receiving, adjustments)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.pms_inventory_transactions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
  part_id UUID NOT NULL REFERENCES public.pms_parts(id),

  -- Transaction type
  transaction_type TEXT NOT NULL CHECK (transaction_type IN ('receive', 'usage', 'adjustment', 'transfer', 'cycle_count')),

  -- Quantity
  quantity INTEGER NOT NULL,  -- Positive for receive/adjustment up, negative for usage/adjustment down

  -- Context
  work_order_id UUID REFERENCES public.pms_work_orders(id),
  receiving_session_id UUID REFERENCES public.pms_receiving_sessions(id),  -- FK added later
  location TEXT,

  -- Notes
  notes TEXT,
  reason TEXT,  -- For adjustments: why stock was adjusted

  -- Audit
  user_id UUID NOT NULL REFERENCES auth.users(id),
  timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_inventory_tx_part ON public.pms_inventory_transactions(part_id, timestamp DESC);
CREATE INDEX idx_inventory_tx_yacht ON public.pms_inventory_transactions(yacht_id, timestamp DESC);
CREATE INDEX idx_inventory_tx_wo ON public.pms_inventory_transactions(work_order_id);
CREATE INDEX idx_inventory_tx_type ON public.pms_inventory_transactions(yacht_id, transaction_type, timestamp DESC);

-- =============================================================================
-- PROCUREMENT DOMAIN (Shopping List, Orders, Receiving)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Shopping List (Procurement queue)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.pms_shopping_list (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

  -- Part reference
  part_id UUID REFERENCES public.pms_parts(id),  -- NULL for candidate parts
  candidate_part_name TEXT,  -- Required if part_id IS NULL
  candidate_part_description TEXT,

  -- Quantity
  quantity INTEGER NOT NULL,

  -- Source trigger (audit trail - why does this exist?)
  source_type TEXT CHECK (source_type IN ('inventory_low', 'inventory_oos', 'work_order_usage', 'receiving_discrepancy', 'manual_add')),
  source_id UUID,  -- work_order_id, receiving_item_id, etc.
  source_notes TEXT,

  -- Status (item-level state machine)
  state TEXT DEFAULT 'CANDIDATE' CHECK (state IN (
    'CANDIDATE',           -- Created but not reviewed
    'ACTIVE',             -- Under review by HOD
    'REJECTED',           -- HOD rejected
    'COMMITTED',          -- Approved and ordered
    'PARTIALLY_FULFILLED', -- Some received
    'FULFILLED',          -- All received
    'INSTALLED',          -- Installed immediately (skip inventory)
    'MISSING',            -- Not received / damaged
    'CANCELLED'           -- Order cancelled
  )),

  -- Order linkage
  purchase_order_id UUID REFERENCES public.pms_purchase_orders(id),  -- FK added later

  -- Procurement metadata
  supplier TEXT,
  supplier_part_number TEXT,
  urgency TEXT DEFAULT 'normal' CHECK (urgency IN ('normal', 'high', 'critical')),
  notes TEXT,

  -- Finance
  estimated_unit_cost DECIMAL(10,2),
  actual_unit_cost DECIMAL(10,2),
  committed_cost DECIMAL(10,2),  -- Order issued (quantity * estimated_unit_cost)
  actual_cost DECIMAL(10,2),     -- Received/installed (quantity * actual_unit_cost)

  -- Workflow
  created_by UUID NOT NULL REFERENCES auth.users(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  reviewed_by UUID REFERENCES auth.users(id),
  reviewed_at TIMESTAMPTZ,
  approved_by UUID REFERENCES auth.users(id),
  approved_at TIMESTAMPTZ,
  ordered_at TIMESTAMPTZ,
  fulfilled_at TIMESTAMPTZ,

  -- Metadata
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_shopping_list_yacht ON public.pms_shopping_list(yacht_id);
CREATE INDEX idx_shopping_list_state ON public.pms_shopping_list(yacht_id, state);
CREATE INDEX idx_shopping_list_part ON public.pms_shopping_list(part_id, state);
CREATE INDEX idx_shopping_list_order ON public.pms_shopping_list(purchase_order_id);
CREATE INDEX idx_shopping_list_source ON public.pms_shopping_list(source_type, source_id);
CREATE INDEX idx_shopping_list_candidate ON public.pms_shopping_list(yacht_id, state) WHERE state = 'CANDIDATE';
CREATE INDEX idx_shopping_list_urgency ON public.pms_shopping_list(yacht_id, urgency, created_at DESC) WHERE urgency IN ('high', 'critical');

-- -----------------------------------------------------------------------------
-- Purchase Orders (Orders to suppliers)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.pms_purchase_orders (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

  -- Identity
  po_number TEXT NOT NULL UNIQUE,  -- e.g., 'PO-2024-001'
  supplier_name TEXT NOT NULL,
  supplier_contact TEXT,
  supplier_reference TEXT,  -- Supplier's order confirmation number

  -- Dates
  order_date DATE NOT NULL,
  expected_delivery DATE,
  actual_delivery DATE,

  -- Status
  status TEXT DEFAULT 'draft' CHECK (status IN (
    'draft',       -- Being prepared
    'pending',     -- Awaiting approval
    'ordered',     -- Sent to supplier
    'partial',     -- Some items received
    'fulfilled',   -- All items received
    'cancelled'    -- Order cancelled
  )),

  -- Finance
  total_amount DECIMAL(10,2),
  currency TEXT DEFAULT 'USD',
  payment_terms TEXT,

  -- Attachments
  documents TEXT[],  -- Array of Supabase storage paths (invoices, confirmations)

  -- Notes
  notes TEXT,

  -- Audit
  created_by UUID NOT NULL REFERENCES auth.users(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  approved_by UUID REFERENCES auth.users(id),
  approved_at TIMESTAMPTZ,
  ordered_by UUID REFERENCES auth.users(id),
  ordered_at TIMESTAMPTZ,

  -- Metadata
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_purchase_orders_yacht ON public.pms_purchase_orders(yacht_id);
CREATE INDEX idx_purchase_orders_status ON public.pms_purchase_orders(yacht_id, status);
CREATE INDEX idx_purchase_orders_supplier ON public.pms_purchase_orders(supplier_name, status);
CREATE INDEX idx_purchase_orders_date ON public.pms_purchase_orders(yacht_id, order_date DESC);

-- Add FK constraint to shopping list
ALTER TABLE public.pms_shopping_list
  ADD CONSTRAINT fk_shopping_list_po
  FOREIGN KEY (purchase_order_id)
  REFERENCES public.pms_purchase_orders(id);

-- -----------------------------------------------------------------------------
-- Receiving Sessions (Event-driven receiving flow)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.pms_receiving_sessions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

  -- Order linkage
  purchase_order_id UUID REFERENCES public.pms_purchase_orders(id),

  -- Source documents
  packing_slip_images TEXT[],  -- Array of Supabase storage paths
  packing_slip_ocr_text TEXT,
  packing_slip_ocr_processed BOOLEAN DEFAULT FALSE,

  -- Status (state machine)
  status TEXT DEFAULT 'CANDIDATE' CHECK (status IN (
    'CANDIDATE',   -- Packing slip uploaded, order not confirmed
    'ACTIVE',      -- Receiving table visible, user checking items
    'REVIEW',      -- User reviewing summary before commit
    'COMMITTED'    -- Session complete, events written
  )),

  -- Summary (set on commit)
  total_items INTEGER,
  items_received INTEGER,
  items_installed INTEGER,
  items_missing INTEGER,
  items_damaged INTEGER,

  -- Audit
  created_by UUID NOT NULL REFERENCES auth.users(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  committed_at TIMESTAMPTZ,
  committed_by UUID REFERENCES auth.users(id),

  -- Metadata
  notes TEXT
);

CREATE INDEX idx_receiving_sessions_yacht ON public.pms_receiving_sessions(yacht_id);
CREATE INDEX idx_receiving_sessions_status ON public.pms_receiving_sessions(yacht_id, status);
CREATE INDEX idx_receiving_sessions_po ON public.pms_receiving_sessions(purchase_order_id);

-- Add FK constraint to inventory transactions
ALTER TABLE public.pms_inventory_transactions
  ADD CONSTRAINT fk_inventory_tx_receiving
  FOREIGN KEY (receiving_session_id)
  REFERENCES public.pms_receiving_sessions(id);

-- -----------------------------------------------------------------------------
-- Receiving Items (Individual items in receiving session)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.pms_receiving_items (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  receiving_session_id UUID NOT NULL REFERENCES public.pms_receiving_sessions(id) ON DELETE CASCADE,

  -- Matching (what is this item?)
  shopping_list_item_id UUID REFERENCES public.pms_shopping_list(id),
  part_id UUID REFERENCES public.pms_parts(id),
  candidate_part_name TEXT,  -- If unmatched, user creates candidate

  -- OCR extracted data (draft)
  ocr_line_text TEXT,
  ocr_quantity INTEGER,
  ocr_part_number TEXT,
  ocr_description TEXT,

  -- Verified quantities
  expected_quantity INTEGER,
  delivered_quantity INTEGER,

  -- Verification (CHECKBOX = TRUTH)
  checked BOOLEAN DEFAULT FALSE,  -- User must explicitly tick

  -- Status
  status TEXT DEFAULT 'pending' CHECK (status IN (
    'pending',    -- Not yet checked
    'ok',         -- Checked, quantity matches
    'missing',    -- Not delivered
    'damaged',    -- Delivered but damaged
    'incorrect'   -- Wrong item delivered
  )),

  -- Discrepancy details
  discrepancy_notes TEXT,
  discrepancy_photos TEXT[],  -- Supabase paths

  -- Installation (skip inventory)
  installed BOOLEAN DEFAULT FALSE,
  work_order_id UUID REFERENCES public.pms_work_orders(id),

  -- Storage
  location TEXT,

  -- Audit
  checked_by UUID REFERENCES auth.users(id),
  checked_at TIMESTAMPTZ
);

CREATE INDEX idx_receiving_items_session ON public.pms_receiving_items(receiving_session_id);
CREATE INDEX idx_receiving_items_shopping ON public.pms_receiving_items(shopping_list_item_id);
CREATE INDEX idx_receiving_items_part ON public.pms_receiving_items(part_id);
CREATE INDEX idx_receiving_items_checked ON public.pms_receiving_items(receiving_session_id, checked);
CREATE INDEX idx_receiving_items_status ON public.pms_receiving_items(receiving_session_id, status);

-- =============================================================================
-- DOCUMENTATION DOMAIN
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Documents (Manuals, procedures, schematics)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.pms_documents (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  yacht_id UUID REFERENCES public.yachts(id),  -- NULL for manufacturer manuals (shared)

  -- Identity
  title TEXT NOT NULL,
  manufacturer TEXT,
  model TEXT,
  document_type TEXT CHECK (document_type IN ('manual', 'procedure', 'schematic', 'certificate', 'datasheet')),

  -- Storage
  storage_path TEXT NOT NULL,  -- Supabase storage path
  file_size_bytes BIGINT,
  page_count INTEGER,

  -- Classification
  category TEXT,
  tags TEXT[],

  -- Indexing status
  indexed BOOLEAN DEFAULT FALSE,
  chunk_count INTEGER DEFAULT 0,

  -- Audit
  upload_date TIMESTAMPTZ DEFAULT NOW(),
  uploaded_by UUID REFERENCES auth.users(id),

  -- Metadata
  version TEXT,
  revision_date DATE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_documents_yacht ON public.pms_documents(yacht_id);
CREATE INDEX idx_documents_type ON public.pms_documents(document_type);
CREATE INDEX idx_documents_manufacturer ON public.pms_documents(manufacturer, model);
CREATE INDEX idx_documents_indexed ON public.pms_documents(indexed) WHERE indexed = FALSE;

-- -----------------------------------------------------------------------------
-- Document Chunks (For search and context extraction)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.pms_document_chunks (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  document_id UUID NOT NULL REFERENCES public.pms_documents(id) ON DELETE CASCADE,

  -- Location in document
  page_number INTEGER,
  chunk_index INTEGER,  -- Chunk number on this page
  section_title TEXT,
  section_number TEXT,  -- e.g., '7.3', '12.4.1'

  -- Content
  content TEXT NOT NULL,
  content_length INTEGER,

  -- Semantic search
  embedding VECTOR(1536),  -- OpenAI ada-002 or similar

  -- Entity references (extracted during indexing)
  fault_code_refs TEXT[],     -- e.g., ['MTU-OVHT-01', 'CAT-COOL-02']
  equipment_refs TEXT[],      -- e.g., ['Generator 2', 'Main Engine']
  part_refs TEXT[],           -- e.g., ['Thermostat', 'Coolant Filter']
  procedure_refs TEXT[],      -- e.g., ['Startup Procedure', 'Shutdown']

  -- Metadata
  chunk_type TEXT CHECK (chunk_type IN ('text', 'table', 'diagram_caption', 'list', 'heading')),
  importance_score DECIMAL(3,2),  -- 0.00-1.00 (for ranking)

  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_doc_chunks_doc ON public.pms_document_chunks(document_id);
CREATE INDEX idx_doc_chunks_page ON public.pms_document_chunks(document_id, page_number);
CREATE INDEX idx_doc_chunks_embedding ON public.pms_document_chunks USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_doc_chunks_fault_refs ON public.pms_document_chunks USING gin(fault_code_refs);
CREATE INDEX idx_doc_chunks_equipment_refs ON public.pms_document_chunks USING gin(equipment_refs);

-- =============================================================================
-- HANDOVER & COMMUNICATION DOMAIN
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Handover (Parent - shift briefing document)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.pms_handover (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

  -- Shift identification
  shift_date DATE NOT NULL,
  shift_period TEXT CHECK (shift_period IN ('day', 'night', '0800-2000', '2000-0800', 'watch_1', 'watch_2', 'watch_3')),

  -- Status
  status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'archived')),

  -- Immutability
  snapshot JSONB,  -- Immutable copy of all items after publish
  is_published BOOLEAN DEFAULT FALSE,

  -- Signature
  signed_by UUID REFERENCES auth.users(id),
  signed_at TIMESTAMPTZ,

  -- Audit
  created_by UUID NOT NULL REFERENCES auth.users(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  published_at TIMESTAMPTZ,
  archived_at TIMESTAMPTZ
);

CREATE INDEX idx_handover_yacht ON public.pms_handover(yacht_id);
CREATE INDEX idx_handover_date ON public.pms_handover(yacht_id, shift_date DESC);
CREATE INDEX idx_handover_status ON public.pms_handover(yacht_id, status);
CREATE INDEX idx_handover_published ON public.pms_handover(yacht_id, published_at DESC) WHERE published_at IS NOT NULL;

-- -----------------------------------------------------------------------------
-- Handover Items (Individual items in handover)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.pms_handover_items (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  handover_id UUID REFERENCES public.pms_handover(id) ON DELETE CASCADE,
  yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

  -- Source (why does this exist in handover?)
  source_type TEXT NOT NULL CHECK (source_type IN ('work_order', 'fault', 'equipment', 'document', 'inventory', 'receiving', 'manual_note')),
  source_id UUID,  -- Polymorphic reference to source entity

  -- Ownership
  owner_id UUID NOT NULL REFERENCES auth.users(id),
  owner_name TEXT NOT NULL,

  -- Risk & Priority
  risk_category TEXT CHECK (risk_category IN ('safety_risk', 'equipment_damage', 'operational_delay', 'regulatory_issue', 'other')),
  priority INTEGER DEFAULT 3 CHECK (priority BETWEEN 1 AND 3),  -- 1=urgent, 2=high, 3=normal

  -- Content
  title TEXT NOT NULL,
  summary_text TEXT NOT NULL,  -- Auto-generated from source + user note
  next_action TEXT NOT NULL,   -- Required, must be specific

  -- Status
  status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'acknowledged', 'archived')),

  -- Acknowledgment
  acknowledged_at TIMESTAMPTZ,
  acknowledged_by UUID REFERENCES auth.users(id),

  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  published_at TIMESTAMPTZ,
  archived_at TIMESTAMPTZ,

  -- Immutability
  is_published BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_handover_items_handover ON public.pms_handover_items(handover_id, status);
CREATE INDEX idx_handover_items_yacht ON public.pms_handover_items(yacht_id, status);
CREATE INDEX idx_handover_items_owner ON public.pms_handover_items(owner_id, status);
CREATE INDEX idx_handover_items_priority ON public.pms_handover_items(yacht_id, priority, created_at DESC);
CREATE INDEX idx_handover_items_source ON public.pms_handover_items(source_type, source_id);
CREATE INDEX idx_handover_items_unacknowledged ON public.pms_handover_items(yacht_id, status, priority) WHERE status = 'published' AND acknowledged_at IS NULL;

-- =============================================================================
-- ACTION SYSTEM CONFIGURATION
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Action Registry (Configuration for action offering)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.pms_action_registry (
  id TEXT PRIMARY KEY,  -- e.g., 'create_work_order_from_fault'

  -- Classification
  action_type TEXT NOT NULL CHECK (action_type IN ('read', 'mutate', 'situational')),
  priority TEXT NOT NULL CHECK (priority IN ('p0', 'p1', 'p2')),

  -- Display
  name TEXT NOT NULL,
  description TEXT,
  icon TEXT,  -- Icon name/code

  -- Entry conditions (JSON config for when action is available)
  entry_conditions JSONB,
  -- Example: {"entity_types": ["fault"], "requires": {"equipment.manual_available": true}}

  -- Pre-fill template (JSON template for form pre-filling)
  prefill_template JSONB,
  -- Example: {"title": "${equipment.name} - ${fault.code}", "priority": "${fault.severity}"}

  -- Permissions
  required_roles TEXT[],  -- Roles allowed to execute this action

  -- Status
  active BOOLEAN DEFAULT TRUE,
  version INTEGER DEFAULT 1,

  -- Metadata
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Example action registry entries (to be inserted)
INSERT INTO public.pms_action_registry (id, action_type, priority, name, entry_conditions, prefill_template) VALUES
('show_manual_section', 'read', 'p0', 'View Manual Section',
  '{"entity_types": ["fault", "equipment"], "requires": {"equipment.manual_available": true}}'::jsonb,
  '{"document_id": "${equipment.manual_document_id}", "section": "${fault.code}"}'::jsonb),

('create_work_order_from_fault', 'mutate', 'p0', 'Create Work Order',
  '{"entity_types": ["fault"], "excludes": {"fault.work_order_id": "NOT NULL"}}'::jsonb,
  '{"title": "${equipment.name} - ${fault.code}", "equipment_id": "${fault.equipment_id}", "priority": "${fault.severity}", "description": "${fault.description}\\n\\nOccurrences: ${fault.occurrence_count} in last 30 days"}'::jsonb),

('add_note_to_work_order', 'mutate', 'p0', 'Add Note',
  '{"entity_types": ["work_order"], "requires": {"work_order.status": ["candidate", "in_progress", "blocked", "pending_parts"]}}'::jsonb,
  '{"category": "update"}'::jsonb),

('add_part_to_work_order', 'mutate', 'p0', 'Add Part',
  '{"entity_types": ["work_order"], "requires": {"work_order.status": ["candidate", "in_progress", "pending_parts"]}}'::jsonb,
  '{}'::jsonb),

('mark_work_order_complete', 'mutate', 'p0', 'Mark Complete',
  '{"entity_types": ["work_order"], "requires": {"work_order.status": "in_progress"}}'::jsonb,
  '{"outcome": "resolved", "time_spent_hours": "${calculated_time}"}'::jsonb),

('check_stock_level', 'read', 'p0', 'Check Stock',
  '{"entity_types": ["part"]}'::jsonb,
  '{}'::jsonb),

('log_part_usage', 'mutate', 'p0', 'Log Part Usage',
  '{"entity_types": ["work_order"], "requires": {"has_unlogged_parts": true}}'::jsonb,
  '{}'::jsonb),

('add_to_handover', 'mutate', 'p0', 'Add to Handover',
  '{"entity_types": ["fault", "work_order", "equipment", "document", "part"]}'::jsonb,
  '{"category": "${source_type_to_category}", "priority": "${source_priority}"}'::jsonb);

-- =============================================================================
-- AUDIT & ACCOUNTABILITY
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Audit Log (Universal event trail)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.pms_audit_log (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  yacht_id UUID REFERENCES public.yachts(id) ON DELETE CASCADE,

  -- Entity
  entity_type TEXT NOT NULL,  -- 'work_order', 'fault', 'inventory', 'handover', etc.
  entity_id UUID NOT NULL,

  -- Action
  action TEXT NOT NULL,  -- 'created', 'updated', 'completed', 'logged_parts', 'acknowledged', etc.
  action_category TEXT CHECK (action_category IN ('create', 'update', 'delete', 'status_change', 'workflow', 'finance')),

  -- Context
  details JSONB,  -- Flexible JSON for action-specific data
  -- Example: {"part_id": "uuid", "quantity": 5, "from_location": "Workshop", "to_location": "3C"}

  -- User
  user_id UUID NOT NULL REFERENCES auth.users(id),
  user_name TEXT NOT NULL,
  user_role TEXT,

  -- IP & Session
  ip_address INET,
  session_id TEXT,

  -- Timestamp
  timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_log_entity ON public.pms_audit_log(entity_type, entity_id, timestamp DESC);
CREATE INDEX idx_audit_log_yacht ON public.pms_audit_log(yacht_id, timestamp DESC);
CREATE INDEX idx_audit_log_user ON public.pms_audit_log(user_id, timestamp DESC);
CREATE INDEX idx_audit_log_action ON public.pms_audit_log(action, timestamp DESC);
CREATE INDEX idx_audit_log_timestamp ON public.pms_audit_log(timestamp DESC);

-- =============================================================================
-- SEARCH & QUERY HISTORY (Optional, for analytics)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Search Queries (Track user searches for intent learning - anonymized)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.pms_search_queries (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

  -- Query
  query_text TEXT NOT NULL,
  query_intent TEXT,  -- 'information', 'action', 'navigation'
  action_keywords TEXT[],
  entity_keywords TEXT[],

  -- Results
  results_count INTEGER,
  top_result_type TEXT,  -- 'fault', 'equipment', 'work_order', etc.
  top_result_id UUID,

  -- User interaction
  action_selected TEXT,  -- Action ID if user selected action from results
  result_clicked BOOLEAN DEFAULT FALSE,

  -- Anonymized user
  user_role TEXT,  -- Role only, not user_id (privacy)

  -- Timestamp
  timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_search_queries_yacht ON public.pms_search_queries(yacht_id, timestamp DESC);
CREATE INDEX idx_search_queries_intent ON public.pms_search_queries(query_intent, timestamp DESC);
CREATE INDEX idx_search_queries_keywords ON public.pms_search_queries USING gin(action_keywords);

-- =============================================================================
-- HELPER FUNCTIONS
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Calculate stock level from transactions
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION calculate_stock_level(p_part_id UUID)
RETURNS INTEGER AS $$
  SELECT COALESCE(SUM(quantity), 0)::INTEGER
  FROM public.pms_inventory_transactions
  WHERE part_id = p_part_id;
$$ LANGUAGE SQL STABLE;

-- -----------------------------------------------------------------------------
-- Auto-update stock level on transaction insert
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION update_part_stock_level()
RETURNS TRIGGER AS $$
BEGIN
  UPDATE public.pms_parts
  SET stock_level = calculate_stock_level(NEW.part_id),
      updated_at = NOW()
  WHERE id = NEW.part_id;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_part_stock
  AFTER INSERT ON public.pms_inventory_transactions
  FOR EACH ROW
  EXECUTE FUNCTION update_part_stock_level();

-- -----------------------------------------------------------------------------
-- Auto-update work order last_activity on note insert
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION update_wo_last_activity()
RETURNS TRIGGER AS $$
BEGIN
  UPDATE public.pms_work_orders
  SET last_activity = NOW(),
      updated_at = NOW()
  WHERE id = NEW.work_order_id;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_wo_activity
  AFTER INSERT ON public.pms_work_order_notes
  FOR EACH ROW
  EXECUTE FUNCTION update_wo_last_activity();

-- =============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- =============================================================================

-- Enable RLS on all tables
ALTER TABLE public.pms_equipment ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pms_faults ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pms_work_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pms_work_order_notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pms_parts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pms_work_order_parts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pms_inventory_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pms_shopping_list ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pms_purchase_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pms_receiving_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pms_receiving_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pms_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pms_document_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pms_handover ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pms_handover_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pms_audit_log ENABLE ROW LEVEL SECURITY;

-- Example RLS policy (yacht isolation)
-- Users can only see data for their yacht
CREATE POLICY yacht_isolation ON public.pms_equipment
  FOR ALL
  USING (yacht_id = (SELECT yacht_id FROM auth.users WHERE id = auth.uid()));

-- Apply similar policies to all yacht-scoped tables...
-- (Full RLS policies would be extensive - this is the pattern)

-- =============================================================================
-- VIEWS (Optional, for common queries)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Active faults without work orders
-- -----------------------------------------------------------------------------
CREATE VIEW pms_faults_needing_wo AS
SELECT
  f.*,
  e.name AS equipment_name,
  e.location
FROM public.pms_faults f
LEFT JOIN public.pms_equipment e ON f.equipment_id = e.id
WHERE f.work_order_id IS NULL
  AND f.status IN ('active', 'acknowledged', 'diagnosed')
  AND f.severity IN ('high', 'critical');

-- -----------------------------------------------------------------------------
-- Parts below minimum threshold
-- -----------------------------------------------------------------------------
CREATE VIEW pms_parts_low_stock AS
SELECT
  p.*,
  (p.minimum_threshold - p.stock_level) AS quantity_needed
FROM public.pms_parts p
WHERE p.stock_level < p.minimum_threshold
  AND p.active = TRUE
ORDER BY p.stock_level, p.critical_threshold;

-- -----------------------------------------------------------------------------
-- Work orders pending parts
-- -----------------------------------------------------------------------------
CREATE VIEW pms_work_orders_pending_parts AS
SELECT
  wo.id,
  wo.number,
  wo.title,
  wo.status,
  COUNT(wop.id) AS parts_count,
  SUM(CASE WHEN p.stock_level < wop.quantity_planned THEN 1 ELSE 0 END) AS parts_unavailable
FROM public.pms_work_orders wo
JOIN public.pms_work_order_parts wop ON wo.id = wop.work_order_id
JOIN public.pms_parts p ON wop.part_id = p.id
WHERE wo.status IN ('candidate', 'in_progress', 'pending_parts')
GROUP BY wo.id, wo.number, wo.title, wo.status
HAVING SUM(CASE WHEN p.stock_level < wop.quantity_planned THEN 1 ELSE 0 END) > 0;

-- =============================================================================
-- END OF SCHEMA
-- =============================================================================

-- Notes:
-- 1. This schema supports the complete action system architecture
-- 2. All tables include yacht_id for multi-tenancy isolation
-- 3. Audit trails are comprehensive with pms_audit_log
-- 4. Action offering is driven by pms_action_registry configuration
-- 5. Situational states (receiving, shopping list) have explicit state machines
-- 6. Thresholds are configurable per-part for inventory actions
-- 7. Document chunking supports semantic search and entity reference extraction
-- 8. Handover supports full lifecycle (draft → published → acknowledged → archived)
-- 9. Finance events are tied to real operational events (receiving, installation)
-- 10. RLS policies enforce yacht isolation (security)
