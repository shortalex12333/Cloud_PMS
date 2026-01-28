# Fault Lens — Scenarios & Journeys (6)

All journeys are backend‑authoritative, deterministic, and auditable. Crew are read‑only; HOD (chief_engineer, chief_officer) and captain mutate; manager signs where explicitly allowed.

---

1) Engine room breakdown at sea (critical)
- Role/where: Chief Engineer in ER on mobile (intermittent signal)
- Intent: "seawater pump failure"
- Steps:
  1. Suggestions lists `report_fault` with prefill (equipment_id resolved, severity=critical)
  2. Execute `report_fault` (200): insert pms_faults; audit row with signature={}
  3. `add_fault_photo` (200): store to pms-discrepancy-photos/{yacht_id}/faults/{fault_id}/…; audit {}
  4. `acknowledge_fault` (200): status→investigating; audit {}
  5. `diagnose_fault` (200): metadata.diagnosis set; audit {}
  6. `create_work_order_from_fault` (SIGNED): captain provides signature; WO created and linked; audit signature JSON
- Edge cases: missing signature → 400; equipment mismatch → 404; cross‑yacht → 403

2) Cosmetic interior issue (false alarm)
- Role/where: Chief Officer during walkthrough
- Intent: "wardrobe scratch in guest cabin"
- Steps: `report_fault` (cosmetic) → later `mark_fault_false_alarm` (200)
- Guardrails: crew cannot mutate; storage path stays under yacht faults prefix

3) Regression after closure (sea trial)
- Role/where: Chief Engineer after sea trial
- Steps: `reopen_fault` (200) → `create_work_order_from_fault` with signature → 200
- Notifications: if WO remains draft > 6h, create pms_notifications (CTA=update_work_order)

4) Night‑shift monitoring (ack backlog)
- Role/where: Captain reviews dashboard; several faults `open`
- Steps: `acknowledge_fault` for each; audit rows recorded
- Error mapping: not found → 404; already in investigating → 409

5) Spare parts dependency (photo evidence)
- Role/where: Chief Officer attaches photos for warranty case
- Steps: `add_fault_photo` (200) multiple files; path preview shown before upload; audit rows `{}`
- Storage: `pms-discrepancy-photos/{yacht_id}/faults/{fault_id}/{filename}`

6) Yard period handover (handover vs fault)
- Role/where: Purser read‑only; HOD handles WOs
- Steps: `view_fault_detail` and `view_fault_history` only; avoid prompting "add to handover" during active fault flow
- Notifications: post‑factum reminder created via v_pending_work_items for incomplete handover sections (CTA=add_to_handover) — outside Fault flow

---

Deterministic error mapping (all scenarios)
- 400 validation: missing required field(s), invalid severity/state transition
- 403 RLS/role denial: crew mutation, cross‑yacht
- 404 not found: wrong IDs in current yacht
- 409 conflict: duplicate WO, illegal double close
- 500 hard failure: treated as bug; tests fail

Ledger (Invariant in all journeys)
- One row per action, signature NOT NULL; {} for non‑signed; canonical JSON for signed
- Entity history by entity_type='fault' and entity_id

