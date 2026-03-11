# MILESTONES — CelesteOS Cloud PMS

> **History of completed milestones and their key deliverables.**

---

## Completed Milestones

### v1.0 — Lens Completion

**Shipped:** 2026-02-17
**Domain:** LENSES
**Phases:** 0-14 (15 phases)
**Requirements:** 60

**Key deliverables:**
- Design system tokens + 6 base components
- 12 lenses fully implemented (Receiving, Parts, Equipment, Fault, Work Order, Certificate, Handover, Hours of Rest, Warranty, Shopping List, Email)
- Cross-lens UX cleanup
- Gap remediation
- Handover export with editable signatures

---

### v1.1 — F1 Search Pipeline Hardening

**Shipped:** 2026-02-20
**Domain:** SEARCH
**Phases:** A-E (5 phases)
**Requirements:** 17

**Key deliverables:**
- Baseline metrics captured pre-deploy
- 25 commits deployed to production via PR #365
- Post-deploy validation with truth sets
- Root cause analysis: truth sets invalid (synthetic IDs)
- Search pipeline confirmed working (24.7% Recall@3 with valid IDs)

**Findings:**
- 96.38% failure rate was validation artifact, not search failure
- Truth set regeneration required for accurate metrics

---

### v1.2 — Search Snippet Enhancement

**Shipped:** 2026-02-26
**Domain:** SEARCH
**Phases:** Backend + Frontend (2 implicit phases)
**Requirements:** 5 (SNIP-01 through SNIP-05)

**Key deliverables:**
- `f1_search_cards` returns `search_text` column (migration 45)
- `generate_snippet()` function in `f1_search_streaming.py`
- SSE response includes snippet with **bold** highlighting
- `SpotlightResultRow.tsx` renders snippet with bold styling

---

### v1.3 — Actionable UX Unification

**Shipped:** 2026-03-03
**Domain:** LENSES
**Phases:** 15, 16, 16.1, 16.2, 17, 18, 19 (7 phases)
**Requirements:** 22

**Key deliverables:**
- IntentEnvelope abstraction (READ | MUTATE | MIXED)
- `/v1/actions/prepare` endpoint for prefill preview
- Readiness states (READY, NEEDS_INPUT, BLOCKED)
- Disambiguation UX for ambiguous entities
- RouteShell pattern (-4,262 LOC across 11 routes)
- PermissionService from lens_matrix.json
- 614 E2E Playwright tests across 12 lenses

---

## Parked Milestones

### v1.4 — Recall Improvement (PARKED)

**Started:** 2026-02-20
**Domain:** SEARCH
**Status:** Blocked on database migration deployment

**Blocker:** `50_enhance_search_text.sql` not deployed to production

**Current metrics:**
- Recall@3: 12.1%
- Target: 25-35% (after migration)

**To resume:**
```bash
psql $DATABASE_URL -f supabase/migrations/50_enhance_search_text.sql
```

---

## Phase Numbering

| Milestone | Domain | First Phase | Last Phase |
|-----------|--------|-------------|------------|
| v1.0 | LENSES | 0 | 14 |
| v1.1 | SEARCH | A | E |
| v1.2 | SEARCH | (implicit) | (implicit) |
| v1.3 | LENSES | 15 | 19 |
| v1.4 | SEARCH | A | D (parked) |

**Next available phase:** 20 (for lens work) or v1.4 Phase E (for search work)

---

*Last updated: 2026-03-03 — v1.3 milestone completed*
