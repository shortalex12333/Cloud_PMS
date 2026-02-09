# Baseline Analysis - Inventory Lens

**Date**: 2026-02-08
**Phase**: Baseline Repro (0:00-0:45)

## Test Queries

1. "parts low in stock"
2. "oil filters"  
3. "spare parts for main engine"

## Results

All 6 tests (3 queries × 2 roles) showed identical issues:

### ✅ What Works
- API returns 200 OK
- Returns 60 results per query
- Authentication works (both Crew and HOD JWTs accepted)
- Average latency: ~2 seconds

### ❌ Confirmed Issues

1. **WRONG DATA TYPE**: Returns Work Orders instead of Parts
   - Example: "parts low in stock" returned work order "Main Engine Port 500-hour service"
   - Result structure: `{id, title, status, priority, wo_number, equipment_id}`
   - Expected: `{id, part_number, name, quantity_on_hand, minimum_quantity, location}`

2. **MISSING CONTEXT**: No context object in response
   - `has_context: false`
   - Missing: domain, intent, mode, confidences, filters

3. **MISSING ACTIONS**: No actions array
   - Response only has: `{success: true, request_id, results}`
   - Missing: `actions` array with role-filtered suggestions

## Sample Response Structure

```json
{
  "success": true,
  "request_id": "...",
  "results": [
    {
      "id": "b36238da-b0fa-4815-883c-0be61fc190d0",
      "title": "Main Engine Port 500-hour service",
      "status": "in_progress",
      "priority": "critical",
      "wo_number": null,
      "equipment_id": "e1000001-0001-4001-8001-000000000001"
    }
    // ... 59 more work orders
  ]
}
```

## Root Cause Hypothesis

The `/v2/search` endpoint is not detecting "inventory" or "part" domain from queries like:
- "parts low in stock"
- "oil filters"
- "spare parts for main engine"

Instead, it's defaulting to returning work orders.

## Next Steps (Phase 2)

Fix domain detection and capability routing:
1. Check domain detection gazetteer for inventory/part terms
2. Check entity extraction for STOCK_STATUS, PART, etc.
3. Check capability mapping (entity → SQL capability)
4. Ensure inventory queries route to `pms_parts` table, not `pms_work_orders`
