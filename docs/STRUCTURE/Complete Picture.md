  Complete Picture

  YOUR SITE
  ├── / (home)
  │   └── SpotlightSearch → search bar + gear icon (settings modal)
  │
  ├── /work-orders         → list page
  ├── /work-orders/[id]    → EntityLensPage (engine) + WorkOrderContent (v2 body)
  ├── /equipment/[id]      → EntityLensPage + EquipmentContent
  ├── /faults/[id]         → EntityLensPage + FaultContent
  ├── /parts/[id]          → EntityLensPage + PartsInventoryContent
  ├── /documents/[id]      → EntityLensPage + DocumentContent
  ├── /certificates/[id]   → EntityLensPage + CertificateContent
  ├── /receiving/[id]      → EntityLensPage + ReceivingContent
  ├── /shopping-list/[id]  → EntityLensPage + ShoppingListContent
  ├── /purchasing/[id]     → EntityLensPage + PurchaseOrderContent
  ├── /hours-of-rest/[id]  → EntityLensPage + HoursOfRestContent
  ├── /warranties/[id]     → EntityLensPage + WarrantyContent
  ├── /handover/[id]       → EntityLensPage + HandoverContent
  ├── /email               → EmailInboxView (own system, not entity lens)
  │
  ├── Actions triggered from any lens:
  │   ├── ActionPopup (v2) — generic form popup for simple actions
  │   ├── 8 specific modals — AddNote, AddPart, AddHours, Reassign, etc.
  │   ├── SignatureCanvas — for SIGNED variant actions
  │   └── SplitButton — primary action + dropdown of secondary actions
  │
  └── Settings (modal from gear icon, not a route)

  Dead Code (can be archived)

  ┌──────────────────────────────────────┬─────────────────────────────────────────────────────┐
  │                 File                 │                      Why Dead                       │
  ├──────────────────────────────────────┼─────────────────────────────────────────────────────┤
  │ lens/sections/AttachmentsSection.tsx │ Replaced by lens-v2/sections/AttachmentsSection.tsx │
  ├──────────────────────────────────────┼─────────────────────────────────────────────────────┤
  │ lens/sections/ChecklistSection.tsx   │ Replaced by lens-v2/sections/ChecklistSection.tsx   │
  ├──────────────────────────────────────┼─────────────────────────────────────────────────────┤
  │ lens/sections/NotesSection.tsx       │ Replaced by lens-v2/sections/NotesSection.tsx       │
  ├──────────────────────────────────────┼─────────────────────────────────────────────────────┤
  │ lens/sections/PartsSection.tsx       │ Replaced by lens-v2/sections/PartsSection.tsx       │
  ├──────────────────────────────────────┼─────────────────────────────────────────────────────┤
  │ lens/LensContainer.tsx               │ Replaced by lens-v2/LensShell.tsx                   │
  ├──────────────────────────────────────┼─────────────────────────────────────────────────────┤
  │ lens/LensHeader.tsx                  │ Replaced by lens-v2/LensGlassHeader.tsx             │
  ├──────────────────────────────────────┼─────────────────────────────────────────────────────┤
  │ lens/ShowRelatedButton.tsx           │ No imports found                                    │
  └──────────────────────────────────────┴─────────────────────────────────────────────────────┘

  Still Active in lens/ (NOT dead)

  ┌──────────────────────────────────────────┬────────────────────────────────────────────────────────────────────────────────────┐
  │                   File                   │                                     Why Active                                     │
  ├──────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────┤
  │ lens/EntityLensPage.tsx                  │ The engine — every page imports this                                               │
  ├──────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────┤
  │ lens/actions/*.tsx (8 modals)            │ Imported by entity content files (e.g., AddNoteModal imported by WorkOrderContent) │
  ├──────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────┤
  │ lens/RelatedDrawer.tsx                   │ Imported by EntityLensPage                                                         │
  ├──────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────┤
  │ lens/AddRelatedItemModal.tsx             │ Imported by RelatedDrawer                                                          │
  ├──────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────┤
  │ lens/sections/HistorySection.tsx         │ No v2 equivalent exists                                                            │
  ├──────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────┤
  │ lens/sections/RelatedEntitiesSection.tsx │ No v2 equivalent exists                                                            │
  ├──────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────┤
  │ lens/handover-export-sections/*          │ Handover-specific, no v2 equivalent                                                │
  └──────────────────────────────────────────┴────────────────────────────────────────────────────────────────────────────────────┘

  Bottom line: Everything you need is built. The "v1 vs v2" confusion is just that the engine (EntityLensPage) lives in lens/ and the
  visual body (*Content files) live in lens-v2/. They work together. 7 files in lens/sections/ are dead and can be archived.
  Everything else is active.



======


NOTES:
he truth:

  How It Actually Works

  Every detail page does the same thing:
  lens/EntityLensPage (v1)  ← the shell (data fetching, actions, layout)
    └── lens-v2/entity/XxxContent  ← the visual design (how data looks)
    └── lens-v2/ActionPopup  ← action execution
    └── lens-v2/lens.module.css  ← styling

  It's not v1 OR v2. It's both — v1 is the engine, v2 is the body.

  The Real Inventory

  ┌──────────────────────────────────────────┬──────────────────────────────────────────────────┬─────────────────────────────────┐
  │                 Location                 │                    What It Is                    │             Status              │
  ├──────────────────────────────────────────┼──────────────────────────────────────────────────┼─────────────────────────────────┤
  │ lens/EntityLensPage.tsx                  │ The engine — fetches data, manages actions,      │ ACTIVE — every page uses this   │
  │                                          │ renders shell                                    │                                 │
  ├──────────────────────────────────────────┼──────────────────────────────────────────────────┼─────────────────────────────────┤
  │ lens/actions/*.tsx (8 modals)            │ Complex action forms (add hours, reassign, etc.) │ ACTIVE — used by EntityLensPage │
  ├──────────────────────────────────────────┼──────────────────────────────────────────────────┼─────────────────────────────────┤
  │ lens/handover-export-sections/           │ Handover signature/editing                       │ ACTIVE                          │
  ├──────────────────────────────────────────┼──────────────────────────────────────────────────┼─────────────────────────────────┤
  │ lens/RelatedDrawer.tsx                   │ Side panel for related entities                  │ ACTIVE                          │
  ├──────────────────────────────────────────┼──────────────────────────────────────────────────┼─────────────────────────────────┤
  │ lens/sections/HistorySection.tsx         │ Timeline/history                                 │ ACTIVE — no v2 equivalent       │
  ├──────────────────────────────────────────┼──────────────────────────────────────────────────┼─────────────────────────────────┤
  │ lens/sections/RelatedEntitiesSection.tsx │ Related entity links                             │ ACTIVE — no v2 equivalent       │
  ├──────────────────────────────────────────┼──────────────────────────────────────────────────┼─────────────────────────────────┤
  │ lens-v2/entity/*.tsx (13 files)          │ Content renderers — one per lens, visual layout  │ ACTIVE — every page uses these  │
  ├──────────────────────────────────────────┼──────────────────────────────────────────────────┼─────────────────────────────────┤
  │ lens-v2/ActionPopup.tsx                  │ Generic action popup                             │ ACTIVE                          │
  ├──────────────────────────────────────────┼──────────────────────────────────────────────────┼─────────────────────────────────┤
  │ lens-v2/LensShell.tsx                    │ Glass header, layout shell                       │ ACTIVE                          │
  ├──────────────────────────────────────────┼──────────────────────────────────────────────────┼─────────────────────────────────┤
  │ lens-v2/LensGlassHeader.tsx              │ Frosted glass header bar                         │ ACTIVE                          │
  ├──────────────────────────────────────────┼──────────────────────────────────────────────────┼─────────────────────────────────┤
  │ lens-v2/sections/*.tsx (7 sections)      │ Reusable visual sections (KV, notes,             │ ACTIVE — used by entity content │
  │                                          │ attachments, etc.)                               │  files                          │
  └──────────────────────────────────────────┴──────────────────────────────────────────────────┴─────────────────────────────────┘

  Duplicates (4 files — v1 versions are DEAD, v2 versions are used)

  ┌────────────────────────┬────────────┬──────────┬────────────────────────┐
  │          File          │ lens/ (v1) │ lens-v2/ │    Which Is Used?      │
  ├────────────────────────┼────────────┼──────────┼────────────────────────┤
  │ AttachmentsSection.tsx │ DEAD       │ ACTIVE   │ v2 (all Content files) │
  ├────────────────────────┼────────────┼──────────┼────────────────────────┤
  │ ChecklistSection.tsx   │ DEAD       │ ACTIVE   │ v2 (WorkOrderContent)  │
  ├────────────────────────┼────────────┼──────────┼────────────────────────┤
  │ NotesSection.tsx       │ DEAD       │ ACTIVE   │ v2 (all Content files) │
  ├────────────────────────┼────────────┼──────────┼────────────────────────┤
  │ PartsSection.tsx       │ DEAD       │ ACTIVE   │ v2 (WorkOrderContent)  │
  └────────────────────────┴────────────┴──────────┴────────────────────────┘

.

  Final Verified State (updated 2026-03-19)

  Total: 206 actions in registry, 231 Phase 4 handlers, 0 orphans.
  All actions route through Phase 4 (_ACTION_HANDLERS). No elif chain, no fallback.
  8 actions return NOT_IMPLEMENTED (clean stub, no 500).

  ┌─────┬─────────────────┬─────────────────┬────────────┬────────────────────────────┬────────────────────────────────┬────────────────┐
  │  #  │      Lens       │     Status      │ ID Matches │       Fields Present       │          Actions               │ Yacht Isolated │
  ├─────┼─────────────────┼─────────────────┼────────────┼────────────────────────────┼────────────────────────────────┼────────────────┤
  │ 1   │ Work Orders     │ ✅ VERIFIED     │ Yes        │ title, status, priority    │ 29 actions (was 15)            │ Yes            │
  ├─────┼─────────────────┼─────────────────┼────────────┼────────────────────────────┼────────────────────────────────┼────────────────┤
  │ 2   │ Equipment       │ ✅ VERIFIED     │ Yes        │ name, status, manufacturer │ 28 actions (was 14)            │ Yes            │
  ├─────┼─────────────────┼─────────────────┼────────────┼────────────────────────────┼────────────────────────────────┼────────────────┤
  │ 3   │ Faults          │ ✅ VERIFIED     │ Yes        │ description, status        │ 18 actions (was 12)            │ Yes            │
  ├─────┼─────────────────┼─────────────────┼────────────┼────────────────────────────┼────────────────────────────────┼────────────────┤
  │ 4   │ Parts           │ ✅ VERIFIED     │ Yes        │ name, part_number          │ 20 actions (was 8)             │ Yes            │
  ├─────┼─────────────────┼─────────────────┼────────────┼────────────────────────────┼────────────────────────────────┼────────────────┤
  │ 5   │ Documents       │ ✅ VERIFIED     │ Yes        │ filename, doc_type         │ 16 actions (was 9)             │ Yes            │
  ├─────┼─────────────────┼─────────────────┼────────────┼────────────────────────────┼────────────────────────────────┼────────────────┤
  │ 6   │ Certificates    │ ✅ VERIFIED     │ Yes        │ name, authority, expiry    │ 10 actions (was 4)             │ Yes            │
  ├─────┼─────────────────┼─────────────────┼────────────┼────────────────────────────┼────────────────────────────────┼────────────────┤
  │ 7   │ Receiving       │ ✅ VERIFIED     │ Yes        │ vendor, ref, status        │ 13 actions (was 10)            │ Yes            │
  ├─────┼─────────────────┼─────────────────┼────────────┼────────────────────────────┼────────────────────────────────┼────────────────┤
  │ 8   │ Shopping List   │ ✅ VERIFIED     │ Yes        │ name, status, urgency      │ 12 actions (was 5)             │ Yes            │
  ├─────┼─────────────────┼─────────────────┼────────────┼────────────────────────────┼────────────────────────────────┼────────────────┤
  │ 9   │ Purchase Orders │ ✅ VERIFIED     │ Yes        │ po_number, supplier, total │ 11 actions (was 0 — FIXED)     │ Yes            │
  ├─────┼─────────────────┼─────────────────┼────────────┼────────────────────────────┼────────────────────────────────┼────────────────┤
  │ 10  │ Hours of Rest   │ ✅ VERIFIED     │ Yes        │ rest/work hours, status    │ 17 actions (was 12)            │ Yes            │
  ├─────┼─────────────────┼─────────────────┼────────────┼────────────────────────────┼────────────────────────────────┼────────────────┤
  │ 11  │ Warranties      │ ✅ VERIFIED     │ Yes        │ title, status, vendor      │ 10 actions (was 0 — NEW)       │ Yes            │
  ├─────┼─────────────────┼─────────────────┼────────────┼────────────────────────────┼────────────────────────────────┼────────────────┤
  │ 12  │ Handover        │ ✅ VERIFIED     │ Yes        │ title, content             │ 15 actions (was 0 — FIXED)     │ Yes            │
  ├─────┼─────────────────┼─────────────────┼────────────┼────────────────────────────┼────────────────────────────────┼────────────────┤
  │ 13  │ Email           │ ✅ VERIFIED     │ N/A        │ subject, is_read, yacht_id │ Own system (not entity lens)   │ Yes            │
  ├─────┼─────────────────┼─────────────────┼────────────┼────────────────────────────┼────────────────────────────────┼────────────────┤
  │ 14  │ Bootstrap       │ ✅ VERIFIED     │ N/A        │ yacht, email, role, name   │ N/A                            │ Yes            │
  ├─────┼─────────────────┼─────────────────┼────────────┼────────────────────────────┼────────────────────────────────┼────────────────┤
  │ 15  │ Search          │ ✅ Health OK    │ N/A        │ 18 capabilities listed     │ N/A                            │ N/A            │
  └─────┴─────────────────┴─────────────────┴────────────┴────────────────────────────┴────────────────────────────────┴────────────────┘

  Action Routing Architecture (2026-03-19)

  Request → /v1/actions/execute
    │
    └─ Phase 4: _ACTION_HANDLERS (231 handlers)
       ├── 16 domain handler files (routes/handlers/*.py) — native Phase 4
       └── internal_adapter.py — shim wrapping 71 legacy INTERNAL_HANDLERS
           into Phase 4 calling convention. Remove entries as handlers go native.

  No elif chain. No fallback. One routing path.

