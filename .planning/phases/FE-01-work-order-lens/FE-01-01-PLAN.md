---
wave: 1
depends_on: []
files_modified:
  - apps/web/src/components/lens/WorkOrderLens.tsx
  - apps/web/src/components/lens/LensHeader.tsx
  - apps/web/src/components/ui/VitalSignsRow.tsx
autonomous: true
requirements: [WO-03]
---

# Plan FE-01-01: Work Order Lens Header + Vital Signs

## Objective

Rebuild the Work Order lens header to match CLAUDE.md spec: entity type label, human-readable title (NO UUID), vital signs row with 5 indicators (status, priority, parts count, age, equipment link).

## Pre-work

<task id="0">
Read Work Order pipeline docs to understand the data model:
- `/docs/pipeline/entity_lenses/work_order/Scope.md`
- `/docs/pipeline/entity_lenses/work_order/Actions.md`

Query Supabase to discover actual table structure:
```sql
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'pms_work_orders';
```
</task>

## Tasks

<task id="1">
Create or update `LensHeader.tsx` as a reusable component:

```tsx
interface LensHeaderProps {
  entityType: string;           // "Work Order", "Fault", etc.
  title: string;                // Human-readable title
  subtitle?: string;            // Optional description
  status?: { label: string; color: 'critical' | 'warning' | 'success' | 'neutral' };
  priority?: { label: string; color: 'critical' | 'warning' | 'success' | 'neutral' };
  onBack?: () => void;
  onClose?: () => void;
}
```

Visual spec:
- Fixed at top of lens
- Back button (left): `[← Back]` ghost button, text-brand-interactive
- Entity type label (center-left): text-txt-tertiary, 13px, uppercase
- Close button (right): `[×]` ghost button
- Height: 56px
- Background: transparent (glass over lens content)
</task>

<task id="2">
Build the title + subtitle block below header:

- Title: text-txt-primary, 28px, font-semibold
- Subtitle: text-txt-secondary, 16px, max 2 lines truncated
- Status pill inline with title (using StatusPill component)
- Priority pill if present
</task>

<task id="3">
Wire VitalSignsRow to Work Order with these 5 signs:

```tsx
const workOrderVitalSigns: VitalSign[] = [
  { label: 'Status', value: workOrder.status, color: mapStatusToColor(workOrder.status) },
  { label: 'Priority', value: workOrder.priority, color: mapPriorityToColor(workOrder.priority) },
  { label: 'Parts', value: `${partsCount} parts` },
  { label: 'Created', value: formatRelativeDate(workOrder.created_at) },
  { label: 'Equipment', value: equipment?.name || 'None', href: equipment ? `/equipment/${equipment.id}` : undefined },
];
```

Equipment link should be `text-brand-interactive` and clickable.
</task>

<task id="4">
Update `WorkOrderLens.tsx` to use the new header structure:

1. Replace any existing header with `<LensHeader />`
2. Add title block with status/priority pills
3. Add `<VitalSignsRow signs={workOrderVitalSigns} />`
4. Ensure NO UUID is visible anywhere in the header
</task>

<task id="5">
Test the header renders correctly:

```bash
cd apps/web && npm run build
```

Visual verification: Screenshot the Work Order lens header showing:
- Entity type label "WORK ORDER"
- Human title (not UUID)
- Status and priority pills
- Vital signs row with 5 indicators
</task>

## Verification

```bash
# Build passes
cd apps/web && npm run build

# No UUIDs visible in header
grep -n "uuid\|UUID" apps/web/src/components/lens/WorkOrderLens.tsx | grep -v "// " | wc -l
# Should be 0 visible in JSX

# VitalSignsRow imported and used
grep -n "VitalSignsRow" apps/web/src/components/lens/WorkOrderLens.tsx
```

## must_haves

- [ ] LensHeader component created with back/close buttons
- [ ] Title displays human-readable text, NO UUID
- [ ] Status and Priority pills visible inline
- [ ] VitalSignsRow shows 5 indicators
- [ ] Equipment link is teal and clickable
- [ ] Build passes
