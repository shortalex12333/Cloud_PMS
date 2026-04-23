# Receiving — Repo Structure & Code Audit

Date: 2026-04-23  
Scope: every receiving-domain file (FE + BE) inventoried, dependency-traced, classified.

## Inventory

### Frontend (live)

| File | Role | Callers / route | Status |
|---|---|---|---|
| `apps/web/src/app/receiving/page.tsx` | List + overlay route | Sidebar nav | LIVE — fixed in this session |
| `apps/web/src/app/receiving/[id]/page.tsx` | Direct detail deep link | URL `/receiving/{id}` | LIVE — already used `EntityLensPage` |
| `apps/web/src/app/receiving/new/page.tsx` | "Log new receiving" page (upload + AI extract) | URL `/receiving/new`, sidebar action | LIVE |
| `apps/web/src/app/receiving/layout.tsx` | DomainProvider wrapper | Next route layout | LIVE |
| `apps/web/src/components/lens-v2/entity/ReceivingContent.tsx` | Lens detail content | `EntityLensPage(entityType='receiving')` | LIVE — patched contract bug A |
| `apps/web/src/components/receiving/ReceivingDocumentUpload.tsx` | OCR upload widget | `app/receiving/new/page.tsx:74` | LIVE |
| `apps/web/src/features/receiving/adapter.ts` | List → row mapping | `app/receiving/page.tsx:11` | LIVE — fixed in this session |
| `apps/web/src/features/receiving/types.ts` | TS types | `adapter.ts`, `types/entity.ts` | LIVE |
| `apps/web/src/lib/receiving/saveExtractedData.ts` | OCR persistence helpers | `ReceivingDocumentUpload.tsx:13` | LIVE |

### Frontend (quarantined this session)

| File | Reason | Replacement |
|---|---|---|
| `apps/web/src/features/receiving/_deprecated/api.ts` | Was the data layer for `ReceivingDetail` (broken — pointed at MASTER Supabase). Zero external callers after the lens fix. | `useEntityLens` hook in lens system |
| `apps/web/src/features/receiving/_deprecated/ReceivingPhotos.tsx` | Only caller was `ReceivingDetail`. | `AttachmentsSection` rendered by `ReceivingContent.tsx` |
| `apps/web/src/features/receiving/_deprecated/README.md` | Deletion criteria + history | — |

### Backend (live)

| File | Role | Notes |
|---|---|---|
| `apps/api/handlers/receiving_handlers.py` | **Plural** — stateful `ReceivingHandlers` class + 11 v1 adapter functions. ~1700 lines. | Imported by `internal_dispatcher.py:36`. The big legacy file — not a duplicate. |
| `apps/api/routes/handlers/receiving_handler.py` | **Singular** — Phase 4 thin dispatch (2 actions). 95 lines. | Imported by `routes/handlers/__init__.py:18`. The note in `__init__.py:6-8` documents the split. |
| `apps/api/routes/receiving_upload.py` | Upload proxy mounted at `/api/receiving/*` | Registered in `pipeline_service.py:411` |
| `apps/api/routes/entity_routes.py:1301-1418` | `GET /v1/entity/receiving/{id}` | Patched in this session for contract gaps |
| `apps/api/routes/vessel_surface_routes.py` | List endpoint `_format_record` for receiving | Patched in this session |
| `apps/api/action_router/registry.py:1302-1497, 3820-3877` | 12 receiving actions | See ACTIONS_MATRIX |
| `apps/api/action_router/dispatchers/internal_dispatcher.py` | Routes action_id → handler | Receiving wired at L116-134, L4191 |
| `apps/api/action_router/entity_actions.py` | `get_available_actions("receiving", entity, role)` | Filters actions by role + entity state |
| `apps/api/tests/handlers/test_receiving_handler.py` | Unit tests for the singular handler | LIVE |

## Naming risks examined

### `receiving_handler.py` (singular) vs `receiving_handlers.py` (plural)

**Decision: keep both, do NOT rename.**

Rationale:
- `routes/handlers/__init__.py:6-8` explicitly documents the split: the singular file is a thin dispatch table for Phase 4 (one function per action), the plural is the legacy stateful business logic class.
- `internal_dispatcher.py:36-50` imports specific function names from `handlers.receiving_handlers`. Any rename breaks this import + tests + the module loader for the entire receiving action cluster.
- The two files don't conflict — they live in different packages (`handlers/` vs `routes/handlers/`).

**Risk of a rename:** HIGH (would silently break action dispatch in production). The naming is unfortunate but documented and the import surface is large.

**Mitigation:** Leave a docstring at the top of each file pointing to the other. (Pending — included in next pass.)

### `pms_receiving_*` table proliferation

| Table | Rows used? | Verdict |
|---|---|---|
| `pms_receiving` | Yes (primary) | KEEP |
| `pms_receiving_items` | Yes (line items) | KEEP |
| `pms_receiving_documents` | Yes (PDF/invoice link) | KEEP |
| `pms_receiving_attachments` | Yes (photos) | KEEP |
| `pms_receiving_extractions` | Yes (OCR results, FK on `receiving_id`) | KEEP — used by extract_receiving_candidates |
| `pms_receiving_draft_lines` | ?? | **AMBIGUOUS** — no live grep hits in `apps/api`. Possible incomplete feature. Marked ambiguous, not deleted. |
| `pms_receiving_events` | ?? | **AMBIGUOUS** — distinct from `pms_receiving`. No live API references. Possible legacy. |
| `pms_receiving_line_items` | ?? | **AMBIGUOUS** — possible duplicate of `pms_receiving_items`. |
| `pms_receiving_sessions` | ?? | **AMBIGUOUS** — possible workflow state table for OCR session. |

**Action:** flag the four ambiguous tables to the user. Do NOT drop without verification — could be live in Phase 5 work or staging migrations.

## Lens display gaps (not bugs, but work to do)

`ReceivingContent.tsx` does not currently render:
- `total` / `currency` — backend returns them but the lens has no money line.
- `linked_work_order_id` — backend doesn't even resolve it; would require join + `_nav("work_order", ...)`.

These are P2 — flag for the next sprint but not in scope of the bugfix.

## Hidden-failure scan (look for silent catches)

Searched receiving-related code for `except Exception: pass` and `try: … except: …` patterns.

| Location | Behaviour | Risk |
|---|---|---|
| `entity_routes.py` PO-id lookup (1379-1380, pre-fix) | Silently swallows | LOW — falls back to no PO link |
| `entity_routes.py` received_by/yacht_name/audit lookups (this session) | Logs warning, continues | OK — visible in logs |
| `receiving_handlers.py` ledger writes (multiple) | Logs warning if not 204 | OK — non-critical audit |

No "silent and dangerous" failures found. The audit logs do warn on failures.

## Repeated-logic scan

| Pattern | Occurrences | Action |
|---|---|---|
| Nav helper `_nav("part", id, label)` | reused across 8+ entity endpoints | Already DRY — keep |
| `_get_attachments(supabase, type, id, yacht)` | reused across all entity endpoints | Already DRY — keep |
| `formatAge(dateStr)` (frontend) | duplicated in each domain adapter (`receiving/adapter.ts`, `purchasing/page.tsx`, etc.) | Minor DRY opportunity — could move to `lib/format/age.ts`. Deferred (low ROI, high blast radius). |

## Build/contract verification

- `npx tsc --noEmit` → 0 errors after all changes.
- Python `ast.parse(entity_routes.py)` → OK.
- All 12 receiving action handlers resolve at import time (`internal_dispatcher.py` lazy-imports `_get_receiving_handlers`).

## Open ambiguities (no deletion / change made — flagged for review)

1. **`pms_receiving_draft_lines`, `pms_receiving_events`, `pms_receiving_line_items`, `pms_receiving_sessions`** — see table above. Need user/historian sign-off before any drop.
2. **`receiving_upload.py`** — proxy routes for the upload widget. Looks live but is sparsely tested. No fix needed; flagging.
3. **`flag_discrepancy` (action 12)** — separate from `reject_receiving` (action 9). Both flag issues; semantics overlap. The lens uses `reject_receiving` for "Flag Receiving Issue" (`registry.py:1474`). `flag_discrepancy` may be vestigial — flagged for review, not removed.

## Verdict

The receiving domain code is now coherent enough for MVP. The big remaining functional gap is **inventory stock not updating on accept** (see `RECEIVING_INVENTORY_GAP.md`). Naming convention in the backend is awkward (singular vs plural handler files) but documented and load-bearing — leave alone.
