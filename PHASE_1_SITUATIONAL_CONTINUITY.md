# PHASE 1: Situational Continuity MVP - Understanding & Setup

**Date**: 2026-01-15
**Branch**: `feature/situational-continuity-mvp`
**Status**: Phase 1 Complete - Awaiting Approval to Proceed

---

## A) REPOSITORY MAP SUMMARY

### Current Repository Structure

**Location**: `/Users/celeste7/Documents/Cloud_PMS`

```
Cloud_PMS/
├── apps/
│   ├── web/                          # Next.js frontend
│   │   ├── src/
│   │   │   ├── app/
│   │   │   │   ├── search/           # Spotlight search page (entry point)
│   │   │   │   ├── (dashboard)/      # Work orders, faults, parts routes
│   │   │   │   └── api/              # Next.js API routes
│   │   │   ├── components/
│   │   │   │   ├── spotlight/        # Search UI component
│   │   │   │   ├── cards/            # FaultCard, WorkOrderCard, DocumentCard, etc.
│   │   │   │   ├── document/         # DocumentViewer.tsx
│   │   │   │   └── situations/       # EXISTING: DocumentSituationView, SituationRouter
│   │   │   ├── lib/
│   │   │   │   ├── situations/       # EXISTING: Situation Engine (fault pattern detection)
│   │   │   │   ├── microactions/     # Action handlers
│   │   │   │   └── action-router/    # Action routing
│   │   │   ├── contexts/             # React contexts
│   │   │   └── hooks/                # React hooks
│   │   └── package.json
│   │
│   ├── api/                          # Python FastAPI backend
│   │   ├── routes/                   # API route handlers
│   │   ├── handlers/                 # Business logic handlers
│   │   ├── action_router/            # Action routing
│   │   └── pipeline_service.py       # Main FastAPI app
│   │
│   └── worker/                       # Background workers (minimal)
│
├── supabase/
│   └── migrations/                   # Database migrations
│       └── 00000000000020_situation_engine_tables.sql  # EXISTING (different purpose)
│
└── docs/                             # Documentation (57 files)
```

### Key Existing Infrastructure

#### 1. **Search Entry Point**
- **File**: `apps/web/src/app/search/SearchContent.tsx`
- **Component**: `<SpotlightSearch />` from `@/components/spotlight`
- **Purpose**: User's search bar home - the starting point for all situations

#### 2. **Existing "Situation" System** (DIFFERENT PURPOSE)
- **Location**: `apps/web/src/lib/situations/`
- **Purpose**: AI-powered fault pattern detection (recurrent symptoms, risk prediction)
- **Tables**: `situation_detections`, `symptom_reports`, `predictive_state`
- **IMPORTANT**: This is NOT the same as the Situational Continuity Layer we're building

#### 3. **Artifact Viewers**
- **Cards**: `FaultCard`, `WorkOrderCard`, `DocumentCard`, `EquipmentCard`, etc.
- **Viewers**: `DocumentViewer`, `DocumentSituationView`
- **Current Flow**: Search → Click result → Open card/viewer

#### 4. **Database**
- **System**: Supabase PostgreSQL
- **Tenant**: Uses `yacht_id` for isolation
- **Auth**: RLS policies on all tables
- **Existing Tables**:
  - `pms_work_orders`, `pms_equipment`, `pms_parts`, `pms_faults`
  - `search_document_chunks` (47k+ rows)
  - `action_executions`, `situation_detections` (existing situation engine)

### Where to Hook In

**Current User Flow**:
```
Search Bar Home → Type Query → Click Result → Open Artifact Viewer
                                                      ↓
                                              (Context LOST - No Related, No Back/Forward)
```

**Target User Flow**:
```
Search Bar Home → Type Query → Click Result → Create Situation → Open Artifact Viewer
                                                   ↓                      ↓
                                            (Persistent Context)    [Show Related]
                                                   ↓                      ↓
                                            Navigate Related → Update Anchor → Viewer
                                                   ↓
                                            [Back/Forward Navigation]
                                                   ↓
                                            Return to Search Home → End Situation
```

---

## B) INVARIANTS TO ENFORCE

### Non-Negotiable Constraints (From Specification)

#### 1. **Situation Lifecycle**
- ✅ Situation created ONLY when artifact opened from search
- ✅ Situation persists across artifact navigation
- ✅ Situation ends ONLY when user returns to search bar home
- ✅ Ended situations archived for audit only (not recoverable)
- ❌ NO situation resurrection after termination

#### 2. **Navigation Integrity**
- ✅ Linear stack only (no branching)
- ✅ Back navigates to prior artifact view
- ✅ Forward available only if Back was pressed
- ✅ Max 9 views in stack (soft cap, silent truncation)
- ❌ NO "back to search results"
- ❌ NO query replay on navigation

#### 3. **Related Expansion Rules**
- ✅ Related is READ-ONLY (no mutations)
- ✅ Related uses SAME situation (no re-query)
- ✅ Domain-first grouping (fixed order)
- ✅ Empty results are valid (silence, not errors)
- ❌ NO vector search or embeddings
- ❌ NO LLM calls
- ❌ NO ranking/confidence scores
- ❌ NO client-side reordering

#### 4. **Audit Trail Purity**
- ✅ Log ONLY explicit user actions: `artefact_opened`, `relation_added`, `situation_ended`
- ❌ NO logging of: `related_opened`, `navigation_back`, `navigation_forward`, hover, scroll

#### 5. **Permission Enforcement**
- ✅ Server-side permission checks
- ✅ Silent omission of unauthorized domains
- ✅ Tenant isolation (yacht_id)
- ❌ NO permission warnings in UI

#### 6. **State Boundaries**
- ✅ Navigation stack in memory ONLY (destroyed on refresh)
- ✅ Situation DB record for audit ONLY
- ❌ NO state persistence beyond situation lifetime
- ❌ NO user preferences or learning

#### 7. **Add Related Semantics**
- ✅ Global within tenant database
- ✅ Immediate activation (no approval)
- ✅ Directional relations
- ✅ User attribution required
- ❌ NO inverse relation inference

---

## C) IMPLEMENTATION PLAN (File-Level)

### Naming Strategy (CRITICAL)

**Problem**: Existing codebase has `lib/situations/` for AI pattern detection.
**Solution**: Use distinct naming to avoid conflicts:
- **New Module Name**: `context-nav` (short for contextual navigation)
- **Primary Types**: `NavigationContext` (not "Situation"), `ViewStack`, `RelatedPanel`

### Database Layer

#### New Migrations

**File**: `supabase/migrations/00000000000022_context_navigation_tables.sql`

```sql
-- Situational Continuity Tables (distinct from situation_detections)
CREATE TABLE navigation_contexts (
  id UUID PRIMARY KEY,
  yacht_id UUID NOT NULL,
  created_by_user_id UUID NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  ended_at TIMESTAMPTZ NULL,
  active_anchor_type TEXT NOT NULL,
  active_anchor_id UUID NOT NULL,
  extracted_entities JSONB NOT NULL DEFAULT '{}',
  temporal_bias TEXT NOT NULL DEFAULT 'now'
);

CREATE TABLE user_added_relations (
  id UUID PRIMARY KEY,
  yacht_id UUID NOT NULL,
  created_by_user_id UUID NOT NULL,
  from_artefact_type TEXT NOT NULL,
  from_artefact_id UUID NOT NULL,
  to_artefact_type TEXT NOT NULL,
  to_artefact_id UUID NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE audit_events (
  id UUID PRIMARY KEY,
  yacht_id UUID NOT NULL,
  user_id UUID NOT NULL,
  event_name TEXT NOT NULL,
  payload JSONB NOT NULL,
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- RLS Policies (yacht isolation)
-- Indexes for performance
```

**File**: `supabase/migrations/00000000000023_context_navigation_rls.sql`
- RLS policies for all new tables
- Indexes on `(yacht_id, created_at)`, `(yacht_id, from_artefact_id)`, etc.

### Backend (Python FastAPI)

#### New Route Files

**File**: `apps/api/routes/context_navigation_routes.py`
```python
# Endpoints:
# POST /api/context/create          - Create navigation context
# PUT  /api/context/{id}/update      - Update anchor
# POST /api/context/{id}/end         - End context
# POST /api/context/related          - Get related artifacts
# POST /api/context/add-relation     - Add user relation
```

**File**: `apps/api/handlers/context_navigation_handlers.py`
```python
# Business logic:
# - create_navigation_context()
# - update_active_anchor()
# - get_related_artifacts()      # Deterministic queries only
# - add_user_relation()
# - end_navigation_context()
```

**File**: `apps/api/context_nav/related_expansion.py`
```python
# Deterministic related queries:
# - query_related_inventory()
# - query_related_work_orders()
# - query_related_faults()
# - query_related_documents()
# - query_user_added_relations()
# ALL use JOIN/FK only (NO vector search)
```

**File**: `apps/api/context_nav/schemas.py`
```python
# Pydantic models matching JSON schemas:
# - NavigationContextCreate
# - RelatedRequest
# - RelatedResponse
# - AddRelatedRequest
```

#### Integration Point

**File**: `apps/api/pipeline_service.py`
```python
# Add router:
from routes.context_navigation_routes import router as context_nav_router
app.include_router(context_nav_router, prefix="/api/context", tags=["context-nav"])
```

### Frontend (Next.js + React)

#### Core Library

**File**: `apps/web/src/lib/context-nav/types.ts`
```typescript
// Navigation context types (separate from existing situations)
export interface NavigationContext {
  id: string;
  yacht_id: string;
  active_anchor_type: string;
  active_anchor_id: string;
  extracted_entities: Record<string, any>;
  temporal_bias: 'now' | 'recent' | 'historical';
}

export interface ViewState {
  id: string;
  context_id: string;
  artefact_type: string;
  artefact_id: string;
  view_mode: 'viewer' | 'related';
}

export interface RelatedGroup {
  domain: string;
  items: RelatedItem[];
}
```

**File**: `apps/web/src/lib/context-nav/navigation-context.ts`
```typescript
// Core context management
export class NavigationContextManager {
  async createContext(artefactType, artefactId): Promise<NavigationContext>
  async updateAnchor(contextId, artefactType, artefactId): Promise<void>
  async endContext(contextId): Promise<void>
}
```

**File**: `apps/web/src/lib/context-nav/view-stack.ts`
```typescript
// In-memory stack management
export class ViewStack {
  private stack: ViewState[] = [];
  private forwardStack: ViewState[] = [];

  push(viewState: ViewState): void
  pop(): ViewState | null
  forward(): ViewState | null
  clear(): void
  // Max 9 items enforcement
}
```

**File**: `apps/web/src/lib/context-nav/related-client.ts`
```typescript
// API client for related expansion
export async function fetchRelated(
  contextId: string,
  anchorType: string,
  anchorId: string
): Promise<RelatedGroup[]>

export async function addRelation(
  fromType: string,
  fromId: string,
  toType: string,
  toId: string
): Promise<void>
```

#### React Context/Hooks

**File**: `apps/web/src/contexts/NavigationContext.tsx`
```typescript
// React context provider for navigation state
export const NavigationContextProvider: React.FC<{children}>
export const useNavigationContext = () => useContext(NavigationContextCtx)
```

**File**: `apps/web/src/hooks/useViewStack.ts`
```typescript
// Hook for back/forward navigation
export function useViewStack() {
  const [stack, setStack] = useState<ViewState[]>([]);
  return { push, pop, forward, canGoBack, canGoForward };
}
```

**File**: `apps/web/src/hooks/useRelated.ts`
```typescript
// Hook for related expansion
export function useRelated(anchorType: string, anchorId: string) {
  const [groups, setGroups] = useState<RelatedGroup[]>([]);
  const [loading, setLoading] = useState(false);
  return { groups, loading, refresh };
}
```

#### UI Components

**File**: `apps/web/src/components/context-nav/ViewerHeader.tsx`
```typescript
// Back/Forward buttons for artifact viewers
export function ViewerHeader() {
  const { canGoBack, canGoForward, goBack, goForward } = useViewStack();
  return (
    <div className="viewer-header">
      <button onClick={goBack} disabled={!canGoBack}>← Back</button>
      <button onClick={goForward} disabled={!canGoForward}>Forward →</button>
      <button onClick={showRelated}>Show Related</button>
    </div>
  );
}
```

**File**: `apps/web/src/components/context-nav/RelatedPanel.tsx`
```typescript
// Domain-grouped related artifacts panel
export function RelatedPanel({ anchorType, anchorId }) {
  const { groups, loading } = useRelated(anchorType, anchorId);

  return (
    <div className="related-panel">
      {groups.map(group => (
        <RelatedDomainGroup key={group.domain} group={group} />
      ))}
      {groups.length === 0 && <EmptyRelatedState />}
    </div>
  );
}
```

**File**: `apps/web/src/components/context-nav/RelatedDomainGroup.tsx`
```typescript
// Single domain group (inventory, work_orders, etc.)
export function RelatedDomainGroup({ group }) {
  return (
    <section className="domain-group">
      <h3>{group.domain}</h3>
      <ul>
        {group.items.map(item => (
          <RelatedItem key={item.artefact_id} item={item} />
        ))}
      </ul>
    </section>
  );
}
```

**File**: `apps/web/src/components/context-nav/AddRelatedButton.tsx`
```typescript
// User-controlled relation addition
export function AddRelatedButton({ fromType, fromId }) {
  return <button onClick={openAddRelatedModal}>+ Add Related</button>;
}
```

#### Integration Points

**Files to Modify** (MINIMAL changes):

1. **`apps/web/src/app/search/SearchContent.tsx`**
   - When user clicks search result → call `createContext()`
   - Wrap with `<NavigationContextProvider>`

2. **`apps/web/src/components/cards/FaultCard.tsx`** (and similar)
   - Add `<ViewerHeader />` at top
   - When opening from Related → call `updateAnchor()`

3. **`apps/web/src/components/document/DocumentViewer.tsx`**
   - Add `<ViewerHeader />` at top
   - Add "Show Related" button

4. **`apps/web/src/app/layout.tsx`** or equivalent
   - Wrap app with `<NavigationContextProvider>`

---

## D) CONFLICT-RISK ASSESSMENT

### HIGH RISK (Avoid These Files)

1. **`apps/web/src/app/api/integrations/outlook/*`**
   - **Status**: Modified but not committed (other developer active)
   - **Action**: DO NOT TOUCH - other developer working on Outlook integration

2. **`apps/web/src/lib/email/*`**
   - **Status**: Untracked new directory
   - **Action**: AVOID - email integration in progress

3. **`supabase/migrations/00000000000021_phase4_email_transport_layer.sql`**
   - **Status**: Untracked migration
   - **Action**: Our migration will be `00000000000022_*` to avoid conflict

### MEDIUM RISK (Minor Overlap)

4. **`apps/web/src/lib/situations/*`**
   - **Risk**: Name collision with existing Situation Engine
   - **Mitigation**: Use `context-nav` namespace instead

5. **`apps/web/src/components/situations/*`**
   - **Risk**: Could be confused with our components
   - **Mitigation**: Use `components/context-nav/` directory

### LOW RISK (Safe to Modify)

6. **`apps/web/src/components/cards/*.tsx`**
   - **Risk**: Low - only adding `<ViewerHeader />`
   - **Mitigation**: Minimal one-line additions

7. **`apps/web/src/app/search/*`**
   - **Risk**: Low - only adding context creation hook
   - **Mitigation**: Non-invasive change in click handler

### ZERO RISK (New Files)

All new files in `context-nav/` namespace have zero conflict risk.

---

## E) LOCAL ENVIRONMENT COMMANDS & STATUS

### Environment Configuration

**Supabase Credentials** (from `env vars.md`):
```
MASTER_SUPABASE_URL=https://qvzmkaamzaqxpzbewjxe.supabase.co
TENANT_1_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
TEST_USER_EMAIL=x@alex-short.com
TEST_YACHT_ID=85fe1119-b04c-41ac-80f1-829d23322598
```

### Git Operations

```bash
# ✅ COMPLETED
cd /Users/celeste7/Documents/Cloud_PMS
git fetch && git pull origin main              # SUCCESS: Already up to date
git checkout -b feature/situational-continuity-mvp  # SUCCESS: Branch created
git branch --show-current                      # OUTPUT: feature/situational-continuity-mvp
```

### Docker/Local Run (NOT YET ATTEMPTED)

**BLOCKER**: No `docker-compose.yml` found in repository root.

**Investigation Needed**:
```bash
# Commands to try in Phase 2:
cd /Users/celeste7/Documents/Cloud_PMS/apps/web
npm install                                    # Install frontend deps
npm run dev                                    # Start Next.js dev server

cd /Users/celeste7/Documents/Cloud_PMS/apps/api
pip install -r requirements.txt                # Install Python deps
uvicorn pipeline_service:app --reload          # Start FastAPI

# Supabase connection test (via Next.js app)
# Expected: Can connect to Tenant 1 database
```

**Status**: ⚠️ PENDING - Requires Phase 2 validation

### Build Validation (NOT YET ATTEMPTED)

```bash
# Frontend typecheck (will run after placeholders created)
cd apps/web
npm run typecheck                              # Verify TS types

# Backend tests (if any exist)
cd apps/api
pytest                                         # Run Python tests
```

**Status**: ⚠️ PENDING - Requires placeholder files first

---

## F) PLACEHOLDER FILES CREATED

**Status**: ⏳ IN PROGRESS - Will create minimal placeholders next

### Backend Placeholders

```
apps/api/
├── routes/
│   └── context_navigation_routes.py          # Placeholder route registration
├── handlers/
│   └── context_navigation_handlers.py        # Placeholder handler stubs
└── context_nav/
    ├── __init__.py
    ├── schemas.py                             # Pydantic models
    └── related_expansion.py                   # Placeholder query functions
```

### Frontend Placeholders

```
apps/web/src/
├── lib/
│   └── context-nav/
│       ├── types.ts                           # Core types
│       ├── navigation-context.ts              # Placeholder class
│       ├── view-stack.ts                      # Placeholder class
│       └── related-client.ts                  # Placeholder API client
├── contexts/
│   └── NavigationContext.tsx                  # Placeholder provider
├── hooks/
│   ├── useViewStack.ts                        # Placeholder hook
│   └── useRelated.ts                          # Placeholder hook
└── components/
    └── context-nav/
        ├── ViewerHeader.tsx                   # Placeholder component
        ├── RelatedPanel.tsx                   # Placeholder component
        └── AddRelatedButton.tsx               # Placeholder button
```

### Database Placeholders

```
supabase/migrations/
└── 00000000000022_context_navigation_tables.sql  # Empty migration (commented SQL)
```

**Placeholder Content**: Each file will contain:
- JSDoc/docstring explaining purpose
- Type definitions only (no logic)
- `// TODO: Implement in Phase 3` comments
- Exports to prevent import errors

---

## NEXT STEPS (Awaiting User Approval)

### Phase 2: MAP (If Approved)
1. Trace exact data flow from search click → artifact viewer
2. Map all artifact types (fault, work_order, document, etc.)
3. Identify all existing permission/RBAC logic
4. Document API contracts in detail

### Phase 3: DESIGN (If Approved)
1. Finalize database schema
2. Design deterministic related queries per domain
3. Design state machine transitions
4. Create wire

frames for UI components

### Phase 4: IMPLEMENT (If Approved)
1. Execute migrations
2. Implement backend routes + handlers
3. Implement frontend hooks + components
4. Wire up integrations

### Phase 5: TEST (If Approved)
1. Unit tests for deterministic queries
2. Integration tests for API contracts
3. E2E tests matching `/examples/*.md` scenarios
4. Manual verification against acceptance tests

### Phase 6: REPORT & PR (If Approved)
1. Document changes
2. Create GitHub PR to main
3. Request code review
4. Address feedback

---

## CRITICAL QUESTIONS FOR USER

1. **Docker Setup**: No `docker-compose.yml` found. How do you currently run the app locally?
   - Option A: `npm run dev` for web + `uvicorn` for API?
   - Option B: Deployed only (Vercel + Render)?
   - Option C: Different setup?

2. **Migration Numbering**: Next migration is `00000000000022_*`. Should I use this number or wait for email migration to be committed first?

3. **Search Integration Point**: Where exactly does search result click happen? Need to trace `<SpotlightSearch />` component.

4. **Existing Viewer Integration**: Do artifact viewers (FaultCard, WorkOrderCard) already have a shared layout/wrapper, or is each standalone?

5. **Testing Requirements**: Should I write tests in parallel with implementation (TDD) or after?

---

## PHASE 1 COMPLETION CHECKLIST

- ✅ Read all specification documents (00_foundation → 80_validation)
- ✅ Read `env vars.md` and noted credentials
- ✅ Inspected repo structure (apps/web, apps/api, supabase)
- ✅ Created feature branch `feature/situational-continuity-mvp`
- ✅ Mapped existing infrastructure (situations, search, viewers)
- ✅ Identified naming conflict (existing situation engine)
- ✅ Produced implementation plan (file-level detail)
- ✅ Assessed conflict risk with other developer (Outlook integration)
- ✅ Documented local run commands (partial - Docker missing)
- ⏳ Create placeholder files (next step)
- ⏳ Test local build (awaiting placeholders + Docker clarity)

---

**STOP HERE**. Awaiting user approval and answers to critical questions before proceeding to placeholder file creation and Phase 2.
