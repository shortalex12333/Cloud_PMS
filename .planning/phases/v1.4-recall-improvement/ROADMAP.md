# v1.4 Roadmap — Recall Improvement

> **Goal:** Improve Recall@3 from 13.2% → 40% through text ranking optimization and search_text enhancement

**Created:** 2026-03-02
**Baseline:** v1.2 (Recall@3: 13.2%, Lens Accuracy: 46.2%)

---

## Architecture Analysis

### Current Search Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│  f1_search_cards (RRF Fusion)                                   │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  Trigram    │  │  Full-Text  │  │   Vector    │             │
│  │  pg_trgm    │  │  tsvector   │  │  pgvector   │             │
│  │             │  │             │  │             │             │
│  │ threshold:  │  │ ts_rank_cd  │  │ cosine sim  │             │
│  │ 0.15        │  │             │  │             │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
│         │                │                │                     │
│         └────────┬───────┴────────┬───────┘                     │
│                  ▼                ▼                              │
│         RRF Score = Σ 1/(k + rank_i)                            │
│         where k = 60 (smoothing constant)                       │
└─────────────────────────────────────────────────────────────────┘
```

### Identified Bottlenecks

| Issue | Evidence | Impact |
|-------|----------|--------|
| **No embeddings** | Harness passes NULL for p_embeddings | Vector signal disabled |
| **search_text quality** | Some lenses have poor text representation | Trigram/TSV mismatch |
| **Trigram threshold** | p_trgm_limit = 0.15 is permissive | Too many false positives |
| **No synonyms** | "WO" doesn't match "work order" | Query-text mismatch |

---

## Phases

### Phase A: Query Embedding Generation
**Goal:** Enable vector search signal in RRF fusion

**Tasks:**
1. Create embedding generation script using OpenAI ada-002
2. Add embedding cache to avoid re-generating
3. Update v12_recall_harness.py to use embeddings
4. Verify search_index has embeddings populated

**Success Criteria:**
- [ ] Harness passes real embeddings to f1_search_cards
- [ ] Vector signal contributes to RRF scores
- [ ] Recall@3 improves by at least 5%

**Files:**
- `scripts/eval/generate_query_embeddings.py` (new)
- `scripts/eval/v12_recall_harness.py` (modify)

---

### Phase B: Search Text Enhancement
**Goal:** Improve search_text quality for better trigram/TSV matching

**Tasks:**
1. Analyze search_text content for each object_type
2. Add common aliases/synonyms to search_text
3. Create migration to update search_text generation
4. Backfill existing records

**Synonyms to Add:**
```
work_order  → "work order WO task job"
fault       → "fault defect issue problem"
certificate → "cert certificate doc document"
equipment   → "equipment machine unit asset"
part        → "part spare component"
inventory   → "inventory stock parts spare"
```

**Success Criteria:**
- [ ] Queries like "show WOs" match work_order entities
- [ ] Lens Accuracy improves by 10%
- [ ] Recall@3 improves by 10%

**Files:**
- `database/migrations/XX_enhance_search_text.sql` (new)
- `scripts/backfill_search_text.py` (new)

---

### Phase C: RRF Parameter Tuning
**Goal:** Optimize fusion parameters for better ranking

**Tasks:**
1. Test different p_rrf_k values (30, 60, 100)
2. Test different p_trgm_limit thresholds (0.1, 0.15, 0.2)
3. Add weighted RRF option (favor vector over trigram)
4. Run grid search to find optimal parameters

**Experiments:**
| k | trgm_limit | Expected Effect |
|---|------------|-----------------|
| 30 | 0.15 | Favor top results more strongly |
| 60 | 0.20 | Stricter trigram matching |
| 100 | 0.10 | More uniform distribution |

**Success Criteria:**
- [ ] Grid search identifies optimal parameters
- [ ] Parameter change improves Recall@3 by 5%

**Files:**
- `scripts/eval/rrf_grid_search.py` (new)
- `database/migrations/XX_rrf_tuning.sql` (new - optional)

---

### Phase D: Validation & Metrics
**Goal:** Confirm improvements and update baseline

**Tasks:**
1. Run full 1,200 query evaluation
2. Generate comparison report (v1.2 vs v1.4)
3. Update STATE.md with new metrics
4. Document learnings

**Success Criteria:**
- [ ] Recall@3 >= 40% (3x improvement)
- [ ] Lens Accuracy >= 60%
- [ ] P95 latency <= 1000ms

**Files:**
- `.planning/phases/v1.4-recall-improvement/recall_report.md` (new)
- `.planning/STATE.md` (modify)

---

## Dependencies

```
Phase A (Embeddings) ──┐
                       ├──▶ Phase D (Validation)
Phase B (Search Text) ─┤
                       │
Phase C (RRF Tuning) ──┘
```

Phases A, B, C can run in parallel. Phase D requires all three to complete.

---

## Risk Analysis

| Risk | Mitigation |
|------|------------|
| OpenAI API rate limits | Use batch embedding API, cache results |
| Migration complexity | Test in staging first |
| Performance regression | Monitor P95 latency during experiments |
| Overfitting to test set | Use stratified sampling, cross-validate |

---

## Success Metrics

| Metric | v1.2 Baseline | v1.4 Target | Improvement |
|--------|---------------|-------------|-------------|
| Recall@3 | 13.2% | 40% | +200% |
| Lens Accuracy | 46.2% | 60% | +30% |
| P95 Latency | 721ms | ≤1000ms | No regression |

---

## Next Milestone (v1.5)

If v1.4 achieves 40% Recall@3:
- v1.5: Fine-tune embeddings + query expansion → 60%
- v1.6: Hybrid re-ranker + user feedback loop → 70%
