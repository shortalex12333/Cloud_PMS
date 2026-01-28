# Next Agent: How to Use This Template

This template was battle-tested on the Certificates lens. Read LESSONS_LEARNED.md first to avoid known pitfalls.

---

## Quick Start (Read Order)

1. **LESSONS_LEARNED.md** - What went wrong, actual file locations
2. **FILE_MAP.md** - Where things actually are (verified)
3. **STAGES.md** - The 7-stage process (includes frontend integration)
4. **ACCEPTANCE_MATRIX.md** - What tests must pass
5. **ACTION_SUGGESTIONS_CONTRACT.md** - Contract for GET /v1/actions/list
6. **TEMPLATE_CHECKLIST.md** - Zero→Gold checklist
7. **RUNBOOK.md** - Commands to run

---

## Implementing the Next Lens

### Step 1: Backend Action Registry

Edit `apps/api/action_router/registry.py`:

```python
# Add to ACTION_REGISTRY
"create_<entity>": ActionDefinition(
    action_id="create_<entity>",
    label="Add <Entity>",
    endpoint="/v1/<entities>/create",
    handler_type=HandlerType.INTERNAL,
    method="POST",
    allowed_roles=["chief_engineer", "captain", "manager"],  # Use EXACT role strings
    required_fields=["yacht_id", "field1", "field2"],
    domain="<entities>",  # For search filtering
    variant=ActionVariant.MUTATE,  # READ, MUTATE, or SIGNED
    search_keywords=["add", "create", "new", "<entity>"],
),

# If action involves file uploads, add to ACTION_STORAGE_CONFIG
ACTION_STORAGE_CONFIG["create_<entity>"] = {
    "bucket": "documents",
    "path_template": "{yacht_id}/<entities>/{entity_id}/{filename}",
    "writable_prefixes": ["{yacht_id}/<entities>/"],
    "confirmation_required": True,
}
```

### Step 2: Backend Handlers

Create `apps/api/handlers/<entity>_handlers.py`:

```python
async def handle_create_<entity>(context: dict, payload: dict, user_context: dict):
    # Validate inputs
    # Insert via Supabase
    # Return {"status": "success", "result": {...}}
```

Register in dispatcher (`apps/api/action_router/dispatchers/internal_dispatcher.py`).

### Step 3: Backend Tests

Add to `tests/docker/run_rls_tests.py`:

```python
def test_<entity>_hod_can_create(jwt_hod: str) -> bool:
    # HOD should be able to create

def test_<entity>_crew_cannot_create(jwt_crew: str) -> bool:
    # CREW should be blocked
```

### Step 4: Frontend Integration

**Option A: Reuse existing components** (recommended)

The `SuggestedActions` and `ActionModal` components are generic. Just:
1. Extend domain detection in `useCelesteSearch.ts`:

```typescript
const ENTITY_ACTION_KEYWORDS = ['add <entity>', 'create <entity>', ...];

function detectEntityActionIntent(query: string): boolean {
  const q = query.toLowerCase();
  return ENTITY_ACTION_KEYWORDS.some(k => q.includes(k));
}
```

2. Fetch suggestions for that domain:

```typescript
if (detectEntityActionIntent(query)) {
  const suggestions = await getActionSuggestions(query, '<entities>');
  setActionSuggestions(suggestions.actions);
}
```

**Option B: Custom UI** (if needed)

Create entity-specific components following the pattern in:
- `apps/web/src/components/SuggestedActions.tsx`
- `apps/web/src/components/actions/ActionModal.tsx`

### Step 5: Verify

```bash
# Backend tests
cd apps/api && python3 -m pytest tests/docker/run_rls_tests.py -v

# Frontend build
cd apps/web && npm run build

# Type check
npx tsc --noEmit
```

---

## Non-Negotiables (Verified)

| Rule | How to Verify |
|------|---------------|
| Backend authority | Frontend calls `/v1/actions/list`, never invents actions |
| RLS everywhere | All Supabase queries use `get_user_yacht_id()` |
| Role gating | `allowed_roles` matches what RLS policies enforce |
| Signature invariant | `pms_audit_log.signature` is `{}` or JSON, never NULL |
| Storage isolation | Paths start with `{yacht_id}/` |

---

## Common Mistakes to Avoid

1. **Wrong endpoint location**: Use `apps/api/routes/p0_actions_routes.py`, NOT `action_router/router.py`
2. **Wrong role names**: Use `chief_engineer`, not "HOD"
3. **Missing frontend build check**: Run `npm run build` before declaring done
4. **Over-engineering**: Don't create separate files unless code exceeds 200 lines
5. **Domain filter bug**: Test with unknown domain → should return empty list

---

## Files You'll Modify

### Backend (always)
- `apps/api/action_router/registry.py` - Add action definitions
- `apps/api/routes/p0_actions_routes.py` - Add endpoints (if needed)
- `apps/api/handlers/<entity>_handlers.py` - Add/create handlers
- `tests/docker/run_rls_tests.py` - Add tests

### Frontend (usually)
- `apps/web/src/hooks/useCelesteSearch.ts` - Add intent detection
- `apps/web/src/lib/actionClient.ts` - Types (if new fields)

### Frontend (rarely)
- `apps/web/src/components/SuggestedActions.tsx` - Only if UI changes
- `apps/web/src/components/actions/ActionModal.tsx` - Only if form logic changes

---

## Verification Checklist

Before marking lens complete:

- [ ] Backend tests pass (all 18+ tests)
- [ ] Frontend builds without errors
- [ ] TypeScript compiles (`npx tsc --noEmit`)
- [ ] Role gating works (HOD sees actions, CREW doesn't)
- [ ] Storage options included for file actions
- [ ] Edge cases handled (empty query, unknown domain, unknown role)
- [ ] CHANGELOG updated
- [ ] Git tagged (e.g., `<entity>-lens-gold`)

---

## Quick cURL (Smoke)

```bash
# List actions (HOD): expect create_* actions when domain matches
curl -H "Authorization: Bearer $HOD_JWT" \
  "$API_BASE/v1/actions/list?q=add+<entity>&domain=<entities>"

# Execute an action
curl -X POST -H "Authorization: Bearer $HOD_JWT" -H "Content-Type: application/json" \
  "$API_BASE/v1/actions/execute" \
  -d '{
    "action": "create_<entity>",
    "context": {"yacht_id": "'$YACHT_ID'"},
    "payload": {"field1": "value"}
  }'
```
