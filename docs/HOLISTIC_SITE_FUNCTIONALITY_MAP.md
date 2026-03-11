# CELESTE OS - HOLISTIC SITE FUNCTIONALITY MAP

> Generated: 2026-02-27
> Status: Production Reference Documentation

---

## EXECUTIVE SUMMARY

| Lens | Routes | Actions | Filters | Data Source | Status |
|------|--------|---------|---------|-------------|--------|
| **Work Orders** | `/work-orders`, `/work-orders/[id]` | 13 | 5 | `pms_work_orders` | Production |
| **Faults** | `/faults`, `/faults/[id]` | 10 | 4 | `pms_faults` | Production |
| **Equipment** | `/equipment`, `/equipment/[id]` | 7 | 4 | `pms_equipment` | Production |
| **Inventory** | `/inventory`, `/inventory/[id]` | 6 | 2 | `pms_parts` | Production |
| **Receiving** | `/receiving`, `/receiving/[id]` | 10 | 2 | `pms_receiving` | Production |
| **Shopping List** | `/shopping-list`, `/shopping-list/[id]` | 6 | 2 | `pms_shopping_list_items` | Production |

**Feature Flag**: All fragmented routes require `NEXT_PUBLIC_FRAGMENTED_ROUTES_ENABLED=true`

---

## 1. FRAGMENTED URL ARCHITECTURE

### Route Pattern
```
/{domain}           → List view with EntityList + infinite scroll
/{domain}/[id]      → Full-page detail view (deep linkable)
/{domain}?id={id}   → List view with side panel overlay
/{domain}?filter={filterId} → Filtered list view
```

### Domain Routes

| Domain | List Route | Detail Route | Layout Provider |
|--------|------------|--------------|-----------------|
| Work Orders | `/work-orders` | `/work-orders/[id]` | `DomainProvider route="/work-orders"` |
| Faults | `/faults` | `/faults/[id]` | `DomainProvider route="/faults"` |
| Equipment | `/equipment` | `/equipment/[id]` | `DomainProvider route="/equipment"` |
| Inventory | `/inventory` | `/inventory/[id]` | `DomainProvider route="/inventory"` |
| Receiving | `/receiving` | `/receiving/[id]` | `DomainProvider route="/receiving"` |
| Shopping List | `/shopping-list` | `/shopping-list/[id]` | `DomainProvider route="/shopping-list"` |
### NEW: Comment: we are missing lenses for document, certificate, crew (hours of rest), parts.

### File Locations

| Domain | List Page | Detail Page | Layout |
|--------|-----------|-------------|--------|
| Work Orders | `apps/web/src/app/work-orders/page.tsx` | `apps/web/src/app/work-orders/[id]/page.tsx` | `apps/web/src/app/work-orders/layout.tsx` |
| Faults | `apps/web/src/app/faults/page.tsx` | `apps/web/src/app/faults/[id]/page.tsx` | `apps/web/src/app/faults/layout.tsx` |
| Equipment | `apps/web/src/app/equipment/page.tsx` | `apps/web/src/app/equipment/[id]/page.tsx` | `apps/web/src/app/equipment/layout.tsx` |
| Inventory | `apps/web/src/app/inventory/page.tsx` | `apps/web/src/app/inventory/[id]/page.tsx` | `apps/web/src/app/inventory/layout.tsx` |
| Receiving | `apps/web/src/app/receiving/page.tsx` | `apps/web/src/app/receiving/[id]/page.tsx` | `apps/web/src/app/receiving/layout.tsx` |
| Shopping List | `apps/web/src/app/shopping-list/page.tsx` | `apps/web/src/app/shopping-list/[id]/page.tsx` | `apps/web/src/app/shopping-list/layout.tsx` |
### NEW: Comment: we are missing lenses for document, certificate, crew (hours of rest), parts.
---

## 2. DATA FETCHING ARCHITECTURE

### API Endpoints per Domain

| Domain | List Endpoint | Detail Endpoint | Action Endpoint |
|--------|---------------|-----------------|-----------------|
| Work Orders | `GET /v1/work-orders` | `GET /v1/entity/work_order/{id}` | `POST /v1/actions/execute` |
| Faults | `GET /v1/faults` | `GET /v1/faults?limit=1` | `POST /v1/actions/execute` |
| Equipment | `GET /v1/equipment` | `GET /v1/entity/equipment/{id}` | `POST /v1/actions/execute` |
| Inventory | `GET /v1/inventory` | `GET /v1/inventory?limit=1` | `POST /v1/actions/execute` |
| Receiving | `GET /v1/receiving` | `GET /v1/entity/receiving/{id}` | `POST /v1/actions/execute` |
| Shopping List | `GET /v1/shopping-list` | `GET /v1/entity/shopping_list/{id}` | `POST /v1/actions/execute` |
### NEW: Comment: we are missing lenses for document, certificate, crew (hours of rest), parts.

### API File Locations

| Domain | API Client | Types | Adapter |
|--------|------------|-------|---------|
| Work Orders | `apps/web/src/features/work-orders/api.ts` | `apps/web/src/features/work-orders/types.ts` | `apps/web/src/features/work-orders/adapter.ts` |
| Faults | `apps/web/src/features/faults/api.ts` | `apps/web/src/features/faults/types.ts` | `apps/web/src/features/faults/adapter.ts` |
| Equipment | `apps/web/src/features/equipment/api.ts` | `apps/web/src/features/equipment/types.ts` | `apps/web/src/features/equipment/adapter.ts` |
| Inventory | `apps/web/src/features/inventory/api.ts` | `apps/web/src/features/inventory/types.ts` | `apps/web/src/features/inventory/adapter.ts` |
| Receiving | `apps/web/src/features/receiving/api.ts` | `apps/web/src/features/receiving/types.ts` | `apps/web/src/features/receiving/adapter.ts` |
| Shopping List | `apps/web/src/features/shopping-list/api.ts` | `apps/web/src/features/shopping-list/types.ts` | `apps/web/src/features/shopping-list/adapter.ts` |
### NEW: Comment: we are missing lenses for document, certificate, crew (hours of rest), parts.

### Database Tables (Supabase)

```sql
-- Core entity tables with yacht isolation
pms_work_orders         → yacht_id, status, priority, assigned_to, equipment_id
pms_work_order_notes    → yacht_id (denormalized), work_order_id
pms_work_order_parts    → yacht_id (denormalized), work_order_id, part_id
pms_faults              → yacht_id, severity, status, equipment_id
pms_equipment           → yacht_id, status, system_type, location
pms_parts               → yacht_id, quantity_on_hand, minimum_quantity
pms_receiving           → yacht_id, status, supplier_name
pms_shopping_list_items → yacht_id, status, priority
pms_audit_log           → yacht_id, action_id, user_id, timestamp
```
### NEW all the tables must have yacht_id isolation. this is multitenant!
there are mutliple segments of risk isolateion. these are, in no particular order, depednding on the data in question, which can be array of the following;
- yacht_id
- user_id
- department
- role
- rank

### RLS Isolation Pattern

All tables enforce yacht isolation via Row-Level Security:

```sql
-- Standard RLS policy pattern
CREATE POLICY "table_select"
ON public.table_name
FOR SELECT
TO authenticated
USING (yacht_id = public.get_user_yacht_id());

CREATE POLICY "table_insert"
ON public.table_name
FOR INSERT
TO authenticated
WITH CHECK (yacht_id = public.get_user_yacht_id());
```

### React Query Integration

| Setting | Value |
|---------|-------|
| Stale Time | 30 seconds |
| Cache Keys | `['domain']` for lists, `['domain', id]` for detail |
| Invalidation | Manual via `queryClient.invalidateQueries()` |
| Pagination | Infinite scroll with `getNextPageParam` |

---

## 3. ACTIONS BY DOMAIN

### Work Orders (13 Actions)

**Hook**: `apps/web/src/hooks/useWorkOrderActions.ts`

| Action | Role | Signed | Description |
|--------|------|--------|-------------|
| `add_wo_note` | HOD+ | No | Add observation note |
| `start_work_order` | HOD+ | No | Transition: draft → in_progress |
| `mark_work_order_complete` | Close roles | No | Transition: → completed |
| `cancel_work_order` | HOD+ | No | Transition: → cancelled |
| `add_part_to_work_order` | Engineer+ | No | Link parts to WO |
| `add_parts_to_work_order` | Engineer+ | No | Bulk link parts |
| `add_work_order_photo` | Engineer+ | No | Attach photo |
| `assign_work_order` | HOD+ | No | Initial assignment |
| `reassign_work_order` | HOD+ | **Yes** | Transfer assignment (PIN+TOTP) |
| `update_work_order` | HOD+ | No | Edit fields |
| `archive_work_order` | Captain/Manager | **Yes** | Soft delete (PIN+TOTP) |
| `add_wo_hours` | HOD+ | No | Log labor hours |
| `view_work_order_checklist` | All | No | Read-only view |

**Role Constants**:
- `HOD_ROLES`: chief_engineer, eto, chief_officer, captain, manager
- `CLOSE_ROLES`: chief_engineer, chief_officer, captain, manager
- `ADD_PARTS_ROLES`: chief_engineer, chief_officer, captain
- `ARCHIVE_ROLES`: captain, manager

### Faults (10 Actions)

**Hook**: `apps/web/src/hooks/useFaultActions.ts`

| Action | Role | Description |
|--------|------|-------------|
| `report_fault` | Crew+ | Create new fault |
| `acknowledge_fault` | Engineer+ | Transition: open → investigating |
| `close_fault` | Engineer+ | Transition: → closed |
| `update_fault` | Engineer+ | Edit severity, description, title |
| `reopen_fault` | Engineer+ | Transition: closed → open |
| `diagnose_fault` | Engineer+ | Add diagnosis + recommended action |
| `mark_fault_false_alarm` | Engineer+ | Transition: → false_alarm |
| `add_fault_photo` | All | Attach image |
| `add_fault_note` | All | Add note |
| `create_work_order_from_fault` | HOD (Signed) | Create linked WO |

**Status State Machine**:
```
open → investigating → work_ordered → resolved → closed
         ↘ false_alarm (terminal)
         ↘ rejected (terminal)
```

### Equipment (7 Actions)

**Hook**: `apps/web/src/hooks/useEquipmentActions.ts`

| Action | Role | Signed | Description |
|--------|------|--------|-------------|
| `update_equipment_status` | Engineer+ | No | Change operational status |
| `add_equipment_note` | All | No | Add observation |
| `attach_file_to_equipment` | All | No | Upload document/photo |
| `create_work_order_for_equipment` | Engineer+ | No | Create linked WO |
| `link_part_to_equipment` | Engineer+ | No | Add to BOM |
| `flag_equipment_attention` | Engineer+ | No | Set/clear attention flag |
| `decommission_equipment` | Captain/Manager | **Yes** | Terminal state (PIN+TOTP) |

**Status Values**: operational, degraded, maintenance, out_of_service, decommissioned

### Inventory (6 Actions)

**Hook**: `apps/web/src/hooks/usePartActions.ts`

| Action | Role | Signed | Description |
|--------|------|--------|-------------|
| `consume_part` | Crew+ | No | Record stock consumption |
| `receive_part` | HOD+ | No | Add incoming stock |
| `transfer_part` | HOD+ | No | Move between locations |
| `adjust_stock_quantity` | Captain/Manager | **Yes** | Manual correction (PIN+TOTP) |
| `write_off_part` | HOD+ | No | Write off damaged/expired |
| `create_shopping_list_item` | Crew+ | No | Request procurement |

**Stock Status Calculation**:
```typescript
if (quantity <= 0) return 'critical';      // Out of stock
if (quantity < minimum) return 'warning';  // Low stock
return 'success';                          // In stock
```

### Receiving (10 Actions)

**Hook**: `apps/web/src/hooks/useActionHandler.ts`

| Action | Role | Confirmation | Description |
|--------|------|--------------|-------------|
| `create_receiving` | HOD | Yes | Start receiving event |
| `view_receiving_history` | HOD | No | View history |
| `add_receiving_item` | HOD | No | Add line item |
| `adjust_receiving_item` | HOD | No | Modify quantity |
| `update_receiving` | HOD | No | Edit fields |
| `attach_receiving_image_with_comment` | HOD | No | Attach photo |
| `extract_receiving_candidates` | HOD | No | OCR line item extraction |
| `accept_receiving` | HOD | Yes | Approve receiving |
| `reject_receiving` | HOD | Yes | Reject receiving |
| `link_receiving_to_invoice` | HOD | No | Link PDF invoice |

**HOD Roles**: chief_engineer, chief_officer, chief_steward, purser, captain, manager

### Shopping List (6 Actions)

**Hook**: `apps/web/src/hooks/useShoppingListActions.ts`

| Action | Role | Description |
|--------|------|-------------|
| `create_shopping_list_item` | All | Add item to list |
| `approve_shopping_list_item` | HOD | Approve request |
| `reject_shopping_list_item` | HOD | Reject with reason |
| `promote_to_part` | Engineer+ | Create part catalog entry |
| `link_shopping_list_to_work_order` | All | Associate with WO |
| `view_shopping_list_history` | All | View audit trail |


**Status State Machine**:
```
candidate → under_review → approved → ordered → partially_fulfilled → fulfilled → installed
                       ↘ rejected (terminal)
```

---

## 4. FILTERS BY DOMAIN

### Filter Catalog Location
`apps/web/src/lib/filters/catalog.ts`

### Work Orders Filters

| Filter ID | Label | Definition | Keywords |
|-----------|-------|------------|----------|
| `wo_overdue` | Overdue | `due_date < NOW AND status NOT IN (completed, cancelled)` | overdue, past due, late |
| `wo_due_7d` | Due this week | `due_date BETWEEN NOW AND NOW+7d` | due soon, upcoming |
| `wo_open` | Open | `status IN (planned, in_progress)` | open, active, pending |
| `wo_priority_emergency` | Emergency | `priority = emergency` | emergency, urgent |
| `wo_priority_critical` | Critical | `priority = critical` | critical, high priority |
### NEW | `wo_note` | notes | `notes = not null || null` | with notes, wihtout notes |
### NEW | `wo_image` | image | `image = uploaded` | with an image, image, images |

### Faults Filters

| Filter ID | Label | Definition | Keywords |
|-----------|-------|------------|----------|
| `fault_open` | Open faults | `status = 'open'` | open, active |
| `fault_unresolved` | Unresolved | `status IN ('open', 'investigating')` | unresolved |
| `fault_critical` | Critical | `severity = 'high'` | critical, severe |
| `fault_investigating` | Investigating | `status = 'investigating'` | investigating |
### NEW | `fault_completed` | completed | `status = 'completed`' | completed |
### NEW | `fault_closed` | closed | `status = 'closed'' | closed |

### Equipment Filters

| Parameter | Type | Operation | Example |
|-----------|------|-----------|---------|
### NEW | `status` | string | Equality on metadata | `?status=operational` |, this should relate to open work_orders nad fualts for breakdown based upon item
| `category` | string | Equality on system_type | `?category=Propulsion` |
| `location` | string | Case-insensitive LIKE | `?location=engine%20room` |
| `search` | string | Case-insensitive LIKE on name | `?search=main%20engine` |

### Inventory Filters

| Filter ID | Label | Definition |
|-----------|-------|------------|
| `inv_low_stock` | Low stock | `quantity_on_hand <= minimum_quantity AND minimum_quantity > 0` |
| `inv_out_of_stock` | Out of stock | `quantity_on_hand = 0` |
### NEW | `search` | string | Case-insensitive LIKE on name | `?search=main%20engine` |
### NEW | `search_location` | string | Case-insensitive LIKE on name | `?search=Box%203D` |

### Receiving Filters

| Filter ID | Label | Definition |
|-----------|-------|------------|
| `recv_pending` | Pending | `status IN ('in_progress', 'partial')` |
| `recv_discrepancy` | Discrepancy | `status = 'discrepancy'` |
### NEW | `recv_complete` | Complete | `status = 'Complete'` | 
### NEW | `recv_person` | string | `?search=2nd%20Engineer`, `?search=John%20Smith` |
### NEW | `recv_content` | string | `?search=Last%20week`, `?search=Engine%20spares`, `?search=rs%20online%20order` | (user can request detials within content, who, from where, sender, timestampz, contents etc.)


### Shopping List Filters

| Filter ID | Label | Definition |
|-----------|-------|------------|
| `shop_pending` | Pending | `status = 'candidate'` |
| `shop_urgent` | Urgent | `priority = 'high'` |

| `recv_pending` | Pending | `status IN ('in_progress', 'partial')` |
| `recv_discrepancy` | Discrepancy | `status = 'discrepancy'` |
### NEW | `shop_complete` | Complete | `status = 'Complete'` | 
### NEW | `shop_person` | string | `?search=2nd%20Engineer`, `?search=John%20Smith` |
### NEW | `shop_department` | string | `?search=Deck%20department` |
### NEW | `shop_content` | string | `?search=Last%20week`, `?search=Engine%20spares`, `?search=rs%20online%20order` | (user can request detials within content, who, from where, sender, timestampz, contents etc.)



### Filter Execution

**Location**: `apps/web/src/lib/filters/execute.ts`

```typescript
// Client-side filter application
const filteredItems = applyFilter(rawItems, filterId, filterDomain);
```

**Note**: All filters are currently **client-side only**. Server-side faceted filtering is planned for Phase 2.

---

## 5. ROLE-BASED ACCESS CONTROL

### Role Hierarchy

```
Tier 1 (HOD - Heads of Department):
  - captain
  - chief_officer
  - chief_engineer
### NEW   - ceto (Chief Electro-Technical Officer)
  - chief_steward
  - purser
  - manager

Tier 2 (Senior Crew):
  - 2nd_officer
  - 2nd_engineer
  - bosun
  - head_chef
  - head_housekeeper
### NEW   - eto (Electro-Technical Officer)

Tier 3 (Junior Crew):
  - deckhand
  - steward
  - junior_engineer
  - crew_chef
  - crew
  - galley
### NEW   - housekeeper
### NEW   - laundry
### NEW   - service
### NEW   - spa
```

### Permission Matrix

| Capability | Crew | Engineer | HOD | Captain/Manager |
|------------|:----:|:--------:|:---:|:---------------:|
| View all entities | ✓ | ✓ | ✓ | ✓ |
| Add notes/photos | ✓ | ✓ | ✓ | ✓ |
| Consume parts | ✓ | ✓ | ✓ | ✓ |
| Report faults | ✓ | ✓ | ✓ | ✓ |
| Create work orders | | ✓ | ✓ | ✓ |
### NEW | Update equipment status | | ✓ | ✓ | ✓ |
### NEW | Close work orders | | ✓ | ✓ | ✓ |
### NEW | Approve/reject items | | | ✓ | ✓ |
### NEW | Reassign (Signed) | | | ✓ | ✓ |
### NEW | Archive (Signed) | | ✓ | ✓ | ✓ |
### NEW | Decommission (Signed) | | ✓ | ✓ | ✓ |
### NEW | Adjust stock (Signed) | | ✓ | ✓ | ✓ |

### Permission UI Pattern

**Rule**: Hide buttons, never disable them.

```typescript
// Example from WorkOrderLensContent.tsx
{permissions.canArchive && (
  <GhostButton onClick={() => setArchiveModalOpen(true)}>
    Archive
  </GhostButton>
)}
```

### Auth Context

**Hook**: `apps/web/src/contexts/AuthContext.tsx`

```typescript
const { user, session } = useAuth();
// user.id, user.role, user.yacht_id
// session.access_token (JWT)
```

---

## 6. LENS COMPONENTS

### Component Architecture

```
RouteLayout
├── EntityList (infinite scroll)
│   └── SpotlightResultRow (per item)
├── EntityDetailOverlay (side panel)
│   └── {Domain}LensContent
│       ├── LensHeader (back/close buttons)
│       ├── VitalSignsRow (status indicators)
│       ├── Action Buttons (role-gated)
│       └── Sections (Notes, Parts, History, Attachments)
└── Action Modals (react-hook-form + zod)
```

### Lens Content Components

| Domain | Lens Component | Location |
|--------|----------------|----------|
| Work Orders | `WorkOrderLensContent` | `apps/web/src/components/lens/WorkOrderLensContent.tsx` |
| Faults | `FaultLensContent` | `apps/web/src/components/lens/FaultLensContent.tsx` |
| Equipment | `EquipmentLensContent` | `apps/web/src/components/lens/EquipmentLensContent.tsx` |
| Inventory | `PartsLensContent` | `apps/web/src/components/lens/PartsLensContent.tsx` |
| Receiving | `ReceivingLensContent` | `apps/web/src/components/lens/ReceivingLensContent.tsx` |
| Shopping List | `ShoppingListLensContent` | `apps/web/src/components/lens/ShoppingListLensContent.tsx` |

### NEW: Comment: we are missing lenses for document, certificate, crew (hours of rest), parts.

### Action Modals

**Location**: `apps/web/src/components/lens/actions/`

| Modal | Domain | Purpose |
|-------|--------|---------|
| `AddNoteModal` | Work Orders | Add observation note |
| `AddHoursModal` | Work Orders | Log labor hours |
| `AddPartModal` | Work Orders | Link parts |
| `MarkCompleteModal` | Work Orders | Close with notes |
| `ReassignModal` | Work Orders | Transfer assignment (Signed) |
| `ArchiveModal` | Work Orders | Soft delete (Signed) |
| `UpdateStatusModal` | Equipment | Change status |
| `DecommissionModal` | Equipment | Terminal state (Signed) |

### Shared UI Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `LensHeader` | `components/lens/LensHeader.tsx` | Fixed header with navigation |
| `VitalSignsRow` | `components/ui/VitalSignsRow.tsx` | Status indicators row |
| `EntityList` | `features/entity-list/components/EntityList.tsx` | Infinite scroll list |
| `EntityDetailOverlay` | `features/entity-list/components/EntityDetailOverlay.tsx` | Side panel overlay |
| `RouteLayout` | `components/layout/RouteLayout.tsx` | Page layout wrapper |

---

## 7. UI PATTERNS & DESIGN SYSTEM

### Design Tokens

**Location**: `apps/web/src/styles/tokens.css`

#### Theme Support

```css
:root, [data-theme="dark"] {
  --surface-base: #111111;
  --surface-primary: #171717;
  --surface-elevated: #1E1E1E;
  --text-primary: #ECECEC;
  --text-secondary: #A0A0A0;
}

[data-theme="light"] {
  --surface-base: #FFFFFF;
  --surface-primary: #F8F8F8;
  --surface-elevated: #FFFFFF;
  --text-primary: #1A1A1A;
  --text-secondary: #666666;
}

### NEW: Comment: NO HARD CODED VLAUES, ALL TOKENISED IN CODE VIA STYLING FILES.
```

#### Brand Colors

```css
--brand-ambient: #3A7C9D;      /* Logo, subtle brand */
--brand-interactive: #2B8FB3;  /* Buttons, links, focus */
--brand-hover: #239AB8;        /* Interactive hover */
```

#### Status Colors

```css
--status-critical: #E5484D;    /* Red - errors, critical */
--status-warning: #F5A623;     /* Orange - warnings */
--status-success: #30A46C;     /* Green - success */
--status-neutral: #71717A;     /* Gray - neutral */
```

#### Z-Index Hierarchy

```css
--z-sticky: 10;
--z-header: 20;
--z-sidebar: 30;
--z-modal: 40;
--z-search: 50;
--z-toast: 60;
```

### Typography Scale

| Class | Size | Weight | Use |
|-------|------|--------|-----|
| `.text-display` | 28px | 600 | Page titles |
| `.text-title` | 24px | 500 | Section headers |
| `.text-heading` | 18px | 500 | Card headers |
| `.text-section` | 14px | 500 | Section labels |
| `.text-body` | 14px | 300 | Body text |
| `.text-label` | 13px | 400 | Form labels |
| `.text-caption` | 12px | 200 | Helper text |

### Button Variants

| Class | Use |
|-------|-----|
| `.btn-primary` | Primary actions |
| `.btn-ghost` | Secondary actions |
| `.btn-danger` | Destructive actions |
| `.btn-icon` | Icon-only buttons |

### Toast Notifications

**Library**: `sonner`

```typescript
import { toast } from 'sonner';

toast.success('Work order created');
toast.error('Permission denied', { description: 'Contact your captain' });
toast.warning('Low stock alert');
```

---

## 8. ACTION EXECUTION FLOW

### Request Flow

```
User Action (Button Click)
    ↓
useActionHandler.executeAction('action_id', payload)
    ↓
POST /v1/actions/execute
{
  "action": "close_work_order",
  "context": { "yacht_id": "..." },
  "payload": { "work_order_id": "...", "notes": "..." }
}
    ↓
Action Router (apps/api/action_router/router.py)
├── Step 1: JWT Validation
├── Step 1.5: Tenant Lookup (yacht_id + role)
├── Step 2: Action Registry Lookup
├── Step 3: Yacht Isolation Check
├── Step 4: Role Permission Check
├── Step 4.5: Signature Validation (if SIGNED)
├── Step 5-7: Field & Schema Validation
└── Handler Dispatch
    ↓
Internal Handler (Supabase operations)
    ↓
Audit Log (action_logs table)
    ↓
Response
{
  "status": "success",
  "data": { ... }
}
    ↓
Toast Notification + Query Invalidation
```

### Signature Validation (SIGNED Actions)

Required for high-risk operations (reassign, archive, decommission, adjust stock).

**Signature Payload**:
```typescript
{
  signer_id: string;        // User ID
  signed_at: string;        // ISO timestamp
  device_id: string;        // Browser device ID (localStorage)
  action_hash: string;      // SHA-256(JSON.stringify(payload))
  signature_type: 'PIN+TOTP'
}
```

---

## 9. KNOWN LIMITATIONS

### Security Status

| Migration | Status | Description |
|-----------|--------|-------------|
| `20260226_001_fix_wo_related_rls.sql` | Deployed | Fixed USING(true) on WO-related tables |
| `20260226_002_enable_inventory_transactions_rls.sql` | Deployed | Enabled RLS on inventory transactions |
| `20260226_003_add_faults_dml_rls.sql` | Deployed | Added DML policies to faults |

### Feature Gaps

| Domain | Gap | Impact | Priority |
|--------|-----|--------|----------|
| Work Orders | Photo upload not wired | Cannot attach images from detail | Medium |
| Work Orders | Checklist UI missing | Cannot view checklist items | Low |
| Faults | No audit trail UI | Cannot see action history | Medium |
| Faults | No attachment gallery | Photos exist but not displayed | Medium |
| Equipment | Status in metadata JSONB | Query performance impact | Low |
| Inventory | fetchPart() inefficient | Fetches all, filters client-side | Medium |
| Receiving | No view_receiving_photos UI | Read-only photos only | Low |
| Shopping List | Add item placeholder | Create flow not fully wired | Medium |
### NEW: Comment: we are missing lenses for document, certificate, crew (hours of rest), parts.

### Filter Limitations

- All filters are **client-side** (no server-side facets)
- No date range filters
- No multi-filter AND/OR logic
- No advanced search operators

### API Inconsistencies

- Some detail endpoints use `/v1/entity/{type}/{id}`, others use list with limit=1
- Payload structure varies: some nest in `payload` field, some flat

---

## 10. TEST COVERAGE

### E2E Test Locations

```
apps/web/e2e/shard-31-fragmented-routes/
├── route-workorders.spec.ts     (22 tests)
├── route-faults.spec.ts         (7 tests)
├── route-equipment.spec.ts      (17 tests)
├── route-inventory.spec.ts      (15 tests)
├── route-receiving.spec.ts      (30 tests)
└── route-shopping-list.spec.ts  (20 tests)

Total: 111 E2E tests across all domains
```

### Test Fixtures

| Fixture | Role | Auth State File |
|---------|------|-----------------|
| `captainPage` | Captain | `.auth/captain.json` |
| `hodPage` | HOD | `.auth/hod.json` |
| `crewPage` | Crew | `.auth/crew.json` |

### Test Commands

```bash
# Run all fragmented route tests
npm run test:e2e -- --grep "shard-31"

# Run specific domain tests
npm run test:e2e -- route-workorders.spec.ts

# Run with UI
npm run test:e2e:ui
```

---

## 11. QUICK REFERENCE

### Environment Variables

```bash
# Feature Flags
NEXT_PUBLIC_FRAGMENTED_ROUTES_ENABLED=true
NEXT_PUBLIC_API_URL=https://pipeline-core.int.celeste7.ai

# Supabase
MASTER_SUPABASE_URL=https://qvzmkaamzaqxpzbewjxe.supabase.co (### NEW: Comment: this is used for authentication on vercel, frontend deployment. no migratiosn needed here. only recognise it exists)
)
TENANT_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co (### NEW: Comment: this is used for yacht specific data, multi tenant with all yachts in our consuemr list here.)
```

### Key Files

| Purpose | Location |
|---------|----------|
| Action Router | `apps/api/action_router/router.py` |
| Action Registry | `apps/api/action_router/registry.py` |
| Feature Flags | `apps/web/src/lib/featureFlags.ts` |
| Filter Catalog | `apps/web/src/lib/filters/catalog.ts` |
| Design Tokens | `apps/web/src/styles/tokens.css` |
| Auth Context | `apps/web/src/contexts/AuthContext.tsx` |

### Common Patterns

```typescript
// Fetch list
const { data } = useQuery({
  queryKey: ['domain'],
  queryFn: fetchDomainItems,
  staleTime: 30000,
});

// Execute action
const { executeAction } = useActionHandler();
await executeAction('action_id', payload);

// Check permissions
const permissions = useDomainPermissions();
{permissions.canDoThing && <Button />}

// Apply filter
const filtered = applyFilter(items, filterId, 'domain');
```

---

## CHANGELOG

| Date | Version | Changes |
|------|---------|---------|
| 2026-02-27 | 1.0.0 | Initial comprehensive documentation |
