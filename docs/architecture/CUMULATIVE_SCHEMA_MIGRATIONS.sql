-- ============================================================================
-- CUMULATIVE SCHEMA MIGRATIONS
-- Entity Lens Architecture → Production DB Alignment
-- ============================================================================
--
-- PURPOSE:
-- This file grows with each Entity Lens we build. Instead of documenting
-- schema gaps, we create the actual SQL that fixes them. This becomes the
-- implementation roadmap for Phase 2.
--
-- WORKFLOW:
-- 1. Build Entity Lens (e.g., Fault Lens, Inventory Lens)
-- 2. Identify gaps between lens requirements and production DB
-- 3. Add ALTER TABLE / CREATE TABLE / CREATE INDEX statements here
-- 4. Run this file in Phase 2 to evolve the schema
--
-- PRINCIPLES:
-- - Production DB is source of truth (verified via db_truth_snapshot.md)
-- - Migrations are hints; this file corrects to actual needs
-- - Each section maps to a specific Entity Lens
-- - Comments explain WHY each change is needed (user outcome, not feature)
--
-- LAST UPDATED: 2026-01-24
-- ============================================================================

-- ============================================================================
-- SECTION 1: FAULT LENS REQUIREMENTS
-- Source: /docs/architecture/entity_lenses/fault_lens_v1.md
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1.1 Add `detected_by` to pms_faults
-- ----------------------------------------------------------------------------
-- USER OUTCOME: Crew needs to know WHO originally reported a fault, not just
-- who created the database record. This matters for follow-up questions
-- ("Who saw this first?") and accountability.
--
-- CURRENT STATE: pms_faults has no `detected_by` column
-- WORKAROUND: Using `created_by` from pms_audit_log, but this is indirect
-- BLOCKER: Fault Lens v1 flagged as BLOCKER 1
-- ----------------------------------------------------------------------------

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'pms_faults'
        AND column_name = 'detected_by'
    ) THEN
        ALTER TABLE pms_faults
        ADD COLUMN detected_by UUID REFERENCES auth.users(id);

        COMMENT ON COLUMN pms_faults.detected_by IS
            'User who originally detected/reported this fault (may differ from created_by in audit log)';

        -- Backfill existing rows: set detected_by = first audit log entry for this fault
        UPDATE pms_faults f
        SET detected_by = (
            SELECT user_id
            FROM pms_audit_log
            WHERE entity_type = 'fault'
            AND entity_id = f.id
            ORDER BY created_at ASC
            LIMIT 1
        )
        WHERE detected_by IS NULL;
    END IF;
END $$;

-- ----------------------------------------------------------------------------
-- 1.2 Add index on pms_faults.detected_by
-- ----------------------------------------------------------------------------
-- USER OUTCOME: When crew asks "What faults did I report?" or when generating
-- reports of crew activity, this index speeds up queries.
-- ----------------------------------------------------------------------------

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pms_faults_detected_by
ON pms_faults(detected_by)
WHERE deleted_at IS NULL;

-- ----------------------------------------------------------------------------
-- 1.3 Verify signature column exists in pms_audit_log (already exists)
-- ----------------------------------------------------------------------------
-- USER OUTCOME: Archive actions require Captain/HoD signature. The signature
-- data (digital signature, timestamp, role verification) must be stored.
--
-- CURRENT STATE: pms_audit_log.signature exists ✅ (JSONB column)
-- NO ACTION NEEDED - just documenting for clarity
-- ----------------------------------------------------------------------------

COMMENT ON COLUMN pms_audit_log.signature IS
    'Digital signature data for high-risk actions (archive, delete, approve).
    Format: {signature_data: base64, signed_by: uuid, signed_at: timestamp, role: text, device_id: text}';

-- ----------------------------------------------------------------------------
-- 1.4 Action metadata lives in Python code (NOT database)
-- ----------------------------------------------------------------------------
-- USER OUTCOME: Frontend needs to know which actions require signature,
-- mutation tier, and allowed roles.
--
-- IMPLEMENTATION: Action registry exists at apps/api/actions/action_registry.py
-- This is a Python singleton loaded at startup, not a database table.
--
-- WHY NOT DB: Action metadata changes frequently during development. Python
-- code is easier to version control, test, and deploy than DB migrations.
--
-- Backend serves action metadata via API response. Frontend renders what
-- backend says (no hardcoded action lists).
--
-- NO MIGRATION NEEDED - registry already exists in code.
-- ----------------------------------------------------------------------------

-- ----------------------------------------------------------------------------
-- 1.5 Ensure fault_severity enum has correct values
-- ----------------------------------------------------------------------------
-- USER OUTCOME: Fault severity must match what crew actually uses:
-- low, medium, high, critical (not "urgent", "normal", etc.)
--
-- CURRENT STATE: Production has fault_severity enum ✅
-- VERIFY: Enum values match Fault Lens spec
-- ----------------------------------------------------------------------------

DO $$
BEGIN
    -- Check if enum exists, create if not
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'fault_severity') THEN
        CREATE TYPE fault_severity AS ENUM ('low', 'medium', 'high', 'critical');
    ELSE
        -- Verify enum values (if wrong, would need to recreate - see commented section)
        -- For now, just document expected values
        COMMENT ON TYPE fault_severity IS 'Fault severity levels: low, medium, high, critical';
    END IF;
END $$;

-- ----------------------------------------------------------------------------
-- 1.6 Ensure fault status CHECK constraint has correct values
-- ----------------------------------------------------------------------------
-- USER OUTCOME: Fault workflow must match crew mental model:
-- open → investigating → resolved → closed (not "pending", "in-progress", etc.)
--
-- CURRENT STATE: pms_faults.status is TEXT with CHECK constraint
-- VERIFY: Constraint allows: open, investigating, resolved, closed
-- ----------------------------------------------------------------------------

-- Drop old constraint if exists (name may vary)
DO $$
DECLARE
    constraint_name TEXT;
BEGIN
    SELECT conname INTO constraint_name
    FROM pg_constraint
    WHERE conrelid = 'pms_faults'::regclass
    AND contype = 'c'
    AND pg_get_constraintdef(oid) LIKE '%status%'
    LIMIT 1;

    IF constraint_name IS NOT NULL THEN
        EXECUTE format('ALTER TABLE pms_faults DROP CONSTRAINT IF EXISTS %I', constraint_name);
    END IF;
END $$;

-- Add correct constraint
ALTER TABLE pms_faults
ADD CONSTRAINT chk_pms_faults_status
CHECK (status IN ('open', 'investigating', 'resolved', 'closed'));

-- ----------------------------------------------------------------------------
-- 1.7 REMOVED: Critical Fault index
-- ----------------------------------------------------------------------------
-- REMOVED: "Critical Faults dashboard" concept doesn't exist.
-- Celeste has no dashboards, no ambient UI.
-- Severity is backend signal only (SLA timers, notifications).
-- No UI queries for "critical faults".
-- ----------------------------------------------------------------------------

-- ----------------------------------------------------------------------------
-- 1.8 DOCTRINE: Faults are NEVER deleted
-- ----------------------------------------------------------------------------
-- USER OUTCOME: Fault history must be preserved for recurrence analysis,
-- audit compliance, and pattern detection.
--
-- RULE: deleted_at, deleted_by, deletion_reason columns on pms_faults
-- exist in schema but should NEVER be populated.
--
-- NO archive_fault action exists.
-- Faults can only be: open → investigating → resolved → closed
-- They cannot be deleted or archived.
-- ----------------------------------------------------------------------------

COMMENT ON COLUMN pms_faults.deleted_at IS
    'DEPRECATED: This column exists but should NEVER be populated. Faults must be preserved for history. Use status=closed instead.';

COMMENT ON COLUMN pms_faults.deleted_by IS
    'DEPRECATED: See deleted_at comment.';

COMMENT ON COLUMN pms_faults.deletion_reason IS
    'DEPRECATED: See deleted_at comment.';

-- ----------------------------------------------------------------------------
-- 1.9 Add index on pms_faults for fault history queries
-- ----------------------------------------------------------------------------
-- USER OUTCOME: When user queries "fault history {equipment}", need fast
-- fetch of all faults for that equipment ordered by detection date.
-- ----------------------------------------------------------------------------

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pms_faults_equipment_history
ON pms_faults(equipment_id, detected_at DESC);

-- ============================================================================
-- SECTION 2: INVENTORY LENS REQUIREMENTS
-- Source: /docs/architecture/entity_lenses/inventory_item_lens_v2.md
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 2.1 Add soft delete columns to pms_parts
-- ----------------------------------------------------------------------------
-- USER OUTCOME: Crew needs to archive obsolete parts without losing historical
-- data. When a part is no longer used (equipment decommissioned, OEM changed
-- spec), we need 30-day undo window before permanent deletion.
--
-- LENS REQUIREMENT: Inventory Lens Section E.6 - archive_part action
-- CURRENT STATE: pms_parts has NO soft delete columns (unlike pms_faults,
-- pms_shopping_list_items, pms_work_orders which already have soft delete)
-- ----------------------------------------------------------------------------

DO $$
BEGIN
    -- Add soft delete columns if they don't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'pms_parts'
        AND column_name = 'deleted_at'
    ) THEN
        ALTER TABLE pms_parts
        ADD COLUMN deleted_at TIMESTAMPTZ,
        ADD COLUMN deleted_by UUID REFERENCES auth.users(id),
        ADD COLUMN deletion_reason TEXT;

        COMMENT ON COLUMN pms_parts.deleted_at IS
            'Soft delete timestamp. Part remains in DB for 30 days (undo window).';

        COMMENT ON COLUMN pms_parts.deleted_by IS
            'User who archived this part (Captain/HoD/Purser with signature).';

        COMMENT ON COLUMN pms_parts.deletion_reason IS
            'Reason for archiving (equipment decommissioned, obsolete, etc.)';
    END IF;
END $$;

-- ----------------------------------------------------------------------------
-- 2.2 Add trigger to prevent hard delete on pms_parts
-- ----------------------------------------------------------------------------
-- USER OUTCOME: Prevent accidental permanent deletion. Only soft delete allowed.
-- Follow same pattern as pms_faults (which has no_hard_delete_faults trigger).
-- ----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION prevent_hard_delete_parts()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Hard delete not allowed on pms_parts. Use soft delete (UPDATE deleted_at = NOW()) instead.';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS no_hard_delete_parts ON pms_parts;

CREATE TRIGGER no_hard_delete_parts
    BEFORE DELETE ON pms_parts
    FOR EACH ROW
    EXECUTE FUNCTION prevent_hard_delete_parts();

COMMENT ON TRIGGER no_hard_delete_parts ON pms_parts IS
    'Prevents hard delete. Forces soft delete pattern for 30-day undo window.';

-- ----------------------------------------------------------------------------
-- 2.3 Add index for active parts query
-- ----------------------------------------------------------------------------
-- USER OUTCOME: Inventory list shows only active parts (deleted_at IS NULL).
-- This partial index speeds up the most common query.
-- ----------------------------------------------------------------------------

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pms_parts_active
ON pms_parts(yacht_id, category, name)
WHERE deleted_at IS NULL;

-- ----------------------------------------------------------------------------
-- 2.4 Add purchase_url to pms_shopping_list_items
-- ----------------------------------------------------------------------------
-- USER OUTCOME: When crew finds a part supplier online, they need to save the
-- URL so purchasing can order quickly. "I found this seal on MarineStore.com"
-- → save URL → Purser clicks directly to order.
--
-- LENS REQUIREMENT: Inventory Lens BLOCKER 2
-- CURRENT STATE: No purchase_url column exists
-- ALTERNATIVE REJECTED: Could use metadata JSONB, but this is a first-class
-- field used in every shopping list flow. Dedicated column is cleaner.
-- ----------------------------------------------------------------------------

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'pms_shopping_list_items'
        AND column_name = 'purchase_url'
    ) THEN
        ALTER TABLE pms_shopping_list_items
        ADD COLUMN purchase_url TEXT;

        COMMENT ON COLUMN pms_shopping_list_items.purchase_url IS
            'URL where part can be purchased. Saved by crew when requesting reorder.';
    END IF;
END $$;

-- ============================================================================
-- SECTION 3: WORK ORDER LENS REQUIREMENTS
-- Source: /docs/architecture/entity_lenses/work_order_lens_v1.md
-- ============================================================================
-- (To be added when building Work Order Lens)

-- ============================================================================
-- SECTION 3.5: FAULT → WORK ORDER CASCADE TRIGGER
-- Required for v3.2 Fault Lens doctrine
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 3.5.1 Auto-update fault status when WO status changes
-- ----------------------------------------------------------------------------
-- USER OUTCOME: When WO is completed, linked fault automatically resolves.
-- No manual fault status update needed.
-- ----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION cascade_wo_status_to_fault()
RETURNS TRIGGER AS $$
BEGIN
    -- Only act if WO has a linked fault and status changed
    IF NEW.fault_id IS NOT NULL AND OLD.status != NEW.status THEN

        -- WO in_progress → fault investigating
        IF NEW.status = 'in_progress' THEN
            UPDATE pms_faults
            SET status = 'investigating',
                updated_at = NOW(),
                updated_by = NEW.updated_by
            WHERE id = NEW.fault_id;

        -- WO completed → fault resolved
        ELSIF NEW.status = 'completed' THEN
            UPDATE pms_faults
            SET status = 'resolved',
                resolved_at = NOW(),
                resolved_by = NEW.updated_by,
                updated_at = NOW(),
                updated_by = NEW.updated_by
            WHERE id = NEW.fault_id;

        -- WO cancelled → fault back to open
        ELSIF NEW.status = 'cancelled' THEN
            UPDATE pms_faults
            SET status = 'open',
                resolved_at = NULL,
                resolved_by = NULL,
                updated_at = NOW(),
                updated_by = NEW.updated_by
            WHERE id = NEW.fault_id;

        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_wo_status_cascade_to_fault ON pms_work_orders;

CREATE TRIGGER trg_wo_status_cascade_to_fault
    AFTER UPDATE OF status ON pms_work_orders
    FOR EACH ROW
    EXECUTE FUNCTION cascade_wo_status_to_fault();

COMMENT ON TRIGGER trg_wo_status_cascade_to_fault ON pms_work_orders IS
    'Fault Lens v3.2 doctrine: Fault status cascades from WO status. No manual fault status updates.';

-- ============================================================================
-- SECTION 4: CROSS-LENS REQUIREMENTS
-- Requirements that span multiple lenses
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 4.1 Ensure pms_audit_log captures session context
-- ----------------------------------------------------------------------------
-- USER OUTCOME: When investigating "who did what", crew needs to know:
-- - Which device (mobile app vs desktop)
-- - IP address (for security)
-- - Session ID (to group related actions)
--
-- CURRENT STATE: pms_audit_log has metadata (JSONB) column ✅
-- ENHANCEMENT: Standardize session context structure
-- ----------------------------------------------------------------------------

COMMENT ON COLUMN pms_audit_log.metadata IS
    'Session and context data. Standard structure:
    {
        session_id: uuid,
        ip_address: text,
        user_agent: text,
        device_type: "mobile" | "desktop" | "tablet",
        app_version: text,
        timestamp_client: timestamptz (client device time, may differ from server)
    }';

-- ----------------------------------------------------------------------------
-- 4.2 Add composite index for audit trail queries
-- ----------------------------------------------------------------------------
-- USER OUTCOME: Common queries:
-- - "Show me all actions by user X in the last 7 days"
-- - "Show me all fault-related actions this week"
-- - "What happened to this equipment between date A and B?"
-- ----------------------------------------------------------------------------

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pms_audit_log_entity_time
ON pms_audit_log(entity_type, entity_id, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pms_audit_log_user_time
ON pms_audit_log(user_id, created_at DESC);

-- ============================================================================
-- SECTION 5: PERFORMANCE OPTIMIZATIONS
-- Indexes identified through user journey flow analysis
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 5.1 pms_work_orders: Support "My Assigned Work Orders" query
-- ----------------------------------------------------------------------------
-- USER OUTCOME: Engineer opens app, sees "My Work Orders" dashboard.
-- Query: WHERE assigned_to = current_user AND status != 'completed'
-- ----------------------------------------------------------------------------

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pms_work_orders_assigned_active
ON pms_work_orders(assigned_to, status)
WHERE deleted_at IS NULL
AND status NOT IN ('completed', 'cancelled');

-- ----------------------------------------------------------------------------
-- 5.2 pms_notes: Support "Recent Notes by Entity" query
-- ----------------------------------------------------------------------------
-- USER OUTCOME: When viewing fault/equipment/WO, show recent notes first.
-- Query: WHERE fault_id = X ORDER BY created_at DESC LIMIT 10
-- ----------------------------------------------------------------------------

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pms_notes_fault_recent
ON pms_notes(fault_id, created_at DESC)
WHERE fault_id IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pms_notes_equipment_recent
ON pms_notes(equipment_id, created_at DESC)
WHERE equipment_id IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pms_notes_wo_recent
ON pms_notes(work_order_id, created_at DESC)
WHERE work_order_id IS NOT NULL;

-- ============================================================================
-- SECTION 6: RLS POLICY VERIFICATION
-- Verify that RLS policies match Entity Lens permission tiers
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 6.1 pms_faults RLS: All crew can view, Engineers+ can manage
-- ----------------------------------------------------------------------------
-- USER OUTCOME: Deckhand can report faults and view them.
-- Engineer can update status, create work orders.
-- Captain/HoD can archive.
--
-- CURRENT STATE: RLS enabled on pms_faults ✅
-- VERIFY: Policies match Fault Lens spec
-- ----------------------------------------------------------------------------

-- Drop existing policies (will recreate with correct logic)
DROP POLICY IF EXISTS "Users can view faults" ON pms_faults;
DROP POLICY IF EXISTS "Engineers can manage faults" ON pms_faults;
DROP POLICY IF EXISTS "Service role full access" ON pms_faults;

-- All crew can view faults for their yacht
CREATE POLICY "crew_can_view_faults" ON pms_faults
    FOR SELECT
    USING (
        yacht_id = (SELECT yacht_id FROM auth.users WHERE id = auth.uid())
        AND deleted_at IS NULL
    );

-- All crew can report faults (INSERT)
CREATE POLICY "crew_can_report_faults" ON pms_faults
    FOR INSERT
    WITH CHECK (
        yacht_id = (SELECT yacht_id FROM auth.users WHERE id = auth.uid())
    );

-- Engineers/Deck/Interior can update faults
CREATE POLICY "engineers_can_manage_faults" ON pms_faults
    FOR UPDATE
    USING (
        yacht_id = (SELECT yacht_id FROM auth.users WHERE id = auth.uid())
        AND deleted_at IS NULL
        AND (
            (SELECT role FROM auth.users WHERE id = auth.uid()) IN
            ('chief_engineer', 'engineer', 'eto', 'deck_officer', 'chief_officer',
             'interior', 'chief_steward', 'captain', 'purser')
        )
    );

-- Captain/HoD can archive (soft delete via UPDATE deleted_at)
CREATE POLICY "hod_can_archive_faults" ON pms_faults
    FOR UPDATE
    USING (
        yacht_id = (SELECT yacht_id FROM auth.users WHERE id = auth.uid())
        AND (
            (SELECT role FROM auth.users WHERE id = auth.uid()) IN
            ('captain', 'chief_engineer', 'chief_steward', 'chief_officer', 'purser')
        )
    );

-- Service role bypass (for backend operations)
CREATE POLICY "service_role_full_access_faults" ON pms_faults
    FOR ALL
    USING (auth.jwt()->>'role' = 'service_role');

-- ============================================================================
-- SECTION 7: HELPER FUNCTIONS
-- Reusable database functions for common operations
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 7.1 Function: Get user's yacht_id (used in RLS policies)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION auth.user_yacht_id()
RETURNS UUID
LANGUAGE sql
SECURITY DEFINER
STABLE
AS $$
    SELECT yacht_id FROM auth.users WHERE id = auth.uid();
$$;

COMMENT ON FUNCTION auth.user_yacht_id IS
    'Returns the yacht_id for the current authenticated user. Used in RLS policies.';

-- ----------------------------------------------------------------------------
-- 7.2 Function: Check if user has role (used in RLS policies)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION auth.user_has_role(required_roles TEXT[])
RETURNS BOOLEAN
LANGUAGE sql
SECURITY DEFINER
STABLE
AS $$
    SELECT EXISTS (
        SELECT 1 FROM auth.users
        WHERE id = auth.uid()
        AND role = ANY(required_roles)
    );
$$;

COMMENT ON FUNCTION auth.user_has_role IS
    'Returns true if current user has one of the specified roles. Usage: auth.user_has_role(ARRAY[''captain'', ''chief_engineer''])';

-- ============================================================================
-- END OF MIGRATIONS
-- ============================================================================

-- VERIFICATION QUERIES (run these after applying migrations)
-- ============================================================================

-- Check pms_faults has detected_by column
-- SELECT column_name, data_type FROM information_schema.columns
-- WHERE table_name = 'pms_faults' AND column_name = 'detected_by';

-- Check action_registry has 6 fault actions
-- SELECT action_name, mutation_tier, signature_required FROM action_registry
-- WHERE action_name LIKE '%fault%';

-- Check RLS policies on pms_faults
-- SELECT policyname, cmd, qual FROM pg_policies
-- WHERE tablename = 'pms_faults';

-- Check indexes on pms_faults
-- SELECT indexname, indexdef FROM pg_indexes
-- WHERE tablename = 'pms_faults';
