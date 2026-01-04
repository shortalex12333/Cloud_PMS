# SQL Foundation Architecture

## Overview

The SQL Foundation provides a unified, secure search infrastructure for yacht PMS data.
It separates **READ** and **WRITE** paths to ensure data integrity and security.

## Two Paths

### READ Path (SQL Foundation)

The READ path handles all search/query operations:

```
Query → PREPARE → EXECUTE → RANK → Response
```

**PREPARE Stage:**
1. Lane assignment (BLOCKED, UNKNOWN, NO_LLM, GPT)
2. Security validation (injection blocking, domain drift detection)
3. Term expansion (synonyms, variants)
4. Table bias scoring (+2.0 for primary tables, etc.)
5. Batch planning (tier 1 high-bias, tier 2 medium-bias, etc.)

**EXECUTE Stage:**
1. Wave-based search (Wave 0: EXACT, Wave 1: ILIKE, Wave 2: TRIGRAM)
2. Tier batching (high-bias tables first)
3. Early exit (stop when enough results found)
4. Parameterized SQL only (no string interpolation)

**RANK Stage:**
1. Score by match type (EXACT +3.0, ILIKE +1.5, TRIGRAM +0.5)
2. Score by table bias (from PREPARE stage)
3. Score by entity confidence (from extraction)
4. Sort by relevance

### WRITE Path (Microactions via n8n)

The WRITE path handles all create/update/delete operations:

```
Intent → Action Detection → n8n Workflow → Supabase → Response
```

**Action Types:**
- `log_entry` - Create log entries
- `schedule_maintenance` - Create work orders
- `update_inventory` - Modify part quantities
- `create_work_order` - Create new work orders
- `close_work_order` - Complete work orders
- `add_to_handover` - Add handover notes
- `export_report` - Generate reports
- `attach_document` - Link documents

**Security:**
- All writes require authenticated user
- Yacht isolation enforced via RLS
- Audit trail for all mutations
- n8n provides workflow orchestration

## Lane Routing

| Lane | When Used | Action |
|------|-----------|--------|
| BLOCKED | Injection/jailbreak detected | Return block message, no SQL |
| UNKNOWN | Domain drift/gibberish | Return suggestions, no SQL |
| NO_LLM | Code-like query (E001, PO-123) | Direct SQL, no LLM needed |
| GPT | Natural language query | SQL with entity extraction |

## Table Bias Scoring

Primary tables for each entity type get +2.0 bias:

| Entity Type | Primary Table |
|-------------|---------------|
| FAULT_CODE | pms_faults |
| EQUIPMENT_NAME | pms_equipment |
| EQUIPMENT_CODE | pms_equipment |
| PART_NAME | pms_parts |
| PART_NUMBER | pms_parts |
| MANUFACTURER | pms_parts |
| SUPPLIER_NAME | pms_suppliers |
| WORK_ORDER_TITLE | pms_work_orders |
| SYMPTOM | symptom_catalog |
| NODE_LABEL | graph_nodes |

## Wave Execution

Search progresses through waves until enough results found:

| Wave | Operator | Example |
|------|----------|---------|
| 0 | EXACT | `code = 'E001'` |
| 1 | ILIKE | `name ILIKE '%filter%'` |
| 2 | TRIGRAM | `similarity(name, 'filtr') > 0.3` |

Early exit triggers when:
- Sufficient rows found (default: 20)
- All tiers exhausted
- Timeout reached

## Integration Points

### /v2/search Endpoint

```python
# In microaction_service.py
if BBWS_AVAILABLE and resolved_entities:
    bbws_results = bbws_search_for_endpoint(
        query=search_request.query,
        entities=resolved_entities,
        yacht_id=yacht_id,
        user_id=user_id,
        user_role=user_role
    )
```

Response includes:
- `bbws_rows` - Ranked results
- `bbws_lane` - Lane used (BLOCKED/UNKNOWN/NO_LLM/GPT)
- `bbws_trace` - Full execution trace
- `bbws_tables` - Tables hit
- `bbws_waves` - Waves executed

### /extract Endpoint

Microaction detection with lane routing:
- NO_LLM lane: Return entities directly
- UNKNOWN lane: Return suggestions
- GPT lane: Full LLM processing

## Files

| File | Purpose |
|------|---------|
| `prepare.py` | PREPARE stage (lane, terms, batches) |
| `execute.py` | EXECUTE stage (waves, SQL) |
| `ranking.py` | RANK stage (scoring, sorting) |
| `bbws_search.py` | Integration wrapper |
| `column_config.py` | Table/column metadata |
| `operators.py` | SQL operators (EXACT, ILIKE, TRIGRAM) |

## Test Coverage

| Suite | Tests | Pass Rate |
|-------|-------|-----------|
| Lane routing | 1620 | 100% |
| Entity types (23) | 3305 | 99.7% |
| Ranking golden | 210 | 100% |

## Security Guarantees

1. **Parameterized SQL only** - No string interpolation
2. **Yacht isolation** - All queries scoped to yacht_id
3. **Injection blocking** - SQL, template, command injection detected
4. **Domain drift** - Off-topic queries routed to UNKNOWN
5. **Lane enforcement** - BLOCKED returns 0 rows always
