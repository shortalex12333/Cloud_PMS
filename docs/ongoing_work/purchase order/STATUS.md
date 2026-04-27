# Purchase Order Domain — Current Status
**Last updated:** 2026-04-27  
**Owner:** PURCHASE05  
**Branch:** `feat/po-phase3` (worktree: `Cloud_PMS-cert04`)  
**PRs landed:** #657, #667, #727, #737, #740

---

## What is live

### PR #657 — Foundation (2026-04-23)
Fixed every PO action returning 400. All fixes in `apps/api/routes/p0_actions_routes.py` and `purchase_order_handler.py`.

| Bug | Fix | File:Line |
|-----|-----|-----------|
| All PO actions → 400 | Added 9 IDs to `_PO_ACTIONS` frozenset | `p0_actions_routes.py:611-617` |
| `purchase_order_id` missing from context | Added 6 entries to `_ENTITY_CONTEXT_MAP` | `p0_actions_routes.py:92-99` |
| `add_po_note` wrong REQUIRED_FIELDS | Fixed to `["note_text"]` | `p0_actions_routes.py:888` |
| Internal adapter KeyError on 5 actions | Added to `_ACTIONS_TO_ADAPT` | `internal_adapter.py:155-159` |
| `purser` role rejected on approve | Added to `_HOD_ROLES` | `purchase_order_handler.py:22` |
| `cancel_purchase_order` unimplemented | Implemented Phase 4 handler | `purchase_order_handler.py:139-185` |
| `submit_po/approve_po/receive_po` aliases | Added to HANDLERS dict + registry | `purchase_order_handler.py:187-189`, `registry.py:3639-3674` |
| Duplicate metadata in lens | Fixed field mapping | `PurchaseOrderContent.tsx:83-99` |
| PO list: no supplier/amount | Added batch enrichment | `vessel_surface_routes.py:804-840` |
| Entity endpoint: no supplier/amount | Added enrichment + soft-delete filter | `entity_routes.py:916-956` |
| Deleted POs visible in list | Added `is_("deleted_at", "null")` filter | `vessel_surface_routes.py:761` |

### PR #667 — .dockerignore hotfix (2026-04-23)
Every lens (PO, shopping, cert, docs, warranty, HoR) returned 404 for ~4.5 hours.  
**Root cause:** `apps/api/.dockerignore` listed `lib/` — stripped `lib/user_resolver.py` from Docker image. `ModuleNotFoundError` swallowed by try/except in `pipeline_service.py:485-491`. Entity routes never registered.  
**Fix:** Removed `lib/` and `lib64/` from `.dockerignore`. Commit `107718e7`.

### PR #727 — UX + new actions (2026-04-24)
7-tab lens redesign (Items / Invoice / Supplier / Related Parts / Docs / Notes / Audit Trail).  
New handlers, registry entries, and entity route fields.

| Feature | File |
|---------|------|
| `deny_po_line_item` handler (sets `line_status='denied'`, `denied_at`, writes ledger) | `purchase_order_handler.py:562` |
| `add_tracking_details` handler (writes tracking fields, auto-advances `approved→ordered`, fires notification) | `purchase_order_handler.py:617` |
| Both added to HANDLERS dict + registry + entity route | `purchase_order_handler.py:801`, `registry.py`, `entity_routes.py` |
| Line items now carry `line_status`, `denied_at`, `denial_reason`, `shopping_list_item_id` | `entity_routes.py` |
| PO response carries `tracking_number`, `carrier`, `expected_delivery_start/end`, `source_shopping_list_id` | `entity_routes.py` |
| Denied items section in Items tab (red chip + denial reason) | `PurchaseOrderContent.tsx` |
| Delivery window KV block | `PurchaseOrderContent.tsx` |
| Shopping list back-link in nav when `source_shopping_list_id` present | `entity_routes.py`, `PurchaseOrderContent.tsx` |

### PR #737 — Shopping list traceability (2026-04-25, combined with SHOPPING05)
`_convert_to_po` (`internal_dispatcher.py:3628`) now:
- Scopes to `shopping_list_id` first
- Writes `source_shopping_list_id` on the PO
- Writes `shopping_list_item_id` per line item
- Marks `pms_shopping_lists` as `converted_to_po`

Bidirectional link: shopping list → PO and PO → shopping list both navigable from the lens.

### PR #740 — Phase 3 (2026-04-25/26)
| Feature | How | File |
|---------|-----|------|
| Silent action failure fixed | Backend now raises HTTP 422 (not 200+error dict); frontend catches result and shows sonner toast | `purchase_order_handler.py:add_item_to_purchase`, `PurchaseOrderContent.tsx:~850` |
| Real invoice upload | Supabase Storage upload to TENANT bucket `pms-finance-documents`; path `{yacht_id}/invoices/{po_id}/{ts}_{filename}` | `PurchaseOrderContent.tsx:~800` |
| `update_supplier_on_po` handler | HOD-gated, blocks received/cancelled with 422, updates `supplier_id/supplier_name`, writes ledger | `purchase_order_handler.py:713` |
| PO PDF export | `GET /v1/purchase-order/{id}/pdf` — PyMuPDF A4, accepted items table, denied items (red), tracking block | `purchase_order_pdf_route.py` |
| PDF route registered | try/except block in `pipeline_service.py` | `pipeline_service.py` |
| Shopping list PDF route also registered (was missing) | Same try/except pattern | `pipeline_service.py` |

---

## Open follow-ups

| Item | Priority | Notes |
|------|----------|-------|
| Wire-walk verification | P0 | Create list → add items → submit → HOD approve → convert to PO → check `source_shopping_list_id` + `shopping_list_item_id` on entity endpoint |
| PO filter panel | P1 | `FILTER_CONFIGS['purchasing']` missing from `filter-config.ts`; backend block needed in `vessel_surface_routes.py` |
| `microactions/handlers/procurement.ts` | P1 | Writes to MASTER Supabase (`NEXT_PUBLIC_SUPABASE_URL`) but targets TENANT table `pms_purchase_orders` — will fail with RLS block. Investigate if any UI triggers this path |
| `action_router/__init__.py:3-4` | P2 | Loads dead router at every startup — remove `from .router import router, execute_action` |
| `action_router/router.py` (783 lines) | P2 | Dead predecessor to `p0_actions_routes.py` — archive or delete after peer confirmation |
| `n8n_dispatcher.py` (122 lines) | P2 | Dead — `HandlerType.N8N` commented out in `registry.py:20`; remove after router.py cleanup |
| `features/receiving/_deprecated/` | P3 | Ready to delete — no callers, README says delete after 14-day stable run |

---

## Key file map

| Concern | File |
|---------|------|
| Action routing + role gating | `apps/api/routes/p0_actions_routes.py` |
| All PO Phase 4 handlers | `apps/api/routes/handlers/purchase_order_handler.py` |
| Action registry (roles, fields) | `apps/api/action_router/registry.py` |
| Entity endpoint (enrichment, nav) | `apps/api/routes/entity_routes.py` |
| PO list (filter, adapter) | `apps/web/src/app/purchasing/page.tsx` |
| Lens UI (7 tabs, all interactions) | `apps/web/src/components/lens-v2/entity/PurchaseOrderContent.tsx` |
| PDF export route | `apps/api/routes/purchase_order_pdf_route.py` |
| Shopping list → PO conversion | `apps/api/action_router/dispatchers/internal_dispatcher.py:3628` |
