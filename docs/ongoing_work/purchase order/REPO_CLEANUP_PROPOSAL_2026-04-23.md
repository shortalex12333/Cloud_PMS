# Repo Cleanup Proposal — Purchase05 Scope
**Date:** 2026-04-23  
**Author:** PURCHASE05  
**Scope:** `action_router/`, `routes/p0_actions_routes.py`, `routes/vessel_surface_routes.py`, `routes/entity_routes.py`, `routes/handlers/purchase_order_handler.py`, `routes/handlers/internal_adapter.py`, `action_router/registry.py`, `web/src/app/purchasing/`, `web/src/components/lens-v2/entity/PurchaseOrderContent.tsx`  
**Status:** Proposal — awaiting CEO sign-off before any destructive execution

---

## How to read this document

Each finding has:
- **Evidence** — exact file:line citations, grep commands to verify
- **Risk** — ZERO / LOW / MEDIUM / HIGH
- **Verdict** — EXECUTE-SAFE / PROPOSE / DEFER

---

## Finding 1 — `action_router/__init__.py` loads 1300+ dead lines at every API startup
**Risk: LOW**  
**Verdict: EXECUTE-SAFE**

### Evidence
`apps/api/action_router/__init__.py:3-4`:
```python
from .router import router, execute_action
```
This line executes the following chain on every import of any `action_router` submodule:
1. `action_router/router.py` (783 lines) loads — dead FastAPI router
2. `router.py:33` does `from .dispatchers import internal_dispatcher, n8n_dispatcher`
3. `dispatchers/__init__.py` does `from . import secure_dispatcher`
4. `secure_dispatcher.py` runs its startup gate (which silently passes — see Finding 4)

Verify with: `grep -n "from .router" apps/api/action_router/__init__.py`

No live code imports `from action_router import router` or `from action_router import execute_action`:
```
grep -rn "from action_router import router\|from action_router import execute_action" apps/api/ --include="*.py"
# → zero results
```

### Fix
Remove lines 3-4 from `action_router/__init__.py` and remove `router` / `execute_action` from `__all__`.

---

## Finding 2 — `action_router/router.py` is a dead FastAPI router (783 lines)
**Risk: LOW**  
**Verdict: PROPOSE (archive, not delete)**

### Evidence
`pipeline_service.py` never imports or mounts `action_router/router.py`:
```
grep -n "action_router.router\|from action_router import router" apps/api/pipeline_service.py
# → zero results
```

The live `POST /v1/actions/execute` endpoint is served by `routes/p0_actions_routes.py` (prefix `/v1/actions`, mounted at `pipeline_service.py:210-211`).

`action_router/router.py` WOULD have registered the same endpoint if mounted — it was the PREDECESSOR. The `p0_actions_routes.py` replaced it.

Tests do not import this file directly:
```
grep -rn "from action_router import router" apps/api/tests/
# → zero results
```

### Fix
Move to `action_router/router.py.dead` or delete. Coordinate with DOCUMENTS04 to confirm no other domain depends on it.

---

## Finding 3 — `action_router/dispatchers/n8n_dispatcher.py` is dead (122 lines)
**Risk: LOW**  
**Verdict: PROPOSE**

### Evidence
`HandlerType.N8N` is commented out in `registry.py:20`:
```python
# N8N = "n8n"  # DEPRECATED 2026-01-27
```
Zero actions in `ACTION_REGISTRY` use `HandlerType.N8N`.

Only imported from:
1. `action_router/router.py` (dead — see Finding 2)
2. `action_router/dispatchers/__init__.py` (which exports it)

No tests or live routes reference it directly:
```
grep -rn "n8n_dispatcher" apps/api/ --include="*.py" | grep -v "router.py\|dispatchers/__init__\|dispatchers/n8n_dispatcher"
# → zero results
```

### Fix
Delete after Finding 1 and 2 are resolved.

---

## Finding 4 — `secure_dispatcher.py` startup gate is always a no-op (broken import)
**Risk: MEDIUM (fixing it would actually enforce the gate)**  
**Verdict: DEFER — needs security review**

### Evidence
`secure_dispatcher.py:55`:
```python
from action_router.dispatchers.internal_dispatcher import HANDLERS
```
But `internal_dispatcher.py` exports `INTERNAL_HANDLERS` (not `HANDLERS`). Verify:
```
grep "^__all__" apps/api/action_router/dispatchers/internal_dispatcher.py
# → ["dispatch", "INTERNAL_HANDLERS"]
```

The `ImportError` is caught silently at `secure_dispatcher.py:58-59` (`except ImportError: return {}`), returning an empty handler dict. 0 handlers → 0 unsecured → gate always passes.

### Fix options
A. Fix the import name (`HANDLERS` → `INTERNAL_HANDLERS`) — this would actually run security checks and FAIL if handlers lack `@secure_action`. High disruption.  
B. Delete `secure_dispatcher.py` as broken dead code (safe if Finding 2 is resolved first, since secure_dispatcher is only loaded via router.py).  
C. No-op: leave broken but harmless.

---

## Finding 5 — `actions/action_gating.py` exports are semantically dead
**Risk: ZERO**  
**Verdict: PROPOSE (cleanup for clarity)**

### Evidence
```
grep -rn "GATED_ACTIONS\|is_gated\|requires_confirmation" apps/api/ --include="*.py" \
  | grep -v "__pycache__\|action_gating.py\|actions/__init__.py"
# → only one result: a docstring comment in certificate_handlers.py:14
```

`action_gating.py` IS loaded (via `actions/__init__.py` when handlers do `from actions.action_response_schema import ...`). No side effects — just dead exports.

### Fix
Remove the `action_gating` imports from `actions/__init__.py` OR leave as-is. Zero risk either way.

---

## Finding 6 — `purchasing/page.tsx` has vestigial props (ignored by backend)
**Risk: ZERO**  
**Verdict: EXECUTE-SAFE (cosmetic clarity)**

### Evidence
`apps/web/src/app/purchasing/page.tsx:96-97`:
```tsx
table="v_purchase_orders_enriched"
columns="id, po_number, status, supplier_id, ordered_at, received_at, currency, created_at, updated_at"
```

`useFilteredEntityList.ts:41` documents: `/** Supabase table name — kept for backwards compat but no longer used for queries */`

The backend ignores both: `vessel_surface_routes.py` uses `DOMAIN_TABLES["purchase_orders"] = "pms_purchase_orders"` and `DOMAIN_SELECT["purchase_orders"] = "*"`.

The view `v_purchase_orders_enriched` is not referenced by any backend code — the backend queries `pms_purchase_orders` directly with batch enrichment.

### Fix
The `table` prop can be updated to the actual table (`pms_purchase_orders`) for accuracy, or removed if `FilteredEntityList` allows omitting it. The `columns` prop can be removed or left as documentation. Low priority.

---

## Finding 7 — `microactions/handlers/procurement.ts` writes to wrong DB
**Risk: MEDIUM**  
**Verdict: DEFER — needs investigation of whether these microactions are triggered in production**

### Evidence
`apps/web/src/lib/microactions/handlers/procurement.ts:36-49`:
```typescript
const { data: pr, error } = await supabase  // ← MASTER Supabase client
  .from('pms_purchase_orders')               // ← TENANT table
  .insert({ ... })
```

`lib/supabaseClient.ts` uses `NEXT_PUBLIC_SUPABASE_URL` = MASTER Supabase. `pms_purchase_orders` lives in TENANT Supabase. This insert fails (RLS block or missing table).

However: The PO lens (`PurchaseOrderContent.tsx`) does NOT use the microactions executor. It uses `useEntityLens.executeAction` → Next.js proxy → Render backend `/v1/actions/execute` → `p0_actions_routes.py`.

`MicroactionsProvider` IS in root layout (`app/layout.tsx:5,29`), so the system is wired. Whether any current UI button triggers `create_purchase_request` via this path needs investigation.

### Fix
Either:  
A. Remove the procurement microaction handlers (if no UI calls them).  
B. Rewrite to proxy through backend API like `useEntityLens.executeAction` does.

---

## Finding 8 — `features/receiving/_deprecated/` is ready for deletion
**Risk: LOW**  
**Verdict: PROPOSE — check 14-day rule**

### Evidence
`features/receiving/_deprecated/README.md`: "Delete after one stable release (≥14 days on production with the new lens pattern and zero `404 receiving` reports)."

No current callers:
```
grep -rn "features/receiving/_deprecated\|from.*_deprecated" apps/web/src/ --include="*.tsx" --include="*.ts"
# → zero results
```

### Fix
`git rm -r apps/web/src/features/receiving/_deprecated/`  
Condition: Confirm receiving lens has been stable for ≥14 days.

---

## Finding 9 — `purchasing/page.tsx` `poAdapter` does not get `supplier_name` from list query
**Risk: LOW — enrichment workaround is in place but fragile**  
**Verdict: EXECUTE-SAFE — verify or improve**

### Evidence
`vessel_surface_routes.py:804-840`: After formatting records, batch-fetches supplier names from `pms_suppliers` and injects `supplier_name` into the record. This IS in the live code (confirmed line 835: `fmt["supplier_name"] = sname`).

`purchasing/page.tsx` `poAdapter` (line 40): `const supplier = po.supplier_name ? ...` — correctly expects `supplier_name`.

The chain works. However, `DOMAIN_SELECT["purchase_orders"] = "*"` — selecting all columns. The batch enrichment adds `supplier_name` AFTER the `*` select. No issue.

Potential fragility: If the batch supplier query fails (line 814 has a try/except that logs + continues), `supplier_name` silently stays empty. The list shows no supplier. Not a bug, but worth monitoring.

---

## Summary table

| # | Finding | File:Line | Risk | Action |
|---|---------|-----------|------|--------|
| 1 | `__init__.py` loads dead router at startup | `action_router/__init__.py:3-4` | LOW | **Execute** |
| 2 | `router.py` is dead (783 lines) | `action_router/router.py` | LOW | Propose archive |
| 3 | `n8n_dispatcher.py` is dead (122 lines) | `action_router/dispatchers/n8n_dispatcher.py` | LOW | Propose |
| 4 | `secure_dispatcher.py` gate is broken no-op | `secure_dispatcher.py:55` | MEDIUM | Defer |
| 5 | `action_gating.py` exports unused | `actions/action_gating.py` | ZERO | Propose |
| 6 | `purchasing/page.tsx` dead `table`/`columns` props | `purchasing/page.tsx:96-97` | ZERO | Execute |
| 7 | `microactions/procurement.ts` wrong DB | `microactions/handlers/procurement.ts:36` | MEDIUM | Defer |
| 8 | `receiving/_deprecated/` ready to delete | `features/receiving/_deprecated/` | LOW | Propose |
| 9 | Supplier batch enrichment fragility | `vessel_surface_routes.py:814` | LOW | Monitor |

---

## Execution order (when approved)

1. Fix `action_router/__init__.py` (Finding 1) — no behavior change, stops loading dead code
2. Fix `purchasing/page.tsx` dead props (Finding 6) — cosmetic
3. Archive `router.py` + delete `n8n_dispatcher.py` (Findings 2-3) — after peers confirm no dependency
4. Handle `secure_dispatcher.py` (Finding 4) — requires security review
5. Handle `microactions/procurement.ts` (Finding 7) — requires UI audit
6. Delete `_deprecated/` (Finding 8) — after confirming 14-day rule

---

## What was already fixed in PR #657 (2026-04-23)

For completeness — the original `po_issues.md` issues resolved before this cleanup:

| Bug | Fix | File |
|-----|-----|------|
| 400 errors on all PO actions | Added 9 action IDs to `_PO_ACTIONS` frozenset | `p0_actions_routes.py:611-617` |
| `purchase_order_id` missing from context | Added 6 entries to `_ENTITY_CONTEXT_MAP` | `p0_actions_routes.py:92-99` |
| `add_po_note` bad REQUIRED_FIELDS | Fixed to `["note_text"]` | `p0_actions_routes.py:888` |
| Internal adapter KeyError | Added 5 actions to `_ACTIONS_TO_ADAPT` | `internal_adapter.py:155-159` |
| `purser` role blocked on approve | Added to `_HOD_ROLES` | `purchase_order_handler.py:22` |
| `cancel_purchase_order` missing | Implemented handler | `purchase_order_handler.py:139-185` |
| Frontend aliases missing | Added `submit_po/approve_po/receive_po` HANDLERS entries | `purchase_order_handler.py:187-189` |
| Frontend aliases missing from registry | Added 3 `ActionDefinition` entries | `registry.py:3639-3674` |
| Duplicate metadata in lens | Fixed field mapping | `PurchaseOrderContent.tsx:83-99` |
| PO list showed no supplier/amount | Added batch enrichment | `vessel_surface_routes.py:804-840` |
| Entity endpoint missing supplier/amount | Added enrichment + soft-delete | `entity_routes.py:916-956` |
| Deleted POs visible | Added `is_("deleted_at", "null")` filter | `vessel_surface_routes.py:761`, `entity_routes.py:916` |
