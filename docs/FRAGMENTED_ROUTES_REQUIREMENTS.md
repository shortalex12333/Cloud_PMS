# REQUIREMENTS TABLE — Fragmented Routes Migration

> **Single Source of Truth**: This table is authoritative. Nothing is DONE without test/proof link.

## Status Codes
- `NOT_STARTED` - Work not begun
- `IN_PROGRESS` - Active development
- `BLOCKED` - Cannot proceed (reason required)
- `DONE` - Implementation complete
- `DONE_VERIFIED` - Playwright + manual spot check passed
- `DEFERRED` - Postponed (reason + owner required)

---

## Global Guardrails (Non-negotiable)

| Req ID | Requirement | Owner Agent | Status | Test/Proof | Notes |
|--------|-------------|-------------|--------|------------|-------|
| GR-01 | No route-specific backend endpoints introduced | API Guardian | DONE_VERIFIED | All routes use /v1/entity/* and /v1/actions/execute | Backend stays unified |
| GR-02 | All mutations go through POST /v1/actions/execute | MicroAction Core | DONE_VERIFIED | Tests use executeApiAction helper | No bypass in new routes |
| GR-03 | Remove single-URL NavigationContext stack | State Agent | DONE_VERIFIED | grep: no NavigationContext in routes | Browser history only |
| GR-04 | Shared entity cache via React Query across routes | State Agent | DONE_VERIFIED | All routes use useQuery | staleTime: 30000ms |
| GR-05 | Browser back/forward works naturally | Routing Agent | DONE_VERIFIED | shard-31: GR-05 tests + HTTP 200 verified | Native routing |
| GR-06 | RLS blockers fixed before Tier 1 migration | Security Agent | DONE_VERIFIED | Migration 20260226_001 deployed | BLOCKER RESOLVED |

---

## RLS Security Fixes (Must complete before Tier 1)

| Req ID | Requirement | Owner Agent | Status | Test/Proof | Notes |
|--------|-------------|-------------|--------|------------|-------|
| RLS-01 | Fix pms_work_order_notes: remove USING(true) | Security Agent | DONE_VERIFIED | Migration 20260226_001 + DB verification | Dropped insecure policy |
| RLS-02 | Fix pms_work_order_parts: remove USING(true) | Security Agent | DONE_VERIFIED | DB query: already secure | No insecure policy found |
| RLS-03 | Fix pms_part_usage: remove USING(true) | Security Agent | DONE_VERIFIED | DB query: already secure | No insecure policy found |
| RLS-04 | Enable RLS on pms_inventory_transactions | Security Agent | DONE_VERIFIED | DB query: relrowsecurity=true | Already enabled with FORCE |
| RLS-05 | Verify yacht isolation with test queries | Security Agent | DONE_VERIFIED | All SELECT policies yacht-isolated | Duplicate policies cleaned up |

---

## Feature Flag

| Req ID | Requirement | Owner Agent | Status | Test/Proof | Notes |
|--------|-------------|-------------|--------|------------|-------|
| FF-01 | FRAGMENTED_ROUTES_ENABLED env flag gates new routes | Routing Agent | DONE_VERIFIED | src/lib/featureFlags.ts + production deploy | Build-time resolution |
| FF-02 | Legacy /app remains accessible during migration | Routing Agent | DONE_VERIFIED | Legacy route untouched | Coexistence enabled |

---

## Route Layout Template

| Req ID | Requirement | Owner Agent | Status | Test/Proof | Notes |
|--------|-------------|-------------|--------|------------|-------|
| LT-01 | Shared RouteLayout component implemented | Layout Agent | DONE_VERIFIED | src/components/layout/RouteLayout.tsx deployed | Single skeleton |
| LT-02 | LensHeader/VitalSignsRow/StatusPill preserved | Layout Agent | DONE_VERIFIED | Reuses existing components | No design changes |
| LT-03 | TopNav + SearchBar in layout | Layout Agent | DONE_VERIFIED | TopNav in RouteLayout | Global search preserved |

---

## Tier 1 Routes — Work Orders

| Req ID | Requirement | Owner Agent | Status | Test/Proof | Notes |
|--------|-------------|-------------|--------|------------|-------|
| T1-WO-01 | /work-orders list route loads | WO Agent | DONE_VERIFIED | HTTP 200 + shard-31 tests | Production verified |
| T1-WO-02 | /work-orders/[id] detail route loads | WO Agent | DONE_VERIFIED | shard-31: T1-WO-02 | Production verified |
| T1-WO-03 | WO create mutation works | WO Agent | DONE_VERIFIED | shard-31: T1-WO-03 | Uses /v1/actions/execute |
| T1-WO-04 | WO update mutation works | WO Agent | DONE_VERIFIED | shard-31: T1-WO-04 | Uses /v1/actions/execute |
| T1-WO-05 | WO complete mutation works | WO Agent | DONE_VERIFIED | shard-31: T1-WO-05 | Uses /v1/actions/execute |
| T1-WO-06 | WO links to equipment navigates correctly | WO Agent | DONE_VERIFIED | shard-31: T1-WO-06 | Cross-route navigation |
| T1-WO-07 | Page refresh preserves state | WO Agent | DONE_VERIFIED | shard-31: T1-WO-07 | URL-based state |
| T1-WO-08 | No SurfaceContext dependency | WO Agent | DONE_VERIFIED | grep: no imports found | Code verified |
| T1-WO-09 | No NavigationContext coupling | WO Agent | DONE_VERIFIED | grep: no imports found | Code verified |

---

## Tier 1 Routes — Faults

| Req ID | Requirement | Owner Agent | Status | Test/Proof | Notes |
|--------|-------------|-------------|--------|------------|-------|
| T1-F-01 | /faults list route loads | Fault Agent | DONE_VERIFIED | HTTP 200 + shard-31 tests | Production verified |
| T1-F-02 | /faults/[id] detail route loads | Fault Agent | DONE_VERIFIED | shard-31: route-faults.spec.ts | Production verified |
| T1-F-03 | Fault create mutation works | Fault Agent | DONE_VERIFIED | shard-31: route-faults.spec.ts | Uses /v1/actions/execute |
| T1-F-04 | Fault status update works | Fault Agent | DONE_VERIFIED | shard-31: route-faults.spec.ts | Uses /v1/actions/execute |
| T1-F-05 | Link equipment to fault works | Fault Agent | DONE_VERIFIED | shard-31: route-faults.spec.ts | Cross-route navigation |
| T1-F-06 | Convert to WO action works | Fault Agent | DONE_VERIFIED | shard-31: route-faults.spec.ts | Uses /v1/actions/execute |
| T1-F-07 | Page refresh preserves state | Fault Agent | DONE_VERIFIED | shard-31: route-faults.spec.ts | URL-based state |

---

## Tier 1 Routes — Equipment

| Req ID | Requirement | Owner Agent | Status | Test/Proof | Notes |
|--------|-------------|-------------|--------|------------|-------|
| T1-EQ-01 | /equipment list route loads | Equipment Agent | DONE_VERIFIED | HTTP 200 + shard-31 tests | Production verified |
| T1-EQ-02 | /equipment/[id] detail route loads | Equipment Agent | DONE_VERIFIED | shard-31: route-equipment.spec.ts | Production verified |
| T1-EQ-03 | Linked WOs render in detail | Equipment Agent | DONE_VERIFIED | shard-31: route-equipment.spec.ts | Cross-entity display |
| T1-EQ-04 | Linked faults render in detail | Equipment Agent | DONE_VERIFIED | shard-31: route-equipment.spec.ts | Cross-entity display |
| T1-EQ-05 | Linked parts render in detail | Equipment Agent | DONE_VERIFIED | shard-31: route-equipment.spec.ts | Cross-entity display |
| T1-EQ-06 | Equipment status update works | Equipment Agent | DONE_VERIFIED | shard-31: route-equipment.spec.ts | Uses /v1/actions/execute |
| T1-EQ-07 | Page refresh preserves state | Equipment Agent | DONE_VERIFIED | shard-31: route-equipment.spec.ts | URL-based state |

---

## Tier 1 Routes — Inventory

| Req ID | Requirement | Owner Agent | Status | Test/Proof | Notes |
|--------|-------------|-------------|--------|------------|-------|
| T1-INV-01 | /inventory list route loads | Inventory Agent | DONE_VERIFIED | HTTP 200 + shard-31 tests | Production verified |
| T1-INV-02 | /inventory/[id] detail route loads | Inventory Agent | DONE_VERIFIED | shard-31: route-inventory.spec.ts | Production verified |
| T1-INV-03 | Transactions visible (RLS safe) | Inventory Agent | DONE_VERIFIED | shard-31: route-inventory.spec.ts | RLS-04 verified |
| T1-INV-04 | Stock locations visible | Inventory Agent | DONE_VERIFIED | shard-31: route-inventory.spec.ts | Production verified |
| T1-INV-05 | Low stock indicators work | Inventory Agent | DONE_VERIFIED | shard-31: route-inventory.spec.ts | Production verified |
| T1-INV-06 | Add to shopping list action works | Inventory Agent | DONE_VERIFIED | shard-31: route-inventory.spec.ts | Uses /v1/actions/execute |
| T1-INV-07 | Page refresh preserves state | Inventory Agent | DONE_VERIFIED | shard-31: route-inventory.spec.ts | URL-based state |

---

## Playwright Test Infrastructure

| Req ID | Requirement | Owner Agent | Status | Test/Proof | Notes |
|--------|-------------|-------------|--------|------------|-------|
| PW-01 | Route-based test structure created | Test Agent | DONE_VERIFIED | shard-31-fragmented-routes/ | Directory created |
| PW-02 | Test fixtures for seeded data | Test Agent | DONE_VERIFIED | rbac-fixtures.ts | seedWorkOrder, seedFault |
| PW-03 | Tests isolated per route | Test Agent | DONE_VERIFIED | route-workorders.spec.ts | No cross-route state |
| PW-04 | Tests non-flaky | Test Agent | DONE_VERIFIED | 45/45 passed | Production verified |

---

## Merge Order (Enforced)

1. Security (RLS fixes) - **DONE_VERIFIED**
2. Layout template - **DONE_VERIFIED**
3. Routing + feature flag - **DONE_VERIFIED**
4. Work Orders - **DONE_VERIFIED**
5. Faults - **DONE_VERIFIED**
6. Equipment - **DONE_VERIFIED**
7. Inventory - **DONE_VERIFIED**
8. Email - NOT_STARTED

**No skipping. No parallel merges on conflicting files.**

---

*Last Updated: 2026-02-26 14:55 UTC*
*Deployment: dpl_4hEPqn22qDN7NPpgm6j6bRbmvCbz*
*PRs: #383, #384 merged to main*
