# Celeste Frontend Design Philosophy

**Status:** Canonical
**Date:** 2026-03-16
**Author:** Celeste7
**Scope:** All web surfaces — search, lenses, ledger, settings, handover, future modules

---

## 0. The Foundation: What This Product Is

Celeste is a **Personal Assistant (PA) for yacht crew**, not a filing cabinet or dashboard.

This single fact determines every visual and interaction decision. The crew:
- Is often in low-light environments (bridge, engine room, night watch)
- Is doing a job, not exploring software
- Issues action-based commands ("find the last WO on the starboard genset")
- Expects the system to respond intelligently and return them to their task

**The UI is not the product. The UI is the vessel the product arrives in.**

Every surface must earn its existence by making a crew member faster or more informed. Decoration is debt. A confused layout is a safety risk.

---

## 1. Mission → Visual Language

| Mission principle | Visual expression |
|-------------------|------------------|
| PA, not filing cabinet | Search bar is the primary control surface |
| Action over browsing | Direct navigation from result to entity — no intermediate steps |
| Trust through honesty | Read-only fields are visually distinct; locked data is labelled; no ghost features |
| Operational environment | Dark mode is primary; it is not a style choice, it is correct for the work context |
| Information density | 44px rows, not cards; every pixel carries meaning |
| Speed | Instant navigation, no loading-state animations that block reading |

---

## 2. Colour System

### The Core Distinction

**Teal/blue (`--mark`) = affordance, not status.**
Red/amber/green = status, not brand.

These two systems must never overlap. Teal tells the user: *this is interactive, this is navigable, this is selected*. Red tells the user: *this is critical, act now*. The moment teal appears on a fault badge, or red appears on a "selected" state, both signals become meaningless.

### Token Hierarchy (Dark)

| Token | Value | Role |
|-------|-------|------|
| `--mark` | `#5AABCC` | Interactive affordance — active nav, selected state, brand accent |
| `--teal-bg` | `rgba(58,124,157,0.13)` | Active surface tint — the "selected item" background |
| `--txt` | `rgba(255,255,255,0.92)` | Primary content — what the user is reading right now |
| `--txt2` | `rgba(255,255,255,0.55)` | Secondary — labels, nav titles, supporting information |
| `--txt3` | `rgba(255,255,255,0.40)` | Tertiary — metadata, entity icons, time values |
| `--txt-ghost` | `rgba(255,255,255,0.20)` | Ghost — section headers, decorative separators, disabled |
| `--red` | `#C0503A` | Danger — destructive actions, critical fault status |
| `--red-bg` | `rgba(192,80,58,0.10)` | Danger surface — deletion zone, critical warning background |

### Traffic Light: Status Colours

Status colours communicate **system state**, not brand identity.

| Colour | Meaning | Where used |
|--------|---------|------------|
| Green | Certified, current, no action needed | Certificate validity, completion state |
| Amber/orange | Warning, pending, attention needed | Overdue, expiring, waiting approval |
| Red | Critical, fault, action required now | Open faults, overdue safety items |
| Teal | Interactive, selected | Never use for status |

**Rule:** If you are tempted to use teal as a status colour, you are confusing affordance with state. Find the correct status colour.

### Why Teal Specifically

The brand name "Celeste" derives from *caelestis* — sky, heavenly blue. The specific teal (`#5AABCC`) sits between sky blue and sea blue: the horizon line where a yacht operates. It is calm, directional, and precise — not aggressive (royal blue) and not passive (grey). In dark mode it reads cleanly against near-black surfaces at the exact contrast ratio needed for nav labels. In light mode it darkens to `#2B7BA3` to maintain readability.

---

## 3. Typography

### The Semantic Split

**Inter** = human-authored language
**SF Mono / Fira Code** = machine-generated structured data

This is a semantic distinction, not aesthetic. When you see monospace text, your brain switches to "reading a serial number" mode. When you see Inter, your brain reads language. Mixing them at random destroys this signal.

| Content type | Font | Example |
|-------------|------|---------|
| Names, roles, descriptions, labels | Inter | "J. Morrison", "Chief Engineer", "Update password" |
| Entity identifiers, file paths, timestamps, version strings, amounts | Mono | `14:32`, `/02_engineering`, `v0.9.4`, `WO-1042` |
| Email addresses | Mono | `j.morrison@sv-andromeda.com` |

**Rule:** If a human typed the value in natural language, use Inter. If the system generated or formatted the value, use Mono.

### Weight Hierarchy

| Weight | Role |
|--------|------|
| 600 | Headers, nav labels, page titles, section anchors |
| 500 | Row primary content, button labels, active states |
| 400 | Secondary text, descriptions, metadata, read events |

Weight communicates importance. A row's entity name at 500 says "this is what this row is". The supporting user + time at 400 says "this is context about it". The day header at 600 says "this is a temporal anchor point, not content". Never use 700+ — it reads as alarm, not hierarchy.

### Font Sizing

| Size | Use |
|------|-----|
| 22px | Version number display (only) |
| 15px | Page titles within content areas |
| 14px | Row primary content, body text |
| 13px | Navigation labels, button text, action text |
| 12.5–12px | Secondary row content, captions |
| 11px | Tertiary metadata |
| 10px | Day/section anchors (uppercase overline) |
| 9px | Section labels within content groups |

**Row primary is always 14px.** This aligns search result rows, ledger event rows, and all future list views into a single visual language. The eye reads them as the same kind of thing.

---

## 4. Borders and Shadows

### The Ambient Light Physics

Borders simulate how physical objects catch and cast light. Objects in a room catch ambient light on their upper surfaces and fade at their bases. The UI replicates this:

```css
/* Dark mode — object floating above dark surface */
border-top:    1px solid rgba(255,255,255,0.09);  /* catches overhead light */
border-right:  1px solid rgba(255,255,255,0.05);
border-bottom: 1px solid rgba(255,255,255,0.02);  /* fades into shadow beneath */
border-left:   1px solid rgba(255,255,255,0.05);
```

This is not decoration. It communicates elevation. A component with a bright top border and dim bottom border is telling you: "I am above the surface. Light hits my top edge."

**Rule:** Never use a uniform border (all four sides same value) on elevated surfaces. It reads as flat, which contradicts the depth the shadow is trying to create.

### Shadow as Elevation Signal

| Shadow | Component | Meaning |
|--------|-----------|---------|
| `0 28px 80px rgba(0,0,0,0.80)` + ring | Modal | This element is the focus of the entire screen |
| `0 28px 80px rgba(0,0,0,0.55)` + `0 4px 16px` | Spotlight panel | Elevated, but embedded in the page context |
| `0 8px 24px rgba(0,0,0,0.35)` | Popover, dropdown | Temporarily elevated, close to the surface |
| None | Row, form field, table cell | Ground level — part of the surface, not above it |

**Rule:** Shadow intensity tells the user how important and focused this element is. Rows have no shadow because they are content on the surface, not objects floating above it.

---

## 5. Glass Effect (Backdrop Blur)

### Where Glass Is Used

| Surface | Glass applied | Why |
|---------|--------------|-----|
| Modal header | Yes | Floats above modal body; stays visible during scroll |
| Panel header (Ledger, Spotlight) | Yes | Navigation layer — persists above scrolling content |
| Notification toasts | Yes | Temporal overlay — aware of content beneath |
| Sidebar (Settings) | No | Static structure — not floating |
| Content rows | Never | Ground level — part of the surface |
| Form inputs | Never | Data entry surface — should feel solid, reliable |

### Why Glass

Glass effect (`backdrop-filter: blur(8px)` + semi-transparent background) signals: *"I am aware of the world beneath me, but I am not of it."*

It is used exclusively on **navigation and context layers** — elements that must persist and remain readable while content scrolls beneath them. It is never used on content itself, because content should feel grounded and stable, not floating.

**Anti-pattern:** Using glass on content rows or data cells. This makes data feel ephemeral and untrustworthy. Data should feel solid.

---

## 6. Spacing and Sizing

### Touch Target: 44px Minimum

Every interactive row is 44px minimum height. This applies to:
- Spotlight search result rows
- Ledger event rows
- Settings rows (interactive)
- Any future list-view rows

This is not a mobile accommodation — it is the minimum size for confident, fast interaction in any environment. Yacht crew wear gloves. They are in rough seas. The touch target must be unambiguous.

**Exception:** Navigation items in Settings sidebar are 32px — they are secondary navigation within an already-focused modal context, not primary operational controls.

### The Three Heights

| Height | Element | Reasoning |
|--------|---------|-----------|
| 42–46px | Panel/modal headers | Navigation authority layer |
| 44px | Content rows | Touch-safe operational content |
| 32px | Secondary nav items | Focused modal context |

### Padding

| Context | Padding | Why |
|---------|---------|-----|
| Row: horizontal | `12px` | Consistent left edge alignment across all rows |
| Row: vertical | `8px` | Breathing room within 44px min-height |
| Content area | `20px 18px` | Comfortable reading margin |
| Sidebar nav | `0 9px` | Tighter — nav is infrastructure, not content |

---

## 7. Interactive States

### The Hover Promise

**Hover = a promise that clicking will do something.**

This is the rule behind `.no-hover`. If a row is read-only — a locked email address, a NAS path set by an admin, a static timestamp — applying hover feedback is a lie. It implies the user can interact, and they cannot. This destroys trust.

```css
.no-hover { cursor: default; }
.no-hover:hover { background: transparent; }
```

Apply `.no-hover` (or equivalent) to any row where clicking does nothing.

### State Progression

| State | Visual | Signal |
|-------|--------|--------|
| Default | Surface background | "I exist, available" |
| Hover | `--surface-hover` (+1 elevation step) | "I am aware of you" |
| Active/selected | `--teal-bg` | "I am chosen" |
| Focus-visible | 2px teal ring, 1px offset | "Keyboard navigation active" |
| Read-only | No hover, `cursor: default` | "I am information, not action" |
| Disabled | Ghost opacity | "Unavailable right now" |

### No Transition Overkill

Transitions serve to communicate change, not to perform. Allowed:
- Background on hover/active: `60ms ease-out` (imperceptible but smooth)
- Chevron rotation: `120ms ease-out` (shows the collapse direction)
- Shine sweep on Spotlight panel open: one-shot, forward only

Not allowed:
- Page transitions between settings sections (instant swap)
- Row entrance animations (content should feel stable, not theatrical)
- Loading skeletons on sub-50ms operations

---

## 8. Icons

### Sizing by Context

| Size | Context |
|------|---------|
| 14px | Sidebar navigation (Settings, panel headers) |
| 16px | Row entity type icons (search results, ledger events) |
| 13px | Inline within text or metadata |
| 11×11px | External link indicators |

### Stroke vs Fill

All icons: **outline/stroke style**. Filled icons read as heavy and aggressive — they demand attention. Stroke icons communicate the same shape at lower visual weight, appropriate for a dense operational UI where the data should dominate, not the chrome.

**Exception:** Status indicator dots (filled circles for online/offline state) because they represent binary state, not entity type.

### Entity Type Semantics

These mappings must be consistent across every surface (search, ledger, lens pages, handover):

| Entity | Icon | Why |
|--------|------|-----|
| `work_order` | Clipboard/document with lines | A work order is a written instruction |
| `fault` | Triangle with exclamation | Universal warning symbol |
| `equipment` | Cog/gear | Mechanical systems |
| `part` / `inventory` | Hexagon | Component shape, neutral |
| `document` | Page with lines | Text document |
| `email_thread` | Envelope | Communication |
| `certificate` | Award/ribbon | Certification and compliance |
| `warranty` | Shield | Protection |
| `purchase_order` | Receipt/cart | Commercial |
| `hours_of_rest` | Clock | Time compliance |
| `handover` | Arrow (→) | Transfer of state |

**Rule:** If you add a new entity type, add it to this table first. Don't pick an icon based on aesthetics; pick it based on what the entity *is*.

---

## 9. Section Headers and Hierarchy

### The Three Levels (Never More)

```
Level 1: Panel/Modal Header  (navigation + context)
Level 2: Section Anchor      (temporal or type grouping)
Level 3: Content Row         (the actual data)
```

Every UI surface has exactly these three levels. Adding a fourth (sub-groups, nested sections, cards within sections) creates confusion about where in the hierarchy the user is.

### Section Anchor Typography

Section headers (day headers in ledger, group headers in search, section labels in settings) share the same visual language:

```
10px / 600 / 0.10–0.12em letter-spacing / uppercase / --txt3 or --txt-ghost
```

They are labels, not rows. They have no background, no hover state, no affordance signals. They are temporal or categorical anchors. The content below them flows from them.

**The visual separator between sections** is either:
- A 1px `--border-sub` line above the next section header (Ledger, Spotlight groups)
- Top padding on the section header (Settings row groups)

Never both. One separator per section boundary.

---

## 10. Dark vs Light Mode

### Dark Is Primary

Dark mode is not the "cool" option. It is operationally correct for the environments Celeste users work in:
- Bridge: low-light, chart-table environment
- Engine room: oil, metal, low ambient light
- Night watch: eye adaptation, red/low light discipline
- Accommodation: low light, checking on a tablet at 0300

Light mode exists for shore-side and office contexts where ambient light is high and dark surfaces create unnecessary contrast.

**Design order:** Design dark first. Adapt to light. Never the reverse.

### Token-Only Switching

No raw hex values appear in component CSS. Zero. Colour switches entirely through token reassignment on `.light` container:

```css
.light {
  --surface:  #FFFFFF;
  --mark:     #2B7BA3;  /* darker teal for light mode contrast */
  /* ... */
}
```

**Rule:** If you write `color: #5AABCC` anywhere in a component, you've broken the system. Write `color: var(--mark)`.

### Light Mode Adjustments

| Property | Dark | Light | Why |
|----------|------|-------|-----|
| `--mark` | `#5AABCC` | `#2B7BA3` | Darker to maintain contrast on white |
| Shadow | Heavy (0.80 opacity) | Light (0.13 opacity) | Light surfaces already create natural separation |
| Border-top | `rgba(255,255,255,0.09)` | `rgba(0,0,0,0.12)` | Light from above still applies, but inverted |

---

## 11. Data Representation

### Rows: The Default

For operational data (lists of entities, audit events, search results), **rows are the default**. Not cards. Not tiles.

Cards waste space and fragment the scanning pattern. Crew scanning for a specific work order number does not need a card with a hero image and title treatment — they need a 44px row they can scan at 200ms per item.

**Use cards when:** The content has significant variation in structure or there is a visual asset (photo, diagram) that carries information. Example: attached photos in a fault report.

### Tables

For dense multi-column structured data (parts list, purchase order line items, hours of rest grid). Tables communicate: "every row is the same shape, and comparing columns matters."

Never use tables for entity lists where the user navigates rows — use rows. Tables are for reading across columns, not navigating to individual items.

### "Object — Verb" Grammar

Event rows, audit entries, and notifications follow a consistent grammar:

```
[Entity Type] [Identifier] — [Verb in past tense]
Work Order 1042 — Updated
Fault F-0221 — Closed
Part 774-B — Issued
```

This grammar is unambiguous. The user knows immediately: what was touched, what happened to it. Avoid passive voice, avoid gerunds, avoid "has been":

❌ "Work order 1042 has been updated by J. Morrison"
✅ "Work Order 1042 — Updated · J. Morrison · 14:32"

---

## 12. Locked and Read-Only Fields

### Visual Honesty

Read-only fields must be visually distinguishable from editable fields. A user should never click a field expecting to edit it and be surprised.

| Signal | Editable | Read-only |
|--------|----------|----------|
| Cursor | `text` or `pointer` | `default` |
| Hover | `--surface-hover` background | None |
| Value typography | Normal | Monospace where applicable |
| Badge | None | `LOCKED` badge (9px uppercase) |

The `LOCKED` badge appears on fields that are locked **by organisational policy** (email, role, department, NAS path). It is not shown on fields that are simply not editable in this view. The distinction matters: one says "an admin controls this", the other is just UI state.

---

## 13. Articulation Conventions

| Element | Convention | Anti-pattern |
|---------|-----------|--------------|
| Labels | Sentence case | Title Case For Everything |
| Buttons | Verb (action word) | "Click here", "Submit" |
| Section headers | UPPERCASE (design token) | Mixed case headers |
| Placeholders | Descriptive example | "Enter value here" |
| Error messages | What happened + what to do | "Error occurred" |
| Empty states | What will appear here + how to create it | Blank space or spinning loader |

---

## 14. What Is Explicitly Out of Scope

These patterns are banned not because they cannot be built, but because they contradict the product's mission:

| Pattern | Why banned |
|---------|-----------|
| Skeleton loaders on <100ms operations | Creates anxiety where none exists |
| Animated page transitions | Slows navigation, adds no meaning |
| Onboarding overlays and tooltips | Crew learn by doing; treat them as professionals |
| Marketing copy in the UI | This is an operational tool, not a sales funnel |
| Ghost features (disabled placeholders) | Implies capability that doesn't exist — dishonest |
| Raw hex values in component CSS | Breaks the token system |
| Cards where rows suffice | Wastes space, fragments scanning |
| Uniform borders on elevated surfaces | Contradicts the ambient light physics |

---

## 15. The Test

Before any component is designed or built, ask:

1. **Does every element earn its place?** If you removed it, would the user notice something missing?
2. **Is this honest?** Read-only is labelled. Interactive has affordance. Locked is marked.
3. **Does the typography communicate semantic meaning?** Inter for language, Mono for system data.
4. **Is dark mode primary?** Designed for low-light first?
5. **Does hover make a promise that clicking fulfils?**
6. **Could a crew member in a hurry, under poor lighting, find what they need in under 3 seconds?**

If all six are yes: ship it.

---

## 16. Entity View Layout (The Document Metaphor)

### What an Entity View Is

An entity view (lens page) is the **detail page for a single record** — a work order, a fault report, an equipment card, a certificate. It is the surface where a crew member reads, acts, and decides.

An entity view is a **document**, not a **dashboard**.

This distinction determines everything. A dashboard is a grid of independent widgets, each reporting on a different domain. Widgets don't flow into each other — they sit in isolation. A document is a narrative with a beginning, middle, and end. It flows top-to-bottom. Each section builds on the one before it.

A work order is a logbook entry. You identify it, read its instructions, check its progress, review its attachments, and decide what to do next. This is sequential thought, not parallel scanning.

**Consequence:** Entity views scroll. They do not paginate. They do not use tabs. They do not use card grids. The crew member sees the complete shape of the record in a single flowing pass.

### Why Not Tabs

Tabs hide information. A tabbed work order forces the crew member to ask: "Is there anything important behind the other tabs?" They must click through each one to build a mental model. This is cognitive overhead where there should be none.

With a flowing scroll, every section heading is visible — even when collapsed. The crew member can see the SHAPE of the record: 5 checklist items (3 done), 3 notes, 2 attachments, 2 parts. They absorb this in a single glance without clicking anything. Sections they need they expand. Sections they don't they scroll past.

**Tabs are appropriate for:** truly distinct modes (e.g., Settings where sections are configuration domains). They are inappropriate for entity records where information belongs to a single narrative.

### Why Not Cards

Cards create visual isolation. Each card becomes its own bounded universe with its own border, shadow, and padding. This fragments the narrative. A checklist card doesn't "flow from" the document section above it — it sits beside it as a peer.

The work order is not a collection of peer items. It has a hierarchy: identity → reference → operations. Cards flatten this hierarchy. Ruled lines preserve it — they say "a new topic starts here" without saying "here is a separate container."

**Cards are appropriate for:** items with genuinely independent identity and visual assets (photo gallery, product catalog). They are inappropriate for sections of the same document.

### The Anatomy

Every entity view follows this vertical structure:

```
┌─────────────────────────────────────────────┐
│ LENS HEADER (glass)                         │  Navigation layer
│ ← Back    WORK ORDER    Related    ✕        │  — persists, blur backdrop
├─────────────────────────────────────────────┤
│                                             │
│ IDENTITY STRIP                              │  Who is this record?
│ ┌─ Overline ──────── Primary Action ──────┐ │
│ │ WO-1042            [Mark Complete ▾]    │ │
│ └─────────────────────────────────────────┘ │
│ Emergency Valve Replacement                 │  Title: standalone, largest type
│ Engine Room · Assigned to R. Chen           │  Context: where + who
│ [In Progress] [Critical]                    │  State: pills below title
│                                             │
│ EQUIPMENT    E-007 Main Engine              │  Detail lines: key-value
│ DUE          17 Mar 2026                    │
│                                             │
│ Description                                 │
│ Emergency isolation valve on port fuel...   │  Full narrative description
│                                             │
├── ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ──┤
│ OFFICIAL DOCUMENTS          3        ▾      │  First section
│ ├ Open SOP — Valve Replace... SOP-ENG-042   │
│ ├ ISM-F042 — Fuel System Isolation...       │
│ └ Class Certificate — Engine Room Fire...   │
├── ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ──┤
│ CHECKLIST                  3/5       ▾      │  Operations: checklist
│ ├ ✓ Isolate fuel supply                     │
│ ├ ✓ Install temporary bypass                │
│ ├ ✓ Order replacement valve (774-B)         │
│ ├ ○ Replace valve and reconnect fuel line   │
│ └ ○ Pressure test at 2.5 bar for 30 min    │
├── ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ──┤
│ NOTES               + Add           ▾      │
│ ...                                         │
├── ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ──┤
│ HISTORY                              ▸      │  Collapsed by default
├── ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ──┤
│ ATTACHMENTS         Upload           ▾      │
│ ...                                         │
├── ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ──┤
│ PARTS               + Add     2      ▸      │  Collapsed by default
│ ...                                         │
└─────────────────────────────────────────────┘
```

### Section Order Is Intentional

The ordering of sections encodes priority:

1. **Official Documents** — the reference material. Before you DO anything, you READ the instructions.
2. **Checklist** — the operational accountability trail. The crew member's primary task.
3. **Notes** — the conversation. Commentary, observations, updates.
4. **History** — the long view. Prior service periods. (Collapsed by default — it's context, not action.)
5. **Attachments** — evidence. Photos, PDFs, supporting files.
6. **Parts** — inventory allocation. (Collapsed by default — you check this when planning, not during execution.)

This order mirrors how a professional approaches a task: read the brief, work the checklist, log what happened, review the history, check the evidence, confirm the resources.

---

## 17. Identity Strip

### The Overline-Title Pattern

The identity strip is the first thing the crew member sees. It answers: **What am I looking at? What's its state? What can I do?**

The vertical order is not random. Each element earns its position:

| Position | Element | Type size | Font | Weight | Why this position |
|----------|---------|-----------|------|--------|-------------------|
| 1 | WO number | 12px | Mono | 500 | System reference. Machine-generated. Subordinate. The system knows what this is. |
| 1 (right) | Primary action | 13px | Inter | 500 | The primary CTA earns the highest position — it's the most important thing you can DO. |
| 2 | Title | 22px | Inter | 600 | Human-readable anchor. This is what the crew member came to see. It earns the largest type. |
| 3 | Context line | 13px | Inter | 400 | WHERE (location) + WHO (assignee). The two immediate operational questions. |
| 4 | Status pills | 12px | Inter | 500 | STATE, not identity. The record IS "Emergency Valve Replacement." It HAPPENS TO BE "In Progress." |
| 5 | Detail lines | 13px | Mixed | 400/500 | Operational parameters (Equipment, Due). Key-value format. Less volatile than status. |
| 6 | Description | 14px | Inter | 400 | The full narrative. Read AFTER you know what you're looking at. |

### Why the System Reference and Primary Action Share a Row

The overline (WO-1042) and the primary action (Mark Complete) sit at the same altitude because they form the **control line** — the system's identification of the record and the user's ability to act on it. They are complementary: one is input (the record exists), the other is output (what you do with it).

The title sits BELOW this line because the title is identity, not action. Mixing title and action on the same row creates visual competition — the eye doesn't know whether to read or to act. By separating them vertically, the crew member reads downward (identity) and glances right (action) as independent visual operations.

### Why the Title Is Standalone

The title does NOT include the WO number. `WO-1042` is a system reference — it helps the database, not the human. The human reads "Emergency Valve Replacement." Combining them (`WO-1042 — Emergency Valve Replacement`) creates a longer line that buries the human-readable part behind a machine identifier.

The overline pattern (small mono text above the title) is borrowed from journalism and document design: the dateline sits above the headline. The date locates the story in time; the headline tells you what it's about. Here, the WO number locates the record in the system; the title tells you what it's about.

### Context Line Grammar

The context line follows this grammar: `{Location} · Assigned to {Crew Member}`

The crew member name is teal (interactive affordance) because clicking it navigates to their profile. The location is plain text because it is context, not navigation. The `·` separator is lighter than both — it's grammatical punctuation, not content.

### Detail Lines: Key-Value, Not Inline

Equipment and Due appear as labeled key-value pairs, not inline metadata. This is intentional:

```
EQUIPMENT    E-007 Main Engine       ← Label left-aligned, value right
DUE          17 Mar 2026
```

The label column (11px, uppercase, `--txt3`) creates a consistent left edge. The value column uses the appropriate font: Equipment ID in mono (system identifier), equipment name in Inter (human name), date in mono (system-formatted). This structure scales — if a future entity has 5 detail lines, they align cleanly.

### Status Pills: Below Title, Not Beside It

Status pills sit below the title and context because they represent volatile state — they change throughout the record's lifecycle. The title and context are stable (they were set when the record was created). Placing pills next to the title would give temporary state the same visual weight as permanent identity.

---

## 18. Section System for Entity Views

### Section Separation: The Ruled Line

Sections are separated by three properties working together:

```css
border-top: 1px solid var(--border-sub);    /* The ruled line — "new topic" */
padding-top: 24px;                           /* Breathing room after the line */
margin-top: 32px;                            /* White space before the line */
```

Total visual separation: ~56px of space with a hairline rule. This is enough to clearly delineate sections without fragmenting the document into isolated containers.

The ruled line says: "A new topic starts here." It does NOT say: "Here is a separate box." This is the difference between a chapter heading in a book and a card in a wallet.

**Anti-pattern:** Adding background colour, borders, border-radius, or shadow to sections. The moment a section looks like a "card" or "module," the document metaphor breaks and the layout becomes a dashboard.

### Section Headings: Landmarks, Not Labels

Entity view section headings differ from list-view section anchors:

| Context | Size | Weight | Tracking | Colour | Purpose |
|---------|------|--------|----------|--------|---------|
| List anchors (ledger, search groups) | 10px | 600 | 0.10em | `--txt-ghost` | Temporal grouping — "Today", "Yesterday" |
| Entity view headings | 14px | 600 | 0.06em | `--txt3` | Wayfinding landmarks — "CHECKLIST", "NOTES" |

Entity view headings are larger because they serve as **wayfinding landmarks** in a longer document. When a crew member scrolls quickly through a work order, these headings must catch the eye and say: "You are now in the Notes section." At 10px, they vanish into the content. At 14px with 600 weight and uppercase, they create clear visual breaks without being overbearing.

### Section Header Composition

Every section header contains up to five elements:

```
[Icon] [TITLE]                [Action]  [Count]  [Chevron]
 16px   14px/600                13px     11px      16px
 --txt3 --txt3/uppercase        --mark   --txt-ghost --txt-ghost
```

| Element | Always present | Role |
|---------|---------------|------|
| Icon | Yes | Entity type identification — matches §8 icon semantics |
| Title | Yes | The section's identity. UPPERCASE, 600 weight. |
| Action | When applicable | "+ Add", "Upload" — section-scoped micro action in teal |
| Count | When applicable | Item count in mono (e.g., "3/5", "2"). System-generated. |
| Chevron | Yes | Collapse/expand indicator. Rotates 90° when collapsed. |

The entire header row is clickable (toggles collapse). The action button stops event propagation — clicking "+ Add" opens the add modal, not the collapse toggle.

### Collapse Behaviour

- Sections default to OPEN (showing content) unless they represent secondary context.
- History and Parts default to COLLAPSED because they are reference material, not active tasks.
- Collapsed sections still show their header row — the crew member always sees the section exists and can see its count.
- Collapse animation: `max-height` transition with `opacity` fade, 300ms ease. Fast enough to not feel sluggish, slow enough to communicate what happened.

---

## 19. Action Patterns and Button Taxonomy

### The Split Button

The primary action on an entity view uses a **split button**: the main button (the CTA) and a dropdown toggle (secondary actions).

```
┌──────────────────┬───┐
│  Mark Complete    │ ▾ │
└──────────────────┴───┘
```

**Why a split button, not separate buttons:**

Six separate buttons ("Start Work", "Edit", "Log Hours", "Reassign", "Archive", "Mark Complete") create choice paralysis. The crew member sees six equal options and must evaluate each one. On mobile, they wrap to multiple lines. As features grow, the button row becomes unmanageable.

The split button encodes a hierarchy: **one primary action, everything else tucked away.** The crew member sees "Mark Complete" (the most likely thing they'll do) and knows the dropdown icon means "more options available." This reduces cognitive load from 6 decisions to 1 glance + 1 optional click.

### Primary CTA: Disabled State

When the work order has an incomplete checklist, Mark Complete is **disabled** — greyed out, cursor default, no hover response. A tooltip on hover explains why: "Complete all checklist items first."

This is not UX friction. It is a **safety guardrail**. Maritime maintenance checklists are evidence trails. Each item represents a physical step that was verified. Allowing completion with pending items invites shortcuts that could have safety consequences.

The disabled state uses `rgba(255,255,255,0.06)` background and `--txt-ghost` text — visually present but clearly non-interactive.

### Button Taxonomy

The entity view uses five distinct button types, each with a specific visual weight and placement:

| Type | Visual | Placement | Purpose | Example |
|------|--------|-----------|---------|---------|
| **Primary CTA** | Subtle fill, 36px height, 13px/500 | Identity strip, top-right | The ONE thing you most likely came to do | Mark Complete, Start Work |
| **Dropdown toggle** | Subtle fill, 36px, icon only | Attached to primary CTA | Reveals secondary actions | ▾ chevron |
| **Dropdown item** | Full-width, 44px, icon + label | Within dropdown menu | Secondary actions | Edit, Add Note, Log Hours, Reassign |
| **Dropdown danger** | Same as item, red text | Bottom of dropdown, after separator | Destructive action | Archive |
| **Section action** | Teal text, no border, 4px/8px padding | Section header, before chevron | Section-scoped creation | + Add, Upload |
| **Inline action** | Teal text, no border, no padding | Within content items | Item-scoped action | Undo, Show more |
| **Header action** | Ghost, 28px height, icon + label | Lens header, top-right | Navigation-level action | Related, ✕ Close |

### Placement Rules

1. **One primary CTA per view.** Never two primary buttons. If there are two competing primary actions (Start Work vs Mark Complete), show only the one that applies to the current state.
2. **Destructive actions go last** in the dropdown, below a separator, in red. They should require deliberate navigation — you scroll past safe options before reaching danger.
3. **Section actions sit in the section header**, not below the content. They are visible when the section is collapsed, so the crew member can add a note without expanding the notes section first.
4. **Inline actions have no button chrome.** They are teal text. Adding a border or background to "Undo" or "Show more" would give them too much visual weight — they'd compete with the content they serve.

### Why Not a Floating Action Bar

Some entity views use a sticky "action bar" pinned to the bottom of the viewport. We do not.

The action bar pattern assumes the user is always ready to act. In an entity view, the crew member is often READING — reviewing notes, checking the checklist, inspecting attachments. A floating bar adds permanent visual noise to a reading activity. The primary action in the identity strip is visible on first load (the most important moment) and accessible by scrolling to top (fast, familiar). The dropdown is accessible from there.

---

## 20. Font Discipline — Complete Content Mapping

### The Governing Principle

**Inter communicates what a human said. Mono communicates what a system generated.**

This is not aesthetic preference. It is a semantic signal that helps the crew member's brain switch between "reading language" and "reading structured data" modes. When you see monospace, you know you're looking at a formatted value — a serial number, a timestamp, a file path. When you see Inter, you know a person composed those words.

### Comprehensive Mapping

| Content | Font | Weight | Size | Example | Reasoning |
|---------|------|--------|------|---------|-----------|
| Entity title | Inter | 600 | 22px | Emergency Valve Replacement | Human-authored name. Largest type — it's what you came to see. |
| Entity ID (overline) | Mono | 500 | 12px | WO-1042 | System-generated identifier. Small — the machine knows this, not the human. |
| Section heading | Inter | 600 | 14px | CHECKLIST, NOTES | Human label for a document section. Uppercase for wayfinding. |
| Context line | Inter | 400 | 13px | Engine Room · Assigned to R. Chen | Human-readable context. Location is a name, not a code. |
| Crew member name | Inter | 400 | 13px | R. Chen, J. Morrison | A person's name is always Inter. Always. |
| Detail label | Inter | 500 | 11px | EQUIPMENT, DUE | Human label. Uppercase, small — infrastructure, not content. |
| Equipment ID | Mono | — | 12–13px | E-007 | System identifier. Machine-generated code. |
| Equipment name | Inter | 400 | 13px | Main Engine | Human-readable name. |
| Status label | Inter | 500 | 12px | In Progress, Critical | Human-readable state. Not a code. |
| Date | Mono | 400 | 11–13px | 17 Mar 2026, 01 Jan 2026 | System-formatted temporal value. |
| Timestamp | Mono | 400 | 10–11px | 14 Mar 10:30, 16 Mar 14:32 | System-generated temporal precision. |
| Document code | Mono | 500 | 12px | SOP-ENG-042, ISM-F042 | Formal document reference number. |
| Document title | Inter | 500 | 13px | Valve Replacement Procedure | Human-readable document name. |
| Revision/version | Mono | 400 | 11px | Revision 3 | System-tracked version number. |
| Quantity | Mono | 500 | 12px | × 2, × 1 | Formatted numeric value. |
| Stock count | Mono | 400 | 11px | Stock: 6, Stock: 13 | System-reported inventory level. |
| File name | Mono | 400 | 13px | valve_inspection_photo.jpg | System path — underscores and extensions are machine conventions. |
| File size | Mono | 400 | 11px | 2.4 MB, 156 KB | Formatted numeric measurement. |
| Part number | Mono | 500 | 12px | 774-B, ORG-114 | Catalogue identifier. |
| Part name | Inter | 500 | 13px | Impeller Kit, O-Ring Set | Human-readable name. |
| Hours logged | Mono | 400 | 11px | 12.5 hrs, 6 hrs | Numeric measurement. |
| Progress count | Mono | 400 | 11px | 3/5, 2 | System-computed count. |
| Note body | Inter | 400 | 14px | "Bypass valve installed..." | Human-authored natural language. |
| Note author | Inter | 500 | 13px | R. Chen | Person's name. |
| Description text | Inter | 400 | 14px | "Emergency isolation valve..." | Human-authored narrative. |
| Button label | Inter | 500 | 13px | Mark Complete, Edit Details | Action verb — human language. |
| Action link | Inter | 500 | 13px | Open SOP, + Add, Upload | Action verb — human language, teal colour. |
| Inline action | Inter | 500 | 11–12px | Undo, Show more | Micro action — human language, teal. |
| PO number | Mono | 400 | 13px | PO-89 | System-generated purchase reference. |
| Period year | Mono | 600 | 13px | 2026, 2024 | System-formatted temporal anchor. |
| Period label | Inter | 400 | 12px | Current period, Previous service | Human-readable description. |
| Caption (image) | Inter | 400 (italic) | 11px | "Leak visible bottom-right..." | Human-authored observation. Italic = quotation. |

### The Test

For any text element, ask: **"Did a person compose this, or did the system format it?"**

- "R. Chen" — a person has this name → Inter
- "14 Mar 10:30" — the system formatted this timestamp → Mono
- "Isolate fuel supply" — a person wrote this instruction → Inter
- "774-B" — a catalogue system assigned this code → Mono
- "Critical" — a person chose this label from a dropdown → Inter (it's a human-readable word, not a machine code)
- "SOP-ENG-042" — a document management system assigned this reference → Mono

---

## 21. Document Row Pattern

### Equal Authority

All official documents linked to an entity have equal visual weight. An SOP, an ISM procedure, and a class certificate are all rows in the same list. None receives special treatment (no tinted background, no larger icon, no border).

**Why:** Over-decorating one document implies it is more important than the others. In a maritime context, a class certificate may be more legally significant than an SOP, but the UI should not make that judgment. The crew member reads all relevant documents — the UI presents them equally and lets professional judgment determine priority.

### The SOP Action Pattern

When a document has a primary action (e.g., "Open SOP"), the action verb appears in teal as the first word of the row title:

```
[doc icon]  Open SOP — Valve Replacement Procedure (SOP-ENG-042)
```

"Open SOP" is the affordance (teal, interactive). The rest of the title is descriptive (default text colour). This communicates: clicking this row will open the SOP. The action IS the row.

This is preferred over a separate "Open" button because the entire row is clickable. Adding a button inside a clickable row creates ambiguity: does clicking the row do something different from clicking the button?

---

## 22. Content Patterns Within Sections

### Checklist: The Evidence Trail

A checklist is not a to-do list. It is a **verification record** — proof that specific physical steps were performed. Each completed item records WHO completed it and WHEN.

| Element | Purpose |
|---------|---------|
| Progress bar | Visual summary — how far along is this work order? |
| Checkbox (circle, not square) | Tap target. Filled green when complete, outlined when pending. |
| Description | What the step requires. Inter, 13px — human-authored instruction. |
| Completion metadata | WHO + WHEN. Crew name in Inter, timestamp in Mono. |
| Undo button | Safety mechanism — teal inline action. Allows reversal of accidental completion. |

**Checklist items that are complete** reduce to 50% opacity. This visually communicates "done — focus on what remains." The line-through on the description text reinforces this.

**Undo** exists because maritime maintenance is safety-critical. Accidentally marking "Pressure test at 2.5 bar" complete when it hasn't been done is not a UX inconvenience — it's a potential safety incident.

### Notes: Truncated Narrative

Notes are free-form human text. They vary wildly in length. A single verbose note (200+ words) can push the entire rest of the page below the fold, destroying the holistic view that the flowing-scroll layout was designed to preserve.

**Solution:** Notes beyond 3 lines are truncated with `-webkit-line-clamp: 3` and a "Show more" toggle. The crew member sees that 3 notes exist, reads the first few lines of each, and expands only the ones they need.

### History: Prior Service Periods

History is NOT an audit log of current session actions (that information lives in notes and checklist metadata). History represents the **temporal life** of the entity across service periods.

Each period shows: year, label, status tag (Active/Closed), and a summary line (notes count, uploads count, hours logged). This gives the crew member temporal context: this valve was also serviced in 2024 by R. Chen.

History defaults to COLLAPSED because it is context, not action.

### Parts: Operational, Not Financial

Parts show: part number (mono), part name (Inter, teal — clickable to navigate to inventory), quantity, and **stock level**.

Parts do NOT show price. The crew member reading a work order is an engineer or deckhand making operational decisions ("Do we have this part?"), not a purser making financial decisions ("Can we afford this part?"). Price belongs on purchase orders.

Stock level answers the operational question immediately: `Stock: 6` means proceed. `Stock: 0` means order first.
