# Agent Onboarding — Spotlight Search v1.3

**Paste this entire document to any Claude agent working on Spotlight Search.**

> ✅ **ALL PHASES COMPLETE:** Phases 15-19 finished. GAP-006 fixed. E2E tests created. Now in verification phase.

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

Unify NLP intent into deterministic **READ** navigation and **MUTATE** actions with prefill preview.

```
User Query → IntentEnvelope → READ (navigate) or MUTATE (action with prefill)
```

## Current Phase Status

```
Phase 15 ✓ → Phase 16 ✓ → Phase 16.1 ✓ → Phase 17 ✓ → Phase 17.1 ✓ → Phase 18 ✓ → Phase 19 ✓ → VERIFICATION
                                                                                                    ↓
                                                                                               E2E TESTS
```

**Progress:** 95% complete (Verification Phase)

| Phase | Name | Status |
|-------|------|--------|
| 15 | Intent Envelope | ✓ Complete |
| 16 | Prefill Integration | ✓ Complete |
| 16.1 | Mount /prepare endpoint | ✓ Complete |
| 17 | Readiness States | ✓ Complete |
| 17.1 | Fragmented Route Action Buttons | ✓ Complete (GAP-006 FIXED) |
| 18 | Route & Disambiguation | ✓ Complete |
| 19 | Agent Deployment | ✓ Complete (4 waves, ~60 E2E tests) |

## Critical Gap (GAP-006) 🚨

**Problem:** Fragmented route pages (`/work-orders/[id]`, `/faults/[id]`, `/equipment/[id]`) have only 2 placeholder action buttons instead of the full set.

**Impact:** Users on holistic views cannot perform most entity actions.

**Current State:**
| Page | Expected | Actual | TestIDs |
|------|----------|--------|---------|
| `/work-orders/[id]` | 5 buttons | 2 | ❌ None |
| `/faults/[id]` | 5 buttons | 2 | ❌ None |
| `/equipment/[id]` | 3 buttons | 2 | ❌ None |

**Fix:** Phase 17.1 — Extract action buttons from Lens components, add to fragmented route pages.

## Action Button Architecture (THREE Systems)

Understanding this is critical for any agent:

| System | Location | Trigger | Status |
|--------|----------|---------|--------|
| **SuggestedActions** | `SpotlightSearch.tsx` | MUTATE queries ("create work order") | ✅ Working (14 buttons) |
| **Fragmented Routes** | `/app/*/[id]/page.tsx` | Click search result (FRAGMENTED_ROUTES=true) | ⚠️ **INCOMPLETE** |
| **Legacy ContextPanel** | `*LensContent.tsx` | Click search result (flag OFF) | ✅ Working |

**Key:** When `NEXT_PUBLIC_FRAGMENTED_ROUTES_ENABLED=true` (production), clicking search results navigates to dedicated pages via `router.push()`. The Lens content panel does NOT open.

## Key Files

### Frontend (apps/web/src)

| File | Purpose |
|------|---------|
| `hooks/useCelesteSearch.ts` | IntentEnvelope, deriveReadinessFromPrefill, CONFIDENCE_THRESHOLD=0.7 |
| `lib/actionClient.ts` | prepareAction(), PrepareResponse |
| `components/SuggestedActions.tsx` | ReadinessIndicator, action buttons for MUTATE |
| `components/ActionModal.tsx` | Prefill display |
| `components/SpotlightSearch.tsx` | Fragmented routes navigation (lines 576-612) |
| **`components/lens/FaultLensContent.tsx`** | **✅ Full fault action buttons** (reference) |
| **`components/lens/EquipmentLensContent.tsx`** | **✅ Full equipment action buttons** (reference) |
| **`components/lens/WorkOrderLensContent.tsx`** | **✅ Full work order action buttons** (reference) |
| **`app/work-orders/[id]/page.tsx`** | ✅ Full action buttons |
| **`app/faults/[id]/page.tsx`** | ✅ Full action buttons |
| **`app/equipment/[id]/page.tsx`** | ✅ Full action buttons |

### Backend (apps/api)

| File | Purpose |
|------|---------|
| `routes/p0_actions_routes.py` | /prepare endpoint ✅ (GAP-001 FIXED) |
| `common/prefill_engine.py` | build_prepare_response() |
| `common/temporal_parser.py` | Date parsing |
| `pipeline_service.py` | Main FastAPI app |

## Key Types

```typescript
type ReadinessState = 'READY' | 'NEEDS_INPUT' | 'BLOCKED';
type IntentMode = 'READ' | 'MUTATE' | 'MIXED';

interface IntentEnvelope {
  query: string;
  query_hash: string;
  mode: IntentMode;
  lens: string | null;
  readiness_state: ReadinessState;
  // ...
}

interface PrepareResponse {
  action_id: string;
  prefill: Record<string, PrefillField>;
  role_blocked?: boolean;
  // ...
}
```

## Confidence Thresholds

| Threshold | Purpose |
|-----------|---------|
| `>= 0.8` | READY state |
| `>= 0.65` | Field prefill gate |

---

# PART 3: GUARDRAILS (Non-Negotiable)

1. **No new random files** — modify existing files only
2. **Determinism first** — same query → same output
3. **100% yacht isolation** — all lookups scoped by yacht_id
4. **Explicit role gating** — RLS + backend checks
5. **Surface uncertainty** — never silently assume

---

# PART 4: LESSONS REFERENCE

**Project lessons:** `tasks/lessons.md`

Read this file before starting any task. Add lessons after completing tasks.

---

# PART 5: DOCKER LOCAL-FIRST

Always verify locally before pushing:

```bash
# Start API
docker compose -f docker-compose.local.yml up api -d

# Test health
curl http://localhost:8000/health

# Test /prepare (after GAP-001 fix)
curl -X POST http://localhost:8000/v1/actions/prepare \
  -H "Content-Type: application/json" \
  -d '{"q": "create work order", "domain": "work_orders"}'
```

---

# PART 6: GSD + RUFLO COMMANDS

```bash
# GSD (planning)
/gsd:progress
/gsd:plan-phase 16.1
/gsd:execute-phase 17
/gsd:verify-work

# Ruflo (memory)
npx ruflo memory search --query "readiness states"
npx ruflo memory store --key "pattern" --value "..."
```

---

# PART 7: TASK TEMPLATE

## Task: [DESCRIBE TASK]

**Context:**
- Project: Spotlight Search (v1.3)
- Current state: [what exists]
- Goal: [end state]

**Constraints:**
- Scope: [specific files only]
- Tech: React, TypeScript, Python, FastAPI
- Priority: [Low/Medium/High/Critical]

**Start in PLANNER MODE:**
1. Read relevant files in `docs/ON_GOING_WORK/BACKEND/SPOTLIGHT_SEARCH/`
2. List files to change
3. Define acceptance criteria
4. Write plan to tasks/todo.md
5. Wait for approval

**Do not write code until plan is approved.**

**After completion:**
1. Verify with Docker local test
2. Write structured lesson to tasks/lessons.md
3. Update project documentation

---

# EXAMPLE TASKS

## Example 1: Fix GAP-006 (Phase 17.1) — CURRENT PRIORITY

```markdown
## Task: Add action buttons to fragmented route pages

**Context:**
- Project: Spotlight Search (v1.3)
- Current state: /work-orders/[id], /faults/[id], /equipment/[id] have only 2 placeholder buttons
- Goal: All action buttons available on fragmented route pages, matching Lens components

**Constraints:**
- Scope: app/work-orders/[id]/page.tsx, app/faults/[id]/page.tsx, app/equipment/[id]/page.tsx
- Reference: components/lens/*LensContent.tsx (working implementation)
- Tech: React, TypeScript, Next.js
- Priority: **CRITICAL** (Production user impact)

**Start in PLANNER MODE:**
1. Read GAPS.md for GAP-006 details
2. Read FaultLensContent.tsx, EquipmentLensContent.tsx, WorkOrderLensContent.tsx
3. Identify action buttons and their testids
4. Plan extraction to shared components or direct addition
5. Define acceptance criteria (E2E tests pass)
6. Wait for approval

Do not write code until plan is approved.

**Reference TestIDs:**
- Fault: acknowledge-fault-btn, close-fault-btn, reopen-fault-btn, false-alarm-btn, add-note-btn
- Equipment: update-status-button, flag-attention-button, decommission-button
- WorkOrder: add-note-btn, mark-complete-btn, add-hours-btn, reassign-btn, edit-wo-btn
```

## Example 2: Verify Action Button E2E Tests

```markdown
## Task: Verify E2E tests for action button rendering

**Context:**
- Project: Spotlight Search (v1.3)
- Current state: E2E tests at e2e/shard-2-search/action-buttons.spec.ts updated
- Goal: Confirm tests correctly detect navigation path and button rendering

**Constraints:**
- Scope: E2E test verification only
- Tech: Playwright, TypeScript
- Priority: High

**Start in VERIFICATION MODE:**
1. Read action-buttons.spec.ts
2. Understand detectNavigationPath() function
3. Run tests: npx playwright test e2e/shard-2-search/action-buttons.spec.ts
4. Verify 6/6 tests passing
5. Document test coverage gaps

This is a verification task, not implementation.
```

---

# CONFIRMATION

Before starting, confirm:

1. ☐ I understand the 4-mode methodology
2. ☐ I know the current phase status (17.1 URGENT - GAP-006)
3. ☐ I understand the THREE action button systems architecture
4. ☐ I know GAP-006 affects production users on holistic views
5. ☐ I know the reference files are *LensContent.tsx components
6. ☐ I will verify locally with Docker before pushing
7. ☐ I will write lessons after completing tasks

**State which mode you are starting in.**
