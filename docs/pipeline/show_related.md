  Who We Are

  - Celeste is an intent‑first single page operating surface for real‑world operations (not a set
    of pages).
  - We are builders of deterministic, auditable systems where the database is truth and
    every user action is a small, verified change to reality (a micro‑action).

  Why We Exist

  - Traditional software forces navigation, hides state, and scatters history.
  - Operators don’t want to “go somewhere”; they want to “do something” safely, quickly,
    and with a provable audit trail.
  - We replace UI guesswork with deterministic triggers, strict role/RLS enforcement,
    and an immutable ledger.
  - traditional software is an array of many pages, naviagtion and endless. Celeste flips this on its head. Rather than users leanring the tradiitonal system navigation, celeste dynamically changes for the user. 1 single pagge always, everythign emebedded within.
  - Traditional software is an over-engineered polished database. Comapneis are requiring users to act upon a "noun" or "data", such as "Generator manual.pdf". What celeste understands is the REASONING for every users request. The REASON they desire to open "generator manual.pdf" may be, but not limited to, a fault, scheduled maintenance, inventory based around this equipment. this is where NLP works wonders. 
    - For example, traditional software = users query:"Generator manual.pdf" -> navigates through 7-12 pages to get tot he final manual page, then scroll to page to find the seciton they require.
        - Celeste software = User query: "Dg1 is overheating", OR, "We have high temperature fuel alarm on main generator", OR, "main eneigne work order", OR "ME1 requires oil change, show me manual".
        All of these terms woudl tehcnically, and roughly speaking, require users to read and open the manual to compelte their work.


"Show related"
- Traditional software has no relationships Graph RAG, RAG, vector embedding or other type of relationship spider-like design between entitiies of data types, documents, and other forms of database values.
- From amrket research and analysis, we know users opening a document within a db are 75% likely to open a further docuemnt related to the work. 
- What this means is there is a gap in the market for our software, celeste, to incroprate a system where users can easily see the related docuemtns and data related ot item in question. 
- an exmaple of this would eb user opening the "generator manual.pdf" via celeste. the "Show related" tab would therefore find relatio shsips between this document adn others to surface (for example) invnentory parts for generator, work order about main generator, handover notes that mention doucment or  reference generator maintenance, faults.


How this works (Front end)
- users will visit and view any peice of data via XXX lens on celeste, and see in the top right of their display, a button labelled "Show related".
- this opens a side bar profiel of all related oducments in an infintte scroll, based upon likeness ranking form backend.
- this infinte scroll adn display of results i teh same UX dimeniosn adn branding of the global search bar seen on users first instance of search.

Usability
- Here is hwo the site will function between Example User X, opening Artefact A from innitial search, then following to Artefact B from "show related" and their relationship.
- As we operate on 1 url only ,(app.celeste7.ai), lets assume user X typed in "Example query" and landed on artefact A,. After, user X clciked "Show related" form artefact A to see all results matching.
- From here user clicks Artefact B, whihc opens to their display, still within 1 url.
- Due to user operating within Artefact B THROUGH artefact A, the frontend UX will now load a "back" and "forward" button in the top left display in header.
- These buttons are for the users to easily navigate between artefact A and B accordingly. 
- IF the user repeats this behaviour and navigates 5 times through artefaact A-> artefact E solely through the show related, User X therefore can operate "back and forward" button in the same top elft display to navigate accordingly through artefact A/B/C/D/E. 
- If user is situated vieweing artefact A, and proceeds to press the back bubtton, user X will go back to the initial searhc bar "home" apge (still iwhtin same 1 url, app.celeste7.ai).
- Therefore to store cache for short period, we will allow user X to navigate back to the same journey (Artefact A/B/C/D/E) through the "Forward" button which is displayed on the "home screen".

Why
- We operate with this to not onyl help the user, but also to limit the db calls and compute oeprations to our system, storing cache, simple navigation releases stress on backend oepratios, and decreasing latency on frontend accordingly.
  


"Show related" (back end)
- to sumamrise briefly, we oNLY operate a rag/search for show related WHEN users click "show related". otherwise this seciton is not popualting, to save compute.
- This search is done based upon ARTEFACT metadata and defining properties.
- This search oepration must maintain intial suer role, crednitals, aycht_id, security protocol accordingly. to eliminte risk of wrong crew seeing adjacent yacht doucments, seeing above rank artefact and anythign else of sensitivity.
- Further to the example of User X opening Artefact A-> B; If users executes a microaction within Artefact A OR B, we MUST bring forward intnital query entity term type and vairbaels for auto-poulation. Even if users engaes in Artefact A->E, we msut still "remember" the term entity types for microaction executed in artefact E.
- If users navigates to hoem screen through "back adn forward" buttons, then proceed to "return' fomr home-> artefact A->B->B->C->D->E accoridngly, again, we must "remmeber" the intial query in question for execution of microactions. 



WHAT SHOW RELATED IS **NOT**
- Show related is NOT an area for users to INPUT a search query within this side panel
- Show releated is NOT searhving RAG based upon suers innital query AGAINST artefact.
- Show related
  
                                                                                                
  ✅ "Show Related" Already Exists                                                                                     
                                                                                                                       
  Your "Show Related" system is already built:                                                                         
                                                                                                                       
  Backend: /v1/related endpoint with Graph RAG/vector search                                                           
  Frontend:                                                                                                            
  - NavigationContext (manages back/forward stack)                                                                     
  - ViewerHeader (shows "Show Related" button, back/forward buttons)                                                   
  - Related artifacts sidebar (infinite scroll results)                                                                
                                                                                                                       
  ---                                                                                                                  
  How The Two Systems Work Together                                                                                    
                                                                                                                       
  1. Search → ContextPanel (What I Just Fixed)                                                                         
                                                                                                                       
  User Flow:                                                                                                           
  Search "generator fault" → Click result → ContextPanel slides in (520px sidebar)                                     
                                                                                                                       
  What shows:                                                                                                          
  - EquipmentCard / WorkOrderCard / FaultCard / PartCard                                                               
  - Entity details (status, location, maintenance history, etc.)                                                       
  - Action buttons (view, edit, create work order, etc.)                                                               
  - ❌ "Email integration is off" panel (irrelevant, as you said)                                                      
                                                                                                                       
  My recent work:                                                                                                      
  - Click content → Expands to full-screen (calc(100vw - 80px))                                                        
  - ESC/ChevronLeft → Collapses back to sidebar (520px)                                                                
                                                                                                                       
  ---                                                                                                                  
  2. "Show Related" Button (Already Exists)                                                                            
                                                                                                                       
  User Flow:                                                                                                           
  User viewing Generator in ContextPanel → Clicks "Show Related" button (top right)                                    
  → Related sidebar opens with infinite scroll of related artifacts                                                    
  → Click "Generator Manual.pdf" → Opens in ContextPanel                                                               
  → Back/Forward buttons appear (top left)                                                                             
                                                                                                                       
  What the backend does:                                                                                               
  - Graph RAG/vector search based on current artifact metadata                                                         
  - Returns grouped results (documents, work orders, parts, faults, etc.)                                              
  - Maintains RLS, yacht_id, user role security                                                                        
  - Only computes when user clicks "Show Related" (not preloaded)                                                      
                                                                                                                       
  Navigation stack:                                                                                                    
  Artifact A → Show Related → Artifact B → Show Related → Artifact C                                                   
             ↑ Back button                 ↑ Back button                                                               
                                                                                                                       
  ---                                                                                                                  
  Summary: Two Separate UX Patterns                                                                                    
  ┌──────────────┬───────────────────────────┬───────────────────────┬────────────────────────────────────────────────┐
  │   Feature    │          Trigger          │        Purpose        │                   What Opens                   │
  ├──────────────┼───────────────────────────┼───────────────────────┼────────────────────────────────────────────────┤
  │ ContextPanel │ Click search result       │ View entity details   │ Sidebar with entity card (520px → expandable)  │
  ├──────────────┼───────────────────────────┼───────────────────────┼────────────────────────────────────────────────┤
  │ Show Related │ Click "Show Related"      │ Find related          │ Sidebar with RAG search results (infinite      │
  │              │ button                    │ artifacts             │ scroll)                                        │
  └──────────────┴───────────────────────────┴───────────────────────┴────────────────────────────────────────────────┘
  Both use sidebars, but:                                                                                              
  - ContextPanel = Entity detail view with actions                                                                     
  - Show Related = Related search results ranked by relevance                                                          
                                                                                     


                                                                                                                                                   
  to articualte a better udnerstnading of celeste, we want to keep the knwoledge of the vessel       
  ON the vessel. current issues with aychting is that memories of faults, working and                
  maintenance onbaord is stored in suers heads, hard for new crew to understnad through rough        
  unorganised notes. hence this is a vague problem we must strive to erradicate and ensure we        
  abide to fix during our working. what this emans is the users experience must eb easy to           
  understnad, and more over EASY to update. hence keeping all memory within the vessel,              
  regardless of crew change.                    