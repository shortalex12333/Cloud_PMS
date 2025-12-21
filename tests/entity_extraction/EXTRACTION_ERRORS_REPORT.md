# Entity Extraction Error Report

**Date:** 2024-12-21
**Tested:** 50 NO_LLM queries against Render endpoint

## Summary

| Metric | Count |
|--------|-------|
| Total Queries | 50 |
| Correct Extractions | ~15 |
| FALSE POSITIVES | 2+ |
| BLOCKED (too_vague) | 10+ |
| MISSING ENTITIES | 25+ |
| Weight Inconsistencies | Multiple |

---

## Critical Issues

### 1. FALSE POSITIVE: "inventory box 3d" → "vent"

**Query:** `inventory box 3d`
**Extracted:** `action: "vent" → VENT_SYSTEM`
**Expected:** `location: "box 3d" → BOX_3D`

**Root Cause:** The `vent_system` diagnostic pattern regex is:
```regex
(vent|vent line|vent pipe|vent tank|...)
```
This matches "vent" substring within "inVENTory" because there are **NO WORD BOUNDARIES**.

**Fix Required:** Add `\b` word boundaries:
```regex
\b(vent|vent line|vent pipe|...)\b
```

---

### 2. FALSE POSITIVE: "manual" → MANUAL_MODE

**Query:** `MTU 16V4000 manual`
**Extracted:** `fault: "manual" → MANUAL_MODE`
**Expected:** `document_type: "manual" → MANUAL`

**Root Cause:** The word "manual" is matched as a fault mode when in context it means documentation.

**Fix Required:** Context-aware disambiguation or blacklist when near "brand+model".

---

### 3. BLOCKED: Valid 2-word queries

**Queries blocked as "too_vague":**
- `Seakeeper manual` ← Should recognize Seakeeper as brand
- `oil filter` ← Core equipment type
- `main engine` ← Core equipment type
- `generator` ← Core equipment type
- `stabilizer` ← Core equipment type
- `watermaker` ← Core equipment type

**Root Cause:** Lane assignment blocks queries with ≤2 words as "too_vague", even when they contain valid entities.

**Fix Required:** Override "too_vague" when valid brand/equipment entities are detected.

---

### 4. MISSING BRANDS (25+)

These major marine brands are NOT in the gazetteer:

| Brand | Category |
|-------|----------|
| Seakeeper | Stabilizers |
| Kohler | Generators |
| Naiad | Stabilizers |
| Racor | Fuel Filtration |
| Dometic | HVAC/AC |
| Cruisair | HVAC/AC |
| Furuno | Navigation |
| Garmin | Navigation |
| Simrad | Navigation |
| Victron | Power/Batteries |
| Mastervolt | Power/Chargers |
| Lewmar | Deck Hardware |
| Muir | Anchoring |
| Webasto | Heating |
| Eberspacher | Heating |
| Cummins | Engines |
| Yanmar | Engines |
| Perkins | Engines |
| Onan | Generators |
| Westerbeke | Generators |
| Raritan | Marine Sanitation |
| Jabsco | Pumps |
| Groco | Seacocks |
| Reverso | Oil Change |
| Spectra | Watermakers |

---

### 5. MISSING EQUIPMENT (Standalone)

These equipment types extract correctly when paired with a brand, but NOT standalone:

- `oil filter` → No extraction (blocked)
- `generator` → No extraction (blocked)
- `stabilizer` → No extraction (blocked)
- `watermaker` → No extraction (blocked)

But work with brand:
- `MTU fuel filter` → ✓ brand + equipment
- `Rule bilge pump` → ✓ brand + equipment

---

### 6. Weight Inconsistencies

Two different weight formats observed:

**Format A (module_b weights):**
```json
{"weight": 3.5, "canonical_weight": 2.8}
```

**Format B (diagnostic pattern weights):**
```json
{"weight": 0.651}  // No canonical_weight
```

**Root Cause:** Different extraction paths use different weight calculation.

---

## Recommended Fixes (Priority Order)

### P0: Add Word Boundaries to Diagnostic Patterns

In `entity_extraction_loader.py`, wrap all regex patterns with `\b`:

```python
# Before compiling, add word boundaries
if not regex_str.startswith(r'\b'):
    regex_str = r'\b' + regex_str
if not regex_str.endswith(r'\b'):
    regex_str = regex_str + r'\b'
```

### P1: Add Missing Brands to Gazetteer

Add 25+ missing marine brands to equipment patterns.

### P2: Fix "too_vague" Lane Logic

In intent_parser, allow short queries when entities are detected:

```python
if word_count <= 2 and not has_valid_entities:
    return "BLOCKED", "too_vague"
```

### P3: Context-Aware "manual" Disambiguation

When "manual" follows brand+model, classify as `document_type` not `fault`.

### P4: Unify Weight Output

Ensure all entities have consistent `weight` and `canonical_weight` fields.

---

## Test Queries for Validation

After fixes, these should all work:

```
inventory box 3d → location: box 3d
MTU 16V4000 manual → brand: MTU, model: 16V4000, document_type: manual
Seakeeper manual → brand: Seakeeper, document_type: manual
oil filter → equipment: oil filter
main engine → equipment: main engine
generator → equipment: generator
```
