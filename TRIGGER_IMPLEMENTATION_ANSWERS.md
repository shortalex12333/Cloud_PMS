# TRIGGER IMPLEMENTATION - ANSWERS TO YOUR QUESTIONS

---

## Question 1: Where should trigger logic live?

**ANSWER: Extend the existing `useAvailableActions` hook**

```
Location: /apps/web/src/lib/microactions/hooks/useAvailableActions.ts
```

**Why this hook?**
- Already receives: cardType, userRole, entityId, yachtId
- Already filters by: handler existence, side effect type
- Missing: trigger condition evaluation

**What to add:**
```typescript
// Add a new function to evaluate trigger rules
function evaluateTriggerConditions(
  action: MicroAction,
  context: TriggerContext
): { allowed: boolean; reason?: string } {
  // Check role restrictions
  // Check entity conditions (is fault known? is part in stock?)
  // Check environmental context
}
```

**Architecture:**
```
Card Component (FaultCard)
        ↓
useAvailableActions({ cardType: 'fault', userRole, entityId, ... })
        ↓
getActionsForCardType('fault')  →  Returns all fault actions
        ↓
evaluateTriggerConditions(action, context)  →  NEW: Check rules
        ↓
Returns only actions that pass trigger evaluation
        ↓
Card renders only those buttons
```

---

## Question 2: Where does user role come from?

**ANSWER: AuthContext → `user.role`**

```
Location: /apps/web/src/contexts/AuthContext.tsx
```

**How to access:**
```typescript
import { useContext } from 'react';
import { AuthContext, isHOD } from '@/contexts/AuthContext';

function MyComponent() {
  const { user } = useContext(AuthContext);

  // Direct role check
  const role = user?.role;  // 'chief_engineer', 'eto', 'captain', 'manager', 'member'

  // Helper function (already exists!)
  const canApprove = isHOD(user);  // true for chief_engineer, eto, captain, manager
}
```

**Role values:**
```typescript
// From AuthContext line 49:
['chief_engineer', 'eto', 'captain', 'manager']  // HOD roles
'member'  // Default/crew role
```

**Role hierarchy (from ACTION_OFFERING_RULES.md):**
```
Crew (member)     → view_*, add_note, add_photo, log_part_usage
HOD (chief/eto)   → All crew + assign_work_order, approve_purchase, tag_for_survey
Management        → All HOD + fleet actions, unlimited approvals
```

---

## Question 3: What is "known_faults database"?

**ANSWER: It's Python AI recognition, NOT a Supabase table**

From ACTION_OFFERING_RULES.md line 72:
```
suggest_parts: IF fault is in known_faults database
```

**What this actually means:**
- The Python backend (pipeline-core) has AI-based fault recognition
- When a fault code/description is recognized, Python returns `is_known: true`
- "known_faults database" = Python's trained model knowledge, not a SQL table

**How to implement:**
```typescript
// When rendering FaultCard, check if Python returned recognition data
interface FaultData {
  id: string;
  code?: string;
  description: string;
  // This comes from Python AI diagnosis
  ai_diagnosis?: {
    is_known: boolean;      // ← This is the "known_faults" check
    confidence: number;
    suggested_parts?: string[];
  };
}

// In trigger evaluation:
function shouldShowSuggestParts(fault: FaultData): boolean {
  return fault.ai_diagnosis?.is_known === true;
}
```

**Alternative (if no AI data available):**
- Check if fault has a recognized `fault_code` format
- Check if fault is linked to known equipment with manual sections

---

## Question 4: Priority - All 57 at once or Cluster 1 first?

**ANSWER: Cluster 1 FIRST as template**

**Why:**
1. Cluster 1 has 7 actions - manageable scope
2. All are fault-related - same card type
3. Mix of trigger types:
   - Always show: `diagnose_fault`, `show_manual_section`, `add_fault_note`, `add_fault_photo`
   - Conditional: `suggest_parts` (if fault is known)
   - Context-aware: `create_work_order_from_fault` (always, but needs fault context)

**Cluster 1 Implementation Order:**
```
1. diagnose_fault      → Always show, auto-run
2. show_manual_section → Always show (if equipment identified)
3. view_fault_history  → Always show
4. add_fault_note      → Always show
5. add_fault_photo     → Always show
6. create_work_order_from_fault → Always show
7. suggest_parts       → CONDITIONAL: Only if fault is known
```

**Once Cluster 1 works:**
- Pattern is established
- Copy trigger logic structure to other clusters
- Each cluster has similar patterns

---

## Question 5: What does "auto-run" mean?

**ANSWER: Auto-EXECUTE when card appears (background)**

From ACTION_OFFERING_RULES.md line 63:
```
diagnose_fault (always, auto-run)
```

**What this means:**
- When a FaultCard renders, `diagnose_fault` runs AUTOMATICALLY
- User doesn't click - it happens in background
- Result appears in the card (diagnosis info)
- Button still exists for manual re-run

**How to implement:**
```typescript
// In FaultCard.tsx
useEffect(() => {
  // Auto-run diagnose_fault when card mounts
  if (fault && !fault.ai_diagnosis) {
    executeDiagnoseFault(fault.id).then(result => {
      setDiagnosisResult(result);
    });
  }
}, [fault.id]);
```

**Auto-run actions from the docs:**
- `diagnose_fault` - Run when fault card appears
- `view_smart_summary` - Run when summary requested
- `request_predictive_insight` - Run when predictive query detected

**NOT auto-run (require user click):**
- `create_work_order_from_fault` - Mutation, needs confirmation
- `suggest_parts` - May have cost implications
- Any `mutation_heavy` action

---

## IMPLEMENTATION PLAN

### Step 1: Add TriggerContext type

```typescript
// /apps/web/src/lib/microactions/types.ts

interface TriggerContext {
  // User context
  userRole: string;
  userId: string;
  yachtId: string;

  // Entity context
  entityId?: string;
  entityType: CardType;

  // Entity-specific data (for conditional checks)
  faultData?: {
    isKnown: boolean;
    faultCode?: string;
    equipmentId?: string;
  };
  partData?: {
    inStock: boolean;
    stockLevel: number;
    reorderThreshold: number;
  };

  // Environmental context
  environment?: 'at_sea' | 'port' | 'shipyard' | 'guest_trip';
}
```

### Step 2: Add trigger rules registry

```typescript
// /apps/web/src/lib/microactions/triggers.ts

const TRIGGER_RULES: Record<string, TriggerRule> = {
  diagnose_fault: {
    always: true,
    autoRun: true,
  },
  suggest_parts: {
    condition: (ctx) => ctx.faultData?.isKnown === true,
    reason: 'Only available for recognized faults',
  },
  assign_work_order: {
    roleRequired: ['chief_engineer', 'eto', 'captain', 'manager'],
    reason: 'Only HOD can assign work orders',
  },
  order_part: {
    condition: (ctx) => ctx.partData?.inStock === false ||
                        ctx.partData?.stockLevel <= ctx.partData?.reorderThreshold,
    reason: 'Only available for low/out of stock parts',
  },
};
```

### Step 3: Update useAvailableActions

```typescript
// Add trigger evaluation to the hook
const actions = useMemo(() => {
  let availableActions = getActionsForCardType(cardType);

  // Existing filters...

  // NEW: Filter by trigger conditions
  availableActions = availableActions.filter(action => {
    const rule = TRIGGER_RULES[action.action_name];
    if (!rule) return true;  // No rule = always show

    if (rule.always) return true;

    if (rule.roleRequired && !rule.roleRequired.includes(userRole)) {
      return false;
    }

    if (rule.condition && !rule.condition(triggerContext)) {
      return false;
    }

    return true;
  });

  return availableActions;
}, [cardType, userRole, triggerContext, ...]);
```

### Step 4: Update FaultCard to use hook

```typescript
// FaultCard.tsx
function FaultCard({ fault }: Props) {
  const { user } = useContext(AuthContext);

  const { actions } = useAvailableActions({
    cardType: 'fault',
    entityId: fault.id,
    userRole: user?.role,
    yachtId: user?.yachtId,
    // NEW: Pass trigger context
    triggerContext: {
      faultData: {
        isKnown: fault.ai_diagnosis?.is_known ?? false,
        faultCode: fault.code,
        equipmentId: fault.equipment_id,
      },
    },
  });

  // Only render buttons for actions that passed trigger evaluation
  return (
    <div>
      {actions.map(action => (
        <ActionButton key={action.action_name} action={action} />
      ))}
    </div>
  );
}
```

---

## FILES TO MODIFY

| File | Change |
|------|--------|
| `/lib/microactions/types.ts` | Add `TriggerContext`, `TriggerRule` types |
| `/lib/microactions/triggers.ts` | NEW FILE - trigger rules registry |
| `/lib/microactions/hooks/useAvailableActions.ts` | Add trigger evaluation |
| `/components/cards/FaultCard.tsx` | Pass trigger context, conditional render |
| `/components/cards/WorkOrderCard.tsx` | Same pattern |
| `/components/cards/EquipmentCard.tsx` | Same pattern |
| `/components/cards/PartCard.tsx` | Same pattern |

---

## SUMMARY

| Question | Answer |
|----------|--------|
| 1. Where does trigger logic live? | Extend `useAvailableActions` hook |
| 2. Where does user role come from? | `AuthContext` → `user.role` |
| 3. What is "known_faults database"? | Python AI recognition, not SQL table |
| 4. Priority: all 57 or Cluster 1 first? | **Cluster 1 first** as template |
| 5. What does "auto-run" mean? | Auto-execute in background when card appears |
