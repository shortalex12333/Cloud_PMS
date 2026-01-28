# Situation State System Design (V2 - No Behavioral Tracking)

**Date:** 2026-01-08
**Status:** Design Phase
**Purpose:** Define situation state management WITHOUT confidence scoring or behavioral tracking

---

## Design Philosophy

### From Action Specifications (README.md):

> **Core principle:** "If a human didn't click it, it doesn't happen."
>
> **No:**
> - Behavioral tracking (time-on-page, scroll depth, copied text)
> - Confidence scores (0-100)
> - ML predictions
> - Proactive nudges
>
> **Yes:**
> - Query intent parsing (explicit queries only)
> - Entity data mapping (simple, deterministic)
> - Preview before commit (no hidden effects)
> - Human confirms every mutation

---

## Situation Lifecycle (Simplified)

### Old System (REJECTED):
```
IDLE → CANDIDATE → ACTIVE → COOLDOWN → RESOLVED
      ↑           ↑         ↑
   Evidence   Evidence  Evidence
   Tracking   Tracking  Tracking
```

### New System (APPROVED):
```
NO_SITUATION → SEARCH_MODE → ENTITY_VIEW
               ↑             ↑
            Query        Click Entity
           Intent        (Explicit)
```

**Key Difference:** No state machine based on evidence. States are purely UI-driven:
- **NO_SITUATION**: User not interacting with system
- **SEARCH_MODE**: User typed query, seeing search results (PREVIEWS ONLY, NO ACTIONS)
- **ENTITY_VIEW**: User clicked entity, seeing detail page (ACTIONS AVAILABLE)

---

## Situation Context (Minimal)

### What to Keep:

```typescript
interface SituationContext {
  // Identity
  yacht_id: string;
  user_id: string;
  role: string;
  device_type: 'mobile' | 'desktop';

  // Current entity context (if in ENTITY_VIEW)
  primary_entity_type: EntityType | null;  // 'fault', 'work_order', etc.
  primary_entity_id: string | null;
  domain: SituationDomain | null;  // 'maintenance', 'inventory', etc.

  // Session tracking (for audit only)
  session_id: string;
  created_at: number;  // Unix timestamp
  last_activity_at: number;  // Unix timestamp

  // Current UI state
  ui_state: 'no_situation' | 'search_mode' | 'entity_view';

  // Query history (last 5 queries only, for intent classification)
  recent_queries: string[];
}
```

### What to Remove:

❌ `confidence_points` - Behavioral tracking
❌ `evidence` - Behavioral tracking
❌ `phase` - Inferred from evidence
❌ `nudge_last_shown_at` - Proactive nudging
❌ `nudge_dismissed` - Nudge tracking
❌ `nudge_budget_remaining` - Nudge limiting

---

## Entity Types

```typescript
export type EntityType =
  | 'document'
  | 'equipment'
  | 'part'
  | 'work_order'
  | 'fault'
  | 'location'
  | 'person'
  | 'inventory';
```

---

## Situation Domains

```typescript
export type SituationDomain =
  | 'manuals'      // Document reading, manual sections
  | 'maintenance'  // Work orders, equipment history
  | 'inventory'    // Parts, stock, locations
  | 'hor'          // Hours of Rest compliance
  | 'purchasing'   // Ordering, procurement
  | 'people';      // Crew management
```

---

## Search Guardrails (Critical)

### Rule: Search = Orientation (Previews Only)

**When user types query:**
1. Intent parser classifies query as: `information_query` or `action_query`
2. If `information_query` → Show entity previews, NO actions
3. If `action_query` → Show action chip BENEATH search bar (not on results)

**Example:**
```
User types: "generator 2 status"
→ Intent: information_query
→ Show: Entity preview cards (no action buttons)
→ Click card → Opens entity detail page → THEN actions appear
```

```
User types: "create work order for generator 2"
→ Intent: action_query
→ Show: "Create Work Order" action chip beneath search bar
→ Click chip → Opens pre-filled form
```

### Entity Preview Card (Search Results)

```typescript
interface EntityPreviewCard {
  entity_type: EntityType;
  entity_id: string;
  title: string;
  summary: string;  // 2-3 line summary
  metadata: {
    status?: string;
    severity?: string;
    location?: string;
    updated_at?: string;
  };
  thumbnail?: string;  // Optional image
  // NO actions field - actions only in detail view
}
```

### Rule Enforcement:

```typescript
// CORRECT: Search results have NO actions
function renderSearchResults(results: EntityPreview[]) {
  return results.map(entity => (
    <PreviewCard
      onClick={() => navigateToEntity(entity.id)}
      {...entity}
      // NO actions prop
    />
  ));
}

// INCORRECT: Search results with actions
function renderSearchResults(results: EntityPreview[]) {
  return results.map(entity => (
    <PreviewCard
      actions={getActions(entity.type)}  // ❌ VIOLATION
      {...entity}
    />
  ));
}
```

---

## Entity View = Commitment Surface

### Rule: Actions Only Appear in Entity Detail View

**When user clicks entity:**
1. UI state changes: `search_mode` → `entity_view`
2. Situation context updated:
   ```typescript
   {
     primary_entity_type: 'fault',
     primary_entity_id: 'uuid',
     domain: 'maintenance',
     ui_state: 'entity_view'
   }
   ```
3. Backend returns entity data + **available_actions** array
4. Frontend renders actions in dropdown / primary button

**Example Flow:**

```
User searches: "MTU overheating"
→ Search results show:
   [Fault Card: MTU-OVHT-01 - Generator 2]  ← Preview only, no actions

User clicks fault card
→ Entity detail page opens
→ Backend responds with:
   {
     entity_type: "fault",
     entity_id: "uuid",
     data: { /* fault details */ },
     available_actions: [
       { action_id: "create_work_order_from_fault", label: "Create Work Order", is_primary: true },
       { action_id: "add_to_handover", label: "Add to Handover" },
       { action_id: "view_manual_section", label: "View Manual" }
     ]
   }

→ Frontend renders:
   [Primary Button: Create Work Order]
   [Dropdown: ▼ More Actions]
      - Add to Handover
      - View Manual
```

---

## Query Intent Classification (Binary, No Confidence)

### Intent Parser Rules (Deterministic):

```typescript
function classifyIntent(query: string): 'information_query' | 'action_query' {
  const actionKeywords = [
    'create', 'add', 'mark', 'log', 'update', 'edit', 'delete',
    'generate', 'make', 'new', 'show manual', 'open manual'
  ];

  const queryLower = query.toLowerCase();

  // Check for explicit action keywords
  for (const keyword of actionKeywords) {
    if (queryLower.includes(keyword)) {
      return 'action_query';
    }
  }

  // Default to information query
  return 'information_query';
}
```

**Examples:**
- ✅ "create work order" → `action_query`
- ✅ "add to handover" → `action_query`
- ✅ "mark complete" → `action_query`
- ✅ "show manual for generator 2" → `action_query`
- ❌ "generator 2 status" → `information_query`
- ❌ "MTU overheating history" → `information_query`
- ❌ "what parts needed" → `information_query`

**No confidence score.** Binary classification only.

---

## Action Gating (Entity-Based)

### Rule: Actions Gated by Entity Type + Entity State

**NOT:** Confidence thresholds, evidence tracking, behavioral scoring

**YES:** Simple mapping:

```typescript
interface ActionPolicy {
  entity_type: EntityType;
  entity_state?: string;  // e.g., work_order.status = "in_progress"
  allowed_actions: string[];  // action_ids
}

const ACTION_POLICIES: ActionPolicy[] = [
  {
    entity_type: 'fault',
    allowed_actions: [
      'create_work_order_from_fault',
      'add_to_handover',
      'view_manual_section',
      'diagnose_fault'
    ]
  },
  {
    entity_type: 'work_order',
    entity_state: 'in_progress',
    allowed_actions: [
      'add_note_to_work_order',
      'add_part_to_work_order',
      'mark_work_order_complete',
      'add_to_handover'
    ]
  },
  {
    entity_type: 'work_order',
    entity_state: 'completed',
    allowed_actions: [
      'view_work_order_history'  // Read-only
    ]
  },
  {
    entity_type: 'part',
    allowed_actions: [
      'check_stock_level',
      'log_part_usage',
      'add_to_handover'
    ]
  }
];
```

**Backend Implementation:**

```python
def get_available_actions(entity_type: str, entity_state: Optional[str] = None) -> List[str]:
    """
    Get allowed actions for entity type + state.

    Simple lookup, no confidence scoring.
    """
    for policy in ACTION_POLICIES:
        if policy['entity_type'] == entity_type:
            if policy.get('entity_state') is None or policy['entity_state'] == entity_state:
                return policy['allowed_actions']

    return []  # No actions allowed
```

---

## Action Execution Flow (With Preview)

### MUTATE Actions (e.g., create_work_order_from_fault):

```
1. User clicks "Create Work Order" (from fault page)
   ↓
2. Frontend calls: GET /v1/actions/create_work_order_from_fault/prefill?fault_id=uuid
   ↓
3. Backend returns pre-filled form data:
   {
     title: "Generator 2 - MTU-OVHT-01",
     equipment_id: "uuid",
     location: "Engine Room Deck 3",
     description: "Coolant temp exceeding normal...",
     priority: "normal"
   }
   ↓
4. Frontend shows form (all fields editable)
   User can edit or accept pre-fill
   ↓
5. User clicks "Next" (not "Submit")
   Frontend calls: POST /v1/actions/create_work_order_from_fault/preview
   ↓
6. Backend returns preview:
   {
     summary: "You are about to create:",
     changes: { ... },
     side_effects: [
       "Work order will be created with status CANDIDATE",
       "Linked to fault F-2024-089",
       "Audit log entry created"
     ],
     requires_signature: true
   }
   ↓
7. User reviews preview, clicks "Sign & Create"
   ↓
8. Frontend calls: POST /v1/actions/execute
   with signature: { user_id, timestamp }
   ↓
9. Backend creates work order, returns:
   {
     status: "success",
     result: { work_order: {...} },
     message: "✓ WO-2024-089 created"
   }
   ↓
10. Frontend shows success toast, navigates to WO detail page
```

**Key Points:**
- Pre-fill is **suggested, not auto-executed**
- User must click **2 times** (Next, then Sign & Create)
- Preview shows **all side effects** (no hidden mutations)
- Signature required for state changes

### READ Actions (e.g., check_stock_level):

```
1. User clicks "Check Stock Level" (from part page)
   ↓
2. Frontend calls: POST /v1/actions/execute
   {
     action: "check_stock_level",
     payload: { part_id: "uuid" }
   }
   ↓
3. Backend returns stock data immediately
   ↓
4. Frontend displays result
```

**Key Points:**
- No preview needed (read-only)
- Executes immediately (safe)
- No signature required

---

## Session Tracking (Audit Only)

### Purpose: Audit trail, not behavioral tracking

```typescript
interface SessionActivity {
  session_id: string;
  user_id: string;
  yacht_id: string;
  events: SessionEvent[];
}

interface SessionEvent {
  timestamp: number;
  event_type: 'query' | 'entity_click' | 'action_execute';
  data: {
    query?: string;
    entity_type?: string;
    entity_id?: string;
    action?: string;
  };
}
```

**Use Cases:**
- Audit compliance (who did what when)
- Security monitoring (unusual access patterns)
- Performance analytics (slow queries)

**NOT Used For:**
- Confidence scoring
- Proactive suggestions
- Behavioral nudging

---

## Frontend State Management

### Recommended: Zustand store

```typescript
interface SituationStore {
  // Current situation
  context: SituationContext | null;

  // Actions
  setQuery: (query: string) => void;
  setEntityView: (entityType: EntityType, entityId: string) => void;
  clearSituation: () => void;

  // Selectors
  isInSearchMode: () => boolean;
  isInEntityView: () => boolean;
  getAvailableActions: () => string[];
}

// Usage
const useSituation = create<SituationStore>((set, get) => ({
  context: null,

  setQuery: (query) => {
    set({
      context: {
        ...get().context,
        ui_state: 'search_mode',
        recent_queries: [query, ...get().context?.recent_queries || []].slice(0, 5)
      }
    });
  },

  setEntityView: (entityType, entityId) => {
    set({
      context: {
        ...get().context,
        ui_state: 'entity_view',
        primary_entity_type: entityType,
        primary_entity_id: entityId
      }
    });
  },

  clearSituation: () => {
    set({ context: null });
  },

  isInSearchMode: () => get().context?.ui_state === 'search_mode',
  isInEntityView: () => get().context?.ui_state === 'entity_view',

  getAvailableActions: () => {
    const ctx = get().context;
    if (!ctx || !ctx.primary_entity_type) return [];

    // Fetch from backend or static policy
    return ACTION_POLICIES.find(p => p.entity_type === ctx.primary_entity_type)?.allowed_actions || [];
  }
}));
```

---

## Migration Plan (From Old System)

### Phase 1: Remove Behavioral Tracking

**Files to Modify:**
1. `/apps/web/src/types/situation.ts`
   - Remove: `SituationEvidence`, `confidence_points`, `phase`, `nudge_*`
   - Keep: Entity context, session tracking
   - Add: `ui_state`, `recent_queries`

2. `/apps/api/actions/action_gating.py`
   - Remove: `get_execution_class()` with confidence
   - Remove: `can_auto_execute()`, `requires_confirmation()`
   - Add: `get_available_actions(entity_type, entity_state)`

3. `/apps/api/microaction_service.py`
   - Remove: `get_action_chips()` with confidence
   - Remove: Auto-execution logic
   - Add: `classify_query_intent()` (binary)

### Phase 2: Implement Search Guardrails

**Frontend:**
1. Modify search results component:
   - Remove action buttons from preview cards
   - Add `onClick` to navigate to entity detail
   - Only render actions in detail view

2. Add action chip component:
   - Render beneath search bar for `action_query` intent
   - Direct action trigger (not on preview cards)

**Backend:**
1. Entity detail endpoint returns `available_actions` array
2. Search endpoint returns only preview data (no actions)

### Phase 3: Add Preview Endpoints

**For each MUTATE action:**
1. Create `GET /v1/actions/{action}/prefill` endpoint
2. Create `POST /v1/actions/{action}/preview` endpoint
3. Add signature validation to execute endpoint

---

## Testing Validation

### Search Guardrail Tests:

```typescript
describe('Search Guardrails', () => {
  test('Information query shows previews only', () => {
    const results = searchEntities("generator 2 status");

    expect(results.every(r => r.actions === undefined)).toBe(true);
    // ✅ No actions on preview cards
  });

  test('Action query shows action chip beneath search', () => {
    const intent = classifyIntent("create work order");
    expect(intent).toBe('action_query');

    // Action chip should render, not on results
  });

  test('Clicking preview card navigates to detail view', () => {
    const card = renderPreviewCard(entity);
    card.click();

    expect(currentRoute()).toBe('/entity/fault/uuid');
    // ✅ Navigates to detail view
  });
});
```

### Entity View Tests:

```typescript
describe('Entity View Actions', () => {
  test('Fault page shows allowed actions', async () => {
    const response = await fetchEntity('fault', 'uuid');

    expect(response.available_actions).toContain('create_work_order_from_fault');
    expect(response.available_actions).toContain('add_to_handover');
    // ✅ Actions appear in detail view
  });

  test('Completed work order shows read-only actions', async () => {
    const response = await fetchEntity('work_order', 'uuid-completed');

    expect(response.available_actions).not.toContain('add_note_to_work_order');
    expect(response.available_actions).toContain('view_work_order_history');
    // ✅ State-based gating works
  });
});
```

### No Behavioral Tracking Tests:

```typescript
describe('No Behavioral Tracking', () => {
  test('Situation context has NO confidence fields', () => {
    const context = getSituationContext();

    expect(context.confidence_points).toBeUndefined();
    expect(context.evidence).toBeUndefined();
    expect(context.phase).toBeUndefined();
    expect(context.nudge_budget_remaining).toBeUndefined();
    // ✅ All tracking removed
  });

  test('Intent classification is binary, not scored', () => {
    const intent = classifyIntent("create work order");

    expect(intent).toBe('action_query');
    expect(typeof intent).toBe('string');
    // ✅ No confidence score returned
  });
});
```

---

## Summary: What Changed

### Before (V1 - Behavioral Surveillance):
- ❌ Confidence scoring (0-100)
- ❌ Evidence tracking (opened_manual, viewed_history, etc.)
- ❌ Inferred phase (investigating, acting, wrapping_up)
- ❌ Nudge budget and dismissal tracking
- ❌ Auto-execution based on confidence
- ❌ Actions in search results

### After (V2 - Explicit Control):
- ✅ Binary intent classification (information vs action query)
- ✅ Entity-based action gating (no confidence thresholds)
- ✅ Search = previews only (no actions)
- ✅ Actions only in entity detail view
- ✅ Preview before commit (all side effects visible)
- ✅ Human confirms every mutation (no auto-execution)
- ✅ Session tracking for audit only (not for behavior prediction)

---

**END OF SITUATION STATE DESIGN V2**
