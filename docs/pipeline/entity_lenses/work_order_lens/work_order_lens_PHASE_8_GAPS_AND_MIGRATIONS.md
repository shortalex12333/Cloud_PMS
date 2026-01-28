# Work Order Lens - PHASE 8: Migration & Gap Report

**Status**: COMPLETE
**Created**: 2026-01-24
**Migration File**: `20260124_work_order_lens_gaps.sql`

---

## BLOCKER SUMMARY

| ID | Blocker | Type | Affects Actions | Resolution |
|----|---------|------|-----------------|------------|
| **B1** | Legacy RLS pattern on pms_work_orders | RLS | All | Migration to canonical pattern |
| **B2** | Enum values undocumented | Schema | Create, Update | Verify in pg_enum |
| **B3** | `user_has_role()` function not deployed | Function | Reassign, Archive | Deploy function |
| **B4** | No role-based RLS policies | RLS | Reassign, Archive | Deploy policies |
| **B5** | pms_work_order_notes references wrong table | RLS | Add Note | Fix policy |
| **B6** | pms_work_order_parts has no RLS | RLS | Complete | Add policies |
| **B7** | pms_work_order_history has no RLS | RLS | Complete | Add policies |
| **B8** | cascade_wo_status_to_fault() not deployed | Trigger | Complete, Archive | Deploy trigger |

---

## GAP INVENTORY

### Schema Gaps

| Gap ID | Type | Table | Description | Migration |
|--------|------|-------|-------------|-----------|
| G1 | Column | pms_work_orders | `work_order_type` deprecated, should be removed | ALTER TABLE |
| G2 | Index | pms_work_orders | No index on `deleted_at` for soft-delete queries | CREATE INDEX |
| G3 | Constraint | pms_work_order_notes | No FK to pms_work_orders (only to work_orders) | ALTER TABLE |

### RLS Gaps

| Gap ID | Type | Table | Description | Migration |
|--------|------|-------|-------------|-----------|
| R1 | Policy | pms_work_orders | Legacy pattern (user_profiles subquery) | DROP + CREATE |
| R2 | Policy | pms_work_orders | No soft-delete filter | ALTER POLICY |
| R3 | Policy | pms_work_order_notes | References wrong table | DROP + CREATE |
| R4 | Missing | pms_work_order_parts | No RLS enabled | ENABLE + CREATE |
| R5 | Missing | pms_work_order_history | No RLS enabled | ENABLE + CREATE |
| R6 | Policy | pms_work_orders | No role-based restrictions | CREATE |

### Function Gaps

| Gap ID | Type | Function | Description | Migration |
|--------|------|----------|-------------|-----------|
| F1 | Missing | user_has_role(TEXT[]) | Required for role-based RLS | CREATE FUNCTION |
| F2 | Missing | cascade_wo_status_to_fault() | WO→Fault status cascade | CREATE FUNCTION + TRIGGER |

---

## MIGRATION SQL

### Priority 1: Critical Blockers

```sql
-- =============================================================================
-- MIGRATION: Work Order Lens - Priority 1 (Critical)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- F1: Create user_has_role() function
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.user_has_role(required_roles TEXT[])
RETURNS BOOLEAN AS $$
  SELECT EXISTS (
    SELECT 1 FROM auth_users_profiles
    WHERE id = auth.uid()
    AND role = ANY(required_roles)
  );
$$ LANGUAGE sql SECURITY DEFINER STABLE;

COMMENT ON FUNCTION public.user_has_role IS 'Check if current user has any of the required roles';

-- -----------------------------------------------------------------------------
-- R1: Fix pms_work_orders RLS to canonical pattern
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users can view their yacht work orders" ON pms_work_orders;
DROP POLICY IF EXISTS "Users can manage their yacht work orders" ON pms_work_orders;

-- SELECT: All crew can view non-deleted WOs
CREATE POLICY "crew_select_work_orders" ON pms_work_orders
    FOR SELECT
    USING (
        yacht_id = public.get_user_yacht_id()
        AND deleted_at IS NULL
    );

-- INSERT: Authenticated users with yacht
CREATE POLICY "crew_insert_work_orders" ON pms_work_orders
    FOR INSERT
    WITH CHECK (
        yacht_id = public.get_user_yacht_id()
    );

-- UPDATE: Assigned or HoD
CREATE POLICY "crew_update_work_orders" ON pms_work_orders
    FOR UPDATE
    USING (
        yacht_id = public.get_user_yacht_id()
        AND deleted_at IS NULL
        AND (
            assigned_to = auth.uid()
            OR public.user_has_role(ARRAY[
                'captain', 'chief_officer', 'chief_engineer', 'eto',
                'chief_steward', 'purser'
            ])
        )
    )
    WITH CHECK (
        yacht_id = public.get_user_yacht_id()
    );

-- Service role bypass
CREATE POLICY "service_role_work_orders" ON pms_work_orders
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- -----------------------------------------------------------------------------
-- R3: Fix pms_work_order_notes RLS (wrong table reference)
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users can view notes on their yacht's work orders" ON pms_work_order_notes;
DROP POLICY IF EXISTS "Users can add notes to their yacht's work orders" ON pms_work_order_notes;

CREATE POLICY "crew_select_work_order_notes" ON pms_work_order_notes
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM pms_work_orders wo
            WHERE wo.id = pms_work_order_notes.work_order_id
            AND wo.yacht_id = public.get_user_yacht_id()
            AND wo.deleted_at IS NULL
        )
    );

CREATE POLICY "crew_insert_work_order_notes" ON pms_work_order_notes
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM pms_work_orders wo
            WHERE wo.id = pms_work_order_notes.work_order_id
            AND wo.yacht_id = public.get_user_yacht_id()
        )
    );
```

### Priority 2: Security Gaps

```sql
-- =============================================================================
-- MIGRATION: Work Order Lens - Priority 2 (Security)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- R4: Add RLS to pms_work_order_parts
-- -----------------------------------------------------------------------------
ALTER TABLE pms_work_order_parts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "crew_select_work_order_parts" ON pms_work_order_parts
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM pms_work_orders wo
            WHERE wo.id = pms_work_order_parts.work_order_id
            AND wo.yacht_id = public.get_user_yacht_id()
        )
        AND deleted_at IS NULL
    );

CREATE POLICY "crew_insert_work_order_parts" ON pms_work_order_parts
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM pms_work_orders wo
            WHERE wo.id = pms_work_order_parts.work_order_id
            AND wo.yacht_id = public.get_user_yacht_id()
        )
    );

CREATE POLICY "crew_update_work_order_parts" ON pms_work_order_parts
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM pms_work_orders wo
            WHERE wo.id = pms_work_order_parts.work_order_id
            AND wo.yacht_id = public.get_user_yacht_id()
        )
    );

CREATE POLICY "service_role_work_order_parts" ON pms_work_order_parts
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- -----------------------------------------------------------------------------
-- R5: Add RLS to pms_work_order_history
-- -----------------------------------------------------------------------------
ALTER TABLE pms_work_order_history ENABLE ROW LEVEL SECURITY;

CREATE POLICY "crew_select_work_order_history" ON pms_work_order_history
    FOR SELECT
    USING (yacht_id = public.get_user_yacht_id());

-- History is INSERT-only, system-generated
CREATE POLICY "service_insert_work_order_history" ON pms_work_order_history
    FOR INSERT
    TO service_role
    WITH CHECK (true);
```

### Priority 3: Cascade Trigger

```sql
-- =============================================================================
-- MIGRATION: Work Order Lens - Priority 3 (Cascade)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- F2: Create WO→Fault status cascade function
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.cascade_wo_status_to_fault()
RETURNS TRIGGER AS $$
BEGIN
    -- Only cascade if fault_id is not null and status changed
    IF NEW.fault_id IS NOT NULL AND OLD.status IS DISTINCT FROM NEW.status THEN
        CASE NEW.status
            WHEN 'in_progress' THEN
                UPDATE pms_faults
                SET status = 'investigating',
                    updated_at = NOW()
                WHERE id = NEW.fault_id;

            WHEN 'completed' THEN
                UPDATE pms_faults
                SET status = 'resolved',
                    resolved_at = NOW(),
                    resolved_by = NEW.completed_by,
                    updated_at = NOW()
                WHERE id = NEW.fault_id;

            WHEN 'cancelled' THEN
                -- If WO cancelled, return fault to open
                UPDATE pms_faults
                SET status = 'open',
                    resolved_at = NULL,
                    resolved_by = NULL,
                    updated_at = NOW()
                WHERE id = NEW.fault_id
                AND status IN ('investigating', 'work_ordered');
        END CASE;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION public.cascade_wo_status_to_fault IS 'Cascade WO status changes to linked fault';

-- Create trigger
DROP TRIGGER IF EXISTS trg_wo_status_cascade_to_fault ON pms_work_orders;

CREATE TRIGGER trg_wo_status_cascade_to_fault
    AFTER UPDATE OF status ON pms_work_orders
    FOR EACH ROW
    EXECUTE FUNCTION public.cascade_wo_status_to_fault();
```

### Priority 4: Schema Cleanup (Optional)

```sql
-- =============================================================================
-- MIGRATION: Work Order Lens - Priority 4 (Cleanup)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- G1: Remove deprecated column (OPTIONAL - verify no code references)
-- -----------------------------------------------------------------------------
-- ALTER TABLE pms_work_orders DROP COLUMN IF EXISTS work_order_type;

-- -----------------------------------------------------------------------------
-- G2: Add index for soft-delete queries
-- -----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_pms_work_orders_deleted
    ON pms_work_orders(yacht_id, deleted_at)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_pms_work_orders_status_active
    ON pms_work_orders(yacht_id, status, priority)
    WHERE deleted_at IS NULL AND status NOT IN ('completed', 'cancelled');

-- -----------------------------------------------------------------------------
-- G3: Add FK constraint to pms_work_order_notes (if missing)
-- -----------------------------------------------------------------------------
-- Check if FK exists first
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_type = 'FOREIGN KEY'
        AND table_name = 'pms_work_order_notes'
        AND constraint_name LIKE '%work_order_id%pms_work_orders%'
    ) THEN
        ALTER TABLE pms_work_order_notes
        ADD CONSTRAINT fk_pms_work_order_notes_work_order
        FOREIGN KEY (work_order_id) REFERENCES pms_work_orders(id)
        ON DELETE CASCADE;
    END IF;
END $$;
```

---

## DEPLOYMENT CHECKLIST

### Pre-Deployment

- [ ] Backup database
- [ ] Verify no active connections using affected tables
- [ ] Review all DROP POLICY statements
- [ ] Confirm role names match actual values in auth_users_profiles

### Deployment Order

1. [ ] Deploy F1: `user_has_role()` function
2. [ ] Deploy R1: Fix pms_work_orders RLS
3. [ ] Deploy R3: Fix pms_work_order_notes RLS
4. [ ] Deploy R4: Add pms_work_order_parts RLS
5. [ ] Deploy R5: Add pms_work_order_history RLS
6. [ ] Deploy F2: Cascade trigger
7. [ ] (Optional) Deploy G2: Indexes

### Post-Deployment Verification

- [ ] Verify crew can view own yacht WOs: `SELECT * FROM pms_work_orders LIMIT 1;`
- [ ] Verify cross-yacht blocked: `SELECT * FROM pms_work_orders WHERE yacht_id != [user_yacht];`
- [ ] Verify notes accessible: `SELECT * FROM pms_work_order_notes LIMIT 1;`
- [ ] Test WO completion cascade: Complete a WO and verify fault updates
- [ ] Test reassign with HoD role
- [ ] Test archive with Captain role

---

## RISK ASSESSMENT

| Migration | Risk Level | Rollback Plan |
|-----------|------------|---------------|
| F1: user_has_role() | LOW | DROP FUNCTION |
| R1: pms_work_orders RLS | MEDIUM | Re-create legacy policies |
| R3: pms_work_order_notes | MEDIUM | Re-create legacy policies |
| R4: pms_work_order_parts | LOW | DISABLE RLS |
| R5: pms_work_order_history | LOW | DISABLE RLS |
| F2: Cascade trigger | MEDIUM | DROP TRIGGER |
| G1: Remove column | HIGH | Requires ALTER TABLE ADD |

---

## ACTIONS BLOCKED UNTIL MIGRATION

| Action | Blocker | Can Deploy After |
|--------|---------|------------------|
| Create WO | B1 | R1 |
| Update WO | B1 | R1 |
| Complete WO | B1, B6, B7, B8 | R1, R4, R5, F2 |
| Add Note | B5 | R3 |
| Reassign WO | B1, B3, B4 | R1, F1, R6 |
| Archive WO | B1, B3, B4, B8 | R1, F1, R6, F2 |

**Note**: Actions can be partially enabled with application-level role checks until B4 (role-based RLS) is deployed.

---

## PHASE 8 GATE: COMPLETE

| Check | Status |
|-------|--------|
| 8.1 All blockers listed | ✅ |
| 8.2 All gaps inventoried | ✅ |
| 8.3 Migration SQL written | ✅ |
| 8.4 Deployment checklist created | ✅ |
| 8.5 Risk assessment completed | ✅ |
| 8.6 Action→Blocker mapping | ✅ |

**Proceeding to FINAL: Compile work_order_lens_v1_FINAL.md**
