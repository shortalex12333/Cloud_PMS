# CRITICAL BLOCKERS - FORENSIC AUDIT

**Generated:** 2026-01-18
**Verdict:** SYSTEM NOT PRODUCTION READY

---

## STOP CONDITIONS TRIGGERED

| Condition | Status |
|-----------|--------|
| yacht_id is not resolvable from any DB table | ❌ FALSE (yacht_id IS in MASTER DB) |
| Membership table does not exist | ⚠️ PARTIAL (user_accounts exists, but crew_members does NOT) |
| Code references tables with no migration | ✅ TRUE - 17 tables referenced but do not exist |
| Placeholders exist in production JS | ✅ TRUE - 5 placeholder locations found |
| RLS allows cross-tenant reads | ⚠️ UNKNOWN (cannot verify without real user tests) |

---

## BLOCKER 1: yacht_id NULL in Search Requests

**Severity:** CRITICAL
**Impact:** ALL search functionality broken

### Evidence
```json
// Captured API request payload
{
  "auth": {
    "user_id": "a0d66b00-581f-4d27-be6b-5b679d5cd347",
    "yacht_id": null,  // ← BROKEN
    "role": "Engineer"
  }
}
```

### Root Cause
`getYachtId()` in `authHelpers.ts:212` reads from `session.user.user_metadata.yacht_id` which is NEVER SET.

### Files Affected
- `apps/web/src/lib/authHelpers.ts:199-217`
- `apps/web/src/hooks/useCelesteSearch.ts:145`

### Repro Steps
1. Login as x@alex-short.com
2. Type any search query
3. Open Network tab
4. Observe POST to `/webhook/search`
5. Request body contains `yacht_id: null`

---

## BLOCKER 2: Placeholder IDs in Production Code

**Severity:** CRITICAL
**Impact:** Viewer and navigation fail with UUID parsing errors

### Evidence
```typescript
// NavigationContext.tsx:123-124
const yachtId = state.yachtId || 'placeholder-yacht-id';
const userId = state.userId || 'placeholder-user-id';

// AddRelatedModal.tsx:34-35
const yachtId = 'placeholder-yacht-id';
const userId = 'placeholder-user-id';
```

### Files Affected
- `apps/web/src/contexts/NavigationContext.tsx:123-124`
- `apps/web/src/components/context-nav/AddRelatedModal.tsx:34-35`
- `apps/web/src/lib/supabaseClient.ts:15`

### Repro Steps
1. Login
2. Search for any document
3. Click on a search result to open viewer
4. Console shows: `uuid_parsing error`

---

## BLOCKER 3: 17 Tables Referenced But Do Not Exist

**Severity:** CRITICAL
**Impact:** Microaction handlers fail silently

### Missing Tables
| Table | Handler |
|-------|---------|
| `attachments` | faults.ts, workOrders.ts |
| `audit_log` | workOrders.ts |
| `auth_users` | lib/auth.ts |
| `checklist_items` | workOrders.ts |
| `crew_members` | useEmailData.ts |
| `deliveries` | procurement.ts |
| `hours_of_rest` | compliance.ts |
| `invoices` | procurement.ts |
| `maintenance_templates` | faults.ts |
| `notes` | equipment.ts, faults.ts, workOrders.ts |
| `pms_equipment_notes` | dispatchers.ts |
| `purchase_request_items` | procurement.ts |
| `purchase_requests` | inventory.ts, procurement.ts |
| `sensor_readings` | equipment.ts |
| `survey_tags` | compliance.ts |
| `work_order_parts` | inventory.ts, workOrders.ts |
| `worklist_items` | workOrders.ts |

### Repro Steps
1. Login
2. Navigate to any equipment
3. Click "Add Note" microaction
4. Action fails (table `notes` does not exist)

---

## BLOCKER 4: Email Panel is Placeholder

**Severity:** HIGH
**Impact:** Email feature appears broken to users

### Evidence
```typescript
// EmailPanel.tsx:79-88
{/* Email list placeholder */}
<div className="flex-1 overflow-y-auto p-4">
  <div className="text-center py-12">
    <Inbox className="w-12 h-12 text-gray-600 mx-auto mb-4" />
    <p className="text-gray-400 text-sm">
      {folder === 'inbox' ? 'Inbox' : 'Sent'} will appear here
    </p>
  </div>
</div>
```

### Files Affected
- `apps/web/src/app/app/EmailPanel.tsx`

### Repro Steps
1. Login
2. Open Email panel
3. See placeholder text instead of real inbox

---

## BLOCKER 5: Add To Handover Fails

**Severity:** HIGH
**Impact:** Core workflow broken

### Evidence
From tasks.md:
> Console shows ActionExecutionError: `add_to_handover` failed

### Potential Causes
1. Placeholder yacht_id/user_id sent
2. Missing required columns in handover_items
3. RLS policy blocking insert

### Files Affected
- `apps/web/src/lib/microactions/handlers/` (various)
- `handover_items` table

---

## BLOCKER 6: Document Viewer Context Broken

**Severity:** HIGH
**Impact:** Cannot view documents

### Evidence
From tasks.md:
> Console shows:
> - `yacht_id = "placeholder-yacht-id"`
> - `user_id = "placeholder-user-id"`

### Root Cause
NavigationContext.pushViewer() uses placeholder fallback when state.yachtId is null.

### Files Affected
- `apps/web/src/contexts/NavigationContext.tsx`

---

## BLOCKER 7: Multiple Disconnected Auth Contexts

**Severity:** MEDIUM
**Impact:** Inconsistent behavior across features

### Evidence
| Context | yacht_id Source | Status |
|---------|-----------------|--------|
| AuthContext | Bootstrap API | ✅ Works |
| useCelesteSearch | user_metadata | ❌ NULL |
| NavigationContext | Internal state | ❌ NULL/Placeholder |
| useActionHandler | AuthContext | ✅ Works |

### Root Cause
No single source of truth. Different code paths use different sources.

---

## BLOCKER 8: Tests Were Skipped, Not Passing

**Severity:** MEDIUM
**Impact:** False confidence in test coverage

### Evidence
```
test-results/results.json:
  Expected (passed): 0
  Skipped: 1550
```

Previous Claude claimed "1481 passed" when actually 0 passed and 1550 were skipped.

---

## SUMMARY

| Blocker | Severity | Can Ship? |
|---------|----------|-----------|
| yacht_id NULL in search | CRITICAL | NO |
| Placeholder IDs | CRITICAL | NO |
| 17 missing tables | CRITICAL | NO |
| Email placeholder | HIGH | NO |
| Add to handover fails | HIGH | NO |
| Document viewer broken | HIGH | NO |
| Multiple auth contexts | MEDIUM | NO |
| Skipped tests | MEDIUM | NO |

**Verdict: CANNOT SHIP**

The system has fundamental data architecture issues where yacht context is not properly propagated. Until these are resolved, the product is not functional.

---

## FIX PRIORITY

1. **Fix yacht_id propagation** - Make AuthContext the single source of truth
2. **Remove all placeholders** - Replace with throws/blocking UI
3. **Create missing tables** - Or remove dead code referencing them
4. **Wire EmailPanel to EmailInboxView**
5. **Fix NavigationContext** - Initialize from AuthContext
6. **Write real E2E tests** - That don't skip
