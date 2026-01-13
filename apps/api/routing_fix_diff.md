# Routing Fix Diff

## Problem Statement

**Before fix:** IntentParser (GPT-based) was the sole routing signal, defaulting to `find_document` for 93% of queries.

**Module A (ActionDetector)** correctly detected actions with 0.93-0.95 confidence but was ignored.

## Solution: Multi-Signal Routing Arbitration

### New Routing Priority Chain

```
1. Module A (confidence >= 0.85)     → Highest priority (strict verb-based)
2. IntentParser (confidence >= 0.70) → Fallback (GPT-based)
3. Module A (confidence >= 0.40)     → Secondary fallback
4. Keyword matching                  → Common phrase patterns
5. Entity inference                  → Route based on detected entities
6. None                              → Refuse to route
```

### Key Changes

#### 1. Module A Precedence (CRITICAL)

```python
# BEFORE: IntentParser only
if self.intent_parser:
    parsed = self.intent_parser.parse(query)
    final_action = parsed.intent  # Always used IntentParser

# AFTER: Module A takes precedence
if module_a_confidence >= 0.85:
    final_action = module_a_action
    source = "module_a"
```

#### 2. find_document Rejection

```python
# BEFORE: find_document with 0.5 confidence was accepted
# AFTER: find_document with low confidence is rejected
if intent_parser_intent == "find_document" and intent_parser_confidence < 0.8:
    # Do not use - try other routing methods
```

#### 3. Keyword Fallback

```python
keyword_routes = [
    (["worklist", "my tasks"], "view_worklist"),
    (["work order history"], "view_work_order_history"),
    (["track delivery"], "track_delivery"),
    # ... more patterns
]
```

#### 4. Entity-Based Inference

```python
if "fault_code" in entity_types or "symptom" in entity_types:
    final_action = "diagnose_fault"
elif "equipment" in entity_types:
    final_action = "view_equipment_details"
elif "part" in entity_types:
    final_action = "view_part_stock"
```

## Results

| Metric | Before | After |
|--------|--------|-------|
| SUCCESS + GATED | 56.7% | 93.3% |
| No Handler | 40.0% | 3.3% |
| Module A used | 0% | 40% |

## Routing Source Distribution (After)

| Source | Count | Description |
|--------|-------|-------------|
| module_a | 12 | High-confidence verb patterns |
| entity_inference | 7 | Entity-based fallback |
| intent_parser | 6 | IntentParser with valid intent |
| keyword_fallback | 4 | Keyword phrase matching |
| none | 1 | Too ambiguous to route |

## Files Changed

- `e2e_sandbox.py` - New sandbox with corrected routing
- `e2e_execution_traces.json` - Full execution traces

## Remaining Issue

One query still fails: "investigate the overheating issue"
- No verb pattern match
- No entities detected
- No keyword match
- **Correct behavior:** System refuses to route ambiguous query
