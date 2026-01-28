# Work Order Lens - PHASE 1: Scope & Doctrine Lock

**Status**: FROZEN
**Created**: 2026-01-24
**Gate**: APPROVED

---

## 1.1 What Work Order Lens IS

The **Work Order Lens** is:

1. **The operational backbone** of CELESTE PMS
2. **The primary unit of work** - crew thinks in "jobs", not faults or equipment
3. **The write-through point** for all maintenance activity
4. **The link between** Equipment ↔ Fault ↔ Part ↔ Crew

**Entity Definition:**
```
A Work Order is a single, trackable unit of maintenance work
on a yacht, with lifecycle: draft → open → in_progress → completed/cancelled
```

**What it encompasses:**
- Corrective maintenance (fault-driven)
- Preventive maintenance (scheduled)
- Predictive maintenance (condition-based)
- Emergency repairs
- Project work (upgrades, refits)

---

## 1.2 What Work Order Lens is NOT

| NOT This | Why |
|----------|-----|
| NOT a dashboard | No "all open WOs" landing page |
| NOT a fault tracker | Faults are metadata ON work orders |
| NOT inventory management | Parts are linked via `pms_work_order_parts` |
| NOT scheduling system | Scheduling emerges from due_date/frequency |
| NOT a reporting tool | Reports are separate analytics |
| NOT a crew assignment portal | Assignment is one field on WO |

**Forbidden assumptions:**
- No "WO inbox" concept
- No "assign to me" button floating in UI
- No calendar view of scheduled WOs
- No Kanban board of WO statuses

---

## 1.3 Classification

| Classification | Value |
|----------------|-------|
| **Type** | **OPERATIONAL** |
| **Read/Write** | Heavy writes (creates, updates, status changes) |
| **Action Count** | Max 6 (backbone lens = full action set) |
| **Complexity** | HIGH (most relationships, most triggers) |

**Why OPERATIONAL (not Read-heavy):**
- Every maintenance action flows through WO creation/update
- Status changes trigger cascades (→ Fault status, → Audit log)
- Completion writes to multiple tables (checklist items, parts used)

---

## 1.4 Allowed Query Patterns

Users can activate the Work Order lens via:

| Pattern | Example Query | Activation |
|---------|---------------|------------|
| **Direct lookup** | `"WO-2026-0042"` | Single WO focus |
| **Equipment context** | `"work orders for generator"` | List → Focus |
| **Status query** | `"open work orders"` | List (no actions until focus) |
| **Assignment query** | `"my work orders"` | List → Focus |
| **Fault-linked** | `"work order for coolant leak"` | Single WO focus |
| **Action intent** | `"create work order for..."` | Action surface |
| **History query** | `"completed work orders this month"` | List (read-only) |

---

## 1.5 Forbidden Query Patterns

| Forbidden Pattern | Why Forbidden |
|-------------------|---------------|
| `"show dashboard"` | No dashboards exist |
| `"WO statistics"` | Analytics is separate lens |
| `"assign all overdue"` | Bulk actions not in query-first paradigm |
| `"schedule maintenance"` | Scheduling is WO creation, not separate |
| `"print work order"` | Print is device action, not lens action |

---

## 1.6 Escape Hatches

When viewing a Work Order, user can escape to:

| Escape To | Trigger | Via |
|-----------|---------|-----|
| **Equipment Lens** | Click equipment name | FK: `equipment_id` |
| **Fault Lens** | Click fault reference | FK: `fault_id` |
| **Part Lens** | Click part in checklist | Via `pms_work_order_parts` |
| **Crew Lens** | Click assigned crew | FK: `assigned_to` |
| **Document Lens** | Click attached document | Via `pms_attachments` |

**Cross-lens navigation is query-based** - clicking "Generator #1" on a WO issues implicit query `"equipment Generator #1"`.

---

## 1.7 Doctrine Statement

```
WORK ORDER LENS DOCTRINE v1.0

1. OPERATIONAL PRIMACY
   Work Order is the primary operational entity. Crew executes work
   through Work Orders. Faults, Parts, and Equipment are context.

2. QUERY-ONLY ACTIVATION
   Work Order views appear ONLY when user queries for them.
   No ambient "My Work Orders" widget. No floating assignment buttons.

3. SINGLE FOCUS FOR ACTIONS
   Actions (complete, reassign, add note) appear only when ONE
   Work Order is focused. List views show data only.

4. WO-FIRST CREATION
   Faults do not "become" Work Orders. User creates WO, optionally
   links to existing Fault. Fault status cascades FROM WO status.

5. STATUS CASCADE
   WO status changes trigger automatic Fault status updates:
   - WO in_progress → Fault investigating
   - WO completed → Fault resolved
   - WO cancelled → Fault back to open

6. SIGNATURE ON HIGH-RISK
   Archive and reassign actions require Captain/HoD signature.
   Complete action requires assigned crew confirmation.

7. NEVER DELETE
   Work Orders are never hard-deleted. Soft delete (cancelled +
   deletion_reason) preserves audit trail.
```

---

## 1.8 Review for Dashboard/Button Leaks

| Check | Result |
|-------|--------|
| Word "dashboard" appears? | NO |
| Word "button" without focus context? | NO |
| "Navigate to" language? | NO |
| "System suggests" language? | NO |
| Implied ambient UI? | NO |
| Bulk actions? | NO |

**PASS** - No UI leaks detected.

---

## PHASE 1 GATE: APPROVED

| Check | Status |
|-------|--------|
| 1.1 What lens IS defined | ✅ |
| 1.2 What lens is NOT defined | ✅ |
| 1.3 Classification (OPERATIONAL) | ✅ |
| 1.4 Allowed query patterns (7) | ✅ |
| 1.5 Forbidden query patterns (5) | ✅ |
| 1.6 Escape hatches (5) | ✅ |
| 1.7 Doctrine statement (7 points) | ✅ |
| 1.8 No dashboard/button leaks | ✅ |

**Scope is FROZEN. Proceeding to Phase 2.**
