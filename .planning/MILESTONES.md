# MILESTONES — CelesteOS Cloud PMS

> **History of completed milestones and their key deliverables.**

---

## Completed Milestones

### v1.0 — Lens Completion

**Shipped:** 2026-02-17
**Phases:** 0-14 (15 phases)
**Requirements:** 60

**Key deliverables:**
- Design system tokens + 6 base components
- 12 lenses fully implemented (Receiving, Parts, Equipment, Fault, Work Order, Certificate, Handover, Hours of Rest, Warranty, Shopping List, Email)
- Cross-lens UX cleanup
- Gap remediation
- Handover export with editable signatures

**Last phase:** 14 (Handover Export Editable)

---

### v1.1 — F1 Search Pipeline Hardening

**Shipped:** 2026-02-20
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
**Phases:** Backend + Frontend (2 implicit phases)
**Requirements:** 5 (SNIP-01 through SNIP-05)

**Key deliverables:**
- `f1_search_cards` returns `search_text` column (migration 45)
- `generate_snippet()` function in `f1_search_streaming.py`
- SSE response includes snippet with **bold** highlighting
- `SpotlightResultRow.tsx` renders snippet with bold styling
- Full verification complete

---

## Current Milestone

### v1.3 — Actionable UX Unification

**Started:** 2026-03-01
**Phases:** 15-19 (5 phases)
**Requirements:** 22

**Target deliverables:**
- IntentEnvelope abstraction (READ | MUTATE | MIXED)
- `/v1/actions/prepare` endpoint for prefill preview
- Readiness states (READY, NEEDS_INPUT, BLOCKED)
- Canonical fragmented URLs for READ navigation
- Disambiguation UX for ambiguous entities
- 24 agent deployment across 4 waves

---

## Phase Numbering

| Milestone | First Phase | Last Phase |
|-----------|-------------|------------|
| v1.0 | 0 | 14 |
| v1.1 | A | E |
| v1.2 | (implicit) | (implicit) |
| v1.3 | 15 | 19 |

**Next phase number:** 15

---
*Last updated: 2026-03-01 — v1.3 milestone started*
