# Search Pipeline Comparison Report

**Generated:** 2026-02-20T03:47:24.205Z

**Baseline:** 2026-02-20T02:51:08.442Z
**Post-Deploy:** 2026-02-20T03:41:39.285Z

---

## Executive Summary

Total queries evaluated: **2400**

| Category | Count | Percentage |
|----------|-------|------------|
| Improved | 2 | 0.08% |
| Regressed | 1 | 0.04% |
| Unchanged (Hit) | 85 | 3.54% |
| Unchanged (Miss) | 2312 | 96.33% |

---

## Overall Metrics Comparison

| Metric | Baseline | Post-Deploy | Delta | Change |
|--------|----------|-------------|-------|--------|
| **Recall@3** | 3.58% | 3.62% | 0.0417% | 1.16% |
| **MRR** | 0.0269 | 0.0274 | 0.0005 | 1.91% |
| **P95 Latency** | 19545ms | 16585ms | -2960ms | -15.14% |

---

## Per-Entity Breakdown

### certificate (60 queries)

| Metric | Baseline | Post-Deploy | Delta |
|--------|----------|-------------|-------|
| Recall@3 | 0.00% | 0.00% | 0.0000% |
| MRR | 0.0000 | 0.0000 | 0.0000 |
| Avg Latency | 6371ms | 6634ms | 263ms |
| **Improved** | - | - | **0** |
| **Regressed** | - | - | **0** |

### document (240 queries)

| Metric | Baseline | Post-Deploy | Delta |
|--------|----------|-------------|-------|
| Recall@3 | 0.00% | 0.00% | 0.0000% |
| MRR | 0.0000 | 0.0000 | 0.0000 |
| Avg Latency | 5629ms | 5733ms | 105ms |
| **Improved** | - | - | **0** |
| **Regressed** | - | - | **0** |

### fault (300 queries)

| Metric | Baseline | Post-Deploy | Delta |
|--------|----------|-------------|-------|
| Recall@3 | 0.00% | 0.00% | 0.0000% |
| MRR | 0.0000 | 0.0000 | 0.0000 |
| Avg Latency | 10387ms | 10549ms | 162ms |
| **Improved** | - | - | **0** |
| **Regressed** | - | - | **0** |

### inventory (300 queries)

| Metric | Baseline | Post-Deploy | Delta |
|--------|----------|-------------|-------|
| Recall@3 | 0.00% | 0.00% | 0.0000% |
| MRR | 0.0000 | 0.0000 | 0.0000 |
| Avg Latency | 6968ms | 7074ms | 106ms |
| **Improved** | - | - | **0** |
| **Regressed** | - | - | **0** |

### parts (300 queries)

| Metric | Baseline | Post-Deploy | Delta |
|--------|----------|-------------|-------|
| Recall@3 | 24.67% | 24.67% | 0.0000% |
| MRR | 0.1745 | 0.1716 | -0.0029 |
| Avg Latency | 8595ms | 8666ms | 71ms |
| **Improved** | - | - | **1** |
| **Regressed** | - | - | **1** |

### receiving (300 queries)

| Metric | Baseline | Post-Deploy | Delta |
|--------|----------|-------------|-------|
| Recall@3 | 4.00% | 4.00% | 0.0000% |
| MRR | 0.0400 | 0.0400 | 0.0000 |
| Avg Latency | 7933ms | 4828ms | -3105ms |
| **Improved** | - | - | **0** |
| **Regressed** | - | - | **0** |

### shopping_list (300 queries)

| Metric | Baseline | Post-Deploy | Delta |
|--------|----------|-------------|-------|
| Recall@3 | 0.00% | 0.00% | 0.0000% |
| MRR | 0.0010 | 0.0010 | 0.0000 |
| Avg Latency | 4967ms | 7853ms | 2887ms |
| **Improved** | - | - | **0** |
| **Regressed** | - | - | **0** |

### work_order_note (300 queries)

| Metric | Baseline | Post-Deploy | Delta |
|--------|----------|-------------|-------|
| Recall@3 | 0.00% | 0.00% | 0.0000% |
| MRR | 0.0000 | 0.0000 | 0.0000 |
| Avg Latency | 4597ms | 5704ms | 1107ms |
| **Improved** | - | - | **0** |
| **Regressed** | - | - | **0** |

### work_order (300 queries)

| Metric | Baseline | Post-Deploy | Delta |
|--------|----------|-------------|-------|
| Recall@3 | 0.00% | 0.33% | 0.3333% |
| MRR | 0.0000 | 0.0070 | 0.0070 |
| Avg Latency | 9433ms | 4881ms | -4552ms |
| **Improved** | - | - | **1** |
| **Regressed** | - | - | **0** |

---

## Top 10 Improved Queries

1. **work_order**: "find w-0056: generator 2 belt inspection"
   - Baseline: Miss
   - Post-Deploy: Rank 1
   - Change: -998 ranks

2. **parts**: "stock count coolant thermostat"
   - Baseline: Miss
   - Post-Deploy: Rank 3
   - Change: -996 ranks

---

## Top 10 Regressed Queries

1. **parts**: "show bearing main onboard"
   - Baseline: Rank 1
   - Post-Deploy: Miss
   - Change: +998 ranks

---

## Recommendations

### Positive Outcome

- Recall@3 improved by 0.0417%
- Latency improved or stayed neutral
- **Recommendation:** Monitor in production for sustained improvement

---

## Acceptance Criteria Check

### Criterion 1: Recall@3 >= 90%

- **Target:** 90%
- **Actual:** 3.62%
- **Status:** ✗ NOT MET

### Criterion 2: No Latency Regression

- **Baseline P95:** 19545ms
- **Post-Deploy P95:** 16585ms
- **Delta:** -2960ms (-15.14%)
- **Status:** ✓ MET

### Overall Verdict

**✗ CRITERIA NOT MET** - Phase E (Iterate) required to address:
- Recall@3 is 86.38% below target

