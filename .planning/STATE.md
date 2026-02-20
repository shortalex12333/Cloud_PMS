# STATE — Current Session Memory

> **This file tracks decisions, blockers, and position across sessions.**
>
> Last Updated: 2026-02-19

---

## Current Position

| Field | Value |
|-------|-------|
| Milestone | v1.1 — F1 Search Pipeline Hardening |
| Phase | Not started (defining requirements) |
| Plan | — |
| Status | Milestone initialized, roadmap pending |
| Last activity | 2026-02-19 — Milestone v1.1 started |

---

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-02-19)

**Core value:** Validate search pipeline with deterministic truth sets before and after deployment.

**Current focus:** Baseline → Deploy → Validate cycle

---

## Milestone v1.1 Summary

| # | Phase | Goal | Requirements | Status |
|---|-------|------|--------------|--------|
| A | Baseline | Run truth sets against current production | SRCH-01 | ○ Pending |
| B | Deploy | Push clean codebase to main | SRCH-02 | ○ Pending |
| C | Validate | Run truth sets against new production | SRCH-03, SRCH-04 | ○ Pending |
| D | Compare | Diff baseline vs post-deploy | SRCH-04, SRCH-05 | ○ Pending |
| E | Iterate | Fix any regressions | All | ○ Pending |

---

## Decisions Made

| Decision | Rationale | Date |
|----------|-----------|------|
| All test files in /test/ only | User directive: no codebase pollution | 2026-02-19 |
| Use existing truth sets | 9 CSVs × 25 items × 12 variations = 2,700 queries | 2026-02-19 |
| Deploy first, then validate | AbortError fix exists locally, needs deployment | 2026-02-19 |
| Baseline before deploy | Capture current state for regression detection | 2026-02-19 |
| GSD agents for execution | User directive: orchestrate, don't execute directly | 2026-02-19 |

---

## Blockers

| Blocker | Impact | Owner | Status |
|---------|--------|-------|--------|
| None identified | — | — | — |

---

## Accumulated Context

### From v1.0 Milestone
- 14 phases complete (60 requirements)
- All lenses rebuilt with design system
- E2E tests passing
- Ledger triggers verified

### Search Infrastructure
- 50+ search functions exist in Supabase
- `f1_search_fusion` (26 args), `f1_search_cards` (7 args) confirmed
- AbortError fix at `useCelesteSearch.ts:534-548`
- Local codebase 18+ commits ahead of production

### Truth Sets Location
- `/Volumes/Backup/CELESTE/` contains:
  - certificate.csv + truthset_certificate.md/jsonl
  - document.csv + truthset_document.md/jsonl
  - fault.csv + truthset_fault.md/jsonl
  - inventory.csv + truthset_inventory.md/jsonl
  - parts.csv + truthset_parts.md/jsonl
  - receiving.csv + truthset_receiving.md/jsonl
  - shopping_list.csv + truthset_shopping_list.md/jsonl
  - work_order_note.csv + truthset_work_order_note.md/jsonl
  - work_order.csv + truthset_work_order.md/jsonl

### Testing Protocol
1. Load truth set JSONL
2. For each query → call search endpoint
3. Check if expected IDs in top 3 results
4. Calculate: Recall@3, MRR, failure list
5. Record to `/test/` directory

---

## Session Notes

### 2026-02-19 (Session 1)
- Context restored from compacted session
- Confirmed: SQL functions ALREADY exist in Supabase (not missing)
- Confirmed: AbortError fix EXISTS in local code (not missing)
- Problem: Code not deployed to production (18+ commits behind)
- Cleaned up unnecessary SQL migration files created in error
- Started milestone v1.1 for search pipeline hardening

---

## Next Single Action

**Define REQUIREMENTS.md and ROADMAP.md for v1.1 milestone.**
