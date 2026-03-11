# Gaps & Missing Components — Spotlight Search v1.3

**Last Updated:** 2026-03-03 (GAP-006 resolved, new gaps from Wave 3 added)

---

## Critical Gaps (ALL RESOLVED)

### GAP-001: /prepare Endpoint Not Mounted ✅ FIXED

**Severity:** CRITICAL → RESOLVED
**Phase:** 16.1 (complete)
**Blocks:** ~~All prefill functionality in production~~ UNBLOCKED

| Field | Value |
|-------|-------|
| **What Was Wrong** | `action_router/router.py` has `/prepare` endpoint but router not mounted |
| **Location** | `apps/api/routes/p0_actions_routes.py` |
| **Evidence** | ~~`curl localhost:8000/v1/actions/prepare` returns 404~~ Now returns 401 (auth required) |
| **Root Cause** | Only `p0_actions_router` was mounted, not `action_router.router` |
| **Fix Applied** | Added `/prepare` endpoint to `p0_actions_routes.py` with all models imported |
| **Status** | ✅ **FIXED** (2026-03-02) |

**Resolution:**

```python
# p0_actions_routes.py - NOW INCLUDES /prepare
from action_router.router import (
    PrepareRequest, PrepareResponse, PrefillField,
    AmbiguityCandidate, Ambiguity, PrepareError,
)
from common.prefill_engine import build_prepare_response

@router.post("/prepare", response_model=PrepareResponse)
async def prepare_action(...):
    # Full implementation with JWT/tenant/role validation
    ...
```

**Verification:**
- `curl -X POST localhost:8000/v1/actions/prepare` → 401 (not 404) ✓
- OpenAPI schema includes `/v1/actions/prepare` ✓
- Docker local build succeeds ✓

---

### GAP-002: User Edit Protection Missing

**Severity:** MEDIUM
**Phase:** 16 (tracked follow-up)
**Blocks:** UX polish

| Field | Value |
|-------|-------|
| **What's Wrong** | Prefill refetch overwrites user edits |
| **Location** | `apps/web/src/components/ActionModal.tsx` |
| **Evidence** | useEffect at lines 128-132 calls setFormData without checking user edits |
| **Root Cause** | No tracking of user-modified fields |
| **Fix** | Track modified fields, merge instead of replace |
| **Status** | Tracked for follow-up (low impact due to debounce/cache) |

**Code Evidence:**

```typescript
// ActionModal.tsx:128-132 - OVERWRITES USER EDITS
useEffect(() => {
  if (prefillData) {
    setFormData(getInitialFormData());  // No merge with user edits
  }
}, [prefillData]);
```

---

## Moderate Gaps

### GAP-003: Missing Route Registration Log ✅ AUTO-RESOLVED

**Severity:** LOW → RESOLVED
**Phase:** 16.1 (complete)

| Field | Value |
|-------|-------|
| **What Was Wrong** | No log entry for /prepare route registration |
| **Status** | ✅ **AUTO-RESOLVED** with GAP-001 fix |
| **Evidence** | Logs now show: `✅ P0 Actions routes registered at /v1/actions/*` |

---

### GAP-004: No /prepare OpenAPI Documentation ✅ AUTO-RESOLVED

**Severity:** LOW → RESOLVED
**Phase:** 16.1 (complete)

| Field | Value |
|-------|-------|
| **What Was Wrong** | /prepare not in OpenAPI schema |
| **Status** | ✅ **AUTO-RESOLVED** with GAP-001 fix |
| **Evidence** | `curl -s localhost:8000/openapi.json \| python3 -c "import sys,json; print('/v1/actions/prepare' in json.load(sys.stdin)['paths'])"` → `True` |

---

## Tracked Follow-ups

### FOLLOW-001: Temporal Parser Edge Cases

**Severity:** LOW
**Phase:** Future

| Field | Value |
|-------|-------|
| **What** | "End of month", "Q2", "fiscal year" not parsed |
| **Impact** | Low - uncommon phrases |
| **Track** | Add when user requests |

---

### FOLLOW-002: Priority Synonym Expansion

**Severity:** LOW
**Phase:** Future

| Field | Value |
|-------|-------|
| **What** | Limited synonym coverage (8 terms) |
| **Impact** | Low - covers common cases |
| **Track** | Expand based on usage data |

---

### FOLLOW-003: Entity Resolution Fuzzy Match

**Severity:** MEDIUM
**Phase:** 18 or future

| Field | Value |
|-------|-------|
| **What** | Exact match only, no fuzzy matching |
| **Impact** | Medium - typos fail silently |
| **Track** | Consider rapidfuzz integration |

---

### GAP-005: E2E Tests Use Wrong TestID Patterns for Action Buttons ✅ FIXED

**Severity:** HIGH → RESOLVED
**Phase:** E2E Testing
**Blocks:** ~~Action button E2E coverage~~ UNBLOCKED

| Field | Value |
|-------|-------|
| **What Was Wrong** | E2E tests assumed ContextPanel lens rendering, but fragmented routes navigate to dedicated pages |
| **Evidence** | Tests found 0 action buttons because click → router.push() to /faults/, /work-orders/, etc. |
| **Root Cause** | THREE separate action button systems with different rendering paths |
| **Fix Applied** | Updated E2E tests to detect navigation path and test correct location |
| **Status** | ✅ **FIXED** (2026-03-02) |

**Complete Architecture Discovery (THREE Systems):**

| System | Location | TestID Pattern | Trigger | Notes |
|--------|----------|----------------|---------|-------|
| **1. SuggestedActions** | `SpotlightSearch.tsx` | `suggested-actions`, `action-btn-{action_id}` | MUTATE queries ("create work order") | Renders 14 buttons for "create work order" ✅ |
| **2. Fragmented Routes** | `/faults/{id}`, `/equipment/{id}`, `/work-orders/{id}` pages | Page-specific testids | Search click when `FRAGMENTED_ROUTES_ENABLED=true` | Active in production |
| **3. Legacy ContextPanel** | `*LensContent.tsx` | `acknowledge-fault-btn`, `update-status-button`, etc. | Search click when flag OFF or unsupported types | Documents fall through here |

**Key Insights:**
- `NEXT_PUBLIC_FRAGMENTED_ROUTES_ENABLED=true` in production
- Clicking fault/equipment/work_order search results → `router.push()` to dedicated page
- ContextPanel only opens for unsupported types (documents) or when flag OFF
- SuggestedActions works perfectly: "create work order" → 14 action buttons
- Page components may have different action button testids than lens components

**E2E Test Strategy (Implemented):**
```typescript
// Detection function determines which path was taken
async function detectNavigationPath(page, initialUrl) {
  const currentUrl = page.url();
  if (/\/(faults|equipment|work-orders|documents)\//.test(currentUrl)) {
    return 'fragmented';  // Dedicated page with action buttons
  }
  // Check if ContextPanel opened
  const panel = page.getByTestId('context-panel');
  if (await panel.isVisible()) return 'contextPanel';
  return 'unknown';
}
```

**Test Results (2026-03-02):**
- 6/6 tests passing
- MUTATE query "create work order" → 14 suggested action buttons ✅
- Fragmented routes correctly detected and handled ✅
- RBAC buttons accessible for crew role ✅

**Lens Action Button TestIDs (for ContextPanel path):**
```
# FaultLensContent.tsx
acknowledge-fault-btn, close-fault-btn, reopen-fault-btn, false-alarm-btn, add-note-btn

# EquipmentLensContent.tsx
update-status-button, flag-attention-button, decommission-button

# WorkOrderLensContent.tsx
add-note-btn, mark-complete-btn, add-hours-btn, reassign-btn, edit-wo-btn
```

---

### GAP-006: Fragmented Route Pages Missing Action Buttons ✅ FIXED

**Severity:** CRITICAL → RESOLVED
**Phase:** 17.1 (complete)
**Blocks:** ~~Full action functionality on detail pages~~ UNBLOCKED

| Field | Value |
|-------|-------|
| **What Was Wrong** | Fragmented route pages had only placeholder action buttons |
| **Evidence** | E2E tests now find all expected buttons |
| **Root Cause** | Pages were built as minimal placeholders |
| **Fix Applied** | Added full action buttons with hooks (useFaultActions, useWorkOrderActions, useEquipmentActions) |
| **Status** | ✅ **FIXED** (2026-03-03) |

**Current State (FIXED):**

| Page | Expected Buttons | Now Rendered | TestIDs |
|------|------------------|--------------|---------|
| `/work-orders/[id]` | 5 buttons | 5 ✅ | `add-note-btn`, `mark-complete-btn`, `add-hours-btn`, `reassign-btn`, `edit-wo-btn` |
| `/faults/[id]` | 5 buttons | 5 ✅ | `acknowledge-fault-btn`, `close-fault-btn`, `reopen-fault-btn`, `false-alarm-btn`, `create-wo-button` |
| `/equipment/[id]` | 3+ buttons | 3+ ✅ | `update-status-button`, `flag-attention-button`, `report-fault-btn` |

**Files Modified:**
- `/apps/web/src/app/work-orders/[id]/page.tsx` - Full action buttons with testids
- `/apps/web/src/app/faults/[id]/page.tsx` - Full action buttons with testids
- `/apps/web/src/app/equipment/[id]/page.tsx` - Full action buttons with testids
- `/apps/web/src/hooks/useFaultActions.ts` - Fault action hooks
- `/apps/web/src/hooks/useWorkOrderActions.ts` - Work order action hooks

---

## Gap Resolution Priority

| Priority | Gap | Status |
|----------|-----|--------|
| ~~1~~ | ~~GAP-001~~ | ✅ **FIXED** (2026-03-02) |
| ~~1~~ | ~~GAP-005~~ | ✅ **FIXED** (2026-03-02) - E2E tests updated for fragmented routes |
| ~~1~~ | ~~GAP-006~~ | ✅ **FIXED** (2026-03-03) - Action buttons added to fragmented routes |
| 2 | GAP-002 | Track for future |
| ~~2~~ | ~~GAP-003~~ | ✅ **AUTO-RESOLVED** |
| ~~3~~ | ~~GAP-004~~ | ✅ **AUTO-RESOLVED** |
| 2 | GAP-007 | 🆕 RBAC mismatches (Wave 3) |
| 2 | GAP-008 | 🆕 Temporal parser gaps (Wave 3) |
| 3 | FOLLOW-* | Track for future milestones |

---

## New Gaps from Phase 19 Wave 3 Analysis

### GAP-007: RBAC Role Mismatches Between lens_matrix.json and registry.py

**Severity:** MEDIUM
**Phase:** Future
**Discovered:** Wave 3 backend integration verification (2026-03-03)

| Field | Value |
|-------|-------|
| **What's Wrong** | 6 actions have role discrepancies between frontend (lens_matrix.json) and backend (registry.py) |
| **Impact** | Some users may see buttons they can't use, or not see buttons they should |
| **Root Cause** | lens_matrix.json and registry.py maintained separately |

**Mismatches Found:**

| Action | lens_matrix.json | registry.py | Issue |
|--------|------------------|-------------|-------|
| `acknowledge_fault` | includes "manager" | missing "manager" | Backend more restrictive |
| `close_fault` | includes "manager" | missing "manager" | Backend more restrictive |
| `adjust_stock_quantity` | includes "chief_engineer" | excludes "chief_engineer" | Backend more restrictive |
| `write_off_part` | includes "chief_engineer" | excludes "chief_engineer" | Backend more restrictive |
| `link_document_to_equipment` | restricted roles | open access | Frontend more restrictive |
| `update_fault` | includes "manager" | missing "manager" | Backend more restrictive |

**Recommended Fix:** Reconcile registry.py to match lens_matrix.json (source of truth for RBAC)

---

### GAP-008: Temporal Parser Edge Cases Not Handled

**Severity:** MEDIUM
**Phase:** Future
**Discovered:** Wave 3 backend integration verification (2026-03-03)

| Field | Value |
|-------|-------|
| **What's Wrong** | Many temporal phrases FAIL to parse |
| **Impact** | Users must manually enter dates for certain phrases |
| **Root Cause** | Limited regex patterns in temporal_parser.py |

**Failing Patterns:**

| Pattern | Expected | Actual |
|---------|----------|--------|
| "expiring next month" | 2026-04-03 | None |
| "valid until 2027" | 2027-12-31 | None |
| "due next Tuesday" | Next Tuesday ISO | None |
| "by end of Q1" | 2026-03-31 | None |
| "charter season" | May-Oct range | None |

**Additional Issues:**
- Timezone parameter accepted but NOT USED
- Two overlapping parsers exist (`temporal_parser.py` and `date_parser.py`)

**Recommended Fix:**
1. Add prefix stripping (remove "due", "by", "expiring" prefixes)
2. Add month-based patterns ("next month", "end of Q1")
3. Consolidate into single parser
4. Implement timezone-aware parsing

---

## Verification Commands

### Check GAP-001 (After Fix)

```bash
# Start local Docker
docker compose -f docker-compose.local.yml up api -d

# Wait for health
sleep 10

# Test /prepare endpoint
curl -X POST http://localhost:8000/v1/actions/prepare \
  -H "Content-Type: application/json" \
  -d '{"q": "create work order", "domain": "work_orders"}'

# Expected: JSON response with action_id, prefill, etc.
# Not expected: 404 or "Not Found"
```

### Check GAP-002 (Manual)

1. Open ActionModal with prefilled data
2. Manually edit a field
3. Trigger refetch (clear cache, re-search)
4. Check if user edit preserved

**Expected after fix:** User edit preserved
**Current behavior:** User edit overwritten

---

## Gap Tracking in Ruflo Memory

```bash
# Store gap tracking
npx ruflo memory store \
  --key "gap-001-prepare-not-mounted" \
  --value '{"severity": "critical", "status": "phase-16.1-inserted", "blocks": "all-prefill"}' \
  --namespace "gaps"

# Search gaps
npx ruflo memory search --query "critical gap" --namespace "gaps"
```

---

*See also: OVERVIEW.md, PHASES-COMPLETE.md, PHASES-REMAINING.md*
