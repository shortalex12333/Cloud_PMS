# UI LOCKS — DEVIATION = REGRESSION

> **This file defines UI invariants. Any deviation is a regression.**
>
> Last Updated: 2026-02-17
> Updated By: Claude Opus 4.5

---

## Search Bar (ChatGPT Parity)

| Element | Status | Evidence |
|---------|--------|----------|
| Border | **REMOVED** | No `border` class in SpotlightSearch.tsx |
| Shadow | **TOKENIZED** | `--celeste-spotlight-shadow` in globals.css |
| Mic icon | **REMOVED** | Not in JSX, import removed |
| Search icon | **REMOVED** | Not in JSX, import removed |
| Category buttons | **REMOVED** | Secondary search surface JSX deleted |
| "+" button | **KEPT** | Opens Log Receiving modal, `data-testid="spotlight-add-button"` |
| Utility row | **KEPT** | Email, Menu, Settings (below search bar) |

### Deviation Detection

If any of these reappear, it is a **REGRESSION**:
- `border` class on main panel
- `Mic` or `Search` imports from lucide-react
- Category buttons array (`['Faults', 'Work Orders', ...]`)
- `--celeste-spotlight-border` token usage

---

## CSS Token Locations (Search Bar)

| Token | Light Mode | Dark Mode |
|-------|------------|-----------|
| `--celeste-spotlight-shadow` | globals.css:210 | globals.css:317 |
| Component usage | SpotlightSearch.tsx:786 | `shadow-[var(--celeste-spotlight-shadow)]` |

### Shadow Values (Tokenized)

**Light Mode:**
```css
--celeste-spotlight-shadow: 0 2px 20px rgba(0, 0, 0, 0.12), 0 8px 32px rgba(0, 0, 0, 0.08);
```

**Dark Mode:**
```css
--celeste-spotlight-shadow: 0 2px 20px rgba(0, 0, 0, 0.4), 0 8px 32px rgba(0, 0, 0, 0.3);
```

---

## Invariants (ENFORCED)

1. **No border ever** — Shadow only (ChatGPT parity)
2. **No Mic/Search icons** — Hard removed, not hidden
3. **No category buttons** — DOM deleted, not display:none
4. **Shadow must be tokenized** — Use `var(--celeste-spotlight-shadow)`
5. **"+" button retained** — Opens Log Receiving modal

---

## Verification Commands

```bash
# Check for border regression
grep -n "border" apps/web/src/components/spotlight/SpotlightSearch.tsx

# Check for icon regression
grep -n "Mic\|Search" apps/web/src/components/spotlight/SpotlightSearch.tsx

# Check for category buttons regression
grep -n "Faults\|Work Orders\|Equipment\|Documents" apps/web/src/components/spotlight/SpotlightSearch.tsx

# Check shadow is tokenized
grep -n "celeste-spotlight-shadow" apps/web/src/styles/globals.css
```

---

## NOT Verified (Pending)

- [ ] Light mode rendering (only dark mode screenshotted)
- [ ] Mobile responsiveness
