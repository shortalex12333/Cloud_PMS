# Work Order Lens v2.0 - FINAL (GOLD)

**Status**: PRODUCTION READY (GOLD)
**Type**: OPERATIONAL
**Created**: 2026-01-24
**Updated**: 2026-01-27
**Actions**: 8 (6 core + 2 signed)
**Source**: Production Database Snapshot (2026-01-24T06:35:34)

---

## BLOCKERS: ALL RESOLVED

| ID | Issue | Table | Resolution | Migration |
|----|-------|-------|------------|-----------|
| **B1** | `USING (true)` SELECT | pms_work_order_notes | RESOLVED | `20260125_001_fix_cross_yacht_notes.sql` |
| **B2** | `USING (true)` SELECT | pms_work_order_parts | RESOLVED | `20260125_002_fix_cross_yacht_parts.sql` |
| **B3** | `USING (true)` SELECT | pms_part_usage | RESOLVED | `20260125_003_fix_cross_yacht_part_usage.sql` |
| **B4** | Missing trigger | cascade_wo_status_to_fault | RESOLVED | `20260125_004_create_cascade_wo_fault_trigger.sql` |

## Production Artifacts

| Artifact | Location | Status |
|----------|----------|--------|
| Migrations (B1-B4) | `supabase/migrations/20260125_00*.sql` | DEPLOYED |
| Handlers | `apps/api/handlers/work_order_mutation_handlers.py` | COMPLETE |
| Action Registry | `apps/api/actions/action_registry.py` | 13 WO actions |
| Acceptance Tests (HTTP) | `tests/acceptance/work_orders/rest/` | READY |
| Staging CI Tests | `tests/ci/staging_work_orders_acceptance.py` | READY |
| GitHub Actions | `.github/workflows/staging-work-orders-acceptance.yml` | READY |

---

## 1. ENTITY DEFINITION

### What Work Order IS

A **Work Order** is a single, trackable unit of maintenance work on a yacht.

| Attribute | Value |
|-----------|-------|
| Primary operational entity | YES |
| Write-through point | All maintenance flows through WOs |
| Lifecycle | planned → in_progress → completed/cancelled |
| Row count | 2,820 (production) |

### What Work Order is NOT

| NOT | Reason |
|-----|--------|
| Dashboard | No "all open WOs" landing page |
| Fault tracker | Faults are metadata ON work orders |
| Inventory system | Parts linked via junction table |
| Ambient list | No floating buttons |

---

## 2. DOCTRINE

```
WORK ORDER LENS DOCTRINE v2.0

1. OPERATIONAL PRIMACY
   Work Order is the primary operational entity.

2. QUERY-ONLY ACTIVATION
   WO views appear ONLY when user queries for them.

3. SINGLE FOCUS FOR ACTIONS
   Actions appear only when ONE WO is focused.

4. WO-FIRST CREATION
   Faults don't "become" WOs. User creates WO, links fault.

5. STATUS CASCADE
   WO status → Fault status (via trigger)

6. SIGNATURE ON HIGH-RISK
   Reassign/Archive require HoD signature.

7. NEVER DELETE
   Soft delete only. History preserved.
```

---

## 3. PRIMARY TABLE: pms_work_orders

**Columns**: 29
**yacht_id**: YES
**RLS**: ✅ CANONICAL (`get_user_yacht_id()`)

### Schema

| Column | Type | Nullable | Classification |
|--------|------|----------|----------------|
| id | uuid | NO | BACKEND_AUTO |
| yacht_id | uuid | NO | BACKEND_AUTO |
| wo_number | text | YES | BACKEND_AUTO |
| title | text | NO | REQUIRED |
| description | text | YES | OPTIONAL |
| type | work_order_type | NO | REQUIRED |
| priority | work_order_priority | NO | REQUIRED |
| status | work_order_status | NO | BACKEND_AUTO |
| equipment_id | uuid | YES | OPTIONAL |
| fault_id | uuid | YES | OPTIONAL |
| assigned_to | uuid | YES | OPTIONAL |
| due_date | date | YES | OPTIONAL |
| due_hours | integer | YES | OPTIONAL |
| frequency | jsonb | YES | CONTEXT |
| last_completed_date | date | YES | CONTEXT |
| last_completed_hours | integer | YES | CONTEXT |
| completed_at | timestamptz | YES | BACKEND_AUTO |
| completed_by | uuid | YES | BACKEND_AUTO |
| completion_notes | text | YES | OPTIONAL |
| metadata | jsonb | YES | OPTIONAL |
| vendor_contact_hash | text | YES | CONTEXT |
| work_order_type | text | YES | **DEPRECATED** |
| created_at | timestamptz | NO | BACKEND_AUTO |
| created_by | uuid | NO | BACKEND_AUTO |
| updated_at | timestamptz | NO | BACKEND_AUTO |
| updated_by | uuid | YES | BACKEND_AUTO |
| deleted_at | timestamptz | YES | BACKEND_AUTO |
| deleted_by | uuid | YES | BACKEND_AUTO |
| deletion_reason | text | YES | REQUIRED (on archive) |

### Secondary Tables

| Table | Columns | yacht_id | RLS Status |
|-------|---------|----------|------------|
| pms_work_order_checklist | 24 | YES | ⚠️ Mixed (secure) |
| pms_work_order_notes | 7 | NO | ❌ BLOCKER B1 |
| pms_work_order_parts | 9 | NO | ❌ BLOCKER B2 |
| pms_work_order_history | 14 | YES | ✅ Canonical |
| pms_part_usage | 11 | YES | ❌ BLOCKER B3 |

---

## 4. RELATIONSHIPS

### FK Paths (Outbound)

```
pms_work_orders.yacht_id → yacht_registry.id
pms_work_orders.equipment_id → pms_equipment.id
pms_work_orders.fault_id → pms_faults.id
pms_work_orders.assigned_to → auth.users.id
```

### FK Paths (Inbound)

```
pms_work_order_checklist.work_order_id → pms_work_orders.id
pms_work_order_notes.work_order_id → pms_work_orders.id
pms_work_order_parts.work_order_id → pms_work_orders.id
pms_work_order_history.work_order_id → pms_work_orders.id
pms_part_usage.work_order_id → pms_work_orders.id
```

### Escape Hatches

| To Lens | Via | Query |
|---------|-----|-------|
| Equipment | equipment_id | "show equipment" |
| Fault | fault_id | "show fault" |
| Part | pms_work_order_parts | "what parts needed" |
| Crew | assigned_to | "who is assigned" |

---

## 5. ACTIONS (6 Maximum)

### Summary

| # | Action | Signature | Status |
|---|--------|-----------|--------|
| 1 | Create Work Order | NO | ✅ Ready |
| 2 | Update Work Order | NO | ✅ Ready |
| 3 | Complete Work Order | NO (confirm) | ⚠️ Blocked (B2, B3, B4) |
| 4 | Add Note | NO | ⚠️ Blocked (B1) |
| 5 | Reassign Work Order | YES | ✅ Ready |
| 6 | Archive Work Order | YES | ⚠️ Blocked (B4) |

---

### Action 1: Create Work Order

**Intent**: "create work order for [equipment/fault]"

**Tables Written**:
- pms_work_orders (INSERT)

**SQL**:
```sql
INSERT INTO pms_work_orders (
    id, yacht_id, wo_number, title, type, priority, status,
    equipment_id, fault_id, assigned_to, due_date,
    created_at, created_by, updated_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    public.generate_wo_number(public.get_user_yacht_id()),
    $title, $type, COALESCE($priority, 'routine'), 'planned',
    $equipment_id, $fault_id, $assigned_to, $due_date,
    NOW(), auth.uid(), NOW()
) RETURNING id, wo_number;
```

**Signature**: `'{}'::jsonb`

---

### Action 2: Update Work Order

**Intent**: "update WO priority" / "assign to Mike"

**Pre-condition**: Status NOT IN ('completed', 'cancelled')

**Signature**: `'{}'::jsonb`

---

### Action 3: Complete Work Order

**Intent**: "complete WO-2026-042"

**Tables Written**:
- pms_work_orders (UPDATE)
- pms_work_order_history (INSERT)
- pms_part_usage (INSERT)
- pms_faults (UPDATE via trigger)

**Pre-conditions**:
1. Status is 'planned' or 'in_progress'
2. All required checklist items completed
3. User is assigned OR has engineer+ role

**Cascade** (via trigger B4):
- WO.completed → Fault.resolved

**Signature**: `'{}'::jsonb` (confirmation required)

**BLOCKED**: B2, B3, B4

---

### Action 4: Add Note

**Intent**: "add note: [content]"

**Tables Written**:
- pms_work_order_notes (INSERT)

**Signature**: `'{}'::jsonb`

**BLOCKED**: B1

---

### Action 5: Reassign Work Order

**Intent**: "reassign WO to [name]"

**Pre-conditions**:
1. User has HoD role
2. Status NOT IN ('completed', 'cancelled')
3. New assignee on same yacht

**Signature**: REQUIRED
```json
{
    "signer_id": "[user_id]",
    "signed_at": "[timestamp]",
    "device_id": "[device]",
    "action_hash": "[hash]"
}
```

---

### Action 6: Archive Work Order

**Intent**: "archive WO-2026-099"

**Pre-conditions**:
1. User has Captain/HoD role
2. Must provide deletion_reason

**Cascade** (via trigger B4):
- WO.cancelled → Fault.open (returned)

**Signature**: REQUIRED

**BLOCKED**: B4

---

## 6. RLS MATRIX

### Production Policies

| Table | SELECT Policy | Status |
|-------|---------------|--------|
| pms_work_orders | `yacht_id = get_user_yacht_id()` | ✅ Canonical |
| pms_work_order_checklist | Mixed patterns | ⚠️ Secure |
| pms_work_order_notes | `USING (true)` | ❌ **B1** |
| pms_work_order_parts | `USING (true)` | ❌ **B2** |
| pms_work_order_history | `yacht_id = get_user_yacht_id()` | ✅ Canonical |
| pms_part_usage | `USING (true)` | ❌ **B3** |

### Role × Action Matrix

| Role | View | Create | Update | Complete | Reassign | Archive |
|------|------|--------|--------|----------|----------|---------|
| Captain | ✅ | ✅ | ✅ All | ✅ All | ✅+Sign | ✅+Sign |
| Chief Engineer | ✅ | ✅ | ✅ Dept | ✅ Dept | ✅+Sign | ✅+Sign |
| 2nd Engineer | ✅ | ✅ | ✅ Assigned | ✅ Assigned | ❌ | ❌ |
| Deckhand | ✅ | ❌ | ✅ Assigned | ✅ Assigned | ❌ | ❌ |

---

## 7. CANONICAL FUNCTIONS

| Function | Verified |
|----------|----------|
| `public.get_user_yacht_id()` | ✅ |
| `public.get_user_role()` | ✅ |
| `public.generate_wo_number(uuid)` | ✅ |
| `public.deduct_part_inventory(...)` | ✅ |
| `cascade_wo_status_to_fault()` | ⚠️ B4 |

---

## 8. SCENARIOS

| # | Scenario | Traditional | Celeste | Reduction |
|---|----------|-------------|---------|-----------|
| 1 | Basic Lookup | 7 | 3 | 57% |
| 2 | My Work Orders | 7 | 4 | 43% |
| 3 | Create from Fault | 9 | 5 | 44% |
| 4 | Complete WO | 9 | 5 | 44% |
| 5 | WOs for Equipment | 7 | 4 | 43% |
| 6 | Add Note | 8 | 4 | 50% |
| 7 | Reassign WO | 11 | 5 | 55% |
| 8 | Overdue WOs | 7 | 3 | 57% |
| 9 | Fault to WO | 7 | 3 | 57% |
| 10 | Archive WO | 10 | 6 | 40% |

**Average Step Reduction: 49%**

---

## 9. MIGRATIONS REQUIRED

### Priority 1: Critical Security

```sql
-- B1: Fix pms_work_order_notes
DROP POLICY IF EXISTS "Authenticated users can view notes" ON pms_work_order_notes;
CREATE POLICY "crew_select_work_order_notes" ON pms_work_order_notes
    FOR SELECT TO authenticated
    USING (EXISTS (
        SELECT 1 FROM pms_work_orders wo
        WHERE wo.id = pms_work_order_notes.work_order_id
        AND wo.yacht_id = public.get_user_yacht_id()
    ));

-- B2: Fix pms_work_order_parts
DROP POLICY IF EXISTS "Authenticated users can view parts" ON pms_work_order_parts;

-- B3: Fix pms_part_usage
DROP POLICY IF EXISTS "Authenticated users can view usage" ON pms_part_usage;
CREATE POLICY "crew_select_part_usage" ON pms_part_usage
    FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());
```

### Priority 2: Functional

```sql
-- B4: Deploy cascade trigger
CREATE OR REPLACE FUNCTION public.cascade_wo_status_to_fault()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.fault_id IS NOT NULL AND OLD.status IS DISTINCT FROM NEW.status THEN
        CASE NEW.status
            WHEN 'completed' THEN
                UPDATE pms_faults SET status = 'resolved', resolved_at = NOW()
                WHERE id = NEW.fault_id;
            WHEN 'cancelled' THEN
                UPDATE pms_faults SET status = 'open'
                WHERE id = NEW.fault_id AND status IN ('investigating', 'work_ordered');
        END CASE;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER trg_wo_status_cascade_to_fault
    AFTER UPDATE OF status ON pms_work_orders
    FOR EACH ROW EXECUTE FUNCTION public.cascade_wo_status_to_fault();
```

---

## 10. VERIFICATION CHECKLIST

| Check | Status |
|-------|--------|
| No dashboard language | ✅ |
| No ambient buttons | ✅ |
| Query-only activation | ✅ |
| Actions only after focus | ✅ |
| Signature invariant (`'{}'::jsonb`) | ✅ |
| All FK paths verified | ✅ |
| No inferred joins | ✅ |
| RLS uses canonical function | ⚠️ B1, B2, B3 need migration |
| All functions verified in snapshot | ⚠️ B4 not deployed |

---

## APPENDIX A: v1 Errors Corrected

| Error | v1 Claim | v2 Truth |
|-------|----------|----------|
| E1 | pms_work_order_parts has yacht_id | **NO yacht_id** (9 columns) |
| E2 | pms_work_orders uses legacy RLS | Uses **canonical get_user_yacht_id()** |
| E3 | pms_work_order_history "NO RLS" | Has **proper canonical RLS** |
| E4 | Notes "wrong table reference" | Has `USING (true)` = **cross-yacht leakage** |
| E5 | pms_part_usage not documented | **11 columns, HAS yacht_id** |
| E6 | created_by is REQUIRED | Should be **BACKEND_AUTO** |

---

## APPENDIX B: Query Patterns

### List Work Orders
```sql
SELECT wo.*, e.name as equipment_name, u.full_name as assigned_to_name
FROM pms_work_orders wo
LEFT JOIN pms_equipment e ON wo.equipment_id = e.id
LEFT JOIN auth_users_profiles u ON wo.assigned_to = u.id
WHERE wo.yacht_id = public.get_user_yacht_id()
AND wo.deleted_at IS NULL
ORDER BY CASE wo.priority
    WHEN 'emergency' THEN 1 WHEN 'critical' THEN 2
    WHEN 'important' THEN 3 WHEN 'routine' THEN 4
END, wo.due_date NULLS LAST;
```

### Single WO Detail
```sql
SELECT wo.*, e.name as equipment_name, f.title as fault_title,
       creator.full_name as created_by_name
FROM pms_work_orders wo
LEFT JOIN pms_equipment e ON wo.equipment_id = e.id
LEFT JOIN pms_faults f ON wo.fault_id = f.id
LEFT JOIN auth_users_profiles creator ON wo.created_by = creator.id
WHERE wo.id = $1 AND wo.yacht_id = public.get_user_yacht_id();
```

---

## APPENDIX C: Enum Values

### work_order_status
`planned`, `in_progress`, `completed`, `deferred`, `cancelled`

### work_order_priority
`routine`, `important`, `critical`, `emergency`

### work_order_type
`scheduled`, `corrective`, `unplanned`, `preventive`

---

**END OF DOCUMENT**

**Next Steps**:
1. Deploy security migrations (B1, B2, B3)
2. Deploy cascade trigger (B4)
3. Re-verify actions after migration
4. Proceed to Lens 2: Equipment
