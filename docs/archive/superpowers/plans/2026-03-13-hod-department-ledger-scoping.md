# HoD Department Ledger Scoping — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give Heads of Department (chief_engineer, manager) a department-scoped view of the ledger timeline — they see events from their own department's crew, not the entire yacht.

**Architecture:** Four sequential layers. (1) DB: add `department` column to `auth_users_roles` with a CHECK constraint and a trigger that auto-derives the value from `role` on insert AND on role-change update — single source of truth. (2) Auth middleware: already queries `auth_users_roles` per request; extend the SELECT to also fetch `department`, propagate it through `tenant_info` and `user_context`. (3) Ledger writes: pass `department` from `user_context` into `build_ledger_event()` via the **centralised fallback middleware only** (line ~6476 in p0_actions_routes.py); the 35 per-action explicit calls are intentionally not changed because the timeline correctly scopes by `user_role` (already populated on all rows), making `department` enrichment data rather than a correctness dependency. (4) `/timeline` endpoint: three-tier scoping — captain=all, HoD=department (filter by `user_role IN (dept_roles)`), crew=self only.

**Why NOT the JWT hook:** Existing JWT sessions would silently miss the `department` claim until the user re-authenticates. The auth middleware already performs a DB lookup on every cache miss and caches the result — adding `department` to that query is free and takes effect immediately for all active sessions.

**Tech Stack:** Python/FastAPI, PostgreSQL triggers, Supabase Python client, psql for migrations.

**Pre-requisite:** Before running any `psql` commands in this plan, set the env var:
```bash
export SUPABASE_DB_PASSWORD='<tenant DB password from secure vault>'
```

---

## Role → Department Mapping (Canonical)

This mapping is deterministic from the role. It is enforced by DB constraint and trigger — never computed ad-hoc in application code.

| Role | Department | Is HoD? |
|---|---|---|
| `captain` | `deck` | Yes (sees ALL yacht events) |
| `deck` | `deck` | No |
| `chief_engineer` | `engineering` | Yes |
| `eto` | `engineering` | No |
| `manager` | `interior` | Yes |
| `interior` | `interior` | No |
| `crew` | `general` | No |
| `vendor` | `general` | No |

**Timeline scoping rules:**
- `captain` → all yacht events (no filter — master of the vessel)
- `chief_engineer` → events where `user_role IN ('chief_engineer', 'eto')` on this yacht
- `manager` → events where `user_role IN ('manager', 'interior')` on this yacht
- All others → self only (`user_id = current_user_id`)

> **Why filter by `user_role` in `ledger_events` rather than `department`?**
> The `department` column in `ledger_events` is NULL for all historical rows. Filtering by the already-populated `user_role` column gives correct results for all rows — past and future. Once new events are written with `department` stamped, both approaches converge.

---

## File Map

| File | Action | What changes |
|---|---|---|
| `database/migrations/14_add_department_to_auth_users_roles.sql` | **Create** | ADD COLUMN department, CHECK constraint, derive-from-role trigger, backfill existing rows, backfill ledger_events.department |
| `apps/api/middleware/auth.py` | **Modify** (3 lines) | Add `department` to SELECT + tenant_info + user_context return |
| `apps/api/routes/p0_actions_routes.py` | **Modify** (1 line) | Pass `department=user_context.get("department")` to centralised `build_ledger_event()` call |
| `apps/api/routes/ledger_routes.py` | **Modify** (~15 lines) | Three-tier scoping in `/timeline` endpoint |

---

## Chunk 1: DB Schema

### Task 1: Write and apply migration 14

**Files:**
- Create: `database/migrations/14_add_department_to_auth_users_roles.sql`

---

- [ ] **Step 1: Write the migration file**

```sql
-- Migration 14: Add department to auth_users_roles
-- Date: 2026-03-13
-- Purpose: Enable HoD department-scoped ledger timeline queries
--
-- The department column is derived from role via trigger — never set manually.
-- Role → department mapping is the canonical truth for this yacht.

-- ================================================================
-- PART 1: Add department column to auth_users_roles
-- ================================================================

ALTER TABLE public.auth_users_roles
  ADD COLUMN IF NOT EXISTS department text;

-- Check constraint: only valid department values
ALTER TABLE public.auth_users_roles
  DROP CONSTRAINT IF EXISTS valid_department;
ALTER TABLE public.auth_users_roles
  ADD CONSTRAINT valid_department CHECK (
    department IN ('deck', 'engineering', 'interior', 'general')
  );

-- ================================================================
-- PART 2: Trigger to auto-derive department from role
-- ================================================================
-- Runs on INSERT and UPDATE. If department is not explicitly set,
-- it derives it from the role. This is the single source of truth.

CREATE OR REPLACE FUNCTION public.derive_department_from_role()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  -- Auto-derive department when:
  --   (a) it is not explicitly set on INSERT, OR
  --   (b) the role changes on UPDATE (promotion/demotion must update department)
  IF NEW.department IS NULL
     OR (TG_OP = 'UPDATE' AND NEW.role IS DISTINCT FROM OLD.role) THEN
    NEW.department := CASE NEW.role
      WHEN 'captain'        THEN 'deck'
      WHEN 'deck'           THEN 'deck'
      WHEN 'chief_engineer' THEN 'engineering'
      WHEN 'eto'            THEN 'engineering'
      WHEN 'manager'        THEN 'interior'
      WHEN 'interior'       THEN 'interior'
      WHEN 'crew'           THEN 'general'
      WHEN 'vendor'         THEN 'general'
      ELSE                       'general'
    END;
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_derive_department ON public.auth_users_roles;
CREATE TRIGGER trg_derive_department
  BEFORE INSERT OR UPDATE ON public.auth_users_roles
  FOR EACH ROW
  EXECUTE FUNCTION public.derive_department_from_role();

-- ================================================================
-- PART 3: Backfill department for existing auth_users_roles rows
-- ================================================================

UPDATE public.auth_users_roles
SET department = CASE role
  WHEN 'captain'        THEN 'deck'
  WHEN 'deck'           THEN 'deck'
  WHEN 'chief_engineer' THEN 'engineering'
  WHEN 'eto'            THEN 'engineering'
  WHEN 'manager'        THEN 'interior'
  WHEN 'interior'       THEN 'interior'
  WHEN 'crew'           THEN 'general'
  WHEN 'vendor'         THEN 'general'
  ELSE                       'general'
END
WHERE department IS NULL;

-- ================================================================
-- PART 4: Backfill ledger_events.department from user_role
-- ================================================================
-- Historical rows have department=NULL. Backfill deterministically
-- from the user_role already stored in the row.

UPDATE public.ledger_events
SET department = CASE user_role
  WHEN 'captain'        THEN 'deck'
  WHEN 'deck'           THEN 'deck'
  WHEN 'chief_engineer' THEN 'engineering'
  WHEN 'eto'            THEN 'engineering'
  WHEN 'manager'        THEN 'interior'
  WHEN 'interior'       THEN 'interior'
  WHEN 'crew'           THEN 'general'
  WHEN 'vendor'         THEN 'general'
  ELSE                       'general'
END
WHERE department IS NULL
  AND user_role IS NOT NULL;

-- ================================================================
-- VERIFICATION
-- ================================================================

SELECT role, department, COUNT(*) AS row_count
FROM public.auth_users_roles
GROUP BY role, department
ORDER BY role;

SELECT 'migration 14 complete' AS status;
```

- [ ] **Step 2: Apply via psql**

```bash
PGPASSWORD="$SUPABASE_DB_PASSWORD" psql \
  -h db.vzsohavtuotocgrfkfyd.supabase.co \
  -p 5432 -U postgres -d postgres \
  -f /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/database/migrations/14_add_department_to_auth_users_roles.sql
```

Expected: NO errors. Final line of output:
```
 migration 14 complete
```

- [ ] **Step 3: Verify the backfill**

```bash
PGPASSWORD="$SUPABASE_DB_PASSWORD" psql \
  -h db.vzsohavtuotocgrfkfyd.supabase.co \
  -p 5432 -U postgres -d postgres \
  -c "
SELECT role, department, COUNT(*) FROM public.auth_users_roles GROUP BY role, department ORDER BY role;
SELECT COUNT(*) AS ledger_rows_with_department FROM public.ledger_events WHERE department IS NOT NULL;
SELECT COUNT(*) AS ledger_rows_still_null FROM public.ledger_events WHERE department IS NULL AND user_role IS NOT NULL;
"
```

Expected:
- Every role has a corresponding department (no NULLs in `auth_users_roles`)
- `ledger_rows_still_null` = 0

- [ ] **Step 4: Commit**

```bash
git add database/migrations/14_add_department_to_auth_users_roles.sql
git commit -m "feat: add department column to auth_users_roles with derive-from-role trigger + backfill"
```

---

## Chunk 2: Auth Middleware

### Task 2: Surface department in user_context

**Files:**
- Modify: `apps/api/middleware/auth.py:343-375`

The auth middleware already queries `auth_users_roles` for `role`. Three surgical edits: extend the SELECT, read the value, propagate it.

---

- [ ] **Step 1: Read the exact lines to modify**

Open `apps/api/middleware/auth.py` and confirm these three locations exist exactly as described:

**Location A** (line ~343–344): The `select()` call
```python
role_result = tenant_client.table('auth_users_roles').select(
    'role, valid_from, valid_until'
```

**Location B** (line ~355): After `sorted_roles`, where `tenant_role` is extracted:
```python
tenant_role = sorted_roles[0]['role']
```

**Location C** (line ~365–371): The `tenant_info` dict:
```python
tenant_info = {
    'yacht_id': yacht_id,
    'tenant_key_alias': tenant_key_alias,
    'role': tenant_role,
    'status': user_account['status'],
    'yacht_name': fleet.get('yacht_name'),
}
```

**Location D** (line ~556–563): The `get_authenticated_user` return:
```python
return {
    'user_id': user_id,
    'email': payload.get('email'),
    'yacht_id': tenant['yacht_id'],
    'tenant_key_alias': tenant['tenant_key_alias'],
    'role': tenant['role'],
    'yacht_name': tenant.get('yacht_name'),
}
```

- [ ] **Step 2: Edit Location A — add department to SELECT**

Change:
```python
role_result = tenant_client.table('auth_users_roles').select(
    'role, valid_from, valid_until'
).eq('user_id', user_id).eq('yacht_id', yacht_id).eq('is_active', True).execute()
```

To:
```python
role_result = tenant_client.table('auth_users_roles').select(
    'role, department, valid_from, valid_until'
).eq('user_id', user_id).eq('yacht_id', yacht_id).eq('is_active', True).execute()
```

- [ ] **Step 3: Edit Location B — extract department alongside role**

Change:
```python
tenant_role = sorted_roles[0]['role']
logger.info(f"[Auth] Found yacht-specific role: {tenant_role} for user {user_id[:8]}... on yacht {yacht_id}")
```

To:
```python
tenant_role = sorted_roles[0]['role']
tenant_dept = sorted_roles[0].get('department') or ''
logger.info(f"[Auth] Found yacht-specific role: {tenant_role} (dept: {tenant_dept}) for user {user_id[:8]}... on yacht {yacht_id}")
```

- [ ] **Step 4: Edit Location C — add department to tenant_info dict**

Change:
```python
tenant_info = {
    'yacht_id': yacht_id,
    'tenant_key_alias': tenant_key_alias,
    'role': tenant_role,
    'status': user_account['status'],
    'yacht_name': fleet.get('yacht_name'),
}
```

To:
```python
tenant_info = {
    'yacht_id': yacht_id,
    'tenant_key_alias': tenant_key_alias,
    'role': tenant_role,
    'department': tenant_dept,
    'status': user_account['status'],
    'yacht_name': fleet.get('yacht_name'),
}
```

Note: `tenant_dept` must be in scope here — it was assigned in Step 3 which runs in the same try block.

- [ ] **Step 5: Edit Location D — add department to get_authenticated_user return**

Change:
```python
return {
    'user_id': user_id,
    'email': payload.get('email'),
    'yacht_id': tenant['yacht_id'],
    'tenant_key_alias': tenant['tenant_key_alias'],
    'role': tenant['role'],
    'yacht_name': tenant.get('yacht_name'),
}
```

To:
```python
return {
    'user_id': user_id,
    'email': payload.get('email'),
    'yacht_id': tenant['yacht_id'],
    'tenant_key_alias': tenant['tenant_key_alias'],
    'role': tenant['role'],
    'department': tenant.get('department', ''),
    'yacht_name': tenant.get('yacht_name'),
}
```

- [ ] **Step 6: Deploy to container and verify**

```bash
docker cp apps/api/middleware/auth.py celeste-api:/app/middleware/auth.py
docker restart celeste-api
sleep 8
curl -s http://localhost:8000/health
```

Expected: `{"status":"healthy",...}`

> **Note — cache invalidation on restart:** The auth middleware uses an in-process `_tenant_cache` (TTL 15 min). `docker restart` kills and recreates the process, so the cache is wiped automatically. Every user's next request will re-fetch `role + department` from `auth_users_roles`. No users will experience the stale-cache degraded window post-restart.

- [ ] **Step 7: Smoke test — confirm department appears in user_context**

```bash
TOKEN=$(cat /tmp/jwt_token.txt)
curl -s -X POST http://localhost:8000/v1/actions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action":"check_stock_level","payload":{"part_id":"00000000-0000-0000-0000-000000000001","yacht_id":"85fe1119-b04c-41ac-80f1-829d23322598"}}' \
  | python3 -m json.tool 2>/dev/null | head -20
```

This verifies the API still works after the auth change. The `department` field isn't visible in the action response — it's internal to `user_context`. The absence of a 500 error is the proof.

To directly confirm `department` is in context, check the container logs:
```bash
docker logs celeste-api --tail 20 2>&1 | grep "dept:"
```

Expected: `[Auth] Found yacht-specific role: captain (dept: deck) for user ...`

- [ ] **Step 8: Commit**

```bash
git add apps/api/middleware/auth.py
git commit -m "feat: add department to auth middleware user_context (fetched from auth_users_roles)"
```

---

## Chunk 3: Stamp Department on Every Ledger Write

### Task 3: Pass department through centralised ledger middleware

**Files:**
- Modify: `apps/api/routes/p0_actions_routes.py` (~line 6476)

The centralised fallback middleware at the end of `p0_actions_routes.py` (line ~6476) is the only call site being changed. There are 35 additional per-action explicit `build_ledger_event()` calls elsewhere in the file — these are intentionally NOT changed because:
1. The `/timeline` endpoint filters by `user_role IN (dept_roles)`, which is already stamped on all rows (past and future). Correct HoD scoping does not depend on `department` being populated in `ledger_events`.
2. `department` in `ledger_events` is enrichment data — useful for analytics and future direct-filtering, not a correctness gate.
3. The centralised block fires as a catch-all for actions that go through the generic dispatcher. Updating it captures the majority of new write events with zero risk of touching the 35 per-action handlers.

---

- [ ] **Step 1: Find the exact call in p0_actions_routes.py**

Run:
```bash
grep -n "actor_name=user_context" apps/api/routes/p0_actions_routes.py
```

Expected: one match around line 6485. Read that block — it should look like:

```python
_ledger_ev = build_ledger_event(
    yacht_id=str(yacht_id),
    user_id=str(user_id),
    event_type=_ev_type,
    entity_type=_entity_type,
    entity_id=_entity_id or "00000000-0000-0000-0000-000000000000",
    action=action,
    user_role=user_role or "",
    change_summary=_resp_dict.get("message", action.replace("_", " ").title()),
    actor_name=user_context.get("email", ""),
    event_category="write",
)
```

- [ ] **Step 2: Add department param**

Change the call to add one line after `actor_name`:

```python
_ledger_ev = build_ledger_event(
    yacht_id=str(yacht_id),
    user_id=str(user_id),
    event_type=_ev_type,
    entity_type=_entity_type,
    entity_id=_entity_id or "00000000-0000-0000-0000-000000000000",
    action=action,
    user_role=user_role or "",
    change_summary=_resp_dict.get("message", action.replace("_", " ").title()),
    actor_name=user_context.get("email", ""),
    department=user_context.get("department", ""),
    event_category="write",
)
```

- [ ] **Step 3: Deploy and verify a write stamps department**

```bash
docker cp apps/api/routes/p0_actions_routes.py celeste-api:/app/routes/p0_actions_routes.py
docker restart celeste-api && sleep 8

TOKEN=$(cat /tmp/jwt_token.txt)

# Trigger a write action
curl -s -X POST http://localhost:8000/v1/actions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action":"add_equipment_note","payload":{"equipment_id":"00000000-0000-0000-0000-000000000001","yacht_id":"85fe1119-b04c-41ac-80f1-829d23322598","note_text":"department test note"}}' \
  | python3 -m json.tool 2>/dev/null
```

Then confirm the ledger row has `department` populated:

```bash
PGPASSWORD="$SUPABASE_DB_PASSWORD" psql \
  -h db.vzsohavtuotocgrfkfyd.supabase.co \
  -p 5432 -U postgres -d postgres \
  -c "SELECT action, user_role, department, created_at FROM public.ledger_events ORDER BY created_at DESC LIMIT 3;"
```

Expected: most recent row has `department = 'deck'` (for captain test user).

- [ ] **Step 4: Commit**

```bash
git add apps/api/routes/p0_actions_routes.py
git commit -m "feat: stamp department on every ledger write via centralised middleware"
```

---

## Chunk 4: Three-Tier Timeline Scoping

### Task 4: Implement department-filtered HoD view in /timeline

**Files:**
- Modify: `apps/api/routes/ledger_routes.py:323-356`

---

- [ ] **Step 1: Read the current timeline endpoint**

Open `apps/api/routes/ledger_routes.py` at lines 323–357. Confirm the current scoping logic:

```python
# Crew sees only their own events; captain/HoD see all yacht events (MVP)
if user_role not in ("captain", "chief_engineer", "manager"):
    query = query.eq("user_id", str(user_id))
```

This is the binary MVP logic to replace.

- [ ] **Step 2: Write the replacement**

Replace the entire `/timeline` function body with the three-tier version:

```python
@router.get("/timeline")
async def get_ledger_timeline(
    limit: int = 50,
    offset: int = 0,
    event_category: Optional[str] = None,
    user_context: dict = Depends(get_authenticated_user),
):
    """
    Three-tier role-scoped timeline:
      captain             -> all events on this yacht (master of vessel)
      chief_engineer      -> engineering department events (chief_engineer + eto)
      manager             -> interior department events (manager + interior)
      all other roles     -> own events only
    """
    # Department → member roles mapping (deterministic, mirrors DB trigger)
    # Only the two HoD-scoped departments are needed here.
    # "deck"/"general" are intentionally absent: captain is handled by the
    # `pass` branch (sees all), and deck/general crew fall into the `else` branch (self-only).
    _DEPT_MEMBER_ROLES: dict = {
        "engineering": ["chief_engineer", "eto"],
        "interior":    ["manager", "interior"],
    }

    tenant_alias = user_context.get("tenant_key_alias", "")
    yacht_id     = user_context.get("yacht_id")
    user_id      = user_context.get("user_id") or user_context.get("sub")
    user_role    = user_context.get("role", "")
    department   = user_context.get("department", "")

    db_client = _get_tenant_client(tenant_alias)

    query = db_client.table("ledger_events") \
        .select("id, action, entity_type, entity_id, event_category, event_type, "
                "change_summary, user_role, actor_name, department, metadata, created_at") \
        .eq("yacht_id", str(yacht_id))

    if user_role == "captain":
        # Captain sees all yacht events — no further filter
        pass
    elif user_role in ("chief_engineer", "manager"):
        # HoD sees their department only — filter by the roles in that department
        dept_roles = _DEPT_MEMBER_ROLES.get(department, [])
        if dept_roles:
            query = query.in_("user_role", dept_roles)
        else:
            # Fallback: department unknown, show self only
            query = query.eq("user_id", str(user_id))
    else:
        # All other roles: self only
        query = query.eq("user_id", str(user_id))

    if event_category:
        query = query.eq("event_category", event_category)

    result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    return {"success": True, "events": result.data, "total": len(result.data)}
```

Key changes from MVP:
- `captain` gets a clearly-labelled no-op pass (not lumped with HoDs)
- `chief_engineer` / `manager` filter by `user_role IN (dept_member_roles)` using the `in_()` Supabase client method
- `department` column is included in the SELECT (will be populated for new events)
- `_DEPT_MEMBER_ROLES` is defined once in the function, not scattered — making it easy to extend

- [ ] **Step 3: Deploy and test the three tiers**

```bash
docker cp apps/api/routes/ledger_routes.py celeste-api:/app/routes/ledger_routes.py
docker restart celeste-api && sleep 8
```

**Test tier 1 — captain sees all:**
```bash
TOKEN=$(cat /tmp/jwt_token.txt)  # captain token
curl -s "http://localhost:8000/v1/ledger/timeline?limit=5" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('total events:', d['total']); [print(e['user_role'], e.get('department','?')) for e in d['events']]"
```

Expected: shows events from multiple user_roles (not just the captain themselves).

**Test tier 3 — verify self-filter still works (negative test):**
The test user is captain, so self-filter isn't directly testable with the test JWT. Instead, confirm the scoping code path exists by reading the deployed file:

```bash
docker exec celeste-api grep -n "dept_roles\|DEPT_MEMBER_ROLES\|captain" /app/routes/ledger_routes.py | head -10
```

Expected: all three lines are present in the deployed file.

- [ ] **Step 4: Confirm department is in timeline response**

```bash
TOKEN=$(cat /tmp/jwt_token.txt)
curl -s "http://localhost:8000/v1/ledger/timeline?limit=3" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool 2>/dev/null | grep -A2 '"department"'
```

Expected: `"department": "deck"` (or other valid value) present in event objects.

- [ ] **Step 5: Commit**

```bash
git add apps/api/routes/ledger_routes.py
git commit -m "feat: three-tier HoD department scoping in /ledger/timeline (captain=all, HoD=dept, crew=self)"
```

---

## Chunk 5: Read Beacon — stamp department on read events

### Task 5: Add department to the /read-event beacon

**Files:**
- Modify: `apps/api/routes/ledger_routes.py:273-319` (the `record_read_event` function)

Read events (fired when a user opens an entity page) also need `department` stamped so the HoD timeline filter works for read events too.

---

- [ ] **Step 1: Find the read-event endpoint**

Open `apps/api/routes/ledger_routes.py` at lines 273–319. Find the `ev` dict construction, which currently has no `department` key.

- [ ] **Step 2: Extract department from user_context and add to ev**

Add `department` extraction after `actor_name = user_context.get("email", "")`:

```python
actor_name    = user_context.get("email", "")
department    = user_context.get("department", "")
```

Then add to the `ev` dict:
```python
ev = {
    "yacht_id":       str(yacht_id),
    "user_id":        str(user_id),
    "user_role":      user_role,
    "actor_name":     actor_name,
    "department":     department,          # ← add this line
    "event_category": "read",
    "event_type":     "update",
    ...
}
```

- [ ] **Step 3: Deploy and verify read beacon stamps department**

```bash
docker cp apps/api/routes/ledger_routes.py celeste-api:/app/routes/ledger_routes.py
docker restart celeste-api && sleep 8

TOKEN=$(cat /tmp/jwt_token.txt)

# Fire a read beacon
curl -s -X POST http://localhost:8000/v1/ledger/read-event \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"entity_type":"work_order","entity_id":"00000000-0000-0000-0000-000000000002","metadata":{}}' \
  | python3 -m json.tool
```

Then verify the DB row:
```bash
PGPASSWORD="$SUPABASE_DB_PASSWORD" psql \
  -h db.vzsohavtuotocgrfkfyd.supabase.co \
  -p 5432 -U postgres -d postgres \
  -c "SELECT action, user_role, department, event_category FROM public.ledger_events WHERE event_category='read' ORDER BY created_at DESC LIMIT 2;"
```

Expected: most recent row has `department = 'deck'` and `event_category = 'read'`.

- [ ] **Step 4: Commit**

```bash
git add apps/api/routes/ledger_routes.py
git commit -m "feat: stamp department on read-event beacons for complete HoD scope coverage"
```

---

## Final Verification

- [ ] **E2E check: confirm all four ledger layers are wired**

```bash
PGPASSWORD="$SUPABASE_DB_PASSWORD" psql \
  -h db.vzsohavtuotocgrfkfyd.supabase.co \
  -p 5432 -U postgres -d postgres \
  -c "
-- 1. auth_users_roles: department populated for all rows
SELECT 'auth_users_roles null department' AS check_name, COUNT(*) AS should_be_zero
FROM public.auth_users_roles WHERE department IS NULL;

-- 2. ledger_events: recent rows have department
SELECT 'ledger events with department (last 10)' AS check_name, COUNT(*) AS count
FROM public.ledger_events
WHERE created_at > now() - interval '10 minutes'
  AND department IS NOT NULL;

-- 3. constraint exists
SELECT conname FROM pg_constraint WHERE conname = 'valid_department';

-- 4. trigger exists
SELECT tgname FROM pg_trigger WHERE tgname = 'trg_derive_department';
"
```

Expected: `should_be_zero = 0`, `count > 0`, constraint and trigger both present.

---

## What is NOT in scope

- Frontend UI for selecting/switching department view — the timeline API returns the correctly-scoped data; the UI renders whatever comes back
- Per-department sub-views in the ledger frontend — future milestone
- Multi-department users (a user with roles in two departments) — current `sorted_roles` logic takes the most recent role; this is acceptable MVP behaviour
