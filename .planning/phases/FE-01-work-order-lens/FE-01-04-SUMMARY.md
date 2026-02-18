---
phase: FE-01-work-order-lens
plan: "04"
subsystem: ui
tags: [react, media, file-rendering, signed-urls, tanstack-query, lightbox]

# Dependency graph
requires:
  - phase: FE-01-02
    provides: AttachmentsSection with inline MediaItem and DocumentCard stubs
  - phase: 00-design-system
    provides: semantic tokens (surface-primary, txt-tertiary, brand-interactive, etc.)

provides:
  - Standalone MediaRenderer component in /components/media/
  - Standalone DocumentCard component in /components/media/
  - fileUtils.ts: getFileCategory, formatFileSize, getDocumentIcon, getAttachmentKind
  - Signed URL detection + auto-fetch via useQuery
  - Full-screen lightbox overlay for media
  - AttachmentsSection wired to standalone components

affects:
  - FE-01-05 (subsequent work order sections referencing attachments)
  - Any lens needing file rendering (DocumentCard, MediaRenderer are reusable across lenses)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "token= URL param check before fetching signed URLs — avoids redundant API calls"
    - "useQuery staleTime 55min for signed URLs (auto-refetch 5min before 1hr expiry)"
    - "MediaRenderer accepts MediaFile interface with mime_type for MIME-based category detection"
    - "AttachmentsSection uses extension-based getAttachmentKind for partitioning (MIME unreliable from signed URLs)"
    - "fileUtils.ts is the canonical location for all file category/size/icon utilities"

key-files:
  created:
    - apps/web/src/components/media/MediaRenderer.tsx
    - apps/web/src/components/media/DocumentCard.tsx
    - apps/web/src/components/media/fileUtils.ts
    - apps/web/src/components/media/index.ts
  modified:
    - apps/web/src/components/lens/sections/AttachmentsSection.tsx
    - apps/web/src/components/lens/sections/index.ts

key-decisions:
  - "MediaRenderer uses MIME-based getFileCategory (reliable when typed file object available)"
  - "AttachmentsSection uses extension-based getAttachmentKind for partitioning (MIME unreliable from storage URLs)"
  - "Signed URL check: token= param presence; staleTime 55min before 1hr expiry"
  - "Lightbox uses fixed z-[9999] overlay, Escape + backdrop click to close"
  - "fileUtils exported from /components/media/ — sections/index.ts re-exports for backward compat"

patterns-established:
  - "MediaFile interface: {id, url, filename, mime_type, size_bytes} — reusable across lenses"
  - "DocumentFile interface: same shape as MediaFile — consistent file contract"
  - "Skeleton + hidden media element pattern: show skeleton until onLoad/onLoadedMetadata fires"

requirements-completed:
  - WO-03

# Metrics
duration: 5min
completed: 2026-02-17
---

# Phase FE-01 Plan 04: File Rendering Summary

**Standalone MediaRenderer (images/videos with lightbox + signed URL handling) and DocumentCard (48px preview card with icon/size/chevron) extracted to /components/media/, wired into AttachmentsSection**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-02-17T21:24:57Z
- **Completed:** 2026-02-17T21:29:41Z
- **Tasks:** 6 (Tasks 1-5 implemented, Task 6 verified)
- **Files modified:** 6

## Accomplishments

- Created `MediaRenderer` with loading skeleton, error state, click-to-fullscreen lightbox, and signed URL auto-fetch
- Created `DocumentCard` matching UI_SPEC.md File Preview Card spec (48px, icon + filename + size + chevron)
- Created `fileUtils.ts` as canonical location for getFileCategory, formatFileSize, getDocumentIcon, getAttachmentKind
- Updated `AttachmentsSection` to import standalone components — inline MediaItem/DocumentCard removed
- Signed URL handling: checks `token=` param presence, uses `useQuery` with 55min staleTime to fetch fresh URLs
- Build: 16/16 routes, 0 TypeScript errors

## Task Commits

Each task committed atomically:

1. **Task 3: fileUtils.ts utility** - `adf1c94d` (feat)
2. **Task 1: MediaRenderer** - `dff941ae` (feat)
3. **Task 2: DocumentCard** - `9733e87f` (feat)
4. **chore: media barrel index** - `7fec203b` (chore)
5. **Task 4: AttachmentsSection refactor** - `a8437390` (refactor)

## Files Created/Modified

- `apps/web/src/components/media/fileUtils.ts` - getFileCategory (MIME), getFileCategoryFromExtension, getAttachmentKind (extension), formatFileSize, getDocumentIcon, extension sets
- `apps/web/src/components/media/MediaRenderer.tsx` - Inline image/video renderer with skeleton, error state, lightbox, signed URL check via useQuery
- `apps/web/src/components/media/DocumentCard.tsx` - 48px clickable preview card (icon + filename/size + chevron)
- `apps/web/src/components/media/index.ts` - Barrel export for all media components
- `apps/web/src/components/lens/sections/AttachmentsSection.tsx` - Refactored to use standalone components; Attachment interface updated with required mime_type/size_bytes
- `apps/web/src/components/lens/sections/index.ts` - getAttachmentKind re-exported from canonical fileUtils location

## Decisions Made

- **MIME vs extension for category detection:** MediaRenderer/DocumentCard use MIME type (reliable when the typed file object is available). AttachmentsSection partitioning uses extension-based `getAttachmentKind` (consistent with the existing STATE.md decision: "MIME unreliable from signed storage URLs").
- **Signed URL staleTime 55min:** Signed URLs expire after 1 hour. Caching for 55 minutes ensures auto-refetch 5 minutes before expiry, preventing 401s on open sessions.
- **fileUtils.ts as canonical location:** Moved out of AttachmentsSection into /components/media/ so both MediaRenderer and DocumentCard can share without circular imports. Backward-compat re-export added to sections/index.ts.
- **Lightbox z-[9999]:** Above all other overlays (modals use z-50, z-header is lower).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Consolidated dual authHelpers imports in MediaRenderer**
- **Found during:** Task 5 (signed URL implementation)
- **Issue:** Initial write had two separate `import { getAuthHeaders } from '@/lib/authHelpers'` and `import { getYachtId } from '@/lib/authHelpers'` lines
- **Fix:** Merged into single `import { getAuthHeaders, getYachtId } from '@/lib/authHelpers'`
- **Files modified:** MediaRenderer.tsx
- **Verification:** Build passes, no duplicate import warnings
- **Committed in:** dff941ae (part of Task 1 commit)

**2. [Rule 2 - Missing Critical] Added getAttachmentKind re-export to sections/index.ts**
- **Found during:** Task 4 (AttachmentsSection refactor)
- **Issue:** sections/index.ts exported `getAttachmentKind` from AttachmentsSection — moving it to fileUtils would break any consumers importing via sections barrel
- **Fix:** Added re-export of getAttachmentKind from @/components/media/fileUtils in sections/index.ts
- **Files modified:** apps/web/src/components/lens/sections/index.ts
- **Verification:** Build passes, no broken imports
- **Committed in:** a8437390 (Task 4 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking import fix, 1 missing backward-compat export)
**Impact on plan:** Both fixes essential for correctness. No scope creep.

## Issues Encountered

None — plan executed with minor import consolidation fixes.

## User Setup Required

None - no external service configuration required. Signed URL fetching is wired to existing backend signing endpoint pattern (`/v1/files/{id}/signed-url`) — requires backend endpoint to exist when files lack token= URLs.

## Next Phase Readiness

- MediaRenderer and DocumentCard are reusable across all lenses (Certificate, Equipment, Fault, etc.)
- AttachmentsSection ready for integration into full WorkOrderLens page with `onDocumentClick` wired to Document lens navigation
- fileUtils.ts available as shared utility for any new lens section that handles files

---
*Phase: FE-01-work-order-lens*
*Completed: 2026-02-17*
