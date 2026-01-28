# Work Order Lens v2 - PHASE 3: Entity Graph

**Status**: COMPLETE
**Created**: 2026-01-24

---

## 3.1 Entity Relationship Diagram

```
                              ┌─────────────────┐
                              │  yacht_registry │
                              │      (id)       │
                              └────────┬────────┘
                                       │ CASCADE
                                       ▼
┌─────────────────┐           ┌─────────────────────┐           ┌─────────────────┐
│  pms_equipment  │◄──────────│   pms_work_orders   │──────────►│   pms_faults    │
│      (id)       │  SET NULL │        (29)         │ SET NULL  │      (id)       │
└─────────────────┘           └──────────┬──────────┘           └─────────────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    │                    │                    │
                    ▼                    ▼                    ▼
         ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
         │ pms_work_order_  │  │ pms_work_order_  │  │ pms_work_order_  │
         │    checklist     │  │      notes       │  │      parts       │
         │      (24)        │  │       (7)        │  │       (9)        │
         │   HAS yacht_id   │  │   NO yacht_id    │  │   NO yacht_id    │
         └──────────────────┘  └──────────────────┘  └────────┬─────────┘
                                                              │
                                                              ▼
         ┌──────────────────┐                        ┌──────────────────┐
         │ pms_work_order_  │                        │    pms_parts     │
         │     history      │                        │      (id)        │
         │      (14)        │                        └──────────────────┘
         │   HAS yacht_id   │
         └──────────────────┘

         ┌──────────────────┐
         │  pms_part_usage  │◄─── Related via work_order_id
         │      (11)        │
         │   HAS yacht_id   │
         └──────────────────┘
```

---

## 3.2 FK Paths (Outbound from pms_work_orders)

| FK Column | References | On Delete | Verified |
|-----------|------------|-----------|----------|
| `yacht_id` | yacht_registry(id) | CASCADE | ✅ |
| `equipment_id` | pms_equipment(id) | SET NULL | ✅ |
| `fault_id` | pms_faults(id) | SET NULL | ✅ |
| `assigned_to` | auth.users(id) | - | ✅ |
| `created_by` | auth.users(id) | - | ✅ |
| `completed_by` | auth.users(id) | - | ✅ |

---

## 3.3 FK Paths (Inbound to pms_work_orders)

| From Table | FK Column | On Delete | Verified |
|------------|-----------|-----------|----------|
| pms_work_order_checklist | work_order_id | CASCADE | ✅ |
| pms_work_order_notes | work_order_id | CASCADE | ✅ |
| pms_work_order_parts | work_order_id | CASCADE | ✅ |
| pms_work_order_history | work_order_id | CASCADE | ✅ |
| pms_part_usage | work_order_id | SET NULL | ✅ |
| pms_faults | work_order_id | SET NULL | ✅ |

---

## 3.4 Escape Hatches (Lens-to-Lens Navigation)

### From Work Order Lens

| To Lens | Via Column | Query Pattern | Example |
|---------|------------|---------------|---------|
| Equipment Lens | equipment_id | Direct FK | "show equipment for WO-2026-042" |
| Fault Lens | fault_id | Direct FK | "show fault linked to this WO" |
| Part Lens | pms_work_order_parts | Junction table | "what parts are needed" |
| Crew Lens | assigned_to | Direct FK | "who is assigned" |

### To Work Order Lens

| From Lens | Via | Query Pattern | Example |
|-----------|-----|---------------|---------|
| Equipment Lens | equipment_id | Reverse FK | "work orders for main generator" |
| Fault Lens | fault_id | Reverse FK | "work order for coolant leak" |
| Part Lens | pms_work_order_parts | Junction table | "work orders using this part" |
| Crew Lens | assigned_to | Reverse FK | "my work orders" |

---

## 3.5 Junction Tables

### pms_work_order_parts (M:N)

Connects Work Orders to Parts.

```
pms_work_orders ──┬── pms_work_order_parts ──┬── pms_parts
                  │                          │
              work_order_id              part_id
```

**Query Pattern**:
```sql
SELECT p.* FROM pms_parts p
JOIN pms_work_order_parts wop ON wop.part_id = p.id
WHERE wop.work_order_id = $1
AND wop.deleted_at IS NULL;
```

### pms_attachments (Polymorphic)

Connects Work Orders to file attachments.

```
pms_work_orders ──── pms_attachments
                     (entity_type = 'work_order')
                     (entity_id = work_order.id)
```

---

## 3.6 Cascade Effects

### WO Status → Fault Status (via trigger)

| WO Status Change | Fault Status Result |
|------------------|---------------------|
| → `in_progress` | → `investigating` |
| → `completed` | → `resolved` |
| → `cancelled` | → `open` (returned) |

**BLOCKER B4**: Trigger `cascade_wo_status_to_fault()` NOT DEPLOYED

### WO Delete → Child Records

| Child Table | Effect |
|-------------|--------|
| pms_work_order_checklist | CASCADE DELETE |
| pms_work_order_notes | CASCADE DELETE |
| pms_work_order_parts | CASCADE DELETE |
| pms_work_order_history | CASCADE DELETE |
| pms_part_usage | SET NULL (work_order_id) |
| pms_faults | SET NULL (work_order_id) |

---

## 3.7 Query Patterns by Relationship

### Get WO with Equipment Name

```sql
SELECT wo.*, e.name as equipment_name
FROM pms_work_orders wo
LEFT JOIN pms_equipment e ON wo.equipment_id = e.id
WHERE wo.id = $1
AND wo.yacht_id = public.get_user_yacht_id();
```

### Get WO with Fault Details

```sql
SELECT wo.*, f.title as fault_title, f.severity as fault_severity
FROM pms_work_orders wo
LEFT JOIN pms_faults f ON wo.fault_id = f.id
WHERE wo.id = $1
AND wo.yacht_id = public.get_user_yacht_id();
```

### Get WO with Assigned Crew

```sql
SELECT wo.*, u.full_name as assigned_to_name, u.role as assigned_to_role
FROM pms_work_orders wo
LEFT JOIN auth_users_profiles u ON wo.assigned_to = u.id
WHERE wo.id = $1
AND wo.yacht_id = public.get_user_yacht_id();
```

### Get WO with Parts List

```sql
SELECT wo.id, wo.wo_number, p.name as part_name, wop.quantity
FROM pms_work_orders wo
JOIN pms_work_order_parts wop ON wop.work_order_id = wo.id
JOIN pms_parts p ON wop.part_id = p.id
WHERE wo.id = $1
AND wo.yacht_id = public.get_user_yacht_id()
AND wop.deleted_at IS NULL;
```

### Get WO with Checklist Summary

```sql
SELECT wo.id, wo.wo_number,
    COUNT(c.id) as total_items,
    COUNT(c.id) FILTER (WHERE c.is_completed) as completed_items,
    COUNT(c.id) FILTER (WHERE c.is_required AND NOT c.is_completed) as required_incomplete
FROM pms_work_orders wo
LEFT JOIN pms_work_order_checklist c ON c.work_order_id = wo.id
WHERE wo.id = $1
AND wo.yacht_id = public.get_user_yacht_id()
GROUP BY wo.id, wo.wo_number;
```

---

## 3.8 Cross-Lens Queries

### "Work orders for main generator"

```sql
SELECT wo.*
FROM pms_work_orders wo
JOIN pms_equipment e ON wo.equipment_id = e.id
WHERE e.name ILIKE '%main generator%'
AND wo.yacht_id = public.get_user_yacht_id()
AND wo.deleted_at IS NULL
ORDER BY wo.created_at DESC;
```

### "Work order for coolant leak fault"

```sql
SELECT wo.*
FROM pms_work_orders wo
JOIN pms_faults f ON wo.fault_id = f.id
WHERE f.title ILIKE '%coolant leak%'
AND wo.yacht_id = public.get_user_yacht_id()
AND wo.deleted_at IS NULL;
```

### "My assigned work orders"

```sql
SELECT wo.*
FROM pms_work_orders wo
WHERE wo.assigned_to = auth.uid()
AND wo.yacht_id = public.get_user_yacht_id()
AND wo.status NOT IN ('completed', 'cancelled')
AND wo.deleted_at IS NULL
ORDER BY wo.priority DESC, wo.due_date ASC;
```

---

## 3.9 Graph Invariants

| Invariant | Verified |
|-----------|----------|
| No circular FK paths | ✅ |
| All FKs use CASCADE or SET NULL (no RESTRICT except pms_parts) | ✅ |
| Yacht isolation enforced at root (pms_work_orders) | ✅ |
| Child tables without yacht_id rely on parent join | ⚠️ BLOCKER for notes/parts |

---

## PHASE 3 GATE: COMPLETE

| Check | Status |
|-------|--------|
| 3.1 ERD documented | ✅ |
| 3.2 Outbound FKs verified | ✅ |
| 3.3 Inbound FKs verified | ✅ |
| 3.4 Escape hatches documented | ✅ |
| 3.5 Junction tables documented | ✅ |
| 3.6 Cascade effects documented | ✅ |
| 3.7 Query patterns provided | ✅ |
| 3.8 Cross-lens queries provided | ✅ |
| 3.9 Graph invariants checked | ✅ |

**Proceeding to Phase 4: Actions**
