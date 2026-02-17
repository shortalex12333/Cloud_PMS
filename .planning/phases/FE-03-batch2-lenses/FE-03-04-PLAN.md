---
wave: 1
depends_on: []
files_modified:
  - apps/web/src/components/lens/WarrantyLens.tsx
  - apps/web/src/app/warranty/[id]/page.tsx
autonomous: true
requirements: [WARR-03]
---

# Plan FE-03-04: Warranty Lens Rebuild

## Objective

Rebuild Warranty Claims lens: LensHeader, VitalSignsRow (status, equipment, fault, supplier, claim date), sections (Claim Details, Linked Equipment/Fault, Documents, History).

## Tasks

<task id="1">
Create WarrantyLens.tsx:

VitalSignsRow with 5 signs:
- Status (draft/submitted/approved/rejected) - StatusPill
- Equipment (linked equipment name) - EntityLink
- Fault (linked fault if any) - EntityLink
- Supplier (warranty provider)
- Submitted (date or "Not submitted")
</task>

<task id="2">
Create warranty-specific sections:

- **ClaimDetailsSection** - Claim description, amount, resolution notes
- **LinkedEntitiesSection** - Equipment link, Fault link (if applicable)
- **DocumentsSection** - Supporting documents, invoices
- **HistorySection** - Reuse from Work Order

Use WarrantyDocumentsSection if it exists.
</task>

<task id="3">
Create useWarrantyActions hook:

Actions:
- draft_claim
- submit_claim
- approve_claim (HOD+)
- reject_claim (HOD+)
- add_document
- update_claim

Role-based: crew can draft/submit, HOD+ can approve/reject.
</task>

<task id="4">
Implement claim workflow:

1. Draft: crew creates claim, links equipment/fault
2. Submit: sends for approval
3. Approve/Reject: HOD decision with optional notes
4. Approved claims can have resolution notes added
</task>

<task id="5">
Wire warranty/[id]/page.tsx and verify build.
</task>

## must_haves

- [ ] WarrantyLens.tsx with full-screen layout
- [ ] VitalSignsRow with equipment and fault links
- [ ] Claim details section
- [ ] Draft → Submit → Approve/Reject workflow
- [ ] useWarrantyActions hook
- [ ] Build passes
