# DB Field Classification — Receiving

Goal: Document → Tests → Code → Verify — backend defines actions, signatures, and RLS; no UI authority.
Lens: Receiving

Classifications
- REQUIRED: caller must supply
- OPTIONAL: caller may supply; validated if present
- BACKEND_AUTO: set by backend/trigger; caller cannot override
- CONTEXT: set from context (e.g., yacht_id), not payload

pms_receiving
- id: BACKEND_AUTO
- yacht_id: BACKEND_AUTO/CONTEXT
- vendor_name: OPTIONAL
- vendor_reference: OPTIONAL
- received_date: OPTIONAL (default today)
- status: BACKEND_AUTO (state machine)
- currency: OPTIONAL
- subtotal: BACKEND_AUTO (set at acceptance)
- tax_total: BACKEND_AUTO
- total: BACKEND_AUTO
- linked_work_order_id: OPTIONAL
- notes: OPTIONAL
- properties: OPTIONAL
- created_at: BACKEND_AUTO

pms_receiving_items
- id: BACKEND_AUTO
- yacht_id: BACKEND_AUTO/CONTEXT
- receiving_id: REQUIRED (or resolved)
- part_id: OPTIONAL
- description: OPTIONAL (REQUIRED if part_id absent)
- quantity_expected: OPTIONAL
- quantity_received: OPTIONAL (default 0; >=0)
- unit_price: OPTIONAL
- currency: OPTIONAL
- properties: OPTIONAL
- created_at: BACKEND_AUTO

pms_receiving_documents
- id: BACKEND_AUTO
- yacht_id: BACKEND_AUTO/CONTEXT
- receiving_id: REQUIRED
- document_id: REQUIRED
- doc_type: OPTIONAL ('invoice','packing_slip','photo')
- comment: OPTIONAL
- created_at: BACKEND_AUTO

pms_receiving_extractions
- id: BACKEND_AUTO
- yacht_id: BACKEND_AUTO/CONTEXT
- receiving_id: REQUIRED
- source_document_id: REQUIRED
- payload: BACKEND_AUTO (from prepare output)
- created_at: BACKEND_AUTO

