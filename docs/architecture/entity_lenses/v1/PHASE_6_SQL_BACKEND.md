# Phase 6 — SQL Backend Patterns

Goal: Document → Tests → Code → Verify — backend defines actions, signatures, and RLS; no UI authority.
Lens: Receiving

Insert receiving
```sql
INSERT INTO pms_receiving (
  id, yacht_id, vendor_name, vendor_reference, received_date, status,
  currency, subtotal, tax_total, total, linked_work_order_id, notes,
  properties, created_at
) VALUES (
  gen_random_uuid(), public.get_user_yacht_id(), :vendor_name, :vendor_reference,
  COALESCE(:received_date, current_date), 'draft', :currency, NULL, NULL, NULL,
  :linked_work_order_id, :notes, COALESCE(:properties,'{}'::jsonb), now()
) RETURNING id;

INSERT INTO pms_audit_log (...)
VALUES (
  gen_random_uuid(), public.get_user_yacht_id(), 'receiving', :new_id,
  'create_receiving', auth.uid(), NULL,
  jsonb_build_object('vendor_reference', :vendor_reference), '{}'::jsonb,
  jsonb_build_object('source','lens','lens','receiving','action','create_receiving','entity_id',:new_id,'entity_type','receiving','session_id',:session_id,'ip_address',:ip), now()
);
```

Attach image with comment
```sql
INSERT INTO pms_receiving_documents (id, yacht_id, receiving_id, document_id, doc_type, comment, created_at)
VALUES (
  gen_random_uuid(), public.get_user_yacht_id(), :receiving_id, :document_id, :doc_type, :comment, now()
);

INSERT INTO pms_audit_log (...)
VALUES (..., 'attach_receiving_image_with_comment', '{}'::jsonb,
  jsonb_build_object('source','lens','lens','receiving','action','attach_receiving_image_with_comment','entity_id',:receiving_id,'entity_type','receiving','doc_id',:document_id,'session_id',:session_id,'ip_address',:ip), now());
```

Store extraction (advisory)
```sql
INSERT INTO pms_receiving_extractions (id, yacht_id, receiving_id, source_document_id, payload, created_at)
VALUES (gen_random_uuid(), public.get_user_yacht_id(), :receiving_id, :source_document_id, :payload::jsonb, now());
```

Accept receiving (SIGNED)
```sql
-- prepare: compute totals, validate completeness; no writes
-- execute:
UPDATE pms_receiving
SET status='accepted', subtotal=:subtotal, tax_total=:tax_total, total=:total
WHERE id=:receiving_id AND yacht_id=public.get_user_yacht_id();

INSERT INTO pms_audit_log (
  id, yacht_id, entity_type, entity_id, action, user_id, old_values, new_values, signature, metadata, created_at
) VALUES (
  gen_random_uuid(), public.get_user_yacht_id(), 'receiving', :receiving_id, 'accept_receiving', auth.uid(),
  NULL, jsonb_build_object('total',:total), :signature::jsonb,
  jsonb_build_object('source','lens','lens','receiving','action','accept_receiving','entity_id',:receiving_id,'entity_type','receiving','session_id',:session_id,'ip_address',:ip), now()
);
```

Read: open vs historical faults for equipment card (tie‑in example)
```sql
-- Receiving lens side only references; actual fault query lives in Fault lens
```

Create related link (Show Related)
```sql
INSERT INTO pms_entity_links (
  id, yacht_id, source_entity_type, source_entity_id,
  target_entity_type, target_entity_id, link_type, note, created_by, created_at
) VALUES (
  gen_random_uuid(), public.get_user_yacht_id(), :source_type, :source_id,
  :target_type, :target_id, :link_type, :note, auth.uid(), now()
);
```

