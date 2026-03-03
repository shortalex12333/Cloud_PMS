# STATE — Current Session Memory

> **This file tracks decisions, blockers, and position across sessions.**
>
> Last Updated: 2026-03-03

---

## Current Position

| Field | Value |
|-------|-------|
| **Active Milestone** | Post-v1.3 — Lens Architecture Conversions |
| **Status** | ⚙️ **IN PROGRESS** |
| **Domain** | LENSES & FRAGMENTED ROUTES |
| **Last Activity** | 2026-03-03 — Phase 20 email conversion complete |

**Progress:** [█] 5% (1/1 phase complete for email conversion)

---

## What v1.3 Delivered (LENSES)

| Phase | Deliverable | Status |
|-------|-------------|--------|
| 15 | IntentEnvelope type (READ/MUTATE/MIXED classification) | ✓ |
| 16 | /v1/actions/prepare endpoint (form prefill) | ✓ |
| 16.1 | Mount /prepare in pipeline_service (fix 404) | ✓ |
| 16.2 | RouteShell + PermissionService (-4,262 LOC) | ✓ |
| 17 | Readiness states (READY/NEEDS_INPUT/BLOCKED) | ✓ |
| 18 | Disambiguation UX (ambiguous entity handling) | ✓ |
| 19 | 614 E2E tests across 12 lenses (4 waves complete) | ✓ |

**Key artifacts:**
- `apps/web/src/components/lens/RouteShell.tsx` — Thin wrapper for all lens routes
- `apps/web/src/services/permissions.ts` — RBAC from lens_matrix.json
- `test/e2e/*-intent.spec.ts` — 614 Playwright tests (50+ per lens)
- `.planning/agents/e2e-coverage/coverage_report.md` — Test coverage report

---

## Completed Milestones Summary

| Version | Name | Domain | Phases | Status |
|---------|------|--------|--------|--------|
| v1.0 | Lens Completion | LENSES | 14 | ✓ Complete |
| v1.1 | Search Pipeline Hardening | SEARCH | 5 (A-E) | ✓ Complete |
| v1.2 | Search Snippet Enhancement | SEARCH | 5 | ✓ Complete |
| v1.3 | Actionable UX Unification | **LENSES** | 7 | ✓ **COMPLETE** |

---

## Phase 20: Email Conversion (Post-v1.3)

**Goal:** Enable email threads to work in both SPA mode (ContextPanel) and fragmented mode

| Phase | Deliverable | Status |
|-------|-------------|--------|
| 20 | EmailLensContent + LensRenderer registration | ✓ Complete |

**Key artifacts:**
- `apps/web/src/components/lens/EmailLensContent.tsx` — SPA mode wrapper for email threads
- `.planning/phases/20-email-conversion/20-01-SUMMARY.md` — Execution summary

**What was delivered:**
- Created EmailLensContent.tsx (153 LOC) that wraps EmailThreadViewer
- Registered 'email' case in LensRenderer switch statement
- SPA mode: `/app?entity=email&id=X` now renders email via ContextPanel
- Fragmented mode: `/email/[threadId]` continues to work unchanged
- SACRED OAuth patterns untouched (0 changes to oauth-utils, authHelpers, useEmailData)

**Execution metrics:**
- Duration: 117 seconds
- Tasks: 2 automated implementation tasks
- Commits: 2 (2a1a9b65, 4dd0b4bf)
- Files: 1 created, 1 modified

---

## Parked Work (SEARCH — Different Domain)

> ⚠️ **This is SEARCH work, NOT lens work.** Do not conflate with v1.3.

### v1.4 — Recall Improvement (PARKED)

**Domain:** Search pipeline, embeddings, text matching
**Status:** Blocked on database migration deployment

| Metric | Current | Target | Gap |
|--------|---------|--------|-----|
| Recall@3 | 12.1% | 25-35% | Migration needed |
| Lens Accuracy | 47.3% | 60-70% | Migration needed |

**Blocker:** `50_enhance_search_text.sql` migration not deployed to production.

**To resume v1.4:**
```bash
# 1. Deploy migration
psql $DATABASE_URL -f supabase/migrations/50_enhance_search_text.sql

# 2. Re-run validation
python3 scripts/eval/v12_recall_harness.py --use-embeddings --sample 100
```

**Files (search-specific):**
- `scripts/eval/generate_query_embeddings.py`
- `scripts/eval/search_synonyms.json`
- `supabase/migrations/50_enhance_search_text.sql`
- `.planning/phases/v1.4-recall-improvement/VALIDATION-REPORT.md`

---

## v1.3 Phase Details (LENSES)

| # | Phase | Goal | Requirements | Status |
|---|-------|------|--------------|--------|
| 15 | Intent Envelope | Create IntentEnvelope abstraction | INTENT-01..03 | ✓ Complete |
| 16 | Prefill Integration | Build /v1/actions/prepare endpoint | PREFILL-01..05 | ✓ Complete |
| 16.1 | Mount /prepare | Fix GAP-001: endpoint returns 404 | GAP-001 | ✓ Complete |
| 16.2 | Unified Route Architecture | RouteShell + PermissionService (-4,262 LOC) | ROUTE-ARCH-01..04 | ✓ Complete |
| 17 | Readiness States | Implement READY/NEEDS_INPUT/BLOCKED | READY-01..04 | ✓ Complete |
| 18 | Route & Disamb | Fragmented URLs + disambiguation UX | ROUTE-01..03, DISAMB-01..03 | ✓ Complete |
| 19 | Agent Deployment | 24 agents across 4 waves (614 E2E tests) | AGENT-01..04 | ✓ Complete (4/4 waves) |

---

## Execution Metrics (v1.3)

| Phase | Duration | Tasks | Files |
|-------|----------|-------|-------|
| Phase 16 P01 | 305s | 3 | 5 |
| Phase 16 P02 | 240s | 3 | 3 |
| Phase 17 P01 | 213s | 3 | 3 |
| Phase 18 P01 | 241s | 3 | 3 |
| Phase 18 P02 | 290s | 3 | 2 |
| Phase 19 P01 | 275s | 3 | 13 |
| Phase 19 P02 | 842s | 3 | 13 |
| Phase 19 P03 | 317s | 2 | 2 |
| Phase 19 P04 | 600s | 3 | 14 |
| Phase 16.2 P01 | 180s | 1 (one-shot) | 12 |

## Execution Metrics (Phase 20)

| Phase | Duration | Tasks | Files |
|-------|----------|-------|-------|
| Phase 20 P01 | 117s | 2 | 2 |

---

## Key Decisions (v1.3 Lens Work)

| Decision | Rationale | Date |
|----------|-----------|------|
| Phase numbering starts at 15 | Continues from v1.0 final phase (14) | 2026-03-01 |
| 5 phases for v1.3 (not arbitrary) | Derived from requirement categories | 2026-03-01 |
| Modify existing files only | User directive: no new random files | 2026-03-01 |
| Use existing Action Detector + Entity Extractor | No duplicate NLP systems | 2026-03-01 |
| IntentMode: READ/MUTATE/MIXED | Three states covers all intent combinations | 2026-03-01 |
| READY threshold: confidence >= 0.8 | Prevents premature READY state | 2026-03-01 |
| Role gating via ACTION_REGISTRY | Centralized role checking | 2026-03-02 |
| Direct lens analysis (no external agents) | More efficient - context already loaded | 2026-03-02 |
| RouteShell pattern for route pages | Eliminates ~400 LOC per route | 2026-03-03 |
| PermissionService from lens_matrix.json | Single RBAC source of truth | 2026-03-03 |

## Key Decisions (Phase 20 Email Conversion)

| Decision | Rationale | Date |
|----------|-----------|------|
| Use EmailThreadViewer delegation pattern | Avoid duplicating 400 LOC OAuth logic | 2026-03-03 |
| No fragmented route changes needed | /email/[threadId] already works | 2026-03-03 |
| Simplified VitalSigns (no icons) | VitalSign type only supports label/value/color | 2026-03-03 |

---

## v1.3 Technical Decisions

- [Phase 16]: "next week" maps to Monday of NEXT week
- [Phase 16]: Separate /prepare endpoint (not polluting /list semantics)
- [Phase 17]: role_blocked field in PrepareResponse for BLOCKED detection
- [Phase 17]: deriveReadinessFromPrefill function for client-side derivation
- [Phase 18]: Segment filters become path segments, not query params
- [Phase 18]: URL normalization: lowercase, hyphens for spaces
- [Phase 18-02]: Confidence threshold 0.85 separates auto-fill from confirm-required
- [Phase 18-02]: AmbiguityDropdown and DateWarning components
- [Phase 19-01]: 12 lens matrices with 81 MUTATE actions, 67 READ filters
- [Phase 19-02]: 1,200 query variants (100 per lens)
- [Phase 19-03]: 12 resolve_*_entities functions in prefill_engine.py
- [Phase 19-04]: 614 E2E tests (307 READ + 307 MUTATE)
- [Phase 16.2]: RouteShell replaces 11 route pages (93% LOC reduction)

---

## v1.3 Guardrails (LENS WORK)

1. **No new random files** — modify existing lens components
2. **Single canonical contracts** — ActionSuggestion type is the interface
3. **Determinism first** — same query → same IntentEnvelope
4. **No duplicate inference systems** — use existing NLP modules
5. **100% yacht isolation** — all entity lookups scoped by yacht_id
6. **Explicit role gating** — RLS + backend checks on all mutations
7. **Surface uncertainty** — never silently assume, show ambiguity to user

---

## What's Next

**v1.3 is COMPLETE.** Options:

1. **Continue with v1.0 Lens Completion** — 14 phases of individual lens refinement remain
2. **Resume v1.4 Recall Improvement** — Deploy search_text migration first
3. **Start new milestone** — Define requirements for next feature set

Ask the user which direction to take.

---

## Blockers

| Blocker | Impact | Owner | Status |
|---------|--------|-------|--------|
| None for lens work | — | — | — |
| v1.4: Migration not deployed | Search recall blocked | Infra | Parked |

---

## Accumulated Context

### From v1.0 Milestone (LENSES)
- 14 phases complete (60 requirements)
- All lenses rebuilt with design system
- E2E tests passing
- Ledger triggers verified

### From v1.3 Milestone (LENSES)
- IntentEnvelope abstraction
- /v1/actions/prepare endpoint
- Readiness states (READY/NEEDS_INPUT/BLOCKED)
- Disambiguation UX
- 614 E2E tests

### From v1.1/v1.2 Milestones (SEARCH — different domain)
- Search pipeline hardening complete
- AbortError fix deployed
- Search snippets with highlighting
- Truth set validation identified issues

---

## Session Notes

### 2026-03-03 (Session 5 - Phase 20 Execution)
- **Executed:** Phase 20 plan 01 - Email lens SPA mode support
- **Created:** EmailLensContent.tsx (153 LOC) wrapper component
- **Modified:** LensRenderer.tsx to register 'email' case
- **Verified:** SACRED OAuth files unchanged (0 changes confirmed)
- **Duration:** 117 seconds for 2 automated tasks
- **Outcome:** SPA mode now supports email, fragmented mode unchanged
- **Manual testing pending:** Browser verification of both modes

### 2026-03-03 (Session 4)
- **Discovered:** Phase 19 Wave 4 was already executed (614 E2E tests exist)
- **Fixed:** Created missing 19-04-SUMMARY.md
- **Fixed:** Updated ROADMAP.md to mark Phase 19 complete
- **Fixed:** Separated v1.3 (lenses) from v1.4 (search) in STATE.md
- **Lesson:** State files can drift — verify against filesystem

### 2026-03-02 (Session 3 continued)
- Phase 16.2 one-shot: RouteShell + PermissionService
- 11 route pages replaced with ~27 LOC each
- Net reduction: 4,262 LOC → 285 LOC (93%)

### 2026-03-01 (Session 3)
- v1.3 roadmap created: 7 phases (15-19), 22 requirements
- Phase 15-19 plans created and executed

---

*This file focuses on LENS work (v1.3). Search work (v1.4) is parked separately.*
