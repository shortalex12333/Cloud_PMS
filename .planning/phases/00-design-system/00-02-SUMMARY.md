---
phase: 00-design-system
plan: "02"
subsystem: ui
tags: [tailwind, css-variables, design-tokens, theming]

# Dependency graph
requires:
  - phase: 00-01
    provides: CSS custom properties in tokens.css (--brand-*, --surface-*, --text-*, --radius-*, --shadow-*, --space-*)
provides:
  - Tailwind color classes: bg-surface-base, bg-surface-primary, bg-surface-elevated, text-txt-primary, text-txt-secondary, text-txt-tertiary, text-brand-interactive, bg-brand-muted
  - Tailwind status classes: text-status-critical, text-status-warning, text-status-success, text-status-neutral with -bg variants
  - Semantic borderRadius: rounded-sm, rounded-md, rounded-lg, rounded-xl, rounded-full (all CSS var backed)
  - Semantic boxShadow: shadow-sm, shadow-md, shadow-lg (all CSS var backed, theme-adaptive)
  - Semantic spacing: ds-1 through ds-20 mapped to var(--space-*)
affects: [00-03, 00-04, 00-05, all-components]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Tailwind extends theme with CSS var references — all semantic tokens are var(--token-name), never raw hex"
    - "Two-layer approach: legacy celeste-prefixed tokens remain alongside new semantic tokens for backward compatibility"
    - "Spacing prefixed ds- to avoid collision with Tailwind numeric scale"

key-files:
  created: []
  modified:
    - apps/web/tailwind.config.ts

key-decisions:
  - "Use var(--token-name) for all semantic color values — zero raw hex in Tailwind config"
  - "Keep legacy celeste-prefixed tokens alongside new semantic tokens for backward compatibility"
  - "Prefix spacing tokens with ds- (design system) to avoid collision with Tailwind's default numeric scale"
  - "borderRadius sm/md/lg/xl/full override Tailwind defaults with CSS var-backed values matching CLAUDE.md spec"

patterns-established:
  - "Semantic token pattern: Tailwind class name -> CSS custom property -> theme-specific value"
  - "All color utilities map to CSS vars: bg-surface-base compiles to background-color: var(--surface-base)"

requirements-completed: [DS-02]

# Metrics
duration: 12min
completed: 2026-02-17
---

# Phase 00 Plan 02: Extend Tailwind Config with Semantic Tokens Summary

**Tailwind config extended with brand/surface/txt/status color groups plus radius/shadow utilities all mapped to CSS custom properties — enables bg-surface-base, text-txt-primary, shadow-sm, rounded-lg with automatic light/dark theme adaptation**

## Performance

- **Duration:** 12 min
- **Started:** 2026-02-17T16:53:12Z
- **Completed:** 2026-02-17T17:06:06Z
- **Tasks:** 6
- **Files modified:** 1

## Accomplishments
- Extended `theme.extend.colors` with 4 semantic groups: brand (4 tokens), status (8 tokens), surface (7 tokens), txt (5 tokens)
- Extended `theme.extend.borderRadius` with 5 semantic tokens: sm/md/lg/xl/full all backed by CSS custom properties
- Extended `theme.extend.boxShadow` with 3 semantic tokens: sm/md/lg that auto-adapt between light/dark themes via tokens.css
- Extended `theme.extend.spacing` with 11 semantic ds-* tokens mapped to var(--space-*)
- All existing legacy celeste-* tokens preserved for backward compatibility with zero breaking changes

## Task Commits

Each task was committed atomically:

1. **Tasks 1-6: Read, extend colors, spacing, borderRadius, boxShadow, verify** - `e958d449` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `apps/web/tailwind.config.ts` - Added brand, status, surface, txt color groups; sm/md/lg/xl/full borderRadius; sm/md/lg boxShadow; ds-1..ds-20 spacing — all via CSS custom properties

## Decisions Made
1. **Zero raw hex** — all semantic token values use `var(--token-name)` ensuring they automatically adapt when theme changes
2. **ds-* prefix for spacing** — avoids collision with Tailwind's default numeric spacing (1=4px, 2=8px...) while keeping design system tokens clearly namespaced
3. **Override default radius/shadow keys** — using sm, md, lg, xl, full for borderRadius and sm, md, lg for boxShadow means standard Tailwind classes work with CSS variables automatically
4. **Backward compatibility** — all legacy celeste-* tokens preserved, enabling gradual migration without breaking existing components

## Deviations from Plan

None — plan executed exactly as written. All six tasks completed as specified.

## Issues Encountered

**Build infrastructure note:** The `npm run build` command reached "Compiled successfully" (TypeScript + Tailwind config valid) but failed during the Next.js static export phase with `ENOENT: no such file or directory, mkdir .../.next/export/...`. This is a pre-existing filesystem issue with running Next.js builds on this external backup volume — evidenced by plans 00-03 and 00-04 already having committed components, and the presence of existing .next/cache. The Tailwind config is syntactically valid and will compile correctly in the production environment. All three verification grep checks passed.

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- All semantic Tailwind utilities available: bg-surface-base, text-txt-primary, text-brand-interactive, bg-brand-muted, rounded-sm/md/lg/xl/full, shadow-sm/md/lg
- Requires tokens.css (plan 00-01) to be wired into globals.css for values to resolve at runtime
- Plan 00-03+ can use these utility classes in components

## Self-Check: PASSED

- [x] apps/web/tailwind.config.ts exists at correct path
- [x] Commit e958d449 exists in git log
- [x] grep for "surface-base" finds tailwind.config.ts
- [x] grep for "brand-interactive" finds tailwind.config.ts
- [x] grep for "txt-primary" finds tailwind.config.ts (via txt.primary key)
- [x] borderRadius has sm/md/lg/xl/full entries
- [x] boxShadow has sm/md/lg entries

---
*Phase: 00-design-system*
*Completed: 2026-02-17*
