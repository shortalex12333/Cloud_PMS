# Lens Prototype Build Guide

> **For agents building lens entity view prototypes.** Read this BEFORE writing any HTML.

## Mandatory Reading (in order)

1. **Design Philosophy:** `docs/superpowers/specs/2026-03-16-frontend-design-philosophy.md` — Read ALL of it, especially §2 (colour), §3 (typography), §4 (borders), §16-22 (entity views).
2. **Reference Prototype:** `apps/web/public/prototypes/lens-work-order.html` — This is your TEMPLATE. Match its exact patterns.
3. **Your Entity's React Component:** `apps/web/src/components/lens/{Entity}LensContent.tsx` — Understand the data fields, actions, and sections.

## File Location

All paths are relative to project root: `/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS`

## What to Match From the Work Order Prototype

### Panel
- Width: 720px, border-radius: 8px
- Asymmetric borders: top 0.13, sides 0.06, bottom 0.03
- Shadow: `0 0 0 1px rgba(0,0,0,0.60), 0 28px 80px rgba(0,0,0,0.80)`
- Background: `var(--surface)`

### Lens Header (glass)
- 56px height, backdrop-filter blur, semi-transparent background
- Back button (left), entity type label (center-left), Related button + Close (right)
- **Add theme toggle button** (sun/moon icon) next to Related button

### Identity Strip
- **Top row:** Entity ID as mono overline (left) ← → Primary action split button (right)
- **Title:** 22px/600 Inter, standalone, full width
- **Context line:** 13px/400, location + assignee/owner in teal (if navigable)
- **Status pills:** Below context. Correct colours — green=good, amber=warning, red=critical
- **Detail lines:** Key-value pairs. Label (11px/500/uppercase/--txt3), value (13px, correct font)
- **Description:** 14px/400 Inter, max-width 600px, muted

### Split Button (Primary Action)
- Main button + dropdown toggle, 36px height
- Dropdown: secondary actions, 44px items, icons + labels
- Archive/Delete/danger action: last, red, after separator
- If action should be disabled (e.g. incomplete prerequisites), grey it out with tooltip

### Section System
- Separator: `border-top: 1px solid var(--border-sub); margin-top: 32px; padding-top: 24px;`
- First section after identity: `margin-top: 24px`
- Heading: Icon (16px) + TITLE (14px/600/uppercase/0.06em tracking) + optional action + optional count + chevron (16px)
- Collapsible: click header toggles. `max-height` + `opacity` transition. Chevron rotates -90° when collapsed.
- Some sections default collapsed (history, parts, less-active sections)

### Font Discipline (CRITICAL)
- **Inter** = anything a human wrote or chose: titles, names, descriptions, labels, button text, status words
- **Mono** = anything the system generated or formatted: IDs, timestamps, dates, file sizes, quantities, serial numbers, PO numbers, revision numbers, stock counts, email addresses, file names
- See spec §20 for the complete mapping table

### Colour Discipline (CRITICAL)
- **Teal (--mark)** = interactive affordance ONLY. Links, buttons, selected states. NEVER status.
- **Green** = good, valid, complete, compliant
- **Amber** = warning, pending, expiring, attention needed
- **Red** = critical, fault, expired, danger, destructive action
- Never mix affordance with status. A link to a faulted item is teal (clickable), not red.

## Tokens and Theming

**ALL tokens live in `prototype-tokens.css`.** No inline `:root {}` or `[data-theme="light"] {}` token blocks in HTML files.

### For lens prototypes:
1. Link `lens-base.css` (which imports `prototype-tokens.css` automatically)
2. Link `lens-base.js` for shared interactions
3. Put ONLY entity-specific styles in an inline `<style>` tag

```html
<head>
  <link rel="stylesheet" href="lens-base.css">
  <style>
    /* Entity-specific styles ONLY — no tokens here */
    .my-custom-widget { ... }
  </style>
</head>
<body>
  ...
  <script src="lens-base.js"></script>
  <script>
    /* Entity-specific JS ONLY — no toggleTheme/toggleSec/etc here */
  </script>
</body>
```

### For non-lens prototypes (search, auth, etc.):
1. Link `prototype-tokens.css` directly
2. Put layout/component CSS inline (these pages don't use lens-base components)

```html
<head>
  <link rel="stylesheet" href="prototype-tokens.css">
  <style>
    /* Page-specific layout and components */
  </style>
</head>
```

### Light mode
Both dark and light tokens are in `prototype-tokens.css`. Light mode activates via `[data-theme="light"]` on the `<html>` element. All shadow, glass, border, and text values adjust automatically.

Theme toggle: small button in header (next to Related). Toggles `document.documentElement.setAttribute('data-theme', ...)`.

### Rules
- **NO inline token definitions** — all via `prototype-tokens.css`
- **NO duplicate JS** for base functions — all via `lens-base.js`
- Entity-specific tokens (e.g., a unique colour for one entity) may be added inline but MUST be documented
- See `TOKEN_MAP.md` for how prototype tokens map to production tokens

## Yacht Context for Sample Data

The yacht is **SV Andromeda**, a 60m sailing yacht. Key crew:
- **Captain:** M. Stevens
- **Chief Engineer:** R. Chen
- **1st Officer:** J. Morrison
- **ETO:** S. Park
- **Bosun:** L. Torres
- **Chef:** A. Dubois

Locations: Bridge, Engine Room, Deck, Galley, Crew Mess, Laundry, Accommodation, Stores

## Quality Checklist (verify before writing)

- [ ] Zero raw hex in component styles — all CSS variables
- [ ] Every interactive element has hover state
- [ ] Every mono element is genuinely system-generated data
- [ ] Status pills use correct colours (never teal for status)
- [ ] Teal used ONLY for affordance/interactive
- [ ] All sections are collapsible
- [ ] Primary action in identity strip top-right as split button
- [ ] Section actions ("+ Add", "Upload") are teal text in section header
- [ ] Destructive actions red, bottom of dropdown, after separator
- [ ] Light mode toggle works
- [ ] 44px min-height touch targets on all interactive rows
- [ ] IntersectionObserver scroll reveal on sections
- [ ] Title uses `<title>` tag: "Lens · {Entity Type} · v1"
