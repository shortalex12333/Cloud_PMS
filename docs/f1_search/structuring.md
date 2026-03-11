╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
 3-Pillar Architecture: Ship This Week                                                                                   
                                                                                                                         
 Status: RBAC centralization ✅ COMPLETE (committed as 90df2bad)                                                         
 New Focus: Restructure codebase into 3 clear pillars to enable shipping                                                 
                                                                                                                         
 ---                                                                                                                     
 The Problem (6 Months, No Ship)                                                                                         
                                                                                                                         
 You're drowning in complexity because everything is connected to everything. The codebase has grown organically without 
  clear boundaries.                                                                                                      
                                                                                                                         
 Current Chaos (From Exploration)                                                                                        
 ┌──────────────────────────────────┬──────────────────────────────────────────────────────────┐                         
 │              Issue               │                          Impact                          │                         
 ├──────────────────────────────────┼──────────────────────────────────────────────────────────┤                         
 │ 3 different API calling patterns │ Direct fetch, actionClient, ActionHandler - inconsistent │                         
 ├──────────────────────────────────┼──────────────────────────────────────────────────────────┤                         
 │ Duplicate hooks                  │ usePartActions vs usePartsActions (both active!)         │                         
 ├──────────────────────────────────┼──────────────────────────────────────────────────────────┤                         
 │ Orphaned files                   │ .patch, .new files in source                             │                         
 ├──────────────────────────────────┼──────────────────────────────────────────────────────────┤                         
 │ 4 redundant search endpoints     │ F1, legacy, RAG, orchestrated                            │                         
 ├──────────────────────────────────┼──────────────────────────────────────────────────────────┤                         
 │ No clear ownership               │ Is button rendering Search or Display?                   │                         
 └──────────────────────────────────┴──────────────────────────────────────────────────────────┘                         
 ---                                                                                                                     
 The Vision: 3 Clear Pillars                                                                                             
                                                                                                                         
 ┌─────────────────────────────────────────────────────────────────────────────┐                                         
 │                              USER INTERFACE                                  │                                        
 │                         (SpotlightSearch input)                             │                                         
 └─────────────────────────────────────────────────────────────────────────────┘                                         
                                     │                                                                                   
                                     ▼                                                                                   
 ┌─────────────────────────────────────────────────────────────────────────────┐                                         
 │  PILLAR 1: SEARCH                                                           │                                         
 │  ═══════════════                                                            │                                         
 │  "I understand what you want and I find it"                                 │                                         
 │                                                                             │                                         
 │  • Entity extraction (5-stage pipeline)                                     │                                         
 │  • Intent detection (action vs navigation vs filter)                        │                                         
 │  • RAG pipeline (semantic + keyword + exact match)                          │                                         
 │  • Result ranking (RRF fusion)                                              │                                         
 │  • Snippet generation                                                       │                                         
 │                                                                             │                                         
 │  OUTPUT: SearchResult[] with snippets and suggested_actions[]               │                                         
 └─────────────────────────────────────────────────────────────────────────────┘                                         
                                     │                                                                                   
                                     ▼                                                                                   
 ┌─────────────────────────────────────────────────────────────────────────────┐                                         
 │  PILLAR 2: DISPLAY                                                          │                                         
 │  ════════════════                                                           │                                         
 │  "I show you what was found, beautifully"                                   │                                         
 │                                                                             │                                         
 │  • Lens components (12 entity types)                                        │                                         
 │  • Entity cards (search result summaries)                                   │                                         
 │  • Detail pages (full entity view)                                          │                                         
 │  • Button visibility (driven by permissions)                                │                                         
 │  • Navigation routing                                                       │                                         
 │                                                                             │                                         
 │  INPUT: Entity data + user permissions                                      │                                         
 │  OUTPUT: Rendered UI with clickable actions                                 │                                         
 └─────────────────────────────────────────────────────────────────────────────┘                                         
                                     │                                                                                   
                                     ▼                                                                                   
 ┌─────────────────────────────────────────────────────────────────────────────┐                                         
 │  PILLAR 3: ACTIONS                                                          │                                         
 │  ════════════════                                                           │                                         
 │  "I execute what you clicked"                                               │                                         
 │                                                                             │                                         
 │  • Action execution (create, update, delete)                                │                                         
 │  • Prefill logic (smart defaults)                                           │                                         
 │  • Validation (permissions already checked by RBAC)                         │                                         
 │  • Ledger logging (audit trail)                                             │                                         
 │  • State transitions                                                        │                                         
 │                                                                             │                                         
 │  INPUT: Action request + context                                            │                                         
 │  OUTPUT: Success/failure + updated entity                                   │                                         
 └─────────────────────────────────────────────────────────────────────────────┘                                         
                                                                                                                         
 ---                                                                                                                     
 SWOT Analysis                                                                                                           
                                                                                                                         
 Strengths ✅                                                                                                            
                                                                                                                         
 - Backend is well-structured (no circular dependencies)                                                                 
 - Permission system now centralized (lens_matrix.json) ← DONE                                                           
 - Action registry comprehensive (40 actions)                                                                            
 - Extraction pipeline solid (5-stage)                                                                                   
 - Lens components exist for all 12 types                                                                                
                                                                                                                         
 Weaknesses ❌                                                                                                           
                                                                                                                         
 - 3 different API calling patterns in frontend                                                                          
 - Duplicate hooks (usePartActions vs usePartsActions)                                                                   
 - Snippets broken (migration 45 not applied)                                                                            
 - 4 redundant search endpoints                                                                                          
 - No clear pillar boundaries                                                                                            
                                                                                                                         
 Opportunities 🎯                                                                                                        
                                                                                                                         
 - Consolidate to single API pattern                                                                                     
 - Delete 3 redundant search endpoints                                                                                   
 - Fix snippets with 2 changes                                                                                           
 - Ship by focusing on 20% that matters                                                                                  
                                                                                                                         
 Threats ⚠️                                                                                                              
                                                                                                                         
 - Adding more features before shipping                                                                                  
 - Refactoring without shipping                                                                                          
 - Trying to fix everything at once                                                                                      
                                                                                                                         
 ---                                                                                                                     
 Critical Bugs (Fix Before Ship)                                                                                         
                                                                                                                         
 Bug 1: Snippets Not Generating                                                                                          
                                                                                                                         
 Root Cause: Migration 45 adds search_text to RPC, but:                                                                  
 1. Migration never applied to production                                                                                
 2. Python SELECT doesn't include search_text                                                                            
                                                                                                                         
 Fix (30 minutes):                                                                                                       
 -- Step 1: Apply migration                                                                                              
 psql $DATABASE_URL -f database/migrations/45_f1_search_cards_with_search_text.sql                                       
                                                                                                                         
 # Step 2: f1_search_streaming.py:796                                                                                    
 # FROM:                                                                                                                 
 SELECT object_type, object_id, payload, fused_score, best_rewrite_idx, ranks, components                                
                                                                                                                         
 # TO:                                                                                                                   
 SELECT object_type, object_id, payload, search_text, fused_score, best_rewrite_idx, ranks, components                   
                                                                                                                         
 Bug 2: Duplicate Hooks                                                                                                  
 ┌────────────────────┬───────┬──────────────────────────┐                                                               
 │        File        │ Lines │          Status          │                                                               
 ├────────────────────┼───────┼──────────────────────────┤                                                               
 │ usePartActions.ts  │ 243   │ Used by inventory page   │                                                               
 ├────────────────────┼───────┼──────────────────────────┤                                                               
 │ usePartsActions.ts │ 332   │ Used by PartsLensContent │                                                               
 └────────────────────┴───────┴──────────────────────────┘                                                               
 Fix: Merge into single usePartActions.ts, update imports.                                                               
                                                                                                                         
 Bug 3: Orphaned Files                                                                                                   
                                                                                                                         
 rm apps/web/src/hooks/useEquipmentActions.ts.patch                                                                      
 rm apps/web/src/hooks/useReceivingActions.ts.new                                                                        
                                                                                                                         
 ---                                                                                                                     
 Gap Analysis                                                                                                            
                                                                                                                         
 Gap 1: No Contract Between Search → Display                                                                             
                                                                                                                         
 Current: Search returns raw data, Display guesses what to do.                                                           
                                                                                                                         
 Needed:                                                                                                                 
 interface SearchResult {                                                                                                
   entity_type: string;                                                                                                  
   entity_id: string;                                                                                                    
   payload: EntityPayload;                                                                                               
   snippet?: string;              // ← BROKEN (fix migration 45)                                                         
   suggested_actions: string[];   // ← MISSING                                                                           
 }                                                                                                                       
                                                                                                                         
 Gap 2: Button Rendering Scattered                                                                                       
                                                                                                                         
 Current: Each LensContent decides which buttons to show.                                                                
                                                                                                                         
 Fixed: Permission hooks now centralized (lens_matrix.json) ✅                                                           
                                                                                                                         
 Gap 3: Intent → Action Not Connected                                                                                    
                                                                                                                         
 Current: Filter inference detects "overdue work orders" but can't suggest actions.                                      
                                                                                                                         
 Needed: Intent → Action mapping for actionable queries.                                                                 
                                                                                                                         
 ---                                                                                                                     
 Proposed File Structure                                                                                                 
                                                                                                                         
 apps/web/src/                                                                                                           
 ├── search/                      # PILLAR 1                                                                             
 │   ├── components/                                                                                                     
 │   │   └── SpotlightSearch.tsx                                                                                         
 │   ├── hooks/                                                                                                          
 │   │   ├── useSearch.ts                                                                                                
 │   │   └── useFilterInference.ts                                                                                       
 │   └── lib/                                                                                                            
 │       └── filters/                                                                                                    
 │                                                                                                                       
 ├── display/                     # PILLAR 2                                                                             
 │   ├── components/                                                                                                     
 │   │   ├── lenses/              # All 12 lens contents                                                                 
 │   │   └── buttons/                                                                                                    
 │   │       └── ActionButtonBar.tsx                                                                                     
 │   └── hooks/                                                                                                          
 │       └── useButtonVisibility.ts                                                                                      
 │                                                                                                                       
 ├── actions/                     # PILLAR 3                                                                             
 │   ├── hooks/                                                                                                          
 │   │   └── useActionExecutor.ts # SINGLE action pattern                                                                
 │   └── lib/                                                                                                            
 │       └── actionClient.ts      # Consolidated API calls                                                               
 │                                                                                                                       
 └── permissions/                 # SHARED (already done!)                                                               
     ├── PermissionService.ts                                                                                            
     └── hooks/                                                                                                          
                                                                                                                         
 ---                                                                                                                     
 Ship This Week: Phased Approach                                                                                         
                                                                                                                         
 Phase 0: Critical Fixes (Day 1)                                                                                         
                                                                                                                         
 □ Apply migration 45 (snippets)                                                                                         
 □ Add search_text to Python SELECT                                                                                      
 □ Delete orphaned .patch/.new files                                                                                     
 □ Merge usePartActions + usePartsActions                                                                                
 □ Deploy and smoke test                                                                                                 
                                                                                                                         
 Phase 1: Consolidate Actions (Day 2)                                                                                    
                                                                                                                         
 □ Create unified useActionExecutor.ts                                                                                   
 □ Migrate all hooks to single API pattern                                                                               
 □ Delete redundant action hooks                                                                                         
                                                                                                                         
 Phase 2: Create Pillar Folders (Day 3)                                                                                  
                                                                                                                         
 □ Create /search/, /display/, /actions/ folders                                                                         
 □ Move SpotlightSearch → /search/                                                                                       
 □ Move lenses → /display/                                                                                               
 □ Update imports                                                                                                        
                                                                                                                         
 Phase 3: Ship (Day 4-5)                                                                                                 
                                                                                                                         
 □ Integration testing                                                                                                   
 □ Fix import errors                                                                                                     
 □ Deploy to production                                                                                                  
 □ SHIP IT 🚀                                                                                                            
                                                                                                                         
 ---                                                                                                                     
 What NOT To Do                                                                                                          
                                                                                                                         
 1. Don't add new features - Ship what works                                                                             
 2. Don't rename to _v2 - Use git branches                                                                               
 3. Don't keep duplicates "just in case" - Git has history                                                               
 4. Don't refactor everything - Incremental moves                                                                        
 5. Don't perfect the architecture - Good enough ships                                                                   
                                                                                                                         
 ---                                                                                                                     
 File Naming Convention                                                                                                  
                                                                                                                         
 ✅ GOOD:                                                                                                                
   useWorkOrderActions.ts       # Hook for domain                                                                        
   WorkOrderLensContent.tsx     # Lens component                                                                         
   actionClient.ts              # Single API client                                                                      
                                                                                                                         
 ❌ BAD:                                                                                                                 
   useWorkOrderActions_v2.ts    # Version suffix                                                                         
   WOActions.ts                 # Abbreviation                                                                           
   actions.ts                   # Too generic                                                                            
                                                                                                                         
 ---                                                                                                                     
 Success Criteria: "Done" Means                                                                                          
                                                                                                                         
 1. Search works: User types "pump", sees results WITH snippets                                                          
 2. Display works: Results show correct buttons per role                                                                 
 3. Actions work: Clicking executes and logs                                                                             
 4. No duplicates: One file per concept                                                                                  
 5. Clear ownership: Any file obviously in Search, Display, or Actions                                                   
                                                                                                                         
 ---                                                                                                                     
 Immediate Actions (Next 24 Hours)                                                                                       
                                                                                                                         
 1. Fix Snippets (30 min)                                                                                                
                                                                                                                         
 # Apply migration                                                                                                       
 psql $DATABASE_URL -f database/migrations/45_f1_search_cards_with_search_text.sql                                       
                                                                                                                         
 Edit apps/api/routes/f1_search_streaming.py:796:                                                                        
 SELECT object_type, object_id, payload, search_text, fused_score, ...                                                   
                                                                                                                         
 2. Delete Garbage (5 min)                                                                                               
                                                                                                                         
 rm apps/web/src/hooks/useEquipmentActions.ts.patch                                                                      
 rm apps/web/src/hooks/useReceivingActions.ts.new                                                                        
                                                                                                                         
 3. Merge Duplicates (1 hour)                                                                                            
                                                                                                                         
 - Consolidate usePartActions + usePartsActions                                                                          
 - Update all imports to single source                                                                                   
                                                                                                                         
 4. Deploy (rest of day)                                                                                                 
                                                                                                                         
 - Deploy current state                                                                                                  
 - Smoke test all 12 lenses                                                                                              
 - Verify buttons work per role                                                                                          
                                                                                                                         
 ---                                                                                                                     
 Verification Checklist                                                                                                  
                                                                                                                         
 - Snippets appear in search results                                                                                     
 - No orphaned files in /hooks/                                                                                          
 - Single usePartActions hook                                                                                            
 - All 12 lenses render                                                                                                  
 - Buttons show/hide per role (crew vs captain)                                                                          
 - Actions execute successfully                                                                                          
 - Build passes                                                                                                          
 - E2E tests pass                                                                                                        
                                                                                                                         
 ---                                                                                                                     
 Files to Modify                                                                                                         
                                                                                                                         
 Critical Path (Ship Blockers)                                                                                           
                                                                                                                         
 1. apps/api/routes/f1_search_streaming.py - Add search_text to SELECT                                                   
 2. apps/web/src/hooks/usePartActions.ts - Merge with usePartsActions                                                    
 3. Delete: useEquipmentActions.ts.patch, useReceivingActions.ts.new                                                     
                                                                                                                         
 Nice to Have (Post-Ship)                                                                                                
                                                                                                                         
 4. Move SpotlightSearch → /search/components/                                                                           
 5. Move lenses → /display/components/lenses/                                                                            
 6. Consolidate action hooks → /actions/hooks/                                                                           
                                                                                                                         
 ---                                                                        