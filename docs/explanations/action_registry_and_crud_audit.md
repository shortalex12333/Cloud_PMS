# Action Registry & CRUD Operation Issues — Audit Strategy

**Status:** Open problem  
**Owner:** CEO01 (decision), FRONTEND02 + ENGINEER02 (execution)  
**Date:** 2026-04-11

---

## The Problem

The site has hundreds of buttons that trigger CRUD operations against entities (work orders, faults, equipment, handovers, etc.). **Some buttons do nothing.** The "create handover" button inside the lens is one example — clicking it has no effect, no error, no feedback. These silent failures are the worst kind of bug because they're invisible until a real user complains.

We have no systematic way today to find every dead button across the site, and no way to know whether the action registry is even *complete*.

---

## The Three Sources of Truth (and why none are complete)

| Source | Tells you... | Doesn't tell you... |
|--------|-------------|---------------------|
| **Backend `ACTION_REGISTRY`** (206 actions) | What backend CAN do | What it SHOULD be able to do |
| **Frontend buttons** (N buttons in `apps/web/src/components/`) | What UI EXPOSES | Whether the click actually works |
| **Domain expectations** (no doc currently) | What users NEED | — (this doc doesn't exist yet) |

The registry is one source of truth, but it's not the source of truth. A button doing nothing does NOT necessarily mean the action is missing from the registry — it might be there, or it might be a phantom action name the frontend invented, or the registry itself might be incomplete (missing actions that should exist).

---

## Failure Modes — and which audit catches each

| # | Bug | What's wrong | Static audit catches? | Click crawler catches? | Smoke test catches? |
|---|-----|--------------|----------------------|----------------------|-------------------|
| 1 | Button has empty `onClick = () => {}` | Frontend wiring | ❌ NO (looks valid) | ✅ YES (no network call fires) | ❌ NO |
| 2 | Button calls action `"create_handover"` — registry has no such name | Frontend phantom | ✅ YES (orphan button) | ✅ YES (404 in network panel) | ❌ NO |
| 3 | Button calls action `X`, X exists, handler is `stub_handlers.py` | Backend stub | ✅ YES (handler type = stub) | ⚠️ Maybe (returns 200 with junk) | ✅ YES |
| 4 | Backend action exists, no frontend entry point | Orphaned backend | ✅ YES (registry entry with no caller) | ❌ NO | ✅ YES (smoke passes but user never sees it) |
| 5 | **Action doesn't exist anywhere — but should** (e.g. no "create handover" button anywhere) | Missing feature | ❌ NO | ❌ NO | ❌ NO |
| 6 | Action fires, backend works, but ledger entry is skipped | Silent side-effect drop | ❌ NO | ⚠️ Only with assertions | ✅ YES (with ledger check) |

**The killer is failure mode #5.** No automated audit can find it. You need a **domain expectation matrix** — a doc that says, per entity, what actions MUST exist.

---

## The Three-Layer Audit Strategy

### Layer 1 — Static Coverage Audit (1 day, finds 80% of bugs)

A script that:
1. Reads `ACTION_REGISTRY` from `apps/api/action_router/registry.py` (source: backend)
2. Greps every `<button>`, `onClick`, and action invocation in `apps/web/src/components/`
3. Cross-references and produces a coverage matrix:

```
action_name           | in_registry | in_frontend | handler_type | status
create_work_order     | YES         | YES         | real         | LIVE
create_handover       | NO          | YES         | —            | PHANTOM (frontend calls non-existent)
revoke_handover       | YES         | NO          | real         | ORPHAN BACKEND
add_part_to_wo        | YES         | YES         | stub         | STUB BACKEND (bug)
close_fault           | YES         | YES         | real         | LIVE
```

**Outputs:**
- `action_coverage_matrix.csv` — every action, every status
- `dead_buttons.md` — list of frontend buttons with no working backend
- `orphan_actions.md` — backend actions with no UI entry point
- `stub_handlers.md` — actions that point to `stub_handlers.py`

**Owner:** ENGINEER02 (script lives in `scripts/audit/action_coverage.py`)  
**Cost:** 1 session  
**Catches:** Failure modes 2, 3, 4

---

### Layer 2 — Playwright Click Crawler (2 days, runtime verification)

A Playwright test that:
1. Logs in as a known test user with full permissions
2. Walks every lens page in the site (work-orders, faults, equipment, handovers, etc.)
3. Opens at least one entity in each lens
4. Finds every visible button on the page
5. For each button:
   - Records the network panel BEFORE click
   - Clicks the button
   - Asserts: a network call was made to `/v1/actions/execute` or `/v1/actions/list`
   - Records: action name, payload, HTTP status, response body
   - If a modal opens, captures it; if it submits, follows through
6. Outputs a per-lens report:

```
work-orders lens:
  buttons_found: 12
  fired_action: 9
  dead (no network call): 2
    - "Add Note" (line 45 of WorkOrderLens.tsx)
    - "Reopen" (line 78)
  errors: 1
    - "Add Part" → 500 INTERNAL_SERVER_ERROR
```

**Outputs:**
- `playwright-action-coverage/` — per-lens reports
- CI integration: this becomes a guard so dead buttons can never be merged again

**Owner:** FRONTEND02 (test lives in `apps/web/e2e/action-coverage/`)  
**Cost:** 2 sessions  
**Catches:** Failure modes 1, 2, 3, 6 (with assertions)

---

### Layer 3 — Backend Smoke Test (1 day, handler verification)

A Python script that:
1. Iterates `ACTION_REGISTRY`
2. For each action, builds a minimal payload from the action's schema definition (use `validators/schema_validator.py` to validate)
3. POSTs to `/v1/actions/execute` against a seeded test tenant DB with a real JWT
4. Records: pass / fail / 500 / wrong shape / stub response

**Outputs:**
- `backend_action_smoke_results.json` — every action, every status
- Highlights actions returning 200 with empty/junk data (probable stubs)

**Owner:** ENGINEER02 (script lives in `scripts/audit/backend_action_smoke.py`)  
**Cost:** 1 session  
**Catches:** Failure modes 3, 4, 6

---

## The Missing Source of Truth: Expected Action Matrix

Layers 1–3 above will catch every failure mode except #5 (missing features). To catch #5 we need a doc that lives in the repo and is updated by product, not engineering:

**`docs/explanations/expected_actions_per_entity.md`** — proposed structure:

```markdown
## Handover
- create_draft (CREATE) — start a new handover
- add_open_fault (UPDATE) — pull an open fault into the draft
- add_open_work_order (UPDATE) — pull an open WO into the draft
- add_manual_note (UPDATE) — free-text addition
- preview (READ) — see the draft as it stands
- export_pdf (CREATE) — generate the final PDF
- sign (UPDATE) — outgoing engineer signs
- countersign (UPDATE) — incoming engineer countersigns
- revoke (DELETE) — cancel a draft

## Fault
- report (CREATE)
- assign (UPDATE)
- close (UPDATE)
- reopen (UPDATE)
- link_to_work_order (UPDATE)
- attach_photo (UPDATE)
- add_note (UPDATE)
- view_history (READ)
...
```

Once this exists, the gap report becomes trivial:

```
Expected ∩ Registry ∩ Frontend = LIVE
Expected ∩ Registry − Frontend = BACKEND READY, NO BUTTON
Expected − Registry − Frontend = MISSING EVERYWHERE (failure mode #5)
Registry − Expected = backend dead code (delete?)
Frontend − Registry = frontend phantom buttons (failure mode #2)
```

**Owner:** CEO01 to draft initial version, FRONTEND02 + ENGINEER02 to validate against current state.

---

## Recommended Execution Order

| Step | What | Who | Cost | Why first |
|------|------|-----|------|-----------|
| 1 | Layer 1 static audit | ENGINEER02 | 1 session | Cheapest, finds the most bugs fastest |
| 2 | Draft expected action matrix | CEO01 | 1 session | Need this to find missing features |
| 3 | Layer 3 backend smoke test | ENGINEER02 | 1 session | Catches stubs that Layer 1 misses |
| 4 | Layer 2 click crawler | FRONTEND02 | 2 sessions | Most expensive, but becomes ongoing CI guard |
| 5 | Triage results, fix red items | Both | Multi-session | The actual bug fixing |
| 6 | Wire Layer 2 into CI | FRONTEND02 | 0.5 session | Prevents regression forever |

---

## Specific Known Issues (current bug list — to be expanded by audit)

1. **"Create handover" button does nothing** — reported by boss 2026-04-11. Likely failure mode 1 (empty onClick) or 2 (phantom action name). To be confirmed by audit.
2. **Ledger entries missing** — reported by boss 2026-04-11. Likely failure mode 6 (action handler skips ledger write). FRONTEND02 + ENGINEER02 investigating.
3. **Handover draft view does not exist** — reported by boss 2026-04-11. Failure mode 5 (missing surface entirely). The `/handover-export` route shows completed handovers only; there is no surface for browsing in-progress drafts. Real product work, scoped separately.

---

## Why This Matters

Today, every dead button is a customer-facing trust failure. A chief engineer clicks "create handover" and nothing happens — they don't trust the system anymore. We can't sell a PMS where buttons silently fail.

The cost of building this audit infrastructure is ~5 engineering sessions. The cost of NOT building it is unbounded — every new feature has the same risk, every refactor can break N buttons silently, and every bug report from the field is reactive instead of preventable.

Build the audit. Run it. Fix the red. Then keep it green forever via CI.
