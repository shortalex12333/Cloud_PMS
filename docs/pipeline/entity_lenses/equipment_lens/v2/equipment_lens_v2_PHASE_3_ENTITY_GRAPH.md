# Equipment Lens v2 - PHASE 3: ENTITY GRAPH

**Goal**: Document → Tests → Code → Verify — backend defines actions, signatures, and RLS; no UI authority.

**Lens**: Equipment

**Date**: 2026-01-27

---

## PURPOSE

Phase 3 maps all entity relationships, escape hatches, and cross-lens interactions. Equipment is the **anchor entity** for operational work.

---

## ENTITY RELATIONSHIP DIAGRAM

```
                              ┌─────────────────────────────────────┐
                              │           EQUIPMENT LENS            │
                              │                                     │
                              │  ┌─────────────────────────────┐    │
                              │  │      pms_equipment          │    │
                              │  │  - id (PK)                  │    │
                              │  │  - yacht_id (RLS)           │    │
                              │  │  - parent_id (self-ref)     │    │
                              │  │  - name, code, status       │    │
                              │  │  - criticality, system_type │    │
                              │  │  - attention_flag           │    │
                              │  └──────────┬──────────────────┘    │
                              │             │                       │
                              │             │ parent_id             │
                              │             ▼                       │
                              │  ┌─────────────────────────────┐    │
                              │  │    pms_equipment (child)    │    │
                              │  │    (hierarchical)           │    │
                              │  └─────────────────────────────┘    │
                              │                                     │
                              └──────────────┬──────────────────────┘
                                             │
                    ┌────────────────────────┼────────────────────────┐
                    │                        │                        │
                    ▼                        ▼                        ▼
    ┌───────────────────────┐  ┌───────────────────────┐  ┌───────────────────────┐
    │  pms_equipment_parts  │  │      pms_notes        │  │   pms_attachments     │
    │       _bom            │  │                       │  │                       │
    │  - equipment_id (FK)  │  │  - equipment_id (FK)  │  │  - entity_type='equip'│
    │  - part_id (FK)       │  │  - text               │  │  - entity_id (FK)     │
    │  - quantity_required  │  │  - note_type          │  │  - storage_path       │
    └───────────┬───────────┘  │  - requires_ack       │  └───────────────────────┘
                │              └───────────────────────┘
                │
                ▼
    ┌───────────────────────┐
    │      pms_parts        │
    │     (Part Lens)       │
    │  - part_number        │
    │  - stock levels       │
    └───────────────────────┘


                   ESCAPE HATCHES (outbound from Equipment Lens)
                   ═══════════════════════════════════════════

    ┌─────────────────────┐           ┌─────────────────────┐
    │     FAULT LENS      │◄──────────│   Equipment Lens    │
    │                     │  view_    │                     │
    │  - pms_faults       │  equipment│  - pms_equipment    │
    │  - equipment_id FK  │  _faults  │                     │
    └─────────────────────┘           └──────────┬──────────┘
                                                 │
    ┌─────────────────────┐                      │ create_work_order_
    │   WORK ORDER LENS   │◄─────────────────────┤ for_equipment
    │                     │                      │
    │  - pms_work_orders  │                      │ view_equipment_
    │  - equipment_id FK  │◄─────────────────────┤ work_orders
    └─────────────────────┘                      │
                                                 │
    ┌─────────────────────┐                      │
    │     PART LENS       │◄─────────────────────┤ view_equipment_parts
    │                     │                      │
    │  - pms_parts        │                      │
    │  - via BOM          │                      │
    └─────────────────────┘                      │
                                                 │
    ┌─────────────────────┐                      │
    │   DOCUMENT LENS     │◄─────────────────────┘ (attachment click)
    │                     │
    │  - doc_metadata     │
    │  - storage.objects  │
    └─────────────────────┘


                   INBOUND REFERENCES (to Equipment Lens)
                   ═══════════════════════════════════════

    ┌─────────────────────┐
    │     FAULT LENS      │───────────┐
    │                     │           │
    │  fault.equipment_id │───────────┼──────► pms_equipment.id
    └─────────────────────┘           │
                                      │
    ┌─────────────────────┐           │
    │   WORK ORDER LENS   │───────────┤
    │                     │           │
    │  wo.equipment_id    │───────────┼──────► pms_equipment.id
    └─────────────────────┘           │
                                      │
    ┌─────────────────────┐           │
    │    RECEIVING LENS   │───────────┘
    │                     │
    │  (parts received    │
    │   for equipment)    │
    └─────────────────────┘
```

---

## ESCAPE HATCHES

### Definition

Escape hatches are controlled exits from the Equipment Lens to other lenses. They:
- Transfer focus to a different entity type
- Pre-fill context from the source entity
- Maintain navigation breadcrumb

### Escape Hatch Matrix

| Trigger | Target Lens | Context Passed | User Action |
|---------|-------------|----------------|-------------|
| `view_equipment_faults` | Fault Lens | equipment_id | Click "View Faults" |
| `view_equipment_work_orders` | Work Order Lens | equipment_id | Click "View Work Orders" |
| `create_work_order_for_equipment` | Work Order Lens | equipment_id, name | Click "Create WO" |
| `view_equipment_parts` | Part Lens | part_id (from BOM) | Click part in BOM |
| Attachment click | Document Lens | document_id | Click attachment |
| Note author click | Crew Lens | person_id | Click author name |

### Escape Flow: Equipment → Work Order

```
┌─────────────────────────────────────────────────────────────────┐
│  EQUIPMENT LENS - Focused on "Generator #2"                     │
│                                                                 │
│  Status: FAILED    Attention: "Alternator bearing failure"     │
│                                                                 │
│  ACTIONS:                                                       │
│  [Update Status] [Add Note] [Attach Photo] [Create Work Order] │
│                                                     ▲           │
└─────────────────────────────────────────────────────│───────────┘
                                                      │
                                                      │ User clicks
                                                      │
┌─────────────────────────────────────────────────────│───────────┐
│  ACTION MODAL: create_work_order_for_equipment      │           │
│                                                                 │
│  Pre-filled:                                                    │
│    equipment_id: "generator-2-uuid"                             │
│    equipment_name: "Generator #2" (display only)                │
│                                                                 │
│  User provides:                                                 │
│    title: "Alternator bearing replacement"                      │
│    type: [corrective ▼]                                         │
│    priority: [critical ▼]                                       │
│    fault_severity: [critical ▼]  (shown because type=corrective)│
│                                                                 │
│  [Cancel]                                    [Create Work Order]│
└─────────────────────────────────────────────────────────────────┘
                                                      │
                                                      │ Submit
                                                      ▼
┌─────────────────────────────────────────────────────────────────┐
│  WORK ORDER LENS - Focused on "WO-2026-0143"                    │
│                                                                 │
│  Equipment: Generator #2                                        │
│  Title: Alternator bearing replacement                          │
│  Type: Corrective    Priority: Critical                         │
│  Linked Fault: FLT-2026-0089 (auto-created)                     │
│                                                                 │
│  ACTIONS:                                                       │
│  [Add Note] [Assign] [Add Parts] [Complete] [Back to Equipment] │
│                                                     ▲           │
│                                                     │           │
│                                            breadcrumb return    │
└─────────────────────────────────────────────────────────────────┘
```

---

## EQUIPMENT HIERARCHY

### Self-Referential Structure

Equipment supports unlimited nesting via `parent_id`:

```
yacht_id: "yacht-uuid"
│
├── Main Engine #1 (id: aaa, parent_id: NULL)
│   ├── Turbocharger (parent_id: aaa)
│   ├── Fuel Injection System (id: bbb, parent_id: aaa)
│   │   ├── Fuel Pump (parent_id: bbb)
│   │   └── Injector Rail (parent_id: bbb)
│   └── Cooling System (id: ccc, parent_id: aaa)
│       └── Heat Exchanger (parent_id: ccc)
│
├── Main Engine #2 (parent_id: NULL)
│   └── ... (similar structure)
│
├── Generator #1 (parent_id: NULL)
│   └── ...
│
└── Generator #2 (parent_id: NULL)
    └── Alternator (parent_id: gen2-id)  ◄── The failed component
```

### Hierarchy Queries

**Get Children**:
```sql
SELECT * FROM pms_equipment
WHERE parent_id = :equipment_id
  AND yacht_id = public.get_user_yacht_id()
  AND deleted_at IS NULL
ORDER BY name;
```

**Get Full Subtree (Recursive)**:
```sql
WITH RECURSIVE equipment_tree AS (
    -- Base: selected equipment
    SELECT id, name, parent_id, 0 AS depth
    FROM pms_equipment
    WHERE id = :equipment_id
      AND yacht_id = public.get_user_yacht_id()
      AND deleted_at IS NULL

    UNION ALL

    -- Recursive: children
    SELECT e.id, e.name, e.parent_id, et.depth + 1
    FROM pms_equipment e
    JOIN equipment_tree et ON e.parent_id = et.id
    WHERE e.yacht_id = public.get_user_yacht_id()
      AND e.deleted_at IS NULL
)
SELECT * FROM equipment_tree ORDER BY depth, name;
```

**Get Ancestors (Path to Root)**:
```sql
WITH RECURSIVE ancestors AS (
    -- Base: selected equipment
    SELECT id, name, parent_id, 0 AS level
    FROM pms_equipment
    WHERE id = :equipment_id
      AND yacht_id = public.get_user_yacht_id()

    UNION ALL

    -- Recursive: parents
    SELECT e.id, e.name, e.parent_id, a.level + 1
    FROM pms_equipment e
    JOIN ancestors a ON e.id = a.parent_id
    WHERE e.yacht_id = public.get_user_yacht_id()
)
SELECT * FROM ancestors ORDER BY level DESC;
-- Returns: Main Engine #1 → Fuel Injection System → Fuel Pump
```

### Hierarchy UI Behavior

| User Action | System Response |
|-------------|-----------------|
| Focus on parent | Show children in expandable tree |
| Focus on child | Show breadcrumb path to root |
| Action on parent | Action applies to parent only (not children) |
| Status change on parent | Does NOT cascade to children |
| Decommission parent | Children remain (orphaned but valid) |

---

## CROSS-LENS DEPENDENCIES

### Equipment → Fault

| Aspect | Dependency |
|--------|------------|
| FK Relationship | `pms_faults.equipment_id → pms_equipment.id` |
| When Created | Corrective/breakdown WO auto-creates fault |
| Query Pattern | Filter faults by equipment_id |
| UI Integration | "View Faults" button shows fault list |

### Equipment → Work Order

| Aspect | Dependency |
|--------|------------|
| FK Relationship | `pms_work_orders.equipment_id → pms_equipment.id` |
| When Created | `create_work_order_for_equipment` action |
| Query Pattern | Filter WOs by equipment_id |
| UI Integration | "View Work Orders" and "Create WO" buttons |

### Equipment → Parts (BOM)

| Aspect | Dependency |
|--------|------------|
| FK Relationship | `pms_equipment_parts_bom.equipment_id → pms_equipment.id` |
| When Created | `link_part_to_equipment` action |
| Query Pattern | Join BOM with parts for equipment |
| UI Integration | Parts panel with stock levels |

### Equipment → Documents

| Aspect | Dependency |
|--------|------------|
| FK Relationship | `pms_attachments.entity_id → pms_equipment.id` WHERE entity_type='equipment' |
| When Created | `attach_file_to_equipment` action |
| Query Pattern | Filter attachments by entity_type + entity_id |
| Storage Path | `{yacht_id}/equipment/{equipment_id}/{filename}` |

---

## LEDGER INTEGRATION

### Entity Type Convention

```sql
-- All equipment audit entries use:
entity_type = 'equipment'
```

### Audit Trail Query

```sql
SELECT
    al.created_at,
    al.action,
    al.actor_role,
    al.old_values,
    al.new_values,
    al.signature,
    aup.name AS actor_name
FROM pms_audit_log al
LEFT JOIN auth_users_profiles aup ON al.actor_user_id = aup.id
WHERE al.yacht_id = public.get_user_yacht_id()
  AND al.entity_type = 'equipment'
  AND al.entity_id = :equipment_id
ORDER BY al.created_at DESC;
```

### Equipment-Specific Events

| Event | Action ID | Signature |
|-------|-----------|-----------|
| Status changed | `update_equipment_status` | `{}` |
| Note added | `add_equipment_note` | `{}` |
| File attached | `attach_file_to_equipment` | `{}` |
| Work order created | `create_work_order_for_equipment` | `{}` |
| Part linked | `link_part_to_equipment` | `{}` |
| Attention flagged | `flag_equipment_attention` | `{}` |
| **Decommissioned** | `decommission_equipment` | **{signature JSON}** |

---

## NOTIFICATION TRIGGERS

### Equipment → Notifications

| Trigger | Recipients | Topic | Level | CTA |
|---------|------------|-------|-------|-----|
| Status → failed (critical) | captain, chief_engineer | equipment_critical_failure | critical | Focus equipment |
| Status → failed (non-critical) | chief_engineer | equipment_failure | warning | Focus equipment |
| Note with requires_ack | chief_engineer | equipment_note_ack | info | View note |
| Attention flag set | chief_engineer | equipment_attention | warning | Focus equipment |
| Decommissioned | captain, manager | equipment_decommissioned | info | View audit |

---

## NEXT PHASE

Proceed to **PHASE 4: ACTIONS** to:
- Define complete action specifications
- Specify field classifications
- Document gating rules
- Define registry entries

---

**END OF PHASE 3**
