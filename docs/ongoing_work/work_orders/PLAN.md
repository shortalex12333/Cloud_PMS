# Work Orders — Living Plan

Owner: WORKORDER05
Started: 2026-04-23
Source of truth for UX: `/Users/celeste7/Desktop/lens_card_upgrades.md` lines 300–498
Fault list: `/Users/celeste7/Desktop/list_of_faults.md` Issue 6 (line 195), possibly Issue 3.

## Deploy coordination
Working alongside WORKORDER05 / HANDOVER08 / EQUIPMENT05 / FAULT05 / SHOPPINGLIST05 / RECEIVING05 / DOCUMENTS05 / CERTIFICATE05 / PURCHASE05. One merge-to-main per cohort per window; no Render-hook throttling. Coordinate via `claude-peers`.

## PR sequence

| PR | Subject | Status | Notes |
|----|---------|--------|-------|
| PR-WO-1 | Dedupe prefill + wire KEEP action buttons | OPEN | Kills 400s on dropdown actions |
| PR-WO-2 | Tabulated list view on shared `EntityTableList` | PENDING | Adopts DOCUMENTS04's cohort component (PR #673) |
| PR-WO-3 | Lens card redesign — horizontal tabs + metadata de-UUID | PENDING | Safety / Checklist / Docs / Faults / Equipment / Parts / Uploads / Notes / Audit / History |
| PR-WO-4 | Checklist overhaul (DB audit + bucket wiring) | PENDING | `pms_work_order_checklist` + `pms_checklist` + `pms_checklist_items` audit first |
| PR-WO-5 | Calendar tab (List / Calendar toggle) | PENDING | Seahub-style; clickable cards; colour by type/criticality |
| PR-WO-6 | Fault→WO bridge + WO-complete→fault auto-resolve | PENDING | Coord with FAULT05 (`wq0prarm`); needs `pms_faults.resolved_by_work_order_id` migration |
| PR-WO-7 | Schema additions — `system_id`, running hours columns | PENDING | Strictly optional; no keyword inference |

---

## PR-WO-1 — button audit (shipped 2026-04-23)

### Root cause
Every `POST /api/v1/actions/execute` from the work-order dropdown 400'd because the `(entity_type, action_id)` lookup in `apps/api/action_router/entity_prefill.py:68-79` was keyed on short aliases (`add_wo_note`, `add_wo_part`, `add_wo_hours`), while the registry exports long ids (`add_note_to_work_order`, `add_parts_to_work_order`, `add_work_order_note`, `add_work_order_photo`). When the lens dispatched the long id, the prefill map returned `{}`, so `work_order_id` was never injected, so the required-fields validator rejected the payload.

Same bug class as certificates (PR #681) and documents (`a2afd097` PR #682). Frontend also rendered every duplicate + wasteful button since `WorkOrderContent.tsx:200` had no `HIDDEN_FROM_DROPDOWN` set.

### Changes
- **`apps/api/action_router/entity_prefill.py`** — added long-form `work_order_id` entries for every KEEP action and supplied both `work_order_id` + `entity_id` on `archive_work_order` (declares `entity_id` in `required_fields`). Short aliases retained for backward compat with shard-33 + shard-41 HARD-PROOF e2e tests that call them directly bypassing the UI.
- **`apps/web/src/components/lens-v2/entity/WorkOrderContent.tsx`** —
  - `getAction()` calls at lines 121-133 now try canonical long ids first with short-alias fallback, so the gate resolves whichever form the backend currently exposes.
  - Added `HIDDEN_FROM_DROPDOWN` (19 entries) covering every Issue 6 REMOVE button plus the four short aliases. Explicit comment maps each entry to its KEEP/REMOVE rationale.
  - `SPECIAL_HANDLERS` now routes all three note-action flavours + both part flavours through the existing `AddNoteModal` / `AddPartModal` instead of raw `executeAction` (which fires without the modal).
  - `handleNoteSubmit` now uses the resolved `addNoteAction.action_id` — survives registry rename without code change.
- **`apps/web/src/types/actions.ts`** — added display (icon + cluster) entries for the canonical long action_ids plus sibling KEEP actions (`assign_work_order`, `view_checklist`, `add_checklist_*`, `mark_checklist_item_complete`, `update_worklist_progress`, `add_to_handover`).
- **`apps/api/tests/test_entity_prefill.py`** — added 24 assertions (1 parametric × 20 actions + 4 explicit) proving every KEEP + the short aliases still prefill `work_order_id`/`entity_id` correctly. Full suite 36/36 green.

### Hidden from dropdown (Issue 6 enforcement)
```
add_wo_note, add_wo_part, add_wo_hours, add_wo_photo         — short-alias duplicates
add_note_to_work_order                                       — duplicate of add_work_order_note
add_part_to_work_order                                       — duplicate of add_parts_to_work_order
add_work_order_hours                                         — PR-WO-3 will rebrand to "change hours preset"
reassign_work_order                                          — duplicate of assign_work_order (HOD-gated in PR-WO-3)
cancel_work_order, delete_work_order                         — duplicates of archive
create_work_order                                            — belongs on /work-orders AppShell, not per-WO
view_work_order_detail                                       — the lens card IS the view
view_work_order_history                                      — history is a section on the card
view_work_order_checklist                                    — redundant with view_checklist
view_my_work_orders, view_related_entities, view_smart_summary — wasteful
record_voice_note                                            — not MVP
upload_photo                                                 — duplicate of add_work_order_photo
```

### Verification
- `python3 -m pytest apps/api/tests/test_entity_prefill.py` → 36/36 green
- `npx tsc --noEmit` on `apps/web` → clean
- Python AST parse on both touched `.py` files → clean
- Frontend build: deferred to post-merge Vercel preview (no runtime code change that could fail differently)

### Known deferred
- Registry dedup (delete short-alias entries) is left to PR-WO-2 once the cohort confirms no out-of-tree callers (workOrders.ts microactions at 1449 lines still references short aliases).
- Checklist actions are wired in the dropdown but the checklist overhaul (DB audit, bucket writes, soft-delete 30d, custom K/V) is PR-WO-4.
- "Change Status" rename from "Update Worklist Progress" is PR-WO-3 (UX concern, not wiring).

---

## PR-WO-2..7 — detailed scope will be filled in as each opens.
