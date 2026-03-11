# Quick Reference — Entity Lenses

**For GSD Workers**

---

## One-Page Summary

```
LENS FRAMEWORK: Backend defines authority. Frontend displays.

INVARIANTS:
• 100% yacht isolation: get_user_yacht_id() on ALL queries
• Signature: '{}'::jsonb or valid payload, NEVER NULL
• No dashboard language / No ambient buttons
• Actions only after focus / Query-only activation

ACTION FLOW:
User Query → /v1/search → Filters (READ) or Actions (MUTATE)
                                    ↓
                         /v1/actions/execute (unified endpoint)
                                    ↓
                         Handler → RLS → Database

CURRENT STATUS:
• Phase 16.1 URGENT: /prepare endpoint not mounted
• Phase 17: 50% complete (readiness indicators)
• 83% E2E pass rate on production
• 3 lenses GOLD: Certificate, Work Order, Equipment
```

---

## Key Files

### Backend

| File | Purpose |
|------|---------|
| `apps/api/action_router/router.py` | Main action router |
| `apps/api/action_router/registry.py` | Action definitions |
| `apps/api/handlers/*.py` | Domain handlers |
| `apps/api/common/prefill_engine.py` | Prefill generation |
| `apps/api/common/temporal_parser.py` | NLP date parsing |
| `apps/api/routes/p0_actions_routes.py` | Action routes (mounted) |

### Frontend

| File | Purpose |
|------|---------|
| `apps/web/src/hooks/useCelesteSearch.ts` | Search hook, IntentEnvelope |
| `apps/web/src/lib/actionClient.ts` | Action API client |
| `apps/web/src/lib/filters/catalog.ts` | Filter definitions |
| `apps/web/src/lib/filters/execute.ts` | Filter execution |
| `apps/web/src/components/SuggestedActions.tsx` | Action buttons |
| `apps/web/src/components/ActionModal.tsx` | Action modal |

### Documentation

| File | Purpose |
|------|---------|
| `docs/pipeline/entity_lenses/*/v2/*_FINAL.md` | Lens specifications |
| `docs/ON_GOING_WORK/BACKEND/LENSES/` | This directory |
| `docs/ON_GOING_WORK/BACKEND/SPOTLIGHT_SEARCH/` | Search integration |

---

## Canonical SQL Functions

```sql
-- Yacht scope (ALL queries)
public.get_user_yacht_id() → UUID

-- Role checks (write operations)
public.is_hod(user_id, yacht_id) → BOOLEAN
public.is_manager() → BOOLEAN
public.get_user_role() → TEXT
```

**Use in RLS:**

```sql
-- SELECT: All crew on yacht
USING (yacht_id = public.get_user_yacht_id());

-- INSERT/UPDATE: HOD only
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
    AND is_hod(auth.uid(), public.get_user_yacht_id())
);

-- DELETE: Manager only
USING (
    yacht_id = public.get_user_yacht_id()
    AND is_manager()
);
```

---

## Action Definition Template

```python
ActionDefinition(
    action_id="create_work_order",
    label="Create Work Order",
    endpoint="/v1/work-orders/create",
    handler_type=HandlerType.INTERNAL,
    method="POST",
    allowed_roles=["engineer", "captain", "manager"],
    required_fields=["title", "type", "priority"],
    optional_fields=["description", "equipment_id", "due_date"],
    domain="work_orders",
    variant=ActionVariant.MUTATE,
    search_keywords=["create", "new", "work order", "job"],
)
```

---

## Filter Definition Template

```typescript
{
  filter_id: 'wo_overdue',
  label: 'Overdue work orders',
  domain: 'work-orders',
  entity_type: 'work_order',
  route: '/work-orders',
  query_params: { filter: 'wo_overdue' },
  keywords: ['overdue', 'past due', 'late'],
  definition: "due_date < CURRENT_DATE AND status NOT IN ('completed', 'cancelled')",
  // blocked: 'EXECUTION_MISSING: ...'  // Add if not executable
}
```

---

## Task Format (GSD Contract)

```
Task ID:
Goal (1 sentence):

WHAT (scope in):
- Exact files you will modify
- Exact functionality you will implement

WHAT NOT (scope out):
- Explicitly list what you will NOT touch

WHERE:
- File paths
- Route paths (if applicable)
- Backend endpoints involved

HOW:
- High-level implementation plan (max 6 bullets)

RISKS:
- What could break?
- How will you verify it doesn't?

DEFINITION OF DONE:
- Exact user-visible outcome
- Exact test that must pass
- Proof artifact required
```

---

## Lessons Reference

**ALWAYS read before starting a task:**

```
tasks/lessons.md
```

**Add lesson after completing tasks:**

```markdown
## LESSON: [Short Title]

**Date:** YYYY-MM-DD
**Context:** [What were we doing?]
**Failure:** [What went wrong?]
**Root Cause:** [Why?]
**Guard Added:** [Rule to prevent]
**Reusable Pattern:** [What to apply elsewhere]
**Tags:** [categories]
```

---

## Quick Commands

### GSD Workflow

```bash
# Check project status
/gsd:progress

# Plan a phase
/gsd:plan-phase 16.1

# Execute a phase
/gsd:execute-phase 17

# Verify work
/gsd:verify-work

# Add a todo
/gsd:add-todo

# Check todos
/gsd:check-todos
```

### Testing

```bash
# Run specific shard
E2E_BASE_URL=https://app.celeste7.ai npx playwright test --project=shard-8-workorders

# Run all tests
npx playwright test

# Run with visible browser
npx playwright test --headed
```

### Database

```bash
# Connect to Supabase
supabase db push

# Check RLS
psql -c "SELECT relname, relrowsecurity FROM pg_class WHERE relname LIKE 'pms_%';"

# Check policies
psql -c "SELECT tablename, policyname FROM pg_policies WHERE tablename LIKE 'pms_%';"
```

### API

```bash
# Test /prepare endpoint (after GAP-001 fixed)
curl -X POST http://localhost:8000/v1/actions/prepare \
  -H "Content-Type: application/json" \
  -d '{"q": "create work order", "domain": "work_orders"}'

# Test /execute endpoint
curl -X POST http://localhost:8000/v1/actions/execute \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"action": "create_work_order", "context": {...}, "payload": {...}}'
```

---

## Lens Maturity Levels

| Level | Meaning | Files Required |
|-------|---------|----------------|
| MINIMAL | FINAL.md only | 1 |
| PARTIAL | FINAL.md + some phases | 2-5 |
| COMPLETE | All 9 phase files + FINAL.md | 10 |
| GOLD | Complete + migrations deployed + tests passing | 10+ |

### Current Status

| Lens | Maturity |
|------|----------|
| Certificate | GOLD |
| Work Order | GOLD |
| Equipment | GOLD |
| Fault | MINIMAL |
| Inventory/Part | PARTIAL |
| Crew | PARTIAL |
| Receiving | MINIMAL |
| Shopping List | MINIMAL |
| Document | MINIMAL |

---

## Role Hierarchy

```
AUTHORITY (signed actions)
├── manager        — Delete, decommission, supersede
└── captain        — Decommission, supersede

HOD (write operations)
├── chief_engineer — Full lens access
├── chief_officer  — Most lens access
└── purser         — Certificate management

ENGINEER (department operations)
├── eto            — Equipment, work orders
└── engineer       — Equipment, work orders

CREW (read + notes)
├── deckhand       — View + notes
├── steward        — View + notes
└── chef           — View + notes
```

---

## Signature Payload Schema

```json
{
  "user_id": "uuid",
  "role_at_signing": "captain|manager",
  "signature_type": "decommission_equipment",
  "reason": "Beyond repair",
  "signature_hash": "sha256:base64...",
  "signed_at": "2026-03-02T10:30:00Z"
}
```

**Non-signed actions:** `signature = '{}'::jsonb`

---

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| 403 Forbidden | Role gating | Check `allowed_roles` in registry |
| 404 Not Found | RLS blocking | Check `yacht_id` + `get_user_yacht_id()` |
| 400 Bad Request | Validation failed | Check `required_fields` |
| 500 Internal | Bug | Never acceptable, investigate |

---

## Priority Order (GSD)

1. **Security** — RLS, yacht isolation, role gating
2. **Determinism** — Same input → same output
3. **Testability** — Provable correctness
4. **Stability** — No regressions
5. **Velocity** — Ship fast
6. **Elegance** — Last priority

---

## What You MUST Do

- [ ] Restate task in GSD format before coding
- [ ] Verify `yacht_id` on ALL queries
- [ ] Use canonical helpers (`get_user_yacht_id()`, `is_hod()`)
- [ ] Include `signature = '{}'::jsonb` on non-signed actions
- [ ] Update REQUIREMENTS_TABLE after completion
- [ ] Provide proof of completion

## What You MUST NOT Do

- [ ] Create route-specific backend logic
- [ ] Duplicate mutation handlers
- [ ] Add global UI state
- [ ] Create custom navigation stack
- [ ] Touch >8 files in one PR
- [ ] Skip verification steps

---

*See also: OVERVIEW.md, PHASES-COMPLETE.md, PHASES-REMAINING.md, GAPS.md*
