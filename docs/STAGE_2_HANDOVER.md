# Stage 2 Handover — Lens Data Construction & Display

**Date:** 2026-03-11
**Author:** Search Interface Officer (automated audit)
**Branch:** `feat/fragmented-routes-all-lenses`
**Scope:** Everything needed for stage 2 engineer to polish lens data display

---

## Architecture Summary

Users search via Spotlight → F1 search returns results from `search_index` → user clicks result → RouteShell fetches entity detail via `/v1/entity/{type}/{id}` → renders the matching LensContent component.

```
SpotlightSearch
  → useCelesteSearch (hooks/useCelesteSearch.ts)
    → GET /api/f1/search/stream?q=...  (SSE)
      → result_batch events with { object_type, object_id, payload }

User clicks result:
  → router.push(/{entity_route}/{id})
    → RouteShell.tsx fetches GET /v1/entity/{type}/{id}
      → LensContent component renders detail view
```

### Key Files

| Layer | File | Purpose |
|-------|------|---------|
| Routing | `apps/web/src/components/lens/RouteShell.tsx` | Unified wrapper — fetches entity, delegates to LensContent |
| Search | `apps/web/src/hooks/useCelesteSearch.ts` | F1 SSE wiring, result mapping |
| Config | `apps/web/src/lib/lens_matrix.json` | 12 lenses, 87 actions, 73 filters |
| API Entry | `apps/api/pipeline_service.py` | FastAPI app, all route registration |
| Search API | `apps/api/routes/f1_search_streaming.py` | SSE search endpoint |
| Actions | `apps/api/routes/p0_actions_routes.py` | Action lifecycle (prefill/prepare/execute) |

---

## RouteShell → API Endpoint Mapping

RouteShell calls `GET /v1/entity/{endpoint}/{id}` where `endpoint` is mapped from entity type.

**Tested 2026-03-11 against running Docker (celeste-api):**

| Entity Type | API Endpoint | HTTP Status | Notes |
|-------------|-------------|-------------|-------|
| `work_order` | `/v1/entity/work_order/{id}` | **200** | Enriched: notes, parts, checklist, audit_history, available_actions |
| `fault` | `/v1/entity/fault/{id}` | **200** | Includes ai_diagnosis, has_work_order flag |
| `equipment` | `/v1/entity/equipment/{id}` | **200** | Full detail with attention_flag |
| `part` | `/v1/entity/part/{id}` | **200** | Maps name→part_name, quantity_on_hand→stock_quantity |
| `inventory` | `/v1/entity/part/{id}` | **200** | Same endpoint as part (RouteShell maps inventory→part) |
| `receiving` | `/v1/entity/receiving/{id}` | **200** | Minimal: vendor_name, status, total, currency |
| `certificate` | `/v1/entity/certificate/{id}` | **404** | **ENDPOINT DOES NOT EXIST in pipeline_service.py** |
| `handover` | `/v1/entity/handover/{id}` | — | No handover rows in search_index (only `handover_item` type exists, 44 rows) |
| `handover_export` | `/v1/entity/handover_export/{id}` | — | Not tested (no search_index data; component fetches directly from Supabase) |
| `hours_of_rest` | `/v1/entity/hours_of_rest/{id}` | **404** | **ENDPOINT DOES NOT EXIST in pipeline_service.py** |
| `warranty` | `/v1/entity/warranty/{id}` | — | Not tested (no warranty type in search_index) |
| `shopping_list` | `/v1/entity/shopping_list/{id}` | — | Not tested (search_index uses `shopping_item` type, not `shopping_list`) |
| `document` | `/v1/entity/document/{id}` | **404** | **ENDPOINT DOES NOT EXIST in pipeline_service.py** |
| `worklist` | `/v1/entity/worklist/{id}` | — | Not tested (no worklist type in search_index) |

### Entity endpoints that exist in pipeline_service.py (lines 904-1310)

Only 5 `/v1/entity/` detail endpoints are implemented:

1. `GET /v1/entity/fault/{fault_id}` (line 904)
2. `GET /v1/entity/work_order/{work_order_id}` (line 1057)
3. `GET /v1/entity/equipment/{equipment_id}` (line 1187)
4. `GET /v1/entity/part/{part_id}` (line 1235)
5. `GET /v1/entity/receiving/{receiving_id}` (line 1282)

### Missing `/v1/entity/` endpoints (RouteShell expects them but they return 404)

- **certificate** — Has handler class `CertificateHandlers` in `handlers/certificate_handlers.py` and routes at `/api/v1/certificates/*`, but no `/v1/entity/certificate/{id}` endpoint
- **document** — Has document signing/streaming at `/v1/documents/{id}/sign` and `/v1/documents/{id}/stream`, but no `/v1/entity/document/{id}` endpoint
- **hours_of_rest** — Has routes in `routes/hours_of_rest_routes.py`, but no `/v1/entity/hours_of_rest/{id}` endpoint
- **handover** — Has handler class `HandoverHandlers` in `handlers/handover_handlers.py`, but no `/v1/entity/handover/{id}` endpoint
- **warranty** — No handler, no routes, no endpoint
- **shopping_list** — Has handler class `ShoppingListHandlers` in `handlers/shopping_list_handlers.py`, but no `/v1/entity/shopping_list/{id}` endpoint
- **worklist** — No handler, no routes, no endpoint

---

## Search Index Data (search_index table)

**Total rows:** 12,251

| object_type | Count | Payload Keys |
|-------------|-------|-------------|
| `work_order` | 428 | equipment_id, label, status |
| `work_order_note` | 2704 | created_at, note_type, snippet, source_table |
| `fault` | 1706 | fault_code, severity, source_table, status, title |
| `equipment` | 637 | code, location, manufacturer, model, name, source_table, status |
| `part` | 886 | category, location, manufacturer, name, part_number, quantity, source_table |
| `inventory` | 401 | location, part_id, quantity, source_table |
| `certificate` | 287 | authority, expiry, name, number, source_table, status |
| `email` | 229 | folder, from_display_name, has_attachments, preview_text, received_at, source_table, subject |
| `document` | 2998 | doc_type, size, source_table, title, url |
| `receiving` | 880 | currency, line_items_text, received_date, source_table, status, total, vendor_name, vendor_reference |
| `shopping_item` | 773 | part_name, part_number, quantity, source_table, status, urgency |
| `hours_of_rest` | 214 | compliance_state, crew_name, has_exception, is_compliant, is_daily_compliant, is_weekly_compliant, location, object_id, record_date, status, title, total_rest_hours, total_work_hours, user_id, voyage_type, weekly_rest_hours |
| `handover_item` | 44 | action_summary, category, entity_id, entity_type, is_critical, priority, section, source_table, status, summary |
| `supplier` | 50 | contact_name, email, name, phone, preferred, source_table |
| `purchase_order` | 9 | currency, ordered_at, po_number, received_at, source_table, status |
| `note` | 5 | note_type, snippet, source_table |

### Search payload vs. LensContent expected fields — Gap Analysis

The search payload (from `search_index.payload`) is **sparse** — it's optimized for search result snippets, not for full entity display. RouteShell does NOT use search payload for detail views. It makes a separate `GET /v1/entity/{type}/{id}` call that returns enriched data from the source tables.

**Where the data flows:**

```
Search result card (in SpotlightSearch):
  → Uses search_index.payload for preview snippet
  → Only needs: name/title, status, type identifier

Detail view (after click, in LensContent):
  → RouteShell fetches /v1/entity/{type}/{id}
  → Returns full entity from source DB table (pms_work_orders, pms_faults, etc.)
  → LensContent renders from this enriched payload
```

**Therefore:** The payload gap is NOT a blocker for lens display. The search payload is intentionally minimal. The real blocker is the missing `/v1/entity/` endpoints listed above.

---

## Per-Lens Status

### 1. Work Order — WORKING

| Item | File | Status |
|------|------|--------|
| Search result | search_index (428 rows) | Working |
| Detail endpoint | `/v1/entity/work_order/{id}` | **200** — enriched with notes, parts, checklist, history |
| Frontend component | `WorkOrderLensContent.tsx` | Present |
| Action hook | `useWorkOrderActions.ts` | 9 actions, 7 modals |
| Handler | `handlers/` (inline in pipeline_service.py) | Present |

**Response keys (tested):** id, wo_number, title, description, status, priority, type, equipment_id, equipment_name, assigned_to, assigned_to_name, due_date, created_at, updated_at, completed_at, completed_by, fault_id, notes, notes_count, parts, parts_count, checklist, checklist_count, checklist_completed, audit_history, available_actions

---

### 2. Fault — WORKING

| Item | File | Status |
|------|------|--------|
| Search result | search_index (1706 rows) | Working |
| Detail endpoint | `/v1/entity/fault/{id}` | **200** |
| Frontend component | `FaultLensContent.tsx` | Present |
| Action hook | `useFaultActions.ts` | 5 actions |
| Handler | `handlers/fault_handlers.py` | Present — view, diagnose, history, suggest_parts |

**Response keys (tested):** id, title, description, severity, status, equipment_id, equipment_name, reported_at, reporter, has_work_order, ai_diagnosis, created_at, updated_at

---

### 3. Equipment — WORKING

| Item | File | Status |
|------|------|--------|
| Search result | search_index (637 rows) | Working |
| Detail endpoint | `/v1/entity/equipment/{id}` | **200** |
| Frontend component | `EquipmentLensContent.tsx` | Present |
| Action hook | `useEquipmentActions.ts` | 6 actions, 6 modals |
| Route file | `routes/equipment_routes.py` | List + Detail |

**Response keys (tested):** id, name, description, equipment_type, manufacturer, model, serial_number, location, status, criticality, installation_date, last_maintenance, next_maintenance, attention_flag, attention_reason, created_at, updated_at

---

### 4. Part / Inventory — WORKING

| Item | File | Status |
|------|------|--------|
| Search result | search_index: part (886) + inventory (401) | Working |
| Detail endpoint | `/v1/entity/part/{id}` | **200** |
| Frontend component | `PartsLensContent.tsx` | Present (handles both part and inventory entityType) |
| Action hook | `usePartActions.ts` | 2 actions (consumePart, adjustStock) |
| Route file | `routes/inventory_routes.py` | List only |

**Response keys (tested):** id, part_name, part_number, stock_quantity, min_stock_level, location, unit_cost, supplier, category, unit, manufacturer, description, last_counted_at, last_counted_by, created_at, updated_at

**Note:** RouteShell maps `inventory` → `part` endpoint. Both `part` and `inventory` search result types route to the same PartsLensContent.

---

### 5. Receiving — WORKING

| Item | File | Status |
|------|------|--------|
| Search result | search_index (880 rows) | Working |
| Detail endpoint | `/v1/entity/receiving/{id}` | **200** |
| Frontend component | `ReceivingLensContent.tsx` | Present |
| Action hook | `useReceivingActions.ts` | 3 actions |
| Handler | `handlers/receiving_handlers.py` | 9 adapter functions |

**Response keys (tested):** id, vendor_name, vendor_reference, received_date, status, total, currency, notes, received_by, created_at, updated_at

**UNCLEAR:** ReceivingLensContent expects `items[]` (line items) and `po_number`. The `/v1/entity/receiving/{id}` response does not include these. The items may need a separate fetch or the endpoint may need enrichment.

---

### 6. Certificate — BROKEN (404)

| Item | File | Status |
|------|------|--------|
| Search result | search_index (287 rows) | Working |
| Detail endpoint | `/v1/entity/certificate/{id}` | **404 — NOT IMPLEMENTED** |
| Frontend component | `CertificateLensContent.tsx` | Present |
| Action hook | `useCertificateActions.ts` | 2 actions |
| Handler | `handlers/certificate_handlers.py` | Present — list, detail, history, expiring |
| Existing routes | `/api/v1/certificates/*` | Present (registered in pipeline_service.py line 287) |

**What exists but isn't wired:** `CertificateHandlers.get_certificate_details()` exists in the handler. It queries `vessel_certificates` or `crew_certificates` by ID. It is registered under the `/api/v1/certificates/` prefix, NOT under `/v1/entity/certificate/`.

**Fix needed:** Add `@app.get("/v1/entity/certificate/{certificate_id}")` to pipeline_service.py that calls the existing handler or queries the certificate tables directly. Pattern: copy the fault/equipment endpoint pattern.

**DB tables:** `vessel_certificates`, `crew_certificates`

---

### 7. Document — BROKEN (404)

| Item | File | Status |
|------|------|--------|
| Search result | search_index (2998 rows) | Working |
| Detail endpoint | `/v1/entity/document/{id}` | **404 — NOT IMPLEMENTED** |
| Frontend component | `DocumentLensContent.tsx` | Present |
| Action hook | `useDocumentActions.ts` | 4 actions |
| Existing endpoints | `/v1/documents/{id}/sign`, `/v1/documents/{id}/stream` | Present (lines 1772, 1945) |

**What exists but isn't wired:** Document signing and streaming endpoints exist. The `documents` table is queried by these endpoints (they fetch by `id` + `yacht_id`). But there's no `/v1/entity/document/{id}` endpoint that returns the full document metadata for the lens.

**Fix needed:** Add `@app.get("/v1/entity/document/{document_id}")` that queries the `documents` table and returns: id, filename, title, description, mime_type, file_size, url, thumbnail_url, created_at, created_by, classification, equipment_id, equipment_name, storage_path.

**DB table:** `documents`

---

### 8. Hours of Rest — BROKEN (404)

| Item | File | Status |
|------|------|--------|
| Search result | search_index (214 rows) | Working |
| Detail endpoint | `/v1/entity/hours_of_rest/{id}` | **404 — NOT IMPLEMENTED** |
| Frontend component | `HoursOfRestLensContent.tsx` | Present |
| Action hook | `useHoursOfRestActions.ts` | 2 actions |
| Handler | `handlers/hours_of_rest_handlers.py` | Present — get, verify, templates, warnings, signoffs |
| Existing routes | `routes/hours_of_rest_routes.py` | Present (registered line 423) |

**Fix needed:** Add `@app.get("/v1/entity/hours_of_rest/{record_id}")` that queries `pms_hours_of_rest` and returns: id, crew_name, date, total_rest_hours, total_work_hours, is_compliant, status, verified_by, verified_at, rest_periods[].

**DB table:** `pms_hours_of_rest`

---

### 9. Handover — MISSING DATA

| Item | File | Status |
|------|------|--------|
| Search result | search_index has `handover_item` (44 rows), NOT `handover` | **Type mismatch** |
| Detail endpoint | `/v1/entity/handover/{id}` | **NOT IMPLEMENTED** |
| Frontend component | `HandoverLensContent.tsx` | Present |
| Action hook | `useHandoverActions.ts` | 1 action (acknowledge) |
| Handler | `handlers/handover_handlers.py` | Present — add, edit, export, acknowledge |

**UNCLEAR:** search_index stores `handover_item` but RouteShell expects `handover`. When a user clicks a handover_item search result, it will try to navigate to `/handover/{id}` which calls `/v1/entity/handover/{id}` — this endpoint doesn't exist. Need to determine: should the endpoint return the parent handover record, or the individual handover_item?

**DB tables:** `pms_handover`, `pms_handover_items`

---

### 10. Handover Export — SEPARATE FLOW

| Item | File | Status |
|------|------|--------|
| Search result | Not in search_index | N/A |
| Detail endpoint | `/v1/entity/handover_export/{id}` | **NOT IMPLEMENTED** |
| Frontend component | `HandoverExportLensContent.tsx` | Present |

**Note:** HandoverExportLensContent fetches directly from Supabase (`Cloud_HQ.handover_exports`) — it does NOT go through the `/v1/entity/` pattern. It has its own data flow with sections, signatures, and edit/review modes. This component may not need a `/v1/entity/` endpoint.

---

### 11. Warranty — NO BACKEND

| Item | File | Status |
|------|------|--------|
| Search result | **Not in search_index** | No data |
| Detail endpoint | `/v1/entity/warranty/{id}` | **NOT IMPLEMENTED** |
| Frontend component | `WarrantyLensContent.tsx` | Present |
| Action hook | `useWarrantyActions.ts` | 4 actions |
| Handler | **None** | Not implemented |
| DB table | **UNCLEAR** | No `pms_warranties` table confirmed |

**UNCLEAR:** Is there a warranty table in the DB? The frontend component exists and defines a full data shape and 4 actions (fileClaim, approveClaim, rejectClaim, composeEmail), but no backend handler or route exists. The search_index has no warranty rows. This may be a future feature that has frontend scaffolding but no backend.

---

### 12. Shopping List — TYPE MISMATCH

| Item | File | Status |
|------|------|--------|
| Search result | search_index has `shopping_item` (773 rows), NOT `shopping_list` | **Type mismatch** |
| Detail endpoint | `/v1/entity/shopping_list/{id}` | **NOT IMPLEMENTED** |
| Frontend component | `ShoppingListLensContent.tsx` | Present |
| Action hook | `useShoppingListActions.ts` | 4 actions |
| Handler | `handlers/shopping_list_handlers.py` | Present — create, approve, reject, promote, order |

**UNCLEAR:** Same issue as handover. search_index stores `shopping_item` (individual items) but the lens expects `shopping_list` (a list with items[]). The shopping list model in the frontend expects a parent list with child items. Need to determine: does a `pms_shopping_lists` parent table exist, or are shopping items standalone?

**DB table:** `pms_shopping_list` (confirmed in handler)

---

### 13. Worklist — NO BACKEND

| Item | File | Status |
|------|------|--------|
| Search result | **Not in search_index** | No data |
| Detail endpoint | `/v1/entity/worklist/{id}` | **NOT IMPLEMENTED** |
| Frontend component | `WorklistLensContent.tsx` | Present (created 2026-03-02, GAP-007 fix) |
| Action hook | `useWorklistActions.ts` | 2 actions (addTask, exportWorklist) |
| Handler | **None** | Not implemented |
| DB table | **UNCLEAR** | No `pms_worklists` table confirmed |

**UNCLEAR:** Same as warranty — frontend scaffolding exists but no backend. May be a future feature.

---

### 14. Email — SEPARATE FLOW

| Item | File | Status |
|------|------|--------|
| Search result | search_index (229 rows) | Working |
| Detail endpoint | N/A | EmailLensContent uses `useThread(id)` hook, not `/v1/entity/` |
| Frontend component | `EmailLensContent.tsx` | Present |
| Action hook | `useEmailPermissions` | Read-only in this lens |

**Note:** Email lens fetches its own data via `useThread()` hook, which presumably queries Supabase directly for `email_threads`. It does NOT go through the RouteShell → `/v1/entity/` pattern. This should work independently.

---

## Summary: What's Wired vs. What Needs Work

### Fully Working (5/14)

| Lens | Search → Click → Detail → Render |
|------|----------------------------------|
| work_order | End-to-end working |
| fault | End-to-end working |
| equipment | End-to-end working |
| part / inventory | End-to-end working |
| receiving | End-to-end working (items may be missing from response) |

### Needs `/v1/entity/` Endpoint (3/14)

| Lens | What's Missing | Estimated Effort |
|------|---------------|-----------------|
| certificate | Add `/v1/entity/certificate/{id}` — handler exists, just needs wiring | Small — pattern exists, copy from fault |
| document | Add `/v1/entity/document/{id}` — table queries exist in sign/stream endpoints | Small |
| hours_of_rest | Add `/v1/entity/hours_of_rest/{id}` — handler exists | Small |

### Needs Endpoint + Data Resolution (2/14)

| Lens | What's Missing |
|------|---------------|
| handover | Endpoint + resolve `handover_item` → `handover` type mismatch |
| shopping_list | Endpoint + resolve `shopping_item` → `shopping_list` type mismatch |

### Separate Data Flow (2/14)

| Lens | How It Works |
|------|-------------|
| email | Uses `useThread()` hook → Supabase direct |
| handover_export | Fetches from `Cloud_HQ.handover_exports` → Supabase direct |

### No Backend (2/14)

| Lens | Status |
|------|--------|
| warranty | Frontend scaffolding only. No handler, no DB data, no search_index rows |
| worklist | Frontend scaffolding only. No handler, no DB data, no search_index rows |

---

## Action Hooks Reference

All action hooks live in `apps/web/src/hooks/`:

| Hook File | Lens | Actions | Signed Actions |
|-----------|------|---------|----------------|
| `useWorkOrderActions.ts` | work_order | 9 | reassign, archive |
| `useFaultActions.ts` | fault | 5 | — |
| `useEquipmentActions.ts` | equipment | 6 | decommission |
| `usePartActions.ts` | part/inventory | 2 | — |
| `useReceivingActions.ts` | receiving | 3 | — |
| `useCertificateActions.ts` | certificate | 2 | — |
| `useHandoverActions.ts` | handover | 1 | — |
| `useHoursOfRestActions.ts` | hours_of_rest | 2 | — |
| `useWarrantyActions.ts` | warranty | 4 | — |
| `useShoppingListActions.ts` | shopping_list | 4 | — |
| `useDocumentActions.ts` | document | 4 | delete |
| `useWorklistActions.ts` | worklist | 2 | — |

All action hooks call the API via `p0_actions_routes.py` using the prefill/prepare/execute lifecycle.

---

## Database Tables (Source of Truth)

These are the source tables that `/v1/entity/` endpoints query:

| Lens | Source Table(s) |
|------|----------------|
| work_order | `pms_work_orders`, `pms_work_order_notes`, `pms_work_order_parts`, `pms_audit_log` |
| fault | `pms_faults`, `graph_edges`, `maintenance_templates` |
| equipment | `pms_equipment` |
| part/inventory | `pms_parts` |
| receiving | `pms_receiving`, `pms_receiving_items` |
| certificate | `vessel_certificates`, `crew_certificates` |
| document | `documents` |
| hours_of_rest | `pms_hours_of_rest`, `pms_hor_templates`, `pms_hor_warnings` |
| handover | `pms_handover`, `pms_handover_items` |
| handover_export | `Cloud_HQ.handover_exports` (different schema) |
| shopping_list | `pms_shopping_list` |
| email | `email_threads`, `email_messages` |

---

## Lens Matrix Configuration

`apps/web/src/lib/lens_matrix.json` defines:

- **12 lenses** (work_order, fault, equipment, part, inventory, certificate, handover, hours_of_rest, warranty, shopping_list, email, receiving, document)
- **87 mutate_actions** with required_fields, optional_fields, role_restricted, requires_signature
- **73 read_filters** with type definitions (enum, date, boolean, numeric)

**Note:** A second copy exists at `apps/web/src/config/lens_matrix.json`. UNCLEAR which one is canonical. Verify imports before editing.

---

## Recommended Execution Order

1. **Wire the 3 missing `/v1/entity/` endpoints** (certificate, document, hours_of_rest) — these have existing handlers/queries and just need the FastAPI route added to `pipeline_service.py`. Follow the pattern at lines 904-1310.

2. **Resolve type mismatches** (handover_item→handover, shopping_item→shopping_list) — decide whether to:
   - (a) Map the search_index type to the lens type in the frontend, OR
   - (b) Add parent entity endpoints that aggregate child items

3. **Enrich receiving endpoint** — Add `items[]` and `po_number` to the `/v1/entity/receiving/{id}` response if ReceivingLensContent needs them.

4. **Test each lens end-to-end** — Search → click → detail view → action buttons. Use the JWT at `/tmp/jwt_token.txt`.

5. **Warranty and worklist** — Decide if these are in scope. Frontend exists but no backend or data.

---

## Docker / Local Development

```bash
cd BACK_BUTTON_CLOUD_PMS/deploy/local
./celeste.sh start        # API + projection + embedding workers
./celeste.sh health       # Health check
./celeste.sh logs api     # Follow API logs
./celeste.sh shell api    # Shell into container
```

API is at `http://localhost:8000`. Frontend (if started) at `http://localhost:3000`.

JWT for testing: `cat /tmp/jwt_token.txt` (auto-minted, expires in 2 hours).

---

## Files Changed in Recent Commits (for context)

The `feat/fragmented-routes-all-lenses` branch contains 10 organized commits (Phase 0):

| Commit | Content |
|--------|---------|
| 0A | Type foundations (`user_context_types.py`, `date_parser.py`, new route files) |
| 0B | Backend core — unified route architecture, signal_router, handlers |
| 0C | Frontend — RouteShell, 13 LensContent components, filters, permissions |
| 0D | Search + action hooks (useCelesteSearch, useActionHandler, usePartActions) |
| 0E | DB migrations 50-52 (search hardening) |
| 0F | RLS security migrations |
| 0G | Test infrastructure (E2E specs, fixtures, ground truth) |
| 0H | Infrastructure cleanup (Docker move, doc deletions, deploy/) |
| 0I | Planning metadata |
| 0J | Supplementary docs |

---

## Search Pipeline Status

Validated 2026-03-11:

| Metric | Value |
|--------|-------|
| L1 (natural language) @3 | 93.3% |
| Overall @3 | 90.7% |
| Overall @5 | 94.7% |
| Bias gap (L1 vs L5) | 0% |
| Avg latency | 1.4s |
| search_index rows | 12,251 |
| Migrations applied | 50 (synonyms), 51 (trgm threshold), 52 (strip action verbs) |

Search is stable. Stage 2 work should not modify search pipeline files.
