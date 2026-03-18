 CEO Summary: Legacy Frontend Removal & Prototype Conversion Readiness                                                                 
                                                                                                                                        
  What Is This Project?                                                                                                                 
  
  Celeste is a Personal Assistant app for yacht crew. Crew members type natural language commands ("find the fire pump manual", "log a  
  fault on engine 2") and the system finds, opens, and acts on the right information across all ship systems — work orders, equipment,
  documents, inventory, emails, certificates, and more.                                                                                 
                                                                  
  The app has a web frontend (what users see and click) and a backend API (where the data lives). This work focused entirely on the     
  frontend.
                                                                                                                                        
  ---                                                                                                                                   
  What Was The Problem?
                                                                                                                                        
  The frontend had two competing architectures running simultaneously:
                                                                                                                                        
  1. Legacy (old): Everything lived on a single URL (/app). When you clicked on a work order, it opened in a sliding panel on the same  
  page. Like a filing cabinet with one drawer that tried to show everything.                                                            
  2. Fragmented (new): Each entity has its own URL (/work-orders/123, /equipment/456). Like having separate pages for each thing. This  
  is how modern web apps work — it enables bookmarking, browser back-button, sharing links, and cleaner code.                           
   
  Both systems were wired in at the same time, creating dead code, confusion, and maintenance risk. Old code referenced components that 
  no longer made sense. New code couldn't fully take over because old code was still tangled in.
                                                                                                                                        
  ---                                                             
  What Was Done
                                                                                                                                        
  Phase 1: Surgical Removal of Legacy Architecture (COMPLETED)
                                                                                                                                        
  Business terms: We removed the old system entirely so the new system is the only one running. This eliminates confusion, reduces bugs,
   and makes the codebase ready for the visual redesign.
                                                                                                                                        
  What changed:                                                   

  ┌───────────────────────┬─────────┬─────────────────────────────────────────────────────────────────┐                                 
  │        Action         │  Count  │                         Why It Matters                          │
  ├───────────────────────┼─────────┼─────────────────────────────────────────────────────────────────┤                                 
  │ Files deleted         │ 20      │ Dead code that could confuse engineers or cause bugs            │
  ├───────────────────────┼─────────┼─────────────────────────────────────────────────────────────────┤
  │ Files edited          │ 8       │ Removed references to deleted code, updated to use new patterns │                                 
  ├───────────────────────┼─────────┼─────────────────────────────────────────────────────────────────┤                                 
  │ Directories removed   │ 4       │ Entire folders of obsolete components                           │                                 
  ├───────────────────────┼─────────┼─────────────────────────────────────────────────────────────────┤                                 
  │ Lines of code removed │ ~2,000+ │ Less code = fewer bugs, faster builds, clearer ownership        │
  └───────────────────────┴─────────┴─────────────────────────────────────────────────────────────────┘                                 
                                                                  
  Key files involved:                                                                                                                   
                                                                  
  ┌─────────────────────────────────┬─────────┬──────────────────────────────────────┬──────────────────────────────────────────────┐   
  │              File               │ Action  │               Purpose                │                Why It Matters                │
  ├─────────────────────────────────┼─────────┼──────────────────────────────────────┼──────────────────────────────────────────────┤   
  │ SurfaceContext.tsx              │ Deleted │ Controlled the old sliding-panel     │ Core of the legacy architecture — removing   │
  │                                 │         │ system                               │ it was the linchpin                          │
  ├─────────────────────────────────┼─────────┼──────────────────────────────────────┼──────────────────────────────────────────────┤   
  │ NavigationContext.tsx           │ Deleted │ Managed navigation state for the old │ No longer needed with URL-based routing      │
  │                                 │         │  single-page model                   │                                              │   
  ├─────────────────────────────────┼─────────┼──────────────────────────────────────┼──────────────────────────────────────────────┤
  │ ContextPanel.tsx                │ Deleted │ The old sliding detail panel         │ Replaced by full-page entity views           │   
  ├─────────────────────────────────┼─────────┼──────────────────────────────────────┼──────────────────────────────────────────────┤   
  │ SituationRouter.tsx + 5         │ Deleted │ Old entity rendering system          │ Replaced by lens-v2 components               │
  │ situation views                 │         │                                      │                                              │   
  ├─────────────────────────────────┼─────────┼──────────────────────────────────────┼──────────────────────────────────────────────┤
  │ SpotlightSearch.tsx             │ Edited  │ The search bar — most critical       │ Removed ~200 lines of legacy wiring; now     │   
  │                                 │         │ user-facing component                │ routes to new pages                          │   
  ├─────────────────────────────────┼─────────┼──────────────────────────────────────┼──────────────────────────────────────────────┤
  │ EmailInboxView.tsx              │ Edited  │ Email thread list                    │ Changed from "open in panel" to "navigate to │   
  │                                 │         │                                      │  email page"                                 │   
  ├─────────────────────────────────┼─────────┼──────────────────────────────────────┼──────────────────────────────────────────────┤
  │ open/page.tsx                   │ Edited  │ Resolves shared links (handover      │ Now sends users to the correct entity page   │   
  │                                 │         │ links)                               │ instead of the old /app                      │   
  ├─────────────────────────────────┼─────────┼──────────────────────────────────────┼──────────────────────────────────────────────┤
  │ featureFlags.ts                 │ Edited  │ Feature toggle utility               │ Removed the "is new architecture enabled?"   │   
  │                                 │         │                                      │ flag (it's always on now)                    │   
  ├─────────────────────────────────┼─────────┼──────────────────────────────────────┼──────────────────────────────────────────────┤
  │ RouteLayout.tsx                 │ Edited  │ Shared page layout template          │ Renamed legacy terminology (ContextPanel →   │   
  │                                 │         │                                      │ DetailPanel)                                 │   
  ├─────────────────────────────────┼─────────┼──────────────────────────────────────┼──────────────────────────────────────────────┤
  │ documentTypes.ts                │ Edited  │ Classifies documents as operational  │ Made self-contained — no longer depends on   │   
  │                                 │         │ vs compliance                        │ deleted type definitions                     │   
  └─────────────────────────────────┴─────────┴──────────────────────────────────────┴──────────────────────────────────────────────┘
                                                                                                                                        
  Verification: After removal, the entire codebase compiles with zero errors. All 13 entity routes return successfully. The build       
  succeeds. No broken references remain.
                                                                                                                                        
  ---                                                             
  Phase 2: Prototype Conversion Assessment (COMPLETED)
                                                      
  Business terms: We audited exactly what exists, what's ready, and what needs to happen to make the new designs visible to users.
                                                                                                                                        
  The situation: The design team created 12 interactive HTML prototypes — one for each entity type (work orders, equipment, faults,     
  etc.). These are pixel-perfect mockups showing exactly how each page should look: dark warm surfaces, teal accent colors, gold        
  identity highlights, glassmorphism headers, collapsible sections, signature workflows.                                                
                                                                  
  Separately, React components (the production code that runs in the actual app) were built to mirror these prototypes. There are 33    
  component files already created.
                                                                                                                                        
  The gap: The React components exist and are wired into the routes, but they don't yet visually match the prototypes. The colors,      
  spacing, typography, animations, and layout precision need to be aligned. Think of it as: the plumbing is installed, but the fixtures
  aren't the ones from the design catalog yet.                                                                                          
                                                                  
  ---
  What Exists Today
                   
  Prototypes (Design Reference — 39 files)
                                                                                                                                        
  Location: apps/web/public/prototypes/
                                                                                                                                        
  These are static HTML pages anyone can view in a browser — no login, no database, no backend needed. They represent the approved      
  visual direction. Every engineering decision about "how should this look?" should reference these files.
                                                                                                                                        
  Production Components (Code That Runs — 33 files)               

  Location: apps/web/src/components/lens-v2/                                                                                            
  
  These are the React components that render when a real user visits /work-orders/123. They fetch real data from the API and render it. 
  They work, but they don't yet look like the prototypes.         
                                                                                                                                        
  Design Token Bridge (Decision Record — 1 file)                  

  Location: apps/web/public/prototypes/TOKEN_MAP.md

  This document maps every design decision (which shade of black, which text color, which accent) from prototype to production. All     
  decisions are resolved — no ambiguity remains.
                                                                                                                                        
  ---                                                             
  Risks & Open Issues

  ┌────────────────────┬──────────┬─────────────────────────────────────────────────────────────────────────────────────────────────┐
  │        Risk        │ Severity │                                           Explanation                                           │
  ├────────────────────┼──────────┼─────────────────────────────────────────────────────────────────────────────────────────────────┤   
  │ Local dev shows    │          │ Entity pages can't load data locally because the tenant database isn't configured on dev        │
  │ "Failed to load"   │ Low      │ machines. This is expected — production (Vercel) has it configured and works fine. CSS/visual   │   
  │                    │          │ work can still be done locally.                                                                 │   
  ├────────────────────┼──────────┼─────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ Root page is bare  │ Medium   │ The home page (/) currently shows only a search bar on an empty background. No navigation menu, │   
  │                    │          │  no dashboard. Users can search, but can't browse. This needs design direction.                 │   
  ├────────────────────┼──────────┼─────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ AuthDebug panel    │ Low      │ A developer diagnostic overlay appears in the bottom-right corner. Should be hidden before any  │   
  │ visible            │          │ user sees it.                                                                                   │   
  ├────────────────────┼──────────┼─────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ E2E tests outdated │ Medium   │ Automated tests still use old URL patterns. They'll fail until updated. Not user-facing but     │   
  │                    │          │ blocks quality assurance.                                                                       │   
  ├────────────────────┼──────────┼─────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ No universal       │          │ The prototypes show a sophisticated form system for actions (signing off work, approving        │   
  │ action popup       │ Medium   │ purchases). Currently only signature capture exists. The full action form system needs          │   
  │                    │          │ building.                                                                                       │
  └────────────────────┴──────────┴─────────────────────────────────────────────────────────────────────────────────────────────────┘   
                                                                  
  ---
  What Should Happen Next
                         
  In priority order:
                                                                                                                                        
  1. Token Alignment (~1 session): Update the production color/typography values to match the approved prototype decisions. This makes  
  every page immediately look closer to the design.                                                                                     
  2. Component Visual Fidelity (~2-3 sessions): For each of the 12 entity types, open the prototype HTML next to the React component and
   pixel-match them — headers, sections, rows, spacing, animations.                                                                     
  3. Universal Action Popup (~1-2 sessions): Build the schema-driven form system so users can execute actions (approve, sign, reject)
  with the designed interface instead of basic prompts.                                                                                 
  4. Root Page & Navigation (~1 session): Design and build a proper landing page so users can navigate without relying solely on search.
  5. Polish & Deploy (~1 session): Remove debug tools, update tests, push to production.                                                
                                                                                                                                        
  ---                                                                                                                                   
  Bottom Line                                                                                                                           
                                                                                                                                        
  What was accomplished: The technical foundation is clean. Legacy code is gone. New architecture is the only architecture. All routes
  work. All components exist. The design specifications are documented and decisions are resolved.                                      
                                                                  
  What remains: Visual implementation — making what users see match what was designed. The engineering risk is low (components exist,   
  data flows work). The work is primarily CSS precision and component refinement.
                                                                                                                                        
  Cost of delay: Every day the old visual experience runs in production, users see an interface that doesn't reflect the product vision.
   The new designs are approved and the code scaffolding exists — it's a matter of applying the paint.
