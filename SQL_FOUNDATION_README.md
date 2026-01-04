# SQL Foundation Module - prepare-module Branch

## Overview

This branch contains the **SQL Foundation** - a complete, secure, and tested search infrastructure for yacht PMS data. It provides a unified PREPARE → EXECUTE → RANK pipeline that replaces ad-hoc per-table REST calls with proper batched SQL execution.

---

## What We're Achieving

### The Problem
- Search queries were hitting tables individually via REST (N+1 problem)
- No consistent security enforcement across search paths
- Hardcoded credentials and paths scattered across 40+ files
- No proper ranking or relevance scoring
- Mixed READ and WRITE paths causing confusion

### The Solution
A three-stage pipeline with strict separation:

```
┌─────────────────────────────────────────────────────────────────┐
│                       SQL FOUNDATION                            │
├─────────────────────────────────────────────────────────────────┤
│  QUERY → PREPARE → EXECUTE → RANK → RESPONSE                   │
│                                                                 │
│  PREPARE:                                                       │
│    • Lane routing (BLOCKED/UNKNOWN/NO_LLM/GPT)                  │
│    • Security validation (injection blocking)                  │
│    • Term expansion (synonyms, variants)                        │
│    • Table bias scoring                                         │
│    • Batch planning                                             │
│                                                                 │
│  EXECUTE:                                                       │
│    • UNION ALL batching (true SQL, not REST per-table)          │
│    • Wave progression (EXACT → ILIKE → TRIGRAM)                 │
│    • Early exit (stop when enough results)                      │
│    • RPC with REST fallback                                     │
│                                                                 │
│  RANK:                                                          │
│    • Match type scoring (EXACT +3.0, ILIKE +1.5, TRIGRAM +0.5)  │
│    • Table bias weighting                                       │
│    • Entity confidence integration                              │
│    • Relevance-sorted output                                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
api/
├── sql_foundation/           # Core SQL Foundation module
│   ├── ARCHITECTURE.md       # Detailed architecture documentation
│   ├── __init__.py           # Module exports
│   ├── prepare.py            # PREPARE stage: lane routing, term expansion
│   ├── execute.py            # EXECUTE stage: per-table REST (fallback)
│   ├── execute_union.py      # EXECUTE stage: true UNION ALL batching
│   ├── ranking.py            # RANK stage: relevance scoring
│   ├── sql_variants.py       # SQL generation for all input combinations
│   ├── column_config.py      # Table/column metadata configuration
│   ├── operators.py          # SQL operators (EXACT, ILIKE, TRIGRAM)
│   ├── bbws_search.py        # Integration wrapper for /v2/search
│   └── generate_sql.py       # SQL generation utilities
│
├── microaction_service.py    # Main API service with BBWS integration
├── entity_extraction_loader.py  # Entity extraction pipeline
└── module_a_action_detector.py  # Action/intent detection

tests/
├── overnight/                # Overnight validation suite
│   ├── expanded_test_suite.py  # 3305 tests across 23 entity types
│   ├── seed_tables.py        # Database seeding (50+ rows per table)
│   └── seed_and_test.py      # Combined seed + test runner
│
├── golden/                   # Golden truth test cases
├── sql_stress/               # SQL stress testing
├── stress_campaign/          # Production stress testing
└── search_tests/             # Search-specific tests

supabase/
└── migrations/
    └── 20260104_search_union_rpc.sql  # UNION RPC function for Supabase

docs/
├── ARCHITECTURE.md           # High-level architecture
├── SQL_EXECUTION_ARCHITECTURE.md  # SQL execution details
├── SQL_SEARCH_ARCHITECTURE.md     # Search flow documentation
└── ...                       # Various audit and analysis docs
```

---

## Key Files Explained

### Core Pipeline

| File | Purpose |
|------|---------|
| `api/sql_foundation/prepare.py` | Lane assignment, term expansion, table bias scoring, batch planning |
| `api/sql_foundation/execute_union.py` | TRUE UNION ALL execution with RPC + REST fallback |
| `api/sql_foundation/ranking.py` | Relevance scoring with 210 golden test cases |
| `api/sql_foundation/bbws_search.py` | Integration wrapper called by /v2/search endpoint |

### Configuration

| File | Purpose |
|------|---------|
| `api/sql_foundation/column_config.py` | Table/column metadata, searchable columns, operators |
| `api/sql_foundation/operators.py` | SQL operator definitions (EXACT, ILIKE, TRIGRAM) |

### Testing

| File | Purpose |
|------|---------|
| `tests/overnight/expanded_test_suite.py` | 3305 tests covering all 23 entity types |
| `tests/overnight/seed_tables.py` | Seeding script for all 7 PMS tables |

---

## Lane Routing

All queries are routed to one of four lanes:

| Lane | When Used | Action |
|------|-----------|--------|
| **BLOCKED** | SQL/template/command injection detected | Return block message, execute NO SQL |
| **UNKNOWN** | Domain drift, gibberish, off-topic | Return suggestions, execute NO SQL |
| **NO_LLM** | Code-like query (E001, PO-123) | Direct SQL, no LLM needed |
| **GPT** | Natural language query | Full pipeline with entity extraction |

---

## Test Results Summary

### Overnight Validation Campaign (3305 tests)
```
Total Tests: 3305
Passed: 3294 (99.7%)
Failed: 11 (0.3%)

Entity Types Covered: 23/23
  [CONTACT, DESCRIPTION, EQUIPMENT_CODE, EQUIPMENT_NAME, FAULT_CODE,
   FREE_TEXT, HOURS, LOCATION, MANUFACTURER, MODEL, NODE_LABEL,
   NODE_TYPE, PART_NAME, PART_NUMBER, PO_NUMBER, PRIORITY,
   SERIAL_NUMBER, SEVERITY, STATUS, SUPPLIER_NAME, SYMPTOM,
   SYSTEM_NAME, WORK_ORDER_TITLE]

By Category:
  injection: 306/306 (100%)  ← Security gate enforced
  domain_drift: 400/400 (100%)
  conjunction: 500/500 (100%)
  early_exit: 250/250 (100%)
  fuzzy: 73/73 (100%)
  chaos: 742/750 (99%)
  stacked_nouns: 300/300 (100%)
  All entity types: 100% (except model at 90%)
```

### Ranking Model (210 golden cases)
```
Golden Ranking Tests: 210/210 passed (100%)
```

---

## Security Fixes Applied

### 1. Hardcoded Service Keys → Environment Variables
**38 files** were updated to use `os.environ.get("SUPABASE_SERVICE_KEY", "")` instead of hardcoded JWT tokens.

### 2. Hardcoded Absolute Paths → Relative Paths
**25 files** were updated to use `os.path.dirname(os.path.abspath(__file__))` instead of `/Users/celeste7/Documents/Cloud_PMS`.

### 3. Service Key Rotation Required
The previously exposed key needs rotation via Supabase dashboard. The key was committed to git history and should be considered compromised.

---

## How to Use

### Running Tests
```bash
# Set environment variable
export SUPABASE_SERVICE_KEY="your-service-key"
export SUPABASE_URL="https://your-project.supabase.co"

# Run overnight test suite
python3 tests/overnight/expanded_test_suite.py

# Run ranking tests
python3 -m api.sql_foundation.ranking
```

### Integration
```python
from api.sql_foundation.bbws_search import bbws_search

result = bbws_search(
    query="fuel filter MTU",
    entities=[
        {"type": "PART_NAME", "value": "fuel filter"},
        {"type": "MANUFACTURER", "value": "MTU"}
    ],
    yacht_id="85fe1119-b04c-41ac-80f1-829d23322598",
    user_id="test-user",
    user_role="engineer"
)

print(f"Lane: {result.lane}")
print(f"Rows: {result.total_rows}")
print(f"Tables hit: {result.tables_hit}")
```

---

## Deployment Checklist

1. [ ] Deploy Supabase migration: `supabase db push`
2. [ ] Set environment variables in production:
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_KEY`
3. [ ] Rotate compromised service key in Supabase dashboard
4. [ ] Verify tests pass with new credentials
5. [ ] Deploy API with updated code

---

## Architecture Decision: Why UNION Batching?

### Before (N+1 REST)
```
Query → REST call 1 (pms_parts) →
        REST call 2 (pms_equipment) →
        REST call 3 (pms_faults) →
        ... (7+ calls) →
        Merge client-side
```
**Problems**: High latency, no transaction isolation, complex error handling

### After (UNION ALL)
```
Query → Single RPC call →
        SELECT ... FROM pms_parts WHERE ...
        UNION ALL
        SELECT ... FROM pms_equipment WHERE ...
        UNION ALL
        SELECT ... FROM pms_faults WHERE ...
        → Single result set
```
**Benefits**: Single round-trip, DB-side merging, atomic execution

---

## Contact

For questions about this module, check the documentation in `api/sql_foundation/ARCHITECTURE.md` or the test files for examples.
