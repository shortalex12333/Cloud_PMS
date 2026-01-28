-- Migration: Create pms_audit_log for tenant databases
-- =============================================================================
-- Purpose: Audit trail for all mutations in tenant DB
-- Required for: acknowledge_fault, update_fault, and all mutation actions
-- =============================================================================

-- Create pms_audit_log table (tenant-specific naming convention)
CREATE TABLE IF NOT EXISTS public.pms_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL,
    action TEXT NOT NULL,  -- e.g., 'acknowledge_fault', 'update_fault'
    entity_type TEXT NOT NULL,  -- e.g., 'fault', 'work_order', 'equipment'
    entity_id UUID NOT NULL,  -- ID of modified entity
    user_id UUID NOT NULL,
    old_values JSONB,  -- Previous state (for updates)
    new_values JSONB NOT NULL,  -- New state
    signature JSONB NOT NULL DEFAULT '{}'::jsonb,  -- {user_id, execution_id, timestamp, action}
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_pms_audit_log_yacht ON public.pms_audit_log(yacht_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_pms_audit_log_entity ON public.pms_audit_log(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_pms_audit_log_user ON public.pms_audit_log(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_pms_audit_log_action ON public.pms_audit_log(action, created_at DESC);

-- Enable RLS
ALTER TABLE public.pms_audit_log ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Users can only see audit logs for their yacht
CREATE POLICY "yacht_isolation_pms_audit_log" ON public.pms_audit_log
    FOR ALL
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()
        )
    );

-- Comment
COMMENT ON TABLE public.pms_audit_log IS 'Audit trail for all mutations - NON-NEGOTIABLE for accountability';
