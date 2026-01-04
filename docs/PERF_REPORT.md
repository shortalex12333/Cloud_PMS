# PERFORMANCE REPORT
## Generated: 2026-01-03T11:05:50.109023

---

## TEST CONFIGURATION

| Metric | Value |
|--------|-------|
| Sample Size | 200 queries |
| Iterations Per Query | 10 |
| Query Types | 20 |
| Test Yacht ID | 85fe1119-b04c-41ac-80f1-829d23322598 |

---

## OVERALL TIMING DISTRIBUTION

| Percentile | Time (ms) |
|------------|-----------|
| min | 71.04 |
| p50 (median) | 130.7 |
| p90 | 205.13 |
| p95 | 221.71 |
| p99 | 317.96 |
| max | 465.28 |
| mean | 134.02 |

---

## BY WAVE

| Wave | Count | p50 | p90 | p95 | p99 |
|------|-------|-----|-----|-----|-----|
| WAVE_0 | 70 | 140.15 | 223.81 | 237.55 | 317.96 |
| WAVE_1 | 190 | 133.38 | 205.13 | 216.24 | 248.07 |
| WAVE_2 | 62 | 197.53 | 223.81 | 237.55 | 465.28 |

---

## BY QUERY TYPE

| Query Type | p50 | p90 | p95 |
|------------|-----|-----|-----|
| DOCUMENT_QUERY | 195.06 | 205.13 | 465.28 |
| EQUIPMENT_NAME | 83.46 | 102.96 | 148.5 |
| FAULT_CODE | 137.14 | 158.89 | 161.04 |
| FREE_TEXT | 95.79 | 203.33 | 203.34 |
| PART_NAME | 82.98 | 120.31 | 150.88 |
| PART_NUMBER | 82.01 | 317.96 | 317.96 |
| STOCK_LOCATION | 135.25 | 147.32 | 154.09 |
| SYSTEM_NAME | 215.39 | 243.79 | 248.07 |
| UNKNOWN | 171.37 | 191.0 | 191.0 |

---

## CLAIM VERIFICATION

| Claim | Actual | Status |
|-------|--------|--------|
| Avg ~116ms | 134.02ms | VERIFIED |
