---
wave: 1
depends_on: []
files_modified:
  - apps/web/src/components/lens/EquipmentLens.tsx
  - apps/web/src/app/equipment/[id]/page.tsx
autonomous: true
requirements: [EQUIP-03]
---

# Plan FE-02-02: Equipment Lens Rebuild

## Objective

Rebuild Equipment lens to Work Order standard: LensHeader, VitalSignsRow with 5 indicators (status, location, make/model, linked faults count, linked work orders count), section containers (Specifications, Maintenance History, Linked Faults, Linked Work Orders, Documents), full-screen layout.

## Tasks

<task id="1">
Create EquipmentLens.tsx:

```tsx
interface EquipmentLensProps {
  equipment: EquipmentData;
  onBack?: () => void;
  onClose: () => void;
}
```

VitalSignsRow with 5 signs:
- Status (active/inactive/maintenance) - StatusPill
- Location (deck/compartment)
- Make/Model (combined string)
- Faults ("N open faults") - count, EntityLink to fault list
- Work Orders ("N active WOs") - count, EntityLink
</task>

<task id="2">
Create equipment-specific sections:

- **SpecificationsSection** - Serial number, manufacturer, installation date, warranty info
- **MaintenanceHistorySection** - Timeline of maintenance events
- **LinkedFaultsSection** - List of faults referencing this equipment, each as EntityLink
- **LinkedWorkOrdersSection** - List of WOs for this equipment
- **DocumentsSection** - Manuals, certificates linked to equipment

All sections use SectionContainer with stickyTop={56}.
</task>

<task id="3">
Create useEquipmentActions hook:

Actions:
- view_equipment
- update_equipment
- link_document
- create_work_order (from equipment)
- report_fault (from equipment)

Role-based visibility.
</task>

<task id="4">
Wire equipment/[id]/page.tsx:

1. Fetch equipment data with linked faults/WOs counts
2. Render EquipmentLens
3. Handle navigation
4. Log to ledger
</task>

<task id="5">
Verify build passes:

```bash
cd apps/web && npm run build
```
</task>

## Verification

```bash
cd apps/web && npm run build
ls apps/web/src/components/lens/EquipmentLens.tsx
```

## must_haves

- [ ] EquipmentLens.tsx with full-screen layout
- [ ] VitalSignsRow with 5 equipment-specific indicators
- [ ] Linked Faults and Work Orders sections with EntityLinks
- [ ] Specifications section
- [ ] useEquipmentActions hook
- [ ] Build passes
