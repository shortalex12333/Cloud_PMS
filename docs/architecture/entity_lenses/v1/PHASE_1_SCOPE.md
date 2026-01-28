# Phase 1 — Scope and Authority

Goal: Document → Tests → Code → Verify — backend defines actions, signatures, and RLS; no UI authority.
Lens: Receiving

Authority & doctrine
- Backend defines and gates all micro‑actions; frontend renders deterministically.
- Prepare/execute: extraction suggests; execution writes; no auto‑mutation.
- One focused entity per action.

Focused entities
- Receiving (header)
- Receiving Item (line)
- Receiving Document (image/PDF link)

Cross‑lens orchestration
- Parts (items link to parts)
- Work Orders (optional linkage — receipts against WO)
- Suppliers/Vendors (matched via extracted fields)
- Inventory (posting later — out of scope v1 write, but link exists)

Equipment card & Show Related interactions
- Receiving records appear in “Show Related” when viewing parts/WO/suppliers; read‑only grouped context with match_reasons.
- No actions in Show Related unless user explicitly invokes add‑related (writes pms_entity_links).

Primary actions (with roles)
- create_receiving (HOD+)
- attach_receiving_image_with_comment (HOD+)
- extract_receiving_candidates (prepare; read‑only)
- update_receiving_fields (HOD+)
- add_receiving_item (HOD+)
- adjust_receiving_item (HOD+)
- link_invoice_document (HOD+)
- accept_receiving (SIGNED: Captain/Manager)
- reject_receiving (HOD+)
- view_receiving_history (Crew+)

Action registry search keywords (examples)
- create_receiving: ["new receiving","receive package","receive invoice"]
- attach_receiving_image_with_comment: ["attach photo","scan invoice","upload image"]
- extract_receiving_candidates: ["extract from image","parse invoice"]
- accept_receiving: ["approve invoice","accept receipt"]
- reject_receiving: ["reject receiving","decline invoice"]

Prepare/Execute flows
- extract_receiving_candidates
  - prepare only: run OCR/parse; return candidates + confidence; flag low confidence
  - never writes; propose updates to `receiving` and `receiving_items`
- accept_receiving
  - prepare: validate completeness (reviewed lines), compute totals, require signature payload
  - execute: mark status=accepted; write signed audit; freeze values

