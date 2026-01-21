# E020: UX DECISION MAPPING

**Date:** 2026-01-21
**Phase:** 10 - Decision Policy Layer
**Status:** LOCKED

---

## Core Principle

**The UI must render decisions, not make them.**

All decision logic lives in:
- Trigger contracts (E017)
- Threshold model (E018)
- State guards (E019)

The UI is a **projection layer only**.

---

## Decision Flow

```
User Input
    ↓
Decision Engine (server-side)
    ↓
ActionDecision[] returned
    ↓
UI renders decisions
    ↓
User sees/acts
```

**What the UI receives:**

```typescript
interface ActionDecision {
  action: string;
  show: boolean;
  confidence: number;
  tier: 'primary' | 'conditional' | 'rare';
  disabled?: boolean;
  disabled_reason?: string;
  explanation: {
    short: string;
    reasons: string[];
  };
}
```

**What the UI does NOT do:**
- Evaluate trigger conditions
- Calculate confidence scores
- Check state guards
- Decide visibility

---

## Tier-to-UI Mapping

### Primary Tier (10 Actions)

| UI Element | Behavior |
|------------|----------|
| Position | First in action list |
| Visual | Solid button, brand color |
| Visibility | Shown if confidence >= 0.50 |
| Auto-suggest | Highlighted if confidence >= 0.80 |

**Actions:**
- view_work_order_detail
- view_work_order_checklist
- view_fault_detail
- view_worklist
- diagnose_fault
- show_manual_section
- report_fault
- add_to_handover
- add_note_to_work_order
- add_wo_note

### Conditional Tier (14 Actions)

| UI Element | Behavior |
|------------|----------|
| Position | After primary actions |
| Visual | Outline button, secondary color |
| Visibility | Shown if confidence >= 0.60 |
| Auto-suggest | Highlighted if confidence >= 0.90 |
| Disabled state | Shown with reason if blocked |

**Actions:**
- create_work_order
- close_work_order
- add_work_order_photo
- view_work_order_checklist
- update_work_order
- add_wo_hours
- add_fault_photo
- start_work_order
- acknowledge_fault
- close_fault
- update_fault
- reopen_fault
- update_equipment_status
- add_worklist_task
- create_work_order_from_fault

### Rare Tier (6 Actions)

| UI Element | Behavior |
|------------|----------|
| Position | In overflow dropdown or context menu |
| Visual | Text-only, muted color |
| Visibility | Shown only if confidence >= 0.70 |
| Auto-suggest | Never (requires explicit selection) |
| Confirmation | Required for all |

**Actions:**
- assign_work_order
- cancel_work_order
- mark_fault_false_alarm
- export_worklist
- add_parts_to_work_order
- add_wo_part

---

## Component Mapping

### ActionPanel Component

```tsx
interface ActionPanelProps {
  decisions: ActionDecision[];
  onAction: (action: string) => void;
}

function ActionPanel({ decisions, onAction }: ActionPanelProps) {
  // Group by tier
  const primary = decisions.filter(d => d.tier === 'primary' && d.show);
  const conditional = decisions.filter(d => d.tier === 'conditional' && d.show);
  const rare = decisions.filter(d => d.tier === 'rare' && d.show);

  return (
    <div className="action-panel">
      {/* Primary actions - always visible */}
      <div className="action-primary">
        {primary.map(d => (
          <ActionButton
            key={d.action}
            decision={d}
            variant="primary"
            onClick={() => onAction(d.action)}
          />
        ))}
      </div>

      {/* Conditional actions - shown inline if space */}
      {conditional.length > 0 && (
        <div className="action-conditional">
          {conditional.slice(0, 2).map(d => (
            <ActionButton
              key={d.action}
              decision={d}
              variant="secondary"
              onClick={() => onAction(d.action)}
            />
          ))}
          {conditional.length > 2 && (
            <MoreActionsDropdown actions={conditional.slice(2)} />
          )}
        </div>
      )}

      {/* Rare actions - always in dropdown */}
      {rare.length > 0 && (
        <RareActionsMenu actions={rare} onAction={onAction} />
      )}
    </div>
  );
}
```

### ActionButton Component

```tsx
interface ActionButtonProps {
  decision: ActionDecision;
  variant: 'primary' | 'secondary' | 'text';
  onClick: () => void;
}

function ActionButton({ decision, variant, onClick }: ActionButtonProps) {
  const needsConfirmation = CONFIRMATION_REQUIRED.includes(decision.action);

  return (
    <Button
      variant={variant}
      disabled={decision.disabled}
      onClick={needsConfirmation ? () => showConfirmation(decision, onClick) : onClick}
      title={decision.explanation.short}
    >
      {decision.disabled && (
        <Tooltip content={decision.disabled_reason}>
          <InfoIcon />
        </Tooltip>
      )}
      {getActionLabel(decision.action)}
    </Button>
  );
}
```

### Confidence Indicator (Optional)

For power users, show confidence:

```tsx
function ConfidenceIndicator({ confidence }: { confidence: number }) {
  if (confidence >= 0.85) return <span className="confidence-high">●●●</span>;
  if (confidence >= 0.70) return <span className="confidence-medium">●●○</span>;
  return <span className="confidence-low">●○○</span>;
}
```

---

## Visibility Rules (UI Enforced)

| Rule | Enforcement |
|------|-------------|
| No action below fold if mutation | Scroll actions into view before mutation |
| No destructive action without confirm | `CONFIRMATION_REQUIRED` list |
| No duplicate actions across panels | Decision engine dedupes |
| Read before mutate | Primary tier = mostly reads |
| Disabled shows reason | Tooltip on disabled button |

### CONFIRMATION_REQUIRED Actions

```typescript
const CONFIRMATION_REQUIRED = [
  'close_work_order',
  'cancel_work_order',
  'close_fault',
  'mark_fault_false_alarm',
  'reopen_fault',
];
```

---

## Auto-Suggest Behavior

When confidence >= auto_suggest threshold:

1. Action is visually highlighted (glow, badge)
2. Keyboard shortcut shown (e.g., "Press Enter")
3. Focus ring on primary action
4. BUT: No auto-execution, ever

```tsx
function AutoSuggestIndicator({ action }: { action: string }) {
  return (
    <div className="auto-suggest-indicator">
      <span className="badge">Suggested</span>
      <kbd>Enter</kbd>
    </div>
  );
}
```

---

## Disabled State Rendering

When action is blocked by state guard:

```tsx
function DisabledAction({ decision }: { decision: ActionDecision }) {
  return (
    <Button disabled className="action-disabled">
      {getActionLabel(decision.action)}
      <Tooltip content={decision.disabled_reason}>
        <LockIcon className="disabled-icon" />
      </Tooltip>
    </Button>
  );
}
```

### Common Disabled Reasons

| Reason | UI Message |
|--------|------------|
| work_order_closed | "Work order is closed" |
| work_order_open | "Start the work order first" |
| fault_closed | "Fault is already resolved" |
| user_not_hod | "Requires supervisor access" |
| no_equipment | "Select equipment first" |

---

## No New UI Logic Until...

The UI team must NOT add new visibility logic. All decisions come from:

1. **E017 Trigger Contracts** - What actions exist
2. **E018 Threshold Model** - What scores are required
3. **E019 State Guards** - What blocks what

**If the UI needs a new behavior:**
1. Add to trigger contract (YAML)
2. Add to threshold model (if scoring change)
3. Add to state guards (if mutual exclusion)
4. THEN update UI to render the new decision

---

## Migration Path

### Current State (Phase 9)
- UI has hardcoded trigger checks
- `shouldShowAction()` called in components
- No confidence scoring
- No state guards in UI

### Target State (Phase 10)
- UI receives `ActionDecision[]` from server/hook
- No trigger logic in components
- Confidence visible to users
- State guards enforced before render

### Migration Steps

1. **Create `useActionDecisions` hook**
   - Calls decision engine
   - Returns `ActionDecision[]`
   - Replaces all `shouldShowAction()` calls

2. **Update card components**
   - Remove direct trigger checks
   - Use `ActionPanel` with decisions

3. **Remove legacy triggers from components**
   - Delete `import { shouldShowAction }` from cards
   - Delete inline condition checks

4. **Add explanation tooltips**
   - Show reasons on hover
   - Show disabled reasons

---

## Validation Checklist

| Check | Requirement |
|-------|-------------|
| No `shouldShowAction` in components | All logic in decision engine |
| No hardcoded visibility | All from `ActionDecision.show` |
| Disabled reason always present | When `disabled: true` |
| Confirmation for destructive | All in `CONFIRMATION_REQUIRED` |
| Tier reflected in UI | Primary/Conditional/Rare styling |
| Explanation available | Every action has `explanation.short` |

---

**Document:** E020_UX_DECISION_MAPPING.md
**Completed:** 2026-01-21
