# E021: EXPLAINABILITY LAYER

**Date:** 2026-01-21
**Phase:** 10 - Decision Policy Layer
**Status:** LOCKED

---

## Core Principle

**If you can't explain it, don't show it.**

Every surfaced action must answer: **"Why am I seeing this?"**

---

## Explanation Payload

Every `ActionDecision` includes explanation:

```typescript
interface ActionExplanation {
  // Short human-readable label
  short: string;

  // Reasons why action is shown/hidden/disabled
  reasons: string[];

  // Confidence breakdown (for debugging/power users)
  confidence_breakdown?: {
    intent: { score: number; reason: string };
    entity: { score: number; reason: string };
    situation: { score: number; reason: string };
  };
}
```

---

## Explanation Templates

### Template Structure

Each action in E017 has an `explanation_template`:

```yaml
create_work_order_from_fault:
  explanation_template: "Create work order to resolve fault {fault.title}"
```

At runtime, variables are substituted:

```typescript
function buildExplanation(template: string, context: Context): string {
  return template.replace(/\{([^}]+)\}/g, (_, path) => {
    return getNestedValue(context, path) || '[unknown]';
  });
}

// Example:
// "Create work order to resolve fault {fault.title}"
// → "Create work order to resolve fault Generator Overheat"
```

---

## Reason Generation

### For Shown Actions

```typescript
function generateShowReasons(decision: ActionDecision, context: Context): string[] {
  const reasons: string[] = [];

  // Entity reason
  if (decision.confidence.entity_match >= 0.8) {
    reasons.push(`${context.primary_entity.type} identified: ${context.primary_entity.name}`);
  } else if (decision.confidence.entity_match >= 0.5) {
    reasons.push(`${context.primary_entity.type} context available`);
  }

  // Intent reason
  if (decision.confidence.intent_match >= 0.8) {
    reasons.push(`Detected intent: ${context.detected_intent[0]}`);
  } else if (decision.confidence.intent_match >= 0.5) {
    reasons.push(`Action matches current context`);
  }

  // Situation reason
  if (decision.confidence.situation_match === 1.0) {
    reasons.push(getSituationReason(context.situation));
  }

  return reasons;
}

function getSituationReason(situation: Situation): string {
  if (situation.work_order_in_progress) return "Work order is in progress";
  if (situation.fault_open) return "Fault is open and active";
  if (situation.fault_has_no_work_order) return "No work order exists yet";
  // ... etc
}
```

### For Hidden Actions

```typescript
function generateHideReasons(decision: ActionDecision, context: Context): string[] {
  const reasons: string[] = [];

  // Below threshold
  if (decision.confidence.total < decision.threshold) {
    reasons.push(`Confidence ${(decision.confidence.total * 100).toFixed(0)}% below threshold`);
  }

  // Specific component failures
  if (decision.confidence.intent_match < 0.3) {
    reasons.push("No clear intent for this action");
  }
  if (decision.confidence.entity_match < 0.5) {
    reasons.push("Required entity not identified");
  }

  return reasons;
}
```

### For Disabled Actions

```typescript
function generateDisabledReason(guard: StateGuard, context: Context): string {
  // Map guard failures to user-friendly messages
  const REASON_MAP: Record<string, string> = {
    'work_order_open': "Start the work order first",
    'work_order_closed': "Work order is already closed",
    'work_order_cancelled': "Work order was cancelled",
    'fault_closed': "Fault is already resolved",
    'fault_has_work_order': "A work order already exists for this fault",
    'user_not_hod': "This action requires supervisor permissions",
    'not_in_shipyard': "Only available in shipyard mode",
  };

  return REASON_MAP[guard.blocked_by] || `Blocked by: ${guard.blocked_by}`;
}
```

---

## Full Explanation Examples

### Shown Action

```json
{
  "action": "create_work_order_from_fault",
  "show": true,
  "confidence": 0.88,
  "explanation": {
    "short": "Create work order to resolve Generator Overheat fault",
    "reasons": [
      "Fault identified: Generator Overheat",
      "Detected intent: schedule repair",
      "No work order exists yet"
    ],
    "confidence_breakdown": {
      "intent": { "score": 0.7, "reason": "Matched 'repair' intent" },
      "entity": { "score": 1.0, "reason": "Fault ID confirmed" },
      "situation": { "score": 1.0, "reason": "No existing work order" }
    }
  }
}
```

### Hidden Action

```json
{
  "action": "close_work_order",
  "show": false,
  "confidence": 0.40,
  "explanation": {
    "short": "Close work order",
    "reasons": [
      "Confidence 40% below threshold (60%)",
      "Work order must be started first"
    ],
    "confidence_breakdown": {
      "intent": { "score": 0.0, "reason": "No close intent detected" },
      "entity": { "score": 1.0, "reason": "Work order ID confirmed" },
      "situation": { "score": 0.0, "reason": "Status is 'open', not 'in_progress'" }
    }
  }
}
```

### Disabled Action

```json
{
  "action": "assign_work_order",
  "show": true,
  "disabled": true,
  "confidence": 0.75,
  "explanation": {
    "short": "Assign work order to team member",
    "reasons": [
      "Work order identified",
      "Action available for supervisors"
    ]
  },
  "disabled_reason": "This action requires supervisor permissions"
}
```

---

## UI Presentation

### Tooltip on Hover

```tsx
function ActionTooltip({ explanation }: { explanation: ActionExplanation }) {
  return (
    <TooltipContent>
      <p className="font-medium">{explanation.short}</p>
      <ul className="mt-1 text-sm text-muted">
        {explanation.reasons.map((reason, i) => (
          <li key={i}>• {reason}</li>
        ))}
      </ul>
    </TooltipContent>
  );
}
```

### Debug Panel (Development)

```tsx
function DebugExplanation({ decision }: { decision: ActionDecision }) {
  if (process.env.NODE_ENV !== 'development') return null;

  return (
    <div className="debug-panel">
      <h4>{decision.action}</h4>
      <p>Show: {decision.show ? 'Yes' : 'No'}</p>
      <p>Confidence: {(decision.confidence * 100).toFixed(0)}%</p>
      {decision.explanation.confidence_breakdown && (
        <ul>
          <li>Intent: {decision.explanation.confidence_breakdown.intent.score}</li>
          <li>Entity: {decision.explanation.confidence_breakdown.entity.score}</li>
          <li>Situation: {decision.explanation.confidence_breakdown.situation.score}</li>
        </ul>
      )}
    </div>
  );
}
```

---

## Logging for Audit

Every decision is logged with full explanation:

```typescript
interface DecisionAuditLog {
  timestamp: string;
  user_id: string;
  yacht_id: string;
  session_id: string;

  // What was decided
  action: string;
  decision: 'show' | 'hide' | 'disable';

  // Why
  confidence: {
    total: number;
    intent: number;
    entity: number;
    situation: number;
  };
  reasons: string[];
  blocked_by?: string;

  // Context snapshot
  context: {
    detected_intent: string[];
    entities: { type: string; id: string; name: string }[];
    situation: Record<string, boolean>;
  };
}
```

### Log Query Examples

```sql
-- Why was action hidden?
SELECT * FROM decision_audit_log
WHERE action = 'close_work_order'
  AND decision = 'hide'
  AND user_id = 'abc123'
ORDER BY timestamp DESC
LIMIT 10;

-- Low confidence decisions
SELECT action, AVG(confidence_total) as avg_conf, COUNT(*) as count
FROM decision_audit_log
WHERE confidence_total < 0.6
GROUP BY action
ORDER BY count DESC;
```

---

## API Response Format

When fetching actions for a context:

```typescript
// Request
POST /v1/actions/available
{
  "context": {
    "yacht_id": "85fe1119-...",
    "entities": [
      { "type": "fault", "id": "1f41d11f-..." }
    ],
    "detected_intent": ["diagnose", "troubleshoot"]
  },
  "include_explanations": true
}

// Response
{
  "decisions": [
    {
      "action": "diagnose_fault",
      "show": true,
      "confidence": 0.95,
      "tier": "primary",
      "explanation": {
        "short": "AI diagnosis for Generator Overheat fault",
        "reasons": [
          "Fault identified: Generator Overheat",
          "Detected intent: troubleshoot"
        ]
      }
    },
    // ... more decisions
  ],
  "context_summary": {
    "primary_entity": "fault:1f41d11f-...",
    "detected_intents": ["diagnose", "troubleshoot"],
    "environment": "at_sea",
    "user_role": "engineer"
  }
}
```

---

## Explainability Rules (Non-Negotiable)

1. **Every shown action has explanation.short**
2. **Every shown action has at least one reason**
3. **Every hidden action has at least one reason**
4. **Every disabled action has disabled_reason**
5. **All decisions are logged with full context**
6. **Debug mode shows confidence breakdown**

---

## Failure Mode

If explanation cannot be generated:

```typescript
function safeExplanation(action: string, context: Context): ActionExplanation {
  try {
    return generateExplanation(action, context);
  } catch (e) {
    // Log error
    console.error(`Failed to generate explanation for ${action}`, e);

    // Return safe default
    return {
      short: getActionLabel(action),
      reasons: ["Available based on current context"]
    };
  }
}
```

**If even the safe default fails → DO NOT SHOW THE ACTION.**

---

## Validation Checklist

| Check | Requirement |
|-------|-------------|
| `explanation.short` always populated | Never undefined |
| `explanation.reasons` always has items | At least 1 reason |
| `disabled_reason` when disabled | Never undefined when `disabled: true` |
| Audit log captures all decisions | No silent decisions |
| Templates render without error | All variables available |

---

**Document:** E021_EXPLAINABILITY.md
**Completed:** 2026-01-21
