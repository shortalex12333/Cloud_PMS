# Work Order Lens v2 - PHASE 1: Scope Definition

**Status**: COMPLETE
**Type**: OPERATIONAL
**Created**: 2026-01-24
**Primary Table**: pms_work_orders (29 columns)

---

## 1.1 Entity Identity

### What Work Order IS

A **Work Order** is a single, trackable unit of maintenance work on a yacht.

| Attribute | Value |
|-----------|-------|
| Primary operational entity | YES - crew thinks in "jobs" |
| Write-through point | YES - all maintenance activity flows through WOs |
| Link entity | Equipment ↔ Fault ↔ Part ↔ Crew |
| Lifecycle | planned → in_progress → completed/cancelled/deferred |
| Row count | 2,820 (production) |

### What Work Order is NOT

| NOT | Reason | Doctrine Reference |
|-----|--------|-------------------|
| Dashboard | No "all open WOs" landing page | Query-only activation |
| Fault tracker | Faults are metadata ON work orders (WO-First Doctrine) | WO-First |
| Inventory system | Parts linked via junction table (pms_work_order_parts) | Separation of concerns |
| Scheduling system | Scheduling = WO creation with due_date | WO is the unit |
| Crew portal | Assignment is one field (assigned_to) | WO owns assignment |
| Ambient list | No floating "create WO" button | No ambient buttons |

---

## 1.2 Lens Type Classification

| Classification | Value | Justification |
|----------------|-------|---------------|
| **Type** | OPERATIONAL | Heavy read + write, multiple actions |
| **Action Count** | 6 (maximum allowed) | Create, Update, Complete, Add Note, Reassign, Archive |
| **Signature Actions** | 2 | Reassign, Archive require HoD signature |
| **Cascade Effects** | YES | WO status → Fault status |

---

## 1.3 Primary Table

| Attribute | Value |
|-----------|-------|
| Table name | `pms_work_orders` |
| Column count | 29 |
| Has yacht_id | YES |
| RLS status | ✅ CANONICAL (`get_user_yacht_id()`) |
| Soft delete | YES (deleted_at, deleted_by, deletion_reason) |
| Prevent hard delete | YES (trigger: prevent_hard_delete) |

---

## 1.4 Secondary Tables

| Table | Relationship | Columns | yacht_id | RLS Status |
|-------|--------------|---------|----------|------------|
| pms_work_order_checklist | 1:N | 24 | YES | ⚠️ Mixed patterns |
| pms_work_order_notes | 1:N | 7 | NO | ❌ CROSS-YACHT LEAKAGE |
| pms_work_order_parts | M:N | 9 | NO | ❌ CROSS-YACHT LEAKAGE |
| pms_work_order_history | 1:N | 14 | YES | ✅ Canonical |
| pms_part_usage | 1:N | 11 | YES | ❌ CROSS-YACHT LEAKAGE |

---

## 1.5 Blockers (from Phase 0)

| ID | Table | Issue | Severity | Affects Actions |
|----|-------|-------|----------|-----------------|
| **B1** | pms_work_order_notes | `USING (true)` SELECT | CRITICAL | Add Note |
| **B2** | pms_work_order_parts | `USING (true)` SELECT | CRITICAL | Complete WO |
| **B3** | pms_part_usage | `USING (true)` SELECT | CRITICAL | Complete WO |
| **B4** | pms_work_orders | Missing cascade trigger | HIGH | Complete WO, Archive WO |

---

## 1.6 Doctrine Compliance

### WO-First Doctrine

```
WORK ORDER LENS DOCTRINE v2.0

1. OPERATIONAL PRIMACY
   Work Order is the primary operational entity.
   Faults are metadata ON work orders, not separate entities to manage.

2. QUERY-ONLY ACTIVATION
   WO views appear ONLY when user queries for them.
   No dashboard, no ambient lists, no floating buttons.

3. SINGLE FOCUS FOR ACTIONS
   Actions appear only when ONE WO is focused.
   List views show no actions except "focus on this WO".

4. WO-FIRST CREATION
   Faults don't "become" WOs. User creates WO, links fault.
   "Create WO for coolant leak" → WO created with fault_id set.

5. STATUS CASCADE
   WO status changes → Fault status follows (via trigger).
   - WO.completed → Fault.resolved
   - WO.cancelled → Fault.open (returned)

6. SIGNATURE ON HIGH-RISK
   Reassign/Archive require HoD signature.
   Signature payload stored in pms_audit_log.

7. NEVER DELETE
   Soft delete only. History preserved.
   deleted_at IS NOT NULL = archived, not deleted.
```

---

## 1.7 Action Summary

| # | Action | Signature | Tables Written | Blocker |
|---|--------|-----------|----------------|---------|
| 1 | Create Work Order | NO | pms_work_orders, pms_audit_log | - |
| 2 | Update Work Order | NO | pms_work_orders, pms_audit_log | - |
| 3 | Complete Work Order | NO (confirm) | pms_work_orders, pms_work_order_history, pms_part_usage, pms_faults | B2, B3, B4 |
| 4 | Add Note | NO | pms_work_order_notes, pms_audit_log | B1 |
| 5 | Reassign Work Order | YES | pms_work_orders, pms_audit_log | - |
| 6 | Archive Work Order | YES | pms_work_orders, pms_faults, pms_audit_log | B4 |

---

## 1.8 Escape Hatches

| To Lens | Via | Query Example |
|---------|-----|---------------|
| Equipment Lens | equipment_id | "show equipment for WO-2026-042" |
| Fault Lens | fault_id | "show fault for this work order" |
| Part Lens | pms_work_order_parts | "what parts needed for this WO" |
| Crew Lens | assigned_to | "who is assigned to WO-2026-042" |

---

## 1.9 Enum Values (Verified)

### work_order_status
| Value | Meaning | Transitions To |
|-------|---------|----------------|
| planned | Created, not started | in_progress |
| in_progress | Work underway | completed, deferred, cancelled |
| completed | Work finished | (terminal) |
| deferred | Postponed | planned, in_progress |
| cancelled | Archived/cancelled | (terminal) |

### work_order_priority
| Value | SLA Implication |
|-------|-----------------|
| routine | No urgency |
| important | Should be addressed soon |
| critical | Must be addressed today |
| emergency | Drop everything |

### work_order_type
| Value | Source |
|-------|--------|
| scheduled | Planned maintenance schedule |
| corrective | Fix something that broke |
| unplanned | Ad-hoc work |
| preventive | Proactive maintenance |

---

## PHASE 1 GATE: COMPLETE

| Check | Status |
|-------|--------|
| 1.1 Entity identity defined | ✅ |
| 1.2 Lens type classified | ✅ |
| 1.3 Primary table identified | ✅ |
| 1.4 Secondary tables listed | ✅ |
| 1.5 Blockers identified | ✅ |
| 1.6 Doctrine compliance verified | ✅ |
| 1.7 Actions summarized (≤6) | ✅ |
| 1.8 Escape hatches documented | ✅ |
| 1.9 Enum values verified | ✅ |
| No dashboard language | ✅ |
| No ambient buttons | ✅ |

**Proceeding to Phase 2: DB Truth**
