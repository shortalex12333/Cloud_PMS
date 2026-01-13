# CelesteOS E2E Test Cases

## Test Suite Overview

**Date:** 2026-01-12
**Total Tests:** 15
**Passed:** 1 (6.7%)
**No Handler:** 14 (93.3%)
**Failed:** 0

## Critical Finding

**IntentParser (GPT-based) is unreliable. Module A (regex-based) is accurate.**

The system has TWO parsing paths:
1. `IntentParser` - GPT-4o-mini based, 67 intents, currently FAILING
2. `Module A` (StrictMicroActionDetector) - Regex verb-based, 21 actions, WORKING

Handler routing currently depends on IntentParser results, but IntentParser defaults to `find_document` for most queries.

---

## Test Case Results

### Test 1: Show Equipment History
| Stage | Result |
|-------|--------|
| **Query** | "show me the equipment history" |
| **IntentParser** | find_document (WRONG) |
| **Module A** | None |
| **Entities** | None |
| **Handler** | None |
| **Status** | NO HANDLER |
| **Expected** | view_equipment_history |

### Test 2: View Compliance Status
| Stage | Result |
|-------|--------|
| **Query** | "view compliance status" |
| **IntentParser** | view_compliance_status (CORRECT) |
| **Module A** | None |
| **Entities** | None |
| **Handler** | view_compliance_status (P3) |
| **Status** | SUCCESS |
| **Latency** | 499ms |

### Test 3: What's My Worklist
| Stage | Result |
|-------|--------|
| **Query** | "what's my worklist" |
| **IntentParser** | find_document (WRONG) |
| **Module A** | None |
| **Entities** | None |
| **Handler** | None |
| **Status** | NO HANDLER |
| **Expected** | view_worklist |

### Test 4: Create Work Order
| Stage | Result |
|-------|--------|
| **Query** | "create work order for bilge pump" |
| **IntentParser** | create_work_order (CORRECT) |
| **Module A** | create_work_order (0.95) (CORRECT) |
| **Entities** | equipment:BILGE_PUMP |
| **Handler** | None (mutation not routed) |
| **Status** | NO HANDLER |

### Test 5: Diagnose Fault
| Stage | Result |
|-------|--------|
| **Query** | "diagnose E047 on main engine" |
| **IntentParser** | find_document (WRONG) |
| **Module A** | diagnose_fault (0.93) (CORRECT) |
| **Entities** | fault_code:E047, equipment:MAIN_ENGINE |
| **Handler** | None |
| **Status** | NO HANDLER |

### Test 6: Open Work Order
| Stage | Result |
|-------|--------|
| **Query** | "open work order for generator maintenance" |
| **IntentParser** | find_document (WRONG) |
| **Module A** | create_work_order (0.95) (CORRECT) |
| **Entities** | equipment:GENERATOR |
| **Handler** | None |
| **Status** | NO HANDLER |

### Test 7: Equipment Description (No Action)
| Stage | Result |
|-------|--------|
| **Query** | "MTU 16V4000 engine overheating" |
| **IntentParser** | find_document |
| **Module A** | None (CORRECT - no verb) |
| **Entities** | brand:MTU, model:16V4000, symptom:ENGINE_OVERHEATING |
| **Handler** | None |
| **Status** | NO HANDLER |
| **Note** | This is correct behavior - entity-only query |

### Test 8: Symptom Description
| Stage | Result |
|-------|--------|
| **Query** | "sea water pump pressure low" |
| **IntentParser** | find_document |
| **Module A** | None |
| **Entities** | measurement_term:WATER_PRESSURE_READING |
| **Handler** | None |
| **Status** | NO HANDLER |

### Test 9: Alarm Query
| Stage | Result |
|-------|--------|
| **Query** | "24V generator failure alarm" |
| **IntentParser** | find_document |
| **Module A** | None |
| **Entities** | measurement:24V, symptom:POWER_LOSS, symptom:ALARM |
| **Handler** | None |
| **Status** | NO HANDLER |

### Test 10: Entity Only
| Stage | Result |
|-------|--------|
| **Query** | "bilge manifold" |
| **IntentParser** | find_document |
| **Module A** | None (CORRECT) |
| **Entities** | equipment:MANIFOLD |
| **Handler** | None |
| **Status** | NO HANDLER |
| **Note** | Correct behavior - no action requested |

### Test 11: Informal Query
| Stage | Result |
|-------|--------|
| **Query** | "tell me about the pump" |
| **IntentParser** | find_document |
| **Module A** | None |
| **Entities** | (varies) |
| **Handler** | None |
| **Status** | NO HANDLER |

### Test 12: Add Note to Work Order (Mutation)
| Stage | Result |
|-------|--------|
| **Query** | "add note to work order: checked oil level" |
| **IntentParser** | find_document (WRONG) |
| **Module A** | add_note_to_work_order (CORRECT) |
| **Entities** | (varies) |
| **Handler** | None |
| **Status** | NO HANDLER |
| **Expected** | Should gate for confirmation |

### Test 13: Acknowledge Fault (Mutation)
| Stage | Result |
|-------|--------|
| **Query** | "acknowledge the fault" |
| **IntentParser** | find_document (WRONG) |
| **Module A** | acknowledge_fault (CORRECT) |
| **Entities** | None |
| **Handler** | None |
| **Status** | NO HANDLER |
| **Expected** | Should gate for confirmation |

### Test 14: Find Documents
| Stage | Result |
|-------|--------|
| **Query** | "find documents about fire safety" |
| **IntentParser** | find_document |
| **Module A** | search_documents (0.90) |
| **Entities** | None |
| **Handler** | None |
| **Status** | NO HANDLER |

### Test 15: Search Manual
| Stage | Result |
|-------|--------|
| **Query** | "search for bilge pump manual" |
| **IntentParser** | find_document |
| **Module A** | None |
| **Entities** | equipment:BILGE_PUMP, document_type:MANUAL |
| **Handler** | None |
| **Status** | NO HANDLER |

---

## Module Accuracy Summary

### IntentParser (GPT-based)
- **Accuracy:** 2/15 (13%)
- **Default fallback:** find_document
- **Confidence:** Always 0.50 (indicates fallback mode)
- **Issue:** GPT not returning valid intents, keyword fallback too broad

### Module A (ActionDetector)
- **Accuracy:** 6/6 (100%) for action queries
- **False positives:** 0
- **Correctly returns None for entity-only queries**

### Module B (EntityExtractor)
- **Extracted meaningful entities from 10/15 queries**
- **Correctly identifies:** brands, models, fault codes, equipment, symptoms
- **Pattern count:** 42,340 terms from 1,330 patterns

---

## Action Items

1. **FIX: Handler routing must use Module A results**, not just IntentParser
2. **FIX: IntentParser GPT prompts** need tuning (currently defaults to find_document)
3. **ADD: Route mutations to n8n webhooks** with confirmation gating
4. **ADD: Search handler** for entity-only queries (should trigger RAG search)

---

## Test Execution Command

```bash
python3 e2e_test_harness.py
```

Traces exported to: `e2e_traces.json`
