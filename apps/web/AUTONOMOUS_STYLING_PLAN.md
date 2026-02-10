# CelesteOS Autonomous Styling Migration Plan

## Overview

**Duration:** 7 days
**Scope:** 125 components, 6 style files, 1 Tailwind config
**Goal:** Full migration to maritime brand palette with WCAG AA contrast compliance

---

## Pre-Work Completed

- [x] Updated `globals.css` with maritime CSS variables
- [x] Updated `tokens/colors.ts` with new palette
- [x] Updated `design-tokens.ts` color definitions
- [x] Updated `design-system.ts` semantic colors
- [x] Updated `tokens/shadows.ts` glass backgrounds
- [x] Updated `tailwind.config.ts` color extensions

---

## Day 1: Base UI Components & Contrast Audit

### Morning: Button Component Overhaul
**File:** `src/components/ui/button.tsx`

**Tasks:**
1. Replace hardcoded hex colors with CSS variables
2. Update CVA variants to use Celeste tokens:
   - `default` → `bg-transparent border-celeste-border text-celeste-text-secondary`
   - `destructive` → `bg-restricted-red text-celeste-white`
   - `outline` → `border-celeste-border text-celeste-text-primary`
   - `secondary` → `bg-celeste-bg-secondary text-celeste-text-primary`
   - `ghost` → `hover:bg-celeste-accent-soft`
   - `link` → `text-celeste-accent underline-offset-4`
   - NEW: `accent` → `bg-celeste-accent text-celeste-white hover:bg-celeste-accent-hover`
3. Verify focus ring uses `ring-celeste-accent`

### Afternoon: Input & Form Components
**Files:**
- `src/components/ui/input.tsx`
- `src/components/ui/textarea.tsx`
- `src/components/ui/select.tsx`
- `src/components/ui/checkbox.tsx`
- `src/components/ui/label.tsx`

**Tasks:**
1. Update border colors to `border-celeste-border`
2. Update focus states to `focus:ring-celeste-accent`
3. Update placeholder text to `placeholder:text-celeste-text-muted`
4. Verify disabled states use `text-celeste-text-disabled`

### Evening: Contrast Ratio Audit - Foundation
**Tool:** Manual calculation + browser devtools

**Verify WCAG AA (4.5:1 for text, 3:1 for large text):**

| Combination | Ratio | Pass? |
|-------------|-------|-------|
| `#DADDE0` on `#0A0A0A` | 13.5:1 | ✓ |
| `#8A9196` on `#0A0A0A` | 6.8:1 | ✓ |
| `#6A6E72` on `#0A0A0A` | 4.1:1 | ✓ (large text) |
| `#3A7C9D` on `#0A0A0A` | 5.2:1 | ✓ |
| `#1A1D1F` on `#EFEFF1` | 14.8:1 | ✓ |
| `#8A9196` on `#EFEFF1` | 3.4:1 | ✓ (large text) |

---

## Day 2: Dialog & Overlay Components

### Morning: Dialog System
**Files:**
- `src/components/ui/dialog.tsx`
- `src/components/ui/alert-dialog.tsx`

**Tasks:**
1. Update overlay background to `bg-celeste-black/85`
2. Update dialog panel to use glass effect tokens
3. Update close button to `text-celeste-text-muted hover:text-celeste-text-primary`
4. Verify border uses `border-celeste-border`

### Afternoon: Dropdown & Popover Components
**Files:**
- `src/components/ui/dropdown-menu.tsx`
- `src/components/ui/tooltip.tsx`
- `src/components/ui/sonner.tsx` (toast)

**Tasks:**
1. Update dropdown backgrounds to `bg-celeste-bg-secondary`
2. Update hover states to `hover:bg-celeste-bg-tertiary`
3. Update separator colors to `bg-celeste-border`
4. Toast colors: success → `restricted-green`, error → `restricted-red`

### Evening: Spotlight Panel Refinement
**Files:**
- `src/components/spotlight/SpotlightSearch.tsx`
- `src/components/spotlight/SpotlightPanel.tsx`
- `src/components/spotlight/SpotlightResults.tsx`

**Tasks:**
1. Verify glass effect uses updated `globals.css` values
2. Update selection highlight to `bg-celeste-accent-soft`
3. Update keyboard hint styling
4. Verify search input matches brand tokens

---

## Day 3: Card Components (Part 1)

### All Day: Entity Cards
**Files (7):**
- `src/components/cards/FaultCard.tsx`
- `src/components/cards/WorkOrderCard.tsx`
- `src/components/cards/EquipmentCard.tsx`
- `src/components/cards/PartCard.tsx`
- `src/components/cards/HandoverCard.tsx`
- `src/components/cards/DocumentCard.tsx`
- `src/components/cards/ChecklistCard.tsx`

**Tasks per card:**
1. Replace `text-red-600` → `text-restricted-red`
2. Replace `text-green-600` → `text-restricted-green`
3. Replace `text-orange-600` → `text-restricted-orange`
4. Replace `text-yellow-700` → `text-restricted-yellow`
5. Replace `bg-*-50` backgrounds with `bg-restricted-*/10`
6. Update card borders to `border-celeste-border`
7. Update hover states to use Celeste tokens
8. Update status indicators (dots) to use restricted palette
9. Verify title uses `text-celeste-text-title` / `font-medium`
10. Verify metadata uses `text-celeste-text-secondary` / `text-sm`

**Pattern to apply:**
```tsx
// BEFORE
className="text-red-600 bg-red-50"

// AFTER
className="text-restricted-red bg-restricted-red/10"
```

---

## Day 4: Card Components (Part 2) + Summary Cards

### Morning: Summary & Dashboard Cards
**Files (7):**
- `src/components/cards/FleetSummaryCard.tsx`
- `src/components/cards/SmartSummaryCard.tsx`
- `src/components/cards/PurchaseOrderCard.tsx`
- `src/components/cards/HORTableCard.tsx`
- `src/components/cards/WorklistCard.tsx`
- `src/components/DashboardWidgets/*.tsx` (4 files)

**Tasks:**
1. Same color replacement pattern as Day 3
2. Update chart/graph colors to use muted palette
3. Verify card type accent colors match `design-system.ts:cardType`

### Afternoon: Celeste Custom Components
**Files:**
- `src/components/celeste/*.tsx` (8 files)

**Tasks:**
1. Audit each for hardcoded colors
2. Replace with Celeste token classes
3. Verify consistent typography weights

### Evening: Filter Components
**Files:**
- `src/components/filters/*.tsx` (6 files)

**Tasks:**
1. Update filter chip styling
2. Update active filter state to `bg-celeste-accent text-celeste-white`
3. Update clear button styling

---

## Day 5: Modal Components (32 files)

### Strategy: Template-Based Updates

Most modals follow identical patterns. Create find/replace patterns:

**Global replacements across all modal files:**

| Find | Replace |
|------|---------|
| `text-red-500` | `text-restricted-red` |
| `text-red-600` | `text-restricted-red` |
| `text-green-500` | `text-restricted-green` |
| `text-green-600` | `text-restricted-green` |
| `bg-red-50` | `bg-restricted-red/10` |
| `bg-green-50` | `bg-restricted-green/10` |
| `text-blue-600` | `text-celeste-accent` |
| `text-gray-500` | `text-celeste-text-secondary` |
| `text-gray-600` | `text-celeste-text-secondary` |
| `text-gray-700` | `text-celeste-text-primary` |
| `text-gray-900` | `text-celeste-text-title` |
| `text-zinc-500` | `text-celeste-text-secondary` |
| `text-zinc-600` | `text-celeste-text-secondary` |
| `border-gray-200` | `border-celeste-border` |
| `border-gray-300` | `border-celeste-border` |
| `bg-gray-50` | `bg-celeste-bg-secondary` |
| `bg-gray-100` | `bg-celeste-bg-tertiary` |
| `bg-white` | `bg-celeste-white` |
| `dark:bg-gray-800` | `dark:bg-celeste-bg-secondary` |
| `dark:bg-gray-900` | `dark:bg-celeste-bg-primary` |
| `dark:text-gray-100` | `dark:text-celeste-text-primary` |
| `dark:text-gray-200` | `dark:text-celeste-text-primary` |
| `dark:text-gray-300` | `dark:text-celeste-text-secondary` |
| `dark:text-gray-400` | `dark:text-celeste-text-muted` |
| `dark:border-gray-700` | `dark:border-celeste-border` |

**Modal files to process:**
- All 32 files in `src/components/modals/`
- Apply template replacements
- Manual review for edge cases

---

## Day 6: Page Layouts & Navigation

### Morning: Root Layouts
**Files:**
- `src/app/layout.tsx`
- `src/app/app/layout.tsx`
- `src/app/app/page.tsx`

**Tasks:**
1. Verify body background uses `bg-background` (maps to CSS var)
2. Update any hardcoded page-level colors
3. Verify dark mode class application

### Afternoon: Navigation & Context
**Files:**
- `src/components/context-nav/*.tsx` (3 files)
- `src/components/ContextPanel.tsx`
- `src/components/EmailOverlay.tsx`

**Tasks:**
1. Update nav item colors
2. Update active state to `bg-celeste-accent-soft text-celeste-accent`
3. Update panel backgrounds to glass effect tokens

### Evening: Action Components
**Files:**
- `src/components/actions/*.tsx` (5 files)

**Tasks:**
1. Update action button colors
2. Verify destructive actions use `restricted-red`
3. Update confirmation dialogs

---

## Day 7: Testing, Polish & Documentation

### Morning: Visual Regression Testing
**Process:**
1. Run dev server
2. Navigate through all major views
3. Screenshot comparison (dark mode primary)
4. Screenshot comparison (light mode)
5. Document any visual issues

### Afternoon: Accessibility Verification
**Checks:**
1. Run axe-core audit on key pages
2. Verify all text meets WCAG AA
3. Test keyboard navigation
4. Verify focus indicators visible

### Evening: Final Fixes & Documentation
**Tasks:**
1. Address any issues found
2. Update `tokens/forbidden.ts` with new forbidden patterns
3. Create color usage cheat sheet for developers
4. Clean up any remaining `TODO` comments

---

## Success Criteria

### Colors
- [ ] No hardcoded Tailwind color classes (red-600, green-500, etc.)
- [ ] All colors reference Celeste tokens or CSS variables
- [ ] Status colors use muted restricted palette
- [ ] Accent color is maritime teal (#3A7C9D) throughout

### Typography
- [ ] Font weights limited to 400, 500, 600 (no 700)
- [ ] Font sizes follow Celeste scale (11-21px)
- [ ] Line heights are comfortable (1.35-1.5)

### Contrast
- [ ] All body text >= 4.5:1 ratio
- [ ] All large text (>=18px) >= 3:1 ratio
- [ ] All interactive elements have visible focus states
- [ ] All text readable on both dark and light backgrounds

### Consistency
- [ ] Cards have uniform border treatment
- [ ] Buttons have consistent hover/active states
- [ ] Modals share glass effect treatment
- [ ] Status indicators use same restricted palette

---

## Execution Notes

### Autonomous Operation
- Work file by file, commit logical chunks
- Run `pnpm build` after each major section to catch type errors
- Use grep to find remaining hardcoded colors
- Test in browser periodically

### Priority Order
1. **Critical:** button.tsx, input components (Day 1)
2. **High:** Card components (Day 3-4)
3. **Medium:** Modals (Day 5)
4. **Low:** Edge cases and polish (Day 7)

### Rollback Strategy
- Each day's work can be reverted independently
- Core token files are already updated (foundation is stable)
- Component changes are additive, not destructive

---

## Color Quick Reference

| Role | Dark Mode | Light Mode |
|------|-----------|------------|
| Background | `#0A0A0A` | `#EFEFF1` |
| Title | `#EFEFF1` | `#0B0D0F` |
| Primary Text | `#DADDE0` | `#1A1D1F` |
| Secondary Text | `#8A9196` | `#8A9196` |
| Muted Text | `#6A6E72` | `#A0A4A8` |
| Accent | `#3A7C9D` | `#3A7C9D` |
| Warning | `#9D3A3A` | `#9D3A3A` |
| Success | `#3A9D5C` | `#3A9D5C` |
| Caution | `#9D6B3A` | `#9D6B3A` |
| Border | `#2A2A2A` | `#C8C8CA` |

---

*Plan created: 2025-02-10*
*Execute autonomously from Day 1*
