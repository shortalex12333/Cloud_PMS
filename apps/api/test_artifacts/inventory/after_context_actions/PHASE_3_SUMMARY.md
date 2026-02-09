# Phase 3: Backend Context + Actions - Summary

**Duration**: 1:45 - 2:45
**Status**: ✅ COMPLETED

## Changes Made

### 1. Added Context Metadata to Response

**File**: `apps/api/routes/orchestrated_search_routes.py`
**Lines**: 60-67, 212-226

**Added**: `ContextMetadata` Pydantic model with fields:
- `domain`: Primary domain from classification (e.g., "parts")
- `domain_confidence`: Confidence score (0.9 for deterministic classification)
- `intent`: Intent family from parser or default "READ"
- `intent_confidence`: Confidence score (0.95 if parsed, 0.8 if default)
- `mode`: Retrieval path used ("sql_only", "vector_only", "hybrid")
- `filters`: Applied filters (time_window_days, scopes)

**Population Logic** (lines 212-226):
```python
# Extract primary domain from allowed_scopes
primary_domain = result.classification.allowed_scopes[0] if result.classification.allowed_scopes else None

# Build context metadata
context_metadata = ContextMetadata(
    domain=primary_domain,
    domain_confidence=0.9,
    intent=result.intent_family or "READ",
    intent_confidence=0.95 if result.intent_family else 0.8,
    mode=result.plan.path.value,
    filters={
        'time_window_days': result.plan.time_window.days,
        'scopes': result.classification.allowed_scopes,
    },
)
```

### 2. Added Actions Array to Response

**File**: `apps/api/routes/orchestrated_search_routes.py`
**Lines**: 30, 77, 228-235, 244

**Import Added** (line 30):
```python
from action_router.registry import get_actions_for_domain
```

**Response Model Updated** (line 77):
```python
class OrchestatedSearchResponse(BaseModel):
    # ... existing fields ...
    context: Optional[ContextMetadata] = None
    actions: Optional[List[Dict[str, Any]]] = None  # NEW
    trust: TrustPayload
    # ... remaining fields ...
```

**Action Filtering Logic** (lines 228-235):
```python
# Get action suggestions filtered by domain and role
# Normalize inventory → parts as per requirements
action_suggestions = []
if primary_domain:
    normalized_domain = "parts" if primary_domain == "inventory" else primary_domain
    user_role = auth.get('role')
    if user_role:
        action_suggestions = get_actions_for_domain(normalized_domain, user_role)
```

**Key Features**:
- ✅ Normalizes "inventory" domain to "parts" before action lookup
- ✅ Filters actions by user role (crew, chief_engineer, captain, etc.)
- ✅ Returns only role-appropriate actions (READ for crew, MUTATE for HOD, SIGNED for captain)

## Testing

### Unit Test Results

**Test**: `test_action_suggestions.py`
**Status**: ✅ ALL TESTS PASSED

**Test 1: Crew role (parts domain)**
- Total actions: 2
- Actions: check_stock_level, view_part_details
- ✅ PASS: Crew only has READ actions (no MUTATE or SIGNED)

**Test 2: chief_engineer role (parts domain)**
- Total actions: 8
- Actions: check_stock_level, log_part_usage, consume_part, receive_part, transfer_part, view_part_details, generate_part_labels, request_label_output
- ✅ PASS: HOD has more actions than crew
- ✅ PASS: HOD has both READ and MUTATE actions

**Test 3: captain role (parts domain)**
- Total actions: 10
- Actions: All of the above + adjust_stock_quantity, write_off_part
- ✅ PASS: Captain has all actions (including SIGNED)
- ✅ PASS: Captain has SIGNED actions (adjust_stock_quantity, write_off_part)

## Expected Response Structure

```json
{
  "success": true,
  "request_id": "abc123",
  "results": [...],
  "results_by_domain": {
    "parts": [...]
  },
  "total_count": 15,
  "context": {
    "domain": "parts",
    "domain_confidence": 0.9,
    "intent": "READ",
    "intent_confidence": 0.95,
    "mode": "hybrid",
    "filters": {
      "time_window_days": 90,
      "scopes": ["parts"]
    }
  },
  "actions": [
    {
      "action_id": "check_stock_level",
      "label": "Check Stock Level",
      "variant": "READ",
      "allowed_roles": ["crew", "deckhand", ...],
      "required_fields": ["yacht_id", "part_id"],
      "has_prefill": false,
      "prefill_endpoint": null,
      "context_required": null
    },
    {
      "action_id": "view_part_details",
      "label": "View Part Details",
      "variant": "READ",
      "allowed_roles": ["crew", "deckhand", ...],
      "required_fields": ["yacht_id", "part_id"],
      "has_prefill": false,
      "prefill_endpoint": null,
      "context_required": null
    }
  ],
  "trust": {
    "path": "hybrid",
    "scopes": ["parts"],
    "time_window_days": 90,
    "used_vector": true,
    "explain": "Hybrid search: SQL filters + semantic on 'parts low in stock...'"
  },
  "timing_ms": {
    "orchestration": 45.2,
    "execution": 123.5,
    "total": 168.7
  }
}
```

## Impact

### Before Phase 3
- Response had results but no context metadata
- Response had no actions array
- Frontend couldn't adapt UI based on domain/intent
- Frontend couldn't show role-appropriate action buttons

### After Phase 3
- Response includes context metadata (domain, intent, mode, confidences, filters)
- Response includes actions array filtered by role and domain
- Frontend can adapt UI based on context
- Frontend can render role-appropriate action buttons
- Crew sees only READ actions
- HOD sees READ + MUTATE actions
- Captain sees all actions including SIGNED

## Files Modified

1. `/apps/api/routes/orchestrated_search_routes.py`
   - Added import for `get_actions_for_domain`
   - Added `ContextMetadata` model
   - Updated `OrchestatedSearchResponse` with `context` and `actions` fields
   - Added context metadata population logic
   - Added action filtering logic with inventory→parts normalization

## Files Created

1. `/test_artifacts/inventory/after_context_actions/test_action_suggestions.py`
   - Unit test proving action filtering works correctly
   - Tests crew, HOD, and captain roles
   - Verifies READ/MUTATE/SIGNED variant filtering

## Acceptance Criteria

✅ **Context metadata included**: domain, domain_confidence, intent, intent_confidence, mode, filters
✅ **Actions array included**: filtered by domain and role
✅ **Inventory normalized to parts**: "inventory" domain maps to "parts" for action lookup
✅ **Role-based filtering works**: crew gets READ, HOD gets READ+MUTATE, captain gets all
✅ **Unit tests pass**: All 3 role tests pass with expected action counts

## Next Phase

**Phase 4 (2:45-3:30): Verify Action Suggestions Contract**
- Test GET /v1/actions/list with different roles and domains
- Verify crew vs HOD action differences via API calls
- Save curl transcripts to actions_list_checks/
