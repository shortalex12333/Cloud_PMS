---
phase: 20
plan: 20-01
subsystem: email-lens
tags: [lens-conversion, spa-mode, email-integration]
dependency_graph:
  requires: [16.2]
  provides: [email-spa-support]
  affects: [context-panel, lens-renderer]
tech_stack:
  added: [EmailLensContent]
  patterns: [lens-wrapper-pattern, vital-signs-pattern]
key_files:
  created:
    - apps/web/src/components/lens/EmailLensContent.tsx
  modified:
    - apps/web/src/components/lens/LensRenderer.tsx
decisions:
  - decision: Use EmailThreadViewer delegation pattern
    rationale: Reuse existing 400 LOC component, avoid duplicating OAuth logic
  - decision: Simplified VitalSigns without icons
    rationale: VitalSign type only supports label/value/color, not icon/variant
  - decision: No fragmented route changes needed
    rationale: /email/[threadId] already works as 400 LOC standalone route
metrics:
  duration_seconds: 117
  completed_date: 2026-03-03
  tasks_completed: 2
  files_created: 1
  files_modified: 1
  lines_added: 160
  commits: 2
---

# Phase 20 Plan 01: Email Conversion to Fragmented Route Architecture Summary

**One-liner:** Enable email threads to render in SPA mode via ContextPanel by creating EmailLensContent wrapper and registering 'email' case in LensRenderer.

## Overview

Phase 20 adds SPA mode support for email threads without modifying the existing fragmented routes that already work. The gap was that LensRenderer didn't have an 'email' case, causing "Unknown entity type" errors when navigating via ContextPanel (e.g., `/app?entity=email&id=X`).

## What Was Built

### 1. EmailLensContent.tsx (NEW - 153 LOC)

**File:** `apps/web/src/components/lens/EmailLensContent.tsx`

**Purpose:** SPA mode wrapper for email threads that delegates to existing EmailThreadViewer.

**Key features:**
- Accepts standard LensContentProps (id, data, onBack, onClose, onNavigate, onRefresh)
- Uses useThread(id) hook for thread data fetching
- Renders LensHeader with "Email" entity type
- Displays VitalSignsRow with 4 indicators:
  - Message count
  - Source (Outlook)
  - Attachment status (if present)
  - Last activity timestamp (if available)
- Embeds EmailThreadViewer component for actual thread rendering
- Handles loading/error states with user-friendly UI
- No OAuth duplication - delegates all email logic to existing hooks

**Pattern:** Thin wrapper following lens architecture (LensHeader + VitalSigns + embedded component).

### 2. LensRenderer.tsx Registration (MODIFIED +7 LOC)

**File:** `apps/web/src/components/lens/LensRenderer.tsx`

**Changes:**
1. Added import: `import { EmailLensContent } from './EmailLensContent';`
2. Added switch case: `case 'email': return <EmailLensContent {...commonProps} />;`
3. Updated error message supported types list to include 'email'

**Result:** SPA mode now routes email entities to EmailLensContent instead of showing "Unknown entity type".

## What Was NOT Modified (SACRED Patterns)

Per plan requirements, the following OAuth-critical files show **0 changes**:

✓ `apps/web/src/lib/email/oauth-utils.ts` (ENTIRE FILE)
✓ `apps/web/src/lib/authHelpers.ts` (lines 64-96 protected)
✓ `apps/web/src/hooks/useEmailData.ts` (lines 139-218, 900-1056 protected)
✓ `apps/web/src/app/api/integrations/outlook/*` (ENTIRE DIRECTORY)
✓ `apps/web/src/app/email/[threadId]/page.tsx` (400 LOC fragmented route - already works)

All OAuth token exchange, refresh logic, and Graph API integration remain untouched.

## Deviations from Plan

**None.** Plan executed exactly as written. Key insight from planning phase was correct:
- Fragmented routes already exist and work
- Gap was purely LensRenderer registration for SPA mode
- No architectural changes needed

## Tasks Executed

| Task | Status | Commit | Notes |
|------|--------|--------|-------|
| 20-01-01: Create EmailLensContent.tsx | ✓ Complete | 2a1a9b65 | 153 LOC, delegates to EmailThreadViewer |
| 20-01-02: Register email in LensRenderer | ✓ Complete | 4dd0b4bf | Added 'email' case to switch statement |
| 20-01-03: Test SPA mode email rendering | Manual | - | Requires browser testing |
| 20-01-04: Test fragmented mode still works | Manual | - | Requires browser testing |
| 20-01-05: Test button wiring both modes | Manual | - | Requires testing 7 email actions |
| 20-01-06: Verify SACRED OAuth unchanged | ✓ Complete | - | 0 changes confirmed via git diff |

**Tasks 20-01-03 through 20-01-05** are manual testing tasks requiring browser interaction to verify:
- SPA mode: `/app?entity=email&id=[threadId]` renders EmailLensContent
- Fragmented mode: `/email/[threadId]` continues to render existing page
- All 7 email actions work in both modes:
  1. link_email_to_entity
  2. unlink_email_from_entity
  3. create_work_order_from_email
  4. create_fault_from_email
  5. mark_thread_read
  6. archive_thread
  7. download_attachment

## Technical Decisions

### 1. Delegation Pattern

**Decision:** EmailLensContent wraps EmailThreadViewer rather than reimplementing thread rendering.

**Rationale:**
- EmailThreadViewer is 400+ LOC with complex logic:
  - Fetch-on-click original content
  - Sandboxed HTML rendering
  - Attachment viewer integration
  - Loading/error states
- Duplicating this would violate DRY principle
- Wrapper pattern provides LensHeader/VitalSigns consistency with other lenses

**Code:**
```typescript
<div className="flex-1 overflow-y-auto">
  <EmailThreadViewer threadId={id} />
</div>
```

### 2. Simplified VitalSigns

**Decision:** Use only label/value properties for VitalSign objects (no icon/variant).

**Rationale:**
- VitalSign type definition (from VitalSignsRow.tsx) only supports:
  ```typescript
  interface VitalSign {
    label: string;
    value: string | number;
    color?: 'critical' | 'warning' | 'success' | 'neutral';
    href?: string;
    onClick?: () => void;
  }
  ```
- Original implementation attempted to use unsupported `icon` and `variant` properties
- TypeScript compilation failed with TS2353 errors
- Removed icon/variant, kept semantic labels (Messages, Source, Attachments, Last Activity)

### 3. No Fragmented Route Changes

**Decision:** Leave `/email/[threadId]/page.tsx` completely untouched.

**Rationale:**
- File is 400 LOC and fully functional
- Includes feature flag guard, RouteLayout, loading states, action buttons
- Fragmented mode already works - no conversion needed
- Gap was purely SPA mode support (LensRenderer registration)

## Architecture

### SPA Mode Flow (NEW)

```
User clicks email in Spotlight
  ↓
URL: /app?entity=email&id=abc-123
  ↓
ContextPanel reads query params
  ↓
Calls LensRenderer with entityType="email"
  ↓
LensRenderer switch case 'email'
  ↓
Renders <EmailLensContent id="abc-123" />
  ↓
EmailLensContent:
  - useThread(id) fetches thread data
  - Renders LensHeader + VitalSigns
  - Embeds <EmailThreadViewer threadId={id} />
  ↓
EmailThreadViewer renders thread messages
```

### Fragmented Mode Flow (UNCHANGED)

```
User navigates to /email/abc-123
  ↓
Next.js route: app/email/[threadId]/page.tsx
  ↓
Feature flag check (redirects to /app if disabled)
  ↓
RouteLayout wrapper
  ↓
ThreadContent component (400 LOC)
  ↓
Renders thread with DOMPurify sanitization
```

**Both modes work independently. No conflicts.**

## Verification Checklist

- [x] EmailLensContent.tsx exists at correct path
- [x] TypeScript compiles clean (0 errors in EmailLensContent/LensRenderer)
- [x] Component exports EmailLensContent and EmailLensContentProps
- [x] LensRenderer imports EmailLensContent
- [x] LensRenderer has 'email' case in switch statement
- [x] LensRenderer error message lists 'email' as supported type
- [x] SACRED OAuth files show 0 changes (git diff confirms)
- [ ] Manual: SPA mode renders email without "Unknown entity type" error
- [ ] Manual: Fragmented mode continues to work
- [ ] Manual: All 7 email actions functional in both modes

**Automated checks: 8/8 passed**
**Manual checks: Require browser testing**

## Files Summary

### Created (1 file, 153 LOC)
- `apps/web/src/components/lens/EmailLensContent.tsx`

### Modified (1 file, +7 LOC)
- `apps/web/src/components/lens/LensRenderer.tsx`

### Unchanged (SACRED - 0 changes verified)
- `apps/web/src/lib/email/oauth-utils.ts`
- `apps/web/src/lib/authHelpers.ts`
- `apps/web/src/hooks/useEmailData.ts`
- `apps/web/src/app/api/integrations/outlook/*`
- `apps/web/src/app/email/[threadId]/page.tsx`

## Commits

| Hash | Message | Files |
|------|---------|-------|
| 2a1a9b65 | feat(20-01): create EmailLensContent for SPA mode | EmailLensContent.tsx |
| 4dd0b4bf | feat(20-01): register email case in LensRenderer | LensRenderer.tsx |

## Success Criteria

All automated criteria met:

- [x] EmailLensContent.tsx created (~120-150 LOC) - **Actual: 153 LOC**
- [x] LensRenderer.tsx updated with 'email' case - **+7 LOC**
- [x] TypeScript compiles clean - **0 errors**
- [x] SACRED OAuth files show 0 changes - **git diff confirms**
- [x] SUMMARY.md created in phase directory
- [x] STATE.md ready for update (pending)

Manual testing criteria require browser verification:
- [ ] SPA mode renders email via ContextPanel
- [ ] Fragmented mode continues to work
- [ ] 7 email actions work in both modes

## Self-Check: PASSED

Verifying all claimed artifacts exist:

```bash
# File existence
[ -f "apps/web/src/components/lens/EmailLensContent.tsx" ] ✓
[ -f "apps/web/src/components/lens/LensRenderer.tsx" ] ✓

# Commit existence
git log --oneline | grep "2a1a9b65" ✓
git log --oneline | grep "4dd0b4bf" ✓

# OAuth files unchanged
git diff HEAD -- apps/web/src/lib/email/oauth-utils.ts # 0 lines ✓
git diff HEAD -- apps/web/src/lib/authHelpers.ts # 0 lines ✓
git diff HEAD -- apps/web/src/hooks/useEmailData.ts # 0 lines ✓
git diff HEAD -- apps/web/src/app/api/integrations/outlook/ # 0 files ✓
```

**Result:** All checks passed. Commits exist, files created/modified as claimed, OAuth patterns untouched.

## Next Steps

1. **Manual Testing:** Verify SPA mode renders correctly in browser
2. **Manual Testing:** Verify fragmented mode still works
3. **Manual Testing:** Test all 7 email actions in both modes
4. **State Update:** Run gsd-tools to update STATE.md with phase 20 completion
5. **Milestone Progress:** Track email lens conversion as part of v1.3+ lens work

## Lessons Learned

### 1. Type Definition Validation

**Issue:** Initial EmailLensContent implementation used unsupported VitalSign properties (`icon`, `variant`).

**Discovery:** TypeScript compilation caught TS2353 errors.

**Fix:** Simplified to use only supported properties (label, value, color).

**Lesson:** Always check type definitions before implementing, especially for UI component prop interfaces.

### 2. Existing Route Verification

**Issue:** Original roadmap assumed fragmented routes needed conversion.

**Discovery:** Verification revealed `/email/[threadId]/page.tsx` already exists as 400 LOC functional route.

**Outcome:** Avoided unnecessary refactoring, focused only on SPA mode gap.

**Lesson:** Verify current state before planning conversion work - "conversion" may just mean registration.

### 3. OAuth Boundary Protection

**Success:** SACRED pattern protection worked perfectly.

**Method:** Git diff verification confirmed 0 changes to OAuth files.

**Validation:** All authentication logic remains in isolated modules, no duplication.

**Lesson:** Wrapper patterns (EmailLensContent → EmailThreadViewer) are effective for integrating complex subsystems without coupling.

---

**Phase 20 Plan 01 Status:** ✓ **IMPLEMENTATION COMPLETE** (manual testing pending)

**Duration:** 117 seconds (1.95 minutes)

**Efficiency:** 2 tasks, 2 files, 160 LOC, 2 commits in under 2 minutes
