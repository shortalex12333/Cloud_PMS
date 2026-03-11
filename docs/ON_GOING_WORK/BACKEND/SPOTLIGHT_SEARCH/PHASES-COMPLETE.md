# Completed Phases — Spotlight Search v1.3

**Last Updated:** 2026-03-03 (Phase 19 Wave 4 complete)

---

## Phase 15: Intent Envelope ✓

**Completed:** 2026-03-01
**Duration:** ~300s
**Plans:** 1/1

### What Was Built

| Component | Location | Purpose |
|-----------|----------|---------|
| `IntentEnvelope` type | useCelesteSearch.ts | Captures READ/MUTATE/MIXED mode |
| `IntentMode` enum | useCelesteSearch.ts | READ \| MUTATE \| MIXED |
| `IntentAction` type | useCelesteSearch.ts | Action with confidence score |
| `deriveIntentEnvelope()` | useCelesteSearch.ts | Derives envelope from search state |
| `djb2()` hash function | useCelesteSearch.ts | Deterministic query hashing |

### Key Code

```typescript
// IntentEnvelope type (useCelesteSearch.ts)
export interface IntentEnvelope {
  query: string;
  query_hash: string;           // djb2 hash for determinism
  mode: IntentMode;             // READ | MUTATE | MIXED
  lens: string | null;
  filters: Record<string, string>;
  entities: Record<string, string>;
  actions: IntentAction[];
  readiness_state: ReadinessState;
  timestamp: string;
}
```

### Commits

| Hash | Description |
|------|-------------|
| `33cdc7e3` | Define IntentEnvelope type + supporting types |
| `9d4c9271` | Implement deriveIntentEnvelope with djb2 hashing |
| `72ad52d4` | Integrate intentEnvelope into useCelesteSearch hook |

### Requirements Completed

- [x] INTENT-01: IntentEnvelope type definition
- [x] INTENT-02: deriveIntentEnvelope function
- [x] INTENT-03: Deterministic output verification

---

## Phase 16: Prefill Integration ✓

**Completed:** 2026-03-01
**Duration:** ~545s (Plan 01: 305s, Plan 02: 240s)
**Plans:** 2/2

### Plan 16-01: Backend

| Component | Location | Purpose |
|-----------|----------|---------|
| `temporal_parser.py` | apps/api/common/ | Natural language date parsing |
| `TemporalResult` | temporal_parser.py | ISO date + confidence + assumption |
| `PRIORITY_SYNONYMS` | prefill_engine.py | urgent→HIGH, critical→EMERGENCY |
| `map_priority()` | prefill_engine.py | Priority synonym mapping |
| `build_prepare_response()` | prefill_engine.py | Builds full prefill preview |
| `prepare_action()` | router.py | /v1/actions/prepare endpoint |

**Temporal Parsing Examples:**

| Input | Output | Confidence |
|-------|--------|------------|
| "tomorrow" | +1 day ISO | 0.95 |
| "next week" | Monday of NEXT week | 0.85 |
| "next tuesday" | Actual Tuesday date | 0.90 |
| "in 3 days" | +3 days ISO | 0.95 |
| "urgent" | None (not temporal) | N/A |

**Priority Mapping:**

| Synonym | Maps To | Confidence |
|---------|---------|------------|
| urgent | HIGH | 0.95 |
| critical | EMERGENCY | 0.95 |
| asap | HIGH | 0.95 |
| high | HIGH | 0.95 |
| medium | MEDIUM | 0.95 |
| low | LOW | 0.95 |

**Commits:**

| Hash | Description |
|------|-------------|
| `2f9ed7e0` | Create temporal_parser.py with timezone-aware parsing |
| `05173506` | Add priority mapping and build_prepare_response |
| `1819bbaa` | Add /v1/actions/prepare endpoint to router |

**Tests:** 19 passing (9 temporal + 10 priority)

---

### Plan 16-02: Frontend

| Component | Location | Purpose |
|-----------|----------|---------|
| `prepareAction()` | actionClient.ts | API client for /prepare |
| `PrepareResponse` type | actionClient.ts | TypeScript interface |
| `PREPARE_DEBOUNCE_MS` | useCelesteSearch.ts | 400ms debounce constant |
| `PREPARE_CACHE_TTL` | useCelesteSearch.ts | 30s cache constant |
| `fetchPrefillData()` | useCelesteSearch.ts | Debounced API call |
| Confidence badges | ActionModal.tsx | Green/amber visual indicators |
| Disambiguation UI | ActionModal.tsx | "Did you mean" dropdown |

**Key Constants:**

```typescript
const PREPARE_DEBOUNCE_MS = 400;  // Debounce delay
const PREPARE_CACHE_TTL = 30000;  // 30s cache
const CONFIDENCE_GATE = 0.65;     // Min confidence to prefill
```

**Confidence Thresholds:**

| Range | Color | Badge |
|-------|-------|-------|
| >= 0.85 | Green | "auto-filled" |
| 0.65-0.84 | Amber | "confirm" |
| < 0.65 | — | Field not prefilled |

**Commits:**

| Hash | Description |
|------|-------------|
| `45331d65` | Add prepareAction API call to actionClient |
| `1e6514fa` | Add prefill integration to useCelesteSearch |
| `8e4b1bea` | Initialize ActionModal from prefill data |

**Known Gap:** B4 user edit protection missing (tracked for follow-up)

---

### Requirements Completed (Phase 16)

- [x] PREFILL-01: /prepare endpoint exists
- [x] PREFILL-02: PrepareResponse with prefill dict
- [x] PREFILL-03: Entity resolution (yacht-scoped)
- [x] PREFILL-04: Priority synonym mapping
- [x] PREFILL-05: Temporal phrase parsing

---

## Phase 16.1: Mount /prepare Endpoint ✓

**Completed:** 2026-03-02
**Duration:** ~25 minutes
**Plans:** 1/1
**Type:** Urgent gap closure (GAP-001)

### The Problem (Resolved)

`/v1/actions/prepare` endpoint code existed in `action_router/router.py:1248` but the router was **NOT mounted** in `pipeline_service.py`.

### The Solution Applied

Moved `/prepare` endpoint to `p0_actions_routes.py` (Option B).

| Component | Location | Purpose |
|-----------|----------|---------|
| Model imports | p0_actions_routes.py:51-60 | PrepareRequest, PrepareResponse, etc. |
| `build_prepare_response` import | p0_actions_routes.py:60 | Prefill engine function |
| `/prepare` endpoint | p0_actions_routes.py:532-750 | Full endpoint with JWT/tenant/role validation |

### Key Code

```python
# p0_actions_routes.py - IMPORTS ADDED
from action_router.router import (
    PrepareRequest, PrepareResponse, PrefillField,
    AmbiguityCandidate, Ambiguity, PrepareError,
)
from common.prefill_engine import build_prepare_response

# p0_actions_routes.py - ENDPOINT ADDED
@router.post("/prepare", response_model=PrepareResponse)
async def prepare_action(
    request_data: PrepareRequest,
    authorization: str = Header(None),
) -> PrepareResponse:
    # Full implementation: JWT → tenant → yacht isolation → domain → role gating → prefill
    ...
```

### Verification Results

| Check | Result |
|-------|--------|
| Docker build | ✅ SUCCESS |
| Health check | ✅ `{"status":"healthy"}` |
| OpenAPI registration | ✅ `/v1/actions/prepare` present |
| Curl test | ✅ Returns 401 (not 404) |

**Before:** `404 Not Found`
**After:** `{"status":"error","error_code":"missing_token","message":"Authorization token is required"}`

### Commits

| Hash | Description |
|------|-------------|
| (pending) | fix(16.1-01): mount /prepare endpoint in p0_actions_routes |

### Requirements Completed

- [x] GAP-001: /prepare endpoint accessible
- [x] GAP-003: Route registration logged (auto-resolved)
- [x] GAP-004: OpenAPI documentation present (auto-resolved)

### Lesson Learned

**FastAPI Router Not Mounted = 404**

Endpoint code existing ≠ endpoint accessible. Always verify:
1. Router is mounted in main app (`pipeline_service.py`)
2. OpenAPI schema includes the endpoint
3. Don't mount conflicting routers — re-export instead

---

## Phase 17: Readiness States ✓

**Completed:** 2026-03-02
**Plans:** 2/2 complete

### Plan 17-01: Complete ✓

| Component | Location | Purpose |
|-----------|----------|---------|
| `role_blocked` field | router.py PrepareResponse | Indicates role gating block |
| `blocked_reason` field | router.py PrepareResponse | Human-readable block reason |
| `role_blocked` type | actionClient.ts | TypeScript interface update |
| `deriveReadinessFromPrefill()` | useCelesteSearch.ts | Classifies READY/NEEDS_INPUT/BLOCKED |

**Readiness Classification Logic:**

```typescript
export function deriveReadinessFromPrefill(
  prefillData: PrepareResponse | null,
  actionSuggestion?: ActionSuggestion
): ReadinessState {
  if (!prefillData) return 'NEEDS_INPUT';
  if (prefillData.role_blocked) return 'BLOCKED';

  const READY_CONFIDENCE_THRESHOLD = 0.8;

  if (prefillData.missing_required_fields?.length > 0) return 'NEEDS_INPUT';

  for (const [fieldName, field] of Object.entries(prefillData.prefill || {})) {
    if (field.confidence < READY_CONFIDENCE_THRESHOLD) return 'NEEDS_INPUT';
  }

  if (prefillData.ambiguities?.length > 0) return 'NEEDS_INPUT';

  return 'READY';
}
```

**Commits:**

| Hash | Description |
|------|-------------|
| `2d02db83` | Add role_blocked field to PrepareResponse |
| `0d237a32` | Update frontend PrepareResponse type |
| `2fef1ebd` | Implement deriveReadinessFromPrefill |
| `4f34cae5` | Complete readiness states plan |

---

### Plan 17-02: Complete ✓

| Component | Location | Purpose |
|-----------|----------|---------|
| `ReadinessIndicator` | SuggestedActions.tsx | Visual state component |
| `readinessStates` prop | SuggestedActions.tsx | State map from hook |
| Button styling | SuggestedActions.tsx | Disabled state for BLOCKED |

**ReadinessIndicator Component:**

```typescript
function ReadinessIndicator({ state }: { state: ReadinessState | undefined }) {
  switch (state) {
    case 'READY':
      return <Check className="w-3.5 h-3.5 text-emerald-400" />;
    case 'NEEDS_INPUT':
      return <Circle className="w-2.5 h-2.5 fill-amber-400 text-amber-400" />;
    case 'BLOCKED':
      return <Lock className="w-3.5 h-3.5 text-red-400" />;
    default:
      return <Circle className="w-2.5 h-2.5 fill-amber-400/50" />;
  }
}
```

**Commits (so far):**

| Hash | Description |
|------|-------------|
| `2705cc34` | Add visual readiness indicators to SuggestedActions |
| `520dce4a` | Wire readiness states from useCelesteSearch |

**Completed:** Visual indicators verified and working

---

### Requirements Status (Phase 17)

- [x] READY-01: READY state classification (confidence >= 0.8)
- [x] READY-02: NEEDS_INPUT state classification
- [x] READY-03: BLOCKED state classification (role_blocked)
- [x] READY-04: Visual readiness indicators (complete)

---

## Commit History (All Phases)

```
520dce4a feat(17-02): wire readiness states from useCelesteSearch
2705cc34 feat(17-02): add visual readiness indicators to SuggestedActions
4f34cae5 docs(17-01): complete readiness states plan
2fef1ebd feat(17-01): implement deriveReadinessFromPrefill function
0d237a32 feat(17-01): update frontend PrepareResponse type with role_blocked
2d02db83 feat(17-01): add role_blocked field to PrepareResponse
342ebafe docs(16-02): complete prefill integration frontend plan
8e4b1bea feat(16-02): initialize ActionModal from prefill data
1e6514fa feat(16-02): add prefill integration to useCelesteSearch
45331d65 feat(16-02): add prepareAction API call to actionClient
0e1376fa docs(16-01): complete prefill integration backend plan
1819bbaa feat(16-01): add /v1/actions/prepare endpoint to action_router
05173506 feat(16-01): add priority mapping and build_prepare_response
2f9ed7e0 feat(16-01): create temporal_parser with timezone-aware parsing
72ad52d4 feat(15-01): integrate intentEnvelope into useCelesteSearch
9d4c9271 feat(15-01): implement deriveIntentEnvelope with djb2 hashing
33cdc7e3 feat(15-01): define IntentEnvelope type and supporting types
```

---

## Phase 17.1: Fragmented Route Action Buttons ✓

**Completed:** 2026-03-03
**Duration:** ~2 hours
**Type:** Gap closure (GAP-006)

### What Was Built

Added full action buttons to all fragmented route pages with proper testids and RBAC.

| Page | Action Buttons Added | TestIDs |
|------|---------------------|---------|
| `/faults/[id]` | 5 | `acknowledge-fault-btn`, `close-fault-btn`, `reopen-fault-btn`, `false-alarm-btn`, `create-wo-button` |
| `/work-orders/[id]` | 5 | `add-note-btn`, `mark-complete-btn`, `add-hours-btn`, `reassign-btn`, `edit-wo-btn` |
| `/equipment/[id]` | 3+ | `update-status-button`, `flag-attention-button`, `report-fault-btn` |

### Files Modified

| File | Changes |
|------|---------|
| `app/faults/[id]/page.tsx` | Added action buttons with useFaultActions, useFaultPermissions hooks |
| `app/work-orders/[id]/page.tsx` | Added action buttons with useWorkOrderActions hooks |
| `app/equipment/[id]/page.tsx` | Added action buttons with useEquipmentActions hooks |
| `hooks/useFaultActions.ts` | Created fault action hooks |
| `hooks/useFaultPermissions.ts` | Created fault permission hooks |

### Requirements Completed

- [x] FRAG-01: Action button components extracted
- [x] FRAG-02: Work order actions (5 buttons)
- [x] FRAG-03: Fault actions (5 buttons)
- [x] FRAG-04: Equipment actions (3+ buttons)
- [x] FRAG-05: TestID consistency
- [x] FRAG-06: RBAC consistency

---

## Phase 18: Route & Disambiguation ✓

**Completed:** 2026-03-03
**Duration:** ~3 hours
**Plans:** 3/3 complete

### What Was Built

| Component | Location | Purpose |
|-----------|----------|---------|
| `generateCanonicalRoute()` | useCelesteSearch.ts | Generate segment-based URLs |
| Filter chips | SpotlightSearch.tsx | Visual route segment display |
| Disambiguation UI | ActionModal.tsx | "Did you mean" dropdown |

### Requirements Completed

- [x] ROUTE-01: Fragmented URLs (`/work-orders/status/open`)
- [x] ROUTE-02: Filter chips display
- [x] ROUTE-03: Canonical route generation
- [x] DISAMB-01: Ambiguous entity dropdown
- [x] DISAMB-02: Low confidence highlighting
- [x] DISAMB-03: No silent assumptions

---

## Phase 19: Agent Deployment ✓

**Completed:** 2026-03-03
**Duration:** ~4 hours
**Waves:** 4/4 complete

### Wave 1: Lens Matrix Analysis ✓

**Agents:** 6 lens analyzers
**Output:** Updated `lens_matrix.json`

| Lens | READ Filters | MUTATE Actions |
|------|--------------|----------------|
| work_order | 12 | 11 |
| fault | 9 | 10 |
| equipment | 10 | 10 |
| part | 10 | 7 |
| certificate | 12 | 5 |
| document | 12 | 4 |
| **Total** | **63** | **47** |

**Key Discovery:** System has 12 lenses with 81 total actions (more than originally documented).

### Wave 2: NLP Variant Generation ✓

**Agents:** 6 variant generators
**Output:** ~360 NLP query variants

| Lens | Variants Generated |
|------|-------------------|
| work_order | 88 (8 per 11 actions) |
| fault | 64 |
| equipment | ~70 |
| part | 56 |
| certificate | ~50 |
| document | 32 |

### Wave 3: Backend Integration Verification ✓

**Agents:** 4 verification agents
**Output:** Audit reports

| Check | Result |
|-------|--------|
| Yacht Isolation | ✅ PASS - 4-layer defense verified |
| RBAC Compliance | ⚠️ 6 mismatches found (GAP-007) |
| Prefill Engine | ✅ PASS - 80% priority coverage |
| Temporal Parser | ⚠️ Edge cases fail (GAP-008) |

### Wave 4: E2E Test Creation ✓

**Agents:** 4 test generators
**Output:** ~60 E2E tests

| Test Suite | Tests Created |
|------------|---------------|
| `spotlight-intent-detection.spec.ts` | ~15 |
| `role-based-actions.spec.ts` | 15 |
| `prefill-extraction.spec.ts` | 18 |
| `error-states.spec.ts` | 12 |

### Requirements Completed

- [x] AGENT-01: Lens Matrix (12 lenses, 81 actions)
- [x] AGENT-02: NLP Variants (~360 variants)
- [x] AGENT-03: Backend Integration (yacht isolation verified)
- [x] AGENT-04: E2E Tests (~60 tests created)

---

## Complete Commit History (All Phases)

```
# Phase 19 (2026-03-03)
Wave 4: E2E test creation complete
Wave 3: Backend verification complete
Wave 2: NLP variant generation complete
Wave 1: Lens matrix analysis complete

# Phase 18 (2026-03-03)
feat(18-03): enhanced disambiguation UI in ActionModal
feat(18-02): add filter chips to SpotlightSearch
feat(18-01): implement generateCanonicalRoute function

# Phase 17.1 (2026-03-03)
feat(17.1): add full action buttons to fragmented route pages
feat(17.1): create useFaultActions and useFaultPermissions hooks

# Phase 17 (2026-03-02)
520dce4a feat(17-02): wire readiness states from useCelesteSearch
2705cc34 feat(17-02): add visual readiness indicators to SuggestedActions
4f34cae5 docs(17-01): complete readiness states plan
2fef1ebd feat(17-01): implement deriveReadinessFromPrefill function
0d237a32 feat(17-01): update frontend PrepareResponse type with role_blocked
2d02db83 feat(17-01): add role_blocked field to PrepareResponse

# Phase 16.1 (2026-03-02)
fix(16.1-01): mount /prepare endpoint in p0_actions_routes

# Phase 16 (2026-03-01)
342ebafe docs(16-02): complete prefill integration frontend plan
8e4b1bea feat(16-02): initialize ActionModal from prefill data
1e6514fa feat(16-02): add prefill integration to useCelesteSearch
45331d65 feat(16-02): add prepareAction API call to actionClient
0e1376fa docs(16-01): complete prefill integration backend plan
1819bbaa feat(16-01): add /v1/actions/prepare endpoint to action_router
05173506 feat(16-01): add priority mapping and build_prepare_response
2f9ed7e0 feat(16-01): create temporal_parser with timezone-aware parsing

# Phase 15 (2026-03-01)
72ad52d4 feat(15-01): integrate intentEnvelope into useCelesteSearch
9d4c9271 feat(15-01): implement deriveIntentEnvelope with djb2 hashing
33cdc7e3 feat(15-01): define IntentEnvelope type and supporting types
```

---

*See also: OVERVIEW.md, PHASES-REMAINING.md, GAPS.md*
