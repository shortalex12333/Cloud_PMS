# CLAUDE B: FOLLOW-UP TASK — Implement Folders 01-15 in Cloud_PMS

---

## CRITICAL: READ THIS FIRST

### Before You Do ANYTHING

1. **If you don't understand something, ASK THE USER.** Don't guess. Don't work around.
2. **Don't fake results.** Empty tests that pass are lies. Mocked data is not implementation.
3. **Verify everything.** Check tables exist. Check functions work. Check code compiles.
4. **The user prefers honesty over appearing productive.** Say "I don't understand X" instead of producing fake work.

### What Previous Claude Got Wrong

Claude B made these mistakes - **DON'T REPEAT THEM**:

1. **Faked test results** - Tests passed but tested nothing real
2. **Didn't read the spec folders** - Guessed instead of reading the Python specs
3. **Assumed tables existed** - Wrote code for tables that weren't created
4. **Worked around problems** - Instead of stopping and asking
5. **Optimized for appearing productive** - Green CI badges, completed todos, but no real work done
6. **Never converted Python to TypeScript** - The handler specs are Python, you must convert them

---

## PREREQUISITE

**Complete the handover_export repo implementation first.** Then return here.

Verify handover_export is complete:
- [ ] All API endpoints working (not mocked)
- [ ] All database tables exist (verified with queries)
- [ ] All tests passing (testing real functionality)
- [ ] Deployed to Render and healthy

---

## SECTION 0: SYSTEM ARCHITECTURE REMINDER

### This Task is for Cloud_PMS (Next.js)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           YOU ARE WORKING HERE                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                         Cloud_PMS (Next.js)                          │  │
│  │                                                                      │  │
│  │  Location: /Users/celeste7/Documents/Cloud_PMS                       │  │
│  │                                                                      │  │
│  │  EXISTING:                         NEED TO CREATE:                   │  │
│  │  ✅ src/app/                       ❌ src/lib/microactions/          │  │
│  │  ✅ src/components/                ❌ src/lib/handlers/              │  │
│  │  ✅ src/lib/supabase/              ❌ src/lib/situations/            │  │
│  │  ✅ src/hooks/                     ❌ src/lib/action-router/         │  │
│  │  ✅ Basic CRUD                     ❌ src/lib/reports/               │  │
│  │                                    ❌ src/lib/services/              │  │
│  │                                                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                              │                                              │
│                              │ Supabase JS client                          │
│                              ▼                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                         TENANT DATABASE                               │  │
│  │                                                                      │  │
│  │  EXISTING:                         NEED TO CREATE:                   │  │
│  │  ✅ user_profiles                  ❌ action_executions              │  │
│  │  ✅ pms_work_orders                ❌ symptom_reports                │  │
│  │  ✅ pms_faults                     ❌ situation_detections           │  │
│  │  ✅ pms_equipment                  ❌ suggestion_log                 │  │
│  │  ✅ pms_parts                      ❌ predictive_state               │  │
│  │  ✅ pms_documents                                                    │  │
│  │                                                                      │  │
│  │  URL: https://vzsohavtuotocgrfkfyd.supabase.co                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### What You're Building

| Component | Source Spec | Target Location | Files to Create |
|-----------|-------------|-----------------|-----------------|
| **57 Microactions** | 03_MICROACTIONS/*.md | src/lib/microactions/ | 9 files |
| **16 Handlers** | 04_HANDLERS/*.py | src/lib/handlers/ | 17 files |
| **Situation Engine** | 05_SITUATIONS/*.py | src/lib/situations/ | 10 files |
| **Action Router** | 11_ACTION_ROUTER/ | src/lib/action-router/ | 8 files |
| **220 Test Scenarios** | 06_TESTING/*.json | tests/ | 25+ files |

---

## SECTION 0.1: WHAT EXISTS VS WHAT DOESN'T

### EXISTING in Cloud_PMS:

**Code:**
- `src/app/` ✅ - Next.js pages exist
- `src/components/` ✅ - React components exist
- `src/lib/supabase/` ✅ - Supabase client works
- `src/hooks/` ✅ - Some hooks exist
- Basic CRUD for work orders, faults, equipment ✅

**Database (Tenant DB):**
- `user_profiles` ✅
- `pms_work_orders` ✅
- `pms_faults` ✅
- `pms_equipment` ✅
- `pms_parts` ✅
- `pms_documents` ✅

### NOT EXISTING (You must CREATE):

**Code:**
- `src/lib/microactions/` ❌ - Directory doesn't exist
- `src/lib/handlers/` ❌ - Directory doesn't exist
- `src/lib/situations/` ❌ - Directory doesn't exist
- `src/lib/action-router/` ❌ - Directory doesn't exist
- `src/lib/reports/` ❌ - Directory doesn't exist
- `src/lib/services/` ❌ - Directory doesn't exist

**Database (Tenant DB - need migrations):**
- `action_executions` ❌
- `symptom_reports` ❌
- `situation_detections` ❌
- `suggestion_log` ❌
- `predictive_state` ❌

### How to Verify

```bash
# Check if directories exist
ls -la /Users/celeste7/Documents/Cloud_PMS/src/lib/

# Check if tables exist
supabase db execute --sql "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename LIKE '%situation%'"
```

---

## SECTION 0.2: WHAT SUCCESS LOOKS LIKE

### End-to-End User Flow

```
1. USER TYPES SEARCH QUERY
   Input: "generator overheating"

2. ACTION ROUTER PARSES INTENT
   Intent: { verb: "diagnose", object: "generator", modifiers: ["overheating"] }

3. ENTITY RESOLVER FINDS EQUIPMENT
   Entity: { type: "equipment", entity_id: "uuid-123", canonical: "Port Generator" }

4. SITUATION ENGINE CHECKS FOR PATTERNS
   Query: check_symptom_recurrence('yacht-id', 'Port Generator', 'OVERHEAT')
   Result: { is_recurrent: true, occurrence_count: 4, span_days: 45 }

5. SITUATION DETECTED
   Situation: {
     type: "RECURRENT_SYMPTOM",
     severity: "high",
     label: "Recurring generator overheating (4 times in 45 days)",
     evidence: ["Fault #123", "Fault #456", "Fault #789", "Current search"]
   }

6. RECOMMENDATIONS GENERATED
   Based on user role (Chief Engineer):
   - "Create diagnostic work order"
   - "Review maintenance history"
   - "Check coolant levels"

7. UI DISPLAYS RESULTS
   - Equipment card with fault history
   - Situation alert banner
   - Recommended actions as buttons

8. USER CLICKS "Create Diagnostic Work Order"

9. MICROACTION EXECUTES
   Action: create_work_order_from_fault
   Handler: fault_handlers.create_work_order_from_fault()

10. CONFIRMATION SHOWN
    "Work Order #WO-2026-0789 created
     Linked to: Port Generator
     Priority: High (recurrent issue)
     Assigned to: Chief Engineer"

11. LEDGER EVENT RECORDED
    Event: work_order.created
    Actor: user-uuid
    Entity: work-order-uuid
```

### Success Criteria Summary

- [ ] User searches → Intent parsed correctly
- [ ] Entities resolved from search query
- [ ] Situations detected when patterns match
- [ ] Recommendations shown based on user role
- [ ] Actions execute and produce confirmations
- [ ] All events logged to audit trail

---

## SECTION 0.3: COMMON MISUNDERSTANDINGS

### "The specs are in Python, but Cloud_PMS is TypeScript?"

**YES.** The spec files in `04_HANDLERS/*.py` are **specifications written in Python**. You must **convert them to TypeScript**.

Example conversion:

```python
# Python spec (04_HANDLERS/work_order_handlers.py)
async def view_work_order(self, entity_id: str, yacht_id: str, params: Optional[Dict] = None) -> Dict:
    builder = ResponseBuilder("view_work_order", entity_id, "work_order", yacht_id)
    result = self.db.table("pms_work_orders").select(...).eq("yacht_id", yacht_id).eq("id", entity_id).execute()
    return builder.build()
```

```typescript
// TypeScript implementation (src/lib/handlers/work-order-handlers.ts)
export async function viewWorkOrder(
  entityId: string,
  yachtId: string,
  params?: { offset?: number; limit?: number }
): Promise<ActionResponseEnvelope<WorkOrderData>> {
  const builder = new ResponseBuilder('view_work_order', entityId, 'work_order', yachtId);
  const supabase = createClient();

  const { data, error } = await supabase
    .from('pms_work_orders')
    .select('...')
    .eq('yacht_id', yachtId)
    .eq('id', entityId)
    .single();

  return builder.build();
}
```

### "Do I need to create the database tables too?"

**YES.** The tables for microactions system don't exist. You need to create migrations:

```sql
-- supabase/migrations/XXXXXX_microactions_system.sql
CREATE TABLE action_executions (...);
CREATE TABLE symptom_reports (...);
CREATE TABLE situation_detections (...);
-- etc.
```

### "Where do I find the 57 microaction definitions?"

In `/Users/celeste7/Desktop/Cloud_PMS_docs_v2/03_MICROACTIONS/MICRO_ACTION_REGISTRY.md`

### "Where do I find the 16 handler specs?"

In `/Users/celeste7/Desktop/Cloud_PMS_docs_v2/04_HANDLERS/*.py` - there are 16 Python files to convert.

### "Where do I find the 220 test scenarios?"

In `/Users/celeste7/Desktop/Cloud_PMS_docs_v2/06_TESTING/scenario_matrix.json`

---

## SECTION 0.4: WHAT NOT TO DO

1. **Don't skip reading the Python specs** - They define exactly what each handler should do
2. **Don't create empty test files** - Each test file needs 15 real tests
3. **Don't assume tables exist** - Create migrations and verify they run
4. **Don't use mocks in production code** - Connect to real Supabase
5. **Don't skip the situation engine** - It's core to the UX
6. **Don't forget RLS policies** - All new tables need vessel isolation
7. **Don't guess the microaction definitions** - Read MICRO_ACTION_REGISTRY.md

---

## SECTION 0.5: QUESTIONS YOU SHOULD ASK

### Before Starting Each Phase

1. "Have I read all the spec files for this phase?"
2. "Do the required database tables exist?"
3. "What TypeScript types do I need to define?"
4. "How will I test this with real data?"

### During Implementation

1. "This Python code does X - is my TypeScript equivalent correct?"
2. "The spec mentions table Y - does it exist in the tenant DB?"
3. "How should this handler connect to Supabase?"
4. "What RLS policy should I add for this table?"

---

## OVERVIEW

You are implementing 15 documentation folders that exist as **SPECS ONLY**. None of this code exists in the Cloud_PMS application. Your job is to turn these specifications into working production code.

**Main Repository:** /Users/celeste7/Documents/Cloud_PMS
**Documentation:** /Users/celeste7/Desktop/Cloud_PMS_docs_v2/

---

## SECTION 1: FOLDER INVENTORY

| Folder | Contents | Implementation Target |
|--------|----------|----------------------|
| 01_START_HERE/ | Onboarding docs | Reference only |
| 02_ARCHITECTURE/ | Architecture specs | Reference only |
| **03_MICROACTIONS/** | **57 microaction definitions** | **src/lib/microactions/** |
| **04_HANDLERS/** | **16 Python handler files** | **src/lib/handlers/** (convert to TS) |
| **05_SITUATIONS/** | **Situation detection engine** | **src/lib/situations/** |
| **06_TESTING/** | **220 test scenarios** | **tests/** |
| 07_IMPLEMENTATION_TRACKER/ | Progress tracking | Reference only |
| 08_GOSPEL_AND_DESIGN/ | Design principles | Reference only |
| 09_SPECS/ | Feature specs | Implementation guide |
| **10_REPORTS/** | Report generators | **src/lib/reports/** |
| **11_ACTION_ROUTER/** | Action routing logic | **src/lib/action-router/** |
| **12_ACTION_SPECIFICATIONS/** | Action execution specs | **src/lib/actions/** |
| 13_HANDOVER/ | Handover specs | Already in handover_export |
| **14_CORE_SERVICES/** | Core service specs | **src/lib/services/** |
| **15_TESTING_AND_INFRASTRUCTURE/** | Test infrastructure | **tests/infrastructure/** |

---

## SECTION 2: THE 57 MICROACTIONS

From `/Users/celeste7/Desktop/Cloud_PMS_docs_v2/03_MICROACTIONS/MICRO_ACTION_REGISTRY.md`

### 2.1 Action Registry (Implement ALL)

```typescript
// src/lib/microactions/registry.ts

export type SideEffectType = 'read_only' | 'mutation_light' | 'mutation_heavy';

export type PurposeCluster =
  | 'fix_something'      // 7 actions
  | 'do_maintenance'     // 16 actions
  | 'manage_equipment'   // 6 actions
  | 'control_inventory'  // 7 actions
  | 'communicate_status' // 9 actions
  | 'comply_audit'       // 5 actions
  | 'procure_suppliers'; // 7 actions

export interface MicroAction {
  action_name: string;
  label: string;
  cluster: PurposeCluster;
  card_types: string[];
  side_effect: SideEffectType;
  description: string;
  handler: string;
  requires_confirmation: boolean;
}

export const MICROACTION_REGISTRY: Record<string, MicroAction> = {
  // === FIX_SOMETHING (7) ===
  diagnose_fault: {
    action_name: 'diagnose_fault',
    label: 'Diagnose Fault',
    cluster: 'fix_something',
    card_types: ['fault'],
    side_effect: 'read_only',
    description: 'Analyze fault code and provide diagnostic guidance',
    handler: 'fault_handlers.diagnose_fault',
    requires_confirmation: false,
  },
  show_manual_section: { /* ... */ },
  view_fault_history: { /* ... */ },
  suggest_parts: { /* ... */ },
  create_work_order_from_fault: {
    action_name: 'create_work_order_from_fault',
    label: 'Create Work Order',
    cluster: 'fix_something',
    card_types: ['fault'],
    side_effect: 'mutation_heavy',
    description: 'Generate work order pre-filled from fault context',
    handler: 'fault_handlers.create_work_order_from_fault',
    requires_confirmation: true,
  },
  add_fault_note: { /* ... */ },
  add_fault_photo: { /* ... */ },

  // === DO_MAINTENANCE (16) ===
  create_work_order: { /* ... */ },
  view_work_order_history: { /* ... */ },
  mark_work_order_complete: { /* ... */ },
  // ... 13 more actions

  // === MANAGE_EQUIPMENT (6) ===
  view_equipment_details: { /* ... */ },
  // ... 5 more actions

  // === CONTROL_INVENTORY (7) ===
  view_part_stock: { /* ... */ },
  // ... 6 more actions

  // === COMMUNICATE_STATUS (9) ===
  add_to_handover: { /* ... */ },
  // ... 8 more actions

  // === COMPLY_AUDIT (5) ===
  view_hours_of_rest: { /* ... */ },
  // ... 4 more actions

  // === PROCURE_SUPPLIERS (7) ===
  create_purchase_request: { /* ... */ },
  // ... 6 more actions
};
```

### 2.2 Files to Create

```
src/lib/microactions/
├── index.ts                    # Re-exports
├── registry.ts                 # Complete registry of 57 actions
├── types.ts                    # TypeScript types
├── executor.ts                 # Action execution engine
├── validator.ts                # Input validation
├── confirmation.ts             # Confirmation dialog logic
└── hooks/
    ├── useAction.ts            # React hook for action execution
    ├── useActionState.ts       # Action loading/error state
    └── useAvailableActions.ts  # Get actions for current context
```

---

## SECTION 3: THE 16 HANDLERS

Convert Python specs from `/Users/celeste7/Desktop/Cloud_PMS_docs_v2/04_HANDLERS/` to TypeScript:

### 3.1 Handler Files to Create

```
src/lib/handlers/
├── index.ts
├── types.ts                        # ActionResponseEnvelope, etc.
├── base-handler.ts                 # Base handler class
├── response-builder.ts             # ResponseBuilder utility
├── fault-handlers.ts               # From fault_handlers.py
├── work-order-handlers.ts          # From work_order_handlers.py
├── work-order-mutation-handlers.ts # From work_order_mutation_handlers.py
├── equipment-handlers.ts           # From equipment_handlers.py
├── inventory-handlers.ts           # From inventory_handlers.py
├── handover-handlers.ts            # From handover_handlers.py
├── manual-handlers.ts              # From manual_handlers.py
├── list-handlers.ts                # From list_handlers.py
├── purchasing-handlers.ts          # From p1_purchasing_handlers.py
├── purchasing-mutation-handlers.ts # From purchasing_mutation_handlers.py
├── compliance-handlers.ts          # From p1_compliance_handlers.py
├── mutation-light-handlers.ts      # From p2_mutation_light_handlers.py
├── read-only-handlers.ts           # From p3_read_only_handlers.py
├── situation-handlers.ts           # From situation_handlers.py
└── schema-mapping.ts               # From schema_mapping.py
```

### 3.2 Handler Response Schema

```typescript
// src/lib/handlers/types.ts

export interface ActionResponseEnvelope<T = unknown> {
  success: boolean;
  action_name: string;
  entity_id: string;
  entity_type: string;
  yacht_id: string;
  data: T | null;
  error: ActionError | null;
  files: FileReference[];
  available_actions: AvailableAction[];
  pagination: PaginationInfo | null;
  metadata: {
    timestamp: string;
    duration_ms: number;
    cached: boolean;
  };
}

export interface ActionError {
  code: 'NOT_FOUND' | 'FORBIDDEN' | 'VALIDATION_ERROR' | 'INTERNAL_ERROR';
  message: string;
  details?: Record<string, unknown>;
}

export interface AvailableAction {
  action_id: string;
  label: string;
  variant: 'READ' | 'MUTATE' | 'NAVIGATE';
  icon: string;
  is_primary?: boolean;
  requires_signature?: boolean;
  disabled?: boolean;
  disabled_reason?: string;
}

export interface FileReference {
  file_id: string;
  filename: string;
  mime_type: string;
  signed_url: string;
  expires_at: string;
  category: 'photo' | 'document' | 'manual' | 'invoice';
}
```

### 3.3 Example Handler Conversion

**Python (spec):**
```python
# From work_order_handlers.py
async def view_work_order(self, entity_id: str, yacht_id: str, params: Optional[Dict] = None) -> Dict:
    builder = ResponseBuilder("view_work_order", entity_id, "work_order", yacht_id)
    result = self.db.table("pms_work_orders").select(...).eq("yacht_id", yacht_id).eq("id", entity_id).execute()
    # ...
    return builder.build()
```

**TypeScript (implementation):**
```typescript
// src/lib/handlers/work-order-handlers.ts
import { createClient } from '@/lib/supabase/server';
import { ResponseBuilder } from './response-builder';
import type { ActionResponseEnvelope, WorkOrderData } from './types';

export async function viewWorkOrder(
  entityId: string,
  yachtId: string,
  params?: { offset?: number; limit?: number }
): Promise<ActionResponseEnvelope<WorkOrderData>> {
  const builder = new ResponseBuilder('view_work_order', entityId, 'work_order', yachtId);
  const supabase = createClient();

  try {
    const { data, error } = await supabase
      .from('pms_work_orders')
      .select(`
        id, title, description, status, priority,
        due_date, created_at, completed_at,
        equipment:pms_equipment(id, name, location),
        assignee:user_profiles(id, full_name)
      `)
      .eq('yacht_id', yachtId)
      .eq('id', entityId)
      .single();

    if (error) throw error;
    if (!data) {
      builder.setError('NOT_FOUND', `Work order not found: ${entityId}`);
      return builder.build();
    }

    // Add computed fields
    const workOrder: WorkOrderData = {
      ...data,
      is_overdue: isOverdue(data),
      days_open: daysOpen(data),
      allowed_transitions: STATUS_FLOW[data.status] || [],
    };

    builder.setData(workOrder);
    builder.addAvailableActions(getWorkOrderActions(workOrder));

    return builder.build();
  } catch (err) {
    builder.setError('INTERNAL_ERROR', String(err));
    return builder.build();
  }
}
```

---

## SECTION 4: SITUATION ENGINE

From `/Users/celeste7/Desktop/Cloud_PMS_docs_v2/05_SITUATIONS/situation_engine.py`

### 4.1 Files to Create

```
src/lib/situations/
├── index.ts
├── types.ts
├── situation-engine.ts         # Main detection engine
├── patterns/
│   ├── recurrent-symptom.ts    # RECURRENT_SYMPTOM pattern
│   ├── high-risk-equipment.ts  # HIGH_RISK_EQUIPMENT pattern
│   └── pre-event-critical.ts   # RECURRENT_SYMPTOM_PRE_EVENT
├── policies/
│   ├── engineering-policy.ts   # Recommendations for engineers
│   └── captain-policy.ts       # Recommendations for captain/management
└── hooks/
    ├── useSituation.ts         # Detect situation from context
    └── useRecommendations.ts   # Get recommendations for situation
```

### 4.2 Situation Types

```typescript
// src/lib/situations/types.ts

export type Severity = 'low' | 'medium' | 'high';

export type SituationType =
  | 'RECURRENT_SYMPTOM'
  | 'RECURRENT_SYMPTOM_PRE_EVENT'
  | 'HIGH_RISK_EQUIPMENT';

export interface Situation {
  type: SituationType;
  label: string;
  severity: Severity;
  context: string | null;
  evidence: string[];
}

export interface Recommendation {
  action: string;
  template: string | null;
  reason: string;
  parts_available: boolean;
  urgency: 'normal' | 'elevated' | 'high' | 'urgent';
}

export interface ResolvedEntity {
  type: 'equipment' | 'symptom' | 'part' | 'document';
  entity_id?: string;
  canonical: string;
  confidence: number;
}

export interface VesselContext {
  hours_until_event?: number;
  next_event_type?: 'charter' | 'survey' | 'crossing' | null;
}
```

### 4.3 Database Functions Required

```sql
-- Create in Supabase migrations

-- Check for recurrent symptoms
CREATE OR REPLACE FUNCTION check_symptom_recurrence(
  p_yacht_id UUID,
  p_equipment_label TEXT,
  p_symptom_code TEXT,
  p_threshold_count INT DEFAULT 3,
  p_threshold_days INT DEFAULT 60
)
RETURNS TABLE (
  is_recurrent BOOLEAN,
  occurrence_count INT,
  span_days INT,
  open_count INT
)
LANGUAGE plpgsql AS $$
BEGIN
  RETURN QUERY
  WITH symptom_occurrences AS (
    SELECT
      id,
      created_at,
      status
    FROM pms_faults
    WHERE yacht_id = p_yacht_id
      AND equipment_label ILIKE '%' || p_equipment_label || '%'
      AND fault_code = p_symptom_code
      AND created_at > NOW() - (p_threshold_days || ' days')::INTERVAL
  )
  SELECT
    COUNT(*) >= p_threshold_count AS is_recurrent,
    COUNT(*)::INT AS occurrence_count,
    EXTRACT(DAY FROM MAX(created_at) - MIN(created_at))::INT AS span_days,
    COUNT(*) FILTER (WHERE status NOT IN ('resolved', 'closed'))::INT AS open_count
  FROM symptom_occurrences;
END;
$$;
```

---

## SECTION 5: ACTION ROUTER

### 5.1 Files to Create

```
src/lib/action-router/
├── index.ts
├── types.ts
├── router.ts                   # Main routing logic
├── intent-parser.ts            # Parse user intent from query
├── entity-resolver.ts          # Resolve entities from query
├── action-matcher.ts           # Match intent to action
├── context-builder.ts          # Build execution context
└── hooks/
    ├── useActionRouter.ts      # Main hook
    └── useSearchAction.ts      # Route search to action
```

### 5.2 Router Implementation

```typescript
// src/lib/action-router/router.ts

import { MICROACTION_REGISTRY } from '../microactions/registry';
import { parseIntent } from './intent-parser';
import { resolveEntities } from './entity-resolver';
import { matchAction } from './action-matcher';
import type { RouteResult, RoutingContext } from './types';

export async function routeQuery(
  query: string,
  context: RoutingContext
): Promise<RouteResult> {
  // Step 1: Parse intent
  const intent = parseIntent(query);

  // Step 2: Resolve entities
  const entities = await resolveEntities(query, context.yacht_id);

  // Step 3: Match to action
  const action = matchAction(intent, entities, context);

  // Step 4: Check if action requires confirmation
  const actionDef = action ? MICROACTION_REGISTRY[action] : null;
  const requiresConfirmation = actionDef?.requires_confirmation ?? false;

  return {
    action_name: action,
    confidence: action ? 0.85 : 0,
    entities,
    intent,
    suggestions: generateSuggestions(intent, entities),
    requires_confirmation: requiresConfirmation,
  };
}
```

---

## SECTION 6: TEST SUITE (220 SCENARIOS)

From `/Users/celeste7/Desktop/Cloud_PMS_docs_v2/06_TESTING/scenario_matrix.json`

### 6.1 Test Categories

| Category | Count | Description |
|----------|-------|-------------|
| normal | 60 | Happy path scenarios |
| edge | 60 | Edge cases (typos, empty, unicode) |
| abuse | 40 | Malicious/invalid input |
| security | 30 | Security violation attempts |
| regression | 30 | Previously fixed bugs |

### 6.2 Test File Structure

```
tests/
├── unit/
│   ├── microactions/
│   │   ├── registry.test.ts              # 15 tests
│   │   ├── executor.test.ts              # 15 tests
│   │   └── validator.test.ts             # 15 tests
│   ├── handlers/
│   │   ├── fault-handlers.test.ts        # 15 tests
│   │   ├── work-order-handlers.test.ts   # 15 tests
│   │   └── ... (one per handler)
│   ├── situations/
│   │   ├── situation-engine.test.ts      # 15 tests
│   │   └── patterns.test.ts              # 15 tests
│   └── action-router/
│       ├── router.test.ts                # 15 tests
│       └── intent-parser.test.ts         # 15 tests
│
├── integration/
│   ├── handler-db.test.ts                # 15 tests
│   ├── situation-db.test.ts              # 15 tests
│   └── router-db.test.ts                 # 15 tests
│
├── e2e/
│   ├── scenarios/
│   │   ├── normal.test.ts                # 60 scenarios
│   │   ├── edge.test.ts                  # 60 scenarios
│   │   ├── abuse.test.ts                 # 40 scenarios
│   │   ├── security.test.ts              # 30 scenarios
│   │   └── regression.test.ts            # 30 scenarios
│   └── workflows/
│       ├── fault-to-work-order.test.ts   # 15 tests
│       └── search-to-action.test.ts      # 15 tests
│
└── fixtures/
    ├── scenario_matrix.json              # Copy from docs
    ├── sample_faults.json
    └── sample_work_orders.json
```

### 6.3 15 Tests Per File (MANDATORY)

| # | Category | Description |
|---|----------|-------------|
| 1 | Success | Happy path - normal flow |
| 2 | Success | Happy path - minimal data |
| 3 | Success | Happy path - maximum load |
| 4 | Failure | Missing required fields |
| 5 | Failure | Invalid data types |
| 6 | Failure | Database constraint violation |
| 7 | Edge | Empty arrays/objects |
| 8 | Edge | Maximum string length |
| 9 | Edge | Unicode/special characters |
| 10 | User | Lazy - partial submission |
| 11 | User | Impatient - rapid clicks |
| 12 | User | Confused - wrong order |
| 13 | System | Network timeout |
| 14 | System | Concurrent access |
| 15 | System | Recovery after failure |

---

## SECTION 7: DATABASE MIGRATIONS

### 7.1 New Tables Required

```sql
-- supabase/migrations/XXXXXX_microactions_system.sql

-- Action execution log
CREATE TABLE action_executions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id UUID NOT NULL,
  user_id UUID NOT NULL REFERENCES auth.users(id),
  action_name TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  entity_id UUID,
  params JSONB,
  result JSONB,
  success BOOLEAN NOT NULL,
  error_code TEXT,
  error_message TEXT,
  duration_ms INT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Symptom reports (for situation engine)
CREATE TABLE symptom_reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id UUID NOT NULL,
  equipment_label TEXT NOT NULL,
  symptom_code TEXT NOT NULL,
  symptom_label TEXT NOT NULL,
  search_query_id UUID,
  reported_by UUID REFERENCES auth.users(id),
  source TEXT NOT NULL DEFAULT 'manual',
  resolved BOOLEAN DEFAULT FALSE,
  resolved_at TIMESTAMPTZ,
  resolved_by UUID,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Situation detections
CREATE TABLE situation_detections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id UUID NOT NULL,
  user_id UUID REFERENCES auth.users(id),
  situation_type TEXT NOT NULL,
  severity TEXT NOT NULL,
  label TEXT NOT NULL,
  context TEXT,
  evidence JSONB,
  recommendations JSONB,
  search_query_id UUID,
  acknowledged BOOLEAN DEFAULT FALSE,
  acknowledged_at TIMESTAMPTZ,
  acknowledged_by UUID,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Suggestion log (for learning)
CREATE TABLE suggestion_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id UUID NOT NULL,
  user_id UUID,
  query_text TEXT NOT NULL,
  intent TEXT,
  search_query_id UUID,
  situation_detected BOOLEAN DEFAULT FALSE,
  situation_type TEXT,
  suggested_actions JSONB,
  action_taken TEXT,
  action_taken_at TIMESTAMPTZ,
  feedback TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Predictive state (for high risk equipment)
CREATE TABLE predictive_state (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id UUID NOT NULL,
  equipment_id UUID NOT NULL REFERENCES pms_equipment(id),
  risk_score DECIMAL(3,2) NOT NULL DEFAULT 0,
  confidence DECIMAL(3,2) NOT NULL DEFAULT 0,
  failure_modes JSONB,
  recommended_actions JSONB,
  last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(equipment_id)
);

-- RLS policies
ALTER TABLE action_executions ENABLE ROW LEVEL SECURITY;
ALTER TABLE symptom_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE situation_detections ENABLE ROW LEVEL SECURITY;
ALTER TABLE suggestion_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE predictive_state ENABLE ROW LEVEL SECURITY;

CREATE POLICY "vessel_isolation" ON action_executions
  FOR ALL USING (yacht_id IN (SELECT yacht_id FROM user_profiles WHERE id = auth.uid()));
CREATE POLICY "vessel_isolation" ON symptom_reports
  FOR ALL USING (yacht_id IN (SELECT yacht_id FROM user_profiles WHERE id = auth.uid()));
CREATE POLICY "vessel_isolation" ON situation_detections
  FOR ALL USING (yacht_id IN (SELECT yacht_id FROM user_profiles WHERE id = auth.uid()));
CREATE POLICY "vessel_isolation" ON suggestion_log
  FOR ALL USING (yacht_id IN (SELECT yacht_id FROM user_profiles WHERE id = auth.uid()));
CREATE POLICY "vessel_isolation" ON predictive_state
  FOR ALL USING (yacht_id IN (SELECT yacht_id FROM user_profiles WHERE id = auth.uid()));

-- Indexes
CREATE INDEX idx_action_executions_yacht ON action_executions(yacht_id, created_at DESC);
CREATE INDEX idx_symptom_reports_yacht ON symptom_reports(yacht_id, equipment_label, symptom_code);
CREATE INDEX idx_situation_detections_yacht ON situation_detections(yacht_id, created_at DESC);
CREATE INDEX idx_predictive_state_equipment ON predictive_state(equipment_id);
```

---

## SECTION 8: GITHUB WORKFLOWS

### 8.1 Workflow Files

```
.github/workflows/
├── ci.yml              # Lint + Type check + Unit tests
├── test-full.yml       # Full test suite (220 scenarios)
├── db-migrate.yml      # Supabase migrations
└── deploy.yml          # Deploy to Vercel
```

---

## SECTION 9: IMPLEMENTATION PHASES

### Phase 1: Foundation
- [ ] Create `src/lib/microactions/` directory structure
- [ ] Implement MICROACTION_REGISTRY with all 57 actions
- [ ] Create types.ts with all TypeScript types
- [ ] Write 15 unit tests for registry
- [ ] **Verify: `npm run type-check` passes**

### Phase 2: Handlers
- [ ] Convert all 16 Python handler files to TypeScript
- [ ] Implement ResponseBuilder class
- [ ] Implement SignedUrlGenerator
- [ ] Write 15 unit tests per handler (16 × 15 = 240 tests)
- [ ] **Verify: All handler tests pass**

### Phase 3: Situation Engine
- [ ] Create `src/lib/situations/` directory structure
- [ ] Implement SituationEngine class
- [ ] Implement 3 pattern detectors
- [ ] Implement 2 policy engines (engineering, captain)
- [ ] Create required DB functions
- [ ] Write 15 unit tests for engine
- [ ] **Verify: Situation detection works with test data**

### Phase 4: Action Router
- [ ] Create `src/lib/action-router/` directory structure
- [ ] Implement intent parser
- [ ] Implement entity resolver
- [ ] Implement action matcher
- [ ] Write 15 unit tests for router
- [ ] **Verify: Query "generator faults" routes correctly**

### Phase 5: Database
- [ ] Create all new tables (action_executions, symptom_reports, etc.)
- [ ] Create all RLS policies
- [ ] Create all RPC functions
- [ ] Run migrations on test database
- [ ] **Verify: Tables exist with `supabase db execute --sql "SELECT..."`**

### Phase 6: Integration Tests
- [ ] Write 15 integration tests per module
- [ ] Test handler + DB integration
- [ ] Test situation + DB integration
- [ ] Test router + DB integration
- [ ] **Verify: All integration tests pass against real DB**

### Phase 7: E2E Scenarios
- [ ] Import scenario_matrix.json
- [ ] Write 60 normal scenario tests
- [ ] Write 60 edge scenario tests
- [ ] Write 40 abuse scenario tests
- [ ] Write 30 security scenario tests
- [ ] Write 30 regression scenario tests
- [ ] **Verify: 220 scenarios passing**

### Phase 8: GitHub Workflows
- [ ] Create ci.yml
- [ ] Create test-full.yml
- [ ] Create db-migrate.yml
- [ ] Configure GitHub secrets
- [ ] **Verify: All workflows green**

---

## SECTION 10: SUCCESS CRITERIA

- [ ] All 57 microactions registered and executable
- [ ] All 16 handlers converted to TypeScript
- [ ] Situation engine detecting 3 pattern types
- [ ] Action router parsing intents and resolving entities
- [ ] All database tables created with RLS
- [ ] **220 E2E scenarios passing**
- [ ] **15 tests per unit test file (all passing)**
- [ ] 90%+ code coverage
- [ ] All GitHub workflows green
- [ ] No TypeScript errors
- [ ] No ESLint errors

---

## SECTION 11: REFERENCE FILES

Read these files from /Users/celeste7/Desktop/Cloud_PMS_docs_v2/:

| File | Purpose |
|------|---------|
| 03_MICROACTIONS/MICRO_ACTION_REGISTRY.md | Complete action list |
| 03_MICROACTIONS/ACTION_OFFERING_MAP.md | Card → action mappings |
| 03_MICROACTIONS/ACTION_OFFERING_RULES.md | When to offer actions |
| 04_HANDLERS/*.py | Handler implementations (convert to TS) |
| 05_SITUATIONS/situation_engine.py | Situation detection |
| 06_TESTING/scenario_matrix.json | 220 test scenarios |
| 11_ACTION_ROUTER/ | Router specs |
| 12_ACTION_SPECIFICATIONS/ | Action execution specs |
| GROUND_TRUTH_FOR_CLAUDE.md | System architecture & common issues |

---

## BEGIN IMPLEMENTATION

**Before starting:**
1. Confirm handover_export is complete
2. Read GROUND_TRUTH_FOR_CLAUDE.md
3. Read the spec files for Phase 1
4. Verify what exists vs what doesn't
5. Ask questions if anything is unclear

**Then start with Phase 1: Foundation — Create the microaction registry.**

**Target:** `/Users/celeste7/Documents/Cloud_PMS/src/lib/microactions/`
