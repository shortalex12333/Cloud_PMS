# PHASE 5: UX Flow & Scenarios Template

**Lens**: [LENS_NAME]
**Phase**: 5 of 8
**Output**: `[lens_name]_lens_PHASE_5_SCENARIOS.md`

---

## Pre-Requisites (must be complete)

- [ ] PHASE 1 (Scope) frozen
- [ ] PHASE 2 (DB Truth) frozen
- [ ] PHASE 3 (Entity Graph) frozen
- [ ] PHASE 4 (Actions) frozen

---

## Scenario Structure (each of 10 must include)

```
### Scenario N: [Title]

**User Context**: [Role, situation, device]

**Query**: "[Exact natural language query]"

---

#### Traditional Software Flow
1. [Step 1]
2. [Step 2]
...
**Total Steps**: X

#### Celeste Flow
1. User types query
2. [What RAG surfaces]
3. [Focus event if any]
4. [Context menu if any]
5. [Result]
**Total Steps**: Y

---

**Data Surfaced**:
- RAG: [What documents/chunks]
- SQL: [What direct queries]

**Focus Event**: [Yes/No - what entity focused]

**Context Menu Activation**: [Yes/No - what actions available]

**Escape Hatch**: [To which lens, if any]

**Verification Checklist**:
- [ ] No ambient buttons
- [ ] No dashboard referenced
- [ ] Query-first maintained
- [ ] Action only if intent in query OR entity focused
```

---

## The 10 Scenarios

### Scenario 1: Basic Lookup
**Pattern**: User wants to find/view entity

### Scenario 2: Status Check
**Pattern**: User wants current state of entity

### Scenario 3: History Query
**Pattern**: User wants past events/changes for entity

### Scenario 4: Related Items
**Pattern**: User wants linked entities (FK traversal)

### Scenario 5: Action Intent (Primary)
**Pattern**: User query includes action verb (most common action)

### Scenario 6: Action Intent (Secondary)
**Pattern**: User query includes action verb (less common action)

### Scenario 7: Comparison/Multiple
**Pattern**: User wants to compare or see multiple entities

### Scenario 8: Alert/Exception
**Pattern**: User checking for problems, overdue, low stock, etc.

### Scenario 9: Cross-Lens Navigation
**Pattern**: User starts here but needs to go elsewhere (escape hatch)

### Scenario 10: Edge Case
**Pattern**: Unusual but valid user flow

---

## Forbidden Patterns (auto-fail if present)

| Pattern | Why Forbidden |
|---------|---------------|
| "User clicks dashboard" | No dashboards |
| "User navigates to..." | No navigation |
| "Button appears" (without focus) | Actions require focus |
| "System suggests..." (unsolicited) | User-initiated only |
| "Menu shows all actions" | Context menu only after focus |

---

## Quality Checklist (all must pass)

| Check | Pass |
|-------|------|
| All 10 scenarios complete | [ ] |
| Each has Traditional vs Celeste comparison | [ ] |
| Each has step count | [ ] |
| Each has data surfaced | [ ] |
| Each has focus event (Yes/No) | [ ] |
| Each has context menu (Yes/No) | [ ] |
| Each has escape hatch (if any) | [ ] |
| No ambient buttons in ANY scenario | [ ] |
| No dashboard references in ANY scenario | [ ] |
| All actions trace to PHASE 4 contract | [ ] |

---

## GATE: Phase 5 Complete

| Criterion | Status |
|-----------|--------|
| All 10 scenarios written | [ ] |
| All quality checks pass | [ ] |
| No forbidden patterns | [ ] |
| Human review complete | [ ] |

**PHASE 5 FROZEN**: [ ] Date: ________
