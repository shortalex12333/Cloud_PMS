# STATE — Current Session Memory

> **This file tracks decisions, blockers, and position across sessions.**
>
> Last Updated: 2026-02-17

---

## Current Position

| Field | Value |
|-------|-------|
| Milestone | v1.0 — Lens Completion |
| Phase | 00 (Design System) |
| Plan | 05 of 5 COMPLETE |
| Status | DS-05 complete - email integration dead code removed, build passes |
| Last activity | 2026-02-17 — Completed 00-05 (remove email integration feature flag dead code) |

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

**Phase 00-design-system COMPLETE - all 5 plans executed. Ready for next phase.**

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

