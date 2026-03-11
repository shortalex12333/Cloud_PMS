# Agent Onboarding — Entity Lenses v2

**Paste this entire document to any Claude agent working on Entity Lenses.**

---

# PART 1: OPERATING FRAMEWORK

## The Four Modes

You operate in **four modes**. Never mix them. Complete each before moving to next.

| Mode | What You Do | What You DON'T Do |
|------|-------------|-------------------|
| **PLANNER** | Create plan, list files, define criteria | Write code |
| **EXECUTION** | Implement only what's planned | Modify unplanned files |
| **VERIFICATION** | Test, prove it works, check for drift | Assume it works |
| **HISTORIAN** | Write structured lesson, capture patterns | Skip documentation |

## The Three Rules

1. **Plan First** — No code without approved plan
2. **Verify Always** — Prove it works with evidence
3. **Learn Forever** — Structured lesson after every task

## File Organization Rules

| Forbidden | Required |
|-----------|----------|
| `_v1`, `_v2`, `_final`, `_old` suffixes | Clear, purpose-driven names |
| `utils.py`, `helpers.py` | Import, don't copy |
| Create file in wrong place | Right location from start |

---

# PART 2: PROJECT CONTEXT

## Project Goal

Entity Lenses provide a **backend-first, document-driven** approach to yacht maintenance operations. Each lens governs a single entity type with:

- **DB TRUTH**: Schema verified from production
- **Actions**: Registered mutations with role gating
- **RLS Matrix**: Row-level security at database layer
- **Scenarios**: User journey documentation

```
User Intent → /v1/search → Filters (READ) or Actions (MUTATE)
                                      ↓
                           /v1/actions/execute (unified endpoint)
                                      ↓
                           Handler → RLS → Database
```

## Current Phase Status

```
Lens Docs (1-8) ✓ → Spotlight (9-14) ✓ → Intent (15) ✓ → Prefill (16) ✓ → Mount (16.1) ○ → Readiness (17) ◐
                                                                              URGENT       checkpoint
```

| Phase | Name | Status |
|-------|------|--------|
| 1-8 | Lens Documentation | ✓ Complete (Certificate, WO, Equipment) |
| 9-14 | Spotlight Search | ✓ Complete |
| 15 | Intent Envelope | ✓ Complete |
| 16 | Prefill Integration | ✓ Complete |
| **16.1** | Mount /prepare endpoint | **○ URGENT** |
| 17 | Readiness States | ◐ In Progress (checkpoint) |
| 18 | Route & Disambiguation | ○ Pending |
| 19 | Agent Deployment | ○ Pending |

## Critical Gap (GAP-001)

**Problem:** `/v1/actions/prepare` endpoint exists in `action_router/router.py:1248` but is **NOT mounted** in `pipeline_service.py`.

**Impact:** Prefill functionality unreachable via API.

**Fix:** Phase 16.1 — Move `/prepare` to `p0_actions_routes.py`.

## Lens Maturity Status

| Lens | Maturity | Blockers |
|------|----------|----------|
| Certificate | GOLD | B1-B6 (migrations ready) |
| Work Order | GOLD | B1-B4 (resolved) |
| Equipment | GOLD | B1-B4 (verify) |
| Fault | MINIMAL | Full v2 needed |
| Inventory/Part | PARTIAL | Full v2 needed |
| Crew | PARTIAL | Full v2 needed |

---

# PART 3: KEY FILES

## Backend (apps/api)

| File | Purpose |
|------|---------|
| `action_router/router.py` | Main action router |
| `action_router/registry.py` | Action definitions |
| `handlers/*.py` | Domain handlers |
| `common/prefill_engine.py` | Prefill generation |
| `common/temporal_parser.py` | NLP date parsing |
| `routes/p0_actions_routes.py` | Action routes (mounted) |
| `pipeline_service.py` | Main FastAPI app |

## Frontend (apps/web/src)

| File | Purpose |
|------|---------|
| `hooks/useCelesteSearch.ts` | IntentEnvelope, readiness derivation |
| `lib/actionClient.ts` | prepareAction(), PrepareResponse |
| `lib/filters/catalog.ts` | Filter definitions |
| `lib/filters/execute.ts` | Filter execution |
| `components/SuggestedActions.tsx` | ReadinessIndicator |
| `components/ActionModal.tsx` | Prefill display |

## Documentation

| File | Purpose |
|------|---------|
| `docs/pipeline/entity_lenses/*/v2/*_FINAL.md` | Lens specifications |
| `docs/ON_GOING_WORK/BACKEND/LENSES/OVERVIEW.md` | Architecture overview |
| `docs/ON_GOING_WORK/BACKEND/LENSES/GAPS.md` | Missing components |

---

# PART 4: CANONICAL SQL FUNCTIONS

**ALWAYS use these — no custom implementations:**

```sql
-- Yacht scope (ALL queries)
public.get_user_yacht_id() → UUID

-- Role checks (write operations)
public.is_hod(user_id, yacht_id) → BOOLEAN
public.is_manager() → BOOLEAN
public.get_user_role() → TEXT
```

**RLS Pattern:**

```sql
-- SELECT: All crew on yacht
USING (yacht_id = public.get_user_yacht_id());

-- INSERT/UPDATE: HOD only
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
    AND is_hod(auth.uid(), public.get_user_yacht_id())
);

-- DELETE: Manager only
USING (
    yacht_id = public.get_user_yacht_id()
    AND is_manager()
);
```

**Signature Invariant:**

```sql
-- Non-signed action: ALWAYS
signature = '{}'::jsonb

-- Signed action: NEVER NULL
signature = :signature_payload::jsonb
```

---

# PART 5: GUARDRAILS (Non-Negotiable)

1. **No new random files** — modify existing files only
2. **No dashboard language** — query-only activation
3. **No ambient buttons** — actions only after focus
4. **100% yacht isolation** — all lookups scoped by yacht_id
5. **Explicit role gating** — RLS + backend checks
6. **Signature invariant** — `'{}'::jsonb` or valid payload, NEVER NULL
7. **Surface uncertainty** — never silently assume

---

# PART 6: LESSONS REFERENCE

**Project lessons:** `tasks/lessons.md` (create if missing)

Read this file before starting any task. Add lessons after completing tasks.

**Lesson Format:**

```markdown
## LESSON: [Short Title]

**Date:** YYYY-MM-DD
**Context:** [What were we doing?]
**Failure:** [What went wrong?]
**Root Cause:** [Why?]
**Guard Added:** [Rule to prevent]
**Reusable Pattern:** [What to apply elsewhere]
**Tags:** [categories]
```

---

# PART 7: DOCKER LOCAL-FIRST

**WHY:** Remote platforms hide information. Local Docker reveals everything.

| Approach | Cost | Debug Visibility | Iteration Speed |
|----------|------|------------------|-----------------|
| Remote | $7+/month | 10% | 5-10 min |
| **Local Docker** | **$0** | **100%** | **10-30 sec** |

**Always verify locally before pushing:**

```bash
# Start API
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS
docker compose -f docker-compose.local.yml up api -d

# Wait for health
sleep 10

# Test health
curl http://localhost:8000/health

# Test /prepare (after GAP-001 fix)
curl -X POST http://localhost:8000/v1/actions/prepare \
  -H "Content-Type: application/json" \
  -d '{"q": "create work order", "domain": "work_orders"}'

# Only then push to remote
git push
```

---

# PART 8: GSD COMMANDS

```bash
# Check progress
/gsd:progress

# Plan a phase
/gsd:plan-phase 16.1

# Execute a phase
/gsd:execute-phase 17

# Continue paused phase
/gsd:execute-phase 17 --continue

# Verify work
/gsd:verify-work

# Add todo
/gsd:add-todo

# Check todos
/gsd:check-todos
```

---

# PART 9: TASK TEMPLATE

## Task: [DESCRIBE TASK]

**Context:**
- Project: Entity Lenses (v2)
- Current state: [what exists]
- Goal: [end state]

**Constraints:**
- Scope: [specific files only]
- Tech: React, TypeScript, Python, FastAPI, PostgreSQL
- Priority: [Low/Medium/High/Critical]

**Start in PLANNER MODE:**
1. Read relevant files in `docs/ON_GOING_WORK/BACKEND/LENSES/`
2. Read relevant lens FINAL.md in `docs/pipeline/entity_lenses/`
3. List files to change
4. Define acceptance criteria
5. Wait for approval

**Do not write code until plan is approved.**

**After completion:**
1. Verify with Docker local test
2. Write structured lesson
3. Update project documentation

---

# EXAMPLE TASKS

## Example 1: Fix GAP-001 (Phase 16.1)

```markdown
## Task: Mount /prepare endpoint in pipeline_service

**Context:**
- Project: Entity Lenses / Spotlight Search
- Current state: /prepare exists in action_router/router.py but not mounted
- Goal: /prepare accessible at localhost:8000/v1/actions/prepare

**Constraints:**
- Scope: p0_actions_routes.py, pipeline_service.py only
- Tech: Python, FastAPI
- Priority: Critical (blocks Phase 17)

**Start in PLANNER MODE:**
1. Read GAPS.md for GAP-001 details
2. Read action_router/router.py:1248 for prepare_action code
3. Plan move to p0_actions_routes.py
4. Define acceptance criteria (curl returns 200)
5. Wait for approval

Do not write code until plan is approved.
```

## Example 2: Complete Fault Lens v2

```markdown
## Task: Document Fault Lens v2 (Phases 0-8)

**Context:**
- Project: Entity Lenses
- Current state: LENS.md exists (single doc)
- Goal: Full v2 documentation like Certificate Lens

**Constraints:**
- Scope: docs/pipeline/entity_lenses/fault_lens/v2/
- Tech: Documentation only (no code)
- Priority: Medium

**Start in PLANNER MODE:**
1. Read certificate_lens_v2_FINAL.md as gold standard
2. Read existing fault_lens/LENS.md
3. Plan 9 phase files + FINAL.md
4. Define verification criteria
5. Wait for approval

This is documentation work, not implementation.
```

## Example 3: Deploy Certificate RLS Migrations

```markdown
## Task: Deploy certificate RLS migrations (B1, B2, B5, B6)

**Context:**
- Project: Entity Lenses / Certificate Lens
- Current state: Migrations written but not deployed
- Goal: pms_vessel_certificates and pms_crew_certificates fully secured

**Constraints:**
- Scope: supabase/migrations/20260125_00*.sql
- Tech: PostgreSQL, Supabase
- Priority: High

**Start in PLANNER MODE:**
1. Read GAPS.md for GAP-002 (certificate RLS)
2. Read certificate_lens_v2_PHASE_8_GAPS_MIGRATIONS.md
3. List migrations in order
4. Define rollback strategy
5. Wait for approval

Do not deploy until plan is approved.
```

---

# CONFIRMATION

Before starting, confirm:

1. ☐ I understand the 4-mode methodology
2. ☐ I know the current phase status (16.1 URGENT)
3. ☐ I know GAP-001 blocks prefill functionality
4. ☐ I will use canonical SQL functions (get_user_yacht_id, is_hod, is_manager)
5. ☐ I will verify locally with Docker before pushing
6. ☐ I will write lessons after completing tasks

**State which mode you are starting in.**
