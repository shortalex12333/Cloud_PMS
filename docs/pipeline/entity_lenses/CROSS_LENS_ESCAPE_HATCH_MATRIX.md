# Cross-Lens Escape Hatch Matrix

**Status**: v1 - PRODUCTION READY
**Last Updated**: 2026-01-25
**Purpose**: Defines all valid transitions between Entity Lenses

---

# OVERVIEW

Escape hatches allow users to navigate from one focused entity to a related entity in a different lens. These are **read-only transitions** - no data is modified during navigation.

## Design Principles

1. **User Intent Preservation**: When escaping to another lens, the user's context (why they navigated) is preserved
2. **Bidirectional Where Sensible**: If A→B exists, consider if B→A makes sense
3. **No Orphan Navigation**: Every escape hatch must land on a valid entity
4. **Query Efficiency**: Escape hatches use indexed foreign keys

---

# ESCAPE HATCH MATRIX

## Full Matrix

| From Lens | To Lens | Trigger Action | Data Passed | Query Pattern |
|-----------|---------|----------------|-------------|---------------|
| **Work Order** | Equipment | `view_equipment` | equipment_id | `equipment_id = :equipment_id` |
| **Work Order** | Fault | `view_linked_fault` | fault_id | `fault_id = :fault_id` |
| **Work Order** | Part | `view_parts_used` | work_order_id | `work_order_id IN pms_part_usage` |
| **Work Order** | Crew | `view_assigned_crew` | assigned_to | `id = :assigned_to` |
| **Fault** | Work Order | `view_linked_work_order` | work_order_id | `work_order_id = :work_order_id` |
| **Fault** | Equipment | `view_equipment` | equipment_id | `equipment_id = :equipment_id` |
| **Equipment** | Fault | `view_equipment_faults` | equipment_id | `equipment_id = :equipment_id` |
| **Equipment** | Work Order | `view_equipment_work_orders` | equipment_id | `equipment_id = :equipment_id` |
| **Equipment** | Part | `view_compatible_parts` | equipment_id | `equipment_id IN pms_equipment_parts_bom` |
| **Equipment** | Document | `view_equipment_documents` | equipment_id | `equipment_ids @> ARRAY[:equipment_id]` |
| **Equipment** | Certificate | `view_equipment_certificates` | equipment_id | `equipment_id = :equipment_id` |
| **Part** | Equipment | `view_compatible_equipment` | part_id | `part_id IN pms_equipment_parts_bom` |
| **Part** | Work Order | `view_part_usage_history` | part_id | `part_id IN pms_part_usage → work_order_id` |
| **Part** | Shopping List | `view_in_shopping_list` | part_id | `part_id = :part_id` |
| **Shopping List** | Part | `view_part_details` | part_id | `part_id = :part_id` |
| **Shopping List** | Work Order | `view_source_work_order` | source_work_order_id | `work_order_id = :source_work_order_id` |
| **Shopping List** | Receiving | `view_receiving_event` | source_receiving_id | `receiving_event_id = :source_receiving_id` |
| **Receiving** | Part | `view_line_item_part` | part_id | `part_id = :part_id` |
| **Receiving** | Shopping List | `view_shopping_list_item` | shopping_list_item_id | `shopping_list_item_id = :shopping_list_item_id` |
| **Receiving** | Equipment | `view_installed_to_equipment` | installed_to_equipment_id | `equipment_id = :installed_to_equipment_id` |
| **Document** | Equipment | `view_linked_equipment` | equipment_ids | `id = ANY(:equipment_ids)` |
| **Certificate** | Document | `view_certificate_document` | document_id | `document_id = :document_id` |
| **Certificate** | Equipment | `view_certificate_equipment` | equipment_id | `equipment_id = :equipment_id` |
| **Crew** | Work Order | `view_assigned_work_orders` | user_id | `assigned_to = :user_id` |

---

# LENS-BY-LENS ESCAPE HATCHES

## Work Order Lens

**Outbound Escapes**:
| Action | Destination | FK Used |
|--------|-------------|---------|
| View Equipment | Equipment Lens | `pms_work_orders.equipment_id` |
| View Linked Fault | Fault Lens | `pms_work_orders.fault_id` |
| View Parts Used | Part Lens (list) | `pms_part_usage.work_order_id` |
| View Assigned Crew | Crew Lens | `pms_work_orders.assigned_to` |

**Inbound Escapes** (others escape TO Work Order):
- Equipment → view_equipment_work_orders
- Fault → view_linked_work_order
- Part → view_part_usage_history
- Shopping List → view_source_work_order
- Crew → view_assigned_work_orders

---

## Equipment Lens

**Outbound Escapes**:
| Action | Destination | FK Used |
|--------|-------------|---------|
| View Faults | Fault Lens (list) | `pms_faults.equipment_id` |
| View Work Orders | WO Lens (list) | `pms_work_orders.equipment_id` |
| View Compatible Parts | Part Lens (list) | `pms_equipment_parts_bom.equipment_id` |
| View Documents | Document Lens (list) | `doc_metadata.equipment_ids` |
| View Certificates | Certificate Lens (list) | `pms_certificates.equipment_id` |

**Inbound Escapes**:
- Work Order → view_equipment
- Fault → view_equipment
- Part → view_compatible_equipment
- Certificate → view_certificate_equipment
- Receiving → view_installed_to_equipment
- Document → view_linked_equipment

---

## Fault Lens

**Outbound Escapes**:
| Action | Destination | FK Used |
|--------|-------------|---------|
| View Linked WO | Work Order Lens | `pms_faults.work_order_id` |
| View Equipment | Equipment Lens | `pms_faults.equipment_id` |

**Inbound Escapes**:
- Work Order → view_linked_fault
- Equipment → view_equipment_faults

---

## Part Lens

**Outbound Escapes**:
| Action | Destination | FK Used |
|--------|-------------|---------|
| View Compatible Equipment | Equipment Lens (list) | `pms_equipment_parts_bom.part_id` |
| View Usage History | Work Order Lens (list) | `pms_part_usage.part_id` |
| View in Shopping List | Shopping List Lens | `pms_shopping_list_items.part_id` |

**Inbound Escapes**:
- Equipment → view_compatible_parts
- Work Order → view_parts_used
- Shopping List → view_part_details
- Receiving → view_line_item_part

---

## Shopping List Lens

**Outbound Escapes**:
| Action | Destination | FK Used |
|--------|-------------|---------|
| View Part Details | Part Lens | `pms_shopping_list_items.part_id` |
| View Source WO | Work Order Lens | `pms_shopping_list_items.source_work_order_id` |
| View Receiving Event | Receiving Lens | `pms_shopping_list_items.source_receiving_id` |

**Inbound Escapes**:
- Part → view_in_shopping_list
- Receiving → view_shopping_list_item

---

## Receiving Lens

**Outbound Escapes**:
| Action | Destination | FK Used |
|--------|-------------|---------|
| View Line Item Part | Part Lens | `pms_receiving_line_items.part_id` |
| View Shopping List Item | Shopping List Lens | `pms_receiving_line_items.shopping_list_item_id` |
| View Installed Equipment | Equipment Lens | `pms_receiving_line_items.installed_to_equipment_id` |

**Inbound Escapes**:
- Shopping List → view_receiving_event

---

## Document Lens

**Outbound Escapes**:
| Action | Destination | FK Used |
|--------|-------------|---------|
| View Linked Equipment | Equipment Lens (list) | `doc_metadata.equipment_ids` (array) |

**Inbound Escapes**:
- Equipment → view_equipment_documents
- Certificate → view_certificate_document

---

## Crew Lens

**Outbound Escapes**:
| Action | Destination | FK Used |
|--------|-------------|---------|
| View Assigned WOs | Work Order Lens (list) | `pms_work_orders.assigned_to` |

**Inbound Escapes**:
- Work Order → view_assigned_crew

---

## Certificate Lens

**Outbound Escapes**:
| Action | Destination | FK Used |
|--------|-------------|---------|
| View Document | Document Lens | `pms_certificates.document_id` |
| View Equipment | Equipment Lens | `pms_certificates.equipment_id` |

**Inbound Escapes**:
- Equipment → view_equipment_certificates

---

# VISUAL GRAPH

```
                    ┌─────────────────────────────────────────────────────────────┐
                    │                        DOCUMENT                              │
                    └─────────────────────────────────────────────────────────────┘
                                              ↑
                                              │ equipment_ids
                    ┌─────────────────────────┼─────────────────────────────────┐
                    │                         │                                  │
                    ↓                         │                                  │
    ┌───────────────────────────┐            │            ┌───────────────────────────┐
    │       CERTIFICATE         │←───────────┼───────────→│       EQUIPMENT           │
    └───────────────────────────┘            │            └───────────────────────────┘
              ↑ equipment_id                 │                ↑        ↑        ↑
              │                              │                │        │        │
              └──────────────────────────────┘                │        │        │
                                                              │        │        │
    ┌───────────────────────────┐        equipment_id         │        │        │ equipment_id
    │          FAULT            │←────────────────────────────┘        │        └────────────┐
    └───────────────────────────┘                                      │                      │
              ↑        ↓                                               │                      │
        fault_id    work_order_id                                      │ part_id              │
              ↑        ↓                                               │ (via BOM)            │
    ┌───────────────────────────┐    assigned_to    ┌─────────────────┴───────────┐          │
    │       WORK ORDER          │←─────────────────→│          CREW               │          │
    └───────────────────────────┘                   └─────────────────────────────┘          │
              ↑        ↓                                                                      │
       work_order_id  part_id (via usage)                                                    │
              ↑        ↓                                                                      │
    ┌───────────────────────────┐                                                            │
    │          PART             │←───────────────────────────────────────────────────────────┘
    └───────────────────────────┘
              ↑        ↓
        part_id    shopping_list_item_id
              ↑        ↓
    ┌───────────────────────────┐
    │     SHOPPING LIST         │
    └───────────────────────────┘
              ↑        ↓
    source_receiving_id   part_id
              ↑        ↓
    ┌───────────────────────────┐
    │       RECEIVING           │
    └───────────────────────────┘
```

---

# IMPLEMENTATION NOTES

## Frontend Navigation

When an escape hatch is triggered:

1. **Store Context**: Remember the source entity and lens
2. **Execute Query**: Run the escape hatch query to get target entity
3. **Navigate**: Switch to target lens with entity focused
4. **Enable Back**: Allow return to previous context via breadcrumb

## Query Optimization

All escape hatch queries use indexed foreign keys:

```sql
-- Example: Equipment → Faults (escape hatch query)
SELECT f.*
FROM pms_faults f
WHERE f.equipment_id = :equipment_id
  AND f.yacht_id = public.get_user_yacht_id()  -- RLS enforcement
ORDER BY f.detected_at DESC;

-- Uses: idx_faults_equipment_id
```

## Null Handling

If escape hatch FK is NULL:
- Show "No [entity] linked" message
- Disable the escape hatch action in UI
- Example: Work Order with `fault_id = NULL` → "No fault linked to this work order"

---

# SUMMARY

| Lens | Outbound Count | Inbound Count |
|------|----------------|---------------|
| Work Order | 4 | 5 |
| Equipment | 5 | 6 |
| Fault | 2 | 2 |
| Part | 3 | 4 |
| Shopping List | 3 | 2 |
| Receiving | 3 | 1 |
| Document | 1 | 2 |
| Crew | 1 | 1 |
| Certificate | 2 | 1 |

**Total Escape Hatches**: 24 unique transitions

---

**END OF CROSS-LENS ESCAPE HATCH MATRIX**
