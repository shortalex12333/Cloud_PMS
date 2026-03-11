                                                                             
  Key Files                                                                                                                            
  ┌──────────────────┬──────────────────────────────────────────────┬────────┐                                                         
  │    Component     │                     File                     │ Lines  │                                                         
  ├──────────────────┼──────────────────────────────────────────────┼────────┤                                                         
  │ FilterChips      │ src/components/spotlight/FilterChips.tsx     │ 1-136  │                                                         
  ├──────────────────┼──────────────────────────────────────────────┼────────┤                                                         
  │ SuggestedActions │ src/components/SuggestedActions.tsx          │ 1-94   │                                                         
  ├──────────────────┼──────────────────────────────────────────────┼────────┤                                                         
  │ SpotlightSearch  │ src/components/spotlight/SpotlightSearch.tsx │ 1-1395 │                                                         
  ├──────────────────┼──────────────────────────────────────────────┼────────┤                                                         
  │ Filter Inference │ src/lib/filters/infer.ts                     │ 1-199  │                                                         
  ├──────────────────┼──────────────────────────────────────────────┼────────┤                                                         
  │ Filter Catalog   │ src/lib/filters/catalog.ts                   │ 1-391  │                                                         
  ├──────────────────┼──────────────────────────────────────────────┼────────┤                                                         
  │ Search Hook      │ src/hooks/useCelesteSearch.ts                │ 1-1231 │                                                         
  └──────────────────┴──────────────────────────────────────────────┴────────┘                                                         
  ---                                                                                                                                  
  Data Flow: Query → Clickable UI                                                                                                      
                                                                                                                                       
  User Types Query (SpotlightSearch:928-976)                                                                                           
           ↓                                                                                                                           
      ┌────┴────┐                                                                                                                      
      ▼         ▼                                                                                                                      
  FILTERS    ACTIONS                                                                                                                   
  (client)   (server)                                                                                                                  
      │         │                                                                                                                      
      ▼         ▼                                                                                                                      
  inferFilters()   GET /v1/actions/list                                                                                                
  (infer.ts:139)   (useCelesteSearch:923)                                                                                              
      │              │                                                                                                                 
      ▼              ▼                                                                                                                 
  FilterChips.tsx   SuggestedActions.tsx                                                                                               
  (lines 105-133)   (lines 60-79)                                                                                                      
      │              │                                                                                                                 
      ▼              ▼                                                                                                                 
  Click → router.push()   Click → ActionModal                                                                                          
                                                                                                                                       
  ---                                                                                                                                  
  Filter Chips (Deterministic, Client-Side)                                                                                            
                                                                                                                                       
  FilterChips.tsx:73 - Inference call:                                                                                                 
  const filters = inferFilters(query, 5);                                                                                              
                                                                                                                                       
  FilterChips.tsx:86-92 - Click handler:                                                                                               
  router.push(`${filter.route}?${new URLSearchParams(filter.query_params)}`);                                                          
                                                                                                                                       
  Three-Phase Inference (infer.ts):                                                                                                    
  1. Explicit Patterns (score 1.0) - 50+ regex patterns                                                                                
  2. Keyword Matching (score 0.3-0.8) - substring matching                                                                             
  3. Domain Fallback (score 0.3) - suggest by domain                                                                                   
                                                                                                                                       
  ---                                                                                                                                  
  Action Buttons (Dynamic, Server-Side)                                                                                                
                                                                                                                                       
  useCelesteSearch.ts:72-284 - Intent keywords for 8 domains:                                                                          
  - Work Orders: "create work order", "assign", "close"                                                                                
  - Faults: "report fault", "acknowledge", "diagnose"                                                                                  
  - Equipment: "update status", "decommission"                                                                                         
  - Inventory: "consume part", "adjust stock"                                                                                          
  - etc.                                                                                                                               
                                                                                                                                       
  SuggestedActions.tsx:60-79 - Render buttons:                                                                                         
  {actions.map(action => (                                                                                                             
    <button onClick={() => openActionModal(action)}>                                                                                   
      {action.type === 'SIGNED' && <SignatureIcon />}                                                                                  
      {action.label}                                                                                                                   
    </button>                                                                                                                          
  ))}                                                                                                                                  
                                                                                                                                       
  ---                                                                                                                                  
  Relationship Between Filters and Actions                                                                                             
  ┌──────────────┬───────────────────────────────┬───────────────────────────────┐                                                     
  │    Aspect    │         Filter Chips          │        Action Buttons         │                                                     
  ├──────────────┼───────────────────────────────┼───────────────────────────────┤                                                     
  │ Source       │ catalog.ts (client)           │ Backend /v1/actions/list      │                                                     
  ├──────────────┼───────────────────────────────┼───────────────────────────────┤                                                     
  │ Purpose      │ Navigate to filtered list     │ Trigger mutation              │                                                     
  ├──────────────┼───────────────────────────────┼───────────────────────────────┤                                                     
  │ Determinism  │ Yes - same query = same chips │ Backend-controlled            │                                                     
  ├──────────────┼───────────────────────────────┼───────────────────────────────┤                                                     
  │ Appears When │ Query matches pattern/keyword │ Query contains intent keyword │                                                     
  ├──────────────┼───────────────────────────────┼───────────────────────────────┤                                                     
  │ Click Result │ router.push(/domain?filter=X) │ Opens ActionModal form        │                                                     
  └──────────────┴───────────────────────────────┴───────────────────────────────┘         