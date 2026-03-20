# Token Map — Prototype → Production

> **Purpose:** During the pairing phase, a developer reads this ONCE and knows exactly what maps where.
> Prototypes use warm, hand-tuned tokens. Production uses ChatGPT-inspired neutral tokens.
> Not every value matches — this doc flags every difference.

---

## Surfaces

| Prototype Token | Prototype Value (dark) | Production Token | Production Value (dark) | Match? |
|----------------|----------------------|-----------------|----------------------|--------|
| `--surface-base` / `--bg` | `#0c0b0a` | `--surface-base` | `#111111` | Hex differs (warmer) |
| `--surface` / `--surface-primary` | `#181614` | `--surface-primary` | `#171717` | Hex differs (warmer) |
| `--surface-el` / `--surface-elevated` | `#1e1b18` | `--surface-elevated` | `#1E1E1E` | Hex differs (warmer) |
| `--surface-hover` | `#242424` | `--surface-hover` | `#252525` | Close (1 shade) |
| — | — | `--surface-active` | `#323232` | No prototype equiv |
| — | — | `--surface-border` | `#404040` | See borders below |
| — | — | `--surface-border-subtle` | `#222222` | See borders below |

**Decision needed:** Warm prototype surfaces → neutral production. Choose one or the other during pairing.

---

## Text

| Prototype Token | Prototype Value (dark) | Production Token | Production Value (dark) | Match? |
|----------------|----------------------|-----------------|----------------------|--------|
| `--txt` / `--txt-primary` | `rgba(255,255,255,0.92)` | `--text-primary` | `#ECECEC` | Format differs (rgba vs hex). Visually ~same |
| `--txt2` / `--txt-secondary` | `rgba(255,255,255,0.55)` | `--text-secondary` | `#A0A0A0` | Format differs. `0.55` ≈ `#8C8C8C`, prod is lighter |
| `--txt3` / `--txt-tertiary` | `rgba(255,255,255,0.70)` | `--text-tertiary` | `#666666` | Differs. Prototype is brighter (user bumped) |
| `--txt-ghost` | `rgba(255,255,255,0.40)` | `--text-disabled` | `#3A3A3A` | Differs. Prototype ghost = rgba, prod disabled = hex |

**Note:** Prototype uses rgba transparency (blends with surface). Production uses flat hex. This is intentional in production (no blending artifacts).

---

## Brand / Teal

| Prototype Token | Prototype Value | Production Token | Production Value | Match? |
|----------------|----------------|-----------------|-----------------|--------|
| `--mark` / `--mark-colour` | `#5AABCC` | `--brand-interactive` | `#2B8FB3` | Hex differs (prototype is lighter) |
| `--teal` | `#3A7C9D` | `--brand-ambient` | `#3A7C9D` | Exact match |
| `--teal-bg` | `rgba(58,124,157,0.12)` | `--brand-muted` | `rgba(43,143,179,0.10)` | Close (slightly different base) |
| `--mark-hover` | `rgba(58,124,157,0.22)` | `--brand-hover` | `#239AB8` | Differs (rgba vs flat hex) |

**Decision needed:** `--mark` (#5AABCC) vs `--brand-interactive` (#2B8FB3). These are the two "main teal" shades across the product. Prototype is lighter for contrast on warm surfaces; production is deeper.

---

## Signal Colours (Status)

| Prototype Token | Prototype Value | Production Token | Production Value | Match? |
|----------------|----------------|-----------------|-----------------|--------|
| `--red` | `#C0503A` | `--status-critical` | `#E5484D` | Hex differs (prototype is muted red-brown) |
| `--red-bg` | `rgba(192,80,58,0.10)` | `--status-critical-bg` | `rgba(229,72,77,0.10)` | Base colour differs |
| `--amber` | `#C4893B` | `--status-warning` | `#F5A623` | Hex differs (prototype = warm amber, prod = bright yellow) |
| `--amber-bg` | `rgba(196,137,59,0.10)` | `--status-warning-bg` | `rgba(245,166,35,0.10)` | Base colour differs |
| `--green` | `#4A9468` | `--status-success` | `#30A46C` | Hex differs (prototype muted, prod vivid) |
| `--green-bg` | `rgba(76,175,129,0.10)` | `--status-success-bg` | `rgba(48,164,108,0.10)` | Base colour differs |
| `--blue` | `#5B8DEF` | — | — | No production equiv yet |

**Pattern:** Prototype status colours are intentionally muted (read well on warm surfaces). Production uses Radix-style vivid colours. Pairing must pick one palette.

---

## Borders

| Prototype Token | Prototype Value (dark) | Production Token | Production Value (dark) | Match? |
|----------------|----------------------|-----------------|----------------------|--------|
| `--border-sub` / `--border` | `rgba(255,255,255,0.07)` | `--surface-border` | `#404040` | Different approach (rgba vs hex) |
| `--border-top` | `rgba(255,255,255,0.11)` | — | — | No production equiv (asymmetric borders are prototype-only) |
| `--border-side` | `rgba(255,255,255,0.06)` | — | — | No production equiv |
| `--border-bottom` | `rgba(255,255,255,0.03)` | — | — | No production equiv |
| `--border-faint` / `--border-subtle` | `rgba(255,255,255,0.04)` | `--surface-border-subtle` | `#222222` | Different approach |
| `--border-chrome` | `rgba(255,255,255,0.08)` | — | — | No production equiv |

**Key difference:** Prototype uses asymmetric borders (top brighter, bottom darker) for 3D illusion. Production uses flat uniform borders. During pairing, decide whether to bring asymmetric borders to production or flatten prototypes.

---

## Shadows

| Prototype Token | Production Token | Match? |
|----------------|-----------------|--------|
| `--shadow-panel` | `--shadow-lg` | Values differ (prototype is heavier) |
| `--shadow-drop` | `--shadow-md` | Values differ |
| `--shadow-tip` | `--shadow-sm` | Values differ |

---

## Typography

| Prototype Token | Production Token | Match? |
|----------------|-----------------|--------|
| `--font-sans` (`'Inter'...`) | `--font-family` (`ui-sans-serif...`) | Different stacks (prototype uses Inter specifically) |
| `--font-mono` (`'SF Mono'...`) | `--font-mono` (`'SF Mono'...`) | Close match |

---

## Tokens in Prototype with NO Production Equivalent

These need to be created in production during pairing:

| Prototype Token | Purpose |
|----------------|---------|
| `--glass-bg` | Frosted glass background (lens header) |
| `--split-bg` / `--split-bg-hover` | Disabled split button background |
| `--mark-underline` | Link underline at reduced opacity |
| `--mark-thumb` | Thumbnail teal overlay |
| `--on-status` | Text on coloured backgrounds (always #fff) |
| `--neutral-bg` | Grey pill/tag backgrounds |
| `--border-top/side/bottom` | Asymmetric border system |

---

## Tokens in Production with NO Prototype Equivalent

These exist in production but prototypes don't use them:

| Production Token | Purpose |
|-----------------|---------|
| `--space-*` | Spacing scale (4px base) |
| `--radius-*` | Border radius hierarchy |
| `--z-*` | Z-index scale |
| `--duration-*` / `--ease-out` | Transition timing |
| `--font-size-*` / `--font-weight-*` | Typography scale |
| `--touch-target-*` | Touch target dimensions |
| `--lens-*` | Layout proportions |

---

## Quick Reference for Pairing

During the conversion, replace prototype tokens using this cheat sheet:

```css
/* In production components, use: */
var(--surface-base)       /* instead of var(--surface-base) — same name, different value */
var(--text-primary)       /* instead of var(--txt) */
var(--text-secondary)     /* instead of var(--txt2) */
var(--text-tertiary)      /* instead of var(--txt3) */
var(--brand-interactive)  /* instead of var(--mark) */
var(--surface-border)     /* instead of var(--border-sub) */
var(--status-critical)    /* instead of var(--red) */
var(--status-warning)     /* instead of var(--amber) */
var(--status-success)     /* instead of var(--green) */
```
