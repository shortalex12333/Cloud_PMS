---
name: celeste-design-philosophy
description: >
  Invoke before ANY frontend design, component creation, or UI decision in the Celeste PMS project.
  Loads the canonical design philosophy: why teal (not any blue), why glass on headers (not rows),
  why monospace for machine data (not natural language), why 44px rows, why dark is primary.
  Prevents drift, inconsistency, and decisions made on aesthetics rather than mission.
trigger: >
  Any of: designing a new component, reviewing existing UI, adding a new colour/token/style,
  choosing an icon, writing placeholder text, deciding on row height, choosing hover behaviour,
  designing a status indicator, adding a new font weight.
---

# Celeste Design Philosophy Skill

## Your first action

Read the full canonical spec:
`docs/superpowers/specs/2026-03-16-frontend-design-philosophy.md`

Do this before proposing any design decisions. The spec is the source of truth.

## What this skill does

Loads the reasoning layer behind every visual decision in Celeste. The design token values live in `src/styles/tokens.css`. This skill carries the *why* behind those values and the rules for applying them.

## Quick decision tree

Before touching any UI element, answer:

**Colour:**
- Is this interactive/navigable? → `--mark` (teal)
- Is this a status (good/warning/critical)? → green / amber / red
- Is this supporting information? → `--txt2`, `--txt3`, `--txt-ghost` hierarchy
- Never mix affordance colours with status colours

**Typography:**
- Did a human write this in natural language? → Inter
- Did the system generate/format this? → Mono (timestamp, ID, path, version, email)
- What level in the hierarchy? → 600 header / 500 primary row / 400 secondary
- See spec §20 for the complete content→font mapping table

**Interactivity:**
- Will clicking do something? → Add hover state (`--surface-hover`)
- Is this read-only? → `.no-hover`, `cursor: default`
- Is this locked by admin? → `LOCKED` badge

**Elevation:**
- Is this floating above content (header, modal)? → Asymmetric border + shadow + glass
- Is this content (row, field)? → No shadow, no glass
- Shadow intensity = importance level (modal > panel > popover > none)

**Row sizing:**
- Operational content row → 44px min-height, `8px 12px` padding, 14px primary text
- Secondary nav (modal sidebar) → 32px, tighter padding
- Never smaller for touch-critical surfaces

**Icons:**
- Nav (sidebar) → 14px stroke
- Row entity type → 16px stroke
- Inline → 13px stroke
- Use entity type semantics from spec §8 — never choose by aesthetics

**Section headers (in list views):**
- Temporal or type anchor → 10px / 600 / uppercase / `--txt-ghost` / no hover / no background
- Not a row. Not a button. A label.

**Section headings (in entity views):**
- Wayfinding landmark → 14px / 600 / uppercase / 0.06em tracking / `--txt3`
- Collapsible (chevron rotates). Icon + title + optional count + optional action.
- Ruled line above: `border-top: 1px solid var(--border-sub)` + `margin-top: 32px` + `padding-top: 24px`
- NOT cards. NOT modules. NOT timelines. Ruled lines preserve the document metaphor.

**Glass effect:**
- Header/nav layer that persists above scrolling content → glass
- Content, data, form inputs → no glass. Ever.

**Entity view layout (lens pages):**
- Entity views are DOCUMENTS, not dashboards. They scroll. No tabs. No card grids.
- Identity strip: overline (system ID, mono, small) ← → primary action (top-right)
- Title: standalone, 22px/600, full width below overline row
- Context line: location + assignee. Status pills below that. Detail lines below that.
- Sections flow: Official Documents → Checklist → Notes → History → Attachments → Parts
- Section order mirrors professional workflow: read brief → work checklist → log notes → review context
- See spec §16-22 for full entity view philosophy.

**Action patterns:**
- ONE primary CTA per view. Split button: main action + dropdown toggle.
- Secondary actions in dropdown (Edit, Add Note, Log Hours, Reassign). Archive last, red, after separator.
- Section actions ("+ Add", "Upload") sit in section headers, teal text, no border.
- Inline actions ("Undo", "Show more") are teal text, no button chrome.
- NO floating action bar. The primary action is visible on first load in the identity strip.
- See spec §19 for the complete button taxonomy.

**Content within sections:**
- Checklist = evidence trail. Completed items show WHO + WHEN. Undo button for safety. Mark Complete disabled until all items done.
- Notes truncate at 3 lines with "Show more". Prevents one verbose note from dominating the view.
- History = prior service periods (year, summary), NOT current session audit log.
- Parts show stock level, NOT price. Crew needs availability, not accounting.
- Documents: equal authority. No special treatment for SOPs. "Open SOP" in teal as action affordance.

## The six-question test (run before shipping)

1. Does every element earn its place?
2. Is this honest? (read-only labelled, interactive has affordance)
3. Does typography communicate semantic meaning?
4. Is dark mode primary?
5. Does hover fulfil a promise?
6. Could a crew member find what they need in under 3 seconds?

## Cross-reference

Full spec: `docs/superpowers/specs/2026-03-16-frontend-design-philosophy.md`
- §0-15: Surface patterns (colour, type, borders, glass, spacing, icons, sections, dark/light)
- §16: Entity view layout (the document metaphor)
- §17: Identity strip anatomy and reasoning
- §18: Section system for entity views (ruled lines, headings, collapse)
- §19: Action patterns and button taxonomy
- §20: Font discipline — complete content-to-font mapping table
- §21: Document row pattern (equal authority)
- §22: Content patterns (checklist, notes, history, parts)

Token values: `apps/web/src/styles/tokens.css`
Spotlight CSS: `apps/web/src/styles/spotlight.css`
Work Order prototype: `apps/web/public/lens-work-order-v6.html` (canonical reference for entity view layout)
Settings prototype: `.superpowers/brainstorm/6432-1773680335/settings-v4.html`
Ledger prototype: `.superpowers/brainstorm/6432-1773680335/ledger-v2.html` (once written)
