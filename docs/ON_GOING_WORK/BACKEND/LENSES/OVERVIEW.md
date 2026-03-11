# Entity Lenses — Backend Framework Overview

**Milestone:** v1.3 Actionable UX Unification — **COMPLETE**
**Status:** 100% Implemented (all CRITICAL/HIGH gaps resolved)
**Last Updated:** 2026-03-03

---

## REALITY CHECK (2026-03-03)

| Metric | Claimed | Actual | Status |
|--------|---------|--------|--------|
| Lenses defined | 13 | **13 in matrix** (Document added) | ✅ |
| LensContent pattern | 14 | **14 (all complete)** | ✅ |
| Route pages | 12 | 12 (Handover/Worklist panel-only by design) | ✅ |
| Action hooks wired | All | 15 hooks → /v1/actions/execute | ✅ |
| PermissionService | — | Centralized, lens_matrix.json | ✅ |
| E2E tests | 1184+ | **shard-6: 2, shard-31: 1182** (42 spec files) | ✅ |
| Tests passing | — | `.last-run.json` = `"status": "passed"` | ✅ |

### Known Gaps (see GAPS.md) — ALL RESOLVED ✅

- ~~**GAP-027 (HIGH)**: Email conversion~~ → ✅ **RESOLVED 2026-03-03**
- ~~**GAP-028 (HIGH)**: Handover/Worklist panel-only~~ → ✅ **RESOLVED 2026-03-03** (intentional design, Add button added)
- ~~**GAP-029 (HIGH)**: Document not in lens_matrix.json~~ → ✅ **RESOLVED 2026-03-03** (6 actions added)
- ~~**GAP-030 (CRITICAL)**: Test suite verification~~ → ✅ **RESOLVED 2026-03-03** (infrastructure verified, 1184+ tests)

### Architecture Note

All lenses now use the unified pattern:
1. **LensContent pattern** (v1.3): All 14 lenses use `*LensContent.tsx` + RouteShell
2. **Email button**: Now navigates to `/email` (was overlay toggle)

✅ **Email Conversion Complete (Phase 20):** `EmailLensContent.tsx` created, registered in `LensRenderer.tsx`, email button navigates to `/email` route. SACRED OAuth patterns unchanged.

---

## Project Goal

Entity Lenses provide a **backend-first, document-driven** approach to yacht maintenance operations. Each lens governs a single entity type with:

- **DB TRUTH**: Schema verified from production database snapshots
- **Actions**: Registered mutations with role gating and signature requirements
- **RLS Matrix**: Row-level security policies enforced at database layer
- **Scenarios**: User journey documentation with step reduction metrics

```
User Intent
    ↓
┌─────────────────────────────────────────────────────────────┐
│                      Entity Lens Layer                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Work Order  │  │  Equipment  │  │ Certificate │  ...    │
│  │   Lens v2   │  │   Lens v2   │  │   Lens v2   │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                              │
│  Actions: /v1/actions/execute (unified endpoint)            │
│  Search:  /v1/search (NLP → deterministic filters)          │
│  RLS:     get_user_yacht_id() / is_hod() / is_manager()    │
└─────────────────────────────────────────────────────────────┘
    ↓
Supabase PostgreSQL (RLS enforced)
```

---

## Architecture Principles

### 1. Backend Defines Authority

Frontend NEVER decides permissions. All authorization is enforced at:
- **RLS policies** (`yacht_id = get_user_yacht_id()`)
- **Action router** (role gating before handler execution)
- **Signature invariant** (`signature = '{}'::jsonb` or valid payload, NEVER NULL)

### 2. Document → Tests → Code → Verify

```
PHASE 0: Extraction Gate
    ↓ (lens approved)
PHASE 1: Scope Definition
    ↓
PHASE 2: DB TRUTH (production schema verification)
    ↓
PHASE 3: Entity Graph (relationships, escape hatches)
    ↓
PHASE 4: Actions (mutations with SQL patterns)
    ↓
PHASE 5: Scenarios (user journeys)
    ↓
PHASE 6: SQL Backend (handler implementations)
    ↓
PHASE 7: RLS Matrix (security policies)
    ↓
PHASE 8: Gaps & Migrations (blockers, deployment)
    ↓
FINAL: Production Ready
```

### 3. Single Source of Truth

- **One FINAL.md per lens** — all specifications consolidated
- **No version suffixes** — Git handles history
- **Canonical helpers** — `get_user_yacht_id()`, `is_hod()`, `is_manager()`

---

## Entity Lenses Inventory (Verified 2026-03-03)

### Fully Wired (Route + Component + Actions + Tests)

| Lens | Route | Component | Actions | E2E Tests | RBAC |
|------|-------|-----------|---------|-----------|------|
| **Work Order** | ✅ `/work-orders/[id]` | ✅ WorkOrderLensContent | 12 | 54 | ✅ |
| **Fault** | ✅ `/faults/[id]` | ✅ FaultLensContent | 9 | 52 | ✅ |
| **Equipment** | ✅ `/equipment/[id]` | ✅ EquipmentLensContent | 5 | 50 | ✅ |
| **Part** | ✅ `/inventory/[id]` | ✅ PartsLensContent | 7 | 52 | ✅ |
| **Inventory** | ✅ `/inventory` | ✅ PartsLensContent | 5 | 50 | ✅ |
| **Receiving** | ✅ `/receiving/[id]` | ✅ ReceivingLensContent | 9 | 52 | ✅ |
| **Certificate** | ✅ `/certificates/[id]` | ✅ CertificateLensContent | 8 | 52 | ✅ |
| **Hours of Rest** | ✅ `/hours-of-rest/[id]` | ✅ HoursOfRestLensContent | 8 | 52 | ✅ |
| **Warranty** | ✅ `/warranties/[id]` | ✅ WarrantyLensContent | 6 | 50 | ✅ |
| **Shopping List** | ✅ `/shopping-list/[id]` | ✅ ShoppingListLensContent | 7 | 52 | ✅ |
| **Handover Export** | ✅ `/handover-export/[id]` | ✅ HandoverExportLensContent | N/A | 50 | ✅ |

### Email Lens — ✅ COMPLETE (Phase 20)

| Lens | Route | Component | Actions | Status |
|------|-------|-----------|---------|--------|
| **Email** | ✅ `/email/[threadId]` | ✅ EmailLensContent (153 LOC) | 7 | ✅ **Complete** |

**Phase 20 Delivered (2026-03-03):**
- ✅ Created `EmailLensContent.tsx` (153 LOC) wrapping `EmailThreadViewer.tsx`
- ✅ Registered 'email' case in `LensRenderer.tsx` (line 142)
- ✅ Email button navigates to `/email` via `router.push(getEntityRoute('email'))`
- ✅ SPA mode (`/app?entity=email&id=X`) works via ContextPanel
- ✅ Fragmented routes continue to work (19/19 tests pass)
- ✅ All 7 email actions functional
- ✅ **SACRED OAuth patterns unchanged** (0 modifications)

**Summary:** `.planning/phases/20-email-conversion/20-01-SUMMARY.md`

### Panel-Only (Intentional Design) ✅ CONFIRMED

| Lens | Route | Component | Actions | Status |
|------|-------|-----------|---------|--------|
| **Handover** | Panel-only | ✅ HandoverDraftPanel | 9 | ✅ Add/Edit/Delete buttons, all roles |
| **Worklist** | Panel-only | ✅ WorklistLensContent | 4 | ✅ Intentional design |

**Handover Panel Access:** Search bar dropdown → "Handover Draft" menu item → `HandoverDraftPanel.tsx` slides in with Add Note, Edit, Delete, and Send to Handover functionality.

### Document Lens — ✅ COMPLETE (2026-03-03)

| Lens | Route | Component | Actions | Status |
|------|-------|-----------|---------|--------|
| **Document** | ✅ `/documents/[id]` | ✅ DocumentLensContent | 6 | ✅ Added to lens_matrix.json |

**Actions Added:** `upload_document`, `update_document`, `delete_document` (signature required), `add_document_tags`, `get_document_url`, `reclassify_document`

### Summary

- **13/13 matrix lenses** configured (Document added 2026-03-03)
- **14/14 components** exist as LensContent (all complete)
- ✅ **Email** lens complete — button navigates to `/email`, SPA mode works
- ✅ **Document** lens complete — added to lens_matrix.json with 6 actions
- ✅ **Handover** panel complete — Add/Edit/Delete buttons for all roles
- **1184+ E2E tests** across 13 suites (shard-6: 2, shard-31: 1182)
- **RBAC** via PermissionService + lens_matrix.json
- **All CRITICAL/HIGH gaps resolved** — v1.3 milestone complete

---

## Key Components

### Action Router

All mutations flow through `/v1/actions/execute`:

```python
# Registry Entry
ActionDefinition(
    action_id="create_work_order",
    endpoint="/v1/work-orders/create",
    handler_type=HandlerType.INTERNAL,
    allowed_roles=["engineer", "captain", "manager"],
    required_fields=["title", "type", "priority"],
    domain="work_orders",
    variant=ActionVariant.MUTATE,
)
```

**Key Files:**
- `apps/api/action_router/router.py` — Main router
- `apps/api/action_router/registry.py` — Action definitions
- `apps/api/handlers/*.py` — Domain handlers

### RLS Canonical Functions

```sql
-- Yacht scope (all queries)
public.get_user_yacht_id() → UUID

-- Role checks (write operations)
public.is_hod(user_id, yacht_id) → BOOLEAN
public.is_manager() → BOOLEAN
public.get_user_role() → TEXT
```

### Signature Invariant

```sql
-- Non-signed action
signature = '{}'::jsonb

-- Signed action (e.g., decommission, supersede)
signature = :signature_payload::jsonb  -- NEVER NULL
```

---

## Database Tables by Lens

### Work Order Lens
| Table | Columns | yacht_id | RLS |
|-------|---------|----------|-----|
| pms_work_orders | 29 | YES | ✅ Canonical |
| pms_work_order_checklist | 24 | YES | ⚠️ Mixed |
| pms_work_order_notes | 7 | NO | ❌ B1 |
| pms_work_order_parts | 9 | NO | ❌ B2 |
| pms_work_order_history | 14 | YES | ✅ Canonical |
| pms_part_usage | 11 | YES | ❌ B3 |

### Equipment Lens
| Table | Columns | yacht_id | RLS |
|-------|---------|----------|-----|
| pms_equipment | 24 | YES | ✅ Deployed |
| pms_equipment_parts_bom | 7 | YES | ⚠️ Verify |
| pms_notes | 11 | YES | ⚠️ B1 |
| pms_attachments | 12 | YES | ⚠️ B2 |

### Certificate Lens
| Table | Columns | yacht_id | RLS |
|-------|---------|----------|-----|
| pms_vessel_certificates | 14 | YES | ❌ B1 |
| pms_crew_certificates | 12 | YES | ⚠️ B2 |

### Fault Lens
| Table | Columns | yacht_id | RLS |
|-------|---------|----------|-----|
| pms_faults | 20+ | YES | ✅ Verify |

### Inventory/Part Lens
| Table | Columns | yacht_id | RLS |
|-------|---------|----------|-----|
| pms_parts | 25+ | YES | ✅ Verify |
| pms_part_stock | 8 | YES | TBD |
| pms_inventory_transactions | 15 | YES | TBD |

---

## Integration with Spotlight Search

### Filter Chips (C1 Invariant)

Filters map to deterministic routes:

```typescript
// catalog.ts
{
  filter_id: 'wo_overdue',
  label: 'Overdue work orders',
  domain: 'work-orders',
  route: '/work-orders',
  query_params: { filter: 'wo_overdue' },
  definition: "due_date < CURRENT_DATE AND status NOT IN ('completed', 'cancelled')",
}
```

**Rule:** If a filter can be suggested, it MUST execute. No dead chips.

### Action Suggestions (C2 Invariant)

Actions limited to 3 per query:

```typescript
// useCelesteSearch.ts
const MAX_ACTION_SUGGESTIONS = 3;
const limitedActions = response.actions.slice(0, MAX_ACTION_SUGGESTIONS);
```

**Rule:** Action suggestions must never spam. Backend limit + frontend slice.

---

## File Organization

### Documentation
```
docs/pipeline/entity_lenses/
├── certificate_lens/v2/
│   ├── certificate_lens_v2_FINAL.md
│   ├── certificate_lens_v2_PHASE_0_EXTRACTION_GATE.md
│   ├── certificate_lens_v2_PHASE_1_SCOPE.md
│   └── ... (PHASE_2 through PHASE_8)
├── equipment_lens/v2/
│   └── ... (same structure)
├── work_order_lens/v2/
│   └── ... (same structure)
├── fault_lens/
│   └── LENS.md
└── ...
```

### Backend Code
```
apps/api/
├── action_router/
│   ├── router.py           # Main action router
│   ├── registry.py         # Action definitions
│   └── dispatchers/        # Handler dispatchers
├── handlers/
│   ├── work_order_handlers.py
│   ├── equipment_handlers.py
│   └── ...
├── common/
│   ├── prefill_engine.py   # Prefill generation
│   └── temporal_parser.py  # NLP date parsing
└── routes/
    └── p0_actions_routes.py
```

### Migrations
```
supabase/migrations/
├── 20260125_001_fix_cross_yacht_notes.sql
├── 20260125_002_fix_cross_yacht_parts.sql
├── 20260125_003_fix_cross_yacht_part_usage.sql
├── 20260125_004_create_cascade_wo_fault_trigger.sql
├── 20260125_006_fix_crew_certificates_rls.sql
├── 20260125_007_vessel_certificates_rls.sql
└── ...
```

---

## Guardrails (Non-Negotiable)

| Rule | Enforcement |
|------|-------------|
| **No dashboard language** | Query-only activation |
| **No ambient buttons** | Actions only after focus |
| **Signature invariant** | `'{}'::jsonb` or valid payload |
| **100% yacht isolation** | `get_user_yacht_id()` on ALL queries |
| **Explicit role gating** | `is_hod()` / `is_manager()` checks |
| **Surface uncertainty** | Never silently assume |

---

## Quick Commands

```bash
# Check lens documentation
ls docs/pipeline/entity_lenses/

# View action registry
grep -r "ActionDefinition" apps/api/action_router/

# Verify RLS policies
# Run in Supabase SQL Editor:
SELECT tablename, policyname FROM pg_policies WHERE tablename LIKE 'pms_%';

# Run E2E tests
E2E_BASE_URL=https://app.celeste7.ai npx playwright test --project=shard-8-workorders
```

---

## Route Architecture

### Current: RouteShell Pattern ✅ IMPLEMENTED (Phase 16.2)

The RouteShell pattern was implemented in v1.3 Phase 16.2:

```
/faults/[id]/page.tsx (~27 lines)
    └── RouteShell
         ├── Data fetching
         ├── Feature flag guard
         └── FaultLensContent (existing, fully wired)
```

**Key Files:**
- `apps/web/src/components/lens/RouteShell.tsx` — Thin wrapper
- `apps/web/src/services/permissions.ts` — RBAC from lens_matrix.json

**Results:**
- 11 route pages replaced (4,262 → 285 LOC = 93% reduction)
- All buttons wired via LensContent components
- Single source of truth for RBAC

### Rendering Paths

| Path | URL Pattern | Renderer |
|------|-------------|----------|
| **SPA Mode** | `/app?entity=fault&id=123` | ContextPanel → LensRenderer → *LensContent |
| **Fragmented Mode** | `/faults/123` | RouteShell → *LensContent |

Both paths use the same LensContent components — buttons work identically.

---

## Related Documentation

| Document | Location | Purpose |
|----------|----------|---------|
| PHASES-COMPLETE.md | This directory | Completed phases 1-16.1 |
| PHASES-REMAINING.md | This directory | Pending phases 17-19 |
| GAPS.md | This directory | Missing components |
| UNIFIED-ROUTE-ARCHITECTURE.md | This directory | Phase 16.2 route unification spec |
| QUICK-REFERENCE.md | This directory | Worker quick reference |
| FAILED_BUTTONS_REPORT_2026-03-02.md | /docs/ | 26 unwired buttons audit |
| Spotlight Search | ../SPOTLIGHT_SEARCH/ | Search/filter integration |

---

*See also: PHASES-COMPLETE.md, PHASES-REMAINING.md, GAPS.md, UNIFIED-ROUTE-ARCHITECTURE.md*
