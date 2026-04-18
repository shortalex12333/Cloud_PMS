### complete picture of handover backend

  ---
  9 Tables — How They Link Together

  USER CLICKS "ADD TO HANDOVER"
           │
           ▼
  ┌─────────────────┐
  │ handover_items   │  ← The raw tagged items. One row per "Add to Handover" click.
  │                  │    Lives here until exported.
  └────────┬────────┘
           │ User clicks "Export"
           │ Backend fetches items, sends to LLM microservice
           ▼
  ┌─────────────────┐
  │ handover_entries │  ← Truth seeds. LLM-merged summaries written here.
  │                  │    IMMUTABLE — no delete policy. Compliance audit trail.
  └────────┬────────┘
           │ Backend creates the draft document structure
           ▼
  ┌─────────────────┐       ┌──────────────────────────┐       ┌────────────────────────┐
  │ handover_drafts  │──1:N──│ handover_draft_sections   │──1:N──│ handover_draft_items    │
  │                  │       │                           │       │                         │
  │ The document     │       │ Department groups         │       │ Individual items with   │
  │ container.       │       │ (Engineering, Deck, etc.) │       │ LLM summary text.       │
  │ Has state machine│       │ Ordered by relevance      │       │ Each has is_critical,   │
  │ DRAFT→SIGNED→    │       │ to user's role.           │       │ action_summary,         │
  │ EXPORTED         │       │                           │       │ entity_url for linking.  │
  └────────┬────────┘       └───────────────────────────┘       └─────────────────────────┘
           │
           │ User reviews, edits, signs
           ▼
  ┌─────────────────┐       ┌──────────────────────────┐
  │ handover_exports │       │ handover_draft_edits     │
  │                  │       │                           │
  │ The final export │       │ Audit trail of every      │
  │ record. Has:     │       │ text change the user made │
  │ - storage URLs   │       │ before signing.           │
  │ - signatures     │       │ WHO changed WHAT, WHEN.   │
  │ - edited_content │       └───────────────────────────┘
  │ - review_status  │
  │ - document_hash  │
  └────────┬────────┘
           │
           │ Both parties sign
           ▼
  ┌──────────────────────────┐       ┌──────────────────────────┐
  │ (signatures live on       │       │ handover_sources          │
  │  handover_exports above)  │       │                           │
  │                           │       │ External material linked  │
  │ user_signature / user_    │       │ to entries (emails, docs).│
  │ signed_at, hod_signature /│       │ Future use — email        │
  │ hod_signed_at, incoming_  │       │ integration.              │
  │ signature / incoming_     │       └──────────────────────────┘
  │ signed_at /incoming_user_ │
  │ id. document_hash frozen  │
  │ at sign time.             │
  └──────────────────────────┘

  NOTE: The earlier `handover_signoffs` table (separate dual-signature row) is DEPRECATED.
  Not created by any migration, not written by any handler, not read by any route.
  Kept here only so searches hit the deprecation note — do not reference in new code.

  Table-by-Table for a New Engineer

  1. handover_items (33 columns) — The Input

  What: Raw items tagged by crew from anywhere in CelesteOS ("Add to Handover" button on faults, work orders, equipment, parts, documents).

  Key columns for UX:

  ┌─────────────────┬─────────┬─────────────────────────────────────────────────────────────────────────────────┐
  │     Column      │  Type   │                                   UX Purpose                                    │
  ├─────────────────┼─────────┼─────────────────────────────────────────────────────────────────────────────────┤
  │ summary         │ text    │ The note the crew member wrote or the system auto-generated                     │
  ├─────────────────┼─────────┼─────────────────────────────────────────────────────────────────────────────────┤
  │ entity_type     │ varchar │ What kind of thing: fault, work_order, equipment, part, document, note, general │
  ├─────────────────┼─────────┼─────────────────────────────────────────────────────────────────────────────────┤
  │ entity_id       │ uuid    │ Links back to the actual fault/WO/equipment record                              │
  ├─────────────────┼─────────┼─────────────────────────────────────────────────────────────────────────────────┤
  │ entity_url      │ text    │ Pre-built URL path for deep linking (e.g., /faults/abc123)                      │
  ├─────────────────┼─────────┼─────────────────────────────────────────────────────────────────────────────────┤
  │ is_critical     │ bool    │ Crew flagged this as critical                                                   │
  ├─────────────────┼─────────┼─────────────────────────────────────────────────────────────────────────────────┤
  │ requires_action │ bool    │ This needs someone to do something                                              │
  ├─────────────────┼─────────┼─────────────────────────────────────────────────────────────────────────────────┤
  │ action_summary  │ text    │ What specifically needs doing                                                   │
  ├─────────────────┼─────────┼─────────────────────────────────────────────────────────────────────────────────┤
  │ category        │ text    │ urgent, in_progress, completed, watch, fyi                                      │
  ├─────────────────┼─────────┼─────────────────────────────────────────────────────────────────────────────────┤
  │ priority        │ int     │ 0=low, 1=normal, 2=high, 3=critical                                             │
  ├─────────────────┼─────────┼─────────────────────────────────────────────────────────────────────────────────┤
  │ section         │ varchar │ Department: Engineering, Deck, Interior, etc.                                   │
  ├─────────────────┼─────────┼─────────────────────────────────────────────────────────────────────────────────┤
  │ added_by        │ uuid    │ → auth_users_profiles.id                                                        │
  ├─────────────────┼─────────┼─────────────────────────────────────────────────────────────────────────────────┤
  │ export_status   │ text    │ pending → exported (after export runs)                                          │
  ├─────────────────┼─────────┼─────────────────────────────────────────────────────────────────────────────────┤
  │ status          │ varchar │ pending → acknowledged → completed → deferred                                   │
  └─────────────────┴─────────┴─────────────────────────────────────────────────────────────────────────────────┘

  Lifecycle: Created on "Add to Handover" → lives here during rotation → marked exported when the export runs → stays in DB permanently for
  audit.

  ---
  2. handover_entries (22 columns) — The Truth Seeds

  What: LLM-processed versions of items. Created by the microservice during export. IMMUTABLE — no delete allowed.

  Key columns for UX:

  ┌─────────────────────┬──────┬──────────────────────────────────────────────────────────┐
  │       Column        │ Type │                        UX Purpose                        │
  ├─────────────────────┼──────┼──────────────────────────────────────────────────────────┤
  │ narrative_text      │ text │ The LLM-written professional summary (NOT editable here) │
  ├─────────────────────┼──────┼──────────────────────────────────────────────────────────┤
  │ summary_text        │ text │ Same as narrative (backup copy)                          │
  ├─────────────────────┼──────┼──────────────────────────────────────────────────────────┤
  │ presentation_bucket │ text │ Department: Command, Engineering, Deck, Interior, etc.   │
  ├─────────────────────┼──────┼──────────────────────────────────────────────────────────┤
  │ primary_domain      │ text │ Domain code: ENG-03, DECK-01, CMD-01, etc.               │
  ├─────────────────────┼──────┼──────────────────────────────────────────────────────────┤
  │ is_critical         │ bool │ Inherited from source item                               │
  ├─────────────────────┼──────┼──────────────────────────────────────────────────────────┤
  │ source_entity_type  │ text │ What the original item was (fault, work_order, etc.)     │
  ├─────────────────────┼──────┼──────────────────────────────────────────────────────────┤
  │ source_entity_id    │ uuid │ Links back to the original entity                        │
  ├─────────────────────┼──────┼──────────────────────────────────────────────────────────┤
  │ status              │ text │ candidate → included → suppressed → resolved             │
  ├─────────────────────┼──────┼──────────────────────────────────────────────────────────┤
  │ created_by_user_id  │ uuid │ → auth_users_profiles.id                                 │
  └─────────────────────┴──────┴──────────────────────────────────────────────────────────┘

  Compliance rule: These are never overwritten. If the LLM summary is wrong, the user edits it in the export (which creates a
  handover_draft_edits audit record), not here.

  ---
  3. handover_drafts (16 columns) — The Document

  What: One row per handover document. Container for sections and items.

  Key columns for UX:

  ┌───────────────────────────┬─────────────┬──────────────────────────────────────────────────────────┐
  │          Column           │    Type     │                        UX Purpose                        │
  ├───────────────────────────┼─────────────┼──────────────────────────────────────────────────────────┤
  │ state                     │ text        │ DRAFT → IN_REVIEW → ACCEPTED → SIGNED → EXPORTED         │
  ├───────────────────────────┼─────────────┼──────────────────────────────────────────────────────────┤
  │ title                     │ text        │ "Technical Handover Report - 24 Mar 2026"                │
  ├───────────────────────────┼─────────────┼──────────────────────────────────────────────────────────┤
  │ period_start / period_end │ timestamptz │ The rotation period this handover covers                 │
  ├───────────────────────────┼─────────────┼──────────────────────────────────────────────────────────┤
  │ department                │ text        │ Primary department (or null for all-department handover) │
  ├───────────────────────────┼─────────────┼──────────────────────────────────────────────────────────┤
  │ generation_method         │ text        │ manual, scheduled, ai_assisted                           │
  ├───────────────────────────┼─────────────┼──────────────────────────────────────────────────────────┤
  │ total_entries             │ int         │ Number of items in this handover                         │
  ├───────────────────────────┼─────────────┼──────────────────────────────────────────────────────────┤
  │ critical_entries          │ int         │ Number of critical items                                 │
  ├───────────────────────────┼─────────────┼──────────────────────────────────────────────────────────┤
  │ generated_by_user_id      │ uuid        │ → auth_users_profiles.id                                 │
  └───────────────────────────┴─────────────┴──────────────────────────────────────────────────────────┘

  State machine: Only DRAFT and IN_REVIEW can be deleted. SIGNED and EXPORTED are permanent.

  ---
  4. handover_draft_sections (8 columns) — Department Groups

  What: One row per department section within a draft. Ordered by relevance to the user's role.

  ┌────────────────┬──────┬──────────────────────────────────────────────────────────────────┐
  │     Column     │ Type │                            UX Purpose                            │
  ├────────────────┼──────┼──────────────────────────────────────────────────────────────────┤
  │ bucket_name    │ text │ Department: Command, Engineering, Deck, Interior, ETO_AVIT, etc. │
  ├────────────────┼──────┼──────────────────────────────────────────────────────────────────┤
  │ display_title  │ text │ Human-readable title (can override bucket_name)                  │
  ├────────────────┼──────┼──────────────────────────────────────────────────────────────────┤
  │ section_order  │ int  │ Display order (1=first, user's own department)                   │
  ├────────────────┼──────┼──────────────────────────────────────────────────────────────────┤
  │ item_count     │ int  │ How many items in this section                                   │
  ├────────────────┼──────┼──────────────────────────────────────────────────────────────────┤
  │ critical_count │ int  │ How many critical items                                          │
  └────────────────┴──────┴──────────────────────────────────────────────────────────────────┘

  FK: draft_id → handover_drafts.id (CASCADE delete)

  UNIQUE: (draft_id, bucket_name) — one section per department per draft.

  ---
  5. handover_draft_items (20 columns) — The Content

  What: Individual items within sections. This is what the user reads, edits, and signs off on.

  Key columns for UX:

  ┌──────────────────┬───────┬────────────────────────────────────────────────────────────────┐
  │      Column      │ Type  │                           UX Purpose                           │
  ├──────────────────┼───────┼────────────────────────────────────────────────────────────────┤
  │ summary_text     │ text  │ The LLM-written professional summary — THIS IS WHAT USERS READ │
  ├──────────────────┼───────┼────────────────────────────────────────────────────────────────┤
  │ section_bucket   │ text  │ Which department section this belongs to                       │
  ├──────────────────┼───────┼────────────────────────────────────────────────────────────────┤
  │ domain_code      │ text  │ Technical domain code (ENG-03, DECK-01, etc.)                  │
  ├──────────────────┼───────┼────────────────────────────────────────────────────────────────┤
  │ is_critical      │ bool  │ Red flag — only true if explicitly tagged in source DB         │
  ├──────────────────┼───────┼────────────────────────────────────────────────────────────────┤
  │ requires_action  │ bool  │ Show action indicator                                          │
  ├──────────────────┼───────┼────────────────────────────────────────────────────────────────┤
  │ action_summary   │ text  │ Multi-line action items (show actions box only if >1 line)     │
  ├──────────────────┼───────┼────────────────────────────────────────────────────────────────┤
  │ item_order       │ int   │ Display order within section                                   │
  ├──────────────────┼───────┼────────────────────────────────────────────────────────────────┤
  │ entity_url       │ text  │ Deep link to source entity in CelesteOS                        │
  ├──────────────────┼───────┼────────────────────────────────────────────────────────────────┤
  │ metadata         │ jsonb │ Flexible store: {title: "...", email_message_id: "..."}        │
  ├──────────────────┼───────┼────────────────────────────────────────────────────────────────┤
  │ confidence_level │ text  │ LOW, MEDIUM, HIGH — how confident the LLM was                  │
  └──────────────────┴───────┴────────────────────────────────────────────────────────────────┘

  FK: draft_id → handover_drafts.id, section_id → handover_draft_sections.id

  ---
  6. handover_exports (37 columns) — The Final Record

  What: The export record with storage URLs, signatures, and the editable JSON. This is the central table for the review/sign/countersign flow.

  Key columns for UX:

  ┌──────────────────────┬─────────────┬─────────────────────────────────────────────────────────────────────────┐
  │        Column        │    Type     │                               UX Purpose                                │
  ├──────────────────────┼─────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ original_storage_url │ text        │ Path to AI-generated HTML in Supabase Storage (Bucket 1, immutable)     │
  ├──────────────────────┼─────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ signed_storage_url   │ text        │ Path to user-signed HTML (Bucket 2, created on submit)                  │
  ├──────────────────────┼─────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ edited_content       │ jsonb       │ The editable JSON structure — {sections: [{title, items: [{content}]}]} │
  ├──────────────────────┼─────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ review_status        │ text        │ pending_review → pending_hod_signature → complete                       │
  ├──────────────────────┼─────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ status               │ text        │ draft → pending_outgoing → pending_incoming → completed                 │
  ├──────────────────────┼─────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ user_signature       │ jsonb       │ {image_base64, signed_at, signer_name, signer_id}                       │
  ├──────────────────────┼─────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ hod_signature        │ jsonb       │ Same structure for HOD countersign                                      │
  ├──────────────────────┼─────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ user_signed_at       │ timestamptz │ When user signed                                                        │
  ├──────────────────────┼─────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ hod_signed_at        │ timestamptz │ When HOD countersigned                                                  │
  ├──────────────────────┼─────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ document_hash        │ text        │ SHA-256 of the HTML — tamper evidence                                   │
  ├──────────────────────┼─────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ export_type          │ text        │ pdf, html, email                                                        │
  ├──────────────────────┼─────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ exported_by_user_id  │ uuid        │ Who triggered the export                                                │
  ├──────────────────────┼─────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ department           │ text        │ Department filter used                                                  │
  ├──────────────────────┼─────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ signoff_complete     │ bool        │ Both signatures present                                                 │
  └──────────────────────┴─────────────┴─────────────────────────────────────────────────────────────────────────┘

  The edit/sign flow lives here:
  1. Export creates record → review_status = 'pending_review', edited_content has sections JSON
  2. User edits → edited_content updated via save-draft endpoint
  3. User signs → user_signature set, signed_storage_url created, review_status = 'pending_hod_signature'
  4. HOD countersigns → hod_signature set, review_status = 'complete'

  ---
  7. handover_draft_edits (11 columns) — Edit Audit Trail

  What: Every text change the user makes before signing. WHO changed WHAT text to WHAT, and WHEN.

  ┌───────────────────┬──────┬──────────────────────────────────────────┐
  │      Column       │ Type │                UX Purpose                │
  ├───────────────────┼──────┼──────────────────────────────────────────┤
  │ draft_item_id     │ uuid │ Which item was edited                    │
  ├───────────────────┼──────┼──────────────────────────────────────────┤
  │ edited_by_user_id │ uuid │ Who edited                               │
  ├───────────────────┼──────┼──────────────────────────────────────────┤
  │ field_edited      │ text │ Which field (default: summary_text)      │
  ├───────────────────┼──────┼──────────────────────────────────────────┤
  │ original_text     │ text │ Before                                   │
  ├───────────────────┼──────┼──────────────────────────────────────────┤
  │ edited_text       │ text │ After                                    │
  ├───────────────────┼──────┼──────────────────────────────────────────┤
  │ edit_reason       │ text │ Why (optional)                           │
  ├───────────────────┼──────┼──────────────────────────────────────────┤
  │ edit_type         │ text │ modification, addition, removal, reorder │
  └───────────────────┴──────┴──────────────────────────────────────────┘

  ---
  8. handover_signoffs — DEPRECATED (signatures now live on handover_exports)

  Single source of truth for all three signatures (outgoing, HOD countersign, incoming
  acknowledgment) is now the `handover_exports` row itself. See section 6 above —
  columns `user_signature / user_signed_at`, `hod_signature / hod_signed_at`,
  `incoming_signature / incoming_signed_at / incoming_user_id /
  incoming_acknowledged_critical / incoming_comments / incoming_role`, plus
  `signoff_complete` and `document_hash`.

  The `handover_signoffs` table existed in an earlier dual-row design (one row per
  draft, outgoing_user_id + incoming_user_id on the same row). It was superseded before
  MVP ship. Current state on TENANT DB:

    - Not created by any migration in this repo
    - Not written by any handler in `pipeline-core`
    - Not read by any route or view used by the app

  Kept as a named deprecation here so searches against historical docs land on this
  note rather than a live-looking schema. Do not reference in new code. A separate
  doc cleanup will remove the last mentions once downstream tooling is confirmed clear.

  ---
  9. handover_sources (16 columns) — External Material

  What: Maps external source material (emails, documents) to handover entries. Currently used for future email integration.

  ┌────────────────┬───────┬──────────────────────────────────────────────────────────┐
  │     Column     │ Type  │                        UX Purpose                        │
  ├────────────────┼───────┼──────────────────────────────────────────────────────────┤
  │ source_type    │ text  │ email, document, work_order, fault, message, api         │
  ├────────────────┼───────┼──────────────────────────────────────────────────────────┤
  │ external_id    │ text  │ e.g., Microsoft Graph message ID                         │
  ├────────────────┼───────┼──────────────────────────────────────────────────────────┤
  │ subject        │ text  │ Email subject line                                       │
  ├────────────────┼───────┼──────────────────────────────────────────────────────────┤
  │ classification │ jsonb │ AI classification result {category, summary, confidence} │
  └────────────────┴───────┴──────────────────────────────────────────────────────────┘

  Status: Schema exists, tables empty. Email integration is shelved for Phase 2.

  ---
  Supporting Tables (Not Handover-Specific)

  ┌─────────────────────┬───────────────────────────────────────────────────────────────────────────────┐
  │        Table        │                               Role in Handover                                │
  ├─────────────────────┼───────────────────────────────────────────────────────────────────────────────┤
  │ auth_users_profiles │ User name + email lookup for signatures, "Prepared by"                        │
  ├─────────────────────┼───────────────────────────────────────────────────────────────────────────────┤
  │ auth_users_roles    │ Role + department for filtering (captain sees all, engineer sees engineering) │
  ├─────────────────────┼───────────────────────────────────────────────────────────────────────────────┤
  │ yacht_registry      │ Yacht name for cover page (instead of UUID)                                   │
  ├─────────────────────┼───────────────────────────────────────────────────────────────────────────────┤
  │ ledger_events       │ Notification: "Your handover export is ready for review"                      │
  ├─────────────────────┼───────────────────────────────────────────────────────────────────────────────┤
  │ pms_audit_log       │ Compliance audit trail entry                                                  │
  ├─────────────────────┼───────────────────────────────────────────────────────────────────────────────┤
  │ search_index        │ Projection worker indexes completed exports here for full-text search         │
  └─────────────────────┴───────────────────────────────────────────────────────────────────────────────┘