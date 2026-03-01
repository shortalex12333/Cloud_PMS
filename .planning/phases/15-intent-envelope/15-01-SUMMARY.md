---
phase: 15-intent-envelope
plan: 01
subsystem: ui
tags: [typescript, react, nlp, intent-detection, search]

# Dependency graph
requires:
  - phase: v1.2-search-snippets
    provides: useCelesteSearch hook foundation, ActionSuggestion type
provides:
  - IntentEnvelope TypeScript type for unified intent representation
  - deriveIntentEnvelope() function for deterministic intent extraction
  - intentEnvelope field exposed in useCelesteSearch hook return value
  - verifyEnvelopeDeterminism() utility for downstream verification
affects: [16-prefill-integration, 17-readiness-states, 18-route-disambiguation]

# Tech tracking
tech-stack:
  added: []
  patterns: [djb2 query hashing, deterministic intent derivation]

key-files:
  created: []
  modified:
    - apps/web/src/hooks/useCelesteSearch.ts

key-decisions:
  - "Used djb2 hash algorithm for deterministic query_hash (no crypto dependencies)"
  - "IntentMode has three states: READ, MUTATE, MIXED (supports combined intents)"
  - "ReadinessState uses confidence threshold of 0.8 for READY in MUTATE mode"
  - "ActionSuggestion.match_score maps to IntentAction.confidence"

patterns-established:
  - "Envelope derivation pattern: query + ActionSuggestion[] -> IntentEnvelope"
  - "Same query always produces same query_hash (determinism guarantee)"
  - "READ mode default for queries without detected action intent"

requirements-completed: [INTENT-01, INTENT-02, INTENT-03]

# Metrics
duration: 8min
completed: 2026-03-01
---

# Phase 15: Intent Envelope Summary

**IntentEnvelope TypeScript abstraction unifying READ navigation and MUTATE action intents with deterministic derivation from existing NLP modules**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-01T22:56:00Z
- **Completed:** 2026-03-01T23:04:00Z
- **Tasks:** 3
- **Files modified:** 1

## Accomplishments

- Defined IntentEnvelope type with 14 LensTypes, 3 IntentModes, and 3 ReadinessStates
- Implemented deriveIntentEnvelope() with deterministic hashing using djb2 algorithm
- Integrated envelope into useCelesteSearch hook state and return value
- Added verifyEnvelopeDeterminism() utility for downstream consumers

## Task Commits

Each task was committed atomically:

1. **Task 1: Define IntentEnvelope Type and Supporting Types** - `33cdc7e3` (feat)
2. **Task 2: Implement deriveIntentEnvelope Function with Deterministic Hashing** - `9d4c9271` (feat)
3. **Task 3: Integrate IntentEnvelope into Search State and Verify Determinism** - `72ad52d4` (feat)

## Files Created/Modified

- `apps/web/src/hooks/useCelesteSearch.ts` - Added IntentEnvelope types, deriveIntentEnvelope function, and hook integration (+337 lines)

## Types Added

```typescript
// Intent classification
type IntentMode = 'READ' | 'MUTATE' | 'MIXED';
type ReadinessState = 'READY' | 'NEEDS_INPUT' | 'BLOCKED';
type LensType = 'work_order' | 'fault' | 'equipment' | 'part' | 'certificate' |
                'handover' | 'hours_of_rest' | 'shopping_list' | 'receiving' |
                'document' | 'crew' | 'email' | 'warranty' | 'unknown';

// Entity and filter structures
interface ExtractedEntity { type, value, canonical, confidence }
interface IntentFilter { field, value, operator }
interface IntentAction { action_id, confidence, verb, matched_text }

// The unified envelope
interface IntentEnvelope {
  query, query_hash, timestamp,
  mode, lens, filters, action, entities,
  readiness_state, confidence, deterministic
}
```

## Helper Functions Added

- `hashQuery()` - djb2 deterministic hashing
- `inferLens()` - Maps query to CelesteOS domain lens
- `extractFilters()` - Extracts status/priority filters
- `extractEntities()` - Pattern matches equipment identifiers
- `inferMode()` - Determines READ/MUTATE/MIXED
- `inferReadiness()` - Determines READY/NEEDS_INPUT/BLOCKED
- `deriveIntentEnvelope()` - Main derivation function
- `verifyEnvelopeDeterminism()` - Equality check (excluding timestamp)

## Decisions Made

- Used djb2 hash algorithm for query_hash (no crypto dependencies, deterministic)
- IntentAction.confidence maps from ActionSuggestion.match_score
- READY state in MUTATE mode requires confidence >= 0.8 AND at least one entity
- READ mode is always READY (just navigation)
- Fallback to READ mode envelope on action suggestion fetch failure

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed ActionSuggestion type mismatch**
- **Found during:** Task 2 (deriveIntentEnvelope implementation)
- **Issue:** ActionSuggestion type has `match_score` not `confidence`, and no `entities` field
- **Fix:** Updated extractEntities to only use query pattern matching, updated deriveIntentEnvelope to use `match_score`
- **Files modified:** apps/web/src/hooks/useCelesteSearch.ts
- **Verification:** TypeScript compiles without errors
- **Committed in:** 9d4c9271 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Type correction necessary for compilation. No scope creep.

## Issues Encountered

None - TypeScript compilation clean after type correction.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- IntentEnvelope available via useCelesteSearch hook
- Ready for Phase 16: Prefill Integration
- Envelope can be passed to /v1/actions/prepare endpoint for form prefill
- verifyEnvelopeDeterminism() ready for test assertions

---
*Phase: 15-intent-envelope*
*Completed: 2026-03-01*

## Self-Check: PASSED

All claims verified:
- FOUND: apps/web/src/hooks/useCelesteSearch.ts
- FOUND: 33cdc7e3 (Task 1 commit)
- FOUND: 9d4c9271 (Task 2 commit)
- FOUND: 72ad52d4 (Task 3 commit)
