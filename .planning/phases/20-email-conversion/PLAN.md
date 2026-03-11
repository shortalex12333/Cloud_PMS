---
phase: 20
plan: 20-01
type: implementation
wave: 1
depends_on: [16.2]
files_modified:
  - apps/web/src/components/lens/EmailLensContent.tsx
  - apps/web/src/components/lens/LensRenderer.tsx
autonomous: true
must_haves:
  truths:
    - EmailLensContent.tsx exists and renders email threads
    - LensRenderer.tsx has 'email' case routing to EmailLensContent
    - SPA mode (/app?entity=email&id=X) renders email via ContextPanel
    - Fragmented mode (/email/[threadId]) continues to work
    - All 7 email actions work in both modes
    - SACRED OAuth files show 0 changes in git diff
  artifacts:
    - apps/web/src/components/lens/EmailLensContent.tsx
  key_links:
    - EmailLensContent imports EmailThreadViewer
    - LensRenderer switch includes 'email' case
    - useEmailPermissions provides action gating
---

# PLAN.md — Phase 20: Email Conversion to Fragmented Route Architecture

**Phase:** 20
**Goal:** Enable Email lens to work in BOTH SPA mode (ContextPanel) AND fragmented mode (/email/[threadId])
**Milestone:** v1.3.1 — Email Architecture Conversion
**Created:** 2026-03-03
**Revised:** 2026-03-03 (post-verification)
**Status:** READY FOR EXECUTION

---

## Revised Understanding

**Previous assumption:** `/email/[threadId]/page.tsx` was SPA-only and needed conversion.

**Actual state:** `/email/[threadId]/page.tsx` is already a 400 LOC fragmented route with:
- Feature flag guard (redirects to /app when disabled)
- RouteLayout integration
- Loading/error/not-found states
- Full ThreadContent viewer with DOMPurify sanitization
- Action buttons (Link to Object, Create Work Order)

**Real gap:** Email is NOT registered in `LensRenderer.tsx`, so SPA mode (`/app?entity=email&id=X`) falls to "Unknown entity type" error.

**Solution:** Create `EmailLensContent.tsx` and register in `LensRenderer.tsx` for SPA mode support. Fragmented mode already works.

---

## SACRED Patterns — DO NOT MODIFY

| File | Protection | Why |
|------|------------|-----|
| `apps/web/src/lib/email/oauth-utils.ts` | ENTIRE FILE | READ/WRITE app separation, forbidden scopes |
| `apps/web/src/lib/authHelpers.ts:64-96` | Lines only | 60-second JWT refresh buffer |
| `apps/web/src/hooks/useEmailData.ts:139-218` | Lines only | OutlookAuthError, authFetch dual 401 |
| `apps/web/src/hooks/useEmailData.ts:900-1056` | Lines only | useOutlookConnection, useWatcherStatus |
| `apps/web/src/app/api/integrations/outlook/*` | ENTIRE DIR | Token exchange, callbacks |

---

## Tasks

<task type="auto" id="20-01-01">
<title>Create EmailLensContent.tsx</title>
<files>
  - apps/web/src/components/lens/EmailLensContent.tsx (NEW)
</files>
<action>
Create EmailLensContent.tsx that wraps EmailThreadViewer for SPA mode rendering.

Component structure:
1. Accept standard LensContentProps (id, data, onBack, onClose, onNavigate, onRefresh)
2. Use useEmailPermissions() for action gating
3. Use useThread(id) to fetch thread data
4. Render LensHeader with "Email" entity type
5. Render VitalSignsRow with message count, attachment status
6. Embed EmailThreadViewer component for thread display
7. Do NOT duplicate OAuth/fetch logic - delegate to existing hooks

Props interface:
```typescript
export interface EmailLensContentProps {
  id: string;
  data: Record<string, unknown>;
  onBack: () => void;
  onClose: () => void;
  onNavigate?: (entityType: string, entityId: string) => void;
  onRefresh?: () => void;
}
```

Import pattern:
```typescript
import { LensHeader, LensTitleBlock } from './LensHeader';
import { VitalSignsRow, type VitalSign } from '@/components/ui/VitalSignsRow';
import { EmailThreadViewer } from '@/components/email/EmailThreadViewer';
import { useEmailPermissions } from '@/hooks/permissions/useEmailPermissions';
import { useThread } from '@/hooks/useEmailData';
```
</action>
<verify>
- File exists at apps/web/src/components/lens/EmailLensContent.tsx
- TypeScript compiles clean (npx tsc --noEmit)
- Component exports EmailLensContent and EmailLensContentProps
</verify>
<done>
EmailLensContent.tsx created with LensHeader, VitalSignsRow, and embedded EmailThreadViewer
</done>
</task>

<task type="auto" id="20-01-02">
<title>Register Email in LensRenderer.tsx</title>
<files>
  - apps/web/src/components/lens/LensRenderer.tsx (MODIFY)
</files>
<action>
Add 'email' case to LensRenderer switch statement for SPA mode support.

Changes:
1. Add import at top:
   ```typescript
   import { EmailLensContent } from './EmailLensContent';
   ```

2. Add case in switch statement (before default):
   ```typescript
   case 'email':
     return <EmailLensContent {...commonProps} />;
   ```

3. Update default error message to include 'email' in supported types list.
</action>
<verify>
- Import compiles without error
- Switch case exists for 'email'
- Supported types list includes 'email'
</verify>
<done>
LensRenderer.tsx has 'email' case routing to EmailLensContent
</done>
</task>

<task type="auto" id="20-01-03">
<title>Test SPA Mode Email Rendering</title>
<files>
  - Manual testing only
</files>
<action>
Test that SPA mode correctly renders email threads via ContextPanel.

Test steps:
1. Navigate to /app
2. Use Spotlight search to find an email thread
3. Click on thread result
4. Verify ContextPanel shows EmailLensContent (not "Unknown entity type")
5. Verify thread subject in header
6. Verify vital signs show message count
7. Verify EmailThreadViewer renders messages
</action>
<verify>
- /app?entity=email&id=[threadId] renders EmailLensContent
- No "Unknown entity type" error
- Thread content displays correctly
</verify>
<done>
SPA mode email rendering works via ContextPanel
</done>
</task>

<task type="auto" id="20-01-04">
<title>Test Fragmented Mode Still Works</title>
<files>
  - Manual testing only
</files>
<action>
Verify existing fragmented routes continue to work after changes.

Test steps:
1. Navigate directly to /email/[threadId] (valid thread ID)
2. Verify page loads with ThreadContent
3. Verify feature flag guard works (disable flag, confirm redirect to /app)
4. Verify action buttons work (Link to Object, Create Work Order)
5. Verify back navigation works
</action>
<verify>
- /email/[threadId] renders existing page (not EmailLensContent)
- Feature flag redirect works
- Action buttons functional
</verify>
<done>
Fragmented mode continues to work unchanged
</done>
</task>

<task type="auto" id="20-01-05">
<title>Test Button Wiring Both Modes</title>
<files>
  - Manual testing only
</files>
<action>
Test all 7 email actions work in both SPA and fragmented modes.

Actions to test:
1. link_email_to_entity - Link thread to entity
2. unlink_email_from_entity - Remove link
3. create_work_order_from_email - Create WO from email
4. create_fault_from_email - Create fault from email
5. mark_thread_read - Mark as read
6. archive_thread - Archive
7. download_attachment - Download file

Test matrix:
| Action | SPA Mode | Fragmented Mode |
|--------|----------|-----------------|
| link_email_to_entity | Test | Test |
| unlink_email_from_entity | Test | Test |
| create_work_order_from_email | Test | Test |
| create_fault_from_email | Test | Test |
| mark_thread_read | Test | Test |
| archive_thread | Test | Test |
| download_attachment | Test | Test |
</action>
<verify>
- All 7 actions work in SPA mode
- All 7 actions work in fragmented mode
- Permission checks work (buttons hidden for unauthorized roles)
</verify>
<done>
All email actions work in both modes
</done>
</task>

<task type="auto" id="20-01-06">
<title>Verify SACRED OAuth Patterns Unchanged</title>
<files>
  - Git diff verification only
</files>
<action>
Verify no changes to SACRED OAuth files.

Commands:
```bash
git diff HEAD -- apps/web/src/lib/email/oauth-utils.ts
git diff HEAD -- apps/web/src/lib/authHelpers.ts
git diff HEAD -- apps/web/src/hooks/useEmailData.ts
git diff HEAD -- apps/web/src/app/api/integrations/outlook/
```

Expected: All commands return empty (no changes)
</action>
<verify>
- oauth-utils.ts: 0 lines changed
- authHelpers.ts: 0 lines changed
- useEmailData.ts: 0 lines changed
- outlook/ directory: 0 files changed
</verify>
<done>
SACRED OAuth patterns verified unchanged via git diff
</done>
</task>

---

## Requirements Coverage

| Requirement | Task(s) | Status |
|-------------|---------|--------|
| EMAIL-CONV-01: Create EmailLensContent.tsx | 20-01-01 | Addressed |
| EMAIL-CONV-02: Register in LensRenderer.tsx | 20-01-02 | Addressed |
| EMAIL-CONV-03: Verify fragmented routes work | 20-01-04 | Addressed (routes already exist) |
| EMAIL-CONV-04: Test button wiring both modes | 20-01-03, 20-01-04, 20-01-05 | Addressed |
| EMAIL-CONV-05: Preserve SACRED OAuth patterns | 20-01-06 | Addressed |

**Note on EMAIL-CONV-03:** The fragmented routes (`/email`, `/email/[threadId]`, `/email/inbox`) already exist and work. The original roadmap said "Verify/fix" — verification confirms they work, no fix needed.

---

## Execution Order

| Order | Task ID | Description | Dependencies |
|-------|---------|-------------|--------------|
| 1 | 20-01-01 | Create EmailLensContent.tsx | None |
| 2 | 20-01-02 | Register in LensRenderer.tsx | 20-01-01 |
| 3 | 20-01-03 | Test SPA mode | 20-01-02 |
| 4 | 20-01-04 | Test fragmented mode | 20-01-02 |
| 5 | 20-01-05 | Test button wiring | 20-01-03, 20-01-04 |
| 6 | 20-01-06 | Verify OAuth unchanged | All |

---

## Files Summary

### New Files (1)
- `apps/web/src/components/lens/EmailLensContent.tsx` (~120-150 LOC)

### Modified Files (1)
- `apps/web/src/components/lens/LensRenderer.tsx` (+3 lines)

### Unchanged Files (SACRED)
- `apps/web/src/lib/email/oauth-utils.ts`
- `apps/web/src/lib/authHelpers.ts`
- `apps/web/src/hooks/useEmailData.ts`
- `apps/web/src/app/api/integrations/outlook/*`
- `apps/web/src/app/email/[threadId]/page.tsx` (already works)
- `apps/web/src/app/email/page.tsx` (already works)

---

## Success Criteria

Phase 20 is complete when:

- [ ] `EmailLensContent.tsx` exists and renders threads
- [ ] `LensRenderer.tsx` includes 'email' case
- [ ] SPA mode (`/app?entity=email&id=X`) renders via ContextPanel
- [ ] Fragmented mode (`/email/[threadId]`) continues to work
- [ ] All 7 email actions work in both modes
- [ ] Git diff shows 0 changes to SACRED OAuth files
- [ ] TypeScript compiles clean

---

## Estimated Effort

| Task | Estimate |
|------|----------|
| 20-01-01: Create EmailLensContent.tsx | 1-2 hours |
| 20-01-02: Register in LensRenderer.tsx | 15 min |
| 20-01-03: Test SPA mode | 30 min |
| 20-01-04: Test fragmented mode | 30 min |
| 20-01-05: Test button wiring | 1 hour |
| 20-01-06: Verify OAuth unchanged | 15 min |
| **TOTAL** | **3-5 hours** |

---

*Plan created: 2026-03-03*
*Revised after verification: 2026-03-03*
*Key insight: Fragmented routes already exist — focus is SPA mode support*
