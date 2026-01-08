# CelesteOS Backend Integration Guide

Complete guide for integrating with the CelesteOS n8n backend. Covers authentication, search API, security, and streaming best practices.

---

## Table of Contents

1. [Authentication](#authentication)
2. [Security & Compliance](#security--compliance)
3. [Search API Integration](#search-api-integration)
4. [Action Router Integration](#action-router-integration)
5. [Error Handling](#error-handling)
6. [Rate Limiting](#rate-limiting)

---

## Authentication

### JWT Token Flow

CelesteOS uses Supabase JWT tokens for authentication:

```typescript
// Get JWT from Supabase session
const { data: { session } } = await supabase.auth.getSession();
const jwt = session?.access_token;

// Include in all API requests
fetch('https://api.celeste7.ai/webhook/search', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${jwt}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({ query: 'main engine' }),
});
```

### Token Validation

Backend validates JWT on every request:

```typescript
// n8n workflow: JWT Validation Node
{
  "nodes": [
    {
      "name": "Validate JWT",
      "type": "n8n-nodes-base.function",
      "parameters": {
        "functionCode": "// Extract user_id from JWT\nconst jwt = $node['Webhook'].json.headers.authorization.split(' ')[1];\nconst decoded = jwt_decode(jwt);\nreturn { user_id: decoded.sub, yacht_id: decoded.yacht_id };"
      }
    }
  ]
}
```

**Security:** User identity comes from JWT **ONLY**. Never trust request body for `user_id`.

---

## Security & Compliance

### GDPR / SOC2 / ISO27001 Requirements

#### 1. Strict Schema Validation

All request schemas use `.strict()` mode to prevent data leakage:

```typescript
// ✅ CORRECT: Strict mode prevents extra fields
const searchSchema = z.object({
  query: z.string().min(1).max(500),
  filters: z.object({
    document_type: z.enum(['manual', 'fault', 'note']).optional(),
    date_range: z.string().optional(),
  }).optional(),
}).strict(); // ← CRITICAL: Reject unknown fields

// ❌ WRONG: Allows user to inject extra data
const searchSchema = z.object({
  query: z.string(),
  user_id: z.string(), // ← SECURITY VIOLATION: User can spoof identity!
});
```

#### 2. Identity from JWT Only

```typescript
// ✅ CORRECT: Extract identity from verified JWT
const jwt = req.headers.authorization.split(' ')[1];
const { sub: user_id, yacht_id } = verify(jwt, SECRET);

// ❌ WRONG: Trust request body
const { user_id } = req.body; // ← GDPR VIOLATION: User can access other users' data
```

#### 3. Request Body Sanitization

```typescript
// ✅ CORRECT: Validate and sanitize all inputs
const sanitized = searchSchema.parse(req.body);

// ❌ WRONG: Use raw request body
const results = await search(req.body.query); // ← SQL injection risk
```

#### 4. RLS Enforcement

All database queries use Row Level Security:

```sql
-- Supabase RLS policy
CREATE POLICY "Users can only access their yacht's data"
ON documents
FOR SELECT
USING (yacht_id = auth.jwt() ->> 'yacht_id');
```

#### 5. Audit Logging

All requests logged with GDPR-compliant retention:

```typescript
// Log search request
await supabase.from('search_logs').insert({
  user_id,
  yacht_id,
  query: sanitized.query,
  timestamp: new Date().toISOString(),
  // NO PII: Don't log full responses or sensitive data
});
```

### Compliance Checklist

- [ ] ✅ All schemas use `.strict()` mode
- [ ] ✅ User identity from JWT only (never request body)
- [ ] ✅ RLS policies enabled on all tables
- [ ] ✅ Audit logs with 90-day retention
- [ ] ✅ No PII in logs (query text only, not results)
- [ ] ✅ Rate limiting per user (prevent abuse)
- [ ] ✅ HTTPS only (TLS 1.3+)
- [ ] ✅ JWT expiry enforced (24h max)

---

## Search API Integration

### Endpoint

```
POST https://api.celeste7.ai/webhook/search
```

### Request Schema

```typescript
interface SearchRequest {
  query: string;                    // Required: 1-500 chars
  filters?: {
    document_type?: 'manual' | 'fault' | 'note';
    equipment_id?: string;
    date_range?: string;            // ISO 8601 format
  };
  yacht_id?: string;                // Optional: Defaults to JWT yacht_id
}
```

### Response Schema

```typescript
interface SearchResponse {
  results: Array<{
    id: string;
    title: string;
    content: string;
    document_type: 'manual' | 'fault' | 'note' | 'work_order';
    relevance_score: number;        // 0.0 - 1.0
    equipment?: {
      id: string;
      name: string;
    };
    created_at: string;
    updated_at: string;
  }>;
  intent?: {
    detected_action: string;        // e.g., 'view_equipment', 'create_work_order'
    confidence: number;             // 0.0 - 1.0
    parameters?: Record<string, any>;
  };
  meta: {
    query: string;
    took_ms: number;
    total_results: number;
  };
}
```

### Example Request

```typescript
const response = await fetch('https://api.celeste7.ai/webhook/search', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${jwt}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    query: 'main engine fault codes',
    filters: {
      document_type: 'manual',
    },
  }),
});

const data: SearchResponse = await response.json();
```

---

## CRITICAL: Search Streaming Implementation

⚠️ **Most important section in this document. Read carefully.**

### The Problem

Without proper debouncing, search-as-you-type destroys backend infrastructure:

```
User types "main engine"
→ 11 requests sent (one per keystroke)
→ 11 GPT extractions ($0.022)
→ 11 vector searches
→ 11 n8n workflow executions
→ Queue backpressure, CPU spikes, rate limits
```

**Annual cost: $600+ in wasted infrastructure**

### The Solution

**200ms debounce + AbortController**

### Complete React Hook

```typescript
// hooks/useSearch.ts

import { useState, useEffect, useCallback, useRef } from 'react';

interface SearchResult {
  id: string;
  title: string;
  content: string;
  relevance_score: number;
}

export function useSearch() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);

  const abortControllerRef = useRef<AbortController | null>(null);
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);

  const performSearch = useCallback(async (searchQuery: string) => {
    // Cancel previous request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Skip if too short
    if (searchQuery.length < 2) {
      setResults([]);
      setLoading(false);
      return;
    }

    // Create new AbortController
    abortControllerRef.current = new AbortController();
    setLoading(true);

    try {
      const { data: { session } } = await supabase.auth.getSession();

      const response = await fetch('https://api.celeste7.ai/webhook/search', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session?.access_token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: searchQuery }),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) throw new Error('Search failed');

      const data = await response.json();
      setResults(data.results || []);
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        return; // Normal cancellation, ignore
      }
      console.error('[Search] Error:', err);
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // Debounced search effect
  useEffect(() => {
    // Clear previous timer
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    // Set new timer (200ms debounce)
    debounceTimerRef.current = setTimeout(() => {
      performSearch(query);
    }, 200);

    // Cleanup
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [query, performSearch]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  return { query, setQuery, results, loading };
}
```

### Usage

```typescript
// components/SearchBar.tsx

import { useSearch } from '@/hooks/useSearch';

export function SearchBar() {
  const { query, setQuery, results, loading } = useSearch();

  return (
    <div>
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search CelesteOS..."
      />

      {loading && <Spinner />}

      {results.map((result) => (
        <SearchResult key={result.id} {...result} />
      ))}
    </div>
  );
}
```

### Request Comparison

| Pattern                  | Requests/Query | Cost     | Backend Load |
|--------------------------|----------------|----------|--------------|
| ❌ Keystroke streaming   | 50-100         | $0.10    | 100%         |
| ✅ Debounced (200ms)     | 1              | $0.002   | 2%           |

### Why This Works

1. **Debounce (200ms):** Wait for user to stop typing
2. **AbortController:** Cancel previous requests if user keeps typing
3. **Minimum length (2 chars):** Don't search on single character
4. **Cleanup:** Prevent memory leaks on unmount

**See `SEARCH_STREAMING.md` for comprehensive guide.**

---

## Action Router Integration

### Endpoint

```
POST https://api.celeste7.ai/webhook/workflows/action
```

### Request Schema

```typescript
interface ActionRequest {
  action_name: string;              // e.g., 'create_work_order'
  context: {
    user_id?: string;               // Optional: Extracted from JWT
    yacht_id?: string;              // Optional: Extracted from JWT
  };
  parameters: Record<string, any>;  // Action-specific parameters
}
```

### Example: Create Work Order

```typescript
const response = await fetch('https://api.celeste7.ai/webhook/workflows/action', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${jwt}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    action_name: 'create_work_order',
    context: {}, // user_id/yacht_id from JWT
    parameters: {
      title: 'Replace HVAC filters',
      equipment_id: 'hvac-001',
      priority: 'high',
      description: 'Filters are clogged, replace immediately',
    },
  }),
});

const data = await response.json();
// { work_order_id: 'wo-123', status: 'created' }
```

### Available Actions

| Action Name             | Description                          | Parameters                          |
|-------------------------|--------------------------------------|-------------------------------------|
| `create_work_order`     | Create maintenance work order        | title, equipment_id, priority, desc |
| `view_equipment`        | Get equipment details                | equipment_id                        |
| `log_fault`             | Log equipment fault                  | equipment_id, fault_code, severity  |
| `add_to_handover`       | Add item to handover notes           | content, category                   |
| `view_smart_summary`    | Get AI-generated daily summary       | none                                |
| `view_pending_approvals`| Get pending WO/PR approvals          | none                                |

---

## Error Handling

### Standard Error Response

```typescript
interface ErrorResponse {
  error: {
    code: string;
    message: string;
    details?: Record<string, any>;
  };
  meta: {
    request_id: string;
    timestamp: string;
  };
}
```

### Common Error Codes

| Code                 | HTTP Status | Meaning                              |
|----------------------|-------------|--------------------------------------|
| `invalid_jwt`        | 401         | Missing or invalid JWT token         |
| `forbidden`          | 403         | User lacks permission                |
| `validation_error`   | 400         | Invalid request schema               |
| `rate_limit`         | 429         | Too many requests                    |
| `internal_error`     | 500         | Backend error (n8n/Supabase)         |

### Example Error Handling

```typescript
try {
  const response = await fetch(url, options);

  if (!response.ok) {
    const error: ErrorResponse = await response.json();

    switch (error.error.code) {
      case 'invalid_jwt':
        // Refresh session
        await supabase.auth.refreshSession();
        return retry();

      case 'rate_limit':
        // Show user-friendly message
        showToast('Too many requests, please wait');
        return;

      case 'validation_error':
        // Show form errors
        showValidationErrors(error.error.details);
        return;

      default:
        // Generic error
        showToast('Something went wrong');
    }
  }
} catch (err) {
  // Network error
  console.error('Network error:', err);
  showToast('Connection error, check your internet');
}
```

---

## Rate Limiting

### Per-User Limits

| Endpoint      | Limit            | Window  |
|---------------|------------------|---------|
| `/search`     | 60 requests/min  | 60s     |
| `/action`     | 120 requests/min | 60s     |
| All endpoints | 300 requests/min | 60s     |

### Rate Limit Headers

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 59
X-RateLimit-Reset: 1640000000
```

### Handling Rate Limits

```typescript
if (response.status === 429) {
  const resetTime = parseInt(response.headers.get('X-RateLimit-Reset') || '0');
  const waitMs = (resetTime * 1000) - Date.now();

  // Wait and retry
  await new Promise(resolve => setTimeout(resolve, waitMs));
  return retry();
}
```

---

## Best Practices Summary

| ✅ DO                          | ❌ DON'T                           |
|-------------------------------|------------------------------------|
| Use 200ms debounce            | Stream on every keystroke          |
| Extract identity from JWT     | Trust request body for user_id     |
| Use `.strict()` schemas       | Allow unknown fields in requests   |
| Implement AbortController     | Let requests pile up               |
| Handle rate limits gracefully | Ignore 429 responses               |
| Log requests (audit trail)    | Log PII or sensitive data          |
| Use RLS for database access   | Query without RLS policies         |

---

## Quick Start Checklist

- [ ] ✅ JWT authentication implemented
- [ ] ✅ Search debounced (200ms)
- [ ] ✅ AbortController for request cancellation
- [ ] ✅ Strict schema validation (`.strict()`)
- [ ] ✅ User identity from JWT only
- [ ] ✅ Error handling for all responses
- [ ] ✅ Rate limit handling (429 responses)
- [ ] ✅ HTTPS only (no HTTP)
- [ ] ✅ Monitoring/logging setup

---

## Additional Resources

- **Detailed streaming guide:** See `SEARCH_STREAMING.md`
- **Action router schemas:** See `src/action_router/schemas/README.md`
- **n8n workflows:** See `n8n-workflows/README.md`
- **Database schema:** See `docs/database-schema.md`

---

**Last updated:** 2025-01-25
**Maintained by:** CelesteOS Core Team
**Questions?** Open an issue or contact the backend team.
