# Phase 8 — Blockers, Migrations, Acceptance

Goal: Document → Tests → Code → Verify — backend defines actions, signatures, and RLS; no UI authority.
Lens: Receiving

Blockers
- B1: RLS enable + policies on receiving tables
- B2: Storage/doc_metadata policies for documents + pms-receiving-images
- B3: Status checks on pms_receiving; quantity_received >= 0
- B4: Indexes for performance on vendor_reference, status
- B5: Helpers presence (is_hod, is_manager, get_user_yacht_id)
- B6: Acceptance tests with 15 JWTs

Migration set (ordered)
1) 20260127_101_helpers_if_missing.sql
2) 20260127_102_receiving_tables.sql  -- pms_receiving, pms_receiving_items, pms_receiving_documents, pms_receiving_extractions
3) 20260127_103_receiving_checks.sql  -- status enum, quantity checks
4) 20260127_104_receiving_rls.sql     -- enable + policies per Phase 7
5) 20260127_105_receiving_indexes.sql -- common indices
6) 20260127_111_documents_storage_policies.sql     -- storage policies for documents bucket
7) 20260127_112_receiving_images_storage_policies.sql -- storage policies for pms-receiving-images bucket
8) 20260127_113_doc_metadata_write_rls.sql

Acceptance (post‑deploy checks)
- RLS enabled: pms_receiving*, pms_entity_links, doc_metadata
- Storage policies: documents + pms-receiving-images present
- Single‑tenant assertions
- REST acceptance (15 JWTs):
  - Crew denied mutations; HOD allowed
  - extract_receiving_candidates returns advisory (no writes)
  - accept_receiving without signature → 403; with signature → 200
  - Invalid storage_path with "documents/" prefix → 400; canonical path accepted
  - Reject receiving sets status='rejected'

