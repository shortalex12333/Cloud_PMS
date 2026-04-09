# Ledger Module — Design Spec

**Status:** Draft — awaiting review
**Date:** 2026-03-16
**Prototype:** `.superpowers/brainstorm/6432-1773680335/ledger-v2.html`
**Author:** Celeste7

---

## 1. Purpose

An audit-trail panel showing chronological read/write/execution events by the current user or their department. Every row is clickable — navigating to the source entity (work order, fault, document, etc.). The ledger is a primary navigation surface: users understand what happened, when, by whom, and can jump directly to the data in question.

---

## 2. Design Principles

| Principle | Rule |
|-----------|------|
| **Spotlight alignment** | Row proportions (44px / 14px / 12px), icon sizing (16px), and group headers match the search result UX exactly |
| **Day = section anchor** | Day headers use the same overline typography as Spotlight group headers. They are temporal anchors, not content rows |
| **Reads are secondary** | Read events are hidden by default. A global toggle reveals them. Writes are the primary information |
| **Honest interactivity** | Every row is clickable and navigates to the source entity. No dead rows. Hover = promise fulfilled |
| **Token-only styling** | Zero raw hex in component CSS. Dark/light switches via token reassignment |

---

## 3. Panel Dimensions & Shell

| Property | Value |
|----------|-------|
| Width | 580px |
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
  - Left: Clock icon (14px, `--mark`) + "Ledger" label (12px/600, `--txt2`)
  - Right: Me/Department pill toggle + Reads toggle button
- Separated from body by 1px `--border-sub`

### Body

- Height: 500px (substantial scroll area — primary surface)
- `overflow-y: auto` with 4px scrollbar
- Padding: 0 (day sections handle their own padding)

---

## 4. Controls

### Me / Department Toggle

Pill-style toggle in panel header. Two states:

| Button | Active state |
|--------|-------------|
| Me | Shows events for the authenticated user only (`/v1/ledger/events` with explicit `user_id` filter) |
| Department | Shows events for all users in the same department/role scope (`/v1/ledger/timeline`) |

Active pill: `--teal-bg` background, `--txt` colour.

### Reads Toggle

Small button in panel header, right of pill toggle:
- Default: ghost text, transparent — reads are hidden
- Active: `--mark` text, `--teal-bg` background — reads are shown
- Applies globally to all day sections via `.show-reads` class on `.panel-body`

---

## 5. Day Sections

Each day is a collapsible section separated by a 1px `--border-sub` line between sections.

### Day Header (Section Anchor)

The day header is NOT a row. It is a temporal anchor — identical visual grammar to Spotlight group headers.

| Property | Value |
|----------|-------|
| Padding | `12px 12px 5px` (first section: `8px` top) |
| Typography | 10px / 600 / `0.10em` letter-spacing / uppercase / `--txt3` |
| Hover | Label brightens to `--txt2` (subtle) |
| Cursor | pointer |
| Background | None — anchors are not rows |

### Day Header Contents

- Left: Date label (`TODAY`, `YESTERDAY · 15 MAR`, `14 MAR`)
- Right: Event count (10px, `--txt-ghost`) + Chevron (10px, ghost opacity)

### Chevron Behaviour

| State | Opacity | Rotation |
|-------|---------|----------|
| Default | 0.35 | 0deg (pointing right) |
| Hover | 0.70 | 0deg |
| Expanded | 0.70 | 90deg (pointing down) |

Transition: `transform 120ms ease, opacity 80ms ease`

### Collapsed State

When collapsed, only the day header is visible. The event count tells the user whether expanding is worthwhile.

### Expanded State

Events flow directly below the header with `4px` bottom padding. No container background — events share the panel surface.

---

## 6. Event Rows

Each event row matches the Spotlight `spotlight-item` proportions exactly.

| Property | Value |
|----------|-------|
| Min-height | 44px |
| Padding | `8px 12px` |
| Gap | 10px |
| Cursor | pointer |
| Hover | `--surface-hover` background, 60ms transition |

### Row Layout

```
┌──────────────────────────────────────────────────────────────┐
│  [16px icon]  [Entity Name — Verb]                    14:32  │
│               [User Name · Role]                             │
└──────────────────────────────────────────────────────────────┘
```

### Icon (left)

- Size: 16px
- Colour: `--txt3` (writes), `--txt-ghost` (reads)
- Entity type semantic mapping per design philosophy spec §8

### Primary Line

- Font: 14px / 500 / `--txt`
- Grammar: `[Entity Type] [Identifier] — [Verb]`
- Verb span: `--txt3` / 400 weight (de-emphasised)
- Read events: primary drops to `--txt3` / 400 weight

### Secondary Line

- Font: 12px / 400 / `--txt3`
- Me view: User name only (`J. Morrison`)
- Department view: User name + role (`R. Chen · Chief Engineer`)

### Time (right-aligned)

- Font: 10.5px / monospace / `--txt-ghost`
- Alignment: `flex-start` (top of row)
- Padding-top: 5px (aligns with primary text baseline)

### Read Events

Read events (views, opens) are hidden by default. When `.show-reads` is active on the panel body:
- They become visible (`display: flex`)
- Primary text drops to `--txt3` / 400 weight
- Icon drops to `--txt-ghost`
- Verb drops to `--txt-ghost`
- This visual treatment communicates "this happened but is background noise"

---

## 7. Entity Type Icons

Consistent across search results, ledger, and all future surfaces.

| Entity type | Icon | SVG description |
|-------------|------|-----------------|
| `work_order` | Clipboard | Stacked rectangles with text lines |
| `fault` | Warning triangle | Triangle with exclamation |
| `equipment` | Machine | Horizontal bars with risers |
| `part` / `inventory` | Hexagon | Hexagonal prism with internal lines |
| `document` | Page | Rectangle with text lines and title bar |
| `certificate` | Award | Circle with checkmark |
| `purchase_order` | Calendar/receipt | Rectangle with date header |
| `hours_of_rest` | Clock | Circle with hands |
| `email_thread` | Envelope | (Not shown in ledger — deferred) |
| `warranty` | Shield | (Not shown in ledger — deferred) |

---

## 8. Navigation

Every event row is clickable. Clicking navigates to the source entity's detail page:

```typescript
// Existing routing function
function getEntityRoute(entityType: string, entityId: string): string {
  // Maps: work_order → /work-orders/{id}
  //        fault → /faults/{id}
  //        equipment → /equipment/{id}
  //        etc.
}
```

This routing already exists in the codebase (`LedgerPanel.tsx`). No new routing logic needed.

---

## 9. Data Sources

| View | Endpoint | Filter |
|------|----------|--------|
| Me | `GET /v1/ledger/events` | `user_id` (authenticated user) |
| Department | `GET /v1/ledger/timeline` | Role-scoped (RLS policy) |

### Event Shape

```typescript
interface LedgerEvent {
  id: string;
  yacht_id: string;
  user_id: string;
  event_type: string;
  entity_type: string;
  entity_id: string;
  action: string;
  change_summary: string | null;
  user_role: string | null;
  metadata: Record<string, unknown> | null;
  created_at: string; // ISO timestamp
}
```

### Read Action Types

```typescript
const READ_ACTIONS = ['artefact_opened', 'situation_ended', 'view', 'open'];
```

Events with actions in this list are classified as reads.

---

## 10. Interaction Behaviour

| Trigger | Behaviour |
|---------|-----------|
| Day header click | Toggle expanded/collapsed state |
| Event row click | Navigate to entity detail page via `router.push()` |
| Me/Dept toggle | Swap view sets instantly (CSS class toggle) |
| Reads button | Toggle `.show-reads` on panel body |
| Scroll | Internal scroll within 500px panel body |

---

## 11. Accessibility

- Day headers: `cursor: pointer`, expandable — should have `aria-expanded` attribute
- Event rows: `role="button"`, `tabindex="0"` for keyboard navigation
- Reads button: `aria-pressed` toggling
- Panel: `aria-label="Activity ledger"`
- Focus-visible ring on all interactive elements (implementation phase)

---

## 12. Out of Scope

| Feature | Reason |
|---------|--------|
| Infinite scroll / pagination | Deferred — initial implementation loads recent events |
| Date range picker | Deferred — not needed for v1 |
| Event detail expansion | Click navigates to entity; no inline detail panel |
| Real-time updates | Deferred — polling or subscription is implementation concern |
| Export from ledger | Activity export lives in Settings > Data |

---

## 13. Cross-Reference

- **Design philosophy:** `docs/superpowers/specs/2026-03-16-frontend-design-philosophy.md`
- **Token values:** `apps/web/src/styles/tokens.css`
- **Existing component:** `apps/web/src/components/ledger/LedgerPanel.tsx`
- **Spotlight alignment:** `apps/web/src/styles/spotlight.css` (`.spotlight-item`, `.spotlight-group-header`)
