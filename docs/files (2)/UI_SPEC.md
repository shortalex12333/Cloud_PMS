# UI SPECIFICATION — Build Guide

> This is the construction manual. Every dimension, proportion, color application, and component spec lives here. When building any UI element, check this file first.

---

## TYPOGRAPHY

### Scale

| Level | Size | Weight | Line-height | Color | Tracking | Transform | Use |
|-------|------|--------|-------------|-------|----------|-----------|-----|
| Display | 28px | 700 | 1.15 | `--text-primary` | -0.02em | none | Lens title on mobile when space is tight |
| Title | 24px | 600 | 1.2 | `--text-primary` | -0.01em | none | Entity name / lens title (largest text on screen) |
| Heading | 18px | 600 | 1.3 | `--text-primary` | 0 | none | Major section breaks if needed |
| Section | 14px | 600 | 1.4 | `--text-secondary` | 0 | none | Sticky section headers (Notes, Parts, History) |
| Body | 14px | 400 | 1.6 | `--text-primary` | 0 | none | Note content, descriptions, general text |
| Body Strong | 14px | 500 | 1.6 | `--text-primary` | 0 | none | Emphasis within body text (use sparingly) |
| Label | 13px | 500 | 1.4 | `--text-secondary` | 0 | none | Vital sign labels, form labels, metadata labels |
| Caption | 12px | 400 | 1.4 | `--text-tertiary` | 0 | none | Timestamps, file sizes, secondary metadata |
| Overline | 11px | 500 | 1.2 | `--text-tertiary` | 0.08em | uppercase | Entity type label (WORK ORDER, FAULT, CERTIFICATE) |
| Action | 13px | 500 | 1 | `--brand-interactive` | 0 | none | Ghost button text, inline action links |

### Rules

- **Weight creates hierarchy, not size.** The range is 14px body to 24px title. That's only 10px across the whole app. Hierarchy comes from weight (400→500→600→700) and color (tertiary→secondary→primary).
- **Never use bold (700) in body text.** Use weight 500 (Body Strong) for emphasis. Bold is reserved for titles only.
- **Line-height increases as size decreases.** Titles at 1.2 (tight, confident). Body at 1.6 (spacious, readable). This is how Apple and ChatGPT handle long-form readability.
- **Tracking (letter-spacing):** Negative on large text (tightens headings). Positive on overline/uppercase (opens small caps for legibility). Zero on body.
- **Max line length:** 680px for body text. Anything wider than ~75 characters per line degrades reading speed. On desktop, lens content max-width is 800px but paragraphs should not fill the full width.
- **Font stack:** `-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', sans-serif`. System fonts first — they load instantly on vessel WiFi. Inter as fallback for consistency.

---

## COLORS — Application Rules

### Surfaces

| Token | Where to apply | Where NOT to apply |
|-------|---------------|-------------------|
| `--surface-base` | App background, behind everything | Never as a card background |
| `--surface-primary` | Card backgrounds, section containers, lens body | Never as the app background |
| `--surface-elevated` | Modals, dropdowns, pinned sticky headers, tooltips | Never as a section container (that's primary) |
| `--surface-hover` | Hover state on cards, rows, list items | Never as a resting state |
| `--surface-active` | Selected/active item in a list, pressed button state | Never as hover (that's hover) |
| `--surface-border` | Dividers between sections, card outlines if needed | Never as a fill color |

### Text

| Token | Where to apply |
|-------|---------------|
| `--text-primary` | Titles, entity names, body content, anything the user READS |
| `--text-secondary` | Section headers, descriptions, metadata values, supporting info |
| `--text-tertiary` | Timestamps, hints, entity type overline, disabled-feeling but readable |
| `--text-disabled` | Truly disabled controls, placeholder text in empty inputs |
| `--text-inverse` | Text on colored backgrounds (primary buttons, colored badges if needed) |

### Brand Teal

| Token | Where to apply | Where NEVER to apply |
|-------|---------------|---------------------|
| `--brand-ambient` | Search bar subtle glow/shadow tint, logo, hover accents on non-critical elements | Background fills, section colors, decorative borders |
| `--brand-interactive` | Buttons, links, focus rings, toggle on-state, selected tab indicator | Status indicators, background fills, body text |
| `--brand-hover` | Hover state of interactive elements | Resting state of anything |
| `--brand-muted` | Ghost button hover background (10% opacity teal) | Text color, border color |

**The rule:** If you remove all teal from the screen, the interface should still be fully usable and hierarchically clear. Teal is signal, not structure.

### Status Colors

| State | Color token | Background token | Use |
|-------|------------|------------------|-----|
| Critical | `--status-critical` | `--status-critical-bg` | Overdue, expired, failed, rejected, zero stock, fault-active |
| Warning | `--status-warning` | `--status-warning-bg` | Expiring soon, low stock, partial delivery, needs attention |
| Success | `--status-success` | `--status-success-bg` | Complete, valid, in-stock, resolved, acknowledged |
| Neutral | `--status-neutral` | `--status-neutral-bg` | Pending, draft, not started, informational |

**Rules:**
- Status colors appear ONLY in pills, badge backgrounds, vital sign values, and indicator dots
- ALWAYS paired with text label. Never color-alone.
- Never as body text color, section background, or decorative element

---

## SHADOWS

| Token | Value (dark) | Value (light) | Use |
|-------|-------------|---------------|-----|
| `--shadow-sm` | `0 2px 8px rgba(0,0,0,0.3)` | `0 1px 3px rgba(0,0,0,0.06)` | Dropdowns, tooltips |
| `--shadow-md` | `0 8px 24px rgba(0,0,0,0.4)` | `0 4px 16px rgba(0,0,0,0.08)` | Search bar, modals |
| `--shadow-lg` | `0 16px 48px rgba(0,0,0,0.5)` | `0 12px 40px rgba(0,0,0,0.10)` | Full-screen transitions (momentary only) |

**Rules:**
- Shadows are RARE. Most elements have NO shadow.
- In dark mode, luminance steps (lighter surface = higher elevation) communicate depth. Shadows are supplementary.
- In light mode, shadows are the primary depth cue but kept extremely subtle (Apple-level restraint).
- The search bar gets `--shadow-md` because it's the primary interaction surface — it should feel like it floats.
- Modals get `--shadow-md` + backdrop overlay.
- Cards and sections: NO shadow. Depth comes from surface color difference only.

---

## RADIUS

| Token | Value | Use |
|-------|-------|-----|
| `--radius-sm` | 8px | Buttons, inputs, pills, badges, small interactive elements |
| `--radius-md` | 12px | Cards, section containers, dropdown menus, toast notifications |
| `--radius-lg` | 16px | Modals, search bar, large containers |
| `--radius-xl` | 24px | Full-screen overlay containers (if used) |
| `--radius-full` | 9999px | Status dots, avatars, fully-round pills |

**Rules:**
- Every element type gets ONE radius value. Buttons are always `--radius-sm`. Cards are always `--radius-md`. No mixing within a type.
- Nested radius: inner element radius = outer radius minus padding. If a card has `12px` radius and `16px` padding, elements inside flush to the edge should have `0px` radius (they're contained by the card's curve). Elements with their own background inside the card: `8px` radius.
- Never use `border-radius: 50%` on non-square elements (it creates ovals). Use `--radius-full` for circles only.

---

## BORDERS

| Pattern | Spec | When |
|---------|------|------|
| Section divider | `1px solid var(--surface-border)` | Between major sections in a lens |
| Subtle divider | `1px solid var(--surface-border-subtle)` | Between rows within a section (notes, history entries) |
| Card outline | `1px solid var(--surface-border)` | ONLY when surface color alone doesn't create enough separation (rare) |
| Input border | `1px solid var(--surface-border)` → `1px solid var(--brand-interactive)` on focus | Form inputs, text areas |
| No border | — | Cards on dark mode (surface color step IS the border). Most elements. |

**Rules:**
- Prefer surface color differentiation over borders. A card at `--surface-primary` on `--surface-base` background needs no border — the luminance step IS the boundary.
- Borders are structural, never decorative. If a border is just "making it look like a card," remove it and use surface color instead.
- Dividers within lists: do NOT extend full width. Indent them past the left icon/avatar (Apple pattern). Start ~48px from left edge.
- Vertical borders: almost never. The only vertical border in the app should be the Show Related sidebar's left edge.

---

## SPACING & WHITE SPACE

### Padding

| Context | Horizontal | Vertical |
|---------|-----------|----------|
| Lens body (desktop) | 40px from viewport edges | — |
| Lens body (tablet) | 24px | — |
| Lens body (mobile) | 16px | — |
| Card / section container | 20px | 16px |
| Section header row | 20px | 12px top, 12px bottom |
| List row (notes, history) | 20px | 12px top, 12px bottom |
| Button (ghost) | 12px horizontal, 8px vertical | — |
| Button (primary) | 24px horizontal, 12px vertical | — |
| Input field | 12px horizontal, 10px vertical | — |
| Status pill | 12px horizontal, 4px vertical | — |
| Toast notification | 16px all sides | — |
| Modal content | 32px all sides | — |

### Gaps Between Elements

| Between | Gap |
|---------|-----|
| Sections (Notes → Parts → History) | 24px |
| Rows within a section | 0px (use border divider, not gap) |
| Vital signs row and first section | 24px |
| Title and vital signs | 12px |
| Entity type overline and title | 4px |
| Section header and first content row | 12px |
| Action button and section header text | (same row, right-aligned, no gap — flexbox justify-between) |
| Between inline vital sign items | 16px (with · separator) |

### Proportions

| Element | Dimension |
|---------|-----------|
| Lens content max-width (desktop) | 800px, centered |
| Show Related sidebar | 420px fixed |
| Search bar width | max 720px, centered |
| Search bar height | 48px |
| Modal width | 480px max |
| Section header height | 44px (matches touch target) |
| List row minimum height | 44px (Apple touch target rule) |
| Button minimum height | 36px (ghost), 40px (primary) |
| Status pill height | 24px |
| Vital signs row height | ~40px (content + padding) |
| Media preview max-height | 240px, maintain aspect ratio |
| File preview card height | 48px |
| Toast width | auto (content-driven), max 400px |

### White Space Philosophy

- **Between sections: generous.** 24px minimum. This is what makes the interface feel calm, not cramped. ChatGPT uses ~24px between messages. Apple uses ~20px between setting groups.
- **Within sections: compact.** Rows separated by 1px dividers, not space. Information within a section is a cohesive group.
- **Around the lens body: spacious.** 40px horizontal padding on desktop means content doesn't cling to edges. The content column (800px max) centered in the viewport means large screens have ample margin.
- **Test: if the screen feels "full," add more space between sections.** An enterprise tool that feels airy communicates competence. One that feels packed communicates chaos.

---

## BUTTONS

### Ghost Button (default action button)

```
Resting:
  background: transparent
  color: var(--brand-interactive)
  font: 13px / weight 500
  padding: 8px 12px
  border-radius: var(--radius-sm)
  border: none
  min-height: 36px
  cursor: pointer

Hover:
  background: var(--brand-muted)  /* 10% teal */
  transition: background 120ms ease-out

Active/Pressed:
  background: rgba(43,143,179,0.18)  /* slightly more opaque */

Disabled:
  color: var(--text-disabled)
  cursor: not-allowed
  background: transparent

With icon prefix:
  icon: 14px, same color as text
  gap: 6px between icon and text
```

### Primary Button (confirmations, sign & submit)

```
Resting:
  background: var(--brand-interactive)
  color: var(--text-inverse)
  font: 14px / weight 600
  padding: 12px 24px
  border-radius: var(--radius-sm)
  border: none
  min-height: 40px
  cursor: pointer

Hover:
  background: var(--brand-hover)
  transition: background 120ms ease-out

Active:
  background: #1E8AAB  /* slightly darker than hover */

Disabled:
  background: var(--surface-hover)
  color: var(--text-disabled)
  cursor: not-allowed

Loading:
  content replaced with 16px spinner icon, centered
  pointer-events: none
```

### Danger Button (destructive actions — delete, reject)

```
Resting:
  background: transparent
  color: var(--status-critical)
  font: 13px / weight 500
  padding: 8px 12px
  border: 1px solid var(--status-critical)
  border-radius: var(--radius-sm)
  min-height: 36px

Hover:
  background: var(--status-critical-bg)

Confirmation variant (after first click):
  background: var(--status-critical)
  color: var(--text-inverse)
```

### Icon-Only Button (close, back, forward, settings)

```
  width: 36px
  height: 36px
  border-radius: var(--radius-sm)
  background: transparent
  color: var(--text-secondary)
  display: flex, center/center
  icon: 18px

Hover:
  background: var(--surface-hover)
  color: var(--text-primary)
```

---

## STATUS PILLS

```
  display: inline-flex
  align-items: center
  gap: 6px
  padding: 4px 12px
  border-radius: var(--radius-full)
  font: 12px / weight 500
  height: 24px

  background: var(--status-{level}-bg)   /* 10% opacity tint */
  color: var(--status-{level})           /* full color text */

  Optional dot prefix:
    width: 6px
    height: 6px
    border-radius: 50%
    background: var(--status-{level})    /* solid dot */
```

**Mapping:**
- Pending, Draft, Not started → neutral
- In Progress, Submitted, Partial → warning (it's in-flight, needs monitoring)
- Complete, Resolved, Valid, Acknowledged, In Stock → success
- Overdue, Expired, Rejected, Failed, Zero Stock, Fault → critical
- Low Stock, Expiring Soon → warning

---

## INPUTS & FORM FIELDS

```
  height: 40px (single line) / auto (textarea)
  padding: 10px 12px
  font: 14px / weight 400
  color: var(--text-primary)
  background: var(--surface-base)
  border: 1px solid var(--surface-border)
  border-radius: var(--radius-sm)
  width: 100%

Placeholder:
  color: var(--text-disabled)

Focus:
  border-color: var(--brand-interactive)
  outline: none
  box-shadow: 0 0 0 3px var(--brand-muted)  /* focus ring */

Error:
  border-color: var(--status-critical)
  box-shadow: 0 0 0 3px var(--status-critical-bg)

Disabled:
  background: var(--surface-hover)
  color: var(--text-disabled)
  cursor: not-allowed
```

### Dropdown / Select

```
  Same as input base styling
  Right icon: chevron-down, 14px, var(--text-tertiary)
  Dropdown menu:
    background: var(--surface-elevated)
    border: 1px solid var(--surface-border)
    border-radius: var(--radius-md)
    box-shadow: var(--shadow-sm)
    z-index: var(--z-sidebar)
    max-height: 240px, overflow-y: auto

  Option row:
    padding: 10px 12px
    min-height: 40px
    hover: var(--surface-hover)
    selected: var(--surface-active) + var(--brand-interactive) text
```

### Textarea

```
  Same as input but:
    min-height: 100px
    resize: vertical
    line-height: 1.6
```

---

## CARDS

### Section Container (the building block of every lens)

```
  background: var(--surface-primary)
  border-radius: var(--radius-md)
  padding: 0 (header handles its own, content handles its own)
  border: none (dark mode) / 1px solid var(--surface-border) (light mode, if needed)
  margin-bottom: 24px (gap between sections)
  overflow: hidden (clips content to radius)
```

### Entity Card (in lists: parts, equipment references, search results)

```
  background: var(--surface-primary)
  border-radius: var(--radius-md)
  padding: 16px 20px
  min-height: 44px
  cursor: pointer (if clickable)
  transition: background 120ms ease-out

Hover (if clickable):
  background: var(--surface-hover)

Content layout:
  Left: icon or status dot (optional)
  Center: title (14px/500) + subtitle (12px/400/tertiary)
  Right: metadata value or chevron
  flex, align-items: center, justify-content: space-between
```

### File Preview Card (documents, not media)

```
  background: var(--surface-primary)
  border-radius: var(--radius-md)
  padding: 12px 16px
  height: 48px
  display: flex, align-items: center, gap: 12px
  cursor: pointer

  Icon: 20px, var(--text-tertiary)  (📄 for PDF, 📊 for xlsx, etc.)
  Filename: 14px/500/var(--text-primary)
  File size: 12px/400/var(--text-tertiary)

Hover:
  background: var(--surface-hover)
```

---

## MODALS

### Signature Modal

```
Backdrop:
  position: fixed, inset: 0
  background: rgba(0,0,0,0.6)
  z-index: var(--z-modal)
  display: flex, center/center

Panel:
  background: var(--surface-elevated)
  border-radius: var(--radius-lg)
  padding: 32px
  width: 480px max
  box-shadow: var(--shadow-md)

Header:
  title: 18px / weight 600 / var(--text-primary)
  subtitle: 14px / weight 400 / var(--text-secondary)
  margin-bottom: 24px

Content:
  key-value rows for user identity
  label: 13px / var(--text-tertiary) / left-aligned
  value: 14px / var(--text-primary) / left-aligned
  rows separated by 8px gap
  divider above action bar: 1px solid var(--surface-border), margin 24px 0

Footer:
  display: flex, justify-content: flex-end, gap: 12px
  [Cancel] = ghost button
  [Sign & Submit] = primary button
```

### Confirmation Modal (simpler)

```
  Same backdrop
  Panel: 400px max, 24px padding
  Message: 14px body text
  Footer: same as signature modal
```

---

## TOAST NOTIFICATIONS

```
Position:
  fixed, bottom: 32px, left: 50%, transform: translateX(-50%)
  z-index: var(--z-toast)

Container:
  background: var(--surface-elevated)
  border: 1px solid var(--surface-border)
  border-radius: var(--radius-md)
  padding: 12px 16px
  box-shadow: var(--shadow-sm)
  display: flex, align-items: center, gap: 10px
  max-width: 400px

Icon:
  16px
  ✓ success: var(--status-success)
  ⚠ warning: var(--status-warning)
  ✕ error: var(--status-critical)

Text:
  14px / weight 400 / var(--text-primary)

Animation:
  Enter: translateY(8px) → translateY(0), opacity 0→1, 200ms ease-out
  Exit: opacity 1→0, 120ms ease-out
  Auto-dismiss: 4 seconds
```

---

## NAVIGATION HEADER (fixed at top of lens)

```
  position: fixed, top: 0, left: 0, right: 0
  height: 56px
  background: var(--surface-base)
  border-bottom: 1px solid var(--surface-border)
  z-index: var(--z-header)
  padding: 0 24px
  display: flex, align-items: center, justify-content: space-between

Left cluster:
  [← Back] icon button (36px)
  [→ Forward] icon button (36px, only if forward history exists)
  gap: 4px

Center:
  Entity type overline: 11px / uppercase / tracking 0.08em / var(--text-tertiary)
  (vertically centered in header)

Right cluster:
  [Show Related] ghost button (if applicable)
  [× Close] icon button (36px)
  gap: 8px
```

---

## SEARCH BAR (home state)

```
  max-width: 720px
  margin: 0 auto
  position: relative (vertically centered on home screen)

Input:
  height: 48px
  background: var(--surface-primary)
  border: 1px solid var(--surface-border)
  border-radius: var(--radius-lg)  /* 16px — pill-like */
  padding: 0 20px 0 48px  (left padding for + icon)
  font: 15px / weight 400
  color: var(--text-primary)
  box-shadow: var(--shadow-md)

  Focus:
    border-color: var(--brand-interactive)
    box-shadow: var(--shadow-md), 0 0 0 3px var(--brand-muted)

  + icon (left):
    position: absolute, left: 16px, center vertically
    20px, var(--text-tertiary)

  × clear icon (right, when has value):
    position: absolute, right: 16px
    icon button style (36px)

Results dropdown:
  margin-top: 8px
  background: var(--surface-primary)
  border: 1px solid var(--surface-border)
  border-radius: var(--radius-md)
  box-shadow: var(--shadow-md)
  max-height: 480px
  overflow-y: auto

  Category header:
    11px / uppercase / tracking 0.08em / var(--brand-ambient) / padding: 12px 20px 4px
  
  Result row:
    padding: 12px 20px
    min-height: 56px
    hover: var(--surface-hover)
    Title: 14px / weight 500 / var(--text-primary)
    Description: 13px / weight 400 / var(--text-secondary)
```

---

## SHOW RELATED SIDEBAR

```
  position: fixed, top: 0, right: 0, bottom: 0
  width: 420px
  background: var(--surface-primary)
  border-left: 1px solid var(--surface-border)
  z-index: var(--z-sidebar)
  overflow-y: auto
  box-shadow: var(--shadow-md)

Enter animation:
  translateX(100%) → translateX(0), 300ms var(--ease-out)

Header:
  padding: 16px 20px
  border-bottom: 1px solid var(--surface-border)
  title: 14px / weight 600 / var(--text-primary) / "Related"
  [× Close] icon button, right-aligned

Results:
  Same layout as search results
  Infinite scroll, loads on demand
  Loading: skeleton cards (3 placeholder rows)
```

---

## TRANSITIONS & ANIMATION

| Event | Duration | Easing | What happens |
|-------|----------|--------|-------------|
| Button hover | 120ms | ease-out | Background color shifts |
| Card/row hover | 120ms | ease-out | Background color shifts |
| Sticky header pin | 120ms | ease-out | Background to elevated, border appears |
| Toast enter | 200ms | ease-out | Slide up 8px + fade in |
| Toast exit | 120ms | ease-out | Fade out |
| Lens open (from search) | 300ms | `cubic-bezier(0.16,1,0.3,1)` | Glass layer fades in, lens slides up, glass fades out |
| Lens → Lens | 300ms | `cubic-bezier(0.16,1,0.3,1)` | Current fades, glass doorway, new fades in |
| Lens close | 200ms | ease-out | Lens fades, search bar fades in |
| Sidebar open | 300ms | `cubic-bezier(0.16,1,0.3,1)` | Slide from right |
| Sidebar close | 200ms | ease-out | Slide to right |
| Dropdown open | 150ms | ease-out | Scale from 0.95 + fade in |
| Modal open | 200ms | ease-out | Backdrop fade + modal scale from 0.95 |
| Modal close | 150ms | ease-out | Backdrop fade + modal fade |
| Success highlight | 1500ms | ease-in-out | Row bg: surface-active → surface-primary (pulse) |

**Glass doorway effect (lens transitions only):**
```css
.glass-transition {
  background: var(--glass-bg);
  backdrop-filter: var(--glass-blur);
  border: var(--glass-border);
  transition: opacity var(--duration-slow) var(--ease-out);
}
```

---

## LOADING STATES

### Skeleton (default — use everywhere instead of spinners)

```css
.skeleton {
  background: var(--surface-hover);
  border-radius: var(--radius-sm);
  animation: shimmer 1.5s ease-in-out infinite;
}

@keyframes shimmer {
  0% { opacity: 0.5; }
  50% { opacity: 0.8; }
  100% { opacity: 0.5; }
}
```

| Element | Skeleton shape |
|---------|---------------|
| Title | Rectangle: 60% width × 24px |
| Body text line | Rectangle: 100% width × 14px (stack 3 with 8px gap) |
| Vital signs row | Rectangle: 80% width × 20px |
| Section header | Rectangle: 40% width × 14px |
| Entity card | Rectangle: 100% width × 56px |
| Media preview | Rectangle: 100% width × 160px |
| Status pill | Rectangle: 64px × 24px, radius-full |

### When to show:
- **Immediately** on lens open: header + 3 skeleton sections
- **Immediately** on search: "Searching..." text under input
- **Per-section** as data arrives: section content replaces its skeleton independently

### When NOT to show:
- Never show a full-page spinner
- Never show a blank screen
- Never block the entire UI while one section loads

---

## RESPONSIVE

| Breakpoint | Width | Lens padding | Content max-width | Sidebar behavior |
|-----------|-------|-------------|-------------------|-----------------|
| Desktop | > 1024px | 40px sides | 800px centered | 420px side-by-side |
| Tablet | 768–1024px | 24px sides | Full width | Overlay (slides in) |
| Mobile | < 768px | 16px sides | Full width | Full-screen overlay |

### Touch targets
- **Minimum height: 44px** for all tappable elements. No exceptions.
- On mobile: increase to 48px
- Ghost buttons that appear small on desktop: add invisible padding to reach 44px tap area

---

## LANGUAGE & COPY

### Tone
- **Direct, factual, no filler.** "Note added" not "Your note has been successfully saved!"
- **No exclamation marks.** Ever. This is professional maritime software.
- **No emoji in system messages.** Icons yes, emoji no.
- **Present tense.** "Save" not "Saving..." (loading states are the exception: "Searching...")

### Button labels
- Use verbs: "Add Note", "Sign", "Reject", "Close"
- Keep to 1-3 words max
- Destructive actions: clear about what will happen: "Delete Note" not just "Delete"

### Empty states
- Specific, not generic: "No parts linked" not "No data found"
- Include the relevant action: "No parts linked — Add Part to track inventory"
- Tone: helpful, not apologetic. Never "Sorry, nothing here"

### Error messages
- What happened + what to do: "Connection lost — changes will sync when reconnected"
- Never expose technical details: "RLS policy violation" → "Access restricted"
- Never blame the user: "Invalid input" → "Please enter a valid date"

### Timestamps
- Relative when recent: "3 hours ago", "Yesterday", "2 days ago"
- Absolute when old: "Jan 23, 2026"
- Threshold: switch to absolute after 7 days
- Always include time for today's entries: "Today at 14:32"
