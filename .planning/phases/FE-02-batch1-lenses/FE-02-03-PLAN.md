---
wave: 1
depends_on: []
files_modified:
  - apps/web/src/components/lens/PartsLens.tsx
  - apps/web/src/app/parts/[id]/page.tsx
autonomous: true
requirements: [PART-03]
---

# Plan FE-02-03: Parts/Inventory Lens Rebuild

## Objective

Rebuild Parts lens to Work Order standard: LensHeader, VitalSignsRow with 5 indicators (stock level, location, unit, reorder point, supplier), section containers (Stock Info, Transaction History, Linked Equipment, Documents), full-screen layout.

## Tasks

<task id="1">
Create PartsLens.tsx:

```tsx
interface PartsLensProps {
  part: PartData;
  onBack?: () => void;
  onClose: () => void;
}
```

VitalSignsRow with 5 signs:
- Stock Level ("N units") - StatusPill if low stock (warning)
- Location (storage location)
- Unit (each/box/liter/etc)
- Reorder Point ("Reorder at N")
- Supplier (supplier name)
</task>

<task id="2">
Create parts-specific sections:

- **StockInfoSection** - Current stock, min stock, max stock, reorder point, unit cost
- **TransactionHistorySection** - Consume, receive, transfer, adjust, write-off events
- **LinkedEquipmentSection** - Equipment that uses this part
- **DocumentsSection** - Spec sheets, MSDS

All sections use SectionContainer with stickyTop={56}.
</task>

<task id="3">
Create usePartActions hook:

Actions:
- view_part
- consume_part
- receive_part
- transfer_part
- adjust_stock
- write_off
- add_to_shopping_list

Role-based visibility (crew can consume, HOD can adjust/write-off).
</task>

<task id="4">
Wire parts/[id]/page.tsx:

1. Fetch part data with stock level
2. Render PartsLens
3. Handle navigation
4. Log to ledger
</task>

<task id="5">
Build verification:

```bash
cd apps/web && npm run build
```
</task>

## Verification

```bash
cd apps/web && npm run build
ls apps/web/src/components/lens/PartsLens.tsx
```

## must_haves

- [ ] PartsLens.tsx with full-screen layout
- [ ] VitalSignsRow with stock level indicator
- [ ] Low stock warning via StatusPill
- [ ] Transaction history section
- [ ] usePartActions hook with consume/receive
- [ ] Build passes
