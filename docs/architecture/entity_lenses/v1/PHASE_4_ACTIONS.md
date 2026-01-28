# Phase 4 — Actions and Contracts

Goal: Document → Tests → Code → Verify — backend defines actions, signatures, and RLS; no UI authority.
Lens: Receiving

Registry model
- Each action defines: id, allowed_roles, search_keywords, gating, required_fields, optional_fields, prepare/execute, validation rules, next_actions.

Actions
1) create_receiving
- Roles: HOD+
- Required: yacht_id, received_date?
- Optional: vendor_name, vendor_reference, currency, notes
- Gating: STATE_CHANGING
- Next: [attach_receiving_image_with_comment, extract_receiving_candidates]

2) attach_receiving_image_with_comment
- Roles: HOD+
- Required: yacht_id, receiving_id, document_id
- Optional: doc_type, comment
- Storage: path must be `{yacht_id}/receiving/{receiving_id}/{filename}` in the relevant bucket
- Gating: STATE_CHANGING
- Next: [extract_receiving_candidates]

3) extract_receiving_candidates (prepare only)
- Roles: HOD+
- Required: yacht_id, receiving_id, source_document_id
- Effect: runs OCR/parse; stores advisory result in pms_receiving_extractions; returns proposed updates and confidence; no writes to authoritative fields
- Gating: PREPARE
- Next: [update_receiving_fields, add_receiving_item]

4) update_receiving_fields
- Roles: HOD+
- Required: yacht_id, receiving_id
- Optional: vendor_name, vendor_reference, currency, received_date
- Gating: STATE_CHANGING
- Next: [accept_receiving]

5) add_receiving_item
- Roles: HOD+
- Required: yacht_id, receiving_id, description OR part_id
- Optional: quantity_expected, quantity_received, unit_price, currency
- Gating: STATE_CHANGING
- Next: [adjust_receiving_item]

6) adjust_receiving_item
- Roles: HOD+
- Required: yacht_id, receiving_id, receiving_item_id
- Optional: quantity_received, unit_price, description
- Gating: STATE_CHANGING; monotonic checks if policy requires

7) link_invoice_document
- Roles: HOD+
- Required: yacht_id, receiving_id, document_id
- Optional: comment
- Storage: same path rule as images; bucket typically `documents`
- Gating: STATE_CHANGING

8) accept_receiving (SIGNED)
- Roles: Captain or Manager
- Prepare: validate completeness (at least one item; totals computed), require signature payload (PIN+TOTP)
- Execute: set status='accepted'; freeze monetary fields; write signed audit
- Next: [optional posting to inventory in future lens]

9) reject_receiving
- Roles: HOD+
- Required: yacht_id, receiving_id, reason
- Effect: set status='rejected'; audit

10) view_receiving_history (read)
- Roles: Crew+
- Required: yacht_id, receiving_id
- Effect: return audit trail + items + attachments overview

Request envelope (all actions)
```json
{
  "action": "...",
  "context": {
    "yacht_id": "uuid",
    "mode": "prepare|execute"
  },
  "payload": { "...": "..." }
}
```

Signature payload (when required)
```json
{
  "signed_at": "ISO8601",
  "user_id": "uuid",
  "role_at_signing": "captain|manager",
  "signature_type": "pin_totp",
  "signature_hash": "...",
  "reason_code": "optional",
  "notes": "optional"
}
```

Search keywords (examples)
- create_receiving: ["new receiving","receive package","scan invoice"]
- accept_receiving: ["approve invoice","finalize receipt","accept receiving"]
- reject_receiving: ["reject receiving","decline invoice"]

