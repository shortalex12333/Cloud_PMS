# Faults Lens — Living Plan

**Owner:** FAULT05 · **Branch:** `feat/fault05-issue7` · **Draft PR:** [#693](https://github.com/shortalex12333/Cloud_PMS/pull/693)
**Source spec:** `/Users/celeste7/Desktop/list_of_faults.md:248` (Issue 7) + `/Users/celeste7/Desktop/lens_card_upgrades.md:501-618`
**Design spec (new vision UX, hero-image Fault card):** [`FAULT_CARD_DESIGN_SPEC.md`](./FAULT_CARD_DESIGN_SPEC.md)
**Wire-walk:** [`wire-walk-2026-04-24.md`](./wire-walk-2026-04-24.md)

## Goal

Ship one consolidated PR that:
1. Unbreaks every button on the Faults page (all currently 400).
2. Prunes wasteful actions, adds missing ones (Archive, Link Parts), and hides buttons that don't apply to the current status.
3. Adopts the shared tabulated list view (DOCUMENTS04's EntityTableList) for the faults list.
4. Integrates the CEO's boil-the-ocean directives: hero-image card, threaded photo comments (via WORKORDER05 cohort), hybrid role+department gate, `close_reason` dropdown, soft-delete Archive.
5. Deletes the illegal `apps/web/src/lib/microactions/handlers/faults.ts` that queries TENANT tables from the MASTER-scoped browser client (broken in practice; security violation in principle).
6. Tests + documentation alongside the code — no debt.

## Status

| # | Item | State |
|---|---|---|
| 1 | Fix 400 on `add_fault_note` (FE payload + BE hardcoded validator → `text`) | ✅ committed `364eca5d` |
| 2 | Pop-up min-height floor (CEO cramped-popup complaint) | ✅ committed this pass |
| 3 | Remove `investigate_fault` primary-action hardcoding in `FaultContent.tsx` | ✅ committed this pass |
| 4 | Seed PLAN.md + wire-walk scaffold | ✅ this commit |
| 5 | Delete REQUIRED_FIELDS hardcoded dict in `p0_actions_routes.py:781-849`; delegate to registry | ⏳ backend sub-agent @ 22:30 NY |
| 6 | Prune registry: delete `diagnose_fault`, `mark_fault_false_alarm`, `view_fault_detail`, `update_fault` | ⏳ backend sub-agent |
| 7 | Retain `view_fault_history` (cross-lens need — EQUIPMENT05 Issue 4) | ⏳ backend sub-agent |
| 8 | Add registry entries: `archive_fault`, `resolve_fault`, `link_parts_to_fault`, `unlink_part_from_fault` | ⏳ backend sub-agent |
| 9 | Migration: `pms_fault_parts` junction table + RLS + projection_worker hook | ⏳ backend sub-agent |
| 10 | Migration: formalise `pms_faults.equipment_id` FK to `pms_equipment(id)` (EQUIPMENT05 delegated) | ⏳ backend sub-agent |
| 11 | Upgrade `close_fault` to SIGNED + mandatory `close_reason` dropdown (6 enum values) | ⏳ backend sub-agent |
| 12 | Hybrid role + department gate (read `auth_users_profiles.department` fallback) | ⏳ backend sub-agent |
| 13 | Delete `lib/microactions/handlers/faults.ts` + migrate consumers to `executeAction()` | ⏳ frontend sub-agent |
| 14 | Wire `add_fault_photo` to `AttachmentUploadModal` (currently a `TODO`) | ⏳ frontend sub-agent |
| 15 | Wire per-photo comment thread via `add_attachment_comment` (WORKORDER05 cohort actions) | ⏳ frontend sub-agent |
| 16 | Add "Linked Parts" section + PartsPickerModal (multi-select refactor of EquipmentPickerModal) | ⏳ frontend sub-agent |
| 17 | Hero image slot on the fault card (per design spec §3 + §5 wireframe) | ⏳ frontend sub-agent |
| 18 | Translate `reported_by`/`resolved_by`/`updated_by` UUIDs → "Name · Role" via `auth_users_profiles` | ⏳ frontend sub-agent |
| 19 | Hide Reopen unless `status ∈ {closed, resolved}` OR `deleted_at IS NOT NULL` | ⏳ frontend sub-agent |
| 20 | Stub Add-to-Handover as disabled dropdown item with tooltip "pending HANDOVER08 contract" | ⏳ frontend sub-agent |
| 21 | Adopt `FAULT_COLUMNS` on faults list page (EntityTableList pattern) | ⏳ frontend sub-agent |
| 22 | Tests: handler unit tests + FaultContent snapshot + Playwright e2e smoke | ⏳ both sub-agents |
| 23 | `HANDOFF.md` + `fault_vs_shopping_list.md` | ⏳ docs sub-agent |
| 24 | Memory updates + MEMORY.md index entries | ✅ ongoing |

## Decisions (all CEO-approved 2026-04-24 — see `project_fault05_issue7_session.md`)

1. Role + Department HYBRID gate — roles primary, `auth_users_profiles.department IN ('ENGINEERING','DECK')` as fallback.
2. Archive = soft-delete (`deleted_at`/`deleted_by`/`deletion_reason`). Close = terminal with mandatory reason dropdown (6 options, stored in `metadata.close_reason`).
3. Resolve is DIRECT — WO creation optional, separate dropdown item.
4. Fault↔Part junction table: `pms_fault_parts`. Must integrate with `projection_worker` → `search_index` + `graph_edges`.
5. Per-photo comments: adopt `pms_attachment_comments` cohort via `add_attachment_comment({attachment_id, comment})` — polymorphic across entity_type, NOT single-caption.
6. Delete illegal FE-direct file — it queries TENANT tables from MASTER-scoped browser client; in-practice broken.
7. Hero image center-of-focus on card — encourages photo upload, differentiates Fault from Work Order visually.

## Deferred (PR-F2, PR-F3 follow-ups)

- Extend `pms_faults.status` CHECK constraint to include `'work_ordered'` (trigger references a dead state; PR-FAULT-STATE-MACHINE)
- Drop dead column `pms_faults.work_order_id` if seed-data check confirms no history (PR-FAULT-CLEANUP-DEAD-COLS)
- Shopping-list bridge from Linked Parts section → "Add to shopping list" (PR-F2)
- `add_fault_to_handover` wiring (blocked on HANDOVER08 contract)
- Nested reply rendering on photo comments (Phase 2; DB column `parent_comment_id` already passes through)

## Peer coordination log

See `project_fault05_issue7_session.md` for the full timestamped message log. Summary:
- **WORKORDER05** (x9hy6zor) shipped PR #689 → PR #691 (fault auto-resolve via DB trigger) + PR #696 (`pms_attachment_comments` polymorphic table) + answers on payload field naming, RLS, role gating.
- **CERTIFICATE04** (a4rjnwoe) confirmed no prior multi-comment work; single-caption was the pre-pivot MVP.
- **EQUIPMENT05** (30wiu4g9) retains `report_fault` + `view_fault_history`; delegated pms_faults.equipment_id FK migration to my branch.
- **HANDOVER08** (uejnwuv3) holding Add-to-Handover contract pending CEO 4-question decision.
- **DOCUMENTS04** (yoipdwmt) confirmed EntityTableList pattern is cohort-stable; FAULT_COLUMNS queued.
