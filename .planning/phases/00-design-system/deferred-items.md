# Deferred Items - Phase 00 Design System

## Pre-existing Build Issues

### AddNoteModal.tsx Type Error

**File:** `apps/web/src/components/modals/AddNoteModal.tsx:157`

**Error:**
```
Type error: Argument of type '"add_fault_note" | "add_work_order_note" | "add_equipment_note" | "add_checklist_note" | "add_part_note" | "add_document_note" | "add_supplier_note" | "add_purchase_order_note" | "add_receiving_note"' is not assignable to parameter of type 'MicroAction'.
Type '"add_part_note"' is not assignable to type 'MicroAction'. Did you mean '"add_fault_note"'?
```

**Context:** This type mismatch existed before 00-03 plan execution. The MicroAction type definition is missing some action types that the component references.

**Recommended Fix:** Update MicroAction type to include all note action types, or fix the actionName mapping.

**Impact:** Blocks full production builds but does not affect the new UI components.

---

*Logged during 00-03 plan execution, 2026-02-17*
