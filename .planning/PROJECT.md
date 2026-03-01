# CelesteOS — Cloud PMS

> **Vision**: Intent-first maritime vessel management platform with AI-powered lenses.

---

## Current Milestone: v1.3 — Actionable UX Unification

**Goal:** Unify READ + MUTATE intent into a holistic NLP → Deterministic Action system with prefill preview, readiness states, and fragmented route leverage.

**Target deliverables:**
- IntentEnvelope abstraction in SpotlightSearch (READ | MUTATE | MIXED)
- `/v1/actions/prepare` endpoint for prefill preview
- Readiness states (READY, NEEDS_INPUT, BLOCKED) with visual indicators
- Canonical fragmented URLs for READ navigation
- Disambiguation UX for ambiguous entities
- 24 agent deployment across 4 waves (Lens Matrix, NLP Variants, Backend Integration, E2E Tests)

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

## Active (v1.3)

### Intent Envelope
- [ ] **INTENT-01**: IntentEnvelope type captures query, lens, mode, filters, actions, entities, readiness
- [ ] **INTENT-02**: Envelope derived from Action Detector + Entity Extractor + filter inference
- [ ] **INTENT-03**: Deterministic: same query → same structured output

### Prefill Integration
- [ ] **PREFILL-01**: `/v1/actions/prepare` endpoint accepts action_id, query, extracted_entities
- [ ] **PREFILL-02**: Returns prefill_preview, missing_fields, confidence
- [ ] **PREFILL-03**: Resolves equipment names → IDs via yacht-scoped lookups
- [ ] **PREFILL-04**: Maps priority synonyms → enum values
- [ ] **PREFILL-05**: Parses temporal phrases → ISO dates

### Readiness States
- [ ] **READY-01**: READY state when all required_fields resolved confidently
- [ ] **READY-02**: NEEDS_INPUT state when fields missing or ambiguous
- [ ] **READY-03**: BLOCKED state when role/RLS denies
- [ ] **READY-04**: Visual indicators: green check (READY), amber dot (NEEDS_INPUT), lock (BLOCKED)

### Fragmented Routes
- [ ] **ROUTE-01**: READ suggestions generate canonical URLs (segments, not query params)
- [ ] **ROUTE-02**: URLs like `/work-orders/status/open`, `/inventory/location/box-3d`
- [ ] **ROUTE-03**: Filter chips in UI reflect canonical route segments

### Disambiguation UX
- [ ] **DISAMB-01**: Ambiguous entities render dropdown in modal ("Did you mean: ME1 / ME2?")
- [ ] **DISAMB-02**: Uncertain date parsing highlights scheduled date field
- [ ] **DISAMB-03**: Never silently assume — always surface uncertainty

### Agent Deployment
- [ ] **AGENT-01**: Wave 1 — 6 Lens Matrix agents produce lens_matrix.json
- [ ] **AGENT-02**: Wave 2 — 6 NLP Variant agents produce intent_truth_set.json (100 variants/lens)
- [ ] **AGENT-03**: Wave 3 — 6 Backend Integration agents implement /prepare, mappings, role gating
- [ ] **AGENT-04**: Wave 4 — 6 E2E Test agents with 50+ tests per lens via Playwright

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| New inference systems | Use existing Action Detector + Entity Extractor |
| Client-side regex override | Backend entity extraction is authoritative |
| Hidden auto-mutations | All actions require explicit user confirmation |
| New duplicate files | Modify existing: useCelesteSearch.ts, SuggestedActions.tsx, ActionModal.tsx, prefill_engine.py |

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
*Last updated: 2026-03-01 — Milestone v1.3 Actionable UX Unification started*
