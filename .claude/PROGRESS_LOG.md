# ⚠ DEPRECATED — do not rely on this file

**Deprecated:** 2026-04-15

This file previously recorded a "1-URL Single Surface Architecture" remediation
dated 2026-02-17, which prescribed a single-URL product rendered via
`ContextPanel` + `LensRenderer` with all fragmented routes deleted. **That
architecture has since been reversed.** The product now uses normal Next.js App
Router conventions with one route per entity endpoint (e.g. `/documents`,
`/work-orders/[id]`, `/faults/[id]`).

Any claim in this file that:

- "1-URL philosophy" is current
- `ContextPanel` is the rendering strategy
- `LensRenderer` maps entity types to lens content
- Fragmented routes are forbidden

…is **stale and must not be followed**. The ContextPanel, SurfaceContext,
NavigationContext, SituationRouter, and all legacy lens components have been
deleted from the codebase.

## Current canonical architecture reference

Read `docs/frontend/README.md` for the CEO-level summary of the legacy removal
and the current fragmented-URL architecture. It lists exactly which files were
deleted during the re-migration and what replaced them.

## Why this file still exists

Kept as a historical deprecation marker rather than deleted outright, so any
future agent or engineer searching for "1-URL" or "ContextPanel" in the repo
lands here first, sees the deprecation notice, and is redirected to the current
source of truth. Removing the file entirely would leave the stale rule
unchallenged in anyone's local git history or cached documentation.

## Related memory

- `/Users/celeste7/.claude/projects/-Users-celeste7/memory/feedback_url_philosophy.md`
  — standing rule that the 1-URL philosophy is dead and any mention of it
  should be deleted on sight.
