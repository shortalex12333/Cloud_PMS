# STATE — Current Session Memory

> **This file tracks decisions, blockers, and position across sessions.**
>
> Last Updated: 2026-02-17

---

## Current Position

| Field | Value |
|-------|-------|
| Milestone | v1.0 — Lens Completion |
| Phase | FE-02-batch1-lenses |
| Plan | 04 of ?? (FE-02-03 + FE-02-04 COMPLETE) |
| Status | FE-02-03 complete - PartsLens with low-stock StatusPill warning, 5 sections, usePartActions, /parts/[id] route, 17 routes build passing |
| Last activity | 2026-02-17 — FE-02-03 executed: Parts/Inventory Lens Rebuild |

---

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-02-17)

**Core value:** Crew can complete maintenance tasks faster with fewer clicks than any existing PMS, with full audit trail.

**Current focus:** Phase 1 — Complete Receiving Lens

---

## Roadmap Summary

| # | Phase | Requirements | Status |
|---|-------|--------------|--------|
| 1 | Receiving | RECV-01..04 | ◐ 1/4 (RECV-04 ✓, rest blocked) |
| 2 | Parts/Inventory | PART-01..05 | ● 5/5 COMPLETE |
| 3 | Equipment | EQUIP-01..05 | ● 5/5 COMPLETE |
| 4 | Fault | FAULT-01..05 | ● 5/5 COMPLETE |
| 5 | Work Order | WO-01..05 | ● 5/5 COMPLETE (13-01 added reassign/archive) |
| 6 | Certificate | CERT-01..05 | ◐ 4/5 (CertificateCard.tsx + E2E done, CERT-04 complete) |
| 7 | Handover | HAND-01..05 | ● 5/5 COMPLETE (HAND-03 role tests added) |
| 8 | Hours of Rest | HOR-01..05 | ● 5/5 COMPLETE |
| 9 | Warranty | WARR-01..05 | ● 5/5 COMPLETE (E2E + ledger triggers added) |
| 10 | Shopping List | SHOP-01..05 | ● 5/5 COMPLETE (state history trigger added) |
| 11 | Email | EMAIL-01..06 | ◐ 4/6 (EMAIL-01 done - email_handlers.py) |
| 12 | Cross-Lens Cleanup | CLEAN-01..04 | ● 4/4 COMPLETE (13-01 fixed CLEAN-01) |

---

## Decisions Made

| Decision | Rationale | Date |
|----------|-----------|------|
| Shadow-only search bar | ChatGPT parity spec | 2026-02-17 |
| Tokenized CSS variables | Design system consistency | 2026-02-17 |
| All crew can create receiving | Draft mode workflow | 2026-02-17 |
| HOD+ for accept | Financial accountability | 2026-02-17 |
| Service role bypass | Backend needs full access | 2026-02-17 |
| Confidence in payload | No separate column | 2026-02-17 |
| Skip research for M1 | Brownfield — codebase mapped, specs exist | 2026-02-17 |
| 12 phases, 60 requirements | One lens per phase | 2026-02-17 |
| Use pms_audit_log for shopping list state tracking | Consistency with other lenses | 2026-02-17 |
| SignaturePrompt renders as full overlay replacing modal | UX spec ownership transfer pattern | 2026-02-17 |
| Email handlers follow warranty_handlers.py pattern | Consistency with existing codebase | 2026-02-17 |
| API-driven E2E tests over UI tests | Reliability and speed | 2026-02-17 |
| Warranty trigger fires on INSERT and UPDATE | Complete audit trail | 2026-02-17 |
| Handover tests use existing fullLogin helper | Consistency with auth patterns | 2026-02-17 |
| Email panel gates on Outlook connection, not env flag | Real service state vs configuration | 2026-02-17 |
| ds-* prefix for Tailwind spacing tokens | Avoid collision with default numeric spacing | 2026-02-17 |
| IntersectionObserver for sticky headers | Performant, no scroll listener overhead | 2026-02-17 |
| forwardRef for all UI components | Consistent ref forwarding pattern | 2026-02-17 |
| Remove useEmailFeatureEnabled hook entirely | No dead code per rules.md | 2026-02-17 |
| Middle dot separator for vital signs | Visual distinction per UI_SPEC.md | 2026-02-17 |
| StatusPill integration via color prop | Conditional rendering pattern | 2026-02-17 |
| getAttachmentKind uses extension set not MIME type | MIME unreliable from signed storage URLs | 2026-02-17 |
| HistorySection has defensive empty state | Guards edge cases even though spec says always has creation entry | 2026-02-17 |
| Section count badge omitted when count==0 | Avoids "Parts Used (0)" display; empty state provides the signal | 2026-02-17 |
| Document cards use role=button + tabIndex=0 | Valid HTML pattern for block-level interactive elements | 2026-02-17 |
| LensTitleBlock co-located in LensHeader.tsx | Companion component, reduces import complexity | 2026-02-17 |
| wo_number (WO-YYYY-NNN) as display title prefix | Never expose raw UUID to users | 2026-02-17 |
| Equipment link uses VitalSign href prop | VitalSignsRow renders teal links natively — no extra markup | 2026-02-17 |
| Status/priority color mappers local to each lens | Domain-specific logic stays with domain component | 2026-02-17 |
| MediaRenderer uses MIME-based getFileCategory | Reliable when typed file object available (vs storage URL) | 2026-02-17 |
| Signed URL staleTime 55min | Auto-refetch 5min before 1hr expiry prevents 401s | 2026-02-17 |
| fileUtils.ts canonical file utility location | MediaRenderer + DocumentCard share without circular imports | 2026-02-17 |
| Lightbox z-[9999] | Above all other overlays (modals z-50, z-header lower) | 2026-02-17 |
| CSS state machine for glass transitions | No Framer Motion dependency; CSS opacity+scale+blur sufficient | 2026-02-17 |
| stickyTop=0 default on SectionContainer | Full backward compat; lens usage passes 56 to clear header | 2026-02-17 |
| Ledger logging fire-and-forget | Auth token fetch never blocks navigation UX | 2026-02-17 |
| useLensNavigation hook per lens instance | Per-page architecture matches Next.js routing model | 2026-02-17 |
| useWorkOrderPermissions hides buttons (not disables) | UI_SPEC.md spec: hide, not disable for role gates | 2026-02-17 |
| execute() helper injects yacht_id + work_order_id automatically | No repetition at call site, DRY action calls | 2026-02-17 |
| Modal state in WorkOrderLens (not sections) | Single source of truth, sections receive only callbacks | 2026-02-17 |
| E2E tests in tests/playwright/ not e2e/ | playwright.config.ts testDir is ./tests/playwright | 2026-02-17 |
| openWorkOrderLens returns bool (not void) | Enables graceful skip when staging data unavailable | 2026-02-17 |
| WO-LENS-009 in separate describe block | Avoids beforeEach HOD auth conflict when testing crew role gate | 2026-02-17 |
| Expiry color: critical/warning/success by daysUntilExpiry | critical=expired, warning=<=30d, success=valid — matches UI_SPEC.md | 2026-02-17 |
| certificateType prop drives entity link (crew_member vs vessel_name) | Two distinct entity contexts with different link targets | 2026-02-17 |
| SectionContainer action: {label,onClick} not ReactNode | Typed interface enforced at build time — use action.label pattern | 2026-02-17 |
| Inline ConsumePartModal + ReceivePartModal co-located in PartsLens | Simple 2-field modals don't warrant separate /actions directory | 2026-02-17 |
| Crew role included in CONSUME_ROLES for parts | Parts consumption is a routine crew-level task per domain spec | 2026-02-17 |
| gitignore parts/ negation for app/parts/ route | Python Buildout artifact pattern was blocking Next.js route directory | 2026-02-17 |
| TransactionType union includes DB schema + legacy types | Backward compat; pms_inventory_transactions uses received/consumed/adjusted etc. | 2026-02-17 |
| UsageLogSection as 5th section (separate from TransactionHistory) | Distinguishes consumptions-with-context (WO, equipment, reason) from raw ledger | 2026-02-17 |
| Fetch /v1/certificates/{id}?type=vessel|crew direct in page.tsx | No microaction handler for certificates yet; consistent with other lens pages | 2026-02-17 |

---

## Blockers

| Blocker | Impact | Owner | Status |
|---------|--------|-------|--------|
| PR #332 pending merge | Receiving 8/10 tests | User | OPEN |
| crew.test@alex-short.com not in Supabase | Crew create test fails | User | OPEN |
| Handler not deployed to staging | Reject→accept test fails against remote | DevOps | OPEN |
| ~~Email lens handler missing~~ | ~~5 actions unimplemented~~ | Claude (Phase 11) | RESOLVED (13-04) |

---

## Accumulated Context

### Roadmap Evolution
- Phase 13 added: Gap Remediation - Fix all failing requirements from verification

### From Codebase Mapping
- 7 documents in `.planning/codebase/` (4,120 lines total)
- 119 actions in registry.py across 10 domains
- 16 lenses identified, 14 at 0% test coverage
- Email lens handler file missing entirely
- Lens specs exist in `/docs/pipeline/entity_lenses/`

### Testing Protocol (from rules.md)
1. DB schema check (RLS, FK, constraints)
2. Search filter restrictions
3. Backend SQL push test
4. Python handler role tests (crew, HOD, captain)
5. Frontend build test (TypeScript, Vite)
6. Playwright login test per user
7. E2E journey tests all roles
8. Ledger backend trigger check
9. Ledger frontend UX verification

---

## Session Notes

### 2026-02-17
- Codebase mapping complete (7 docs, 4,120 lines)
- GSD milestone M1 initialized
- Requirements defined: 60 REQ-IDs across 12 categories
- Roadmap created: 12 phases

### 2026-02-17 (Session 2)
- Phase 1 assessment: 8/10 E2E tests passing
- RECV-04 VERIFIED: All 9 receiving actions write to pms_audit_log
- RECV-01/02/03 BLOCKED by user actions (PR merge, crew user, staging deploy)
- Proceeding to Phase 2 while Phase 1 blockers resolved

### 2026-02-17 (Session 3) - Full Verification Run
**Phases 2-12 verified via parallel GSD agents:**

| Phase | Status | Notes |
|-------|--------|-------|
| 2 Parts/Inventory | 5/5 ✓ | All requirements verified |
| 3 Equipment | 5/5 ✓ | All requirements verified |
| 4 Fault | 5/5 ✓ | 57/57 E2E tests passed |
| 5 Work Order | 4/5 | WO-03: reassign/archive UI missing |
| 6 Certificate | 3/5 | CertificateCard.tsx done (13-02), E2E tests missing |
| 7 Handover | 3/5 | Signature display + role tests partial |
| 8 Hours of Rest | 5/5 ✓ | All requirements verified |
| 9 Warranty | 3/5 | WarrantyCard.tsx done (13-03), E2E/ledger missing |
| 10 Shopping List | 4/5 | State history table missing |
| 11 Email | 4/6 | email_handlers.py done (13-04) |
| 12 Cross-Lens | 2/4 | Email message + SignaturePrompt not wired |

**Total: 42/54 requirements verified (78%)**

**Critical gaps requiring remediation:**
1. ~~CertificateCard.tsx - create frontend component~~ DONE (13-02)
2. ~~WarrantyCard.tsx - create frontend component~~ DONE (13-03)
3. ~~email_handlers.py - create registry handler file~~ DONE (13-04)
4. ~~Shopping list state_history trigger - deploy migration~~ DONE (13-05)
5. ~~SignaturePrompt - wire to finalize/approve modals~~ DONE (13-06)
6. ~~Remove "email integration is off" message~~ DONE (13-01)

---

## Next Single Action

**FE-01-05 COMPLETE — LensContainer + glass transitions + body scroll lock + useLensNavigation + stickyTop. Continue with FE-01-06.**

### 2026-02-17 (Session 4) - Design System Phase 00
- Plan 00-05: Verified "email integration is off" dead code removal (DS-05)
- Primary work committed in 9b8dfb52
- Pre-existing TypeScript error in AddNoteModal.tsx logged to deferred-items.md

### 2026-02-17 (Session 5) - Design System Plan 00-01
- Plan 00-01: Implemented design tokens CSS (DS-01)
- All tokens present: surface, text, brand, status, shadow, spacing, radius, transitions, z-index
- Dark theme default (:root), light theme via [data-theme="light"] attribute
- Commits: d7eb6ed2 (tokens.css), 1d5cc028 (globals.css import), 6a27bf89 (layout.tsx data-theme), 8a30f9e9 (25 tests)
- 25/25 design token tests pass
- SUMMARY.md updated with complete execution record

### Key decisions from 00-01:
- Dark theme as :root default (prevents FOUC)
- data-theme attribute for theme switching (not className)
- tokens.css imported before @tailwind directives

### 2026-02-17 (Session 6) - Design System Plan 00-02
- Plan 00-02: Verified Tailwind config semantic tokens (DS-02)
- All mappings present: brand/status/surface/txt colors, ds-* spacing, radius, shadow
- Tailwind build compiles in 852ms
- Prior commit: a245820f (work order dark mode tokens)
- SUMMARY.md created documenting previously completed work

### 2026-02-17 (Session 7) - Design System Plan 00-03
- Plan 00-03: Built 6 base UI components (DS-03)
- StatusPill, SectionContainer, GhostButton, PrimaryButton, EntityLink, Toast
- Zero raw hex values - all semantic tokens
- 7 atomic commits: 1c259f25, 650c713a, 04314162, 4116ce59, 7f9a3a42, 0ca498ab, d9668a5a
- Pre-existing build issue (AddNoteModal.tsx) logged to deferred-items.md

### 2026-02-17 (Session 8) - Design System Plan 00-04
- Plan 00-04: Built VitalSignsRow component (DS-04)
- Generic horizontal row for 3-5 factual database values
- Middle-dot separators, StatusPill integration, clickable entity links
- Typography: 13px label, 14px value per UI_SPEC.md
- 2 atomic commits: bf95999c (interface), 53640e13 (implementation + index export)
- Pre-existing build issue (AddPhotoModal.tsx @ts-nocheck) fixed as blocking issue

### 2026-02-17 (Re-execution) - Design System Plan 00-05
- Plan 00-05: Confirmed email integration dead code removal (DS-05)
- Zero grep results for "email integration", useEmailFeatureEnabled, EMAIL_ENABLED
- Build passes after clearing stale .next cache: 25 routes generated
- Commit: 9b8dfb52 (feat: remove email integration feature flag dead code)
- Phase 00-design-system COMPLETE - all 5 plans executed

### 2026-02-17 (FE-01-01) - Work Order Lens Header + Vital Signs
- Plan FE-01-01: Created LensHeader reference implementation and WorkOrderLens component
- LensHeader: 56px fixed header, back/close icon buttons, entity type overline (11px/uppercase)
- LensTitleBlock: 28px display title, 16px subtitle (2-line clamp), status/priority StatusPills
- WorkOrderLens: VitalSignsRow wired with 5 indicators (status, priority, parts, created, equipment)
- Equipment link: text-brand-interactive, clickable via href prop
- Updated work-orders/[id]/page.tsx to use WorkOrderLens, removing old celeste-* CSS classes
- No UUID visible: wo_number (WO-YYYY-NNN) displayed, raw id never rendered
- Commits: 0ba11258 (LensHeader), 7e1a13a7 (VitalSignsRow), 33723d94 (page refactor)
- Build: 16/16 routes, 0 TS errors

### 2026-02-17 (FE-01-02) - Work Order Section Containers
- Plan FE-01-02: Built all 4 section containers for Work Order lens
- NotesSection: 3-line clamp/expand, relative/absolute timestamps, Add Note CTA
- PartsSection: EntityLink to Parts lens, StatusPill (consumed=success, reserved=warning)
- AttachmentsSection: media inline max-h 240px, document File Preview Cards with onDocumentClick
- HistorySection: read-only, 20-entry pagination, collapsible details, no action button
- 1 auto-fix: StatusPill prop mismatch (color→status) found during Task 2
- Commits: 4eab661c, 4c5e443c, 572c712f, c83c7843, aeab7c8e
- Build: 16/16 routes, 0 TS errors

### 2026-02-17 (FE-01-03) - Work Order Actions (All 20)
- Plan FE-01-03: Wired all work order actions from backend registry to frontend
- useWorkOrderActions: 14 typed helpers (addNote, closeWorkOrder, startWorkOrder, cancelWorkOrder, addPart, addParts, addPhoto, assignWorkOrder, reassignWorkOrder, updateWorkOrder, archiveWorkOrder, addHours, viewChecklist)
- useWorkOrderPermissions: 10 role flags matching registry.py allowed_roles (hide, not disable)
- 5 action modals: AddNoteModal, AddPartModal, MarkCompleteModal, ReassignModal, ArchiveModal
- WorkOrderLens updated: all 4 sections wired + header action buttons + 5 modals at root
- Rule 1 fix: useCallback hooks moved above early returns in page.tsx (build was failing)
- Commits: df5dce5a (hook), 8d000097 (modals), 2725ccd1 (wiring + fix)
- Build: 16/16 routes, 0 TS errors

### 2026-02-17 (FE-01-04) - File Rendering Components
- Plan FE-01-04: Created standalone MediaRenderer and DocumentCard in /components/media/
- MediaRenderer: loading skeleton, error state, lightbox (z-9999), signed URL via useQuery (55min staleTime)
- DocumentCard: 48px preview card, icon + filename/size + chevron, role=button keyboard accessible
- fileUtils.ts: getFileCategory (MIME), getFileCategoryFromExtension, getAttachmentKind (extension), formatFileSize, getDocumentIcon
- AttachmentsSection refactored: imports standalone components, onDocumentClick typed as (fileId) => void
- 2 auto-fixes: merged duplicate authHelpers imports, added backward-compat re-export for getAttachmentKind
- Commits: adf1c94d (fileUtils), dff941ae (MediaRenderer), 9733e87f (DocumentCard), 7fec203b (index), a8437390 (AttachmentsSection)
- Build: 16/16 routes, 0 TS errors

### 2026-02-17 (FE-01-05) - Full-Screen Lens Layout + Glass Transitions
- Plan FE-01-05: LensContainer, glass transitions, body scroll lock, navigation stack hook, sticky header fix
- LensContainer: fixed inset-0 (100vw x 100vh), z-modal (40), overflow-y auto, overscroll-contain, Escape handler
- lens.css: lens-entering/entered/exiting/exited CSS state machine; enter 300ms ease-out, exit 200ms ease-in; prefers-reduced-motion fallback
- Body scroll lock: document.body.style.overflow hidden + scrollbar-width compensation
- useLensNavigation hook: linear stack (max 9), push/back/close, each logs to ledger via callback
- WorkOrderLensPage: logNavigationEvent (navigate_to_lens, navigate_back, close_lens) — fire-and-forget
- stickyTop prop: SectionContainer + all 4 sections; WorkOrderLens passes stickyTop={56}
- 2 auto-fixes: stickyTop missing (sections would stick behind header), useCallback hooks before early returns
- Commits: 3bc868d6 (LensContainer+CSS), 7100dc80 (wiring+ledger), 9789e888 (hook), a49edd78 (stickyTop)
- Build: 16/16 routes, 0 TS errors

### 2026-02-17 (FE-01-06) - Work Order E2E Tests + Verification
- Plan FE-01-06: Created Playwright E2E test suite for Work Order lens
- 15 tests covering: no UUID in header, 5 vital signs, crew add note, HOD mark complete, role gate, ledger
- Test location: tests/playwright/work-order-lens.spec.ts (not e2e/ — matches playwright.config.ts testDir)
- Auth: loginAs() helper (not login()) per auth.helper.ts pattern
- Selectors: text/role-based (no data-testid on lens components)
- Test results: 13 passed, 2 skipped (staging credentials required), 0 failures
- Ledger SQL reference documented in WO-LENS-012 test
- 3 Rule 3 auto-fixes: testDir, auth helper, selector strategy
- 2 Rule 1 auto-fixes: openWorkOrderLens bool return, WO-LENS-009 describe conflict
- Commits: 7fc4fbc7 (spec file), e1889adc (robustness fixes)
- Build: 16/16 routes, 0 TS errors
- FE-01-work-order-lens PHASE COMPLETE (all 6 plans executed)

### 2026-02-17 (FE-02-04) - Certificate Lens Rebuild
- Plan FE-02-04: Created CertificateLens component for vessel + crew certificates
- VitalSignsRow: 5 indicators with expiry color logic (critical/warning/success)
- DetailsSection, LinkedDocumentsSection, RenewalHistorySection (SectionContainer pattern)
- useCertificateActions: 6 typed helpers (view, create, update, findExpiring, linkDocument, supersede)
- useCertificatePermissions: 6 role flags (HOD+ / MANAGE_ROLES / captain+manager)
- /certificates/[id] page.tsx: ?type=vessel|crew query param, fire-and-forget ledger logging
- Rule 3 auto-fix: Pre-existing TS error in ReceivingLineItemsSection (string|number vs number)
- Commits: 39f54e95 (component), a738e191 (hook), 79cd00a2 (page), 892c3c23 (auto-fix)
- Build: TypeScript compiled successfully, 16/16 routes, /certificates/[id] = ƒ dynamic

### 2026-02-17 (FE-02-03) - Parts/Inventory Lens Rebuild
- Plan FE-02-03: Created PartsLens component following WorkOrderLens pattern exactly
- VitalSignsRow: 5 indicators (Stock with StatusPill warning/critical, Location, Unit, Reorder At, Supplier)
- Low stock: StatusPill in vital sign + role=alert banner below vitals for double emphasis
- 5 sections: StockInfoSection (qty/min/max/cost), TransactionHistorySection, UsageLogSection, LinkedEquipmentSection, DocumentsSection
- usePartActions: 7 typed helpers (view, consume, receive, transfer, adjust, write_off, addToShoppingList)
- usePartPermissions: 7 flags — crew can consume; HOD+ can receive/transfer/adjust/write_off
- /parts/[id]/page.tsx: viewPartStock() microaction, field mapping, ledger logging
- Rule 3 auto-fix: .gitignore `parts/` Python artifact was blocking Next.js app/parts/ route
- Commits: 8c92612f (PartsLens), 1892bec4 (sections), 2a8b8d36 (hook), 2da15688 (page+gitignore), d8cb25c0 (build)
- Build: 17/17 routes, 0 TS errors (+1 route vs previous)

### Next Action
**FE-02-03 complete — Parts Lens implemented. FE-02-04 also complete (Certificate Lens). Continue with FE-02-05.**

