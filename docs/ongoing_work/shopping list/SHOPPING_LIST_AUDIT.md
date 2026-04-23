# Shopping List Lens — Repo Structure & Wiring Audit

**Date:** 2026-04-23
**Scope:** Shopping-list lens only. No changes touch other domains.
**Purpose:** Fulfill the repo-cleanup mandate — identify dead code, stale wiring, naming chaos, DB/handler drift, and document every finding with file:line citations.

All claims below are verified by either (a) direct grep, (b) live DB query against the TENANT project (`vzsohavtuotocgrfkfyd.supabase.co`), or (c) reading the current code at HEAD (origin/main).

---

## 1. File inventory

### Primary, live (kept)
| File | Role | Cite |
|---|---|---|
| `apps/api/handlers/shopping_list_handlers.py` | Domain business logic (`ShoppingListHandlers` class — create / approve / reject / promote / view_history) | L59–L1071 |
| `apps/api/routes/handlers/shopping_handler.py` | Phase-4 dispatch shim — registered in `SHOP_HANDLERS`, delegates to the class above; also owns `delete_shopping_item` + `mark_shopping_list_ordered` | L255–L263 |
| `apps/api/routes/handlers/__init__.py` | Wires `SHOP_HANDLERS` into `_ACTION_HANDLERS` dispatch table | L24, L39 |
| `apps/api/routes/p0_actions_routes.py` | Action executor, REQUIRED_FIELDS validation, `_ACTION_ENTITY_MAP` | L44, L58, L83–L87, L907–L911, L814 |
| `apps/api/routes/entity_routes.py` | `GET /v1/entity/shopping_list/{item_id}` — enriched detail payload | L480–L576 |
| `apps/api/routes/vessel_surface_routes.py` | List endpoint `_format_record` shopping_list branch + filter block + batch name resolver | L53, L671–L676, L747–L757, L783–L802, L1090–L1125 |
| `apps/api/action_router/registry.py` | Registers 5 canonical + 1 delete + 1 cross-domain (`add_to_shopping_list`) + 6 legacy list-level actions | see §4 |
| `apps/api/action_router/entity_prefill.py` | Injects `item_id=id` prefill for 6 shopping_list mutation actions | L145–L153 |
| `apps/web/src/app/shopping-list/page.tsx` | List view + Add-Item modal + detail overlay | all |
| `apps/web/src/app/shopping-list/[id]/page.tsx` | Standalone detail route — EntityLensPage + ShoppingListContent | all |
| `apps/web/src/app/shopping-list/layout.tsx` | DomainProvider wrapper | all |
| `apps/web/src/components/lens-v2/entity/ShoppingListContent.tsx` | Lens content — pills, lifecycle, KV, actions | all |
| `apps/web/src/features/shopping-list/adapter.ts` | Row adapter for FilteredEntityList | all |
| `apps/web/src/features/shopping-list/types.ts` | `ShoppingListItem`, `ShoppingListStateHistory`, `CreateShoppingListItemPayload` — aligned with DB | all |
| `apps/web/src/features/entity-list/types/filter-config.ts` | `SHOPPING_LIST_FILTERS` — 5 filter fields | L237–L284 |

### Dead — deleted in this pass
| File | Evidence it's dead | Risk of deletion |
|---|---|---|
| `apps/web/src/features/shopping-list/api.ts` | grep `shopping-list/api` across `apps/web/src/**` and `apps/web/e2e/**`: only self-references. Contained `fetchShoppingList / fetchShoppingListItem / fetchShoppingListHistory` — all using `supabase` client directly, which hits MASTER DB on Vercel and was the original 404 cause (PR #653 replaced it with Render API). | **LOW** — zero importers; keeping it risks regressing the 404 bug if anyone re-imports it. |
| `apps/web/src/features/shopping-list/hooks/useShoppingListActions.ts` | Zero external importers (only self-refs from its own `console.error` logs). UI now routes every action through `useEntityLens.executeAction` via `EntityLensPage` + `CreateItemModal`. | **LOW** — the hook used the old `executeAction` client pattern that bypasses the new prefill/context merge logic; re-importing it would break approve/reject with 400s again. |

### Ambiguous — left in place, flagged for follow-up
| File / Entry | Why ambiguous | Recommended action |
|---|---|---|
| `mark_shopping_list_ordered` handler @ `routes/handlers/shopping_handler.py:213` | Handler is dispatch-registered (SHOP_HANDLERS L262) and in `_ACTION_ENTITY_MAP` (p0_actions_routes.py:86) but **NOT in `ACTION_REGISTRY`** → never appears in `available_actions[]` → UI can't trigger it. Entity prefill entry at `entity_prefill.py:153` is equally unreachable. | Either add an `ActionDefinition` registration so the Split-Button can surface it, or remove the handler + prefill entry if "ordered" transitions happen via `convert_to_po` instead. Ticket owner to decide. |
| Legacy list-level actions (6): `approve_list`, `add_list_item`, `archive_list`, `delete_list`, `convert_to_po`, `submit_list` | Registered under `domain="shopping_list"` (registry.py:2744, 2756, 3735, 3747, 3832, 3844) → `get_available_actions` returns them for shopping_list entities → they appear in the SplitButton dropdown for HoD+ roles. Their labels **overlap** with canonical actions (e.g. `approve_list` label = "Approve Shopping List Item", duplicating `approve_shopping_list_item`). They operate on individual `pms_shopping_list_items` rows (verified at `internal_dispatcher.py:3262–3278` for `submit_list`). **No `pms_shopping_lists` parent table exists** (probed → HTTP 404). | Non-destructive fix: filter them out in `entity_actions.py` for `entity_type="shopping_list"` via a `_SHOPPING_LIST_HIDDEN_ACTIONS` set. Kept here as a follow-up to avoid cross-domain churn. |
| Shopping list entity response has **no `audit_history`** | `pms_shopping_list_state_history` table exists (probed → returns rows) but `entity_routes.py:480–576` doesn't query it; `ShoppingListContent.tsx` reads `audit_history` → always empty. | Additive endpoint change — add `audit_history` fetch in shopping_list branch. Safe to do later; no user harm today. |
| Lifecycle stepper incomplete in `ShoppingListContent.tsx:205` | `LIFECYCLE = ['candidate', 'under_review', 'approved', 'ordered', 'fulfilled']` — missing `rejected`, `partially_fulfilled`, `installed` which are live in DB (verified: distinct values on 1000 rows = `candidate`, `under_review`, `ordered`, `partially_fulfilled`, `installed`). When status = `partially_fulfilled` or `installed`, `currentIdx = -1` and no step renders active. | UI-only fix; add branches to the stepper. Low risk. |

---

## 2. DB surface used by shopping lens

Direct queries only:

1. **`pms_shopping_list_items`** — primary. 49 columns verified live on TENANT (service-key query against `/rest/v1/pms_shopping_list_items?select=*&limit=1`):

   **User-visible columns** (surfaced by adapter / lens / entity response):
   `part_name, part_number, manufacturer, is_candidate_part, quantity_requested, quantity_approved, quantity_ordered, quantity_received, quantity_installed, unit, preferred_supplier, estimated_unit_price, status, source_type, source_notes, urgency, required_by_date, approved_at, approval_notes, rejected_at, rejection_reason, rejection_notes, fulfilled_at, installed_at, order_line_number, created_at, updated_at, requested_at`

   **Hidden** (UUIDs / plumbing / never displayed as-is):
   `id, yacht_id, part_id, source_work_order_id, source_receiving_id, order_id, approved_by, rejected_by, installed_to_equipment_id, created_by, updated_by, deleted_by, candidate_promoted_to_part_id, promoted_by, requested_by, metadata, deleted_at, deletion_reason, is_seed, promoted_at`

2. **`auth_users_profiles`** — name lookup. `entity_routes.py:503` (single-row detail) + `vessel_surface_routes.py:789–795` (batched for the list page). No FK between this and the items table — both resolutions are manual joins.

3. **`pms_shopping_list_state_history`** — exists, populated (verified: `shopping_list_item_id / previous_state / new_state / transition_reason / changed_by / changed_at`). **Not currently read by the lens.** See ambiguity #3 above.

FK-link only (no fetch from the shopping lens):
- `pms_parts` — via `part_id` and `candidate_promoted_to_part_id` — rendered as a nav link in `_nav("part", ...)` at `entity_routes.py:533`.
- `pms_work_orders` — via `source_work_order_id` — rendered as nav link at `entity_routes.py:534`.
- `pms_receiving` / `pms_equipment` — columns exist on the row but no reads; no handler touches them.

**No other table is read from a shopping-lens code path.** Confirmed by: `grep -rn "pms_shopping\|shopping_list_item_id" apps/api --include='*.py' | grep -v test_`.

---

## 3. Bugs / fixes shipped in the two preceding PRs

### PR #653 (merged) — `fix(shopping-list): wire EntityLensPage, fix DB routing, fix action 400s`

| Bug | Root cause | File:line | Fix |
|---|---|---|---|
| Detail view 404 on Vercel | `fetchShoppingListItem` used `supabase` client directly; Vercel `NEXT_PUBLIC_SUPABASE_URL` points to MASTER DB which has no `pms_shopping_list_items` | was `apps/web/src/features/shopping-list/api.ts:24` (now deleted) | Replaced with `EntityLensPage` → Render API → TENANT DB |
| Approve/Reject 400 "Missing required field: item_id" | REQUIRED_FIELDS check at `p0_actions_routes.py:917` runs **before** `resolve_entity_context` at L1110; prefill had no shopping_list entries | `entity_prefill.py` (before this fix: empty) | Added 6 prefill entries `entity_prefill.py:148–153`, mapping `item_id ← entity.id` |
| Create flow missing | No button on the page | `apps/web/src/app/shopping-list/page.tsx` | Added `CreateItemModal` + floating "Add Item" button posting to `/api/v1/actions/execute` |
| Detail view showed sparse data | Entity endpoint returned minimal payload | `entity_routes.py:480–576` | Enriched to join user names, include all item fields + rejection/approval metadata + related-entity nav |
| `useShoppingListActions.ts:40` logic bug | `if (!activeVesselId || user?.yachtId)` short-circuited to always true when user had a yachtId | was `useShoppingListActions.ts:40` (now deleted with the whole file) | Changed to `&&` (file later deleted as it had no remaining consumers) |

### PR #656 (merged) — `fix(shopping-list): filter system + list rendering`

| Bug | Root cause | File:line | Fix |
|---|---|---|---|
| List rows showed UUID substring as title | `_format_record` in `vessel_surface_routes.py` had no `shopping_list` branch; fell to generic fallback at `vessel_surface_routes.py:1008` which emits `title = str(id)[:8]` | `vessel_surface_routes.py:1090–1125` | Added shopping_list branch returning `part_name`, urgency, qty, source, status with correct meta string |
| Requester name empty in list rows | No name resolution in list endpoint | `vessel_surface_routes.py:783–802` | Added batch `auth_users_profiles` lookup — single query per page, attached as `requested_by_name` on each formatted row |
| Urgency / source_type / is_candidate_part / required_by_date filters silently dropped | Endpoint only honored `.eq("status")` at `vessel_surface_routes.py:731` | `vessel_surface_routes.py:671–676, 747–757` | Added URL params and query filters |
| `SHOPPING_LIST_FILTERS` missing states | Status options: `[candidate, under_review, ordered, partially_fulfilled, installed]` — missing approved / rejected / fulfilled | `filter-config.ts:237` | 8-value enum + source_type + is_candidate_part + required_by_date range |
| Adapter read non-existent columns | `item.unit_of_measure` and `item.priority` — real DB cols are `unit` and `urgency` | was `adapter.ts:23, 29` | Rewrote adapter; subtitle now uses `unit`, `urgency`, candidate badge |
| `ShoppingListItem` type lied about DB shape | `unit_of_measure`, `priority`, `requested_by_id`, `approved_by_id` — none exist on `pms_shopping_list_items` | `features/shopping-list/types.ts` | Rewritten to mirror real column names; kept `*_name` resolved-only fields as documentation |

### This pass — cleanup (committed in follow-up commit)

| Change | Rationale | File |
|---|---|---|
| Delete `apps/web/src/features/shopping-list/api.ts` | Dead code; direct-Supabase client causing the original 404; zero importers | removed |
| Delete `apps/web/src/features/shopping-list/hooks/useShoppingListActions.ts` | Dead code; old action-client pattern; zero importers | removed (hooks dir now empty, also removed) |
| Fix stale registry comment | Comment at `registry.py:3897` claimed `delete_shopping_item` was "handler not deployed" but it's been live since Phase 4 (`routes/handlers/shopping_handler.py:256`) | `registry.py:3897` |

---

## 4. Action wiring — the full truth table

| action_id | In `ACTION_REGISTRY`? | In `REQUIRED_FIELDS`? | In `_ACTION_ENTITY_MAP`? | In `entity_prefill`? | In `SHOP_HANDLERS`? | In `get_available_actions` output? | Shown by UI? |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `create_shopping_list_item` | ✓ (1980) | `[source_type]` (907) | ✓ (83) | — (created via modal) | ✓ (257) | ✓ | floating Add-Item btn |
| `approve_shopping_list_item` | ✓ (2014) | `[item_id, quantity_approved]` (908) | ✓ (84) | `item_id=id` (148) | ✓ (258) | ✓ | primary SplitButton |
| `reject_shopping_list_item` | ✓ (2033) | `[item_id, rejection_reason]` (909) | ✓ (85) | `item_id=id` (149) | ✓ (259) | ✓ | dropdown |
| `promote_candidate_to_part` | ✓ (2053) | `[item_id]` (910) | ✓ (87) | `item_id=id` (150) | ✓ (260) | ✓ | dropdown |
| `view_shopping_list_history` | ✓ (2069) | `[item_id]` (911) | — | `item_id=id` (151) | ✓ (261) | ✓ | dropdown |
| `delete_shopping_item` | ✓ (3380) | `[item_id]` (814) | — | `item_id=id` (152) | ✓ (256) | ✓ | dropdown (danger) |
| `mark_shopping_list_ordered` | **✗** | — | ✓ (86) | `item_id=id` (153) | ✓ (262) | **✗** | **never** |
| `add_to_shopping_list` (cross-domain) | ✓ (3454) | — | — | triggered on `part` entities (entity_prefill L175) | n/a — handler lives elsewhere | only on `part` entity | part lens |
| `approve_list` | ✓ (2744) | — | — | — | ✗ (legacy dispatcher) | ✓ | **leaks into dropdown** |
| `add_list_item` | ✓ (2756) | — | — | — | ✗ | ✓ | **leaks into dropdown** |
| `archive_list` | ✓ (3735) | — | — | — | ✗ | ✓ | **leaks into dropdown** |
| `delete_list` | ✓ (3747) | — | — | — | ✗ | ✓ | **leaks into dropdown** |
| `convert_to_po` | ✓ (3832) | — | — | — | ✗ | ✓ | **leaks into dropdown** |
| `submit_list` | ✓ (3844) | — | — | — | ✗ | ✓ | **leaks into dropdown** |

"Leaks into dropdown" means: `ShoppingListContent.tsx:187–202` maps *all* `availableActions` (minus the primary) into `DropdownItem[]`, so any action returned by `get_available_actions` with the user's role appears in the SplitButton dropdown. These 6 legacy actions still show up for HoD+ users today. **This is a live UX bug** — user confusion, not a crash.

---

## 5. Risk analysis for the cleanup changes

| Change | Blast radius | Rollback cost | Confidence |
|---|---|---|---|
| Delete `features/shopping-list/api.ts` | Zero — not imported | `git revert` | HIGH — verified by grep across `src/` and `e2e/` |
| Delete `features/shopping-list/hooks/useShoppingListActions.ts` | Zero — not imported | `git revert` | HIGH — verified by grep across `src/` and `e2e/` |
| Fix comment at `registry.py:3897` | Zero — comment only | `git revert` | HIGH |

**Total blast radius:** nil. No runtime behavior changes. No type signatures changed. Local `npm run build` was attempted — the build currently fails on receiving-domain changes (`features/receiving/_deprecated/ReceivingPhotos.tsx:18` imports `'../api'` which was moved into the `_deprecated/` folder itself; this is another agent's unfinished work, present in the working tree before this audit). A targeted `tsc --noEmit` shows zero shopping-list type errors.

---

## 6. Follow-ups — CLOSED (PR #665, merged 2026-04-23)

All four items from the original follow-up list have been executed and shipped.

1. **✅ `mark_shopping_list_ordered` registered.** `ActionDefinition` added at `registry.py` adjacent to `view_shopping_list_history`; roles mirror `_MARK_ORDERED_ROLES` (`chief_engineer / captain / manager`). REQUIRED_FIELDS entry added at `p0_actions_routes.py` (`["item_id"]`). State gate added at `entity_actions.py` so the action is disabled unless `status == 'approved'`; the same gate disables `approve / reject / promote / mark_ordered` with a human-readable reason when the status is terminal (`rejected / fulfilled / installed`).

2. **✅ 6 legacy list-level actions hidden.** `_SHOPPING_LIST_HIDDEN_ACTIONS = {approve_list, add_list_item, archive_list, delete_list, convert_to_po, submit_list}` in `entity_actions.py`. `get_available_actions` skips any action in this set when `entity_type='shopping_list'`. Registry entries and internal_dispatcher handlers are left intact so programmatic callers still work. Verified by Python smoke test — captain on a shopping_list entity no longer sees these 6 in the response.

3. **✅ `audit_history` surfaced.** `entity_routes.py` shopping_list endpoint fetches `pms_shopping_list_state_history` ordered by `changed_at`, batches every actor UUID (requester + approver + every history actor) into a single `auth_users_profiles` query (no N+1), projects rows into `{action, actor, timestamp, previous_state, new_state, transition_notes}`. The existing `ShoppingListContent.tsx:158-163` reader consumes `{action, actor, timestamp}` directly. Failure mode is fail-soft: `audit_history = []` on any DB error.

4. **✅ Lifecycle stepper extended.** `LIFECYCLE` in `ShoppingListContent.tsx:205` is now `[candidate, under_review, approved, ordered, partially_fulfilled, fulfilled, installed]`. `rejected` is handled as a terminal off-ramp: a red banner (uses existing design tokens `--red` / `--red-bg`) with the rejection reason replaces the stepper entirely — previously `currentIdx === -1` silently produced a stepper with no active step.

### New follow-ups surfaced during this pass

- `add_to_shopping_list` is registered with `domain="shopping_list"` (registry.py:3454) AND as a cross-domain action on `part` entities (entity_actions.py:151). Because of the domain field it is also returned by `get_available_actions` for the shopping_list entity itself, where it duplicates the floating "+ Add Item" button's intent. Low-priority UX cleanup — consider either dropping it from the shopping_list dropdown via `_SHOPPING_LIST_HIDDEN_ACTIONS` or moving it to cross-domain-only (domain=parts, injected to shopping_list? — no, actually the cleanest fix is hide-from-UI).

---

## Appendix A — Commands used for verification

```bash
# Live DB column dump
curl -s 'https://vzsohavtuotocgrfkfyd.supabase.co/rest/v1/pms_shopping_list_items?select=*&limit=1' \
  -H 'apikey: <TENANT_SERVICE_KEY>' -H 'Authorization: Bearer <TENANT_SERVICE_KEY>'

# Live distinct status/urgency/source_type values (1000-row sample)
curl -s 'https://vzsohavtuotocgrfkfyd.supabase.co/rest/v1/pms_shopping_list_items?select=status,urgency,source_type&limit=1000' …

# Probe for legacy parent table — returned HTTP 404
curl -sI 'https://vzsohavtuotocgrfkfyd.supabase.co/rest/v1/pms_shopping_lists?select=*&limit=1' …

# Dead-file trace
grep -rn "shopping-list/api\|useShoppingListActions\|fetchShoppingList" apps/web/src apps/web/e2e

# Action registry enumeration
awk '/^    "[a-z_]+": ActionDefinition\(/{a=$0} /domain="shopping_list"/{…print a}' apps/api/action_router/registry.py
```
