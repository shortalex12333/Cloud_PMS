-- =============================================
-- PREDICTIVE ENGINE TABLES
-- Run this in Supabase SQL Editor FIRST
-- =============================================

-- Table: predictive_state
-- Stores risk scores for each equipment
CREATE TABLE IF NOT EXISTS predictive_state (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL,
    equipment_id UUID NOT NULL,
    equipment_name TEXT,
    risk_score NUMERIC(5,4) NOT NULL CHECK (risk_score >= 0 AND risk_score <= 1),
    trend VARCHAR(1) NOT NULL DEFAULT '→' CHECK (trend IN ('↑', '↓', '→')),
    fault_signal NUMERIC(5,4) DEFAULT 0,
    work_order_signal NUMERIC(5,4) DEFAULT 0,
    crew_signal NUMERIC(5,4) DEFAULT 0,
    part_signal NUMERIC(5,4) DEFAULT 0,
    global_signal NUMERIC(5,4) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_yacht_equipment UNIQUE (yacht_id, equipment_id)
);

-- Table: predictive_insights
-- Stores human-readable insights and recommendations
CREATE TABLE IF NOT EXISTS predictive_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL,
    equipment_id UUID,
    equipment_name TEXT,
    insight_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    summary TEXT NOT NULL,
    explanation TEXT,
    recommended_action TEXT,
    contributing_signals JSONB DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_predictive_state_yacht ON predictive_state(yacht_id);
CREATE INDEX IF NOT EXISTS idx_predictive_state_risk ON predictive_state(risk_score DESC);
CREATE INDEX IF NOT EXISTS idx_predictive_insights_yacht ON predictive_insights(yacht_id);
CREATE INDEX IF NOT EXISTS idx_predictive_insights_severity ON predictive_insights(severity);

-- Enable RLS (optional - enable if you have yacht isolation)
-- ALTER TABLE predictive_state ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE predictive_insights ENABLE ROW LEVEL SECURITY;

-- Grant access to service role
GRANT ALL ON predictive_state TO service_role;
GRANT ALL ON predictive_insights TO service_role;
