-- Situation Engine Tables
-- =======================
-- Tables required for situation detection and recommendation system

-- Action execution log
CREATE TABLE IF NOT EXISTS action_executions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id UUID NOT NULL,
  user_id UUID NOT NULL,
  action_name TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  entity_id UUID,
  params JSONB,
  result JSONB,
  success BOOLEAN NOT NULL,
  error_code TEXT,
  error_message TEXT,
  duration_ms INT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Symptom reports (for situation engine pattern detection)
CREATE TABLE IF NOT EXISTS symptom_reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id UUID NOT NULL,
  equipment_label TEXT NOT NULL,
  symptom_code TEXT NOT NULL,
  symptom_label TEXT NOT NULL,
  search_query_id UUID,
  reported_by UUID,
  source TEXT NOT NULL DEFAULT 'manual',
  resolved BOOLEAN DEFAULT FALSE,
  resolved_at TIMESTAMPTZ,
  resolved_by UUID,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Situation detections
CREATE TABLE IF NOT EXISTS situation_detections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id UUID NOT NULL,
  user_id UUID,
  situation_type TEXT NOT NULL,
  severity TEXT NOT NULL,
  label TEXT NOT NULL,
  context TEXT,
  evidence JSONB,
  recommendations JSONB,
  search_query_id UUID,
  acknowledged BOOLEAN DEFAULT FALSE,
  acknowledged_at TIMESTAMPTZ,
  acknowledged_by UUID,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Suggestion log (for learning)
CREATE TABLE IF NOT EXISTS suggestion_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id UUID NOT NULL,
  user_id UUID,
  query_text TEXT NOT NULL,
  intent TEXT,
  search_query_id UUID,
  situation_detected BOOLEAN DEFAULT FALSE,
  situation_type TEXT,
  suggested_actions JSONB,
  action_taken TEXT,
  action_taken_at TIMESTAMPTZ,
  feedback TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Predictive state (for high risk equipment detection)
CREATE TABLE IF NOT EXISTS predictive_state (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id UUID NOT NULL,
  equipment_id UUID NOT NULL,
  risk_score DECIMAL(3,2) NOT NULL DEFAULT 0,
  confidence DECIMAL(3,2) NOT NULL DEFAULT 0,
  failure_probability DECIMAL(3,2) DEFAULT 0,
  trend TEXT DEFAULT 'stable',
  anomalies JSONB DEFAULT '[]'::JSONB,
  failure_modes JSONB,
  recommended_actions JSONB,
  next_maintenance_due TIMESTAMPTZ,
  last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(equipment_id)
);

-- RLS policies
ALTER TABLE action_executions ENABLE ROW LEVEL SECURITY;
ALTER TABLE symptom_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE situation_detections ENABLE ROW LEVEL SECURITY;
ALTER TABLE suggestion_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE predictive_state ENABLE ROW LEVEL SECURITY;

-- Vessel isolation policies (allow access only to user's yacht data)
CREATE POLICY "vessel_isolation_action_executions" ON action_executions
  FOR ALL USING (yacht_id IN (SELECT yacht_id FROM user_profiles WHERE id = auth.uid()));

CREATE POLICY "vessel_isolation_symptom_reports" ON symptom_reports
  FOR ALL USING (yacht_id IN (SELECT yacht_id FROM user_profiles WHERE id = auth.uid()));

CREATE POLICY "vessel_isolation_situation_detections" ON situation_detections
  FOR ALL USING (yacht_id IN (SELECT yacht_id FROM user_profiles WHERE id = auth.uid()));

CREATE POLICY "vessel_isolation_suggestion_log" ON suggestion_log
  FOR ALL USING (yacht_id IN (SELECT yacht_id FROM user_profiles WHERE id = auth.uid()));

CREATE POLICY "vessel_isolation_predictive_state" ON predictive_state
  FOR ALL USING (yacht_id IN (SELECT yacht_id FROM user_profiles WHERE id = auth.uid()));

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_action_executions_yacht ON action_executions(yacht_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_symptom_reports_yacht ON symptom_reports(yacht_id, equipment_label, symptom_code);
CREATE INDEX IF NOT EXISTS idx_symptom_reports_recurrence ON symptom_reports(yacht_id, equipment_label, symptom_code, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_situation_detections_yacht ON situation_detections(yacht_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_suggestion_log_yacht ON suggestion_log(yacht_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_predictive_state_equipment ON predictive_state(equipment_id);
CREATE INDEX IF NOT EXISTS idx_predictive_state_risk ON predictive_state(yacht_id, risk_score DESC);

-- Function: Check symptom recurrence
CREATE OR REPLACE FUNCTION check_symptom_recurrence(
  p_yacht_id UUID,
  p_equipment_label TEXT,
  p_symptom_code TEXT,
  p_threshold_count INT DEFAULT 3,
  p_threshold_days INT DEFAULT 60
)
RETURNS TABLE (
  is_recurrent BOOLEAN,
  occurrence_count INT,
  span_days INT,
  open_count INT
)
LANGUAGE plpgsql AS $$
BEGIN
  RETURN QUERY
  WITH symptom_occurrences AS (
    SELECT
      sr.id,
      sr.created_at,
      sr.resolved
    FROM symptom_reports sr
    WHERE sr.yacht_id = p_yacht_id
      AND sr.equipment_label ILIKE '%' || p_equipment_label || '%'
      AND sr.symptom_code = p_symptom_code
      AND sr.created_at > NOW() - (p_threshold_days || ' days')::INTERVAL
    UNION ALL
    -- Also check pms_faults table for historical data
    SELECT
      f.id,
      f.detected_at AS created_at,
      (f.resolved_at IS NOT NULL) AS resolved
    FROM pms_faults f
    WHERE f.yacht_id = p_yacht_id
      AND (f.equipment_label ILIKE '%' || p_equipment_label || '%' OR f.title ILIKE '%' || p_equipment_label || '%')
      AND (f.fault_code = p_symptom_code OR f.title ILIKE '%' || p_symptom_code || '%')
      AND f.detected_at > NOW() - (p_threshold_days || ' days')::INTERVAL
  )
  SELECT
    COUNT(*) >= p_threshold_count AS is_recurrent,
    COUNT(*)::INT AS occurrence_count,
    COALESCE(EXTRACT(DAY FROM MAX(created_at) - MIN(created_at))::INT, 0) AS span_days,
    COUNT(*) FILTER (WHERE NOT resolved)::INT AS open_count
  FROM symptom_occurrences;
END;
$$;

-- Function: Log symptom from search
CREATE OR REPLACE FUNCTION log_symptom_from_search(
  p_yacht_id UUID,
  p_equipment_label TEXT,
  p_symptom_code TEXT,
  p_symptom_label TEXT,
  p_search_query_id UUID DEFAULT NULL,
  p_user_id UUID DEFAULT NULL
)
RETURNS UUID
LANGUAGE plpgsql AS $$
DECLARE
  v_id UUID;
BEGIN
  INSERT INTO symptom_reports (
    yacht_id,
    equipment_label,
    symptom_code,
    symptom_label,
    search_query_id,
    reported_by,
    source
  ) VALUES (
    p_yacht_id,
    p_equipment_label,
    p_symptom_code,
    p_symptom_label,
    p_search_query_id,
    p_user_id,
    'search'
  )
  RETURNING id INTO v_id;

  RETURN v_id;
END;
$$;

-- Function: Get equipment risk score
CREATE OR REPLACE FUNCTION get_equipment_risk(
  p_equipment_id UUID
)
RETURNS TABLE (
  risk_score DECIMAL(3,2),
  confidence DECIMAL(3,2),
  failure_probability DECIMAL(3,2),
  trend TEXT,
  anomalies JSONB
)
LANGUAGE plpgsql AS $$
BEGIN
  RETURN QUERY
  SELECT
    ps.risk_score,
    ps.confidence,
    ps.failure_probability,
    ps.trend,
    ps.anomalies
  FROM predictive_state ps
  WHERE ps.equipment_id = p_equipment_id;
END;
$$;

-- Grant execute permissions
GRANT EXECUTE ON FUNCTION check_symptom_recurrence TO authenticated;
GRANT EXECUTE ON FUNCTION log_symptom_from_search TO authenticated;
GRANT EXECUTE ON FUNCTION get_equipment_risk TO authenticated;
