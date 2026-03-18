# Celeste PMS — Design Direction: Dark Mode
> Canonical reference for the dark theme visual language. Established March 2026.
> Prototype: `apps/web/public/elegant.html` (live at localhost:3005/elegant.html)

---

## Product Philosophy (Non-Negotiable)

**Celeste is a PA, not a filing cabinet.**

- The search interface IS the product. There is no dashboard.
- Users issue natural language commands. The NLP pipeline handles intent across all domains.
- Cross-domain results (faults + inventory + documents in one query) is the system working correctly — not a bug.
- Glass is used ONLY at entry points (search panel, modals, drawers). All data surfaces are solid.

---

## Two UI States

### Idle State
- Search panel centered, `14vh` from top
- Below search: **smart pointers** — time-sensitive, role-aware, priority-sorted
  - Surfaced by the backend, not manually curated
  - Red stripe = critical, Amber = warning, Teal = info, Green = ok
  - Each row: entity name bold + context sentence, mono metadata below, time-delta right-aligned
- **Lens jump pills** below pointers — direct route shortcuts with live counts
- Top bar: `CELESTE | SY Andromeda` left, role pill (`CHIEF ENGINEER`) right

### Results State
- Same search panel, no animation/transition needed — just results appear below
- Results grouped by domain (FAULTS, INVENTORY, DOCUMENTS, etc.)
- Query term highlighted in teal within result titles
- First result pre-selected (highest urgency/relevance)
- `↵` hint only on selected row — not on all rows
- Footer: `↑↓ Navigate · ↵ Open · Esc Clear` — always visible in results state

---

## Colour System

### Role discipline — strictly enforced

| Token | Value | Role | Used for |
|-------|-------|------|----------|
| `--brand-interactive` | `#2B8FB3` | Teal | Buttons, links, focus rings, search input divider line, query highlights in results |
| `--brand-identity` | `#B8935A` | Gold | Brand mark, vessel name, active nav indicator — NEVER interactive |
| `--status-critical` | `#C0503A` | Red | Critical faults, destructive actions only |
| `--status-warning` | `#C08840` | Amber | High priority, expiring, overdue |
| `--status-success` | `#4A9468` | Green | Closed, compliant, OK status |
| Everything else | — | Monochrome | No colour role — warm greys only |

**Teal means: you can click this.**
**Gold means: this is a proper noun (vessel, system identity).**
**Colour only appears as signal — not decoration.**

---

## Surface System (Warm Dark)

Cold blue-grey is retired. All surfaces are warm charcoal.

```css
--surface-base:     #0c0b0a   /* App background — warm near-black */
--surface-primary:  #181614   /* Cards, lens pages — warm charcoal */
--surface-elevated: #1e1b18   /* Modals, dropdowns, spotlight */
--surface-hover:    #252118   /* Hover states */
--surface-active:   #2c271f   /* Selected states */
--surface-border:   #363028   /* Borders — warm brown-grey */
```

### Asymmetric borders (creates depth without glass)
Every card/surface has a brighter top border simulating a light source from above:
```css
border-top:    1px solid rgba(255,255,255,0.10);  /* catches light */
border-right:  1px solid rgba(255,255,255,0.07);
border-bottom: 1px solid rgba(255,255,255,0.04);  /* recedes */
border-left:   1px solid rgba(255,255,255,0.07);
```

---

## Typography

### Editorial numbers (future KPI use)
```css
font-family: Georgia, 'Times New Roman', serif;  /* var(--font-serif) */
font-size: 48-52px;
font-weight: 400;  /* Light weight at large scale = gravitas */
letter-spacing: -0.02em;
```
Labels: 8px uppercase mono above. Deltas: 9px mono below. Scale contrast does the authority work.

### Operational data
```
Titles:    Inter 600, 13-15px
Metadata:  SF Mono / Fira Code, 10-11px, uppercase, 0.06em tracking
Timestamps: Mono, muted, right-aligned
```

---

## Glass Rules (macOS 26 philosophy)

| Surface | Material | Why |
|---------|----------|-----|
| Spotlight / Search panel | Glass (`backdrop-filter: blur(24px)`) | Entry point — threshold the user crosses |
| Modals | Glass | Entry/overlay |
| Navigation drawers | Glass | Entry |
| Lens pages (faults, equipment, etc.) | Solid warm charcoal | Work surfaces — glass would compete with data |
| Buttons | Solid | Actions, not entries |
| Cards / data rows | Solid | Content, not chrome |

### Spotlight panel CSS (dark mode)
```css
background: rgba(14,12,10,0.72);
backdrop-filter: blur(28px);
border-top:    1px solid rgba(255,255,255,0.13);
border-right:  1px solid rgba(255,255,255,0.06);
border-bottom: 1px solid rgba(255,255,255,0.03);
border-left:   1px solid rgba(255,255,255,0.06);
border-radius: 4px;  /* Sharp — machined, not consumer */
box-shadow: 0 20px 80px rgba(0,0,0,0.60), 0 4px 20px rgba(0,0,0,0.40);
```

Teal appears **exactly once** in the search panel: the 1px divider line beneath the input.

---

## Lens Backdrop System

Per-route ambient orb system. Each lens route has its own colour identity.

```
Fixed layer (z-index: -1)
  └── 3 radial-gradient orbs (position: fixed)
        └── filter: blur(80-100px), opacity 0.45-0.60
              └── React state drives orb colors on route change
                    └── CSS transition: 1.4s cubic-bezier(0.4,0,0.2,1)
```

Purpose: gives the glass Spotlight panel something rich to refract against.
Without the orb layer, glass reads as a flat grey rectangle.

Route palettes defined in: `apps/web/src/components/backdrop/lensColors.ts`

---

## What Is Not a Dashboard

The "home" view is NOT a dashboard. It contains:
1. The search panel (always the hero)
2. Smart pointers (time-sensitive PA surfacing, not KPI cards)
3. Lens jump pills (direct navigation shortcuts)

Smart pointers are ephemeral — they're the PA saying "before you search, here's what I know needs your attention." They are:
- Filtered by user role
- Sorted by priority + time sensitivity
- Cross-domain (a fault, a stock alert, a certificate, and a receiving ETA can all appear together)
- NOT a notification inbox — they're a live working memory

---

## Files Changed (Dark Mode Implementation)

| File | Change |
|------|--------|
| `apps/web/src/styles/tokens.css` | Warm surface tokens, gold token, serif font token, border-top token |
| `apps/web/src/styles/spotlight.css` | 4px radius, asymmetric border, light-mode border variant |
| `apps/web/src/styles/globals.css` | Import spotlight.css |
| `apps/web/src/components/backdrop/lensColors.ts` | Per-route palette map |
| `apps/web/src/components/backdrop/LensBackdrop.tsx` | Orb system, pulse handle |
| `apps/web/src/components/backdrop/BackdropRoot.tsx` | Client root with context |
| `apps/web/src/contexts/BackdropContext.tsx` | triggerPulse() context |
| `apps/web/src/app/layout.tsx` | dark class, BackdropRoot wrapper |
| `apps/web/package.json` | dev script pinned to port 3005 |

---

## Prototype

`apps/web/public/elegant.html` — full dark mode prototype showing:
- Idle state with smart pointers and lens pills
- Results state with "oil" cross-domain query
- Warm surfaces, gold nav, sharp spotlight glass
- Toggle buttons bottom-right to switch states

Served at `http://localhost:3005/elegant.html`
