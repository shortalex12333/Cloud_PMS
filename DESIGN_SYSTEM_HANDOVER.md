# CelesteOS Design System Handover

**Date:** 2026-02-11
**From:** Claude Opus 4.5
**To:** Gemini (Frontend Design Engineer)
**Project:** CelesteOS - Maritime PMS (Planned Maintenance System)

---

## Executive Summary

You are inheriting a **7-day autonomous design migration** that is now ~85% complete. The goal: transform a generic SaaS-looking interface into an **authoritative maritime command system**.

The user is the **frontend UX designer** for a maritime company. Their primary complaint: *"We look too SaaS."*

Your role: Continue the work as a **250 IQ frontend colour/font/style engineer** who understands surfaces, authority, and brand values.

---

## Brand Philosophy

### The Core Doctrine

> "Colour is a signal of state, not personality."

CelesteOS is **infrastructure for yacht engineering operations**. It is not a consumer app. It does not need to be friendly, playful, or engaging in the traditional SaaS sense.

**Authority is communicated through:**
- Restraint, not decoration
- Structure, not color variance
- Precision, not personality
- Silence, not noise

### What We Are NOT

- Bright
- Playful
- Colorful
- Animated
- Glowing
- Gradient-heavy

### What We ARE

- Dark (night-first for maritime operations)
- Structural
- Silent
- Controlled
- Institutional
- Authoritative

---

## The Color System

### Foundation (80-90% of interface)

| Token | Hex | Usage |
|-------|-----|-------|
| `celeste-black` | `#0A0A0A` | Primary background |
| `celeste-bg-secondary` | `#121212` | Elevated surfaces |
| `celeste-bg-tertiary` | `#1A1A1A` | Cards, panels |
| `celeste-surface` | `#111316` | Elevated cards |
| `celeste-panel` | `#15191C` | Nested panels, modals |
| `celeste-divider` | `#1E2428` | Structural separators |

### Text Hierarchy

| Token | Hex | Usage |
|-------|-----|-------|
| `celeste-text-title` | `#EFEFF1` | Titles, headers |
| `celeste-text-primary` | `#DADDE0` | Body text |
| `celeste-text-secondary` | `#8A9196` | Secondary info |
| `celeste-text-muted` | `#6A6E72` | Tertiary, hints |
| `celeste-text-disabled` | `#4A4E52` | Disabled states |

### Accent (Precision Instrument - NOT decoration)

| Token | Value | Usage |
|-------|-------|-------|
| `celeste-accent` | `#3A7C9D` | Primary action, selection, verified state |
| `celeste-accent-hover` | `#327189` | Hover on primary actions ONLY |
| `celeste-accent-muted` | `rgba(58,124,157,0.7)` | Focus rings |
| `celeste-accent-subtle` | `rgba(58,124,157,0.2)` | Selected state backgrounds |
| `celeste-accent-line` | `rgba(58,124,157,0.1)` | Dividers, borders |

**CRITICAL RULE:** Blue (`celeste-accent`) appears ONLY when:
1. A user **selects** something
2. A state is **verified**
3. A **primary action** is possible
4. A **live system focus** is active

NOT for icons. NOT for decorative hover. NOT for casual links.

### Restricted Functional Colors (Specific contexts ONLY)

| Token | Hex | Usage |
|-------|-----|-------|
| `restricted-red` | `#9D3A3A` | Faults, destructive actions, errors |
| `restricted-orange` | `#9D6B3A` | Inspection warnings |
| `restricted-yellow` | `#9D8A3A` | Time-sensitive advisories |
| `restricted-green` | `#3A9D5C` | Confirmed completion ONLY |

These are **muted, dignified** versions - not saturated consumer colors.

---

## Technical Architecture

### File Locations

| File | Purpose |
|------|---------|
| `/apps/web/tailwind.config.ts` | Tailwind color definitions |
| `/apps/web/src/styles/globals.css` | CSS variables, base styles |
| `/apps/web/src/app/layout.tsx` | Root layout (has `dark` class) |

### How Colors Are Defined

**Two systems in parallel:**

1. **Tailwind Config** (`tailwind.config.ts`)
   - Direct hex values: `'celeste-accent': '#3A7C9D'`
   - Used via classes: `bg-celeste-accent`, `text-celeste-accent`

2. **CSS Variables** (`globals.css`)
   - HSL format for shadcn compatibility: `--primary: 196 46% 42%`
   - Direct hex for custom tokens: `--celeste-accent: #3A7C9D`

### Dark Mode

- Applied via `className="dark"` on `<html>` element in `layout.tsx`
- CSS variables switch in `.dark { }` block in `globals.css`
- This is a **night-first** system - dark mode is primary

---

## Work Completed

### PRs Merged

| PR | Description |
|----|-------------|
| #252 | Replace legacy gray-* colors with Celeste maritime tokens (53 files) |
| #257 | Replace Tailwind blue-* with hierarchical Celeste accent system (56 files) |
| #258 | Sync CSS variables with Tailwind tonal accent hierarchy |
| #259 | Replace hardcoded #0a84ff iOS blue with celeste-accent (10 files) |

### What Was Fixed

1. **Gray palette migration** - All `gray-*` Tailwind classes → `celeste-*` tokens
2. **Blue palette migration** - All `blue-*` Tailwind classes → contextual `celeste-accent-*`
3. **Hex color migration** - All `#0a84ff` hardcoded colors → `celeste-accent`
4. **Tonal hierarchy** - Added accent variants (muted, subtle, line)
5. **Surface depth** - Added surface/panel/divider tokens

---

## Outstanding Work

### Known Issues

1. **Placeholder text overlay bug** - In SpotlightSearch, the animated placeholder may show through typed text (z-index/React state issue - needs investigation)

2. **Remaining zinc-* colors** - 21 files in `_archived/` still use `zinc-*` (low priority, archived code)

3. **Some hardcoded hex colors may remain** - Grep for:
   ```bash
   grep -r "#[0-9a-fA-F]\{6\}" apps/web/src --include="*.tsx" | grep -v celeste
   ```

4. **Light mode not tested** - All work focused on dark mode (primary). Light mode variables exist but untested.

### Recommended Next Steps

1. **Audit remaining hex colors** - Search for any non-Celeste hex values
2. **Test visual consistency** - Run through all major screens
3. **Typography audit** - Fonts are defined but may not be loading (Eloquia Display/Text)
4. **Spacing consistency** - `celeste-spacing-*` tokens exist but may not be widely used
5. **Component library alignment** - Ensure shadcn components use Celeste tokens

---

## Development Workflow

### Building

```bash
cd apps/web
rm -rf .next          # Clear cache (IMPORTANT after color changes)
npm run build         # Production build
npm run dev           # Development server
```

### Verifying Changes

```bash
# Check for old blue classes
grep -r "blue-[0-9]" apps/web/src --include="*.tsx"

# Check for old gray classes
grep -r "gray-[0-9]" apps/web/src --include="*.tsx"

# Check for hardcoded iOS blue
grep -r "#0a84ff" apps/web/src --include="*.tsx"

# Check compiled CSS
grep -o "celeste-accent[a-z-]*" apps/web/.next/static/css/*.css | sort -u
```

### Git Workflow

Main branch is protected. Always:
1. Create feature branch: `git checkout -b fix/description`
2. Push branch: `git push -u origin fix/description`
3. Create PR: `gh pr create --title "..." --body "..."`
4. Merge with admin: `gh pr merge --merge --admin`

---

## Key Design Decisions Made

### 1. Tonal Variants Over New Colors

Instead of adding new accent colors, we use opacity variants of the single accent:
- 100% solid for primary actions
- 70% for focus rings
- 20% for selected backgrounds
- 10% for dividers

This creates hierarchy without adding personality.

### 2. Surface Depth Over Shadow

Instead of heavy shadows, we use subtle background color differences:
- `#0A0A0A` → `#111316` → `#15191C` → `#1E2428`

This creates layering without the "floating card" SaaS aesthetic.

### 3. Restraint Over Expression

Blue is used surgically. If something doesn't need to be blue, it shouldn't be. Decorative icons use `text-celeste-text-muted`, not accent colors.

---

## Files You'll Work With Most

```
apps/web/
├── tailwind.config.ts          # Color definitions
├── src/
│   ├── styles/globals.css      # CSS variables, base styles
│   ├── app/
│   │   ├── layout.tsx          # Root layout
│   │   ├── app/page.tsx        # Main app surface
│   │   └── login/              # Login screens
│   └── components/
│       ├── spotlight/          # Main search interface
│       ├── modals/             # All modal components
│       ├── cards/              # Card components
│       ├── email/              # Email components
│       └── ui/                 # Base UI components
```

---

## Contact Points

- **Codebase:** `/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS`
- **Repo:** `https://github.com/shortalex12333/Cloud_PMS`
- **Dev Server:** `http://localhost:3000` (or 3001/3002 if ports in use)

---

## Final Notes

The user values:
- **Speed** - Don't over-explain, just execute
- **Autonomy** - Make decisions, don't ask permission for obvious things
- **Authority** - The design should feel like infrastructure, not an app
- **Consistency** - One accent, one system, no exceptions

The most important thing: **Blue is a precision instrument, not an identity wash.**

Good luck.

— Claude Opus 4.5
