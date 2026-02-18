---
wave: 1
depends_on: []
files_modified:
  - apps/web/src/components/lens/HoursOfRestLens.tsx
  - apps/web/src/app/hours-of-rest/[id]/page.tsx
autonomous: true
requirements: [HOR-03]
---

# Plan FE-03-03: Hours of Rest Lens Rebuild

## Objective

Rebuild Hours of Rest lens for STCW compliance: LensHeader, VitalSignsRow (compliance status, crew member, date range, violations count, sign-off status), sections (Daily Log, Warnings, Monthly Sign-off).

## Tasks

<task id="1">
Create HoursOfRestLens.tsx:

VitalSignsRow with 5 signs:
- Compliance (compliant/warning/violation) - StatusPill with color
- Crew Member (name)
- Period (date range, e.g., "Feb 1-28, 2026")
- Violations ("N violations" or "None")
- Sign-off ("Signed" or "Pending")
</task>

<task id="2">
Create HOR-specific sections:

- **DailyLogSection** - Daily rest periods, work hours, visual timeline
- **WarningsSection** - STCW violations with acknowledge button
- **MonthlySignOffSection** - Sign-off status, signature if required

Special: Visual timeline showing rest vs work periods per day.
</task>

<task id="3">
Create useHoursOfRestActions hook:

Actions:
- log_hours
- upsert_hours
- get_hours
- create_signoff
- sign_monthly
- list_warnings
- acknowledge_warning
- create_template
- apply_template

Role-based: crew logs own hours, captain signs off.
</task>

<task id="4">
Implement STCW compliance indicators:

- Green: Meets minimum rest requirements
- Amber: Close to violation threshold
- Red: STCW violation (requires acknowledgment)

Visual timeline: 24-hour bar showing rest (green) vs work (gray) blocks.
</task>

<task id="5">
Wire hours-of-rest/[id]/page.tsx and verify build.
</task>

## must_haves

- [ ] HoursOfRestLens.tsx with full-screen layout
- [ ] VitalSignsRow with compliance status
- [ ] Daily log with visual timeline
- [ ] STCW violation warnings with acknowledge
- [ ] Monthly sign-off flow
- [ ] Build passes
