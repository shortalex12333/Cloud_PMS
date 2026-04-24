# Fault Card — Design Spec (NEW VISION UX)

**Owner:** FAULT05 · **Date:** 2026-04-24 · **Supersedes:** blank section at `/Users/celeste7/Desktop/lens_card_upgrades.md:501-618`
**Design system:** `celeste-design-philosophy` skill (`Cloud_PMS/.claude/skills/celeste-design-philosophy/skill.md`). Design tokens: `apps/web/src/styles/tokens.css`. Work-order parallel: `apps/web/public/prototypes/lens-work-order-v6.html`.

## 1. Why the Fault card looks different from Work Order

A fault is **evidence**. A work order is **instruction**. The two entities must *feel* different at first glance so crew never confuse logging a problem with scheduling a fix.

- **Work Order card** opens with checklist + SOP + parts → task-to-complete posture.
- **Fault card** opens with a **hero image** (the photo the reporter took) + identity strip → proof-of-observation posture.

The hero image is deliberate, not ornamental:
1. 80% of faults are spotted visually; the photo *is* the primary evidence.
2. Encourages crew to always upload a photo — habit-forming through visual primacy.
3. Visually differentiates Fault from Work Order at one glance.
4. Matches SOLAS/MLC surveyor norm: "show me a picture of the defect".

If no photo exists, the hero slot shows a **placeholder with an inline "Upload the first photo" CTA** — not a broken frame. One teal button. Nothing else in the slot.

## 2. Column-by-column audit (pms_faults + v_faults_enriched)

Columns confirmed via live psql probe 2026-04-24. Format: `column | type | FE/BE | visible where | how rendered | why`.

### Identity & classification
- `id` | `uuid` | BE only | — | — | Primary key. Never shown to users — "non legibile, security risk" (CEO doctrine, `lens_card_upgrades.md:530`).
- `yacht_id` | `uuid NOT NULL` | FE with transposition | Audit trail footer only | Transpose via MASTER `fleet_registry` → vessel name | Users should see "*MY EXAMPLE*" not a UUID.
- `equipment_id` | `uuid NOT NULL` | FE with transposition | **Identity strip detail line** | Transpose via TENANT `pms_equipment` → `{code} — {name}` clickable chip | Click routes to equipment card. The fault MUST be tied to equipment; if a reporter lands with no equipment the Report Fault modal prompts for it.
- `fault_code` | `text` | FE | **Identity overline**, monospace, above title | e.g. `FLT-0042` | CEO specifically asked for this to be visible (`lens_card_upgrades.md:535`).
- `title` | `text NOT NULL` | FE | **Identity title**, 22px/600 | As-is | First-read handle.
- `description` | `text` | FE | **Below identity strip** (collapsible if >3 lines) | Inter body 14px/400 | The reporter's words.
- `severity` | `enum(critical,high,medium,low)` | FE | **Pill on identity strip** | Red (critical/high) / Amber (medium) / Neutral (low) | Glance-readable urgency.
- `status` | `text`, CHECK(`open,investigating,resolved,closed`) | FE | **Pill on identity strip** | Red (open) / Amber (investigating) / Green (resolved) / Neutral (closed) | Primary state indicator. Note: `'archived'` is NOT in the enum — archived faults show via the `deleted_at IS NOT NULL` pill variant "Archived", neutral grey.
- `category` | *(not in pms_faults; maybe in metadata)* | FE | Identity detail line if present | Plain text | Lightweight classifier when present.
- `root_cause` | *(in `metadata` or a TBD column)* | FE | Root-cause-analysis section | KV list | Often populated post-resolution.

### Temporal
- `detected_at` | `timestamptz NOT NULL DEFAULT now()` | FE | **Identity detail line** "Date Reported" | Human-formatted: "2 days ago · Mon 22 Apr 14:06" | The canonical timestamp; do NOT show raw ISO.
- `resolved_at` | `timestamptz` | FE | Identity detail line "Resolved" (only if set) | Same format | Shown only when `status IN ('resolved','closed')`.
- `created_at` | `timestamptz NOT NULL` | BE only OR Audit Trail | — | — | CEO noted repetition with `detected_at` (`lens_card_upgrades.md:543`). For MVP: treat `created_at` = system insert time, `detected_at` = physical observation time. Surfaced ONLY in audit trail footer.
- `updated_at` | `timestamptz` | Audit trail | Row per event | Mono timestamp + actor | Audit section only.
- `imported_at` | `timestamptz` | BE only | — | — | Seed data provenance; hidden.

### Actors (UUIDs — must transpose to name+role per `feedback_reviewer_handover_format.md` and CERT04 pattern)
- `resolved_by` | `uuid` | FE enriched | "Resolved by" line under Identity strip when resolved | Transpose via MASTER `auth_users_profiles` → "Jane Smith · Chief Engineer" | Clickable crew chip → crew profile.
- `updated_by` | `uuid` | Audit trail only | Same transposition | Row-per-event | Audit section only.
- `deleted_by` / `deletion_reason` | `uuid / text` | FE on archived | Audit trail + "Archived" pill hover | Transpose name | Visible only when row is archived (soft-deleted).

### Linkage
- `work_order_id` | `uuid` | FE | "Related Work Order" row in Related section | Transpose via TENANT `pms_work_orders` → `{wo_code} — {title}` chip | Canonical FK for "resolved by WO #…" and active-WO linkage (authoritative per WORKORDER05 PR #691). Do NOT introduce a second column.
- `related_text` | `text` | BE only | — | — | Internal projection-worker helper; not user-facing.
- `metadata` | `jsonb` | Mixed | Context-dependent | Renders whatever keys are present via KV list | Holds: `archive_reason`, `close_reason`, `root_cause`, freeform crew notes. Not a user-entry surface directly; set by specific actions.

### Seed/import provenance (all BE only)
- `is_seed`, `source`, `source_id`, `source_reported_by`, `source_resolved_by`, `import_session_id` | mixed | BE only | — | — | Hidden. Used by ingestion pipeline only.

## 3. Sections — top-to-bottom order

Strict order, per `celeste-design-philosophy` §16 (Fault view is a DOCUMENT, not a dashboard — scroll, no tabs, no card grids):

1. **HERO IMAGE STRIP** ← NEW — center-of-focus, 4:3 aspect, first photo's `storage_path` rendered with `pms-discrepancy-photos` bucket signed URL. Caption overlay at bottom (`username: caption`). Click to open full-screen lightbox.
2. **IDENTITY STRIP** — overline (`fault_code` mono), title, context line (equipment chip + location + reporter + vessel), pills (`severity`, `status`), detail lines (Equipment, Date Reported, Category, Root Cause, Resolved), primary action on right.
3. **Description** — the reporter's words, inline with the entity. KVSection with no label.
4. **Corrective Action** — if populated (after investigation).
5. **Root Cause Analysis** — key/value list from `metadata.root_cause_analysis`.
6. **Related** — work order chip (if `work_order_id`), linked equipment (auto from `equipment_id`), **Linked Parts** (new, from `pms_fault_parts` junction).
7. **Evidence & Attachments** (more photos beyond the hero) — thumbnail grid; single `description` caption per photo; Add Photo button top-right of section header.
8. **Notes** — `pms_notes WHERE fault_id=...`, newest first, truncate at 3 lines with "Show more". Add Note button top-right.
9. **Reference Documents** — linked `pms_documents` (SOPs, manuals, survey reports).
10. **History** — prior fault periods (recurrence on same equipment).
11. **Audit Trail** — every mutation: created, acknowledged, linked parts, closed, archived, etc. Mono timestamps, actor name+role, one line per event.

## 4. Action matrix (final — source of truth for the consolidated PR)

Legend: **K**=Keep, **N**=New, **R**=Remove, **C**=Conditional. Gate: role first, department fallback via `auth_users_profiles.department`.

| Action | Status | Roles allowed | Dept fallback | Signature | Where it lives |
|---|---|---|---|---|---|
| Acknowledge Fault | K | HOD, Captain | ENG / DECK | No | Dropdown |
| Resolve Fault | K | HOD, Captain, Crew | ENG / DECK | L2 (typed name) | Primary when status=investigating |
| Close Fault (with reason dropdown) | K | HOD, Captain | ENG / DECK | L3 (PIN) + mandatory `close_reason` select | Dropdown |
| Archive Fault (soft-delete) | N | HOD, Captain | ENG / DECK | L3 (PIN) + `reason` free text | Dropdown, danger style |
| Reopen Fault | C | HOD, Captain | ENG / DECK | L2 | Dropdown, only when status IN (closed, resolved) OR deleted_at IS NOT NULL |
| Add Fault Photo | K | Crew, HOD, Captain | ENG / DECK | No | Section header of Evidence |
| Add Fault Note | K | Crew, HOD, Captain | ENG / DECK | No | Section header of Notes |
| Link Parts | N | HOD, Captain | ENG / DECK | No (for link); L2 for unlink | Section header of Related |
| Unlink Part | N | HOD, Captain | ENG / DECK | L2 + reason | Inline on each linked-part row |
| Create Work Order from Fault | K | HOD, Captain, Manager | ENG / DECK | L3 (PIN) | Dropdown (optional — Resolve does not require this) |
| Add to Handover | N (stubbed) | HOD, Captain | ENG / DECK | No | Dropdown — disabled until HANDOVER08 ships contract |
| View Fault History | K | All | — | No | Dropdown (retained for EQUIPMENT05 cross-lens) |
| Report Fault | K | Crew, HOD, Captain | ENG / DECK | No | Top-of-list CTA, NOT in per-card dropdown |
| Investigate | R | — | — | — | REMOVED — wasteful |
| Diagnose Fault | R | — | — | — | REMOVED — duplicates Update Fault intent |
| Mark as False Alarm | R | — | — | — | REMOVED — folded into Close Fault reason="False alarm" |
| Classify Fault | R | — | — | — | REMOVED — wasteful |
| Suggest Parts | R | — | — | — | REMOVED — replaced by explicit "Link Parts" |
| Update Fault | R | — | — | — | REMOVED — repeated semantics |
| Delete Fault | R | — | — | — | REMOVED — Archive is the only terminal-remove |
| View Fault Detail | R | — | — | — | REMOVED — card already shows it |

### `close_reason` enum — dropdown options on Close Fault modal

Per CEO doctrine "Close is vague — provide categories":
1. `fault_resolved` — "Fault resolved in situ"
2. `awaiting_parts` — "Awaiting parts — held in queue"
3. `machinery_out_of_service` — "Machinery taken out of service"
4. `false_alarm` — "Closed as false alarm"
5. `superseded_by_work_order` — "Superseded — see linked WO"
6. `other` — "Other" (requires free-text explanation)

Stored as `pms_faults.metadata.close_reason` + `pms_faults.metadata.close_reason_note` (when `other`). New migration NOT required — jsonb. Ledger event includes the close_reason.

## 5. Wireframe (ASCII)

```
╔════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║                     ██████████████████████████                          ║
║                     █                        █                          ║
║                     █      HERO IMAGE        █                          ║
║                     █       (first photo,    █                          ║
║                     █        4:3 aspect)     █                          ║
║                     █                        █                          ║
║                     ██████████████████████████                          ║
║                     │ user_name: "caption" │  ← overlay at bottom        ║
║                                                                          ║
╠════════════════════════════════════════════════════════════════════════╣
║  FLT-0042                                         ┌──────────────────┐ ║
║  ──────────────────                                │ Resolve Fault  ▼ │ ║
║  Rudder bearing excessive play                    └──────────────────┘ ║
║                                                                          ║
║  [INVESTIGATING]  [CRITICAL]                                            ║
║  FA037 AC Cooling Unit Master Cabin · Jane Smith (Chief Engineer) ·    ║
║      MY EXAMPLE                                                          ║
║                                                                          ║
║  EQUIPMENT       FA037 — Rudder bearing assembly (click →)              ║
║  DATE REPORTED   2 days ago · Mon 22 Apr 14:06                          ║
║  CATEGORY        Mechanical                                              ║
║  ROOT CAUSE      —                                                       ║
║                                                                          ║
║  Description                                                             ║
║  > Port-side rudder bearing exhibits 3mm lateral play when helm at       ║
║  > centre. Audible knock under engine load. Oil weep at seal.            ║
║                                                                          ║
╠════════════════════════════════════════════════════════════════════════╣
║  🔗 RELATED                                         + Link Parts        ║
║  ─────────────────                                                       ║
║  ▸ Work Order  WO-0081 — Bearing replacement & realignment  → (click)   ║
║  ▸ Equipment   FA037 — Rudder bearing assembly                          ║
║  ▸ Parts       FA037-BR1 — Port rudder bearing (×1)          ✕ unlink   ║
║                FA037-SEAL — Shaft seal oil weep kit (×1)     ✕ unlink   ║
║                                                                          ║
╠════════════════════════════════════════════════════════════════════════╣
║  📷 EVIDENCE & ATTACHMENTS                       + Add Photo           ║
║  ─────────────────────────                                               ║
║  ┌──────┐ ┌──────┐ ┌──────┐                                             ║
║  │ img1 │ │ img2 │ │ img3 │                                             ║
║  └──────┘ └──────┘ └──────┘                                             ║
║  caption  caption  caption                                               ║
║                                                                          ║
║  ▸ img1 (primary caption: "bearing race pitting, port side")            ║
║    │ Jane Smith · ChEng · 30m  "oil weep visible along seal"            ║
║    │ John Doe   · Deck  · 10m  "sound also audible during sail"         ║
║    │ + Add new comment                                                   ║
║                                                                          ║
╠════════════════════════════════════════════════════════════════════════╣
║  💬 NOTES                                        + Add Note            ║
║  ─────────                                                               ║
║  Jane Smith · Chief Engineer · 1 h ago                                   ║
║  > Hauled the rudder-quadrant cover; bearing race pitted. Part ordered.  ║
║                                                                          ║
║  John Doe · Deckhand · 2 h ago                                           ║
║  > Noticed the knock while manoeuvring. Heading noise recording uploaded ║
║    as img2.                                                              ║
║                                                                          ║
╠════════════════════════════════════════════════════════════════════════╣
║  📄 REFERENCE DOCUMENTS                                                 ║
║  ─────────────────────                                                   ║
║  ▸ SOP — Rudder bearing inspection                                       ║
║  ▸ Manual — ABB MH-500 rudder assembly                                   ║
║                                                                          ║
╠════════════════════════════════════════════════════════════════════════╣
║  🕓 HISTORY (prior occurrences on FA037)                          ▼    ║
╠════════════════════════════════════════════════════════════════════════╣
║  🧾 AUDIT TRAIL                                                   ▼    ║
╚════════════════════════════════════════════════════════════════════════╝
```

## 6. Styling notes (celeste-design-philosophy compliance)

- **Colour:** status pills use canonical green/amber/red; severity pill uses canonical red/amber/neutral. Action buttons use `--mark` (teal). Never mix affordance with status colours.
- **Typography:** `fault_code` in overline = mono; title = Inter 22px/600; body = Inter 14px/400; timestamps + IDs = mono. Section headers = 14px/600 uppercase `--txt3`.
- **Elevation:** Identity strip and hero image have NO shadow (content, not floating). Popup modals use asymmetric border + shadow (floating above content).
- **Rows:** Related/Parts/Attachments rows use 44px min-height, 8/12 padding.
- **Glass:** NO glass on any section (content layer). Glass is header/sidebar only.
- **Ruled lines:** `border-top: 1px solid var(--border-sub)`, `margin-top: 32px`, `padding-top: 24px` between sections. Preserves the document metaphor.

## 7. Integration with projection_worker (the GraphRAG pipeline)

Per CEO: "show_related" must surface cross-entity links from the fault (work order, equipment, linked parts, notes) via the semantic search/projection pipeline.

**Required:** the new `pms_fault_parts` junction table must be picked up by the projection worker so:
- Querying "rudder bearing" on any lens returns this fault as a result via `search_index`.
- Opening `FA037-BR1` (part) shows "Related faults: FLT-0042" via graph_edges.

**Action for projection_worker:** add a projection function `project_fault_parts_link(fault_id)` that:
1. Writes a `search_index` row for each `(fault_id, part_id)` link with type `fault_part_link`, `yacht_id` scoped, embedding computed from concatenated fault title + part name.
2. Writes a `graph_edges` row `source=fault_id`, `target=part_id`, `edge_type='HAS_LINKED_PART'`.
3. Fires on `INSERT` and marks `deleted_at IS NOT NULL` on `unlink_part_from_fault` soft-delete.

Pattern to mirror: `apps/api/orchestration/projection_worker.py` (TBD exact path — sub-agent will grep on resume). CERT04's linked-equipment pattern is the closest reference point.

## 8. Known MVP tradeoffs (documented so no one is surprised)

1. **~~Single-caption per photo.~~ Upgraded to threaded comments via WORKORDER05 PR #696 (2026-04-24 14:36Z).** New polymorphic table `pms_attachment_comments` ships with cohort actions — our evidence photos get real threaded discussion. `pms_attachments.description` remains the primary caption (set at upload); threaded follow-ups via `add_attachment_comment({attachment_id})`. Matches CEO's original Issue 7 illustration frame with the `*Add new comment**` button.
2. **`'work_ordered'` is a dead status value.** Trigger `trg_wo_status_cascade_to_fault` references it; CHECK constraint rejects it. Queued as PR-FAULT-STATE-MACHINE follow-up.
3. **`pms_faults.work_order_id` vs historical assumptions.** Real, live, indexed FK. Not a dead column (WORKORDER05 PR #691 correction).
4. **Archive = soft-delete** (write `deleted_at`, `deleted_by`, `deletion_reason`) rather than adding `'archived'` to the status CHECK — zero schema change, matches existing columns.
5. **`work_order_id` canonical for terminal resolver**; do not reintroduce `resolved_by_work_order_id`.

## 9. References

- CEO directive: `/Users/celeste7/Desktop/list_of_faults.md:248` (Issue 7)
- CEO UX sheet (this spec fills the blank): `/Users/celeste7/Desktop/lens_card_upgrades.md:501-618`
- Work-order parallel structure: `lens_card_upgrades.md:300-500`
- DB architecture: `docs/explanations/DB_ARCHITECTURE.md`
- Design philosophy: `Cloud_PMS/.claude/skills/celeste-design-philosophy/skill.md`
- Work-order HTML prototype: `apps/web/public/prototypes/lens-work-order-v6.html` (canonical layout reference)
- Shared EntityTableList pattern (for list view): DOCUMENTS04's PR #673
