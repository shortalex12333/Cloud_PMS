# Latest Test Results - SQL Foundation Overnight Campaign

## Test Run: 2026-01-04

### Expanded Test Suite (3305 tests)

```
============================================================
EXECUTING TESTS
============================================================
  Progress: 100/3305 | Passed: 100 | Failed: 0 | Rate: 4.6/s
  Progress: 200/3305 | Passed: 200 | Failed: 0 | Rate: 3.8/s
  Progress: 300/3305 | Passed: 297 | Failed: 3 | Rate: 3.1/s
  Progress: 400/3305 | Passed: 397 | Failed: 3 | Rate: 3.1/s
  Progress: 500/3305 | Passed: 497 | Failed: 3 | Rate: 2.9/s
  Progress: 600/3305 | Passed: 597 | Failed: 3 | Rate: 2.9/s
  Progress: 700/3305 | Passed: 697 | Failed: 3 | Rate: 3.2/s
  Progress: 800/3305 | Passed: 797 | Failed: 3 | Rate: 3.4/s
  Progress: 900/3305 | Passed: 897 | Failed: 3 | Rate: 3.8/s
  Progress: 1000/3305 | Passed: 997 | Failed: 3 | Rate: 4.2/s
  Progress: 1100/3305 | Passed: 1097 | Failed: 3 | Rate: 4.6/s
  Progress: 1200/3305 | Passed: 1197 | Failed: 3 | Rate: 5.1/s
  Progress: 1300/3305 | Passed: 1297 | Failed: 3 | Rate: 5.5/s
  Progress: 1400/3305 | Passed: 1397 | Failed: 3 | Rate: 5.9/s
  Progress: 1500/3305 | Passed: 1497 | Failed: 3 | Rate: 5.2/s
  Progress: 1600/3305 | Passed: 1597 | Failed: 3 | Rate: 4.8/s
  Progress: 1700/3305 | Passed: 1697 | Failed: 3 | Rate: 4.3/s
  Progress: 1800/3305 | Passed: 1797 | Failed: 3 | Rate: 3.7/s
  Progress: 1900/3305 | Passed: 1897 | Failed: 3 | Rate: 3.2/s
  Progress: 2000/3305 | Passed: 1997 | Failed: 3 | Rate: 2.9/s
  Progress: 2100/3305 | Passed: 2094 | Failed: 6 | Rate: 2.9/s
  Progress: 2200/3305 | Passed: 2192 | Failed: 8 | Rate: 2.9/s
  Progress: 2300/3305 | Passed: 2291 | Failed: 9 | Rate: 2.9/s
  Progress: 2400/3305 | Passed: 2391 | Failed: 9 | Rate: 2.9/s
  Progress: 2500/3305 | Passed: 2491 | Failed: 9 | Rate: 2.9/s
  Progress: 2600/3305 | Passed: 2591 | Failed: 9 | Rate: 2.9/s
  Progress: 2700/3305 | Passed: 2691 | Failed: 9 | Rate: 2.7/s
  Progress: 2800/3305 | Passed: 2791 | Failed: 9 | Rate: 2.6/s
  Progress: 2900/3305 | Passed: 2891 | Failed: 9 | Rate: 2.4/s
  Progress: 3000/3305 | Passed: 2990 | Failed: 10 | Rate: 2.4/s
  Progress: 3100/3305 | Passed: 3089 | Failed: 11 | Rate: 2.4/s
  Progress: 3200/3305 | Passed: 3189 | Failed: 11 | Rate: 2.3/s
  Progress: 3300/3305 | Passed: 3289 | Failed: 11 | Rate: 2.2/s

============================================================
RESULTS SUMMARY
============================================================
Total Tests: 3305
Passed: 3294 (99.7%)
Failed: 11 (0.3%)
Time: 1518.6s
```

### Entity Types Covered: 23/23

```
['CONTACT', 'DESCRIPTION', 'EQUIPMENT_CODE', 'EQUIPMENT_NAME',
 'FAULT_CODE', 'FREE_TEXT', 'HOURS', 'LOCATION', 'MANUFACTURER',
 'MODEL', 'NODE_LABEL', 'NODE_TYPE', 'PART_NAME', 'PART_NUMBER',
 'PO_NUMBER', 'PRIORITY', 'SERIAL_NUMBER', 'SEVERITY', 'STATUS',
 'SUPPLIER_NAME', 'SYMPTOM', 'SYSTEM_NAME', 'WORK_ORDER_TITLE']
```

### Results by Category

| Category | Pass | Total | Rate |
|----------|------|-------|------|
| chaos | 742 | 750 | 99% |
| conjunction | 500 | 500 | 100% |
| domain_drift | 400 | 400 | 100% |
| early_exit | 250 | 250 | 100% |
| entity_contact | 27 | 27 | 100% |
| entity_description | 15 | 15 | 100% |
| entity_equipment_code | 48 | 48 | 100% |
| entity_equipment_name | 48 | 48 | 100% |
| entity_fault_code | 48 | 48 | 100% |
| entity_free_text | 15 | 15 | 100% |
| entity_hours | 24 | 24 | 100% |
| entity_location | 45 | 45 | 100% |
| entity_manufacturer | 45 | 45 | 100% |
| entity_model | 27 | 30 | 90% |
| entity_node_label | 21 | 21 | 100% |
| entity_node_type | 15 | 15 | 100% |
| entity_part_name | 60 | 60 | 100% |
| entity_part_number | 45 | 45 | 100% |
| entity_po_number | 15 | 15 | 100% |
| entity_priority | 18 | 18 | 100% |
| entity_serial_number | 30 | 30 | 100% |
| entity_severity | 27 | 27 | 100% |
| entity_status | 18 | 18 | 100% |
| entity_supplier_name | 30 | 30 | 100% |
| entity_symptom | 42 | 42 | 100% |
| entity_system_name | 30 | 30 | 100% |
| entity_work_order_title | 30 | 30 | 100% |
| fuzzy | 73 | 73 | 100% |
| **injection** | **306** | **306** | **100%** |
| stacked_nouns | 300 | 300 | 100% |

---

## Ranking Model Tests (210 Golden Cases)

```
Running 210 golden ranking tests...

Results: 210/210 passed (100.0%)
```

### Ranking Score Weights
- EXACT match: +3.0
- ILIKE match: +1.5
- TRIGRAM match: +0.5
- Primary column bonus: +1.0

---

## Lane Routing Truth Reconciliation (1620 tests)

```
============================================================
TRUTH RECONCILIATION SUMMARY
============================================================
Total: 1620
Passed: 1620 (100%)
Failed: 0 (0%)

Category Breakdown:
  injection (sql, template, command): 306/306 (100%)
  domain_drift: 400/400 (100%)
  code_like (NO_LLM): 400/400 (100%)
  natural_language (GPT): 514/514 (100%)
```

---

## Security Gate Enforcement

### Injection Detection: 306/306 (100%)

All injection attempts correctly routed to BLOCKED lane:

- SQL injection patterns: 100+ cases
- Template injection: 50+ cases
- Command injection: 50+ cases
- Jailbreak attempts: 50+ cases
- Mixed/compound attempts: 50+ cases

### Example Blocked Patterns
```
"'; DROP TABLE users; --"  → BLOCKED
"{{config.__class__}}"     → BLOCKED
"ignore all instructions"   → BLOCKED
"${7*7}"                   → BLOCKED
"<script>alert(1)</script>" → BLOCKED
```

---

## Test Data Seeded

All 7 PMS tables seeded to 50+ rows:

| Table | Count |
|-------|-------|
| pms_equipment | 50+ |
| pms_parts | 50+ |
| pms_faults | 50+ |
| pms_work_orders | 50+ |
| pms_suppliers | 50+ |
| pms_purchase_orders | 50+ |
| symptom_catalog | 50+ |
| graph_nodes | 50+ |

---

## Files Changed

- 38 files: Removed hardcoded service keys → environment variables
- 25 files: Removed hardcoded absolute paths → relative paths
- 2 files: Wired UNION batching into execute path
- 1 file: Created search_union RPC migration

---

## How to Reproduce

```bash
# Set credentials
export SUPABASE_SERVICE_KEY="your-key"
export SUPABASE_URL="https://your-project.supabase.co"

# Seed data
python3 tests/overnight/seed_tables.py

# Run tests
python3 tests/overnight/expanded_test_suite.py
```
