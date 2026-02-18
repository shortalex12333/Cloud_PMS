---
wave: 1
depends_on: []
files_modified:
  - apps/web/src/components/lens/ReceivingLens.tsx
  - apps/web/src/app/receiving/[id]/page.tsx
autonomous: true
requirements: [RECV-03]
---

# Plan FE-03-01: Receiving Lens Rebuild

## Objective

Rebuild Receiving lens to Work Order standard with rejection flow per CLAUDE.md: LensHeader, VitalSignsRow (status, supplier, PO number, items count, receiver), sections (Line Items, Documents, History), full rejection workflow with reason dropdown and signature.

## Tasks

<task id="1">
Create ReceivingLens.tsx following WorkOrderLens pattern:

VitalSignsRow with 5 signs:
- Status (draft/pending/accepted/rejected) - StatusPill
- Supplier (supplier name)
- PO Number (purchase order reference)
- Items ("N items")
- Receiver (who created it)

Full-screen layout with LensContainer, glass transitions.
</task>

<task id="2">
Create receiving-specific sections:

- **LineItemsSection** - List of received items with quantities, condition
- **DocumentsSection** - Delivery notes, invoices, packing lists
- **HistorySection** - Reuse from Work Order

Use ReceivingLineItemsSection and ReceivingDocumentsSection if they exist.
</task>

<task id="3">
Create useReceivingActions hook:

Actions per registry:
- create_receiving (all crew)
- add_receiving_item
- update_receiving_fields
- accept_receiving (HOD+ with signature)
- reject_receiving (HOD+ with reason)
- view_receiving_history

Role-based visibility: crew can create/edit draft, HOD can accept/reject.
</task>

<task id="4">
Implement rejection flow per CLAUDE.md:

1. Reject button opens RejectModal
2. RejectModal has reason dropdown (standard reasons + "Other")
3. If "Other", show text input
4. Rejection requires signature
5. Optional email notification with template
6. After reject, status changes to "rejected"
</task>

<task id="5">
Wire receiving/[id]/page.tsx and verify build:

```bash
cd apps/web && npm run build
```
</task>

## Verification

```bash
cd apps/web && npm run build
ls apps/web/src/components/lens/ReceivingLens.tsx
```

## must_haves

- [ ] ReceivingLens.tsx with full-screen layout
- [ ] VitalSignsRow with 5 receiving-specific indicators
- [ ] Line Items section with quantities
- [ ] Rejection flow with reason dropdown + signature
- [ ] useReceivingActions hook
- [ ] Build passes
