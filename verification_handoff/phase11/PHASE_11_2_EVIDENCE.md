# Phase 11.2: Frontend Contract Replacement - EVIDENCE

**Date:** 2026-01-21
**Status:** CODE COMPLETE (Migration Path Provided)

---

## Deliverables

### 1. useActionDecisions Hook

**File:** `apps/web/src/lib/microactions/hooks/useActionDecisions.ts`

```typescript
export function useActionDecisions(
  options: UseActionDecisionsOptions = {}
): UseActionDecisionsReturn {
  // Calls /v1/decisions endpoint
  // Returns decisions with confidence, reasons, breakdown
  // Provides isAllowed(), getDecision(), getDisabledReason()
}
```

**Usage:**
```tsx
const { isAllowed, getDisabledReason, byTier } = useActionDecisions({
  detected_intents: ['diagnose'],
  entities: [{ type: 'fault', id: faultId, status: 'reported' }],
});

// Check if action is allowed
if (isAllowed('diagnose_fault')) {
  // Show button
}

// Get disabled reason
const reason = getDisabledReason('close_work_order');
// → "Work order must be started first"
```

### 2. Deprecated Client-Side Triggers

**File:** `apps/web/src/lib/microactions/triggers.ts`

```typescript
/**
 * @deprecated Phase 11.2: Use useActionDecisions hook instead.
 */
export function shouldShowAction(actionName, context) {
  console.warn(`[DEPRECATED] shouldShowAction('${actionName}') called.`);
  // ... legacy logic kept for backward compatibility
}
```

### 3. ActionPanel Component (Example)

**File:** `apps/web/src/components/actions/ActionPanel.tsx`

Demonstrates E020 pattern:
- Groups actions by tier (primary, conditional, rare)
- Shows disabled actions with reason tooltip
- Renders from server decisions, not client logic

---

## Migration Guide

### Before (Deprecated)

```tsx
// ❌ Client-side decision making
import { shouldShowAction } from '@/lib/microactions/triggers';

function FaultCard({ fault }) {
  const triggerContext = {
    fault: { id: fault.id, status: fault.status },
    user_role: 'engineer',
  };

  const showDiagnose = shouldShowAction('diagnose_fault', triggerContext);
  const showCreateWO = shouldShowAction('create_work_order_from_fault', triggerContext);

  return (
    <div>
      {showDiagnose && <Button>Diagnose</Button>}
      {showCreateWO && <Button>Create WO</Button>}
    </div>
  );
}
```

### After (Phase 11.2)

```tsx
// ✅ Server-driven decisions
import { useActionDecisions } from '@/lib/microactions/hooks';

function FaultCard({ fault }) {
  const { isAllowed, getDisabledReason } = useActionDecisions({
    detected_intents: ['diagnose'],
    entities: [{ type: 'fault', id: fault.id, status: fault.status }],
  });

  return (
    <div>
      <Button
        disabled={!isAllowed('diagnose_fault')}
        title={getDisabledReason('diagnose_fault')}
      >
        Diagnose
      </Button>
      <Button
        disabled={!isAllowed('create_work_order_from_fault')}
        title={getDisabledReason('create_work_order_from_fault')}
      >
        Create WO
      </Button>
    </div>
  );
}
```

---

## E020 Compliance

| Rule | Implementation |
|------|----------------|
| "UI must render decisions, not make them" | useActionDecisions calls server |
| Tier-to-UI mapping | byTier groups decisions |
| Disabled state with reason | getDisabledReason() provides message |
| No hardcoded visibility | All from ActionDecision.allowed |
| Explanation available | ActionDecision.explanation + reasons |

---

## Files Created/Modified

| File | Action |
|------|--------|
| `apps/web/src/lib/microactions/hooks/useActionDecisions.ts` | Created |
| `apps/web/src/lib/microactions/hooks/index.ts` | Modified (export added) |
| `apps/web/src/lib/microactions/triggers.ts` | Modified (deprecated) |
| `apps/web/src/components/actions/ActionPanel.tsx` | Created (example) |

---

## TypeScript Types Exported

```typescript
// From useActionDecisions.ts
export interface ActionDecision {
  action: string;
  allowed: boolean;
  tier: 'primary' | 'conditional' | 'rare';
  confidence: number;
  reasons: string[];
  breakdown: ConfidenceBreakdown;
  blocked_by?: BlockedBy;
  explanation: string;
}

export interface EntityInput {
  type: 'work_order' | 'fault' | 'equipment' | 'part' | 'purchase' | 'handover';
  id?: string;
  name?: string;
  status?: string;
  has_work_order?: boolean;
  has_checklist?: boolean;
  has_manual?: boolean;
  acknowledged?: boolean;
}
```

---

## Deprecation Warnings

When deprecated functions are called, they emit console warnings:

```
[DEPRECATED] shouldShowAction('diagnose_fault') called.
Use useActionDecisions hook instead (Phase 11.2).
```

This helps track migration progress and identify remaining usages.

---

## Components to Migrate

The following components use `shouldShowAction` or `triggerContext` and need migration:

```bash
# Find usages
grep -r "shouldShowAction" apps/web/src/
grep -r "triggerContext" apps/web/src/components/
```

Key components:
- `FaultCard.tsx`
- `WorkOrderCard.tsx`
- `EquipmentCard.tsx`
- `useAvailableActions.ts`
- `SituationPanel.tsx`

---

## Phase 11.2 Checklist

| Item | Status |
|------|--------|
| useActionDecisions hook created | ✅ |
| Hook exported from index | ✅ |
| shouldShowAction deprecated | ✅ |
| getVisibleActions deprecated | ✅ |
| ActionPanel example created | ✅ |
| TypeScript types exported | ✅ |
| Migration guide documented | ✅ |
| Component migration | ⏳ Gradual |

---

## Definition of DONE

Phase 11.2 is **code complete** with migration path. Full migration requires:

1. **Deploy backend** (11.1 + 11.3)
2. **Run SQL migration** on tenant DB
3. **Update components** to use useActionDecisions
4. **Remove deprecated code** after migration complete

---

**Document:** PHASE_11_2_EVIDENCE.md
**Completed:** 2026-01-21
