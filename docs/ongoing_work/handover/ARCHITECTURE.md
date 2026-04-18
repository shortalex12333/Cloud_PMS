# Handover Domain — Architecture (working notes)

Status: living document for the `feat/handover04-incoming-sign` branch.
Keep it narrow — this file is for invariants worth pinning down, not a rehash of
`docs/explanations/LENS_DOMAINS/handover.md`.

## 1. Where data lives

All operational tables live in TENANT DB (`vzsohavtuotocgrfkfyd`). The app's
`supabase` client points at MASTER and is for auth only. All PMS reads/writes flow
through Render API (`pipeline-core.int.celeste7.ai`).

## 2. The document row

`handover_exports` is the single source of truth for the document and for all three
signatures. One row per export. See `docs/explanations/LENS_DOMAINS/handover.md`
for the column listing. The earlier `handover_signoffs` table is deprecated — not
created, not written, not read by current code.

## 3-7. (Sections reserved — add as invariants surface)

## 8. State machine

Two state columns exist on `handover_exports`. Only one is real.

### `review_status` — the real state machine

```
pending_review  ──(user signs)─────────▶  pending_hod_signature  ──(HOD countersigns)─▶  complete
```

| Value | Meaning | Routes that transition INTO this |
|---|---|---|
| `pending_review` | Export generated, user has not yet signed | `POST /v1/handover/export` (create) |
| `pending_hod_signature` | User signed (`user_signature` + `user_signed_at` set). Waiting for HOD countersign. | `POST /v1/handover/export/{id}/submit` |
| `complete` | HOD countersigned (`hod_signature` + `hod_signed_at` set). Document is frozen. | `POST /v1/handover/export/{id}/countersign` |

`review_status` is the column every route, every handler, and every role gate reads.
Treat it as canonical.

### `status` — legacy, kept for backward compatibility

The `status` column on `handover_exports` predates `review_status` and is retained
for backward compat with old rows and any downstream consumer that may still query
it. **Do not branch on `status` in new code.** If the two ever disagree,
`review_status` wins.

## 8a. Deprecated: `status` column

PR #642 retired `status` as the state-machine driver for handover_exports.

### Why deprecated
- `review_status` (`pending_review → pending_hod_signature → complete`) is the
  compliance-gated state machine. Every HOD-gate and every frontend read already
  uses it.
- The legacy values on `status` (`pending_outgoing → pending_incoming → completed`)
  modelled the dual-signature flow from the older `/sign/outgoing` +
  `/sign/incoming` handler path. They parallel `review_status` but with different
  labels, and the two columns drifted — the `sign_incoming` handler was reading
  `status` while `countersign` was writing `review_status`, which is the bug PR
  #642 fixed.
- With PR #642 the `sign_incoming` gate reads `review_status='complete' AND
  incoming_signed_at IS NULL`. The state is fully expressed by `review_status` +
  the per-role `*_signed_at` columns.

### What changed in this PR
- `handover_workflow_handlers.sign_outgoing` no longer writes
  `status='pending_incoming'`.
- `handover_workflow_handlers.get_pending_handovers` now filters on
  `review_status` + `outgoing_signed_at` / `incoming_signed_at` instead of
  `status`.
- `handover_workflow_handlers.sign_incoming` still writes `status='completed'`
  as a backward-compat mirror (it is the point of the state machine where the
  semantics of `status` and `review_status + incoming_signed_at IS NOT NULL`
  unambiguously coincide).
- `generate_export` still writes `status='pending_outgoing'` because
  `sign_outgoing` still reads it as its precondition. Both sites carry a
  `DEPRECATED` comment pointing here and to task T4.

### status ↔ review_status mapping (for reference and for any remaining SQL)
| Legacy `status`      | Equivalent `review_status` + signature columns                        |
|----------------------|-----------------------------------------------------------------------|
| `draft`              | `review_status='pending_review' AND user_signed_at IS NULL`           |
| `pending_outgoing`   | `review_status='pending_review' AND outgoing_signed_at IS NULL`       |
| `submitted`          | `review_status='pending_hod_signature'`                               |
| `pending_incoming`   | `review_status='complete' AND incoming_signed_at IS NULL`             |
| `completed`          | `review_status='complete' AND incoming_signed_at IS NOT NULL` (or `signoff_complete=true`) |

Note: production rows written before PR #642 may have `status` but no populated
`review_status`. The column is not dropped yet; historic SQL that still reads
`status` will continue to return meaningful values for those rows.

### Why not dropped yet
1. Production data — rows created before PR #642 carry `status` values and
   downstream BI / audit scripts may still query the column.
2. The twin handler path (`/sign/outgoing` + `/sign/incoming`) still uses
   `status='pending_outgoing'` as a precondition; removing the column without
   consolidating that path first would break it. Consolidation lives on task
   T4.
3. Dropping a column with live RLS policies attached is a schema migration
   that warrants its own PR + rollback plan.

### Migration plan for a future PR
1. Finish task T4 — pick one of the twin signing paths (`/submit + /countersign`
   vs `/sign/outgoing + /sign/incoming`) and remove the other. The remaining
   path must gate exclusively on `review_status`.
2. Add a SQL backfill that populates `review_status` + `*_signed_at` columns
   for any legacy row where they are NULL but `status` is set, using the mapping
   above. Verify row counts match before deleting anything.
3. Add a Postgres trigger on `handover_exports` that keeps `status` in sync with
   `review_status` + `incoming_signed_at` for any external consumer still
   reading the column. The trigger is one-way — `status` becomes a derived
   column that the app never writes directly.
4. Audit / confirm no external consumer (other services, dashboards, exports)
   reads `status` anymore.
5. Drop the trigger, drop the column, and remove the three `DEPRECATED`
   annotations in `handover_workflow_handlers.py`.

### Incoming acknowledgment — fourth transition, no state change

Incoming acknowledgment is modelled as signature fields on the already-`complete`
row, not as an extra `review_status` value. The signal for "complete handover but
not yet acknowledged by the incoming crew member" is:

```
review_status = 'complete'  AND  incoming_signed_at IS NULL
```

On `POST /v1/handover/export/{id}/sign/incoming` the route writes
`incoming_signature`, `incoming_signed_at`, `incoming_user_id`,
`incoming_acknowledged_critical`, `incoming_comments`, `incoming_role` on the same
row. `review_status` stays `complete`. `signoff_complete` flips to `true` once all
three signatures are present.

Why not a new state value: the HOD countersign is the compliance gate. The incoming
acknowledgment is an operational receipt — useful, auditable, but not a blocker to
declaring the handover legally complete. Modelling it as a state transition would
imply the HOD-signed document is not "done" until the replacement crew reads it,
which is not the design intent.

## 9. (Reserved)
