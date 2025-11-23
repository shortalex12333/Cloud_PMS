-- Schema Reference for Predictive Maintenance Engine (Worker 7)
-- These tables ALREADY EXIST in Supabase - this file is for reference only
-- Based on actual information_schema.columns from Supabase

-- ============================================
-- TABLE: predictive_state
-- Stores computed risk scores for each equipment
-- ============================================
CREATE TABLE IF NOT EXISTS predictive_state (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL,
    equipment_id UUID NOT NULL,
    risk_score NUMERIC NOT NULL,           -- 0.0 to 1.0 risk value
    confidence NUMERIC,                     -- 0.0 to 1.0 confidence level
    contributing_factors JSONB,             -- JSON with signal breakdown
    last_calculated_at TIMESTAMPTZ,         -- When risk was computed
    metadata JSONB,                         -- Additional data
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_yacht_equipment UNIQUE (yacht_id, equipment_id)
);

-- ============================================
-- TABLE: predictive_insights
-- Stores generated recommendations/alerts
-- ============================================
CREATE TABLE IF NOT EXISTS predictive_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL,
    equipment_id UUID,
    insight_type TEXT,                      -- e.g., 'risk_alert', 'recommendation'
    title TEXT,                             -- Short title
    description TEXT,                       -- Detailed description
    recommendation TEXT,                    -- Suggested action
    severity TEXT,                          -- 'low', 'medium', 'high', 'critical'
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_by UUID,
    acknowledged_at TIMESTAMPTZ,
    metadata JSONB,                         -- Contributing factors JSON
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- TABLE: notes (existing - used for crew signals)
-- ============================================
-- Already exists with columns:
-- id, yacht_id, equipment_id, work_order_id, fault_id, text, note_type,
-- created_by, attachments, metadata, created_at, updated_at

-- ============================================
-- INDEXES (add if not exists for performance)
-- ============================================
CREATE INDEX IF NOT EXISTS idx_predictive_state_yacht ON predictive_state(yacht_id);
CREATE INDEX IF NOT EXISTS idx_predictive_state_equipment ON predictive_state(equipment_id);
CREATE INDEX IF NOT EXISTS idx_predictive_state_risk ON predictive_state(risk_score DESC);
CREATE INDEX IF NOT EXISTS idx_predictive_insights_yacht ON predictive_insights(yacht_id);
CREATE INDEX IF NOT EXISTS idx_predictive_insights_severity ON predictive_insights(severity);
CREATE INDEX IF NOT EXISTS idx_predictive_insights_unack ON predictive_insights(acknowledged) WHERE acknowledged = FALSE;

-- ============================================
-- WORKFLOW SQL QUERIES REFERENCE
-- ============================================

-- Query 1: Get Equipment
-- SELECT id, yacht_id, name, system_type, manufacturer, criticality
-- FROM equipment WHERE yacht_id = $1;

-- Query 2: Get Fault Stats (90 days)
-- SELECT equipment_id, COUNT(*) as fault_count, MAX(detected_at) as last_fault
-- FROM faults WHERE yacht_id = $1 AND detected_at > NOW() - INTERVAL '90 days'
-- GROUP BY equipment_id;

-- Query 3: Get Work Order Stats (90 days)
-- SELECT equipment_id,
--        COUNT(*) as wo_count,
--        COUNT(*) FILTER (WHERE due_date < CURRENT_DATE AND status NOT IN ('completed', 'cancelled')) as overdue_count,
--        COUNT(*) FILTER (WHERE type = 'corrective') as corrective_count
-- FROM work_orders WHERE yacht_id = $1 AND created_at > NOW() - INTERVAL '90 days'
-- GROUP BY equipment_id;

-- Query 4: Get Notes Stats (90 days)
-- SELECT equipment_id, COUNT(*) as note_count
-- FROM notes WHERE yacht_id = $1 AND equipment_id IS NOT NULL AND created_at > NOW() - INTERVAL '90 days'
-- GROUP BY equipment_id;

-- Query 5: Upsert predictive_state
-- INSERT INTO predictive_state (yacht_id, equipment_id, risk_score, confidence, contributing_factors, last_calculated_at, updated_at)
-- VALUES ($1, $2, $3, $4, $5::jsonb, $6, NOW())
-- ON CONFLICT (yacht_id, equipment_id) DO UPDATE SET
--   risk_score = EXCLUDED.risk_score,
--   confidence = EXCLUDED.confidence,
--   contributing_factors = EXCLUDED.contributing_factors,
--   last_calculated_at = EXCLUDED.last_calculated_at,
--   updated_at = NOW();

-- Query 6: Insert predictive_insights
-- INSERT INTO predictive_insights (yacht_id, equipment_id, insight_type, title, description, recommendation, severity, metadata)
-- VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb);
