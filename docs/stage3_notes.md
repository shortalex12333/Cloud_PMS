  Stage 3 Agent Briefing — Actions, Mutations & Ledger

  Who You Are and What You're Building

  You are the Stage 3 engineer on CelesteOS PMS — a Personal Assistant for yacht crew.

  Stage 1 (search pipeline) — complete, signed off.
  Stage 2 (entity lens display) — complete, signed off. All 12 entity endpoints return data. All 14 lens pages render. Fragmented routes
  canonical.
  Stage 3 (your work) — wire every action button, mutation, and write operation so crew can actually change system state from within a
  lens. Also ensure every mutation writes to the ledger so the audit trail is live.

  This is polishing existing work, not building from scratch. The scaffolding — backend handlers, action registry, frontend hooks, ledger
   routes — is already built. Your job is to connect the ends and verify every action works end-to-end.

  ---
  Project Root

  /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/

  Everything lives here. Not /Volumes/Backup/CELESTE/ — that is just the parent volume.

  ---
  Hardware and Docker

  This runs on a Mac Studio (~$4k capex). No cloud compute during staging. Zero cost.

  cd BACK_BUTTON_CLOUD_PMS/deploy/local
  ./celeste.sh start          # API + projection + embedding
  ./celeste.sh health         # health check all services
  ./celeste.sh logs api       # follow API logs
  ./celeste.sh shell api      # exec into container

  Running containers:

  ┌────────────────────┬──────┬──────────────────────────────────────┐
  │     Container      │ Port │                Status                │
  ├────────────────────┼──────┼──────────────────────────────────────┤
  │ celeste-api        │ 8000 │ healthy                              │
  ├────────────────────┼──────┼──────────────────────────────────────┤
  │ celeste-web-local  │ 3000 │ running                              │
  ├────────────────────┼──────┼──────────────────────────────────────┤
  │ celeste-projection │ —    │ unhealthy (normal — no health check) │
  ├────────────────────┼──────┼──────────────────────────────────────┤
  │ celeste-embedding  │ —    │ unhealthy (normal)                   │
  └────────────────────┴──────┴──────────────────────────────────────┘

  JWT minting (expires every 2h, remint when you get 401):

  docker exec celeste-api python3 -c "
  import jwt, time, os, urllib.request, json
  MASTER_URL = os.environ.get('MASTER_SUPABASE_URL', '')
  MASTER_KEY = os.environ.get('MASTER_SUPABASE_SERVICE_KEY', os.environ.get('MASTER_SUPABASE_SERVICE_ROLE_KEY', ''))
  JWT_SECRET = os.environ.get('MASTER_SUPABASE_JWT_SECRET', os.environ.get('SUPABASE_JWT_SECRET', ''))
  req =
  urllib.request.Request(f'{MASTER_URL}/rest/v1/user_accounts?yacht_id=eq.85fe1119-b04c-41ac-80f1-829d23322598&status=eq.active&limit=1')
  req.add_header('apikey', MASTER_KEY); req.add_header('Authorization', f'Bearer {MASTER_KEY}')
  u = json.loads(urllib.request.urlopen(req, timeout=10).read())[0]
  token = jwt.encode({'sub': u['id'], 'aud': 'authenticated', 'role': 'authenticated', 'iss': 'supabase', 'iat': int(time.time()), 'exp':
   int(time.time()) + 7200, 'email': u['email']}, JWT_SECRET, algorithm='HS256')
  open('/tmp/jwt_token.txt', 'w').write(token)
  print('Minted for', u['email'])
  "

  Test credentials:
  - Email: x@alex-short.com, role: captain
  - User UUID: a35cad0b-02ff-4287-b6e4-17c96fa6a424 (master DB)
  - Yacht ID: 85fe1119-b04c-41ac-80f1-829d23322598
  - Tenant key alias: yTEST_YACHT_001

  ---
  Two-Database Architecture

  Every request touches two Supabase projects:

  ┌─────────────────────────────────────────────┬──────────────────────┬─────────────────────────────────────────────┐
  │                  Variable                   │      Project ID      │                   Purpose                   │
  ├─────────────────────────────────────────────┼──────────────────────┼─────────────────────────────────────────────┤
  │ MASTER_SUPABASE_URL                         │ qvzmkaamzaqxpzbewjxe │ Auth — who you are, tenant lookup           │
  ├─────────────────────────────────────────────┼──────────────────────┼─────────────────────────────────────────────┤
  │ SUPABASE_URL / yTEST_YACHT_001_SUPABASE_URL │ vzsohavtuotocgrfkfyd │ PMS data — all entity tables, ledger, audit │
  └─────────────────────────────────────────────┴──────────────────────┴─────────────────────────────────────────────┘

  The API validates JWT against master, extracts user_id, calls get_my_bootstrap RPC to resolve yacht_id and tenant_key_alias, then
  queries tenant DB with service key (bypasses Supabase RLS — API enforces isolation with .eq('yacht_id', yacht_id) on every query).

  Connection: Direct :5432, NOT Supavisor pooler (doesn't work for this tenant).

  ---
  Action System Architecture

  The Three-Phase Lifecycle

  Every mutation follows this pattern:

  GET  /v1/actions/{action_name}/prefill?{entity_type}_id={id}
       → Current entity state, pre-populated fields, validation constraints

  POST /v1/actions/{action_name}/preview   (optional — for high-impact actions)
       → Dry run, shows what will change, confirmation token

  POST /v1/actions/execute
       Body: { action, context: {yacht_id, user_id, role}, payload: {...} }
       → Commits mutation, writes audit log, writes ledger event

  Key Backend Files

  ┌───────────────────────────────────────────────────┬─────────────────────────────────────────┬─────────────┐
  │                       File                        │                 Purpose                 │    Size     │
  ├───────────────────────────────────────────────────┼─────────────────────────────────────────┼─────────────┤
  │ apps/api/routes/p0_actions_routes.py              │ All action FastAPI endpoints            │ 307KB       │
  ├───────────────────────────────────────────────────┼─────────────────────────────────────────┼─────────────┤
  │ apps/api/action_router/registry.py                │ Declarative registry of all 130 actions │ ~1800 lines │
  ├───────────────────────────────────────────────────┼─────────────────────────────────────────┼─────────────┤
  │ apps/api/handlers/work_order_mutation_handlers.py │ WO mutations                            │ ~2344 lines │
  ├───────────────────────────────────────────────────┼─────────────────────────────────────────┼─────────────┤
  │ apps/api/handlers/fault_mutation_handlers.py      │ Fault mutations                         │ ~2000 lines │
  ├───────────────────────────────────────────────────┼─────────────────────────────────────────┼─────────────┤
  │ apps/api/handlers/equipment_handlers.py           │ Equipment mutations                     │ ~1900 lines │
  ├───────────────────────────────────────────────────┼─────────────────────────────────────────┼─────────────┤
  │ apps/api/handlers/certificate_handlers.py         │ Certificate mutations                   │ ~2600 lines │
  ├───────────────────────────────────────────────────┼─────────────────────────────────────────┼─────────────┤
  │ apps/api/handlers/inventory_handlers.py           │ Stock operations                        │ —           │
  ├───────────────────────────────────────────────────┼─────────────────────────────────────────┼─────────────┤
  │ apps/api/handlers/receiving_handlers.py           │ Goods receipt (adapter pattern)         │ —           │
  ├───────────────────────────────────────────────────┼─────────────────────────────────────────┼─────────────┤
  │ apps/api/handlers/shopping_list_handlers.py       │ Procurement                             │ —           │
  ├───────────────────────────────────────────────────┼─────────────────────────────────────────┼─────────────┤
  │ apps/api/handlers/hours_of_rest_handlers.py       │ Crew compliance                         │ —           │
  ├───────────────────────────────────────────────────┼─────────────────────────────────────────┼─────────────┤
  │ apps/api/handlers/handover_handlers.py            │ Shift handover                          │ —           │
  ├───────────────────────────────────────────────────┼─────────────────────────────────────────┼─────────────┤
  │ apps/api/routes/ledger_routes.py                  │ Ledger read/write endpoints             │ —           │
  └───────────────────────────────────────────────────┴─────────────────────────────────────────┴─────────────┘

  All Action Endpoints (/v1/actions/ prefix)

  PREFILL (GET):
  - /create_work_order_from_fault/prefill
  - /add_note_to_work_order/prefill
  - /add_part_to_work_order/prefill
  - /mark_work_order_complete/prefill
  - /log_part_usage/prefill
  - /add_to_handover/prefill

  PREVIEW (POST):
  - /work_order/create/prepare
  - /mark_work_order_complete/preview
  - /add_part_to_work_order/preview
  - /create_work_order_from_fault/preview
  - /log_part_usage/preview

  EXECUTE (POST — all mutations go here):
  - /work_order/create/commit
  - /execute ← primary endpoint, handles all 130 actions by name

  HANDOVER (POST):
  - /handover/{draft_id}/validate
  - /handover/{draft_id}/finalize
  - /handover/{draft_id}/export
  - /handover/{export_id}/sign/outgoing
  - /handover/{export_id}/sign/incoming

  The 130 Actions by Domain

  Work Orders (16): add_note_to_work_order, close_work_order, add_work_order_photo, add_parts_to_work_order, view_work_order_checklist,
  assign_work_order, update_work_order, add_wo_hours, start_work_order, cancel_work_order, create_work_order_from_fault,
  reassign_work_order (SIGNED), archive_work_order (SIGNED), add_wo_note, add_wo_part, view_related_entities

  Equipment (18): update_equipment_status, add_equipment_note, attach_file_to_equipment, create_work_order_for_equipment,
  link_part_to_equipment, flag_equipment_attention, decommission_equipment (SIGNED), record_equipment_hours, create_equipment,
  assign_parent_equipment, archive_equipment, restore_archived_equipment, link_document_to_equipment, set_equipment_status,
  attach_image_with_comment, decommission_and_replace_equipment

  Faults (9): report_fault, acknowledge_fault, close_fault (SIGNED), update_fault, reopen_fault, mark_fault_false_alarm, add_fault_photo,
   add_fault_note, diagnose_fault

  Parts/Inventory (11): consume_part, receive_part, transfer_part, adjust_stock_quantity (SIGNED), write_off_part,
  create_shopping_list_item, approve_shopping_list_item, reject_shopping_list_item, check_stock_level, log_part_usage, view_low_stock

  Documents (8): upload_document, update_document, delete_document, add_document_tags, add_document_comment, delete_document_comment,
  update_document_comment, list_document_comments

  Certificates (6): create_crew_certificate, create_vessel_certificate, link_document_to_certificate, update_certificate,
  supersede_certificate

  Warranty (5): draft_warranty_claim, submit_warranty_claim, approve_warranty_claim, reject_warranty_claim, compose_warranty_email

  Receiving (9): create_receiving, add_receiving_item, adjust_receiving_item, extract_receiving_candidates, promote_candidate_to_part,
  update_receiving_fields, accept_receiving, reject_receiving, attach_receiving_image_with_comment

  Hours of Rest (6): upsert_hours_of_rest, get_hours_of_rest, get_monthly_signoff, sign_monthly_signoff, create_monthly_signoff,
  list_crew_warnings

  Handover (8): add_to_handover, validate_handover_draft, finalize_handover_draft, export_handover, sign_handover_outgoing,
  sign_handover_incoming, get_pending_handovers, verify_handover_export

  ---
  Frontend Action Hooks

  ┌────────────────────────┬────────────────┬───────────────────┬───────────────────┐
  │       Hook File        │     Entity     │      Actions      │  Signed Actions   │
  ├────────────────────────┼────────────────┼───────────────────┼───────────────────┤
  │ useWorkOrderActions.ts │ work_order     │ 13                │ reassign, archive │
  ├────────────────────────┼────────────────┼───────────────────┼───────────────────┤
  │ useFaultActions.ts     │ fault          │ 9                 │ close             │
  ├────────────────────────┼────────────────┼───────────────────┼───────────────────┤
  │ useEquipmentActions.ts │ equipment      │ 7 spec + 6 legacy │ decommission      │
  ├────────────────────────┼────────────────┼───────────────────┼───────────────────┤
  │ usePartActions.ts      │ part/inventory │ 7                 │ adjust_stock      │
  ├────────────────────────┼────────────────┼───────────────────┼───────────────────┤
  │ useDocumentActions.ts  │ document       │ 4                 │ delete            │
  └────────────────────────┴────────────────┴───────────────────┴───────────────────┘

  All hooks call: POST /v1/actions/execute with Authorization: Bearer <JWT> except useDocumentActions which calls Supabase PostgREST
  directly.

  Signed actions require a signature field in the payload — a confirmation token with PIN + timestamp hash. The frontend generates this.
  If the backend receives a signed action without the token, it must reject it.

  ---
  Ledger System

  Two separate but complementary audit systems:

  pms_audit_log — Structured Audit Trail

  Who did what when. Written after every mutation by every handler.

  # Pattern used across all handlers
  def _write_audit_log(db, entry):
      db.table("pms_audit_log").insert({
          "yacht_id": ...,
          "entity_type": ...,
          "entity_id": ...,
          "action": ...,
          "user_id": ...,
          "old_values": ...,   # None for creates
          "new_values": ...,
          "signature": entry.get("signature", {}),  # INVARIANT: never None, {} if unsigned
          "created_at": datetime.now(timezone.utc).isoformat(),
      }).execute()

  ledger_events — Event Stream

  SHA-256 hashed event stream for immutability proof. Written by p0_actions_routes.py after specific high-value mutations.

  Ledger API Endpoints

  ┌─────────────────────────────────────────────┬──────────────────────────────────────────────────┐
  │                  Endpoint                   │                     Purpose                      │
  ├─────────────────────────────────────────────┼──────────────────────────────────────────────────┤
  │ GET /v1/ledger/events                       │ Paginated event history (limit, offset, filters) │
  ├─────────────────────────────────────────────┼──────────────────────────────────────────────────┤
  │ GET /v1/ledger/events/by-entity/{type}/{id} │ Entity-specific history (used by HistorySection) │
  ├─────────────────────────────────────────────┼──────────────────────────────────────────────────┤
  │ GET /v1/ledger/day-anchors                  │ Day-by-day mutation/read counts for timeline UI  │
  ├─────────────────────────────────────────────┼──────────────────────────────────────────────────┤
  │ POST /v1/ledger/record                      │ Frontend logs read events (artefact_opened)      │
  └─────────────────────────────────────────────┴──────────────────────────────────────────────────┘

  Frontend Ledger Components

  ┌──────────────────────────────────────────────────────────┬───────────────────────────────┐
  │                           File                           │            Purpose            │
  ├──────────────────────────────────────────────────────────┼───────────────────────────────┤
  │ apps/web/src/components/ledger/LedgerPanel.tsx           │ Full ledger UI panel          │
  ├──────────────────────────────────────────────────────────┼───────────────────────────────┤
  │ apps/web/src/components/lens/sections/HistorySection.tsx │ Per-entity history in lens    │
  ├──────────────────────────────────────────────────────────┼───────────────────────────────┤
  │ apps/web/src/components/spotlight/SpotlightSearch.tsx    │ Logs artefact_opened on click │
  └──────────────────────────────────────────────────────────┴───────────────────────────────┘

  HistorySection calls GET /v1/ledger/events/by-entity/{entity_type}/{entity_id} — this is the live audit trail that appears in every
  lens detail page.

  ---
  Verification Protocol (Non-Negotiable)

  This is how every action must be verified. A 200 response is not a pass.

  For every action:

  1. Trigger it — click the button in the browser at localhost:3000
  2. Check HTTP response — must be 200 (or expected status)
  3. Check DB mutation — query the source table directly, confirm the row changed
  4. Check pms_audit_log — confirm a new row was written with correct entity_type, action, user_id
  5. Check ledger_events — confirm a new event was written (for actions that trigger ledger)
  6. Check HistorySection — refresh the entity lens, confirm the history entry appears in the UI
  7. Role enforcement — for role_restricted actions, test with a crew role JWT — must return 403

  Two independent facts must agree for a PASS. A 200 with no DB change is a fail. A DB change with no audit log is a fail.

  The verification discipline from the stage 2 session: the lie was caught because DB said 245KB but the actual file was 334 bytes. Check
   both sides of every claim.

  ---
  What Stage 2 Left That Affects You

  Known gaps documented in docs/STAGE_2_HANDOVER.md:

  - warranty and worklist lenses have frontend scaffolding but no backend handler and no DB data. Decide scope before touching.
  - file_size in pms_attachments is not populated by the upload path — only seeded rows have it. The read side works; the write side
  (upload → derive size from storage object) was deferred.
  - handover and shopping_list have a type mismatch in search_index (handover_item / shopping_item) vs what the lens expects. This may
  surface when action results try to navigate back.

  docs/superpowers/agents/ — Per-lens DATA.md and VERIFY.md documents exist for all 12 lenses. These define exactly what each action
  should do and how to verify it. Read them before touching each lens.

  ---
  Build Rules

  # TypeScript build — must stay 0 errors
  cd apps/web && npx tsc --noEmit

  # API imports — must stay clean
  docker exec celeste-api python3 -c "from pipeline_service import app"

  # After any backend change — rebuild API container
  cd deploy/local && docker compose up --build -d api

  NEVER commit without:
  - TypeScript build passing
  - At least one real end-to-end test of the changed action (button → DB → audit log)
  - tasks/lessons.md updated if anything went wrong

  ---
  Repository Discipline

  - Never save to root — use src/, tests/, docs/, config/, scripts/
  - Never commit .env, .swarm/, .claude/skills/ — in .gitignore
  - Commit messages explain WHY — not "fix bug", but "fix: fault close returns 403 for captain role — role check was comparing against
  wrong field"
  - No version suffixes — _v2, _final, _old — git handles versioning
  - One canonical location per concept — if you find duplicate files, consolidate

  ---
  Lessons From Stage 2 (Apply These)

  1. Test first, fix second, document third. Don't read code and infer what works. Run it.
  2. A 200 with wrong data is harder to catch than a 500. Always check the DB mutation independently of the HTTP response.
  3. Seed data quality = code quality. Plausible-but-wrong test data passes visual inspection and gets into reports.
  4. Two independent sources must agree for a PASS. DB state + HTTP response + audit log — all three, every time.
  5. The gap between "handler exists" and "endpoint is wired" is exactly where bugs hide. Grep for the route decorator, don't assume.
  6. dict.get(key, default) ≠ dict.get(key) or default — the former doesn't catch explicit None from the DB.
  7. .single() in supabase-py throws on 0 rows (500). .maybe_single() returns None (404). Always use maybe_single().

  ---
  Execution Order

  Start with the actions that are most critical for daily vessel operations, in this order:

  1. Work order mutations — start, add note, add part, mark complete (these have the most complete handler coverage)
  2. Fault mutations — acknowledge, close, add note (tight coupling to work orders)
  3. Part/inventory mutations — consume part, log usage, adjust stock
  4. Equipment mutations — status update, add note, flag attention
  5. Certificate mutations — create, update, supersede
  6. Ledger end-to-end — verify every action above writes to both pms_audit_log and ledger_events, and that HistorySection renders the
  entries live
  7. Receiving, shopping list, hours of rest — after core entities are clean
  8. Warranty, worklist — assess scope, implement or defer with explicit documentation

  For each action: trigger → verify DB → verify audit → verify ledger UI → test role enforcement. One at a time. No batching unverified
  work.

  ★ Insight ─────────────────────────────────────
  The ledger is not a separate feature — it is the trust layer. Maritime operations run on accountability: who changed the engine status,
   who consumed the last spare filter, who signed off the work order at 0200. If mutations fire without writing to pms_audit_log and
  ledger_events, the data exists but cannot be trusted. Stage 3 is not "add action buttons" — it is "make the system auditable."
  ─────────────────────────────────────────────────
