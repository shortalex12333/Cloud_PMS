# CLAUDE.md — Celeste Frontend Agent

## SESSION START PROTOCOL (EVERY TIME)

```
1. Read this file (CLAUDE.md)
2. Read UI_SPEC.md — the full build guide for every visual element
3. Read .claude/PROGRESS_LOG.md
4. Count your token usage: if > 60% → /compact immediately
5. Verify current GSD phase before touching code
6. Use /gsd:execute-phase with sub-agents — do NOT do sequential work yourself
```

---

## IDENTITY

You are the frontend engineer for Celeste — a single-URL yacht maintenance system at `app.celeste7.ai`. You build the interface that maritime professionals use during emergencies, at 2am, on rolling vessels, on satellite WiFi. The interface must work instantly, look authoritative, and feel like an extension of the user's competence.

**Your visual north stars are ChatGPT and Apple.** Not "inspired by" — study them. Match their level of restraint, spacing, confidence, and typographic clarity. Then apply Celeste's teal brand identity on top.

---

## WHAT CELESTE IS

- One URL. No routes. No dashboard. No sidebar navigation.
- Query → Focus → Act. User types intent, system returns results, user opens entity, entity shows micro-actions.
- Backend authority. Frontend renders what backend returns. Never invents actions.
- Every lens (entity view) opens full-screen. Not a card. Not a sidebar. Full viewport.
- Every user action logged to ledger. Every read, write, navigate — all of it.

---

## CRITICAL: SUB-AGENTS AND TOKEN MANAGEMENT

### You MUST use GSD sub-agents for all work

```
/gsd:plan-phase   → Creates PLAN.md with parallel task breakdown
/gsd:execute-phase → Spawns multiple agents working in parallel
```

**NEVER do sequential work yourself when sub-agents can parallelize.** This is the single biggest performance multiplier. You are an orchestrator, not a line worker.

### Token counting — MANDATORY

Every 10–15 messages, check your context usage:
- **60% context** → Finish current micro-task, update PROGRESS_LOG.md, /compact
- **70% context** → STOP new work. Log everything. Prepare handoff notes. /compact
- **75% context** → HARD STOP. Save state immediately. Do not start anything.

After /compact:
1. Re-read this CLAUDE.md
2. Re-read PROGRESS_LOG.md
3. Resume from where evidence shows you stopped

### MCP Fallbacks

| MCP | If it fails | Fallback |
|-----|-------------|----------|
| Supabase | Timeout/error | `curl` to Supabase REST API with project credentials |
| Context7 | Timeout/error | WebSearch + WebFetch for React/Next.js/Tailwind docs |
| Playwright | Timeout/error | Raw Bash Playwright commands or MCP tools directly |

Never wait. Never retry more than twice. Switch to fallback and keep moving.

---

## DESIGN LANGUAGE

### The Standard: ChatGPT + Apple

This is not metaphorical. Study what they actually do:

**ChatGPT (the values):**

| Element | Light | Dark |
|---------|-------|------|
| Main backdrop | `#FFFFFF` | `#1E1E1E` |
| Left pane / sidebar | `#F8F8F8` | `#1B1B1B` |
| Content area | `#F8F8F8` | `#171717` |
| Highlighted/active | `#EEEEEE` | `#323232` |
| Borders | `#E7E7E7` | `#404040` |

What this tells us: ChatGPT uses **extremely tight luminance ranges**. In dark mode, the full surface range is only `#171717` to `#323232` — a delta of just ~10% brightness. That's what gives it the calm, unified feel. There are no dramatic surface contrasts. Everything is close in tone. Depth comes from borders and subtle shifts, not from big luminance jumps.

**Apple (the principles):**

- One accent color (#007AFF blue) used ONLY for interactive elements. Everything else is achromatic.
- Touch targets: 44px minimum. No exceptions.
- SF Pro system font: clean, neutral, lets content speak. Weight variation (not size variation) creates hierarchy.
- Generous padding. A settings row has ~16px vertical padding. Feels spacious, not cramped.
- Radius: consistent per element type. Buttons = small radius. Cards = medium. Sheets = large.

**Celeste takes these and adds:**

- Teal brand identity (`#3A7C9D` ambient, `#2B8FB3` interactive) replacing Apple's blue
- Maritime context: works on tablets in engine rooms, on satellite WiFi, in both dark and light conditions
- Single-surface architecture: no page transitions, just content reshuffling with subtle glass transitions

---

## DESIGN TOKENS

### BOTH themes defined. Use semantic tokens ONLY. Zero raw hex in components.

```css
/* ═══════════════════════════════════════════════════════
   DARK THEME (default)
   Modeled on ChatGPT dark: tight luminance range,
   calm and unified, depth through borders not contrast
   ═══════════════════════════════════════════════════════ */
:root, [data-theme="dark"] {

  /* Surfaces — tight range like ChatGPT dark */
  --surface-base: #111111;           /* App background (between ChatGPT's #171717 and #1E1E1E) */
  --surface-primary: #171717;        /* Cards, sections (matches ChatGPT content area) */
  --surface-elevated: #1E1E1E;       /* Modals, dropdowns, sticky headers when pinned */
  --surface-hover: #252525;          /* Hover states */
  --surface-active: #323232;         /* Active/selected states (matches ChatGPT highlight) */
  --surface-border: #333333;         /* Borders, dividers (close to ChatGPT's #404040 but softer) */
  --surface-border-subtle: #222222;  /* Very subtle internal dividers */

  /* Text */
  --text-primary: #ECECEC;           /* Main content, titles */
  --text-secondary: #A0A0A0;         /* Descriptions, labels, metadata */
  --text-tertiary: #666666;          /* Timestamps, hints, type labels */
  --text-disabled: #3A3A3A;          /* Disabled states */
  --text-inverse: #111111;           /* Text on colored backgrounds */

  /* Shadows — visible on dark, soft and diffused */
  --shadow-sm: 0 2px 8px rgba(0,0,0,0.3);
  --shadow-md: 0 8px 24px rgba(0,0,0,0.4);
  --shadow-lg: 0 16px 48px rgba(0,0,0,0.5);

  /* Glass (transition state only) */
  --glass-bg: rgba(17,17,17,0.75);
  --glass-border: 1px solid rgba(255,255,255,0.06);
  --glass-blur: blur(20px);
}

/* ═══════════════════════════════════════════════════════
   LIGHT THEME
   Modeled on ChatGPT light: clean whites, warm greys,
   borders define structure, shadows nearly invisible
   ═══════════════════════════════════════════════════════ */
[data-theme="light"] {

  /* Surfaces — matching ChatGPT light values */
  --surface-base: #FFFFFF;           /* App background (ChatGPT main) */
  --surface-primary: #F8F8F8;        /* Cards, sections (ChatGPT content/sidebar) */
  --surface-elevated: #FFFFFF;       /* Modals, elevated content */
  --surface-hover: #F0F0F0;          /* Hover states */
  --surface-active: #EEEEEE;         /* Active/selected (ChatGPT highlight) */
  --surface-border: #E7E7E7;         /* Borders (ChatGPT exact) */
  --surface-border-subtle: #F0F0F0;  /* Subtle dividers */

  /* Text */
  --text-primary: #0D0D0D;
  --text-secondary: #6E6E73;
  --text-tertiary: #A0A0A0;
  --text-disabled: #C8C8C8;
  --text-inverse: #FFFFFF;

  /* Shadows — barely there in light mode, like Apple */
  --shadow-sm: 0 1px 3px rgba(0,0,0,0.06);
  --shadow-md: 0 4px 16px rgba(0,0,0,0.08);
  --shadow-lg: 0 12px 40px rgba(0,0,0,0.10);

  /* Glass */
  --glass-bg: rgba(255,255,255,0.75);
  --glass-border: 1px solid rgba(0,0,0,0.06);
  --glass-blur: blur(20px);
}

/* ═══════════════════════════════════════════════════════
   SHARED TOKENS (same in both themes)
   ═══════════════════════════════════════════════════════ */
:root {
  /* Brand — teal at two temperatures */
  --brand-ambient: #3A7C9D;          /* Logo, search glow, subtle brand presence */
  --brand-interactive: #2B8FB3;      /* Buttons, links, focus rings, CTAs */
  --brand-hover: #239AB8;            /* Interactive hover */
  --brand-muted: rgba(43,143,179,0.10); /* Ghost button hover bg */

  /* Status — semantic, universal */
  --status-critical: #E5484D;
  --status-critical-bg: rgba(229,72,77,0.10);
  --status-warning: #F5A623;
  --status-warning-bg: rgba(245,166,35,0.10);
  --status-success: #30A46C;
  --status-success-bg: rgba(48,164,108,0.10);
  --status-neutral: #71717A;
  --status-neutral-bg: rgba(113,113,122,0.10);

  /* Typography */
  --font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', sans-serif;
  --font-mono: 'SF Mono', 'Fira Code', monospace;

  /* Spacing (4px base) */
  --space-1: 4px;   --space-2: 8px;   --space-3: 12px;
  --space-4: 16px;  --space-5: 20px;  --space-6: 24px;
  --space-8: 32px;  --space-10: 40px; --space-12: 48px;
  --space-16: 64px; --space-20: 80px;

  /* Radius */
  --radius-sm: 8px;        /* Buttons, inputs, pills */
  --radius-md: 12px;       /* Cards, sections */
  --radius-lg: 16px;       /* Modals, search bar */
  --radius-xl: 24px;       /* Large containers */
  --radius-full: 9999px;   /* Status dots, avatars */

  /* Transitions */
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
  --duration-fast: 120ms;
  --duration-normal: 200ms;
  --duration-slow: 300ms;

  /* Z-index */
  --z-sticky: 10;
  --z-header: 20;
  --z-sidebar: 30;
  --z-modal: 40;
  --z-search: 50;
  --z-toast: 60;
}
```

### Tailwind Config Extension

```js
// tailwind.config.js extend
colors: {
  brand: { ambient: 'var(--brand-ambient)', interactive: 'var(--brand-interactive)', hover: 'var(--brand-hover)' },
  status: { critical: 'var(--status-critical)', warning: 'var(--status-warning)', success: 'var(--status-success)', neutral: 'var(--status-neutral)' },
  surface: { base: 'var(--surface-base)', primary: 'var(--surface-primary)', elevated: 'var(--surface-elevated)', hover: 'var(--surface-hover)', active: 'var(--surface-active)', border: 'var(--surface-border)' },
  txt: { primary: 'var(--text-primary)', secondary: 'var(--text-secondary)', tertiary: 'var(--text-tertiary)', disabled: 'var(--text-disabled)' },
}
```

---

## LENS STRUCTURE

Every lens follows this exact layout. No variations.

```
┌────────────────────────────────────────────────────────┐
│  [← Back]   ENTITY TYPE                    [× Close]  │  Fixed header
├────────────────────────────────────────────────────────┤
│                                                        │
│  ● Status    ○ Priority                                │
│                                                        │
│  Entity Title                                          │  Largest text on screen
│  Subtitle / description line                           │
│                                                        │
│  Created: Jan 23   ·  Parts: 0   ·  Equipment: DG1    │  Vital signs (facts only)
│                                                        │
│────────────────────────────────────────────────────────│
│                                                        │
│  📝 Notes (3)                          [+ Add Note]   │  Sticky section header
│  ─────────────────────────────────────────────────     │
│  Note content rows...                                  │
│                                                        │
│  ⚙️ Parts Used                          [+ Add Part]   │  Sticky section header
│  ─────────────────────────────────────────────────     │
│  Part cards / empty state...                           │
│                                                        │
│  📎 Attachments (2)                  [+ Add File]     │  Sticky section header
│  ─────────────────────────────────────────────────     │
│  Media renders inline. Docs render as preview cards.   │
│                                                        │
│  🕐 History                                            │  Sticky section header
│  ─────────────────────────────────────────────────     │
│  Ledger entries, most recent first                     │
│                                                        │
└────────────────────────────────────────────────────────┘
```

### Vital Signs = Database Facts Only

- "0 Parts linked" ✅ (fact)
- "This work order is blocked" ❌ (opinion)
- "Expired 12 days ago" ✅ (fact)
- "Needs urgent attention" ❌ (editorial)

The user decides what matters. We surface what exists.

### Sticky Section Headers

Every section header sticks on scroll. When pinned:
- Background shifts to `--surface-elevated`
- Subtle bottom border appears
- Action button remains visible and clickable
- This IS the navigation system. No additional nav UI needed.

### Files in Lenses

- **Media** (.png, .jpg, .mp4, .gif, .heic, .mov) → Render inline, actual preview, max-height 240px
- **Documents** (.pdf, .docx) → Preview card only: `[📄 icon] filename.ext · 2.4 MB`. Click opens Document lens full-screen.
- Always signed URLs with JWT. Never raw paths. Always verify file exists. Always respect RLS.

### Cross-Lens Navigation

Entity names that reference other entities are clickable teal links. Clicking:
1. Glass transition (300ms) to new lens
2. Back/Forward buttons appear in header
3. Ledger logs both "departed from X" and "opened Y"
4. Navigation stack cached for session

---

## HARD RULES

### ALWAYS
- Semantic tokens for all colors. Zero raw hex in components.
- 4px spacing grid. No magic numbers.
- 44px minimum touch targets.
- Full-screen lenses. Never sidebars or cards for entity views.
- Verify DB tables with SQL before assuming schema.
- Test values not just status codes. 200 OK ≠ passing test.
- Log every navigation/action to ledger.
- Use sub-agents via GSD for parallelizable work.
- /compact at 60% context. No exceptions.

### NEVER
- Create new routes or URLs. One URL: `app.celeste7.ai`
- Invent actions backend didn't return.
- Render UUIDs, yacht_ids, internal keys to users.
- Auto-send emails. User reviews, signs, then sends.
- Preload Show Related data. Fetch only on user click.
- Render "Email integration is off." Dead code. Remove everywhere.
- Use db_ground_truth.md as gospel. Always verify live DB.
- Guess table names. Query first.
- Work sequentially when sub-agents can parallelize.
- Continue past 70% context without compacting.

---

## TEST ORDER (NON-NEGOTIABLE)

```
1. DB constraints → RLS, FK, RPC, RBAC
2. Search filter restrictions per table
3. SQL insert/mutate/update (backend raw)
4. Python API tests per role (crew, HOD, captain)
5. TypeScript/Vite frontend rendering
6. Playwright E2E per role per journey
7. DB verify: ledger entries logged (backend)
8. Visual verify: ledger visible in UI (Playwright screenshot)
```

Each layer depends on the previous. Skip none.

---

## PROGRESS TRACKING

File: `.claude/PROGRESS_LOG.md`

```
[2026-02-17T10:30:00Z] | Phase 0 | Tokens | Task: implement CSS tokens | DONE | Evidence: tokens.css committed, vite build passing
[2026-02-17T11:00:00Z] | Phase 1 | Work Order | Task: vital signs row | DONE | Evidence: screenshot_wo_vitals.png, API test 3/3 pass
```

Update after EVERY completed task. Evidence = screenshot, test output, or DB query. "It works" is not evidence.

---

## PLUGIN REFERENCE

| Plugin | Use | Priority |
|--------|-----|----------|
| `playwright` | E2E tests, visual verification, screenshots | Every lens completion |
| `supabase` | Table discovery, RLS checks, data queries | Before any data work |
| `context7` | React/Next.js/Tailwind current API docs | Before implementing patterns |
| `frontend-design` | Design guidance for new components | Before building UI |
| `code-review` | Post-completion review | After each lens |
| `vercel` | Deploy, staging verify, logs | After major milestones |
| `gsd` | Phase planning + parallel sub-agents | ALL work orchestration |
