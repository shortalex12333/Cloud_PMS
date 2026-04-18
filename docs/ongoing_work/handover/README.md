# Handover — Ongoing Work

This directory holds the living state of the Handover domain while work is in
flight. Once a PR merges, the corresponding bullets are moved to the "Resolved"
section below (and, where relevant, mirrored into `HANDOVER_FINAL_STATUS.md`).

## Index

- `ARCHITECTURE.md` — invariants (state machine, SSOT, table deprecations).
- `HANDOVER_FINAL_STATUS.md` — scenario-by-scenario MVP test status.
- `HANDOVER_CEO_SUMMARY.md`, `HANDOVER_MANUAL_TEST_LOG.md`,
  `HANDOVER_NEXT_ENGINEER.md`, `HANDOVER_PLAYWRIGHT_AGENT_RUNBOOK.md` —
  supporting notes and runbooks.

## Known gaps (as of MVP ship)

Mirror of the known-gaps table in `HANDOVER_FINAL_STATUS.md` plus anything
surfaced after that file was last updated. Keep both in sync when you close a
gap.

| Gap | Impact | Status |
|---|---|---|
| Incoming crew 3rd sign | No "received" acknowledgment from replacement | In-flight on `feat/handover04-incoming-sign` — see pre-staged section below |
| `entity_url` null on old exports | "View Fault" links don't render on March exports | New exports populate correctly |
| Signature block static | No SIGNED timestamps | Data available, rendering not dynamic |
| Manager test account | TENANT JWT, backend expects MASTER | Test infra gap — needs MASTER user |
| PDF export | `window.print()` only | Works but not server-side |

## Resolved in `feat/handover04-incoming-sign` (PR pending — DO NOT mark closed until merge)

Pre-staged entries. Flip each to "Closed" in this file and move the matching
bullet out of "Known gaps" above once the PR lands on `main`.

- [ ] Incoming 3rd sign button added to `HandoverContent.tsx` (dynamic 3-column
  signature block: Prepared / Reviewed / Received).
- [ ] `sign_incoming` state machine reconciled — route writes incoming_*
  fields on the same `handover_exports` row; `review_status` stays `complete`;
  `signoff_complete` flips once all three signatures present. See
  `ARCHITECTURE.md` section 8.
- [ ] Ledger event `handover_acknowledged` added (emitted on successful
  `/sign/incoming`).
- [ ] Notification cascade on incoming acknowledgment — captain + HOD + manager
  receive a ledger_events row with entity_id set for navigability.
- [ ] Entity endpoint (`/v1/entity/handover_export/{id}`) exposes `incoming_*`
  fields in its response payload so the frontend can render the Received
  column without a second round trip.
- [ ] Role gate on `/sign/incoming` widened to all authenticated yacht users
  (any crew member can acknowledge a handover targeted at them).

On merge: remove "In-flight" tag from the "Incoming crew 3rd sign" row above,
flip checkboxes here to `[x]`, and update `HANDOVER_FINAL_STATUS.md` known-gaps
table to match.
