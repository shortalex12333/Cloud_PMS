---
wave: 1
depends_on: []
files_modified:
  - apps/web/src/components/lens/ShoppingListLens.tsx
  - apps/web/src/app/shopping-list/[id]/page.tsx
autonomous: true
requirements: [SHOP-03]
---

# Plan FE-03-05: Shopping List Lens Rebuild

## Objective

Rebuild Shopping List lens: LensHeader, VitalSignsRow (status, items count, requester, approver, created date), sections (Items, Approval History), approval workflow.

## Tasks

<task id="1">
Create ShoppingListLens.tsx:

VitalSignsRow with 5 signs:
- Status (pending/approved/rejected/ordered) - StatusPill
- Items ("N items")
- Requester (crew member who created)
- Approver (HOD who approved, or "Pending")
- Created (relative date)
</task>

<task id="2">
Create shopping list sections:

- **ItemsSection** - List of requested items with quantities, notes, part links
- **ApprovalHistorySection** - Approval/rejection log with timestamps

Items should link to Parts lens if part_id exists.
</task>

<task id="3">
Create useShoppingListActions hook:

Actions:
- create_item
- update_item
- remove_item
- approve_item (HOD+)
- reject_item (HOD+ with reason)
- mark_ordered

Role-based: crew can create/edit items, HOD+ can approve/reject.
</task>

<task id="4">
Implement approval workflow:

1. Crew adds items to shopping list
2. HOD reviews and approves/rejects each item
3. Approved items can be marked as ordered
4. State history tracked in pms_audit_log
</task>

<task id="5">
Wire shopping-list/[id]/page.tsx and verify build.
</task>

## must_haves

- [ ] ShoppingListLens.tsx with full-screen layout
- [ ] VitalSignsRow with requester/approver
- [ ] Items section with part links
- [ ] Approval workflow (approve/reject per item)
- [ ] useShoppingListActions hook
- [ ] Build passes
