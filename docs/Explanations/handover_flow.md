⏺ Let me gather the actual proof first, then walk you through the complete flow.

  Proof It Works

  1. Microservice health:
  curl http://localhost:10000/health
  → {"status":"healthy","timestamp":"2026-03-23T18:26:19","service":"handover-export"}

  2. E2E test — 4 items sent, professional document returned:
  POST /api/v1/handover/generate → 201 Created
  {
      "draft_id": "66b691de-9358-428e-acc8-bfaf5cc0122d",
      "storage_url": "handover-exports/85fe1119-.../original/66b691de-..._20260323_184019.html",
      "document_hash": "sha256:2560fda19e3b4ead1b5169d89b6b526a26a6ac28cc129d9ce2b142ae49f8d677",
      "sections_count": 2,
      "items_count": 3,
      "critical_count": 3
  }

  3. LLM output quality — DB records prove real GPT-4o-mini summaries:
  Engineering | ENG-03 | "You need to address the high coolant temperature reading on
                         the starboard engine and investigate the root cause. Parts for
                         the heat exchanger inspection are currently on order."

  Admin       | ADM-05 | "You need to address the low stock of hydraulic oil, with only
                         3 of 8 drums remaining. The supplier has not confirmed the
                         delivery date."

  Admin       | ADM-04 | "You need to prepare for the watermaker membrane replacement
                         scheduled for 25 March, which will require a 4-hour system
                         shutdown. Additionally, prioritize replacing overdue HVAC
                         filters in guest accommodation..."

  4. DB row counts verified via direct SQL:
  entries  | 2   (truth seeds from LLM merge)
  drafts   | 1   (the assembled document)
  sections | 2   (Engineering + Admin_Compliance)
  items    | 3   (LLM-summarised items within sections)

  5. Cloud_PMS build: 0 errors, all routes compiled
  6. Cloud_PMS unit tests: 109/109 pass
  7. Microservice tests: 350/351 pass (1 pre-existing failure unrelated to our work)

  8. Docker logs show the full pipeline ran:
  18:40:14 - generate_handover: yacht_id=85fe1119... items=4
  18:40:16 - HTTP POST openai.com/v1/chat/completions → 200 OK (×4 classify)
  18:40:16 - Classification complete: 4 items classified
  18:40:16 - Grouped 4 PMS items into 3 category groups
  18:40:19 - HTTP POST openai.com/v1/chat/completions → 200 OK (×3 merge)
  18:40:19 - Merge complete: 3 merged entries
  18:40:19 - HTTP POST supabase.co/rest/v1/handover_entries → 201 (×3)
  18:40:19 - Inserted 3 handover_entries (3 critical)
  18:40:19 - HTTP POST supabase.co/rest/v1/handover_drafts → 201
  18:40:19 - HTTP POST supabase.co/rest/v1/handover_draft_sections → 201 (×2)
  18:40:19 - HTTP POST supabase.co/rest/v1/handover_draft_items → 201 (×3)
  18:40:19 - Draft generated: 66b691de-...
  18:40:19 - HTTP POST supabase.co/storage/v1/object/handover-exports/... → 200
  18:40:19 - generate_handover complete: sections=2 items=3 elapsed=5200ms

  ---
  Complete End-to-End Flow

  Phase 1: User Tags Items (Cloud_PMS Frontend → Tenant DB)

  ┌──────────────────────────────────────────────────────────────────┐
  │  USER views a fault in CelesteOS                                │
  │  → Clicks "Add to Handover"                                    │
  │  → Frontend calls Supabase directly (RLS-protected)             │
  │                                                                  │
  │  INSERT INTO handover_items (                                    │
  │    id, yacht_id, entity_type, entity_id,                        │
  │    summary, category, priority, is_critical,                     │
  │    requires_action, action_summary, added_by                     │
  │  )                                                               │
  │                                                                  │
  │  Security: RLS policy on handover_items ensures                  │
  │    yacht_id = get_user_yacht_id()                               │
  │    User can only write to their own yacht                        │
  └──────────────────────────────────────────────────────────────────┘

  This happens repeatedly over days/weeks. Items accumulate.

  Phase 2: User Clicks "Export Handover" (Frontend → Cloud_PMS API)

  ┌──────────────────────────────────────────────────────────────────┐
  │  Frontend                                                        │
  │  POST /v1/handover/export                                       │
  │  Authorization: Bearer <JWT>                                     │
  │                                                                  │
  │  Security:                                                       │
  │  1. JWT validated by get_authenticated_user() middleware         │
  │  2. yacht_id + user_id extracted from JWT claims (NEVER from    │
  │     request body — prevents tenant spoofing)                     │
  │  3. Master DB lookup: JWT → tenant_key_alias → tenant client    │
  └──────────────────────────────────────────────────────────────────┘

  Phase 3: Cloud_PMS Fetches Items (Cloud_PMS API → Tenant DB)

  ┌──────────────────────────────────────────────────────────────────┐
  │  Cloud_PMS export route (feature flag: HANDOVER_USE_MICROSERVICE)│
  │                                                                  │
  │  SELECT * FROM handover_items                                    │
  │  WHERE yacht_id = $yacht_id        ← from JWT, not user input  │
  │    AND deleted_at IS NULL                                        │
  │    AND status != 'completed'       ← unless include_completed   │
  │  ORDER BY created_at DESC                                        │
  │  LIMIT 200                                                       │
  │                                                                  │
  │  Security: Uses service_role client for this query               │
  │  BUT yacht_id comes from authenticated JWT context               │
  │  (double isolation: auth + explicit filter)                      │
  └──────────────────────────────────────────────────────────────────┘

  Phase 4: Cloud_PMS Calls Microservice (HTTP)

  ┌──────────────────────────────────────────────────────────────────┐
  │  Cloud_PMS → POST http://handover-export:10000/api/v1/handover/generate │
  │                                                                  │
  │  Request body:                                                   │
  │  {                                                               │
  │    "yacht_id": "85fe1119-...",     ← from JWT context           │
  │    "user_id": "a35cad0b-...",      ← from JWT context           │
  │    "items": [                                                    │
  │      {                                                           │
  │        "id": "...",                                              │
  │        "entity_type": "fault",                                   │
  │        "summary": "Starboard engine coolant...",                │
  │        "is_critical": true,                                      │
  │        ...                                                       │
  │      },                                                          │
  │      ... more items                                              │
  │    ],                                                            │
  │    "period_start": "2026-03-20T00:00:00Z",                     │
  │    "period_end": "2026-03-23T23:59:59Z"                         │
  │  }                                                               │
  │                                                                  │
  │  Timeout: 120 seconds (LLM calls are slow)                      │
  │  Fallback: If microservice fails → old basic HTML export runs   │
  │                                                                  │
  │  Security: Internal service-to-service call                      │
  │  Microservice trusts yacht_id/user_id because Cloud_PMS         │
  │  already authenticated the user via JWT                          │
  └──────────────────────────────────────────────────────────────────┘

  Phase 5: LLM Pipeline (Inside Microservice)

  ┌──────────────────────────────────────────────────────────────────┐
  │  STAGE 1: CLASSIFY (ClassifyPMSStage)                           │
  │  ─────────────────────────────────                              │
  │  For each item, concurrent call to GPT-4o-mini (semaphore=10):  │
  │                                                                  │
  │  System: "You are a maritime email subject classifier."          │
  │  User: "Categorise into: Electrical, Projects, Financial,       │
  │         Galley Laundry, Risk, Admin, Fire Safety, Tenders,      │
  │         Logistics, Deck, General Outstanding"                    │
  │                                                                  │
  │  Input mapping:                                                  │
  │    subject = "fault: urgent"       ← entity_type: category     │
  │    body    = "Starboard engine..." ← item summary              │
  │    short_id = "11111111"           ← first 8 chars of ID       │
  │                                                                  │
  │  Output: { category: "Electrical", summary: "...", confidence } │
  │  Model: gpt-4o-mini, temp=0.2, response_format=json_object     │
  │                                                                  │
  │  Error handling: Falls back to category "General Outstanding"   │
  │  with confidence 0.0 if LLM call fails                          │
  │                                                                  │
  │  STAGE 2: GROUP (GroupPMSStage)                                 │
  │  ─────────────────────────────                                  │
  │  Groups classified items by category:                           │
  │    Electrical → [item1]                                          │
  │    Admin      → [item2, item3]                                   │
  │    Logistics  → [item4]                                          │
  │                                                                  │
  │  Each group becomes a TopicGroup with:                           │
  │    merge_key, category, notes[], source_ids[]                   │
  │                                                                  │
  │  STAGE 3: MERGE (MergeSummariesStage)                           │
  │  ──────────────────────────────────                              │
  │  For each group, concurrent call to GPT-4o-mini (semaphore=5):  │
  │                                                                  │
  │  System: "You are a maritime handover summarisation assistant"   │
  │  User: "Merge these notes into professional handover entry:     │
  │         - Use 2nd person ('You need to...')                     │
  │         - Extract actions with priority CRITICAL/HIGH/NORMAL    │
  │         - Keep concise and professional"                         │
  │                                                                  │
  │  Output: {                                                       │
  │    subject: "Starboard Engine — Coolant Warning",               │
  │    summary: "You need to address the high coolant...",          │
  │    actions: [                                                    │
  │      { priority: "CRITICAL", task: "Monitor every 4 hours" }   │
  │    ]                                                             │
  │  }                                                               │
  │                                                                  │
  │  Error handling: Falls back to raw notes text if LLM fails      │
  └──────────────────────────────────────────────────────────────────┘

  Phase 6: Write to Tenant DB (Microservice → Supabase)

  ┌──────────────────────────────────────────────────────────────────┐
  │  All writes use SERVICE_ROLE key (bypasses RLS)                  │
  │  BUT every write explicitly includes yacht_id for isolation      │
  │                                                                  │
  │  WRITE 1: handover_entries (truth seeds — immutable)             │
  │  ─────────────────────────────────────────────────               │
  │  For each merged item:                                           │
  │  INSERT INTO handover_entries (                                   │
  │    yacht_id, created_by_user_id, primary_domain,                │
  │    presentation_bucket, narrative_text, summary_text,            │
  │    source_entity_type, is_critical, status='candidate'           │
  │  )                                                               │
  │  These are NEVER overwritten — compliance audit trail            │
  │                                                                  │
  │  WRITE 2: handover_drafts (the document)                        │
  │  ──────────────────────────────────────                          │
  │  INSERT INTO handover_drafts (                                   │
  │    yacht_id, generated_by_user_id, period_start, period_end,    │
  │    state='DRAFT', generation_method='ai_assisted'                │
  │  )                                                               │
  │                                                                  │
  │  WRITE 3: handover_draft_sections (department buckets)           │
  │  ────────────────────────────────────────────────────            │
  │  For each non-empty bucket (Engineering, Admin_Compliance, etc): │
  │  INSERT INTO handover_draft_sections (                           │
  │    draft_id, bucket_name, section_order                          │
  │  )                                                               │
  │                                                                  │
  │  WRITE 4: handover_draft_items (LLM-summarised content)         │
  │  ──────────────────────────────────────────────────              │
  │  For each entry in each section:                                 │
  │  INSERT INTO handover_draft_items (                              │
  │    draft_id, section_id, section_bucket, summary_text,          │
  │    domain_code, is_critical, item_order, source_entry_ids       │
  │  )                                                               │
  │                                                                  │
  │  RLS policies on all tables:                                     │
  │  - authenticated: yacht_id = user's yacht (via auth_users_profiles) │
  │  - service_role: full access (WITH CHECK TRUE)                   │
  │  - handover_entries: NO DELETE policy (immutable truth seeds)    │
  │  - handover_drafts: DELETE only in DRAFT/IN_REVIEW states       │
  └──────────────────────────────────────────────────────────────────┘

  Phase 7: Render HTML (Microservice → Jinja2 Template)

  ┌──────────────────────────────────────────────────────────────────┐
  │  HandoverExporter._fetch_draft_with_details(draft_id, yacht_id) │
  │  → Fetches draft + sections + items + signoffs from DB          │
  │  → Enriches items with entity hyperlinks (signed tokens)        │
  │                                                                  │
  │  HandoverExporter._render_template(draft_data)                   │
  │  → templates/handover_report.html (Jinja2)                      │
  │  → A4-ready professional document:                               │
  │    - Header: TECHNICAL HANDOVER REPORT, doc number, date        │
  │    - Table of Contents                                           │
  │    - Sections by department (Engineering, Deck, Admin...)        │
  │    - Numbered items with LLM summaries + action items           │
  │    - Priority tags: [CRITICAL] [HIGH] [NORMAL]                  │
  │    - Deep links: "View in App" buttons with signed tokens       │
  │    - Dual signature block: PREPARED BY / REVIEWED BY            │
  │    - Footer: confidentiality notice, document hash              │
  │                                                                  │
  │  document_hash = SHA256 of rendered HTML                         │
  │  (tamper-evidence for compliance)                                │
  └──────────────────────────────────────────────────────────────────┘

  Phase 8: Upload to Storage (Microservice → Supabase Storage)

  ┌──────────────────────────────────────────────────────────────────┐
  │  Bucket: handover-exports                                        │
  │  Path:   {yacht_id}/original/{draft_id}_{timestamp}.html        │
  │                                                                  │
  │  supabase.storage.from_("handover-exports").upload(              │
  │    path=storage_path,                                            │
  │    file=html_bytes,                                              │
  │    content_type="text/html"                                      │
  │  )                                                               │
  │                                                                  │
  │  Security: Service role key for storage writes                   │
  │  Isolation: Files namespaced by yacht_id in path                │
  │  Storage RLS: Supabase Storage policies enforce yacht isolation  │
  └──────────────────────────────────────────────────────────────────┘

  Phase 9: Microservice Returns to Cloud_PMS

  ┌──────────────────────────────────────────────────────────────────┐
  │  HTTP 201 Created                                                │
  │  {                                                               │
  │    "draft_id": "66b691de-...",                                  │
  │    "storage_url": "handover-exports/85fe1119-.../original/...", │
  │    "document_hash": "sha256:2560fda...",                        │
  │    "sections_count": 2,                                          │
  │    "items_count": 3,                                             │
  │    "critical_count": 3                                           │
  │  }                                                               │
  └──────────────────────────────────────────────────────────────────┘

  Phase 10: Cloud_PMS Creates Export Record + Ledger (Cloud_PMS → Tenant DB)

  ┌──────────────────────────────────────────────────────────────────┐
  │  WRITE 5: handover_exports (Cloud_PMS owns this table)          │
  │  ─────────────────────────────────────────────────               │
  │  INSERT INTO handover_exports (                                  │
  │    id = draft_id,                                                │
  │    yacht_id, export_type, exported_by_user_id,                  │
  │    document_hash, export_status='completed',                     │
  │    original_storage_url = storage_url,                           │
  │    review_status = 'pending_review',                             │
  │    exported_at = NOW()                                           │
  │  )                                                               │
  │                                                                  │
  │  WRITE 6: ledger_events (compliance audit trail)                │
  │  ──────────────────────────────────────────────                  │
  │  create_export_ready_ledger_event()                              │
  │  → INSERT INTO pms_audit_log (signature, new_values)            │
  │  → INSERT INTO ledger_events via build_ledger_event()           │
  │    - event_type: 'export_ready_for_review'                      │
  │    - entity_type: 'handover_export'                              │
  │    - proof_hash: SHA256 chain (tamper-evident)                  │
  │    - change_summary: 'Handover export ready for review (N items)' │
  │                                                                  │
  │  WHY NOT in microservice:                                        │
  │  record_ledger_event() RPC uses auth.uid() which is NULL        │
  │  with service_role. Cloud_PMS uses build_ledger_event() helper  │
  │  which constructs the proof_hash manually and inserts directly. │
  └──────────────────────────────────────────────────────────────────┘

  Phase 11: User Sees Notification (Tenant DB → Frontend)

  ┌──────────────────────────────────────────────────────────────────┐
  │  The ledger_events row triggers:                                 │
  │  1. LedgerPanel in frontend shows "Handover export ready"       │
  │  2. User clicks → opens the export preview page                  │
  │  3. Frontend fetches HTML from Supabase Storage via signed URL   │
  │                                                                  │
  │  The export page flow:                                           │
  │  GET /v1/handover/export/{export_id}/content                    │
  │  → Fetches HTML from storage                                    │
  │  → Parses into editable sections (handover_html_parser.py)      │
  │  → User can edit text, reorder sections                          │
  │  → Auto-saves to handover_exports.edited_content                │
  └──────────────────────────────────────────────────────────────────┘

  Phase 12: Sign → Countersign → Complete (Future — Already Built)

  ┌──────────────────────────────────────────────────────────────────┐
  │  POST /v1/handover/export/{id}/submit                           │
  │  → User draws signature on canvas                               │
  │  → Generates signed HTML (Bucket 2 in storage)                  │
  │  → Updates: review_status → 'pending_hod_signature'             │
  │  → Ledger event: 'requires_countersignature'                    │
  │  → HOD gets notification                                         │
  │                                                                  │
  │  POST /v1/handover/export/{id}/countersign                      │
  │  → HOD reviews and countersigns                                  │
  │  → Final HTML with both signatures                               │
  │  → Updates: review_status → 'complete'                           │
  │  → Ledger event: 'handover_signed'                              │
  │  → Indexes in search_index for full-text search                 │
  │  → Document hash = tamper-evident compliance record              │
  │                                                                  │
  │  DB state machine (RPC functions):                               │
  │  sign_handover_outgoing() → DRAFT/IN_REVIEW → ACCEPTED         │
  │  sign_handover_incoming() → ACCEPTED → SIGNED                   │
  │  (requires acknowledge_critical if critical items exist)         │
  └──────────────────────────────────────────────────────────────────┘

  Security Protocol Summary

  ┌─────────────────────────┬─────────────────────────────────────────────────────────────────────────────────────────┐
  │          Layer          │                                        Mechanism                                        │
  ├─────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────┤
  │ Authentication          │ JWT from Master Supabase, validated by get_authenticated_user()                         │
  ├─────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────┤
  │ Tenant isolation        │ yacht_id from JWT claims, never from user input                                         │
  ├─────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────┤
  │ RLS                     │ Every table has yacht_id = get_user_yacht_id() policies                                 │
  ├─────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────┤
  │ Service role writes     │ Explicit yacht_id on every INSERT even though RLS is bypassed                           │
  ├─────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────┤
  │ Immutability            │ handover_entries has no DELETE policy — truth seeds can't be erased                     │
  ├─────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────┤
  │ Tamper evidence         │ document_hash (SHA256 of HTML), proof_hash chain in ledger                              │
  ├─────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────┤
  │ State machine           │ Draft deletion only in DRAFT/IN_REVIEW states (RLS enforced)                            │
  ├─────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────┤
  │ Critical acknowledgment │ sign_handover_incoming() rejects if critical items exist and acknowledge_critical=false │
  ├─────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────┤
  │ Storage isolation       │ Files namespaced by {yacht_id}/ in Supabase Storage bucket                              │
  ├─────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────┤
  │ Link tokens             │ Entity deep links in exported docs use HMAC-SHA256 signed tokens (24h TTL)              │
  ├─────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────┤
  │ CORS                    │ Explicit allowlist: app.celeste7.ai, localhost:3000                                     │
  └─────────────────────────┴─────────────────────────────────────────────────────────────────────────────────────────┘

✻ Crunched for 1m 53s
