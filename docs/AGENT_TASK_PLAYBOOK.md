# CelesteOS — Agent Task Execution Playbook

**What this is:** Copy-pasteable task briefs for your code agent (Claude Code).
**How to use:** Feed these in order. One task at a time. Review output before moving on.
**Rule:** Never skip a phase. Each phase builds on the last.

---

## BEFORE YOU START — The System Prompt

Paste this at the start of every Claude Code session. It sets the ground rules so you don't have to repeat them per task.

```
You are working on CelesteOS, a maritime PMS (Planned Maintenance System) delivered
through a search-first interface (like Apple Spotlight for yacht management).

BRAND RULES (non-negotiable):
- This is enterprise infrastructure, not startup SaaS
- Dark mode only. Primary background: #0A0A0A
- No gradients, no glow, no glassmorphism, no playful motion
- Mutation must feel visually heavier than read
- No Tailwind defaults (zinc, gray, slate, blue, red, green)
- ALL styling must use celeste-* prefixed tokens only
- Font weights restricted to 400, 500, 600 — no 700/bold
- Border radii restricted to 4px, 8px, 12px — nothing else
- Spacing on 4px grid only

TOKEN SOURCE OF TRUTH: tailwind.config.ts + src/styles/tokens/

When I give you a file to migrate, you must:
1. Replace every non-celeste Tailwind class with its celeste equivalent
2. Replace every hex color with a celeste token class
3. Replace every inline style with token-based Tailwind classes
4. Preserve all functionality — only change styling
5. Report what you changed and how many replacements
```

---

## PHASE 1: FOUNDATION LOCK (Days 1–2)

### Task 1.1 — Verify Tailwind Config Completeness

```
TASK: Audit tailwind.config.ts

Open tailwind.config.ts and verify that EVERY value in
src/styles/tokens/colors.ts, typography.ts, spacing.ts,
and shadows.ts has a corresponding Tailwind class.

Check for gaps. If a token exists in the .ts files but has
no Tailwind class, add it.

Report:
- How many tokens are defined in the .ts files
- How many have Tailwind mappings
- What's missing (if anything)

Do NOT change any token values. Only ensure coverage.
```

### Task 1.2 — Disable Default Tailwind Colors

```
TASK: Lock down tailwind.config.ts to prevent off-system values

In tailwind.config.ts, override the default Tailwind color
palette so that ONLY celeste-* colors are available.

This means:
- Remove or override the default zinc, gray, slate, red,
  green, blue, amber, etc. palettes
- Keep ONLY the celeste.* color definitions
- This will cause build errors in files still using defaults
  — that's intentional, it shows us what needs migrating

Method: Set the theme.colors to ONLY contain your celeste
tokens (not extend — replace).

IMPORTANT: Before doing this, make sure the celeste color
tokens include equivalents for every semantic use (error,
success, warning, etc.) so nothing is left without a mapping.

SUCCESS: Running `npm run build` shows errors ONLY in
component files using old defaults. The config itself is valid.
```

**⚠️ DECISION: SKIP TASK 1.2**

We are going gradual. Keep the app running throughout migration.
Lock down Tailwind config as the LAST step in Phase 9 once everything is clean.
Proceed directly to Phase 2 after completing Task 1.1.

---

## PHASE 2: SEARCH SURFACE (Days 3–5)

### Task 2.1 — SpotlightSearch.tsx

```
TASK: Migrate SpotlightSearch.tsx to celeste tokens

FILE: src/components/spotlight/SpotlightSearch.tsx

This file has 6 hardcoded hex values and likely uses default
Tailwind classes. It is the most important surface in the app.

MIGRATION MAP:
  bg-zinc-900     → bg-celeste-black
  bg-zinc-800     → bg-celeste-surface
  bg-zinc-700     → bg-celeste-panel
  text-zinc-100   → text-celeste-text-title
  text-zinc-200   → text-celeste-text-primary
  text-zinc-400   → text-celeste-text-secondary
  text-zinc-500   → text-celeste-text-muted
  text-zinc-600   → text-celeste-text-disabled
  border-zinc-*   → border-celeste-border
  Any #XXXXXX     → nearest celeste token class
  Any red-*       → celeste-warning
  Any green-*     → celeste-success

Also check:
- Border radius values (must be 4px, 8px, or 12px only)
- Spacing values (must be on 4px grid)
- Font sizes (must match typography token scale)
- Font weights (must be 400, 500, or 600 only)
- No inline style={{}} objects

PRESERVE: All functionality, event handlers, state logic,
imports, component structure. Only change styling classes.

REPORT: List every replacement made (old → new) with line numbers.
```

### Task 2.2 — SpotlightResultRow.tsx

```
TASK: Migrate SpotlightResultRow.tsx to celeste tokens

FILE: src/components/spotlight/SpotlightResultRow.tsx

Same migration map as Task 2.1. This is a search result row
inside the Spotlight dropdown.

Additional requirements:
- Hover state must use celeste token (e.g., hover:bg-celeste-surface)
- Selected/active state must use celeste token
- Text hierarchy must follow: title → primary → secondary → muted
- No default Tailwind colors

REPORT: List every replacement made.
```

### Task 2.3 — SpotlightPreviewPane.tsx

```
TASK: Migrate SpotlightPreviewPane.tsx to celeste tokens

FILE: src/components/spotlight/SpotlightPreviewPane.tsx

Same migration map. This is the preview pane that appears
alongside search results.

REPORT: List every replacement made.
```

### Task 2.4 — MicroactionButton.tsx

```
TASK: Migrate MicroactionButton.tsx to celeste tokens

FILE: src/components/spotlight/MicroactionButton.tsx

Same migration map. Additionally:
- This is an ACTION component, so it should follow the
  MUTATE visual weight rules:
  - Bordered, not just text
  - Slightly heavier than pure read elements
  - Use celeste-accent for primary actions
  - Use celeste-warning for destructive actions

REPORT: List every replacement made.
```

---

## PHASE 3: UI PRIMITIVES (Days 6–8)

These are shadcn/radix base components. They set the foundation for everything else.

### Task 3.1 — button.tsx

```
TASK: Migrate button.tsx to celeste tokens

FILE: src/components/ui/button.tsx

This is a shadcn button component. It likely uses default
zinc/slate classes in its variants.

For each button variant, replace:
  default   → bg-celeste-accent text-celeste-white
  outline   → border-celeste-border text-celeste-text-primary bg-transparent
  ghost     → text-celeste-text-secondary hover:bg-celeste-surface
  secondary → bg-celeste-surface text-celeste-text-primary
  destructive → bg-celeste-warning text-celeste-white

Hover states should be ONE STEP lighter/darker in the
celeste scale (e.g., celeste-surface → celeste-panel).

Focus rings should use celeste-accent.
Disabled states should use celeste-text-disabled and reduced opacity.

REPORT: List each variant's old → new styling.
```

### Task 3.2 — dialog.tsx

```
TASK: Migrate dialog.tsx to celeste tokens

FILE: src/components/ui/dialog.tsx

This is the base modal component. All 33 mutation modals
build on this, so getting it right is critical.

Requirements:
- Overlay backdrop: bg-black/85 (85% opacity per spec)
- Dialog surface: bg-celeste-surface
- Dialog border: border-celeste-border
- Shadow: use highest elevation shadow from tokens
- Title: text-celeste-text-title
- Description: text-celeste-text-secondary
- Close button: text-celeste-text-muted hover:text-celeste-text-primary
- Border radius: rounded-lg (12px) only
- No zinc, gray, or default colors

This sets the mutation ritual foundation. The modal must
feel HEAVIER than the read surface behind it.

REPORT: List every replacement made.
```

### Task 3.3 — input.tsx

```
TASK: Migrate input.tsx to celeste tokens

FILE: src/components/ui/input.tsx

Requirements:
- Background: bg-celeste-black or bg-celeste-surface
- Border: border-celeste-border
- Text: text-celeste-text-primary
- Placeholder: placeholder:text-celeste-text-muted
- Focus: focus:border-celeste-accent (no ring glow, just border change)
- Disabled: opacity + text-celeste-text-disabled
- No default colors

REPORT: List every replacement made.
```

### Task 3.4 — Remaining UI Primitives (Batch)

```
TASK: Migrate all remaining src/components/ui/ files to celeste tokens

FILES:
- src/components/ui/alert-dialog.tsx
- src/components/ui/checkbox.tsx
- src/components/ui/dropdown-menu.tsx
- src/components/ui/label.tsx
- src/components/ui/Pagination.tsx
- src/components/ui/select.tsx
- src/components/ui/sonner.tsx
- src/components/ui/SortControls.tsx
- src/components/ui/textarea.tsx
- src/components/ui/tooltip.tsx

Apply the same migration map. For each file:
- Replace all zinc/gray/slate/red/green → celeste equivalents
- Replace all hex colors → celeste token classes
- Ensure border radii are 4px, 8px, or 12px only
- Ensure spacing is on 4px grid
- Ensure font weights are 400/500/600 only

NOTE: tooltip.tsx is flagged as "forbidden per brand" in the
dependency tree. MIGRATE IT anyway, then add this comment at the
top of the file:
// BRAND NOTE: Tooltips are discouraged per brand doctrine. Prefer inline context.
Do NOT delete it — deletion risks breaking import chains.

REPORT: Summary per file — how many replacements, any issues found.
```

---

## PHASE 4: CELESTE PRIMITIVES (Days 8–10)

These ARE your brand. They should already be close but may have drift.

### Task 4.1 — ResultCard.tsx

```
TASK: Audit and enforce ResultCard.tsx against lens invariants

FILE: src/components/celeste/ResultCard.tsx

This is the canonical result card. Verify it follows
these EXACT invariants:

  Card padding:       p-4 (16px)
  Border radius:      rounded-lg (12px)
  Shadow:             shadow-md (elevation-2)
  Title typography:   text-[15px] font-semibold (600)
  Meta typography:    text-[12px] text-celeste-text-secondary
  Action button:      h-8 px-3 text-[13px]
  Status dot:         8px (w-2 h-2)
  Action icon:        14px (h-3.5 w-3.5)

If any value deviates, fix it.
If any non-celeste color class is used, replace it.

This card is the TEMPLATE. Every lens card must follow
this structure.

REPORT: What was correct, what needed fixing.
```

### Task 4.2 — Remaining Celeste Primitives (Batch)

```
TASK: Migrate all src/components/celeste/ files to celeste tokens

FILES:
- src/components/celeste/ActionDropdown.tsx
- src/components/celeste/AuditRecord.tsx
- src/components/celeste/EntityLine.tsx
- src/components/celeste/MutationPreview.tsx
- src/components/celeste/SignaturePrompt.tsx
- src/components/celeste/StatusLine.tsx
- src/components/celeste/UncertaintySelector.tsx

Standard migration map applies. Additional notes:

AuditRecord.tsx — This is an IMMUTABLE record display.
  It should feel permanent. Use slightly different background
  (bg-celeste-panel) to signal "this cannot be changed."

MutationPreview.tsx — This is a PREVIEW before commit.
  It should feel heavier than read. Use elevation-2 shadow
  and a subtle border to separate it from surrounding content.

SignaturePrompt.tsx — This is a COMMITMENT action.
  Highest visual weight. Use elevation-3 shadow.
  Background should be distinct from standard surfaces.

REPORT: Summary per file.
```

---

## PHASE 5: LENS CARDS (Days 10–14)

### Task 5.1 — Critical Cards First

```
TASK: Migrate FaultCard.tsx and WorkOrderCard.tsx to celeste tokens

FILES:
- src/components/cards/FaultCard.tsx (7 zinc violations + severity colors)
- src/components/cards/WorkOrderCard.tsx (7 zinc violations + status colors)

These are the two most-used lens cards.

MIGRATION MAP (same base map plus):
  red-500, red-600   → text-celeste-warning
  bg-red-500/10       → bg-celeste-warning/10
  green-500, green-600 → text-celeste-success
  bg-green-500/10     → bg-celeste-success/10
  yellow-*, amber-*   → text-celeste-caution
  orange-*            → text-celeste-inspect

Card structure must follow ResultCard.tsx invariants:
  Padding: p-4
  Radius: rounded-lg
  Title: text-[15px] font-semibold
  Meta: text-[12px] text-celeste-text-secondary
  Actions: h-8 px-3 text-[13px]

REPORT: Every replacement with line numbers.
```

### Task 5.2 — Remaining Cards (Batch)

```
TASK: Migrate all remaining src/components/cards/ files

FILES:
- ChecklistCard.tsx
- DocumentCard.tsx
- EquipmentCard.tsx
- FleetSummaryCard.tsx
- HandoverCard.tsx
- HandoverItemCard.tsx
- HORTableCard.tsx
- PartCard.tsx
- PurchaseCard.tsx
- ReceivingCard.tsx
- SmartSummaryCard.tsx
- WorklistCard.tsx

Same migration map and card invariants as Task 5.1.
Each card MUST follow the same structural anatomy:
  Header slot → Title slot → Body slot → Metadata slot → Actions slot

If any card has a completely different structure, flag it
but still migrate its colors/spacing.

REPORT: Summary per file. Flag any structural outliers.
```

---

## PHASE 6: MODALS — High-Violation Files (Days 14–18)

### Task 6.1 — Worst Offenders First

```
TASK: Migrate the 8 highest-violation modal files

FILES (in order of violation count):
1. EditFaultDetailsModal.tsx      (18 red-* violations)
2. AddPartModal.tsx               (15 red-* violations)
3. LogPartUsageModal.tsx          (15 red-* + 5 green-*)
4. CreatePurchaseRequestModal.tsx  (13 red-* violations)
5. EditPartQuantityModal.tsx      (12 red-* violations)
6. EditWorkOrderDetailsModal.tsx  (12 red-* violations)
7. CompleteWorkOrderModal.tsx     (11 red-* violations)
8. OrderPartModal.tsx             (11 red-* violations)

MIGRATION MAP for modals:
  red-500       → celeste-warning (error text)
  red-500/10    → celeste-warning/10 (error background)
  red-600       → celeste-warning (error border/darker)
  green-500     → celeste-success (success text)
  green-500/10  → celeste-success/10 (success background)
  text-red-*    → text-celeste-warning
  bg-red-*      → bg-celeste-warning/10
  border-red-*  → border-celeste-warning
  focus:ring-red-* → focus:ring-celeste-warning

CONTEXT for red/green in modals:
- red is used for: validation errors, required field indicators,
  destructive action warnings, error messages
- green is used for: success states, completion indicators,
  valid input feedback

All of these map to celeste-warning and celeste-success
respectively. The visual meaning is preserved, only the
exact color values change.

REPORT: Per-file summary with replacement count.
```

### Task 6.2 — Remaining Modals (Batch)

```
TASK: Migrate all remaining src/components/modals/ files

FILES: All .tsx files in src/components/modals/ not covered
in Task 6.1 (approximately 25 files).

Same migration map. These files have fewer violations each
(typically <10 per file).

Additionally ensure every modal:
- Uses the dialog.tsx base (which was already migrated in Phase 3)
- Has consistent padding (p-6 for modal body)
- Has consistent title styling (text-celeste-text-title font-semibold)
- Has consistent button placement (right-aligned, primary action last)

REPORT: Summary per file. Flag any modal that doesn't use
the dialog.tsx base component.
```

---

## PHASE 7: HIGH-VIOLATION SURFACES (Days 18–22)

### Task 7.1 — Email Components

```
TASK: Migrate email-related components

FILES:
- EmailThreadViewer.tsx       (29 zinc violations)
- RelatedEmailsPanel.tsx      (20 zinc violations)
- EmailInboxView.tsx          (14 zinc violations)
- EmailSurface.tsx            (10 green violations)
- EmailSituationView.tsx      (15 hex violations)
- LinkEmailModal.tsx          (12 zinc violations)

NOTE: email/_legacy/EmailSearchView.tsx has 70 hex violations
but is LEGACY. DO NOT MIGRATE. Instead, add this comment at line 1:
// LEGACY: Not migrated to celeste tokens. Scheduled for removal.
Same treatment for any files in app/_archived/*.

Standard migration map. These are heavy zinc users, so
the bulk of changes will be zinc → celeste-* replacements.

REPORT: Per-file summary.
```

### Task 7.2 — Dashboard & Situation Components

```
TASK: Migrate dashboard and situation components

FILES:
- ModuleContainer.tsx         (18 zinc violations)
- PredictiveRiskModule.tsx    (17 zinc violations)
- SituationCard.tsx           (11 zinc violations)
- SituationPanel.tsx          (9 zinc violations)
- ControlCenter.tsx           (9 zinc violations)
- CrewNotesModule.tsx         (10 zinc violations)
- HandoverStatusModule.tsx    (10 zinc violations)

Standard migration map.

REPORT: Per-file summary.
```

### Task 7.3 — Action System Components

```
TASK: Migrate action system components

FILES:
- ActionModal.tsx             (21 hex violations — HIGH)
- ActionButton.tsx
- ActionPanel.tsx
- ConfirmationDialog.tsx
- CreateWorkOrderFromFault.tsx
- actions/modals/CreateWorkOrderModal.tsx

ActionModal.tsx is the second-worst hex offender after
the legacy email file. It needs special attention.

For action components, enforce the READ vs MUTATE distinction:
- READ actions (viewing, navigating): lighter weight,
  text-only styling, minimal visual presence
- MUTATE actions (creating, editing, deleting): bordered,
  separated from content, higher contrast, heavier shadow

REPORT: Per-file summary. Note which actions are READ vs MUTATE.
```

---

## PHASE 8: CLEANUP & AUDIT (Days 22–25)

### Task 8.1 — ThreadLinksPanel.tsx

```
TASK: Migrate ThreadLinksPanel.tsx

FILE: ThreadLinksPanel.tsx (29 hex violations)

This is a standalone high-violation file. Standard migration.

REPORT: Replacement count.
```

### Task 8.2 — Pages

```
TASK: Migrate all page-level files

FILES: All files in src/app/ that contain UI styling
(likely 8 files per dependency tree).

Standard migration map. Pages should be mostly layout
containers — if they have heavy styling, flag that as
a potential architectural concern (styling should be in
components, not pages).

REPORT: Per-file summary.
```

### Task 8.3 — Full Codebase Audit

```
TASK: Final audit — find ALL remaining non-celeste values

Run these searches across the entire src/ directory:

1. Any remaining Tailwind default color classes:
   zinc, gray, slate, red, green, blue, amber, orange, yellow

2. Any remaining hex colors in .tsx files:
   #[0-9a-fA-F]{3,8}

3. Any remaining inline style objects:
   style={{

4. Any border-radius values that aren't 4px, 8px, or 12px

5. Any font-weight values that aren't 400, 500, or 600

REPORT:
- Total remaining violations (target: 0)
- List every violation with file path and line number
- For each, suggest the correct celeste token replacement
```

---

## PHASE 9: GOVERNANCE LOCK (Days 25–28)

### Task 9.1 — ESLint Rule (Optional but Recommended)

```
TASK: Add ESLint rule to prevent non-celeste color classes

Create or update .eslintrc to warn on any Tailwind class
that uses a default color palette (zinc, gray, slate, red,
green, blue, etc.) instead of celeste-* prefixed classes.

If a formal ESLint plugin for this doesn't exist, create a
simple custom rule or use eslint-plugin-tailwindcss with a
whitelist configuration.

The goal: any future code that uses bg-zinc-800 instead of
bg-celeste-surface should trigger a lint warning.

REPORT: Rule configuration and test output.
```

### Task 9.2 — Migration Verification Report

```
TASK: Generate a final migration report

Produce a markdown document that lists:

1. TOKENS DEFINED
   - Every celeste-* color with hex value and contrast ratio
   - Every spacing value
   - Every shadow level
   - Every border radius value
   - Every font size and weight

2. COMPONENTS MIGRATED
   - Every .tsx file that was changed
   - Number of replacements per file
   - Any exceptions or known issues

3. REMAINING VIOLATIONS
   - Any files that still have hardcoded values (with reason)
   - Legacy files excluded from migration
   - Files flagged for removal

4. CONTRAST RATIOS
   - Every text/background combination in use
   - Pass/fail status per WCAG AA
   - Any borderline cases

Save this to docs/MIGRATION_REPORT.md
```

---

## QUICK REFERENCE — The Migration Map

Keep this open while running tasks. It's the single source of truth for replacements.

```
BACKGROUNDS
  bg-zinc-900, bg-zinc-950, bg-black  → bg-celeste-black
  bg-zinc-800                          → bg-celeste-surface
  bg-zinc-700                          → bg-celeste-panel

TEXT
  text-zinc-100, text-white            → text-celeste-text-title
  text-zinc-200                        → text-celeste-text-primary
  text-zinc-400                        → text-celeste-text-secondary
  text-zinc-500                        → text-celeste-text-muted
  text-zinc-600                        → text-celeste-text-disabled

BORDERS
  border-zinc-700, border-zinc-800     → border-celeste-border
  border-zinc-600, border-zinc-500     → border-celeste-border-subtle

STATES — RESTRICTED COLORS (map directly, no aliases)
  red-*, rose-*      (error/destructive) → restricted-red
  green-*, emerald-* (success/valid)     → restricted-green
  yellow-*, amber-*  (caution/warning)   → restricted-yellow
  orange-*           (inspect/review)    → restricted-orange

OPACITY PATTERNS
  bg-red-500/10     → bg-restricted-red/10
  bg-green-500/10   → bg-restricted-green/10
  bg-yellow-500/10  → bg-restricted-yellow/10
  bg-orange-500/10  → bg-restricted-orange/10
  text-red-*        → text-restricted-red
  text-green-*      → text-restricted-green
  border-red-*      → border-restricted-red

HOVER STATES
  hover:bg-zinc-800 → hover:bg-celeste-surface
  hover:bg-zinc-700 → hover:bg-celeste-panel

FOCUS STATES
  focus:ring-blue-*  → focus:ring-celeste-accent
  focus:border-blue-* → focus:border-celeste-accent
  focus:ring-red-*   → focus:ring-restricted-red
```

---

## READ vs MUTATE ACTION STYLING

The principle: READ actions = text links. MUTATE actions = buttons.
Weight comes from border + background + padding, NOT shadows.

```
READ ACTION:
  bg-transparent
  text-celeste-text-secondary
  font-normal (400)
  px-2 py-1
  hover:text-celeste-text-primary

MUTATE ACTION:
  bg-celeste-surface
  border border-celeste-border
  text-celeste-text-primary
  font-medium (500)
  px-3 py-1.5
  rounded-celeste-sm
  hover:bg-celeste-panel
```

---

## DAILY WORKFLOW

```
Morning:
  1. Open Claude Code
  2. Paste the system prompt (once per session)
  3. Give it the next task from this playbook
  4. Review the output

Per task:
  1. Read the agent's proposed changes
  2. Check: are all values from the celeste token set?
  3. Check: does the component still render correctly?
  4. If yes → accept and move to next task
  5. If no → tell the agent what's wrong, re-run

End of day:
  1. Run the build (npm run build)
  2. Note any new errors
  3. Visual check the app — does anything look wrong?
  4. Update your tracking (which tasks are done)
```

---

## TRACKING CHECKLIST

Copy this and check off as you go:

```
PHASE 1: Foundation
  [ ] Task 1.1 — Tailwind config audit
  [SKIP] Task 1.2 — Disable default colors (do in Phase 9 instead)

PHASE 2: Search Surface
  [ ] Task 2.1 — SpotlightSearch.tsx
  [ ] Task 2.2 — SpotlightResultRow.tsx
  [ ] Task 2.3 — SpotlightPreviewPane.tsx
  [ ] Task 2.4 — MicroactionButton.tsx

PHASE 3: UI Primitives
  [ ] Task 3.1 — button.tsx
  [ ] Task 3.2 — dialog.tsx
  [ ] Task 3.3 — input.tsx
  [ ] Task 3.4 — Remaining UI primitives (10 files)

PHASE 4: Celeste Primitives
  [ ] Task 4.1 — ResultCard.tsx
  [ ] Task 4.2 — Remaining celeste components (7 files)

PHASE 5: Lens Cards
  [ ] Task 5.1 — FaultCard.tsx + WorkOrderCard.tsx
  [ ] Task 5.2 — Remaining cards (12 files)

PHASE 6: Modals
  [ ] Task 6.1 — Top 8 violation modals
  [ ] Task 6.2 — Remaining modals (~25 files)

PHASE 7: High-Violation Surfaces
  [ ] Task 7.1 — Email components (6 files)
  [ ] Task 7.2 — Dashboard/situation components (7 files)
  [ ] Task 7.3 — Action system components (6 files)

PHASE 8: Cleanup
  [ ] Task 8.1 — ThreadLinksPanel.tsx
  [ ] Task 8.2 — Pages (8 files)
  [ ] Task 8.3 — Full codebase audit

PHASE 9: Governance
  [ ] Task 9.1 — ESLint rule
  [ ] Task 9.2 — Migration verification report

TOTAL: 878 violations → 0
```
