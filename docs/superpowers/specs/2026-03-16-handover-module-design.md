# Handover Module — Design Spec

**Status:** Draft — awaiting review
**Date:** 2026-03-16
**Prototype:** `.superpowers/brainstorm/6432-1773680335/handover-v1.html`
**Author:** Celeste7

---

## 1. Purpose

A structured watch-handover panel allowing users to compose, review, export, and sign off on shift handover packages. Items are grouped by category (urgent, in progress, watch, FYI, completed), each expandable to show full context with links back to the source entity. The handover is a critical operational surface — it bridges two watches with a clear, auditable chain of custody.

---

## 2. Design Principles

| Principle | Rule |
|-----------|------|
| **Spotlight alignment** | Item rows (44px / 14px / 12px), icon sizing (16px), and category headers match the Spotlight/Ledger UX exactly |
| **Category = section anchor** | Category headers use the same overline typography as Spotlight group headers. They are organisational anchors, not content rows |
| **Expand for detail** | Items show title + secondary only. Full summary, entity links, and controls appear on expansion — no clutter at rest |
| **Entity traceability** | Every item links to its source entity. The handover is a lens into existing data, not a silo |
| **Dual-signature integrity** | Export → Outgoing sign → Incoming countersign. Content hashing at finalize, document hashing at export. No shortcuts |
| **Token-only styling** | Zero raw hex in component CSS. Dark/light switches via token reassignment |

---

## 3. Panel Dimensions & Shell

| Property | Value |
|----------|-------|
| Width | 620px |
| Border radius | 8px |
| Overflow | hidden |
| Shadow (dark) | `0 0 0 1px rgba(0,0,0,0.60)`, `0 28px 80px rgba(0,0,0,0.80)`, `0 8px 24px rgba(0,0,0,0.45)` |
| Shadow (light) | `0 0 0 1px rgba(0,0,0,0.05)`, `0 28px 80px rgba(0,0,0,0.13)`, `0 8px 24px rgba(0,0,0,0.08)` |
| Asymmetric border | Top brightest, bottom dimmest (ambient light physics) |
| Background | `--surface-el` |

### Header

- Height: 46px
- Glass effect: `backdrop-filter: blur(8px)` + semi-transparent background
- Contents:
  - Left: Handover icon (14px, `--mark`) + "Handover" label (12px/600, `--txt2`)
  - Right: Draft/Published pill toggle + Add item button (24×24px, `+`)
- Separated from body by 1px `--border-sub`

### Summary Bar (Draft View Only)

- Height: ~32px
- Padding: `8px 12px`
- Contents: Critical count (red/600), Action count (amber/500), Total items (right-aligned, ghost)
- Separated from body by 1px `--border-sub`
- Hidden when Published view is active

### Body

- Height: 480px (substantial scroll area — primary surface)
- `overflow-y: auto` with 4px scrollbar
- Padding: 0 (category sections handle their own padding)
- Two view sets: Draft (category-grouped items) and Published (historical handovers)

### Footer Action Bar

- Height: 46px
- Contents: Item count + critical count (left), Validate / Finalize / Export buttons (right)
- Validate and Finalize: default style (`--surface-el` bg, `--border-sub` border)
- Export: primary style (`--mark` bg, white text)
- Separated from body by 1px `--border-sub`

---

## 4. Controls

### Draft / Published Toggle

Pill-style toggle in panel header. Two states:

| Button | Active state |
|--------|-------------|
| Draft | Shows the current draft handover with category-grouped items |
| Published | Shows historical completed/signed handover exports |

Active pill: `--teal-bg` background, `--txt` colour.

When switching to Published:
- Summary bar hides
- Footer buttons change context (or hide — implementation decision)

### Add Item Button

Small `+` button in panel header, right of pill toggle:
- 24×24px, 4px radius
- Default: `--txt3` text, transparent bg, transparent border
- Hover: `--mark` text, `--teal-bg` bg, `--border-sub` border
- Opens item creation flow (implementation phase)

---

## 5. Category Sections (Draft View)

Items are grouped by category, each as a section separated by 1px `--border-sub`.

### Categories

| Category | Label colour | Badge | Description |
|----------|-------------|-------|-------------|
| `urgent` | `--red` | Critical (red), Action (amber) | Items requiring immediate attention on incoming watch |
| `in_progress` | `--txt3` (default) | Action (amber) | Work underway that needs monitoring or completion |
| `watch` | `--txt3` (default) | — | Items to observe, no immediate action required |
| `fyi` | `--txt3` (default) | — | Informational items for awareness |
| `completed` | `--green` | Done (green) | Items resolved during outgoing watch |

### Category Header (Section Anchor)

Same visual grammar as Spotlight group headers and Ledger day headers.

| Property | Value |
|----------|-------|
| Padding | `12px 12px 5px` (first section: `8px` top) |
| Typography | 10px / 600 / `0.10em` letter-spacing / uppercase |
| Colour | `--txt3` default, `--red` for urgent, `--green` for completed |
| Hover | None — anchors are not interactive |
| Background | None — anchors are not rows |

### Category Header Contents

- Left: Category label (uppercase)
- Right: Item count (10px, `--txt-ghost`)

---

## 6. Item Rows (Draft View)

Each item row matches the Spotlight `spotlight-item` proportions exactly.

| Property | Value |
|----------|-------|
| Min-height | 44px |
| Padding | `8px 12px` |
| Gap | 10px |
| Cursor | pointer |
| Hover | `--surface-hover` background, 60ms transition |

### Row Layout

```
┌──────────────────────────────────────────────────────────────────┐
│  [16px icon]  [Entity — Description]           [badges]  [▸]    │
│               [Location · Added by]                             │
└──────────────────────────────────────────────────────────────────┘
```

### Icon (left)

- Size: 16px
- Colour: `--txt3`
- Entity type semantic mapping per design philosophy spec §8

### Primary Line

- Font: 14px / 500 / `--txt`
- Grammar: `[Entity Type] [Identifier] — [Description]`
- Completed items: drop to `--txt3` / 400 weight (de-emphasised)

### Secondary Line

- Font: 12px / 400 / `--txt3`
- Grammar: `[Location] · Added by [Name]`

### Badges (right of text, left of chevron)

| Badge | Background | Text colour | Border |
|-------|-----------|-------------|--------|
| Critical | `--red-bg` | `--red` | `--red-border` |
| Action | `--amber-bg` | `--amber` | `--amber-border` |
| Done | `--green-bg` | `--green` | `--green-border` |

Badge: 18px height, 6px horizontal padding, 3px radius, 9px / 600 / uppercase.

### Chevron (far right)

| State | Opacity | Rotation |
|-------|---------|----------|
| Default | 0.35 | 0deg (pointing right) |
| Hover | 0.70 | 0deg |
| Expanded | 0.70 | 90deg (pointing down) |

Transition: `transform 120ms ease, opacity 80ms ease`

---

## 7. Item Detail (Expanded State)

When an item row is expanded, its detail panel appears directly below.

| Property | Value |
|----------|-------|
| Padding | `0 12px 12px 38px` (left indent aligns with text, past icon) |
| Gap | 10px |
| Display | flex column |

### Detail Components

**Summary block:**
- 13px / `--txt2` / 1.55 line-height
- Background: `--surface` with `--border-sub` border, 4px radius
- Padding: `8px 10px`
- Completed items: text drops to `--txt3`

**Entity link:**
- 12px / 500 / `--mark` colour
- Grammar: `View [Entity Type] [Identifier] →`
- Hover: opacity 0.8
- Clicking navigates to the source entity's detail page

**Controls row:**
- Flex row, 6px gap, wrapping
- Three buttons (default state): Edit summary, Change category, Remove
- Button: 26px height, 10px padding, 4px radius, 11px/500
- Remove button: `.danger` variant — `--red` text, `--red-bg` + `--red-border` on hover

**Meta row:**
- 10.5px / `--txt-ghost`
- Contents: `Added [timestamp]` (monospace) + `Priority: [level]`
- Separator: `·` character

---

## 8. Published View

Historical list of completed handover exports, sorted newest first.

### Published Item Row

| Property | Value |
|----------|-------|
| Min-height | 54px |
| Padding | `10px 12px` |
| Cursor | pointer |
| Hover | `--surface-hover`, 60ms transition |
| Separator | 1px `--border-sub` between items |

### Row Layout

```
┌────────────────────────────────────────────────────────────────┐
│  [65px date block]  [Signers: Out → In]                  [▸]  │
│  [status dot+text]  [N items · Dept · Shift]                  │
└────────────────────────────────────────────────────────────────┘
```

**Date block (65px, left):**
- Date: 12px / 600 / monospace / `--txt`
- Status: 10px / 500 + 6px dot

**Status indicators:**
| Status | Dot | Text |
|--------|-----|------|
| Signed (complete) | `--green` | `Signed` in `--green` |
| Pending incoming | `--amber` | `Pending` in `--amber` |

**Signers line:** 12px / `--txt2` — `[Outgoing Name] → [Incoming Name]`

**Meta line:** 11px / `--txt3` — `[N items] · [Department] · [Shift Type → Shift Type]`

### Published Detail (Expanded)

| Property | Value |
|----------|-------|
| Padding | `0 12px 12px` |
| Gap | 8px |

**Signature rows (2 per export):**
- Background: `--surface`, 4px radius
- Padding: `6px 10px`
- Contents: Label (10px/600/uppercase/`--txt-ghost`, 70px width) + Name + Role (12px/`--txt2`) + Check mark (`--green`) + Timestamp (10.5px/mono/`--txt-ghost`)
- Pending incoming: 50% opacity, name in `--amber`, timestamp shows `—`

**Hash display:**
- 10px / monospace / `--txt-ghost`
- Grammar: `Content: [truncated hash] · Document: [truncated hash]`
- Padding: `4px 10px`

**Download link:**
- 12px / 500 / `--mark`
- Download icon (12px) + "Download PDF"
- Only shown when both signatures are complete
- Hover: opacity 0.8

---

## 9. Entity Type Icons

Consistent across search results, ledger, handover, and all future surfaces.

| Entity type | Icon | SVG description |
|-------------|------|-----------------|
| `fault` | Warning triangle | Triangle with exclamation |
| `work_order` | Clipboard | Stacked rectangles with text lines |
| `equipment` | Machine | Horizontal bars with risers |
| `part` / `inventory` | Hexagon | Hexagonal prism with internal lines |
| `document` / `document_chunk` | Page | Rectangle with text lines and title bar |
| `certificate` | Award | Circle with checkmark |
| `note` | Notepad | Rectangle with folded corner |

---

## 10. Workflow States

The handover follows a 4-stage workflow. Each stage changes the panel's visual state.

### Stage 1: Draft

- Default state — items are editable
- Footer shows: Validate + Finalize + Export
- Summary bar visible with critical/action counts
- All item controls available (edit, change category, remove)

### Stage 2: Finalized

- Content is locked — no further edits
- `content_hash` (SHA256) is computed over all item data
- Footer: Finalize button becomes disabled/checked, Export becomes primary
- Visual indicator: finalized badge or lock icon in summary bar (implementation detail)

### Stage 3: Exported

- HTML/PDF document generated
- `document_hash` computed over exported document
- Footer: Export button shows completion state
- Handover appears in Published view with "Pending" status

### Stage 4: Signed

- Two signatures required:
  1. **Outgoing:** HMAC soft signature by the departing watch officer
  2. **Incoming:** Countersignature by the arriving watch officer (requires `acknowledge_critical` for critical items)
- Once both signed: status → `completed`, appears with green "Signed" dot in Published view

### Validation Rules (Stage 1 → 2)

- No items with empty summaries
- All critical items must have an `action_summary`
- Validation feedback shown inline (implementation detail)

---

## 11. Data Sources

### Endpoints

| Action | Method | Endpoint | Purpose |
|--------|--------|----------|---------|
| List items | GET | `/v1/handover/items` | Current draft items |
| Add item | POST | `/v1/handover/items` | Add entity to handover |
| Edit item | PATCH | `/v1/handover/items/{id}` | Edit summary, category, priority |
| Remove item | DELETE | `/v1/handover/items/{id}` | Soft delete (sets `deleted_at`) |
| Validate draft | POST | `/v1/handover/validate` | Check readiness for finalization |
| Finalize draft | POST | `/v1/handover/finalize` | Lock content, compute `content_hash` |
| Export | POST | `/v1/handover/export` | Generate HTML/PDF, compute `document_hash` |
| Sign outgoing | POST | `/v1/handover/sign/outgoing` | HMAC soft signature |
| Sign incoming | POST | `/v1/handover/sign/incoming` | Countersignature with critical acknowledgement |
| List published | GET | `/v1/handover/exports` | Historical signed handovers |
| Verify export | GET | `/v1/handover/exports/{id}/verify` | Both hashes + signature metadata |

### Item Shape

```typescript
interface HandoverItem {
  id: string;
  yacht_id: string;
  entity_type: string;     // fault, work_order, equipment, document, document_chunk, part, note
  entity_id: string;
  summary: string;
  section: string | null;
  category: string;         // urgent, in_progress, completed, watch, fyi
  priority: number;         // 0-3
  is_critical: boolean;
  requires_action: boolean;
  action_summary: string | null;
  entity_url: string | null;
  added_by: string;
  created_at: string;
  deleted_at: string | null;
}
```

### Export Shape

```typescript
interface HandoverExport {
  id: string;
  yacht_id: string;
  content_hash: string;     // SHA256 of finalized content
  document_hash: string;    // SHA256 of generated document
  status: 'pending_outgoing' | 'pending_incoming' | 'completed';
  outgoing_signer: string;
  incoming_signer: string | null;
  signatures: {
    outgoing?: { user_id: string; role: string; timestamp: string; hmac: string };
    incoming?: { user_id: string; role: string; timestamp: string; hmac: string; acknowledged_critical: boolean };
  };
  item_count: number;
  department: string;
  shift_type: string;       // e.g., "Night → Day"
  created_at: string;
}
```

---

## 12. Navigation

Every entity link in an expanded item detail navigates to the source entity's detail page:

```typescript
function getEntityRoute(entityType: string, entityId: string): string {
  // Maps: fault → /faults/{id}
  //        work_order → /work-orders/{id}
  //        equipment → /equipment/{id}
  //        part → /inventory/{id}
  //        document → /documents/{id}
  //        etc.
}
```

This routing already exists in the codebase. No new routing logic needed.

---

## 13. Interaction Behaviour

| Trigger | Behaviour |
|---------|-----------|
| Item row click | Toggle expanded/collapsed state |
| Entity link click | Navigate to entity detail page via `router.push()` |
| Draft/Published toggle | Swap view sets, toggle summary bar visibility |
| Add item (+) | Open item creation flow (implementation phase) |
| Edit summary | Inline edit or modal (implementation phase) |
| Change category | Dropdown or popover (implementation phase) |
| Remove | Confirm, then soft delete |
| Validate | Run validation checks, show inline feedback |
| Finalize | Lock content, compute content_hash, disable edits |
| Export | Generate document, compute document_hash, move to Published |
| Published row click | Toggle expanded to show signatures + hashes |
| Download PDF | Fetch export document from API |

---

## 14. Accessibility

- Item rows: `role="button"`, `tabindex="0"`, `aria-expanded` toggling
- Category headers: not interactive, no ARIA role needed (label only)
- Badge labels: include `aria-label` for screen readers (e.g., "Critical priority")
- Published signature rows: `role="status"` for pending signatures
- Footer buttons: standard button semantics, disabled state communicated via `aria-disabled`
- Panel: `aria-label="Watch handover"`
- Focus-visible ring on all interactive elements (implementation phase)

---

## 15. Out of Scope

| Feature | Reason |
|---------|--------|
| Inline summary editing | Implementation detail — modal vs inline TBD |
| Real-time collaboration | Deferred — single-user draft for v1 |
| Item reordering / drag-drop | Deferred — category grouping handles prioritisation |
| Attachment uploads | Not part of handover — items link to existing entities |
| Template handovers | Deferred — v2 consideration |
| Email notification on pending signature | Backend concern, not frontend spec |
| Predictive item suggestions | AI feature — deferred |

---

## 16. Cross-Reference

- **Design philosophy:** `docs/superpowers/specs/2026-03-16-frontend-design-philosophy.md`
- **Token values:** `apps/web/src/styles/tokens.css`
- **Spotlight alignment:** `apps/web/src/styles/spotlight.css` (`.spotlight-item`, `.spotlight-group-header`)
- **Ledger alignment:** `docs/superpowers/specs/2026-03-16-ledger-module-design.md`
- **Backend handlers:** `apps/api/handlers/handover_handlers.py`
- **Backend workflow:** `apps/api/handlers/handover_workflow_handlers.py`
- **Frontend client:** `apps/web/src/lib/handoverExportClient.ts`
- **Frontend actions:** `apps/web/src/lib/microactions/handlers/handover.ts`
