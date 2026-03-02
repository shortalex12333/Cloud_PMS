# v1.2 — Search Pipeline Truth Hardening

> **Goal**: Fix false recall metrics by using real production entity IDs, validate button rendering across difficulty tiers, and implement confidence-based fallback to search.

---

## Phase Summary

| Phase | Goal | Deliverable |
|-------|------|-------------|
| A | Regenerate truth sets | `truth_sets/` with real entity UUIDs from production |
| B | Map difficulty tiers | Each query classified as easy/medium/hard |
| C | Validate button rendering | E2E tests proving buttons render per intent |
| D | Confidence-based fallback | Route low-confidence queries to search |
| E | Measure final Recall | Accurate baseline with real data |

---

## Phase A: Regenerate Truth Sets with Real IDs

### Objective
Query production database for real entity UUIDs per lens, match to existing 1,200 NLP variants.

### Steps
1. Query each entity table with `yacht_id` scope
2. Sample 25 entities per lens (matching existing truth set size)
3. Map queries to real entity IDs
4. Output: `truth_sets/{lens}_truth.jsonl`

### Success Criteria
- [ ] 12 truth set files created
- [ ] Each file has real UUIDs (not synthetic inventory_item IDs)
- [ ] All IDs exist in production database

---

## Phase B: Map NLP Variants to Difficulty Tiers

### Objective
Classify each of 1,200 queries into difficulty tiers based on linguistic complexity.

### Tiers
| Tier | Difficulty | Criteria | Expected Recall |
|------|------------|----------|-----------------|
| 1 | Easy | Single keyword, direct match (e.g., "show work orders") | 95%+ |
| 2 | Medium | Entity reference (e.g., "work orders for engine room") | 75%+ |
| 3 | Hard | Compound/ambiguous (e.g., "that thing I was looking at yesterday") | 50%+ |
| 4 | Fallback | Unrecognizable → route to search | N/A |

### Steps
1. Parse each query for entity references
2. Count filter complexity
3. Check for temporal/contextual references
4. Assign tier 1-4

### Success Criteria
- [ ] All 1,200 queries have difficulty tier
- [ ] Distribution: ~40% easy, ~35% medium, ~20% hard, ~5% fallback

---

## Phase C: Validate Button Rendering Across Tiers

### Objective
Ensure buttons render correctly based on intent classification.

### Test Matrix
| Query Tier | Expected UX |
|------------|-------------|
| Easy READ | Navigate button → instant filter |
| Easy MUTATE | Execute button → prefilled modal |
| Medium READ/MUTATE | Requires entity resolution → render if resolved |
| Hard | Show suggestions with confidence indicator |
| Fallback | No button → search results only |

### Steps
1. Run queries through IntentEnvelope derivation
2. Verify button visibility matches tier
3. Verify modal prefill for MUTATE actions

### Success Criteria
- [ ] 100% button render accuracy for Tier 1
- [ ] 90%+ button render accuracy for Tier 2
- [ ] 70%+ for Tier 3
- [ ] 0% false buttons for Tier 4 (must fallback)

---

## Phase D: Implement Confidence-Based Fallback

### Objective
Route queries below confidence threshold to existing RAG/QL search pipeline.

### Architecture
```
USER QUERY
    ↓
INTENT PIPELINE (IntentEnvelope)
    ↓
CONFIDENCE CHECK
    ├── >= 0.7: RENDER BUTTONS (Navigate/Execute)
    └── < 0.7: FALLBACK TO SEARCH
                    ↓
           /api/search/fallback (existing)
```

### Implementation
1. Add `confidence` threshold check in `useCelesteSearch.ts`
2. Route to existing fallback mechanism when below threshold
3. Log confidence values for analysis

### Success Criteria
- [ ] Confidence threshold configurable (default 0.7)
- [ ] Low-confidence queries show search results (no buttons)
- [ ] No silent failures — always show something useful

---

## Phase E: Measure End-to-End Recall with Real Data

### Objective
Run full evaluation harness with regenerated truth sets.

### Metrics
| Metric | Target | Rationale |
|--------|--------|-----------|
| Recall@3 (Easy) | 90%+ | Direct matches should hit |
| Recall@3 (Medium) | 70%+ | Entity resolution required |
| Recall@3 (Hard) | 50%+ | Ambiguity expected |
| Overall Recall@3 | 70%+ | Weighted average |
| P95 Latency | < 500ms | UX requirement |

### Steps
1. Run `ranking_truth_harness.py` with new truth sets
2. Generate comparison report
3. Identify remaining gaps for v1.3

### Success Criteria
- [ ] Overall Recall@3 >= 70%
- [ ] No regression from current baseline (3.62% was invalid metric)
- [ ] Report generated with per-tier breakdown

---

## Dependencies

```
A (Truth Sets) → B (Difficulty Tiers) → C (Button Validation) → E (Metrics)
                                      ↓
                                      D (Fallback) → E (Metrics)
```

---

## Files Modified

| File | Changes |
|------|---------|
| `scripts/eval/ranking_truth_harness.py` | Load new truth sets, add tier filtering |
| `apps/web/src/hooks/useCelesteSearch.ts` | Add confidence threshold routing |
| `.planning/agents/nlp-variants/intent_truth_set.jsonl` | Add difficulty_tier field |
| NEW: `truth_sets/{lens}_truth.jsonl` | Real entity IDs per lens |

---

## Timeline

Single execution burst — all phases via parallel agents.
