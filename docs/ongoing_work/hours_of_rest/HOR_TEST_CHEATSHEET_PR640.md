# Hours of Rest — PR #640 Test Cheat Sheet

**PR:** #640 `feat/hor-boil-the-ocean-20260417`
**Test env:** Local Docker — `http://localhost:3010` (web) / `http://localhost:8000` (API)
**TENANT DB:** `vzsohavtuotocgrfkfyd`
**Base for these tests:** PRs #567–#596 are all live on main. This sheet covers **only the new features shipped in PR #640**. For baseline sign-chain, role-gate, and UI scenarios see `HOR_TEST_CHEATSHEET.md` + `HOR_MANUAL_TEST_GUIDE.md`.

---

## Test credentials

| Role | Email | Password | User ID |
|------|-------|----------|---------|
| Crew | engineer.test@alex-short.com | Password2! | `4a66036f-899c-40c8-9b2a-598cee24a62f` |
| HOD (ETO) | eto.test@alex-short.com | Password2! | `81c239df-f8ef-4bba-9496-78bf8f46733c` |
| Captain | x@alex-short.com | Password2! | `a35cad0b-02ff-4287-b6e4-17c96fa6a424` |
| Fleet Manager | fleet-test-1775570624@celeste7.ai | Password2! | `f11f1247-b7bd-4017-bfe3-ebd3f8c9e871` |

**Yacht:** `85fe1119-b04c-41ac-80f1-829d23322598` (M/Y Test Vessel)

---

## Browser console setup

Open DevTools → Console **before** every scenario. Paste to intercept all API calls:

```javascript
const _origFetch = window.fetch;
window.fetch = async (...args) => {
  const r = await _origFetch(...args);
  if (args[0]?.includes?.('/actions/execute') || args[0]?.includes?.('/v1/')) {
    const clone = r.clone();
    clone.json().then(d => console.log('[API]', args[0], JSON.stringify(d)));
  }
  return r;
};
```

---

## What PR #640 delivered (new test surface)

| Feature | Source file | Handler |
|---------|------------|---------|
| 14h interval rule | `hours_of_rest_handlers.py:L76-L106` | `_compute_max_gap_hours` |
| 1h minimum period threshold | `hours_of_rest_handlers.py:L67-L73` | `_filter_qualifying_periods` |
| Rolling 24h window compliance | `hours_of_rest_handlers.py:L127-L228` | `_check_rolling_24h_compliance` |
| MLC exceptions workflow | `routes/hours_of_rest_routes.py` | `/exceptions/create`, `/exceptions/revoke`, `/exceptions` |
| Crew comment required on non-compliant entry | `hours_of_rest_handlers.py:L507-L515` | `upsert_hours_of_rest` |
| Forward scheduling preview | `routes/hor_compliance_routes.py` | `POST /v1/hours-of-rest/schedule/preview` |
| HOD self-completion guard | `hours_of_rest_handlers.py:L1133-L1157` | `sign_monthly_signoff` |

---

## Scenario 12 — Non-compliant entry requires crew comment

**Role:** Crew
**Path:** Log in → Hours of Rest → submit a day with < 10h rest
**New behaviour:** `upsert_hours_of_rest` with `is_daily_compliant=false` and no `crew_comment` → `VALIDATION_ERROR`. Must supply justification.

| Step | Expected | Pass/Fail | Notes |
|------|----------|-----------|-------|
| Submit day with 6h rest, no `crew_comment` | `success=false`, `error.code=VALIDATION_ERROR`, `requires_crew_comment=true` | | |
| Console shows error response | `[API] /api/v1/hours-of-rest/upsert {"success":false,"error":{"code":"VALIDATION_ERROR",...},"requires_crew_comment":true}` | | |
| Inline error visible in UI | Error rendered under the day cell — NOT silent revert | | |
| Retry same day WITH `crew_comment` | `success=true`, `is_daily_compliant=false`, `crew_comment` stored | | |
| DB row has comment | `SELECT crew_comment, is_daily_compliant FROM pms_hours_of_rest WHERE user_id='4a66036f' ORDER BY record_date DESC LIMIT 1` — column is non-null | | |

**To force a non-compliant day:** use a work period that covers > 14h of the 24h slot.
E.g. single period `00:00–16:00` → 16h work → only 8h rest → `is_daily_compliant=false`.

**Via action bus directly (for API wire-walk):**
```bash
# Step 1 — submit without comment (expect VALIDATION_ERROR)
curl -s -X POST http://localhost:8000/v1/actions/execute \
  -H "Authorization: Bearer $CREW_JWT" \
  -H "Content-Type: application/json" \
  -d '{"action":"upsert_hours_of_rest","context":{"yacht_id":"85fe1119-b04c-41ac-80f1-829d23322598"},
       "payload":{"yacht_id":"85fe1119-b04c-41ac-80f1-829d23322598",
                  "record_date":"2026-04-20",
                  "work_periods":[{"start":"00:00","end":"16:00"}]}}' | jq '.success,.error,.requires_crew_comment'

# Step 2 — retry with comment (expect success=true)
curl -s -X POST http://localhost:8000/v1/actions/execute \
  -H "Authorization: Bearer $CREW_JWT" \
  -H "Content-Type: application/json" \
  -d '{"action":"upsert_hours_of_rest","context":{"yacht_id":"85fe1119-b04c-41ac-80f1-829d23322598"},
       "payload":{"yacht_id":"85fe1119-b04c-41ac-80f1-829d23322598",
                  "record_date":"2026-04-20",
                  "work_periods":[{"start":"00:00","end":"16:00"}],
                  "crew_comment":"Engine emergency — 16h watch required"}}' | jq '.success,.data.is_daily_compliant'
```

**Expected responses:**
```
Step 1: success=false, error.code=VALIDATION_ERROR, requires_crew_comment=true
Step 2: success=true,  data.is_daily_compliant=false
```

**DB verification:**
```sql
SELECT record_date, total_work_hours, total_rest_hours, is_daily_compliant, crew_comment
FROM pms_hours_of_rest
WHERE user_id = '4a66036f-899c-40c8-9b2a-598cee24a62f'
  AND record_date = '2026-04-20';
-- Expect: work=16, rest=8, is_daily_compliant=false, crew_comment='Engine emergency...'
```

**Fail reasons:**
| Symptom | Why | Fix location |
|---------|-----|-------------|
| No `requires_crew_comment` hint in response | Handler not returning hint field | `hours_of_rest_handlers.py:L507-L515` |
| Non-compliant entry accepted without comment | Guard not firing | `hours_of_rest_handlers.py` — check `is_daily_compliant` gate |
| Comment stored as null | `crew_comment` not passed through route model | `hours_of_rest_routes.py:L129` — `UpdateHoursRequest` |

---

## Scenario 13 — 14h interval rule catches violations

**Role:** Crew (or API wire-walk)
**Path:** Submit a day with a single work block > 14h (no rest gap inside the block)
**New behaviour:** `mlc_interval_check.violates_14h_rule=true` in upsert response when longest gap between consecutive rest periods ≤ 14h.

**Clarification:** MLC Article A2.3 para 6 — rest must not be divided into more than 2 periods, ONE of which must be ≥ 6h. The 14h rule says no rest gap (gap between rest start and next rest start, spanning a work block) should exceed 14h.

Test: submit a work period of `06:00–23:00` (17h work block) on a new date. Rest periods are only `00:00–06:00` (6h) and `23:00–24:00` (1h).

```bash
curl -s -X POST http://localhost:8000/v1/actions/execute \
  -H "Authorization: Bearer $CREW_JWT" \
  -H "Content-Type: application/json" \
  -d '{"action":"upsert_hours_of_rest","context":{"yacht_id":"85fe1119-b04c-41ac-80f1-829d23322598"},
       "payload":{"yacht_id":"85fe1119-b04c-41ac-80f1-829d23322598",
                  "record_date":"2026-04-21",
                  "work_periods":[{"start":"06:00","end":"23:00"}],
                  "crew_comment":"Test 14h interval rule"}}' \
  | jq '.success, .data.mlc_interval_check'
```

| Step | Expected | Pass/Fail | Notes |
|------|----------|-----------|-------|
| Upsert with 17h work block | `success=true` (with comment), `mlc_interval_check.violates_14h_rule=true`, `mlc_interval_check.max_gap_hours≈17.0` | | |
| `is_daily_compliant` | `false` — 7h total rest < 10h minimum | | |
| Submit compliant day (e.g. 4h work) | `mlc_interval_check.violates_14h_rule=false`, `max_gap_hours≤14` | | |

**Expected response shape:**
```json
{
  "success": true,
  "data": {
    "is_daily_compliant": false,
    "mlc_interval_check": {
      "max_gap_hours": 17.0,
      "violates_14h_rule": true
    }
  }
}
```

**Fail reason:** `mlc_interval_check` absent from response → `_compute_max_gap_hours` not called or not returned — check `hours_of_rest_handlers.py:L76-L106`.

---

## Scenario 14 — 1h minimum period filter

**Role:** Crew (API wire-walk)
**Purpose:** Verify that rest periods < 60 min do NOT count toward MLC `total_rest_hours`.

**Setup:** Submit a day with many short rest slivers — e.g. 11 × 55-minute rest periods alternating with work. Without the filter these add up to ~10h and the day would appear compliant. With the filter, they are all excluded → 0 qualifying rest hours → non-compliant.

```bash
# 11 × (55 min rest + 5 min work) ≈ 11h of short-period "rest"
# With _filter_qualifying_periods: all 55-min periods dropped → 0h rest → VIOLATION
curl -s -X POST http://localhost:8000/v1/actions/execute \
  -H "Authorization: Bearer $CREW_JWT" \
  -H "Content-Type: application/json" \
  -d '{"action":"upsert_hours_of_rest","context":{"yacht_id":"85fe1119-b04c-41ac-80f1-829d23322598"},
       "payload":{"yacht_id":"85fe1119-b04c-41ac-80f1-829d23322598",
                  "record_date":"2026-04-22",
                  "work_periods":[
                    {"start":"00:55","end":"01:00"},{"start":"01:55","end":"02:00"},
                    {"start":"02:55","end":"03:00"},{"start":"03:55","end":"04:00"},
                    {"start":"04:55","end":"05:00"},{"start":"05:55","end":"06:00"},
                    {"start":"06:55","end":"07:00"},{"start":"07:55","end":"08:00"},
                    {"start":"08:55","end":"09:00"},{"start":"09:55","end":"10:00"},
                    {"start":"10:55","end":"11:00"}
                  ],
                  "crew_comment":"Test 1h minimum period filter"}}' \
  | jq '.success, .data.total_rest_hours, .data.is_daily_compliant'
```

| Step | Expected | Pass/Fail | Notes |
|------|----------|-----------|-------|
| 11 × 55-min rest periods | `total_rest_hours` reflects only qualifying (≥60 min) periods | | If filter working, qualifying rest = 0 or very low → `is_daily_compliant=false` |
| Opposite: submit 2 × 5h rest periods | `total_rest_hours=10.0`, `is_daily_compliant=true` (both periods ≥60 min) | | Control test to confirm ≥1h periods DO count |

**Fail reason:** `total_rest_hours` equals the sum of ALL periods (no filtering) → `_filter_qualifying_periods` not applied before sum — check `hours_of_rest_handlers.py:L67-L73`.

---

## Scenario 15 — Rolling 24h window check

**Role:** Crew
**Purpose:** Verify `rolling_24h_check` block in upsert response reflects true sliding-window compliance, not just single-day boundary.

**Key architectural point:** The `_check_rolling_24h_compliance` function slides a 24h window in 30-min increments across the current day + previous day. A crew member who sleeps 14h at night then works all day can be non-compliant within a rolling window even if each isolated calendar day shows ≥10h rest.

| Step | Expected | Pass/Fail | Notes |
|------|----------|-----------|-------|
| Upsert any valid day | Response includes `rolling_24h_check` block | | Key: field must be present on every upsert |
| `rolling_24h_check.rolling_24h_rest_min` | Integer, minutes of minimum rest in any 24h window | | |
| `rolling_24h_check.is_rolling_compliant` | `true` if min rest ≥ 600 min (10h) across all windows | | |
| `rolling_24h_check.prev_day_available` | `true` if previous day record exists in DB | | If `false`, window only covers current day |
| Submit a day after a very heavy previous day | `is_rolling_compliant` may differ from `is_daily_compliant` | | This is the edge case the rolling window exists for |

**Expected response shape:**
```json
{
  "data": {
    "rolling_24h_check": {
      "rolling_24h_rest_min": 480,
      "is_rolling_compliant": false,
      "prev_day_available": true
    }
  }
}
```

**Direct API check (any upsert — inspect the response):**
```bash
# After any upsert from Scenario 12 or 13, look at the full response:
# The rolling_24h_check block must be present.
# If absent → _check_rolling_24h_compliance not called from upsert path.
```

**Fail reason:** `rolling_24h_check` absent → function not called in upsert — check `hours_of_rest_handlers.py:L127-L228`.

---

## Scenario 16 — MLC exceptions workflow

**Role:** Captain or Manager only (create/revoke). Any authenticated role (list).
**Endpoints:**
- `POST /v1/hours-of-rest/exceptions/create`
- `POST /v1/hours-of-rest/exceptions/revoke`
- `GET /v1/hours-of-rest/exceptions`

**Note:** Backend-only. No UI panel built (known gap in delivery manifest). Test via curl only.

### 16a — List active exceptions (no exceptions yet)

```bash
curl -s "http://localhost:8000/v1/hours-of-rest/exceptions?yacht_id=85fe1119-b04c-41ac-80f1-829d23322598" \
  -H "Authorization: Bearer $CAPTAIN_JWT" | jq '.success, (.data.exceptions | length)'
# Expect: success=true, length=0 (assuming clean state)
```

### 16b — Create a `three_rest_periods` exception (captain only)

MLC basis: Article A2.3 para 13 — allows 3 rest periods instead of 2 in special circumstances.

```bash
curl -s -X POST "http://localhost:8000/v1/hours-of-rest/exceptions/create" \
  -H "Authorization: Bearer $CAPTAIN_JWT" \
  -H "Content-Type: application/json" \
  -d '{"yacht_id":"85fe1119-b04c-41ac-80f1-829d23322598",
       "exception_type":"three_rest_periods",
       "reason":"Heavy weather passage — 3 watch rotations required",
       "start_date":"2026-04-20",
       "end_date":"2026-04-23"}' | jq '.success, .data.exception.id, .data.exception.exception_type'
```

| Step | Expected | Pass/Fail | Notes |
|------|----------|-----------|-------|
| Create `three_rest_periods` | `success=true`, new exception ID returned | | |
| Row in `pms_hor_exceptions` | `SELECT id, exception_type, is_active FROM pms_hor_exceptions WHERE yacht_id='85fe1119...'` | | |
| Crew role tries to create | `FORBIDDEN` — captain/manager only | | |
| Create `reduced_77_to_70` with duration > 14 days | `VALIDATION_ERROR` — MLC caps this type at 14 days | | |

### 16c — Create a `reduced_77_to_70` exception (within 14-day limit)

```bash
curl -s -X POST "http://localhost:8000/v1/hours-of-rest/exceptions/create" \
  -H "Authorization: Bearer $CAPTAIN_JWT" \
  -H "Content-Type: application/json" \
  -d '{"yacht_id":"85fe1119-b04c-41ac-80f1-829d23322598",
       "exception_type":"reduced_77_to_70",
       "reason":"Port entry work schedule",
       "start_date":"2026-04-20",
       "end_date":"2026-04-27"}' | jq '.success, .data.exception.exception_type'
# Duration = 8 days — within 14-day MLC limit
```

### 16d — Compliance wiring: `three_rest_periods` relaxes rest_period_count guard

Submit a day with 3 separate rest periods while the `three_rest_periods` exception is active. Normally the MLC compliance engine enforces max 2 rest periods. With the exception active, 3 periods should not cause a violation on THAT ground.

```bash
curl -s -X POST http://localhost:8000/v1/actions/execute \
  -H "Authorization: Bearer $CREW_JWT" \
  -H "Content-Type: application/json" \
  -d '{"action":"upsert_hours_of_rest","context":{"yacht_id":"85fe1119-b04c-41ac-80f1-829d23322598"},
       "payload":{"yacht_id":"85fe1119-b04c-41ac-80f1-829d23322598",
                  "record_date":"2026-04-21",
                  "work_periods":[
                    {"start":"00:00","end":"03:00"},
                    {"start":"07:00","end":"09:00"},
                    {"start":"15:00","end":"18:00"}
                  ]}}' | jq '.success, .data.is_daily_compliant'
```

| Step | Expected | Pass/Fail | Notes |
|------|----------|-----------|-------|
| 3-period day without active exception | Compliance check considers period count | | Check if `rest_period_count > 2` triggers a violation in response |
| 3-period day WITH active `three_rest_periods` exception | Period count relaxed — exception correctly applied | | `authorised_exception_id` should appear on the row |

### 16e — Revoke exception

```bash
curl -s -X POST "http://localhost:8000/v1/hours-of-rest/exceptions/revoke" \
  -H "Authorization: Bearer $CAPTAIN_JWT" \
  -H "Content-Type: application/json" \
  -d '{"yacht_id":"85fe1119-b04c-41ac-80f1-829d23322598",
       "exception_id":"<UUID from 16b>"}' | jq '.success'
# Expect: success=true, exception is_active=false
```

**DB verification:**
```sql
SELECT id, exception_type, is_active, revoked_at, revoked_by
FROM pms_hor_exceptions
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
ORDER BY created_at DESC LIMIT 5;
```

**Fail reasons:**
| Symptom | Why | Fix location |
|---------|-----|-------------|
| 404 on `/exceptions/create` | Route not registered | `hours_of_rest_routes.py` — check catch-all proxy registration |
| `reduced_77_to_70` creation succeeds with 20-day span | Duration CHECK not enforced | `hours_of_rest_handlers.py` — exception creation validation |
| Exception does not appear on upsert response | `get_active_exception_for_day()` not wired into upsert path | `hours_of_rest_handlers.py` — upsert calls `get_active_exception_for_day` |

---

## Scenario 17 — Forward scheduling preview

**Endpoint:** `POST /v1/hours-of-rest/schedule/preview`
**Role:** Any authenticated
**Purpose:** Zero-DB-write compliance preview for up to 7 days. Planners can check if a proposed schedule is MLC compliant before committing.

```bash
curl -s -X POST "http://localhost:8000/v1/hours-of-rest/schedule/preview" \
  -H "Authorization: Bearer $CREW_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "entries": [
      {"record_date":"2026-05-01","work_periods":[{"start":"08:00","end":"18:00"}]},
      {"record_date":"2026-05-02","work_periods":[{"start":"06:00","end":"20:00"}]},
      {"record_date":"2026-05-03","work_periods":[{"start":"00:00","end":"20:00"}]},
      {"record_date":"2026-05-04","work_periods":[]},
      {"record_date":"2026-05-05","work_periods":[{"start":"08:00","end":"18:00"}]},
      {"record_date":"2026-05-06","work_periods":[{"start":"08:00","end":"18:00"}]},
      {"record_date":"2026-05-07","work_periods":[{"start":"08:00","end":"18:00"}]}
    ],
    "week_start":"2026-05-01"
  }' | jq '.preview_only, .summary, (.days[] | {date:.record_date, compliant:.is_daily_compliant})'
```

| Step | Expected | Pass/Fail | Notes |
|------|----------|-----------|-------|
| `preview_only: true` in every response | MANDATORY — confirms no DB writes | | |
| Per-day analysis returned | `days` array with `is_daily_compliant`, `total_rest_hours`, `mlc_interval_check` per entry | | |
| Weekly summary | `week_rest`, `ok`, `violations_count` | | |
| Day 3 (20h work) | `is_daily_compliant=false`, `mlc_interval_check.violates_14h_rule=true` | | |
| Day 4 (rest day, no work) | `total_rest_hours=24`, `is_daily_compliant=true` | | |
| Submit > 7 entries | `VALIDATION_ERROR` — max 7 per MLC weekly window | | |
| DB unchanged after call | `SELECT COUNT(*) FROM pms_hours_of_rest WHERE record_date BETWEEN '2026-05-01' AND '2026-05-07'` — count unchanged | | **Critical** — must be zero new rows |
| Any role (crew, HOD, captain, fleet) can call | No `FORBIDDEN` | | Available to all authenticated roles |

**Expected shape:**
```json
{
  "preview_only": true,
  "days": [
    {"record_date":"2026-05-01","is_daily_compliant":true,"total_rest_hours":14.0,
     "mlc_interval_check":{"max_gap_hours":10.0,"violates_14h_rule":false}},
    ...
  ],
  "summary": {"week_rest": 98.0, "ok": false, "violations_count": 1}
}
```

**Fail reasons:**
| Symptom | Why | Fix location |
|---------|-----|-------------|
| 404 | Route not registered | `hor_compliance_routes.py` end of file — check `@router.post("/schedule/preview")` |
| `preview_only` absent or `false` | Handler not setting flag | `hor_compliance_routes.py` — preview handler |
| DB rows created | Preview not isolated from write path | `hor_compliance_routes.py` — must NOT call `upsert_hours_of_rest` handler |
| No `mlc_interval_check` per day | Compliance engine not invoked on preview entries | `hor_compliance_routes.py` — full engine must run on in-memory periods |

---

## Scenario 18 — HOD self-completion guard

**Role:** Captain (or any role that is both crew-signer and HOD-signer on the same signoff)
**New behaviour:** If `crew_signed_by == request JWT sub` AND the request tries `signature_level=hod`, the handler returns `FORBIDDEN`.

**Setup:** Create a fresh signoff for a month that doesn't exist yet. Use captain as crew-signer (captain can sign at crew level for their own record).

```bash
# Step 1: Create fresh signoff (captain for a past month with no existing signoff)
curl -s -X POST http://localhost:8000/v1/actions/execute \
  -H "Authorization: Bearer $CAPTAIN_JWT" \
  -H "Content-Type: application/json" \
  -d '{"action":"create_monthly_signoff","context":{"yacht_id":"85fe1119-b04c-41ac-80f1-829d23322598"},
       "payload":{"yacht_id":"85fe1119-b04c-41ac-80f1-829d23322598",
                  "user_id":"a35cad0b-02ff-4287-b6e4-17c96fa6a424",
                  "month":"2025-08","department":"deck"}}' | jq '.success, .data.signoff.id'
# Capture the signoff ID

# Step 2: Captain crew-signs own signoff
curl -s -X POST http://localhost:8000/v1/actions/execute \
  -H "Authorization: Bearer $CAPTAIN_JWT" \
  -H "Content-Type: application/json" \
  -d '{"action":"sign_monthly_signoff","context":{"yacht_id":"85fe1119-b04c-41ac-80f1-829d23322598"},
       "payload":{"signoff_id":"<ID from Step 1>","signature_level":"crew",
                  "signature_data":{"name":"Captain Test","declaration":"I confirm this record.","timestamp":"2026-04-18T00:00:00Z"}}}' \
  | jq '.success, .data.new_status'
# Expect: success=true, new_status=crew_signed

# Step 3: SAME captain tries HOD sign → MUST FAIL
curl -s -X POST http://localhost:8000/v1/actions/execute \
  -H "Authorization: Bearer $CAPTAIN_JWT" \
  -H "Content-Type: application/json" \
  -d '{"action":"sign_monthly_signoff","context":{"yacht_id":"85fe1119-b04c-41ac-80f1-829d23322598"},
       "payload":{"signoff_id":"<ID from Step 1>","signature_level":"hod",
                  "signature_data":{"name":"Captain Test","declaration":"I confirm this record.","timestamp":"2026-04-18T00:00:00Z"}}}' \
  | jq '.success, .error'
# MUST return: success=false, error.code=FORBIDDEN
```

| Step | Expected | Pass/Fail | Notes |
|------|----------|-----------|-------|
| Create fresh signoff (captain) | `success=true`, status=`draft` | | Use month `2025-08` or any clean month |
| Captain crew-signs own signoff | `success=true`, status=`crew_signed`, `crew_signed_by=a35cad0b` | | **Critical prerequisite** — guard only fires when `crew_signed_by` is set |
| Same captain HOD-sign attempt | `success=false`, `error.code` ∈ `{FORBIDDEN, VALIDATION_ERROR, SELF_SIGN_FORBIDDEN}` | | |
| Error message mentions self-completion | e.g. `"Cannot countersign as HOD — you signed this record at crew level"` | | Confirms the correct guard (not the old HOD-before-crew guard) |
| Different HOD signs same signoff | `success=true`, status=`hod_signed` | | Control: proves signoff is not stuck |

**Fail reasons:**
| Symptom | Why | Fix location |
|---------|-----|-------------|
| HOD sign succeeds when `crew_signed_by == jwt.sub` | Guard not firing | `hours_of_rest_handlers.py:L1133-L1157` |
| Guard fires even when `crew_signed_by` is null | Over-broad guard condition | Same — check guard only fires post-crew-sign |
| `FORBIDDEN` code on Step 2 (crew-sign itself blocked) | Guard mis-applied to crew sign | Logic error — guard must only block `hod` level |

**Cleanup after test:**
```sql
DELETE FROM pms_hor_monthly_signoffs
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND month = '2025-08';
```

---

## Quick Y/N checklist — PR #640 only

Mark each with Y/N. Any N: see fail reasons in the scenario above.

```
[ ] S12a: Non-compliant upsert WITHOUT crew_comment → success=false, VALIDATION_ERROR, requires_crew_comment=true
[ ] S12b: Non-compliant upsert WITH crew_comment → success=true, crew_comment stored in DB
[ ] S12c: Compliant upsert (≥10h rest) → no crew_comment required, success=true
[ ] S12d: Error renders inline in UI — not a silent revert (browser only)

[ ] S13:  17h work block → mlc_interval_check.violates_14h_rule=true, max_gap_hours≈17.0
[ ] S13b: 4h work block → mlc_interval_check.violates_14h_rule=false

[ ] S14:  11 × 55-min rest periods → total_rest_hours does NOT count them (< 10h → non-compliant)
[ ] S14b: 2 × 5h rest periods → total_rest_hours=10.0, is_daily_compliant=true

[ ] S15:  rolling_24h_check block present on every upsert response
[ ] S15b: rolling_24h_check.rolling_24h_rest_min is an integer (minutes)
[ ] S15c: rolling_24h_check.is_rolling_compliant reflects true sliding window

[ ] S16a: GET /exceptions returns empty array (clean state)
[ ] S16b: Captain creates three_rest_periods exception → success=true, ID returned
[ ] S16c: Captain creates reduced_77_to_70 (≤14 days) → success=true
[ ] S16d: reduced_77_to_70 with 20-day span → VALIDATION_ERROR
[ ] S16e: Crew role tries create → FORBIDDEN
[ ] S16f: Revoke exception → is_active=false in DB
[ ] S16g: three_rest_periods exception wired into upsert path (authorised_exception_id on row)

[ ] S17a: preview_only=true in every preview response
[ ] S17b: Per-day compliance analysis returned (days array)
[ ] S17c: Zero DB rows written (SELECT confirms no new pms_hours_of_rest rows)
[ ] S17d: > 7 entries → VALIDATION_ERROR
[ ] S17e: All roles (crew/HOD/captain/fleet) can call — no FORBIDDEN
[ ] S17f: Day with 20h work → is_daily_compliant=false + violates_14h_rule=true in preview

[ ] S18a: Captain crew-signs own signoff → success=true, crew_signed
[ ] S18b: Same captain HOD-signs → success=false, FORBIDDEN (self-completion guard)
[ ] S18c: Different HOD signs same signoff → success=true, hod_signed (not stuck)
```

---

## DB quick-checks

```sql
-- Verify crew_comment column exists
\d pms_hours_of_rest | grep crew_comment

-- Verify pms_hor_exceptions table exists
\d pms_hor_exceptions

-- Verify authorised_exception_id FK on pms_hours_of_rest
SELECT column_name, data_type FROM information_schema.columns
WHERE table_name='pms_hours_of_rest' AND column_name='authorised_exception_id';

-- Verify rolling_7day_rest_hours on dash_crew_hours_compliance
SELECT column_name FROM information_schema.columns
WHERE table_name='dash_crew_hours_compliance' AND column_name='rolling_7day_rest_hours';
```

---

## Mint JWTs for curl testing (Docker local)

The Docker API validates TENANT JWTs. Get real tokens via login:

```bash
# Get CREW JWT
CREW_JWT=$(curl -s -X POST "https://vzsohavtuotocgrfkfyd.supabase.co/auth/v1/token?grant_type=password" \
  -H "apikey: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM1OTI4NzUsImV4cCI6MjA3OTE2ODg3NX0.JhJLvLSfLD3OtPDxTgHqgF8dNaZk8ius62jKN68E4WE" \
  -H "Content-Type: application/json" \
  -d '{"email":"engineer.test@alex-short.com","password":"Password2!"}' \
  | jq -r '.access_token')

# Get CAPTAIN JWT
CAPTAIN_JWT=$(curl -s -X POST "https://vzsohavtuotocgrfkfyd.supabase.co/auth/v1/token?grant_type=password" \
  -H "apikey: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM1OTI4NzUsImV4cCI6MjA3OTE2ODg3NX0.JhJLvLSfLD3OtPDxTgHqgF8dNaZk8ius62jKN68E4WE" \
  -H "Content-Type: application/json" \
  -d '{"email":"x@alex-short.com","password":"Password2!"}' \
  | jq -r '.access_token')

echo "CREW: ${CREW_JWT:0:30}..."
echo "CAPTAIN: ${CAPTAIN_JWT:0:30}..."
```

---

## State left by these tests (clean up after)

| Table | Filter | Created by |
|-------|--------|-----------|
| `pms_hours_of_rest` | `record_date IN ('2026-04-20','2026-04-21','2026-04-22')` AND `user_id='4a66036f'` | S12, S13, S14 |
| `pms_hor_exceptions` | `yacht_id='85fe1119...'` | S16b, S16c |
| `pms_hor_monthly_signoffs` | `month='2025-08'` AND `yacht_id='85fe1119...'` | S18 |

```sql
-- Cleanup after testing
DELETE FROM pms_hours_of_rest
WHERE user_id = '4a66036f-899c-40c8-9b2a-598cee24a62f'
  AND record_date IN ('2026-04-20','2026-04-21','2026-04-22');

DELETE FROM pms_hor_exceptions
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598';

DELETE FROM pms_hor_monthly_signoffs
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND month = '2025-08';
```

---

## Known gaps (not testable yet — backend complete, no UI)

| Gap | Why untestable | When |
|-----|---------------|------|
| Exceptions UI panel | Frontend panel not built | Next HoR sprint |
| Forward scheduling UI | Endpoint live; no UI component | Next HoR sprint |
| Preview + exception interaction | Needs both UI panels | After above |

---

*Mark Y/N inline. Paste API responses under each step. Any N = file a bug, note the handler and line.*
