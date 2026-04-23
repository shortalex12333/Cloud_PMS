# Receiving Bugfix Log — 2026-04-23

Owner: receiving05  
Branch: `fix/documents-422` → merged to `main` via PR #654 (initial wave) and follow-up commits  
Render deploy: triggered via deploy hook for backend changes

This log enumerates every bug from `docs/ongoing_work/receiving/receiving_errors.md`,
the root cause located in code, the change made, and the citation.

---

## Issue 1 — Where the receiving page reads its data

**Source asked for:** what table, what filter, what is human-readable vs hidden, RLS confirmation.

### List view (the cards on `/receiving`)

| Layer | File | Line(s) | Behaviour |
|---|---|---|---|
| Page | `apps/web/src/app/receiving/page.tsx` | 41–53 | Renders `FilteredEntityList` with `domain="receiving"`, `queryKey=['receiving']` |
| Hook | `apps/web/src/features/entity-list/hooks/useFilteredEntityList.ts` | 162 | Calls `${API_BASE}/api/vessel/${vesselId}/domain/receiving/records` |
| API | `apps/api/routes/vessel_surface_routes.py` | 663 (`get_domain_records`) | Routes to `pms_receiving` (`DOMAIN_TABLE_MAP` line 55) |
| DB query | (same file) | 949–977 (`_format_record` for receiving) | Selects all columns (`DOMAIN_SELECT["receiving"] = "*"` line 73) |

Tenant client used: `get_tenant_client(tenant_key)` — auth context provides `tenant_key_alias` from JWT. Yacht scope enforced via `.eq("yacht_id", yacht_id)` server-side AND via RLS policy `pms_receiving_select_yacht_scope` (`USING has_yacht_access(yacht_id)`).

### Detail view (the card overlay)

| Layer | File | Line(s) | Behaviour |
|---|---|---|---|
| Overlay | `apps/web/src/app/receiving/page.tsx` | 54–58 | Mounts `EntityLensPage entityType="receiving"` |
| Hook | `apps/web/src/hooks/useEntityLens.ts` | 41 | `GET ${API_BASE}/v1/entity/receiving/{id}` |
| API | `apps/api/routes/entity_routes.py` | 1301–1418 | `get_receiving_entity` |
| Tables read | (same) | 1309 (`pms_receiving`), 1321 (`pms_receiving_items`), 1328 (`pms_attachments` via `_get_attachments`), 1349 (`pms_purchase_orders` for po_id), 1372 (`auth_users_profiles` for received_by name), 1382 (`yacht_registry` for yacht_name), 1396 (`ledger_events` for audit_history) | All scoped `.eq("yacht_id", yacht_id)` |

### Field classification — `pms_receiving`

Cited from live `\d pms_receiving` (tenant DB).

| Column | Type | UI exposure | Rendered where |
|---|---|---|---|
| `id` | uuid | **HIDDEN** | URL only, never displayed |
| `yacht_id` | uuid | **HIDDEN** | RLS scope only |
| `vendor_name` | text | **VISIBLE** | List title (`vessel_surface_routes.py:957`); lens IdentityStrip (`ReceivingContent.tsx:80,124`) |
| `vendor_reference` | text | **VISIBLE** | Lens detail line (`ReceivingContent.tsx:81,127-128`) |
| `received_date` | date | **VISIBLE** | List subtitle, lens detail (`ReceivingContent.tsx:82`) |
| `received_by` | uuid | **HIDDEN as UUID** — resolved server-side to user name | Lens detail line "Received By" (`ReceivingContent.tsx:83,136`) |
| `status` | text (enum) | **VISIBLE** | List status pill, lens IdentityStrip pill (`ReceivingContent.tsx:77,116`) |
| `currency` | text | **VISIBLE** | Lens (when total shown) |
| `subtotal`/`tax_total`/`total` | numeric | **VISIBLE** | Lens — currently not rendered (gap, see RECEIVING_AUDIT.md) |
| `linked_work_order_id` | uuid | **HIDDEN** | Used to compute `nav` related entities |
| `notes` | text | **VISIBLE** | Lens NotesSection (`ReceivingContent.tsx:89`) |
| `properties` | jsonb | **HIDDEN** | Internal extension point |
| `created_at`/`updated_at` | timestamp | **VISIBLE** | List `age`, lens audit context |
| `created_by` | uuid | **HIDDEN** | Audit only |
| `po_number` | text | **VISIBLE** | List ref (when present), lens IdentityStrip (`ReceivingContent.tsx:78,131`) |
| `deleted_at`/`deleted_by` | timestamp/uuid | **HIDDEN** | Soft-delete bookkeeping |
| `is_seed` | boolean | **HIDDEN** | Demo data flag |

### Action buttons rendered in lens

Sourced from `availableActions[]` returned by `get_available_actions("receiving", entity, role)` in `entity_routes.py:1418`. Render gating in `ReceivingContent.tsx:103-194`. Per-action role table in **RECEIVING_ACTIONS_MATRIX.md**.

| Button | Source action_id | KEEP/REMOVE | Notes |
|---|---|---|---|
| Confirm Receipt (primary) | `confirm_receiving` | KEEP | HOD+captain only, marks `accepted` w/o signature |
| Add Line Item | `add_receiving_item` | KEEP | HOD+captain+purser+manager, requires `quantity_received` |
| Adjust Line Item | `adjust_receiving_item` | KEEP | HOD+captain+purser+manager |
| Flag Discrepancy | `reject_receiving` (label: "Flag Receiving Issue") | KEEP | All crew can flag — discovery role |
| Attach Image/Document | `attach_receiving_image_with_comment` | KEEP | All crew |
| Extract from Image (OCR) | `extract_receiving_candidates` | KEEP | HOD+captain+purser+manager, advisory only |
| Update Receiving Fields | `update_receiving_fields` | KEEP | HOD+captain+purser+manager |
| Link Invoice PDF | `link_invoice_document` | KEEP | HOD+captain+purser+manager |
| Accept Receiving (Sign) | `accept_receiving` | KEEP | HOD+captain+purser+manager, **PIN/TOTP signature required** |
| View Receiving History | `view_receiving_history` | KEEP | All crew, read-only |
| Submit for Review | `submit_receiving_for_review` | KEEP | New Phase 4 handler, `routes/handlers/receiving_handler.py:28` |
| Edit Receiving | `edit_receiving` | KEEP | New Phase 4 handler, `routes/handlers/receiving_handler.py:60` |

---

## Issue 2 — 404 when opening any card (wrong DB)

**Status:** **FIXED** (commit `43dff37`).

### Root cause

`apps/web/src/app/receiving/page.tsx` (pre-fix) defined a custom `ReceivingDetail` component that called `fetchReceivingItem(id, token)` from `apps/web/src/features/receiving/api.ts:30`. That function used the imported `supabase` client from `apps/web/src/lib/supabaseClient.ts:15`, which reads `NEXT_PUBLIC_SUPABASE_URL` — the **MASTER** Supabase used for auth. `pms_receiving` exists only in the **TENANT** Supabase. Result: `GET https://qvzmkaamzaqxpzbewjxe.supabase.co/rest/v1/pms_receiving?...` → 404 (the URL captured in the user's console error log).

### Fix

`apps/web/src/app/receiving/page.tsx` now mirrors the proven pattern in `apps/web/src/app/purchasing/page.tsx:88`:

```tsx
<EntityDetailOverlay isOpen={!!selectedId} onClose={handleCloseDetail}>
  {selectedId && (
    <EntityLensPage entityType="receiving" entityId={selectedId} content={LensContent} />
  )}
</EntityDetailOverlay>
```

`EntityLensPage` → `useEntityLens` (`apps/web/src/hooks/useEntityLens.ts:41`) → `GET pipeline-core.int.celeste7.ai/v1/entity/receiving/{id}` → backend `get_receiving_entity` (`apps/api/routes/entity_routes.py:1301`) → tenant client → `pms_receiving`.

The deep-link route `apps/web/src/app/receiving/[id]/page.tsx` already used this pattern. The two routes are now consistent.

### Quarantined dead code

- `apps/web/src/features/receiving/api.ts` → moved to `_deprecated/api.ts`
- `apps/web/src/features/receiving/components/ReceivingPhotos.tsx` → moved to `_deprecated/ReceivingPhotos.tsx`
- README in `_deprecated/` explains origin, last caller, and deletion criteria.

---

## Issue 3 — UUIDs visible to user

**Status:** **FIXED** (multiple commits).

### Bugs found

1. **List title shows UUID fragment.** `vessel_surface_routes.py` (pre-fix L952) emitted `"title": f"Receiving {str(record.get('id', ''))[:8]}"`. When `vendor_name` is null (test fixtures), the user saw `Receiving ac137d1e`.
2. **List meta shows received_by UUID.** Pre-fix L956 emitted `"meta": f"{record.get('received_by', '')} · {record.get('status', '').upper()}"` — `received_by` is a UUID column.
3. **List entityRef empty.** Frontend adapter `apps/web/src/features/receiving/adapter.ts` (pre-fix L46) read `item.receiving_number || ''`, which the API never returns. Empty `entityRef` caused fall-back to `SpotlightResultRow` instead of the proper `EntityRecordRow` (the rich `@ ref — title` row format).
4. **Lens detail shows received_by UUID.** Lens read `entity.received_by` and displayed it verbatim (`ReceivingContent.tsx:83,136`).

### Fixes

- `apps/api/routes/vessel_surface_routes.py:949-977` (new block):
  - `title` = `vendor_name` → `Received {day} {Mon} {year}` → `"Draft Receiving"`
  - `ref` = `f"PO {po_num}"` if PO known, else `f"RCV-{id[:6]}"` (a short hex prefix, NOT a UUID)
  - `meta` = `f"{vendor or 'No vendor'} · {status_val.upper()}"` — no UUIDs.
  - Adds `vendor_name`, `po_number`, `received_date` as top-level keys so the adapter has them.
- `apps/web/src/features/receiving/adapter.ts:23-60` (new):
  - Reads `raw.vendor_name` (API field) with `supplier_name` fallback (legacy alias).
  - `entityRef = raw.ref` — uses the pre-formatted ref the backend now sends.
  - Title falls through `vendorName → raw.title → "Draft Receiving"`.
- `apps/api/routes/entity_routes.py:1340-1349` (new): joins `auth_users_profiles` to resolve `received_by` UUID → user name. The lens still reads `entity.received_by`, but the value is now the human name. UUID never leaves the backend.

### What is now ALWAYS hidden from the UI
- `pms_receiving.id` (uuid)
- `pms_receiving.yacht_id` (uuid)
- `pms_receiving.received_by` (uuid) — only the resolved name reaches the UI
- `pms_receiving.created_by` / `deleted_by` (uuid)
- `pms_receiving.is_seed` (internal flag)
- `pms_receiving.properties` (internal jsonb)

---

## Issue 4 — Filtering is weak

**Status:** **FIXED** (commit `43dff37`).

### Before

`RECEIVING_FILTERS` in `apps/web/src/features/entity-list/types/filter-config.ts:202-221` had only `status` (select) and `received_date` (date-range). No way to find a receiving by vendor or by PO.

### After (current `filter-config.ts:202-235`)

Added:
- `vendor_name` — text filter, category `properties`. Hits the `vendor_name` column directly via the API (the hook converts text fields to `ilike` semantics — see `useFilteredEntityList.ts:154`).
- `po_number` — text filter, category `properties`.

The Subbar search input is also already wired to `title` (`useFilteredEntityList.ts:155`), which the API maps to `q=` for fuzzy search (`vessel_surface_routes.py` `get_domain_records`).

### What's NOT filterable yet (deliberately deferred)

- `received_by` — filter UI would need a user-picker, which doesn't exist yet for receiving.
- `currency` — low ROI for MVP.
- Date received vs date created — only `received_date` is exposed; users can use Subbar sort for created_at.

---

## Issue 5 — Buttons did nothing

**Status:** **FIXED** (commit `43dff37`).

### Root cause

The dead `ReceivingDetail` component (now removed) wired buttons via `useActionHandler.executeAction(...)`. But because `useQuery` (in the same component) returned `error` on every load (the 404 from Issue 2), the entire detail panel rendered the error fallback — buttons were never visible. When testing flow opened the rare card that loaded successfully, the buttons were not gated by `availableActions`, so role-restricted actions also fired blind 403s.

### Fix

`EntityLensPage + ReceivingContent` reads `availableActions` from the API response (computed by `get_available_actions("receiving", entity, role)` in `entity_routes.py:1418`). The lens (`ReceivingContent.tsx:181-194`) builds the dropdown from those actions, gates each by `disabled`, and routes through `safeExecute` (the parent `EntityLensPage` intercepts SIGNED actions to show the PIN modal).

Every button is now:
- Visible only if the role has access (server-side gate).
- Wired to a real handler (registry → `internal_dispatcher` → `ReceivingHandlers` adapter).
- Shows discrepancy/disabled reasons inline.

Confirmed handlers exist for every receiving action:
- `apps/api/handlers/receiving_handlers.py` — 10 v1 actions (lines 153, 287, 428, 577, 735, 895, 1028, 1206, 1399, 1517) + flag_discrepancy adapter (1659)
- `apps/api/routes/handlers/receiving_handler.py` — 2 Phase 4 actions (`submit_receiving_for_review`, `edit_receiving`)

---

## Lens contract bugs found during audit (NEW, not in original issues)

### A. `notes` type mismatch (would crash)

Lens code (`ReceivingContent.tsx:89` pre-fix) cast `entity.notes` to `Array<Record<string, unknown>>`, but `pms_receiving.notes` is a `text` column → backend returns a string. JavaScript strings have no `.map`, so the lens would throw at runtime when a record had notes set.

**Fix:** `ReceivingContent.tsx:89-99` (new) defensively wraps a string into a single note row, keeps array passthrough for future schema extension. No DB migration required.

### B. `po_id` was never returned

Lens uses `po_id` to navigate from the receiving lens to the linked purchase order (`ReceivingContent.tsx:154`). Backend pre-fix only put the PO id inside `related_entities[]` — the top-level `po_id` was undefined → the link was silently disabled.

**Fix:** `entity_routes.py:1387` now sets `po_id` at the top level alongside `po_number`.

### C. `yacht_name` not surfaced

Lens displays `Vessel: {yacht_name}` in the IdentityStrip (`ReceivingContent.tsx:84,139-141`). Backend pre-fix never resolved it → blank in UI.

**Fix:** `entity_routes.py:1382-1390` joins `yacht_registry` once per call.

### D. `audit_history` empty

Lens renders an `AuditTrailSection` (`ReceivingContent.tsx:329`). Backend pre-fix returned no history → "No events" was always shown.

**Fix:** `entity_routes.py:1396-1404` queries `ledger_events` for this `entity_type='receiving'` + `entity_id` (already scoped by yacht_id).

### E. `total_items` missing

Lens header shows the item count pill (`ReceivingContent.tsx:120-122`). Without `total_items`, the count fell back to `items.length` only when items had loaded — fine, but inconsistent with other entities that send the count separately.

**Fix:** `entity_routes.py:1391` sets `total_items = len(raw_items)`.

---

## Out-of-scope but flagged: Inventory stock not updated on accept

`accept_receiving` in `apps/api/handlers/receiving_handlers.py:1206-1397` marks `pms_receiving.status = 'accepted'` and writes a `ledger_events` row. **It does NOT update `pms_inventory_stock.quantity`** for any line item with a `part_id`. See `RECEIVING_INVENTORY_GAP.md`.

---

## Files changed (this session)

| File | Why |
|---|---|
| `apps/api/routes/vessel_surface_routes.py` (`_format_record` receiving block) | Issue 3 list title |
| `apps/api/routes/entity_routes.py` (`get_receiving_entity`) | Issue 3 detail UUID, contract gaps A–E |
| `apps/web/src/app/receiving/page.tsx` | Issues 2 & 5 |
| `apps/web/src/features/receiving/adapter.ts` | Issue 3 list mapping |
| `apps/web/src/components/lens-v2/entity/ReceivingContent.tsx` | Lens contract bug A |
| `apps/web/src/features/entity-list/types/filter-config.ts` | Issue 4 |
| `apps/web/src/features/receiving/_deprecated/*` (moved) | Repo cleanup — quarantine of dead code |
