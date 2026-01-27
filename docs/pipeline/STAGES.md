# Pipeline Stages (Updated After Certificates)

The original 6-stage process was missing frontend integration. Here's the corrected 7-stage pipeline.

---

## Stage 0: Lens Authoring (Docs)

**Goal:** Write gold lens spec with DB-grounded schema, RLS/storage, signature invariant, micro-actions, migrations, acceptance criteria.

**Output:** `docs/architecture/entity_lenses/<lens>/v2/<lens>_FINAL.md`

---

## Stage 1: DB Truth & Migrations

**Goal:** Author/verify migrations for RLS, storage policies, indexes, constraints.

**Files:**
- `supabase/migrations/YYYYMMDD_NNN_<description>.sql`

**Verify:**
```sql
-- RLS enabled
SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public';

-- Policies exist
SELECT * FROM pg_policies WHERE tablename = '<table>';
```

---

## Stage 2: Action Registry

**Goal:** Register micro-actions with domain, variant, search keywords, storage config.

**File:** `apps/api/action_router/registry.py`

**Pattern:**
```python
"create_<entity>": ActionDefinition(
    action_id="create_<entity>",
    label="Add <Entity>",
    endpoint="/v1/<entities>/create",
    handler_type=HandlerType.INTERNAL,
    method="POST",
    allowed_roles=["chief_engineer", "captain", "manager"],
    required_fields=["yacht_id", ...],
    domain="<entities>",
    variant=ActionVariant.MUTATE,
    search_keywords=["add", "create", "<entity>"],
),
```

---

## Stage 3: Handlers & Router

**Goal:** Implement handlers and wire to dispatcher.

**Files:**
- `apps/api/handlers/<entity>_handlers.py` - Business logic
- `apps/api/action_router/dispatchers/internal_dispatcher.py` - Routing
- `apps/api/routes/p0_actions_routes.py` - Endpoints (if new ones needed)

**Note:** Add endpoints to `p0_actions_routes.py`, NOT `action_router/router.py`.

---

## Stage 4: Backend Tests (Docker)

**Goal:** Fast-loop validation with real users.

**File:** `tests/docker/run_rls_tests.py`

**Required tests:**
- Role gating: HOD can create, CREW cannot
- CRUD: Create, read, update work correctly
- Isolation: Cross-yacht access blocked
- Edge cases: Invalid inputs return 4xx, not 5xx
- Audit: Signature invariant maintained

**Run:**
```bash
cd apps/api && python3 -m pytest tests/docker/run_rls_tests.py -v
```

---

## Stage 5: Frontend Integration (NEW - Was Missing!)

**Goal:** Wire backend suggestions to UI.

**Files to modify:**
| File | Change |
|------|--------|
| `apps/web/src/hooks/useCelesteSearch.ts` | Add intent detection for new domain |
| `apps/web/src/lib/actionClient.ts` | Types (if new response fields) |

**Existing reusable components:**
- `SuggestedActions.tsx` - Renders action buttons (generic)
- `ActionModal.tsx` - Dynamic form + execution (generic)

**Pattern for new domain:**
```typescript
// In useCelesteSearch.ts
const <ENTITY>_ACTION_KEYWORDS = ['add <entity>', 'create <entity>', ...];

function detect<Entity>ActionIntent(query: string): boolean {
  const q = query.toLowerCase();
  return <ENTITY>_ACTION_KEYWORDS.some(k => q.includes(k));
}

// In search effect
if (detect<Entity>ActionIntent(query)) {
  fetchActionSuggestions(query, '<entities>');
}
```

**Verify:**
```bash
cd apps/web && npm run build && npx tsc --noEmit
```

---

## Stage 6: Staging Acceptance (CI)

**Goal:** Validate with real JWTs in staging environment.

**Files:**
- `tests/ci/staging_<lens>_acceptance.py`
- `.github/workflows/staging-<lens>-acceptance.yml`

**Mark as required check on main branch.**

---

## Stage 7: Release

**Goal:** Tag release and update changelog.

**Commands:**
```bash
git add <files>
git commit -m "feat(<lens>): <description>"
git tag -a <lens>-gold -m "<description>"
```

**Files:**
- `CHANGELOG.md` - Add entry

---

## Stage Summary

| Stage | Focus | Verify |
|-------|-------|--------|
| 0 | Docs | Lens spec complete |
| 1 | DB | Migrations apply cleanly |
| 2 | Registry | Actions defined with metadata |
| 3 | Handlers | Endpoints respond correctly |
| 4 | Backend tests | 100% pass |
| 5 | Frontend | Build passes, intent detection works |
| 6 | Staging CI | Real JWT validation passes |
| 7 | Release | Tagged and documented |
