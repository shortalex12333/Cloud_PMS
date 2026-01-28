# Entity Lens Maturity Matrix

**Updated**: 2026-01-27 (post-Certificates gold)

This document provides a holistic view of all entity lenses, their current state, and what's needed to bring each to production quality.

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Total Lenses Required | 10 |
| Production Ready (Gold) | 1 (Certificates) |
| Has Code Implementation | 2 (Certificates, Work Order partial) |
| Documentation Only | 7 |
| Not Started | 1 (Inventory - has docs but outdated) |

---

## The 10 Entity Lenses

| # | Lens | Maturity | Lines | Has v2? | Has Code? | Has Tests? | Frontend? |
|---|------|----------|-------|---------|-----------|------------|-----------|
| 1 | **Certificate** | GOLD | 500+ | ✅ Yes | ✅ Yes | ✅ 18 pass | ✅ Yes |
| 2 | Work Order | ALPHA | 436 | ✅ Yes | Partial | ❌ No | ❌ No |
| 3 | Fault | ALPHA | 1228 | ❌ No | ❌ No | ❌ No | ❌ No |
| 4 | Equipment | ALPHA | 868 | ❌ No | ❌ No | ❌ No | ❌ No |
| 5 | Part | ALPHA | 910 | ❌ No | ❌ No | ❌ No | ❌ No |
| 6 | Inventory Item | DRAFT | 1967 | ❌ No | ❌ No | ❌ No | ❌ No |
| 7 | Receiving | DRAFT | 450 | ❌ No | ❌ No | ❌ No | ❌ No |
| 8 | Shopping List | DRAFT | 439 | ❌ No | ❌ No | ❌ No | ❌ No |
| 9 | Document | STUB | 208 | ❌ No | ❌ No | ❌ No | ❌ No |
| 10 | Crew | STUB | 253 | ❌ No | ❌ No | ❌ No | ❌ No |

### Maturity Levels

- **GOLD**: Full implementation, tests passing, frontend integrated, CI gates
- **BETA**: Code exists, tests written but not all passing
- **ALPHA**: Good documentation (800+ lines), no code
- **DRAFT**: Partial documentation (400-800 lines), needs expansion
- **STUB**: Minimal documentation (<400 lines), needs significant work

---

## Lens Detail Breakdown

### 1. Certificate Lens - GOLD ✅

**Status**: Production ready. Reference implementation for other lenses.

| Component | Status | Location |
|-----------|--------|----------|
| Lens Spec | ✅ v2 Complete | `docs/pipeline/entity_lenses/certificate_lens/v2/` |
| Backend Actions | ✅ 5 actions | `apps/api/action_router/registry.py` |
| Endpoint | ✅ `/v1/actions/list` | `apps/api/routes/p0_actions_routes.py:4148` |
| Handlers | ✅ Complete | `apps/api/handlers/certificate_handlers.py` |
| Tests | ✅ 18 passing | `tests/docker/run_rls_tests.py` |
| Frontend | ✅ Complete | `SuggestedActions.tsx`, `ActionModal.tsx` |
| CI | ✅ Staging gate | `.github/workflows/staging-certificates-acceptance.yml` |

**Actions**:
- `create_vessel_certificate` (MUTATE)
- `create_crew_certificate` (MUTATE)
- `update_certificate` (MUTATE)
- `link_document_to_certificate` (MUTATE)
- `supersede_certificate` (SIGNED)

---

### 2. Work Order Lens - ALPHA

**Status**: Best documented but code not wired to new pipeline.

| Component | Status | Location |
|-----------|--------|----------|
| Lens Spec | ✅ v2 Complete | `docs/pipeline/entity_lenses/work_order_lens/v2/` |
| Backend Actions | ⚠️ Partial | Handlers exist but not in registry with domain/variant |
| Endpoint | ❌ Not integrated | Actions exist but not in `/v1/actions/list` |
| Tests | ❌ No action list tests | - |
| Frontend | ❌ Not wired | - |

**Gap**: Has 8-phase documentation (excellent) but needs:
1. Add `domain: "work_orders"` and `variant` to existing actions in registry
2. Add work order actions to `search_actions()` flow
3. Wire frontend detection for work order intent
4. Add tests

**Documented Actions** (need code):
- `create_work_order`
- `update_work_order`
- `complete_work_order`
- `add_note`
- `reassign_work_order`
- `archive_work_order`

---

### 3. Fault Lens - ALPHA

**Status**: Extensive documentation (1228 lines), no code.

| Component | Status | Notes |
|-----------|--------|-------|
| Lens Spec | ✅ v5 Final | Most thorough documentation |
| Code | ❌ None | Needs handler + registry |

**Gap**: Pure documentation. Needs full pipeline implementation.

**Documented Actions**:
- `report_fault`
- `acknowledge_fault`
- `update_fault`
- `close_fault`
- `reopen_fault`
- `mark_false_alarm`

---

### 4. Equipment Lens - ALPHA

**Status**: Good documentation (868 lines), no code.

| Component | Status | Notes |
|-----------|--------|-------|
| Lens Spec | ✅ v1 Final | Solid depth |
| Code | ❌ None | Needs handler + registry |

**Gap**: Read-heavy lens with minimal mutations.

**Documented Actions**:
- `view_equipment`
- `add_note`
- `update_status`
- `link_document`

---

### 5. Part Lens - ALPHA

**Status**: Good documentation (910 lines), no code.

| Component | Status | Notes |
|-----------|--------|-------|
| Lens Spec | ✅ v1 Final | Excellent depth with SQL |
| Code | ❌ None | Needs handler + registry |

**Documented Actions**:
- `adjust_stock_quantity`
- `create_purchase_request`
- `receive_parts`
- `transfer_parts`
- `view_stock_history`

---

### 6. Inventory Item Lens - DRAFT

**Status**: Multiple versions, confusing state.

| Component | Status | Notes |
|-----------|--------|-------|
| Lens Spec | ⚠️ v3 Enhanced exists | 1967 lines but may be outdated |
| Code | ❌ None | - |

**Gap**: Three versions exist (v1, v2, v3_ENHANCED). Need to consolidate and verify against current DB truth.

---

### 7. Receiving Lens - DRAFT

**Status**: Partial documentation (450 lines).

| Component | Status | Notes |
|-----------|--------|-------|
| Lens Spec | ⚠️ v1 Final | Below gold standard depth |
| Code | ❌ None | - |

**Gap**: Needs expansion to 800+ lines with full SQL patterns.

---

### 8. Shopping List Lens - DRAFT

**Status**: Partial documentation (439 lines).

| Component | Status | Notes |
|-----------|--------|-------|
| Lens Spec | ⚠️ v1 Final | Below gold standard depth |
| Code | ❌ None | - |

**Gap**: Needs expansion to 800+ lines with full SQL patterns.

---

### 9. Document Lens - STUB

**Status**: Minimal documentation (208 lines). Needs significant work.

| Component | Status | Notes |
|-----------|--------|-------|
| Lens Spec | ❌ Inadequate | Only 17% of gold standard depth |
| Code | ❌ None | - |

**Gap**: Missing action SQL, field classifications, business rules, scenarios.

---

### 10. Crew Lens - STUB

**Status**: Minimal documentation (253 lines). Needs significant work.

| Component | Status | Notes |
|-----------|--------|-------|
| Lens Spec | ❌ Inadequate | Only 21% of gold standard depth |
| Code | ❌ None | - |

**Gap**: Missing role hierarchy, invitation flow, profile update rules.

---

## Implementation Priority

Based on user journeys and dependencies:

### Priority 1: Core Operational (Ship Now)
| Lens | Reason | Effort |
|------|--------|--------|
| Work Order | Core operations, handlers exist | Low (wire to pipeline) |
| Fault | Directly linked to WO | Medium |

### Priority 2: Inventory Flow
| Lens | Reason | Effort |
|------|--------|--------|
| Part | Stock management | Medium |
| Inventory Item | Low stock alerts | Medium |
| Receiving | Part arrival | Medium |
| Shopping List | Procurement | Medium |

### Priority 3: Reference Data
| Lens | Reason | Effort |
|------|--------|--------|
| Equipment | Read-heavy, low mutations | Low |
| Document | File management | Medium |
| Crew | User profiles | Low |

---

## What Each Lens Needs

### To Reach ALPHA (Documentation Complete)

| Lens | Action |
|------|--------|
| Document | +600 lines: SQL, field classifications, scenarios |
| Crew | +650 lines: SQL, role hierarchy, invitation flow |
| Receiving | +350 lines: More scenarios, edge cases |
| Shopping List | +350 lines: More scenarios, edge cases |
| Inventory Item | Consolidate v1/v2/v3, verify DB truth |

### To Reach BETA (Code Exists)

For each lens:
1. Add actions to `apps/api/action_router/registry.py` with domain/variant/search_keywords
2. Create or verify handlers in `apps/api/handlers/<lens>_handlers.py`
3. Add to `search_actions()` flow
4. Add intent detection in `useCelesteSearch.ts`

### To Reach GOLD (Production Ready)

For each lens:
1. Write tests in `tests/docker/run_rls_tests.py`
2. Add CI assertions in `tests/ci/staging_<lens>_acceptance.py`
3. Verify frontend integration
4. Pass all tests
5. Tag release

---

## Effort Estimate

| Phase | Lenses | Estimated Work |
|-------|--------|----------------|
| Documentation expansion | Document, Crew | 2 days |
| Wire Work Order to pipeline | Work Order | 0.5 days |
| Fault implementation | Fault | 2 days |
| Part + Inventory | Part, Inventory | 3 days |
| Receiving + Shopping | Receiving, Shopping List | 2 days |
| Equipment + Document | Equipment, Document | 2 days |
| Crew | Crew | 1 day |
| **Total** | 9 remaining lenses | ~12-15 days |

---

## Cross-Lens Dependencies

```
Certificate ─────────────────────────────────────────────►
     │
     └──► Document (link_document_to_certificate)

Work Order ──────────────────────────────────────────────►
     │
     ├──► Part (add_parts_to_work_order)
     ├──► Fault (create_work_order_from_fault)
     └──► Equipment (via FK)

Fault ───────────────────────────────────────────────────►
     │
     └──► Equipment (fault.equipment_id FK)

Part ────────────────────────────────────────────────────►
     │
     ├──► Inventory Item (stock levels)
     ├──► Receiving (receive_parts)
     └──► Shopping List (reorder)
```

---

## Files to Reference

| Purpose | Location |
|---------|----------|
| Certificate implementation (GOLD standard) | `apps/api/action_router/registry.py` (lines 393-490) |
| Endpoint pattern | `apps/api/routes/p0_actions_routes.py:4148` |
| Test pattern | `tests/docker/run_rls_tests.py` (test_action_list_*) |
| Frontend pattern | `apps/web/src/hooks/useCelesteSearch.ts` |

---

## Recommendation

**Start with Work Order** - It has the best documentation and partial code. Wiring it to the new pipeline (domain/variant, frontend intent detection) validates the pattern with minimal risk before applying to other lenses.

After Work Order, do **Fault** (high operational value, linked to WO).

Then batch the **inventory flow** lenses together (Part → Inventory → Receiving → Shopping) since they share concepts.

Leave **Document**, **Crew**, and **Equipment** for last as they're simpler and lower operational priority.
