# Start Here — Next Lens (What We Wish We Had On Day 1)

This is the compact, practical briefing you need to take any new lens from zero → gold using the Certificates template without guessing.

---

## 60‑Second Map
- Source of truth: Backend. Registry defines actions, roles, variants, and storage semantics.
- RLS: Deny‑by‑default. `public.get_user_yacht_id()` drives row access; helpers `is_hod()`/`is_manager()` gate writes.
- Frontend: Renders backend‑provided actions (no UI authority). Buttons come from `GET /v1/actions/list`.
- CI gates: Docker proves RLS/roles/error mapping; Staging CI proves 400/404 vs 200 with real JWTs. Both must be green.

---

## Top 10 Things To Know (before you touch code)
1) Roles are exact strings: `crew`, `chief_engineer`, `captain`, `manager`.
2) Endpoint lives in `apps/api/routes/p0_actions_routes.py` (not `action_router/router.py`).
3) Search + storage semantics belong in `apps/api/action_router/registry.py`.
4) File storage must be under `{yacht_id}/...`; never accept arbitrary paths.
5) Client error mapping: invalid input → 400/404; 500 is a hard failure (tests fail on it).
6) Audit invariant: `pms_audit_log.signature` is `{}` (non‑signed) or JSON (signed). Never NULL.
7) Use stable CI users (CREATE_USERS=false). Do not pollute DB with timestamped emails.
8) Render vs CI env: Render uses `DEFAULT_YACHT_CODE` + `y<ALIAS>_SUPABASE_*`; CI uses `TENANT_*`.
9) Copy intent, not literals: replace “certificate” actions with your domain’s actions but keep the same guarantees and test categories.
10) Frontend integration is required: Suggestions → Buttons → Modal → Execute → Refresh.

---

## Environment Matrix
- MASTER (auth/routing): issue JWTs; map users in `user_accounts` (user_id, yacht_id, role).
- TENANT (PMS data): profiles/roles for RLS joins; all `pms_*` tables and `doc_metadata`.
- Staging service (Render): set `FEATURE_<DOMAIN>=true`, `DEFAULT_YACHT_CODE`, and tenant env vars.

---

## File Hotspots You Will Edit
- Registry: `apps/api/action_router/registry.py`
  - Add actions with `domain`, `variant`, `search_keywords`, `required_fields`.
  - Add `ACTION_STORAGE_CONFIG` for file actions.
- Handlers: `apps/api/handlers/<entity>_handlers.py`
- Dispatcher: `apps/api/action_router/dispatchers/internal_dispatcher.py`
- Endpoint (already present): `GET /v1/actions/list` in `apps/api/routes/p0_actions_routes.py`.
- Frontend: `apps/web/src/hooks/useCelesteSearch.ts`, `apps/web/src/components/SuggestedActions.tsx`, `apps/web/src/components/actions/ActionModal.tsx`.

---

## Action Registry Recipe (minimal)
```python
"create_<entity>": ActionDefinition(
  action_id="create_<entity>",
  label="Add <Entity>",
  endpoint="/v1/<entities>/create",
  handler_type=HandlerType.INTERNAL,
  method="POST",
  allowed_roles=["chief_engineer","captain","manager"],
  required_fields=["yacht_id","field1","field2"],
  domain="<entities>",
  variant=ActionVariant.MUTATE,
  search_keywords=["add","create","<entity>"],
)

ACTION_STORAGE_CONFIG["create_<entity>"] = {
  "bucket": "documents",
  "path_template": "{yacht_id}/<entities>/{entity_id}/{filename}",
  "writable_prefixes": ["{yacht_id}/<entities>/"],
  "confirmation_required": True,
}
```

---

## Testing Philosophy (copy this intent)
- Role & CRUD: HOD can create/update; CREW cannot; SIGNED actions only for captain/manager.
- Isolation & Storage: Cross‑yacht rejects; storage prefixes enforced.
- Edge cases: Invalid input is 400/404; duplicate = 409; terminal state respected.
- Audit: `{}` for non‑signed; JSON for signed; never NULL.

Where:
- Docker suite: `tests/docker/run_rls_tests.py` (fast, hermetic)
- Staging CI: `tests/ci/staging_<lens>_acceptance.py` (real JWTs) → required on main

---

## Frontend Integration (cookie cutter)
1) Detect intent in `useCelesteSearch.ts` for your domain.
2) Call `getActionSuggestions(query, '<entities>')`.
3) Render `<SuggestedActions actions={...} />`.
4) Open `<ActionModal>` to collect `required_fields` and confirm `storage_options.path_preview`.
5) Execute via `executeAction()`; then refetch results.

---

## Quick Verifications
```bash
# Suggest actions (HOD): should list create_* for your domain
curl -H "Authorization: Bearer $HOD_JWT" \
  "$BASE_URL/v1/actions/list?q=add+<entity>&domain=<entities>"

# Execute happy path
curl -X POST "$BASE_URL/v1/actions/execute" \
  -H "Authorization: Bearer $HOD_JWT" -H "Content-Type: application/json" \
  -d '{"action":"create_<entity>","context":{"yacht_id":"'$YACHT_ID'"},"payload":{"field":"value"}}'
```

---

## Anti‑Patterns (don’t do these)
- Invent actions or fields in the UI.
- Accept arbitrary storage paths or cross‑yacht prefixes.
- Swallow 500s in tests (500 means “stop and fix”).
- Use conceptual role names (“HOD”) instead of actual strings (`chief_engineer`).

---

## If It Breaks
See TROUBLESHOOTING.md for quick fixes (staging redeploy, env drift, users pollution, domain filter).

