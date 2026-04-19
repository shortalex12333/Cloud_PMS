# Handover — Incoming-Ack Manual Test Log

**Tester:** CEO (manual walk against local handover04 Docker stack)
**Date:** 2026-04-17
**Feature:** Incoming-crew acknowledgement (3rd signature) + dynamic 3-column signature block
**PR:** [#642](https://github.com/shortalex12333/Cloud_PMS/pull/642)
**Branch:** `feat/handover04-incoming-sign`
**Commit under test:** `ef1bdbfb`
**Worktree:** `/Users/celeste7/Documents/Cloud_PMS-handover04`

**Web URL:** `http://localhost:3030`
**API URL:** `http://localhost:8020`
**Microservice URL:** `http://localhost:10010`
**Auth URL (MASTER Supabase):** `https://qvzmkaamzaqxpzbewjxe.supabase.co`

**Method:** Hand-walk each scenario in a real Chrome window against the local stack. Paste console/network errors directly into the ERR cells. API-only verifications are done with curl + psql from a second terminal.

**Results legend:**
- `Y` — verified visually in browser
- `Y (API)` — verified via curl / psql / microservice logs
- `PENDING-UI` — requires live browser interaction, not yet walked
- `N` — element missing or behaviour wrong
- `ERR` — console error or API failure (paste body)
- `SKIP` — known non-testable path (e.g. broken test account, print dialog)

---

## Test credentials

All on yacht `85fe1119-b04c-41ac-80f1-829d23322598`. Password is the same for every test user.

| Role | Email | Password | DB role | Department |
|------|-------|----------|---------|------------|
| Crew | `crew.test@alex-short.com` | `Password2!` | crew | general |
| HOD (Chief Eng) | `hod.test@alex-short.com` | `Password2!` | chief_engineer | engineering |
| Captain | `captain.tenant@alex-short.com` | `Password2!` | captain | deck |
| Fleet Manager | `fleet-test-1775570624@celeste7.ai` | `Password2!` | manager (BROKEN — TENANT JWT, backend expects MASTER; same caveat as reference) | interior |

The MASTER Supabase anon key (needed for token exchange from curl) is in `/Users/celeste7/Documents/Cloud_PMS/env/env vars.md` under `MASTER_SUPABASE_ANON_KEY`.

---

## Browser console setup

Open DevTools → Console before every scenario. Paste this to intercept API calls:

```javascript
const _origFetch = window.fetch;
window.fetch = async (...args) => {
  const r = await _origFetch(...args);
  const url = typeof args[0] === 'string' ? args[0] : args[0]?.url || '';
  if (url.includes('/actions/execute') || url.includes('/v1/') || url.includes('/api/')) {
    const clone = r.clone();
    clone.json().then(d => console.log(`[API ${r.status}]`, url.split('/').slice(-3).join('/'), JSON.stringify(d).slice(0, 300))).catch(() => {});
  }
  return r;
};
```

---

## What ships in PR #642

| Change | Where |
|-------|-------|
| New route `POST /v1/actions/handover/{export_id}/sign/incoming?acknowledge_critical=true` (widened role gate — crew can now sign) | `apps/api` handover action handler |
| New ledger event `handover_acknowledged` + cascade to outgoing signer + yacht captains + yacht managers | handover action handler |
| Entity endpoint `/v1/entity/handover_export/{id}` now returns `incoming_user_id`, `incoming_user_name`, `incoming_role`, `incoming_signed_at`, `incoming_comments`, `incoming_acknowledged_critical`, `incoming_signature`, `signoff_complete` | `entity_routes.py` |
| Frontend: "Acknowledge Handover" button on `/handover-export/{id}` when `review_status='complete' AND incoming_signed_at IS NULL` AND current user is NOT the outgoing signer AND NOT the HOD signer | `HandoverContent.tsx` |
| Dynamic 3-column signature block (Prepared / Reviewed / Acknowledged) | `SignatureBlock.tsx` |
| Critical-items acknowledgement checkbox in sign modal when export contains at least one critical item | sign modal |
| State-machine reconciliation (handler now reads `review_status` not legacy `status`) | handover action handler |

---

## Pre-flight — stack must be up

Run these from `/Users/celeste7/Documents/Cloud_PMS-handover04` in a fresh terminal before starting.

```bash
cd /Users/celeste7/Documents/Cloud_PMS-handover04

# Start both compose projects (takes ~20s after first build)
COMPOSE_PROJECT_NAME=handover04 docker compose --profile full up -d
COMPOSE_PROJECT_NAME=handover04-export \
  docker compose -f docker-compose.handover-export.yml up -d

# Verify up
COMPOSE_PROJECT_NAME=handover04 docker compose --profile full ps
COMPOSE_PROJECT_NAME=handover04-export \
  docker compose -f docker-compose.handover-export.yml ps
```

| # | Check | Command / URL | Expected | Y / N / ERR | Notes |
|---|-------|--------------|----------|-------------|-------|
| P1a | API liveness | `curl -fsS http://localhost:8020/healthz` | `{"status":"ok"}` | | |
| P1b | API pipeline ready | `curl -fsS http://localhost:8020/health` | `pipeline_ready:true` | | |
| P1c | Microservice up | `curl -fsS http://localhost:10010/health` | `{"status":"healthy",...}` | | |
| P1d | Web serves 200 | `curl -fsS -o /dev/null -w "%{http_code}\n" http://localhost:3030/` | `200` | | |
| P1e | Containers healthy | `docker compose --profile full ps` | `api`, `web`, workers `running` (cache-listener may show `unhealthy` — ignore per RUNBOOK) | | |
| P2 | Login as captain | Open `http://localhost:3030/login` → captain creds → dashboard loads | Dashboard renders, no redirect loop | | |
| P3 | Login as HOD | Logout → HOD creds | Dashboard renders | | |
| P4 | Login as crew | Logout → crew creds | Dashboard renders | | |
| P5 | No red console errors on dashboard | DevTools Console | No 400/500 from `localhost:8020`, no CORS errors | | |

---

## Scenario 1 — Seed a complete export (prerequisite for Scenarios 2-6, 8-10)

**Goal:** End this scenario with a `handover_exports` row where `review_status='complete' AND incoming_signed_at IS NULL`. All downstream scenarios assume this exists.

**Walk:**

| # | Step | Location | Expected | Y / N / ERR | Notes |
|---|------|----------|----------|-------------|-------|
| 1.1 | Login as **captain** | `http://localhost:3030/login` | Dashboard loads | | |
| 1.2 | Open Handover → Queue tab | Sidebar → Handover | Queue view renders | | |
| 1.3 | Add at least 1 item via + Add (any section) | Any queue row | Button flips to ✓ Added | | |
| 1.4 | Draft Items → click **+ Add Note** | Draft Items tab | Modal opens | | |
| 1.5 | Add a note with **Category = Critical** | Modal (section = Engineering) | Note appears under Today | | |
| 1.6 | Click **Export Handover** | Bottom of Draft Items | Loading spinner → redirect to `/handover-export/{id}` | | |
| 1.7 | On the export page, click **Sign Handover** → draw → Confirm & Sign | IdentityStrip top-right | Toast "Handover signed — HOD notified for countersignature"; status pill flips to Pending Hod Signature | | |
| 1.8 | Logout. Login as **HOD** (`hod.test@alex-short.com`) | — | Dashboard loads | | |
| 1.9 | Navigate to same `/handover-export/{id}` | Use URL from step 1.6 | Page loads with status "Pending Hod Signature" | | |
| 1.10 | Click **Countersign Handover** → draw → Confirm & Sign | IdentityStrip | Toast "Handover countersigned — rotation complete", status flips to **Complete** | | |

**Record the export ID:** `______________________________________` (from URL bar after 1.6)

**Verify DB row state (from a second terminal):**

```bash
PGPASSWORD='@-Ei-9Pa.uENn6g' psql "postgresql://postgres@db.vzsohavtuotocgrfkfyd.supabase.co:5432/postgres?sslmode=require" \
  -c "SELECT id, review_status, user_signed_at IS NOT NULL AS outgoing_signed, hod_signed_at IS NOT NULL AS hod_signed, incoming_signed_at, signoff_complete FROM handover_exports WHERE yacht_id='85fe1119-b04c-41ac-80f1-829d23322598' ORDER BY created_at DESC LIMIT 3;"
```

| # | DB assertion | Expected | Y / N / ERR |
|---|--------------|----------|-------------|
| 1.11 | Newest row `review_status` | `complete` | |
| 1.12 | Newest row `outgoing_signed` | `t` | |
| 1.13 | Newest row `hod_signed` | `t` | |
| 1.14 | Newest row `incoming_signed_at` | `NULL` | |
| 1.15 | Newest row `signoff_complete` | `f` (two of three signed — not yet complete) | |

**Notes:**
```



```

---

## Scenario 2 — Dynamic 3-column signature block (visual)

Still logged in as HOD (or captain), navigate to `/handover-export/{export_id_from_1}`. Scroll to the signature block at the bottom of the white document.

| # | Check | How proved | Y / N / ERR |
|---|-------|-----------|-------------|
| 2.1 | Signature block renders **three columns** side by side | Visual DOM | |
| 2.2 | Column 1 header = **"Prepared By"** | Header text | |
| 2.3 | Column 2 header = **"Reviewed By"** | Header text | |
| 2.4 | Column 3 header = **"Acknowledged By"** | Header text | |
| 2.5 | Prepared column shows captain's signed name + timestamp + **SIGNED** badge | Visual | |
| 2.6 | Reviewed column shows HOD's signed name + timestamp + **SIGNED** badge | Visual | |
| 2.7 | Acknowledged column shows "Pending" (ghost/italic text) with NO timestamp | Visual | |
| 2.8 | Timestamps render in **monospace** (IBM Plex Mono) | Font inspector | |
| 2.9 | No horizontal scrollbar on the document container | Visual | |
| 2.10 | Signature block sits inside the white "paper" frame (no breakout) | Visual | |

**Known UI issue to record here:**
The handover-export microservice (`http://localhost:10010`) renders a Jinja HTML document from `/Users/celeste7/Documents/handover_export/templates/handover_report.html:615` which contains a **legacy 2-column sigblock** ("Officer on Watch" / "Head of Department"). Playwright shard-54 currently reports seeing this legacy block. The NEW React `SignatureBlock` is rendered inside the Next.js page, NOT in the microservice HTML blob. If both blocks appear on the page, log **where each one appears** (top/middle/bottom of the document) so the CEO can decide whether to deprecate the microservice template.

| # | Check | How proved | Y / N / ERR |
|---|-------|-----------|-------------|
| 2.11 | If legacy 2-col block present, record its location on page | Visual / DOM inspector | |
| 2.12 | If legacy 2-col block present, record exact text ("Officer on Watch" etc.) | Visual | |

**Notes:**
```



```

---

## Scenario 3 — Acknowledge button visibility matrix

Using the completed export from Scenario 1, log in as each role in sequence and record whether the **Acknowledge Handover** button is visible on `/handover-export/{id}`.

| # | Login as | Expected button visible? | Reason | Y / N / ERR |
|---|----------|-------------------------|--------|-------------|
| 3.1 | `captain.tenant@alex-short.com` (was outgoing signer) | **NOT visible** | Self-ack prevention — same user as `user_signed_by` | |
| 3.2 | `hod.test@alex-short.com` (countersigned) | **NOT visible** | Same user as `hod_signed_by` | |
| 3.3 | `crew.test@alex-short.com` (not a prior signer) | **Visible** | crew role, not a prior signer | |
| 3.4 | Any other chief_engineer / chief_officer account who did NOT sign | **Visible** | Role passes gate, not a prior signer | |
| 3.5 | `fleet-test-1775570624@celeste7.ai` (manager) | **Visible** (if login works — otherwise SKIP) | manager role, not a prior signer | |
| 3.6 | After Scenario 4 completes (someone else acknowledged) — log back in as captain | **NOT visible** | `incoming_signed_at` now populated | |

**Notes (manager account likely still broken — TENANT JWT vs MASTER expectation):**
```



```

---

## Scenario 4 — Acknowledge WITHOUT critical items — happy path

**Prerequisite:** Create a NEW complete export that has **NO critical items**. Repeat Scenario 1 steps 1.1–1.10 but in step 1.5 use **Category = Standard** (not Critical). Record this new export ID: `______________________________________`.

Log in as **crew** (`crew.test@alex-short.com`) and navigate to `/handover-export/{new_export_id}`.

| # | Step | Location | Expected | Y / N / ERR |
|---|------|----------|----------|-------------|
| 4.1 | Page loads | URL bar | Status pill "Complete", Acknowledge button visible | |
| 4.2 | Click **Acknowledge Handover** | IdentityStrip top-right | Canvas modal opens | |
| 4.3 | Modal does **NOT** show "I acknowledge critical items" checkbox | Modal body | (No export had no critical items) | |
| 4.4 | Draw signature | Canvas | Ink follows mouse | |
| 4.5 | Click **Confirm & Sign** | Primary button | Toast "Handover acknowledged" (or similar success copy); page reloads | |
| 4.6 | Acknowledged column flips to **SIGNED ✓** with crew's name + timestamp | Signature block | | |
| 4.7 | Acknowledge button disappears | IdentityStrip | Gone | |

**API verification (run from second terminal):**

```bash
# Capture crew token
CREW_TOKEN=$(curl -s -X POST "https://qvzmkaamzaqxpzbewjxe.supabase.co/auth/v1/token?grant_type=password" \
  -H "apikey: ${MASTER_SUPABASE_ANON_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"email":"crew.test@alex-short.com","password":"Password2!"}' \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])")

EXPORT_ID="<paste new export id from 4.0>"

# Fetch entity (should show incoming_signed_at populated post-UI-ack)
curl -s "http://localhost:8020/v1/entity/handover_export/$EXPORT_ID" \
  -H "Authorization: Bearer $CREW_TOKEN" | python3 -m json.tool | head -60
```

| # | API / DB assertion | Expected | Y / N / ERR |
|---|--------------------|----------|-------------|
| 4.8 | Entity response `incoming_user_id` | = crew UUID | |
| 4.9 | Entity response `incoming_user_name` | non-null | |
| 4.10 | Entity response `incoming_role` | `"crew"` | |
| 4.11 | Entity response `incoming_signed_at` | ISO timestamp | |
| 4.12 | Entity response `incoming_acknowledged_critical` | `true` (query string was always sent true) | |
| 4.13 | Entity response `signoff_complete` | `true` | |

```bash
# DB spot check
PGPASSWORD='@-Ei-9Pa.uENn6g' psql "postgresql://postgres@db.vzsohavtuotocgrfkfyd.supabase.co:5432/postgres?sslmode=require" \
  -c "SELECT incoming_user_id, incoming_signed_at, incoming_acknowledged_critical, signoff_complete FROM handover_exports WHERE id='$EXPORT_ID';"

# Ledger events for this export (expect >= 2 rows: actor + outgoing cascade, plus captain+manager rows)
PGPASSWORD='@-Ei-9Pa.uENn6g' psql "postgresql://postgres@db.vzsohavtuotocgrfkfyd.supabase.co:5432/postgres?sslmode=require" \
  -c "SELECT user_id, action, length(proof_hash) AS phlen, created_at FROM ledger_events WHERE entity_id='$EXPORT_ID' AND action='handover_acknowledged' ORDER BY created_at;"

# Audit log (actor row)
PGPASSWORD='@-Ei-9Pa.uENn6g' psql "postgresql://postgres@db.vzsohavtuotocgrfkfyd.supabase.co:5432/postgres?sslmode=require" \
  -c "SELECT actor_id, action, created_at FROM pms_audit_log WHERE entity_id='$EXPORT_ID' AND action='handover_acknowledged';"
```

| # | DB assertion | Expected | Y / N / ERR |
|---|--------------|----------|-------------|
| 4.14 | `handover_exports.incoming_user_id` = crew UUID | Match | |
| 4.15 | `handover_exports.incoming_signed_at` NOT NULL | Match | |
| 4.16 | `handover_exports.signoff_complete = true` | Match | |
| 4.17 | `ledger_events` rows with `action='handover_acknowledged'` ≥ 2 | Match | |
| 4.18 | Every ledger row has `length(proof_hash) = 64` (sha256 hex) | Match | |
| 4.19 | `pms_audit_log` has 1 row with `action='handover_acknowledged'`, `actor_id` = crew UUID | Match | |

**Notes:**
```



```

---

## Scenario 5 — Acknowledge WITH critical items — gate works

**Prerequisite:** The export from **Scenario 1** has a critical note (step 1.5) and is `review_status='complete' AND incoming_signed_at IS NULL`. Use that one. If Scenario 4 re-used it, seed a new critical export via Scenario 1 repeat.

Log in as **crew** (`crew.test@alex-short.com`), navigate to `/handover-export/{scenario_1_export_id}`.

| # | Step | Location | Expected | Y / N / ERR |
|---|------|----------|----------|-------------|
| 5.1 | Click **Acknowledge Handover** | IdentityStrip | Canvas modal opens | |
| 5.2 | Checkbox **"I acknowledge critical items"** is present | Modal body | Visible, label matches exactly | |
| 5.3 | Checkbox is **unchecked** by default | Modal body | Unchecked | |
| 5.4 | **Confirm & Sign** button is **DISABLED** | Primary button | Button greyed out | |
| 5.5 | Draw signature while unchecked | Canvas | Ink draws, Confirm still disabled | |
| 5.6 | Check the checkbox | Modal body | Checkbox state → checked | |
| 5.7 | Confirm button enables | Primary button | Active/clickable | |
| 5.8 | Uncheck again | Modal body | Confirm disables again | |
| 5.9 | Check + click **Confirm & Sign** | Primary button | Toast success, page reloads | |
| 5.10 | Acknowledged column → SIGNED ✓ with crew's name + timestamp | Signature block | Match | |

**DB check:**
```bash
PGPASSWORD='@-Ei-9Pa.uENn6g' psql "postgresql://postgres@db.vzsohavtuotocgrfkfyd.supabase.co:5432/postgres?sslmode=require" \
  -c "SELECT incoming_acknowledged_critical FROM handover_exports WHERE id='<scenario_1_export_id>';"
```

| # | DB assertion | Expected | Y / N / ERR |
|---|--------------|----------|-------------|
| 5.11 | `incoming_acknowledged_critical = true` | Match | |

**Notes:**
```



```

---

## Scenario 6 — Double-acknowledge is rejected

After a successful acknowledge (Scenarios 4 or 5), try to acknowledge the same export again — both via UI and direct API call.

**UI path:**

| # | Step | Expected | Y / N / ERR |
|---|------|----------|-------------|
| 6.1 | Refresh the page as crew | Acknowledge button GONE | |
| 6.2 | Logout → login as an OTHER chief_engineer / chief_officer role (not a prior signer) | Button GONE because `incoming_signed_at` populated | |

**Direct API call (bypasses UI gating):**

```bash
# Re-use CREW_TOKEN from Scenario 4
EXPORT_ID="<already-acknowledged export id>"

curl -i -X POST "http://localhost:8020/v1/actions/handover/$EXPORT_ID/sign/incoming?acknowledge_critical=true" \
  -H "Authorization: Bearer $CREW_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"signature":{"image_base64":"data:image/png;base64,iVBORw0KGgo=","signed_at":"2026-04-17T00:00:00Z","signer_name":"Crew Test","signer_id":"<crew uuid>"}}'
```

| # | API assertion | Expected | Y / N / ERR |
|---|---------------|----------|-------------|
| 6.3 | HTTP status | `409` | |
| 6.4 | Response body contains `"error":"Handover has already been acknowledged by incoming crew."` (or equivalent "already acknowledged" message) | Match | |
| 6.5 | DB `incoming_signed_at` unchanged (still the original timestamp) | Match | |

**Notes:**
```



```

---

## Scenario 7 — Wrong state is rejected

Create an export that has been **submitted** but NOT countersigned (i.e. `review_status='pending_hod_signature'`). Stop partway through Scenario 1 — do step 1.7 (captain signs) but DO NOT log in as HOD to countersign.

Record this partial export ID: `______________________________________`.

**UI check:**

| # | Step | Expected | Y / N / ERR |
|---|------|----------|-------------|
| 7.1 | Login as crew, navigate to partial export page | Acknowledge button NOT visible (export is not yet complete) | |
| 7.2 | Status pill reads **Pending Hod Signature** | Match | |

**Direct API call:**

```bash
curl -i -X POST "http://localhost:8020/v1/actions/handover/$PARTIAL_EXPORT_ID/sign/incoming?acknowledge_critical=true" \
  -H "Authorization: Bearer $CREW_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"signature":{"image_base64":"data:image/png;base64,iVBORw0KGgo=","signed_at":"2026-04-17T00:00:00Z","signer_name":"Crew Test","signer_id":"<crew uuid>"}}'
```

| # | API assertion | Expected | Y / N / ERR |
|---|---------------|----------|-------------|
| 7.3 | HTTP status | `409` | |
| 7.4 | Body names `review_status` AND `complete` in the error message | e.g. `"Handover must be in review_status=complete to be acknowledged"` | |
| 7.5 | DB row unchanged | `incoming_signed_at` still NULL | |

**Notes:**
```



```

---

## Scenario 8 — Role gate widening (Bug 1 regression gate)

Key claim of PR #642: **crew** can now call `/sign/incoming`. The old gate blocked crew with 403. This scenario is the regression gate for that fix.

```bash
# Completed export from Scenario 1 (or a fresh one seeded for this test)
curl -i -X POST "http://localhost:8020/v1/actions/handover/$EXPORT_ID/sign/incoming?acknowledge_critical=true" \
  -H "Authorization: Bearer $CREW_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"signature":{"image_base64":"data:image/png;base64,iVBORw0KGgo=","signed_at":"2026-04-17T00:00:00Z","signer_name":"Crew Test","signer_id":"<crew uuid>"}}'
```

| # | API assertion | Expected | Y / N / ERR |
|---|---------------|----------|-------------|
| 8.1 | HTTP status is **NOT 403** | Must be 200 OR a different real error (409 already-acked, 409 wrong-state) | |
| 8.2 | Response body does not mention `"role"` or `"forbidden"` | If 403 → Bug 1 regressed; file immediately | |

**Notes:**
```



```

---

## Scenario 9 — Ledger cascade

After a successful acknowledge (Scenarios 4 or 5), verify the cascade fan-out.

```bash
# Expected cascade recipients on yacht 85fe1119-b04c-41ac-80f1-829d23322598:
#   - the actor (the crew who acknowledged)
#   - the outgoing signer (captain)
#   - every user with role captain on the yacht
#   - every user with role manager on the yacht
PGPASSWORD='@-Ei-9Pa.uENn6g' psql "postgresql://postgres@db.vzsohavtuotocgrfkfyd.supabase.co:5432/postgres?sslmode=require" \
  -c "SELECT user_id, action, length(proof_hash) AS phlen, created_at
      FROM ledger_events
      WHERE entity_id='$EXPORT_ID' AND action='handover_acknowledged'
      ORDER BY created_at;"

# Cross-check expected recipient set
PGPASSWORD='@-Ei-9Pa.uENn6g' psql "postgresql://postgres@db.vzsohavtuotocgrfkfyd.supabase.co:5432/postgres?sslmode=require" \
  -c "SELECT user_id, role FROM auth_users_roles
      WHERE yacht_id='85fe1119-b04c-41ac-80f1-829d23322598'
      AND role IN ('captain','manager')
      ORDER BY role, user_id;"
```

| # | DB assertion | Expected | Y / N / ERR |
|---|--------------|----------|-------------|
| 9.1 | At least 2 `handover_acknowledged` rows for the export | Match | |
| 9.2 | One row has `user_id` = crew (actor) | Match | |
| 9.3 | One row has `user_id` = outgoing signer (captain who submitted) | Match | |
| 9.4 | All captains of the yacht have a row | Cross-check against `auth_users_roles` query | |
| 9.5 | All managers of the yacht have a row | Cross-check | |
| 9.6 | Every row has `length(proof_hash) = 64` hex chars | Match | |

**Notes:**
```



```

---

## Scenario 10 — Notification visibility (out-of-band)

After Scenarios 4 or 5, log back in as the outgoing signer (captain). Check the notification bell / Needs Attention panel.

| # | Check | Expected | Y / N / ERR |
|---|-------|----------|-------------|
| 10.1 | Notification bell shows a new entry | e.g. "Handover acknowledged by Crew Test" | |
| 10.2 | Clicking the notification lands on `/handover-export/{id}` | Navigation works | |

If the notification bell is NOT listening for `handover_acknowledged` action, mark as `PENDING-UI` and note it as a follow-up — this is not a test failure for this PR, just an integration gap to track.

**Notes:**
```



```

---

## Listen-for-this bugs

Concrete things to watch for as the CEO walks these scenarios. Log each one as it appears, not as a scenario failure.

| # | Thing to watch | Where / how it surfaces | Log here |
|---|---------------|------------------------|---------|
| B1 | Old export entries (pre-March data-gap) with `entity_url=null` on items → items won't be clickable | Any pre-March export in the list | Expected, documented limitation, not a regression |
| B2 | Legacy 2-column sigblock ("Officer on Watch" / "Head of Department") appearing alongside the new 3-col React block | On `/handover-export/{id}` — comes from microservice Jinja template `/Users/celeste7/Documents/handover_export/templates/handover_report.html:615` | Record WHERE on page + WHAT text |
| B3 | Signature block visually "breaking out" of the white-paper frame | Cosmetic only | Screenshot + note location |
| B4 | CHECK-constraint errors on archive teardown (`metadata` column missing) | API logs during test cleanup | Cosmetic, not blocking |
| B5 | Docker `.next/` cache trap — frontend changes not reflected | Still seeing old button text after rebuild | Fix: `rm -rf /Users/celeste7/Documents/Cloud_PMS-handover04/apps/web/.next && COMPOSE_PROJECT_NAME=handover04 docker compose build --no-cache web` |
| B6 | Broken fleet-manager test account (`fleet-test-1775570624@...`) | TENANT JWT vs MASTER expectation | SKIP any scenario that requires manager login |
| B7 | Browser console 4xx/5xx | DevTools Console / Network | Paste full error body |
| B8 | 5xx from `/v1/entity/handover_export/{id}` | Would break the UI load entirely | Log full response body + timestamp |

---

## Overall verdict

| Area | Result | Blocking? | Notes |
|------|--------|-----------|-------|
| Pre-flight (stack up) | | | |
| Scenario 1 — seed complete export | | | |
| Scenario 2 — 3-col signature block visual | | | |
| Scenario 3 — button visibility matrix | | | |
| Scenario 4 — happy path (no critical items) | | | |
| Scenario 5 — critical items gate | | | |
| Scenario 6 — double-ack rejected | | | |
| Scenario 7 — wrong state rejected | | | |
| Scenario 8 — role gate (Bug 1 regression) | | | |
| Scenario 9 — ledger cascade | | | |
| Scenario 10 — notification visibility | | | |

---

## All console errors (paste everything)

```



```

---

## Questions for HANDOVER01 / PR author

```
Q1:

Q2:

Q3:
```
