# Template Checklist (Zero → Gold)

Practical, file‑linked steps to take a new lens from spec to production.

---

## 1) Environment & Secrets
- Render (staging):
  - `DEFAULT_YACHT_CODE`, `y<ALIAS>_SUPABASE_URL`, `y<ALIAS>_SUPABASE_SERVICE_KEY`
  - `MASTER_SUPABASE_URL`, `MASTER_SUPABASE_SERVICE_KEY`, `MASTER_SUPABASE_JWT_SECRET`
  - `FEATURE_<DOMAIN>=true`
- GitHub repo secrets:
  - `BASE_URL`, `MASTER_SUPABASE_URL`, `MASTER_SUPABASE_ANON_KEY`, `MASTER_SUPABASE_SERVICE_ROLE_KEY`
  - `TENANT_SUPABASE_URL`, `TENANT_SUPABASE_SERVICE_ROLE_KEY`, `TEST_USER_YACHT_ID`
  - Stable CI users: `STAGING_CREW_EMAIL`, `STAGING_HOD_EMAIL`, `STAGING_CAPTAIN_EMAIL`, `STAGING_USER_PASSWORD`

## 2) DB Migrations
- Add RLS/storage/indexes under `supabase/migrations/*`
- Verify with SQL:
```sql
SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname='public';
SELECT * FROM pg_policies WHERE tablename='<table>';
```

## 3) Backend Code
- Registry: `apps/api/action_router/registry.py`
  - Add actions with `domain`, `variant`, `search_keywords`, `required_fields`
  - If file actions: extend `ACTION_STORAGE_CONFIG`
- Handlers: `apps/api/handlers/<entity>_handlers.py`
- Dispatcher: `apps/api/action_router/dispatchers/internal_dispatcher.py`
- Endpoint (if needed): `apps/api/routes/p0_actions_routes.py` (`GET /v1/actions/list` already exists)

## 4) Backend Tests
- Add tests to `tests/docker/run_rls_tests.py`
- Run:
```bash
./scripts/test-local-docker.sh
# or
docker-compose -f docker-compose.test.yml up --build
```

## 5) Frontend Integration
- Fetch suggestions in `apps/web/src/hooks/useCelesteSearch.ts` for the new domain
- Render buttons: `apps/web/src/components/SuggestedActions.tsx`
- Execute via modal: `apps/web/src/components/actions/ActionModal.tsx`
- Build check: `cd apps/web && npm run build && npx tsc --noEmit`

## 6) Staging Acceptance (CI)
- Add `tests/ci/staging_<lens>_acceptance.py`
- Add `.github/workflows/staging-<lens>-acceptance.yml`
- Use stable users: set `CREATE_USERS='false'`
- Mark workflow required on `main`

## 7) Release
- Update `CHANGELOG.md`
- Tag: `git tag -a <lens>-gold -m "<desc>"`

---

## Quick CURLs
```bash
# Suggest actions
curl -H "Authorization: Bearer $HOD_JWT" \
  "$BASE_URL/v1/actions/list?q=add+<entity>&domain=<entities>"

# Execute action
curl -X POST -H "Authorization: Bearer $HOD_JWT" -H "Content-Type: application/json" \
  "$BASE_URL/v1/actions/execute" \
  -d '{"action":"create_<entity>","context":{"yacht_id":"'$YACHT_ID'"},"payload":{"field":"value"}}'
```

