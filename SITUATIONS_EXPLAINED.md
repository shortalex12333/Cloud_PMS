# Situations Explained

**Understanding the situation state machine**

**Purpose:** Learn how user focus state works in CelesteOS
**Audience:** Engineers working on frontend or context-aware actions
**Reading time:** 15 minutes

---

## 🎯 What Is a Situation?

**Simple definition:**
A situation is the user's current focus state in the UI.

**Three states:**
- **IDLE** - User on main search surface (no entity selected)
- **CANDIDATE** - User hovered/selected entity (preview mode)
- **ACTIVE** - User opened entity detail (ContextPanel visible)

**Why it matters:**
- Situations provide context for microactions
- Example: User viewing Fault F-123 (ACTIVE) → Clicks "Create Work Order" → Action pre-fills fault_id from situation

---

## 🔄 State Machine Diagram

```
┌──────────┐
│   IDLE   │  ← User on main search surface
└────┬─────┘
     │
     │ User clicks search result
     ↓
┌──────────┐
│ CANDIDATE│  ← Preview shown (hover/single-click)
└────┬─────┘
     │
     │ User presses Enter or double-clicks
     ↓
┌──────────┐
│  ACTIVE  │  ← ContextPanel opens, entity detail shown
└────┬─────┘
     │
     │ User closes panel or selects different entity
     ↓
┌──────────┐
│   IDLE   │  ← Back to search surface
└──────────┘
```

---

## 📊 The Three States

### State 1: IDLE

**When:** User is on main search surface, no entity selected

**UI:**
```
┌────────────────────────────────────┐
│                                    │
│      [🔍 Search CelesteOS...]     │
│                                    │
│      (No entity selected)          │
│                                    │
│                                    │
└────────────────────────────────────┘
```

**Context available:**
- yacht_id (from JWT)
- user_id (from JWT)
- role (from JWT)

**Context NOT available:**
- ❌ equipment_id (no equipment selected)
- ❌ work_order_id (no work order selected)
- ❌ fault_id (no fault selected)

**Actions available:**
- General actions (create_work_order, add_equipment, search_parts)
- Actions that don't need entity context

**Example:**
```typescript
// User in IDLE state types: "create a work order"
// ✅ Can execute (doesn't need entity context)

// User types: "mark work order complete"
// ❌ Needs work_order_id (which WO to complete?)
// → System asks user to select work order first
```

### State 2: CANDIDATE

**When:** User hovered or single-clicked a search result

**UI:**
```
┌────────────────────────────────────┐
│                                    │
│  [🔍 Search CelesteOS...]         │
│                                    │
│  Results:                          │
│  ┌──────────────────────────────┐ │
│  │ WO-1234: Oil Change          │ │ ← Highlighted
│  │ Status: Open                 │ │ ← Preview shown
│  │ Equipment: Main Engine       │ │
│  └──────────────────────────────┘ │
│  - WO-1235: Filter replacement   │
│                                    │
└────────────────────────────────────┘
```

**Context available:**
- yacht_id (from JWT)
- user_id (from JWT)
- role (from JWT)
- **entity_type** (e.g., "work_order")
- **entity_id** (e.g., work order UUID)

**Context NOT available (yet):**
- ❌ Full entity details (not loaded until ACTIVE)

**Actions available:**
- Preview-level actions (quick view, share link)
- Transition to ACTIVE (press Enter, double-click)

**Example:**
```typescript
// User hovers over "WO-1234: Oil Change"
// Situation becomes CANDIDATE:
{
  state: "CANDIDATE",
  entity_type: "work_order",
  entity_id: "50e9c919-6fc2-4b3d-b913-e0da3285f14d",
  metadata: {
    title: "WO-1234: Oil Change",
    status: "open"
  }
}

// User presses Enter → Transition to ACTIVE
```

### State 3: ACTIVE

**When:** User opened entity detail (ContextPanel visible)

**UI:**
```
┌──────────────────────────────────────────┐
│                                          │
│  [🔍 Search...]                          │
│                                          │
│                      ┌─────────────────┐ │
│                      │ WO-1234         │ │
│                      │ Oil Change      │ │
│                      ├─────────────────┤ │
│                      │ Status: Open    │ │
│                      │ Equipment: ...  │ │
│                      │                 │ │
│                      │ [✅ Complete]   │ │ ← Context actions
│                      │ [✏️ Edit]       │ │
│                      │ [👤 Assign]     │ │
│                      ├─────────────────┤ │
│                      │ Notes:          │ │
│                      │ - Started work  │ │
│                      └─────────────────┘ │
└──────────────────────────────────────────┘
```

**Context available:**
- yacht_id (from JWT)
- user_id (from JWT)
- role (from JWT)
- **entity_type** (e.g., "work_order")
- **entity_id** (e.g., work order UUID)
- **Full entity data** (all fields loaded)
- **Related entities** (equipment, fault, parts, etc.)

**Actions available:**
- All entity-specific actions
- mark_work_order_complete (knows which WO)
- assign_work_order (knows which WO)
- add_work_order_note (knows which WO)
- create_work_order_from_fault (if entity is fault)

**Example:**
```typescript
// User viewing WO-1234 in ACTIVE state
// Situation:
{
  state: "ACTIVE",
  entity_type: "work_order",
  entity_id: "50e9c919-6fc2-4b3d-b913-e0da3285f14d",
  evidence: {
    id: "50e9c919-6fc2-4b3d-b913-e0da3285f14d",
    title: "Oil Change",
    status: "open",
    equipment_id: "abc-123",
    fault_id: "def-456",
    assigned_to: "user-789",
    ... // All fields
  }
}

// User clicks "Mark Complete" button
// Action knows:
// - work_order_id: "50e9c919-6fc2-4b3d-b913-e0da3285f14d"
// - equipment_id: "abc-123" (from situation evidence)
// - fault_id: "def-456" (from situation evidence)
```

---

## 🔀 State Transitions

### IDLE → CANDIDATE

**Trigger:** User clicks or hovers over search result

**What happens:**
```typescript
// User clicks search result
const handleResultSelect = (result: SearchResult) => {
  createSituation({
    entity_type: mapResultType(result.type),
    entity_id: result.id,
    domain: mapDomain(result.type),
    initial_state: 'CANDIDATE',  // ← Preview mode
    metadata: {
      title: result.title,
      subtitle: result.subtitle
    }
  });
};
```

**UI change:**
- Search result highlighted
- Preview info shown (title, subtitle, metadata)
- No ContextPanel yet

### CANDIDATE → ACTIVE

**Trigger:** User presses Enter or double-clicks

**What happens:**
```typescript
// User presses Enter or double-clicks
const handleResultOpen = async (result: SearchResult) => {
  if (situation && situation.state === 'CANDIDATE') {
    // Load full entity data
    const fullData = await loadEntityData(result.id);

    // Update situation with full evidence
    await updateSituation({
      evidence: fullData
    });

    // Transition to ACTIVE
    await transitionTo('ACTIVE', 'User opened entity');
  }
};
```

**UI change:**
- ContextPanel slides in from right
- Full entity details loaded and displayed
- Action buttons shown (contextual to entity)

### ACTIVE → IDLE

**Trigger:** User closes ContextPanel or clicks away

**What happens:**
```typescript
// User closes panel
const handleClosePanel = () => {
  resetToIdle();
};
```

**UI change:**
- ContextPanel slides out
- Back to main search surface

### CANDIDATE → IDLE

**Trigger:** User deselects or clicks away

**What happens:**
```typescript
// User clicks away from result
const handleDeselect = () => {
  resetToIdle();
};
```

**UI change:**
- Search result unhighlighted
- Preview cleared

---

## 🎯 How Actions Use Situations

### Example 1: Create Work Order (No Situation Needed)

**User action:** Types "create a work order"

**Situation:** IDLE (no entity selected)

**What happens:**
```typescript
// Action detected
action = "create_work_order"

// No situation context needed
context = {
  yacht_id: "...",  // From JWT
  user_id: "..."    // From JWT
}

// User fills form from scratch
payload = {
  title: "...",
  equipment_id: "...",  // User selects from dropdown
  priority: "routine"
}
```

**Result:** Work order created with user-provided data

### Example 2: Create Work Order from Fault (Situation Required)

**User action:** Viewing Fault F-123 (ACTIVE), clicks "Create Work Order"

**Situation:**
```typescript
{
  state: "ACTIVE",
  entity_type: "fault",
  entity_id: "fault-123-uuid",
  evidence: {
    id: "fault-123-uuid",
    equipment_id: "equipment-456-uuid",
    title: "Generator overheating",
    severity: "high",
    description: "Coolant leak detected"
  }
}
```

**What happens:**
```typescript
// Action triggered from situation
action = "create_work_order_from_fault"

// Context from situation
context = {
  yacht_id: "...",      // From JWT
  user_id: "...",       // From JWT
  fault_id: "fault-123-uuid",           // From situation
  equipment_id: "equipment-456-uuid"    // From situation
}

// Form pre-filled from situation
payload = {
  title: "Fix: Generator overheating",  // Pre-filled from fault title
  description: "Coolant leak detected",  // Pre-filled from fault description
  priority: "critical",                   // Pre-filled from fault severity
  equipment_id: "equipment-456-uuid",    // Pre-filled from fault
  fault_id: "fault-123-uuid"             // Hidden, immutable
}
```

**Result:** Work order created and automatically linked to fault

### Example 3: Mark Work Order Complete (Situation Required)

**User action:** Viewing WO-1234 (ACTIVE), clicks "Mark Complete"

**Situation:**
```typescript
{
  state: "ACTIVE",
  entity_type: "work_order",
  entity_id: "wo-1234-uuid",
  evidence: {
    id: "wo-1234-uuid",
    title: "Oil Change",
    status: "in_progress",
    equipment_id: "equipment-789-uuid"
  }
}
```

**What happens:**
```typescript
// Action triggered from situation
action = "mark_work_order_complete"

// Context from situation
context = {
  yacht_id: "...",            // From JWT
  user_id: "...",             // From JWT
  work_order_id: "wo-1234-uuid"  // From situation
}

// Minimal payload (just completion notes)
payload = {
  completion_notes: "Oil and filter replaced. Tested OK."
}

// Backend knows which work order to update from context
```

**Result:** WO-1234 status updated to "completed"

---

## 🧩 Situation Data Structure

### Situation Object

```typescript
interface Situation {
  // Identity
  id: string;  // Situation UUID
  yacht_id: string;  // Which yacht

  // State
  state: 'IDLE' | 'CANDIDATE' | 'ACTIVE';

  // Entity
  entity_type: EntityType;  // 'work_order' | 'fault' | 'equipment' | 'part' | ...
  entity_id: string;  // Entity UUID
  domain: SituationDomain;  // 'maintenance' | 'inventory' | 'manuals' | 'email'

  // Evidence (full entity data, loaded in ACTIVE)
  evidence?: {
    id: string;
    [key: string]: any;  // All entity fields
  };

  // Metadata
  metadata?: {
    title?: string;
    subtitle?: string;
    [key: string]: any;
  };

  // History
  state_history?: Array<{
    from_state: string;
    to_state: string;
    reason: string;
    timestamp: string;
  }>;

  // Timestamps
  created_at: string;
  updated_at: string;
}
```

### Entity Types

```typescript
type EntityType =
  | 'work_order'
  | 'fault'
  | 'equipment'
  | 'part'
  | 'inventory'
  | 'document'
  | 'email_thread'
  | 'checklist'
  | 'purchase_order'
  | 'shipyard_project';
```

### Domains

```typescript
type SituationDomain =
  | 'maintenance'    // work_orders, faults, equipment
  | 'inventory'      // parts, inventory movements
  | 'manuals'        // documents, search results
  | 'email'          // email threads
  | 'compliance'     // inspections, certificates
  | 'purchasing';    // purchase orders
```

---

## 🎨 UI Implications

### ContextPanel Content by Entity Type

**Work Order (ACTIVE):**
```
┌─────────────────────────┐
│ WO-1234: Oil Change     │
│ Status: Open            │
├─────────────────────────┤
│ Equipment: Main Engine  │
│ Priority: Routine       │
│ Assigned to: John       │
├─────────────────────────┤
│ [✅ Complete]           │ ← mark_work_order_complete
│ [✏️ Edit]               │ ← update_work_order
│ [👤 Assign]             │ ← assign_work_order
│ [🗑️ Delete]            │ ← delete_work_order
├─────────────────────────┤
│ Notes (3):              │
│ - Started work at 10am  │
│ [Add note...]           │ ← add_work_order_note
└─────────────────────────┘
```

**Fault (ACTIVE):**
```
┌─────────────────────────┐
│ F-123: Generator issue  │
│ Status: Reported        │
├─────────────────────────┤
│ Equipment: Generator    │
│ Severity: High          │
├─────────────────────────┤
│ [✅ Acknowledge]        │ ← acknowledge_fault
│ [🔍 Diagnose]           │ ← diagnose_fault
│ [📋 Create WO]          │ ← create_work_order_from_fault
│ [🗑️ Close]             │ ← close_fault
├─────────────────────────┤
│ Notes (1):              │
│ - Coolant leak found    │
│ [Add note...]           │ ← add_fault_note
└─────────────────────────┘
```

**Equipment (ACTIVE):**
```
┌─────────────────────────┐
│ Main Generator          │
│ Status: Operational     │
├─────────────────────────┤
│ Manufacturer: Caterpillar│
│ Model: 3516             │
│ Location: Engine Room   │
├─────────────────────────┤
│ [✏️ Edit]               │ ← update_equipment
│ [🚨 Flag Attention]     │ ← flag_equipment_attention
│ [📋 Create WO]          │ ← create_work_order (pre-filled)
│ [🔧 Report Fault]       │ ← report_fault (pre-filled)
├─────────────────────────┤
│ Work Orders (5):        │
│ - WO-1234: Oil Change   │
│ Faults (2):             │
│ - F-123: Overheating    │
└─────────────────────────┘
```

---

## 🔍 Deep Linking (E2E Testing)

### URL Query Params

**Situations can be created from URL:**
```
/app?entity=work_order&id=50e9c919-6fc2-4b3d-b913-e0da3285f14d
```

**What happens:**
1. DeepLinkHandler reads query params
2. Creates ACTIVE situation with entity
3. ContextPanel opens automatically
4. User sees entity detail immediately

**Why this matters:**
- E2E tests can deep-link to specific entities
- Email notifications can link directly to entities
- Shared links work

**Example E2E test:**
```typescript
test('mark work order complete from deep link', async ({ page }) => {
  // Deep link to work order
  await page.goto('/app?entity=work_order&id=wo-1234-uuid');

  // ContextPanel should open automatically
  await page.waitForSelector('[data-testid="context-panel"]');

  // Situation should be ACTIVE
  // Can now click "Mark Complete" button
  await page.click('button:has-text("Mark Complete")');

  // ...
});
```

---

## 🧪 Testing Situations

### Test Pattern: Situation-Aware Actions

**Test that action uses situation context:**
```typescript
test('create_work_order_from_fault uses fault context', async ({ page }) => {
  // 1. Navigate to fault
  await page.goto('/app?entity=fault&id=fault-123-uuid');

  // 2. Wait for ContextPanel (ACTIVE situation)
  await page.waitForSelector('[data-testid="context-panel"]');

  // 3. Click "Create Work Order" button
  await page.click('button:has-text("Create Work Order")');

  // 4. Form should be pre-filled from fault
  await page.waitForSelector('[data-testid="action-modal"]');

  const titleValue = await page.inputValue('[name="title"]');
  expect(titleValue).toContain('Fault F-123');  // Pre-filled from fault

  const equipmentValue = await page.inputValue('[name="equipment_id"]');
  expect(equipmentValue).toBeTruthy();  // Pre-filled from fault

  // 5. Submit
  await page.click('button:has-text("Create")');

  // 6. Verify WO linked to fault
  const { data: wo } = await supabase
    .from('pms_work_orders')
    .select('*')
    .eq('fault_id', 'fault-123-uuid')
    .single();

  expect(wo).toBeTruthy();
  expect(wo.fault_id).toBe('fault-123-uuid');
});
```

---

## 🎯 Design Patterns

### Pattern 1: Context Inheritance

**Actions inherit context from situation:**
```typescript
// User viewing Equipment ABC (ACTIVE)
situation = {
  entity_type: 'equipment',
  entity_id: 'equipment-abc-uuid'
}

// User clicks "Create Work Order"
// Action inherits equipment_id from situation
executeAction(
  'create_work_order',
  {
    yacht_id: '...',
    user_id: '...',
    equipment_id: 'equipment-abc-uuid'  // ← From situation
  },
  {
    title: '...',
    // equipment_id already in context, don't duplicate
  }
)
```

### Pattern 2: Situation Chaining

**One situation can lead to another:**
```typescript
// User viewing Fault F-123 (ACTIVE)
// Clicks "Create Work Order from Fault"
// Work order created
// Situation transitions to new work order:

oldSituation = {entity_type: 'fault', entity_id: 'fault-123'}
  ↓ create_work_order_from_fault
newSituation = {entity_type: 'work_order', entity_id: 'wo-456'}
```

### Pattern 3: Situation History

**Track state transitions for debugging:**
```typescript
situation.state_history = [
  {
    from_state: 'IDLE',
    to_state: 'CANDIDATE',
    reason: 'User clicked search result',
    timestamp: '2026-01-22T10:00:00Z'
  },
  {
    from_state: 'CANDIDATE',
    to_state: 'ACTIVE',
    reason: 'User opened entity from CANDIDATE state',
    timestamp: '2026-01-22T10:00:05Z'
  }
]
```

---

## 📚 Related Documentation

- **MICROACTIONS_EXPLAINED.md** - How actions use situation context
- **ARCHITECTURE.md** - Overall system architecture
- **CUSTOMER_JOURNEY_FRAMEWORK.md** - How situations flow in UX

---

## 🎓 Key Takeaways

1. **Situations = User Focus State** (IDLE, CANDIDATE, ACTIVE)

2. **ACTIVE situations provide context** for actions (equipment_id, fault_id, work_order_id)

3. **Actions inherit context** from situations (pre-filled forms, automatic linking)

4. **ContextPanel visibility = ACTIVE** state

5. **Deep linking creates ACTIVE** situations from URL

6. **Test situation-aware actions** by navigating to entity first

---

**Document Version:** 1.0
**Last Updated:** 2026-01-22
**Maintained By:** Engineering Team
**State Machine:** IDLE ↔ CANDIDATE ↔ ACTIVE
