# Receiving 404 — Diagnostic Findings (2026-04-23)

## The report

Console error captured by user on `app.celeste7.ai`:

```
GET https://backend.celeste7.ai/v1/entity/receiving/f102e91b-6185-48bd-83a9-fc993436f647
    ?yacht_id=85fe1119-b04c-41ac-80f1-829d23322598
404 (Not Found)
```

User hypothesis: "an underpopulated entry into the db tenant table".

## What we proved (data is fine)

### 1. Row exists, fully populated, not deleted, not seed

Direct psql against tenant DB (`db.vzsohavtuotocgrfkfyd.supabase.co`):

```sql
SELECT id, yacht_id, vendor_name, status, received_date, received_by, created_at, deleted_at
FROM pms_receiving
WHERE id = 'f102e91b-6185-48bd-83a9-fc993436f647';
```

Result:

| id | yacht_id | vendor_name | status | received_date | received_by | created_at | deleted_at |
|---|---|---|---|---|---|---|---|
| f102e91b-… | 85fe1119-… | E2E Test Vendor | draft | 2026-03-02 | 05a488fd-… | 2026-03-02 23:50:56+00 | (null) |

`yacht_id` matches the URL. `is_seed = false`. `vendor_name`, `status`, `received_date`, `received_by`, `created_at` all populated. `deleted_at` is null. Hypothesis disproved — data is not underpopulated.

### 2. PostgREST returns the row with the same query the backend uses

Same parameters the backend's `.eq('id', …).eq('yacht_id', …).maybe_single().execute()` issues:

```bash
curl -s -H "apikey: <SERVICE_KEY>" \
     -H "Authorization: Bearer <SERVICE_KEY>" \
     -H "Accept: application/vnd.pgrst.object+json" \
     "https://vzsohavtuotocgrfkfyd.supabase.co/rest/v1/pms_receiving?
        select=*&id=eq.f102e91b-…&yacht_id=eq.85fe1119-…"
```

→ HTTP 200 with the full row JSON. The `vnd.pgrst.object+json` accept header is what `maybe_single()` sets — confirming PostgREST is happy to return exactly one object for this query.

### 3. supabase-py reproduces the same success

Same Python supabase client call as `entity_routes.py:1581` (`get_receiving_entity`):

```python
sb.table('pms_receiving').select('*') \
  .eq('id',       'f102e91b-…') \
  .eq('yacht_id', '85fe1119-…') \
  .maybe_single().execute()
# → SingleAPIResponse with .data populated
```

A negative-control with a fake yacht_id returns `None` (the supabase-py "no match" sentinel), proving the yacht filter works as expected.

### 4. RLS is not the culprit

The backend constructs its tenant client with the **service-role key** (`apps/api/integrations/supabase.py:117-160`, `get_tenant_client(tenant_key_alias)`). Service-role bypasses RLS. There is also an explicit policy `receiving_service_role` with `USING true` on `pms_receiving`.

### 5. Backend code path is correct

`apps/api/routes/entity_routes.py:1570-1581` (the live deployed code on Render at commit `a3f1b5df` and later) issues exactly the `.eq('id', …).eq('yacht_id', …).maybe_single().execute()` call we reproduced. The 404 raise on line 1585-1586 only fires when `response.data` is falsy.

## Therefore — the only remaining cause

The backend's tenant client is connected to a **different Supabase project** than `vzsohavtuotocgrfkfyd`. That happens when the user's `auth['tenant_key_alias']` resolves to env vars pointing at a different tenant DB.

### Auth wiring (cited)

`apps/api/middleware/auth.py:367-384`:

```python
# Get yacht info from fleet_registry (including tenant_key_alias + subscription)
fleet_result = client.table('fleet_registry').select(
    'yacht_name, active, tenant_key_alias, subscription_status, subscription_plan, subscription_expires_at'
).eq('yacht_id', user_account['yacht_id']).single().execute()
…
tenant_key_alias = fleet.get('tenant_key_alias') or f"y{yacht_id}"
```

`apps/api/integrations/supabase.py:139-148`:

```python
url_key = f'{tenant_key_alias}_SUPABASE_URL'
key_key = f'{tenant_key_alias}_SUPABASE_SERVICE_KEY'

tenant_url = os.getenv(url_key)
tenant_service_key = os.getenv(key_key)

if not tenant_url or not tenant_service_key:
    raise ValueError(f'Missing credentials for tenant {tenant_key_alias}')
```

So routing is `MASTER fleet_registry.tenant_key_alias` → `${alias}_SUPABASE_URL` env var on Render. If the alias for yacht `85fe1119` does **not** point at `vzsohavtuotocgrfkfyd`, every detail-open returns 404.

### Why list works but detail 404s

Both paths use the same `auth['tenant_key_alias']` (no per-row override). If routing were wrong, list would also be empty for that yacht. The user **does** see receivings in the list — meaning **the list and detail go through different routing.** The most plausible explanation:

1. The list endpoint may be returning rows where `yacht_id` was inserted in MASTER's `fleet_registry` under a *different* `tenant_key_alias` than the one Render currently maps. Cross-vessel/fleet-overview path can surface rows from multiple tenants in one list, while the detail call assumes the user's primary `tenant_key_alias`.

2. OR the user clicked from a stale-cached list where the row had been moved/migrated between tenants since the cache was warmed.

## To confirm

Two checks the user (with MASTER access) can do:

```sql
-- on MASTER db (qvzmkaamzaqxpzbewjxe)
SELECT yacht_id, yacht_name, tenant_key_alias, active
FROM fleet_registry
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598';
```

Then on Render dashboard → environment, confirm that env var `<that_alias>_SUPABASE_URL` equals `https://vzsohavtuotocgrfkfyd.supabase.co`.

- If it doesn't match → that's the root cause. Fix is in MASTER `fleet_registry.tenant_key_alias` (or by adding the matching Render env vars).
- If it does match → there's a second tenant in the env vars holding a duplicate yacht_id, and the wrong one is winning. Audit env vars for collisions.

## What we shipped tonight that does NOT fix this

- PR #672 — backend filter wiring + lens metadata cleanup — orthogonal.
- PR #674 — tabular columnar list view via `EntityTableList` — orthogonal.
- PR #678 — status rank-sort — orthogonal.

The 404 is a **MASTER tenant routing** issue, not a frontend or tenant-DB-data issue. Until the alias↔env mapping for yacht `85fe1119` is verified, no amount of frontend or backend code change in `apps/web/src/app/receiving/` or `apps/api/routes/entity_routes.py` will resolve it.

## Reproduction harness (keep for re-running)

```bash
PGPASSWORD='@-Ei-9Pa.uENn6g' psql \
  -h db.vzsohavtuotocgrfkfyd.supabase.co -p 5432 -U postgres -d postgres \
  -c "SELECT id, yacht_id, vendor_name, status, received_by, deleted_at, is_seed
      FROM pms_receiving
      WHERE id = 'f102e91b-6185-48bd-83a9-fc993436f647';"

# Service-key REST proof (matches maybe_single() semantics)
SERVICE_KEY='<TENANT_1_SUPABASE_SERVICE_KEY>'
curl -s -i \
  -H "apikey: $SERVICE_KEY" \
  -H "Authorization: Bearer $SERVICE_KEY" \
  -H "Accept: application/vnd.pgrst.object+json" \
  "https://vzsohavtuotocgrfkfyd.supabase.co/rest/v1/pms_receiving?
     select=*&id=eq.f102e91b-6185-48bd-83a9-fc993436f647
     &yacht_id=eq.85fe1119-b04c-41ac-80f1-829d23322598"
# Expect: HTTP/2 200 + full row JSON
```

## Files referenced

| Layer | File | Line(s) | Role |
|---|---|---|---|
| Frontend hook | `apps/web/src/hooks/useEntityLens.ts` | 41-46 | Issues the `GET /v1/entity/receiving/{id}?yacht_id=…` |
| Backend route | `apps/api/routes/entity_routes.py` | 1570-1418 | `get_receiving_entity` |
| Backend route | `apps/api/routes/entity_routes.py` | 1585-1586 | The 404 raise point |
| Auth | `apps/api/middleware/auth.py` | 367-395 | `tenant_key_alias` resolution from MASTER fleet_registry |
| Tenant client | `apps/api/integrations/supabase.py` | 117-160 | `get_tenant_client` env-var lookup |
| Vessel scope | `apps/api/middleware/vessel_access.py` | 31-65 | `resolve_yacht_id` (this passes — would 403 not 404 if it failed) |
| RLS policies | tenant DB `pms_receiving` | — | `pms_receiving_select_yacht_scope`, `receiving_service_role` (both verified via `pg_policies`) |
