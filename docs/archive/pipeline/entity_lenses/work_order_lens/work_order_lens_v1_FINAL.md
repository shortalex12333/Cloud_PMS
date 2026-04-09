# Work Order Lens v1.0 - FINAL

**Status**: COMPLETE
**Type**: OPERATIONAL
**Created**: 2026-01-24
**Actions**: 6

---

## BLOCKERS

| ID | Blocker | Type | Affects | Resolution |
|----|---------|------|---------|------------|
| **B1** | Legacy RLS pattern | RLS | All write actions | Migration: `20260124_work_order_lens_gaps.sql` |
| **B3** | `user_has_role()` not deployed | Function | Reassign, Archive | Deploy function first |
| **B4** | No role-based RLS | Policy | Reassign, Archive | Deploy after B3 |
| **B5** | pms_work_order_notes wrong table ref | RLS | Add Note | Fix in migration |
| **B6** | pms_work_order_parts no RLS | RLS | Complete | Enable + add policies |
| **B7** | pms_work_order_history no RLS | RLS | Complete | Enable + add policies |
| **B8** | Cascade trigger not deployed | Trigger | Complete, Archive | Deploy trigger |

---

## 1. ENTITY DEFINITION

### What Work Order IS

A **Work Order** is a single, trackable unit of maintenance work on a yacht.

- **Primary operational entity** - crew thinks in "jobs"
- **Write-through point** for all maintenance activity
- **Link between** Equipment ↔ Fault ↔ Part ↔ Crew
- **Lifecycle**: draft → open → in_progress → completed/cancelled

### What Work Order is NOT

| NOT | Reason |
|-----|--------|
| Dashboard | No "all open WOs" landing page |
| Fault tracker | Faults are metadata ON work orders |
| Inventory system | Parts linked via junction table |
| Scheduling system | Scheduling = WO creation |
| Crew portal | Assignment is one field |

---

## 2. DOCTRINE

```
WORK ORDER LENS DOCTRINE v1.0

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

## 3. PRIMARY TABLE: `pms_work_orders`

### Schema (29 columns)

| Column | Type | Nullable | Classification |
|--------|------|----------|----------------|
| id | uuid | NO | BACKEND_AUTO |
| yacht_id | uuid | NO | BACKEND_AUTO |
| wo_number | text | YES | BACKEND_AUTO |
| title | text | NO | REQUIRED |
| description | text | YES | OPTIONAL |
| type | work_order_type (enum) | NO | REQUIRED |
| priority | work_order_priority (enum) | NO | REQUIRED |
| status | work_order_status (enum) | NO | BACKEND_AUTO |
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

| Table | Relationship | Columns |
|-------|--------------|---------|
| pms_work_order_checklist | 1:N | 23 |
| pms_work_order_notes | 1:N | 7 |
| pms_work_order_parts | M:N | 9 |
| pms_work_order_history | 1:N | 14 |

---

## 4. RELATIONSHIPS

### FK Paths (Outbound)

```
pms_work_orders.yacht_id → yachts.id
pms_work_orders.equipment_id → pms_equipment.id
pms_work_orders.fault_id → pms_faults.id
pms_work_orders.assigned_to → auth.users.id
pms_work_orders.created_by → auth.users.id
```

### FK Paths (Inbound)

```
pms_work_order_checklist.work_order_id → pms_work_orders.id
pms_work_order_notes.work_order_id → pms_work_orders.id
pms_work_order_parts.work_order_id → pms_work_orders.id
pms_attachments.entity_id → pms_work_orders.id (polymorphic)
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

| # | Action | Signature | Blocker |
|---|--------|-----------|---------|
| 1 | Create Work Order | NO | B1 |
| 2 | Update Work Order | NO | B1 |
| 3 | Complete Work Order | NO (confirm) | B1, B6, B7, B8 |
| 4 | Add Note | NO | B5 |
| 5 | Reassign Work Order | YES | B1, B3, B4 |
| 6 | Archive Work Order | YES | B1, B3, B4, B8 |

---

### Action 1: Create Work Order

**Intent**: "create work order for [equipment/fault]"

**Tables Written**:
- pms_work_orders (INSERT)
- pms_audit_log (INSERT)

**Key SQL**:
```sql
INSERT INTO pms_work_orders (
  id, yacht_id, wo_number, title, type, priority, status,
  equipment_id, fault_id, assigned_to, due_date,
  created_at, created_by, updated_at
) VALUES (
  gen_random_uuid(),
  public.get_user_yacht_id(),
  public.generate_wo_number(public.get_user_yacht_id()),
  $1, $2, COALESCE($3, 'medium'), 'open',
  $4, $5, $6, $7,
  NOW(), auth.uid(), NOW()
) RETURNING id, wo_number;
```

**Signature**: `'{}'::jsonb`

---

### Action 2: Update Work Order

**Intent**: "update this work order" / "change priority"

**Tables Written**:
- pms_work_orders (UPDATE)
- pms_audit_log (INSERT)

**Pre-condition**: WO not completed/cancelled

**Signature**: `'{}'::jsonb`

---

### Action 3: Complete Work Order

**Intent**: "complete WO-2026-042"

**Tables Written**:
- pms_work_orders (UPDATE: status, completed_at, completed_by)
- pms_faults (UPDATE via trigger)
- pms_work_order_history (INSERT)
- pms_parts (UPDATE: quantity_on_hand)
- pms_part_usage (INSERT)
- pms_audit_log (INSERT)

**Pre-conditions**:
1. Status is 'open' or 'in_progress'
2. All required checklist items completed
3. User is assigned OR has engineer+ role

**Cascade**:
```
WO.status = 'completed'
  → Trigger: cascade_wo_status_to_fault()
    → Fault.status = 'resolved'
```

**Signature**: `'{}'::jsonb` (confirmation required)

---

### Action 4: Add Note

**Intent**: "add note: [content]"

**Tables Written**:
- pms_work_order_notes (INSERT)
- pms_audit_log (INSERT)

**Signature**: `'{}'::jsonb`

---

### Action 5: Reassign Work Order

**Intent**: "reassign WO to [name]"

**Tables Written**:
- pms_work_orders (UPDATE: assigned_to)
- pms_audit_log (INSERT with signature)

**Pre-conditions**:
1. User has HoD role
2. WO not completed/cancelled
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

**Tables Written**:
- pms_work_orders (UPDATE: deleted_at, deleted_by, deletion_reason, status='cancelled')
- pms_faults (UPDATE via trigger: status='open')
- pms_audit_log (INSERT with signature)

**Pre-conditions**:
1. User has Captain/HoD role
2. Must provide deletion_reason

**Cascade**:
```
WO.status = 'cancelled'
  → Trigger: cascade_wo_status_to_fault()
    → Fault.status = 'open' (returned)
```

**Signature**: REQUIRED (same format as Action 5)

---

## 6. RLS MATRIX

### Deployed (Current)

| Policy | Table | Condition |
|--------|-------|-----------|
| "Users can view..." | pms_work_orders | Yacht isolation (legacy) |
| "Users can manage..." | pms_work_orders | Yacht isolation (legacy) |

### Required (Target)

| Role | View | Create | Update | Complete | Reassign | Archive |
|------|------|--------|--------|----------|----------|---------|
| Captain | ✅ | ✅ | ✅ All | ✅ All | ✅+Sign | ✅+Sign |
| Chief Engineer | ✅ | ✅ | ✅ Dept | ✅ Dept | ✅+Sign | ✅+Sign |
| 2nd Engineer | ✅ | ✅ | ✅ Own | ✅ Own | ❌ | ❌ |
| Deckhand | ✅ | ❌ | ✅ Own | ✅ Own | ❌ | ❌ |

---

## 7. CANONICAL FUNCTIONS

| Function | Location | Verified |
|----------|----------|----------|
| `public.get_user_yacht_id()` | 02_p0_actions.sql:489 | ✅ |
| `public.generate_wo_number(uuid)` | 02_p0_actions.sql:391 | ✅ |
| `public.deduct_part_inventory(...)` | 02_p0_actions.sql:424 | ✅ |
| `public.user_has_role(TEXT[])` | PROPOSED | ⚠️ B3 |
| `cascade_wo_status_to_fault()` | PROPOSED | ⚠️ B8 |

---

## 8. SCENARIOS (Summary)

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

### Priority 1 (Blockers)
1. Deploy `user_has_role()` function
2. Fix pms_work_orders RLS to canonical pattern
3. Fix pms_work_order_notes RLS (wrong table)

### Priority 2 (Security)
4. Add RLS to pms_work_order_parts
5. Add RLS to pms_work_order_history

### Priority 3 (Functionality)
6. Deploy `cascade_wo_status_to_fault()` trigger

### Priority 4 (Cleanup)
7. Add indexes for soft-delete queries
8. (Optional) Remove deprecated `work_order_type` column

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
| RLS uses canonical function | ⚠️ MIGRATION NEEDED |
| All functions verified in snapshot | ⚠️ 2 PROPOSED |

---

## APPENDIX A: Query Patterns

### List Work Orders
```sql
SELECT wo.*, e.name as equipment_name, u.full_name as assigned_to_name
FROM pms_work_orders wo
LEFT JOIN pms_equipment e ON wo.equipment_id = e.id
LEFT JOIN auth_users_profiles u ON wo.assigned_to = u.id
WHERE wo.yacht_id = public.get_user_yacht_id()
AND wo.deleted_at IS NULL
ORDER BY CASE wo.priority
  WHEN 'critical' THEN 1 WHEN 'high' THEN 2
  WHEN 'medium' THEN 3 WHEN 'low' THEN 4
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

## APPENDIX B: Ledger Events

| Action | Event Type | Entity Type |
|--------|------------|-------------|
| Create | created | work_order |
| Update | updated | work_order |
| Complete | completed | work_order |
| Add Note | note_added | work_order |
| Reassign | reassigned | work_order |
| Archive | archived | work_order |

---

**END OF DOCUMENT**

**Next Steps**:
1. Review and approve this lens
2. Deploy migrations (Phase 8)
3. Implement frontend components
4. Proceed to Lens 2: Equipment
