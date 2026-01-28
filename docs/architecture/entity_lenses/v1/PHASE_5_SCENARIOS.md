# Phase 5 — Scenarios and Journeys

Goal: Document → Tests → Code → Verify — backend defines actions, signatures, and RLS; no UI authority.
Lens: Receiving

Personas
- Crew (view only), Chief Engineer (HOD), Chief Officer (HOD), Purser (HOD), Captain, Manager

Scenarios (12)
1) Capture invoice photo and extract candidates
- Actor: Purser
- Flow: create_receiving → attach_receiving_image_with_comment → extract_receiving_candidates (prepare) → update_receiving_fields → add_receiving_item → accept_receiving (SIGNED by captain/manager)
- Success: image stored; extraction advisory saved; user edits; signed acceptance; audit complete
- Errors: 400 invalid path; 403 crew mutation; 404 receiving not found

2) Receive package with packing slip (no PO)
- Actor: Chief Officer
- Flow: create_receiving → attach_receiving_image_with_comment (packing slip) → add_receiving_item descriptions → accept_receiving (SIGNED)
- Success: accepted; audit signed
- Errors: 400 missing minimum item; 403 role

3) Partial receipt vs expected
- Actor: Chief Engineer
- Flow: add_receiving_item with quantity_expected > quantity_received → status in_review → accept later when reconciled
- Success: acceptance only when explicitly executed; no auto‑mutation

4) Reject receiving due to mismatch
- Actor: HOD
- Flow: reject_receiving(reason)
- Success: status='rejected'; audit reason recorded

5) Attach PDF invoice and link vendor reference
- Actor: Purser
- Flow: link_invoice_document(doc_metadata for PDF) → update_receiving_fields(vendor_reference)
- Success: linked; metadata present

6) Low confidence extraction requires manual edits
- Actor: Purser
- Flow: extract_receiving_candidates (prepare) → user reviews low confidence flags → update_receiving_fields
- Success: no writes until update; advisory retained

7) Role denial for crew mutation
- Actor: Crew
- Flow: attempt update_receiving_fields
- Error: 403

8) Cross‑yacht isolation
- Actor: HOD from Yacht B
- Flow: read receiving of Yacht A
- Success: 0 rows

9) Show Related curation
- Actor: HOD
- Flow: open Show Related on receiving → add related WO or part via selection mode → pms_entity_links write
- Success: links saved; future panels show improved context

10) Accept receiving (SIGNED) without signature
- Actor: Captain
- Flow: accept_receiving execute without signature payload
- Error: 403; signature required

11) Storage path validation
- Actor: HOD
- Flow: attach_receiving_image_with_comment with storage_path prefixed "documents/"
- Error: 400 invalid path

12) Equipment tie‑in via Show Related
- Actor: HOD
- Flow: from WO related to equipment, Show Related displays receiving of related parts; read‑only
- Success: deterministic; no actions invented

Edge policies
- Extraction is advisory; acceptance is explicit and signed; storage path must be yacht‑scoped; RLS deny‑by‑default.

