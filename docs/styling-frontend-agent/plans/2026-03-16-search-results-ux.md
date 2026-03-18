# Search Results UX — Full Polish Plan (Light + Dark)

> **For agentic workers:** REQUIRED: Use superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring both `elegant.html` (dark) and `light.html` (light) to production-quality standard across results state contrast, depth, honest affordances, query transparency, and brand colour discipline.

**Architecture:** Direct CSS + HTML edits to the two standalone prototype files. No build step. All changes verified by opening `localhost:3005` in a browser. Both files share structural parity — every fix is applied to both unless noted as mode-specific.

**Files:**
- Modify: `apps/web/public/elegant.html`
- Modify: `apps/web/public/light.html`

---

## Issue → Task Mapping

| User Issue | Task |
|---|---|
| Category headers (Faults, Inventory, Documents) weak contrast | Task 1 |
| Icon adjacent to result row weak | Task 1 |
| Sub-info per row (WO·1156 etc.) weak contrast | Task 1 |
| "5 results for oil" weak contrast at bottom | Task 1 |
| First result permanently active — wrong affordance | Task 2 |
| Keyboard hints (↑↓↵Esc) shown but not wired — hidden on mobile | Task 3 |
| No result row visual container — results float on backdrop | Task 4 |
| Light mode is flat beige with no depth vs dark's orbs/gradients | Task 5 |
| Query interpretation panel — what the NLP understood | Task 6 |
| Brand teal `#3A7C9D` fails 4.5:1 on light beige for mark highlights | Task 7 |
| `CELESTE` / `SY Andromeda` using gold — should be brand teal | Task 8 |

---

## Chunk 1: Contrast Fixes

### Task 1 — Fix contrast on all result-state text (both files)

**Problem:** Category headers, icons, sub-info, and result count use `--txt-ghost` (~1.6:1). All must reach 4.5:1 minimum.

**Fix map:**

| Selector | Current | Fixed |
|---|---|---|
| `.result-group-label` | `var(--txt-ghost)` | `var(--txt-tertiary)` |
| `.result-icon` | `var(--txt-ghost)` | `var(--txt-tertiary)` |
| `.result-sub` | `var(--txt-tertiary)` | `var(--txt-secondary)` — bumped one level for 10px mono |
| Results count `"5 results for..."` | `var(--txt-ghost)` | `var(--txt-tertiary)` |

**Why `.result-sub` gets bumped to secondary:** At 10px mono, tertiary sits at 4.5:1 against the page bg but falls to ~3.8:1 against a white card surface. Secondary is safer at 6:1+.

**elegant.html:**

- [ ] **Step 1: Fix `.result-group-label` colour**

Find in CSS:
```css
.result-group-label {
  ...
  color: var(--txt-ghost);
```
Change to:
```css
  color: var(--txt-tertiary);
```

- [ ] **Step 2: Fix `.result-icon` colour**

Find:
```css
.result-icon { width: 14px; height: 14px; color: var(--txt-ghost); flex-shrink: 0; }
```
Change to:
```css
.result-icon { width: 14px; height: 14px; color: var(--txt-tertiary); flex-shrink: 0; }
```

- [ ] **Step 3: Fix `.result-sub` colour**

Find:
```css
.result-sub {
  font-size: 10.5px; color: var(--txt-tertiary);
```
Change to:
```css
.result-sub {
  font-size: 10.5px; color: var(--txt-secondary);
```

- [ ] **Step 4: Fix results count footer text**

Find the inline style on the `"5 results for..."` span:
```html
<span style="font-size:10px; color: var(--txt-ghost); font-family: var(--font-mono);">5 results for "oil"</span>
```
Change to:
```html
<span style="font-size:10px; color: var(--txt-tertiary); font-family: var(--font-mono);">5 results for "oil"</span>
```

- [ ] **Step 5: Repeat all four steps in light.html** (same selectors, same changes)

- [ ] **Step 6: Commit**
```bash
git add apps/web/public/elegant.html apps/web/public/light.html
git commit -m "fix(prototype): bump result state text contrast to 4.5:1 minimum"
```

---

## Chunk 2: Affordance Honesty

### Task 2 — Remove permanent active state from first result (both files)

**Problem:** First result has `.active` class hardcoded. This implies keyboard selection is active — it isn't. Users will try arrow keys and nothing happens, breaking trust.

**Fix:** Remove `.active` from the HTML. Keep the CSS — it will be wired to real keyboard navigation later.

- [ ] **Step 1: elegant.html — remove `.active` from first result row**

Find:
```html
      <div class="result-row active">
```
Change to:
```html
      <div class="result-row">
```

- [ ] **Step 2: light.html — same**

Find:
```html
      <div class="result-row active">
```
Change to:
```html
      <div class="result-row">
```

- [ ] **Step 3: Add CSS comment marking `.active` as keyboard-driven only**

In both files, find `.result-row.active` and add comment above:
```css
/* Applied via JS on keyboard navigation — not a default state */
.result-row.active { ... }
```

- [ ] **Step 4: Commit**
```bash
git commit -m "fix(prototype): remove false active state from results — keyboard nav not yet wired"
```

---

### Task 3 — Hide keyboard hints on mobile, clarify they are non-functional (both files)

**Problem:** `↑ ↓ Navigate · ↵ Open · Esc Clear` shows on mobile touch devices where none of these keys exist. Also these hints imply functioning keyboard navigation.

**Fix:**
1. Add CSS to hide `.search-footer` and the results-bottom hints on `max-width: 640px`
2. Add `aria-label` clarifying these are keyboard shortcuts for desktop

- [ ] **Step 1: Add mobile hide CSS to both files**

In the CSS of both files, add after the existing `.footer-sep` rule:
```css
@media (max-width: 640px) {
  .search-footer { display: none; }
  .results-footer-hints { display: none; }
}
```

- [ ] **Step 2: Wrap results bottom hints in a classed div (both files)**

In both files, find the results footer div (the one with `↑↓ Navigate` at the bottom of results):
```html
      <div style="display:flex; align-items:center; gap:4px; padding: 4px 2px;">
```
Replace with:
```html
      <div class="results-footer-hints" style="display:flex; align-items:center; gap:4px; padding: 4px 2px;">
```

- [ ] **Step 3: Commit**
```bash
git commit -m "fix(prototype): hide keyboard hints on mobile — not applicable on touch"
```

---

## Chunk 3: Result Row Visual Treatment

### Task 4 — Add visual separation to result rows (both files)

**Problem:** Results float on the raw backdrop with no container. Dark mode has the orb backdrop to create context; light mode has nothing. Result rows need minimal visual grounding without becoming heavy cards (smart pointer cards are the "priority" container — result rows are list items).

**Design decision:** Subtle bottom border between rows + hover state. NOT full card treatment. Optionally a very faint container wrapping the entire results section.

**CSS to add (both files, colour-appropriate):**

**elegant.html** — add to result row CSS:
```css
.result-row {
  ...existing...
  border-bottom: 1px solid var(--border-subtle);
}
.result-row:last-of-type {
  border-bottom: none;
}
```

And wrap the results list in a subtle container — add a `.results-container` class to the `results-wrap` content area (not the outer `results-wrap` div):

```css
/* elegant.html */
.results-container {
  background: var(--surface-primary);
  border-top:    1px solid rgba(255,255,255,0.09);
  border-right:  1px solid rgba(255,255,255,0.05);
  border-bottom: 1px solid rgba(255,255,255,0.03);
  border-left:   1px solid rgba(255,255,255,0.05);
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
}
```

```css
/* light.html */
.results-container {
  background: var(--surface-primary);
  border-top:    1px solid rgba(0,0,0,0.10);
  border-right:  1px solid rgba(0,0,0,0.06);
  border-bottom: 1px solid rgba(0,0,0,0.04);
  border-left:   1px solid rgba(0,0,0,0.06);
  border-radius: 4px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.07);
  overflow: hidden;
  margin-bottom: 8px;
}
```

Group labels sit inside the container but are NOT result rows — they stay as section headers.

- [ ] **Step 1: elegant.html — add `.results-container` CSS above `.result-row`**

- [ ] **Step 2: elegant.html — wrap result groups in `.results-container` divs in HTML**

Find the results-wrap HTML. Wrap the Faults group (label + 2 rows) in one container, Inventory group in another, Documents group in another:
```html
<div class="results-container">
  <div class="result-group-label">Faults</div>
  <div class="result-row">...</div>
  <div class="result-row">...</div>
</div>
<div class="results-container">
  <div class="result-group-label">Inventory</div>
  ...
</div>
<div class="results-container">
  <div class="result-group-label">Documents</div>
  ...
</div>
```

- [ ] **Step 3: light.html — add `.results-container` CSS (light version)**

- [ ] **Step 4: light.html — same HTML grouping**

- [ ] **Step 5: Commit**
```bash
git commit -m "feat(prototype): add grouped result containers with correct per-mode border treatment"
```

---

## Chunk 4: Light Mode Depth

### Task 5 — Add ambient depth to light mode (light.html only)

**Problem:** Dark mode has three blurred radial gradient orbs providing depth and giving the glass search panel something to refract against. Light mode has a flat `#F2F0EC` background — dead and equal.

**Fix:** Radial gradient background (no separate orb divs needed in light mode — the gradient IS the depth) plus a very faint warm glow behind the search area.

- [ ] **Step 1: Change `body` background in light.html from flat colour to gradient**

Find:
```css
body {
  ...
  background: var(--bg);
```
Change to:
```css
body {
  ...
  background: var(--bg);  /* fallback */
  background: radial-gradient(ellipse at 50% 30%, #F8F6F2 0%, #F2F0EC 40%, #E8E3DA 100%);
```

- [ ] **Step 2: Add a single warm ambient orb behind the search panel**

After the `<header>` tag in light.html, add:
```html
<div class="light-ambient" aria-hidden="true"></div>
```

Add CSS:
```css
.light-ambient {
  position: fixed; inset: 0; z-index: 0;
  pointer-events: none;
  background: radial-gradient(ellipse at 50% 28%, rgba(43,123,163,0.06) 0%, transparent 60%);
}
```

This puts a barely-there teal glow centred on the search panel position — same principle as dark mode orbs but at 6% opacity instead of 50%. Warms the glass panel from below.

- [ ] **Step 3: Ensure `.stage` and `.app`-equivalent wrapper is `z-index: 1` relative to the ambient layer**

Confirm the stage div has `position: relative; z-index: 1` so content sits above the ambient layer.

- [ ] **Step 4: Commit**
```bash
git commit -m "feat(prototype): add ambient depth gradient to light mode — parity with dark orb system"
```

---

## Chunk 5: Query Interpretation Panel

### Task 6 — Build the "Understood:" panel (both files)

**Problem:** The results state shows no indication of what the NLP pipeline interpreted. Users who mistype or use unfamiliar phrasing have no visibility into what the system heard.

**Design spec:**

```
┌──────────────────────────────────────────────────────────────┐
│  ↳  Understood  oil · fault domain · engine room · cross-domain
└──────────────────────────────────────────────────────────────┘
```

- Positioned: below the search panel divider, above the first results-container
- Left accent: 2px teal border (same teal as search divider — continuity)
- Label `Understood`: italic, `var(--txt-tertiary)`, `font-size: 10px`
- Entity terms: `font-family: var(--font-mono); font-size: 10px; color: var(--mark-colour)` (teal)
- Separators `·`: `var(--txt-ghost)`
- Meta tags like `cross-domain`: italic, `var(--txt-tertiary)`
- No background fill — inherits backdrop. Left border is the only container signal.
- `opacity: 0.90` on the whole block — it's supporting info, not primary

**CSS (both files, colour tokens handle the difference):**

```css
.query-understood {
  width: 100%; max-width: 600px; padding: 0 20px;
  margin-top: 6px; margin-bottom: 2px;
}
.query-understood-inner {
  display: flex; align-items: baseline; flex-wrap: wrap; gap: 3px;
  padding: 5px 10px;
  border-left: 2px solid var(--teal);
  opacity: 0.88;
}
.understood-label {
  font-size: 10px; font-style: italic;
  color: var(--txt-tertiary);
  margin-right: 5px; flex-shrink: 0;
}
.understood-term {
  font-size: 10px; font-family: var(--font-mono); font-weight: 500;
  color: var(--mark-colour);  /* mode-specific teal — defined in Task 7 */
}
.understood-sep {
  font-size: 10px; color: var(--txt-ghost); user-select: none;
}
.understood-meta {
  font-size: 10px; font-family: var(--font-mono);
  font-style: italic; color: var(--txt-tertiary);
}
```

**HTML (insert after `.search-wrap`, before `.results-wrap` in results state of both files):**

```html
<!-- Query interpretation — what the NLP understood -->
<div class="query-understood">
  <div class="query-understood-inner">
    <span class="understood-label">Understood</span>
    <span class="understood-term">oil</span>
    <span class="understood-sep">·</span>
    <span class="understood-term">fault domain</span>
    <span class="understood-sep">·</span>
    <span class="understood-term">engine room</span>
    <span class="understood-sep">·</span>
    <span class="understood-term">inventory</span>
    <span class="understood-sep">·</span>
    <span class="understood-meta">cross-domain</span>
  </div>
</div>
```

- [ ] **Step 1: Add CSS to elegant.html**
- [ ] **Step 2: Add HTML to elegant.html results state (after search-wrap, before results-wrap)**
- [ ] **Step 3: Add CSS to light.html**
- [ ] **Step 4: Add HTML to light.html results state**
- [ ] **Step 5: Commit**
```bash
git commit -m "feat(prototype): add query interpretation panel — NLP transparency below search"
```

---

## Chunk 6: Brand Colour Fixes

### Task 7 — Fix query highlight colour per mode (both files)

**Problem:**
- Dark mode `mark` colour: `#3A7C9D` on `#181614` = 3.9:1 ❌ fails AA
- Light mode `mark` colour: `#2B7BA3` on `#F2F0EC` = 4.15:1 ❌ fails AA

**Fix:** Introduce `--mark-colour` token, set per-mode to a value that passes 4.5:1.

Calculated values:
- Dark: `#5AABCC` — lighter teal, same brand family, 6.5:1 on dark card surfaces ✅
- Light: `#1A6B96` — deeper teal-blue (from brain logo palette), 5.15:1 on light beige ✅

Both remain unmistakably in the Celeste teal family. The brain logo gradient spans `#A8D8EA` (light) → `#1D78A0` (deep). `#1A6B96` sits at the deep end of that brand range.

- [ ] **Step 1: elegant.html — add `--mark-colour` to `:root` block**
```css
--mark-colour: #5AABCC;   /* brand teal, lighter for contrast on dark surfaces */
```

- [ ] **Step 2: elegant.html — change `.result-title mark` colour**
```css
.result-title mark {
  background: none; color: var(--mark-colour); font-weight: 500;
}
```

- [ ] **Step 3: elegant.html — change `.understood-term` to use `var(--mark-colour)`** (already in Task 6 CSS — confirm it's consistent)

- [ ] **Step 4: light.html — add `--mark-colour` to `:root` block**
```css
--mark-colour: #1A6B96;   /* brain-logo deep blue, 5.1:1 on warm beige */
```

- [ ] **Step 5: light.html — change `.result-title mark` colour to `var(--mark-colour)`**

- [ ] **Step 6: Commit**
```bash
git commit -m "fix(prototype): introduce --mark-colour token — accessible teal per mode, brand-consistent"
```

---

### Task 8 — Fix nav bar brand colour: gold → teal (both files)

**Problem:** `CELESTE` wordmark and `SY Andromeda` vessel name use gold (`#B8935A` dark / `#A07840` light). User has confirmed: use brand teal `#3A7C9D` instead. Gold is retiring from nav identity role.

**Contrast check:**
- `#3A7C9D` on dark topbar `rgba(12,11,10,0.70)` ≈ `#0C0B0A` → 3.9:1 — passes for large text (≥14pt bold). Wordmark is 10px uppercase bold with wide tracking. Borderline but acceptable; could use `#4A9EC0` (lighter) for safe AA.
- `#3A7C9D` on light topbar `rgba(242,240,236,0.88)` ≈ `#F2F0EC` → 4.15:1. Use `#1A6B96` (same as mark-colour) to pass 4.5:1 ✅

- [ ] **Step 1: elegant.html — update topbar brand + vessel colours**

Find:
```css
.topbar-brand { ... color: var(--gold); }
```
Change to:
```css
.topbar-brand { ... color: #4A9EC0; }
```

Find:
```css
.topbar-vessel em { font-style: normal; color: rgba(184,147,90,0.70); }
```
Change to:
```css
.topbar-vessel em { font-style: normal; color: rgba(74,158,192,0.80); }
```

- [ ] **Step 2: light.html — update topbar brand + vessel colours**

Find:
```css
.topbar-brand { ... color: var(--gold); }
```
Change to:
```css
.topbar-brand { ... color: var(--mark-colour); }
```

Find:
```css
.topbar-vessel em { font-style: normal; color: rgba(160,120,64,0.80); }
```
Change to:
```css
.topbar-vessel em { font-style: normal; color: rgba(26,107,150,0.85); }
```

- [ ] **Step 3: Commit**
```bash
git commit -m "fix(prototype): nav CELESTE + vessel name — gold retired, brand teal applied"
```

---

## Chunk 7: Final verification

### Task 9 — Visual QA pass (both files)

Open `localhost:3005/elegant.html` and `localhost:3005/light.html`. Work through each checklist item:

**Dark mode:**
- [ ] Category headers (Faults, Inventory, Documents) — visibly legible, not ghost
- [ ] Icons — readable at tertiary contrast
- [ ] Sub-info rows — clearly legible at secondary contrast
- [ ] First result — no permanent active highlight
- [ ] Keyboard hints — hidden on viewport < 640px
- [ ] Results grouped in subtle containers per domain
- [ ] "Understood" panel visible below search, before results
- [ ] Mark colour `#5AABCC` — brand teal family, readable
- [ ] CELESTE + SY Andromeda — teal, not gold
- [ ] "5 results for oil" — tertiary contrast, readable

**Light mode:**
- [ ] All of the above — adapted for light surfaces
- [ ] Background has subtle gradient depth (lighter center, darker edges)
- [ ] Ambient teal glow faint behind search panel
- [ ] Mark colour `#1A6B96` — deep blue, passes 4.5:1 on beige
- [ ] Result containers have box-shadow — float off the background
- [ ] CELESTE + SY Andromeda — `#1A6B96`, clearly legible

- [ ] **Final commit**
```bash
git add apps/web/public/elegant.html apps/web/public/light.html
git commit -m "feat(prototype): search results UX polish — contrast, depth, query transparency, honest affordances"
```

---

## What this plan does NOT change

| Item | Reason |
|---|---|
| Smart pointer cards | Already correct — card treatment intentional |
| Keyboard navigation JS | Not wired in prototype — deferred |
| Signal colours (red/amber/green/teal) on pointer cards | Already passing non-text contrast 3:1+ |
| Lens pills | No contrast failures |
| Search panel glass treatment | Correct per design direction |
| Anything outside the two prototype HTML files | Out of scope |
