# Phase 7 — RLS Matrix and Verification

Goal: Document → Tests → Code → Verify — backend defines actions, signatures, and RLS; no UI authority.
Lens: Receiving

Helpers
- public.is_hod(auth.uid())
- public.is_manager(auth.uid())
- public.get_user_yacht_id()

Policies
1) pms_receiving
- SELECT USING (yacht_id = public.get_user_yacht_id())
- INSERT/UPDATE WITH CHECK (yacht_id = public.get_user_yacht_id() AND public.is_hod(auth.uid()))

2) pms_receiving_items
- SELECT USING (yacht_id = public.get_user_yacht_id())
- INSERT/UPDATE WITH CHECK (yacht_id = public.get_user_yacht_id() AND public.is_hod(auth.uid()))

3) pms_receiving_documents
- SELECT USING (yacht_id = public.get_user_yacht_id())
- INSERT WITH CHECK (yacht_id = public.get_user_yacht_id() AND public.is_hod(auth.uid()))

4) pms_receiving_extractions
- SELECT USING (yacht_id = public.get_user_yacht_id())
- INSERT WITH CHECK (yacht_id = public.get_user_yacht_id() AND public.is_hod(auth.uid()))

5) pms_entity_links
- SELECT USING (yacht_id = public.get_user_yacht_id())
- INSERT WITH CHECK (yacht_id = public.get_user_yacht_id() AND public.is_hod(auth.uid()))

6) Storage/doc_metadata
- documents bucket and pms-receiving-images bucket paths start with `{yacht_id}/receiving/...`
- storage.objects policies present: hod_insert_yacht_documents, hod_update_yacht_documents, manager_delete_yacht_documents
- doc_metadata policies present: crew_insert_doc_metadata, hod_update_doc_metadata, manager_delete_doc_metadata

Verification queries
```sql
SELECT relname, relrowsecurity FROM pg_class
WHERE relname IN (
  'pms_receiving','pms_receiving_items','pms_receiving_documents','pms_receiving_extractions','pms_entity_links','doc_metadata'
);

SELECT tablename, policyname FROM pg_policies
WHERE tablename IN (
  'pms_receiving','pms_receiving_items','pms_receiving_documents','pms_receiving_extractions','pms_entity_links'
) ORDER BY tablename, policyname;

SELECT policyname FROM pg_policies
WHERE schemaname='storage' AND tablename='objects'
  AND policyname IN ('hod_insert_yacht_documents','hod_update_yacht_documents','manager_delete_yacht_documents');

SELECT policyname FROM pg_policies
WHERE tablename='doc_metadata'
  AND policyname IN ('crew_insert_doc_metadata','hod_update_doc_metadata','manager_delete_doc_metadata');
```

