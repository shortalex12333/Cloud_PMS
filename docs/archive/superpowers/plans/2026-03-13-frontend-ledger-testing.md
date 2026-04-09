# Frontend Ledger Testing Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove that the ledger audit trail, read beacon, and RBAC role-scoped views all work end-to-end against a local Docker environment.

**Architecture:** Three-layer verification — (1) Docker environment startup, (2) API-level curl tests with real JWTs proving every ledger endpoint returns correct JSON for all 3 personas, (3) Playwright E2E tests in a new shard-32-ledger proving the frontend renders correct data and the three-tier scoping (captain=all, HoD=dept, crew=self) is enforced.

**Tech Stack:** Docker Compose (API port 8000, Web port 3000), FastAPI, Next.js 14, Playwright with existing RBAC fixtures (`rbac-fixtures.ts`), Supabase tenant `vzsohavtuotocgrfkfyd.supabase.co`

---

## Pass Criteria (superpowers:verification-before-completion)

A test **PASSES** only when ALL of:
- HTTP status = 200
- Response body contains `"success": true`
- Required data fields are present and non-null
- Role-scoped data only contains events for the correct scope

A test **FAILS** if ANY of:
- HTTP status ≠ 200
- `"success": false` or `"success"` key missing
- Expected fields absent or null
- Crew sees other users' events; HoD sees other departments' events

**TypeScript gate**: `cd apps/web && npx tsc --noEmit` must exit 0 with no output before any Playwright run.

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `apps/web/.env.local` | Create (gitignored) | Local env vars for `npm run dev` |
| `.gitignore` | Modify | Add `apps/web/.env.local` |
| `scripts/test-ledger-api.sh` | Create | Bash: curl all ledger endpoints for all 3 personas with pass/fail output |
| `apps/web/e2e/shard-32-ledger/ledger-history-section.spec.ts` | Create | Playwright: HistorySection renders on entity pages (uses `seedWorkOrder` fixture) |
| `apps/web/e2e/shard-32-ledger/ledger-panel-roles.spec.ts` | Create | Playwright: LedgerPanel me/department views per role (opens dropdown → clicks Ledger) |
| `apps/web/e2e/shard-32-ledger/ledger-read-beacon.spec.ts` | Create | Playwright: beacon fires → verify row in Supabase via `supabaseAdmin` fixture |
| `apps/web/playwright.config.ts` | Modify | Add `shard-32-ledger` project entry |

---

## Chunk 1: Environment Setup

### Task 1: Create `.env.local` + add to `.gitignore`

**Files:**
- Create: `apps/web/.env.local`
- Modify: `.gitignore` (root)

- [ ] **Step 1: Create `apps/web/.env.local`**

```bash
cat > /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/web/.env.local << 'EOF'
NEXT_PUBLIC_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM1OTI4NzUsImV4cCI6MjA3OTE2ODg3NX0.JhJLvLSfLD3OtPDxTgHqgF8dNaZk8ius62jKN68E4WE
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_URL=http://localhost:3000
NEXT_PUBLIC_FRAGMENTED_ROUTES_ENABLED=true
EOF
```

- [ ] **Step 2: Add `.env.local` to root `.gitignore` (if not already there)**

Check first:
```bash
grep "env.local" /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/.gitignore 2>/dev/null || echo "NOT IN GITIGNORE"
```

If "NOT IN GITIGNORE" is printed, add it:
```bash
echo "apps/web/.env.local" >> /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/.gitignore
```

- [ ] **Step 3: Verify `.env.local` was created and is not tracked**

```bash
cat /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/web/.env.local
```

Expected: 5 env vars printed.

---

### Task 2: Start Docker and verify services

**Note:** docker-compose.yml references `${yTEST_YACHT_001_SUPABASE_SERVICE_KEY}` and `${NEXT_PUBLIC_SUPABASE_ANON_KEY}` from shell env. Export them first:

```bash
export yTEST_YACHT_001_SUPABASE_SERVICE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY"
export NEXT_PUBLIC_SUPABASE_ANON_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM1OTI4NzUsImV4cCI6MjA3OTE2ODg3NX0.JhJLvLSfLD3OtPDxTgHqgF8dNaZk8ius62jKN68E4WE"
export AZURE_READ_CLIENT_SECRET=""
export AZURE_WRITE_CLIENT_SECRET=""
```

- [ ] **Step 4: Build and start Docker services**

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS && docker compose up --build -d
```

Wait 30 seconds for API cold start.

- [ ] **Step 5: Verify API health**

```bash
curl -s http://localhost:8000/health
```

Expected: HTTP 200, body contains `"status"` key. If you get connection refused, run `docker compose logs api --tail 30`.

- [ ] **Step 6: Verify web is reachable**

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/
```

Expected: `200` or `307` (redirect to login — both confirm server is up).

---

### Task 3: Get JWTs for all 3 test personas

- [ ] **Step 7: Sign in all 3 users and capture tokens**

```bash
ANON_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM1OTI4NzUsImV4cCI6MjA3OTE2ODg3NX0.JhJLvLSfLD3OtPDxTgHqgF8dNaZk8ius62jKN68E4WE"
SUPABASE_URL="https://vzsohavtuotocgrfkfyd.supabase.co"

get_token() {
  curl -s -X POST "${SUPABASE_URL}/auth/v1/token?grant_type=password" \
    -H "apikey: ${ANON_KEY}" -H "Content-Type: application/json" \
    -d "{\"email\":\"$1\",\"password\":\"$2\"}" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('access_token') or 'ERROR: '+str(d)[:200))"
}

CAPTAIN_TOKEN=$(get_token "x@alex-short.com" "Password2!")
HOD_TOKEN=$(get_token "hod.test@alex-short.com" "Password2!")
CREW_TOKEN=$(get_token "crew.test@alex-short.com" "Password2!")

echo "Captain: ${CAPTAIN_TOKEN:0:50}..."
echo "HoD:     ${HOD_TOKEN:0:50}..."
echo "Crew:    ${CREW_TOKEN:0:50}..."
```

Expected: Three long `eyJ...` strings. If you see `ERROR:` the password is wrong or the user doesn't exist in this tenant.

---

## Chunk 2: API-Level Ledger Tests (Bash Script)

### Task 4: Create the API test script

**Files:**
- Create: `scripts/test-ledger-api.sh`

- [ ] **Step 8: Create `scripts/test-ledger-api.sh`**

```bash
cat > /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/scripts/test-ledger-api.sh << 'SCRIPT'
#!/usr/bin/env bash
set -euo pipefail

API="http://localhost:8000"
ANON_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM1OTI4NzUsImV4cCI6MjA3OTE2ODg3NX0.JhJLvLSfLD3OtPDxTgHqgF8dNaZk8ius62jKN68E4WE"
SUPABASE_URL="https://vzsohavtuotocgrfkfyd.supabase.co"

PASS=0
FAIL=0

# ─── Helpers ─────────────────────────────────────────────────────────────────

get_token() {
  local email="$1" password="$2"
  curl -s -X POST "${SUPABASE_URL}/auth/v1/token?grant_type=password" \
    -H "apikey: ${ANON_KEY}" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"${email}\",\"password\":\"${password}\"}" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('access_token') or 'ERROR')"
}

# check: verifies HTTP 200 + success:true + required key present
check() {
  local label="$1" status="$2" body="$3" required_key="$4"
  local ok=1

  [ "$status" -ne 200 ] && ok=0

  if [ "$ok" -eq 1 ]; then
    echo "$body" | python3 -c "
import sys, json
d = json.load(sys.stdin)
if d.get('success') is not True:
    raise SystemExit(1)
if d.get('${required_key}') is None:
    raise SystemExit(1)
" 2>/dev/null || ok=0
  fi

  if [ "$ok" -eq 1 ]; then
    echo "  ✅ PASS — ${label}"
    PASS=$((PASS + 1))
  else
    echo "  ❌ FAIL — ${label} (HTTP ${status})"
    echo "     $(echo "$body" | head -c 300)"
    FAIL=$((FAIL + 1))
  fi
}

# ─── Get tokens ──────────────────────────────────────────────────────────────

echo "=== Fetching JWTs ==="
CAPTAIN_TOKEN=$(get_token "x@alex-short.com" "Password2!")
HOD_TOKEN=$(get_token "hod.test@alex-short.com" "Password2!")
CREW_TOKEN=$(get_token "crew.test@alex-short.com" "Password2!")

[ "${CAPTAIN_TOKEN:0:5}" = "ERROR" ] && echo "❌ Captain JWT failed" && exit 1
[ "${HOD_TOKEN:0:5}" = "ERROR" ] && echo "❌ HoD JWT failed" && exit 1
[ "${CREW_TOKEN:0:5}" = "ERROR" ] && echo "❌ Crew JWT failed" && exit 1

echo "  Tokens obtained ✓"

# ─── GET /v1/ledger/events ────────────────────────────────────────────────────

echo ""
echo "=== GET /v1/ledger/events (me/all view) ==="

for entry in "captain:${CAPTAIN_TOKEN}" "hod:${HOD_TOKEN}" "crew:${CREW_TOKEN}"; do
  NAME="${entry%%:*}"
  TOKEN="${entry##*:}"
  HTTP=$(curl -s -o /tmp/lb.json -w "%{http_code}" \
    "${API}/v1/ledger/events?limit=10" \
    -H "Authorization: Bearer ${TOKEN}")
  check "${NAME} /events — 200 + success:true + events" "$HTTP" "$(cat /tmp/lb.json)" "events"
done

# ─── GET /v1/ledger/events?user_id= (explicit me filter + no bleed) ──────────

echo ""
echo "=== GET /v1/ledger/events?user_id=... (me filter — no bleed) ==="

CAPTAIN_UID=$(echo "${CAPTAIN_TOKEN}" | cut -d'.' -f2 | python3 -c "
import sys, base64, json
p = sys.stdin.read().strip()
p += '=' * (4 - len(p) % 4)
print(json.loads(base64.urlsafe_b64decode(p)).get('sub',''))
")
echo "  Captain UID: ${CAPTAIN_UID}"

HTTP=$(curl -s -o /tmp/lb.json -w "%{http_code}" \
  "${API}/v1/ledger/events?user_id=${CAPTAIN_UID}&limit=20" \
  -H "Authorization: Bearer ${CAPTAIN_TOKEN}")
BODY=$(cat /tmp/lb.json)
check "captain /events?user_id — 200 + success:true + events" "$HTTP" "$BODY" "events"

# No bleed: all returned events must belong to captain
WRONG=$(echo "$BODY" | python3 -c "
import sys, json
d = json.load(sys.stdin)
bad = [e for e in d.get('events',[]) if e.get('user_id') != '${CAPTAIN_UID}']
print(len(bad))
")
if [ "$WRONG" -eq 0 ]; then
  echo "  ✅ PASS — No event bleed (all events belong to captain)"
  PASS=$((PASS + 1))
else
  echo "  ❌ FAIL — ${WRONG} events from other users in captain's me-filter"
  FAIL=$((FAIL + 1))
fi

# ─── GET /v1/ledger/timeline (three-tier role-scoped) ────────────────────────

echo ""
echo "=== GET /v1/ledger/timeline (role-scoped) ==="

for entry in "captain:${CAPTAIN_TOKEN}" "hod:${HOD_TOKEN}" "crew:${CREW_TOKEN}"; do
  NAME="${entry%%:*}"
  TOKEN="${entry##*:}"
  HTTP=$(curl -s -o /tmp/lb.json -w "%{http_code}" \
    "${API}/v1/ledger/timeline?limit=10" \
    -H "Authorization: Bearer ${TOKEN}")
  check "${NAME} /timeline — 200 + success:true + events" "$HTTP" "$(cat /tmp/lb.json)" "events"
done

# Three-tier ordering: captain >= hod >= crew (by event count)
CAPTAIN_N=$(curl -s "${API}/v1/ledger/timeline?limit=1000" \
  -H "Authorization: Bearer ${CAPTAIN_TOKEN}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('total',0))")
CREW_N=$(curl -s "${API}/v1/ledger/timeline?limit=1000" \
  -H "Authorization: Bearer ${CREW_TOKEN}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('total',0))")

echo "  Captain total: ${CAPTAIN_N}  |  Crew total: ${CREW_N}"
if [ "$CAPTAIN_N" -ge "$CREW_N" ]; then
  echo "  ✅ PASS — Captain sees >= crew events (tier ordering correct)"
  PASS=$((PASS + 1))
else
  echo "  ❌ FAIL — Crew sees more events than captain (scoping broken)"
  FAIL=$((FAIL + 1))
fi

# ─── GET /v1/ledger/events/by-entity/{type}/{id} ─────────────────────────────

echo ""
echo "=== GET /v1/ledger/events/by-entity/{type}/{id} ==="

# Get a real entity ref from captain's events
ENTITY=$(curl -s "${API}/v1/ledger/events?limit=5" \
  -H "Authorization: Bearer ${CAPTAIN_TOKEN}" \
  | python3 -c "
import sys, json
evs = json.load(sys.stdin).get('events', [])
for e in evs:
  if e.get('entity_id') and e.get('entity_type'):
    print(e['entity_type']+':'+e['entity_id'])
    break
" || echo "")

if [ -z "$ENTITY" ]; then
  echo "  ⚠️  SKIP — No events in tenant to derive entity reference"
else
  ETYPE="${ENTITY%%:*}"
  EID="${ENTITY##*:}"
  HTTP=$(curl -s -o /tmp/lb.json -w "%{http_code}" \
    "${API}/v1/ledger/events/by-entity/${ETYPE}/${EID}?limit=10" \
    -H "Authorization: Bearer ${CAPTAIN_TOKEN}")
  check "captain /by-entity — 200 + success:true + events" "$HTTP" "$(cat /tmp/lb.json)" "events"
fi

# ─── POST /v1/ledger/read-event (read beacon) ────────────────────────────────

echo ""
echo "=== POST /v1/ledger/read-event (read beacon) ==="

for entry in "captain:${CAPTAIN_TOKEN}" "hod:${HOD_TOKEN}" "crew:${CREW_TOKEN}"; do
  NAME="${entry%%:*}"
  TOKEN="${entry##*:}"
  HTTP=$(curl -s -o /tmp/lb.json -w "%{http_code}" \
    -X POST "${API}/v1/ledger/read-event" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{\"entity_type\":\"work_order\",\"entity_id\":\"test-$(date +%s%3N)\",\"metadata\":{}}")
  check "${NAME} /read-event — 200 + success:true" "$HTTP" "$(cat /tmp/lb.json)" "success"
done

# ─── POST /v1/ledger/record (explicit record) ────────────────────────────────

echo ""
echo "=== POST /v1/ledger/record ==="

HTTP=$(curl -s -o /tmp/lb.json -w "%{http_code}" \
  -X POST "${API}/v1/ledger/record" \
  -H "Authorization: Bearer ${CAPTAIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"action\": \"artefact_opened\",
    \"entity_type\": \"work_order\",
    \"entity_id\": \"test-$(date +%s%3N)\",
    \"metadata\": {\"source\": \"api_test\"}
  }")
check "captain /record — 200 + success:true" "$HTTP" "$(cat /tmp/lb.json)" "success"

# ─── GET /v1/ledger/day-anchors ──────────────────────────────────────────────

echo ""
echo "=== GET /v1/ledger/day-anchors ==="

HTTP=$(curl -s -o /tmp/lb.json -w "%{http_code}" \
  "${API}/v1/ledger/day-anchors?days=7" \
  -H "Authorization: Bearer ${CAPTAIN_TOKEN}")
check "captain /day-anchors — 200 + success:true + anchors" "$HTTP" "$(cat /tmp/lb.json)" "anchors"

# ─── Summary ─────────────────────────────────────────────────────────────────

echo ""
echo "════════════════════════════════════════"
echo "  Results: ${PASS} passed, ${FAIL} failed"
echo "════════════════════════════════════════"

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
SCRIPT

chmod +x /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/scripts/test-ledger-api.sh
```

- [ ] **Step 9: Run the API test script**

```bash
bash /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/scripts/test-ledger-api.sh
```

Expected output (minimum passing):
```
=== Fetching JWTs ===
  Tokens obtained ✓

=== GET /v1/ledger/events (me/all view) ===
  ✅ PASS — captain /events — 200 + success:true + events
  ✅ PASS — hod /events — 200 + success:true + events
  ✅ PASS — crew /events — 200 + success:true + events
...
════════════════════════════════════════
  Results: 11 passed, 0 failed
════════════════════════════════════════
```

**If a test fails:**
- `401`: JWT wrong → recheck password / tenant
- `400 No yacht_id`: User not in `auth_users_roles` for this tenant
- `500`: `docker compose logs api --tail 50`
- `success:false`: Check the detail field in the printed body

- [ ] **Step 10: Commit the bash test script (NOT .env.local)**

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS
git add scripts/test-ledger-api.sh .gitignore
git commit -m "test: add ledger API curl test script for all 3 personas"
```

---

## Chunk 3: Playwright E2E — shard-32-ledger

### Task 5: Add shard-32-ledger to Playwright config

**Files:**
- Modify: `apps/web/playwright.config.ts`

- [ ] **Step 11: Add the shard-32-ledger project to `playwright.config.ts`**

Open `apps/web/playwright.config.ts`. Find the `shard-31-fragmented-routes` project entry (the last one). Add immediately after its closing `},`:

```typescript
// =========================================================================
// SHARD 32: Ledger Audit Trail — HistorySection, LedgerPanel, Read Beacon
// =========================================================================
{
  name: 'shard-32-ledger',
  testDir: './e2e/shard-32-ledger',
  dependencies: ['setup'],
  use: {
    ...devices['Desktop Chrome'],
  },
},
```

- [ ] **Step 12: Verify TypeScript compiles clean**

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/web && npx tsc --noEmit
```

Expected: No output (exit 0). Any errors must be fixed before continuing.

---

### Task 6: Playwright — HistorySection renders on seeded entity pages

**Files:**
- Create: `apps/web/e2e/shard-32-ledger/ledger-history-section.spec.ts`

**Key design decision:** Use `seedWorkOrder` and `seedFault` fixtures from `rbac-fixtures.ts` to guarantee a real entity exists. This avoids any dependency on list endpoints (which don't exist as collection routes). After the action that creates the entity, the ledger middleware in `p0_actions_routes.py` writes a creation event — so by the time we navigate to the detail page, there will be at least 1 ledger entry.

However: the entity is seeded directly via Supabase (bypassing the API), so the ledger middleware does NOT fire. We need to trigger a mutation via the API first, or alternatively verify the `useEntityLedger` hook simply renders gracefully with 0 entries (which is also valid since the empty state renders "No history entries found" without crashing).

For a clean test with guaranteed entries: seed via the API's action endpoint to trigger the centralised ledger middleware.

- [ ] **Step 13: Create `apps/web/e2e/shard-32-ledger/ledger-history-section.spec.ts`**

```typescript
// apps/web/e2e/shard-32-ledger/ledger-history-section.spec.ts

import { test, expect, generateTestId } from '../rbac-fixtures';

/**
 * SHARD 32: Ledger — HistorySection on entity detail pages
 *
 * Verifies:
 * - HistorySection heading 'History' renders on entity pages
 * - No crash when 0 entries (renders empty state gracefully)
 * - When entries exist, rows are visible
 * - Read beacon fires on mount (network request intercepted)
 *
 * Pass criteria:
 * - 'History' heading is visible (getByRole heading)
 * - No error/crash text present
 * - Read beacon POST request fires within 5s of page load
 */

const BASE_URL = process.env.E2E_BASE_URL || 'http://localhost:3000';
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

test.describe('HistorySection renders on entity detail pages', () => {
  test.use({ storageState: './playwright/.auth/hod.json' });

  test('work-order detail page: History heading visible, no crash', async ({
    hodPage,
    seedWorkOrder,
  }) => {
    // 1. Seed a fresh work order (guaranteed to exist)
    const wo = await seedWorkOrder(`History Test WO ${generateTestId('hist')}`);

    // 2. Navigate to the fragmented detail page
    await hodPage.goto(`${BASE_URL}/work-orders/${wo.id}`);
    await hodPage.waitForLoadState('networkidle');

    // 3. History heading should render (even with 0 entries — empty state is valid)
    await expect(
      hodPage.getByRole('heading', { name: 'History' })
    ).toBeVisible({ timeout: 10_000 });

    // 4. No error text anywhere on the page
    await expect(hodPage.getByText('500').first()).not.toBeVisible();
    await expect(hodPage.getByText('Failed to Load').first()).not.toBeVisible();
  });

  test('fault detail page: History heading visible, no crash', async ({
    hodPage,
    seedFault,
  }) => {
    const fault = await seedFault(`History Test Fault ${generateTestId('hist')}`);

    await hodPage.goto(`${BASE_URL}/faults/${fault.id}`);
    await hodPage.waitForLoadState('networkidle');

    await expect(
      hodPage.getByRole('heading', { name: 'History' })
    ).toBeVisible({ timeout: 10_000 });

    await expect(hodPage.getByText('500').first()).not.toBeVisible();
  });

  test('work-order detail page: read beacon fires on mount', async ({
    hodPage,
    seedWorkOrder,
  }) => {
    const wo = await seedWorkOrder(`Beacon Test WO ${generateTestId('bcn')}`);

    // Watch for the beacon request BEFORE navigating
    const beaconPromise = hodPage.waitForRequest(
      (req) =>
        req.url().includes('/v1/ledger/read-event') && req.method() === 'POST',
      { timeout: 10_000 }
    );

    await hodPage.goto(`${BASE_URL}/work-orders/${wo.id}`);

    // Beacon must fire (fire-and-forget, but still fires synchronously on mount)
    const beaconReq = await beaconPromise;
    const body = beaconReq.postDataJSON();

    expect(body).toHaveProperty('entity_type', 'work_order');
    expect(body).toHaveProperty('entity_id', wo.id);
    expect(body).toHaveProperty('metadata');

    // Auth header must be Bearer JWT (not unauthenticated)
    const authHeader = beaconReq.headers()['authorization'];
    expect(authHeader).toMatch(/^Bearer eyJ/);
  });

  test('fault detail page: read beacon fires with correct entity_type', async ({
    hodPage,
    seedFault,
  }) => {
    const fault = await seedFault(`Beacon Test Fault ${generateTestId('bcn')}`);

    const beaconPromise = hodPage.waitForRequest(
      (req) =>
        req.url().includes('/v1/ledger/read-event') && req.method() === 'POST',
      { timeout: 10_000 }
    );

    await hodPage.goto(`${BASE_URL}/faults/${fault.id}`);

    const beaconReq = await beaconPromise;
    const body = beaconReq.postDataJSON();
    expect(body.entity_type).toBe('fault');
    expect(body.entity_id).toBe(fault.id);
  });

  test('HistorySection rows render for work order with existing ledger events', async ({
    hodPage,
    supabaseAdmin,
    seedWorkOrder,
  }) => {
    const wo = await seedWorkOrder(`Ledger Row Test WO ${generateTestId('row')}`);

    // Insert a ledger event directly via service role to guarantee at least 1 entry
    const YACHT_ID = process.env.TEST_YACHT_ID || '85fe1119-b04c-41ac-80f1-829d23322598';
    await supabaseAdmin.from('ledger_events').insert({
      yacht_id: YACHT_ID,
      user_id: '00000000-0000-0000-0000-000000000001', // placeholder user
      user_role: 'captain',
      actor_name: 'Test Suite',
      department: 'deck',
      event_category: 'mutation',
      event_type: 'create',
      action: 'create_work_order',
      entity_type: 'work_order',
      entity_id: wo.id,
      change_summary: 'Work order created by test suite',
      source_context: 'microaction',
      proof_hash: 'test-hash-' + wo.id,
    });

    await hodPage.goto(`${BASE_URL}/work-orders/${wo.id}`);
    await hodPage.waitForLoadState('networkidle');

    // Wait for the by-entity fetch to complete
    await hodPage.waitForResponse(
      (res) => res.url().includes('/v1/ledger/events/by-entity/work_order/') && res.status() === 200,
      { timeout: 10_000 }
    );

    // History heading visible
    await expect(
      hodPage.getByRole('heading', { name: 'History' })
    ).toBeVisible();

    // At least 1 entry row visible (HistorySection renders rows as px-5 py-3 divs/anchors)
    const rows = hodPage.locator('[class*="px-5"][class*="py-3"]');
    await expect(rows.first()).toBeVisible({ timeout: 5_000 });
    const rowCount = await rows.count();
    expect(rowCount).toBeGreaterThanOrEqual(1);
  });
});
```

- [ ] **Step 14: Run this spec**

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/web && \
  E2E_BASE_URL=http://localhost:3000 \
  NEXT_PUBLIC_API_URL=http://localhost:8000 \
  E2E_NO_SERVER=true \
  npx playwright test e2e/shard-32-ledger/ledger-history-section.spec.ts \
  --project=shard-32-ledger --reporter=list
```

Expected: All tests PASS (or the 5th test skips if Supabase insert is rejected by RLS — in that case, use the service role client correctly). No failures.

---

### Task 7: Playwright — LedgerPanel role-scoped views

**Files:**
- Create: `apps/web/e2e/shard-32-ledger/ledger-panel-roles.spec.ts`

**Key design decision:** The LedgerPanel is opened via a two-step UI flow:
1. Click `[data-testid="utility-menu-button"]` (the BookOpen+Menu button in SpotlightSearch)
2. Click the `DropdownMenuItem` with text "Ledger"

- [ ] **Step 15: Create `apps/web/e2e/shard-32-ledger/ledger-panel-roles.spec.ts`**

```typescript
// apps/web/e2e/shard-32-ledger/ledger-panel-roles.spec.ts

import { test, expect } from '../rbac-fixtures';

/**
 * SHARD 32: Ledger — LedgerPanel role-scoped views
 *
 * The LedgerPanel is opened via:
 * 1. Click [data-testid="utility-menu-button"] (BookOpen+Menu dropdown trigger)
 * 2. Click the "Ledger" DropdownMenuItem inside the opened menu
 *
 * Tests:
 * - Panel opens and renders (heading 'Ledger' or 'Activity' visible)
 * - 'Me' mode → network request to /v1/ledger/events?user_id=...
 * - 'Department' mode → network request to /v1/ledger/timeline
 * - Crew /timeline API call returns only own events (self-only tier)
 * - HoD /timeline returns only dept-role events (not other departments)
 * - Captain /timeline returns more events than crew (all-events tier)
 */

const BASE_URL = process.env.E2E_BASE_URL || 'http://localhost:3000';
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Opens the LedgerPanel via the utility-menu dropdown
async function openLedgerPanel(page: import('@playwright/test').Page) {
  // Step 1: Open the utility dropdown (BookOpen + Menu button)
  const menuTrigger = page.locator('[data-testid="utility-menu-button"]');
  await expect(menuTrigger).toBeVisible({ timeout: 10_000 });
  await menuTrigger.click();

  // Step 2: Click "Ledger" in the dropdown menu
  // Use role="menuitem" (Radix DropdownMenuItem default) to survive strictLocators:true
  // Fallback: .first() if multiple "Ledger" text nodes exist simultaneously
  const ledgerItem = page.getByRole('menuitem', { name: 'Ledger' });
  await expect(ledgerItem).toBeVisible({ timeout: 5_000 });
  await ledgerItem.click();
}

test.describe('LedgerPanel — opens via utility menu', () => {
  test.use({ storageState: './playwright/.auth/hod.json' });

  test('LedgerPanel opens and shows content (no crash)', async ({ hodPage }) => {
    await hodPage.goto(BASE_URL);
    await hodPage.waitForLoadState('networkidle');

    await openLedgerPanel(hodPage);

    // Panel should render — check for any heading containing Ledger or Activity
    const panelHeading = hodPage.getByRole('heading', { name: /ledger|activity/i }).first();
    await expect(panelHeading).toBeVisible({ timeout: 10_000 });

    // No error states
    await expect(hodPage.getByText('500').first()).not.toBeVisible();
  });

  test('LedgerPanel Me mode fires request to /v1/ledger/events', async ({ hodPage }) => {
    await hodPage.goto(BASE_URL);
    await hodPage.waitForLoadState('networkidle');

    // Listen for /events request (not by-entity, not /timeline)
    const eventsPromise = hodPage.waitForRequest(
      (req) =>
        req.url().includes('/v1/ledger/events') &&
        !req.url().includes('by-entity') &&
        !req.url().includes('timeline'),
      { timeout: 15_000 }
    );

    await openLedgerPanel(hodPage);

    // The panel defaults to 'Me' mode — /events should fire
    const eventsReq = await eventsPromise;
    expect(eventsReq.url()).toContain('/v1/ledger/events');
    // Me mode must include user_id param
    expect(eventsReq.url()).toContain('user_id=');
  });

  test('LedgerPanel Department mode fires request to /v1/ledger/timeline', async ({
    hodPage,
  }) => {
    await hodPage.goto(BASE_URL);
    await hodPage.waitForLoadState('networkidle');

    await openLedgerPanel(hodPage);
    await hodPage.waitForTimeout(1_000); // Let Me mode load first

    // Watch for /timeline request
    const timelinePromise = hodPage.waitForRequest(
      (req) => req.url().includes('/v1/ledger/timeline'),
      { timeout: 15_000 }
    );

    // Switch to Department mode
    // Try common toggle patterns: 'Department', 'All', 'Team', 'Dept'
    const deptToggle = hodPage
      .getByRole('button', { name: /department|all|team|dept/i })
      .first();
    if (await deptToggle.isVisible()) {
      await deptToggle.click();
    } else {
      // Fallback: look for any tab/button after the 'Me' button
      const meBtn = hodPage.getByRole('button', { name: /me|mine/i }).first();
      if (await meBtn.isVisible()) {
        // The sibling button should be department mode
        await meBtn.locator('..').getByRole('button').nth(1).click();
      }
    }

    const timelineReq = await timelinePromise;
    expect(timelineReq.url()).toContain('/v1/ledger/timeline');
  });
});

test.describe('LedgerPanel — API-level role scoping verification', () => {
  test('Crew /timeline — API returns only own events', async ({ crewPage }) => {
    // Direct API test: no UI needed, verifies the backend scoping rule
    const res = await crewPage.request.get(`${API_URL}/v1/ledger/timeline?limit=100`);
    expect(res.status()).toBe(200);
    const data = await res.json();
    expect(data.success).toBe(true);

    const events: Array<{ user_id: string }> = data.events || [];
    console.log(`Crew /timeline: ${events.length} events`);

    // Get crew user_id from the response — if all events belong to same user, scoping works
    if (events.length > 1) {
      const uniqueUsers = new Set(events.map((e) => e.user_id));
      // Crew should only see their own events → 1 unique user_id
      expect(uniqueUsers.size).toBe(1);
      console.log(`✅ Crew sees exactly 1 user's events (self-only tier confirmed)`);
    } else {
      console.log(`ℹ️ ${events.length} events — insufficient data to assert uniqueness`);
    }
  });

  test('Captain /timeline — API returns more or equal events than crew', async ({
    captainPage,
    crewPage,
  }) => {
    const captainRes = await captainPage.request.get(
      `${API_URL}/v1/ledger/timeline?limit=1000`
    );
    const crewRes = await crewPage.request.get(
      `${API_URL}/v1/ledger/timeline?limit=1000`
    );

    expect(captainRes.status()).toBe(200);
    expect(crewRes.status()).toBe(200);

    const captainData = await captainRes.json();
    const crewData = await crewRes.json();

    const captainTotal = captainData.total ?? (captainData.events || []).length;
    const crewTotal = crewData.total ?? (crewData.events || []).length;

    console.log(`Captain: ${captainTotal} events | Crew: ${crewTotal} events`);
    expect(captainTotal).toBeGreaterThanOrEqual(crewTotal);
    console.log(`✅ Captain sees >= crew events (three-tier captain=all confirmed)`);
  });

  test('HoD /timeline — API returns only engineering/interior department roles', async ({
    hodPage,
  }) => {
    // HoD role = chief_engineer or manager → should only see:
    // engineering dept: chief_engineer, eto
    // interior dept: manager, interior
    const HOD_VISIBLE_ROLES = ['chief_engineer', 'eto', 'manager', 'interior'];

    const res = await hodPage.request.get(`${API_URL}/v1/ledger/timeline?limit=100`);
    expect(res.status()).toBe(200);
    const data = await res.json();
    expect(data.success).toBe(true);

    const events: Array<{ user_role: string }> = data.events || [];
    console.log(`HoD /timeline: ${events.length} events`);

    if (events.length > 0) {
      const badEvents = events.filter((e) => !HOD_VISIBLE_ROLES.includes(e.user_role));
      if (badEvents.length > 0) {
        const badRoles = [...new Set(badEvents.map((e) => e.user_role))];
        throw new Error(
          `HoD sees ${badEvents.length} events from non-department roles: ${badRoles.join(', ')}`
        );
      }
      console.log(
        `✅ All ${events.length} HoD events have dept-scoped roles (middle-tier confirmed)`
      );
    } else {
      console.log(`ℹ️ No events returned for HoD — cannot verify dept scoping`);
    }
  });
});
```

- [ ] **Step 16: Run this spec**

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/web && \
  E2E_BASE_URL=http://localhost:3000 \
  NEXT_PUBLIC_API_URL=http://localhost:8000 \
  E2E_NO_SERVER=true \
  npx playwright test e2e/shard-32-ledger/ledger-panel-roles.spec.ts \
  --project=shard-32-ledger --reporter=list
```

**If "utility-menu-button not found":** The button was located at `SpotlightSearch.tsx:1281` with `data-testid="utility-menu-button"`. If it fails, inspect the element:
```bash
cd apps/web && npx playwright test --project=shard-32-ledger \
  --grep "opens via utility menu" --headed --slowmo=1000
```

**If dept toggle button not found** (test 3): Check `LedgerPanel.tsx` for the mode toggle buttons. Add `data-testid="ledger-mode-dept"` to the department toggle button, then update the test selector.

---

### Task 8: Playwright — Read beacon DB verification (service role)

**Files:**
- Create: `apps/web/e2e/shard-32-ledger/ledger-read-beacon.spec.ts`

**Note:** Uses `supabaseAdmin` fixture from `rbac-fixtures.ts` — already initialised with `RBAC_CONFIG.supabaseServiceKey`. No hardcoded keys.

- [ ] **Step 17: Create `apps/web/e2e/shard-32-ledger/ledger-read-beacon.spec.ts`**

```typescript
// apps/web/e2e/shard-32-ledger/ledger-read-beacon.spec.ts

import { test, expect, generateTestId } from '../rbac-fixtures';

/**
 * SHARD 32: Ledger — Read beacon DB verification
 *
 * The useReadBeacon hook fires POST /v1/ledger/read-event on every entity page mount.
 * This test verifies the event is actually written to ledger_events in Supabase.
 *
 * Strategy:
 * 1. Seed a fresh work order (guaranteed unique entity_id)
 * 2. Count ledger rows for that entity BEFORE navigation (expect 0)
 * 3. Navigate to /work-orders/{id} — triggers useReadBeacon
 * 4. Intercept the beacon POST request, verify its shape
 * 5. Wait 3s for async DB write
 * 6. Count ledger rows AFTER navigation (expect >= 1, event_category='read')
 *
 * Uses supabaseAdmin fixture (service role — bypasses RLS).
 * Pass criteria: DB count increases by >= 1.
 */

const BASE_URL = process.env.E2E_BASE_URL || 'http://localhost:3000';

test.describe('Read beacon DB persistence', () => {
  test.use({ storageState: './playwright/.auth/hod.json' });

  test('navigating to work-order page writes event_category=read row to ledger_events', async ({
    hodPage,
    seedWorkOrder,
    supabaseAdmin,
  }) => {
    // 1. Seed a fresh WO — guaranteed unique entity_id, 0 existing ledger rows
    const wo = await seedWorkOrder(`Beacon DB Test ${generateTestId('db')}`);

    const YACHT_ID = process.env.TEST_YACHT_ID || '85fe1119-b04c-41ac-80f1-829d23322598';

    // 2. Pre-navigation count — should be 0 for this brand-new entity
    const { count: beforeCount, error: beforeErr } = await supabaseAdmin
      .from('ledger_events')
      .select('*', { count: 'exact', head: true })
      .eq('entity_id', wo.id)
      .eq('event_category', 'read');

    if (beforeErr) throw new Error(`Pre-count query failed: ${beforeErr.message}`);
    console.log(`Before navigation: ${beforeCount} read events for WO ${wo.id}`);
    expect(beforeCount).toBe(0); // Fresh entity — no events yet

    // 3. Intercept the beacon request
    const beaconPromise = hodPage.waitForRequest(
      (req) =>
        req.url().includes('/v1/ledger/read-event') && req.method() === 'POST',
      { timeout: 10_000 }
    );

    // 4. Navigate (triggers useReadBeacon on mount)
    await hodPage.goto(`${BASE_URL}/work-orders/${wo.id}`);

    // 5. Verify beacon request fired with correct body
    const beaconReq = await beaconPromise;
    const body = beaconReq.postDataJSON();
    expect(body.entity_type).toBe('work_order');
    expect(body.entity_id).toBe(wo.id);
    expect(beaconReq.headers()['authorization']).toMatch(/^Bearer eyJ/);
    console.log(`Beacon fired: ${JSON.stringify(body)}`);

    // 6. Wait for the async DB write (fire-and-forget → give API time to write)
    await hodPage.waitForTimeout(3_000);

    // 7. Post-navigation count — should be >= 1
    const { count: afterCount, error: afterErr } = await supabaseAdmin
      .from('ledger_events')
      .select('*', { count: 'exact', head: true })
      .eq('entity_id', wo.id)
      .eq('event_category', 'read');

    if (afterErr) throw new Error(`Post-count query failed: ${afterErr.message}`);
    console.log(`After navigation: ${afterCount} read events for WO ${wo.id}`);

    const delta = (afterCount || 0) - (beforeCount || 0);
    expect(delta).toBeGreaterThanOrEqual(1);
    console.log(`✅ Read beacon created ${delta} ledger_events row(s) with event_category=read`);
  });

  test('read beacon row has correct fields stamped (user_role, department, proof_hash)', async ({
    hodPage,
    seedWorkOrder,
    supabaseAdmin,
  }) => {
    const wo = await seedWorkOrder(`Beacon Fields Test ${generateTestId('fld')}`);

    const beaconPromise = hodPage.waitForRequest(
      (req) =>
        req.url().includes('/v1/ledger/read-event') && req.method() === 'POST',
      { timeout: 10_000 }
    );

    await hodPage.goto(`${BASE_URL}/work-orders/${wo.id}`);
    await beaconPromise; // wait for it to fire

    // Wait for DB write
    await hodPage.waitForTimeout(3_000);

    // Fetch the actual DB row
    const { data: rows, error } = await supabaseAdmin
      .from('ledger_events')
      .select('user_role, department, proof_hash, event_category, source_context, action')
      .eq('entity_id', wo.id)
      .eq('event_category', 'read')
      .limit(1);

    if (error) throw new Error(`Fetch failed: ${error.message}`);

    if (!rows || rows.length === 0) {
      throw new Error('No read event found in DB — beacon did not persist');
    }

    const row = rows[0];
    console.log(`DB row: ${JSON.stringify(row)}`);

    // Verify required fields are stamped
    expect(row.event_category).toBe('read');
    expect(row.source_context).toBe('microaction'); // fixed in ledger_routes.py
    expect(row.proof_hash).toBeTruthy(); // SHA-256 hash, not null
    expect(row.user_role).toBeTruthy(); // Role must be stamped
    // action should be view_work_order (f`view_{entity_type}`)
    expect(row.action).toBe('view_work_order');
  });
});
```

- [ ] **Step 18: Run this spec**

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/web && \
  E2E_BASE_URL=http://localhost:3000 \
  NEXT_PUBLIC_API_URL=http://localhost:8000 \
  E2E_NO_SERVER=true \
  npx playwright test e2e/shard-32-ledger/ledger-read-beacon.spec.ts \
  --project=shard-32-ledger --reporter=list
```

Expected: Both tests PASS.

**If `delta = 0` (beacon fires but DB row not written):**
```bash
docker compose logs api --tail 50 | grep -i "ledger\|beacon\|read-event"
```
Check if `source_context='microaction'` is accepted. If `source_context='read_beacon'` appears in logs, migration 13's valid_source_context constraint needs to include `'read_beacon'` — run the constraint expansion from migration 13 Part 3.

- [ ] **Step 19: Commit all Playwright tests**

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS
git add apps/web/e2e/shard-32-ledger/ apps/web/playwright.config.ts
git commit -m "test(e2e): shard-32-ledger — HistorySection, LedgerPanel roles, read beacon DB verification"
```

---

## Chunk 4: Full Shard Run + Fix Loop

### Task 9: Run full shard-32-ledger

- [ ] **Step 20: Authenticate all test users (required before shard run)**

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/web && \
  E2E_BASE_URL=http://localhost:3000 \
  npx playwright test --project=setup --reporter=list
```

Expected: `hod.json`, `crew.json`, `captain.json` written to `playwright/.auth/`.

- [ ] **Step 21: Run full shard-32-ledger**

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/web && \
  E2E_BASE_URL=http://localhost:3000 \
  NEXT_PUBLIC_API_URL=http://localhost:8000 \
  E2E_NO_SERVER=true \
  npx playwright test --project=shard-32-ledger --reporter=list 2>&1 | tee /tmp/shard32.txt
```

- [ ] **Step 22: Check the results**

```bash
grep -E "passed|failed|skipped" /tmp/shard32.txt | tail -3
```

**Pass threshold (evidence required before claiming complete):**
- `0 failed`
- `≥ 5 passed`
- Skips are acceptable only for tests that log `ℹ️`

---

### Task 10: Fix Loop

**A. `utility-menu-button not found`**
- The element exists at `SpotlightSearch.tsx:1281`. Check if the page loaded correctly.
- Run with `--headed --slowmo=500` to watch the click.
- If the search bar doesn't render: the user may not be authenticated. Re-run setup.

**B. `History heading not found` on entity pages**
- Verify `HistorySection` is wired to the page. Check `apps/web/src/app/work-orders/[id]/page.tsx` for `useEntityLedger` + `HistorySection` render guard.
- If page returns error (404/403): the seeded entity may not be RLS-accessible. Check `pms_work_orders` RLS policy — it must allow the HoD user to SELECT.

**C. `Crew sees multiple user_ids in /timeline`**
- Backend scope leak. Open `apps/api/routes/ledger_routes.py`, find the `get_ledger_timeline` function.
- Verify the `else` branch ends with `query = query.eq("user_id", str(user_id))`.

**D. `HoD sees captain or deck events`**
- `_DEPT_MEMBER_ROLES` dict fallback triggers when `department` is empty.
- Check auth middleware: `apps/api/middleware/auth.py` must include `department` in the SELECT from `auth_users_roles`.

**E. `Beacon delta = 0`**
- The `ledger_events` INSERT policy is service_role only (migration 13, line 119).
- The API's `_get_tenant_client()` must return a service-role client.
- Check: `apps/api/integrations/supabase.py` — verify it uses the service key, not anon key.

- [ ] **Step 23: After any fix, run only the failing spec**

```bash
cd apps/web && npx playwright test e2e/shard-32-ledger/<failing-spec>.spec.ts \
  --project=shard-32-ledger --reporter=list
```

Expected: PASS

- [ ] **Step 24: Full shard-32 green run**

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/web && \
  E2E_BASE_URL=http://localhost:3000 \
  NEXT_PUBLIC_API_URL=http://localhost:8000 \
  E2E_NO_SERVER=true \
  npx playwright test --project=shard-32-ledger --reporter=list
```

Expected: `0 failed`.

- [ ] **Step 25: Final commit**

```bash
git add -A
git commit -m "test: all shard-32-ledger specs passing — audit trail verified end-to-end"
```

---

## Quick Reference

### Ports
| Service | URL |
|---------|-----|
| API | `http://localhost:8000` |
| Web | `http://localhost:3000` |
| API health | `http://localhost:8000/health` |

### Test personas
| Email | Role | `/timeline` scope |
|-------|------|-------------------|
| `x@alex-short.com` | `captain` | All yacht events |
| `hod.test@alex-short.com` | `chief_engineer` or `manager` | Dept only (engineering/interior) |
| `crew.test@alex-short.com` | crew | Self only |

### Commands
```bash
# Start Docker
docker compose up --build -d

# API tests (no browser)
bash scripts/test-ledger-api.sh

# TypeScript check
cd apps/web && npx tsc --noEmit

# Auth setup (Playwright)
cd apps/web && E2E_BASE_URL=http://localhost:3000 npx playwright test --project=setup

# Run shard-32 only
cd apps/web && E2E_BASE_URL=http://localhost:3000 NEXT_PUBLIC_API_URL=http://localhost:8000 \
  E2E_NO_SERVER=true npx playwright test --project=shard-32-ledger --reporter=list

# View HTML report
cd apps/web && npx playwright show-report
```
