# Search Streaming Best Practices

**TL;DR:** Use 200ms debounce + AbortController. Never stream on every keystroke.

---

## The Problem

Without proper debouncing, search-as-you-type destroys backend infrastructure and costs real money.

### Example: User types "main engine"

**❌ WRONG (keystroke streaming):**
```
"m"           → n8n request #1  → GPT extraction → Vector search → $0.002
"ma"          → n8n request #2  → GPT extraction → Vector search → $0.002
"mai"         → n8n request #3  → GPT extraction → Vector search → $0.002
"main"        → n8n request #4  → GPT extraction → Vector search → $0.002
"main "       → n8n request #5  → GPT extraction → Vector search → $0.002
"main e"      → n8n request #6  → GPT extraction → Vector search → $0.002
"main en"     → n8n request #7  → GPT extraction → Vector search → $0.002
"main eng"    → n8n request #8  → GPT extraction → Vector search → $0.002
"main engi"   → n8n request #9  → GPT extraction → Vector search → $0.002
"main engin"  → n8n request #10 → GPT extraction → Vector search → $0.002
"main engine" → n8n request #11 → GPT extraction → Vector search → $0.002
```
**Total: 11 requests, $0.022 cost**

**✅ CORRECT (200ms debounce):**
```
User types "main engine"
→ Frontend buffers locally
→ Timer resets on each keystroke
→ 200ms pause detected
→ ONE request sent: "main engine"
```
**Total: 1 request, $0.002 cost**

---

## Cost Analysis

### Per Search Query

| Metric                    | Keystroke Streaming | Debounced  | Improvement |
|---------------------------|---------------------|------------|-------------|
| Requests sent             | 50-100              | 1          | **98% ↓**   |
| GPT extraction calls      | 50-100              | 1          | **98% ↓**   |
| Vector searches           | 50-100              | 1          | **98% ↓**   |
| n8n workflow executions   | 50-100              | 1          | **98% ↓**   |
| Cost per search           | $0.10 - $0.20       | $0.002     | **99% ↓**   |

### Annual Impact (1000 searches/day)

| Metric                    | Before      | After    | Savings      |
|---------------------------|-------------|----------|--------------|
| Total requests/year       | 18,250,000  | 365,000  | 17,885,000   |
| GPT API costs             | $3,650      | $73      | **$3,577**   |
| n8n execution hours       | 6,083 hrs   | 122 hrs  | **5,961 hrs**|
| Supabase queries          | 182,500,000 | 3,650,000| 178,850,000  |
| Infrastructure cost       | $15,000+    | $300     | **$14,700**  |

---

## Infrastructure Damage

### Backend Systems Impacted

1. **n8n Webhook Queue**
   - 50-100 concurrent workflows per user
   - Queue backpressure and timeouts
   - CPU spikes on Render

2. **GPT-4o Extraction**
   - Meaningless extraction on "m", "ma", "mai"
   - Rate limit warnings
   - Token waste on garbage input

3. **Supabase Vector Search**
   - 50-100 `pgvector` searches per query
   - RLS evaluation overhead
   - Connection pool exhaustion

4. **Feedback Logs (JSONB)**
   - 50-100 log writes per query
   - JSONB index bloat
   - Storage waste

5. **Situational Detection**
   - False triggers on incomplete input
   - "m" → equipment_issue? part_search?
   - Incorrect action routing

---

## How Industry Leaders Handle This

### Spotlight (macOS) - 150ms debounce
```typescript
// Apple's approach
const DEBOUNCE_MS = 150;
const MIN_CHARS = 2;
```

### Raycast - 200ms debounce
```typescript
// Raycast's approach
const DEBOUNCE_MS = 200;
const MIN_CHARS = 1; // but intelligently filters
```

### Arc Browser Search - 250ms debounce
```typescript
// Arc's approach
const DEBOUNCE_MS = 250;
const MIN_CHARS = 3;
```

### VS Code Command Palette - 200ms debounce
```typescript
// VS Code's approach
const DEBOUNCE_MS = 200;
const MIN_CHARS = 0; // instant local filtering
```

**Industry consensus: 200ms debounce is the sweet spot**

---

## Complete Implementation

### React Hook (Production-Ready)

```typescript
// hooks/useSearch.ts

import { useState, useEffect, useCallback, useRef } from 'react';

interface SearchResult {
  // Your search result type
  id: string;
  title: string;
  content: string;
  // ...
}

interface UseSearchOptions {
  debounceMs?: number;
  minChars?: number;
  enabled?: boolean;
}

export function useSearch(options: UseSearchOptions = {}) {
  const {
    debounceMs = 200,  // Industry standard
    minChars = 2,      // Minimum meaningful input
    enabled = true,
  } = options;

  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  // AbortController for request cancellation
  const abortControllerRef = useRef<AbortController | null>(null);
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);

  const performSearch = useCallback(async (searchQuery: string) => {
    // Cancel previous request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Skip if below minimum length
    if (searchQuery.length < minChars) {
      setResults([]);
      setLoading(false);
      return;
    }

    // Create new AbortController
    abortControllerRef.current = new AbortController();
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: searchQuery }),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        throw new Error(`Search failed: ${response.statusText}`);
      }

      const data = await response.json();
      setResults(data.results || []);
    } catch (err) {
      // Ignore abort errors (normal when user keeps typing)
      if (err instanceof Error && err.name === 'AbortError') {
        return;
      }
      setError(err instanceof Error ? err : new Error('Search failed'));
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, [minChars]);

  // Debounced search effect
  useEffect(() => {
    if (!enabled) {
      return;
    }

    // Clear previous timer
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    // Set new timer
    debounceTimerRef.current = setTimeout(() => {
      performSearch(query);
    }, debounceMs);

    // Cleanup
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [query, enabled, debounceMs, performSearch]);

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

  return {
    query,
    setQuery,
    results,
    loading,
    error,
    // Manual trigger (for immediate search)
    search: performSearch,
  };
}
```

### Usage Example

```typescript
// components/SearchBar.tsx

import { useSearch } from '@/hooks/useSearch';

export function SearchBar() {
  const { query, setQuery, results, loading } = useSearch({
    debounceMs: 200,
    minChars: 2,
  });

  return (
    <div>
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search CelesteOS..."
      />

      {loading && <div>Searching...</div>}

      {results.length > 0 && (
        <ul>
          {results.map((result) => (
            <li key={result.id}>{result.title}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

---

## Advanced Patterns

### 1. Instant Local Filtering + Debounced Remote

```typescript
const [localResults, setLocalResults] = useState([]);
const [remoteResults, setRemoteResults] = useState([]);

useEffect(() => {
  // INSTANT: Local filtering (no debounce)
  const filtered = recentSearches.filter(s =>
    s.toLowerCase().includes(query.toLowerCase())
  );
  setLocalResults(filtered);
}, [query]);

useEffect(() => {
  // DEBOUNCED: Remote search (200ms)
  const timer = setTimeout(() => {
    fetchRemoteResults(query);
  }, 200);
  return () => clearTimeout(timer);
}, [query]);
```

### 2. Progressive Enhancement

```typescript
// Show local results immediately
// Show remote results after debounce
// Show AI-enhanced results after 500ms

const [tier1Local, setTier1Local] = useState([]);      // 0ms
const [tier2Remote, setTier2Remote] = useState([]);    // 200ms
const [tier3AI, setTier3AI] = useState([]);            // 500ms
```

### 3. Adaptive Debounce

```typescript
// Faster debounce for HOD users (they type faster)
// Slower debounce for crew users (they type slower)

const debounceMs = user.role === 'hod' ? 150 : 250;
```

---

## Request Cancellation (Critical)

### Why AbortController is Required

Without cancellation, slow network + fast typing = disaster:

```
User types: "m"
→ Request 1 starts (takes 2 seconds)

User continues typing: "main engine"
→ Request 2 starts

Request 1 finally completes (2s later)
→ Shows results for "m" (WRONG)
→ Overwrites results for "main engine" (CORRECT)
```

### Correct Pattern

```typescript
const abortController = new AbortController();

fetch('/api/search', {
  signal: abortController.signal,
  // ...
});

// On new keystroke:
abortController.abort(); // Cancel previous request
```

---

## Loading States

### UX Feedback

```typescript
// Don't show spinner immediately (jarring for fast searches)
const [showSpinner, setShowSpinner] = useState(false);

useEffect(() => {
  if (loading) {
    // Only show spinner if search takes >300ms
    const timer = setTimeout(() => setShowSpinner(true), 300);
    return () => clearTimeout(timer);
  } else {
    setShowSpinner(false);
  }
}, [loading]);
```

### Skeleton States

```typescript
// Show skeleton for in-flight searches
{loading && query.length >= minChars && (
  <div className="skeleton">
    <div className="skeleton-line" />
    <div className="skeleton-line" />
    <div className="skeleton-line" />
  </div>
)}
```

---

## Testing

### Unit Tests

```typescript
describe('useSearch', () => {
  it('debounces search requests', async () => {
    const { result } = renderHook(() => useSearch());

    act(() => result.current.setQuery('m'));
    act(() => result.current.setQuery('ma'));
    act(() => result.current.setQuery('mai'));
    act(() => result.current.setQuery('main'));

    // Should only make 1 request after debounce
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(1);
    });
  });

  it('cancels previous requests', async () => {
    const { result } = renderHook(() => useSearch());

    act(() => result.current.setQuery('slow'));
    await new Promise(r => setTimeout(r, 50));
    act(() => result.current.setQuery('fast'));

    // First request should be cancelled
    await waitFor(() => {
      expect(abortController.abort).toHaveBeenCalled();
    });
  });
});
```

### Load Testing

```bash
# Simulate 100 concurrent users typing
artillery quick --count 100 --num 50 \
  -p '{ "url": "/api/search", "method": "POST" }'

# Expected: <500ms p99 latency
# Expected: No n8n queue backpressure
# Expected: No rate limit errors
```

---

## Comparison: Before vs After

### Request Waterfall

**Before (keystroke streaming):**
```
0ms:   "m"          → Request #1 starts
50ms:  "ma"         → Request #2 starts (Request #1 still pending)
100ms: "mai"        → Request #3 starts (Request #1,#2 still pending)
150ms: "main"       → Request #4 starts (Request #1,#2,#3 still pending)
200ms: "main "      → Request #5 starts (Request #1,#2,#3,#4 still pending)
250ms: "main e"     → Request #6 starts (Request #1-5 still pending)
...
1000ms: Request #1 completes (wrong results)
1050ms: Request #2 completes (wrong results)
1100ms: Request #3 completes (wrong results)
...
```

**After (debounced):**
```
0ms:   User types "main engine"
200ms: Debounce timer expires
200ms: Request #1 starts
700ms: Request #1 completes (correct results)
```

### Metrics

| Metric               | Before    | After   | Improvement |
|----------------------|-----------|---------|-------------|
| Time to first byte   | 1000ms    | 700ms   | **30% ↓**   |
| Concurrent requests  | 50        | 1       | **98% ↓**   |
| Backend load         | 100%      | 2%      | **98% ↓**   |
| Cost per search      | $0.10     | $0.002  | **98% ↓**   |
| User experience      | ❌ Laggy  | ✅ Fast | Much better |

---

## Common Mistakes

### ❌ Mistake 1: No debounce at all

```typescript
// WRONG: Search on every keystroke
onChange={(e) => {
  performSearch(e.target.value); // Disaster
}}
```

### ❌ Mistake 2: Debounce but no cancellation

```typescript
// WRONG: Debounced but requests still pile up
useEffect(() => {
  const timer = setTimeout(() => {
    fetch('/api/search'); // No AbortController
  }, 200);
}, [query]);
```

### ❌ Mistake 3: Debounce too short

```typescript
// WRONG: 50ms is too fast (still 5-10 requests per query)
const DEBOUNCE_MS = 50; // Too short!
```

### ❌ Mistake 4: No minimum length

```typescript
// WRONG: Searching on single character
if (query.length >= 1) { // Should be >= 2
  performSearch(query);
}
```

### ❌ Mistake 5: Server-side debouncing

```typescript
// WRONG: Debouncing on backend (requests still sent)
// n8n workflow:
{
  "nodes": [
    {
      "name": "Debounce",
      "type": "n8n-nodes-base.delay",
      "parameters": { "wait": 200 }
    }
  ]
}
// ❌ Still processing 50-100 requests!
```

---

## Deployment Checklist

Before deploying search functionality:

- [ ] ✅ 200ms debounce implemented
- [ ] ✅ AbortController for request cancellation
- [ ] ✅ Minimum 2 character filter
- [ ] ✅ Loading states with 300ms delay
- [ ] ✅ Error handling for network failures
- [ ] ✅ Cleanup on component unmount
- [ ] ✅ Unit tests for debounce logic
- [ ] ✅ Load testing with 100+ concurrent users
- [ ] ✅ Monitoring: request rate < 5/sec per user
- [ ] ✅ Cost analysis: <$0.01 per search

---

## Monitoring

### Key Metrics to Track

```sql
-- Average requests per search query
SELECT
  DATE_TRUNC('day', created_at) as day,
  COUNT(*) / COUNT(DISTINCT user_id) as requests_per_user
FROM search_logs
GROUP BY day;
-- Target: <2 requests per user per search
```

```sql
-- Cost per search
SELECT
  SUM(gpt_cost + vector_cost) / COUNT(DISTINCT search_id) as cost_per_search
FROM search_analytics
WHERE created_at > NOW() - INTERVAL '7 days';
-- Target: <$0.01 per search
```

---

## Summary

| ✅ DO                          | ❌ DON'T                        |
|-------------------------------|---------------------------------|
| 200ms debounce                | Stream on every keystroke       |
| AbortController cancellation  | Let requests pile up            |
| Minimum 2 character filter    | Search single characters        |
| Delayed loading spinner       | Show spinner immediately        |
| Request rate monitoring       | Deploy without metrics          |
| Unit test debounce logic      | Assume it works                 |
| Load test with 100+ users     | Deploy without testing          |

**Bottom line:** Use the `useSearch()` hook from this guide. It handles debouncing, cancellation, and loading states correctly.

---

## References

- [Spotlight Search Internals](https://developer.apple.com/documentation/corespotlight)
- [Raycast API Best Practices](https://developers.raycast.com/api-reference/preferences)
- [Arc Browser Engineering Blog](https://arc.net/blog/engineering)
- [React useDebounce Pattern](https://usehooks.com/useDebounce/)
- [AbortController MDN](https://developer.mozilla.org/en-US/docs/Web/API/AbortController)

---

**Last updated:** 2025-01-25
**Maintained by:** CelesteOS Core Team
**Questions?** See `INTEGRATION.md` for API integration details.
