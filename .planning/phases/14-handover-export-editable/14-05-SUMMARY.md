---
phase: 14-handover-export-editable
plan: 05
subsystem: api
tags: [fastapi, nextjs, supabase, storage, signatures, handover]

# Dependency graph
requires:
  - phase: 14-02
    provides: handover_exports DB columns (original_storage_url, signed_storage_url, edited_content, user_signature, hod_signature, review_status)
  - phase: 14-03
    provides: parse_handover_html() service function for HTML to editable section structure

provides:
  - Python FastAPI endpoints for full editable handover workflow (content/save-draft/submit/countersign)
  - Next.js proxy route wrappers for all 4 endpoints
  - Two-bucket storage write path (signed bucket on submit + countersign)
  - HOD ledger notification on submit
  - Embedding indexing trigger on countersign

affects: [14-06, 14-07, 14-08]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Append new endpoints to existing router (preserve prior routes)
    - Next.js routes proxy to Python with Authorization passthrough (no createServerClient)
    - Python auth via middleware.auth.get_authenticated_user (not services.auth)
    - _trigger_indexing via search_index_queue table insert (not Render deploy hook)
    - _notify_hod via pms_audit_log INSERT per HOD user

key-files:
  created:
    - apps/web/src/app/api/handover-export/[id]/content/route.ts
    - apps/web/src/app/api/handover-export/[id]/save-draft/route.ts
    - apps/web/src/app/api/handover-export/[id]/submit/route.ts
    - apps/web/src/app/api/handover-export/[id]/countersign/route.ts
  modified:
    - apps/api/routes/handover_export_routes.py
    - apps/web/src/components/lens/handover-export-sections/EditableSectionRenderer.tsx

key-decisions:
  - "Append editable workflow endpoints to existing handover_export_routes.py (do not replace existing generation routes)"
  - "Next.js routes proxy Authorization header directly — no createServerClient (lib/supabase/server does not exist in this codebase)"
  - "Python HOD role check in countersign endpoint (Python layer is authoritative for role enforcement)"
  - "_trigger_indexing uses search_index_queue table insert with error swallowed via try/except (fire-and-forget)"
  - "user.id accessed via hasattr guard (get_authenticated_user may return dict or object depending on middleware)"

patterns-established:
  - "Two-bucket storage: original bucket = AI-generated HTML (immutable), signed bucket = user-edited + signatures"
  - "Submit flow: generate signed HTML → upload to signed bucket → update DB → notify HOD via pms_audit_log"
  - "Countersign flow: re-upload signed HTML with both signatures → update DB → queue indexing"

requirements-completed: []

# Metrics
duration: 15min
completed: 2026-02-18
---

# Phase 14 Plan 05: Two-Bucket Storage + API Endpoints Summary

**FastAPI editable workflow endpoints (content/save-draft/submit/countersign) + Next.js proxy wrappers implementing two-bucket handover export storage with dual-signature workflow and HOD ledger notifications**

## Performance

- **Duration:** 15 min
- **Started:** 2026-02-18T16:20:07Z
- **Completed:** 2026-02-18T16:35:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Added 4 new FastAPI endpoints to existing handover_export_routes.py: GET /content, POST /save-draft, POST /submit, POST /countersign
- Created 4 Next.js API proxy routes under /api/handover-export/[id]/ forwarding Bearer token to Python layer
- Implemented full two-bucket storage write path: user edits uploaded to signed bucket on submit, re-uploaded with both signatures on countersign
- HOD notification via pms_audit_log on submit; embedding indexing via search_index_queue on countersign

## Task Commits

Each task was committed atomically:

1. **Task 1: Python routes for handover export** - `8ec9de8d` (feat)
2. **Task 2: Next.js API route wrappers** - `d122b291` (feat)

**Plan metadata:** [see final commit below]

## Files Created/Modified
- `apps/api/routes/handover_export_routes.py` - Added 4 editable workflow endpoints + 5 Pydantic models + 4 private helpers
- `apps/web/src/app/api/handover-export/[id]/content/route.ts` - GET proxy to Python /content
- `apps/web/src/app/api/handover-export/[id]/save-draft/route.ts` - POST proxy to Python /save-draft
- `apps/web/src/app/api/handover-export/[id]/submit/route.ts` - POST proxy to Python /submit
- `apps/web/src/app/api/handover-export/[id]/countersign/route.ts` - POST proxy to Python /countersign
- `apps/web/src/components/lens/handover-export-sections/EditableSectionRenderer.tsx` - [Rule 1 fix] Removed invalid size="sm" prop

## Decisions Made
- Next.js routes use Authorization header passthrough instead of createServerClient — `@/lib/supabase/server` does not exist in this codebase; all existing API routes use the Bearer token from the incoming request
- Python countersign endpoint re-enforces HOD role check (Python is the authoritative authorization layer; Next.js wrapper skips redundant profile check)
- `_trigger_indexing` uses search_index_queue table insert wrapped in try/except so a missing table never blocks the countersign response

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed invalid `size="sm"` prop on GhostButton in EditableSectionRenderer.tsx**
- **Found during:** Task 2 (TypeScript build verification)
- **Issue:** `GhostButtonProps` interface does not define a `size` field; three GhostButton calls in EditableSectionRenderer.tsx passed `size="sm"` causing 3 TypeScript errors from plan 14-04
- **Fix:** Removed `size="sm"` from all three GhostButton calls (button already has fixed 36px min-height)
- **Files modified:** `apps/web/src/components/lens/handover-export-sections/EditableSectionRenderer.tsx`
- **Verification:** `npx tsc --noEmit` exits with 0 errors
- **Committed in:** `d122b291` (Task 2 commit)

**2. [Rule 3 - Blocking] Adapted Python import paths to match existing codebase**
- **Found during:** Task 1 (reviewing existing file structure)
- **Issue:** Plan spec used `..services.supabase_client` and `..services.auth` but existing routes use `integrations.supabase.get_supabase_client` and `middleware.auth.get_authenticated_user`
- **Fix:** Used correct import paths matching all other routes in the codebase
- **Files modified:** `apps/api/routes/handover_export_routes.py`
- **Verification:** `python3 -c "import ast; ast.parse(...)` syntax check passes
- **Committed in:** `8ec9de8d` (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (1 pre-existing bug, 1 import path mismatch)
**Impact on plan:** Both fixes essential for correctness and build integrity. No scope creep.

## Issues Encountered
- `@/lib/supabase/server` import path from plan spec does not exist; existing codebase uses Authorization header passthrough pattern — handled as Rule 3 adaptation

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 4 API endpoints ready: GET content, POST save-draft, POST submit, POST countersign
- Storage paths follow convention: handover-exports/{yacht_id}/original/{export_id}.html + handover-exports/{yacht_id}/signed/{export_id}.html
- HOD ledger notifications wired via pms_audit_log
- TypeScript build: 0 errors
- Ready for 14-06 (frontend HandoverExportLens wiring to these endpoints)

---
## Self-Check: PASSED

- FOUND: apps/api/routes/handover_export_routes.py
- FOUND: apps/web/src/app/api/handover-export/[id]/content/route.ts
- FOUND: apps/web/src/app/api/handover-export/[id]/save-draft/route.ts
- FOUND: apps/web/src/app/api/handover-export/[id]/submit/route.ts
- FOUND: apps/web/src/app/api/handover-export/[id]/countersign/route.ts
- FOUND: commit 8ec9de8d (Task 1 — Python routes)
- FOUND: commit d122b291 (Task 2 — Next.js routes)

*Phase: 14-handover-export-editable*
*Completed: 2026-02-18*
