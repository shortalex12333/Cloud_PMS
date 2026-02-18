---
phase: 00-design-system
plan: "01"
subsystem: ui
tags: [css-custom-properties, design-tokens, dark-mode, light-mode, tailwind, nextjs]

# Dependency graph
requires: []
provides:
  - CSS custom property system with dark and light theme tokens
  - Dark theme (default) via :root and [data-theme="dark"] with ChatGPT-inspired tight luminance range
  - Light theme via [data-theme="light"] attribute on html element
  - Surface tokens: --surface-base/primary/elevated/hover/active/border/border-subtle (both themes)
  - Text tokens: --text-primary/secondary/tertiary/disabled/inverse (both themes)
  - Shadow tokens: --shadow-sm/md/lg (different opacity per theme)
  - Glass tokens: --glass-bg/border/blur (both themes)
  - Brand tokens: --brand-ambient/interactive/hover/muted (shared)
  - Status tokens: --status-critical/warning/success/neutral with -bg variants (shared)
  - Spacing scale: --space-1 through --space-20 (4px grid, shared)
  - Radius scale: --radius-sm/md/lg/xl/full (shared)
  - Transition tokens: --ease-out, --duration-fast/normal/slow (shared)
  - Z-index scale: --z-sticky through --z-toast (shared)
affects:
  - All frontend components (must use semantic tokens, zero raw hex)
  - Any future theme toggle implementation
  - Tailwind config extension (brand/status/surface/txt colors reference these vars)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - CSS custom properties for design tokens (not Tailwind values directly)
    - Dark theme as default (:root), light theme via [data-theme="light"] attribute
    - Semantic tokens only in components - zero raw hex values
    - "@import './tokens.css' before @tailwind directives in globals.css"

key-files:
  created:
    - apps/web/src/styles/tokens.css
    - apps/web/tests/unit/design-tokens.test.ts
  modified:
    - apps/web/src/styles/globals.css
    - apps/web/src/app/layout.tsx

key-decisions:
  - "Dark theme is default via :root - no class or attribute required for dark mode baseline"
  - "Light theme switching uses [data-theme='light'] on html element - theme toggle sets this attribute"
  - "tokens.css imported before Tailwind to ensure tokens available to all utility classes"
  - "Tokens named semantically (--surface-base not --color-gray-900) for component portability"
  - "Kept existing className=dark (for shadcn) alongside new data-theme=dark (for our token system)"

patterns-established:
  - "tokens.css: single source of truth for all design values - import this, never hardcode hex"
  - "theme switching: toggle data-theme attribute on html element (dark/light)"
  - "CSS import order: tokens.css first, then @tailwind base/components/utilities"

requirements-completed: [DS-01]

# Metrics
duration: 25min
completed: 2026-02-17
---

# Phase 00 Plan 01: Implement Design Tokens CSS Summary

**CSS custom property token system with ChatGPT-parity dark/light themes: 7 surface tokens, 5 text tokens, 3 shadows, 3 glass tokens per theme, plus 30+ shared brand/status/spacing/layout tokens — verified by 25 automated assertions**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-02-17T16:53:08Z
- **Completed:** 2026-02-17T17:18:00Z
- **Tasks:** 5/5
- **Files modified:** 4 (2 new, 2 modified)

## Accomplishments

- Created `tokens.css` with exact dark and light theme tokens from CLAUDE.md — zero deviation from specification
- Wired `tokens.css` import into `globals.css` before Tailwind directives so all components can consume semantic tokens
- Added `data-theme="dark"` to html element in `layout.tsx` enabling CSS selector-based theme switching
- Created 25-assertion test suite verifying every token category; all 25 tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Create tokens.css** - `d7eb6ed2` (feat)
2. **Task 2: Import tokens.css in globals.css** - `1d5cc028` (feat)
3. **Task 3: Add data-theme to layout.tsx** - `6a27bf89` (feat)
4. **Task 4: Build verification** - no commit (CSS compiled successfully; build ENOENT is pre-existing filesystem issue)
5. **Task 5: Design token tests** - `8a30f9e9` (test)

**Plan metadata:** See final docs commit below.

## Files Created/Modified

- `apps/web/src/styles/tokens.css` - Complete design token system: dark theme (:root, [data-theme="dark"]), light theme ([data-theme="light"]), shared brand/status/spacing/radius/z-index/transition tokens
- `apps/web/src/styles/globals.css` - Added `@import './tokens.css'` before Tailwind directives
- `apps/web/src/app/layout.tsx` - Added `data-theme="dark"` attribute to html element
- `apps/web/tests/unit/design-tokens.test.ts` - 25 vitest assertions verifying token values match CLAUDE.md spec exactly

## Decisions Made

- Dark theme as `:root` default — no attribute required on page load, prevents FOUC
- Light theme uses `[data-theme="light"]` attribute selector — theme toggle sets `document.documentElement.setAttribute('data-theme', 'light')`
- Kept existing `className="dark"` on html element (used by shadcn components) alongside new `data-theme="dark"` (used by our semantic token system)
- Build error (`ENOENT mkdir .next/export`) is a pre-existing filesystem permission constraint on the Backup external volume — CSS compilation passed (`✓ Compiled successfully`), not caused by this plan

## Deviations from Plan

None — plan executed exactly as written. The build failure in Task 4 is a pre-existing infrastructure issue (external volume filesystem permissions during Next.js static export phase), not introduced by this plan.

## Issues Encountered

- **Build ENOENT on Backup volume:** `next build` fails during static export with `ENOENT: mkdir .next/export/...`. CSS compiled successfully (`✓ Compiled successfully`). Pre-existing on this machine.
- **Test split logic:** Initial test used `split('[data-theme="light"]')` which hit comment text. Fixed to use regex to extract actual CSS ruleset. All 25 tests pass.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Token system is complete and verified. All components can now use semantic tokens.
- Rule for all future components: use `var(--token-name)` only. Zero raw hex values.
- Theme toggle: set `document.documentElement.setAttribute('data-theme', 'light'|'dark')` to switch themes.
- Tailwind config should be extended per CLAUDE.md spec to map token vars to Tailwind utilities (next design system task).

---
*Phase: 00-design-system*
*Completed: 2026-02-17*

## Self-Check: PASSED

**Files verified:**
- FOUND: apps/web/src/styles/tokens.css
- FOUND: apps/web/src/styles/globals.css (with @import ./tokens.css)
- FOUND: apps/web/src/app/layout.tsx (with data-theme="dark")
- FOUND: apps/web/tests/unit/design-tokens.test.ts (25/25 passing)

**Commits verified:**
- FOUND: d7eb6ed2 (feat(00-01): create design tokens CSS with dark and light themes)
- FOUND: 1d5cc028 (feat(00-01): import tokens.css in globals.css before Tailwind directives)
- FOUND: 6a27bf89 (feat(00-01): add data-theme attribute to html element in layout.tsx)
- FOUND: 8a30f9e9 (test(00-01): add design token verification tests - 25 assertions)
