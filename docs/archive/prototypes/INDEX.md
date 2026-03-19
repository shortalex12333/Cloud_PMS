# Prototype Index

> **Master catalogue of all design prototypes for Celeste PMS.**
> Every renderable HTML file in this directory is documented here.
> Static server: `python3 -m http.server 3006` from this directory.

---

## How This Directory Is Organised

```
prototypes/
  INDEX.md                          ← You are here
  PROTOTYPE_GUIDE.md                ← Build instructions for agents writing lens HTML
  DESIGN_SIGNATURES_AND_POPUPS.md   ← Architecture spec for popup/signature system
  WORK_ORDER_LENS_REVIEW.md         ← Owner review notes on Work Order lens

  lens-base.css                     ← Shared brand CSS (tokens, reset, components)
  lens-base.js                      ← Shared JS (theme toggle, section collapse, scroll reveal)

  elegant.html                      ← Spotlight Search — dark mode
  light.html                        ← Spotlight Search — light mode
  popup-journeys.html               ← Universal Action Popup gallery (L0–L5)
  show-related.html                 ← Show Related drawer (GraphRAG discovery)

  lens-work-order.html              ← CANONICAL lens reference (all others derive from this)
  lens-equipment.html
  lens-fault.html
  lens-certificate.html
  lens-parts.html
  lens-purchase-order.html
  lens-document.html
  lens-warranty.html
  lens-hours-of-rest.html
  lens-shopping-list.html
  lens-receiving.html
  lens-handover.html

  archive/                          ← Historical iterations (git-like record, not canonical)
```

---

## Spotlight Search (Homepage)

The main search experience. User types a natural language command; NLP pipeline returns cross-domain results rendered Raycast-style.

| File | Mode | Description | Status |
|------|------|-------------|--------|
| `elegant.html` | Dark | Homepage with search bar, grouped result rows, entity type icons, match highlighting. Warm dark surfaces, teal affordance, glass header. | **Owner-approved** |
| `light.html` | Light | Same layout, light mode tokens. White surfaces, softened shadows, adjusted contrast. | **Owner-approved** |

**Design docs:**
- `docs/styling-frontend-agent/design-direction/DESIGN_DIRECTION_DARK.md` — dark mode direction
- `docs/styling-frontend-agent/plans/2026-03-16-search-results-ux.md` — search results UX plan
- `docs/superpowers/specs/2026-03-16-frontend-design-philosophy.md` — master design spec (§0–15 surface patterns)

**Production code:** `src/components/spotlight/SpotlightSearch.tsx`, `SpotlightResultRow.tsx`, `src/styles/spotlight.css`, `src/lib/spotlightGrouping.ts`

---

## Entity Lens Views (12 lenses)

Each lens renders a single entity as a scrolling document. Identity strip at top, collapsible sections below, primary action split button top-right. Dark mode default with light mode toggle.

All lenses share `lens-base.css` (tokens + components) and `lens-base.js` (interactions).

| File | Entity | Key Sections | Status |
|------|--------|-------------|--------|
| `lens-work-order.html` | Work Order | Checklist, parts, notes, history, attachments, official docs | **CANONICAL** — all others derive from this |
| `lens-equipment.html` | Equipment | Specs, spare parts, maintenance history, active WOs/faults, certs | Owner-approved |
| `lens-fault.html` | Fault | Journal/first-log, corrective action, root cause, related entities | Owner-approved |
| `lens-certificate.html` | Certificate | Crew + machinery, survey dates, renewal history, related equipment | Owner-approved |
| `lens-parts.html` | Parts/Inventory | Stock levels, MOQ intelligence, where used, purchase history, specs | Owner-approved |
| `lens-purchase-order.html` | Purchase Order | Line items, approval signatures, receiving log, budget context | Owner-approved |
| `lens-document.html` | Document | Original file preview, revision history, read acknowledgement | Owner-approved |
| `lens-warranty.html` | Warranty | Coverage, claims, financial summary, days remaining, related entities | Owner-approved |
| `lens-hours-of-rest.html` | Hours of Rest | 24h entry grid, 7-day view, compliance checking, template system | Owner-approved |
| `lens-shopping-list.html` | Shopping List | Line items, lifecycle status, cross-entity links | Owner-approved |
| `lens-receiving.html` | Receiving | Delivery tracking, acceptance workflow, barcode print, discrepancy email | Owner-approved |
| `lens-handover.html` | Handover | View-only rendered document, embedded entity links, signatures | Owner-approved |

**Design docs:**
- `docs/superpowers/specs/2026-03-16-frontend-design-philosophy.md` — §16–22 (entity view philosophy, identity strip, sections, actions, font mapping, content patterns)
- `docs/superpowers/specs/2026-03-16-lens-entity-views-design.md` — lens entity views spec
- `PROTOTYPE_GUIDE.md` (this directory) — build instructions for agents

**Brand rules:**
- Dark mode hover = neutral grey `#242424` (not amber)
- All action buttons = ghost teal (`--teal-bg` + `--mark`), never solid
- Standard button: 44px height, 8px radius
- Entity views are documents, not dashboards — they scroll

---

## Universal Action Popups (Signatures)

Gallery of all popup journey types, demonstrating the schema-driven signature ladder from L0 (tap) to L5 (chain approval).

| File | Description | Status |
|------|-------------|--------|
| `popup-journeys.html` | 8 popup examples: Read Overlay, L1 Confirm, L2 Attest, L3 Verify (PIN), L4 Wet Sign, L5 Chain, Data Gates, Entity Search. Annotations explain every design decision. | **Owner-approved** |

**Architecture:** Frontend is a dumb shell. Backend provides `ActionSchema` (fields, gates, signature level, permissions). Two surfaces: Read Overlay (lightweight, no signature) and Mutation Popup (heavier, gated, signed).

**Design docs:**
- `DESIGN_SIGNATURES_AND_POPUPS.md` (this directory) — full architecture spec with schema shape, gate types, signature levels, SQL schema, production path

**Key design decisions:**
- Backdrop opacity scales with signature level (25% read → 60% L4/L5)
- Data gates block submission until prerequisites met (checklist, attachments, required fields)
- PIN digits: `2px solid var(--txt3)` border, teal fill when entered
- No amber for gates — grey/neutral for pending, green for satisfied

---

## Show Related (GraphRAG Discovery)

Right-side drawer that discovers semantically related entities using entity_serializer embeddings + f1_search_cards.

| File | Description | Status |
|------|-------------|--------|
| `show-related.html` | Interactive drawer: click "Related" button → 320px drawer slides in from right → loading spinner → staggered result reveal. FK groups (direct links) + "Also Related" signal group (semantic matches). Teal match highlighting. | **Pending owner review** |

**Pipeline:** Source entity → entity_serializer (concise attribute-rich text) → embedding → f1_search_cards → cross-domain results. Distinct from Spotlight Search which uses projection worker (keyword density for findability).

**Design docs:**
- Show Related signal v2 notes in project memory
- `src/components/lens/RelatedDrawer.tsx` — production React implementation

**Key design decisions:**
- Drawer width 320px, panel 720px, flex layout
- FK groups first (Equipment, Faults, Parts, Docs), then "Also Related" signal group
- Match highlighting: teal (`--mark`) + font-weight 500 for source entity attribute matches
- Staggered fade-in animation per result group (100ms intervals)

---

## Auth (Sign In / Sign Up)

| File | Mode | Description | Status |
|------|------|-------------|--------|
| `auth.html` | Dark + Light | Sign-in and sign-up card. Teal accent, glass topbar, orb backdrop. Theme toggle. Error states, password reveal, social auth stubs. | **Owner-approved** |

---

## Shared Assets

| File | Purpose |
|------|---------|
| `prototype-tokens.css` | **Single source of truth** for all design tokens (surfaces, text, brand, signal colours, borders, shadows, typography). Dark + light mode. Dual aliases for backward compatibility (lens names ↔ elegant/auth names). Every prototype links here directly or via lens-base.css. |
| `lens-base.css` | ~660 lines. Imports `prototype-tokens.css` for tokens. Contains reset, panel, header, identity strip, pills, split button, dropdown, section system, doc rows, notes, audit trail, attachments, parts, checklist, history, entity icons, preview area, print button, scroll reveal, KV rows, equip links, report footer. |
| `lens-base.js` | ~40 lines. `toggleTheme()` (CSS-only icon swap), `toggleSec()`, `toggleDd()`/`closeDd()`, IntersectionObserver scroll reveal. |
| `TOKEN_MAP.md` | Prototype → Production token mapping. Bridge document for the production pairing phase. |

---

## Documentation Files

| File | Purpose |
|------|---------|
| `INDEX.md` | This file — master catalogue |
| `PROTOTYPE_GUIDE.md` | Build instructions for agents writing new lens prototypes |
| `TOKEN_MAP.md` | Prototype → Production token mapping for the pairing phase |
| `DESIGN_SIGNATURES_AND_POPUPS.md` | Architecture spec for popup/signature system (schema shape, gates, levels, SQL) |
| `WORK_ORDER_LENS_REVIEW.md` | Owner review notes on Work Order lens |

**Related docs elsewhere:**
| Doc | Location |
|-----|----------|
| Frontend Design Philosophy (master) | `docs/superpowers/specs/2026-03-16-frontend-design-philosophy.md` |
| Design Direction — Dark Mode | `docs/styling-frontend-agent/design-direction/DESIGN_DIRECTION_DARK.md` |
| Search Results UX Plan | `docs/styling-frontend-agent/plans/2026-03-16-search-results-ux.md` |
| Lens Entity Views Spec | `docs/superpowers/specs/2026-03-16-lens-entity-views-design.md` |
| Phase 2 Available Actions | `docs/superpowers/specs/2026-03-16-phase2-available-actions-design.md` |
| Handover Module | `docs/superpowers/specs/2026-03-16-handover-module-design.md` |
| Settings Module | `docs/superpowers/specs/2026-03-16-settings-module-design.md` |
| Ledger Module | `docs/superpowers/specs/2026-03-16-ledger-module-design.md` |

---

## Archive (Historical Iterations)

Files in `archive/` are preserved for historical reference. They are NOT canonical — do not use as build references.

| File | What It Was |
|------|-------------|
| `lens-work-order-v2.html` | WO lens iteration 2 — early section layout |
| `lens-work-order-v3.html` | WO lens iteration 3 — added split button |
| `lens-work-order-v4.html` | WO lens iteration 4 — added all sections |
| `lens-work-order-v5a.html` | WO lens v5 variant A — typography experiment |
| `lens-work-order-v5b.html` | WO lens v5 variant B — spacing experiment |
| `lens-work-order-v5c.html` | WO lens v5 variant C — section order experiment |
| `lens-work-order-v6.html` | WO lens v6 — final pre-shared-base version (became canonical `lens-work-order.html`) |
| `authority.html` | Early design exploration — authority/hierarchy concept |
| `glass-preview.html` | Glass effect experimentation |
| `refine.html` | Design refinement iteration |
| `variations.html` | Multiple design variation comparisons |

---

## Localhost Serving

```bash
# Serve all prototypes (from this directory)
cd apps/web/public/prototypes
python3 -m http.server 3006

# URLs
http://localhost:3006/elegant.html            # Spotlight dark
http://localhost:3006/light.html              # Spotlight light
http://localhost:3006/popup-journeys.html     # Popup gallery
http://localhost:3006/show-related.html       # Related drawer
http://localhost:3006/lens-work-order.html    # Canonical lens
http://localhost:3006/lens-equipment.html     # ... (all 12 lenses)
```

Note: The Python server must be started from the `prototypes/` directory. Port 3005 is typically occupied by Next.js dev server.
