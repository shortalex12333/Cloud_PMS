# Lens v1 vs Lens v2: Architecture Explained

> **Audience:** Anyone working on CelesteOS frontend — engineers, designers, or non-technical leads who need to understand how entity detail pages are built.

---

## What is a "Lens"?

A lens is the detail page you see when you click on any entity — a work order, fault, certificate, piece of equipment, etc. It's called a lens because it's a focused view of one record.

Every lens page in CelesteOS uses **two component libraries working together**:

- **Lens v1** (`components/lens/`) — The **frame**
- **Lens v2** (`components/lens-v2/`) — The **content**

They are **not competing versions**. They are **inner and outer layers** of the same page. The naming is misleading — "v2" implies replacement, but in reality v2 was built to sit inside v1.

---

## How They Work Together

Every entity detail page looks like this:

```
┌─────────────────────────────────────────────┐
│  EntityLensPage (lens v1)                   │  ← Frame
│  ┌─────────────────────────────────────────┐│
│  │  Glass Header: ← Back │ Title │ ☰  ◐   ││  ← v1
│  ├─────────────────────────────────────────┤│
│  │                                         ││
│  │  WorkOrderContent (lens v2)             ││  ← Content
│  │  ┌─────────────────────────────────┐    ││
│  │  │  Identity Strip                 │    ││  ← v2
│  │  │  Status Badge │ Priority │ Date │    ││
│  │  ├─────────────────────────────────┤    ││
│  │  │  KV Section (key-value fields)  │    ││  ← v2
│  │  │  Equipment: Main Engine         │    ││
│  │  │  Assigned To: Chief Engineer    │    ││
│  │  ├─────────────────────────────────┤    ││
│  │  │  Notes Section                  │    ││  ← v2
│  │  │  Attachments Section            │    ││  ← v2
│  │  │  Checklist Section              │    ││  ← v2
│  │  └─────────────────────────────────┘    ││
│  │                                         ││
│  │  ┌─ Related Drawer (slides out) ──────┐ ││  ← v1
│  │  │  Linked faults, parts, docs...     │ ││
│  │  └────────────────────────────────────┘ ││
│  │                                         ││
│  │  ┌─ ActionPopup (overlay) ────────────┐ ││  ← v2
│  │  │  Signature popup for mutations     │ ││
│  │  └────────────────────────────────────┘ ││
│  └─────────────────────────────────────────┘│
└─────────────────────────────────────────────┘
```

---

## What Each Layer Owns

### Lens v1 — The Frame (`components/lens/`)

**26 files.** Handles everything that wraps around the content.

| Component | Purpose |
|-----------|---------|
| `EntityLensPage.tsx` | The main wrapper. Fetches entity data, manages loading/error/not-found states, provides context to children |
| `LensHeader.tsx` | Glass header bar — back button, entity title, theme toggle |
| `LensContainer.tsx` | Layout container |
| `RelatedDrawer.tsx` | "Show Related" slide-out panel — linked entities (faults, parts, docs) |
| `ShowRelatedButton.tsx` | Button that triggers the related drawer |
| `AddRelatedItemModal.tsx` | Modal for linking a new entity |
| `actions/` (7 modals) | AddNoteModal, ArchiveModal, MarkCompleteModal, ReassignModal, etc. |
| `sections/` (6 sections) | Legacy sections: Attachments, Checklist, History, Notes, Parts, RelatedEntities |
| `handover-export-sections/` | Handover-specific: signature canvas, editable sections |

**Key fact:** `EntityLensPage.tsx` imports `ActionPopup` and `lens.module.css` FROM lens v2. The frame depends on the content library for its popup and styling.

### Lens v2 — The Content (`components/lens-v2/`)

**33 files.** The actual visible UI for each entity type.

| Component | Purpose |
|-----------|---------|
| `entity/` (13 files) | One content component per entity: WorkOrderContent, FaultContent, CertificateContent, EquipmentContent, etc. |
| `sections/` (8 files) | Rebuilt sections with prototype styling: KVSection, NotesSection, HistorySection, AuditTrailSection, AttachmentsSection, ChecklistSection, DocRowsSection, PartsSection |
| `ActionPopup.tsx` | Schema-driven action popup with signature levels L0–L5 |
| `IdentityStrip.tsx` | Entity identity bar (status badge, priority, reference number) |
| `SplitButton.tsx` | Dropdown action button |
| `LensGlassHeader.tsx` | Rebuilt glass header (not yet swapped in) |
| `LensShell.tsx` | Rebuilt frame (not yet swapped in) |
| `CollapsibleSection.tsx` | Expandable section wrapper |
| `ScrollReveal.tsx` | Scroll-triggered animation |
| `lens.module.css` | All styling — 34KB CSS module matching approved prototypes |
| `popup.module.css` | ActionPopup styling — 17KB CSS module |

---

## How a Page Wires Them Together

Every entity page follows this exact pattern:

```typescript
// apps/web/src/app/work-orders/[id]/page.tsx

import { EntityLensPage } from '@/components/lens/EntityLensPage';     // v1 frame
import { WorkOrderContent } from '@/components/lens-v2/entity';        // v2 content
import lensStyles from '@/components/lens-v2/lens.module.css';         // v2 styling

function LensContent() {
  return <div className={lensStyles.root}><WorkOrderContent /></div>;
}

export default function WorkOrderDetailPage() {
  const params = useParams();
  return (
    <EntityLensPage
      entityType="work_order"
      entityId={params.id as string}
      content={LensContent}                  // v2 content injected into v1 frame
    />
  );
}
```

All 17 page files follow this pattern. No exceptions.

---

## Pages Using This Pattern

| Route | Content Component (v2) |
|-------|----------------------|
| `/work-orders/[id]` | WorkOrderContent |
| `/faults/[id]` | FaultContent |
| `/equipment/[id]` | EquipmentContent |
| `/certificates/[id]` | CertificateContent |
| `/documents/[id]` | DocumentContent |
| `/inventory/[id]` | PartsInventoryContent |
| `/purchasing/[id]` | PurchaseOrderContent |
| `/receiving/[id]` | ReceivingContent |
| `/shopping-list/[id]` | ShoppingListContent |
| `/warranties/[id]` | WarrantyContent |
| `/hours-of-rest/[id]` | HoursOfRestContent |
| `/hours-of-rest/signoffs/[id]` | HoRSignoffContent |
| `/handover-export/[id]` | HandoverContent |
| `/work-orders` (list) | WorkOrderContent |
| `/equipment` (list) | EquipmentContent |
| `/faults` (list) | FaultContent |

---

## Cross-Dependencies (Entanglement Points)

Only **4 cross-imports** exist between the two libraries:

| Direction | File | What it imports | Why |
|-----------|------|-----------------|-----|
| v1 → v2 | `EntityLensPage.tsx` | `lens-v2/ActionPopup` | Signature popup for actions |
| v1 → v2 | `EntityLensPage.tsx` | `lens-v2/lens.module.css` | Styling |
| v2 → v1 | `WorkOrderContent.tsx` | `lens/actions/AddNoteModal` | Reuses the v1 note modal |
| external | `SuggestedActions.tsx` | `lens-v2/ActionPopup` | Spotlight search actions |

---

## Show Related

"Show Related" lives entirely in **lens v1**:

| Component | Purpose |
|-----------|---------|
| `RelatedDrawer.tsx` | The slide-out panel showing linked entities |
| `ShowRelatedButton.tsx` | The button to open it |
| `AddRelatedItemModal.tsx` | Modal for linking a new entity |

**Backend:** `GET /v1/related?entity_type=X&entity_id=Y` returns linked entities. Defined in `apps/api/routes/related_routes.py`.

**Tests:** `RelatedDrawer.test.tsx` — 11 unit tests, all passing. Active code, do not remove.

---

## Planned Atomic Swap

The eventual goal is to merge both libraries into one:

```bash
# Step 1: Rename current lens to deprecated
git mv components/lens components/lens-deprecated

# Step 2: Rename lens-v2 to lens
git mv components/lens-v2 components/lens

# Step 3: Move components that v2 still needs from deprecated
#   - EntityLensPage.tsx (the frame)
#   - RelatedDrawer.tsx + ShowRelatedButton.tsx
#   - handover-export-sections/
#   - actions/ (AddNoteModal, etc.)

# Step 4: Update 4 cross-imports

# Step 5: Delete lens-deprecated (once nothing imports from it)
```

**Status:** Not yet executed. Requires resolving the 4 cross-imports first. Documented in `lens-v2/index.ts` comments.

**Risk:** Low if done carefully — all 17 page files use the same pattern and would not need changes if the import paths are aliased.

---

## Section Overlap

6 section components exist in **both** directories with the same name but different implementations:

| Section | lens v1 (old) | lens v2 (new) |
|---------|--------------|---------------|
| AttachmentsSection | Basic file list | Prototype-matched with upload zone |
| ChecklistSection | Simple checklist | Collapsible with progress bar |
| HistorySection | Flat list | Audit trail with ledger integration |
| NotesSection | Simple notes | Styled with timestamp formatting |
| PartsSection | Basic table | KV-style with stock indicators |

They don't conflict — each entity content component imports from its own `lens-v2/sections/`, never from `lens/sections/`. The v1 sections are only used by v1 action modals (MarkCompleteModal, etc.).

---

## FAQs

**Is lens v2 a replacement for lens v1?**
Partially. v2 replaces the *content* (what you see), but v1 still provides the *frame* (loading, header, related drawer). The planned atomic swap will merge them.

**Can I delete lens v1?**
No. `EntityLensPage.tsx` is the production frame for all 17 pages. The related drawer, action modals, and handover sections are all in v1 and actively used.

**Where should I add new entity-specific UI?**
In `lens-v2/entity/`. Follow the existing pattern (e.g., `WorkOrderContent.tsx`). Use sections from `lens-v2/sections/`.

**Where should I add new action modals?**
Use `ActionPopup` from `lens-v2/ActionPopup.tsx`. It's schema-driven — define fields and signature level, the component handles the rest. Don't create new one-off modals.
