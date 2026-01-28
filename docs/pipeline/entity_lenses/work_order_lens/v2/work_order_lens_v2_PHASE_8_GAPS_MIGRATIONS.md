# Work Order Lens v2 - PHASE 8: Gaps & Migrations

**Status**: COMPLETE
**Created**: 2026-01-24
**Migration File**: `20260124_work_order_lens_v2_security_fixes.sql`

---

## 8.1 Blocker Summary

| ID | Blocker | Type | Tables | Affects Actions | Severity |
|----|---------|------|--------|-----------------|----------|
| **B1** | `USING (true)` SELECT on pms_work_order_notes | RLS | pms_work_order_notes | Add Note | CRITICAL |
| **B2** | `USING (true)` SELECT on pms_work_order_parts | RLS | pms_work_order_parts | Complete WO | CRITICAL |
| **B3** | `USING (true)` SELECT on pms_part_usage | RLS | pms_part_usage | Complete WO | CRITICAL |
| **B4** | `cascade_wo_status_to_fault()` not deployed | Trigger | pms_work_orders, pms_faults | Complete WO, Archive WO | HIGH |

---

## 8.2 Gap Inventory

### Security Gaps

| Gap ID | Type | Table | Issue | Impact |
|--------|------|-------|-------|--------|
| G1 | RLS | pms_work_order_notes | Cross-yacht data leakage | Any user sees all notes |
| G2 | RLS | pms_work_order_parts | Cross-yacht data leakage | Any user sees all part assignments |
| G3 | RLS | pms_part_usage | Cross-yacht data leakage | Any user sees all part usage |

### Functional Gaps

| Gap ID | Type | Component | Issue | Impact |
|--------|------|-----------|-------|--------|
| G4 | Trigger | cascade_wo_status_to_fault | Not deployed | Fault status doesn't update on WO complete/archive |
| G5 | Policy | pms_work_order_checklist | Duplicate inconsistent policies | Maintenance burden |

### Schema Gaps

| Gap ID | Type | Table | Issue | Impact |
|--------|------|-------|-------|--------|
| G6 | Column | pms_work_orders | `work_order_type` deprecated | Confusion |
| G7 | Index | pms_work_orders | No index on deleted_at | Slow soft-delete queries |

---

## 8.3 Migration SQL

### Priority 1: Critical Security Fixes

```sql
-- =============================================================================
-- MIGRATION: Work Order Lens v2 - Priority 1 (Critical Security)
-- File: 20260124_work_order_lens_v2_security_fixes.sql
-- =============================================================================

-- -----------------------------------------------------------------------------
-- B1: Fix pms_work_order_notes - CROSS-YACHT DATA LEAKAGE
-- -----------------------------------------------------------------------------

-- Drop the insecure policy
DROP POLICY IF EXISTS "Authenticated users can view notes" ON pms_work_order_notes;

-- Create secure policy using join to parent table
CREATE POLICY "crew_select_work_order_notes" ON pms_work_order_notes
    FOR SELECT TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM pms_work_orders wo
            WHERE wo.id = pms_work_order_notes.work_order_id
            AND wo.yacht_id = public.get_user_yacht_id()
            AND wo.deleted_at IS NULL
        )
    );

-- Ensure INSERT policy uses same pattern
DROP POLICY IF EXISTS "pms_work_order_notes_yacht_isolation" ON pms_work_order_notes;

CREATE POLICY "crew_insert_work_order_notes" ON pms_work_order_notes
    FOR INSERT TO authenticated
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM pms_work_orders wo
            WHERE wo.id = pms_work_order_notes.work_order_id
            AND wo.yacht_id = public.get_user_yacht_id()
        )
    );

-- -----------------------------------------------------------------------------
-- B2: Fix pms_work_order_parts - CROSS-YACHT DATA LEAKAGE
-- -----------------------------------------------------------------------------

-- Drop the insecure policy (keep the secure join-based one)
DROP POLICY IF EXISTS "Authenticated users can view parts" ON pms_work_order_parts;

-- The existing "Users can view work order parts" policy is secure, keep it

-- -----------------------------------------------------------------------------
-- B3: Fix pms_part_usage - CROSS-YACHT DATA LEAKAGE
-- -----------------------------------------------------------------------------

-- Drop the insecure policy
DROP POLICY IF EXISTS "Authenticated users can view usage" ON pms_part_usage;
DROP POLICY IF EXISTS "pms_part_usage_yacht_isolation" ON pms_part_usage;

-- Create secure policy using yacht_id directly (table HAS yacht_id)
CREATE POLICY "crew_select_part_usage" ON pms_part_usage
    FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

CREATE POLICY "crew_insert_part_usage" ON pms_part_usage
    FOR INSERT TO authenticated
    WITH CHECK (yacht_id = public.get_user_yacht_id());
```

### Priority 2: Functional Fixes

```sql
-- =============================================================================
-- MIGRATION: Work Order Lens v2 - Priority 2 (Functional)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- B4: Deploy cascade_wo_status_to_fault() trigger
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
                WHERE id = NEW.fault_id
                AND yacht_id = NEW.yacht_id;

            WHEN 'completed' THEN
                UPDATE pms_faults
                SET status = 'resolved',
                    resolved_at = NOW(),
                    resolved_by = NEW.completed_by,
                    updated_at = NOW()
                WHERE id = NEW.fault_id
                AND yacht_id = NEW.yacht_id;

            WHEN 'cancelled' THEN
                -- If WO cancelled, return fault to open
                UPDATE pms_faults
                SET status = 'open',
                    resolved_at = NULL,
                    resolved_by = NULL,
                    updated_at = NOW()
                WHERE id = NEW.fault_id
                AND yacht_id = NEW.yacht_id
                AND status IN ('investigating', 'work_ordered');
        END CASE;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION public.cascade_wo_status_to_fault IS
    'Cascade WO status changes to linked fault (WO-First Doctrine)';

-- Create trigger
DROP TRIGGER IF EXISTS trg_wo_status_cascade_to_fault ON pms_work_orders;

CREATE TRIGGER trg_wo_status_cascade_to_fault
    AFTER UPDATE OF status ON pms_work_orders
    FOR EACH ROW
    EXECUTE FUNCTION public.cascade_wo_status_to_fault();
```

### Priority 3: Cleanup (Optional)

```sql
-- =============================================================================
-- MIGRATION: Work Order Lens v2 - Priority 3 (Cleanup)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- G5: Consolidate pms_work_order_checklist policies
-- -----------------------------------------------------------------------------

-- Drop redundant policies (keep canonical ones)
DROP POLICY IF EXISTS "yacht_isolation_select" ON pms_work_order_checklist;
DROP POLICY IF EXISTS "yacht_isolation_insert" ON pms_work_order_checklist;
DROP POLICY IF EXISTS "yacht_isolation_update" ON pms_work_order_checklist;
DROP POLICY IF EXISTS "yacht_isolation_delete" ON pms_work_order_checklist;

-- Keep users_view, users_insert, users_update, users_delete (canonical)

-- -----------------------------------------------------------------------------
-- G7: Add index for soft-delete queries
-- -----------------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_pms_work_orders_active
    ON pms_work_orders(yacht_id, status, priority)
    WHERE deleted_at IS NULL AND status NOT IN ('completed', 'cancelled');

CREATE INDEX IF NOT EXISTS idx_pms_work_orders_deleted_at
    ON pms_work_orders(yacht_id, deleted_at)
    WHERE deleted_at IS NULL;

-- -----------------------------------------------------------------------------
-- G6: Remove deprecated column (OPTIONAL - verify no code references first)
-- -----------------------------------------------------------------------------
-- ALTER TABLE pms_work_orders DROP COLUMN IF EXISTS work_order_type;
```

---

## 8.4 Deployment Checklist

### Pre-Deployment

- [ ] Backup database
- [ ] Verify no active connections to affected tables
- [ ] Review all DROP POLICY statements
- [ ] Test migration on staging environment

### Deployment Order

1. [ ] **P1-B1**: Fix pms_work_order_notes RLS
2. [ ] **P1-B2**: Fix pms_work_order_parts RLS
3. [ ] **P1-B3**: Fix pms_part_usage RLS
4. [ ] **P2-B4**: Deploy cascade trigger
5. [ ] **P3-G5**: (Optional) Consolidate checklist policies
6. [ ] **P3-G7**: (Optional) Add indexes

### Post-Deployment Verification

```sql
-- Test 1: Verify yacht isolation on notes
SET request.jwt.claims = '{"sub": "user-a-id"}';
SELECT COUNT(*) FROM pms_work_order_notes; -- Should only see own yacht

-- Test 2: Verify yacht isolation on parts
SELECT COUNT(*) FROM pms_work_order_parts; -- Should only see own yacht

-- Test 3: Verify yacht isolation on part usage
SELECT COUNT(*) FROM pms_part_usage; -- Should only see own yacht

-- Test 4: Verify cascade trigger
UPDATE pms_work_orders SET status = 'completed' WHERE id = 'test-wo-id';
SELECT status FROM pms_faults WHERE id = 'linked-fault-id'; -- Should be 'resolved'
```

---

## 8.5 Risk Assessment

| Migration | Risk | Rollback Plan |
|-----------|------|---------------|
| B1: Fix notes RLS | MEDIUM | Re-create `USING (true)` policy |
| B2: Fix parts RLS | LOW | Re-create `USING (true)` policy |
| B3: Fix part_usage RLS | MEDIUM | Re-create `USING (true)` policy |
| B4: Cascade trigger | MEDIUM | DROP TRIGGER |
| G5: Consolidate policies | LOW | Re-create dropped policies |
| G7: Add indexes | LOW | DROP INDEX |

---

## 8.6 Actions Blocked Until Migration

| Action | Blockers | Can Deploy After |
|--------|----------|------------------|
| Create WO | - | ✅ Ready now |
| Update WO | - | ✅ Ready now |
| Complete WO | B2, B3, B4 | After P1 + P2 |
| Add Note | B1 | After P1-B1 |
| Reassign WO | - | ✅ Ready now |
| Archive WO | B4 | After P2-B4 |

---

## 8.7 Action-Safe Status

| Action | RLS Safe? | Functionally Complete? | Overall Status |
|--------|-----------|------------------------|----------------|
| Create WO | ✅ | ✅ | ✅ READY |
| Update WO | ✅ | ✅ | ✅ READY |
| Complete WO | ❌ (B2, B3) | ❌ (B4) | ⚠️ BLOCKED |
| Add Note | ❌ (B1) | ✅ | ⚠️ BLOCKED |
| Reassign WO | ✅ | ✅ | ✅ READY |
| Archive WO | ✅ | ❌ (B4) | ⚠️ PARTIAL |

---

## PHASE 8 GATE: COMPLETE

| Check | Status |
|-------|--------|
| 8.1 All blockers summarized | ✅ |
| 8.2 All gaps inventoried | ✅ |
| 8.3 Migration SQL written | ✅ |
| 8.4 Deployment checklist created | ✅ |
| 8.5 Risk assessment completed | ✅ |
| 8.6 Action→Blocker mapping | ✅ |
| 8.7 Action-safe status documented | ✅ |

**Proceeding to FINAL: Compile work_order_lens_v2_FINAL.md**
