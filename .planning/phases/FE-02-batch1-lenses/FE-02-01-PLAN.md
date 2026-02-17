---
wave: 1
depends_on: []
files_modified:
  - apps/web/src/components/lens/FaultLens.tsx
  - apps/web/src/app/faults/[id]/page.tsx
autonomous: true
requirements: [FAULT-03]
---

# Plan FE-02-01: Fault Lens Rebuild

## Objective

Rebuild Fault lens to Work Order standard: LensHeader, VitalSignsRow with 5 indicators (status, severity, equipment link, reporter, age), section containers (Description, Photos, Notes, History), full-screen layout with glass transitions.

## Pre-work

<task id="0">
Read Fault pipeline docs and discover table structure:
- `/docs/pipeline/entity_lenses/fault/Scope.md` (if exists)
- Query pms_faults table columns

```bash
grep -rn "pms_faults" /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/ --include="*.py" | head -20
```
</task>

## Tasks

<task id="1">
Create FaultLens.tsx using Work Order as template:

```tsx
interface FaultLensProps {
  fault: FaultData;
  onBack?: () => void;
  onClose: () => void;
}
```

Components to use:
- LensContainer (full-screen + glass)
- LensHeader (back/close)
- LensTitleBlock (title = fault summary, no UUID)
- VitalSignsRow with 5 signs:
  - Status (open/acknowledged/diagnosed/closed) - StatusPill
  - Severity (critical/high/medium/low) - StatusPill
  - Equipment (linked equipment name) - EntityLink
  - Reporter (crew member name)
  - Age (relative date)
</task>

<task id="2">
Create fault-specific sections:

- **DescriptionSection** - Full fault description, read-only
- **PhotosSection** - MediaRenderer for fault photos, Add Photo button
- **NotesSection** - Reuse from Work Order
- **HistorySection** - Reuse from Work Order

All sections use SectionContainer with stickyTop={56}.
</task>

<task id="3">
Create useFaultActions hook:

Actions per registry:
- report_fault
- acknowledge_fault
- diagnose_fault
- close_fault
- reopen_fault
- mark_false_alarm
- add_photo
- add_note

Role-based visibility same pattern as useWorkOrderActions.
</task>

<task id="4">
Wire faults/[id]/page.tsx:

1. Fetch fault data
2. Render FaultLens
3. Handle navigation (back/close)
4. Log to ledger on open
</task>

<task id="5">
Verify build passes:

```bash
cd apps/web && npm run build
```
</task>

## Verification

```bash
# Build passes
cd apps/web && npm run build

# FaultLens exists
ls apps/web/src/components/lens/FaultLens.tsx

# No UUID in lens (search for uuid render)
grep -n "fault\.id\|fault_id" apps/web/src/components/lens/FaultLens.tsx | grep -v "// " | wc -l
```

## must_haves

- [ ] FaultLens.tsx with LensContainer wrapper
- [ ] VitalSignsRow with 5 fault-specific indicators
- [ ] Section containers with sticky headers
- [ ] useFaultActions hook
- [ ] No UUID visible to user
- [ ] Build passes
