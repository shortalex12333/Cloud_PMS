# AGENT CHECKLISTS — Microtask Doctrine

> **Purpose**: Forces every sub-agent to do tiny tasks, in the same format, with clear Definition of Done.

---

## Global Rules for Sub-Agents

1. **One agent = one lens OR one system concern**
2. **One task = one PR-sized change (small)**
3. **Every task must end with**:
   - Tests executed
   - Proof artifact (screenshot/log)
   - Updated REQUIREMENTS_TABLE row status

---

## Task Template (MANDATORY)

```markdown
### Task ID: <e.g., T1-WO-01>
- **Goal** (1 sentence):
- **Scope IN**:
- **Scope OUT**:
- **Files expected to change**:
- **Success criteria**:
- **Tests to run** (exact commands):
- **Proof required** (screenshot/log link):
- **Rollback plan**:
```

---

## Concurrency Rules (HARD)

Only **TWO agents** can touch shared files at once:
- RouteLayout
- Router config
- React Query provider / app shell

Everyone else works **lens-local**.

---

## Merge Discipline (ENFORCED)

Merge order MUST be:
1. Security (RLS)
2. Layout template
3. Routing + flag
4. WorkOrders
5. Faults
6. Equipment
7. Inventory
8. Email

**No skipping.**

---

## Anti-Token-Waste Rule

Sub-agent tasks must be **small and testable**.

If a task can't be tested in isolation, it's **too big**.

Split it.

---

## Agent Roles & Boundaries

### Orchestrator (Claude main)
- **Owns**: Task assignment, merge order, conflict prevention
- **Must**: Keep REQUIREMENTS_TABLE authoritative
- **Must**: Stop parallel work if conflicts appear
- **DoD**: All agents complete their tasks, all reqs DONE_VERIFIED

### Security Agent
- **Owns**: RLS policy fixes and regression tests
- **Scope**:
  - pms_work_order_notes
  - pms_work_order_parts
  - pms_part_usage
  - pms_inventory_transactions
- **DoD**: Cross-yacht reads are impossible in staging + local checks documented
- **Req IDs**: RLS-01, RLS-02, RLS-03, RLS-04, RLS-05, GR-06

### Layout Agent
- **Owns**: RouteLayout + shared UI skeleton
- **Scope**:
  - RouteLayout component
  - TopNav component
  - SearchBar integration
  - Shared CSS tokens
- **DoD**: All Tier 1 routes reuse template without drift
- **Req IDs**: LT-01, LT-02, LT-03

### Routing Agent
- **Owns**: Route scaffolding + feature flag gating + legacy /app coexistence
- **Scope**:
  - Route definitions
  - FRAGMENTED_ROUTES_ENABLED flag
  - Legacy route preservation
- **DoD**: FRAGMENTED_ROUTES_ENABLED toggles routes deterministically
- **Req IDs**: FF-01, FF-02, GR-05

### State Agent
- **Owns**: React Query cache strategy + route-local state
- **Scope**:
  - QueryProvider configuration
  - Cache invalidation patterns
  - Remove NavigationContext coupling
  - Remove SurfaceContext dependency
- **DoD**: No global UI state resurrected; cache persists across routes
- **Req IDs**: GR-03, GR-04

### WorkOrder Agent
- **Owns**: /work-orders list + /work-orders/[id] detail + mutations
- **Scope**:
  - List page component
  - Detail page component
  - All WO mutations via /v1/actions/execute
  - Audit log verification
- **DoD**: Playwright passes for list/detail/mutation/refresh
- **Req IDs**: T1-WO-01 through T1-WO-09

### Fault Agent
- **Owns**: /faults list + /faults/[id] detail + mutations
- **Scope**: Same pattern as WorkOrder
- **DoD**: Playwright passes for list/detail/mutation/refresh
- **Req IDs**: T1-F-01 through T1-F-07

### Equipment Agent
- **Owns**: /equipment list + /equipment/[id] detail + mutations
- **Scope**: Same pattern as WorkOrder
- **DoD**: Playwright passes for list/detail/mutation/refresh
- **Req IDs**: T1-EQ-01 through T1-EQ-07

### Inventory Agent
- **Owns**: /inventory list + /inventory/[id] detail + mutations
- **Scope**: Same pattern as WorkOrder
- **DoD**: Playwright passes for list/detail/mutation/refresh
- **Req IDs**: T1-INV-01 through T1-INV-07

### Email Agent
- **Owns**: /email route + link-to-entity flow
- **Scope**:
  - Email list page
  - Email detail view
  - Link to entity modal
  - Cache invalidation on link
- **DoD**: Link works, invalidation works, refresh persists
- **Req IDs**: EM-01 through EM-05

### Test Agent
- **Owns**: Playwright harness structure + fixtures + incremental runs
- **Scope**:
  - Test directory structure
  - Fixture files
  - Route-based test isolation
- **DoD**: Tests are non-flaky and isolated per route
- **Req IDs**: PW-01 through PW-04

### API Guardian Agent
- **Owns**: Backend integrity verification
- **Scope**:
  - Verify no new route-specific endpoints
  - Verify all mutations use /v1/actions/execute
- **DoD**: Diff scan shows no backend route changes
- **Req IDs**: GR-01, GR-02

---

## Active Tasks

<!-- Agents record their active tasks here -->

### Security Agent — Current Task
```markdown
### Task ID: RLS-01, RLS-02, RLS-03, RLS-04
- **Goal**: Fix all RLS security blockers before Tier 1 migration
- **Scope IN**:
  - Drop USING(true) policies
  - Create yacht-scoped policies
  - Enable RLS on pms_inventory_transactions
- **Scope OUT**: Any schema changes, any new tables
- **Files expected to change**: SQL migration file
- **Success criteria**: Cross-yacht SELECT returns 0 rows for all 4 tables
- **Tests to run**: SQL verification queries
- **Proof required**: Query output showing 0 cross-yacht rows
- **Rollback plan**: Drop new policies, recreate old ones
```

---

## Completed Tasks

<!-- Move completed tasks here with results -->

---

*Last Updated: 2026-02-26*
