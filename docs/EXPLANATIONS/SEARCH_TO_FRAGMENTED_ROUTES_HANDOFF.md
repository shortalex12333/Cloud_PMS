# Search System → Fragmented Routes Handoff Document

> **Author**: Claude Opus 4.5 (Protocol Omega)
> **Date**: 2026-02-26
> **Purpose**: Complete technical handoff for transitioning search results from single-URL to fragmented route architecture

---

## Executive Summary

The Celeste OS search system operates on a **two-stage fetch model** (like Google):
1. **Stage 1 (Search)**: Query `search_index` table → return lightweight results with `object_type` + `object_id`
2. **Stage 2 (Detail)**: On click, fetch full entity from source table via `/v1/entity/{type}/{id}`

The transition to fragmented routes changes **how we navigate to detail views**, NOT how search works.

---

## 1. SEARCH ARCHITECTURE OVERVIEW

### 1.1 Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SEARCH FLOW                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  [User Types Query]                                                          │
│         │                                                                    │
│         ▼                                                                    │
│  ┌──────────────────┐     SSE Stream      ┌─────────────────────────────┐   │
│  │ useCelesteSearch │ ──────────────────► │ /api/f1/search/stream?q=... │   │
│  │ (Frontend Hook)  │ ◄────────────────── │ (Backend SSE Endpoint)      │   │
│  └──────────────────┘     result_batch    └─────────────────────────────┘   │
│         │                                            │                       │
│         │                                            ▼                       │
│         │                                 ┌─────────────────────────────┐   │
│         │                                 │     search_index TABLE      │   │
│         │                                 │  (Lightweight: payload JSONB)│   │
│         │                                 │  Returns: object_type,       │   │
│         │                                 │           object_id,         │   │
│         │                                 │           payload (display)  │   │
│         │                                 └─────────────────────────────┘   │
│         │                                                                    │
│         ▼                                                                    │
│  ┌──────────────────┐                                                       │
│  │ SpotlightSearch  │  User clicks result                                   │
│  │ (Result List UI) │ ─────────────────────────────────────────────┐        │
│  └──────────────────┘                                              │        │
│                                                                    │        │
├────────────────────────────────────────────────────────────────────┼────────┤
│                           DETAIL FLOW                              │        │
├────────────────────────────────────────────────────────────────────┼────────┤
│                                                                    ▼        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    NAVIGATION DECISION POINT                         │   │
│  │                                                                       │   │
│  │   if (isFragmentedRoutesEnabled()) {                                 │   │
│  │     router.push(`/${routeMap[entityType]}/${entityId}`);             │   │
│  │     // e.g., /work-orders/abc-123                                    │   │
│  │   } else {                                                            │   │
│  │     surfaceContext.showContext(entityType, entityId);                │   │
│  │     // Opens ContextPanel (slide-in)                                 │   │
│  │   }                                                                   │   │
│  │                                                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              │                                              │
│                              ▼                                              │
│  ┌──────────────────┐                    ┌─────────────────────────────┐   │
│  │ ContextPanel OR  │  GET /v1/entity/   │      SOURCE TABLES          │   │
│  │ Fragmented Route │ ─────────────────► │  pms_equipment              │   │
│  │ Detail Page      │ ◄───────────────── │  pms_work_orders            │   │
│  └──────────────────┘   Full Entity Data │  pms_faults                 │   │
│                                          │  pms_parts                  │   │
│                                          │  pms_documents              │   │
│                                          └─────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Key Principle: Two-Stage Fetch

| Stage | Source | Data | Purpose |
|-------|--------|------|---------|
| **Search** | `search_index` | `object_type`, `object_id`, `payload` (JSONB) | Fast results display |
| **Detail** | Source tables (`pms_*`) | Full entity with all fields | Complete entity view |

**WHY**: `search_index` contains denormalized, searchable text + lightweight display data. Source tables contain the authoritative, complete entity data.

---

## 2. SEARCH INDEX TABLE SCHEMA

**File**: `database/migrations/01_create_search_index.sql`

### 2.1 Core Columns

```sql
CREATE TABLE public.search_index (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- Identity (CRITICAL for routing)
  object_type TEXT NOT NULL,     -- 'equipment', 'work_order', 'fault', 'part', etc.
  object_id UUID NOT NULL,       -- FK to source table (pms_equipment.id, etc.)

  -- Tenant Isolation (LAW 8)
  org_id UUID NOT NULL,
  yacht_id UUID NOT NULL,

  -- Search Content
  search_text TEXT,              -- Raw text for trigram search
  tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', search_text)) STORED,
  embedding_1536 VECTOR(1536),   -- Semantic search vector

  -- Display Data (returned in search results)
  payload JSONB,                 -- {name, code, status, source_table, ...}

  -- Filtering
  filters JSONB,                 -- {status: 'open', category: 'engine'}

  UNIQUE (object_type, object_id)
);
```

### 2.2 Payload Structure by Entity Type

| object_type | payload fields | Example |
|-------------|----------------|---------|
| `equipment` | `name`, `code`, `status`, `source_table` | `{"name": "Generator 1", "code": "GEN-001", "status": "operational"}` |
| `work_order` | `title`, `status`, `priority`, `source_table` | `{"title": "Oil Change", "status": "in_progress"}` |
| `fault` | `title`, `fault_code`, `status`, `severity` | `{"title": "Engine Overheat", "fault_code": "F-001"}` |
| `part` | `name`, `part_number`, `manufacturer`, `quantity` | `{"name": "Oil Filter", "part_number": "CAT-123"}` |
| `document` | `name`, `document_type`, `source_table` | `{"name": "Engine Manual", "document_type": "manual"}` |
| `shopping_item` | `part_name`, `status`, `urgency`, `quantity` | `{"part_name": "Oil Filter", "status": "approved"}` |

---

## 3. BACKEND: F1 SEARCH ENDPOINT

**File**: `apps/api/routes/f1_search_streaming.py`

### 3.1 Endpoint

```
GET /api/f1/search/stream?q={query}
Headers:
  Authorization: Bearer {jwt}
  X-Yacht-Signature: {optional}
Response: text/event-stream (SSE)
```

### 3.2 SSE Events

```typescript
// 1. Search started
event: diagnostics
data: {"search_id": "uuid", "status": "started", "query": "generator"}

// 2. Results batch (MAIN DATA)
event: result_batch
data: {
  "search_id": "uuid",
  "items": [
    {
      "object_type": "equipment",        // ← Entity type for routing
      "object_id": "abc-123-uuid",       // ← Entity ID for fetching
      "payload": {                        // ← Display data
        "name": "Generator 1",
        "code": "GEN-001",
        "status": "operational",
        "source_table": "pms_equipment"
      },
      "fused_score": 0.87,
      "ranks": {"trigram": 1, "tsv": 3, "vector": null}
    }
  ],
  "partial": false,
  "count": 20
}

// 3. Search complete
event: finalized
data: {"search_id": "uuid", "latency_ms": 187, "total_results": 20}
```

### 3.3 Database Function: `f1_search_cards`

**File**: `database/migrations/40_create_f1_search_cards.sql`

```sql
SELECT object_type, object_id, payload, fused_score, best_rewrite_idx, ranks, components
FROM f1_search_cards(
  $1::text[],           -- Query rewrites (max 3)
  $2::vector(1536)[],   -- Embeddings for semantic search
  $3::uuid,             -- org_id
  $4::uuid,             -- yacht_id
  $5::int,              -- rrf_k (default 60)
  $6::int,              -- page_limit (default 20)
  $7::real,             -- trigram threshold (default 0.15)
  $8::text[]            -- object_types filter (NULL = all)
)
```

**Returns from `search_index` table only** - does NOT join to source tables.

---

## 4. FRONTEND: SEARCH HOOK

**File**: `apps/web/src/hooks/useCelesteSearch.ts`

### 4.1 Field Mapping (Lines 576-604)

```typescript
// Backend returns:
{
  object_id: "abc-123",        // UUID from search_index
  object_type: "equipment",    // Entity type string
  payload: { name: "...", code: "...", status: "..." }
}

// Hook maps to:
{
  id: result.object_id,        // ← CRITICAL: This is what gets passed to detail view
  type: result.object_type,    // ← CRITICAL: This determines the route/lens
  title: payload.name || payload.title || payload.part_name,
  subtitle: payload.code || payload.status,
  score: result.fused_score,
  metadata: { payload }        // Original payload preserved
}
```

### 4.2 Hook API

```typescript
const {
  query,              // Current search text
  results,            // SearchResult[] - mapped results
  isLoading,
  error,
  handleQueryChange,  // Update query
  clear,              // Clear search
} = useCelesteSearch(yachtId);
```

---

## 5. RESULT CLICK HANDLING

**File**: `apps/web/src/components/spotlight/SpotlightSearch.tsx`

### 5.1 Current Flow (Lines 533-610)

```typescript
const handleResultOpen = async (result: SpotlightResult) => {
  // 1. Map result type to entity type
  const entityType = mapResultTypeToEntityType(result.type);
  // e.g., "pms_equipment" → "equipment"
  //       "work_order" → "work_order"

  // 2. Get entity ID (already mapped by useCelesteSearch)
  const entityId = result.id;

  // 3. Open detail view
  surfaceContext.showContext(entityType, entityId, contextMetadata);
  // This triggers ContextPanel to fetch from /v1/entity/{type}/{id}
};
```

### 5.2 Type Mapping (Lines 478-487)

```typescript
const mapResultTypeToEntityType = (type: string): EntityType => {
  if (type.includes('document')) return 'document';
  if (type.includes('equipment') || type === 'pms_equipment') return 'equipment';
  if (type.includes('part') || type === 'pms_parts') return 'part';
  if (type.includes('work_order')) return 'work_order';
  if (type.includes('fault')) return 'fault';
  if (type.includes('inventory') || type === 'v_inventory') return 'inventory';
  if (type.includes('email')) return 'email_thread';
  return 'document'; // fallback
};
```

---

## 6. DETAIL VIEW FETCHING

**File**: `apps/web/src/app/app/ContextPanel.tsx`

### 6.1 Entity Fetch Endpoint

```typescript
// Line 57-65
const response = await fetch(
  `${PIPELINE_URL}/v1/entity/${entityType}/${entityId}`,
  {
    headers: {
      'Authorization': `Bearer ${session.access_token}`,
    },
  }
);
```

**This fetches from SOURCE TABLES, not search_index.**

### 6.2 Backend Entity Endpoint

**Expected Endpoint**: `GET /v1/entity/{entityType}/{entityId}`

**Returns**: Full entity data from source table (pms_equipment, pms_work_orders, etc.)

---

## 7. FRAGMENTED ROUTES IMPLEMENTATION

**File**: `apps/web/src/lib/featureFlags.ts`

### 7.1 Feature Flag

```typescript
export function isFragmentedRoutesEnabled(): boolean {
  return process.env.NEXT_PUBLIC_FRAGMENTED_ROUTES_ENABLED === 'true';
}
```

### 7.2 Route Mapping

```typescript
export function getEntityRoute(entityType: string, entityId?: string): string {
  if (isFragmentedRoutesEnabled()) {
    const routeMap: Record<string, string> = {
      work_order: '/work-orders',
      fault: '/faults',
      equipment: '/equipment',
      part: '/inventory',
      email: '/email',
    };
    const base = routeMap[entityType] || '/app';
    return entityId ? `${base}/${entityId}` : base;
  }
  return entityId ? `/app?entity=${entityType}&id=${entityId}` : '/app';
}
```

### 7.3 Example Fragmented Route Page

**File**: `apps/web/src/app/work-orders/[id]/page.tsx`

```typescript
// 1. Feature flag guard - redirect to legacy if disabled
function FeatureFlagGuard({ children }) {
  const router = useRouter();
  const params = useParams();

  useEffect(() => {
    if (!isFragmentedRoutesEnabled()) {
      router.replace(`/app?entity=work_order&id=${params.id}`);
    }
  }, []);

  if (!isFragmentedRoutesEnabled()) return <Redirecting />;
  return children;
}

// 2. Fetch entity data
async function fetchWorkOrderDetail(id: string, token: string) {
  const response = await fetch(`${API_URL}/v1/entity/work_order/${id}`, {
    headers: { 'Authorization': `Bearer ${token}` },
  });
  return response.json();
}

// 3. Render lens component
export default function WorkOrderDetailPage() {
  return (
    <FeatureFlagGuard>
      <RouteLayout>
        <WorkOrderLensContent id={id} data={data} onNavigate={handleNavigate} />
      </RouteLayout>
    </FeatureFlagGuard>
  );
}
```

---

## 8. WHAT NEEDS TO CHANGE FOR FRAGMENTED ROUTES

### 8.1 SpotlightSearch.tsx - handleResultOpen

**BEFORE** (current):
```typescript
surfaceContext.showContext(entityType, entityId, contextMetadata);
```

**AFTER** (fragmented routes):
```typescript
if (isFragmentedRoutesEnabled()) {
  router.push(getEntityRoute(entityType, entityId));
  onClose?.();  // Close spotlight
} else {
  surfaceContext.showContext(entityType, entityId, contextMetadata);
}
```

### 8.2 New Route Pages to Create

| Entity Type | Route | Page File |
|-------------|-------|-----------|
| `work_order` | `/work-orders/[id]` | `app/work-orders/[id]/page.tsx` ✅ EXISTS |
| `fault` | `/faults/[id]` | `app/faults/[id]/page.tsx` |
| `equipment` | `/equipment/[id]` | `app/equipment/[id]/page.tsx` |
| `part` | `/inventory/[id]` | `app/inventory/[id]/page.tsx` |
| `document` | `/documents/[id]` | `app/documents/[id]/page.tsx` |
| `certificate` | `/certificates/[id]` | `app/certificates/[id]/page.tsx` |
| `receiving` | `/receiving/[id]` | `app/receiving/[id]/page.tsx` |
| `shopping_list` | `/shopping-list/[id]` | `app/shopping-list/[id]/page.tsx` |

### 8.3 Cross-Entity Navigation

When inside a detail page, clicking related entities must also route correctly:

```typescript
const handleNavigate = (entityType: string, entityId: string) => {
  if (isFragmentedRoutesEnabled()) {
    router.push(getEntityRoute(entityType, entityId));
  } else {
    router.push(`/app?entity=${entityType}&id=${entityId}`);
  }
};
```

---

## 9. DO's AND DON'Ts

### 9.1 DO's

| DO | WHY |
|----|-----|
| Use `result.id` (mapped from `object_id`) for routing | This is the source table PK |
| Use `result.type` (mapped from `object_type`) for route selection | Determines which page/lens to load |
| Fetch full entity from `/v1/entity/{type}/{id}` on detail page | `search_index.payload` is incomplete |
| Include feature flag guard on all new route pages | Allows gradual rollout |
| Preserve back navigation with `NavigationContext` or browser history | Users expect back button to work |
| Handle deep links (direct URL access) | `/equipment/abc-123` must work without prior search |
| Record click events via `POST /api/f1/search/click` | Enables learning feedback loop |

### 9.2 DON'Ts

| DON'T | WHY |
|-------|-----|
| Don't fetch detail data from `search_index` | `payload` is denormalized for display only, not complete |
| Don't hardcode entity types | Use mapping functions for extensibility |
| Don't skip the feature flag check | Legacy users need fallback |
| Don't break ContextPanel (legacy) | Must coexist during transition |
| Don't assume `object_type` equals route segment | Mapping required (e.g., `part` → `/inventory`) |
| Don't lose search context on navigation | User may want to return to results |

---

## 10. GUARDRAILS & LIMITATIONS

### 10.1 Tenant Isolation (LAW 8)

- `yacht_id` is ALWAYS extracted from JWT server-side
- NEVER trust `yacht_id` from client payload
- All entity fetches must include JWT for authorization

### 10.2 Search Index Latency

- Projector worker updates `search_index` asynchronously
- New entities may not appear in search immediately (seconds to minutes)
- Detail pages fetch from source tables (always current)

### 10.3 Entity Types Without Routes

Some entity types in search results may not have dedicated routes:
- `email_thread` - Opens in EmailPanel, not a route
- `shopping_item` - Part of shopping list, not standalone
- `handover_item` - Part of handover document

Handle these with fallback to ContextPanel or appropriate panel.

### 10.4 URL Structure Constraints

- IDs are UUIDs - URL safe but long
- No special characters in route segments
- Consider SEO-friendly slugs for future (e.g., `/equipment/generator-1-abc123`)

---

## 11. TESTING CHECKLIST

### 11.1 Search → Detail Flow

- [ ] Search "generator" → Click equipment result → Opens `/equipment/{id}`
- [ ] Search "work order" → Click WO result → Opens `/work-orders/{id}`
- [ ] Search "fault" → Click fault result → Opens `/faults/{id}`
- [ ] Search "part" → Click part result → Opens `/inventory/{id}`

### 11.2 Deep Links

- [ ] Direct URL `/equipment/{id}` loads correctly
- [ ] Direct URL with invalid ID shows 404
- [ ] Direct URL without auth redirects to login

### 11.3 Navigation

- [ ] Back button returns to search results (if came from search)
- [ ] Back button returns to previous page (if deep linked)
- [ ] Cross-entity navigation works (Equipment → related Fault)

### 11.4 Feature Flag

- [ ] Flag OFF: All routes redirect to `/app?entity=...`
- [ ] Flag ON: Routes work as expected
- [ ] Flag change doesn't break active sessions

---

## 12. FILE REFERENCE

| Purpose | File Path |
|---------|-----------|
| Search Hook | `apps/web/src/hooks/useCelesteSearch.ts` |
| Spotlight UI | `apps/web/src/components/spotlight/SpotlightSearch.tsx` |
| Context Panel | `apps/web/src/app/app/ContextPanel.tsx` |
| Surface Context | `apps/web/src/contexts/SurfaceContext.tsx` |
| Feature Flags | `apps/web/src/lib/featureFlags.ts` |
| Route Layout | `apps/web/src/components/layout/RouteLayout.tsx` |
| Lens Renderer | `apps/web/src/components/lens/LensRenderer.tsx` |
| Work Order Route | `apps/web/src/app/work-orders/[id]/page.tsx` |
| Search Backend | `apps/api/routes/f1_search_streaming.py` |
| Entity Backend | `apps/api/routes/entity_routes.py` (expected) |
| Search Index Schema | `database/migrations/01_create_search_index.sql` |
| F1 Search RPC | `database/migrations/40_create_f1_search_cards.sql` |

---

## 13. SUMMARY

**The search system works. The detail fetching works. What changes is the NAVIGATION.**

1. **Search returns** `object_type` + `object_id` from `search_index`
2. **Click handler** maps these to a route URL
3. **Route page** fetches full entity from `/v1/entity/{type}/{id}`
4. **Lens component** renders the entity data

The fragmented routes transition is a **frontend routing change**, not a search or backend change.

---

*Document generated by Claude Opus 4.5 for Protocol Omega handoff.*
