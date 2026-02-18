---
phase: FE-02-batch1-lenses
plan: "04"
subsystem: certificate-lens
tags: [lens, certificate, vessel, crew, expiry, vital-signs, sections]
dependency_graph:
  requires:
    - FE-01-01 (LensHeader, LensTitleBlock)
    - FE-01-02 (SectionContainer pattern)
    - FE-01-03 (useWorkOrderActions pattern)
    - FE-01-05 (LensContainer, glass transitions)
    - DS-03 (StatusPill, GhostButton, PrimaryButton)
    - DS-04 (VitalSignsRow)
  provides:
    - CertificateLens component (vessel + crew support)
    - useCertificateActions hook (6 actions, role gates)
    - /certificates/[id] Next.js route
  affects:
    - Certificate E2E tests (future FE-02-0x)
tech_stack:
  added: []
  patterns:
    - WorkOrderLens forwardRef pattern
    - SectionContainer with stickyTop=56
    - execute() wrapper with yacht_id + certificate_id injection
    - Fire-and-forget ledger logging
    - Hide-not-disable role gates
key_files:
  created:
    - apps/web/src/components/lens/CertificateLens.tsx
    - apps/web/src/hooks/useCertificateActions.ts
    - apps/web/src/app/certificates/[id]/page.tsx
  modified:
    - apps/web/src/components/lens/receiving-sections/ReceivingLineItemsSection.tsx (Rule 3 auto-fix)
decisions:
  - Certificate expiry color logic in CertificateLens: critical (expired), warning (<=30 days), success (valid)
  - certificateType prop drives entity link label/href (crew_member vs vessel_name)
  - SectionContainer action prop takes { label, onClick } not ReactNode — inline sections avoid GhostButton wrapper
  - Fetch from /v1/certificates/{id}?type=vessel|crew (no microaction handler for certificates yet)
  - countDisplay string removed from SectionContainer count — pass numeric totalItems only
metrics:
  duration_minutes: 6
  completed_date: "2026-02-17"
  tasks_completed: 5
  files_created: 3
  files_modified: 1
---

# Phase FE-02 Plan 04: Certificate Lens Rebuild Summary

## One-liner

CertificateLens with expiry-color vital signs, DetailsSection, LinkedDocumentsSection, RenewalHistorySection, and 6-action useCertificateActions hook — supports both vessel and crew certificates via certificateType prop.

## What Was Built

### Task 1+2: CertificateLens.tsx (component + sections)

Full-screen entity lens for vessel and crew certificates following the WorkOrderLens reference pattern.

**Component interface:**
```tsx
interface CertificateLensProps {
  certificate: CertificateData;
  certificateType: 'vessel' | 'crew';
  onBack?: () => void;
  onClose?: () => void;
  className?: string;
  onRefresh?: () => void;
}
```

**VitalSignsRow — 5 indicators:**
| # | Label | Value | Color logic |
|---|-------|-------|-------------|
| 1 | Status | Valid / Expiring Soon / Expired / Superseded | StatusPill: critical/warning/success/neutral |
| 2 | Type | certificate_type_name or derived label | Plain text |
| 3 | Expiry | "Expires Jan 23, 2026" or "Expired 5 days ago" | critical (expired), warning (<=30d), success (valid) |
| 4 | Authority | issuing_authority | Plain text |
| 5 | Crew Member / Vessel | crew_member_name or vessel_name | EntityLink href for crew only |

**Sections (all with stickyTop=56):**
- **DetailsSection**: cert number, issue date, expiry date, issuing authority, notes — `dl` grid layout
- **LinkedDocumentsSection**: empty state + doc list, Link Document action (HOD+ only via SectionContainer action prop)
- **RenewalHistorySection**: superseded cert history with issue/expiry/superseded dates, empty state

**Glass transitions:** LensContainer isOpen state machine (300ms ease-out enter, 200ms ease-in exit).

### Task 3: useCertificateActions hook

6 typed action helpers wired to `/v1/certificates/` backend:

| Action | Endpoint | Role gate |
|--------|----------|-----------|
| `viewCertificate` | `/view` | All |
| `createCertificate` | `/create` | HOD+ |
| `updateCertificate` | `/update` | MANAGE_ROLES |
| `findExpiringCertificates` | `/expiring` | HOD+ |
| `linkDocument` | `/link-document` | HOD+ |
| `supersedeCertificate` | `/supersede` | captain/manager |

`useCertificatePermissions` returns 6 boolean flags (canView, canCreate, canUpdate, canFindExpiring, canLinkDocument, canSupersede) — used to hide (not disable) action buttons.

### Task 4: certificates/[id]/page.tsx

Dynamic route wired to CertificateLens. Determines certificate type from `?type=vessel|crew` query param (default: vessel). Fetches from backend API with JWT auth. Ledger logging fire-and-forget on navigate_to_lens, navigate_back, close_lens.

### Task 5: Build verification

Build compiles successfully — TypeScript 0 errors, 16 routes generated including `/certificates/[id]`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] SectionContainer action prop is `{label, onClick}` not ReactNode**
- **Found during:** Task 2 — LinkedDocumentsSection
- **Issue:** Plan suggested passing GhostButton ReactNode as `action` prop to SectionContainer, but SectionContainer.action is typed as `{ label: string; onClick: () => void } | undefined`
- **Fix:** Changed LinkedDocumentsSection to pass `{ label: 'Link Document', onClick: onLinkDocument }` and removed GhostButton from that section
- **Files modified:** CertificateLens.tsx (LinkedDocumentsSection)
- **Commit:** 39f54e95

**2. [Rule 3 - Blocking] Pre-existing TypeScript error in ReceivingLineItemsSection.tsx**
- **Found during:** Task 5 build verification
- **Issue:** `countDisplay` was typed as `string | number` (template literal `${totalItems} (${shortCount} short)`) but `SectionContainer.count` accepts `number | undefined` only — blocked TypeScript compilation
- **Fix:** Removed `countDisplay` variable, pass `totalItems` (number) directly to `count` prop
- **Files modified:** `apps/web/src/components/lens/receiving-sections/ReceivingLineItemsSection.tsx`
- **Commit:** 892c3c23
- **Out-of-scope note:** `DescriptionSection.tsx` and `FaultPhotosSection.tsx` were untracked files picked up in the same commit — they were pre-existing working-tree files, not created by this plan.

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 39f54e95 | feat | CertificateLens component with sections |
| a738e191 | feat | useCertificateActions hook with role permissions |
| 79cd00a2 | feat | Wire certificates/[id]/page.tsx to CertificateLens |
| 892c3c23 | fix | Fix pre-existing TS error in ReceivingLineItemsSection |

## Self-Check

Files created:
- [x] apps/web/src/components/lens/CertificateLens.tsx — FOUND
- [x] apps/web/src/hooks/useCertificateActions.ts — FOUND
- [x] apps/web/src/app/certificates/[id]/page.tsx — FOUND

Commits:
- [x] 39f54e95 — FOUND
- [x] a738e191 — FOUND
- [x] 79cd00a2 — FOUND
- [x] 892c3c23 — FOUND

Build: TypeScript compiled successfully, 16 routes including /certificates/[id]

## Self-Check: PASSED
