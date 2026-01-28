-- Migration: 011_create_audit_views.sql
-- Purpose: Create auditor-friendly views for compliance evidence extraction
-- SOC2: CC6, CC7, CC8 | ISO: A.9, A.12, A.16

-- ============================================================================
-- v_audit_actions_enriched
-- ============================================================================
-- Joins audit logs with memberships and roles for complete action context

CREATE OR REPLACE VIEW v_audit_actions_enriched AS
SELECT
    al.id,
    al.request_id,
    al.idempotency_key,
    al.user_id,
    al.yacht_id,
    al.action_name,
    al.outcome,
    al.entity_type,
    al.entity_id,
    al.payload_hash,
    al.created_at,
    -- Membership context
    m.status AS membership_status,
    m.role_requested,
    m.invited_by,
    m.approved_by,
    -- Role at time of action (if available)
    r.role AS actor_role,
    r.valid_from AS role_valid_from,
    r.valid_until AS role_valid_until,
    -- Fleet context
    fr.yacht_name,
    fr.is_frozen AS yacht_frozen_at_time
FROM pms_audit_log al
LEFT JOIN memberships m ON m.user_id = al.user_id AND m.yacht_id = al.yacht_id
LEFT JOIN auth_users_roles r ON r.user_id = al.user_id AND r.yacht_id = al.yacht_id AND r.is_active = TRUE
LEFT JOIN fleet_registry fr ON fr.yacht_id = al.yacht_id;

COMMENT ON VIEW v_audit_actions_enriched IS
'Enriched audit log with membership, role, and yacht context for compliance reporting';


-- ============================================================================
-- v_admin_changes_enriched
-- ============================================================================
-- Focused view on admin operations with actor/approver details

CREATE OR REPLACE VIEW v_admin_changes_enriched AS
SELECT
    se.id,
    se.event_type,
    se.user_id AS target_user_id,
    se.yacht_id,
    se.details->>'actor_id' AS actor_id,
    se.details->>'actor_role' AS actor_role,
    se.details->>'outcome' AS outcome,
    se.details->>'idempotency_key' AS idempotency_key,
    -- For invites/approvals
    se.details->>'inviter_id' AS inviter_id,
    se.details->>'approver_id' AS approver_id,
    se.details->>'membership_id' AS membership_id,
    -- For role changes
    se.details->>'old_role' AS old_role,
    se.details->>'new_role' AS new_role,
    -- For revocations
    se.details->>'reason' AS reason,
    -- For freezes
    se.details->>'freeze' AS freeze_action,
    -- 2-person rule check
    CASE
        WHEN se.event_type LIKE '%approve%'
             AND se.details->>'inviter_id' IS NOT NULL
             AND se.details->>'approver_id' IS NOT NULL
        THEN se.details->>'inviter_id' != se.details->>'approver_id'
        ELSE NULL
    END AS two_person_compliant,
    se.created_at,
    -- Fleet context
    fr.yacht_name
FROM security_events se
LEFT JOIN fleet_registry fr ON fr.yacht_id = se.yacht_id
WHERE se.event_type IN (
    'admin_invite_attempt',
    'admin_invite_success',
    'admin_invite_error',
    'admin_approve_attempt',
    'admin_approve_success',
    'admin_approve_denied_2person',
    'admin_approve_error',
    'admin_change_role_attempt',
    'admin_change_role_success',
    'admin_change_role_denied_self',
    'admin_change_role_error',
    'admin_revoke_attempt',
    'admin_revoke_success',
    'admin_revoke_error',
    'admin_freeze_attempt',
    'admin_freeze_success',
    'admin_unfreeze_success',
    'admin_freeze_error',
    'incident_mode_enable_attempt',
    'incident_mode_enabled',
    'incident_mode_disable_attempt',
    'incident_mode_disabled'
);

COMMENT ON VIEW v_admin_changes_enriched IS
'Admin operations (invites, approvals, role changes, revokes, freezes, incident mode) with 2-person compliance check';


-- ============================================================================
-- v_membership_transitions
-- ============================================================================
-- Tracks membership status changes over time

CREATE OR REPLACE VIEW v_membership_transitions AS
SELECT
    m.id AS membership_id,
    m.user_id,
    m.yacht_id,
    m.status,
    m.role_requested,
    m.invited_by,
    m.approved_by,
    m.notes,
    m.valid_until,
    m.created_at,
    m.updated_at,
    -- Join with fleet for yacht name
    fr.yacht_name,
    -- Compliance fields
    CASE
        WHEN m.role_requested IN ('captain', 'manager', 'chief_engineer')
             AND m.invited_by IS NOT NULL
             AND m.approved_by IS NOT NULL
        THEN m.invited_by != m.approved_by
        WHEN m.role_requested IN ('captain', 'manager', 'chief_engineer')
        THEN FALSE  -- Missing approver means not compliant
        ELSE TRUE   -- Non-privileged roles don't need 2-person
    END AS two_person_compliant
FROM memberships m
LEFT JOIN fleet_registry fr ON fr.yacht_id = m.yacht_id;

COMMENT ON VIEW v_membership_transitions IS
'Membership records with 2-person rule compliance status for privileged roles';


-- ============================================================================
-- v_incident_timeline
-- ============================================================================
-- Timeline of incident mode changes for incident response auditing

CREATE OR REPLACE VIEW v_incident_timeline AS
SELECT
    se.id,
    se.event_type,
    CASE
        WHEN se.event_type = 'incident_mode_enabled' THEN 'ENABLED'
        WHEN se.event_type = 'incident_mode_disabled' THEN 'DISABLED'
        ELSE 'ATTEMPT'
    END AS incident_action,
    se.details->>'actor_id' AS actor_id,
    se.details->>'reason' AS incident_reason,
    se.details->>'resolution_notes' AS resolution_notes,
    se.details->>'disable_streaming' AS disable_streaming,
    se.details->>'disable_signed_urls' AS disable_signed_urls,
    se.details->>'disable_writes' AS disable_writes,
    se.created_at,
    -- Calculate duration if disabled event follows enabled
    NULL::interval AS duration  -- Would need window function for actual duration
FROM security_events se
WHERE se.event_type IN (
    'incident_mode_enable_attempt',
    'incident_mode_enabled',
    'incident_mode_disable_attempt',
    'incident_mode_disabled'
)
ORDER BY se.created_at DESC;

COMMENT ON VIEW v_incident_timeline IS
'Incident mode enable/disable timeline for SOC2 CC7 and ISO A.16 compliance';


-- ============================================================================
-- INDEXES for typical compliance queries
-- ============================================================================

-- Index for filtering audits by yacht and time
CREATE INDEX IF NOT EXISTS idx_pms_audit_log_yacht_created
ON pms_audit_log(yacht_id, created_at);

-- Index for filtering audits by user and time
CREATE INDEX IF NOT EXISTS idx_pms_audit_log_user_created
ON pms_audit_log(user_id, created_at);

-- Index for filtering audits by action type
CREATE INDEX IF NOT EXISTS idx_pms_audit_log_action_created
ON pms_audit_log(action_name, created_at);

-- Index for security events by type and time
CREATE INDEX IF NOT EXISTS idx_security_events_type_created
ON security_events(event_type, created_at);

-- Index for security events by yacht
CREATE INDEX IF NOT EXISTS idx_security_events_yacht_created
ON security_events(yacht_id, created_at);

-- Index for memberships by yacht and status
CREATE INDEX IF NOT EXISTS idx_memberships_yacht_status
ON memberships(yacht_id, status);


-- ============================================================================
-- Helper functions for compliance queries
-- ============================================================================

-- Function to get audit summary for a yacht/period
CREATE OR REPLACE FUNCTION get_audit_summary(
    p_yacht_id TEXT,
    p_start_ts TIMESTAMPTZ,
    p_end_ts TIMESTAMPTZ
)
RETURNS TABLE(
    category TEXT,
    total_count BIGINT,
    allowed_count BIGINT,
    denied_count BIGINT,
    error_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        'router_actions'::TEXT AS category,
        COUNT(*)::BIGINT AS total_count,
        COUNT(*) FILTER (WHERE outcome = 'allowed')::BIGINT AS allowed_count,
        COUNT(*) FILTER (WHERE outcome = 'denied')::BIGINT AS denied_count,
        COUNT(*) FILTER (WHERE outcome = 'error')::BIGINT AS error_count
    FROM pms_audit_log
    WHERE yacht_id = p_yacht_id
      AND created_at >= p_start_ts
      AND created_at <= p_end_ts;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION get_audit_summary IS
'Returns audit summary counts for a yacht and time period';


-- Function to check 2-person rule compliance for a yacht
CREATE OR REPLACE FUNCTION check_two_person_compliance(p_yacht_id TEXT)
RETURNS TABLE(
    membership_id UUID,
    user_id UUID,
    role_requested TEXT,
    invited_by UUID,
    approved_by UUID,
    is_compliant BOOLEAN,
    violation_reason TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        m.id AS membership_id,
        m.user_id,
        m.role_requested,
        m.invited_by,
        m.approved_by,
        CASE
            WHEN m.role_requested NOT IN ('captain', 'manager', 'chief_engineer') THEN TRUE
            WHEN m.invited_by IS NULL THEN FALSE
            WHEN m.approved_by IS NULL THEN FALSE
            WHEN m.invited_by = m.approved_by THEN FALSE
            ELSE TRUE
        END AS is_compliant,
        CASE
            WHEN m.role_requested NOT IN ('captain', 'manager', 'chief_engineer') THEN NULL
            WHEN m.invited_by IS NULL THEN 'Missing inviter'
            WHEN m.approved_by IS NULL THEN 'Missing approver'
            WHEN m.invited_by = m.approved_by THEN 'Same person invited and approved'
            ELSE NULL
        END AS violation_reason
    FROM memberships m
    WHERE m.yacht_id = p_yacht_id
      AND m.status = 'ACTIVE'
      AND m.role_requested IN ('captain', 'manager', 'chief_engineer');
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION check_two_person_compliance IS
'Returns 2-person rule compliance status for privileged roles on a yacht';


-- ============================================================================
-- Grant permissions (adjust based on your role setup)
-- ============================================================================

-- Grant read access to authenticated users for their own yacht's audit data
-- (Actual grants depend on your RLS setup)

-- GRANT SELECT ON v_audit_actions_enriched TO authenticated;
-- GRANT SELECT ON v_admin_changes_enriched TO authenticated;
-- GRANT SELECT ON v_membership_transitions TO authenticated;
-- GRANT SELECT ON v_incident_timeline TO authenticated;
-- GRANT EXECUTE ON FUNCTION get_audit_summary TO authenticated;
-- GRANT EXECUTE ON FUNCTION check_two_person_compliance TO authenticated;
