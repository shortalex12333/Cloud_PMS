# Shopping List V2 — Status

**Shipped:** PR #737 + PR #739 (merged 2026-04-27T13:10Z) · Frontend fixes in working branch  
**DB migrations:** M0–M6 applied to TENANT — do not re-run  
**Render deploy:** `dep-d7nltf1f9bms738jnqg0` — import fix live

---

## What's live

| Layer | File | Description |
|---|---|---|
| Handler | `apps/api/handlers/shopping_list_v2_handlers.py` | 7 list-level actions: create, add_item, update_item, delete_item, submit, hod_review, approve |
| Route | `apps/api/routes/shopping_list_pdf_route.py` | `GET /v1/shopping-list`, `/{id}`, `/{id}/pdf` (A4 PyMuPDF) |
| Registry | `apps/api/action_router/registry.py` | 8 ActionDefinitions: 7 V2 list actions + add_shopping_list_photo |
| Dispatcher | `apps/api/action_router/dispatchers/internal_dispatcher.py` | 8 wrappers; `add_to_shopping_list` passes `shopping_list_id` + urgency |
| Frontend | `apps/web/src/app/shopping-list/page.tsx` | Document list table + CreateListModal |
| Frontend | `apps/web/src/app/shopping-list/[id]/page.tsx` | Full document view — identity strip, status-gated actions, items table, PDF link |
| Frontend | `apps/web/src/app/inventory/AddToListModal.tsx` | Draft-list picker modal launched from PartDetail overlay |
| Frontend | `apps/web/src/app/inventory/page.tsx` | PartDetail overlay with "Add to Shopping List" CTA |

**Status flow:** `draft → submitted → hod_approved → converted_to_po` (convert owned by PURCHASE05)

---

## Bugs fixed (PR #739 + post-merge cleanup)

**1. `/v1/shopping-list` returned 404**  
`apps/api/routes/shopping_list_pdf_route.py:27`  
`from db import get_supabase_client` — module `db` doesn't exist.  
Silent failure: `pipeline_service.py` wraps the import in `try/except`, so the route was never registered.  
→ Fixed: `from integrations.supabase import get_supabase_client`

**2. `add_to_shopping_list` from Parts lens wrote invalid status**  
`apps/api/handlers/part_handlers.py:414`  
`status='requested'` violates the M3 CHECK constraint (valid values: candidate, under_review, approved, rejected, ordered, partially_fulfilled, fulfilled, installed).  
→ Fixed: `status='candidate'`

**3. `shopping_list_id` not passed through from dispatcher**  
`apps/api/action_router/dispatchers/internal_dispatcher.py:3043`  
Parts added via `add_to_shopping_list` got `shopping_list_id=None` — invisible on the V2 document page.  
→ Fixed: `shopping_list_id=params.get("shopping_list_id")` passed to handler

**4. `urgency='medium'` invalid**  
`apps/api/handlers/part_handlers.py:379` + `internal_dispatcher.py:3043`  
Valid options are `low / normal / high / critical`. `medium` silently stored a bad value.  
→ Fixed: default changed to `'normal'` in both locations

**5. Currency code `'MED'` not a real ISO code**  
`apps/web/src/app/shopping-list/page.tsx:289`  
CreateListModal offered `{ value: 'MED', label: 'USD — Med Charter' }`.  
→ Fixed: `{ value: 'CHF', label: 'CHF — Swiss Franc' }`

**6. No "Add to Shopping List" entry point from inventory**  
`apps/web/src/app/inventory/page.tsx`  
PartDetail overlay was read-only — no action button.  
→ Fixed: added "Add to Shopping List" CTA + `AddToListModal`

**7. `notes` field silently dropped on add/edit item**  
`apps/web/src/app/shopping-list/[id]/page.tsx` (popup) vs `shopping_list_v2_handlers.py`  
Frontend sent `notes`, handler read `source_notes` — mismatch, never saved.  
→ Fixed: renamed popup field from `notes` → `source_notes`. Handler reads `source_notes` correctly.

**8. `source_url` / `storage_location` in popup but never saved**  
`apps/web/src/app/shopping-list/[id]/page.tsx`  
Fields shown in add/edit item popup but `shopping_list_v2_handlers.py` never inserts them.  
DB column existence unconfirmed. Removed from popup to avoid silent data loss.

**9. `shopping_list_item` entity type missing from entityRoutes**  
`apps/web/src/lib/entityRoutes.ts`  
New-style V2 line items emit `entity_type='shopping_list_item'` in ledger. This type was not in  
`EntityRouteType` union, so ledger navigation would fall through to `/` (root). Added to union and routeMap.

---

## Open follow-ups

**Candidate part data continuity** (not yet built)  
`pms_shopping_list_items` rows with `is_candidate_part=true` and `part_id IS NULL` should:
- Write a ledger row at creation: `event_type='shopping_list.candidate_captured'`, `requires_followup=true`
- Queue a recurring weekly notification to the requester until the row is promoted or rejected

**PO PDF export** (not yet built)  
`/v1/purchase-order/{id}/pdf` — accepted lines + denied lines with reasons + tracking + totals. Owned by PURCHASE05.

**`upload_invoice` storage** (fake path)  
`apps/api/action_router/dispatchers/internal_dispatcher.py` — writes `pending/...` path, no real Supabase Storage upload wired.

**`update_supplier` action** (not built)  
No registry entry, handler, or UI exists.

**`add_item_to_purchase` silent rejection** (no toast)  
If a PO is not in `draft` status the action silently fails with no user-facing feedback.

**`source_url` / `storage_location` on items** (deferred)  
Were included in UI but removed (2026-04-27) as DB columns unconfirmed. Confirm schema, add columns if  
needed via migration, add to handler insert/update, add back to popup.
