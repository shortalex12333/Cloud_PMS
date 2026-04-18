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
