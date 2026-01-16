-- ============================================================================
-- Migration: Create pms_worklist_tasks table
-- Description: Daily worklist tasks for crew members
-- Author: Claude
-- Date: 2026-01-16
-- ============================================================================

-- Create pms_worklist_tasks table
CREATE TABLE IF NOT EXISTS pms_worklist_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL,

    -- Task content
    description TEXT NOT NULL,
    instructions TEXT,
    priority VARCHAR(20) NOT NULL DEFAULT 'normal',
    -- Priority: low, normal, high, urgent

    -- Assignment
    assigned_to UUID,
    assigned_by UUID,
    assigned_at TIMESTAMPTZ,

    -- Schedule
    scheduled_date DATE,
    due_date DATE,
    estimated_duration_minutes INTEGER,

    -- Associations (optional)
    equipment_id UUID,
    work_order_id UUID,
    fault_id UUID,

    -- Status tracking
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    -- Status: pending, in_progress, completed, cancelled, deferred

    -- Completion
    completed_at TIMESTAMPTZ,
    completed_by UUID,
    completion_notes TEXT,
    actual_duration_minutes INTEGER,

    -- Progress (0-100)
    progress INTEGER DEFAULT 0,

    -- Metadata
    tags TEXT[],
    metadata JSONB DEFAULT '{}',

    -- Standard timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID NOT NULL,
    updated_at TIMESTAMPTZ,
    updated_by UUID,

    -- Soft delete
    deleted_at TIMESTAMPTZ,
    deleted_by UUID,
    deletion_reason TEXT,

    -- Foreign keys (optional associations)
    CONSTRAINT fk_pms_worklist_tasks_equipment
        FOREIGN KEY (equipment_id) REFERENCES pms_equipment(id) ON DELETE SET NULL,
    CONSTRAINT fk_pms_worklist_tasks_work_order
        FOREIGN KEY (work_order_id) REFERENCES pms_work_orders(id) ON DELETE SET NULL,
    CONSTRAINT fk_pms_worklist_tasks_fault
        FOREIGN KEY (fault_id) REFERENCES pms_faults(id) ON DELETE SET NULL,

    -- Check constraints
    CONSTRAINT chk_pms_worklist_tasks_priority
        CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
    CONSTRAINT chk_pms_worklist_tasks_status
        CHECK (status IN ('pending', 'in_progress', 'completed', 'cancelled', 'deferred')),
    CONSTRAINT chk_pms_worklist_tasks_progress
        CHECK (progress >= 0 AND progress <= 100)
);

-- Comment on table
COMMENT ON TABLE pms_worklist_tasks IS 'Daily worklist tasks for crew members with scheduling and progress tracking';

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_pms_worklist_tasks_yacht_id ON pms_worklist_tasks(yacht_id);
CREATE INDEX IF NOT EXISTS idx_pms_worklist_tasks_assigned_to ON pms_worklist_tasks(assigned_to) WHERE assigned_to IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_pms_worklist_tasks_status ON pms_worklist_tasks(status) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_pms_worklist_tasks_scheduled_date ON pms_worklist_tasks(scheduled_date) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_pms_worklist_tasks_due_date ON pms_worklist_tasks(due_date) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_pms_worklist_tasks_created_at ON pms_worklist_tasks(created_at DESC);

-- Enable Row Level Security
ALTER TABLE pms_worklist_tasks ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Service role bypass
CREATE POLICY service_role_bypass ON pms_worklist_tasks
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- RLS Policies for authenticated users
CREATE POLICY yacht_isolation_select ON pms_worklist_tasks
    FOR SELECT
    TO authenticated
    USING (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR EXISTS (
            SELECT 1 FROM user_accounts
            WHERE user_accounts.auth_user_id = auth.uid()
            AND user_accounts.yacht_id = pms_worklist_tasks.yacht_id
        )
    );

CREATE POLICY yacht_isolation_insert ON pms_worklist_tasks
    FOR INSERT
    TO authenticated
    WITH CHECK (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR EXISTS (
            SELECT 1 FROM user_accounts
            WHERE user_accounts.auth_user_id = auth.uid()
            AND user_accounts.yacht_id = pms_worklist_tasks.yacht_id
        )
    );

CREATE POLICY yacht_isolation_update ON pms_worklist_tasks
    FOR UPDATE
    TO authenticated
    USING (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR EXISTS (
            SELECT 1 FROM user_accounts
            WHERE user_accounts.auth_user_id = auth.uid()
            AND user_accounts.yacht_id = pms_worklist_tasks.yacht_id
        )
    );

CREATE POLICY yacht_isolation_delete ON pms_worklist_tasks
    FOR DELETE
    TO authenticated
    USING (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR EXISTS (
            SELECT 1 FROM user_accounts
            WHERE user_accounts.auth_user_id = auth.uid()
            AND user_accounts.yacht_id = pms_worklist_tasks.yacht_id
        )
    );

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_pms_worklist_tasks_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_pms_worklist_tasks_updated_at ON pms_worklist_tasks;
CREATE TRIGGER trg_pms_worklist_tasks_updated_at
    BEFORE UPDATE ON pms_worklist_tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_pms_worklist_tasks_updated_at();

-- Trigger to set completed_at when status changes to completed
CREATE OR REPLACE FUNCTION set_worklist_task_completed_at()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'completed' AND OLD.status != 'completed' THEN
        NEW.completed_at = NOW();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_set_worklist_task_completed ON pms_worklist_tasks;
CREATE TRIGGER trg_set_worklist_task_completed
    BEFORE UPDATE ON pms_worklist_tasks
    FOR EACH ROW
    EXECUTE FUNCTION set_worklist_task_completed_at();
