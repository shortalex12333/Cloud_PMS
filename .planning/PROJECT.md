# CelesteOS — Cloud PMS

> **Vision**: Intent-first maritime vessel management platform with AI-powered lenses.

---

## Current Milestone: v1.1 — F1 Search Pipeline Hardening

**Goal:** Deploy clean codebase to production and validate search pipeline with deterministic truth sets.

**Target deliverables:**
- Baseline metrics from current production (pre-deploy)
- Clean codebase deployed (18+ commits including AbortError fix)
- Post-deploy validation with 2,700 truth set queries
- Recall@3, MRR metrics recorded in `/test/`
- Regression report if metrics degrade

---

## Scope: Full Stack (Search Pipeline Focus)

**Role**: Full stack for search infrastructure validation.

**Focus Areas**:
- Search pipeline validation (RRF fusion, embeddings)
- Truth set test harness in `/test/`
- Deployment verification
- Metric recording and comparison

---

## Technical Stack

| Layer | Technology |
|-------|------------|
| Framework | Next.js 14, React, FastAPI |
| Database | Supabase (PostgreSQL + pgvector) |
| Search | RRF fusion (`f1_search_fusion`), HNSW index |
| Testing | Truth sets (9 CSVs × 25 items × 12 variations) |
| Deployment | Vercel (frontend), Render (API) |

---

## Architecture: F1-Spec Kappa

1. **Single Stream** — Unified `search_index` table
2. **RRF Fusion** — Text + trigram + vector combined
3. **AbortError Handling** — New AbortController for fallback (not reused)
4. **Multi-tenant** — yacht_id isolation

---

## Validated (v1.0 Complete)

- 14 lens phases complete (60 requirements)
- Design system tokens + components
- All E2E tests passing
- Ledger triggers verified

---

## Active (v1.1)

- [ ] **SRCH-01**: Baseline metrics recorded before deployment
- [ ] **SRCH-02**: Clean codebase deployed to production
- [ ] **SRCH-03**: Post-deploy validation with truth sets
- [ ] **SRCH-04**: Recall@3 ≥ 90% on truth set queries
- [ ] **SRCH-05**: No regression in search response time

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| New search features | Hardening only, no new functionality |
| UI changes | Infrastructure focus |
| Additional truth sets | 9 CSVs sufficient for v1.1 |

---

## References

- `/Volumes/Backup/CELESTE/` — Truth set CSVs and JSONL files
- `/test/` — Test scripts and metric records (ONLY location for new files)
- `apps/web/src/hooks/useCelesteSearch.ts` — AbortError fix location

---

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Test files in /test/ only | User directive: no pollution | — Pending |
| Truth sets as validation | Deterministic, no guessing | — Pending |
| Deploy before optimize | Fix is in local code, needs deployment | — Pending |

---
*Last updated: 2026-02-19 — Milestone v1.1 started*
