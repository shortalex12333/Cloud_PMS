# Part Lens v2 - Critical Architecture Gap
**Date**: 2026-01-30
**Status**: 🔴 CRITICAL - Actions on Top Pattern Not Implemented

---

## Executive Summary

Backend and frontend have all the pieces for Part Lens v2, but **they're not connected**. The "actions on top" pattern exists in backend endpoints but frontend doesn't integrate with them properly.

**Impact**: Users see generic action lists instead of context-aware, intent-driven suggestions.

---

## What Works ✅

1. **Backend Endpoints Exist**:
   - ✅ `/v1/parts/suggestions?part_id={id}` - Context-valid actions with stock filtering
   - ✅ `/v1/parts/receive/prefill` - Prepare data for receive_part
   - ✅ `/v1/parts/adjust-stock/prefill` - Prepare data for adjust_stock_quantity
   - ✅ Action registry with role-based filtering
   - ✅ Stock-based action gating (consume/write-off require on_hand > 0)

2. **Frontend Components Exist**:
   - ✅ Search with entity extraction
   - ✅ `SuggestedActions` component for action buttons
   - ✅ `useCelesteSearch` hook with action intent detection
   - ✅ Situation state management (CANDIDATE/ACTIVE)

3. **Backend Action Filtering**:
   - ✅ SIGNED actions (adjust_stock, write_off) → Captain/Manager only
   - ✅ MUTATE actions (consume, receive, transfer) → Chief Engineer+
   - ✅ Stock-based filtering (on_hand = 0 → hide consume/write-off)

---

## What's Broken ❌

### Issue 1: No Intent-Aware Rendering

**Current Behavior**:
```
User: "receive engine oil filter"
   ↓
Frontend: Searches for "receive engine oil filter"
   ↓
Backend: Returns Part #1234 (entity extraction works)
   ↓
Frontend: Shows generic actions from /v1/actions/list?domain=parts
   ↓
User sees: ALL part actions (receive, create, adjust, consume, etc.)
```

**Problem**: Frontend ignores the "receive" intent. Shows all actions instead of focusing on receive_part.

**Expected Behavior**:
```
User: "receive engine oil filter"
   ↓
Backend: Detects intent = "receive_part" (confidence: 0.85)
   ↓
Backend: Auto-calls prepare/prefill for receive_part
   ↓
Frontend: Renders focused "Receive Part" action with pre-filled form
   ↓
User sees: Modal/form for receive_part, other actions minimized
```

---

### Issue 2: Frontend Doesn't Call Entity-Specific Suggestions

**Current Behavior**:
```
User clicks: Part #1234 in search results
   ↓
Frontend: Opens situation viewer
   ↓
Frontend: Shows... nothing? Or generic /v1/actions/list actions
```

**Expected Behavior**:
```
User clicks: Part #1234 in search results
   ↓
Frontend: Calls GET /v1/parts/suggestions?part_id=1234
   ↓
Backend: Returns context-valid actions:
   - consume_part ✅ (on_hand > 0)
   - receive_part ✅
   - write_off_part ✅ (Captain role + on_hand > 0)
   - NO create_part ❌ (part exists)
   - NO adjust_stock ✅ (Chief Engineer doesn't have SIGNED permission)
   ↓
Frontend: Renders ONLY these context-valid action buttons
```

---

### Issue 3: Missing Intent Analysis in Search Response

**Current Search Response** (`/webhook/search`):
```json
{
  "success": true,
  "results": [
    {
      "id": "1234",
      "type": "part",
      "title": "Engine Oil Filter",
      "score": 0.95
    }
  ]
}
```

**Missing**: Intent analysis, confidence, trigger threshold

**Expected Search Response**:
```json
{
  "success": true,
  "results": [...],
  "intent": {
    "action": "receive_part",
    "confidence": 0.85,
    "trigger_threshold": 0.7,
    "should_focus": true,
    "entity_id": "1234"
  },
  "prefill_data": {
    "part_id": "1234",
    "part_name": "Engine Oil Filter",
    "current_quantity": 10,
    "default_location": "Engine Room"
  }
}
```

---

## Architectural Components

### Backend Modules Status

| Module | Endpoint | Status | Integration |
|--------|----------|--------|-------------|
| Intent Detection | N/A | ⚠️ Exists in code but not exposed | Missing API |
| Entity Extraction | `/webhook/search` | ✅ Working | Integrated |
| Context Suggestions | `/v1/parts/suggestions` | ✅ Implemented | Not called by UI |
| Prepare/Prefill | `/v1/parts/{action}/prefill` | ✅ Implemented | Not called by UI |
| Action Execution | `/v1/actions/execute` | ✅ Working | Integrated |

### Frontend Components Status

| Component | File | Status | Integration |
|-----------|------|--------|-------------|
| Search Input | `SpotlightSearch.tsx` | ✅ Working | Integrated |
| Intent Detection | `useCelesteSearch.ts` | ⚠️ Partial | Detects keywords but doesn't fetch suggestions |
| Action Buttons | `SuggestedActions.tsx` | ✅ Implemented | Only shows generic /v1/actions/list |
| Entity Viewer | `SituationRouter.tsx` | ⚠️ Partial | No part-specific viewer |
| Action Modal | `ActionModal.tsx` | ✅ Working | Integrated |

---

## Required Changes

### Backend Changes

#### 1. Add Intent Analysis to Search Response
**File**: `apps/api/routes/search_routes.py` (or webhook handler)

**Change**:
```python
# After entity extraction
intent = detect_action_intent(query, extracted_entities)

if intent.confidence > 0.7:
    # Auto-fetch prefill data
    prefill_data = await get_prefill_data(intent.action, intent.entity_id)

    response["intent"] = {
        "action": intent.action,
        "confidence": intent.confidence,
        "trigger_threshold": 0.7,
        "should_focus": True,
        "entity_id": intent.entity_id
    }
    response["prefill_data"] = prefill_data
```

#### 2. Expose Intent Detection Endpoint (Optional)
**File**: `apps/api/action_router/router.py`

```python
@router.post("/analyze-intent")
async def analyze_intent(
    query: str,
    authorization: str = Header(...),
):
    """
    Analyze query for action intent.

    Returns:
        action: Detected action ID (e.g., "receive_part")
        confidence: 0.0-1.0
        entity_type: "part", "equipment", etc.
        entity_id: UUID if entity found
    """
```

---

### Frontend Changes

#### 1. Handle Intent from Search Response
**File**: `apps/web/src/hooks/useCelesteSearch.ts`

**Change**:
```typescript
// After search completes
const searchResponse = await fetch('/webhook/search', ...);
const data = await searchResponse.json();

setState(prev => ({
  ...prev,
  results: data.results,
  intent: data.intent,              // NEW
  prefillData: data.prefill_data,   // NEW
}));

// If intent detected, update actionSuggestions
if (data.intent?.should_focus) {
  setState(prev => ({
    ...prev,
    actionSuggestions: [{
      action_id: data.intent.action,
      label: getActionLabel(data.intent.action),
      variant: "MUTATE",
      prefill_data: data.prefill_data,
    }]
  }));
}
```

#### 2. Call Entity-Specific Suggestions on Selection
**File**: `apps/web/src/components/spotlight/SpotlightSearch.tsx`

**Change**:
```typescript
const handleResultSelect = useCallback(async (result: SpotlightResult) => {
  // Existing situation creation...

  // NEW: Fetch entity-specific actions
  if (result.type === 'part') {
    const suggestions = await fetch(
      `/v1/parts/suggestions?part_id=${result.id}`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    const data = await suggestions.json();

    setActionSuggestions(data.suggested_actions);
  }
}, [...]);
```

#### 3. Differentiate Intent vs Browse Rendering
**File**: `apps/web/src/components/spotlight/SpotlightSearch.tsx`

**Change**:
```tsx
{/* Intent Mode: Focused action */}
{intent?.should_focus && (
  <div className="border-b border-[#3d3d3f]/30">
    <div className="px-4 py-2 text-[12px] text-[#98989f]">
      Detected Action: {intent.action}
    </div>
    <ActionFocusedView
      action={intent.action}
      entity={results[0]}
      prefillData={prefillData}
    />
  </div>
)}

{/* Browse Mode: Show results */}
{!intent?.should_focus && (
  <div data-testid="search-results">
    {results.map((result, index) => (
      <SpotlightResultRow
        result={result}
        onClick={() => handleResultSelect(result, index)}
      />
    ))}
  </div>
)}

{/* Contextual actions after selection */}
{selectedResult && actionSuggestions.length > 0 && (
  <SuggestedActions
    actions={actionSuggestions}
    yachtId={yachtId}
  />
)}
```

---

## Implementation Plan

### Phase 1: Backend Intent Integration (2-3 hours)
1. Add intent analysis to search response
2. Auto-call prepare/prefill when intent detected
3. Test intent detection with various queries
4. Deploy to staging

### Phase 2: Frontend Intent Rendering (3-4 hours)
1. Update `useCelesteSearch` to handle intent from response
2. Create `ActionFocusedView` component for intent mode
3. Update `SpotlightSearch` to differentiate intent vs browse
4. Test rendering with intent queries

### Phase 3: Entity-Specific Suggestions (2 hours)
1. Add `/v1/parts/suggestions` call on entity selection
2. Update `SuggestedActions` to use entity-specific actions
3. Test with different roles (crew, chief_engineer, captain)
4. Verify stock-based filtering (on_hand = 0 scenarios)

### Phase 4: E2E Test Fixes (1 hour)
1. Update test selectors to match actual UI
2. Add tests for intent detection
3. Add tests for entity-specific suggestions
4. Verify all 7 tests pass

**Total Estimate**: 8-10 hours of development

---

## Test Scenarios

### Scenario 1: Intent Query (Focused Action)
```
Input: "receive engine oil filter"
Expected:
  - Part entity found ✅
  - Intent: receive_part (confidence: 0.85) ✅
  - Prefill data loaded ✅
  - UI shows focused "Receive Part" modal ✅
  - Other actions hidden/minimized ✅
```

### Scenario 2: Browse Query (No Intent)
```
Input: "engine oil filter"
Expected:
  - Part entity found ✅
  - No intent detected ✅
  - UI shows search result row ✅
  - No actions visible yet ✅
  - User clicks → Load /v1/parts/suggestions ✅
  - Show context-valid actions ✅
```

### Scenario 3: Stock-Based Filtering
```
Given: Part #1234 with on_hand = 0
When: Chief Engineer clicks part in results
Expected:
  - receive_part ✅ (can add stock)
  - consume_part ❌ (hidden - no stock)
  - write_off_part ❌ (hidden - no stock)
  - adjust_stock_quantity ❌ (hidden - SIGNED action)
```

### Scenario 4: Role-Based Filtering
```
Given: Part #1234 with on_hand = 10
When: Captain clicks part in results
Expected:
  - receive_part ✅
  - consume_part ✅
  - write_off_part ✅ (SIGNED - Captain only)
  - adjust_stock_quantity ✅ (SIGNED - Captain only)
  - transfer_part ✅
```

---

## Decision Points

### Question 1: Intent Threshold
**Decision Needed**: What confidence threshold triggers intent mode?
- Option A: 0.7 (conservative - only obvious intents)
- Option B: 0.5 (aggressive - more false positives)
- **Recommendation**: Start with 0.7, adjust based on user feedback

### Question 2: Prefill Auto-Fetch
**Decision Needed**: Always fetch prefill when intent detected?
- Option A: Yes - faster for users
- Option B: No - only on modal open
- **Recommendation**: Yes - prefetch for <500ms perceived latency

### Question 3: Browse Mode Actions
**Decision Needed**: When to show actions in browse mode?
- Option A: On selection/click
- Option B: On hover
- Option C: Always visible inline
- **Recommendation**: On click (Option A) - cleaner UI, explicit user intent

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Intent detection false positives | High | Use 0.7 threshold, allow manual refinement |
| Prefill API latency | Medium | Cache recent prefills, show loading state |
| Action overload in UI | Medium | Collapse secondary actions, focus on top 3 |
| Backend breaking changes | Low | Version API, keep backward compatibility |

---

## Success Criteria

✅ All 7 E2E tests pass
✅ Intent queries show focused action within 500ms
✅ Browse queries show context-valid actions on selection
✅ Stock-based filtering working (on_hand = 0 scenarios)
✅ Role-based filtering working (SIGNED actions for Captain only)
✅ Zero 5xx errors
✅ Prefill data loads automatically for intent queries

---

## References

- **Test File**: `tests/e2e/parts/parts_suggestions.spec.ts`
- **Backend Suggestions**: `apps/api/routes/part_routes.py:197`
- **Frontend Search Hook**: `apps/web/src/hooks/useCelesteSearch.ts`
- **Action Buttons**: `apps/web/src/components/SuggestedActions.tsx`
- **Spec**: `docs/pipeline/entity_lenses/part_lens/v2/part_lens_v2_FINAL.md`

---

**Next Steps**: Implement Phase 1 (Backend Intent Integration) first, then test before proceeding to frontend changes.
