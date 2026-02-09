# Entity Extraction Infrastructure Analysis

**Date**: 2026-02-02
**Scope**: Part Lens Microaction Issues - Root Cause Analysis

---

## Executive Summary

**Finding:** Part Lens microactions work correctly, but manufacturer/part name queries fail due to entity extraction misclassification.

**Root Cause:** Manufacturers (like "Racor") are extracted as `org` entity type, which has no capability mapping, causing search to return 0 results and no microactions.

**Impact:** HIGH - Affects all natural language part searches (manufacturer names, part names like "oil filter")

---

## Entity Extraction Pipeline Architecture

### 5-Stage Pipeline

```
Stage 1: Clean           → TextCleaner
         ├─ Normalize text
         ├─ Expand brands
         └─ Tokenize

Stage 2: Regex Extract   → RegexExtractor
         ├─ 60+ regex patterns (fault codes, part numbers, measurements)
         ├─ Gazetteer lookup (32K manufacturers, 1K equipment terms)
         └─ ENTITY_EXTRACTION_EXPORT (33K brands, 1.3K types, 485 patterns)

Stage 3: Controller      → CoverageController
         ├─ Calculate coverage
         ├─ Detect gaps
         └─ Decide if AI needed (~30% of queries)

Stage 4: AI Extract      → AIExtractor (GPT-4o-mini)
         ├─ Extract from uncovered spans
         └─ Only called if coverage < threshold

Stage 5: Merge           → EntityMerger
         ├─ Deduplicate overlaps
         ├─ Filter by confidence
         └─ Normalize text
```

### Files

| File | Purpose | Lines |
|------|---------|-------|
| `extraction/orchestrator.py` | Coordinates 5-stage pipeline | 199 |
| `extraction/regex_extractor.py` | Regex patterns + gazetteer | 1700+ |
| `extraction/entity_merger.py` | Deduplication & filtering | 600+ |
| `extraction/coverage_controller.py` | AI trigger decision | ~200 |
| `extraction/ai_extractor_openai.py` | GPT-4o-mini extraction | ~300 |

---

## Issue 1: Manufacturer Names Misclassified as ORG

### Current Behavior

**Query:** `"Racor"`

**Extraction Flow:**
```python
# Stage 2: Regex Extract (regex_extractor.py)

# Line 1168-1169: Manufacturers added to 'org' gazetteer
gazetteer['org'] = gazetteer['org'] | filtered_manufacturers

# Line 742-743: Load manufacturers from REGEX_PRODUCTION
regex_prod_manufacturers = load_manufacturers()  # Returns 32,293 manufacturers including "Racor"

# Line 1149-1169: Filter and add to gazetteer
for mfg in regex_prod_manufacturers:
    if not_contaminated(mfg):
        filtered_manufacturers.add(mfg)

gazetteer['org'] = gazetteer['org'] | filtered_manufacturers
```

**Result:**
```json
{
  "entities": {
    "org": ["Racor"]  ← Wrong! Should be "manufacturer"
  }
}
```

**Capability Lookup:**
```python
# prepare/capability_composer.py Line 196
mapping = ENTITY_TO_SEARCH_COLUMN.get("org")  # Returns None!
# 'org' is NOT in the mapping, so no capability selected
```

**Error:**
```json
{
  "error": "No capabilities matched the extracted entities",
  "results": []
}
```

### Problem Analysis

**Location:** `apps/api/extraction/regex_extractor.py` Lines 1018-1023, 1168-1169

**Code:**
```python
# Lines 1018-1023: Hardcoded manufacturers in 'org' gazetteer
'org': {
    # Engine manufacturers & Generators
    'caterpillar', 'cat', 'man', 'wartsila', 'wärtsilä', 'rolls royce', 'mtu',
    'volvo', 'volvo penta', 'penta', 'yanmar', 'cummins', 'deutz', 'perkins',
    'john deere', 'scania', 'iveco', 'detroit diesel', 'fischer panda',
    'kohler', 'onan', 'northern lights',  # Generators - ADDED 2025-10-20
    # ... more manufacturers
}

# Lines 1168-1169: Add 32K manufacturers from REGEX_PRODUCTION to 'org'
gazetteer['org'] = gazetteer['org'] | filtered_manufacturers
```

**Why 'org' instead of 'manufacturer'?**
- Historical: Initially designed for general organization names
- No dedicated 'manufacturer' entity type in gazetteer
- Manufacturers lumped with orgs

**Impact:**
- 32,000+ manufacturer names extracted as 'org'
- All fail capability lookup
- No part search results
- No Part Lens microactions

---

## Issue 2: Part Names Misclassified as Equipment

### Current Behavior

**Query:** `"Air Filter Element"`

**Extraction:**
```json
{
  "entities": {
    "equipment": ["Filter"]  ← Wrong! Should be "part_name"
  }
}
```

**Result:**
- Searches `pms_equipment` table instead of `pms_parts`
- Returns equipment, not parts
- Equipment Lens applied, not Part Lens
- No Part Lens microactions

### Problem Analysis

**Location:** `apps/api/extraction/regex_extractor.py` Lines 747-1100

**Gazetteer Structure:**
```python
gazetteer = {
    'equipment': {
        # Equipment types
        'pump', 'motor', 'valve', 'filter', 'sensor',  # ← "filter" is here!
        'gauge', 'meter', 'controller', 'switch',
        # ... 1,141 equipment terms
    },
    'org': {
        # Manufacturers
        'caterpillar', 'racor', 'volvo', ...
    }
}
```

**Conflict:**
- "filter" is in `gazetteer['equipment']`
- "Air Filter Element" contains "filter"
- Extracted as `equipment` type

**Why not part?**
- No part-specific gazetteer
- No "part_name" entity type in gazetteer
- Part names only extracted if they match part_number regex patterns

**Regex Patterns for Part Names:**
```python
# Lines 488-520: Part number patterns
'part_number': [
    re.compile(r'\b[A-Z]{2,4}[-_ ]?\d{3,7}[-_ ]?[A-Z0-9]{1,4}\b'),  # MTU-12345-XYZ
    re.compile(r'\b(FILT(ER)?|OIL|KIT|SEAL|GASKET|BELT|HOSE)[-_]\d{2,6}(?:[-_][A-Z0-9]{1,3})?\b'),  # FILTER-12345
    # ... more patterns
]
```

These patterns require:
- Alphanumeric codes (FLT-0170-576) ✅ Works
- Keywords + numbers (FILTER-12345) ✅ Works
- Natural language ("Air Filter Element") ❌ Fails - no pattern matches

---

## Issue 3: Generic Part Terms Misclassified

### Current Behavior

**Query:** `"oil filter"`

**Extraction:**
```json
{
  "entities": {
    "equipment": ["Filter"],
    "equipment": ["Oil"]  ← Both as equipment!
  }
}
```

**Same issue as Issue 2** - "oil" and "filter" both in equipment gazetteer.

---

## Entity Type Flow

### From Extraction to Capability

```
┌─────────────────────┐
│ Regex Extractor     │
│ entity.type = 'org' │  ← "Racor" extracted from gazetteer['org']
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Entity Merger       │
│ keeps type = 'org'  │  ← No transformation
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Orchestrator        │
│ groups by type      │  ← {'org': ['Racor']}
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Pipeline V1         │
│ translate frontend  │  ← EXTRACTION_TO_FRONTEND.get('org') → None
│ type stays 'org'    │  ← Fallback: 'org'
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Capability Composer │
│ lookup capability   │  ← ENTITY_TO_SEARCH_COLUMN.get('org') → None
│ NO MAPPING FOUND!   │  ← Error: "No capabilities matched"
└─────────────────────┘
```

### Capability Mapping

**File:** `apps/api/prepare/capability_composer.py` Lines 113-164

**Current Mappings:**
```python
ENTITY_TO_SEARCH_COLUMN = {
    "PART_NUMBER": ("part_by_part_number_or_name", "part_number"),
    "PART_NAME": ("part_by_part_number_or_name", "name"),
    "MANUFACTURER": ("part_by_part_number_or_name", "manufacturer"),  ✅ EXISTS
    "EQUIPMENT_NAME": ("equipment_by_name_or_model", "name"),
    # ... 40+ mappings
}
```

**Missing Mappings:**
- `"ORG"` → No mapping
- `"org"` → No mapping

---

## Current Infrastructure Limitations

### 1. No Dedicated Manufacturer Entity Type

**Gazetteer Structure:**
```python
gazetteer = {
    'equipment': {...},   # 1,141 terms
    'org': {...},         # 32,293 manufacturers + organizations
    'model': {...},       # Model names
    'location': {...},    # Locations
}
```

**Missing:**
```python
'manufacturer': {...}  # Should have 32K manufacturer names
```

### 2. No Part Name Gazetteer

**Current:** Part names only extracted via regex patterns (requires alphanumeric codes)

**Missing:** Gazetteer for common part names:
```python
'part_name': {
    'oil filter', 'air filter', 'fuel filter', 'water pump',
    'alternator', 'starter motor', 'fan belt', 'oil seal',
    # ... common part names
}
```

### 3. Equipment vs Part Disambiguation

**Problem:** Many terms are ambiguous:
- "filter" - Is it a part or equipment?
- "pump" - Is it a part or equipment?
- "valve" - Is it a part or equipment?

**Current:** Always extracted as equipment (from gazetteer)

**Needed:** Context-based disambiguation:
```python
# "oil filter for engine" → part (consumable context)
# "main filter system" → equipment (installed system context)
```

---

## Precedence Order

**File:** `apps/api/extraction/regex_extractor.py` Lines 154-191

```python
PRECEDENCE_ORDER = [
    'fault_code',          # CRITICAL: Must be before po_number
    'location_on_board',   # Multi-word locations before equipment
    'work_order_status',
    'rest_compliance',
    'warning_severity',
    'delivery_date',
    'receiving_status',
    'stock_status',
    'measurement',         # Process measurements BEFORE model patterns
    'measurement_range',
    'setpoint',
    'limit',
    'model',               # Model codes after measurements
    'part_number',         # After model to avoid matching model numbers as parts
    'serial_number',
    # ... more types
]
```

**Note:**
- `'part_number'` is in precedence (line 172)
- `'manufacturer'` is NOT in precedence (doesn't exist as entity type)
- `'part_name'` is NOT in precedence (doesn't exist as entity type)

---

## Solutions

### Option 1: Add 'manufacturer' Entity Type (RECOMMENDED)

**Changes Required:**

1. **regex_extractor.py** (Lines 1018-1023, 1168-1169)
   ```python
   # BEFORE:
   gazetteer['org'] = gazetteer['org'] | filtered_manufacturers

   # AFTER:
   gazetteer['manufacturer'] = filtered_manufacturers
   ```

2. **regex_extractor.py** (Lines 154-191)
   ```python
   PRECEDENCE_ORDER = [
       'fault_code',
       # ...
       'manufacturer',      # ADD THIS - before 'model' to prioritize brand names
       'model',
       'part_number',
       # ...
   ]
   ```

3. **capability_composer.py** (Already exists!)
   ```python
   # Line 117 - Already mapped:
   "MANUFACTURER": ("part_by_part_number_or_name", "manufacturer"),  ✅
   ```

4. **pipeline_v1.py** (Already exists!)
   ```python
   # Line 615 - Already mapped:
   'MANUFACTURER': 'part',  ✅
   ```

**Impact:**
- "Racor" → extracted as 'manufacturer'
- Maps to part_by_part_number_or_name capability
- Searches pms_parts table
- Part Lens microactions appear ✅

---

### Option 2: Add 'ORG' to Capability Mapping (QUICK FIX)

**Changes Required:**

1. **capability_composer.py**
   ```python
   ENTITY_TO_SEARCH_COLUMN = {
       # ... existing mappings ...
       "ORG": ("part_by_part_number_or_name", "manufacturer"),  # ADD THIS
   }
   ```

2. **pipeline_v1.py**
   ```python
   EXTRACTION_TO_FRONTEND = {
       # ... existing mappings ...
       'ORG': 'part',  # ADD THIS
   }
   ```

**Pros:**
- Quick fix, minimal changes
- Works immediately

**Cons:**
- Incorrect semantics (org != manufacturer)
- Assumes all orgs are manufacturers (false)
- Will match corporate names, suppliers, etc.

---

### Option 3: Add Part Name Gazetteer (LONG-TERM)

**Changes Required:**

1. **Create part name gazetteer** (`regex_production_data.py` or new file)
   ```python
   def load_part_names():
       return {
           # Filters
           'oil filter', 'fuel filter', 'air filter', 'hydraulic filter',
           'water filter', 'filter element', 'filter cartridge',

           # Gaskets & Seals
           'oil seal', 'head gasket', 'o-ring', 'seal kit',

           # Pumps
           'water pump', 'fuel pump', 'oil pump', 'coolant pump',

           # Electrical
           'alternator', 'starter motor', 'glow plug', 'ignition coil',

           # Belts & Hoses
           'drive belt', 'v-belt', 'serpentine belt', 'coolant hose',

           # ... 500+ common part names
       }
   ```

2. **regex_extractor.py** - Add to gazetteer
   ```python
   gazetteer = {
       'equipment': {...},
       'manufacturer': {...},  # From Option 1
       'part_name': load_part_names(),  # ADD THIS
       'model': {...},
       'location': {...},
   }
   ```

3. **Add to precedence**
   ```python
   PRECEDENCE_ORDER = [
       'fault_code',
       # ...
       'manufacturer',
       'part_name',  # ADD THIS - extract part names before equipment
       'model',
       'part_number',
       # ...
   ]
   ```

**Benefits:**
- "oil filter", "Air Filter Element" extracted as 'part_name'
- Natural language part searches work
- Better user experience

**Effort:** Medium (requires curating part name list)

---

## Recommended Implementation Plan

### Phase 1: Fix Manufacturer Classification (IMMEDIATE)

**File:** `apps/api/extraction/regex_extractor.py`

1. Line 1168: Change from:
   ```python
   gazetteer['org'] = gazetteer['org'] | filtered_manufacturers
   ```

   To:
   ```python
   gazetteer['manufacturer'] = filtered_manufacturers
   ```

2. Lines 154-191: Add 'manufacturer' to precedence (before 'model')

3. Test queries:
   - "Racor" → Should return 5 Racor parts with microactions ✅
   - "Caterpillar" → Should return CAT parts ✅
   - "Volvo" → Should return Volvo parts ✅

**Estimated Time:** 15 minutes
**Risk:** Low
**Impact:** HIGH - Fixes 32K manufacturer name searches

---

### Phase 2: Improve Equipment vs Part Disambiguation (SHORT-TERM)

**File:** `apps/api/extraction/regex_extractor.py`

Add context checking for ambiguous terms:

```python
def _is_part_context(text, term, span):
    """Check if term appears in part context vs equipment context."""
    # Part indicators
    part_keywords = [
        'replacement', 'spare', 'consumable', 'filter element',
        'order', 'purchase', 'stock', 'inventory', 'part number'
    ]

    # Equipment indicators
    equipment_keywords = [
        'system', 'installed', 'main', 'auxiliary', 'primary',
        'location', 'room', 'deck'
    ]

    # Check 20 chars before and after
    context = text[max(0, span[0]-20):min(len(text), span[1]+20)].lower()

    has_part_context = any(kw in context for kw in part_keywords)
    has_equipment_context = any(kw in context for kw in equipment_keywords)

    return has_part_context and not has_equipment_context
```

**Estimated Time:** 2 hours
**Risk:** Medium
**Impact:** Medium - Improves ambiguous term handling

---

### Phase 3: Add Part Name Gazetteer (LONG-TERM)

**Files:**
1. Create `apps/api/regex_production_data.py` - Add `load_part_names()`
2. Update `apps/api/extraction/regex_extractor.py` - Add to gazetteer

**Estimated Time:** 1 day (research + implementation)
**Risk:** Low
**Impact:** HIGH - Enables natural language part searches

---

## Testing Plan

### Test Queries (After Fixes)

| Query | Expected Entity Type | Expected Results | Microactions |
|-------|---------------------|------------------|--------------|
| Racor | MANUFACTURER | 5 Racor parts | ✅ 4-6 actions |
| Caterpillar | MANUFACTURER | CAT parts | ✅ 4-6 actions |
| FLT-0170-576 | PART_NUMBER | 1 part | ✅ 4 actions (already works) |
| oil filter | PART_NAME | Oil filter parts | ✅ 4-6 actions |
| Air Filter Element | PART_NAME | 1 part | ✅ 4 actions |
| filter | PART_NAME or EQUIPMENT_NAME | Parts or equipment | Depends on context |

### Validation Commands

```bash
# Test manufacturer search
curl -X POST https://pipeline-core.int.celeste7.ai/webhook/search \
  -H "Authorization: Bearer $JWT" \
  -d '{"query": "Racor", "limit": 5}' | jq '.entities, .results[0].actions'

# Expected:
# entities: [{"type": "part", "extraction_type": "MANUFACTURER", "value": "Racor"}]
# actions: [4-6 microactions]

# Test part name search
curl -X POST https://pipeline-core.int.celeste7.ai/webhook/search \
  -H "Authorization: Bearer $JWT" \
  -d '{"query": "oil filter", "limit": 5}' | jq '.entities, .results[0].actions'

# Expected:
# entities: [{"type": "part", "extraction_type": "PART_NAME", "value": "oil filter"}]
# actions: [4-6 microactions]
```

---

## Performance Considerations

### Gazetteer Size

**Current:**
- `gazetteer['org']`: ~32,500 terms
- `gazetteer['equipment']`: ~1,200 terms
- Total: ~34,000 terms

**After Changes:**
- `gazetteer['manufacturer']`: ~32,000 terms (moved from org)
- `gazetteer['part_name']`: ~500-1,000 terms (new)
- Total: ~35,000 terms (+3% growth)

**Impact:** Negligible (gazetteer lookup is O(1) dict lookup)

### Extraction Latency

**Current:** 200-600ms (regex/gazetteer only)

**After Changes:** Same (no algorithmic changes, just reorganization)

---

## Summary

**Current State:**
- ✅ Part Lens microactions working perfectly
- ❌ Manufacturer searches fail (classified as 'org', no mapping)
- ❌ Part name searches fail (classified as 'equipment', wrong table)

**Root Cause:**
- Manufacturers in 'org' gazetteer instead of 'manufacturer'
- No part name gazetteer, conflicts with equipment terms

**Fix Priority:**
1. **HIGH:** Move manufacturers to 'manufacturer' gazetteer (15 min fix)
2. **MEDIUM:** Add part name gazetteer (1 day)
3. **LOW:** Improve disambiguation logic (2 hours)

**Expected Outcome:**
- All manufacturer queries work (Racor, CAT, Volvo, etc.)
- Natural language part searches work (oil filter, air filter, etc.)
- Part Lens microactions appear for all part searches

---

**Created By:** Claude Sonnet 4.5
**Analysis Type:** Infrastructure Deep Dive
**Date:** 2026-02-02
