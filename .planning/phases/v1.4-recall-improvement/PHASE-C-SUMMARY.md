# Phase C: RRF Parameter Tuning - Implementation Summary

**Status:** Implementation Complete (Pending Execution)
**Created:** 2026-03-02

---

## Deliverables

### 1. Grid Search Script

**File:** `scripts/eval/rrf_grid_search.py`

The script implements a comprehensive grid search over RRF fusion parameters:

#### Parameters Tested
- **p_rrf_k**: [30, 60, 100] - RRF smoothing constant
- **p_trgm_limit**: [0.10, 0.15, 0.20, 0.25] - Trigram similarity threshold

#### Metrics Captured
| Metric | Description |
|--------|-------------|
| **Recall@3** | Whether truth entity appears in top 3 results |
| **Lens Accuracy** | Whether top-1 result type matches expected lens |
| **Avg Latency** | Mean response time in milliseconds |
| **P95 Latency** | 95th percentile response time |
| **Hits** | Count of queries with truth entity in top 3 |
| **Errors** | Count of failed queries |

### 2. Parameter Override Implementation

The `execute_search_f1_cards()` function accepts custom RRF parameters:

```python
def execute_search_f1_cards(
    conn,
    query: str,
    yacht_id: str,
    org_id: Optional[str],
    lens: str,
    rrf_k: int,          # Customizable: 30, 60, 100
    trgm_limit: float,   # Customizable: 0.10, 0.15, 0.20, 0.25
    limit: int = 10,
) -> Tuple[List[Dict], float]:
```

### 3. Results Matrix Output

Output location: `test-results/rrf-grid/results_matrix.md`

Expected format:
```
| k   | trgm | Recall@3 | Lens Acc | Avg Latency | P95 Latency | Hits | Errors |
|-----|------|----------|----------|-------------|-------------|------|--------|
| 30  | 0.10 | ?%       | ?%       | ?ms         | ?ms         | ?    | ?      |
| 30  | 0.15 | ?%       | ?%       | ?ms         | ?ms         | ?    | ?      |
| ... | ...  | ...      | ...      | ...         | ...         | ...  | ...    |
```

---

## Usage

### Basic Execution
```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS
OPENAI_API_KEY=<your-key> python3 scripts/eval/rrf_grid_search.py
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--sample` | 75 | Number of queries to sample |
| `--yacht-id` | 85fe1119-b04c-41ac-80f1-829d23322598 | Yacht ID |
| `--seed` | 42 | Random seed for reproducibility |
| `--rrf-k` | 30,60,100 | Custom RRF K values (comma-separated) |
| `--trgm` | 0.10,0.15,0.20,0.25 | Custom trigram thresholds |
| `--quick` | False | Quick mode: fewer params, smaller sample |

### Quick Mode
```bash
python3 scripts/eval/rrf_grid_search.py --quick
```
Tests only k=[30,60] and trgm=[0.10,0.15] with 50 queries.

---

## Technical Details

### f1_search_cards Signature

```sql
CREATE OR REPLACE FUNCTION public.f1_search_cards(
    p_texts TEXT[],                    -- Array of query text rewrites
    p_embeddings VECTOR(1536)[],       -- Array of embeddings
    p_org_id UUID,                     -- Organization ID
    p_yacht_id UUID,                   -- Yacht ID
    p_rrf_k INT DEFAULT 60,            -- RRF smoothing constant
    p_page_limit INT DEFAULT 20,       -- Max results
    p_trgm_limit REAL DEFAULT 0.15,    -- Trigram threshold
    p_object_types TEXT[] DEFAULT NULL -- Filter to object types
)
```

### RRF Formula

```
score = SUM(1/(k + rank_i)) for each ranking signal

where:
- k = smoothing constant (higher = more uniform distribution)
- rank_i = 1-indexed position in each source (trigram, TSV, vector)
```

### Expected Behavior by Parameter

| k | Effect |
|---|--------|
| 30 | Favors top results more strongly (steeper ranking curve) |
| 60 | Balanced (current default) |
| 100 | More uniform distribution (flatter ranking curve) |

| trgm | Effect |
|------|--------|
| 0.10 | More permissive trigram matching (more false positives) |
| 0.15 | Balanced (current default) |
| 0.20 | Stricter matching (fewer matches, higher precision) |
| 0.25 | Very strict (may miss fuzzy matches) |

---

## Outputs

### Files Generated

1. **`test-results/rrf-grid/results_matrix.md`** - Human-readable report
2. **`test-results/rrf-grid/grid_results.json`** - Full results data
3. **`test-results/rrf-grid/best_config.json`** - Optimal parameters

### Best Config Format

```json
{
  "timestamp": "2026-03-02T...",
  "best_params": {
    "p_rrf_k": 60,
    "p_trgm_limit": 0.15
  },
  "metrics": {
    "recall_at_3": 0.45,
    "lens_accuracy": 0.52,
    "avg_latency_ms": 450
  }
}
```

---

## Success Criteria

| Criterion | Status |
|-----------|--------|
| Grid search covers all parameter combinations | COMPLETE |
| Results matrix shows clear winner | PENDING (requires execution) |
| Optimal parameters documented | PENDING (requires execution) |

---

## Next Steps

1. **Execute grid search** with `OPENAI_API_KEY` set
2. **Review results** in `test-results/rrf-grid/results_matrix.md`
3. **Update production parameters** if improvement found
4. **Document optimal configuration** in project STATE.md

---

## Dependencies

- Python 3.9+
- psycopg2-binary
- openai (for embedding generation)
- OPENAI_API_KEY environment variable
- Database access to Supabase production

---

*Phase C implemented by RRF Grid Search script. Execute to generate results.*
