# ROADMAP — CelesteOS v1.0 Lens Completion

**Milestone:** v1.0 — Lens Completion
**Phases:** 15
**Requirements:** 84

---

## Summary

| # | Phase | Goal | Requirements | Status |
|---|-------|------|--------------|--------|
| 0 | Design System | Complete    | 2026-02-17 | ○ |
| 1 | Receiving | Complete receiving lens end-to-end | RECV-01, RECV-02, RECV-03, RECV-04 | ○ |
| 2 | Parts/Inventory | Complete parts and inventory lens end-to-end | PART-01, PART-02, PART-03, PART-04, PART-05 | ○ |
| 3 | Equipment | Complete equipment lens end-to-end | EQUIP-01, EQUIP-02, EQUIP-03, EQUIP-04, EQUIP-05 | ○ |
| 4 | Fault | Complete fault lens end-to-end | FAULT-01, FAULT-02, FAULT-03, FAULT-04, FAULT-05 | ○ |
| 5 | Work Order | Complete work order lens end-to-end | WO-01, WO-02, WO-03, WO-04, WO-05 | ○ |
| 6 | Certificate | Complete certificate lens end-to-end | CERT-01, CERT-02, CERT-03, CERT-04, CERT-05 | ○ |
| 7 | Handover | Complete handover lens end-to-end | HAND-01, HAND-02, HAND-03, HAND-04, HAND-05 | ○ |
| 8 | Hours of Rest | Complete hours of rest and compliance lens end-to-end | HOR-01, HOR-02, HOR-03, HOR-04, HOR-05 | ○ |
| 9 | Warranty | Complete warranty claims lens end-to-end | WARR-01, WARR-02, WARR-03, WARR-04, WARR-05 | ○ |
| 10 | Shopping List | Complete shopping list lens end-to-end | SHOP-01, SHOP-02, SHOP-03, SHOP-04, SHOP-05 | ○ |
| 11 | Email | Complete email lens end-to-end | EMAIL-01, EMAIL-02, EMAIL-03, EMAIL-04, EMAIL-05, EMAIL-06 | ○ |
| 12 | Cross-Lens Cleanup | Resolve cross-lens UX issues across all lenses | CLEAN-01, CLEAN-02, CLEAN-03, CLEAN-04 | ○ |
| 13 | Gap Remediation | Complete    | 2026-02-17 | ○ |
| 14 | Handover Export Editable | Two-bucket storage + dual signatures | HEXPORT-01..07 | ● COMPLETE |

---

## Phase 0: Design System Implementation

**Goal:** Implement complete design token system, build base UI components, extend Tailwind config, and remove dead code — BLOCKING for all other phases.

**Requirements:** DS-01, DS-02, DS-03, DS-04, DS-05

**Success Criteria:**
1. `tokens.css` implemented with all CSS custom properties (dark + light themes) wired into app root.
2. `tailwind.config.js` extended with semantic token mappings.
3. 6 base components built: StatusPill, SectionContainer, GhostButton, PrimaryButton, EntityLink, Toast.
4. VitalSignsRow component built and rendering correctly.
5. All "email integration is off" instances removed from codebase.

**Status:** ○ Pending

---

## Phase 1: Receiving Lens

**Goal:** Deliver a fully tested receiving lens with PR deployed, crew user provisioned, all E2E tests passing, and ledger triggers verified.

**Requirements:** RECV-01, RECV-02, RECV-03, RECV-04

**Success Criteria:**
1. PR #332 is merged and live in the deployed environment with no regressions.
2. A crew test user exists in Supabase auth and can authenticate against the receiving lens.
3. All 10 E2E tests for the receiving lens pass in CI without flakiness.
4. Ledger triggers fire correctly for every receiving action (create, accept, reject, adjust) and entries are verifiable in the ledger table.

**Status:** ○ Pending

---

## Phase 2: Parts/Inventory Lens

**Goal:** Deliver a fully verified parts and inventory lens covering schema integrity, multi-role handler tests, frontend rendering, CRUD E2E coverage, and ledger audit trail.

**Requirements:** PART-01, PART-02, PART-03, PART-04, PART-05

**Success Criteria:**
1. Database schema for pms_parts, pms_inventory_transactions, pms_inventory_stock, and pms_shopping_list_items passes RLS, foreign key, and constraint checks.
2. Backend handler tests pass for all user roles (Captain, Chief Engineer, Crew) covering view, consume, receive, transfer, adjust, and write-off actions.
3. Frontend lens renders all required part and stock values including stock level, location, unit, and low-stock indicator.
4. E2E tests cover the full CRUD lifecycle for part management and inventory transactions.
5. Ledger triggers are verified for every inventory mutation action.

**Status:** ○ Pending

---

## Phase 3: Equipment Lens

**Goal:** Deliver a fully verified equipment lens covering schema integrity, multi-role handler tests, frontend rendering, CRUD E2E coverage, and ledger audit trail.

**Requirements:** EQUIP-01, EQUIP-02, EQUIP-03, EQUIP-04, EQUIP-05

**Success Criteria:**
1. Database schema for pms_equipment passes RLS, foreign key, and constraint checks, including links to work orders, parts, and faults.
2. Backend handler tests pass for all user roles covering view, maintenance history, linked parts, linked faults, and manual retrieval.
3. Frontend lens renders all required equipment values including make, model, serial number, location, and maintenance status.
4. E2E tests cover the full equipment view and update lifecycle.
5. Ledger triggers are verified for all equipment state changes.

**Status:** ○ Pending

---

## Phase 4: Fault Lens

**Goal:** Deliver a fully verified fault lens covering schema integrity, multi-role handler tests, frontend rendering, full fault lifecycle E2E coverage, and ledger audit trail.

**Requirements:** FAULT-01, FAULT-02, FAULT-03, FAULT-04, FAULT-05

**Success Criteria:**
1. Database schema for pms_faults and related attachment tables passes RLS, foreign key, and constraint checks.
2. Backend handler tests pass for all user roles covering report, acknowledge, diagnose, close, reopen, and mark-false-alarm actions.
3. Frontend lens renders all required fault values including severity, status, linked equipment, notes, and photos.
4. E2E tests cover the full fault lifecycle from reporting through closure including photo upload and note addition.
5. Ledger triggers fire correctly for every fault state transition.

**Status:** ○ Pending

---

## Phase 5: Work Order Lens

**Goal:** Deliver a fully verified work order lens with all missing frontend actions restored, multi-role handler tests passing, CRUD E2E coverage, and ledger audit trail.

**Requirements:** WO-01, WO-02, WO-03, WO-04, WO-05

**Success Criteria:**
1. Database schema for pms_work_orders, pms_work_order_notes, and pms_work_order_parts passes RLS, foreign key, and constraint checks.
2. Backend handler tests pass for all user roles covering open, view, add note, add part, create from fault, and mark complete actions.
3. All 6 previously missing frontend action buttons are present and functional in the work order lens.
4. E2E tests cover the full work order lifecycle from creation through completion including part and note attachment.
5. Ledger triggers fire correctly for every work order state transition and mutation.

**Status:** ○ Pending

---

## Phase 6: Certificate Lens

**Goal:** Deliver a fully verified certificate lens covering vessel and crew certificates with schema integrity, multi-role handler tests, frontend rendering, CRUD E2E coverage, and ledger audit trail.

**Requirements:** CERT-01, CERT-02, CERT-03, CERT-04, CERT-05

**Success Criteria:**
1. Database schema for vessel_certificates and crew_certificates passes RLS, foreign key, and constraint checks.
2. Backend handler tests pass for all user roles covering list, view, create, update, find-expiring, link-document, and supersede actions for both vessel and crew certificates.
3. Frontend lens renders all required certificate values including type, issue date, expiry date, issuing authority, and linked documents.
4. E2E tests cover the full certificate lifecycle from creation through renewal and supersession.
5. Ledger triggers are verified for all certificate mutations.

**Status:** ○ Pending

---

## Phase 7: Handover Lens

**Goal:** Deliver a fully verified handover lens covering the complete sign-off workflow with schema integrity, multi-role handler tests, frontend rendering, CRUD E2E coverage, and ledger audit trail.

**Requirements:** HAND-01, HAND-02, HAND-03, HAND-04, HAND-05

**Success Criteria:**
1. Database schema for handover_items and handover_exports passes RLS, foreign key, and constraint checks.
2. Backend handler tests pass for all user roles covering add, edit, validate, finalize, export, sign-outgoing, and sign-incoming actions.
3. Frontend lens renders all required handover values including status, items list, signatures, and export format.
4. E2E tests cover the full handover lifecycle from draft creation through dual signature and export.
5. Ledger triggers are verified for all handover state transitions.

**Status:** ○ Pending

---

## Phase 8: Hours of Rest Lens

**Goal:** Deliver a fully verified hours of rest and compliance lens covering STCW-compliant rest tracking, monthly sign-off workflow, crew templates, and warning acknowledgement.

**Requirements:** HOR-01, HOR-02, HOR-03, HOR-04, HOR-05

**Success Criteria:**
1. Database schema for pms_hours_of_rest, pms_crew_hours_warnings, pms_monthly_signoffs, and pms_crew_templates passes RLS, foreign key, and constraint checks.
2. Backend handler tests pass for all user roles covering log, upsert, get, create sign-off, sign, list warnings, acknowledge warning, create template, and apply template actions.
3. Frontend lens renders all required HOR values including daily rest periods, violation indicators, monthly summary, and sign-off status.
4. E2E tests cover the full HOR lifecycle from daily logging through monthly sign-off and warning acknowledgement.
5. Ledger triggers are verified for all HOR mutations and sign-off events.

**Status:** ○ Pending

---

## Phase 9: Warranty Lens

**Goal:** Deliver a fully verified warranty claims lens covering the full claim lifecycle with schema integrity, multi-role handler tests, frontend rendering, CRUD E2E coverage, and ledger audit trail.

**Requirements:** WARR-01, WARR-02, WARR-03, WARR-04, WARR-05

**Success Criteria:**
1. Database schema for pms_warranty_claims passes RLS, foreign key, and constraint checks, including links to equipment and faults.
2. Backend handler tests pass for all user roles covering draft, submit, approve, and reject claim actions.
3. Frontend lens renders all required warranty claim values including claim status, linked equipment, linked fault, supplier, and resolution.
4. E2E tests cover the full warranty claim lifecycle from draft through approval or rejection.
5. Ledger triggers are verified for all warranty claim state transitions.

**Status:** ○ Pending

---

## Phase 10: Shopping List Lens

**Goal:** Deliver a fully verified shopping list lens covering item creation, approval workflow, schema integrity, multi-role handler tests, frontend rendering, CRUD E2E coverage, and ledger audit trail.

**Requirements:** SHOP-01, SHOP-02, SHOP-03, SHOP-04, SHOP-05

**Success Criteria:**
1. Database schema for pms_shopping_list_items passes RLS, foreign key, and constraint checks.
2. Backend handler tests pass for all user roles covering create, approve, and reject shopping list item actions.
3. Frontend lens renders all required shopping list values including item name, quantity, status, requester, and approver.
4. E2E tests cover the full shopping list lifecycle from item creation through approval or rejection.
5. Ledger triggers are verified for all shopping list item state changes.

**Status:** ○ Pending

---

## Phase 11: Email Lens

**Goal:** Deliver a fully implemented and tested email lens with handler file, all 5 registry actions, verified schema, multi-role tests, E2E coverage, and ledger audit trail.

**Requirements:** EMAIL-01, EMAIL-02, EMAIL-03, EMAIL-04, EMAIL-05, EMAIL-06

**Success Criteria:**
1. email_handlers.py exists and is registered in the handler registry with no import errors.
2. All 5 email actions (search_emails, view_email_thread, extract_entities, link_to_work_order, link_to_equipment) are implemented and callable.
3. Database schema for email_messages, email_extraction_jobs, and email_extraction_results passes RLS, foreign key, and constraint checks.
4. Backend handler tests pass for all user roles covering search, view thread, extract, and link actions.
5. E2E tests cover the email lens flow from search through entity extraction and linking to a work order or equipment record.
6. Ledger triggers are verified for email extraction and linking events.

**Status:** ○ Pending

---

## Phase 12: Cross-Lens Cleanup

**Goal:** Resolve all cross-cutting UX issues across every lens to meet the single-URL, full-screen, intent-first design standard.

**Requirements:** CLEAN-01, CLEAN-02, CLEAN-03, CLEAN-04

**Success Criteria:**
1. No lens displays the "email integration is off" message; the message is removed from all lens components.
2. Every lens opens in full-screen view rather than a side-view card, verified by visual regression tests across all 12 lenses.
3. Action buttons are positioned adjacent to the section they act upon in every lens, with no orphaned or misplaced action controls.
4. All actions requiring confirmation (e.g., sign-off, finalize, approve) display a signature confirmation dialog before executing.

**Status:** ○ Pending

---

## Phase 13: Gap Remediation

**Goal:** Fix all failing requirements from phases 1-12 verification. Close the gap from 78% to 100% requirement coverage.

**Depends on:** Phase 12

**Requirements:** WO-03, CERT-03, CERT-04, HAND-02, HAND-03, WARR-03, WARR-04, WARR-05, SHOP-05, EMAIL-01, CLEAN-01, CLEAN-04

**Plans:** 5/5 plans complete

Plans:
- [ ] 13-01-PLAN.md — WorkOrder reassign/archive + remove email disabled message
- [ ] 13-02-PLAN.md — Create CertificateCard.tsx component
- [ ] 13-03-PLAN.md — Create WarrantyCard.tsx component
- [ ] 13-04-PLAN.md — Create email_handlers.py and register
- [ ] 13-05-PLAN.md — Shopping list state_history trigger migration
- [ ] 13-06-PLAN.md — Wire SignaturePrompt to finalize/approve modals
- [ ] 13-07-PLAN.md — Certificate and warranty E2E tests + warranty ledger triggers
- [ ] 13-08-PLAN.md — Handover role tests and signature flow E2E

**Success Criteria:**
1. All 12 requirements addressed by plans are verified passing.
2. Total verification coverage increases from 78% (42/54) to 100% (54/54).
3. No new regressions introduced.

**Status:** ○ Pending

---

## Phase 14: Handover Export Editable with Signature

**Goal:** Enable users to view, edit, and sign their AI-generated handover exports before final submission, with two-bucket storage for legal compliance and searchable indexing.

**Depends on:** Phase 7 (Handover)

**Requirements:** HEXPORT-01, HEXPORT-02, HEXPORT-03, HEXPORT-04, HEXPORT-05, HEXPORT-06, HEXPORT-07

**Plans:** 8/8 plans complete

Plans:
- [x] 14-01-PLAN.md — External service integration + UX change
- [x] 14-02-PLAN.md — Database schema updates
- [x] 14-03-PLAN.md — HTML→Editable conversion (Python parser)
- [x] 14-04-PLAN.md — HandoverExportLens component
- [x] 14-05-PLAN.md — Two-bucket storage + API endpoints
- [x] 14-06-PLAN.md — Embedding worker integration
- [x] 14-07-PLAN.md — Ledger integration + navigation
- [x] 14-08-PLAN.md — E2E tests + phase verification

**Success Criteria:**
1. Export button shows "visible in ledger ~5min" (not email).
2. External service called and HTML stored in Bucket 1 (original).
3. HandoverExportLens allows full editing with add/remove sections.
4. User can sign via canvas and submit.
5. HOD notified and can countersign in read-only review mode.
6. Signed content stored in Bucket 2 and indexed for search.
7. All 21 E2E tests pass.

**Status:** ● Complete (2026-02-18)

---

# MILESTONE v1.1 — F1 Search Pipeline Hardening

**Milestone:** v1.1 — F1 Search Pipeline Hardening
**Phases:** 5 (A-E)
**Requirements:** 17

---

## v1.1 Summary

| # | Phase | Goal | Requirements | Status |
|---|-------|------|--------------|--------|
| A | Baseline | Record pre-deploy search metrics | BASE-01, BASE-02, BASE-03, BASE-04 | ○ Pending |
| B | Deploy | Push clean codebase to production | DEPLOY-01, DEPLOY-02, DEPLOY-03, DEPLOY-04 | ○ Pending |
| C | Validate | Run truth sets against new production | VAL-01, VAL-02 | ○ Pending |
| D | Compare | Generate regression report | VAL-03, VAL-04, VAL-05 | ○ Pending |
| E | Iterate | Fix regressions if any | ITER-01, ITER-02, ITER-03, ITER-04 | ○ Pending |

---

## Phase A: Baseline Metrics

**Goal:** Capture search performance metrics from current production before any deployment.

**Requirements:** BASE-01, BASE-02, BASE-03, BASE-04

**Plans:** 1 plan

Plans:
- [ ] A-01-PLAN.md — Create and run search test harness for baseline metrics

**Success Criteria:**
1. Test harness script exists in `/test/` that loads truth set JSONL files
2. Harness calls current production search endpoint with all 2,700 queries
3. Baseline metrics (Recall@3, MRR, p95 latency) recorded to `/test/baseline/`
4. Per-query results logged with expected IDs vs actual IDs
5. Summary report generated showing per-entity-type breakdown

**Output:**
- `/test/search_harness.ts` — Test harness script
- `/test/baseline/metrics.json` — Aggregate metrics
- `/test/baseline/results.jsonl` — Per-query results

**Status:** ○ Pending

---

## Phase B: Deploy Clean Codebase

**Goal:** Push the clean local codebase (18+ commits including AbortError fix) to production.

**Requirements:** DEPLOY-01, DEPLOY-02, DEPLOY-03, DEPLOY-04

**Success Criteria:**
1. Local branch merged to main (direct push or PR as preferred)
2. CI/CD passes: build, lint, type check, tests
3. Production deployment completes (Vercel frontend, Render API)
4. Health check confirms services responding
5. AbortError fix verified in production bundle (source map or behavior test)

**Output:**
- Merge commit or PR URL
- CI/CD pipeline logs
- Health check confirmation

**Status:** ○ Pending

---

## Phase C: Post-Deploy Validation

**Goal:** Run the same truth set queries against new production to capture post-deploy metrics.

**Requirements:** VAL-01, VAL-02

**Success Criteria:**
1. Same test harness used (no changes between baseline and post-deploy)
2. All 2,700 queries executed against production search endpoint
3. Post-deploy metrics recorded to `/test/post-deploy/`
4. Per-query results logged for comparison

**Output:**
- `/test/post-deploy/metrics.json` — Aggregate metrics
- `/test/post-deploy/results.jsonl` — Per-query results

**Status:** ○ Pending

---

## Phase D: Compare and Report

**Goal:** Generate regression report comparing baseline vs post-deploy metrics.

**Requirements:** VAL-03, VAL-04, VAL-05

**Success Criteria:**
1. Comparison script runs diff between baseline and post-deploy results
2. Recall@3 calculated per entity type
3. MRR calculated overall and per entity type
4. p95 latency compared (no increase)
5. Report identifies:
   - Improved queries (new correct results)
   - Regressed queries (lost correct results)
   - Unchanged queries
6. Overall Recall@3 ≥ 90% achieved

**Output:**
- `/test/comparison/report.md` — Human-readable comparison
- `/test/comparison/diff.json` — Machine-readable diff
- `/test/comparison/failures.jsonl` — Failed queries for investigation

**Status:** ○ Pending

---

## Phase E: Iterate on Regressions

**Goal:** If any regressions found, identify root cause, fix, and re-validate.

**Requirements:** ITER-01, ITER-02, ITER-03, ITER-04

**Success Criteria:**
1. Failed queries categorized (embedding issue, SQL issue, timeout, etc.)
2. Root cause identified for each category
3. Fixes applied (if needed)
4. Re-validation shows metrics meet acceptance criteria
5. Final report confirms Recall@3 ≥ 90%, no latency regression

**Output:**
- `/test/iteration/analysis.md` — Root cause analysis
- Fix commits (if needed)
- `/test/final/metrics.json` — Final validated metrics

**Status:** ○ Pending

---

# MILESTONE v1.3 — Actionable UX Unification

**Milestone:** v1.3 — Actionable UX Unification
**Phases:** 5 (15-19)
**Requirements:** 22

---

## v1.3 Phases

- [x] **Phase 15: Intent Envelope** - Create IntentEnvelope abstraction (READ | MUTATE | MIXED) (completed 2026-03-01)
- [x] **Phase 16: Prefill Integration** - Build /v1/actions/prepare endpoint with entity resolution (completed 2026-03-01)
- [x] **Phase 16.1: Mount /prepare Endpoint** - Fix GAP-001, mount endpoint in pipeline_service (completed 2026-03-02)
- [x] **Phase 16.2: Unified Route Architecture** - RouteShell + PermissionService, eliminated 4,262 LOC (completed 2026-03-03)
- [x] **Phase 17: Readiness States** - Implement READY/NEEDS_INPUT/BLOCKED classification (completed 2026-03-02)
- [x] **Phase 18: Route & Disambiguation** - Fragmented URLs + uncertainty surfacing UX (completed 2026-03-02)
- [x] **Phase 19: Agent Deployment** - 24 agents across 4 waves, 614 E2E tests (completed 2026-03-03)

---

## Phase Details

### Phase 15: Intent Envelope

**Goal:** Create IntentEnvelope abstraction that unifies READ and MUTATE intent with deterministic derivation from existing NLP modules.

**Depends on:** Nothing (first phase of v1.3)

**Requirements:** INTENT-01, INTENT-02, INTENT-03

**Success Criteria** (what must be TRUE):
1. User types "show open work orders" and IntentEnvelope captures mode: READ, lens: work_order, filters: {status: "open"}
2. User types "create fault on ME1" and IntentEnvelope captures mode: MUTATE, action_id: "create_fault", entities: {equipment: "ME1"}
3. Same query produces identical IntentEnvelope structure across repeated searches (deterministic output verified)
4. IntentEnvelope includes readiness_state field derived from Action Detector + Entity Extractor outputs

**Plans:** 1/1 plans complete

Plans:
- [x] 15-01-PLAN.md — Define IntentEnvelope type, implement deriveIntentEnvelope function, integrate with search state

---

### Phase 16: Prefill Integration

**Goal:** Build /v1/actions/prepare endpoint that accepts NLP outputs and returns prefilled form previews with entity resolution and confidence scoring.

**Depends on:** Phase 15 (IntentEnvelope must capture entities)

**Requirements:** PREFILL-01, PREFILL-02, PREFILL-03, PREFILL-04, PREFILL-05

**Success Criteria** (what must be TRUE):
1. User query "report critical fault on ME1 tomorrow" triggers /prepare and returns prefill_preview with equipment_id resolved, severity: "critical", scheduled_date: "+1 day ISO"
2. Equipment name "ME1" successfully resolves to UUID via yacht-scoped lookup against production pms_equipment
3. Priority synonym "urgent" maps to ActionPriority.HIGH enum value in prefill response
4. Temporal phrase "next Tuesday" parsed to actual ISO date based on current date
5. Response includes missing_fields: [] when all required fields resolved, or list of field names when incomplete

**Plans:** 2/2 plans complete

Plans:
- [x] 16-01-PLAN.md — Create /v1/actions/prepare endpoint with temporal parsing and priority mapping
- [x] 16-02-PLAN.md — Frontend integration: prepareAction() in useCelesteSearch + ActionModal prefill initialization

---

### Phase 16.1: Mount /prepare Endpoint in pipeline_service

**Goal:** Fix GAP-001 — the /v1/actions/prepare endpoint exists in action_router/router.py but is not mounted in pipeline_service.py, causing 404 errors.

**Depends on:** Phase 16

**Requirements:** MOUNT-01

**Plans:** 1/1 plans complete

Plans:
- [x] 16.1-01-PLAN.md — Copy PrepareRequest/Response models, move prepare_action handler to p0_actions_routes.py, verify via Docker

**Success Criteria:**
1. POST /v1/actions/prepare returns 401 (auth required) not 404
2. Docker local build succeeds
3. OpenAPI schema includes /prepare endpoint
4. Endpoint appears in health check routes

**Status:** ● Complete (2026-03-02)

---

### Phase 16.2: Unified Route Architecture

**Goal:** Eliminate ~4,800 lines of duplicated code in 12 fragmented route pages by introducing RouteShell wrapper that renders existing LensContent components. Also consolidate RBAC from 12 permission hooks into single lens_matrix.json source of truth.

**Depends on:** Phase 16.1 (endpoint must be accessible for action hooks)

**Requirements:**
- ROUTE-ARCH-01: RouteShell component exists and handles feature flag gating ✓
- ROUTE-ARCH-02: usePermissions hook reads RBAC from lens_matrix.json (single source of truth) ✓
- ROUTE-ARCH-03: 11 of 13 fragmented route pages replaced with RouteShell (~27 LOC each) ✓
- ROUTE-ARCH-04: No hardcoded role arrays remain in permission hooks ✓

**Plans:** 1/1 executed (16.2-02/03/04 merged into one-shot execution)

Plans:
- [x] 16.2-01-PLAN.md — Create RouteShell.tsx component + PermissionService

**Execution Summary (2026-03-03):**
- Created RouteShell.tsx (~350 LOC) with feature flag gating, data fetching, LensContent delegation
- Created PermissionService (~200 LOC) reading from lens_matrix.json
- Copied lens_matrix.json to apps/web/src/lib/ (single source of truth)
- Replaced 11 route pages: certificates, documents, equipment, faults, handover-export, hours-of-rest, inventory, receiving, shopping-list, warranties, work-orders
- Skipped 2 routes (email, purchasing) - no LensContent components exist
- **Net reduction: 4,262 LOC → 285 LOC (93% reduction)**

**Success Criteria:**
1. ✅ TypeScript compiles clean with no errors
2. ✅ Feature flag OFF: all routes redirect to /app?entity=
3. ✅ Feature flag ON: all routes render LensContent with working buttons
4. ✅ No hardcoded role arrays remain in permission hooks
5. ✅ lens_matrix.json is single source of truth for RBAC
6. ✅ ~4,262 LOC reduced to ~285 LOC (-93%)

**Status:** ● Complete (2026-03-03)

**Specification:** `/docs/ON_GOING_WORK/BACKEND/LENSES/UNIFIED-ROUTE-ARCHITECTURE.md`

### Phase 17: Readiness States

**Goal:** Implement readiness classification (READY/NEEDS_INPUT/BLOCKED) with visual indicators so users know if an action can execute immediately or requires disambiguation.

**Depends on:** Phase 16 (prefill response must include confidence + missing_fields)

**Requirements:** READY-01, READY-02, READY-03, READY-04

**Success Criteria** (what must be TRUE):
1. Suggested action shows green checkmark when all required_fields resolved with confidence >= 0.8
2. Suggested action shows amber dot when any required field missing or confidence < 0.8
3. Suggested action shows lock icon when user role (crew) attempts Captain-only action (role gating blocks)
4. User can distinguish READY actions from NEEDS_INPUT actions at a glance without clicking modal

**Plans:** 2/2 plans complete

Plans:
- [x] 17-01-PLAN.md — Backend role gating + frontend readiness derivation (READY-01, READY-02, READY-03)
- [x] 17-02-PLAN.md — Visual indicators in SuggestedActions (READY-04)

---

### Phase 18: Route & Disambiguation

**Goal:** Generate canonical segment-based URLs for READ navigation and surface all NLP uncertainty explicitly in the ActionModal for user confirmation.

**Depends on:** Phase 17 (readiness states drive disambiguation UX)

**Requirements:** ROUTE-01, ROUTE-02, ROUTE-03, DISAMB-01, DISAMB-02, DISAMB-03

**Success Criteria** (what must be TRUE):
1. User query "show open work orders" generates navigation to /work-orders/status/open (not /work-orders?status=open)
2. User query "show inventory in box-3d" generates navigation to /inventory/location/box-3d
3. Filter chips in SpotlightSearch reflect canonical route segments visually
4. Ambiguous equipment entity ("ME" matches ME1, ME2) renders dropdown in ActionModal with "Did you mean: ME1 / ME2?"
5. Uncertain date parsing ("next week" -> low confidence) highlights scheduled_date field with warning indicator
6. No silent assumptions made - all low-confidence prefills surface in modal for user confirmation before execution

**Plans:** 2/2 plans complete

Plans:
- [x] 18-01-PLAN.md — Canonical route generation + filter chips (ROUTE-01, ROUTE-02, ROUTE-03)
- [x] 18-02-PLAN.md — Disambiguation UI: AmbiguityDropdown + DateWarning (DISAMB-01, DISAMB-02, DISAMB-03)

---

### Phase 19: Agent Deployment

**Goal:** Execute 24-agent deployment across 4 waves to analyze lenses, generate truth sets, implement backend logic, and create comprehensive E2E test coverage.

**Depends on:** Phase 18 (READ/MUTATE routing and disambiguation UX must exist before E2E testing)

**Requirements:** AGENT-01, AGENT-02, AGENT-03, AGENT-04

**Success Criteria** (what must be TRUE):
1. Wave 1 complete: 12 Lens Matrix agents produce lens_matrix.json with READ filters + MUTATE required_fields for all lenses
2. Wave 2 complete: 12 NLP Variant agents produce intent_truth_set.jsonl with 100 query variants per lens (1,200 total)
3. Wave 3 complete: 12 Backend Integration agents implement /prepare endpoint, entity mappings, readiness classification, role gating per lens
4. Wave 4 complete: 12 E2E Test agents create 50+ Playwright tests per lens (600+ total) covering suggestion -> modal -> execution -> DB verification

**Plans:** 4/4 plans complete

Plans:
- [x] 19-01-PLAN.md — Wave 1: Lens Matrix Analysis (12 agents)
- [x] 19-02-PLAN.md — Wave 2: NLP Variant Generation (12 agents, 1,200 queries)
- [x] 19-03-PLAN.md — Wave 3: Backend Integration (/prepare endpoint per lens)
- [x] 19-04-PLAN.md — Wave 4: E2E Test Coverage (614 Playwright tests)

**Status:** ● Complete (2026-03-03)

---

## v1.3 Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 15. Intent Envelope | 1/1 | Complete | 2026-03-01 |
| 16. Prefill Integration | 2/2 | Complete | 2026-03-01 |
| 16.1. Mount /prepare Endpoint | 1/1 | Complete | 2026-03-02 |
| 16.2. Unified Route Architecture | 1/1 | Complete | 2026-03-03 |
| 17. Readiness States | 2/2 | Complete | 2026-03-02 |
| 18. Route & Disambiguation | 2/2 | Complete | 2026-03-02 |
| 19. Agent Deployment | 4/4 | Complete | 2026-03-03 |

**v1.3 Milestone Status:** ● COMPLETE (7/7 phases, all requirements met)

---

# MILESTONE v1.3.1 — Email Architecture Conversion

**Milestone:** v1.3.1 — Email Architecture Conversion
**Phases:** 1 (20)
**Requirements:** 5

---

## v1.3.1 Summary

| # | Phase | Goal | Requirements | Status |
|---|-------|------|--------------|--------|
| 20 | Email Conversion | Convert Email from single-URL SPA to fragmented route architecture | EMAIL-CONV-01, EMAIL-CONV-02, EMAIL-CONV-03, EMAIL-CONV-04, EMAIL-CONV-05 | ○ Pending |

---

## Phase 20: Email Conversion to Fragmented Route Architecture

**Goal:** Convert Email lens from single-URL SPA pattern (EmailOverlay + SurfaceContext) to fragmented route architecture (RouteShell + EmailLensContent) while preserving all SACRED OAuth/fetch patterns.

**Depends on:** Phase 16.2 (RouteShell pattern must exist)

**Requirements:**
- EMAIL-CONV-01: Create EmailLensContent.tsx wrapper around existing EmailThreadViewer.tsx
- EMAIL-CONV-02: Register Email in LensRenderer.tsx switch statement
- EMAIL-CONV-03: Verify/fix fragmented routes (/email, /email/[threadId]) with RouteShell
- EMAIL-CONV-04: Test button wiring in both SPA and fragmented modes
- EMAIL-CONV-05: Preserve all SACRED OAuth patterns (dual 401 handling, token exchange, refresh buffers)

**SACRED Patterns (DO NOT MODIFY):**
- `oauth-utils.ts` — READ/WRITE app separation, forbidden scopes
- `useEmailData.ts:185-218` — authFetch with dual 401 handling
- `useEmailData.ts:900-996` — useOutlookConnection with 5-minute expiry buffer
- `authHelpers.ts:64-96` — 60-second JWT refresh buffer
- Token exchange location — Render backend only

**Plans:** 0/? plans (to be created)

**Success Criteria:**
1. EmailLensContent.tsx exists and wraps EmailThreadViewer.tsx
2. LensRenderer.tsx includes 'email' case routing to EmailLensContent
3. /email route renders via RouteShell + EmailLensContent
4. /email/[threadId] route renders specific thread
5. All 7 email actions from lens_matrix.json work in both modes
6. OAuth flow works identically in both SPA and fragmented modes
7. No modifications to SACRED patterns (verified via git diff)

**Status:** ○ Pending

---

*Created: 2026-02-17*
*Updated: 2026-03-01 — v1.3 Actionable UX Unification roadmap added (phases 15-19)*
*Updated: 2026-03-01 — Phase 15 plan created (15-01-PLAN.md)*
*Updated: 2026-03-01 — Phase 16 plans created (16-01-PLAN.md, 16-02-PLAN.md)*
*Updated: 2026-03-01 — Phase 17 plans created (17-01-PLAN.md, 17-02-PLAN.md)*
*Updated: 2026-03-02 — Phase 18 plans created (18-01-PLAN.md, 18-02-PLAN.md)*
*Updated: 2026-03-02 — Phase 19 plans created (19-01-PLAN.md through 19-04-PLAN.md)*
