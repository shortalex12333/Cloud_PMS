# Phase 2 — DB Truth

Goal: Document → Tests → Code → Verify — backend defines actions, signatures, and RLS; no UI authority.
Lens: Receiving

Canonical helpers (required)
- public.is_hod(auth.uid())
- public.is_manager(auth.uid())
- public.get_user_yacht_id()

Tables
1) pms_receiving (header)
- id uuid PK
- yacht_id uuid NOT NULL
- vendor_name text NULL
- vendor_reference text NULL  -- invoice number, AWB, packing slip
- received_date date NOT NULL DEFAULT current_date
- status text NOT NULL DEFAULT 'draft' CHECK in ('draft','in_review','accepted','rejected')
- currency text NULL
- subtotal numeric(14,2) NULL
- tax_total numeric(14,2) NULL
- total numeric(14,2) NULL
- linked_work_order_id uuid NULL
- notes text NULL
- properties jsonb NULL
- created_at timestamptz NOT NULL DEFAULT now()

Indices: (yacht_id, received_date DESC), (yacht_id, status), (yacht_id, vendor_reference)

2) pms_receiving_items (lines)
- id uuid PK
- yacht_id uuid NOT NULL
- receiving_id uuid NOT NULL (FK → pms_receiving.id ON DELETE CASCADE)
- part_id uuid NULL
- description text NULL
- quantity_expected numeric(12,2) NULL
- quantity_received numeric(12,2) NOT NULL DEFAULT 0 CHECK (quantity_received >= 0)
- unit_price numeric(14,4) NULL
- currency text NULL
- properties jsonb NULL
- created_at timestamptz NOT NULL DEFAULT now()

Indices: (yacht_id, receiving_id), (yacht_id, part_id)

3) pms_receiving_documents (photos/PDFs linked to receiving)
- id uuid PK
- yacht_id uuid NOT NULL
- receiving_id uuid NOT NULL (FK → pms_receiving.id ON DELETE CASCADE)
- document_id uuid NOT NULL (FK → doc_metadata.id)
- doc_type text NULL  -- 'invoice','packing_slip','photo'
- comment text NULL  -- inline note about this attachment
- created_at timestamptz NOT NULL DEFAULT now()

Indices: (yacht_id, receiving_id), (yacht_id, doc_type)

4) pms_receiving_extractions (advisory extraction results; non‑authoritative)
- id uuid PK
- yacht_id uuid NOT NULL
- receiving_id uuid NOT NULL (FK → pms_receiving.id ON DELETE CASCADE)
- source_document_id uuid NOT NULL (FK → doc_metadata.id)
- payload jsonb NOT NULL  -- extracted fields, confidences
- created_at timestamptz NOT NULL DEFAULT now()

Notes:
- Keep extraction advisory; handlers must not auto‑apply

5) pms_entity_links (reuse for Show Related)
- As defined in Equipment lens; links between receiving↔WO↔parts↔suppliers↔docs

Storage
- Bucket `documents` for PDFs; storage_path: `{yacht_id}/receiving/{receiving_id}/{filename}`
- Bucket `pms-receiving-images` for photos; path: `{yacht_id}/receiving/{receiving_id}/{filename}`
- Do NOT prefix storage_path with `documents/`

Audit
- All mutations write to `pms_audit_log` with `entity_type='receiving'`; signature NOT NULL ({} if not signed)
- Required metadata: source='lens', lens='receiving', action, entity_id, entity_type, wo_id?, vendor_reference?, session_id, ip_address

Verification queries
- RLS enabled on all receiving tables + doc_metadata + storage policies present
- Single‑tenant assertions on yacht_id across receiving tables

