# Inventory Item Lens - Phase 0: Extraction Gate

**Status**: Draft v1
**Last Updated**: 2026-01-27
**Author**: Full Stack Engineer

---

## 1. Lens Identification

### Entity Type
**Inventory Item** (Part, Spare Part, Consumable)

### Canonical Table
`pms_parts`

### Domain
`inventory`

### Entity Type Code
`part` (used in URLs, audit logs, entity extraction)

---

## 2. Extraction Gate Criteria

The Inventory Item lens activates when **ALL** of the following are true:

### 2.1 Entity Recognition

| Trigger | Source | Example |
|---------|--------|---------|
| Search result click | Search pipeline returns `entity_type: "part"` | User clicks "Oil Filter (PN: OF-1234)" |
| Direct URL | URL contains `/parts/<uuid>` or `?focus=part:<uuid>` | Deep link shared by crew |
| Related link | FK navigation from Work Order, Equipment, Shopping List | "View Part" button |
| Context resolution | Entity extraction resolves part from query | "check oil filter stock" |

### 2.2 Entity Validation

Before lens activation, backend validates:
```sql
SELECT EXISTS (
    SELECT 1 FROM pms_parts
    WHERE id = $entity_id
    AND yacht_id = public.get_user_yacht_id()
    AND deleted_at IS NULL  -- When soft delete implemented
) AS exists;
```

**If validation fails**:
- 404 response: "Part not found or not accessible"
- No lens activation
- User stays on previous view

### 2.3 User Authentication

- User must have valid JWT
- `yacht_id` extracted from token via `get_user_yacht_id()`
- RLS automatically filters to user's yacht

---

## 3. Activation Patterns

### 3.1 Search Query → Part Focus

**User Query**: "oil filter"

**Backend Response** (simplified):
```json
{
  "results": [
    {
      "entity_type": "part",
      "entity_id": "abc-123-...",
      "display": {
        "primary": "Oil Filter",
        "secondary": "PN: OF-1234 | Qty: 5 | Mann+Hummel"
      },
      "score": 0.95
    }
  ]
}
```

**User Action**: Click result → Lens activates

### 3.2 Direct Navigation

**URL Patterns**:
- `/parts/{uuid}` - Direct part view
- `/?focus=part:{uuid}` - Query string encoding for SPA state

**Backend Validates**: Part exists + yacht_id matches

### 3.3 Related Navigation (Escape Hatch Reversal)

| From Lens | Link Clicked | Result |
|-----------|--------------|--------|
| Work Order | "View Part" button | Part lens activates |
| Equipment | Part in BOM list | Part lens activates |
| Shopping List | Part name link | Part lens activates |
| Document | Part mentioned in manual | Part lens activates (if resolvable) |

### 3.4 Explicit Action Request

**User Query**: "log part usage" (literal action name)

**Backend Response**:
```json
{
  "results": [
    {
      "entity_type": "action",
      "action_id": "log_part_usage",
      "display": {
        "primary": "Log Part Usage",
        "secondary": "Record consumption of parts from inventory"
      },
      "requires_focus": true,
      "focus_entity_type": "part"
    }
  ]
}
```

**User Action**:
1. Click action → Modal prompts "Select a part"
2. User selects part → Modal prefills `part_id`
3. User completes form → Action executes

---

## 4. Entity Extraction for Auto-Population

When user query contains recognizable entities, backend extracts them for modal pre-fill:

### 4.1 Part Name Recognition

**Query**: "check hydraulic seal stock"
**Extracted**: `part_name_fragment = "hydraulic seal"`
**Pre-fill**: Part selector pre-filtered to "hydraulic seal*"

### 4.2 Equipment + Part Context

**Query**: "oil filter for generator 2"
**Extracted**:
- `part_name_fragment = "oil filter"`
- `equipment_name_fragment = "generator 2"`
**Pre-fill**:
- Part selector filtered
- `equipment_id` resolved and pre-filled in `log_part_usage` modal

### 4.3 Quantity Extraction

**Query**: "order 10 hydraulic seals"
**Extracted**:
- `part_name_fragment = "hydraulic seals"`
- `quantity = 10`
**Pre-fill**:
- Part selector filtered
- `quantity_requested = 10` in `add_to_shopping_list` modal

### 4.4 Action Name Extraction

**Query**: "log part usage"
**Extracted**: `action_id = "log_part_usage"`
**Result**: Action button rendered directly in search results

**Recognized Action Phrases**:
| Phrase | Action ID |
|--------|-----------|
| "log usage", "log part usage", "record usage" | `log_part_usage` |
| "add to shopping list", "order part", "reorder" | `add_to_shopping_list` |
| "update stock", "stock count", "inventory count" | `update_stock_count` |
| "edit part", "update part details" | `edit_part_details` |
| "usage history", "view usage" | `view_usage_history` |
| "archive part", "delete part", "remove part" | `archive_part` |

---

## 5. Lens Deactivation

The Inventory Item lens deactivates when:

| Trigger | Result |
|---------|--------|
| User clicks escape hatch to another entity | Target lens activates |
| User performs new search | Search results view |
| User clicks "Back" / browser back | Previous lens or search |
| Part is archived while viewing | Error + redirect to search |
| Session expires | Login redirect |

---

## 6. Non-Activating Scenarios

The Inventory Item lens does **NOT** activate for:

| Scenario | Correct Behavior |
|----------|------------------|
| Query returns no parts | "No results" message |
| Query returns multiple parts | Search results list (user must select one) |
| Part belongs to different yacht | 404 (RLS blocks) |
| Part is archived (soft-deleted) | 404 (deleted_at IS NOT NULL) |
| User requests shopping list view | Shopping List lens (different entity) |
| User requests equipment with parts | Equipment lens (parts shown in context) |

---

## 7. State Encoding

### 7.1 URL State

```
/parts/{part_uuid}
```

Or with query params:
```
/?focus=part:{part_uuid}&source=work_order:{wo_uuid}
```

### 7.2 Session State (Memory)

Frontend maintains:
```typescript
interface LensState {
  entity_type: "part";
  entity_id: string;
  source_context?: {
    type: "work_order" | "equipment" | "shopping_list" | "search";
    id?: string;
  };
  active_situations: SituationModifier[];
  dismissed_banners: string[];
}
```

---

## 8. Acceptance Criteria for Extraction Gate

| Test | Input | Expected |
|------|-------|----------|
| Valid part ID in URL | `/parts/{valid_uuid}` | Lens activates, part data loads |
| Invalid part ID | `/parts/{random_uuid}` | 404, lens does not activate |
| Part from different yacht | `/parts/{other_yacht_part}` | 404 (RLS blocks) |
| Search click | Click part in results | Lens activates |
| Action name search | "log part usage" | Action button renders |
| Quantity extraction | "order 5 oil filters" | Modal pre-fills qty=5 |

---

**STOP. Phase 0 complete. Proceed to Phase 1: Scope Definition.**
