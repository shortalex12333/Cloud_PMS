# Cloud PMS — Full UX Audit
**Date:** 2026-04-08
**Auditor:** FRONTEND02 (Team 4)
**Scope:** Every screen, visual consistency, loading/empty/error states, navigation, responsive, overview vs single-vessel
**Mode:** Audit only — no code changes

---

## 1. LOADING STATES

### 1.1 Bootstrap / Cold Start — HIGH
**Where:** Login → authenticated shell transition
**Issue:** Render free tier takes 30s+ to wake. User sees "Loading your account..." spinner with no progress indicator, no retry button, and no timeout message. Bootstrap can fail 4x silently before succeeding.
**What user sees:** Teal `Loader2` spinner + "Loading your account..." text, indefinitely.
**Files:** `apps/web/src/app/login/LoginContent.tsx:311-313`

### 1.2 Bootstrap Error State — MEDIUM
**Where:** Login page when bootstrap fails
**Issue:** Error state shows "Connecting to server... Retrying..." with a spinner but gives no indication of attempt count, no manual retry button, and no timeout. User has no way to know if the system is actually retrying or stuck.
**Files:** `LoginContent.tsx:416-418`

### 1.3 Entity List Loading Spinner Inconsistency — LOW
**Where:** Entity list pages (all 12 domains)
**Issue:** EntityList spinner uses `borderTopColor: 'var(--txt)'` while EntityLensPage spinner uses `borderTopColor: 'var(--mark)'`. Two different visual treatments for the same concept.
**Files:** `features/entity-list/components/EntityList.tsx:141` vs `components/lens/EntityLensPage.tsx:41`

### 1.4 No Loading State for Sidebar Counts — LOW
**Where:** Sidebar domain items
**Issue:** Count badges show nothing while loading (they just don't appear). No skeleton/shimmer to indicate data is being fetched. First render has no counts, then they pop in.
**Files:** `components/shell/Sidebar.tsx:295-307`

### 1.5 VesselSurface Has No Loading State — MEDIUM
**Where:** Home screen (Vessel Surface)
**Issue:** `useVesselSurface()` hook provides `data` but VesselSurface.tsx does not check for a loading state. If the endpoint is slow, the user sees an empty grid with no cards (all arrays default to `[]`). No spinner, no skeleton.
**Files:** `components/shell/VesselSurface.tsx:100-101`

---

## 2. EMPTY STATES

### 2.1 VesselSurface Empty Vessel — MEDIUM
**Where:** Surface cards when a vessel has zero data (e.g., M/Y Artemis)
**Issue:** Cards render with headers but completely empty bodies — no rows, no message. The "View all 0 work orders" footer is misleading. Should show a gentle empty message like "No open work orders" inside the card.
**Files:** `VesselSurface.tsx:214-230` (work orders map over empty array)

### 2.2 Recent Activity Empty — LOW
**Where:** VesselSurface "Recent Activity" card
**Issue:** When there's no activity, the card renders with just the header and nothing else. No "No recent activity" message.
**Files:** `VesselSurface.tsx:319-350`

### 2.3 Certificates Expiring Empty — LOW
**Where:** VesselSurface "Certificates" card
**Issue:** Same as above — empty card body with no message when no certificates are expiring.
**Files:** `VesselSurface.tsx:352-371`

### 2.4 Search Results Empty State — LOW
**Where:** Subbar Tier 2 search across all domains
**Issue:** Subbar search input fires `onSearch` but there's no empty state for "no matches found" from the scoped search. The EntityList empty state only covers the base "no records" case.
**Files:** `components/shell/Subbar.tsx:230-243`

---

## 3. ERROR STATES

### 3.1 Entity List Error — Minimal Styling — MEDIUM
**Where:** Any domain list page when API fails
**Issue:** Error state is a single line: `<p className="text-red-400">Failed to load items</p>`. No retry button, no icon, no guidance. Uses hardcoded Tailwind `text-red-400` instead of design token `var(--red)`.
**Files:** `features/entity-list/components/EntityList.tsx:149-154`

### 3.2 No Global Error Boundary — MEDIUM
**Where:** Entire app
**Issue:** No React error boundary wrapping the app shell. If a component throws, the entire app crashes to a white screen. Next.js `error.tsx` files would catch route-level errors but none were found in the app directory.
**Files:** No `error.tsx` found in `apps/web/src/app/`

### 3.3 VesselSurface API Failure — MEDIUM
**Where:** Home screen
**Issue:** If `useVesselSurface()` errors, there's no error handling — same as the loading issue. The hook returns undefined data and the surface renders empty cards with no error indication.
**Files:** `VesselSurface.tsx:100`

---

## 4. NAVIGATION FLOW

### 4.1 "Forgot?" Link Does Nothing — LOW
**Where:** Login page, password field
**Issue:** "Forgot?" link has `onClick={(e) => { e.preventDefault(); }}` — it's a dead link with no feedback. Should either be removed or show a "contact admin" message.
**Files:** `LoginContent.tsx:525-526`

### 4.2 Subbar Primary Action Not Wired — HIGH
**Where:** All domain list pages
**Issue:** The "Create Work Order", "Log Fault", etc. buttons in the Subbar pass `onPrimaryAction` but AppShell never provides this prop. Clicking does nothing — no feedback, no error, just silent failure on a prominent CTA button.
**Files:** `AppShell.tsx:224-230` (no onPrimaryAction passed), `Subbar.tsx:314-336`

### 4.3 Mobile Navigation — No Hamburger Menu — HIGH
**Where:** Mobile breakpoint (<640px)
**Issue:** Sidebar is hidden on mobile (`showSidebar = breakpoint !== 'mobile'`), but there's no hamburger drawer or alternative navigation. Users on mobile have no way to navigate between domains except through the topbar menu (which only has Command Center, Settings, Sign Out — no domain links).
**Files:** `AppShell.tsx:189-190`, `Sidebar.tsx` (no mobile drawer)

### 4.4 Activity Row Click Goes Nowhere — LOW
**Where:** VesselSurface "Recent Activity" card
**Issue:** Activity rows have `cursor: 'pointer'` and hover state but no `onClick` handler. Users expect clicking to navigate to the referenced entity.
**Files:** `VesselSurface.tsx:325-349`

### 4.5 Vessel Surface Quick Actions Route Incorrectly — LOW
**Where:** "Create Work Order" and "Log Fault" quick action buttons
**Issue:** These navigate to the list page (`/work-orders`, `/faults`) but don't open any create modal. The user lands on the list with no indication they wanted to create something.
**Files:** `VesselSurface.tsx:231-233, 261-263`

---

## 5. RESPONSIVE / MOBILE

### 5.1 No Mobile Navigation (Critical) — HIGH
See §4.3 above. Mobile users are stranded with no domain navigation.

### 5.2 Subbar Overflow on Narrow Screens — MEDIUM
**Where:** Tablet and narrow laptop
**Issue:** Filter chips have `overflowX: 'auto'` with `scrollbarWidth: 'none'` — horizontal scroll with no scrollbar. Users don't know there are more chips off-screen. No scroll indicators or fade effect.
**Files:** `Subbar.tsx:248-258`

### 5.3 Related Drawer Overlaps Content on Tablet — MEDIUM
**Where:** Entity lens detail page
**Issue:** Related drawer is fixed at `width: 600px` with `maxWidth: 100vw`. On tablet (640-899px), it covers the entire viewport with no way to see the entity behind it. Should be a slide-over that pushes content or uses a smaller width.
**Files:** `EntityLensPage.tsx:286-289`

### 5.4 VesselSurface Grid at Mobile — LOW
**Where:** Home screen on mobile
**Issue:** Work Orders card has `span={2}` (gridColumn: span 2) but on mobile the grid is `1fr` single column, so `span 2` has no effect. This is harmless but the span logic could be cleaner.
**Files:** `VesselSurface.tsx:102, 206`

### 5.5 Settings Modal Fixed Dimensions — LOW
**Where:** Settings modal
**Issue:** Settings modal is designed as 547x483px fixed. On mobile this will overflow or require scroll. No responsive override detected.
**Files:** `components/settings/Settings.tsx` (spec comment line 8)

---

## 6. OVERVIEW MODE vs SINGLE-VESSEL

### 6.1 No Visual Indicator for Active Mode — MEDIUM
**Where:** Topbar vessel dropdown
**Issue:** When "All Vessels" is selected, the vessel name in the topbar shows the name of the first vessel (or default), not "All Vessels". Users can't tell at a glance whether they're in overview or single-vessel mode without opening the dropdown.
**Files:** `Topbar.tsx:77, 417` — `vessel.vesselName` is displayed, which may not say "All Vessels"

### 6.2 Surface Cards Don't Show Vessel Source in Overview — MEDIUM
**Where:** VesselSurface in "All Vessels" mode
**Issue:** When viewing all vessels, surface rows from different vessels are mixed together but there's no vessel name label on each row. Users can't tell which vessel a work order or fault belongs to without clicking into it.
**Files:** `VesselSurface.tsx:214-224` (no vesselName rendered on rows)

### 6.3 Sidebar Counts Not Aggregated in Overview — LOW
**Where:** Sidebar domain counts
**Issue:** In "All Vessels" mode, sidebar counts should aggregate across all vessels. Currently unclear if `useSidebarCounts()` handles this — if it only returns single-vessel counts, the numbers are misleading.
**Files:** `AppShell.tsx:121`, `hooks.ts` (useSidebarCounts implementation)

---

## 7. VISUAL CONSISTENCY

### 7.1 Hardcoded Colors in Button Tokens — MEDIUM
**Where:** tokens.css button class definitions
**Issue:** `.btn-primary`, `.btn-secondary`, `.btn-ghost`, `.btn-danger` all use hardcoded hex values instead of CSS custom properties. This means theme switching may not correctly update button colors.
**Examples:**
- `.btn-primary { background: #111111; }` (should use a token)
- `.btn-ghost:hover { background: #eeeeee; }` (should use `var(--surface-hover)`)
- `.btn-danger { background: #dc2626; }` (should use `var(--red)`)
**Files:** `styles/tokens.css` (button section)

### 7.2 Inline RGBA in Component Files — MEDIUM
**Where:** Settings.tsx, LedgerPanel.tsx, QueryInterpretation.tsx, LoginContent.tsx
**Issue:** Multiple components use inline `rgba()` values and hardcoded hex colors instead of design tokens. Violates the token-first design system rule.
**Examples:**
- `Settings.tsx`: `rgba(255,255,255,0.05)`, `rgba(90,171,204,0.28)`
- `LoginContent.tsx`: `rgba(58,124,157,0.50)`, `rgba(30,90,130,0.38)` in backdrop orbs
- `LoginContent.tsx:129`: `color: 'var(--mark, #5AABCC)'` fallback pattern (acceptable but inconsistent)
**Files:** Multiple — see §7.2 locations above

### 7.3 ReportFaultModal Uses Tailwind Palette — LOW
**Where:** Report Fault modal severity options
**Issue:** Uses `bg-green-500`, `bg-yellow-500`, `bg-orange-500`, `bg-red-500` (Tailwind defaults) instead of design tokens (`var(--green)`, `var(--amber)`, `var(--red)`). Won't respect theme changes.
**Files:** `components/modals/ReportFaultModal.tsx`

### 7.4 Login Topbar Height Mismatch — LOW
**Where:** Login page topbar
**Issue:** Login topbar is 40px (`TOPBAR` style), but main app topbar is 48px. Subtle but noticeable if the user pays attention during the login→app transition.
**Files:** `LoginContent.tsx:44-55` vs `AppShell.tsx:201`

### 7.5 Brand Name Inconsistent Size — LOW
**Where:** Login page vs main app topbar
**Issue:** "CELESTE" brand text is 9px in the main topbar but 10px on the login topbar. Slight inconsistency.
**Files:** `Topbar.tsx:114` (9px) vs `LoginContent.tsx:443-444` (10px)

---

## 8. INTERACTION ROUGH EDGES

### 8.1 Hover States via Inline JS — LOW
**Where:** Throughout all shell components
**Issue:** All hover states use `onMouseEnter`/`onMouseLeave` inline style manipulation instead of CSS `:hover`. This means hover doesn't work on touch devices and creates unnecessary re-renders. Acceptable for the glass design system but worth noting.
**Files:** Topbar.tsx, Sidebar.tsx, VesselSurface.tsx, Subbar.tsx, EntityLensPage.tsx — pervasive pattern

### 8.2 No Focus Visible on Shell Navigation — MEDIUM
**Where:** Sidebar items, topbar menu items, vessel dropdown
**Issue:** No `:focus-visible` outlines on any shell navigation elements. Keyboard-only users can't see which element is focused. All sidebar items, dropdown items, and menu buttons lack focus ring styling.
**Files:** `Sidebar.tsx` (DomainItem, SurfaceItem), `Topbar.tsx` (VesselDropdown, menu buttons)

### 8.3 Dropdown Keyboard Navigation Missing — MEDIUM
**Where:** Topbar menu dropdown, vessel dropdown
**Issue:** Dropdowns close on outside click but have no keyboard support — no Escape to close, no arrow key navigation, no Enter to select. Only mouse interaction works.
**Files:** `Topbar.tsx:62-69` (menu), `Topbar.tsx:388-395` (vessel dropdown)

### 8.4 Sort Dropdown Styling — LOW
**Where:** Subbar sort control
**Issue:** Native `<select>` element with minimal styling. Looks different across browsers, especially Safari. Doesn't match the glass design language of the rest of the subbar.
**Files:** `Subbar.tsx:291-310`

---

## 9. ACCESSIBILITY

### 9.1 Missing ARIA Labels — MEDIUM
**Where:** Various interactive elements
**Issues:**
- Sidebar domain items have no `aria-label` or `role="navigation"` (the `<nav>` tag is correct but items lack roles)
- Subbar filter chips have no `aria-pressed` state
- VesselSurface cards and rows have no `role="button"` despite being clickable divs
- Activity rows are clickable divs with no keyboard accessibility
**Files:** `Sidebar.tsx`, `Subbar.tsx`, `VesselSurface.tsx`

### 9.2 Color-Only Status Indicators — LOW
**Where:** Sidebar severity badges, VesselSurface accent bars
**Issue:** Severity is communicated through color only (red/amber/green accent bars, count colors). The StatusPill component adds text labels which is good, but the sidebar count color and left accent bars rely on color alone.
**Files:** `Sidebar.tsx:236-243`, `VesselSurface.tsx:494-498`

---

## 10. MISCELLANEOUS

### 10.1 Topbar z-index: 100, Subbar z-index: 90, Dropdown z-index: 200 — LOW
**Where:** Shell header stack
**Issue:** Z-index values are not tokenized. Currently non-conflicting but fragile. The Related Drawer also uses `z-index: 100`, same as the topbar — could conflict.
**Files:** `Topbar.tsx:108`, `Subbar.tsx:163`, `Topbar.tsx:294,438`, `EntityLensPage.tsx:290`

### 10.2 Console Logging in Production — LOW
**Where:** Login page
**Issue:** Multiple `console.log('[LoginPage]...')` statements will appear in production browser console. Should be behind a debug flag.
**Files:** `LoginContent.tsx:244-275`

### 10.3 Version Stamp Hardcoded — LOW
**Where:** Login page footer
**Issue:** `v1.0.0` is hardcoded. Not automatically synced with package.json or build version.
**Files:** `LoginContent.tsx:599`

---

## SEVERITY SUMMARY

| Severity | Count | Items |
|----------|-------|-------|
| **HIGH** | 3 | §1.1 Bootstrap cold start, §4.2 Primary action not wired, §4.3/5.1 No mobile navigation |
| **MEDIUM** | 13 | §1.2 Bootstrap error, §1.5 Surface no loading, §2.1 Empty vessel cards, §3.1 List error styling, §3.2 No error boundary, §3.3 Surface error, §5.2 Chip overflow, §5.3 Related drawer tablet, §6.1 No mode indicator, §6.2 No vessel source label, §7.1 Hardcoded button colors, §7.2 Inline RGBA, §8.2-8.3 Keyboard/focus |
| **LOW** | 16 | §1.3 Spinner inconsistency, §1.4 Sidebar count loading, §2.2-2.4 Empty states, §4.1 Forgot link, §4.4-4.5 Click targets, §5.4-5.5 Mobile grid/settings, §6.3 Sidebar aggregation, §7.3-7.5 Visual nits, §8.1 Hover via JS, §8.4 Sort dropdown, §9.1-9.2 A11y, §10.1-10.3 Misc |

---

**Total findings: 32**
**Recommendation:** Address the 3 HIGH items first (mobile nav, primary action wiring, cold start UX). Then batch the MEDIUM items into a polish sprint.
