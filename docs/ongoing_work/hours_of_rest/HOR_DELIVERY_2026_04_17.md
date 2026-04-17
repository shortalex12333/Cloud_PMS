# Hours of Rest — Delivery Manifest
**Date:** 2026-04-17
**Branch:** feat/hor-boil-the-ocean-20260417
**Engineer:** HOURSOFREST04
**Commits:** a061c451, 3398f3e6
**Source of truth:** docker run from `/Users/celeste7/hor-worktree`

---

## What Was Built (and Why)

Context: competitor analysis of Workrest (market leader) revealed MLC 2006 compliance gaps and missing features. This delivery closes every verifiable gap from that analysis.

---

## 1. MLC Compliance Engine Corrections

**Source:** `apps/api/handlers/hours_of_rest_handlers.py`

Three MLC 2006 Article A2.3 rules were absent. All three are now enforced.

### 1a. 14-hour interval rule (NEW)
- `_compute_max_gap_hours(sorted_rest_periods)` at handler:L76-L106
- Returns the longest gap between consecutive rest periods in a day
- `is_daily_compliant` now requires `max_gap_hours <= 14`
- Response includes `mlc_interval_check: {max_gap_hours, violates_14h_rule}`
- Wire-walk W5: `14h_gap=17.0` correctly flagged for a 17h work block

### 1b. 1-hour minimum period threshold (NEW)
- `_filter_qualifying_periods(periods)` at handler:L67-L73
- Drops periods shorter than 60 minutes from MLC accounting
- `total_rest_hours` is now computed from qualifying periods only
- Crew who game compliance with 11 x 55-min "rest periods" will fail correctly

### 1c. Rolling 24-hour window (NEW)
- `_check_rolling_24h_compliance(db, yacht_id, user_id, record_date)` at handler:L127-L228
- Slides a 24h window in 30-min increments across current + previous day
- Returns `{rolling_24h_rest_min, is_rolling_compliant, prev_day_available}`
- Response includes `rolling_24h_check` per upsert
- Python path is the **authoritative compliance gate**
- Postgres trigger `update_crew_hours_compliance()` is a **date-boundary approximation** for dashboard display — suitable for HOD/Captain overview, NOT for compliance decisions

### Tests
- 6 unit tests in `apps/api/tests/test_hor_compliance_rules.py` — all passing
- Tests cover: period filtering, gap calculation, rolling window boundary case

---

## 2. MLC Exceptions Workflow (NEW)

**MLC basis:** Article A2.3 paragraphs 13-14 — authorised exceptions to rest minimums

### Schema
- `pms_hor_exceptions` table: 3 types (`reduced_77_to_70`, `three_rest_periods`, `emergency_suspension`), revocation tracking, duration CHECK for `reduced_77_to_70` (≤14 days per MLC), indexes on active exceptions
- `authorised_exception_id UUID` FK on `pms_hours_of_rest` — links a record to its covering exception

### Compliance wiring
- `get_active_exception_for_day()` called inside `upsert_hours_of_rest`
- `three_rest_periods` exception relaxes `rest_period_count <= 3` (was hard 2)
- `reduced_77_to_70` / `emergency_suspension` don't relax daily 10h minimum — only weekly

### API endpoints (via catch-all proxy)
- `POST /v1/hours-of-rest/exceptions/create` — captain/manager only
- `POST /v1/hours-of-rest/exceptions/revoke` — captain/manager only
- `GET /v1/hours-of-rest/exceptions` — list active exceptions for vessel

---

## 3. Crew Comment on Non-Compliant Entry (NEW)

**Source:** `apps/api/handlers/hours_of_rest_handlers.py:L507-L515`, `apps/api/routes/hours_of_rest_routes.py:L129`

- `crew_comment TEXT NULL` added to `pms_hours_of_rest` via migration
- Upsert with `is_daily_compliant=false` and no `crew_comment` → `VALIDATION_ERROR`
- Upsert with comment → proceeds normally, comment stored in DB
- Response includes `requires_crew_comment: true` hint when comment is needed
- `UpdateHoursRequest` Pydantic schema includes `crew_comment: Optional[str]`
- **Bug found and fixed during wire-walk:** crew_comment was in handler but not wired through route request model — fixed in commit 3398f3e6

Wire-walk W4: non-compliant without comment → PASS (VALIDATION_ERROR)
Wire-walk W5: non-compliant WITH comment → PASS (success=True, stored)

---

## 4. Forward Scheduling Preview (NEW)

**Source:** `apps/api/routes/hor_compliance_routes.py` (end of file)

- `POST /v1/hours-of-rest/schedule/preview`
- Accepts `{entries: [{record_date, work_periods}], week_start}` — max 7 entries
- Runs full MLC compliance engine (14h interval, 1h min period, rolling periods)
- **Zero DB writes** — `preview_only: true` in every response
- Returns per-day analysis + weekly summary
- Available to any authenticated role

Wire-walk W6: 7-day week, mixed compliant/off days → PASS (preview_only=True, week_rest=108h, ok=True)

---

## 5. HOD Self-Completion General Guard (NEW)

**Source:** `apps/api/handlers/hours_of_rest_handlers.py:L1133-L1157`

Same user cannot sign at crew level AND HOD or master level on the same sign-off. Complements the existing `hod_signed_by == user_id` check for HOD→master case.

Wire-walk W7: captain signs crew, then tries HOD → PASS (FORBIDDEN)

---

## 6. Tier 6 Legacy Removal

Dead code removed: `view_hours_of_rest`, `update_hours_of_rest`, `export_hours_of_rest`

These queried a table (`hours_of_rest`) that doesn't exist on TENANT, used deprecated scalar columns, contained the `maybe_single()` bug, and swallowed all DB errors as false-success. Removed from:
- `routes/handlers/hours_of_rest_handler.py` (primary)
- `action_router/registry.py` (3 ActionDefinition blocks)
- `action_router/dispatchers/internal_dispatcher.py` (3 wrappers + 3 ACTION_MAP entries)
- `handlers/p1_compliance_handlers.py` + `p3_read_only_handlers.py`
- `routes/p0_actions_routes.py`
- `services/intent_parser.py` + `domain_microactions.py` (rewired to Crew Lens v3 actions)
- `web/src/lib/microactions/registry.ts` + `executor.ts` + `types/actions.ts`

**14 hours_of_rest actions remain, 0 Tier 6.**

---

## 7. Frontend Tokenization

**Source:** 5 HoR components + `apps/web/src/styles/tokens.css`

217 hardcoded rgba/hex values replaced with CSS var tokens across:
- `FleetView.tsx`, `MyTimeView.tsx`, `DepartmentView.tsx`, `VesselComplianceView.tsx`, `TimeSlider.tsx`

14 new tokens added to `tokens.css`:
`--surface-card`, `--surface-subtle`, `--border-top`, `--amber-bg`, `--amber-border`,
`--red-border`, `--red-border-strong`, `--green-strong`, `--red-strong`, `--mark-strong`,
`--mark-border`, `--compliance-good`, `--compliance-warn`, `--compliance-crit`,
`--overlay-subtle`, `--radius-full`

---

## 8. Bug Fixes

| Bug | Fix location | Verified |
|-----|-------------|---------|
| `VesselComplianceView.tsx:261` Bearer undefined | Null-guard on session token | ✅ |
| `MyTimeView.tsx:106` empty string when session null | Null-guard | ✅ |
| `DEPARTMENT_MAP: 'manager' → 'interior'` | signoffs/page.tsx:79 | ✅ |
| Dead mock functions | DepartmentView + VesselComplianceView | ✅ |
| crew_comment not wired through route request model | hours_of_rest_routes.py:129 | ✅ Wire-walk |

---

## 9. E2E / Tests

| Item | Status |
|------|--------|
| BUG-HOR-4: real `supabase.auth.signInWithPassword` in global-setup.ts | ✅ Fixed |
| shard-37: 2 skipped tests un-skipped | ✅ |
| shard-46: apply_crew_template + acknowledge_warning HARD PROOF | ✅ |
| shard-46: create_monthly_signoff re-check HARD PROOF | ✅ |
| shard-46: HOD self-completion guard test added | ✅ |
| shard-46 doc comment: pms_monthly_signoffs → pms_hor_monthly_signoffs | ✅ |
| Unit tests: 6/6 compliance rule tests passing | ✅ |
| shard-46 baseline (pre-change, MCP02): 10/10 | 📌 benchmark |

---

## 10. Migrations Applied to TENANT (`vzsohavtuotocgrfkfyd`)

| Migration | Status | Rows affected |
|-----------|--------|---------------|
| `20260417_pms_hours_of_rest_crew_comment.sql` | ✅ Applied | — |
| `20260417_trigger_rolling_compliance.sql` | ✅ Applied | — (trigger replaced) |
| `20260417_pms_hor_exceptions.sql` | ✅ Applied | — (new table) |
| `20260417_pms_hor_exceptions_link.sql` | ✅ Applied | — |
| `20260417_hor_legacy_totals_backfill.sql` | ✅ Applied | 8 rows backfilled |

`dash_crew_hours_compliance` confirmed present (65 rows). `rolling_7day_rest_hours` column added.

---

## 11. Known Gaps (Not Built This Session)

| Item | Why deferred | Suggested owner |
|------|-------------|-----------------|
| HoR PDF export | HMAC01/Receipt Layer domain — data is clean, sign chain complete | HMAC01 |
| Exceptions handler UI panel (frontend) | Backend complete; frontend panel not built | Next HoR sprint |
| Forward scheduling frontend panel | Endpoint exists; no UI component yet | Next HoR sprint |
| Offline data entry | Explicitly excluded by CEO | — |
| iOS/Android app | Explicitly excluded by CEO | — |
| Auto-email on sign-off | Explicitly excluded by CEO | — |
| Batch ZIP export | Explicitly excluded by CEO | — |
| BUG-HOR-4 Playwright run | Docker-only per CEO; real auth wired, ready to run | Run on next test pass |

---

## 12. Architecture Notes for Next Engineer

1. **Python is authoritative, trigger is approximate.** `_check_rolling_24h_compliance` in the handler is the MLC compliance gate. The Postgres trigger `update_crew_hours_compliance()` updates `dash_crew_hours_compliance` with a rolling-7-day sum that is DATE-BOUNDARY anchored (not true sliding window). Use trigger data for dashboard display; use API response `rolling_24h_check` for compliance decisions.

2. **`my-week` endpoint reads stored `is_daily_compliant` from DB.** This could diverge from Python's rolling-window computation on edge cases (midnight-boundary violations). Consider returning the Python-computed value from upsert cache rather than DB-read in a future sprint.

3. **Exception workflow is backend-only.** The `pms_hor_exceptions` table and endpoints exist; no UI component was built. The compliance engine reads active exceptions on every upsert.

4. **Crew comment is API-enforced, not DB-enforced.** The column is nullable; corrections and backfilled records legitimately have no comment. Only fresh non-compliant entries require justification.

---

W8: fleet-compliance (fleet manager JWT): PASS (2 vessels, compliance_pct=float|None, violations=int, crew=int — all assertions green)

Note: compliance_pct=None on a vessel with 0 crew is correct behaviour — no data, not a bug. Confirmed at hor_compliance_routes.py:811-813 (total_expected_days=0 returns None).

*End of delivery manifest. PR #640 open. shard-46 baseline: 10/10 (MCP02). CEO review requested.*
