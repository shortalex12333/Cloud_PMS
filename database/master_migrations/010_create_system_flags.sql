-- Migration: 010_create_system_flags.sql
-- Created: 2026-01-28
-- Purpose: System flags table for global incident mode and kill switches
--
-- Security invariants:
-- 1. Single row table (enforced by unique constraint on id=1)
-- 2. Only ADMIN users can modify (enforced at application layer)
-- 3. All changes are audited
-- 4. incident_mode=true disables: streaming, signed URLs, all writes
--
-- Usage:
--   SELECT incident_mode, disable_streaming, disable_signed_urls, disable_writes
--   FROM system_flags WHERE id = 1;

-- ============================================================================
-- CREATE TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS system_flags (
    -- Primary key (always 1 for singleton pattern)
    id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),

    -- Global incident mode (disables everything)
    incident_mode BOOLEAN NOT NULL DEFAULT FALSE,

    -- Granular controls (used when incident_mode is false)
    disable_streaming BOOLEAN NOT NULL DEFAULT FALSE,
    disable_signed_urls BOOLEAN NOT NULL DEFAULT FALSE,
    disable_writes BOOLEAN NOT NULL DEFAULT FALSE,

    -- Incident metadata
    incident_reason TEXT,
    incident_started_at TIMESTAMPTZ,
    incident_started_by UUID,  -- User who enabled incident mode

    -- Timestamps
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by UUID,  -- User who last updated

    -- Constraints
    CONSTRAINT system_flags_singleton CHECK (id = 1)
);

-- Insert default row if not exists
INSERT INTO system_flags (id, incident_mode, disable_streaming, disable_signed_urls, disable_writes)
VALUES (1, FALSE, FALSE, FALSE, FALSE)
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE system_flags IS 'Global system flags for incident mode and kill switches';
COMMENT ON COLUMN system_flags.incident_mode IS 'When true, disables streaming, signed URLs, and all writes globally';
COMMENT ON COLUMN system_flags.disable_streaming IS 'Disable streaming search (when incident_mode is false)';
COMMENT ON COLUMN system_flags.disable_signed_urls IS 'Disable signed URL generation (when incident_mode is false)';
COMMENT ON COLUMN system_flags.disable_writes IS 'Disable all MUTATE/SIGNED/ADMIN actions (when incident_mode is false)';
COMMENT ON COLUMN system_flags.incident_reason IS 'Human-readable reason for incident mode';
COMMENT ON COLUMN system_flags.incident_started_at IS 'When incident mode was enabled';
COMMENT ON COLUMN system_flags.incident_started_by IS 'User who enabled incident mode';

-- ============================================================================
-- INDEXES
-- ============================================================================

-- No additional indexes needed (singleton table)

-- ============================================================================
-- RPC FUNCTIONS
-- ============================================================================

-- Get system flags (cached at application layer)
CREATE OR REPLACE FUNCTION get_system_flags()
RETURNS TABLE (
    incident_mode BOOLEAN,
    disable_streaming BOOLEAN,
    disable_signed_urls BOOLEAN,
    disable_writes BOOLEAN,
    incident_reason TEXT,
    incident_started_at TIMESTAMPTZ
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT
        sf.incident_mode,
        sf.disable_streaming,
        sf.disable_signed_urls,
        sf.disable_writes,
        sf.incident_reason,
        sf.incident_started_at
    FROM system_flags sf
    WHERE sf.id = 1;
END;
$$;

-- Enable incident mode
CREATE OR REPLACE FUNCTION enable_incident_mode(
    p_user_id UUID,
    p_reason TEXT DEFAULT 'Security incident'
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    UPDATE system_flags
    SET
        incident_mode = TRUE,
        incident_reason = p_reason,
        incident_started_at = NOW(),
        incident_started_by = p_user_id,
        updated_at = NOW(),
        updated_by = p_user_id
    WHERE id = 1;

    RETURN TRUE;
END;
$$;

-- Disable incident mode
CREATE OR REPLACE FUNCTION disable_incident_mode(
    p_user_id UUID
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    UPDATE system_flags
    SET
        incident_mode = FALSE,
        incident_reason = NULL,
        incident_started_at = NULL,
        incident_started_by = NULL,
        updated_at = NOW(),
        updated_by = p_user_id
    WHERE id = 1;

    RETURN TRUE;
END;
$$;

-- Update individual flags (for granular control)
CREATE OR REPLACE FUNCTION update_system_flag(
    p_user_id UUID,
    p_flag_name TEXT,
    p_flag_value BOOLEAN
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- Validate flag name
    IF p_flag_name NOT IN ('disable_streaming', 'disable_signed_urls', 'disable_writes') THEN
        RAISE EXCEPTION 'Invalid flag name: %', p_flag_name;
    END IF;

    -- Update the specific flag
    EXECUTE format(
        'UPDATE system_flags SET %I = $1, updated_at = NOW(), updated_by = $2 WHERE id = 1',
        p_flag_name
    ) USING p_flag_value, p_user_id;

    RETURN TRUE;
END;
$$;

-- ============================================================================
-- AUDIT TRIGGER
-- ============================================================================

-- Create audit trigger for system_flags changes
CREATE OR REPLACE FUNCTION audit_system_flags_change()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO security_events (
        event_type,
        severity,
        user_id,
        details,
        created_at
    ) VALUES (
        'SYSTEM_FLAGS_CHANGED',
        CASE
            WHEN NEW.incident_mode = TRUE AND (OLD.incident_mode IS NULL OR OLD.incident_mode = FALSE) THEN 'CRITICAL'
            WHEN NEW.incident_mode = FALSE AND OLD.incident_mode = TRUE THEN 'HIGH'
            ELSE 'MEDIUM'
        END,
        NEW.updated_by,
        jsonb_build_object(
            'old_incident_mode', OLD.incident_mode,
            'new_incident_mode', NEW.incident_mode,
            'old_disable_streaming', OLD.disable_streaming,
            'new_disable_streaming', NEW.disable_streaming,
            'old_disable_signed_urls', OLD.disable_signed_urls,
            'new_disable_signed_urls', NEW.disable_signed_urls,
            'old_disable_writes', OLD.disable_writes,
            'new_disable_writes', NEW.disable_writes,
            'reason', NEW.incident_reason
        ),
        NOW()
    );

    RETURN NEW;
END;
$$;

-- Create trigger (only if security_events table exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'security_events') THEN
        DROP TRIGGER IF EXISTS system_flags_audit_trigger ON system_flags;
        CREATE TRIGGER system_flags_audit_trigger
            AFTER UPDATE ON system_flags
            FOR EACH ROW
            EXECUTE FUNCTION audit_system_flags_change();
    END IF;
END;
$$;

-- ============================================================================
-- RLS POLICIES
-- ============================================================================

-- Enable RLS
ALTER TABLE system_flags ENABLE ROW LEVEL SECURITY;

-- Only service role can read/modify system_flags
-- (All access goes through RPC functions which use SECURITY DEFINER)
CREATE POLICY "system_flags_service_only" ON system_flags
    FOR ALL
    USING (auth.role() = 'service_role');

-- ============================================================================
-- GRANTS
-- ============================================================================

-- Grant execute on RPC functions to authenticated users
-- (Authorization is handled at application layer)
GRANT EXECUTE ON FUNCTION get_system_flags() TO authenticated;
GRANT EXECUTE ON FUNCTION enable_incident_mode(UUID, TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION disable_incident_mode(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION update_system_flag(UUID, TEXT, BOOLEAN) TO authenticated;
