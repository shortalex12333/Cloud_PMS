---
phase: FE-03-batch2-lenses
plan: "02"
subsystem: handover-lens
tags: [handover, lens, dual-signature, crew-rotation, pdf-export]
dependency_graph:
  requires:
    - FE-01-work-order-lens (LensHeader, LensContainer, VitalSignsRow, SectionContainer pattern)
    - FE-02-batch1-lenses (FaultLens, PartsLens patterns)
    - DS-03 (GhostButton, PrimaryButton, StatusPill, EntityLink, SectionContainer)
    - DS-04 (VitalSignsRow)
  provides:
    - HandoverLens (full-screen handover view)
    - useHandoverActions (handover action hook)
    - HandoverItemsSection, SignaturesSection, HandoverExportsSection
    - /handover/[id] route
  affects:
    - FE-03-03..06 (other Batch 2 lenses can reference this pattern)
tech_stack:
  added: []
  patterns:
    - Dual signature flow (outgoing → incoming → complete) via SignaturePrompt overlay
    - Status derived from export signatures (draft/pending_signatures/complete)
    - Section co-location in handover-sections/ subdirectory
    - Direct Supabase query in page.tsx (no dedicated view handler)
key_files:
  created:
    - apps/web/src/components/lens/HandoverLens.tsx
    - apps/web/src/components/lens/handover-sections/HandoverItemsSection.tsx
    - apps/web/src/components/lens/handover-sections/SignaturesSection.tsx
    - apps/web/src/components/lens/handover-sections/HandoverExportsSection.tsx
    - apps/web/src/components/lens/handover-sections/index.ts
    - apps/web/src/hooks/useHandoverActions.ts
    - apps/web/src/app/handover/[id]/page.tsx
  modified: []
decisions:
  - Derive handover status from export signatures (no separate status column needed)
  - Direct Supabase query in page.tsx — no dedicated viewHandover microaction handler yet
  - SignatureStep state machine (none/outgoing/incoming) renders SignaturePrompt overlay
  - canSignOutgoing/canSignIncoming: role check in hook + crew_id/status check in lens
  - HandoverCard types reused (HandoverItem, HandoverExport interfaces) as model reference
metrics:
  duration_seconds: 461
  completed_date: "2026-02-17"
  tasks_completed: 5
  tasks_total: 5
  files_created: 7
  files_modified: 0
---

# Phase FE-03 Plan 02: Handover Lens Rebuild Summary

Handover Lens for crew rotation sign-off with dual signature workflow and PDF export.

## What Was Built

**HandoverLens.tsx** — Full-screen glass overlay lens for crew rotation handovers.

- `LensHeader`: "Handover" overline, 56px fixed header, back/close buttons
- `LensTitleBlock`: handover title + department subtitle + status StatusPill
- `VitalSignsRow`: 5 indicators — Status (StatusPill), Outgoing crew name, Incoming crew name, Items count, Export status ("PDF Ready" / "Not Exported")
- Dual signature state machine: `none` → `outgoing` → `incoming` → signs submitted
- Signature progress banner during `pending_signatures` state (which crew has signed)
- Role-gated action buttons: Finalize, Sign as Outgoing, Sign as Incoming, Export to PDF

**Handover Sections** (in `handover-sections/` subdirectory):

1. `HandoverItemsSection` — Items grouped by priority (Critical → Action Required → FYI), each with entity icon, category badge, EntityLink to source entity, Acknowledge CTA
2. `SignaturesSection` — Two signature cards side-by-side (Outgoing/Incoming), completion banner when both signed, sequence explanation
3. `HandoverExportsSection` — Export history rows with dual-signature status, download links, "Export PDF" CTA (only when canExport)

**useHandoverActions hook** — 8 typed action helpers:
- `addHandoverItem`, `editHandoverItem` (crew+, draft state)
- `validateHandover`, `finalizeHandover` (HOD+)
- `signOutgoing`, `signIncoming` (dual signature flow)
- `exportHandover` (captain+, complete status)
- `acknowledgeItem` (any crew)

**useHandoverPermissions** — 7 role flags (canAddItem, canEditItem, canFinalize, canSignOutgoing, canSignIncoming, canExport, canAcknowledge)

**handover/[id]/page.tsx** — Page component with Supabase direct fetch, status derivation from signatures, fire-and-forget ledger logging.

## Dual Signature Flow

1. HOD+ clicks **Finalize Handover** → `status: draft → pending_signatures` (locked)
2. Outgoing crew clicks **Sign as Outgoing** → `SignaturePrompt` overlay with outgoing diffs
3. After signing, incoming crew clicks **Sign as Incoming** → `SignaturePrompt` with incoming diffs
4. Both signatures present → `status: complete`
5. Captain+ sees **Export to PDF** button → `HandoverExportsSection` shows export history

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

### Discovery: No HandoverItemsSection/HandoverExportsSection as standalone files

**Found during:** Task 2 review

These existed as private sub-components inside `HandoverCard.tsx` (not exported). Per plan instruction to "Use these if they exist" — extracted the pattern and logic into proper standalone section components in `handover-sections/` following the `parts-sections/` and `equipment/` subdirectory pattern used by other lenses.

### Discovery: No viewHandover microaction handler

**Found during:** Task 5

The `handover.ts` microaction file contains `addToHandover`, `exportHandover`, `editHandoverSection` but no `viewHandover`. Per the certificates pattern (STATE.md: "Fetch /v1/certificates/{id}?type=vessel|crew direct in page.tsx"), used direct Supabase queries in page.tsx. Status is derived from export signature records.

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Derive status from export signatures | No separate status column; signoff_complete + signed_at fields on exports are the ground truth |
| Direct Supabase query in page.tsx | No dedicated viewHandover microaction handler; consistent with certificate pattern |
| SignatureStep state machine (none/outgoing/incoming) | Renders SignaturePrompt overlay without full modal — matches UX spec ownership transfer pattern |
| handover-sections/ subdirectory | Consistent with parts-sections/, sections/equipment/ pattern; sections are lens-specific |
| canSignOutgoing/Incoming: role + crew_id check | Role in hook (base capability), crew_id/status check in lens (contextual gate) |

## Build Verification

- TypeScript: zero errors in all new files (`tsc --noEmit`)
- Pre-existing error: `hours-of-rest/[id]/page.tsx` (2 errors, out of scope per scope boundary rule — logged)
- Next.js: compiled successfully, `/handover/[id]` = ƒ dynamic route
- Route count: `/handover/[id]` added (8.57 kB, 202 kB First Load JS)

## Self-Check: PASSED

All 7 created files verified on disk. All 3 FE-03-02 commits verified in git log.

| Check | Result |
|-------|--------|
| HandoverLens.tsx | FOUND |
| HandoverItemsSection.tsx | FOUND |
| SignaturesSection.tsx | FOUND |
| HandoverExportsSection.tsx | FOUND |
| handover-sections/index.ts | FOUND |
| useHandoverActions.ts | FOUND |
| handover/[id]/page.tsx | FOUND |
| Commit d1327a9a (Lens + sections) | VERIFIED |
| Commit 0397816b (useHandoverActions) | VERIFIED |
| Commit e5cde0f3 (page.tsx + build) | VERIFIED |
