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
| GR-01 | No route-specific backend endpoints introduced | API Guardian | NOT_STARTED | Diff scan: no new /v1/* route endpoints | Backend stays unified |
| GR-02 | All mutations go through POST /v1/actions/execute | MicroAction Core | NOT_STARTED | Playwright: mutation uses actions/execute | No bypass allowed |
| GR-03 | Remove single-URL NavigationContext stack | State Agent | NOT_STARTED | Code search: no custom back stack used | Use browser history |
| GR-04 | Shared entity cache via React Query across routes | State Agent | NOT_STARTED | Devtools: cache persists cross-route | No global UI state |
| GR-05 | Browser back/forward works naturally | Routing Agent | NOT_STARTED | Playwright: back/forward assertions | Native routing |
| GR-06 | RLS blockers fixed before Tier 1 migration | Security Agent | NOT_STARTED | SQL policy diff + test: cross-yacht denied | **CRITICAL BLOCKER** |

---

## RLS Security Fixes (Must complete before Tier 1)

| Req ID | Requirement | Owner Agent | Status | Test/Proof | Notes |
|--------|-------------|-------------|--------|------------|-------|
| RLS-01 | Fix pms_work_order_notes: remove USING(true) | Security Agent | NOT_STARTED | SQL: cross-yacht SELECT returns 0 rows | CRITICAL |
| RLS-02 | Fix pms_work_order_parts: remove USING(true) | Security Agent | NOT_STARTED | SQL: cross-yacht SELECT returns 0 rows | CRITICAL |
| RLS-03 | Fix pms_part_usage: remove USING(true) | Security Agent | NOT_STARTED | SQL: cross-yacht SELECT returns 0 rows | CRITICAL |
| RLS-04 | Enable RLS on pms_inventory_transactions | Security Agent | NOT_STARTED | SQL: relrowsecurity = true | CRITICAL |
| RLS-05 | Verify yacht isolation with test queries | Security Agent | NOT_STARTED | Test script output logged | Regression proof |

---

## Feature Flag

| Req ID | Requirement | Owner Agent | Status | Test/Proof | Notes |
|--------|-------------|-------------|--------|------------|-------|
| FF-01 | FRAGMENTED_ROUTES_ENABLED env flag gates new routes | Routing Agent | NOT_STARTED | Toggle flag: routes appear/disappear | Build-time resolution |
| FF-02 | Legacy /app remains accessible during migration | Routing Agent | NOT_STARTED | Manual: /app loads correctly | Coexistence required |

---

## Route Layout Template

| Req ID | Requirement | Owner Agent | Status | Test/Proof | Notes |
|--------|-------------|-------------|--------|------------|-------|
| LT-01 | Shared RouteLayout component implemented | Layout Agent | NOT_STARTED | Snapshot: layout identical across routes | Single skeleton |
| LT-02 | LensHeader/VitalSignsRow/StatusPill preserved | Layout Agent | NOT_STARTED | Visual parity checklist | No design changes |
| LT-03 | TopNav + SearchBar in layout | Layout Agent | NOT_STARTED | Component renders in all routes | Global search preserved |

---

## Tier 1 Routes — Work Orders

| Req ID | Requirement | Owner Agent | Status | Test/Proof | Notes |
|--------|-------------|-------------|--------|------------|-------|
| T1-WO-01 | /work-orders list route loads | WO Agent | NOT_STARTED | PW: list renders with items | |
| T1-WO-02 | /work-orders/[id] detail route loads | WO Agent | NOT_STARTED | PW: detail renders correct entity | |
| T1-WO-03 | WO create mutation works | WO Agent | NOT_STARTED | PW: create + audit log exists | |
| T1-WO-04 | WO update mutation works | WO Agent | NOT_STARTED | PW: update + audit log exists | |
| T1-WO-05 | WO complete mutation works | WO Agent | NOT_STARTED | PW: complete + status changes | |
| T1-WO-06 | WO links to equipment navigates correctly | WO Agent | NOT_STARTED | PW: click equipment → /equipment/[id] | |
| T1-WO-07 | Page refresh preserves state | WO Agent | NOT_STARTED | PW: reload → same data visible | |
| T1-WO-08 | No SurfaceContext dependency | WO Agent | NOT_STARTED | Code search: no SurfaceContext import | |
| T1-WO-09 | No NavigationContext coupling | WO Agent | NOT_STARTED | Code search: no nav stack usage | |

---

## Tier 1 Routes — Faults

| Req ID | Requirement | Owner Agent | Status | Test/Proof | Notes |
|--------|-------------|-------------|--------|------------|-------|
| T1-F-01 | /faults list route loads | Fault Agent | NOT_STARTED | PW: list renders with items | |
| T1-F-02 | /faults/[id] detail route loads | Fault Agent | NOT_STARTED | PW: detail renders correct entity | |
| T1-F-03 | Fault create mutation works | Fault Agent | NOT_STARTED | PW: create + audit log exists | |
| T1-F-04 | Fault status update works | Fault Agent | NOT_STARTED | PW: status change persists | |
| T1-F-05 | Link equipment to fault works | Fault Agent | NOT_STARTED | PW: equipment linked | |
| T1-F-06 | Convert to WO action works | Fault Agent | NOT_STARTED | PW: WO created from fault | |
| T1-F-07 | Page refresh preserves state | Fault Agent | NOT_STARTED | PW: reload → same data visible | |

---

## Tier 1 Routes — Equipment

| Req ID | Requirement | Owner Agent | Status | Test/Proof | Notes |
|--------|-------------|-------------|--------|------------|-------|
| T1-EQ-01 | /equipment list route loads | Equipment Agent | NOT_STARTED | PW: list renders with items | |
| T1-EQ-02 | /equipment/[id] detail route loads | Equipment Agent | NOT_STARTED | PW: detail renders correct entity | |
| T1-EQ-03 | Linked WOs render in detail | Equipment Agent | NOT_STARTED | PW: WO list visible | |
| T1-EQ-04 | Linked faults render in detail | Equipment Agent | NOT_STARTED | PW: fault list visible | |
| T1-EQ-05 | Linked parts render in detail | Equipment Agent | NOT_STARTED | PW: parts BOM visible | |
| T1-EQ-06 | Equipment status update works | Equipment Agent | NOT_STARTED | PW: status change + audit | |
| T1-EQ-07 | Page refresh preserves state | Equipment Agent | NOT_STARTED | PW: reload → same data visible | |

---

## Tier 1 Routes — Inventory

| Req ID | Requirement | Owner Agent | Status | Test/Proof | Notes |
|--------|-------------|-------------|--------|------------|-------|
| T1-INV-01 | /inventory list route loads | Inventory Agent | NOT_STARTED | PW: list renders with items | |
| T1-INV-02 | /inventory/[id] detail route loads | Inventory Agent | NOT_STARTED | PW: detail renders correct entity | |
| T1-INV-03 | Transactions visible (RLS safe) | Inventory Agent | NOT_STARTED | PW: transactions list renders | Depends on RLS-04 |
| T1-INV-04 | Stock locations visible | Inventory Agent | NOT_STARTED | PW: multi-location breakdown | |
| T1-INV-05 | Low stock indicators work | Inventory Agent | NOT_STARTED | PW: warning shown when qty <= min | |
| T1-INV-06 | Add to shopping list action works | Inventory Agent | NOT_STARTED | PW: item added + audit | |
| T1-INV-07 | Page refresh preserves state | Inventory Agent | NOT_STARTED | PW: reload → same data visible | |

---

## Email Route

| Req ID | Requirement | Owner Agent | Status | Test/Proof | Notes |
|--------|-------------|-------------|--------|------------|-------|
| EM-01 | /email route loads | Email Agent | NOT_STARTED | PW: email list renders | |
| EM-02 | Email detail view works | Email Agent | NOT_STARTED | PW: email content displays | |
| EM-03 | Link email to entity modal works | Email Agent | NOT_STARTED | PW: modal opens, search works | |
| EM-04 | Link action creates association | Email Agent | NOT_STARTED | PW: link persists + cache invalidated | |
| EM-05 | Page refresh preserves state | Email Agent | NOT_STARTED | PW: reload → same data visible | |

---

## Playwright Test Infrastructure

| Req ID | Requirement | Owner Agent | Status | Test/Proof | Notes |
|--------|-------------|-------------|--------|------------|-------|
| PW-01 | Route-based test structure created | Test Agent | NOT_STARTED | Directory: /tests/work-orders/ etc | |
| PW-02 | Test fixtures for seeded data | Test Agent | NOT_STARTED | Fixtures file exists | |
| PW-03 | Tests isolated per route | Test Agent | NOT_STARTED | No cross-route state dependency | |
| PW-04 | Tests non-flaky | Test Agent | NOT_STARTED | 3 consecutive passes | |

---

## Merge Order (Enforced)

1. Security (RLS fixes) - **MUST BE FIRST**
2. Layout template
3. Routing + feature flag
4. Work Orders
5. Faults
6. Equipment
7. Inventory
8. Email

**No skipping. No parallel merges on conflicting files.**

---

*Last Updated: 2026-02-26*
