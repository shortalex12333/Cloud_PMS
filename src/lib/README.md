# CelesteOS API Client

**Centralized TypeScript client for all CelesteOS backend services**

---

## Overview

The CelesteOS API client provides a type-safe, convenient interface to interact with:

- **Search Engine** (Task 6) - Entity extraction, intent detection, RAG, GraphRAG, card generation
- **Predictive Engine** (Task 7) - Risk scores, anomalies, insights, predictions
- **Action Router** - Work orders, handovers, notes

### Features

✅ **Type-safe** - Full TypeScript support with interfaces
✅ **Authentication** - Automatic JWT and yacht signature attachment
✅ **Streaming** - Real-time search results via async generators
✅ **Error handling** - Consistent error types and handling
✅ **Singleton pattern** - Global instance or create custom clients
✅ **Framework agnostic** - Works with React, Vue, vanilla JS, etc.

---

## Installation

The API client is already included in this repository at `/src/lib/api.ts`.

No additional installation needed beyond your existing dependencies:

```bash
# TypeScript support (if not already installed)
npm install typescript @types/node
```

---

## Quick Start

### 1. Initialize the Client

In your app initialization (e.g., `_app.tsx`, `main.ts`):

```typescript
import api from '@/lib/api';

// Initialize once at app startup
api.init({
  baseUrl: process.env.NEXT_PUBLIC_API_URL || 'https://api.celesteos.com',
  predictiveEngineUrl: 'https://celeste-predictive-api.onrender.com',

  // Provide auth token (from your auth system)
  getAuthToken: () => localStorage.getItem('auth_token'),

  // Provide yacht signature
  getYachtSignature: () => localStorage.getItem('yacht_signature'),
});
```

### 2. Use the Client

```typescript
import api from '@/lib/api';

async function example() {
  const client = api.get();

  // Search with streaming
  for await (const card of client.searchStream({ query: 'fault E047' })) {
    console.log(card);
  }

  // Get predictive state
  const state = await client.getPredictiveState(yachtId);
  console.log(`High risk equipment: ${state.high_risk_count}`);
}
```

---

## Core Concepts

### Authentication

All requests automatically include:
- `Authorization: Bearer <JWT>` - User authentication
- `X-Yacht-Signature: <signature>` - Yacht identification

These are provided via the `getAuthToken()` and `getYachtSignature()` functions during initialization.

### Error Handling

The client throws `ApiError` with status codes:

```typescript
import { ApiError } from '@/lib/api';

try {
  const result = await client.search({ query: 'test' });
} catch (error) {
  if (error instanceof ApiError) {
    console.error(`API Error ${error.status}: ${error.statusText}`);
    console.error(error.data); // Additional error details
  }
}
```

### Streaming

Search results can be streamed for real-time display:

```typescript
// Streaming (results arrive one by one)
for await (const card of client.searchStream({ query })) {
  updateUI(card); // Update UI as each card arrives
}

// Standard (all results at once)
const response = await client.search({ query });
console.log(response.results); // All results together
```

---

## API Reference

### Search Engine Methods

#### `searchStream(request: SearchRequest)`

Stream search results in real-time.

```typescript
for await (const card of client.searchStream({
  query: 'fault code E047 on main engine',
  mode: 'auto', // 'auto' | 'standard' | 'deep'
  filters: {
    equipment_id: 'uuid',
    document_type: 'manual',
  },
})) {
  console.log(card);
}
```

**Returns:** `AsyncGenerator<SearchResultCard>`

#### `search(request: SearchRequest)`

Get all search results at once.

```typescript
const response = await client.search({
  query: 'HVAC manual',
  mode: 'standard',
});

console.log(response.results); // All cards
console.log(response.actions); // Micro-actions
console.log(response.intent); // Detected intent
```

**Returns:** `Promise<SearchResponse>`

---

### Predictive Engine Methods

#### `getPredictiveState(yachtId: string, equipmentId?: string)`

Get risk scores and states for equipment.

```typescript
const state = await client.getPredictiveState(yachtId);

console.log(state.high_risk_count); // Equipment with risk >= 0.75
console.log(state.equipment_risks); // Array of risk scores
```

**Returns:**
```typescript
{
  yacht_id: string;
  total_equipment: number;
  high_risk_count: number;
  emerging_risk_count: number;
  monitor_count: number;
  normal_count: number;
  equipment_risks: PredictiveState[];
}
```

#### `getPredictiveInsights(yachtId: string, minSeverity?: string, limit?: number)`

Get predictive insights and recommendations.

```typescript
const insights = await client.getPredictiveInsights(yachtId, 'high', 20);

insights.insights.forEach((insight) => {
  console.log(insight.summary);
  console.log(insight.recommended_action);
});
```

**Returns:**
```typescript
{
  yacht_id: string;
  total_insights: number;
  critical_count: number;
  insights: PredictiveInsight[];
}
```

#### `getPredictiveCard(equipmentId: string)`

Get predictive card for specific equipment (for search integration).

```typescript
const card = await client.getPredictiveCard(equipmentId);

console.log(card.risk_score); // 0.0 - 1.0
console.log(card.trend); // '↑' | '↓' | '→'
console.log(card.severity); // 'low' | 'medium' | 'high' | 'critical'
```

**Returns:** `Promise<SearchResultCard>`

#### `getAnomalies(yachtId: string)`

Get detected anomalies.

```typescript
const anomalies = await client.getAnomalies(yachtId);

console.log(anomalies.critical_anomalies);
console.log(anomalies.anomalies);
```

#### `runPredictive(yachtId: string, forceRecalculate?: boolean)`

Trigger predictive computation (on-demand).

```typescript
const result = await client.runPredictive(yachtId, false);
console.log(result.summary);
```

---

### Action Router Methods

#### `createWorkOrder(request: CreateWorkOrderRequest)`

Create a work order.

```typescript
const wo = await client.createWorkOrder({
  equipment_id: 'uuid',
  title: 'Fix pump leak',
  description: 'Hydraulic leak observed',
  priority: 'important',
  type: 'corrective',
});

console.log(wo.work_order_id);
```

#### `addToHandover(request: AddHandoverItemRequest)`

Add item to handover draft.

```typescript
const item = await client.addToHandover({
  handover_id: 'uuid',
  source_type: 'fault',
  source_id: 'fault-uuid',
  summary: 'Main engine overheat',
  importance: 'high',
});
```

#### `createNote(request: CreateNoteRequest)`

Create a note.

```typescript
const note = await client.createNote({
  text: 'Oil leak observed at 14:23',
  equipment_id: 'uuid',
  tags: ['leak', 'monitoring'],
});
```

#### `createHandover(title: string, periodStart?: string, periodEnd?: string)`

Create new handover draft.

```typescript
const handover = await client.createHandover(
  'Weekly Handover',
  '2024-11-13',
  '2024-11-20'
);
```

---

### Utility Methods

#### `getDashboardSummary(yachtId: string)`

Get dashboard summary data.

```typescript
const dashboard = await client.getDashboardSummary(yachtId);

console.log(dashboard.predictive_summary);
console.log(dashboard.high_risk_equipment);
console.log(dashboard.recent_insights);
```

#### `health()`

Check API health.

```typescript
const health = await client.health();
console.log(health.status); // 'ok'
```

#### `predictiveHealth()`

Check predictive engine health.

```typescript
const health = await client.predictiveHealth();
console.log(health.status); // 'ok'
```

---

## React Integration

### Custom Hooks

```typescript
import { useState, useEffect } from 'react';
import api from '@/lib/api';

export function useSearchResults(query: string) {
  const [results, setResults] = useState<SearchResultCard[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!query) return;

    const performSearch = async () => {
      setLoading(true);
      setResults([]);

      const client = api.get();
      for await (const card of client.searchStream({ query })) {
        setResults((prev) => [...prev, card]);
      }

      setLoading(false);
    };

    performSearch();
  }, [query]);

  return { results, loading };
}

export function usePredictiveState(yachtId: string) {
  const [state, setState] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchState = async () => {
      const client = api.get();
      const data = await client.getPredictiveState(yachtId);
      setState(data);
      setLoading(false);
    };

    fetchState();
  }, [yachtId]);

  return { state, loading };
}
```

### Component Usage

```tsx
import { useSearchResults } from '@/hooks/useApi';

function SearchPage() {
  const [query, setQuery] = useState('');
  const { results, loading } = useSearchResults(query);

  return (
    <div>
      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search..."
      />

      {loading && <div>Loading...</div>}

      {results.map((card, i) => (
        <SearchCard key={i} card={card} />
      ))}
    </div>
  );
}
```

---

## Advanced Usage

### Custom Client Instance

Create a separate client instance with different config:

```typescript
import { createApiClient } from '@/lib/api';

const customClient = createApiClient({
  baseUrl: 'https://custom-api.com',
  getAuthToken: () => customToken,
  getYachtSignature: () => customSignature,
});

const results = await customClient.search({ query: 'test' });
```

### Multiple Environments

```typescript
const isDev = process.env.NODE_ENV === 'development';

api.init({
  baseUrl: isDev
    ? 'http://localhost:8000'
    : 'https://api.celesteos.com',
  predictiveEngineUrl: isDev
    ? 'http://localhost:8001'
    : 'https://celeste-predictive-api.onrender.com',
  // ...
});
```

---

## Type Reference

### SearchRequest

```typescript
interface SearchRequest {
  query: string;
  mode?: 'auto' | 'standard' | 'deep';
  filters?: {
    equipment_id?: string;
    document_type?: string;
    date_range?: {
      start: string;
      end: string;
    };
  };
}
```

### SearchResultCard

```typescript
interface SearchResultCard {
  type: 'document_chunk' | 'fault' | 'work_order' | 'part' | 'predictive' | ...;
  title?: string;
  text_preview?: string;
  score?: number;
  actions?: MicroAction[];

  // Predictive specific
  equipment?: string;
  risk_score?: number;
  trend?: '↑' | '↓' | '→';
  severity?: 'low' | 'medium' | 'high' | 'critical';
  // ...
}
```

### PredictiveState

```typescript
interface PredictiveState {
  id: string;
  equipment_id: string;
  equipment_name?: string;
  risk_score: number; // 0.0 - 1.0
  trend: '↑' | '↓' | '→';
  fault_signal: number;
  work_order_signal: number;
  crew_signal: number;
  part_signal: number;
  global_signal: number;
  updated_at: string;
}
```

### PredictiveInsight

```typescript
interface PredictiveInsight {
  id: string;
  equipment_id?: string;
  insight_type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  summary: string;
  explanation: string;
  recommended_action?: string;
  contributing_signals?: Record<string, number>;
  created_at: string;
}
```

See `api.ts` for complete type definitions.

---

## Examples

See `api-client.example.ts` for 14 complete examples covering all functionality.

---

## Troubleshooting

### "API client not initialized"

```typescript
// Make sure to call init() before using get()
api.init({ /* config */ });

// Then use
const client = api.get();
```

### Authentication errors (401)

Check that `getAuthToken()` returns a valid JWT:

```typescript
api.init({
  getAuthToken: () => {
    const token = localStorage.getItem('auth_token');
    console.log('Token:', token); // Debug
    return token;
  },
  // ...
});
```

### CORS errors

Ensure your API server allows requests from your frontend origin:

```
Access-Control-Allow-Origin: https://your-frontend.com
Access-Control-Allow-Headers: Authorization, X-Yacht-Signature
```

---

## Integration Checklist

- [ ] Initialize API client in app startup
- [ ] Configure authentication token provider
- [ ] Configure yacht signature provider
- [ ] Set correct API URLs (dev vs production)
- [ ] Implement error handling in UI
- [ ] Test streaming search
- [ ] Test predictive state queries
- [ ] Test action creation (work orders, notes)
- [ ] Handle loading states
- [ ] Handle error states
- [ ] Test with real backend

---

## Status

✅ **Complete and ready for use**
✅ **Integrated with Search Engine (Task 6)**
✅ **Integrated with Predictive Engine (Task 7)**
✅ **Type-safe TypeScript**
✅ **Streaming support**
✅ **Error handling**
✅ **Examples provided**

---

**Ready for Task 8 (Frontend Implementation)! 🚀**
