frontend                                                                                     

⏺ What Was Done

  One thing: removed dead code from the old navigation system. 20 files deleted, 8 files edited. The app compiles and the dev server
  runs. No new features, no visual changes, no design work.

  What Was NOT Done

  - No prototype implementation
  - No new UI built
  - No visual design changes
  - No user-facing improvements
  - The root page looks identical to before
  - Entity pages still show "Failed to load" locally (no tenant DB



  Here's the complete handoff document for the prototype-to-production conversion.

  ---
  Prototype → Production Conversion: Full Engineering Handoff                                                                         
                                                                                                                                      
  1. WHERE THE PROTOTYPES LIVE                                                                                                        
                                                                                                                                      
  apps/web/public/prototypes/                                                                                                         
  ├── lens-work-order.html        ← canonical reference prototype                                                                     
  ├── lens-equipment.html                                                                                                             
  ├── lens-fault.html                                                                                                                 
  ├── lens-inventory.html                                                                                                             
  ├── lens-document.html                                                                                                              
  ├── lens-email.html                                                                                                                 
  ├── lens-receiving.html                                                                                                             
  ├── lens-shopping.html                                                                                                                
  ├── lens-handover.html                                                                                                              
  ├── lens-certificate.html                                                                                                             
  ├── lens-purchase-order.html                                                                                                        
  ├── lens-requisition.html                                                                                                             
  ├── prototype-tokens.css        ← shared design tokens                                                                              
  ├── lens-base.css               ← shared layout/section styles                                                                      
  ├── lens-base.js                ← shared interactivity (collapse, scroll-reveal)                                                      
  ├── TOKEN_MAP.md                ← prototype→production token bridge                                                                 
  ├── DESIGN_SIGNATURES_AND_POPUPS.md  ← action popup architecture                                                                      
  ├── PROTOTYPE_GUIDE.md                                                                                                              
  └── archive/                    ← older iterations                                                                                  
                                                                                                                                      
  View any prototype directly: localhost:3007/prototypes/lens-work-order.html (no auth needed).                                       
                                                                                                                                      
  2. WHERE THE REACT COMPONENTS LIVE                                                                                                    
                                                                                                                                        
  apps/web/src/components/lens-v2/                                                                                                      
  ├── LensShell.tsx               ← outer chrome (header + action bar)                                                                  
  ├── LensGlassHeader.tsx         ← glassmorphism top header                                                                            
  ├── IdentityStrip.tsx           ← entity identity row (icon + title + status)                                                         
  ├── SplitButton.tsx             ← primary/secondary action split button                                                               
  ├── CollapsibleSection.tsx      ← expandable content sections                                                                         
  ├── LensPill.tsx                ← status/tag pills                                                                                    
  ├── ScrollReveal.tsx            ← scroll-triggered fade-in                                                                            
  ├── lens.module.css             ← ~1,200 lines, ALL tokens + styles (CSS Module)                                                      
  ├── sections/                   ← 8 reusable section components                                                                       
  │   ├── MetadataGrid.tsx                                                                                                              
  │   ├── TimelineSection.tsx                                                                                                           
  │   ├── DocumentsSection.tsx                                                                                                        
  │   ├── PartsSection.tsx                                                                                                              
  │   ├── NotesSection.tsx                                                                                                              
  │   ├── SignatureSection.tsx                                                                                                          
  │   ├── RelatedItemsSection.tsx                                                                                                       
  │   └── ChecklistSection.tsx                                                                                                          
  └── entity/                     ← 12 entity-specific content renderers                                                                
      ├── index.ts                ← re-exports all                                                                                      
      ├── WorkOrderContent.tsx                                                                                                          
      ├── EquipmentContent.tsx                                                                                                          
      ├── FaultContent.tsx                                                                                                              
      ├── InventoryContent.tsx                                                                                                        
      ├── DocumentContent.tsx                                                                                                           
      ├── EmailContent.tsx                                                                                                              
      ├── ReceivingContent.tsx                                                                                                          
      ├── ShoppingContent.tsx                                                                                                           
      ├── HandoverContent.tsx                                                                                                           
      ├── CertificateContent.tsx                                                                                                        
      ├── PurchaseOrderContent.tsx                                                                                                      
      └── RequisitionContent.tsx                                                                                                        
                                                                                                                                        
  3. HOW THE FRONTEND CURRENTLY CONNECTS                                                                                                
                                                                                                                                        
  Route: /work-orders/[id]/page.tsx                                                                                                   
           │                                                                                                                          
           ▼                                                                                                                          
    EntityLensPage.tsx (orchestrator — 384 lines)                                                                                       
           │                                                                                                                            
           ├─ useEntityLens(entityType, entityId)                                                                                       
           │     └─ GET /v1/entity/{type}/{id} → { entity, available_actions }                                                          
           │                                                                                                                          
           ├─ Renders: LensShell (chrome)                                                                                             
           │     ├─ LensGlassHeader                                                                                                     
           │     ├─ IdentityStrip                                                                                                     
           │     └─ SplitButton (wired to available_actions)                                                                            
           │                                                                                                                          
           ├─ Renders: <content /> (e.g. WorkOrderContent)                                                                            
           │     └─ reads data via useEntityLensContext() (zero props)                                                                  
           │                                                                                                                            
           └─ Signature modal interception                                                                                              
                 └─ if action.requires_signature → show SignatureModal before executing                                                 
                                                                                                                                      
  Data flow: API returns raw entity JSON → useEntityLens stores it in context → content component reads from context and renders      
  sections.                                                                                                                             
                                                                                                                                      
  Actions: Backend defines available_actions[] per entity. Each action has label, action_key, prefill, required_fields,                 
  requires_signature, disabled_reason. Frontend is a "dumb shell" — it renders buttons from the action list and executes via POST       
  /v1/entity/{type}/{id}/action.                                                                                                        
                                                                                                                                        
  4. THE GAP: WHAT NEEDS TO CHANGE                                                                                                    
                                                                                                                                      
  The React components exist and are wired, but they don't match the prototypes visually. Here's the gap:                               
                                                                                                                                      
  ┌─────────────────┬──────────────────────────────────────────────┬───────────────────────────┬──────────────────────┐                 
  │     Aspect      │               Prototype (HTML)               │    Production (React)     │         Gap          │                 
  ├─────────────────┼──────────────────────────────────────────────┼───────────────────────────┼──────────────────────┤                 
  │ Surface colors  │ Warm #0c0b0a backgrounds                     │ Neutral #111111           │ Token values differ  │                 
  ├─────────────────┼──────────────────────────────────────────────┼───────────────────────────┼──────────────────────┤                 
  │ Text colors     │ rgba(255,255,255,0.87)                       │ #e5e5e5 hex               │ Need token alignment │                 
  ├─────────────────┼──────────────────────────────────────────────┼───────────────────────────┼──────────────────────┤               
  │ Glass header    │ backdrop-blur + gradient                     │ Basic implementation      │ Visual fidelity      │                 
  ├─────────────────┼──────────────────────────────────────────────┼───────────────────────────┼──────────────────────┤               
  │ Section styling │ Precise padding, borders, collapse animation │ Basic collapsible         │ CSS precision        │                 
  ├─────────────────┼──────────────────────────────────────────────┼───────────────────────────┼──────────────────────┤               
  │ Identity strip  │ Gold accent, icon placement, status pills    │ Basic layout              │ Design polish        │                 
  ├─────────────────┼──────────────────────────────────────────────┼───────────────────────────┼──────────────────────┤               
  │ Document rows   │ File icon + metadata + action buttons        │ Minimal render            │ Full row design      │                 
  ├─────────────────┼──────────────────────────────────────────────┼───────────────────────────┼──────────────────────┤               
  │ Timeline        │ Dot-connected vertical timeline              │ Basic list                │ Timeline CSS         │                 
  ├─────────────────┼──────────────────────────────────────────────┼───────────────────────────┼──────────────────────┤               
  │ Action popup    │ Schema-driven modal with field types         │ SignatureModal only       │ Universal popup      │                 
  ├─────────────────┼──────────────────────────────────────────────┼───────────────────────────┼──────────────────────┤                 
  │ Content density │ Each entity has unique section order/layout  │ Generic section rendering │ Per-entity tuning    │                 
  └─────────────────┴──────────────────────────────────────────────┴───────────────────────────┴──────────────────────┘                 
                                                                                                                                        
  5. TOKEN BRIDGE (TOKEN_MAP.md decisions — all resolved)                                                                             
                                                                                                                                        
  ┌────────────────────┬────────────────────────┬─────────────────────────────────────┐                                               
  │       Token        │       Prototype        │          Production Winner          │                                                 
  ├────────────────────┼────────────────────────┼─────────────────────────────────────┤                                               
  │ --surface-base     │ #0c0b0a (warm)         │ Prototype wins → warm black         │                                                 
  ├────────────────────┼────────────────────────┼─────────────────────────────────────┤                                               
  │ --surface-primary  │ #141312 (warm)         │ Prototype wins                      │                                                 
  ├────────────────────┼────────────────────────┼─────────────────────────────────────┤                                               
  │ --surface-elevated │ #1c1b19 (warm)         │ Prototype wins                      │                                                 
  ├────────────────────┼────────────────────────┼─────────────────────────────────────┤                                               
  │ --txt-primary      │ rgba(255,255,255,0.87) │ Production wins → hex #e0e0e0       │                                                 
  ├────────────────────┼────────────────────────┼─────────────────────────────────────┤                                               
  │ --accent-teal      │ #2dd4bf                │ Prototype wins                      │                                                 
  ├────────────────────┼────────────────────────┼─────────────────────────────────────┤                                               
  │ --accent-gold      │ #d4a843                │ Prototype wins                      │                                                 
  ├────────────────────┼────────────────────────┼─────────────────────────────────────┤                                               
  │ --signal-*         │ Vivid saturated        │ Production wins → Radix-style muted │                                                 
  └────────────────────┴────────────────────────┴─────────────────────────────────────┘                                               
                                                                                                                                      
  6. WHAT THE NEXT ENGINEER NEEDS TO DO                                                                                                 
                                                                                                                                        
  Phase A — Token Alignment (1 session)                                                                                                 
  1. Update apps/web/src/styles/tokens.css to match TOKEN_MAP.md decisions                                                              
  2. Update lens.module.css variables to reference production tokens                                                                  
  3. Verify all 12 entity routes render with correct colors                                                                             
                                                                                                                                      
  Phase B — Component Visual Fidelity (2-3 sessions)                                                                                    
  1. Open prototype HTML side-by-side with React component                                                                            
  2. For each entity, pixel-match:                                                                                                      
    - Glass header gradient + blur                                                                                                    
    - Identity strip layout (icon, title, status pill positions)                                                                        
    - Section headers (border, padding, collapse animation)                                                                           
    - Content rows (document rows, parts rows, timeline dots)                                                                           
  3. Use lens.module.css for ALL styling — no inline styles or global CSS                                                             
                                                                                                                                        
  Phase C — Universal Action Popup (1-2 sessions)                                                                                     
  1. Build schema-driven action modal per DESIGN_SIGNATURES_AND_POPUPS.md                                                               
  2. Replace current SignatureModal with universal popup that handles:                                                                
    - Text fields, dropdowns, date pickers (from required_fields)                                                                       
    - Signature capture (from requires_signature)                                                                                     
    - Prefilled values (from prefill)                                                                                                   
  3. Wire into EntityLensPage.tsx action handler                                                                                      
                                                                                                                                        
  Phase D — Root Page & Navigation (1 session)                                                                                          
  1. Root page (/) currently shows only SpotlightSearch on empty background                                                           
  2. Add navigation to entity list pages (/work-orders, /equipment, etc.)                                                               
  3. Consider: search-first landing vs dashboard vs sidebar nav                                                                       
                                                                                                                                        
  Phase E — Polish & Deploy (1 session)                                                                                               
  1. Remove AuthDebug panel from production                                                                                           
  2. Update E2E tests for new routes                                                                                                    
  3. Push to Vercel — production at app.celeste7.ai                                                                                   
                                                                                                                                        
  7. LOCAL DEV REALITY                                                                                                                
                                                                                                                                        
  - Prototype HTML: Works perfectly at localhost:3007/prototypes/*.html — no auth, no API                                             
  - Production routes (/work-orders/123): Show "Failed to load items" locally because READ_DB_DSN (tenant database) is not configured in
   local env. This is expected. Production (Vercel) has READ_DB_DSN set and works.                                                      
  - Token/CSS work: Can be done locally — just needs visual inspection against prototypes                                               
  - Data-dependent work: Must deploy to production or configure local tenant DB                                                         
                                                                                                                                      
  8. KEY FILES TO READ FIRST                                                                                                            
                                                                                                                                      
  1. apps/web/public/prototypes/lens-work-order.html — canonical visual reference                                                       
  2. apps/web/public/prototypes/TOKEN_MAP.md — token decisions                                                                        
  3. apps/web/src/components/lens-v2/lens.module.css — all current CSS tokens                                                         
  4. apps/web/src/components/lens/EntityLensPage.tsx — orchestrator (data flow)                                                       
  5. apps/web/src/hooks/useEntityLens.ts — API contract                                                                                 
  6. apps/web/src/styles/tokens.css — production design tokens                                                                        
  7. apps/web/public/prototypes/DESIGN_SIGNATURES_AND_POPUPS.md — action popup spec                                                     
                                                                                                                                        
  ---                                                                                                                                 
  The groundwork is done — legacy code removed, routes wired, React components exist. The remaining work is visual: making the React    
  components look like the prototypes. 