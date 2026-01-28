AGENT BRIEFING: CelesteOS Cloud PMS                                      
                                                                           
  Copy this entire prompt to the next Claude session.                      
                                                                           
  ---                                                                      
  WHAT THIS PROJECT IS                                                     
                                                                           
  CelesteOS Cloud PMS is a yacht Planned Maintenance System with a natural 
  language interface. Crew speaks naturally → GPT-4o-mini extracts entities
   → System maps to capabilities → UI shows action buttons → Backend       
  executes maintenance actions.                                            
                                                                           
  The core pipeline:                                                       
  User: "The generator is overheating"                                     
      ↓                                                                    
  /search endpoint (GPT-4o-mini extracts: equipment="generator",           
  symptom="overheating")                                                   
      ↓                                                                    
  Maps to capabilities → Returns available actions                         
      ↓                                                                    
  UI shows: [Diagnose] [View History] [View Manual]                        
      ↓                                                                    
  /v1/actions/execute → Handler processes → Writes to DB                   
                                                                           
  ---                                                                      
  CURRENT STATE (as of 2026-01-22)                                         
                                                                           
  Handlers Implemented:     81/81  (100%)                                  
  Actions Returning 200:    61/64  (95%)                                   
  NL Tests Passing:         64/64  (100%)                                  
  Production Verified:      1/64   (1.5%)  ← THIS IS THE GAP               
                                                                           
  The 3 "failures" are NOT bugs - they're correct business logic           
  rejections:                                                              
  - show_manual_section → "No manual available" (equipment has no manual)  
  - create_work_order_from_fault → "WO already exists" (duplicate          
  prevention)                                                              
  - log_part_usage → "Not enough stock" (stock validation)                 
                                                                           
  ---                                                                      
  CRITICAL FILE LOCATIONS                                                  
  What: ALL 81 action handlers                                             
  Where: apps/api/routes/p0_actions_routes.py (4,160 lines)                
  ────────────────────────────────────────                                 
  What: All 64 action definitions                                          
  Where: tests/fixtures/microaction_registry.ts                            
  ────────────────────────────────────────                                 
  What: Health check tests                                                 
  Where: tests/e2e/diagnostic_baseline.spec.ts                             
  ────────────────────────────────────────                                 
  What: NL coverage tests                                                  
  Where: tests/e2e/nl_to_action_mapping.spec.ts                            
  ────────────────────────────────────────                                 
  What: Full E2E flow tests                                                
  Where: tests/e2e/chat_to_action.spec.ts                                  
  ────────────────────────────────────────                                 
  What: Test data discovery                                                
  Where: tests/helpers/test-data-discovery.ts                              
  ────────────────────────────────────────                                 
  What: Handover docs                                                      
  Where: _HANDOVER/ folder                                                 
  ---                                                                      
  THE 7 ACTION CLUSTERS (64 total actions)                                 
  ┌────────────────────┬───────┬─────────────────────────────────────┐     
  │      Cluster       │ Count │               Purpose               │     
  ├────────────────────┼───────┼─────────────────────────────────────┤     
  │ fix_something      │ 10    │ Fault diagnosis, repair guidance    │     
  ├────────────────────┼───────┼─────────────────────────────────────┤     
  │ do_maintenance     │ 16    │ Work orders, checklists, worklists  │     
  ├────────────────────┼───────┼─────────────────────────────────────┤     
  │ manage_equipment   │ 9     │ Equipment details, history, manuals │     
  ├────────────────────┼───────┼─────────────────────────────────────┤     
  │ control_inventory  │ 7     │ Parts stock, orders, usage          │     
  ├────────────────────┼───────┼─────────────────────────────────────┤     
  │ communicate_status │ 10    │ Handovers, summaries, photos        │     
  ├────────────────────┼───────┼─────────────────────────────────────┤     
  │ comply_audit       │ 5     │ Hours of rest, compliance           │     
  ├────────────────────┼───────┼─────────────────────────────────────┤     
  │ procure_suppliers  │ 7     │ Purchase requests, deliveries       │     
  └────────────────────┴───────┴─────────────────────────────────────┘     
  ---                                                                      
  DATABASE SCHEMA - WHAT YOU NEED TO KNOW                                  
                                                                           
  Multi-tenant architecture:                                               
  - Master DB (Supabase) → User management, yacht registry                 
  - Tenant DB (Supabase) → All yacht-specific data                         
                                                                           
  Key tables (ALL prefixed with pms_):                                     
  pms_equipment        → Equipment/machinery on yacht                      
  pms_faults           → Reported faults/issues                            
  pms_work_orders      → Maintenance work orders                           
  pms_parts            → Spare parts inventory                             
  pms_checklist_items  → Maintenance checklist items                       
  pms_documents        → Uploaded documents/manuals                        
  handovers            → Shift handover records (NO prefix!)               
  worklist_items       → Worklist tasks (NOT worklist_tasks!)              
  purchase_requests    → Purchase requests                                 
  audit_log            → All action audit trail                            
                                                                           
  RLS (Row Level Security):                                                
  - ALL queries must include yacht_id                                      
  - Without it, queries return empty even if data exists                   
  - Service role key bypasses RLS for testing                              
                                                                           
  ---                                                                      
  COLUMN NAME TRAPS (THESE WILL WASTE YOUR TIME)                           
                                                                           
  The code uses WRONG column names. Always verify before coding:           
  ┌────────────┬──────────────────────────┬──────────────────┐             
  │   Table    │        Code Uses         │  Actual Column   │             
  ├────────────┼──────────────────────────┼──────────────────┤             
  │ pms_parts  │ current_quantity_onboard │ quantity_on_hand │             
  ├────────────┼──────────────────────────┼──────────────────┤             
  │ pms_parts  │ min_quantity             │ quantity_minimum │             
  ├────────────┼──────────────────────────┼──────────────────┤             
  │ pms_parts  │ location                 │ storage_location │             
  ├────────────┼──────────────────────────┼──────────────────┤             
  │ documents  │ file_path                │ storage_path     │             
  ├────────────┼──────────────────────────┼──────────────────┤             
  │ pms_faults │ fault_code               │ fault_number     │             
  └────────────┴──────────────────────────┴──────────────────┘             
  Table name traps:                                                        
  ┌─────────────────┬─────────────────────┐                                
  │    Expected     │       Actual        │                                
  ├─────────────────┼─────────────────────┤                                
  │ handover        │ handovers           │                                
  ├─────────────────┼─────────────────────┤                                
  │ checklist_items │ pms_checklist_items │                                
  ├─────────────────┼─────────────────────┤                                
  │ equipment       │ pms_equipment       │                                
  ├─────────────────┼─────────────────────┤                                
  │ worklist_tasks  │ worklist_items      │                                
  └─────────────────┴─────────────────────┘                                
  Always verify first:                                                     
  SELECT column_name FROM information_schema.columns WHERE table_name =    
  'pms_parts';                                                             
                                                                           
  ---                                                                      
  TEST PAYLOAD MISMATCHES (KNOWN ISSUES)                                   
                                                                           
  Tests send wrong field names. These cause 400 errors:                    
  ┌───────────────┬─────────────────┐                                      
  │  Test Sends   │ Handler Expects │                                      
  ├───────────────┼─────────────────┤                                      
  │ photo         │ photo_url       │                                      
  ├───────────────┼─────────────────┤                                      
  │ assignee_id   │ assigned_to     │                                      
  ├───────────────┼─────────────────┤                                      
  │ yacht_id      │ vessel_id       │                                      
  ├───────────────┼─────────────────┤                                      
  │ section_query │ section_id      │                                      
  └───────────────┴─────────────────┘                                      
  To find what a handler expects:                                          
  grep -A 5 'elif action == "add_fault_photo"'                             
  apps/api/routes/p0_actions_routes.py                                     
                                                                           
  ---                                                                      
  AUTH & JWT                                                               
                                                                           
  Environment variables needed:                                            
  MASTER_SUPABASE_URL=https://xxx.supabase.co                              
  MASTER_SUPABASE_SERVICE_ROLE_KEY=eyJ...                                  
  TENANT_SUPABASE_URL=https://yyy.supabase.co                              
  TENANT_SUPABASE_SERVICE_ROLE_KEY=eyJ...                                  
  TEST_YACHT_ID=85fe1119-b04c-41ac-80f1-829d23322598                       
  TEST_USER_ID=a35cad0b-02ff-4287-b6e4-17c96fa6a424                        
                                                                           
  Auth flow:                                                               
  - JWT tokens from Supabase Auth                                          
  - Service role key bypasses RLS (use for testing)                        
  - JWT_SECRET must match Supabase project secret                          
                                                                           
  Common auth errors:                                                      
  - 401 → Token expired, re-authenticate                                   
  - 403 → RLS policy blocking, use service role                            
  - Empty results → Missing yacht_id in query                              
                                                                           
  ---                                                                      
  TESTING WITH PLAYWRIGHT                                                  
                                                                           
  Essential commands:                                                      
  # Health check (expect 61/64 pass)                                       
  npx playwright test tests/e2e/diagnostic_baseline.spec.ts                
  --project=e2e-chromium                                                   
                                                                           
  # NL coverage (expect 64/64 pass)                                        
  npx playwright test tests/e2e/nl_to_action_mapping.spec.ts               
  --project=e2e-chromium                                                   
                                                                           
  # Single action                                                          
  npx playwright test -g "diagnose_fault"                                  
                                                                           
  # Debug mode with UI                                                     
  npx playwright test --debug                                              
  npx playwright test --ui                                                 
                                                                           
  Test data discovery pattern:                                             
  - tests/helpers/test-data-discovery.ts finds real entity IDs             
  - Queries Supabase for existing equipment, faults, work orders, etc.     
  - If entity doesn't exist, test is skipped (not failed)                  
                                                                           
  Timeout issues:                                                          
  test('my test', async () => {                                            
    test.setTimeout(60000); // 60 seconds                                  
  });                                                                      
                                                                           
  ---                                                                      
  CI/CD & DEPLOYMENT                                                       
                                                                           
  Platforms:                                                               
  - Backend: Render (Python FastAPI)                                       
  - Frontend: Vercel (Next.js)                                             
  - Database: Supabase (PostgreSQL)                                        
                                                                           
  Render config: render.yaml                                               
  # Backend API deployment                                                 
                                                                           
  Vercel: Connected to GitHub, auto-deploys on push to main                
                                                                           
  GitHub Actions: .github/ folder                                          
  - Runs tests on PR                                                       
  - Deploys on merge to main                                               
                                                                           
  Common deployment issues:                                                
  - Environment variables not set in Render/Vercel                         
  - Supabase connection strings different per environment                  
  - Service role keys have different permissions than user tokens          
                                                                           
  ---                                                                      
  THE MAIN GAP TO CLOSE                                                    
                                                                           
  What exists: 95% of handlers return HTTP 200                             
  What's missing: Proof they actually write to the database                
                                                                           
  Only 1 action (acknowledge_fault) has been verified end-to-end:          
  1. ✅ API returns 200                                                    
  2. ✅ Database row created/updated                                       
  3. ✅ Audit log entry exists                                             
                                                                           
  The remaining 63 mutation actions need this verification.                
                                                                           
  How to verify:                                                           
  -- Before action                                                         
  SELECT * FROM pms_work_orders WHERE id = 'xxx';                          
                                                                           
  -- Run action via API                                                    
                                                                           
  -- After action                                                          
  SELECT * FROM pms_work_orders WHERE id = 'xxx';                          
  SELECT * FROM audit_log WHERE entity_id = 'xxx';                         
                                                                           
  ---                                                                      
  REPEATED MISTAKES I MADE (DON'T REPEAT)                                  
                                                                           
  1. Assumed column names match code → Always verify schema first          
  2. Assumed table names are singular → Many are plural or prefixed        
  3. Tested without yacht_id → RLS returns empty, not error                
  4. Treated 400 as failure → Some are correct business logic              
  5. Didn't check handler's REQUIRED_FIELDS → Test payloads mismatched     
  6. Used cd commands in bash → Causes "too many arguments" errors, use    
  full paths                                                               
  7. Ran summary tests → They re-run all 64 actions and timeout            
                                                                           
  ---                                                                      
  CONFUSION I STILL HAVE                                                   
                                                                           
  1. Why 81 handlers but only 64 actions? → Some actions have variants     
  (e.g., view vs. list)                                                    
  2. Which handlers actually write to DB? → Only acknowledge_fault is      
  verified                                                                 
  3. What's the relationship between microaction_registry and              
  p0_actions_routes? → Registry defines actions, routes implement them     
  4. How does tenant isolation work exactly? → RLS on yacht_id, but        
  implementation details unclear                                           
  5. Are the security patches (P0-001 through P0-008) actually working? →  
  Applied but not tested                                                   
                                                                           
  ---                                                                      
  WHAT'S LEFT TO DO (~38 hours)                                            
  ┌────────────────────────────────────────┬───────┐                       
  │                  Task                  │ Hours │                       
  ├────────────────────────────────────────┼───────┤                       
  │ Mutation proofs (63 actions)           │ 16    │                       
  ├────────────────────────────────────────┼───────┤                       
  │ Fix test payload mismatches (10 fixes) │ 1     │                       
  ├────────────────────────────────────────┼───────┤                       
  │ Security pen testing (13 patches)      │ 6.5   │                       
  ├────────────────────────────────────────┼───────┤                       
  │ Edge case tests                        │ 10    │                       
  ├────────────────────────────────────────┼───────┤                       
  │ Performance baselines                  │ 5     │                       
  └────────────────────────────────────────┴───────┘                       
  Suggested order:                                                         
  1. Fix payload mismatches first (makes future tests accurate)            
  2. Mutation proofs for high-value actions: create_work_order,            
  add_fault_note, mark_work_order_complete, order_part                     
  3. Remaining mutation proofs                                             
  4. Security testing                                                      
  5. Edge cases and performance                                            
                                                                           
  ---                                                                      
  QUICK START COMMANDS                                                     
                                                                           
  # Navigate to project                                                    
  cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS                         
                                                                           
  # Install deps                                                           
  npm install                                                              
  npx playwright install                                                   
                                                                           
  # Run health check                                                       
  npx playwright test tests/e2e/diagnostic_baseline.spec.ts                
  --project=e2e-chromium                                                   
                                                                           
  # Start backend locally                                                  
  cd apps/api && uvicorn main:app --reload --port 8000                     
                                                                           
  # Find a handler                                                         
  grep -A 30 'elif action == "create_work_order"'                          
  apps/api/routes/p0_actions_routes.py                                     
                                                                           
  # Count handlers                                                         
  grep -c 'elif action ==' apps/api/routes/p0_actions_routes.py  # Should  
  be 81                                                                    
                                                                           
  ---                                                                      
  FILES TO READ FIRST                                                      
                                                                           
  1. _HANDOVER/README.md → 60-second overview                              
  2. _HANDOVER/04_KNOWN_TRAPS.md → Save yourself hours                     
  3. apps/api/routes/p0_actions_routes.py → All handlers                   
  4. tests/fixtures/microaction_registry.ts → Action definitions           
                                                                           
  ---                                                                      
  GIT INFO                                                                 
                                                                           
  - Repo: https://github.com/shortalex12333/Cloud_PMS.git                  
  - Branch: main                                                           
  - Latest commit: 2a68c03 - "Reorganize repo - clean structure for new    
  engineers"                                                               
                                                                           
  ---                                                                      
  END OF BRIEFING    