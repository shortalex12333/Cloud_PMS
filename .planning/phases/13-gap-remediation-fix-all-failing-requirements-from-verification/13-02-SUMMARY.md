---
phase: 13-gap-remediation
plan: 02
subsystem: ui
tags: [react, typescript, certificate, frontend, card-component]

# Dependency graph
requires:
  - phase: 06-certificate
    provides: Certificate lens backend and data model
provides:
  - CertificateCard.tsx frontend component for certificate lens
  - Status badge rendering for valid/expiring_soon/expired/superseded
  - Expiry countdown indicator with color-coded thresholds
  - Documents and audit history sections
affects: [certificate-lens, frontend-cards]

# Tech tracking
tech-stack:
  added: []
  patterns: [tokenized-css-variables, card-component-pattern]

key-files:
  created:
    - apps/web/src/components/cards/CertificateCard.tsx
  modified: []

key-decisions:
  - "Follow WorkOrderCard pattern for consistency"
  - "Color-coded expiry thresholds: green (90+ days), orange (30-90 days), red (< 30 days)"

patterns-established:
  - "Certificate card structure: header -> metadata grid -> documents -> audit history"

requirements-completed: [CERT-03]

# Metrics
duration: 2min
completed: 2026-02-17
---

# Phase 13 Plan 02: CertificateCard Component Summary

**CertificateCard.tsx frontend component with status badges, expiry countdown, documents section, and audit history following WorkOrderCard patterns**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-17T16:26:26Z
- **Completed:** 2026-02-17T16:28:32Z
- **Tasks:** 1
- **Files created:** 1

## Accomplishments
- Created CertificateCard.tsx component (455 lines)
- Implemented all four status states with appropriate icons and colors
- Added expiry countdown indicator with color-coded thresholds
- Included linked documents section with empty state CTA
- Added audit history section with human-readable action labels

## Task Commits

Each task was committed atomically:

1. **Task 1: Create CertificateCard component** - `3c9662e1` (feat)

## Files Created/Modified
- `apps/web/src/components/cards/CertificateCard.tsx` - Full-screen entity view for vessel and crew certificates

## Decisions Made
- Followed WorkOrderCard.tsx as the reference pattern for consistency
- Used tokenized CSS variables (--celeste-*) for design system compliance
- Implemented color-coded expiry thresholds: green (90+ days), orange (30-90 days), red (< 30 days/expired)
- Included empty state CTAs for missing documents section

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- CertificateCard component ready for integration with certificate lens
- Component exports CertificateCard function
- TypeScript compilation verified

## Self-Check: PASSED

- FOUND: apps/web/src/components/cards/CertificateCard.tsx
- FOUND: 3c9662e1 (Task 1 commit)

---
*Phase: 13-gap-remediation*
*Completed: 2026-02-17*
