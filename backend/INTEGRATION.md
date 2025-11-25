# CelesteOS Backend Integration Guide

**For Worker 8 (Frontend Developer) & Worker 9 (Integration Engineer)**

---

## Architecture Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Frontend      │────▶│  Cloud API       │────▶│   Supabase      │
│   (Next.js)     │     │  (Hono)          │     │   (Postgres)    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌──────────────────┐
                        │   n8n Workflows  │
                        │   (Heavy Logic)  │
                        └──────────────────┘
```

**Key Principle:** Frontend NEVER queries Supabase directly (except Auth). All data flows through backend endpoints.

---

## API Endpoints Reference

### Base URL
```
Production: https://api.celeste7.ai/v1
Development: http://localhost:3000/v1
```

### Authentication
All requests require JWT token from Supabase Auth:
```
Authorization: Bearer <supabase_jwt>
```

Optional yacht signature for additional validation:
```
X-Yacht-Signature: <yacht_signature>
```

---

## 1. Dashboard Endpoints

### GET /v1/dashboard/briefing
Returns the intelligence snapshot for the HOD dashboard.

**Response:**
```typescript
interface DashboardBriefingResponse {
  risk_movements: RiskMovement[];
  high_risk_equipment: HighRiskEquipmentItem[];
  patterns_7d: Pattern[];
  unstable_systems: UnstableSystem[];
  inventory_gaps: InventoryGap[];
  overdue_critical: OverdueWorkOrder[];
  inspections_due: InspectionDue[];
  crew_frustration: CrewFrustration[];
  summary: SummaryStats;
  generated_at: string;
  cache_valid_until?: string;
}
```

**Frontend Usage:**
```typescript
// In your dashboard component
const { data, error } = await fetch('/v1/dashboard/briefing', {
  headers: { Authorization: `Bearer ${session.access_token}` }
}).then(r => r.json());

// Data is pre-aggregated - no need to fetch multiple sources
```

### GET /v1/dashboard/legacy
Returns traditional PMS-style overview data.

**Response:**
```typescript
interface DashboardLegacyResponse {
  equipment: EquipmentOverviewItem[];
  work_orders: WorkOrderOverviewItem[];
  inventory: InventoryOverviewItem[];
  certificates: CertificateOverviewItem[];
  faults: FaultHistoryItem[];
  scheduled_maintenance: ScheduledMaintenanceItem[];
  parts: PartUsageItem[];
  documents: DocumentsSummary;
  counts: {
    equipment: number;
    work_orders: number;
    inventory: number;
    certificates: number;
    faults_active: number;
    maintenance_overdue: number;
  };
  generated_at: string;
}
```

---

## 2. Action Router (Mutations)

**ALL mutations go through a single endpoint:**

### POST /v1/actions/execute

This is the canonical way to perform any action in CelesteOS.

**Request:**
```typescript
interface ActionExecuteRequest {
  action: string;  // e.g., "add_note", "create_work_order"
  context: {
    yacht_id: string;  // Optional - auto-injected from JWT
    equipment_id?: string;
    work_order_id?: string;
    document_id?: string;
  };
  payload: Record<string, unknown>;
}
```

**Response:**
```typescript
interface ActionExecuteResponse {
  status: 'success' | 'error';
  action: string;
  result?: Record<string, unknown>;
  error?: string;
  error_code?: string;
}
```

### Available Actions

| Action | Required Context | Required Payload |
|--------|-----------------|------------------|
| `add_note` | equipment_id | note_text |
| `create_work_order` | equipment_id | title, description?, priority? |
| `add_note_to_work_order` | work_order_id | note_text |
| `close_work_order` | work_order_id | - |
| `add_to_handover` | equipment_id | summary_text |
| `add_document_to_handover` | document_id | context? |
| `add_predictive_to_handover` | equipment_id | insight_id, summary |
| `export_handover` | - | format? |
| `open_document` | - | storage_path |
| `order_part` | - | part_id, qty |

**Example - Add Note:**
```typescript
const response = await fetch('/v1/actions/execute', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${session.access_token}`
  },
  body: JSON.stringify({
    action: 'add_note',
    context: {
      equipment_id: 'uuid-here'
    },
    payload: {
      note_text: 'Observed oil leak near pump housing'
    }
  })
});

const { status, result, error } = await response.json();

if (status === 'success') {
  // result.note_id contains the new note's ID
}
```

---

## 3. Search Integration

### POST /v1/search
Proxies to the search microservice.

**SECURITY: GDPR/SOC2/ISO27001 Compliant**
- Identity (yacht_id, user_id, role) comes **ONLY from JWT header**
- Frontend **MUST NOT** send identity fields in request body
- Schema uses `.strict()` mode to reject unexpected fields

**Request:**
```typescript
interface SearchRequest {
  query: string;  // Required: 1-1000 characters
  mode?: 'auto' | 'semantic' | 'keyword' | 'graph';  // Optional: defaults to 'auto'
  filters?: {
    equipment_id?: string;  // Optional: UUID
    document_type?: string;  // Optional
    date_from?: string;  // Optional: ISO datetime
    date_to?: string;  // Optional: ISO datetime
  };
  context?: Record<string, unknown>;  // Optional: Generic metadata (no identity)
}

// ❌ FORBIDDEN FIELDS (will be rejected):
// - user_id, yacht_id, role, email, yacht_signature
```

**Response includes actions:**
```typescript
interface SearchResponse {
  query_id: string;
  intent: string;
  entities: Record<string, unknown>;
  results: SearchResult[];
  actions: ActionSuggestion[];  // <-- Important!
}

interface ActionSuggestion {
  label: string;
  action: string;
  endpoint: string;  // Always "/v1/actions/execute"
  payload_template: Record<string, unknown>;
  constraints: {
    requires_equipment_id?: boolean;
    role?: string[];
  };
}
```

### CRITICAL: Proper Search Streaming Implementation

**❌ WRONG: Sending every keystroke**
```typescript
// DON'T DO THIS - Causes 50-100 requests per query
<input onChange={(e) => search(e.target.value)} />
```

**Problems with keystroke streaming:**
- 50-100 requests per query → n8n webhook spam
- GPT extraction runs on "m", "ma", "mai", "main" → costs explode
- Vector search on garbage → Supabase rate limits
- Feedback logs filled with noise → learning pipeline poisoned
- Situational detection triggers prematurely
- n8n queue backpressure, Render CPU spikes

**✅ CORRECT: Debounced streaming (Spotlight/Raycast model)**

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
    // Clear previous debounce timer
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    // Minimum length filter - avoid garbage
    const trimmedQuery = query.trim();
    if (trimmedQuery.length < 2) {
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

      // Create new abort controller
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
          body: JSON.stringify({
            query: trimmedQuery,
            mode: 'auto',
          }),
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
    }, 200); // 200ms debounce - industry standard

    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
      if (controllerRef.current) {
        controllerRef.current.abort();
      }
    };
  }, [query]);

  return { query, setQuery, results, isLoading };
}
```

**Usage in component:**
```tsx
export function SearchBar() {
  const { query, setQuery, results, isLoading } = useSearch();

  return (
    <div>
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search equipment, faults, documents..."
      />
      {isLoading && <Spinner />}
      {results && <ResultsList results={results} />}
    </div>
  );
}
```

**Key principles:**
1. **Debounce 200ms** - Only send when user pauses typing
2. **Cancel previous requests** - AbortController ensures latest wins
3. **Minimum length = 2 chars** - Avoid single-letter noise
4. **Show loading state** - UX feedback during fetch
5. **Handle Enter key** - Optional instant search on Enter

**Why this matters:**
- ✅ GPT extraction only runs on meaningful queries
- ✅ n8n receives 1 request instead of 50
- ✅ Feedback learning gets real terms, not keystrokes
- ✅ Situational detection triggers correctly
- ✅ Cost reduction: 98% fewer GPT calls
- ✅ Better entity extraction confidence
- ✅ Cleaner logs, stable ranking

**Result rendering pattern:**
```typescript
// Display result cards with micro-actions
{results?.results.map(result => (
  <ResultCard key={result.id}>
    <ResultContent result={result} />

    {/* Render suggested actions */}
    <ActionButtons>
      {result.actions?.map(action => (
        <Button
          key={action.action}
          onClick={() => executeAction(action)}
        >
          {action.label}
        </Button>
      ))}
    </ActionButtons>
  </ResultCard>
))}

// Execute action when clicked
async function executeAction(action: ActionSuggestion) {
  const response = await fetch('/v1/actions/execute', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${session.access_token}`,
    },
    body: JSON.stringify({
      action: action.action,
      context: action.payload_template.context || {},
      payload: action.payload_template.payload || {}
    })
  });

  const result = await response.json();
  if (result.status === 'success') {
    toast.success('Action completed');
    // Refresh data if needed
  }
}
```

---

## 4. Predictive Engine

### GET /v1/predictive/state?equipment_id=<uuid>
Get predictive state for specific equipment.

**Response:**
```typescript
interface PredictiveStateResponse {
  equipment_id: string;
  equipment_name: string;
  risk_score: number;      // 0.0 - 1.0
  risk_level: 'normal' | 'monitor' | 'emerging' | 'high' | 'critical';
  trend: 'improving' | 'stable' | 'worsening';
  confidence: number;
  contributing_factors: {
    fault_signal: number;
    work_order_signal: number;
    notes_signal: number;
    corrective_signal: number;
    criticality_signal: number;
  };
  last_calculated_at: string;
}
```

### GET /v1/predictive/insights
List active predictive insights.

**Query params:**
- `limit` (default: 20)
- `offset` (default: 0)
- `include_acknowledged` (default: false)

### POST /v1/predictive/insight/:id/acknowledge
Mark an insight as acknowledged.

### POST /v1/predictive/insight/:id/dismiss
Dismiss an insight.

---

## 5. Frontend Implementation Guide

### Page 1: Global Search (Primary Interface)

```tsx
// pages/index.tsx
export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState(null);

  const handleSearch = async (q: string) => {
    const response = await fetch('/v1/search', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${session.access_token}`
      },
      body: JSON.stringify({ query: q, mode: 'auto' })
    });
    setResults(await response.json());
  };

  return (
    <div>
      <SearchBar value={query} onChange={setQuery} onSubmit={handleSearch} />
      <ResultCanvas results={results} onAction={executeAction} />
    </div>
  );
}
```

### Page 2: Dashboard (HOD Interface)

```tsx
// pages/dashboard.tsx
export default function DashboardPage() {
  const { data: briefing } = useSWR('/v1/dashboard/briefing', fetcher);
  const { data: legacy } = useSWR('/v1/dashboard/legacy', fetcher);

  return (
    <div>
      {/* Navigation */}
      <DashboardNav />

      {/* Intelligence Briefing Section */}
      <section>
        <RiskOverview
          highRisk={briefing?.high_risk_equipment}
          movements={briefing?.risk_movements}
        />
        <AlertsList
          overdue={briefing?.overdue_critical}
          inventoryGaps={briefing?.inventory_gaps}
        />
        <PatternDetection patterns={briefing?.patterns_7d} />
      </section>

      {/* Legacy Views */}
      <section>
        <EquipmentTable data={legacy?.equipment} />
        <WorkOrderTable data={legacy?.work_orders} />
        <InventoryTable data={legacy?.inventory} />
      </section>
    </div>
  );
}
```

### Action Execution Pattern

```tsx
// hooks/useAction.ts
export function useAction() {
  const { session } = useAuth();

  const execute = async (
    action: string,
    context: Record<string, unknown>,
    payload: Record<string, unknown>
  ) => {
    const response = await fetch('/v1/actions/execute', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${session.access_token}`
      },
      body: JSON.stringify({ action, context, payload })
    });

    const result = await response.json();

    if (result.status === 'error') {
      throw new Error(result.message || result.error);
    }

    return result;
  };

  return { execute };
}
```

---

## 6. Error Handling

All errors follow a consistent format:

```typescript
interface APIError {
  status: 'error';
  error_code: string;
  message: string;
}
```

**Error Codes:**
| Code | HTTP Status | Meaning |
|------|-------------|---------|
| `missing_field` | 400 | Required field not provided |
| `invalid_field` | 400 | Field value invalid |
| `schema_invalid` | 400 | Request body validation failed |
| `unauthorized` | 401 | Invalid or missing token |
| `forbidden` | 403 | Role not allowed |
| `yacht_mismatch` | 403 | Cross-yacht access attempt |
| `not_found` | 404 | Resource not found |
| `workflow_failed` | 500 | n8n workflow error |
| `internal_error` | 500 | Server error |

---

## 7. n8n Webhook Integration

### Internal Webhooks (for triggering from backend)

| Webhook | Method | Purpose |
|---------|--------|---------|
| `/internal/predictive-recompute` | POST | Recompute risk score for equipment |
| `/internal/predictive-event` | POST | Notify of event (fault, WO, note) |
| `/internal/micro-action-dispatch` | POST | Execute micro-actions from insights |
| `/internal/dashboard-refresh` | POST | Force refresh dashboard snapshots |

### Workflow Webhooks (for action routing)

| Webhook | Method | Purpose |
|---------|--------|---------|
| `/create_work_order` | POST | Create new work order |
| `/close_work_order` | POST | Close work order |
| `/add_document_to_handover` | POST | Add document to handover |
| `/order_part` | POST | Create purchase order |
| `/export_handover` | POST | Generate handover PDF |

---

## 8. Caching Strategy

**Dashboard Briefing:**
- Cached for 30 minutes
- Auto-regenerated by n8n workflow
- `cache_valid_until` field indicates freshness

**Legacy View:**
- Cached for 1 hour
- Invalidated nightly by cleanup workflow

**Predictive State:**
- Recalculated on events (fault, WO, note)
- Full recalculation runs daily at midnight

---

## 9. Environment Variables

Backend requires:
```env
# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...

# n8n
N8N_WEBHOOK_URL=https://n8n.celeste7.ai/webhook

# Internal
INTERNAL_SERVICE_KEY=your-secret-key
ALLOWED_ORIGINS=https://app.celeste7.ai,http://localhost:3000

# Optional
SEARCH_SERVICE_URL=http://localhost:3001
PORT=3000
NODE_ENV=production
```

---

## 10. Testing Checklist

Before deploying:

- [ ] Authentication flow works with Supabase JWT
- [ ] Dashboard briefing loads with cached data
- [ ] Dashboard legacy view loads all sections
- [ ] Action router validates roles correctly
- [ ] Search returns results with action suggestions
- [ ] Predictive insights list and acknowledge work
- [ ] Error responses follow standard format
- [ ] Yacht isolation prevents cross-yacht access

---

## Support

For questions:
- Architecture: See `architecture.md`
- API Spec: See `api-spec.md`
- Action Details: See `action-endpoint-contract.md`
- Predictive Logic: See `predictive-maintenance.md`
