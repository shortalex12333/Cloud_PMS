# Quick Reference — Spotlight Search v1.3

**Last Updated:** 2026-03-03
**Progress:** ✅ 95% complete (Verification Phase)

---

## Current Status

```
Phase 15 ✓ → Phase 16 ✓ → Phase 16.1 ✓ → Phase 17 ✓ → Phase 17.1 ✓ → Phase 18 ✓ → Phase 19 ✓ → VERIFICATION
                                                                                                    ↓
                                                                                               E2E TESTS
```

**Next Action:** Run E2E tests to verify all functionality

> ✅ **ALL PHASES COMPLETE:** Phases 15-19 finished. GAP-006 fixed. ~60 E2E tests created.

---

## Action Button Architecture (THREE Systems)

| System | Location | Status | TestIDs |
|--------|----------|--------|---------|
| **SuggestedActions** | `SpotlightSearch.tsx` | ✅ Working | `suggested-actions`, `action-btn-*` |
| **Fragmented Routes** | `/work-orders/[id]`, `/faults/[id]`, `/equipment/[id]` | ⚠️ **INCOMPLETE** | ❌ Missing |
| **Lens Content** | `*LensContent.tsx` | ✅ Working | `acknowledge-fault-btn`, etc. |

### Action Button TestIDs (Lens Components)

```typescript
// FaultLensContent.tsx
'acknowledge-fault-btn', 'close-fault-btn', 'reopen-fault-btn', 'false-alarm-btn', 'add-note-btn'

// EquipmentLensContent.tsx
'update-status-button', 'flag-attention-button', 'decommission-button'

// WorkOrderLensContent.tsx
'add-note-btn', 'mark-complete-btn', 'add-hours-btn', 'reassign-btn', 'edit-wo-btn'
```

---

## Key Files

### Frontend (apps/web/src)

| File | Key Functions |
|------|---------------|
| `hooks/useCelesteSearch.ts` | `IntentEnvelope`, `deriveIntentEnvelope()`, `deriveReadinessFromPrefill()` |
| `lib/actionClient.ts` | `prepareAction()`, `PrepareResponse` |
| `components/SuggestedActions.tsx` | `ReadinessIndicator`, action buttons for MUTATE queries |
| `components/ActionModal.tsx` | Prefill display, confidence badges |
| `components/SpotlightSearch.tsx` | Fragmented routes navigation (lines 576-612) |
| `components/lens/FaultLensContent.tsx` | Full fault action buttons ✅ |
| `components/lens/EquipmentLensContent.tsx` | Full equipment action buttons ✅ |
| `components/lens/WorkOrderLensContent.tsx` | Full work order action buttons ✅ |
| `app/work-orders/[id]/page.tsx` | ✅ Full action buttons |
| `app/faults/[id]/page.tsx` | ✅ Full action buttons |
| `app/equipment/[id]/page.tsx` | ✅ Full action buttons |

### Backend (apps/api)

| File | Key Functions |
|------|---------------|
| `routes/p0_actions_routes.py` | `/prepare` endpoint ✅ (GAP-001 FIXED) |
| `common/prefill_engine.py` | `build_prepare_response()`, `map_priority()` |
| `common/temporal_parser.py` | `parse_temporal_phrase()` |
| `pipeline_service.py` | Main FastAPI app |

---

## GSD Commands

```bash
# Check progress
/gsd:progress

# Plan a phase
/gsd:plan-phase 16.1

# Execute a phase
/gsd:execute-phase 17

# Verify work
/gsd:verify-work

# Insert urgent phase
/gsd:insert-phase 16 "description"

# Debug mode
/gsd:debug
```

---

## Ruflo Commands

```bash
# Memory operations
npx ruflo memory store --key "key" --value "value" --namespace "patterns"
npx ruflo memory search --query "readiness states" --namespace "patterns"
npx ruflo memory list --namespace "patterns"

# Swarm operations
npx ruflo swarm init --topology hierarchical --max-agents 8
npx ruflo agent spawn --type coder --name my-agent

# Hooks
npx ruflo hooks route --task "fix prepare endpoint"
npx ruflo hooks metrics --period 24h
```

---

## Docker Commands

```bash
# Start API locally
docker compose -f docker-compose.local.yml up api -d

# Check health
curl http://localhost:8000/health

# View logs
docker logs -f back_button_cloud_pms-api-1

# Stop
docker compose -f docker-compose.local.yml down
```

---

## Type Definitions

### IntentEnvelope

```typescript
interface IntentEnvelope {
  query: string;
  query_hash: string;
  mode: 'READ' | 'MUTATE' | 'MIXED';
  lens: string | null;
  filters: Record<string, string>;
  entities: Record<string, string>;
  actions: IntentAction[];
  readiness_state: 'READY' | 'NEEDS_INPUT' | 'BLOCKED';
  timestamp: string;
}
```

### PrepareResponse

```typescript
interface PrepareResponse {
  action_id: string;
  match_score: number;
  ready_to_commit: boolean;
  prefill: Record<string, PrefillField>;
  missing_required_fields: string[];
  ambiguities: Ambiguity[];
  errors: Array<{ error_code: string; message: string; field?: string }>;
  role_blocked?: boolean;
  blocked_reason?: string;
}
```

### PrefillField

```typescript
interface PrefillField {
  value: any;
  confidence: number;
  source: 'entity_resolver' | 'keyword_map' | 'temporal' | 'user_input';
}
```

### ReadinessState

```typescript
type ReadinessState = 'READY' | 'NEEDS_INPUT' | 'BLOCKED';
```

---

## Confidence Thresholds

| Threshold | Purpose |
|-----------|---------|
| `>= 0.8` | READY state classification |
| `>= 0.65` | Field prefill gate |
| `>= 0.85` | Green "auto-filled" badge |
| `0.65-0.84` | Amber "confirm" badge |
| `< 0.65` | Field not prefilled |

---

## Constants

```typescript
// useCelesteSearch.ts
const PREPARE_DEBOUNCE_MS = 400;
const PREPARE_CACHE_TTL = 30000;  // 30 seconds

// deriveReadinessFromPrefill
const READY_CONFIDENCE_THRESHOLD = 0.8;

// ActionModal
const CONFIDENCE_GATE = 0.65;
```

---

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/v1/actions/prepare` | Get prefill preview ✅ (MOUNTED) |
| POST | `/v1/actions/execute` | Execute action |
| GET | `/v1/actions/list` | List available actions |
| GET | `/v1/actions/suggestions` | Get action suggestions |
| GET | `/health` | Health check |

---

## Requirements Quick Reference

| Phase | Requirements | Status |
|-------|--------------|--------|
| 15 | INTENT-01, INTENT-02, INTENT-03 | ✅ Complete |
| 16 | PREFILL-01..05 | ✅ Complete |
| 16.1 | GAP-001 (mount /prepare) | ✅ Complete |
| 17 | READY-01..04 | ✅ Complete |
| 17.1 | FRAG-01..06 (GAP-006) | ✅ Complete |
| 18 | ROUTE-01..03, DISAMB-01..03 | ✅ Complete |
| 19 | AGENT-01..04 | ✅ Complete |

## E2E Test Suites Created

| Suite | Tests | Coverage |
|-------|-------|----------|
| `spotlight-intent-detection.spec.ts` | ~15 | MUTATE/READ routing |
| `role-based-actions.spec.ts` | 15 | RBAC button visibility |
| `prefill-extraction.spec.ts` | 18 | Entity/priority/temporal |
| `error-states.spec.ts` | 12 | Error handling |

---

## Commit Prefixes

| Prefix | Usage |
|--------|-------|
| `feat(NN-PP)` | Feature for phase NN plan PP |
| `fix(NN-PP)` | Bug fix for phase NN plan PP |
| `docs(NN-PP)` | Documentation for phase NN plan PP |
| `refactor(NN-PP)` | Refactor for phase NN plan PP |

Example: `feat(16-01): add temporal parsing to prefill_engine`

---

## Files in This Directory

| File | Purpose |
|------|---------|
| `OVERVIEW.md` | Project status and architecture |
| `PHASES-COMPLETE.md` | Detailed completed phase documentation |
| `PHASES-REMAINING.md` | Remaining phases and next steps |
| `GAPS.md` | Missing components and fixes |
| `DOCKER-TESTING.md` | Local testing setup |
| `QUICK-REFERENCE.md` | This file |

---

## Emergency Commands

```bash
# Something broke - check logs
docker logs back_button_cloud_pms-api-1 --tail 200

# API not responding - restart
docker compose -f docker-compose.local.yml restart api

# Need fresh start
docker compose -f docker-compose.local.yml down -v
docker compose -f docker-compose.local.yml up api -d --build

# Revert last commit
git revert HEAD
```

---

*See also: OVERVIEW.md, GAPS.md, DOCKER-TESTING.md*
