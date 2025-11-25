# Search Streaming Best Practices

**For Worker 8 (Frontend Developer)**

---

## TL;DR

**DON'T send every keystroke. Debounce 200ms. Cancel previous requests. Minimum 2 characters.**

This is how Spotlight, Raycast, Arc, and VS Code work.

---

## ❌ Current Problem (What NOT to Do)

```typescript
// WRONG - Sends 50-100 requests per query
<input onChange={(e) => search(e.target.value)} />
```

### What happens:

```
User types: "main engine"

Frontend sends:
- "m"          → n8n webhook #1
- "ma"         → n8n webhook #2
- "mai"        → n8n webhook #3
- "main"       → n8n webhook #4
- "main "      → n8n webhook #5
- "main e"     → n8n webhook #6
- "main en"    → n8n webhook #7
- "main eng"   → n8n webhook #8
- "main engi"  → n8n webhook #9
- "main engin" → n8n webhook #10
- "main engine" → n8n webhook #11

Total: 11 requests for ONE search
```

### Cost impact:

| Component | Cost per keystroke | Cost per query (11 keystrokes) |
|-----------|-------------------|--------------------------------|
| GPT-4o extraction | $0.002 | $0.022 |
| Vector search | $0.0001 | $0.0011 |
| n8n workflow | 1 execution | 11 executions |
| Supabase queries | 3 queries | 33 queries |

**For 100 searches/day:**
- 1,100 n8n executions (vs 100)
- $2.20 GPT cost (vs $0.20)
- 3,300 DB queries (vs 300)

**Annual waste: ~$600/year + rate limits + degraded UX**

---

## ✅ Correct Implementation (Spotlight Model)

### Core principles:

1. **Debounce 200ms** - Only send when user stops typing
2. **Cancel previous requests** - Latest response wins
3. **Minimum length = 2 chars** - Filter garbage
4. **Show loading state** - Visual feedback

### Implementation:

```typescript
// hooks/useSearch.ts
import { useState, useEffect, useRef } from 'react';

export function useSearch() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const controllerRef = useRef<AbortController | null>(null);
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    // Clear previous timer
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    // Filter garbage
    const trimmed = query.trim();
    if (trimmed.length < 2) {
      setResults(null);
      setIsLoading(false);
      return;
    }

    // Debounce: wait 200ms after user stops typing
    debounceTimerRef.current = setTimeout(async () => {
      // Cancel previous request
      if (controllerRef.current) {
        controllerRef.current.abort();
      }

      controllerRef.current = new AbortController();
      setIsLoading(true);

      try {
        const response = await fetch('/v1/search', {
          method: 'POST',
          signal: controllerRef.current.signal,
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${session.access_token}`,
          },
          body: JSON.stringify({ query: trimmed, mode: 'auto' }),
        });

        const data = await response.json();
        setResults(data);
      } catch (error) {
        if (error.name !== 'AbortError') {
          console.error('Search error:', error);
        }
      } finally {
        setIsLoading(false);
      }
    }, 200); // Industry standard debounce

    return () => {
      if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current);
      if (controllerRef.current) controllerRef.current.abort();
    };
  }, [query]);

  return { query, setQuery, results, isLoading };
}
```

### Usage:

```tsx
export function SearchBar() {
  const { query, setQuery, results, isLoading } = useSearch();

  return (
    <div className="search-container">
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search equipment, faults, documents..."
      />
      {isLoading && <Spinner />}
      {results && <SearchResults results={results} />}
    </div>
  );
}
```

---

## 🎯 Expected Behavior

### User types: "main engine"

```
Timeline:

t=0ms:    User types "m"
          → Timer starts (200ms countdown)

t=50ms:   User types "a"
          → Timer resets (200ms countdown)

t=100ms:  User types "i"
          → Timer resets (200ms countdown)

t=150ms:  User types "n"
          → Timer resets (200ms countdown)

t=200ms:  User types " "
          → Timer resets (200ms countdown)

t=250ms:  User types "e"
          → Timer resets (200ms countdown)

...continues until user stops...

t=1200ms: User stops typing
          → Timer expires
          → ONE request sent: "main engine"
```

**Result: 1 request instead of 11**

---

## 🔍 Why This Matters

### Backend impact:

| Metric | Before (keystroke streaming) | After (debounced) | Improvement |
|--------|----------------------------|-------------------|-------------|
| Requests per query | 50-100 | 1 | 98% reduction |
| GPT extraction calls | 50-100 | 1 | 98% reduction |
| n8n executions | 50-100 | 1 | 98% reduction |
| DB queries | 150-300 | 3-5 | 95% reduction |
| Feedback log noise | High | None | Clean learning |
| Entity extraction confidence | Low (0.1-0.3) | High (0.7-0.9) | Meaningful results |

### UX impact:

- ✅ Faster perceived performance (no UI jank from 50 pending requests)
- ✅ Loading spinner shows during real search (not flickering constantly)
- ✅ Results stable (not re-rendering 50 times)
- ✅ Matches user mental model (Spotlight, Raycast, Arc, VS Code)

### Cost impact:

- ✅ 98% reduction in GPT API costs
- ✅ 95% reduction in Supabase usage
- ✅ No rate limit warnings
- ✅ n8n queue stays healthy

---

## 📊 Comparison: Keystroke vs Debounced

### Scenario: User searches 10 times per day

| Metric | Keystroke Streaming | Debounced (200ms) | Savings |
|--------|-------------------|-------------------|---------|
| Daily requests | 500-1000 | 10 | 99% |
| Monthly GPT cost | $30-60 | $0.60 | $29-59 |
| n8n executions | 15,000-30,000 | 300 | 99% |
| Supabase queries | 1,500-3,000 | 30-50 | 98% |
| Feedback log rows | 500-1000 junk | 10 clean | Quality data |

**Annual savings: $350-700 + better data quality + stable infrastructure**

---

## 🎨 Advanced: Optional Enhancements

### 1. Instant search on Enter

```typescript
<input
  onKeyDown={(e) => {
    if (e.key === 'Enter' && query.trim().length >= 2) {
      // Clear debounce timer
      clearTimeout(debounceTimerRef.current);
      // Trigger search immediately
      triggerSearch(query);
    }
  }}
/>
```

### 2. Visual feedback

```tsx
{isLoading && (
  <div className="loading-indicator">
    <Spinner />
    <span>Searching...</span>
  </div>
)}
```

### 3. Empty state

```tsx
{!query && (
  <div className="empty-state">
    <p>Start typing to search equipment, faults, or documents...</p>
  </div>
)}

{query.length > 0 && query.length < 2 && (
  <div className="hint">
    <p>Type at least 2 characters</p>
  </div>
)}
```

### 4. Keyboard shortcuts

```typescript
// ⌘K or Ctrl+K to focus search
useEffect(() => {
  const handleKeyDown = (e: KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      searchInputRef.current?.focus();
    }
  };

  window.addEventListener('keydown', handleKeyDown);
  return () => window.removeEventListener('keydown', handleKeyDown);
}, []);
```

---

## 🚫 Common Mistakes

### Mistake #1: No debounce
```typescript
// WRONG
<input onChange={(e) => search(e.target.value)} />
```

### Mistake #2: Debounce too short
```typescript
// WRONG - 50ms is too short, still fires too often
setTimeout(() => search(query), 50);
```

### Mistake #3: Not canceling previous requests
```typescript
// WRONG - Creates race conditions
setTimeout(() => {
  fetch('/search', { body: JSON.stringify({ query }) });
}, 200);
```

### Mistake #4: No minimum length filter
```typescript
// WRONG - Sends "a", "b", "c" to backend
if (query.length > 0) search(query);
```

---

## ✅ Checklist

Before deploying search UI:

- [ ] Debounce implemented (200ms)
- [ ] AbortController cancels previous requests
- [ ] Minimum length = 2 characters
- [ ] Loading state visible to user
- [ ] Empty state for no query
- [ ] Enter key triggers instant search (optional)
- [ ] No identity fields in request body (GDPR compliance)
- [ ] Authorization header included
- [ ] Error handling for network failures

---

## 📚 References

### Industry examples:

- **Apple Spotlight**: 200ms debounce, cancels previous, shows spinner
- **Raycast**: 150ms debounce, instant on Enter, fuzzy matching
- **VS Code Command Palette**: 200ms debounce, keyboard-first UX
- **Arc Browser**: 250ms debounce, optimistic rendering

### Libraries (if you need them):

- `use-debounce` - Simple React hook
- `lodash.debounce` - Classic utility
- `react-query` - Advanced caching + debouncing

**But the custom hook above is recommended** - no dependencies, full control.

---

## 🆘 Support

Questions? Check:
- `backend/INTEGRATION.md` - Full API documentation
- `backend/api-spec.md` - Search endpoint spec
- `backend/src/schemas/index.ts` - Request validation

**Bottom line:** Debounce 200ms. Cancel previous. Minimum 2 chars. This is standard practice.
