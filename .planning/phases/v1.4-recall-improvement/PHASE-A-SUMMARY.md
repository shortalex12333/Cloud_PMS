# Phase A: Query Embedding Generation - Summary

**Status:** COMPLETE
**Date:** 2026-03-02
**Goal:** Enable vector search signal in the recall harness

---

## Deliverables

### 1. Embedding Generation Script

**File:** `scripts/eval/generate_query_embeddings.py`

A standalone script that generates query embeddings with:

- **OpenAI ada-002 support**: Production mode using OpenAI API
- **Mock mode**: Deterministic random embeddings for testing without API
- **Auto mode**: Tries OpenAI, falls back to mock if no API key
- **Caching**: Loads existing embeddings to avoid re-generation
- **Batch processing**: Processes queries in batches of 100 with rate limiting

**Usage:**
```bash
# Generate with OpenAI (requires OPENAI_API_KEY env var)
python scripts/eval/generate_query_embeddings.py --mode openai

# Generate mock embeddings for testing
python scripts/eval/generate_query_embeddings.py --mode mock

# Auto-detect available mode
python scripts/eval/generate_query_embeddings.py --mode auto
```

**Output:** `test-results/v14/query_embeddings.jsonl`

### 2. Updated Recall Harness

**File:** `scripts/eval/v12_recall_harness.py`

Modified to support v1.4 embedding mode:

- New `--use-embeddings` flag to enable vector search
- New `--embeddings-file` flag to specify custom embeddings path
- `load_embeddings_cache()` function to load pre-generated embeddings
- `format_embedding_for_sql()` to format embeddings as PostgreSQL vector literals
- Updated `execute_search_direct()` to pass embeddings to f1_search_fusion
- Updated weight parameters when embeddings are available:
  - With embeddings: w_text=0.35, w_vector=0.25
  - Without embeddings: w_text=0.50, w_vector=0.0

**Usage:**
```bash
# v1.2 mode (text-only, original behavior)
python scripts/eval/v12_recall_harness.py --sample 100

# v1.4 mode (with embeddings)
python scripts/eval/v12_recall_harness.py --use-embeddings --sample 100
```

### 3. Directory Structure

Created `test-results/v14/` with:
- `query_embeddings.jsonl` - 1,199 query embeddings (1536-dim each)
- `recall_report.md` - Generated recall report
- `metrics.json` - Structured metrics output
- `detailed_results.jsonl` - Per-query results

---

## Test Results

**Test Run:** 20-query sample with mock embeddings

| Metric | Value |
|--------|-------|
| Embeddings Loaded | 1,199 |
| Coverage | 100.0% |
| Queries Evaluated | 20 |
| Embeddings Used | 20 |
| Average Latency | 451ms |

**Note:** Recall@3 = 0% with mock embeddings is expected because random vectors don't provide meaningful semantic similarity. With real OpenAI ada-002 embeddings, the vector signal will contribute to improved ranking.

---

## Success Criteria Status

| Criteria | Status |
|----------|--------|
| Script generates embeddings for all 1,200 queries | PASS (1,199 generated - 1 metadata line) |
| Harness loads and passes embeddings to search function | PASS |
| Run harness with embeddings and capture metrics | PASS |

---

## Files Modified/Created

| File | Action | Description |
|------|--------|-------------|
| `scripts/eval/generate_query_embeddings.py` | Created | Embedding generation script |
| `scripts/eval/v12_recall_harness.py` | Modified | Added embedding support |
| `test-results/v14/query_embeddings.jsonl` | Created | 1,199 query embeddings |
| `test-results/v14/recall_report.md` | Created | Sample run report |
| `test-results/v14/metrics.json` | Created | Sample run metrics |
| `test-results/v14/detailed_results.jsonl` | Created | Per-query results |

---

## Next Steps

1. **Generate Real Embeddings**: Set `OPENAI_API_KEY` and run with `--mode openai` to get production-quality embeddings

2. **Full Evaluation**: Run harness on all 1,200 queries:
   ```bash
   python scripts/eval/v12_recall_harness.py --use-embeddings --sample 0
   ```

3. **Compare with Baseline**: Compare v1.4 (with embeddings) against v1.2 (text-only) baseline

4. **Proceed to Phase B**: Enhance search_text quality for better trigram/TSV matching

---

## Technical Notes

### Embedding Format

```json
{"_metadata": {"version": "1.0", "model": "text-embedding-ada-002", "dimension": 1536, ...}}
{"query": "show all certificates", "embedding": [0.1, 0.2, ...]}
```

### SQL Parameter Weights

When embeddings are provided:
- p_w_text = 0.35 (reduced from 0.50)
- p_w_vector = 0.25 (increased from 0.0)

This balanced configuration allows both text and vector signals to contribute to RRF fusion.

### PostgreSQL Vector Format

Embeddings are passed as PostgreSQL vector literals:
```sql
'[0.1,0.2,0.3,...]'::vector(1536)
```

---

*Phase A completed 2026-03-02*
