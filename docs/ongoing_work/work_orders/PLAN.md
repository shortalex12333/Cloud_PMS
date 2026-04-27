# Work Orders — Living Plan

Owner: WORKORDER05  
UX source: `/Users/celeste7/Desktop/lens_card_upgrades.md` lines 300–498  
Fault list: `/Users/celeste7/Desktop/list_of_faults.md` Issue 6 (line 195)

---

## PR Sequence

| PR | Subject | Status | Notes |
|----|---------|--------|-------|
| PR-WO-1 | Dedupe prefill + wire KEEP buttons | MERGED #686 | Dropdown 400s fixed |
| PR-WO-2 | Tabulated list view (`EntityTableList`) | MERGED #687 | 12 cols, batch resolvers |
| PR-WO-3 | Lens card redesign — horizontal tabs | MERGED | 10-tab `LensTabBar`, header metadata, UUID guard |
| PR-WO-4 | Checklist + Safety tab activation | MERGED | `add_checklist_item` + `upsert_sop` actions |
| PR-WO-4b | Replace `window.prompt()` + Archive modal + Upload | OPEN #741 | See below |
| PR-WO-5 | Calendar tab (List / Calendar toggle) | PENDING | Seahub-style |
| PR-WO-6 | Fault→WO bridge | MERGED #689 → corrected in PR-WO-6b | DB trigger owns cascade; handler writes reverse-link + ledger |
| PR-WO-7 | Schema: `system_id`, running-hours columns | MERGED | Migration applied to tenant DB |
| PR-ATT | Threaded attachment comments | MERGED | `pms_attachment_comments` table, 4 actions |
| fix/731 | Dropdown 400s round-2 + AddPartModal + AssignModal | OPEN #731 | Needs merge before #741 |

---

## PR #741 — fix/workorder-p0-bugs (OPEN, 2026-04-27)

Branch: `fix/workorder-p0-bugs`

### Bug 1 — entity endpoint hitting wrong database (P0)

**File:** `apps/api/routes/entity_routes.py:1543`  
**Root cause:** `get_work_order_entity` called `get_supabase_client()` instead of `get_tenant_client(tenant_key)`. Every downstream query (notes, parts, checklist, audit_history) ran against the wrong DB and returned empty. All other entity handlers in the same file use `get_tenant_client(tenant_key)`.  
**Fix:** Added `tenant_key = auth['tenant_key_alias']` + `supabase = get_tenant_client(tenant_key)`.  
**Effect:** Notes, parts, checklist items, and audit trail now appear after submit without a reload.

### Bug 2 — `window.prompt()` for checklist + SOP (P0)

**File:** `apps/web/src/components/lens-v2/entity/WorkOrderContent.tsx` (lines 454, 456, 467, 469, 481 before fix)  
**Root cause:** `handleAddSafetyCheckpoint`, `handleAddGeneralCheckpoint`, `handleEditSOP` used native Chrome prompt dialogs as MVP shortcuts.  
**Fix:** Three callbacks now open in-app modals:
- `AddChecklistItemModal` — title (required) + guidance textarea (optional), shared between safety and general; `category` prop controls label/placeholder text.
- `EditSOPModal` — monospace textarea pre-filled with existing SOP; empty string clears it.

### Bug 3 — Archive → 400 "invalid signature payload: missing required fields" (P0)

**File:** `apps/web/src/components/lens-v2/entity/WorkOrderContent.tsx`  
**Root cause:** `archive_work_order` is `ActionVariant.SIGNED` (`registry.py:412-429`), requiring `deletion_reason` + `signature`. There was no SPECIAL_HANDLER — clicking Archive fired `executeAction` with an empty payload, which the validator rejected.  
**Fix:** Added `archive_work_order` to `SPECIAL_HANDLERS`. New `ArchiveWorkOrderModal` collects `deletion_reason` (textarea) + `signature` (typed full name). Submit button stays disabled until both fields have content.

### Bug 4 — +Upload button in Uploads tab does nothing (P1)

**File:** `apps/web/src/components/lens-v2/entity/WorkOrderContent.tsx:583` (before fix)  
**Root cause:** `onAddFile` callback was an empty stub left from PR-WO-4 (`{/* wired in PR-WO-4 */}`).  
**Fix:** Opens `AttachmentUploadModal` in default mode (`entityType=work_order`, `bucket=pms-work-order-photos`, `category=photo`). Standard 15 MB / MIME validation applies.

---

## PR #731 — fix/workorder-dropdown-400s (OPEN)

Round-2 dropdown fix on top of PR-WO-1. Adds:
- `AddPartModal` — searchable parts list fetched from `/v1/{yachtId}/domain/parts/records`, quantity input.
- `AssignModal` — user ID text input (placeholder until a crew-picker is built).
- `runAction` toast wrapper — success/failure feedback on all generic dropdown actions.
- Expanded `HIDDEN_FROM_DROPDOWN` to cover inline-only actions (`add_checklist_item`, `upsert_sop`, `mark_checklist_item_complete`, `add_work_order_photo`, all attachment-comment variants, `update_work_order`, `update_worklist_progress`, `view_checklist`).

Must merge before #741 (both touch `WorkOrderContent.tsx`; #741 cherry-picks on top).

---

## Notifications wired (2026-04-27 session)

Three fire-and-forget `pms_notifications` inserts added to `internal_dispatcher.py` for data-continuity:

| Trigger | Notification type | Recipient | Priority |
|---------|------------------|-----------|----------|
| `create_work_order` with no `assigned_to` | `wo_unassigned` | creator | medium |
| `assign_work_order` | `wo_assigned` | assignee | medium |
| `close_work_order` with required incomplete checklist items | `wo_closed_incomplete_checklist` | closer | high |

All three are try/except — never block the primary action.

---

## Open items

- **Checklist photo requirement**: items with `requires_photo=true` should open the upload modal before `mark_checklist_item_complete` fires.
- **Link fault/equipment to WO**: no UI to add/remove these links from inside a WO card.
- **Documents sub-tab**: upload wiring deferred (no endpoint yet).
- **Crew picker for Assign**: `AssignModal` currently takes a raw user ID. Needs a searchable dropdown like `AddPartModal`.
- **Port JSON checklist → `pms_checklists` tables**: `metadata.checklist[]` is the live path; the relational tables exist but have no active writers. Separate PR after UX is settled.
- **Drop `pms_attachments.description`**: wait until all lenses adopt threaded comments, then remove.
- **PR-WO-5**: Calendar tab. ~6–10h. Begins after #731 + #741 are merged.
