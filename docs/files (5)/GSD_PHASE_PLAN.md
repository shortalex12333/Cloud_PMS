# GSD Phase Plan — Frontend UX Workstream

> This is a SEPARATE workstream from the existing ROADMAP.md (Phases 1–13).
> These phases are prefixed FE- to avoid any collision.
> The existing roadmap covers backend/infrastructure. This covers frontend UX quality.
> Both workstreams run in parallel. Neither blocks the other unless explicitly noted.

---

## FE-Audit: Codebase Scan (MANDATORY — runs before FE-Phase 0)

**This is not optional. Hardcoded styles WILL silently override your new tokens.**

1. Read `CODEBASE_AUDIT.md`
2. Run the full audit script from CODEBASE_AUDIT.md (or run each scan manually)
3. Log ALL results to `.claude/audit/`
4. Categorize every finding (token replacement, dead code, duplicate, conflict)
5. Summarize in PROGRESS_LOG.md
6. Do NOT fix anything yet — fixes happen in FE-Phase 0

**FE-Audit exit criteria:**
- [ ] All 7 audit scans complete, results in `.claude/audit/`
- [ ] Hardcoded colors categorized with replacement tokens
- [ ] Inline styles categorized
- [ ] Duplicate files identified with consolidation plan
- [ ] CSS load order documented
- [ ] Z-index mapped to token scale
- [ ] Summary in PROGRESS_LOG.md

---

## FE-Phase 0: Design System Implementation
**BLOCKING — no other FE-Phase starts until this is done**

### Why this exists
The current codebase has no shared design tokens, no consistent component library, and raw hex values scattered across components. Every lens built on top of this foundation will inherit the inconsistency. Fix the foundation first.

### First: Apply audit fixes

Before building new components, fix what the audit found:
- Replace all hardcoded colors with semantic tokens
- Convert critical inline styles to Tailwind/token classes
- Delete duplicate files, consolidate to canonical locations
- Ensure `tokens.css` is the FIRST CSS import in app root
- Replace z-index chaos with token scale
- Remove all `!important` overrides (or document why each is necessary)

### Then: Build new components

### Sub-agent tasks (parallel via /gsd:execute-phase):

| Agent | Task | Done when |
|-------|------|-----------|
| A | Implement `tokens.css` with ALL CSS custom properties from CLAUDE.md (dark + light themes). Wire into app root layout. Verify both themes toggle. | `data-theme="dark"` and `data-theme="light"` both render correctly. No raw hex in any existing component. `vite build` passes. Screenshot evidence of both themes. |
| B | Extend `tailwind.config.js` with semantic token mappings from CLAUDE.md. Ensure all Tailwind utility classes resolve to CSS vars. | `bg-surface-primary`, `text-txt-secondary`, `text-brand-interactive` etc. all work. Build passes. |
| C | Build base components: `StatusPill`, `SectionContainer` (with sticky header logic), `EntityLink`, `GhostButton`, `PrimaryButton`, `DangerButton`, `IconButton` | Each component renders correctly in both themes. Verified via Playwright screenshot or dev server inspection. |
| D | Build: `VitalSignsRow` (generic, accepts array of `{label, value, color?, href?}`), `Toast`, `SignatureModal`, `FilePreviewCard`, `SkeletonLoader` | Each component renders in both themes. Toast auto-dismisses. Modal opens/closes. Skeleton animates. |
| E | Remove ALL instances of "Email integration is off" from every lens component in the codebase. | `grep -r "email integration" src/` returns zero results. `grep -r "Email integration" src/` returns zero results. Case-insensitive search clean. |

**FE-Phase 0 exit criteria:**
- [ ] `tokens.css` loaded globally, both themes switch correctly
- [ ] Tailwind config extended with all semantic tokens
- [ ] 11 base components built and rendering in both themes
- [ ] Zero "email integration" remnants in codebase
- [ ] `vite build` clean, zero errors, zero warnings
- [ ] PROGRESS_LOG.md updated with screenshot evidence per component

---

## FE-Phase 1: Reference Lens — Work Order
**This lens sets the quality standard. Every subsequent lens copies this pattern.**

Work Order chosen because: most visible UX problems (UUIDs shown, flat cards, no hierarchy), 20 actions (stress-tests the pattern), 6 missing frontend components.

### Pre-work (sequential, orchestrator does this first):
1. Read `/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/docs/pipeline/entity_lenses/work_order/Scope.md`
2. Read `Actions.md`, `Scenarios.md`, `RLS_Matrix.md` for work_order
3. Supabase MCP: `list_tables` → find all tables containing "work_order"
4. Supabase MCP: `execute_sql` → print columns, data types, FK, RLS for each
5. Classify every column: frontend-visible vs backend-only (per rules in CLAUDE.md)
6. Document findings in PROGRESS_LOG.md before spawning sub-agents

### Sub-agent tasks (parallel):

| Agent | Task | Done when |
|-------|------|-----------|
| A | Rebuild WO lens header: Overline (WORK ORDER, 11px/uppercase/tertiary), Title (24px/600/primary — NO UUID), Status pill, Priority badge. Full-screen layout (100vw × 100vh). | Screenshot: header matches UI_SPEC.md lens structure exactly. Zero UUIDs visible. |
| B | Build VitalSignsRow for WO with 5 indicators: status (pill), priority (badge), parts count, age, equipment (clickable link). Wire to real API data. | Vital signs populate from real DB. Equipment link navigates to equipment lens. |
| C | Build all section containers: Notes, Parts Used, Attachments, History. Each with sticky header, adjacent action button, empty state with contextual message. | All sections render. Headers stick on scroll (verified via Playwright scroll test). Actions adjacent per UI_SPEC.md. |
| D | Wire all 20 WO micro-actions to backend endpoints. Build the 6 missing frontend action components. Each action: button click → API call → success toast → section refresh → ledger entry. | All 20 actions triggerable from UI. Each produces correct API response (verified with value checks, not just 200). |
| E | File rendering: media (.png/.jpg/.mp4) inline preview, documents (.pdf/.docx) as FilePreviewCard. Signed URLs via JWT. RLS-compliant. Glass transition when opening Document lens from WO. | Upload test image → renders inline. Upload test PDF → preview card renders. Click → Document lens opens full-screen with transition. |

### Post-work (sequential):
1. Full 8-step test suite (DB constraints → RLS → SQL → Python per role → TS/Vite → Playwright E2E → DB ledger → Visual ledger)
2. Playwright E2E: crew user searches "generator fault" → opens WO → views notes → adds note → verifies in ledger
3. Playwright E2E: HOD opens same WO → signs action → verifies signature in audit
4. Screenshot ALL states (empty, populated, loading, error), attach to PROGRESS_LOG.md
5. Run code-review plugin

**FE-Phase 1 exit criteria:**
- [ ] WO lens is full-screen, themed (both modes), structured per CLAUDE.md and UI_SPEC.md
- [ ] All 20 actions wired, tested with value verification
- [ ] All sections populated with real data, sticky headers working
- [ ] File rendering working with signed URLs
- [ ] No UUIDs, no raw IDs visible anywhere
- [ ] All Playwright E2E tests pass per role
- [ ] Ledger entries confirmed in DB and visible in UI
- [ ] Code review plugin run, findings addressed
- [ ] PROGRESS_LOG.md updated with evidence for every sub-task

---

## FE-Phase 2: Lens Rollout Batch 1
**Lenses: Fault, Equipment, Parts/Inventory, Certificate**

All four have backend complete + frontend exists but needs quality upgrade to match WO standard.

### Pre-work:
1. Extract reusable patterns from FE-Phase 1 into shared components (if not already generic)
2. Read each lens's pipeline docs (Scope, Actions, Scenarios, RLS_Matrix)
3. SQL discovery per lens: tables, columns, FK, RLS

### Sub-agent tasks (4 agents, 1 per lens, parallel):

Each agent follows identical checklist:
1. Read lens pipeline docs
2. SQL: discover tables, classify columns
3. Rebuild lens header (overline, title, status, priority)
4. Build VitalSignsRow with lens-specific indicators (per VITAL_SIGNS.md)
5. Build all section containers with sticky headers + adjacent actions
6. Wire all actions to backend endpoints
7. Implement file rendering
8. Full-screen layout with glass transitions
9. 8-step test suite
10. Playwright E2E per role
11. Screenshot evidence

**FE-Phase 2 exit criteria:**
- [ ] 4 lenses rebuilt to FE-Phase 1 standard
- [ ] Shared components working identically across all 5 lenses (WO + these 4)
- [ ] All tests passing per lens with value verification
- [ ] PROGRESS_LOG.md updated with evidence per lens

---

## FE-Phase 3: Lens Rollout Batch 2
**Lenses: Receiving, Handover, Hours of Rest, Warranty, Shopping List**

Same process as FE-Phase 2. Special attention:

- **Receiving:** Full rejection flow — reason dropdown (quantity mismatch, damaged, wrong items, missing, quality, partial delivery), signature modal, optional email with pre-populated template (nullable dynamic fields), HOD notification. Email is NEVER auto-sent. User reviews, signs, then sends.
- **Handover:** Acknowledged status tracking per department
- **Hours of Rest:** MLC compliance calculations, per-crew-member view
- **Shopping List:** Linked receivals status tracking

---

## FE-Phase 4: Lens Rollout Batch 3 + Navigation System
**Lenses: Admin, Document, List/Query**
**System: Navigation (back/forward/history)**

Special attention:

- **Navigation system:** Back/forward via NavigationContext, glass transitions between entities, forward stack preservation when returning to home search bar, ledger logging for every navigation event
- **Show Related sidebar:** 420px, lazy-loaded on click only, infinite scroll with search-result-style cards, RLS-compliant, maintains yacht_id/role/department security
- **Document lens:** Full document viewer for PDFs/documents opened from other lenses (this is the destination when a FilePreviewCard is clicked)

---

## FE-Phase 5: Email Lens
**BLOCKED — Email backend (5 endpoints) is NOT IMPLEMENTED**

Frontend agent can pre-build:
1. Email compose UI (template rendering with nullable variables, CC auto-population with HOD, signature-before-send flow)
2. Email viewing UI (linked items display)
3. Leave backend wiring as stubs with clear TODO comments referencing which endpoints are needed

---

## FE-Phase 6: Integration, Polish, QA

| Task | Method |
|------|--------|
| Cross-lens navigation | Verify Part A → Equipment B → back/forward works across all lens combinations |
| Ledger completeness | Verify every action type across every lens logs to ledger correctly |
| Show Related | Verify works from every lens, results are relevant, RLS holds |
| Light mode QA | Playwright screenshots of every lens in light mode. Fix any contrast/readability issues. |
| Dark mode QA | Same for dark mode |
| Performance | Simulate 300ms+ latency (satellite WiFi). Verify skeleton loaders, progressive loading, no blank screens |
| Accessibility | Contrast ratios (WCAG AA), touch targets (44px min), keyboard navigation (⌘K for search, Escape to close, Tab between elements) |
| Mobile/tablet | Verify responsive breakpoints: desktop >1024, tablet 768-1024, mobile <768 |

---

## PHASE EXECUTION RULES

1. **Phase gating:** Never start FE-Phase N+1 until FE-Phase N exit criteria ALL have evidence
2. **Phase planning:** Every phase begins with `/gsd:plan-phase` → formal PLAN.md
3. **Phase execution:** Every phase runs via `/gsd:execute-phase` → parallel sub-agents
4. **Token management:** At 60% context → /compact. Re-read CLAUDE.md + UI_SPEC.md + PROGRESS_LOG.md after compact.
5. **Evidence standard:** Screenshots, test output, DB queries. "It works" is not evidence.
6. **No collision:** These FE-Phases are independent of ROADMAP.md Phases 1–13. Reference existing roadmap phases by their original names if cross-referencing.
