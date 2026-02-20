# GSD Phase Plan — Celeste Frontend

> Use `/gsd:plan-phase` to formalize each phase. Use `/gsd:execute-phase` to spawn sub-agents.
> NEVER do sequential work yourself. You are the orchestrator.

---

## Phase 0: Design System Implementation
**Priority: BLOCKING — nothing else starts until this is done**

### Sub-agent tasks (run in parallel):

| Agent | Task | Done when |
|-------|------|-----------|
| A | Implement `tokens.css` with all CSS custom properties (dark + light) from CLAUDE.md. Wire into app root. | Both themes toggle correctly. No raw hex in any existing component. `vite build` passes. |
| B | Extend `tailwind.config.js` with semantic token mappings from CLAUDE.md. | Tailwind classes resolve to CSS vars. Build passes. |
| C | Build base components: `StatusPill`, `SectionContainer` (with sticky header), `EntityLink`, `GhostButton`, `PrimaryButton`, `Toast` | Each component renders correctly in both themes. Storybook or isolated test page. |
| D | Build `VitalSignsRow` component — generic, accepts array of `{label, value, color?, href?}` | Renders horizontal row, wraps on mobile, clickable values navigate. |
| E | Remove ALL instances of "Email integration is off" from every lens. | `grep -r "email integration" src/` returns zero results. |

**Phase 0 exit criteria:**
- `tokens.css` loaded globally, both themes work
- Tailwind config extended
- 6 base components built and rendering
- Zero "email integration" remnants
- `vite build` clean, zero errors

---

## Phase 1: Reference Lens — Work Order
**Priority: HIGH — this lens sets the standard for all others**

Work Order is chosen because: (1) it has the most visible UX problems right now, (2) it has 20 actions which stress-tests the pattern, (3) 6 frontend components are missing.

### Pre-work (sequential, do first):
1. Read `/docs/pipeline/entity_lenses/work_order/Scope.md`
2. Read `/docs/pipeline/entity_lenses/work_order/Actions.md`
3. Read `/docs/pipeline/entity_lenses/work_order/Scenarios.md`
4. Read `/docs/pipeline/entity_lenses/work_order/RLS_Matrix.md`
5. SQL: query all tables containing "work_order" — print columns, types, FK, RLS
6. Classify each column: frontend-visible vs backend-only

### Sub-agent tasks (parallel after pre-work):

| Agent | Task | Done when |
|-------|------|-----------|
| A | Rebuild Work Order lens header: entity type label, title (no UUID), vital signs row with 5 indicators (status, priority, parts count, age, equipment link) | Screenshot matches CLAUDE.md lens structure. No UUID visible. Vital signs pull real data. |
| B | Build all section containers: Notes, Parts Used, Attachments, History. Sticky headers, adjacent action buttons, empty states with contextual messages. | All sections render, headers stick on scroll, actions are adjacent and clickable. |
| C | Build the 6 missing frontend components for Work Order actions. Wire to backend endpoints. | All 20 actions accessible from UI. Each action triggers correct API call. |
| D | Implement file rendering: media inline, documents as preview cards. Signed URLs. RLS-compliant. | Upload test image → renders inline. Upload test PDF → renders as card. Click card → Document lens opens. |
| E | Full-screen lens layout: `100vw × 100vh`, proper header with back/close, glass transition from search results. | Lens opens full-screen from search result click. Close returns to search. Transition is smooth (300ms). |

### Post-work (sequential):
1. Run full test suite (8-step order from CLAUDE.md)
2. Playwright E2E: crew user searches "generator fault" → opens Work Order → views notes → adds note → verifies in ledger
3. Playwright E2E: HOD user opens same WO → signs action → verifies signature in audit
4. Screenshot all states, attach to PROGRESS_LOG.md
5. Code review via plugin

**Phase 1 exit criteria:**
- Work Order lens is full-screen, themed, structured per CLAUDE.md
- All 20 actions wired and working
- All sections populated with real data
- Sticky headers working
- File rendering working
- All tests passing with value verification (not just 200 OK)
- Ledger entries confirmed in DB and visible in UI

---

## Phase 2: Pattern Extraction + Lens Rollout (Batch 1)
**Lenses: Fault, Equipment, Parts/Inventory, Certificate**

These four are chosen because: all have backend complete + frontend exists but needs quality upgrade.

### Pre-work:
1. Extract reusable patterns from Phase 1 Work Order into shared components
2. Document which components are generic vs Work-Order-specific
3. Read each lens's pipeline docs (Scope, Actions, Scenarios, RLS_Matrix)

### Sub-agent tasks (4 agents, 1 per lens, in parallel):

Each agent follows the same checklist:
1. SQL: discover tables, classify columns
2. Rebuild lens header with entity type, title, vital signs (per vital-signs spec)
3. Build all section containers with sticky headers + adjacent actions
4. Wire all actions to backend
5. Implement file rendering
6. Full-screen layout with glass transitions
7. Test suite (8 steps)
8. Playwright E2E per role
9. Screenshot evidence

**Phase 2 exit criteria:**
- 4 lenses rebuilt to Phase 1 standard
- All shared components working across lenses
- All tests passing per lens
- Progress log updated with evidence per lens

---

## Phase 3: Lens Rollout (Batch 2)
**Lenses: Receiving, Handover, Hours of Rest, Warranty, Shopping List**

Same process as Phase 2. Special attention:
- **Receiving:** Full rejection flow (reason dropdown, signature, optional email with template, HOD notification). See CLAUDE.md rejection flow section.
- **Handover:** Acknowledged status tracking
- **Hours of Rest:** MLC compliance calculations

---

## Phase 4: Lens Rollout (Batch 3) + Navigation
**Lenses: Admin, Document, List/Query, Navigation system**

Special attention:
- **Navigation:** Back/forward system via NavigationContext, glass transitions between entities, forward stack preservation when returning to home
- **Show Related:** Sidebar (420px), lazy-loaded on click only, infinite scroll, RLS-compliant
- **Document lens:** Full document viewer for PDFs/documents opened from other lenses

---

## Phase 5: Email Lens (Backend Build Required)
**Email backend is NOT IMPLEMENTED — this lens is blocked**

Depends on backend agent completing email infrastructure. Frontend agent can:
1. Build the email compose UI (template rendering, CC auto-population, signature-before-send)
2. Build the email viewing UI (linked items display)
3. Leave backend wiring as stubs until endpoints exist

---

## Phase 6: Cross-Lens Integration + Polish
- Verify all cross-lens navigation works (Part A → Equipment B → back/forward)
- Verify all ledger entries log correctly across lens transitions
- Verify Show Related works from every lens
- Light mode visual QA across all lenses
- Dark mode visual QA across all lenses
- Performance audit: satellite WiFi simulation (300ms+ latency)
- Accessibility audit: contrast ratios, touch targets, keyboard navigation

---

## PHASE EXECUTION RULES

1. Never start Phase N+1 until Phase N exit criteria are ALL met with evidence
2. Each phase starts with `/gsd:plan-phase` to formalize the PLAN.md
3. Each phase executes with `/gsd:execute-phase` to spawn parallel sub-agents
4. At 60% context within any phase: /compact, re-read CLAUDE.md, resume
5. Progress log updated after EVERY sub-task, not just phase completion
