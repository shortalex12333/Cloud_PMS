# Failure Diagnosis: Exact Breakpoints

**Date:** 2026-01-02

---

## Summary: Where Queries Break

| Failure Class | Root Cause | Code Location | Fix Complexity |
|---------------|------------|---------------|----------------|
| **multi_intent** | No clause decomposition | `route_to_lane()` L1073-1115 | MEDIUM |
| **context_dependent** | No session state | Architectural gap | HIGH |
| **overloaded_entities** | No verb → falls to UNKNOWN | `route_to_lane()` L1104 | LOW |
| **greeting_prefix** | Greeting stripped, core lost | `POLITE_PREFIX` L927 | LOW |
| **politeness_suffix** | Suffix not stripped | No pattern exists | LOW |

---

## CLASS 1: MULTI_INTENT (60% fail)

### What Breaks
Queries with conjunctions ("and", "then", "also") that combine two intents:

```
"check oil level and create wo if low"     → UNKNOWN (expected RULES_ONLY)
"find the manual and schedule service"     → UNKNOWN (expected NO_LLM)
"check if we have filters then order more" → UNKNOWN (expected RULES_ONLY)
```

### Why It Breaks
The query enters `route_to_lane()` as a single string. No pattern matches the compound structure:

1. **ELLIPTICAL_PATTERNS** (L932-952): No match - query is too long
2. **IMPLICIT_ACTION_PATTERNS** (L956-985): No match - patterns are specific phrases
3. **COMMAND_PATTERNS** (L987+): No match - verbs are split across clauses
4. **DIRECT_LOOKUP** (L1014-1041): No match - multiple intents
5. **GPT triggers** (L1069-1091): No match - no problem words
6. **Falls to default** (L1104): Returns UNKNOWN

### Where In Pipeline
```
/extract endpoint
  → route_to_lane() at microaction_service.py:1151
    → All pattern checks fail
    → Returns {'lane': 'UNKNOWN'} at L1104-1115
  → Response: lane=UNKNOWN
```

### Fix: Query Decomposition
```python
# Proposed: Before route_to_lane()
CLAUSE_SPLIT = re.compile(r'\s+(?:and|then|also|plus)\s+')
clauses = CLAUSE_SPLIT.split(query)
if len(clauses) > 1:
    # Route each clause separately
    results = [route_to_lane(c) for c in clauses]
    # Return compound response with both intents
```

---

## CLASS 2: CONTEXT_DEPENDENT (50% fail)

### What Breaks
Queries that reference prior conversation:

```
"do the same thing"      → UNKNOWN (expected RULES_ONLY)
"add this too"           → UNKNOWN (expected RULES_ONLY)
"the thing we discussed" → UNKNOWN (expected NO_LLM)
```

### Why It Breaks
**Architectural gap:** The system has no session state. Each request is independent.

1. "do the same thing" - What thing? No prior context.
2. "add this too" - Add what? To where?
3. "the thing we discussed" - What thing?

### Where In Pipeline
```
/extract endpoint receives query
  → No session_id lookup
  → No conversation history retrieval
  → route_to_lane() sees isolated query
  → Returns UNKNOWN (correct for stateless system)
```

### Fix: Session State (HIGH complexity)
```python
# Would require:
1. Redis/DB storage of last N turns per session
2. session_id passed from frontend
3. Context injection before routing
4. Reference resolution ("this" → actual entity)
```

**Verdict:** These queries SHOULD return UNKNOWN until session state exists. UNKNOWN is the honest answer.

---

## CLASS 3: OVERLOADED_ENTITIES (30% fail)

### What Breaks
Entity-only queries with no verb:

```
"main engine generator watermaker AC"        → UNKNOWN (expected NO_LLM)
"oil filter fuel filter air filter impeller" → UNKNOWN (expected NO_LLM)
"captain engineer bosun deckhand"            → UNKNOWN (expected NO_LLM)
```

### Why It Breaks
The routing logic requires either:
- A command verb (create, log, schedule)
- A problem word (overheating, broken)
- A direct lookup pattern (WO-1234, CAT 3512 manual)

Entity-soup queries have none of these signals:
1. No verb → not RULES_ONLY
2. No problem word → not GPT
3. Not matching DIRECT_LOOKUP regex → not NO_LLM
4. Falls to UNKNOWN

### Where In Pipeline
```
route_to_lane():
  → COMMAND_PATTERNS: No verb, no match
  → DIRECT_LOOKUP: Doesn't match "entity entity entity" pattern
  → is_simple_lookup: False (no lookup intent detected)
  → Falls to UNKNOWN at L1104
```

### Fix: Entity-Only Detection (LOW complexity)
```python
# Add before UNKNOWN fallback:
# If query is ALL entities and no verb, treat as search
if all(is_maritime_entity(w) for w in words) and not has_verb:
    return {'lane': 'NO_LLM', 'lane_reason': 'entity_search'}
```

---

## CLASS 4: GREETING PREFIX (70% fail on subset)

### What Breaks
Queries starting with greetings:

```
"hello i need help with the watermaker" → UNKNOWN (expected GPT)
"good morning need to log hours"        → UNKNOWN (expected RULES_ONLY)
"hi can you schedule maintenance"       → UNKNOWN (expected RULES_ONLY)
```

### Why It Breaks
`POLITE_PREFIX` (L927) strips greeting prefixes, but then the remaining query fails to match:

1. `"hello i need help with the watermaker"`
   - Stripped to: `"i need help with the watermaker"`
   - "help" was removed from PROBLEM_WORDS (caused over-triggering)
   - No pattern match → UNKNOWN

2. `"good morning need to log hours"`
   - Stripped to: `"need to log hours"`
   - "need to log" doesn't match COMMAND_PATTERNS
   - Falls to UNKNOWN

### Where In Pipeline
```
route_to_lane():
  → POLITE_PREFIX strips "hello/hi/good morning"
  → Remaining query enters pattern matching
  → "need help" - "help" not in PROBLEM_WORDS
  → "need to log" - not in COMMAND_PATTERNS
  → Falls to UNKNOWN
```

### Fix: Restore Narrow "help" Pattern (LOW complexity)
```python
# In PROBLEM_WORDS, add narrow match:
r'(?:need|want)\s+help\b'  # Only "need help" or "want help"
```

---

## CLASS 5: POLITENESS SUFFIX

### What Breaks
Queries ending with politeness phrases:

```
"show specs if you can"          → UNKNOWN (expected NO_LLM)
"need to fix this would you mind" → UNKNOWN (expected GPT)
```

### Why It Breaks
`POLITE_PREFIX` only handles prefixes. Suffixes like "if you can", "would you mind" are not stripped:

1. `"show specs if you can"`
   - Full query enters routing
   - "if you can" breaks pattern matching
   - "show specs" alone would match DIRECT_LOOKUP

2. `"need to fix this would you mind"`
   - "fix" should trigger GPT
   - But "fix" was removed from PROBLEM_WORDS
   - Falls to UNKNOWN

### Where In Pipeline
```
route_to_lane():
  → POLITE_PREFIX: Only handles start of query
  → "if you can" / "would you mind" remain in query
  → Pattern matching fails on polluted query
```

### Fix: Add POLITE_SUFFIX Stripping (LOW complexity)
```python
POLITE_SUFFIX = re.compile(
    r'\s*(?:if you (?:can|could|don\'t mind)|'
    r'would you(?: mind)?|please|thanks|thank you)\s*$',
    re.IGNORECASE
)
query_clean = POLITE_SUFFIX.sub('', query_clean)
```

---

## Render Pipeline Flow (Where Each Failure Occurs)

```
Request → /extract endpoint (L1122)
         │
         ├─ route_to_lane(query) (L1151)
         │   │
         │   ├─ GUARD 0: Paste dump check (L762) ────────────────────► BLOCKED
         │   ├─ GUARD 1: NON_DOMAIN check (L812) ───────────────────► BLOCKED
         │   ├─ GUARD 2: INJECTION_TOKENS (L847) ───────────────────► BLOCKED
         │   ├─ GUARD 3: CLAUSE_NON_DOMAIN (L875) ──────────────────► BLOCKED
         │   │
         │   ├─ ELLIPTICAL_PATTERNS (L932) ─────────────────────────► RULES_ONLY
         │   ├─ IMPLICIT_ACTION_PATTERNS (L956) ────────────────────► RULES_ONLY
         │   ├─ COMMAND_PATTERNS (L987) ────────────────────────────► RULES_ONLY
         │   │
         │   ├─ DIRECT_LOOKUP (L1014) ──────────────────────────────► NO_LLM
         │   ├─ is_simple_lookup (L1029) ───────────────────────────► NO_LLM
         │   │
         │   ├─ has_problem_words (L1069) ──────────────────────────► GPT
         │   ├─ has_temporal_context (L1070) ───────────────────────► GPT
         │   ├─ diagnosis_intents (L1071) ──────────────────────────► GPT
         │   │
         │   └─ DEFAULT FALLBACK (L1104) ───────────────────────────► UNKNOWN  ⚠️
         │
         ├─ if lane == BLOCKED → return immediately (L1155)
         ├─ if lane in [NO_LLM, RULES_ONLY, UNKNOWN] → regex extraction (L1171)
         └─ else → GPT extraction (L1224)

FAILURES OCCUR AT:
- multi_intent:      Falls through all patterns to L1104 (UNKNOWN)
- context_dependent: Falls through all patterns to L1104 (UNKNOWN)
- overloaded_entities: Falls through all patterns to L1104 (UNKNOWN)
- greeting_prefix:   POLITE_PREFIX strips too much, then L1104 (UNKNOWN)
- politeness_suffix: No suffix stripping, patterns fail, L1104 (UNKNOWN)
```

---

## Priority Fix Order

| Priority | Fix | Impact | Effort |
|----------|-----|--------|--------|
| 1 | Add POLITE_SUFFIX stripping | +10% | 10 min |
| 2 | Restore narrow "need help" | +5% | 5 min |
| 3 | Add entity-only detection | +5% | 15 min |
| 4 | Query decomposition for multi_intent | +10% | 2 hrs |
| 5 | Session state for context_dependent | +5% | Days |

**Quick wins (1-3) would push accuracy from 73% → ~85%**

---

*Report generated: 2026-01-02*
