                                                                                                
  CelesteOS PMS — Agent Handover                                                                                                    
                                                                                                                                    
  1. What This Project Is                                                                                                           
                                                                                                                                  
  CelesteOS is a Personal Assistant (PA) for yacht crew, not a filing cabinet. Users issue action-based natural language commands
  through a search bar. The NLP pipeline interprets intent and routes commands to backend actions. This is the foundational product
  philosophy — every test, feature, and UI decision flows from it.

  Working directory: /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/web
  API directory: /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api

  Stack: Next.js (frontend) + FastAPI/Python (backend) + Supabase PostgreSQL. The E2E tests live in apps/web/e2e/ and run against
  the live production API at https://pipeline-core.int.celeste7.ai (never localhost — see env vars below).

  ---
  2. What a "Lens" Is

  A lens is a dedicated full-page detail view for a single entity instance. The architecture shifted from a single
  ContextPanel/LensRenderer to fragmented routes — each entity type has its own URL:

  /work-orders/{id}    → Work Order Lens
  /faults/{id}         → Fault Lens
  /equipment/{id}      → Equipment Lens
  /inventory/{id}      → Parts/Inventory Lens
  /documents/{id}      → Document Lens
  /certificates/{id}   → Certificate Lens
  /shopping-list       → Shopping List Lens
  /receiving           → Receiving Workflow Lens
  /hours-of-rest       → Hours of Rest Lens
  /handover            → Handover Lens
  /purchase-orders     → Purchase Order Lens

  Each lens has action buttons — buttons that call POST /v1/actions/execute. The entire test campaign is about verifying these
  buttons work end-to-end: HTTP 200 → correct DB state.

  ---
  3. What "Testing" and "Ensuring" Means Here

  Every test follows one of two patterns:

  HARD PROOF — The gold standard:
  1. Call action via callActionDirect
  2. Assert result.status === 200 and result.data.status === 'success'
  3. Poll the actual database via supabaseAdmin (service-role, bypasses RLS) to verify the write happened

  ADVISORY — For known backend bugs or gated workflows:
  1. Call the action
  2. Accept multiple status codes: expect([200, 400, 409, 500]).toContain(result.status)
  3. No DB poll, or DB poll only on the 200 branch
  4. Always include a console.log explaining WHY it's advisory (the specific bug or gate)

  The rule: 200 means the test must verify DB state. Anything else must be documented. Never let a test pass silently without
  proving the write happened.

  ---
  4. The Three "Waves" of Coverage (What Stage 3 Is)

  Work on expanding action coverage has proceeded in three waves, all under apps/web/e2e/:

  ┌─────────────┬─────────┬────────────────────────────────────────────────────────────────────────────────────┬───────────────┐
  │    Wave     │ Shards  │                                   What Was Built                                   │    Status     │
  ├─────────────┼─────────┼────────────────────────────────────────────────────────────────────────────────────┼───────────────┤
  │             │         │ Lens action smoke tests + full coverage of core actions (close_fault,              │ ✅ All        │
  │ Wave 1      │ 33, 34  │ reopen_fault, add_fault_note, assign_WO, cancel_WO, record_equipment_hours,        │ passing after │
  │ (original)  │         │ log_part_usage, transfer_part, upload/update/tag documents,                        │  major fixes  │
  │             │         │ create/update/supersede certificates)                                              │               │
  ├─────────────┼─────────┼────────────────────────────────────────────────────────────────────────────────────┼───────────────┤
  │ Wave 2      │ 35, 36, │ Shopping list CRUD, part mutations (receive/consume), receiving workflow, hours of │ ✅ 19/19      │
  │             │  37     │  rest                                                                              │ passing       │
  ├─────────────┼─────────┼────────────────────────────────────────────────────────────────────────────────────┼───────────────┤
  │ Wave 3      │ 38, 39, │ Fault extended actions, WO+Equipment extended, purchase+handover                   │ ✅ 13/13      │
  │             │  40     │                                                                                    │ passing       │
  └─────────────┴─────────┴────────────────────────────────────────────────────────────────────────────────────┴───────────────┘

  Wave 3 = Shards 38-40. That is what "stage 3" means in context. This is what was completed in the most recent session.

  The completed plan file for the shard-33/34 work is at: /Users/celeste7/.claude/plans/linked-plotting-charm.md — all 4 phases are
  done.

  ---
  5. Lens-by-Lens Action Button Coverage

  Work Order Lens (pms_work_orders):

  ┌──────────────────────────────────────┬───────────────┬────────────┐
  │                Action                │     Shard     │  Pattern   │
  ├──────────────────────────────────────┼───────────────┼────────────┤
  │ add_wo_note / add_note_to_work_order │ 33, 34        │ HARD PROOF │
  ├──────────────────────────────────────┼───────────────┼────────────┤
  │ start_work_order                     │ 33, 34        │ HARD PROOF │
  ├──────────────────────────────────────┼───────────────┼────────────┤
  │ assign_work_order                    │ 34            │ HARD PROOF │
  ├──────────────────────────────────────┼───────────────┼────────────┤
  │ cancel_work_order                    │ 34            │ HARD PROOF │
  ├──────────────────────────────────────┼───────────────┼────────────┤
  │ complete_work_order                  │ 39            │ HARD PROOF │
  ├──────────────────────────────────────┼───────────────┼────────────┤
  │ update_work_order                    │ 39            │ HARD PROOF │
  ├──────────────────────────────────────┼───────────────┼────────────┤
  │ create_work_order                    │ ❌ Not tested │ —          │
  └──────────────────────────────────────┴───────────────┴────────────┘

  Fault Lens (pms_faults):

  ┌────────────────────────┬───────┬────────────────────────────────┐
  │         Action         │ Shard │            Pattern             │
  ├────────────────────────┼───────┼────────────────────────────────┤
  │ acknowledge_fault      │ 33    │ HARD PROOF                     │
  ├────────────────────────┼───────┼────────────────────────────────┤
  │ close_fault            │ 34    │ HARD PROOF                     │
  ├────────────────────────┼───────┼────────────────────────────────┤
  │ reopen_fault           │ 34    │ HARD PROOF                     │
  ├────────────────────────┼───────┼────────────────────────────────┤
  │ add_fault_note         │ 34    │ HARD PROOF                     │
  ├────────────────────────┼───────┼────────────────────────────────┤
  │ report_fault           │ 38    │ HARD PROOF                     │
  ├────────────────────────┼───────┼────────────────────────────────┤
  │ update_fault           │ 38    │ HARD PROOF                     │
  ├────────────────────────┼───────┼────────────────────────────────┤
  │ diagnose_fault         │ 38    │ HARD PROOF (existence check)   │
  ├────────────────────────┼───────┼────────────────────────────────┤
  │ mark_fault_false_alarm │ 38    │ HARD PROOF (resolved_at check) │
  └────────────────────────┴───────┴────────────────────────────────┘

  Equipment Lens (pms_equipment):

  ┌───────────────────────────────────────────────┬───────────────┬────────────┐
  │                    Action                     │     Shard     │  Pattern   │
  ├───────────────────────────────────────────────┼───────────────┼────────────┤
  │ add_equipment_note                            │ 33, 34        │ HARD PROOF │
  ├───────────────────────────────────────────────┼───────────────┼────────────┤
  │ record_equipment_hours / update_running_hours │ 34            │ HARD PROOF │
  ├───────────────────────────────────────────────┼───────────────┼────────────┤
  │ update_equipment_status                       │ 39            │ HARD PROOF │
  ├───────────────────────────────────────────────┼───────────────┼────────────┤
  │ create_work_order_from_fault                  │ ❌ Not tested │ —          │
  └───────────────────────────────────────────────┴───────────────┴────────────┘

  Inventory/Parts Lens (pms_parts, pms_inventory_transactions):

  ┌───────────────────────┬───────┬─────────────────────────────────────────┐
  │        Action         │ Shard │                 Pattern                 │
  ├───────────────────────┼───────┼─────────────────────────────────────────┤
  │ log_part_usage        │ 34    │ HARD PROOF                              │
  ├───────────────────────┼───────┼─────────────────────────────────────────┤
  │ transfer_part         │ 34    │ HARD PROOF                              │
  ├───────────────────────┼───────┼─────────────────────────────────────────┤
  │ receive_part          │ 35    │ HARD PROOF (pms_inventory_transactions) │
  ├───────────────────────┼───────┼─────────────────────────────────────────┤
  │ consume_part          │ 35    │ ADVISORY (data model split — see §9)    │
  ├───────────────────────┼───────┼─────────────────────────────────────────┤
  │ add_to_shopping_list  │ 35    │ ADVISORY (source_type NOT NULL bug)     │
  ├───────────────────────┼───────┼─────────────────────────────────────────┤
  │ adjust_stock_quantity │ 35    │ ADVISORY (signed action, no sig → 400)  │
  ├───────────────────────┼───────┼─────────────────────────────────────────┤
  │ write_off_part        │ 35    │ ADVISORY (signed action, no sig → 400)  │
  └───────────────────────┴───────┴─────────────────────────────────────────┘

  Document Lens (doc_metadata):

  ┌───────────────────┬───────────────┬──────────────────────────────────────────────────────────────────┐
  │      Action       │     Shard     │                             Pattern                              │
  ├───────────────────┼───────────────┼──────────────────────────────────────────────────────────────────┤
  │ upload_document   │ 34            │ HARD PROOF                                                       │
  ├───────────────────┼───────────────┼──────────────────────────────────────────────────────────────────┤
  │ update_document   │ 34            │ ADVISORY (handler didn't write to DB — fixed in plan but verify) │
  ├───────────────────┼───────────────┼──────────────────────────────────────────────────────────────────┤
  │ add_document_tags │ 34            │ HARD PROOF                                                       │
  ├───────────────────┼───────────────┼──────────────────────────────────────────────────────────────────┤
  │ get_document_url  │ ❌ Not tested │ —                                                                │
  ├───────────────────┼───────────────┼──────────────────────────────────────────────────────────────────┤
  │ delete_document   │ ❌ Not tested │ —                                                                │
  └───────────────────┴───────────────┴──────────────────────────────────────────────────────────────────┘

  Certificate Lens (pms_certificates / pms_vessel_certificates):

  ┌───────────────────────────┬───────┬─────────────────────────────────────────────────┐
  │          Action           │ Shard │                     Pattern                     │
  ├───────────────────────────┼───────┼─────────────────────────────────────────────────┤
  │ create_vessel_certificate │ 34    │ HARD PROOF                                      │
  ├───────────────────────────┼───────┼─────────────────────────────────────────────────┤
  │ update_certificate        │ 34    │ HARD PROOF                                      │
  ├───────────────────────────┼───────┼─────────────────────────────────────────────────┤
  │ supersede_certificate     │ 34    │ ADVISORY (signature gate — rejects without sig) │
  └───────────────────────────┴───────┴─────────────────────────────────────────────────┘

  Shopping List Lens (pms_shopping_list_items):

  ┌────────────────────────────┬───────┬────────────────────────────────────────────────┐
  │           Action           │ Shard │                    Pattern                     │
  ├────────────────────────────┼───────┼────────────────────────────────────────────────┤
  │ create_shopping_list_item  │ 35    │ HARD PROOF                                     │
  ├────────────────────────────┼───────┼────────────────────────────────────────────────┤
  │ approve_shopping_list_item │ 35    │ HARD PROOF                                     │
  ├────────────────────────────┼───────┼────────────────────────────────────────────────┤
  │ reject_shopping_list_item  │ 35    │ HARD PROOF                                     │
  ├────────────────────────────┼───────┼────────────────────────────────────────────────┤
  │ mark_shopping_list_ordered │ 39    │ HARD PROOF (chained)                           │
  ├────────────────────────────┼───────┼────────────────────────────────────────────────┤
  │ delete_shopping_item       │ 39    │ ADVISORY (backend user_role unbound bug → 500) │
  ├────────────────────────────┼───────┼────────────────────────────────────────────────┤
  │ promote_candidate_to_part  │ 35    │ ADVISORY (forbidden for captain)               │
  └────────────────────────────┴───────┴────────────────────────────────────────────────┘

  Receiving Lens (pms_receiving):

  ┌─────────────────────────────┬───────┬───────────────────┐
  │           Action            │ Shard │      Pattern      │
  ├─────────────────────────────┼───────┼───────────────────┤
  │ create_receiving            │ 36    │ HARD PROOF        │
  ├─────────────────────────────┼───────┼───────────────────┤
  │ add_receiving_item          │ 36    │ HARD PROOF        │
  ├─────────────────────────────┼───────┼───────────────────┤
  │ update_receiving_fields     │ 36    │ HARD PROOF        │
  ├─────────────────────────────┼───────┼───────────────────┤
  │ submit_receiving_for_review │ 36    │ ADVISORY          │
  ├─────────────────────────────┼───────┼───────────────────┤
  │ accept_receiving            │ 36    │ ADVISORY (signed) │
  ├─────────────────────────────┼───────┼───────────────────┤
  │ reject_receiving            │ 36    │ ADVISORY (signed) │
  └─────────────────────────────┴───────┴───────────────────┘

  Hours of Rest Lens (pms_hours_of_rest, pms_monthly_signoffs):

  ┌────────────────────────┬───────┬─────────────────────────────────────────────────────┐
  │         Action         │ Shard │                       Pattern                       │
  ├────────────────────────┼───────┼─────────────────────────────────────────────────────┤
  │ upsert_hours_of_rest   │ 37    │ ADVISORY (SyncQueryRequestBuilder Python bug → 500) │
  ├────────────────────────┼───────┼─────────────────────────────────────────────────────┤
  │ get_hours_of_rest      │ 37    │ HARD PROOF                                          │
  ├────────────────────────┼───────┼─────────────────────────────────────────────────────┤
  │ create_monthly_signoff │ 37    │ ADVISORY (NoneType.data Python bug → 500)           │
  ├────────────────────────┼───────┼─────────────────────────────────────────────────────┤
  │ sign_monthly_signoff   │ 37    │ ADVISORY (sequential workflow gate)                 │
  └────────────────────────┴───────┴─────────────────────────────────────────────────────┘

  Handover Lens (handover_items — note: no pms_ prefix):

  ┌───────────────────────┬───────┬───────────────────────────────────┐
  │        Action         │ Shard │              Pattern              │
  ├───────────────────────┼───────┼───────────────────────────────────┤
  │ add_to_handover       │ 40    │ HARD PROOF                        │
  ├───────────────────────┼───────┼───────────────────────────────────┤
  │ edit_handover_section │ 40    │ ADVISORY (accepts any UUID → 200) │
  └───────────────────────┴───────┴───────────────────────────────────┘

  Purchase Order Lens (pms_purchase_orders):

  ┌─────────────────────────┬───────────────┬───────────────────────────────┐
  │         Action          │     Shard     │            Pattern            │
  ├─────────────────────────┼───────────────┼───────────────────────────────┤
  │ create_purchase_request │ 40            │ ADVISORY (signature required) │
  ├─────────────────────────┼───────────────┼───────────────────────────────┤
  │ submit_purchase_order   │ ❌ Not tested │ —                             │
  ├─────────────────────────┼───────────────┼───────────────────────────────┤
  │ approve_purchase_order  │ ❌ Not tested │ —                             │
  ├─────────────────────────┼───────────────┼───────────────────────────────┤
  │ mark_po_received        │ ❌ Not tested │ —                             │
  ├─────────────────────────┼───────────────┼───────────────────────────────┤
  │ cancel_purchase_order   │ ❌ Not tested │ —                             │
  └─────────────────────────┴───────────────┴───────────────────────────────┘

  ---
  6. How Far We've Tested

  - Total actions in system: ~91 (confirmed in apps/api/routes/p0_actions_routes.py)
  - Actions in _ACTION_ENTITY_MAP (ledger-tracked mutations): 36
  - Shards covering actions 33–40: ~50+ actions tested across all patterns
  - Estimated coverage: ~55% of all actions have at least an advisory or hard-proof test

  Untested actions to tackle next (from _ACTION_ENTITY_MAP and inline handlers):
  submit_purchase_order, approve_purchase_order, mark_po_received, cancel_purchase_order
  create_work_order, create_work_order_from_fault
  get_document_url, delete_document
  view_shopping_list_history (read action)
  add_parts_to_work_order
  update_running_hours (alias of record_equipment_hours)
  promote_candidate_to_part (chief_engineer only — needs different JWT)

  ---
  7. Roles — What You Need to Know

  There are three role fixtures: captainPage, hodPage, crewPage. They load auth state from:
  apps/web/playwright/.auth/captain.json
  apps/web/playwright/.auth/hod.json
  apps/web/playwright/.auth/crew.json

  CRITICAL: All three files currently resolve to the same captain JWT (x@alex-short.com, sub: a35cad0b-02ff-4287-b6e4-17c96fa6a424).
   Crew and HOD auth states have never been separately provisioned. This means:

  - All RBAC tests that use crewPage or hodPage are testing the captain, not actual crew/HOD
  - All crew 403 tests from shards 33/34 have been test.skip()-d (per the plan)
  - If you need real RBAC coverage, callActionAs (from shard-34 helpers) lets you mint a JWT for any user with any role

  The captain user ID is hardcoded in some tests: a35cad0b-02ff-4287-b6e4-17c96fa6a424. This is the only fully-tested identity.

  supabaseAdmin: This is the service-role Supabase client used for DB verification. It uses SUPABASE_SERVICE_KEY and
  NEXT_PUBLIC_SUPABASE_URL from RBAC_CONFIG. It bypasses RLS entirely. Always use this for DB state polls — never use a user-role
  client for verification.

  ---
  8. How to Run Tests (Env Vars)

  Never load .env.e2e — it points to localhost:3000 and breaks the global-setup auth. Pass env vars directly:

  cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/web

  SUPABASE_JWT_SECRET='ep2o/+mEQD/b54M8W50Vk3GrsuVayQZfValBnshte7yaZtoIGDhb9ffFQNU31su109d2wBz8WjSNX6wc3MiEFg==' \
  SUPABASE_SERVICE_KEY='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI
  6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY' \
  TEST_YACHT_ID='85fe1119-b04c-41ac-80f1-829d23322598' \
  E2E_NO_SERVER=1 npx playwright test \
    --project=shard-38-fault-actions \
    --reporter=list

  E2E_NO_SERVER=1 prevents Playwright from trying to start a dev server. The tests hit production directly.

  ---
  9. Known Backend Bugs (Documented in Advisory Tests)

  ┌───────────────────────────────────┬────────────────────────┬───────────┬───────────────────────────────────────────────────┐
  │                Bug                │         Action         │ Advisory  │                       Error                       │
  │                                   │                        │   Shard   │                                                   │
  ├───────────────────────────────────┼────────────────────────┼───────────┼───────────────────────────────────────────────────┤
  │ source_type NOT NULL ignored      │ add_to_shopping_list   │ 35        │ 500 from DB constraint                            │
  ├───────────────────────────────────┼────────────────────────┼───────────┼───────────────────────────────────────────────────┤
  │ Data model split (two stock       │                        │           │ 409 insufficient stock (receive_part writes to    │
  │ systems)                          │ consume_part           │ 35        │ pms_inventory_transactions but consume_part reads │
  │                                   │                        │           │  pms_parts.quantity_on_hand)                      │
  ├───────────────────────────────────┼────────────────────────┼───────────┼───────────────────────────────────────────────────┤
  │ Python                            │ upsert_hours_of_rest   │ 37        │ 500 Python client bug                             │
  │ SyncQueryRequestBuilder.select()  │                        │           │                                                   │
  ├───────────────────────────────────┼────────────────────────┼───────────┼───────────────────────────────────────────────────┤
  │ NoneType.data                     │ create_monthly_signoff │ 37        │ 500 Python exception                              │
  ├───────────────────────────────────┼────────────────────────┼───────────┼───────────────────────────────────────────────────┤
  │ user_role unbound variable        │ delete_shopping_item   │ 39        │ 500 Python scoping bug                            │
  └───────────────────────────────────┴────────────────────────┴───────────┴───────────────────────────────────────────────────┘

  ---
  10. The Two Biggest Pitfalls — Response Format Mismatches

  There are two distinct response formats and you WILL get it wrong the first time if you don't check:

  Format A — Flat (most older/inline actions):
  {"status": "success", "message": "...", "some_id": "...", "action": "...", "execution_id": "..."}
  Access: result.data.status, result.data.some_id

  Format B — Wrapped (newer actions using ResponseBuilder.success()):
  {"success": true, "data": {"the_id": "...", "nested_object": {...}}, "message": "..."}
  Access: result.data.success, result.data.data.the_id

  Format C — Semi-wrapped (actions like add_to_handover):
  {"status": "success", "action": "add_to_handover", "result": {"item_id": "...", "handover_item": {...}}, "message": "..."}
  Access: result.data.status, result.data.result.item_id

  Rule: Always add console.log([JSON] action_name: ${JSON.stringify(result.data)}) and look at the actual output before writing
  assertions. Don't assume.

  Shopping list actions all use Format B. Report_fault, diagnose_fault, mark_fault_false_alarm use Format A or C. add_to_handover
  uses Format C.

  ---
  11. Field Name Traps (Validation Gate vs Handler)

  The route file p0_actions_routes.py has a REQUIRED_FIELDS dict (around line 860–900) that is checked before the handler runs.
  Sometimes the required field name differs from what the handler parameter is called:

  ┌─────────────────────────┬──────────────────────────┬────────────────────────────────────────────────────────┐
  │         Action          │ Validation gate requires │                  Handler extracts as                   │
  ├─────────────────────────┼──────────────────────────┼────────────────────────────────────────────────────────┤
  │ update_equipment_status │ new_status               │ Uses new_status ✅                                     │
  ├─────────────────────────┼──────────────────────────┼────────────────────────────────────────────────────────┤
  │ add_to_handover         │ title                    │ summary = payload.get("summary") or title — pass title │
  ├─────────────────────────┼──────────────────────────┼────────────────────────────────────────────────────────┤
  │ create_purchase_request │ title                    │ Proceeds to signature check — still requires signature │
  └─────────────────────────┴──────────────────────────┴────────────────────────────────────────────────────────┘

  Always pass what the validation gate requires, not what the handler's Python signature says.

  ---
  12. DB Routing: Two Different Supabase Clients

  The API has TWO ways to talk to the database:

  1. Inline route handlers (e.g., update_work_order, complete_work_order): use get_tenant_supabase_client(tenant_alias) —
  dynamically resolves from JWT context
  2. Handler class methods (e.g., diagnose_fault, mark_fault_false_alarm): use self.db initialized at startup with the master
  Supabase URL

  The supabaseAdmin client in tests uses RBAC_CONFIG.supabaseUrl = https://vzsohavtuotocgrfkfyd.supabase.co (the master project). If
   self.db in a handler class writes to a different URL, the poll will time out. This is why diagnose_fault and
  mark_fault_false_alarm use weaker assertions (checking resolved_at or updated_at exists rather than specific status values).

  If a HARD PROOF DB poll times out even though the action returns 200, suspect this DB routing split and fall back to checking
  resolved_at/updated_at is not null.

  ---
  13. The callActionDirect Mechanism

  Located at apps/web/e2e/shard-34-lens-actions/helpers.ts. This is used by every shard 34-40:

  - Mints a fresh JWT using SUPABASE_JWT_SECRET env var
  - POSTs to ${API_URL}/v1/actions/execute
  - Always sends context: { yacht_id: RBAC_CONFIG.yachtId } alongside the payload
  - Uses page.evaluate() to run the fetch inside the browser context
  - Returns { status: number, data: Record<string, unknown> }

  The body structure is always:
  {
    "action": "action_name",
    "context": { "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598" },
    "payload": { ...action-specific fields... }
  }

  Some HOR actions also need yacht_id inside the payload (not just context) — the HOR handlers validate from payload directly. Pass
  it in both places for those.

  ---
  14. The seedFault / seedWorkOrder Fixtures

  Located in apps/web/e2e/rbac-fixtures.ts. These insert directly via supabaseAdmin (bypassing the action API) into pms_faults and
  pms_work_orders. They include cleanup teardown.

  - seedFault creates with no explicit status — DB default applies (should be 'open')
  - seedWorkOrder creates with status: 'open'
  - Both require yacht_id = RBAC_CONFIG.yachtId
  - getExistingEquipment, getExistingPart are read-only (no teardown needed)

  ---
  15. Shard Configuration in playwright.config.ts

  Every new shard must be registered in apps/web/playwright.config.ts under projects: [...]. Pattern:

  {
    name: 'shard-XX-name',
    testDir: './e2e/shard-XX-name',
    dependencies: ['setup'],
    use: { ...devices['Desktop Chrome'] },
  },

  Current shards registered: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40.

  ---
  16. Skills and Superpowers — When to Use What

  /superpowers — invoke this at the START of any session, especially for complex multi-file work. Key sub-skills:

  - /superpowers:executing-plans — when you have a written plan and need to execute it step by step
  - /superpowers:systematic-debugging — when a test fails and you need to diagnose root cause before fixing. USE THIS instead of
  guessing at fixes.
  - /superpowers:verification-before-completion — before claiming "all tests pass", verify with an actual test run
  - /superpowers:dispatching-parallel-agents — when writing multiple independent spec files at once

  /gsd:progress — run at session start to understand where the project is in its roadmap. The .planning/ directory has the canonical
   state.

  /gsd:plan-phase — use before starting a new wave of test coverage. Don't just code — plan first.

  /core:review — run before finalizing any spec file to check it against standards.

  Explore agent (subagent_type: 'Explore') — use this when you need to understand backend handler signatures, response formats,
  required fields, or table names BEFORE writing tests. Much faster than reading files manually when you need to survey across 5+
  handler files.

  Plan agent — use when scoping the next batch of actions to test. It can survey what's untested and propose a logical grouping.

  ---
  17. Circular Errors and Common Pitfalls

  Pitfall 1: Loading .env.e2e
  The file at apps/web/.env.e2e sets E2E_BASE_URL=http://localhost:3000. If this gets loaded, global-setup will try to authenticate
  against a local server that doesn't exist and fail with a network error. Always pass env vars on the command line with
  E2E_NO_SERVER=1.

  Pitfall 2: Assuming "200 success" = DB write happened
  Handler class methods (self.db) and inline route handlers use different Supabase connections. An action can return 200 while
  writing to a DB your poll can't see. Always verify: if the poll times out despite 200, weaken to checking resolved_at/updated_at
  not null, and mark it advisory.

  Pitfall 3: Wrapping format assumptions
  create_shopping_list_item returns {success:true, data:{shopping_list_item_id}} (Format B). add_to_handover returns
  {status:'success', result:{item_id}} (Format C). Never assume — always log and read the actual response first.

  Pitfall 4: The new_status vs status field
  update_equipment_status validation gate requires new_status. If you pass status you get 400 "Missing required field(s):
  new_status".

  Pitfall 5: add_to_handover needs title, not summary
  The validation gate at line 880 of p0_actions_routes.py requires title. The handler internally maps title → summary. Pass title
  with at least 10 characters.

  Pitfall 6: The _ACTION_ENTITY_MAP is not exhaustive
  Many actions exist in the system that are NOT in _ACTION_ENTITY_MAP — they work fine but don't write to ledger_events. Don't
  conclude an action is broken just because no ledger entry appears.

  Pitfall 7: pms_handover vs handover_items
  The old table was pms_handover. It was consolidated into handover_items (no pms_ prefix). Some read handlers in
  p3_read_only_handlers.py still query pms_handover. The write path for add_to_handover uses handover_items. When polling for
  add_to_handover results, query .from('handover_items'), not .from('pms_handover').

  Pitfall 8: transfer_part missing from _ACTION_ENTITY_MAP
  This was identified in the shard-33/34 fix plan (item #7). The plan says to add "transfer_part": ("part", "part_id") to the map —
  check if this was actually done before writing a ledger poll test for it.

  Pitfall 9: promote_candidate_to_part role restriction
  This action is restricted to chief_engineer and manager roles. The captain role is rejected with 403. Testing this requires
  callActionAs with a custom JWT that has role: 'chief_engineer'.

  ---
  18. Important File Locations

  apps/web/e2e/rbac-fixtures.ts                    — All fixture definitions + RBAC_CONFIG
  apps/web/e2e/shard-34-lens-actions/helpers.ts    — callActionDirect, callActionAs, pollLedger, generateFreshJwt
  apps/web/e2e/shard-33-lens-actions/helpers.ts    — BASE_URL, API_URL (imported by all shards)
  apps/web/playwright.config.ts                    — Shard registration
  apps/api/routes/p0_actions_routes.py             — THE main action router (~6400 lines). Required fields at ~860,
  _ACTION_ENTITY_MAP at ~117, inline handlers throughout
  apps/api/handlers/fault_mutation_handlers.py     — report_fault, diagnose_fault, mark_fault_false_alarm etc
  apps/api/handlers/handover_handlers.py           — add_to_handover
  apps/api/handlers/p1_purchasing_handlers.py      — create_purchase_request
  apps/api/handlers/equipment_handlers.py          — update_equipment_status adapter
  apps/api/handlers/equipment_utils.py             — VALID_EQUIPMENT_STATUSES
  apps/api/handlers/schema_mapping.py              — Table name mappings
  /Users/celeste7/.claude/plans/linked-plotting-charm.md  — The shard-33/34 fix plan (COMPLETED)

  ---
  19. The State of the Codebase Right Now

  - All shards 33–40 are fully green as of this handover
  - 19 tests in shards 35–37 (previously debugged)
  - 13 tests in shards 38–40 (just completed)
  - The plan at /Users/celeste7/.claude/plans/linked-plotting-charm.md is fully executed
  - The next agent should run /gsd:progress to understand what milestone phase is current, then scope Wave 4 (shards 41+) to cover
  the remaining ~40 untested actions

  ---
  20. One Thing to Always Do First

  Run /gsd:progress at the start of every session. The .planning/ directory has the GSD roadmap with phases up to 14+. The test
  coverage work sits outside those formal phases (it's been done ad-hoc). The next formal phase the project is working toward may be
   something entirely different from test coverage — check before assuming "add more E2E tests" is the right thing to do.

