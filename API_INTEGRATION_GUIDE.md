# Production API Integration Guide - Search & Entity Extraction

**Version**: 2.0 (Post-Async Refactor)
**Last Updated**: 2026-01-30
**Status**: ✅ Production Ready

---

## Quick Start

### Production Base URL
```
https://pipeline-core.int.celeste7.ai
```

### Authentication
All endpoints require JWT authentication via Bearer token.

**Get Token**:
```bash
# Using Supabase Auth
curl -X POST https://qvzmkaamzaqxpzbewjxe.supabase.co/auth/v1/token?grant_type=password \
  -H "apikey: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF2em1rYWFtemFxeHB6YmV3anhlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM5NzkwNDYsImV4cCI6MjA3OTU1NTA0Nn0.MMzzsRkvbug-u19GBUnD0qLDtMVWEbOf6KE8mAADaxw" \
  -H "Content-Type: application/json" \
  -d '{"email": "your@email.com", "password": "yourpassword"}'
```

Response includes `access_token` - use this as your JWT.

---

## Endpoint 1: Primary Search (Recommended)

### `/webhook/search` - Main Search Endpoint

**Use this for**: All standard search queries, entity extraction, and retrieval

**Method**: `POST`

**URL**: `https://pipeline-core.int.celeste7.ai/webhook/search`

**Headers**:
```
Authorization: Bearer <YOUR_JWT_TOKEN>
Content-Type: application/json
```

**Request Body**:
```json
{
  "query": "oil filter for caterpillar c32",
  "limit": 20
}
```

**Parameters**:
- `query` (string, required): Search query text
- `limit` (integer, optional): Max results to return (default: 20, max: 100)

---

### Response Format

```json
{
  "ok": true,
  "success": true,
  "results": [
    {
      "id": "part_12345",
      "type": "part",
      "title": "Oil Filter - Caterpillar C32",
      "description": "Genuine Caterpillar oil filter for C32 engines",
      "confidence": 0.95,
      "metadata": {
        "part_number": "1R-0750",
        "manufacturer": "Caterpillar",
        "model_compatibility": ["C32"]
      }
    }
  ],
  "results_by_domain": {},  // ⚠️ Currently empty in production - use results array instead
  "total_count": 15,
  "entities": [
    {
      "type": "equipment",
      "value": "oil filter",
      "confidence": 0.85,
      "extraction_type": "EQUIPMENT_NAME"
    },
    {
      "type": "marine brand",
      "value": "caterpillar",
      "confidence": 0.95,
      "extraction_type": "MARINE_BRAND"
    },
    {
      "type": "model",
      "value": "c32",
      "confidence": 0.90,
      "extraction_type": "MODEL"
    }
  ],
  "timing_ms": {
    "extraction": 245.3,
    "retrieval": 180.2,
    "total": 450.5
  }
}
```

**Response Fields**:
- `ok` / `success`: Request succeeded
- `results`: Array of search results (all domains)
- `results_by_domain`: ⚠️ **Currently returns empty object `{}` in production**. Use `results` array instead.
- `total_count`: Total number of results
- `entities`: Extracted entities from query (see Entity Extraction section)
- `timing_ms`: Performance metrics

---

### Code Examples

#### JavaScript/Node.js
```javascript
const axios = require('axios');

async function search(query, jwtToken) {
  const response = await axios.post(
    'https://pipeline-core.int.celeste7.ai/webhook/search',
    {
      query: query,
      limit: 20
    },
    {
      headers: {
        'Authorization': `Bearer ${jwtToken}`,
        'Content-Type': 'application/json'
      },
      timeout: 15000
    }
  );

  return response.data;
}

// Usage
const token = 'your_jwt_token_here';
const result = await search('oil filter for caterpillar c32', token);

console.log(`Found ${result.total_count} results`);
console.log('Extracted entities:', result.entities);
console.log('Results:', result.results);  // Use results array (results_by_domain is empty)
```

#### Python
```python
import requests

def search(query: str, jwt_token: str):
    """Execute search query against production API"""
    url = "https://pipeline-core.int.celeste7.ai/webhook/search"

    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }

    data = {
        "query": query,
        "limit": 20
    }

    response = requests.post(url, headers=headers, json=data, timeout=15)
    response.raise_for_status()
    return response.json()

# Usage
token = "your_jwt_token_here"
result = search("oil filter for caterpillar c32", token)

print(f"Found {result['total_count']} results")
print(f"Entities: {result['entities']}")
print(f"Results: {result['results']}")  # Use results array (results_by_domain is empty)
```

#### cURL
```bash
curl -X POST https://pipeline-core.int.celeste7.ai/webhook/search \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "oil filter for caterpillar c32",
    "limit": 20
  }'
```

#### TypeScript (with Types)
```typescript
interface SearchRequest {
  query: string;
  limit?: number;
}

interface Entity {
  type: string;
  value: string;
  confidence: number;
  extraction_type: string;
  source?: string;  // Optional: present for some entity types
}

interface SearchResponse {
  ok: boolean;
  success: boolean;
  results: any[];
  results_by_domain: Record<string, any[]>;  // ⚠️ Currently empty {} in production
  total_count: number;
  entities: Entity[];
  timing_ms: {
    extraction: number;
    retrieval: number;
    total: number;
  };
}

async function search(
  query: string,
  jwtToken: string
): Promise<SearchResponse> {
  const response = await fetch(
    'https://pipeline-core.int.celeste7.ai/webhook/search',
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${jwtToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ query, limit: 20 })
    }
  );

  if (!response.ok) {
    throw new Error(`Search failed: ${response.statusText}`);
  }

  return await response.json();
}

// Usage
const result = await search('oil filter for caterpillar c32', token);
console.log(`Found ${result.total_count} results`);
result.entities.forEach(entity => {
  console.log(`- ${entity.value} (${entity.type}, ${entity.confidence})`);
});
```

---

## Endpoint 2: Orchestrated Search V2 (Advanced)

### `/v2/search` - Orchestrated Search with Trust Payload

**Use this for**:
- Advanced search with explainability
- Context-aware search (inbox, entity detail views)
- Debugging query routing
- Applications requiring trust/transparency

**Method**: `POST`

**URL**: `https://pipeline-core.int.celeste7.ai/v2/search`

**Headers**:
```
Authorization: Bearer <YOUR_JWT_TOKEN>
Content-Type: application/json
```

**Request Body**:
```json
{
  "query_text": "pending shopping list items",
  "surface_state": "search",
  "open_entity_type": null,
  "open_entity_id": null,
  "open_thread_id": null,
  "direction_bias": "inbound",
  "debug": false
}
```

**Parameters**:
- `query_text` (string): Search query (can be empty for inbox)
- `surface_state` (string): UI surface state
  - `"search"` - Search interface
  - `"inbox"` - Inbox view
  - `"entity_detail"` - Entity detail view
- `open_entity_type` (string|null): Type of open entity (e.g., "equipment", "work_order")
- `open_entity_id` (string|null): ID of open entity
- `open_thread_id` (string|null): Email thread ID if applicable
- `direction_bias` (string): Email direction bias
  - `"inbound"` - Prioritize incoming emails
  - `"outbound"` - Prioritize outgoing emails
  - `"bidirectional"` - Both directions
- `debug` (boolean): Include debug payload (default: false)

---

### Response Format

```json
{
  "success": true,
  "request_id": "req_abc123xyz",
  "results": [
    {/* search results */}
  ],
  "results_by_domain": {
    "shopping_list": [
      {/* shopping list items */}
    ]
  },
  "total_count": 12,
  "trust": {
    "path": "shopping_list_explicit",
    "scopes": ["shopping_list:pending"],
    "time_window_days": 90,
    "used_vector": false,
    "explain": "Routed via Shopping List Explicit path because query contains 'shopping list' keywords. Using SQL-based retrieval with pending status filter over 90-day window."
  },
  "timing_ms": {
    "orchestration": 45.2,
    "execution": 320.8,
    "total": 366.0
  },
  "debug": {
    /* Only if debug: true */
    "classification": {
      "has_query_text": true,
      "has_entities": true,
      "entity_types": ["status"],
      "query_intent": "search"
    },
    "plan": {
      "path": "shopping_list_explicit",
      "scopes": ["shopping_list:pending"],
      "filters": {"status": "pending"}
    }
  }
}
```

**Response Fields**:
- `success`: Request succeeded
- `request_id`: Unique request identifier for tracing
- `results`: Search results
- `results_by_domain`: Results grouped by domain
- `total_count`: Total results
- `trust`: **Explainability payload** - explains WHY these results were returned
  - `path`: Routing path used (e.g., "shopping_list_explicit", "inbox_email_implicit")
  - `scopes`: Data scopes queried
  - `time_window_days`: Time window applied
  - `used_vector`: Whether vector search was used
  - `explain`: Human-readable explanation
- `timing_ms`: Performance breakdown
- `debug`: Debug information (if requested)

---

### Code Examples

#### JavaScript/Node.js
```javascript
async function orchestratedSearch(params, jwtToken) {
  const response = await axios.post(
    'https://pipeline-core.int.celeste7.ai/v2/search',
    {
      query_text: params.query || '',
      surface_state: params.surface || 'search',
      open_entity_type: params.entityType || null,
      open_entity_id: params.entityId || null,
      open_thread_id: params.threadId || null,
      direction_bias: params.direction || 'inbound',
      debug: params.debug || false
    },
    {
      headers: {
        'Authorization': `Bearer ${jwtToken}`,
        'Content-Type': 'application/json'
      }
    }
  );

  return response.data;
}

// Usage: Search interface
const result = await orchestratedSearch({
  query: 'pending shopping list items',
  surface: 'search'
}, token);

console.log('Trust:', result.trust.explain);
console.log('Results:', result.total_count);

// Usage: Inbox view (no query)
const inboxResult = await orchestratedSearch({
  query: '',
  surface: 'inbox',
  direction: 'inbound'
}, token);

console.log('Inbox routing:', inboxResult.trust.path);

// Usage: Entity detail view
const detailResult = await orchestratedSearch({
  query: 'maintenance history',
  surface: 'entity_detail',
  entityType: 'equipment',
  entityId: 'eq_12345'
}, token);

console.log('Context-aware results:', detailResult.total_count);
```

#### Python
```python
def orchestrated_search(
    query_text: str = "",
    surface_state: str = "search",
    open_entity_type: str = None,
    open_entity_id: str = None,
    open_thread_id: str = None,
    direction_bias: str = "inbound",
    debug: bool = False,
    jwt_token: str = None
):
    """Execute orchestrated search with context awareness"""
    url = "https://pipeline-core.int.celeste7.ai/v2/search"

    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }

    data = {
        "query_text": query_text,
        "surface_state": surface_state,
        "open_entity_type": open_entity_type,
        "open_entity_id": open_entity_id,
        "open_thread_id": open_thread_id,
        "direction_bias": direction_bias,
        "debug": debug
    }

    response = requests.post(url, headers=headers, json=data, timeout=15)
    response.raise_for_status()
    return response.json()

# Usage
result = orchestrated_search(
    query_text="pending shopping list items",
    surface_state="search",
    jwt_token=token
)

print(f"Trust: {result['trust']['explain']}")
print(f"Results: {result['total_count']}")
```

---

## Endpoint 3: Plan Only (Debugging)

### `/v2/search/plan` - Get Retrieval Plan Without Execution

**Use this for**:
- Debugging query classification
- Understanding routing logic
- Testing orchestration without database queries

**Method**: `POST`

**URL**: `https://pipeline-core.int.celeste7.ai/v2/search/plan`

**Request**: Same as `/v2/search`

**Response**:
```json
{
  "success": true,
  "request_id": "req_xyz789",
  "plan": {
    "path": "shopping_list_explicit",
    "scopes": ["shopping_list:pending"],
    "time_window_days": 90,
    "use_vector": false,
    "use_sql": true,
    "filters": {
      "status": "pending"
    }
  },
  "classification": {
    "has_query_text": true,
    "has_entities": true,
    "entity_types": ["status"],
    "query_intent": "search"
  }
}
```

**Usage**:
```javascript
// Get plan without executing query
const plan = await axios.post(
  'https://pipeline-core.int.celeste7.ai/v2/search/plan',
  { query_text: 'pending shopping list items', surface_state: 'search' },
  { headers: { 'Authorization': `Bearer ${token}` }}
);

console.log('Would route via:', plan.data.plan.path);
console.log('Would query scopes:', plan.data.plan.scopes);
```

---

## Endpoint 4: Health Check

### `/v2/search/health` - Service Health Status

**Use this for**: Monitoring, uptime checks, deployment validation

**Method**: `GET`

**URL**: `https://pipeline-core.int.celeste7.ai/v2/search/health`

**Authentication**: Not required

**Response**:
```json
{
  "status": "healthy",
  "orchestrator_ready": true,
  "has_intent_parser": true,
  "has_entity_extractor": true
}
```

**Usage**:
```bash
# Simple health check
curl https://pipeline-core.int.celeste7.ai/v2/search/health

# Monitoring script
if curl -f https://pipeline-core.int.celeste7.ai/v2/search/health; then
  echo "Service healthy"
else
  echo "Service down!"
  # Alert team
fi
```

---

## Entity Extraction Deep Dive

### What Are Entities?

Entities are **structured data extracted from natural language queries** using a 5-stage pipeline:

1. **Clean**: Normalize text, expand brand abbreviations
2. **Regex**: Extract using 60+ specialized patterns
3. **Coverage**: Decide if AI extraction needed
4. **AI**: GPT-4o-mini extraction for gaps (when needed)
5. **Merge**: Deduplicate and resolve overlaps

### Entity Types

```
Type                Description                        Example
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
fault_code          Equipment error codes              "P0420", "SPN 157 FMI 3"
measurement         Quantities with units              "5 gallons", "3000 RPM"
model               Equipment model numbers            "C32", "QSM11", "6068TFM75"
equipment           Equipment names                    "main engine", "generator"
part_number         OEM part numbers                   "1R-0750", "3406-1234"
org                 Organizations/brands               "Caterpillar", "Cummins"
document_id         Document identifiers               "WO-2024-001", "INV-12345"
identifier          Generic IDs                        "Serial: ABC123"
status              State descriptors                  "pending", "completed"
symptom             Fault symptoms                     "overheating", "vibration"
system              System categories                  "fuel system", "cooling"
location_on_board   Vessel locations                   "engine room", "bridge"
person              People names                       "Captain Smith"
document_type       Document categories                "invoice", "manual"
date                Temporal dates                     "2024-01-15"
time                Temporal times                     "14:30"
action              Action verbs                       "inspect", "replace"
```

### Entity Confidence Scores

Each entity has a confidence score (0.0-1.0):

```
Source              Confidence Multiplier
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Regex pattern       1.0  (highest)
Gazetteer match     0.95 (curated lists)
Proper noun         0.85 (capitalization)
AI extraction       0.70 (GPT-4o-mini)
Fallback Python     0.90 (Python extractors)
```

Only entities meeting type-specific thresholds are returned (e.g., equipment: 0.70, model: 0.75).

### Using Entities in Your Application

#### Example 1: Search Filters from Entities
```javascript
const result = await search('oil filter for caterpillar c32', token);

// Extract entities
const partEntities = result.entities.filter(e => e.type === 'equipment');
const brandEntities = result.entities.filter(e => e.type === 'marine brand');
const modelEntities = result.entities.filter(e => e.type === 'model');

// Build filters
const filters = {
  part_name: partEntities.map(e => e.value),
  manufacturer: brandEntities.map(e => e.value),
  model: modelEntities.map(e => e.value)
};

console.log(filters);
// {
//   part_name: ['oil filter'],
//   manufacturer: ['caterpillar'],
//   model: ['c32']
// }
```

#### Example 2: Intent Detection
```javascript
const result = await search('error code P0420 high temperature', token);

const hasFaultCode = result.entities.some(e => e.type === 'fault_code');
const hasSymptom = result.entities.some(e => e.type === 'symptom');

if (hasFaultCode) {
  // Route to fault diagnosis flow
  console.log('Fault code detected:', result.entities.find(e => e.type === 'fault_code').text);
}

if (hasSymptom) {
  // Suggest troubleshooting
  console.log('Symptom detected:', result.entities.find(e => e.type === 'symptom').text);
}
```

#### Example 3: Auto-complete Suggestions
```javascript
// User types: "cat"
const result = await search('cat', token);

const brandEntity = result.entities.find(e => e.type === 'marine brand');
if (brandEntity && brandEntity.value === 'caterpillar') {
  // Suggest full brand name
  console.log('Did you mean: Caterpillar?');
}
```

---

## Performance & Optimization

### Expected Latency

```
Query Type                  Typical Latency
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Simple part search          200-400ms
Equipment + model search    300-600ms
Complex multi-entity        400-800ms
Semantic/AI search          2000-6000ms
Document search             3000-6000ms
```

### Fast Path vs AI Path

**Fast Path** (200-600ms):
- Query fully covered by regex extraction
- No AI call needed
- ~70% of queries

**AI Path** (2000-6000ms):
- Query has significant gaps after regex extraction
- GPT-4o-mini called to extract from gaps
- ~30% of queries

### Optimization Tips

#### 1. Use Specific Queries
```javascript
// Slow (triggers AI)
await search('stuff for the thing', token);

// Fast (regex-only)
await search('oil filter caterpillar', token);
```

#### 2. Batch Requests
```javascript
// Instead of sequential
for (const query of queries) {
  await search(query, token);
}

// Use parallel requests
const results = await Promise.all(
  queries.map(q => search(q, token))
);
```

#### 3. Cache Results Client-Side
```javascript
const cache = new Map();

async function cachedSearch(query, token) {
  if (cache.has(query)) {
    return cache.get(query);
  }

  const result = await search(query, token);
  cache.set(query, result);
  return result;
}
```

#### 4. Use Timeouts
```javascript
// Set appropriate timeout
const result = await axios.post(url, data, {
  headers,
  timeout: 10000  // 10s timeout
});
```

---

## Error Handling

### HTTP Status Codes

```
Code    Meaning                 Action
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
200     Success                 Process results
400     Bad Request             Check request format
401     Unauthorized            Refresh JWT token
403     Forbidden               Check permissions
429     Rate Limited            Retry with backoff
500     Server Error            Retry, then alert
503     Service Unavailable     Retry with backoff
```

### Error Response Format

```json
{
  "ok": false,
  "success": false,
  "error": "Error message here",
  "detail": "Detailed error information"
}
```

### Recommended Error Handling

#### JavaScript
```javascript
async function safeSearch(query, token, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const result = await search(query, token);
      return result;
    } catch (error) {
      if (error.response) {
        const status = error.response.status;

        // Don't retry client errors (except 429)
        if (status >= 400 && status < 500 && status !== 429) {
          throw error;
        }

        // Retry server errors and rate limits
        if (status >= 500 || status === 429) {
          const delay = Math.min(1000 * Math.pow(2, i), 10000);
          console.log(`Retrying in ${delay}ms...`);
          await new Promise(resolve => setTimeout(resolve, delay));
          continue;
        }
      }

      // Unknown error
      if (i === maxRetries - 1) throw error;
    }
  }
}
```

#### Python
```python
import time
from requests.exceptions import RequestException

def safe_search(query: str, token: str, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            return search(query, token)
        except RequestException as e:
            if hasattr(e, 'response') and e.response is not None:
                status = e.response.status_code

                # Don't retry client errors (except 429)
                if 400 <= status < 500 and status != 429:
                    raise

                # Retry server errors and rate limits
                if status >= 500 or status == 429:
                    if attempt < max_retries - 1:
                        delay = min(1.0 * (2 ** attempt), 10.0)
                        print(f"Retrying in {delay}s...")
                        time.sleep(delay)
                        continue

            # Unknown error or last attempt
            if attempt == max_retries - 1:
                raise
```

---

## Rate Limiting

### Current Limits

```
Endpoint                Rate Limit
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
/webhook/search         100 requests/minute
/v2/search              100 requests/minute
/v2/search/plan         100 requests/minute
/v2/search/health       Unlimited
```

### Rate Limit Headers

Response includes:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

### Handling Rate Limits

```javascript
async function searchWithRateLimit(query, token) {
  try {
    return await search(query, token);
  } catch (error) {
    if (error.response?.status === 429) {
      const resetTime = error.response.headers['x-ratelimit-reset'];
      const waitMs = (resetTime * 1000) - Date.now();

      console.log(`Rate limited. Waiting ${waitMs}ms...`);
      await new Promise(resolve => setTimeout(resolve, waitMs));

      // Retry
      return await search(query, token);
    }
    throw error;
  }
}
```

---

## Security Best Practices

### 1. Never Expose JWT Tokens
```javascript
// ❌ BAD - Token in client-side code
const token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...';

// ✅ GOOD - Token from secure backend
const token = await fetch('/api/get-token').then(r => r.json());
```

### 2. Use Environment Variables
```javascript
// Node.js backend
const API_URL = process.env.PIPELINE_API_URL;
const JWT_SECRET = process.env.JWT_SECRET;

// Never commit tokens to git
```

### 3. Implement Token Refresh
```javascript
class AuthManager {
  constructor() {
    this.token = null;
    this.tokenExpiry = null;
  }

  async getToken() {
    if (this.token && Date.now() < this.tokenExpiry) {
      return this.token;
    }

    // Refresh token
    const response = await this.authenticate();
    this.token = response.access_token;
    this.tokenExpiry = Date.now() + (response.expires_in * 1000);

    return this.token;
  }

  async authenticate() {
    // Call Supabase auth
    // ...
  }
}
```

### 4. Validate Responses
```javascript
function validateSearchResponse(data) {
  if (!data || typeof data !== 'object') {
    throw new Error('Invalid response format');
  }

  if (!data.ok && !data.success) {
    throw new Error(data.error || 'Search failed');
  }

  if (!Array.isArray(data.results)) {
    throw new Error('Results must be an array');
  }

  return data;
}

// Usage
const result = await search(query, token);
const validated = validateSearchResponse(result);
```

---

## Complete Integration Example

### React Application with Search

```typescript
import React, { useState } from 'react';
import axios from 'axios';

interface SearchResult {
  ok: boolean;
  results: any[];
  entities: Entity[];
  total_count: number;
}

interface Entity {
  text: string;
  type: string;
  confidence: number;
}

const PIPELINE_API = 'https://pipeline-core.int.celeste7.ai';

function SearchComponent() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const search = async () => {
    if (!query.trim()) return;

    setLoading(true);
    setError(null);

    try {
      // Get token from your auth system
      const token = await getAuthToken();

      const response = await axios.post(
        `${PIPELINE_API}/webhook/search`,
        { query, limit: 20 },
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          timeout: 15000
        }
      );

      setResults(response.data);
    } catch (err: any) {
      console.error('Search error:', err);
      setError(err.response?.data?.error || 'Search failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search parts, equipment, work orders..."
          onKeyPress={(e) => e.key === 'Enter' && search()}
        />
        <button onClick={search} disabled={loading}>
          {loading ? 'Searching...' : 'Search'}
        </button>
      </div>

      {error && (
        <div style={{ color: 'red' }}>{error}</div>
      )}

      {results && (
        <div>
          <h3>Results ({results.total_count})</h3>

          {/* Extracted Entities */}
          {results.entities.length > 0 && (
            <div>
              <h4>Extracted Entities:</h4>
              {results.entities.map((entity, i) => (
                <span key={i} style={{
                  padding: '4px 8px',
                  margin: '4px',
                  background: '#e0e0e0',
                  borderRadius: '4px',
                  display: 'inline-block'
                }}>
                  {entity.value} ({entity.type})
                </span>
              ))}
            </div>
          )}

          {/* Search Results */}
          <div>
            {results.results.map((result, i) => (
              <div key={i} style={{
                border: '1px solid #ddd',
                padding: '12px',
                margin: '8px 0'
              }}>
                <strong>{result.title || result.id}</strong>
                <p>{result.description}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// Auth helper
async function getAuthToken(): Promise<string> {
  // Implement your authentication logic
  // Could call your backend, use Supabase client, etc.
  const response = await fetch('/api/auth/token');
  const data = await response.json();
  return data.token;
}

export default SearchComponent;
```

---

## Testing

### Manual Testing with cURL

```bash
# 1. Get JWT token
TOKEN=$(curl -X POST https://qvzmkaamzaqxpzbewjxe.supabase.co/auth/v1/token?grant_type=password \
  -H "apikey: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF2em1rYWFtemFxeHB6YmV3anhlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM5NzkwNDYsImV4cCI6MjA3OTU1NTA0Nn0.MMzzsRkvbug-u19GBUnD0qLDtMVWEbOf6KE8mAADaxw" \
  -H "Content-Type: application/json" \
  -d '{"email": "your@email.com", "password": "yourpassword"}' | jq -r '.access_token')

# 2. Test basic search
curl -X POST https://pipeline-core.int.celeste7.ai/webhook/search \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "oil filter caterpillar", "limit": 10}' | jq

# 3. Test orchestrated search
curl -X POST https://pipeline-core.int.celeste7.ai/v2/search \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "pending shopping list items",
    "surface_state": "search",
    "debug": true
  }' | jq

# 4. Get plan only (debug)
curl -X POST https://pipeline-core.int.celeste7.ai/v2/search/plan \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "oil filter",
    "surface_state": "search"
  }' | jq

# 5. Health check
curl https://pipeline-core.int.celeste7.ai/v2/search/health | jq
```

### Unit Test Example (Python)

```python
import pytest
import requests

PIPELINE_API = "https://pipeline-core.int.celeste7.ai"

@pytest.fixture
def auth_token():
    # Implement authentication
    return "your_jwt_token"

def test_basic_search(auth_token):
    """Test basic search functionality"""
    response = requests.post(
        f"{PIPELINE_API}/webhook/search",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"query": "oil filter", "limit": 10}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "results" in data
    assert "entities" in data

def test_entity_extraction(auth_token):
    """Test entity extraction quality"""
    response = requests.post(
        f"{PIPELINE_API}/webhook/search",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"query": "caterpillar c32 oil filter"}
    )

    data = response.json()
    entities = data["entities"]

    # Should extract brand
    assert any(e["type"] == "org" for e in entities)

    # Should extract model
    assert any(e["type"] == "model" for e in entities)

    # Should extract part
    assert any(e["type"] == "part" for e in entities)

def test_orchestrated_search_trust(auth_token):
    """Test trust payload in orchestrated search"""
    response = requests.post(
        f"{PIPELINE_API}/v2/search",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "query_text": "pending shopping list",
            "surface_state": "search"
        }
    )

    data = response.json()
    assert "trust" in data
    assert "path" in data["trust"]
    assert "explain" in data["trust"]
```

---

## Migration Guide

### From Old Endpoint to New

If you're currently using an older version:

#### Old Way (Deprecated)
```javascript
// Old endpoint (if applicable)
const result = await fetch('/api/old-search', {
  method: 'POST',
  body: JSON.stringify({ q: query })
});
```

#### New Way (Current)
```javascript
// New endpoint
const result = await fetch('https://pipeline-core.int.celeste7.ai/webhook/search', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ query, limit: 20 })
});
```

### Key Changes
1. **Authentication**: Now requires JWT Bearer token
2. **Request format**: `query` field instead of `q`
3. **Response format**: Includes `entities` array
4. **Base URL**: Moved to dedicated domain

---

## FAQ

### Q: Do I need to implement entity extraction myself?
**A**: No, entity extraction happens automatically. Just send your query and receive extracted entities in the response.

### Q: What's the difference between `/webhook/search` and `/v2/search`?
**A**:
- `/webhook/search`: Standard search, simpler response
- `/v2/search`: Advanced search with trust payload, context awareness, and explainability

Use `/webhook/search` for most cases. Use `/v2/search` when you need to understand WHY results were returned or when implementing context-aware search.

### Q: How do I know if my query will trigger AI extraction?
**A**: Check `timing_ms.extraction` in the response:
- < 500ms: Fast path (regex only)
- \> 2000ms: AI path (GPT-4o-mini used)

Or use `/v2/search/plan` to see the planned extraction strategy.

### Q: Can I customize entity extraction thresholds?
**A**: No, thresholds are server-side configuration. However, you can filter entities client-side by confidence score.

### Q: How do I handle pagination?
**A**: Currently, use the `limit` parameter (max 100). For more results, implement client-side pagination or contact the engineering team for server-side pagination support.

### Q: What's the maximum query length?
**A**: 500 characters recommended. Longer queries may timeout.

### Q: How do I report issues?
**A**: Contact the engineering team or submit issues to the project repository.

---

## Support

### Engineering Team
- **Issues**: Report to engineering team
- **Questions**: Contact team lead
- **Documentation**: See `/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/` for additional docs

### Additional Resources
- **Full Technical Docs**: `ASYNC_REFACTOR_SUMMARY.md`
- **Developer Guide**: `ENTITY_EXTRACTION_GUIDE.md`
- **Deployment Status**: `DEPLOYMENT_STATUS.md`

---

## Appendix: Quick Reference

### Endpoints Summary

```
GET  /v2/search/health          Health check (no auth)
POST /webhook/search            Primary search endpoint
POST /v2/search                 Orchestrated search with trust
POST /v2/search/plan            Plan only (debug)
```

### Common Query Patterns

```javascript
// Basic search
{query: "oil filter", limit: 20}

// Equipment search
{query: "caterpillar c32 main engine"}

// Fault diagnosis
{query: "error code P0420 high temperature"}

// Part with model
{query: "fuel filter for volvo penta d4"}

// Shopping list
{query: "pending shopping list items"}

// Work orders
{query: "completed work orders last month"}
```

### Response Status Quick Check

```javascript
// Check success
if (result.ok || result.success) {
  // Process results
}

// Check entities extracted
if (result.entities && result.entities.length > 0) {
  // Use entities
}

// Check result count
if (result.total_count > 0) {
  // Display results
}
```

---

**Document Version**: 1.0
**API Version**: 2.0 (Post-Async Refactor)
**Last Updated**: 2026-01-30
**Status**: Production Ready ✅
