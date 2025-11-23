-- ============================================
-- CelesteOS V1 Agent Execution Layer
-- Action execution + confidence thresholds + role-aware recs
-- ============================================

-- ============================================
-- 1. ACTION_EXECUTIONS - Track executed actions
-- ============================================

CREATE TABLE IF NOT EXISTS action_executions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  suggestion_id UUID REFERENCES suggestion_log(id) ON DELETE SET NULL,

  -- What action was executed
  action_type TEXT NOT NULL,          -- 'create_work_order', 'run_diagnostic', 'schedule_inspection', etc.
  action_payload JSONB NOT NULL,      -- Final payload used to execute the action

  -- Result
  result_id UUID,                     -- e.g. work_orders.id after creation
  result_data JSONB,                  -- Any additional result info
  status TEXT NOT NULL DEFAULT 'pending',  -- 'pending' | 'completed' | 'failed'
  error_message TEXT,                 -- If status = 'failed'

  -- Timing
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ
);

-- Constraints
ALTER TABLE action_executions
  ADD CONSTRAINT action_executions_status_check
  CHECK (status IN ('pending', 'completed', 'failed'));

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_action_executions_yacht ON action_executions (yacht_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_action_executions_user ON action_executions (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_action_executions_suggestion ON action_executions (suggestion_id);
CREATE INDEX IF NOT EXISTS idx_action_executions_status ON action_executions (yacht_id, status) WHERE status = 'pending';

-- RLS
ALTER TABLE action_executions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own yacht action executions"
  ON action_executions FOR SELECT
  USING (yacht_id = public.get_user_yacht_id());

CREATE POLICY "Users can create action executions"
  ON action_executions FOR INSERT
  WITH CHECK (yacht_id = public.get_user_yacht_id());

CREATE POLICY "Service role full access"
  ON action_executions FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

GRANT SELECT, INSERT, UPDATE ON action_executions TO authenticated;
GRANT ALL ON action_executions TO service_role;

COMMENT ON TABLE action_executions IS 'Tracks executed agent actions (WO creation, diagnostics, etc.)';

-- ============================================
-- 2. USERS.ROLE - Add role column if missing
-- ============================================

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
    AND table_name = 'users'
    AND column_name = 'role'
  ) THEN
    ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'crew';
  END IF;
END $$;

-- Add constraint for valid roles
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.constraint_column_usage
    WHERE table_name = 'users' AND constraint_name = 'users_role_check'
  ) THEN
    ALTER TABLE users
      ADD CONSTRAINT users_role_check
      CHECK (role IN ('captain', 'chief_engineer', 'engineer', 'crew', 'management'));
  END IF;
EXCEPTION WHEN duplicate_object THEN
  NULL;
END $$;

COMMENT ON COLUMN users.role IS 'User role for role-aware recommendations: captain, chief_engineer, engineer, crew, management';

-- ============================================
-- 3. EXTEND SUGGESTION_LOG - Add feedback tracking
-- ============================================

-- Add feedback columns if they don't exist
ALTER TABLE suggestion_log
  ADD COLUMN IF NOT EXISTS feedback_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS action_execution_id UUID REFERENCES action_executions(id) ON DELETE SET NULL;

-- Update constraint for user_action_taken if needed
DO $$
BEGIN
  -- Drop old constraint if exists
  ALTER TABLE suggestion_log DROP CONSTRAINT IF EXISTS suggestion_log_action_check;
  -- Add proper constraint
  ALTER TABLE suggestion_log
    ADD CONSTRAINT suggestion_log_action_check
    CHECK (user_action_taken IS NULL OR user_action_taken IN ('accepted', 'ignored', 'modified'));
EXCEPTION WHEN undefined_table THEN
  NULL;
END $$;

CREATE INDEX IF NOT EXISTS idx_suggestion_log_feedback ON suggestion_log (yacht_id, user_action_taken) WHERE user_action_taken IS NOT NULL;

-- ============================================
-- 4. EXECUTE_ACTION RPC - Log action execution
-- ============================================

CREATE OR REPLACE FUNCTION execute_action(
  p_yacht_id UUID,
  p_user_id UUID,
  p_action_type TEXT,
  p_action_payload JSONB,
  p_suggestion_id UUID DEFAULT NULL
) RETURNS UUID AS $$
DECLARE
  v_id UUID;
BEGIN
  -- Validate action_type
  IF p_action_type NOT IN (
    'create_work_order',
    'run_diagnostic',
    'schedule_inspection',
    'configure_alert',
    'view_predictive_analysis',
    'create_handover_note',
    'log_symptom'
  ) THEN
    RAISE EXCEPTION 'Invalid action_type: %', p_action_type;
  END IF;

  -- Insert execution record
  INSERT INTO action_executions (
    yacht_id,
    user_id,
    action_type,
    action_payload,
    suggestion_id
  ) VALUES (
    p_yacht_id,
    p_user_id,
    p_action_type,
    p_action_payload,
    p_suggestion_id
  )
  RETURNING id INTO v_id;

  -- If there's a linked suggestion, update it
  IF p_suggestion_id IS NOT NULL THEN
    UPDATE suggestion_log
    SET action_execution_id = v_id,
        user_action_taken = 'accepted',
        feedback_at = now()
    WHERE id = p_suggestion_id;
  END IF;

  RETURN v_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION execute_action IS 'Logs an action execution and optionally links to suggestion_log';

-- ============================================
-- 5. COMPLETE_ACTION RPC - Mark action as done
-- ============================================

CREATE OR REPLACE FUNCTION complete_action(
  p_execution_id UUID,
  p_status TEXT,
  p_result_id UUID DEFAULT NULL,
  p_result_data JSONB DEFAULT NULL,
  p_error_message TEXT DEFAULT NULL
) RETURNS BOOLEAN AS $$
BEGIN
  IF p_status NOT IN ('completed', 'failed') THEN
    RAISE EXCEPTION 'Invalid status: %. Must be completed or failed.', p_status;
  END IF;

  UPDATE action_executions
  SET status = p_status,
      result_id = COALESCE(p_result_id, result_id),
      result_data = COALESCE(p_result_data, result_data),
      error_message = p_error_message,
      completed_at = now()
  WHERE id = p_execution_id;

  RETURN FOUND;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION complete_action IS 'Marks an action execution as completed or failed';

-- ============================================
-- 6. LOG_SUGGESTION_FEEDBACK RPC
-- ============================================

CREATE OR REPLACE FUNCTION log_suggestion_feedback(
  p_suggestion_id UUID,
  p_user_action_taken TEXT,
  p_action_execution_id UUID DEFAULT NULL
) RETURNS BOOLEAN AS $$
BEGIN
  IF p_user_action_taken NOT IN ('accepted', 'ignored', 'modified') THEN
    RAISE EXCEPTION 'Invalid user_action_taken: %', p_user_action_taken;
  END IF;

  UPDATE suggestion_log
  SET user_action_taken = p_user_action_taken,
      feedback_at = now(),
      action_execution_id = COALESCE(p_action_execution_id, action_execution_id)
  WHERE id = p_suggestion_id;

  RETURN FOUND;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION log_suggestion_feedback IS 'Records user feedback on a suggestion';

-- ============================================
-- 7. GET_USER_ROLE RPC - For API use
-- ============================================

CREATE OR REPLACE FUNCTION get_user_role(p_user_id UUID)
RETURNS TEXT AS $$
DECLARE
  v_role TEXT;
BEGIN
  SELECT COALESCE(role, 'crew') INTO v_role
  FROM users
  WHERE id = p_user_id;

  RETURN COALESCE(v_role, 'crew');
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

COMMENT ON FUNCTION get_user_role(UUID) IS 'Returns user role for role-aware recommendations';

-- ============================================
-- 8. GRANTS
-- ============================================

GRANT EXECUTE ON FUNCTION execute_action TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION complete_action TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION log_suggestion_feedback TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION get_user_role TO authenticated, service_role;
