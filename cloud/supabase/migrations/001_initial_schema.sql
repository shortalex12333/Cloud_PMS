-- CelesteOS Initial Schema Migration
-- Version: 1.0
-- Description: Core tables for yacht management, users, and authentication

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- =============================================================================
-- CORE: Yachts, Users, Authentication
-- =============================================================================

-- Yachts table
CREATE TABLE yachts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    imo TEXT,
    mmsi TEXT,
    flag_state TEXT,
    length_m NUMERIC,
    owner_ref TEXT,
    signature TEXT UNIQUE NOT NULL,
    nas_root_path TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'demo')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_yachts_signature ON yachts(signature);
CREATE INDEX idx_yachts_status ON yachts(status);

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('captain', 'chief_engineer', 'eto', 'deck', 'interior', 'manager', 'vendor')),
    auth_provider TEXT NOT NULL DEFAULT 'password' CHECK (auth_provider IN ('password', 'oauth', 'sso')),
    password_hash TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_yacht_id ON users(yacht_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_active ON users(is_active);

-- User tokens table
CREATE TABLE user_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL,
    token_type TEXT NOT NULL CHECK (token_type IN ('api', 'device', 'refresh')),
    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_user_tokens_user_id ON user_tokens(user_id);
CREATE INDEX idx_user_tokens_yacht_id ON user_tokens(yacht_id);
CREATE INDEX idx_user_tokens_type ON user_tokens(token_type);

-- Yacht signatures table (optional, can be merged with yachts)
CREATE TABLE yacht_signatures (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
    signature TEXT UNIQUE NOT NULL,
    public_key TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_yacht_signatures_yacht_id ON yacht_signatures(yacht_id);

-- =============================================================================
-- PMS: Equipment, Work Orders, Faults
-- =============================================================================

-- Equipment table
CREATE TABLE equipment (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
    parent_id UUID REFERENCES equipment(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    code TEXT,
    description TEXT,
    location TEXT,
    manufacturer TEXT,
    model TEXT,
    serial_number TEXT,
    installed_date DATE,
    criticality TEXT CHECK (criticality IN ('low', 'medium', 'high')),
    system_type TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_equipment_yacht_id ON equipment(yacht_id);
CREATE INDEX idx_equipment_parent_id ON equipment(parent_id);
CREATE INDEX idx_equipment_system_type ON equipment(system_type);
CREATE INDEX idx_equipment_criticality ON equipment(criticality);

-- Work orders table
CREATE TABLE work_orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
    equipment_id UUID REFERENCES equipment(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    description TEXT,
    type TEXT NOT NULL CHECK (type IN ('scheduled', 'corrective', 'unplanned')),
    priority TEXT NOT NULL DEFAULT 'routine' CHECK (priority IN ('routine', 'important', 'critical')),
    status TEXT NOT NULL DEFAULT 'planned' CHECK (status IN ('planned', 'in_progress', 'completed', 'deferred', 'cancelled')),
    due_date DATE,
    due_hours INTEGER,
    last_completed_date DATE,
    last_completed_hours INTEGER,
    frequency JSONB,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_work_orders_yacht_id ON work_orders(yacht_id);
CREATE INDEX idx_work_orders_equipment_id ON work_orders(equipment_id);
CREATE INDEX idx_work_orders_status ON work_orders(status);
CREATE INDEX idx_work_orders_priority ON work_orders(priority);

-- Work order history table
CREATE TABLE work_order_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
    work_order_id UUID NOT NULL REFERENCES work_orders(id) ON DELETE CASCADE,
    equipment_id UUID REFERENCES equipment(id) ON DELETE SET NULL,
    completed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    completed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    notes TEXT,
    hours_logged INTEGER,
    status_on_completion TEXT,
    parts_used JSONB,
    documents_used JSONB,
    faults_related JSONB,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_work_order_history_yacht_id ON work_order_history(yacht_id);
CREATE INDEX idx_work_order_history_work_order_id ON work_order_history(work_order_id);
CREATE INDEX idx_work_order_history_equipment_id ON work_order_history(equipment_id);
CREATE INDEX idx_work_order_history_completed_at ON work_order_history(completed_at);

-- Faults table
CREATE TABLE faults (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
    equipment_id UUID REFERENCES equipment(id) ON DELETE SET NULL,
    fault_code TEXT,
    title TEXT NOT NULL,
    description TEXT,
    severity TEXT NOT NULL DEFAULT 'low' CHECK (severity IN ('low', 'medium', 'high')),
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    resolved_by UUID REFERENCES users(id) ON DELETE SET NULL,
    work_order_id UUID REFERENCES work_orders(id) ON DELETE SET NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_faults_yacht_id ON faults(yacht_id);
CREATE INDEX idx_faults_equipment_id ON faults(equipment_id);
CREATE INDEX idx_faults_fault_code ON faults(fault_code);
CREATE INDEX idx_faults_severity ON faults(severity);
CREATE INDEX idx_faults_detected_at ON faults(detected_at);

-- =============================================================================
-- INVENTORY: Parts, Stock, Suppliers
-- =============================================================================

-- Parts table
CREATE TABLE parts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    part_number TEXT,
    manufacturer TEXT,
    description TEXT,
    category TEXT,
    model_compatibility JSONB,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_parts_yacht_id ON parts(yacht_id);
CREATE INDEX idx_parts_part_number ON parts(part_number);
CREATE INDEX idx_parts_category ON parts(category);

-- Stock locations table
CREATE TABLE stock_locations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    deck TEXT,
    position TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_stock_locations_yacht_id ON stock_locations(yacht_id);

-- Stock levels table
CREATE TABLE stock_levels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
    part_id UUID NOT NULL REFERENCES parts(id) ON DELETE CASCADE,
    location_id UUID REFERENCES stock_locations(id) ON DELETE SET NULL,
    quantity INTEGER NOT NULL DEFAULT 0,
    min_quantity INTEGER NOT NULL DEFAULT 0,
    max_quantity INTEGER,
    reorder_quantity INTEGER,
    last_counted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_stock_levels_yacht_id ON stock_levels(yacht_id);
CREATE INDEX idx_stock_levels_part_id ON stock_levels(part_id);
CREATE INDEX idx_stock_levels_location_id ON stock_levels(location_id);

-- Suppliers table
CREATE TABLE suppliers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    contact_name TEXT,
    email TEXT,
    phone TEXT,
    address JSONB,
    preferred BOOLEAN NOT NULL DEFAULT FALSE,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_suppliers_yacht_id ON suppliers(yacht_id);

-- Purchase orders table
CREATE TABLE purchase_orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
    supplier_id UUID REFERENCES suppliers(id) ON DELETE SET NULL,
    po_number TEXT,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'sent', 'partially_received', 'closed')),
    ordered_at TIMESTAMPTZ,
    received_at TIMESTAMPTZ,
    currency TEXT DEFAULT 'USD',
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_purchase_orders_yacht_id ON purchase_orders(yacht_id);
CREATE INDEX idx_purchase_orders_supplier_id ON purchase_orders(supplier_id);
CREATE INDEX idx_purchase_orders_status ON purchase_orders(status);

-- Purchase order lines table
CREATE TABLE purchase_order_lines (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
    purchase_order_id UUID NOT NULL REFERENCES purchase_orders(id) ON DELETE CASCADE,
    part_id UUID REFERENCES parts(id) ON DELETE SET NULL,
    description TEXT,
    quantity_ordered INTEGER NOT NULL,
    quantity_received INTEGER NOT NULL DEFAULT 0,
    unit_price NUMERIC,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_purchase_order_lines_yacht_id ON purchase_order_lines(yacht_id);
CREATE INDEX idx_purchase_order_lines_po_id ON purchase_order_lines(purchase_order_id);
CREATE INDEX idx_purchase_order_lines_part_id ON purchase_order_lines(part_id);

-- =============================================================================
-- COMPLIANCE: Hours of Rest
-- =============================================================================

-- Hours of rest records table
CREATE TABLE hours_of_rest_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    hours_worked NUMERIC(5,2) NOT NULL,
    hours_of_rest NUMERIC(5,2) NOT NULL,
    violations BOOLEAN NOT NULL DEFAULT FALSE,
    notes TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_hours_of_rest_yacht_id ON hours_of_rest_records(yacht_id);
CREATE INDEX idx_hours_of_rest_user_id ON hours_of_rest_records(user_id);
CREATE INDEX idx_hours_of_rest_date ON hours_of_rest_records(date);

-- =============================================================================
-- HANDOVER: Drafts, Items, Exports
-- =============================================================================

-- Handover drafts table
CREATE TABLE handover_drafts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
    period_start DATE,
    period_end DATE,
    title TEXT NOT NULL,
    description TEXT,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'finalised')),
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_handover_drafts_yacht_id ON handover_drafts(yacht_id);
CREATE INDEX idx_handover_drafts_status ON handover_drafts(status);
CREATE INDEX idx_handover_drafts_period ON handover_drafts(period_start, period_end);

-- Handover items table
CREATE TABLE handover_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
    handover_id UUID NOT NULL REFERENCES handover_drafts(id) ON DELETE CASCADE,
    source_type TEXT NOT NULL CHECK (source_type IN ('work_order', 'fault', 'doc_chunk', 'note', 'part')),
    source_id UUID,
    summary TEXT,
    detail TEXT,
    importance TEXT NOT NULL DEFAULT 'normal' CHECK (importance IN ('low', 'normal', 'high')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_handover_items_yacht_id ON handover_items(yacht_id);
CREATE INDEX idx_handover_items_handover_id ON handover_items(handover_id);
CREATE INDEX idx_handover_items_source_type ON handover_items(source_type);

-- Handover exports table
CREATE TABLE handover_exports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
    handover_id UUID NOT NULL REFERENCES handover_drafts(id) ON DELETE CASCADE,
    format TEXT NOT NULL CHECK (format IN ('pdf', 'html')),
    storage_path TEXT NOT NULL,
    exported_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    exported_by UUID REFERENCES users(id) ON DELETE SET NULL,
    metadata JSONB
);

CREATE INDEX idx_handover_exports_yacht_id ON handover_exports(yacht_id);
CREATE INDEX idx_handover_exports_handover_id ON handover_exports(handover_id);

-- =============================================================================
-- ANALYTICS: Search Queries, Event Log
-- =============================================================================

-- Search queries table (for analytics and predictive patterns)
CREATE TABLE search_queries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    query_text TEXT NOT NULL,
    interpreted_intent TEXT,
    entities JSONB,
    latency_ms INTEGER,
    success BOOLEAN,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_search_queries_yacht_id ON search_queries(yacht_id);
CREATE INDEX idx_search_queries_user_id ON search_queries(user_id);
CREATE INDEX idx_search_queries_created_at ON search_queries(created_at);

-- Event log table (general-purpose audit log)
CREATE TABLE event_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL,
    entity_type TEXT,
    entity_id UUID,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_event_log_yacht_id ON event_log(yacht_id);
CREATE INDEX idx_event_log_user_id ON event_log(user_id);
CREATE INDEX idx_event_log_event_type ON event_log(event_type);
CREATE INDEX idx_event_log_created_at ON event_log(created_at);

-- =============================================================================
-- TRIGGERS: Auto-update timestamps
-- =============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to all tables with updated_at column
CREATE TRIGGER update_yachts_updated_at BEFORE UPDATE ON yachts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_equipment_updated_at BEFORE UPDATE ON equipment
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_work_orders_updated_at BEFORE UPDATE ON work_orders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_parts_updated_at BEFORE UPDATE ON parts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_stock_locations_updated_at BEFORE UPDATE ON stock_locations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_stock_levels_updated_at BEFORE UPDATE ON stock_levels
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_suppliers_updated_at BEFORE UPDATE ON suppliers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_purchase_orders_updated_at BEFORE UPDATE ON purchase_orders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_handover_drafts_updated_at BEFORE UPDATE ON handover_drafts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- ROW LEVEL SECURITY (RLS)
-- =============================================================================

-- Enable RLS on all tables
ALTER TABLE yachts ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE equipment ENABLE ROW LEVEL SECURITY;
ALTER TABLE work_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE work_order_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE faults ENABLE ROW LEVEL SECURITY;
ALTER TABLE parts ENABLE ROW LEVEL SECURITY;
ALTER TABLE stock_levels ENABLE ROW LEVEL SECURITY;
ALTER TABLE handover_drafts ENABLE ROW LEVEL SECURITY;
ALTER TABLE handover_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE search_queries ENABLE ROW LEVEL SECURITY;
ALTER TABLE event_log ENABLE ROW LEVEL SECURITY;

-- Example RLS policy (yacht isolation)
CREATE POLICY yacht_isolation_policy ON yachts
    FOR ALL
    USING (id = current_setting('app.current_yacht_id', true)::UUID);

-- Note: Additional RLS policies should be created per table
-- based on specific access requirements

-- =============================================================================
-- COMMENTS
-- =============================================================================

COMMENT ON TABLE yachts IS 'Yacht registry - each yacht gets isolated environment';
COMMENT ON TABLE users IS 'Crew and management users';
COMMENT ON TABLE equipment IS 'Equipment hierarchy with parent/child relationships';
COMMENT ON TABLE work_orders IS 'Maintenance tasks - scheduled and corrective';
COMMENT ON TABLE work_order_history IS 'Completed work order executions with notes';
COMMENT ON TABLE faults IS 'Fault events and codes';
COMMENT ON TABLE parts IS 'Spare parts master list';
COMMENT ON TABLE stock_levels IS 'Current inventory per location';
COMMENT ON TABLE handover_drafts IS 'Handover documents in progress';
COMMENT ON TABLE handover_items IS 'Individual items in a handover';
COMMENT ON TABLE search_queries IS 'Search analytics for predictive patterns';
COMMENT ON TABLE event_log IS 'Audit trail of all system events';
