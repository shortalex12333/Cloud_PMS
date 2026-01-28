                                                                                    
⏺ After completing those 8 schema-focused phases, here's what would still be missing for a complete 
  MVP:                                                                                              
                                                                                                    
  🟢 COMPLETED (After Your 8 Phases)                                                                
                                                                                                    
  - ✅ Database schema (all tables exist)                                                           
  - ✅ RLS policies (verified and working)                                                          
  - ✅ Data types validated                                                                         
  - ✅ Schema documentation                                                                         
  - ✅ Missing tables deployed                                                                      
  - ✅ Schema tests passing                                                                         
                                                                                                    
  ---                                                                                               
  🔴 MISSING: Frontend Implementation (Estimated: 2-3 weeks)                                        
                                                                                                    
  Phase 9: UI Component Development                                                                 
                                                                                                    
  - Build entity detail cards (Equipment, Fault, Work Order, Part, PO)                              
  - Build action button layout (Primary, More ▾, Evidence, Safety)                                  
  - Build action forms (47 MVP actions = 47 forms)                                                  
  - Build signature capture UI ("tap accept")                                                       
  - Build toast notifications (success/error)                                                       
  - Build search results list                                                                       
  - Build loading states (spinners, disabled states)                                                
                                                                                                    
  Phase 10: Situation State Machine                                                                 
                                                                                                    
  - Implement IDLE → CANDIDATE → ACTIVE → COMMIT → COOLDOWN transitions                             
  - Handle back navigation (ACTIVE → CANDIDATE)                                                     
  - Handle deep links (IDLE → ACTIVE)                                                               
  - Handle resumable situations (receiving sessions, checklists)                                    
  - Implement cooldown timers (3-5s)                                                                
                                                                                                    
  Phase 11: Action Surfacing Logic                                                                  
                                                                                                    
  - Implement ENTITY_ACTION_SURFACING.md rules                                                      
  - Hide actions in CANDIDATE state (Rule 1)                                                        
  - Show 2-3 Primary actions in ACTIVE state                                                        
  - Populate "More ▾" dropdown                                                                      
  - Populate Evidence/Related section                                                               
  - Apply STOP conditions (status checks, permission checks)                                        
                                                                                                    
  Phase 12: RAG Integration (Frontend)                                                              
                                                                                                    
  - Display RAG suggestions (yellow banners)                                                        
  - Prefill form fields from RAG                                                                    
  - Show evidence links with context                                                                
  - Handle RAG failures gracefully                                                                  
                                                                                                    
  ---                                                                                               
  🟠 MISSING: Backend Handler Fixes (Estimated: 1-2 weeks)                                          
                                                                                                    
  From SYSTEM_INVENTORY.md:                                                                         
  - Only 1/64 handlers proven to write database                                                     
  - 60/64 don't create audit logs                                                                   
  - No transaction boundaries                                                                       
  - Inconsistent error handling                                                                     
                                                                                                    
  Phase 13: Handler Audit & Fixes (Per ACTION_IO_MATRIX.md)                                         
                                                                                                    
  # Current state (61 handlers):                                                                    
  async def diagnose_fault(fault_id, ...):                                                          
      fault = db.table("pms_faults").select("*").eq("id", fault_id).single()                        
      # ❌ No permission check                                                                      
      # ❌ No audit log                                                                             
      # ❌ No transaction                                                                           
      # ❌ Returns 200 but may not write                                                            
      return {"status": "success", "diagnostic_steps": [...]}                                       
                                                                                                    
  # Required MVP state:                                                                             
  async def diagnose_fault(fault_id, yacht_id, user_id, params):                                    
      # ✅ Permission check                                                                         
      if not has_permission(user_id, yacht_id, "diagnose_fault"):                                   
          return ResponseBuilder.error("FORBIDDEN")                                                 
                                                                                                    
      # ✅ Transaction boundary                                                                     
      with db.transaction():                                                                        
          # ✅ Write diagnosis                                                                      
          db.table("pms_faults").update({                                                           
              "metadata": {"diagnosis": params["diagnosis"]}                                        
          }).eq("id", fault_id).execute()                                                           
                                                                                                    
          # ✅ Create audit log                                                                     
          db.table("pms_audit_log").insert({                                                        
              "action": "diagnose_fault",                                                           
              "entity_type": "fault",                                                               
              "entity_id": fault_id,                                                                
              "user_id": user_id,                                                                   
              "new_values": params                                                                  
          }).execute()                                                                              
                                                                                                    
          # ✅ Create ledger event (if signature required)                                          
          if params.get("signature"):                                                               
              db.table("ledger_events").insert({...}).execute()                                     
                                                                                                    
      return ResponseBuilder.success(...)                                                           
                                                                                                    
  Tasks:                                                                                            
  - Add permission checks to all 47 MVP handlers                                                    
  - Add audit log writes to all MUTATE handlers                                                     
  - Wrap multi-table writes in transactions                                                         
  - Standardize error responses (ResponseBuilder pattern)                                           
  - Add signature validation for MUTATE_HIGH actions                                                
  - Verify database writes (not just HTTP 200)                                                      
                                                                                                    
  ---                                                                                               
  🟡 MISSING: RAG Infrastructure (Estimated: 1 week)                                                
                                                                                                    
  From SYSTEM_INVENTORY.md (line 362):                                                              
  Status: Partially implemented. GraphRAG query exists but search chunks table has RLS issues.      
                                                                                                    
  Phase 14: RAG Completion                                                                          
                                                                                                    
  - Fix search chunks RLS policies                                                                  
  - Implement prefill logic (extract suggested values from RAG)                                     
  - Implement evidence link generation                                                              
  - Implement manual section search                                                                 
  - Test RAG suggestions for all 47 actions                                                         
  - Handle RAG timeouts/failures                                                                    
                                                                                                    
  Example RAG integration:                                                                          
  # In diagnose_fault handler:                                                                      
  rag_suggestions = await rag_service.get_suggestions(                                              
      entity_type="fault",                                                                          
      entity_id=fault_id,                                                                           
      action="diagnose_fault"                                                                       
  )                                                                                                 
  # Returns: {                                                                                      
  #   "prefill": {"diagnosis": "Coolant pump seal failure (Manual pg. 47)"},                        
  #   "evidence": [{"type": "manual", "reference": "pg. 47", "text": "..."}]                        
  # }                                                                                               
                                                                                                    
  ---                                                                                               
  🟢 MISSING: Testing (Estimated: 1 week)                                                           
                                                                                                    
  From SYSTEM_INVENTORY.md (lines 318-327):                                                         
  - 1/64 actions have database mutation tests                                                       
  - 0/64 actions have audit log tests                                                               
  - 0/64 actions have RLS tests                                                                     
                                                                                                    
  Phase 15: Database Mutation Tests                                                                 
                                                                                                    
  // Example: Verify diagnose_fault actually writes                                                 
  test('diagnose_fault writes to database', async ({ request, db }) => {                            
    const response = await request.post('/v1/actions/execute', {                                    
      data: { action: 'diagnose_fault', payload: {...} }                                            
    });                                                                                             
                                                                                                    
    // Verify DB write                                                                              
    const fault = await db.from('pms_faults').select('metadata').eq('id', faultId).single();        
    expect(fault.metadata.diagnosis).toBe("Expected diagnosis text");                               
                                                                                                    
    // Verify audit log                                                                             
    const audit = await db.from('pms_audit_log').select('*').eq('entity_id', faultId).single();     
    expect(audit.action).toBe('diagnose_fault');                                                    
  });                                                                                               
                                                                                                    
  Tasks:                                                                                            
  - Write database mutation tests for all 47 MVP actions                                            
  - Write audit log verification tests for all MUTATE actions                                       
  - Write RLS tests (verify yacht isolation)                                                        
  - Write permission tests (verify role checks)                                                     
  - Write signature validation tests                                                                
                                                                                                    
  ---                                                                                               
  🔵 MISSING: Integration & E2E (Estimated: 3-5 days)                                               
                                                                                                    
  Phase 16: Full Flow Testing                                                                       
                                                                                                    
  Test complete user journeys from SITUATIONS_CLARIFICATION.md:                                     
                                                                                                    
  Example: Sarah diagnoses fault (lines 356-418)                                                    
  test('Complete fault diagnosis flow', async ({ page }) => {                                       
    // Step 1: IDLE                                                                                 
    await page.goto('/');                                                                           
                                                                                                    
    // Step 2: IDLE → CANDIDATE (search)                                                            
    await page.fill('[data-testid="search-bar"]', 'gen 2 overheating');                             
    await page.press('[data-testid="search-bar"]', 'Enter');                                        
    await expect(page.locator('[data-testid="search-results"]')).toBeVisible();                     
    await expect(page.locator('[data-testid="action-button"]')).toHaveCount(0); // Rule 1           
                                                                                                    
    // Step 3: CANDIDATE → ACTIVE (click entity)                                                    
    await page.click('[data-testid="fault-F-456"]');                                                
    await expect(page.locator('[data-testid="entity-detail"]')).toBeVisible();                      
    await expect(page.locator('[data-testid="primary-action"]')).toHaveCount(3); // 2-3 primary     
                                                                                                    
    // Step 4: ACTIVE → ACTION_PREVIEW (click diagnose)                                             
    await page.click('[data-testid="action-diagnose-fault"]');                                      
    await expect(page.locator('[data-testid="action-form"]')).toBeVisible();                        
    await expect(page.locator('[data-testid="prefilled-diagnosis"]')).toContain('Coolant pump'); // 
  RAG                                                                                               
                                                                                                    
    // Step 5: ACTION_PREVIEW → COMMIT (confirm)                                                    
    await page.fill('[data-testid="diagnosis-field"]', 'Confirmed seal leaking');                   
    await page.click('[data-testid="confirm-button"]');                                             
    await expect(page.locator('[data-testid="loading-spinner"]')).toBeVisible();                    
                                                                                                    
    // Step 6: COMMIT → COOLDOWN (success)                                                          
    await expect(page.locator('[data-testid="success-toast"]')).toBeVisible();                      
    await expect(page.locator('[data-testid="success-toast"]')).toContain('Diagnosis saved');       
                                                                                                    
    // Step 7: COOLDOWN → ACTIVE (toast dismisses)                                                  
    await page.waitForTimeout(3000);                                                                
    await expect(page.locator('[data-testid="success-toast"]')).not.toBeVisible();                  
    await expect(page.locator('[data-testid="primary-action"]')).toBeEnabled();                     
  });                                                                                               
                                                                                                    
  ---                                                                                               
  🟣 MISSING: Deployment & Operations (Estimated: 2-3 days)                                         
                                                                                                    
  Phase 17: Deployment Pipeline                                                                     
                                                                                                    
  - CI/CD setup (GitHub Actions / GitLab CI)                                                        
  - Migration deployment strategy (blue-green? rolling?)                                            
  - Rollback procedures                                                                             
  - Environment variables management                                                                
  - Database backup strategy                                                                        
  - Monitoring/alerting setup                                                                       
                                                                                                    
  Phase 18: Production Readiness                                                                    
                                                                                                    
  - Load testing (performance benchmarks)                                                           
  - Security audit (penetration testing)                                                            
  - Compliance verification (audit logs, signatures)                                                
  - Disaster recovery plan                                                                          
  - On-call runbooks                                                                                
                                                                                                    
  ---                                                                                               
  📊 COMPLETE TASK BREAKDOWN                                                                        
  ┌────────────────────────┬────────┬────────────────┬──────────────────────────────────────┐       
  │        Category        │ Phases │ Estimated Time │            Blocking MVP?             │       
  ├────────────────────────┼────────┼────────────────┼──────────────────────────────────────┤       
  │ Schema (Your 8 Phases) │ 1-8    │ 3-5 days       │ ✅ YES                               │       
  ├────────────────────────┼────────┼────────────────┼──────────────────────────────────────┤       
  │ Frontend               │ 9-12   │ 2-3 weeks      │ ✅ YES                               │       
  ├────────────────────────┼────────┼────────────────┼──────────────────────────────────────┤       
  │ Backend Handlers       │ 13     │ 1-2 weeks      │ ✅ YES                               │       
  ├────────────────────────┼────────┼────────────────┼──────────────────────────────────────┤       
  │ RAG                    │ 14     │ 1 week         │ ⚠️ PARTIAL (can stub)                │       
  ├────────────────────────┼────────┼────────────────┼──────────────────────────────────────┤       
  │ Testing                │ 15-16  │ 1-2 weeks      │ ⚠️ PARTIAL (manual testing possible) │       
  ├────────────────────────┼────────┼────────────────┼──────────────────────────────────────┤       
  │ Deployment             │ 17-18  │ 1 week         │ ❌ NO (manual deploy OK for MVP)     │       
  └────────────────────────┴────────┴────────────────┴──────────────────────────────────────┘       
  Total estimated time: 6-9 weeks (assuming 1-2 engineers, frontend + backend split)                
                                                                                                    
  ---                                                                                               
  🎯 MINIMUM VIABLE PATH (3-4 Weeks)                                                                
                                                                                                    
  If you want to launch faster, here's what you could skip initially:                               
                                                                                                    
  Must Have (Blocking):                                                                             
                                                                                                    
  - ✅ Phases 1-8 (Your schema work)                                                                
  - ✅ Phase 9-11 (Frontend basics)                                                                 
  - ✅ Phase 13 (Handler fixes - at least audit logs + permissions)                                 
                                                                                                    
  Can Stub/Defer:                                                                                   
                                                                                                    
  - ⚠️ Phase 12 (RAG) - Stub with empty prefills, no suggestions                                    
  - ⚠️ Phase 14 (RAG Infrastructure) - Defer, show static suggestions                               
  - ⚠️ Phase 15-16 (Comprehensive testing) - Manual QA for MVP                                      
  - ⚠️ Phase 17-18 (Production ops) - Manual deploy, basic monitoring                               
                                                                                                    
  Critical Validation Needed:                                                                       
                                                                                                    
  From SYSTEM_INVENTORY.md:                                                                         
  Only 1/64 actions proven to write to database. HTTP 200 ≠ database mutation.                      
                                                                                                    
  You MUST verify handlers actually work (Phase 13) before launch. Current test suite only proves   
  HTTP responses, not database writes.                                                              
                                                                                                    
  ---                                                                                               
  🚨 RECOMMENDATION                                                                                 
                                                                                                    
  After your 8 phases, prioritize in this order:                                                    
                                                                                                    
  1. Phase 13 (Handler Audit) - CRITICAL                                                            
    - Pick 10 most-used MVP actions                                                                 
    - Verify they write to database                                                                 
    - Add audit logs                                                                                
    - Add permissions                                                                               
    - Test with real data                                                                           
  2. Phase 9-10 (Core Frontend) - CRITICAL                                                          
    - Entity detail cards                                                                           
    - Action buttons                                                                                
    - Forms for 10 priority actions                                                                 
    - Basic state machine                                                                           
  3. Phase 15 (Mutation Testing) - HIGH                                                             
    - Test 10 priority actions end-to-end                                                           
    - Verify DB writes                                                                              
    - Verify audit logs                                                                             
  4. Phase 11-12 (Polish) - MEDIUM                                                                  
    - Action surfacing rules                                                                        
    - RAG integration                                                                               
    - Remaining 37 action forms                                                                     
                                                                                            