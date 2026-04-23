# Purchase Order Lens — Filter Panel + Issue #14 Button Audit

**Author:** PURCHASE05
**Date:** 2026-04-23
**Scope:** PO filter panel (tokenized, universal pattern) + Issue #14 button corrections
**Depends on:** PR #667 (`.dockerignore` hotfix — restored `/v1/entity/*` route mounts)

---

## Part 0 — 404 investigation (closed)

User report: "404 when opening a random shopping list". Actual URL: `/v1/entity/purchase_order/8c64d1e9-…`. **Every** `/v1/entity/*` route returned 404.

**Root cause** — not an underpopulated tenant row. DB row exists:
`pms_purchase_orders.id=8c64d1e9-…, yacht_id=85fe1119-…, deleted_at=NULL, status=received` (confirmed via psql).

**Chain of failure:**
1. `apps/api/routes/entity_routes.py:23` imported `from lib.user_resolver import resolve_users, resolve_yacht_name, resolve_equipment_batch` (added by PR #663 at ~18:37 today).
2. `apps/api/.dockerignore` listed `lib/` and `lib64/` (Python venv template boilerplate). Docker image built without `apps/api/lib/user_resolver.py`.
3. `ModuleNotFoundError` at startup.
4. `apps/api/pipeline_service.py:485-491` wraps router mount in `try/except Exception` — swallowed the error.
5. `/v1/entity/*` never registered. FastAPI returns 404.
6. Symptom: every lens (PO, shopping, cert, document, warranty, HoR) broken for ~4.5 hours.

**Fix:** PR #667 (merged `107718e7`) removed `lib/` and `lib64/` from `apps/api/.dockerignore`.

**Verified live** (with HOD token): `GET /v1/entity/purchase_order/8c64d1e9-…?yacht_id=85fe1119-…` → HTTP 200 with full enriched payload + 15 available_actions.

---

## Part A — Filter Panel (MVP)

### Today's state (bad)

`apps/web/src/app/purchasing/page.tsx:99` passes `filterConfig={[]}` — empty. No filter panel. Row display (via `poAdapter` at line 38-55) uses `title = po_number`, `entityRef = po_number`. EntityRecordRow renders Line 1 as `entityRef — title`, so both cells show the same PO number ("title — title — status" repetition).

### Universal pattern

Every other lens imports its filter array from `apps/web/src/features/entity-list/types/filter-config.ts` and maps the domain → array in `FILTER_CONFIGS` (line 323). Shopping, inventory, receiving, certificate, equipment all follow this shape. POs have **no entry**. Backend consumes filter params at `apps/api/routes/vessel_surface_routes.py:700-761` with a per-domain block (shopping_list already has one).

### Surfacable columns (no UUIDs — FE humans only)

| Column                    | DB column (pms_purchase_orders) | Type          | Semantics                     |
|---------------------------|----------------------------------|---------------|--------------------------------|
| Status                    | `status`                         | enum select   | draft/submitted/approved/ordered/partially_received/received/cancelled |
| PO Number                 | `po_number`                      | text ILIKE    | `%user_input%`                 |
| Supplier                  | `supplier_id` → `pms_suppliers.name` | text ILIKE | joined lookup                  |
| Currency                  | `currency`                       | enum select   | USD / EUR / GBP                |
| Ordered                   | `ordered_at`                     | date-range    | `gte(from), lte(to)`           |
| Received                  | `received_at`                    | date-range    | `gte(from), lte(to)`           |
| Expected Delivery         | `expected_delivery`              | date-range    | `gte(from), lte(to)`           |

Deferred (needs design): numeric range for `total_amount` (computed from items), notes ILIKE (buried in JSONB `metadata.notes`).

### Files changing

- `apps/web/src/features/entity-list/types/filter-config.ts` — add `PURCHASE_ORDER_FILTERS`, register `'purchasing'` in `FILTER_CONFIGS`.
- `apps/web/src/app/purchasing/page.tsx` — pass the new filter config; tighten `poAdapter` so `entityRef` and `title` are not the same.
- `apps/api/routes/vessel_surface_routes.py` — add a `if domain == "purchase_orders":` filter block mirroring shopping_list.

### Tokenization / peer coordination

Entire pattern is already tokenized — FilterPanel renders via `apps/web/src/features/entity-list/components/FilterPanel.tsx` which uses only CSS vars (`--surface-*`, `--txt-*`, `--mark`). No new styling work needed. Peers ping: CERT04 (a4rjnwoe) + DOCUMENTS04 (yoipdwmt) already use this registry; the new PO entry plugs in with zero new visual language.

---

## Part B — Issue #14 Button Audit

### What user sees today

All buttons except `cancel_po` return HTTP 400. `delete_po` "succeeds" but the row is not actually soft-deleted. `track_delivery` refreshes the page silently.

### Button matrix

| Button                    | Action ID                | User decision | Backend state                                                    | This PR               |
|---------------------------|--------------------------|---------------|-------------------------------------------------------------------|-----------------------|
| Add PO Note               | `add_po_note`            | KEEP          | No Phase 4 handler → falls to `internal_adapter` → 400            | ADD Phase 4 handler   |
| Create Purchase Request   | `create_purchase_request`| REMOVE        | Wasteful from a card — belongs on list page only                  | HIDE in `entity_actions.py` |
| Order Part                | `order_part`             | KEEP          | Not a PO action — belongs on Part/Inventory lens                  | Defer (separate lens) |
| Approve Purchase          | `approve_purchase`       | KEEP          | Legacy alias — points to `approve_purchase_order` Phase 4 handler  | Verify alias wired    |
| Add Item to Purchase      | `add_item_to_purchase`   | KEEP (draft only) | No handler; state gate exists at `entity_actions.py:335-337`   | ADD Phase 4 handler   |
| Update Purchase Status    | `update_purchase_status` | KEEP          | No Phase 4 handler → 400                                          | ADD Phase 4 handler   |
| Upload Invoice            | `upload_invoice`         | KEEP          | Needs attachment pipeline — complex                              | Defer (needs upload surface) |
| Add to Handover           | `add_to_handover`        | KEEP (form schema) | Cross-domain injected at `entity_actions.py:165-170` — handler exists but prefill schema thin | Defer (needs form schema work) |
| Delete Purchase Order     | `delete_po`              | KEEP          | Phase 4 handler exists (PR #662); PIN field is **frontend-only cosmetic** — no backend check. "Delete" then doesn't show up because UI doesn't refetch | Fix list refetch; PIN verification deferred (requires crypto scheme) |
| Track Delivery            | `track_delivery`         | REMOVE        | Dead action, no handler                                            | HIDE in `entity_actions.py` |
| Cancel Purchase Order     | `cancel_po`              | KEEP          | ✅ Works — Phase 4 handler (PR #662)                              | No change              |

### Role matrix (applies to all KEEP buttons)

Purser, HOD of department (chief_engineer / chief_officer / chief_steward), captain, manager — matches `_HOD_ROLES` in `apps/api/routes/handlers/purchase_order_handler.py:22`.

### Files changing

- `apps/api/action_router/entity_actions.py` — add `_PURCHASE_ORDER_HIDDEN_ACTIONS = {"create_purchase_request", "track_delivery"}` and a filter in `get_available_actions` (mirrors `_SHOPPING_LIST_HIDDEN_ACTIONS` pattern line 63-70 / 102-103).
- `apps/api/routes/handlers/purchase_order_handler.py` — add Phase 4 handlers: `add_po_note`, `update_purchase_status`, `add_item_to_purchase` (with draft-only DB-side gate).
- `apps/api/routes/p0_actions_routes.py` — register the three new actions in `_PO_ACTIONS` + `_ACTION_ENTITY_MAP`.

### Deferred (next PR)

- `upload_invoice` — attachment upload pipeline + signed URL.
- `add_to_handover` form schema — bring forward `title`/`status` from PO record, add key/value notes inputs. User specifically asked for this; scope is a dedicated form builder PR.
- `delete_po` PIN enforcement — PIN today is cosmetic; real enforcement needs a verification scheme (not in this PR).
- `order_part` on PO lens — likely misplaced; real home is Part lens.

---

## Risk / rollback

- Filter panel additions are additive; if a filter breaks, `filterConfig=[]` restores today's behavior.
- Action hiding is reversible — remove the entry from `_PURCHASE_ORDER_HIDDEN_ACTIONS`.
- Phase 4 handler additions follow the same contract as PR #662 and have dict-aliases for FE-facing names.
