# Deferred Items - Phase 00 Design System

Items discovered during plan execution that are out of scope and should be addressed later.

## Pre-existing TypeScript Error in AddNoteModal.tsx

**Discovered during:** 00-05 execution (build verification step)

**File:** `apps/web/src/components/modals/AddNoteModal.tsx`

**Issue:** Type error - `ENTITY_CONFIG` is missing entries for `part`, `document`, `supplier`, `purchase_order`, `receiving` but the `EntityType` union includes these types.

**Error message:**
```
Type '{ fault: ...; work_order: ...; equipment: ...; checklist: ...; }' is missing the following properties from type 'Record<EntityType, ...>': part, document, supplier, purchase_order, receiving
```

**Why deferred:** Pre-existing issue unrelated to 00-05 plan objective (remove "email integration is off" dead code). The plan objective was already completed in plan 13-01.

**Recommended fix:** Either:
1. Add missing entity type configs to `ENTITY_CONFIG`, OR
2. Narrow the `EntityType` union to only supported types, OR
3. Make `ENTITY_CONFIG` partial: `Partial<Record<EntityType, ...>>`

**Priority:** Medium - blocks production build
