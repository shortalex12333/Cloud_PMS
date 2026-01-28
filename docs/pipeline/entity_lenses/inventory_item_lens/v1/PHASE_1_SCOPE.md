# Inventory Item Lens - Phase 1: Scope Definition

**Status**: Draft v1
**Last Updated**: 2026-01-27
**Author**: Full Stack Engineer

---

## 1. Lens Purpose

### Core Mission
Enable yacht crew to **view, track, and manage physical inventory items** stored onboard. This includes:
- Viewing part details and stock levels
- Logging part consumption (usage)
- Requesting reorders via shopping list
- Maintaining accurate inventory counts
- Linking parts to work orders and equipment

### Single Sentence Definition
> The Inventory Item lens provides focused access to a single part's information and all actions that can be performed on that part.

---

## 2. In-Scope

### 2.1 Data Display

| Data | Source | Notes |
|------|--------|-------|
| Part name, number, manufacturer | `pms_parts` | Always visible |
| Quantity on hand | `pms_parts.quantity_on_hand` | With color badge |
| Minimum quantity (reorder threshold) | `pms_parts.minimum_quantity` | Triggers Stock Risk |
| Physical location | `pms_parts.location` | Storage location on yacht |
| Unit of measure | `pms_parts.unit` | ea, L, box, etc. |
| Category | `pms_parts.category` | Part classification |
| Description | `pms_parts.description` | Long-form text |
| Model compatibility | `pms_parts.model_compatibility` | JSONB array |
| Last counted | `pms_parts.last_counted_at`, `last_counted_by` | Audit info |
| Supplier info | `pms_parts.metadata.supplier` | From JSONB |
| Unit cost | `pms_parts.metadata.unit_cost` | From JSONB |
| Lead time | `pms_parts.metadata.lead_time_days` | From JSONB |

### 2.2 Micro-Actions (7 Total)

| Action | Type | Signature | Role |
|--------|------|-----------|------|
| `log_part_usage` | MUTATE | No | All Crew |
| `add_to_shopping_list` | MUTATE | No | All Crew |
| `update_stock_count` | MUTATE | No | All Crew |
| `edit_part_details` | MUTATE | No | All Crew |
| `view_usage_history` | READ | No | All Crew |
| `attach_document` | MUTATE | No | All Crew |
| `archive_part` | MUTATE | **YES** | Captain, HoD, Purser |

### 2.3 Situation Modifiers (1)

| Situation | Trigger | UX Change |
|-----------|---------|-----------|
| Stock Risk | `quantity_on_hand < minimum_quantity` | Action reorder, banner, prefill |

### 2.4 Related Navigation (Escape Hatches)

| Link | Target Lens | Condition |
|------|-------------|-----------|
| Work Orders Using This Part | Work Order lens | `pms_work_order_parts.part_id` exists |
| Equipment Using This Part | Equipment lens | Part in equipment BOM |
| Shopping List Requests | Shopping List lens | `pms_shopping_list_items.part_id` exists |
| Related Manuals | Document lens | Vector search on part fields |

### 2.5 File Storage

| Action | Bucket | Path Template |
|--------|--------|---------------|
| `attach_document` | `documents` | `{yacht_id}/parts/{part_id}/{filename}` |

---

## 3. Out-of-Scope

### 3.1 Explicitly Excluded

| Excluded | Reason | Correct Location |
|----------|--------|------------------|
| Create new part | Separate workflow, not lens action | Part creation modal from search |
| Bulk part upload | Admin function | Admin console |
| Shopping list approval | Different entity focus | Shopping List lens |
| Purchase order creation | Different entity focus | Shopping List lens / Purchasing lens |
| Receiving parts | Different entity focus | Receiving lens |
| Work order creation | Different entity focus | Work Order lens |
| Equipment maintenance | Different entity focus | Equipment lens |
| Part transfers between yachts | N/A (single-tenant) | Not applicable |
| Inventory forecasting/predictions | No AI predictions | Out of MVP |
| Automatic reorder triggers | No auto-commit | Banners only, user must click |

### 3.2 Not This Lens

| User Intent | Correct Lens |
|-------------|--------------|
| "Approve shopping list" | Shopping List lens |
| "Create purchase order" | Purchasing lens |
| "Receive parts delivery" | Receiving lens |
| "Add part to work order" | Work Order lens (link part action) |
| "View all low stock parts" | Dashboard / Report (not lens) |

---

## 4. Boundaries

### 4.1 Data Boundaries

```
pms_parts (OWNED)
    ├── pms_part_usage (CHILD - created by log_part_usage)
    ├── pms_shopping_list_items (REFERENCE - created by add_to_shopping_list)
    ├── pms_work_order_parts (REFERENCE - read only in this lens)
    └── documents (REFERENCE - attached via attach_document)
```

### 4.2 Permission Boundaries

| Role | Can Do | Cannot Do |
|------|--------|-----------|
| All Crew | View, log usage, add to shopping list, update count, edit, attach doc | Archive |
| HoD | All above + Archive (with signature) | - |
| Captain | All above + Archive (with signature) | - |
| Purser | All above + Archive (with signature) | - |

### 4.3 Time Boundaries

- **Session-scoped**: Banner dismissals persist for session only
- **30-day undo**: Archived parts can be restored within 30 days
- **Immediate effect**: Stock deductions are immediate (no pending state)

---

## 5. Dependencies

### 5.1 Database Tables

| Table | Dependency Type |
|-------|-----------------|
| `pms_parts` | Primary (OWNED) |
| `pms_part_usage` | Write target |
| `pms_shopping_list_items` | Write target |
| `pms_work_order_parts` | Read only |
| `pms_equipment` | Read only |
| `documents` | Write target (attachments) |
| `pms_audit_log` | Write target (all mutations) |
| `auth_users_profiles` | Read only (user names) |

### 5.2 Database Functions

| Function | Purpose |
|----------|---------|
| `public.get_user_yacht_id()` | RLS yacht isolation |
| `public.is_hod(user_id, yacht_id)` | Role check |
| `public.is_manager(user_id, yacht_id)` | Role check |
| `deduct_part_inventory()` | Atomic stock deduction (TO BE CREATED) |

### 5.3 Storage Dependencies

| Bucket | Purpose |
|--------|---------|
| `documents` | Part spec sheets, datasheets |

### 5.4 External Dependencies

None. All data is local to tenant database.

---

## 6. Success Metrics

### 6.1 Functional Success

| Metric | Target |
|--------|--------|
| Stock accuracy | Actual matches `quantity_on_hand` within 5% |
| Usage logged | 100% of part consumption has usage record |
| Reorder visibility | Low stock parts have shopping list item within 24h |

### 6.2 UX Success

| Metric | Target |
|--------|--------|
| Time to log usage | < 30 seconds from lens activation |
| Time to add to shopping list | < 20 seconds with prefill |
| Error rate | < 1% of actions fail due to user error |

---

## 7. Constraints

### 7.1 Technical Constraints

- **Single-tenant**: No cross-yacht data access
- **RLS enforced**: All queries filtered by yacht_id
- **Audit required**: All mutations logged to pms_audit_log
- **Signature required**: archive_part requires captured signature

### 7.2 Business Constraints

- **No auto-reorder**: System suggests, user must confirm
- **No negative stock blocking**: User can log usage even at 0 (with warning)
- **30-day undo**: Archived parts not permanently deleted for 30 days

### 7.3 UX Constraints

- **Single banner rule**: Only ONE situation banner at a time
- **Dismissible banners**: All banners can be dismissed (session-scoped)
- **No modal auto-open**: User must click button to open action modal

---

## 8. Assumptions

| Assumption | Rationale |
|------------|-----------|
| Parts are physical items | Not services or labor |
| yacht_id is always available | From authenticated session |
| Users know part names | No guided discovery in lens |
| Stock counts are manual | No barcode/RFID integration |
| Concurrent usage is rare | < 0.001% collision rate |

---

## 9. Risks

| Risk | Mitigation |
|------|------------|
| Race condition on stock deduction | `deduct_part_inventory()` function with row lock |
| Orphaned shopping list items | Soft delete prevents FK breaks |
| Stale stock display | Real-time subscription or refresh on action |
| Archive collision | Check `deleted_at` before action |

---

**STOP. Phase 1 complete. Proceed to Phase 2: DB Truth.**
