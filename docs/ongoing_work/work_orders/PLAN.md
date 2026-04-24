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
| PR-WO-1 | Dedupe prefill + wire KEEP action buttons | MERGED #686 | 400s on work-order dropdown dead |
| PR-WO-2 | Tabulated list view on shared `EntityTableList` | MERGED #687 | 12 cols live; backend batch resolvers in place |
| PR-WO-3 | Lens card redesign — horizontal tabs + metadata de-UUID | OPEN | 10-tab LensTabBar; extended header metadata; "Change Status" rename |
| PR-WO-4 | Checklist overhaul — Safety tab activation + add-item + SOP | OPEN | 2 new backend actions + Safety tab live; table-migration deferred |
| PR-WO-5 | Calendar tab (List / Calendar toggle) | PENDING | Seahub-style; clickable cards; colour by type/criticality |
| PR-WO-6 | Fault→WO bridge + WO-complete→fault auto-resolve | MERGED #689 → CORRECTED in PR-WO-6b | DB trigger owns status cascade; handler now writes reverse-link + ledger only |
| PR-WO-7 | Schema additions — `system_id`, running hours columns | OPEN | Strictly optional; no keyword inference; migration + TS + registry |

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

## PR-WO-2 — list-view tabulation (shipped 2026-04-23)

### Goal
UX sheet `/Users/celeste7/Desktop/lens_card_upgrades.md:492 + 506-522` — move `/work-orders` from `SpotlightResultRow` cards to columnar tabulated view using the cohort-shared `EntityTableList` (introduced by DOCUMENTS04 in PR #673, receiving opt-in via `tableColumns?` prop in PR #674).

### Column order (fixed by UX sheet)
`W/O Code · Title · Priority · Equipment · Assigned · Severity · Type · Status · Created · Frequency · Due · Completed`

### Changes
- **`apps/api/routes/vessel_surface_routes.py`** —
  - `DOMAIN_SELECT.work_orders` extended: added `type, work_order_type, frequency, completed_at`.
  - `_format_record(domain="work_orders")` now emits `severity, wo_type, frequency, due_date, completed_at` (previously only the bare card-row fields).
  - Added a work-orders batch-enrichment block mirroring the PO/shopping-list pattern: `resolve_equipment_batch` + `resolve_users` run as two IN queries per list fetch, returning `linked_equipment_name`, `linked_equipment_code`, `assigned_to_name`, `assigned_to_role`. No client-side N+1.
- **`apps/web/src/features/entity-list/hooks/useFilteredEntityList.ts`** — `apiRecordToAdapterInput` now forwards the enriched fields + stops the silent double-read of `assigned_to_name: record.assigned_to` (which displayed UUIDs whenever the backend didn't resolve the name). Field-contract matches what the backend emits after the enrichment block.
- **`apps/web/src/features/work-orders/types.ts`** — `WorkOrder` gained `type, work_order_type, severity, frequency, completed_at`.
- **`apps/web/src/features/work-orders/adapter.ts`** — adapter metadata now surfaces `severity, wo_type, frequency, assigned_to_name, wo_number, due_date, completed_at` for column accessors.
- **`apps/web/src/features/work-orders/columns.tsx` (new)** — `WORK_ORDER_COLUMNS` spec, tokenised pill palettes, deliberate-rank sorts (Emergency < Critical < Important < Routine; in_progress before completed; terminal states last). Mirrors `SHOPPING_LIST_COLUMNS` structure.
- **`apps/web/src/app/work-orders/page.tsx`** — SELECT list extended; `tableColumns={WORK_ORDER_COLUMNS}` passed to `FilteredEntityList`. One line of UX migration; everything else (filters, pagination, vessel attribution, Subbar sort/chip) keeps working.
- **`apps/web/src/features/work-orders/__tests__/columns.test.tsx` (new)** — 11 unit tests covering column order, accessor fallbacks, sort-rank correctness (including null-to-end + unknown-enum-to-null).

### Verification
- `vitest run src/features/work-orders/__tests__/columns.test.tsx` → 11/11 green
- `pytest apps/api/tests/test_entity_prefill.py` → 36/36 green (regression)
- `npx tsc --noEmit` on apps/web → clean
- Python AST parse on `vessel_surface_routes.py` → clean

### Deferred
- Column-visibility toggles / multi-column sort / virtualisation — cohort-frozen per DOCUMENTS04 (extensions require co-signed PR).
- The deliberate-rank maps (`PRIORITY_RANK`, `SEVERITY_RANK`, `STATUS_RANK`) live in `columns.tsx` for MVP. If two lenses end up needing the same rank map, extract to `features/work-orders/status-ranks.ts`.

---

## PR-WO-3 — card redesign (shipped 2026-04-23)

### Scope
UX sheet `/Users/celeste7/Desktop/lens_card_upgrades.md:300-405` — the legacy work-order card "reads like a receipt". CEO asks for a deeper, tabbed card with safety / sop / LOTO visibility, reverse-linked equipment + faults, and all the hidden header metadata (severity, type, due_date + due_at, frequency, completed_at).

### Changes
- **`apps/web/src/components/lens-v2/LensTabBar.tsx` (new)** — shared horizontal tab-bar component. Sticky, keyboard-navigable (←/→ skip disabled tabs), aria-compliant (`role=tablist`/`tab`/`tabpanel`, `aria-selected`, `aria-controls`, `aria-disabled`), tokenised only. Count badges suppress when count = 0. Controlled + uncontrolled modes. Cohort-shared — available for FAULT05, EQUIPMENT05, HANDOVER08 to adopt.
- **`apps/web/src/components/lens-v2/index.ts`** — export barrel updated.
- **`apps/web/src/components/lens-v2/entity/WorkOrderContent.tsx`** —
  - Extended header metadata: `wo_number` overline, title, status/priority/severity/type pills (UX lines 374-380). Details now include Equipment, Due (`due_date` + `due_at`), Created, Frequency, Completed, Hours. Severity is now distinct from priority.
  - Added `LABEL_OVERRIDES` so `update_worklist_progress` renders as "Change Status" in the dropdown (UX line 238) without breaking the backend action_id.
  - Added UUID-guard on `assigned_to` display — if the entity endpoint hasn't been enriched and the value is still a raw UUID, the Assigned link suppresses entirely rather than leaking the id. Role (`assigned_to_role`) appended when present, e.g. "Alex Kapranos (Chief Engineer)".
  - Replaced the legacy stacked `ScrollReveal` sections with a 10-tab `LensTabBar`: Checklist · Documents · Faults · Equipment · Parts · Uploads · Notes · Audit Trail · History · Safety.
  - Each tab either renders its existing section component or an `EmptyTab` with a clear next-step message. `FaultsTabBody` + `EquipmentTabBody` helpers render minimal linked-entity cards that navigate to the corresponding lens on click.
  - `Safety` tab is `disabled: true` with `disabledReason="LOTO + SOP attachments land with PR-WO-4 checklist overhaul"` — no dead tab, no silent failure.
- **`apps/web/src/components/lens-v2/__tests__/LensTabBar.test.tsx` (new)** — 7 specs: tab rendering + aria wiring, count-badge suppression, disabled aria + click-ignore, onChange + body switch, ←/→ keyboard wrap skipping disabled, controlled-mode passivity, first-enabled-default fallback.

### Verification
- `vitest run src/components/lens-v2/__tests__/LensTabBar.test.tsx` → 7/7 green
- `vitest run src/features/work-orders/__tests__/columns.test.tsx` → 11/11 green (regression)
- `npx tsc --noEmit` on apps/web → clean

### Deferred (PR-WO-4..7)
- Safety tab content (LOTO + SOP attachments) → PR-WO-4.
- Checklist custom K/V, photo+comment upload, bucket wiring, soft-delete 30d → PR-WO-4.
- Calendar tab (List / Calendar toggle) → PR-WO-5.
- Fault→WO bridge + WO-complete→fault auto-resolve → PR-WO-6 (needs `pms_faults.resolved_by_work_order_id` migration; FAULT05 confirmed column absent + enum is `open/investigating/acknowledged/work_ordered/resolved/closed`).
- `system_id` + running-hours columns → PR-WO-7.

---

## PR-WO-6 — fault bridge (shipped 2026-04-23)

### Scope
Data-continuity USP. When a work order created from a fault (`pms_work_orders.fault_id IS NOT NULL`) reaches `status='completed'`, the linked fault must auto-transition to `status='resolved'` with a `resolved_at` timestamp, a `resolved_by_work_order_id` FK, and a `fault_auto_resolved` ledger row that FAULT05's lens reacts to. Coordinated with FAULT05 (`wq0prarm`) who confirmed the fault-status enum (`open / investigating / acknowledged / work_ordered / resolved / closed`) and the column absence.

### Changes
- **`supabase/migrations/20260423_pms_faults_resolved_by_work_order.sql` (new, temporary)** — adds nullable `resolved_by_work_order_id uuid REFERENCES pms_work_orders(id) ON DELETE SET NULL` + partial index. Per `feedback_migration_convention.md`, apply manually and delete the file afterwards.
- **`apps/api/action_router/dispatchers/internal_dispatcher.py::close_work_order`** —
  - Pre-reads `pms_work_orders.fault_id` before the status update (single extra select — supabase-py doesn't expose `RETURNING`).
  - After WO status update succeeds, if `fault_id` is set and the linked fault's current status is NOT in `('resolved', 'closed')` (idempotent guard), writes `pms_faults.status='resolved'` + `resolved_at=now()` + `resolved_by=<user_id>` + `resolved_by_work_order_id=<wo_id>`.
  - **FK write is guarded**: if the column doesn't exist yet (migration not applied), the bridge catches the exception and retries the same update without the FK. Fault status + ledger still flow; the FK just stays null until the migration lands.
  - Emits a `fault_auto_resolved` ledger row via `routes.handlers.ledger_utils.build_ledger_event` with `event_type='status_change'`, `entity_type='fault'`, `metadata={resolved_by_work_order_id, previous_status, new_status}`. Ledger emission is try/except — never fails the WO close.
  - Return envelope extended: adds `fault_auto_resolved: bool` and `linked_fault_id: str | null` so the frontend can render a post-close toast without a refetch.
- **`apps/api/tests/test_close_work_order_bridge.py` (new)** — 5 pytest-asyncio cases covering:
  - no `fault_id` → zero fault writes, zero ledger inserts
  - open fault → single fault update with FK + ledger insert
  - already-resolved / closed fault → idempotent, no writes
  - FK column absent → first update raises, handler retries without FK, status still flips, ledger still fires
  - WO update returns empty → `ValueError`, bridge never runs

### Verification
- `pytest tests/test_close_work_order_bridge.py` → 5/5 green
- `python3 ast.parse` on `internal_dispatcher.py` → clean
- Migration SQL includes verification query for CEO to run post-apply

### Deploy steps (CEO owns DB apply)
1. Merge this PR to `main`; Render deploys the handler. Frontend no-op.
2. Apply the migration SQL (pooler auth currently failing from both WORKORDER05 and FAULT05 agents — CEO runs via Supabase dashboard SQL editor or proper psql env).
3. Verify column: `SELECT column_name FROM information_schema.columns WHERE table_name='pms_faults' AND column_name='resolved_by_work_order_id';`
4. Delete the migration file per `feedback_migration_convention.md`.
5. Close any WO with a linked fault and inspect `ledger_events` for `fault_auto_resolved`.

### Deferred
- `pms_faults` frontend: FAULT05 will refetch on ledger change in their own PR.

---

## PR-WO-7 — schema additions (shipped 2026-04-23)

### Scope
UX sheet `/Users/celeste7/Desktop/lens_card_upgrades.md:354-356`. Two additions:
1. **System linkage** — denormalised `system_id` (FK → `pms_equipment.id`) + `system_name` (text). Frontend doesn't have to walk the self-referential `pms_equipment.parent_id` tree to label "Propulsion · HVAC · Electrical · Navigation".
2. **Running hours** — `running_hours_required` (bool, default false), `running_hours_current` (numeric), `running_hours_checkpoint` (numeric). Rotating machinery (engines / gens / HVAC compressors / winches / nav motors) is scheduled against hours, not calendar. CEO spec line 356 explicitly forbids keyword inference ("if WO contains 'motor', 'crane', 'engine' then list hours") — every WO carries the columns and users opt in via the boolean.

### Changes
- **`supabase/migrations/20260423_pms_work_orders_system_running_hours.sql` (new, temporary)** — ADD COLUMN IF NOT EXISTS for all five columns, partial index on `system_id`, `CHECK (running_hours_* >= 0)` sanity constraints. Apply manually, verify, delete.
- **`apps/api/action_router/registry.py`** — `create_work_order` field_metadata extended with six new OPTIONAL entries (system_id + system_name + frequency + running_hours_{required,current,checkpoint}). `update_work_order` is a pass-through handler and doesn't need field_metadata additions; the new columns flow through on UPDATE.
- **`apps/web/src/features/work-orders/types.ts`** — `WorkOrder` interface extended with the five new optional fields.

### Verification
- `python3 ast.parse` on `registry.py` → clean
- `npx tsc --noEmit` on apps/web → clean
- `pytest apps/api/tests/test_entity_prefill.py + test_close_work_order_bridge.py` → 41/41 green (regression)

### Deploy steps (CEO)
1. Merge → Render deploys.
2. Apply `supabase/migrations/20260423_pms_work_orders_system_running_hours.sql` via Supabase dashboard.
3. Verify columns: `SELECT column_name, data_type, column_default FROM information_schema.columns WHERE table_name='pms_work_orders' AND column_name LIKE 'system_%' OR column_name LIKE 'running_hours_%';`
4. Delete the migration file.

### Deferred (UI polish)
- Running-hours edit form on the WO card — lands with PR-WO-4 (checklist overhaul) or a PR-WO-8 follow-up.
- System picker modal — equipment-lens concern; EQUIPMENT05 owns it.

---

## PR-WO-6b — correction after DB probe (shipped 2026-04-24)

### What I got wrong in PR-WO-6
Direct psql probe (once the correct connection string landed: `db.<slug>.supabase.co:5432` with user `postgres`, not the pooler format) revealed two facts my earlier code-only analysis missed:

1. **`pms_faults.work_order_id` already exists as a real FK** with index `idx_faults_work_order_id` and constraint `faults_work_order_id_fkey FOREIGN KEY (work_order_id) REFERENCES pms_work_orders(id) ON DELETE SET NULL`. Populated in 124/3404 rows (seed/imported data; no current application writers — grep of `apps/api/` finds zero `.update({"work_order_id": ...})` against `pms_faults`).
2. **A DB trigger `trg_wo_status_cascade_to_fault`** on `pms_work_orders` UPDATE already cascades status: `NEW.status='completed'` → `pms_faults.status='resolved'`, `resolved_at=NOW()`, `resolved_by=NEW.completed_by`. Idempotent guard on fault's current status. Full function body in `cascade_wo_status_to_fault()` is `SECURITY DEFINER` and ships today.

My PR-WO-6 (a) added a duplicate `resolved_by_work_order_id` column via migration and (b) duplicated the status/resolved_at/resolved_by writes from Python.

### Correction (this PR)
- **Deleted** `supabase/migrations/20260423_pms_faults_resolved_by_work_order.sql` — never applied, never needed. The pre-existing `pms_faults.work_order_id` column covers the reverse-link semantics.
- **Deleted** `supabase/migrations/20260423_pms_work_orders_system_running_hours.sql` — applied successfully to tenant DB via direct connection, verified all 5 columns present with correct types + defaults + CHECK constraints. File removed per `feedback_migration_convention.md`.
- **Rewrote `close_work_order` in `apps/api/action_router/dispatchers/internal_dispatcher.py`**:
  - Removed the status/resolved_at/resolved_by writes on `pms_faults`. The DB trigger owns those.
  - Kept the pre-read of the fault's previous status for ledger metadata.
  - Writes `pms_faults.work_order_id = wo_id` (reverse-link; trigger doesn't touch this column).
  - Still emits the `fault_auto_resolved` ledger row (trigger doesn't emit ledger).
  - Both post-cascade writes are best-effort try/except; WO close never fails because of them.
- **Rewrote `apps/api/tests/test_close_work_order_bridge.py`** to match new semantics: 6 cases covering no-fault / open-fault / terminal-fault / reverse-link-failure-resilience / ledger-failure-resilience / WO-not-found.

### Verification
- `pytest tests/test_close_work_order_bridge.py + tests/test_entity_prefill.py` → 42/42 green
- `python3 ast.parse internal_dispatcher.py` → clean
- `psql \d pms_work_orders` post-migration → 5 new columns present, CHECK constraints active

### Tenant DB state after this PR
- `pms_work_orders` has `system_id`, `system_name`, `running_hours_required` (default false), `running_hours_current`, `running_hours_checkpoint`. All in prod.
- `pms_faults` unchanged (no new column). Handler will start filling `pms_faults.work_order_id` for any new WO-driven resolution going forward.

---

## PR-WO-4 — checklist + Safety tab (shipped 2026-04-24)

### DB reality check (via direct psql)
Two parallel checklist systems exist:
- **`pms_work_orders.metadata.checklist[]`** — JSON array on each WO row. Live code path: read by `p3_read_only_handlers.view_checklist_execute`; written by `p2_mutation_light_handlers.mark_checklist_item_complete_execute`.
- **`pms_checklists` (parent, plural) + `pms_checklist_items`** — real tables with `checklist_type` enum (maintenance / safety / inspection / departure / arrival / watch / custom), is_template flag, richer value_type/unit/min/max fields. 29 items exist from seed; no active code reads or writes these tables.

MVP call: enhance the JSON path (where the live data and handlers are). Table migration is deferred — a separate follow-up PR can port the JSON blob to the relational tables once UX is settled. Documented at `docs/ongoing_work/work_orders/PLAN.md` so the next engineer knows.

### Changes
- **`apps/api/handlers/p2_mutation_light_handlers.py`** — two new handlers:
  - `add_checklist_item_execute` — user A appends `{id, title, description, instructions, category, sequence, is_required, requires_photo, requires_signature, is_completed, created_by, created_at}` to `metadata.checklist[]`. Auto-increments sequence. Rejects empty title. Preserves sibling metadata keys (no clobber).
  - `upsert_sop_execute` — writes `metadata.sop = {text, document_id, updated_at, updated_by}`. Partial update (either field may be None leaves the other intact). Rejects fully-empty input.
- **`apps/api/action_router/dispatchers/internal_dispatcher.py`** — two new wrappers `_p2_add_checklist_item` + `_p2_upsert_sop`; wired into `HANDLER_MAP` with keys `add_checklist_item` / `upsert_sop`.
- **`apps/api/action_router/registry.py`** — two new `ActionDefinition` entries with full `field_metadata` (including `category` enum `general/safety/loto/sop` so the frontend form UI surfaces the right controls).
- **`apps/api/action_router/entity_prefill.py`** — added the two `(work_order, ...)` prefill entries.
- **`apps/api/tests/test_checklist_item_sop_handlers.py` (new)** — 9 pytest-asyncio specs:
  - Append with all fields surfaces correctly / auto-sequences / empty-title rejected / sibling metadata preserved / WO-not-found
  - SOP: text only / document only / partial update / empty input rejected
- **`apps/web/src/components/lens-v2/entity/WorkOrderContent.tsx`** —
  - Reads `metadata.checklist[]` + `metadata.sop{}` off the entity payload.
  - Three new callbacks: `handleAddSafetyCheckpoint`, `handleAddGeneralCheckpoint`, `handleEditSOP` (MVP uses native `window.prompt()` — a tokenised modal lands in PR-WO-4b).
  - Checklist tab: existing section + `+ Add Checklist Item` button.
  - **Safety tab activated** (was `disabled: true`). New `SafetyTabBody` component renders:
    - SOP block — text display + `Edit/Add SOP` button + `Open SOP PDF` button (when a document_id is linked).
    - Safety checklist — filtered `category IN {safety, loto}` items with token-coloured completion state (`var(--green-bg)` when done, `var(--surface)` otherwise), click to toggle, `+ Add Safety Checkpoint` button.
  - Tab count badge surfaces `safetyItems.length + (sopText ? 1 : 0)`.

### Verification
- `pytest test_checklist_item_sop_handlers.py + test_close_work_order_bridge.py + test_entity_prefill.py` → 51/51 green
- `vitest run src/features/work-orders src/components/lens-v2` → 29/29 green (regression)
- `npx tsc --noEmit` on apps/web → clean
- `python3 ast.parse` on all 4 touched Python files → clean

### Deferred to PR-WO-4b
- Tokenised `AddChecklistItemModal` + `EditSOPModal` (replace native `window.prompt()` — same pattern as `AddNoteModal`).
- Require-photo flow: if a checklist item has `requires_photo=true`, mark-complete should first open the photo-upload modal wired to the `pms-work-order-photos` bucket.
- Require-signature flow: PIN+TOTP signature via existing ActionPopup SIGNED pattern.
- Close-work-order guard: refuse close if any required + non-deleted checklist item is incomplete.

### Deferred to PR-WO-4c
- Port the JSON checklist to `pms_checklists` + `pms_checklist_items` tables (queryable, templatable, shared across WOs). Requires data migration of existing `metadata.checklist[]` rows.

---

## PR-ATT-COMMENTS — threaded attachment comments (shipped 2026-04-24)

### Why
CEO pivot 2026-04-24: move from single-caption (`pms_attachments.description`) to threaded comments. Image/photo reviewers commonly need multi-message discussion on damage progression, repair validation, and hand-off sign-off — single `description` was MVP shorthand that doesn't reflect the real flow. Cohort-shared because the table is polymorphic — every lens that uploads to `pms_attachments` gets the same thread primitive.

### DB (applied directly via psql, file-less per `feedback_migration_convention.md`)
Table `public.pms_attachment_comments` mirrors `doc_metadata_comments` 1:1 with `attachment_id` in place of `document_id`:
```sql
CREATE TABLE pms_attachment_comments (
  id uuid PK,
  yacht_id uuid NOT NULL REFERENCES yacht_registry(id) ON DELETE CASCADE,
  attachment_id uuid NOT NULL REFERENCES pms_attachments(id) ON DELETE CASCADE,
  comment text NOT NULL CHECK (length(trim(comment)) > 0),
  created_by uuid NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_by uuid, updated_at timestamptz,
  deleted_by uuid, deleted_at timestamptz,
  author_department varchar(100) CHECK (... in list),
  parent_comment_id uuid REFERENCES pms_attachment_comments(id) ON DELETE CASCADE,
  metadata jsonb DEFAULT '{}'::jsonb
);
-- 5 indexes (active, attachment, yacht, parent, created_at).
-- 4 RLS policies (select/insert/update + service-role bypass) — same shape as doc comments.
-- Trigger trg_populate_att_comment_department_before_insert reuses
-- trg_populate_doc_comment_department() — same NEW.created_by/yacht_id → department map.
```
Backfill: every existing `pms_attachments.description` that is non-null and non-blank becomes row-1 of the thread, authored by `uploaded_by` at `uploaded_at`, tagged `metadata.source='backfill_20260424'`. 6 rows migrated in prod.

### Backend
- **`apps/api/handlers/attachment_comment_handlers.py` (new)** — `AttachmentCommentHandlers` with 4 methods (add/update/edit/delete + list_with_thread_tree). Direct mirror of `document_comment_handlers.py` with column renames. Explicit ownership + HOD-override for edit/delete (`admin`/`captain`/`chief_engineer`/`manager`). Soft-delete only — full audit trail.
- **`apps/api/action_router/dispatchers/internal_dispatcher.py`** — lazy-init getter, 4 wrappers (`_att_add`/`_att_update`/`_att_delete`/`_att_list_attachment_comments`), HANDLER_MAP entries.
- **`apps/api/action_router/registry.py`** — 4 `ActionDefinition` entries (domain=None because this is cross-lens / polymorphic), full `field_metadata`, HOD-broad `allowed_roles` (every role including `crew` can comment; the DB RLS is the last line of defense).
- **`apps/api/tests/test_attachment_comment_handlers.py` (new)** — 18 pytest-asyncio specs covering happy paths, validation errors (empty text, deleted attachment, missing parent), RBAC (owner vs non-owner + HOD override), thread-tree assembly (orphan handling), include_threads=false flat-list return.

### Verification
- `pytest test_attachment_comment_handlers.py + test_entity_prefill.py + test_close_work_order_bridge.py + test_checklist_item_sop_handlers.py` → 69/69 green
- `python3 ast.parse` on touched .py files → clean
- `psql` verify post-migration: 1 table, 6 indexes, 4 policies, 6 backfilled comments ✓

### Frontend status
**`LensImageViewer` UNCHANGED in this PR.** Current viewer reads `LensImage.description` as the single-caption overlay — which still renders correctly because the backfill preserved all descriptions. Threaded-comment UI adoption is a per-lens decision:
- **WORKORDER05 (PR-WO-4b)** — will extend the viewer to accept `comments: LensImageComment[]` as an optional prop and render the thread below the image when present.
- **EQUIPMENT05 (PR-EQ-4)** — same extension; pulls from `list_attachment_comments` via the action router.
- **FAULT05 / future lenses** — consume identically.
This per-lens migration path means: no breaking change to the `LensImageViewer` API today; threaded UI ships when each consumer is ready to wire it.

### Actions surfaced
| action_id | Purpose | Roles |
|---|---|---|
| `add_attachment_comment` | Append a comment (optionally a reply via `parent_comment_id`) | crew+ |
| `update_attachment_comment` | Edit text (owner or HOD) | crew+ |
| `delete_attachment_comment` | Soft-delete (owner or HOD) | crew+ |
| `list_attachment_comments` | Fetch flat or threaded tree | crew+ |

### Deferred
- Viewer-side threaded-UI (per-lens adoption PRs).
- Bulk-import shape for vessels arriving with legacy captions beyond a single field (out of scope — single `description` backfill covers everything we see today).
- Drop `pms_attachments.description` column once all lenses have migrated — wait 2-3 lens PRs before removing for safety.

---

## PR-WO-5 — remaining scope

Calendar tab (List / Calendar toggle). ~6-10h focused work. Begins after the cohort adopts threaded comments into the viewer.
