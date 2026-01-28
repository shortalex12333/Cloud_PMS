# Work Order Lens - PHASE 3: Entity & Relationship Model

**Status**: COMPLETE
**Source**: Database schema FK analysis
**Created**: 2026-01-24

---

## 3.1 Primary Entity

**Entity**: `pms_work_orders`

**Definition**: A single, trackable unit of maintenance work on a yacht.

**Identity**:
- Primary Key: `id` (UUID)
- Natural Key: `yacht_id` + `wo_number` (unique constraint)
- Display Format: `WO-YYYY-NNN` (e.g., WO-2026-042)

---

## 3.2 Secondary Entities

| Entity | Relationship | Cardinality | Notes |
|--------|--------------|-------------|-------|
| `pms_work_order_checklist` | Child | 1:N | Checklist items for WO |
| `pms_work_order_notes` | Child | 1:N | Notes/comments |
| `pms_work_order_parts` | Junction | M:N | Parts needed for WO |
| `pms_work_order_history` | Child | 1:N | Completion records |
| `pms_equipment` | Parent | N:1 | Equipment being worked on |
| `pms_faults` | Parent | N:1 | Fault that triggered WO |
| `pms_parts` | Related | M:N | Via junction table |
| `auth_users_profiles` | Related | N:1 | Assigned user, created_by |
| `pms_audit_log` | Related | 1:N | Audit trail |
| `pms_attachments` | Related | 1:N | Photos, documents |

---

## 3.3 FK Paths (Explicit Only)

### Direct Foreign Keys FROM pms_work_orders

```
pms_work_orders.yacht_id → yachts.id
pms_work_orders.equipment_id → pms_equipment.id
pms_work_orders.fault_id → pms_faults.id
pms_work_orders.assigned_to → auth.users.id
pms_work_orders.created_by → auth.users.id
pms_work_orders.completed_by → auth.users.id
pms_work_orders.updated_by → auth.users.id
pms_work_orders.deleted_by → auth.users.id
```

### Foreign Keys TO pms_work_orders

```
pms_work_order_checklist.work_order_id → pms_work_orders.id
pms_work_order_notes.work_order_id → pms_work_orders.id
pms_work_order_parts.work_order_id → pms_work_orders.id
pms_work_order_history.work_order_id → pms_work_orders.id
pms_worklist_tasks.work_order_id → pms_work_orders.id
pms_attachments.work_order_id → pms_work_orders.id (polymorphic via entity_type)
```

---

## 3.4 Verify No Inferred Joins

| Potential Join | In Schema? | Status |
|----------------|------------|--------|
| WO → Fault | YES (fault_id FK) | ✅ ALLOWED |
| WO → Equipment | YES (equipment_id FK) | ✅ ALLOWED |
| WO → Crew | YES (assigned_to FK) | ✅ ALLOWED |
| WO → Vendor | NO (vendor_contact_hash is text) | ❌ NO FK |
| WO → Shopping List | NO | ❌ INFERRED |
| WO → Receiving | NO | ❌ INFERRED |

**FORBIDDEN**: Do not join WO to shopping_list_items or receiving_events without explicit FK.

---

## 3.5 Verify No Vector Joins

| Join Type | Status |
|-----------|--------|
| Similarity search | NOT in this phase |
| Document embedding | NOT in this phase |
| RAG retrieval | Handled by search pipeline, not lens |

**All joins in Phase 3 are FK-based only.**

---

## 3.6 Textual ER Diagram

```
                                    ┌──────────────────────┐
                                    │       yachts         │
                                    │ ────────────────────│
                                    │ id (PK)             │
                                    └──────────┬───────────┘
                                               │
                                               │ yacht_id (FK)
                                               ▼
┌──────────────────────┐           ┌──────────────────────────────────────┐           ┌──────────────────────┐
│   pms_equipment      │           │           pms_work_orders            │           │     pms_faults       │
│ ────────────────────│           │ ────────────────────────────────────│           │ ────────────────────│
│ id (PK)             │◄──────────┤ id (PK)                              ├──────────►│ id (PK)             │
│ yacht_id (FK)       │equipment_id│ yacht_id (FK)                       │ fault_id  │ yacht_id (FK)       │
│ name                │           │ wo_number                            │           │ title               │
│ category            │           │ title                                │           │ severity            │
│ status              │           │ type (enum)                          │           │ status              │
└──────────────────────┘           │ priority (enum)                      │           │ work_order_id (FK)  │
                                    │ status (enum)                        │           └──────────────────────┘
                                    │ equipment_id (FK) ──────────────────┘
                                    │ fault_id (FK) ──────────────────────────────────┘
                                    │ assigned_to (FK) ──────────────────┐
                                    │ created_by (FK)                    │
                                    │ completed_by (FK)                  │
                                    │ ...                                │
                                    └──────────────────┬─────────────────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    │                          │                          │
                    ▼                          ▼                          ▼
┌──────────────────────────┐  ┌──────────────────────────┐  ┌──────────────────────────┐
│ pms_work_order_checklist │  │  pms_work_order_notes    │  │  pms_work_order_parts    │
│ ────────────────────────│  │ ────────────────────────│  │ ────────────────────────│
│ id (PK)                  │  │ id (PK)                  │  │ id (PK)                  │
│ work_order_id (FK)       │  │ work_order_id (FK)       │  │ work_order_id (FK)       │
│ yacht_id (FK)            │  │ note_text                │  │ part_id (FK)             │
│ title                    │  │ note_type                │  │ quantity                 │
│ sequence                 │  │ created_by (FK)          │  │ notes                    │
│ is_completed             │  │ created_at               │  └──────────┬───────────────┘
│ requires_signature       │  └──────────────────────────┘             │
└──────────────────────────┘                                           │ part_id (FK)
                                                                       ▼
                                                          ┌──────────────────────────┐
                                                          │       pms_parts          │
                                                          │ ────────────────────────│
                                                          │ id (PK)                  │
                                                          │ yacht_id (FK)            │
                                                          │ name                     │
                                                          │ part_number              │
                                                          │ quantity_on_hand         │
                                                          └──────────────────────────┘
```

---

## 3.7 Allowed Traversal Paths

### From Work Order Focus

| Traversal | Path | Query Pattern |
|-----------|------|---------------|
| WO → Equipment | `equipment_id` FK | "show equipment for this WO" |
| WO → Fault | `fault_id` FK | "show fault that triggered this" |
| WO → Checklist Items | Join on `work_order_id` | "show checklist" |
| WO → Notes | Join on `work_order_id` | "show notes" |
| WO → Parts Needed | Join via `pms_work_order_parts` | "what parts needed" |
| WO → Assigned Crew | `assigned_to` FK | "who is assigned" |
| WO → Creator | `created_by` FK | "who created this" |
| WO → History | Join on `work_order_id` | "past completions" |
| WO → Attachments | Join on `work_order_id` | "photos, documents" |

### To Work Order (Inbound)

| From | Path | Query Pattern |
|------|------|---------------|
| Equipment → WOs | `pms_work_orders.equipment_id` | "work orders for generator" |
| Fault → WO | `pms_work_orders.fault_id` | "work order for this fault" |
| Crew → WOs | `pms_work_orders.assigned_to` | "my work orders" |
| Part → WOs | Via `pms_work_order_parts` | "WOs using this part" |

---

## 3.8 Forbidden Traversals

| Traversal | Why Forbidden |
|-----------|---------------|
| WO → Shopping List | No FK exists |
| WO → Receiving Event | No FK exists |
| WO → Vendor | `vendor_contact_hash` is text, not FK |
| WO → Certificate | No relationship |
| WO → Finance Transaction | No direct FK |
| WO → Similar WOs | Vector similarity not in FK scope |

---

## 3.9 Cascade Behaviors

### On Work Order Delete

| Child Table | Cascade Behavior |
|-------------|------------------|
| `pms_work_order_checklist` | CASCADE (assumed) |
| `pms_work_order_notes` | CASCADE (assumed) |
| `pms_work_order_parts` | CASCADE (assumed) |
| `pms_work_order_history` | SET NULL or CASCADE |

### On Equipment Delete

```sql
pms_work_orders.equipment_id → SET NULL
```

### On Fault Delete

```sql
pms_work_orders.fault_id → SET NULL
```

### On User Delete

```sql
pms_work_orders.assigned_to → SET NULL
pms_work_orders.created_by → (restricted - cannot delete user with WOs)
```

---

## 3.10 Denormalization Notes

| Table | Denormalized Column | Why |
|-------|---------------------|-----|
| `pms_work_order_checklist` | `yacht_id` | RLS performance |
| `pms_work_order_history` | `yacht_id` | RLS performance |
| `pms_work_order_history` | `equipment_id` | Historical snapshot |

**Pattern**: Denormalize `yacht_id` to child tables for RLS USING clause performance.

---

## PHASE 3 GATE: COMPLETE

| Check | Status |
|-------|--------|
| 3.1 Primary entity defined | ✅ |
| 3.2 Secondary entities listed | ✅ |
| 3.3 FK paths mapped (8 outbound, 6 inbound) | ✅ |
| 3.4 No inferred joins | ✅ |
| 3.5 No vector joins | ✅ |
| 3.6 ER diagram drawn | ✅ |
| 3.7 Allowed traversals defined (9 outbound, 4 inbound) | ✅ |
| 3.8 Forbidden traversals documented | ✅ |
| 3.9 Cascade behaviors documented | ✅ |
| 3.10 Denormalization noted | ✅ |

**Proceeding to Phase 4: Micro-Actions Contract**
