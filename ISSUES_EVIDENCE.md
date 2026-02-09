# Issues Evidence Report

**Date**: 2026-02-01
**Analysis**: Production API vs Documentation Comparison
**Method**: Direct API testing with fresh JWT token

---

## Summary

**3 Critical Issues Identified** requiring documentation fixes:

1. ❌ **Entity field name mismatch** - Documentation incorrect
2. ⚠️  **results_by_domain behavior** - Documentation incomplete
3. ❌ **Entity type naming inconsistency** - Documentation uses different names

**Impact**: Engineers following current documentation will write code that fails when calling production API.

---

## Issue #1: Entity Field Name Mismatch

### Evidence

**Production API Response** (Actual):
```json
{
  "entities": [
    {
      "type": "equipment",
      "value": "Filter",
      "confidence": 0.8,
      "extraction_type": "EQUIPMENT_NAME"
    },
    {
      "type": "marine brand",
      "value": "caterpillar",
      "confidence": 0.8,
      "extraction_type": "MARINE_BRAND"
    },
    {
      "type": "work order equipment",
      "value": "Filter",
      "confidence": 0.72,
      "source": "work_order_lens_transformation",
      "extraction_type": "WORK_ORDER_EQUIPMENT"
    }
  ]
}
```

**Current Documentation** (API_INTEGRATION_GUIDE.md, line ~202):
```json
{
  "entities": [
    {
      "text": "oil filter",
      "type": "part",
      "confidence": 0.85,
      "source": "regex",
      "span": [0, 10]
    }
  ]
}
```

### Field Comparison

| Field | Documentation | Production | Status |
|-------|---------------|------------|--------|
| `text` | ✅ Present | ❌ Missing | **WRONG** |
| `value` | ❌ Missing | ✅ Present | **UNDOCUMENTED** |
| `type` | ✅ Present | ✅ Present | ✅ Match |
| `confidence` | ✅ Present | ✅ Present | ✅ Match |
| `source` | ✅ Present | ⚠️ Optional | **INCONSISTENT** |
| `extraction_type` | ❌ Missing | ✅ Present | **UNDOCUMENTED** |
| `span` | ✅ Present | ❌ Missing | **WRONG** |

### Impact

**Code that will FAIL**:
```javascript
// Following current documentation
result.entities.forEach(entity => {
  console.log(entity.text);  // ❌ undefined - field doesn't exist
  console.log(entity.span);  // ❌ undefined - field doesn't exist
});
```

**Code that will WORK**:
```javascript
// Using actual API format
result.entities.forEach(entity => {
  console.log(entity.value);  // ✅ Works
  console.log(entity.extraction_type);  // ✅ Works
});
```

### Root Cause

Documentation was written based on internal extraction pipeline format, not the actual API response format. The API applies transformations before returning entities to clients.

---

## Issue #2: results_by_domain Behavior

### Evidence

**Production API Response** (Actual):
```json
{
  "results": [
    {/* 8 results */}
  ],
  "results_by_domain": {},  // ❌ EMPTY
  "total_count": 8
}
```

**Current Documentation** (API_INTEGRATION_GUIDE.md, line ~208):
```json
{
  "results_by_domain": {
    "parts": [
      {/* part results */}
    ],
    "equipment": [
      {/* equipment results */}
    ],
    "work_orders": [
      {/* work order results */}
    ]
  }
}
```

### Observation

The `results_by_domain` field is present in the API response but returns an **empty object** `{}` in production.

**Possible causes**:
1. Feature not yet implemented in production
2. Only populated for certain query types
3. Requires specific request parameter

### Test Evidence

Query tested: `"oil filter caterpillar"`

```bash
export JWT_TOKEN=$(cat /tmp/jwt_token.txt)
curl -X POST https://pipeline-core.int.celeste7.ai/webhook/search \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "oil filter caterpillar", "limit": 10}' | jq '.results_by_domain'

# Output: {}
```

### Impact

**Moderate** - Code expecting grouped results will receive empty object:

```javascript
// Following documentation
const parts = result.results_by_domain.parts;  // ✅ No error, but undefined
const equipment = result.results_by_domain.equipment;  // ✅ No error, but undefined

if (parts) {
  // This code never executes
}
```

**Workaround**: Use `results` array instead, which is properly populated.

---

## Issue #3: Entity Type Naming Inconsistency

### Evidence

**Production API Entity Types** (from actual response):
```
- "equipment"
- "marine brand"
- "work order equipment"
```

**Documentation Entity Types** (API_INTEGRATION_GUIDE.md, line ~568):
```
Type                Description
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
fault_code          Equipment error codes
measurement         Quantities with units
model               Equipment model numbers
equipment           Equipment names
part_number         OEM part numbers
org                 Organizations/brands      ← Documentation says "org"
document_id         Document identifiers
...
```

### Comparison

| Concept | Documentation | Production | Match |
|---------|---------------|------------|-------|
| Equipment | `equipment` | `equipment` | ✅ |
| Brand/Org | `org` | `marine brand` | ❌ |
| Part | `part` | (not in sample) | ❓ |
| Work Order Equipment | (not documented) | `work order equipment` | ❌ |

### Test Evidence

Query: `"oil filter caterpillar"`

Expected entities (per documentation):
- Type: `part` for "oil filter"
- Type: `org` for "caterpillar"

Actual entities (from production):
- Type: `equipment` for "Filter"
- Type: `marine brand` for "caterpillar"
- Type: `equipment` for "Oil"
- Type: `work order equipment` for "Filter"

### Impact

**Code assuming specific type names will fail**:

```javascript
// Following documentation
const brands = result.entities.filter(e => e.type === 'org');
console.log(brands.length);  // ❌ 0 - wrong type name

// Should be:
const brands = result.entities.filter(e => e.type === 'marine brand');
console.log(brands.length);  // ✅ 1 - correct
```

### Root Cause

The production API uses domain-specific entity types ("marine brand", "work order equipment") that differ from the generic entity extraction pipeline types ("org", "part"). Documentation reflects internal pipeline, not API output.

---

## Additional Observations

### Working Features (Not Issues)

1. ✅ **Response structure** - Top-level fields correct:
   - `success`, `ok`, `results`, `total_count`, `entities`, `timing_ms`

2. ✅ **Authentication** - JWT Bearer token working correctly

3. ✅ **Search functionality** - Returning relevant results

4. ✅ **Confidence scores** - Present and reasonable (0.72 - 0.80)

5. ✅ **Timing metrics** - Accurate performance data

### New Fields (Not Documented)

Production API includes additional fields not in documentation:

- `extraction_type`: Entity extraction method (e.g., "EQUIPMENT_NAME", "MARINE_BRAND")
- `plans`: Array of query execution plans
- `available_actions`: Array of possible actions on results
- `prepare_debug`: Debug info about entity mapping
- `code_version`: API version timestamp
- `request_id`: Request tracking ID
- `score_components`: Detailed scoring breakdown for each result

---

## Test Environment

**Date**: 2026-02-01
**Endpoint**: `https://pipeline-core.int.celeste7.ai/webhook/search`
**Method**: POST
**Auth**: JWT Bearer token (fresh, expires in 1 hour)
**User**: x@alex-short.com
**Query**: "oil filter caterpillar"
**Response**: Saved to `/tmp/search_response.json`

### Reproduction Steps

1. **Get JWT token**:
   ```bash
   python3 /private/tmp/claude/-Volumes-Backup-CELESTE/2c7d59b4-1f2a-49d5-a582-d77d8ac60cb0/scratchpad/get_token.py
   ```

2. **Export token**:
   ```bash
   export JWT_TOKEN=$(cat /tmp/jwt_token.txt)
   ```

3. **Test search**:
   ```bash
   curl -X POST https://pipeline-core.int.celeste7.ai/webhook/search \
     -H "Authorization: Bearer $JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"query": "oil filter caterpillar", "limit": 10}' > /tmp/search_response.json
   ```

4. **Analyze response**:
   ```bash
   cat /tmp/search_response.json | jq '.entities'
   cat /tmp/search_response.json | jq '.results_by_domain'
   ```

---

## Recommended Actions

### Priority 1: Fix Entity Documentation (CRITICAL)

**File**: `API_INTEGRATION_GUIDE.md`

**Changes needed**:
1. Replace `text` with `value` in all entity examples
2. Replace `source` with `extraction_type` (note: some entities have both)
3. Remove `span` field from documentation
4. Update entity type names to match production ("marine brand" not "org")
5. Document optional `source` field
6. Add `extraction_type` field to examples

### Priority 2: Fix results_by_domain Documentation (MODERATE)

**File**: `API_INTEGRATION_GUIDE.md`

**Changes needed**:
1. Mark `results_by_domain` as "Currently returns empty object in production"
2. Recommend using `results` array instead
3. Update code examples to not rely on `results_by_domain`

### Priority 3: Document Additional Fields (LOW)

**File**: `API_INTEGRATION_GUIDE.md`

**Changes needed**:
1. Document `extraction_type` field
2. Document `plans` array
3. Document `available_actions` array
4. Document `prepare_debug` object
5. Document `code_version` field
6. Document `request_id` field

---

## Validation Plan

After fixes applied:

1. **Re-test with production API** to verify documentation matches
2. **Create code samples** using documented format
3. **Test code samples** against production API
4. **Verify no errors** in sample code execution
5. **Document any remaining edge cases**

---

**Evidence Compiled By**: Systematic API analysis
**Source**: Production endpoint `/webhook/search`
**Status**: Ready for remediation
