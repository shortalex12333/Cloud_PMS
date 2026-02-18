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

*Created: 2026-02-17*
*Updated: 2026-02-18 — Phase 14 planned*
