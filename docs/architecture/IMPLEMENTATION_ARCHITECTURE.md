# 🏗️ CelesteOS Micro-Actions Implementation Architecture

**Status:** Implementation Plan
**Version:** 1.0
**Date:** 2025-11-21

---

## Current State Audit

### ✅ What Exists

**Frontend Foundation:**
- ✅ Basic search interface (SearchBar.tsx)
- ✅ Result card rendering (ResultCard.tsx)
- ✅ Micro-action buttons (MicroActions.tsx)
- ✅ Dashboard widgets (4 widgets)
- ✅ Auth system (Supabase integration)
- ✅ Basic types (8 actions, 7 card types)

**Backend Foundation:**
- ✅ n8n webhook base URL configured (`https://api.celeste7.ai/webhook/`)
- ✅ Supabase database (tables exist from previous work)
- ✅ API client with JWT auth (apiClient.ts)

### ❌ What's Missing (Critical Gaps)

**Frontend:**
- ❌ Only **8 micro-actions** implemented vs **67 needed**
- ❌ Only **placeholder handlers** (console.log) vs **actual execution**
- ❌ Only **7 card types** vs **12 needed**
- ❌ **No modals/forms** for action inputs
- ❌ **No view patterns** (filters, grouping, etc.)
- ❌ **No confirmation dialogs** for mutation_heavy actions
- ❌ **Mock search results** vs **real API integration**

**Backend:**
- ❌ **Zero n8n workflows** implemented (all 67 actions need workflows)
- ❌ **No database CRUD operations** for actions
- ❌ **No audit logging** for edits
- ❌ **No view pattern query builders**

**Database:**
- ❌ Incomplete schema (missing tables for handovers, HOR, purchases, etc.)
- ❌ No audit_log table
- ❌ No RLS policies for micro-actions

---

## Implementation Phases

### Phase 1: Foundation (HIGHEST PRIORITY) ⚡
**Goal:** Get end-to-end flow working for 10 critical actions

**Timeline:** Immediate
**Scope:** 10 most-used actions fully functional

#### 1.1 Complete Type System
- [ ] Update `MicroAction` type with all 67 actions
- [ ] Update `ResultCardType` with all 12 card types
- [ ] Add `ViewPattern` type (14 patterns)
- [ ] Add `ActionMetadata` type (side_effect_type, requires_confirmation, etc.)
- [ ] Add `FilterParam` type for view patterns

#### 1.2 Build Core Action Handler Infrastructure
- [ ] Create `useActionHandler` hook
- [ ] Create `ActionModal` component system
- [ ] Create `ConfirmationDialog` component
- [ ] Implement action routing logic
- [ ] Add loading/error states

#### 1.3 Implement 10 Critical Actions (End-to-End)

**Read Actions (No Backend Required):**
1. ✅ `view_equipment_details` - Display equipment card
2. ✅ `view_part_stock` - Display part card with stock info
3. ✅ `view_fault_history` - Display historical faults for equipment

**Mutation Actions (Require Backend):**
4. ⚡ `create_work_order` - Modal form → n8n workflow → DB insert
5. ⚡ `mark_work_order_complete` - Confirmation → n8n → DB update
6. ⚡ `add_to_handover` - Quick action → n8n → DB insert
7. ⚡ `add_work_order_note` - Modal → n8n → DB insert
8. ⚡ `order_part` - Form → n8n → DB insert (purchase_requests)
9. ⚡ `edit_work_order_details` - Modal form → n8n → DB update + audit
10. ⚡ `edit_invoice_amount` - Audit-sensitive modal → n8n → DB update + notification

#### 1.4 Build 5 Priority Card Components

1. **FaultCard** - Display fault with diagnostic info
2. **WorkOrderCard** - Display WO with status, actions
3. **EquipmentCard** - Equipment details, history, parts
4. **PartCard** - Stock level, location, usage history
5. **HandoverCard** - Handover sections with edit capability

#### 1.5 Create 5 Critical n8n Workflows

1. **Action - Create Work Order**
   - Webhook trigger
   - Validate JWT
   - Insert into `work_orders` table
   - Return success/error

2. **Action - Mark Work Order Complete**
   - Webhook trigger
   - Validate JWT
   - Update `work_orders` SET status='completed', completed_at=NOW()
   - Create audit log entry

3. **Action - Add to Handover**
   - Webhook trigger
   - Insert into `handover_items` table
   - Link to source (fault_id, work_order_id, etc.)

4. **Action - Edit Work Order Details**
   - Webhook trigger
   - Validate user owns WO or is HOD
   - Update `work_orders` with changed fields
   - Insert audit log with old/new values

5. **Action - Edit Invoice Amount**
   - Webhook trigger
   - Validate user role (HOD/Management only)
   - Check threshold (> $500 or > 10% change)
   - Update `purchases` table
   - Insert HIGH PRIORITY audit log
   - Send email notification if threshold exceeded

---

### Phase 2: Scale to Full Action Set (HIGH PRIORITY) 🚀
**Goal:** All 67 actions functional

**Timeline:** After Phase 1 complete
**Scope:** Remaining 57 actions

#### 2.1 Complete All Card Components (Remaining 7)
6. **DocumentCard** - Manual/SOP display with view actions
7. **PurchaseCard** - PO details, status, invoice upload
8. **HORTableCard** - Hours of rest table with edit capability
9. **ChecklistCard** - Operational checklist with tickable items
10. **WorklistCard** - Shipyard tasks/snags
11. **FleetSummaryCard** - Multi-vessel overview
12. **SmartSummaryCard** - Daily briefing/situational awareness

#### 2.2 Build All Remaining n8n Workflows (62 workflows)

**Fault & Diagnosis (7 workflows):**
- Action - Diagnose Fault
- Action - Show Manual Section
- Action - View Fault History
- Action - Suggest Parts
- Action - Create Work Order From Fault
- Action - Add Fault Note
- Action - Add Fault Photo

**Work Orders (8 workflows):**
- Action - Create Work Order (✅ done in Phase 1)
- Action - View Work Order History
- Action - Mark Work Order Complete (✅ done in Phase 1)
- Action - Add Work Order Note (✅ done in Phase 1)
- Action - Add Work Order Photo
- Action - Add Parts to Work Order
- Action - View Work Order Checklist
- Action - Assign Work Order

**Equipment (6 workflows):**
- Action - View Equipment Details
- Action - View Equipment History
- Action - View Equipment Parts
- Action - View Linked Faults
- Action - View Equipment Manual
- Action - Add Equipment Note

...and so on for all 67 actions.

#### 2.3 Action Handler System Completion

**Modal Components:**
- `CreateWorkOrderModal` - WO creation form
- `EditWorkOrderModal` - Edit WO details
- `EditInvoiceModal` - Audit-sensitive invoice edit
- `AddNoteModal` - Add note to entity
- `UploadPhotoModal` - Photo upload with preview
- `OrderPartModal` - Part ordering form
- `EditPartDetailsModal` - Part info editing
- `EditEquipmentModal` - Equipment info editing
- `ConfirmDeleteModal` - Soft delete confirmation

**Form Validation:**
- Zod schemas for all forms
- Real-time validation
- Error handling

---

### Phase 3: View Patterns & Filters (MEDIUM PRIORITY) 🔍
**Goal:** Enable all viewing/filtering patterns

**Timeline:** After Phase 2
**Scope:** 14 view patterns

#### 3.1 Implement Core View Patterns

**filter_by_location:**
```typescript
interface LocationFilter {
  location_type: 'deck' | 'room' | 'locker' | 'box' | 'shelf' | 'zone';
  location_value: string;
}

// Usage: "Show me all parts in Deck 2, Locker 5"
const results = await applyViewPattern('filter_by_location', {
  entity_type: 'parts',
  location: { location_type: 'locker', location_value: 'Deck 2, Locker 5' }
});
```

**filter_by_status:**
```typescript
// Work orders: open, in_progress, pending_approval, completed, overdue
// Parts: in_stock, low_stock, out_of_stock, on_order
// Faults: open, resolved, recurring

const results = await applyViewPattern('filter_by_status', {
  entity_type: 'work_orders',
  status: 'overdue'
});
```

**filter_by_time:**
```typescript
// Presets: today, this_week, this_month, last_30_days, custom
const results = await applyViewPattern('filter_by_time', {
  entity_type: 'faults',
  time_range: 'this_week'
});
```

**group_by:**
```typescript
// Group WOs by equipment, assigned_to, status, etc.
const results = await applyViewPattern('group_by', {
  entity_type: 'work_orders',
  group_field: 'equipment_id'
});
```

#### 3.2 Build View Pattern Components

- `FilterBar` - Dynamic filter UI based on entity type
- `GroupedResultList` - Display grouped results
- `TimeRangePicker` - Date range selector
- `LocationPicker` - Hierarchical location selector
- `StatusFilterChips` - Multi-select status filter

#### 3.3 Backend Query Builders (n8n Function Nodes)

Create reusable n8n function nodes for view patterns:
- `build_location_filter_query` - Generate SQL WHERE clause for location
- `build_status_filter_query` - Generate SQL WHERE clause for status
- `build_time_filter_query` - Generate SQL WHERE clause for date ranges
- `build_group_by_query` - Generate SQL GROUP BY with aggregation

---

### Phase 4: Advanced Features (LOW PRIORITY) ✨
**Goal:** Polish and premium features

**Timeline:** After Phase 3
**Scope:** Nice-to-have features

#### 4.1 Bulk Operations
- Bulk mark complete (select multiple WOs → mark all done)
- Bulk add to handover
- Bulk status change

#### 4.2 Comparison Views
- This month vs last month (faults, costs, WO completion)
- Equipment A vs Equipment B performance
- Budget vs actual

#### 4.3 Hierarchical Views
- Equipment tree (system → subsystem → component)
- Document folder structure
- Bill of materials

#### 4.4 Dashboard Customization
- Drag-and-drop widgets
- Custom widget configuration
- Saved dashboard layouts

---

## Technical Implementation Details

### Frontend Architecture

```
/frontend/src
├── /app
│   ├── /search                    # Main search interface
│   ├── /dashboard                 # Dashboard with widgets
│   ├── /equipment/[id]            # Equipment detail page
│   ├── /work-orders/[id]          # Work order detail page
│   └── /handover                  # Handover editor
├── /components
│   ├── /cards                     # 12 card components
│   │   ├── FaultCard.tsx
│   │   ├── WorkOrderCard.tsx
│   │   ├── EquipmentCard.tsx
│   │   ├── PartCard.tsx
│   │   ├── HandoverCard.tsx
│   │   ├── DocumentCard.tsx
│   │   ├── PurchaseCard.tsx
│   │   ├── HORTableCard.tsx
│   │   ├── ChecklistCard.tsx
│   │   ├── WorklistCard.tsx
│   │   ├── FleetSummaryCard.tsx
│   │   └── SmartSummaryCard.tsx
│   ├── /actions                   # Action system
│   │   ├── ActionButton.tsx       # Generic action button
│   │   ├── ActionModal.tsx        # Modal wrapper
│   │   └── ConfirmationDialog.tsx # Confirmation UI
│   ├── /modals                    # Specific modals
│   │   ├── CreateWorkOrderModal.tsx
│   │   ├── EditWorkOrderModal.tsx
│   │   ├── EditInvoiceModal.tsx
│   │   ├── AddNoteModal.tsx
│   │   ├── UploadPhotoModal.tsx
│   │   └── ...
│   ├── /filters                   # View pattern components
│   │   ├── FilterBar.tsx
│   │   ├── LocationPicker.tsx
│   │   ├── TimeRangePicker.tsx
│   │   └── StatusFilterChips.tsx
│   └── /widgets                   # Dashboard widgets
├── /hooks
│   ├── useActionHandler.ts        # Action execution hook
│   ├── useViewPattern.ts          # View pattern hook
│   ├── useFilters.ts              # Filter state management
│   └── useConfirmation.ts         # Confirmation dialog hook
├── /lib
│   ├── actionRegistry.ts          # 67 action definitions
│   ├── viewPatterns.ts            # 14 view pattern definitions
│   ├── apiClient.ts               # API integration (extended)
│   └── validation.ts              # Zod schemas
└── /types
    ├── actions.ts                 # All 67 action types
    ├── cards.ts                   # All 12 card types
    ├── viewPatterns.ts            # 14 view pattern types
    └── filters.ts                 # Filter types
```

### Backend Architecture (n8n)

```
/n8n-workflows
├── /actions                       # 67 workflow files
│   ├── create-work-order.json
│   ├── mark-work-order-complete.json
│   ├── edit-invoice-amount.json
│   ├── add-to-handover.json
│   └── ... (63 more)
├── /view-patterns                 # View pattern workflows
│   ├── filter-by-location.json
│   ├── filter-by-status.json
│   ├── group-by.json
│   └── ... (11 more)
└── /utilities                     # Shared functions
    ├── validate-jwt.json
    ├── check-permissions.json
    ├── audit-log.json
    └── send-notification.json
```

**n8n Workflow Template Structure:**

```javascript
// Example: Action - Edit Invoice Amount
{
  "nodes": [
    {
      "name": "Webhook",
      "type": "n8n-nodes-base.webhook",
      "parameters": {
        "path": "api/actions/edit_invoice_amount",
        "method": "POST"
      }
    },
    {
      "name": "Validate JWT",
      "type": "n8n-nodes-base.function",
      "parameters": {
        "functionCode": "// Validate JWT and extract user_id"
      }
    },
    {
      "name": "Check Role",
      "type": "n8n-nodes-base.if",
      "parameters": {
        "conditions": {
          "boolean": [
            {
              "value1": "={{$json.user_role}}",
              "operation": "equal",
              "value2": "HOD"
            }
          ]
        }
      }
    },
    {
      "name": "Update Invoice",
      "type": "n8n-nodes-base.postgres",
      "parameters": {
        "query": "UPDATE purchases SET invoice_amount = $1 WHERE id = $2",
        "parameters": {
          "bindings": ["={{$json.new_amount}}", "={{$json.purchase_id}}"]
        }
      }
    },
    {
      "name": "Create Audit Log",
      "type": "n8n-nodes-base.postgres",
      "parameters": {
        "query": "INSERT INTO audit_log (...) VALUES (...)"
      }
    },
    {
      "name": "Check Threshold",
      "type": "n8n-nodes-base.if",
      "parameters": {
        "conditions": {
          "number": [
            {
              "value1": "={{Math.abs($json.new_amount - $json.old_amount)}}",
              "operation": "larger",
              "value2": 500
            }
          ]
        }
      }
    },
    {
      "name": "Send Notification",
      "type": "n8n-nodes-base.sendEmail",
      "parameters": {
        "to": "management@yacht.com",
        "subject": "Invoice Amount Changed - Requires Review"
      }
    }
  ]
}
```

### Database Schema Extensions

**New Tables Needed:**

```sql
-- Handover system
CREATE TABLE handovers (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  yacht_id UUID NOT NULL REFERENCES yachts(id),
  period_start DATE,
  period_end DATE,
  title TEXT NOT NULL,
  description TEXT,
  status TEXT DEFAULT 'draft',
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE handover_items (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  handover_id UUID REFERENCES handovers(id) ON DELETE CASCADE,
  source_type TEXT NOT NULL, -- 'work_order', 'fault', 'note', 'equipment', 'part'
  source_id UUID NOT NULL,
  summary TEXT NOT NULL,
  detail TEXT,
  importance TEXT DEFAULT 'normal',
  added_at TIMESTAMPTZ DEFAULT NOW()
);

-- Audit logging
CREATE TABLE audit_log (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  entity_type TEXT NOT NULL,
  entity_id UUID NOT NULL,
  action TEXT NOT NULL,
  field TEXT,
  old_value JSONB,
  new_value JSONB,
  reason TEXT,
  user_id UUID REFERENCES users(id),
  timestamp TIMESTAMPTZ DEFAULT NOW(),
  severity TEXT DEFAULT 'normal' -- 'low', 'normal', 'high'
);

-- Hours of Rest
CREATE TABLE hours_of_rest (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(id),
  date DATE NOT NULL,
  hours_worked DECIMAL(4,2),
  hours_rested DECIMAL(4,2),
  compliant BOOLEAN,
  notes TEXT,
  UNIQUE(user_id, date)
);

-- Purchases
CREATE TABLE purchases (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  yacht_id UUID REFERENCES yachts(id),
  status TEXT DEFAULT 'draft', -- 'draft', 'submitted', 'approved', 'in_transit', 'received'
  items JSONB NOT NULL, -- Array of {part_id, quantity, unit_price}
  total_amount DECIMAL(10,2),
  invoice_amount DECIMAL(10,2),
  supplier TEXT,
  delivery_date DATE,
  delivery_address TEXT,
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Checklists
CREATE TABLE checklists (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  yacht_id UUID REFERENCES yachts(id),
  checklist_type TEXT NOT NULL, -- 'arrival', 'departure', 'pre_guest', 'fuel_transfer'
  items JSONB NOT NULL, -- Array of {text, completed, timestamp}
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Worklists (Shipyard)
CREATE TABLE worklist_items (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  yacht_id UUID REFERENCES yachts(id),
  task_description TEXT NOT NULL,
  equipment_id UUID REFERENCES equipment(id),
  status TEXT DEFAULT 'open', -- 'open', 'in_progress', 'completed'
  contractor TEXT,
  tagged_for_survey BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Implementation Priority Matrix

| Feature | Phase | Priority | Complexity | User Impact |
|---------|-------|----------|------------|-------------|
| 10 Core Actions | 1 | 🔴 CRITICAL | Medium | Immediate value |
| 5 Core Cards | 1 | 🔴 CRITICAL | Medium | Immediate value |
| 5 Core n8n Workflows | 1 | 🔴 CRITICAL | Medium | Enables actions |
| Remaining 57 Actions | 2 | 🟡 HIGH | High | Complete feature set |
| All 12 Cards | 2 | 🟡 HIGH | Medium | Complete UI |
| All 67 n8n Workflows | 2 | 🟡 HIGH | High | Full functionality |
| View Patterns (14) | 3 | 🟢 MEDIUM | Medium | Enhanced UX |
| Filter System | 3 | 🟢 MEDIUM | Medium | Power user feature |
| Bulk Operations | 4 | ⚪ LOW | Medium | Efficiency |
| Comparison Views | 4 | ⚪ LOW | High | Analytics |
| Hierarchical Views | 4 | ⚪ LOW | High | Advanced navigation |

---

## Success Criteria

### Phase 1 Complete ✅ When:
- [ ] User can create a work order from fault card
- [ ] User can mark work order complete with confirmation
- [ ] User can add items to handover
- [ ] User can edit WO details with audit trail
- [ ] User can edit invoice amount with justification
- [ ] All 10 actions call real n8n workflows
- [ ] All 10 actions update database
- [ ] Audit logs created for mutations
- [ ] Error handling works
- [ ] Loading states display correctly

### Phase 2 Complete ✅ When:
- [ ] All 67 actions are implemented
- [ ] All 12 card types render correctly
- [ ] All 67 n8n workflows deployed
- [ ] Full CRUD coverage (create, read, update, delete)
- [ ] Role-based access control working
- [ ] All forms validate correctly
- [ ] All confirmations work
- [ ] Audit logging comprehensive

### Phase 3 Complete ✅ When:
- [ ] User can filter parts by location
- [ ] User can filter WOs by status
- [ ] User can filter by time range
- [ ] User can group results
- [ ] User can save filters
- [ ] View patterns work across all entity types

### Phase 4 Complete ✅ When:
- [ ] Bulk operations functional
- [ ] Comparison views implemented
- [ ] Equipment hierarchy displays
- [ ] Dashboard customizable

---

## Next Steps

**IMMEDIATE (Start Now):**

1. ✅ Update types with all 67 actions
2. ✅ Create `useActionHandler` hook
3. ✅ Build `CreateWorkOrderModal`
4. ✅ Create first n8n workflow (create-work-order)
5. ✅ Test end-to-end: Search → Fault Card → Create WO → n8n → DB → Success

**THEN:**
6. Implement remaining 9 Phase 1 actions
7. Build remaining 4 Phase 1 cards
8. Deploy 5 core n8n workflows
9. Test all Phase 1 actions end-to-end
10. Move to Phase 2

---

**This is the blueprint for transforming specifications into working software. Let's build!** 🚀
