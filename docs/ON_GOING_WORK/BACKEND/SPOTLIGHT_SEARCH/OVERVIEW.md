# Spotlight Search — Actionable UX Unification

**Milestone:** v1.3
**Status:** ✅ COMPLETE (95% → Verification Phase)
**Last Updated:** 2026-03-03 (Phase 19 Wave 4 complete)

> ✅ **ALL PHASES COMPLETE:** Phases 15-19 finished. GAP-006 fixed. Agent deployment done. E2E tests created.

---

## Project Goal

Unify NLP intent into deterministic **READ** navigation and **MUTATE** actions with prefill preview.

```
User Query
    ↓
┌─────────────────────────────────────────────────────────┐
│                   IntentEnvelope                        │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │
│  │ mode: READ  │ or │mode: MUTATE │ or │ mode: MIXED │ │
│  └─────────────┘    └─────────────┘    └─────────────┘ │
│                                                         │
│  lens: work_order | fault | inventory | equipment | ... │
│  entities: { equipment: "ME1", priority: "urgent" }     │
│  readiness_state: READY | NEEDS_INPUT | BLOCKED         │
└─────────────────────────────────────────────────────────┘
    ↓                           ↓
READ → Navigate to             MUTATE → Action execution
       /work-orders/status/open        with prefill preview
```

---

## Action Button Architecture (THREE Systems)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  User Query                                                                  │
└─────────────────┬───────────────────────────────────────────────────────────┘
                  │
     ┌────────────┴────────────┐
     │                         │
     ▼                         ▼
┌─────────────┐         ┌─────────────┐
│ READ Query  │         │ MUTATE Query│
│ "engine"    │         │ "create WO" │
└──────┬──────┘         └──────┬──────┘
       │                       │
       │                       ▼
       │                ┌──────────────────┐
       │                │ SuggestedActions │
       │                │ (SpotlightSearch)│
       │                │ ✅ 14 buttons    │
       │                └──────────────────┘
       │ Click result
       ▼
┌──────────────────────────────────────────┐
│ FRAGMENTED ROUTES (Production Default)   │
│                                          │
│  /work-orders/{id} → ⚠️ 2/5 buttons     │
│  /faults/{id}      → ⚠️ 2/5 buttons     │
│  /equipment/{id}   → ⚠️ 2/3 buttons     │
│                                          │
│  GAP-006: Missing most action buttons!   │
└──────────────────────────────────────────┘
       │
       │ (flag OFF or unsupported type)
       ▼
┌──────────────────────────────────────────┐
│ CONTEXT PANEL (Legacy Path)              │
│                                          │
│  LensRenderer → *LensContent.tsx         │
│  ✅ Full action buttons with testids     │
└──────────────────────────────────────────┘
```

| System | Location | Status | TestIDs |
|--------|----------|--------|---------|
| **SuggestedActions** | SpotlightSearch.tsx | ✅ Working | `suggested-actions`, `action-btn-*` |
| **Fragmented Routes** | `/work-orders/[id]`, etc. | ⚠️ INCOMPLETE | ❌ Missing |
| **Lens Content** | `*LensContent.tsx` | ✅ Working | `acknowledge-fault-btn`, etc. |

---

## Architecture

### Core Components

| Component | Location | Purpose |
|-----------|----------|---------|
| **IntentEnvelope** | `useCelesteSearch.ts` | Captures query intent (READ/MUTATE/MIXED) |
| **/prepare endpoint** | `action_router/router.py` | Returns prefill preview with confidence |
| **deriveReadinessFromPrefill** | `useCelesteSearch.ts` | Classifies READY/NEEDS_INPUT/BLOCKED |
| **ReadinessIndicator** | `SuggestedActions.tsx` | Visual state indicators |
| **ActionModal** | `ActionModal.tsx` | Prefill display + disambiguation UI |

### Data Flow

```
1. User types query in SpotlightSearch
    ↓
2. useCelesteSearch derives IntentEnvelope
    ↓
3. If MUTATE intent detected:
    ↓
4. Debounced call to /v1/actions/prepare (400ms)
    ↓
5. PrepareResponse returns:
   - prefill: { field: { value, confidence, source } }
   - missing_required_fields: []
   - ambiguities: []
   - role_blocked: boolean
    ↓
6. deriveReadinessFromPrefill() classifies state
    ↓
7. SuggestedActions shows visual indicator
    ↓
8. User clicks → ActionModal opens with prefilled form
```

---

## Progress Summary

| Phase | Name | Status | Plans |
|-------|------|--------|-------|
| 15 | Intent Envelope | ✓ Complete | 1/1 |
| 16 | Prefill Integration | ✓ Complete | 2/2 |
| 16.1 | Mount /prepare endpoint | ✓ Complete | 1/1 |
| 17 | Readiness States | ✓ Complete | 2/2 |
| 18 | Route & Disambiguation | ○ Pending | 0/? |
| 19 | Agent Deployment | ○ Pending | 0/? |

---

## Key Files

### Frontend (apps/web/src)

| File | What It Does |
|------|--------------|
| `hooks/useCelesteSearch.ts` | IntentEnvelope type, deriveIntentEnvelope(), deriveReadinessFromPrefill(), prefill API integration |
| `lib/actionClient.ts` | prepareAction() API client, PrepareResponse type |
| `components/SuggestedActions.tsx` | ReadinessIndicator component, visual state display |
| `components/ActionModal.tsx` | Prefill form initialization, confidence badges, disambiguation UI |

### Backend (apps/api)

| File | What It Does |
|------|--------------|
| `routes/p0_actions_routes.py` | /v1/actions/prepare endpoint (Phase 16.1 fix) |
| `action_router/router.py` | Action execution, role gating |
| `common/prefill_engine.py` | build_prepare_response(), priority mapping |
| `common/temporal_parser.py` | Natural language date parsing |
| `pipeline_service.py` | Main app, mounts p0_actions_router |

---

## Requirements Coverage

| ID | Requirement | Phase | Status |
|----|-------------|-------|--------|
| INTENT-01 | IntentEnvelope type definition | 15 | ✓ |
| INTENT-02 | deriveIntentEnvelope function | 15 | ✓ |
| INTENT-03 | Deterministic output verification | 15 | ✓ |
| PREFILL-01 | /prepare endpoint exists | 16 | ✓ |
| PREFILL-02 | PrepareResponse with prefill dict | 16 | ✓ |
| PREFILL-03 | Entity resolution (yacht-scoped) | 16 | ✓ |
| PREFILL-04 | Priority synonym mapping | 16 | ✓ |
| PREFILL-05 | Temporal phrase parsing | 16 | ✓ |
| READY-01 | READY state classification | 17 | ✓ |
| READY-02 | NEEDS_INPUT state classification | 17 | ✓ |
| READY-03 | BLOCKED state classification | 17 | ✓ |
| READY-04 | Visual readiness indicators | 17 | ✓ |
| ROUTE-01 | Fragmented URLs for READ | 18 | ○ |
| ROUTE-02 | Filter chips in SpotlightSearch | 18 | ○ |
| ROUTE-03 | Canonical route generation | 18 | ○ |
| DISAMB-01 | Ambiguous entity dropdown | 18 | ○ |
| DISAMB-02 | Low confidence field highlighting | 18 | ○ |
| DISAMB-03 | No silent assumptions | 18 | ○ |
| AGENT-01 | Lens Matrix agents | 19 | ○ |
| AGENT-02 | NLP Variant agents | 19 | ○ |
| AGENT-03 | Backend Integration agents | 19 | ○ |
| AGENT-04 | E2E Test agents | 19 | ○ |

---

## Guardrails (Non-Negotiable)

1. **No new random files** — modify existing: useCelesteSearch.ts, SuggestedActions.tsx, ActionModal.tsx, prefill_engine.py
2. **Single canonical contracts** — ActionSuggestion conforms to defined interface
3. **Determinism first** — same query → same structured output
4. **No duplicate inference systems** — use existing Action Detector + Entity Extractor
5. **100% yacht isolation** — all entity lookups scoped by yacht_id
6. **Explicit role gating** — RLS + backend checks on all mutations
7. **Surface uncertainty** — never silently assume, always show ambiguity to user

---

## Agent Onboarding

**For new Claude agents:** Paste `AGENT-ONBOARDING.md` first. It contains:
- 4-mode framework
- Project context
- Current phase status
- Task templates
- Example tasks

---

## Quick Commands

```bash
# Check project status
/gsd:progress

# Plan next phase
/gsd:plan-phase 16.1

# Execute phase
/gsd:execute-phase 17

# Verify work
/gsd:verify-work

# Search patterns in Ruflo memory
npx ruflo memory search --query "readiness states"
```

---

*See also: PHASES-COMPLETE.md, PHASES-REMAINING.md, GAPS.md*
