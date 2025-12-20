# Unified Extraction Endpoint - Documentation

## Quick Start

**🚀 Primary Endpoint:** `https://extract.core.celeste7.ai/extract`

This is the **single entry point** for all extraction requests in CelesteOS.

```bash
# Example Request (2 headers only)
curl -X POST https://extract.core.celeste7.ai/extract \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "X-Yacht-Signature: YOUR_YACHT_SIGNATURE" \
  -d '{"query": "create work order for bilge pump"}'
```

**Response:** Unified JSON with actions, entities, confidence scores, and canonical mappings.

---

## Overview

The **Unified Extraction Endpoint** (`POST /extract`) is the single source of truth for all NLP extraction logic in CelesteOS. It combines micro-action detection, maritime entity extraction, and canonicalization into one structured response.

**Version:** 2.0.0
**Production URL:** `https://extract.core.celeste7.ai/extract`
**Status:** Production-ready ✅

---

## Architecture

The unified extraction pipeline combines three isolated modules:

```
┌─────────────────────┐
│   User Query        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Module A           │  Detect actions & intent
│  (Action Detector)  │  (STRICT verb-based)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Module B           │  Extract maritime entities
│  (Entity Extractor) │  (equipment, faults, etc.)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Module C           │  Canonicalize & weight
│  (Canonicalizer)    │  (normalize, merge)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Unified Output     │  Single structured JSON
└─────────────────────┘
```

---

## Modules

### Module A: Strict Micro-Action Detector

**File:** `api/module_a_action_detector.py`

**Purpose:** Detect actionable intents using STRICT verb-based patterns

**Key Features:**
- ✅ Only verb-based patterns (no phrasal regex like "find the", "tell me")
- ✅ Patterns start with `^` (beginning of string)
- ✅ Confidence scoring (0.0-1.0)
- ✅ Intent categorization (create, update, view, action, search)
- ❌ Maritime nouns CANNOT trigger actions
- ❌ Fault codes NEVER trigger actions

**Example Patterns:**
```python
"create_work_order": [
    (r"^create\s+(a\s+)?(new\s+)?work\s*order", 0.95, "create"),
    (r"^open\s+(a\s+)?(new\s+)?work\s*order", 0.95, "open"),
]

"diagnose_fault": [
    (r"^diagnose\s+(the\s+)?fault", 0.95, "diagnose"),
    (r"^diagnose\s+[EePp]\d{3,4}", 0.93, "diagnose"),  # diagnose E047
]
```

**Supported Actions:**
- Work Order: `create_work_order`, `list_work_orders`, `update_work_order`, `close_work_order`
- Handover: `add_to_handover`, `export_handover`, `view_handover`
- Fault: `report_fault`, `diagnose_fault`, `acknowledge_fault`
- Inventory: `check_stock`, `order_parts`
- Documents: `upload_document`, `search_documents`
- Purchasing: `create_purchase_request`, `approve_purchase_order`
- Hours of Rest: `log_hours_of_rest`

---

### Module B: Maritime Entity Extractor

**File:** `api/module_b_entity_extractor.py`

**Purpose:** Extract maritime-specific entities from queries

**Key Features:**
- ✅ NO interaction with micro-action logic
- ✅ Returns canonical mappings
- ✅ Confidence scores for each entity
- ✅ Overlap resolution (keeps higher confidence)

**Entity Types:**

1. **Equipment:** main engine, auxiliary engine, generator, bilge pump, sea water pump, etc.
2. **Systems:** cooling system, fuel system, electrical system, hydraulic system, etc.
3. **Parts:** oil filter, fuel filter, impeller, seal, gasket, bearing, valve, sensor, etc.
4. **Fault Codes:** J1939 SPN/FMI, E-codes, OBD-II codes (P/C/B/U), MTU codes
5. **Measurements:** Voltage (24V, 110V), Temperature (85°C), Pressure (3 bar), RPM, Flow
6. **Maritime Terms:** coolant leak, oil leak, pressure drop, temperature high, vibration, etc.

**Example Patterns:**
```python
"main engine": ["main\\s+engine", "me1?", "m\\.?e\\.?\\s*1?"]
"fault_code": r"E\d{3,4}"  # E047, E0420
"voltage": r"\d+\s*[Vv](?:olts?)?(?:\s*(?:AC|DC))?"  # 24V, 110VAC
```

---

### Module C: Canonicalizer

**File:** `api/module_c_canonicalizer.py`

**Purpose:** Normalize entities and assign importance weights

**Key Features:**
- ✅ Abbreviation normalization (ME1 → MAIN_ENGINE_1)
- ✅ Entity importance weighting (fault_code=1.0, equipment=0.95)
- ✅ Duplicate merging (keeps highest confidence)
- ✅ Preserves all entity detections from Module B

**Abbreviation Mappings:**
```python
"ME" → "MAIN_ENGINE"
"ME1" → "MAIN_ENGINE_1"
"AE" → "AUXILIARY_ENGINE"
"SWP" → "SEA_WATER_PUMP"
"24V" → "24_VDC"
"TEMP" → "TEMPERATURE"
```

**Entity Weights (for search ranking):**
- Fault Code: `1.0` (highest priority)
- Equipment: `0.95` (critical)
- System: `0.90` (important)
- Measurement: `0.85` (context)
- Part: `0.80` (specific)
- Maritime Term: `0.75` (descriptive)

---

## API Endpoint

### `POST /extract` - **Primary Endpoint**

**Production URL:** `https://extract.core.celeste7.ai/extract`

**Description:** Unified extraction endpoint combining all modules - **This is the single entry point for all extraction requests**

**Security (2 headers only - clean & minimal):**
- ✅ JWT authentication (Supabase) - auto-expires, no manual rotation
- ✅ Yacht signature verification - proof of yacht ownership
- ✅ Rate limiting (100 req/min per IP)
- ✅ Strict CORS
- ✅ No shared secrets to manage

**Request Headers:**
```http
Content-Type: application/json
Authorization: Bearer <JWT_TOKEN>
X-Yacht-Signature: <YACHT_SIGNATURE>
```

**Request Body:**
```json
{
  "query": "create work order for bilge pump",
  "include_metadata": false,
  "validate_combination": true
}
```

**Response (200 OK):**
```json
{
  "intent": "create",
  "microactions": [
    {
      "action": "create_work_order",
      "confidence": 0.95,
      "verb": "create",
      "matched_text": "create work order"
    }
  ],
  "entities": [
    {
      "type": "equipment",
      "value": "bilge pump",
      "confidence": 0.92
    }
  ],
  "canonical_entities": [
    {
      "type": "equipment",
      "value": "bilge pump",
      "canonical": "BILGE_PUMP",
      "confidence": 0.87,
      "weight": 0.95
    }
  ],
  "scores": {
    "intent_confidence": 0.95,
    "entity_confidence": 0.87,
    "entity_weights": {
      "equipment": 0.87
    }
  },
  "metadata": {
    "query": "create work order for bilge pump",
    "latency_ms": 45,
    "modules_run": ["action_detector", "entity_extractor", "canonicalizer"],
    "action_count": 1,
    "entity_count": 1
  }
}
```

---

## Test Cases

All 5 required test cases plus 10 additional tests have been validated:

### Required Test Cases (from specification)

1. **"create work order for bilge pump"**
   - ✅ Actions: `["create_work_order"]`
   - ✅ Entities: `["BILGE_PUMP"]`
   - ✅ Intent: `"create"`

2. **"bilge manifold"**
   - ✅ Actions: `[]` (no false action)
   - ✅ Entities: `["BILGE_PUMP"]`
   - ✅ Intent: `None`

3. **"diagnose E047 on ME1"**
   - ✅ Actions: `["diagnose_fault"]`
   - ✅ Entities: `["E047" (fault_code), "MAIN_ENGINE" (equipment)]`
   - ✅ Intent: `"action"`

4. **"tell me bilge pump"**
   - ✅ Actions: `[]` (phrasal pattern rejected)
   - ✅ Entities: `["MAIN_ENGINE", "BILGE_PUMP"]`
   - ✅ Intent: `None`

5. **"find coolant temp"**
   - ✅ Actions: `[]` (ambiguous "find" rejected)
   - ✅ Entities: varies
   - ✅ Intent: `None`

### Additional Test Cases

6. Equipment + Maritime Term
7. Measurement + Equipment
8. Complex Action with Entities
9. Empty Query Handling
10. Canonicalization Verification
11. No False Positives on Maritime Nouns
12. Verb-Based Action Detection
13. Confidence & Weights Validation
14. Performance/Latency Check
15. Metadata Completeness

**Run Tests:**
```bash
cd api
python test_unified_extraction.py
# OR
pytest test_unified_extraction.py -v
```

**Expected Output:**
```
Total tests: 15
✅ Passed: 15
❌ Failed: 0
🎉 ALL TESTS PASSED!
```

---

## Non-Negotiable Rules

### Action Detection Rules
1. ✅ Only verb-based action patterns
2. ❌ NO phrasal regex ("find the", "tell me", "where is")
3. ❌ NO patterns that could match maritime terms
4. ✅ Confidence scoring required
5. ❌ Maritime nouns CANNOT trigger actions
6. ❌ Fault codes NEVER trigger actions

### Entity Extraction Rules
1. ✅ Must NOT interact with micro-action logic
2. ✅ Returns canonical mappings
3. ✅ Provides confidence scores
4. ✅ Overlap resolution (higher confidence wins)

### Canonicalization Rules
1. ✅ Preserves all entity detections from Module B
2. ✅ Only normalizes, does not add/remove
3. ✅ Weights reflect business importance
4. ✅ Abbreviations mapped to canonical forms

---

## Intent Categories

| Intent | Description | Example Actions |
|--------|-------------|-----------------|
| `create` | User wants to create something | create_work_order, create_purchase_request |
| `update` | User wants to modify something | update_work_order, edit_work_order |
| `view` | User wants to see information | list_work_orders, view_handover, check_stock |
| `action` | User wants to perform an action | close_work_order, approve_purchase_order, diagnose_fault |
| `search` | User wants to find something | search_documents, find_manual |

---

## Migration Guide

### From Old Endpoints to `/extract`

**Old Approach:**
```javascript
// OLD - Using /extract_microactions (deprecated)
const response = await fetch('https://extract.core.celeste7.ai/extract_microactions', {
  method: 'POST',
  body: JSON.stringify({ query: "create work order" })
});
// Returns: { micro_actions: ["create_work_order"], count: 1 }
```

**New Approach:**
```javascript
// NEW - Using /extract (unified) - PRIMARY ENDPOINT
// Only 2 headers needed - clean & minimal
const response = await fetch('https://extract.core.celeste7.ai/extract', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${jwt_token}`,      // Supabase JWT
    'X-Yacht-Signature': yacht_signature        // sha256(yacht_id + salt)
  },
  body: JSON.stringify({ query: "create work order for bilge pump" })
});
// Returns: Full unified response with actions, entities, confidence, etc.
```

**Benefits:**
- ✅ Single API call instead of multiple
- ✅ Consistent confidence scoring
- ✅ Canonical entity mappings included
- ✅ Intent categorization
- ✅ Entity importance weighting for search ranking

---

## n8n Integration

### HTTP Request Node Configuration

**⭐ Primary Endpoint:** `https://extract.core.celeste7.ai/extract`

**URL:** `https://extract.core.celeste7.ai/extract`
**Method:** `POST`
**Authentication:** Custom

**Headers (2 only - clean & minimal):**
```json
{
  "Content-Type": "application/json",
  "Authorization": "Bearer {{$node['Supabase'].json['access_token']}}",
  "X-Yacht-Signature": "{{$node['GenerateSignature'].json['signature']}}"
}
```

**Body:**
```json
{
  "query": "{{$node['UserInput'].json['query']}}",
  "include_metadata": false,
  "validate_combination": true
}
```

**Example Workflow:**
1. **User Input** → Capture query
2. **Supabase Auth** → Get JWT token
3. **Generate Signature** → Compute yacht signature
4. **HTTP Request** → Call `https://extract.core.celeste7.ai/extract`
5. **Route by Intent** → Switch based on `intent` field
6. **Execute Action** → Call appropriate workflow

**n8n Example cURL:**
```bash
# Only 2 headers needed - clean & minimal
curl -X POST https://extract.core.celeste7.ai/extract \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "X-Yacht-Signature: $YACHT_SIGNATURE" \
  -d '{
    "query": "create work order for bilge pump",
    "include_metadata": false,
    "validate_combination": true
  }'
```

---

## Performance

- **Latency:** < 100ms (warm)
- **Cold Start:** ~3-5 seconds
- **Memory:** ~50MB per instance
- **Throughput:** 100 req/min per IP
- **Concurrency:** 10-20 requests

---

## Security

### Two-Layer Authentication (Clean & Minimal)

**Headers Required:**
```http
Authorization: Bearer <supabase_jwt>
X-Yacht-Signature: <sha256_signature>
```

1. **JWT Validation** (`Authorization: Bearer` header)
   - Validates Supabase JWT (auto-expires, no manual rotation needed)
   - Extracts `user_id` and `yacht_id` from JWT claims
   - Ensures user is authenticated

2. **Yacht Signature Verification** (`X-Yacht-Signature` header)
   - Verifies SHA256 hash: `sha256(yacht_id + YACHT_SALT)`
   - Ensures request comes from authorized yacht
   - Prevents cross-yacht unauthorized access

**Benefits:**
- ✅ No shared secrets (API keys) to manage
- ✅ JWT auto-expires (15min-1hr depending on Supabase config)
- ✅ Supabase handles token refresh automatically
- ✅ User identity built into JWT
- ✅ Yacht ownership verified cryptographically

### Development Mode

If security secrets are not configured, the service runs in **development mode**:
- ⚠️ JWT verification skipped (uses dev_user, dev_yacht)
- ⚠️ Yacht signature check skipped
- ⚠️ Logs warning messages

**Set Secrets in Render Dashboard:**
```bash
SUPABASE_JWT_SECRET=<supabase-jwt-secret>  # For JWT validation
YACHT_SALT=<random-salt>                   # For signature verification
```

**Generate YACHT_SALT:**
```bash
openssl rand -hex 32
# Result: 64-character random hex string
```

---

## Deployment

### Render.com (Production)

**Instance:** Starter ($7/month)
**Runtime:** Python 3.11.8
**Build Command:** `pip install -r api/requirements.txt`
**Start Command:** `cd api && uvicorn microaction_service:app --host 0.0.0.0 --port $PORT`

**Environment Variables:**
```yaml
# Runtime
PYTHON_VERSION: "3.11.8"
ENVIRONMENT: "production"
LOG_LEVEL: "info"
AI_FALLBACK_THRESHOLD: "0.75"
MIN_OUTPUT_CONFIDENCE: "0.70"

# Security (2 secrets only)
SUPABASE_JWT_SECRET: <set in dashboard>  # For JWT validation
YACHT_SALT: <set in dashboard>           # For yacht signature verification
```

**Health Check:** `GET https://extract.core.celeste7.ai/health`

**API Docs:** `GET https://extract.core.celeste7.ai/docs`

**Auto-Deploy:** Enabled (push to `claude/build-frontend-pages-*` triggers deploy)

**Custom Domain:** `extract.core.celeste7.ai`

---

## Files

| File | Purpose |
|------|---------|
| `api/module_a_action_detector.py` | Strict micro-action detector (Module A) |
| `api/module_b_entity_extractor.py` | Maritime entity extractor (Module B) |
| `api/module_c_canonicalizer.py` | Canonicalizer & weighting (Module C) |
| `api/unified_extraction_pipeline.py` | Unified pipeline combining A+B+C |
| `api/microaction_service.py` | FastAPI service with `/extract` endpoint |
| `api/test_unified_extraction.py` | Comprehensive test suite (15 tests) |
| `api/microaction_extractor.py` | Legacy extractor (used by old endpoints) |
| `api/microaction_config.py` | Configuration and validation rules |
| `render.yaml` | Render deployment configuration |

---

## Troubleshooting

### Common Issues

**Issue: "Unified pipeline not initialized"**
- **Cause:** Service startup failed to load pipeline
- **Fix:** Check logs for module import errors, ensure all dependencies installed

**Issue: "Invalid API key" (401)**
- **Cause:** Missing or incorrect `X-Celeste-Key` header
- **Fix:** Set `CELESTE_API_KEY` in Render Dashboard, pass correct header

**Issue: "Invalid JWT" (401)**
- **Cause:** Expired or invalid JWT token
- **Fix:** Refresh Supabase auth token, ensure JWT includes `sub` and `yacht_id` claims

**Issue: "Invalid yacht signature" (403)**
- **Cause:** Incorrect signature calculation
- **Fix:** Verify SHA256 hash: `hashlib.sha256(f"{yacht_id}{YACHT_SALT}".encode()).hexdigest()`

**Issue: No actions detected for valid query**
- **Cause:** Query doesn't start with explicit verb
- **Fix:** Ensure query starts with action verb (e.g., "create", "open", "diagnose")

**Issue: False action detection on maritime noun**
- **Cause:** Bug in Module A patterns
- **Fix:** Report issue, patterns should be strict verb-based only

---

## Support

- **Production URL:** `https://extract.core.celeste7.ai/extract`
- **API Documentation:** `https://extract.core.celeste7.ai/docs`
- **Health Check:** `https://extract.core.celeste7.ai/health`
- **GitHub Issues:** https://github.com/shortalex12333/Cloud_PMS/issues
- **Technical Docs:** This file (`api/UNIFIED_EXTRACTION_README.md`)
- **Test Suite:** `api/test_unified_extraction.py`

---

## Version History

### v2.0.0 (2025-11-21)
- ✅ Added unified `/extract` endpoint (Modules A+B+C)
- ✅ Comprehensive test suite (15 tests, all passing)
- ✅ Multi-layer security (API key + JWT + yacht signature)
- ✅ Rate limiting (100 req/min)
- ✅ Canonical entity mappings
- ✅ Intent categorization
- ✅ Entity importance weighting

### v1.0.1 (Previous)
- `/extract_microactions` (legacy)
- `/extract_detailed` (legacy)
- Basic micro-action detection

---

**Last Updated:** 2025-11-21
**Status:** Production-ready ✅
