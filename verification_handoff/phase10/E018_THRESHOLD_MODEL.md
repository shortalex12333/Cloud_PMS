# E018: THRESHOLD MODEL

**Date:** 2026-01-21
**Phase:** 10 - Decision Policy Layer
**Status:** LOCKED

---

## Purpose

Replace binary triggers with confidence-weighted decisions.

**Core Principle:** Binary logic is why the system feels dumb.

---

## Confidence Scoring Model

### Score Components

| Component | Weight | Description |
|-----------|--------|-------------|
| **intent_match** | 0.40 | How well user intent matches action purpose |
| **entity_match** | 0.40 | How strong the entity context is |
| **situation_match** | 0.20 | How well current state matches requirements |
| **Total** | 1.00 | Weighted sum |

### Calculation

```typescript
interface ConfidenceScore {
  intent_match: number;    // 0.0 - 1.0
  entity_match: number;    // 0.0 - 1.0
  situation_match: number; // 0.0 - 1.0
  total: number;           // Weighted sum
  reasons: string[];       // Why each score was given
}

function calculateConfidence(
  action: string,
  context: DecisionContext
): ConfidenceScore {
  const contract = getTriggerContract(action);

  const intent_match = scoreIntentMatch(context.detected_intent, contract.requires.intent);
  const entity_match = scoreEntityMatch(context.entities, contract.requires.entities);
  const situation_match = scoreSituationMatch(context.situation, contract.requires.situation);

  const total = (intent_match * 0.4) + (entity_match * 0.4) + (situation_match * 0.2);

  return {
    intent_match,
    entity_match,
    situation_match,
    total,
    reasons: buildReasons(intent_match, entity_match, situation_match, contract)
  };
}
```

---

## Thresholds

| Threshold | Score | Behavior |
|-----------|-------|----------|
| **suppress** | < 0.50 | Do not show action |
| **show** | >= 0.50 | Show in UI (conditional placement) |
| **auto_suggest** | >= 0.85 | Surface as primary recommendation |
| **auto_execute** | FORBIDDEN | Never auto-execute mutations |

### Tier-Specific Thresholds

| Tier | Show Threshold | Auto-Suggest Threshold |
|------|---------------|----------------------|
| Primary | 0.50 | 0.80 |
| Conditional | 0.60 | 0.90 |
| Rare | 0.70 | 0.95 |

---

## Intent Match Scoring

### Scoring Rules

```typescript
function scoreIntentMatch(
  detected: string[],
  required: string[]
): number {
  if (!detected || detected.length === 0) {
    return 0.0;  // No intent = no match
  }

  // Exact match
  const exactMatches = detected.filter(d => required.includes(d));
  if (exactMatches.length > 0) {
    return 1.0;
  }

  // Semantic similarity (via embedding or keyword overlap)
  const semanticScore = calculateSemanticSimilarity(detected, required);

  return semanticScore;
}
```

### Intent Categories

| Category | Keywords | Score if Detected |
|----------|----------|-------------------|
| **explicit_action** | "create", "close", "report", "add" | 1.0 |
| **implicit_action** | "need to", "should", "fix", "broken" | 0.7 |
| **information_query** | "what", "show", "view", "list" | 0.5 for mutations, 1.0 for reads |
| **ambiguous** | "help", "this", "check" | 0.3 |
| **none_detected** | - | 0.0 |

---

## Entity Match Scoring

### Scoring Rules

```typescript
function scoreEntityMatch(
  present: Entity[],
  required: EntityRequirement
): number {
  if (required.min) {
    // All required entities must be present
    const allPresent = required.min.every(req =>
      present.some(p => p.type === req)
    );
    if (!allPresent) return 0.0;

    // Score based on entity quality
    return scoreEntityQuality(present, required.min);
  }

  if (required.min_one_of) {
    // At least one required entity must be present
    const hasOne = required.min_one_of.some(req =>
      present.some(p => p.type === req)
    );
    if (!hasOne) return 0.0;

    return scoreEntityQuality(present, required.min_one_of);
  }

  // No entity requirement
  return 1.0;
}

function scoreEntityQuality(
  present: Entity[],
  types: string[]
): number {
  let score = 0.5;  // Base score for presence

  // Bonus for ID confirmed (not just name match)
  if (present.some(p => p.id)) score += 0.3;

  // Bonus for recent entity (not stale context)
  if (present.some(p => p.resolved_at > Date.now() - 30000)) score += 0.2;

  return Math.min(score, 1.0);
}
```

### Entity Quality Levels

| Quality | Description | Score |
|---------|-------------|-------|
| **confirmed** | ID resolved, fresh context | 1.0 |
| **probable** | Name matched, ID found | 0.8 |
| **possible** | Partial match, ambiguous | 0.5 |
| **stale** | Context > 30s old | 0.3 |
| **missing** | Required entity not found | 0.0 |

---

## Situation Match Scoring

### Scoring Rules

```typescript
function scoreSituationMatch(
  current: Situation,
  required: string[]
): number {
  if (required.length === 0) {
    return 1.0;  // No situation requirement
  }

  // Check forbidden contexts first
  if (checkForbiddenContexts(current)) {
    return 0.0;  // Hard block
  }

  // Score required situations
  const matches = required.filter(req => situationMatches(current, req));
  return matches.length / required.length;
}
```

### Situation Checks

| Situation | Check | Score if True |
|-----------|-------|---------------|
| work_order_active | status in [open, in_progress] | 1.0 |
| work_order_open | status == open | 1.0 |
| work_order_in_progress | status == in_progress | 1.0 |
| fault_open | status != closed | 1.0 |
| fault_closed | status == closed | 1.0 |
| user_is_hod | role in HOD_ROLES | 1.0 |
| environment_shipyard | environment == shipyard | 1.0 |
| equipment_has_manual | has_manual == true | 1.0 |
| fault_has_no_work_order | !has_work_order | 1.0 |

---

## Forbidden Context Handling

Forbidden contexts are **hard blocks** - they override confidence scoring.

```typescript
function checkForbiddenContexts(
  action: string,
  context: DecisionContext
): { blocked: boolean; reason: string } {
  const contract = getTriggerContract(action);

  for (const forbidden of contract.forbidden) {
    if (contextMatches(context, forbidden)) {
      return {
        blocked: true,
        reason: getForbiddenReason(forbidden)
      };
    }
  }

  return { blocked: false, reason: '' };
}
```

### Forbidden Reasons

| Forbidden Context | User-Friendly Reason |
|------------------|---------------------|
| work_order_closed | "Work order is already closed" |
| work_order_cancelled | "Work order was cancelled" |
| fault_closed | "Fault is already resolved" |
| fault_has_work_order | "A work order already exists for this fault" |
| user_not_hod | "This action requires supervisor permissions" |
| no_equipment | "No equipment selected" |
| no_work_order | "No work order selected" |
| no_fault | "No fault selected" |

---

## Decision Output Format

```typescript
interface ActionDecision {
  action: string;
  show: boolean;
  confidence: ConfidenceScore;
  tier: 'primary' | 'conditional' | 'rare';
  blocked?: {
    reason: string;
    forbidden_context: string;
  };
  explanation: {
    short: string;      // "Create work order for Main Engine"
    reasons: string[];  // ["Equipment identified", "No existing work order"]
  };
}
```

### Example Decisions

```json
{
  "action": "create_work_order_from_fault",
  "show": true,
  "confidence": {
    "intent_match": 0.7,
    "entity_match": 1.0,
    "situation_match": 1.0,
    "total": 0.88,
    "reasons": [
      "Detected repair intent (0.7)",
      "Fault ID confirmed (1.0)",
      "No existing work order (1.0)"
    ]
  },
  "tier": "conditional",
  "explanation": {
    "short": "Create work order to resolve Generator Overheat fault",
    "reasons": [
      "Fault requires attention",
      "No work order exists yet"
    ]
  }
}
```

```json
{
  "action": "close_work_order",
  "show": false,
  "confidence": {
    "intent_match": 0.0,
    "entity_match": 1.0,
    "situation_match": 0.0,
    "total": 0.40,
    "reasons": [
      "No close intent detected (0.0)",
      "Work order ID confirmed (1.0)",
      "Work order not in progress (0.0)"
    ]
  },
  "tier": "conditional",
  "blocked": {
    "reason": "Work order must be started before closing",
    "forbidden_context": "work_order_open"
  }
}
```

---

## Logging Requirements

Every decision MUST be logged for explainability:

```typescript
interface DecisionLog {
  timestamp: string;
  user_id: string;
  session_id: string;
  action: string;
  decision: 'show' | 'suppress' | 'block';
  confidence: ConfidenceScore;
  context_snapshot: {
    entities: Entity[];
    detected_intent: string[];
    situation: Situation;
  };
  blocked_reason?: string;
}
```

---

## Rules (Non-Negotiable)

1. **No mutation below show threshold (0.50)**
2. **No auto-execute, ever**
3. **All decisions must be logged**
4. **Forbidden contexts are hard blocks**
5. **Scores must be explainable**

---

## Implementation Priority

| Priority | Component | Reason |
|----------|-----------|--------|
| P0 | Forbidden context checks | Safety first |
| P0 | Entity match scoring | Core functionality |
| P1 | Intent match scoring | Better UX |
| P1 | Decision logging | Explainability |
| P2 | Situation match scoring | Refinement |
| P2 | Semantic intent matching | Advanced UX |

---

**Document:** E018_THRESHOLD_MODEL.md
**Completed:** 2026-01-21
