⏺ ★ Insight ─────────────────────────────────────
  - The backend for this feature is complete — related_handlers.py (959 lines), /v1/related endpoint, FK queries, pms_entity_links
  table, shadow logging for V2 vector upgrade. Someone already built it.
  - The frontend component (RelatedEntitiesSection.tsx) also exists. The only missing piece is the button and wiring — nobody
  connected the front to the back.
  - The "show related" button is not a new feature — it's a plumbing task. The new engineer's job is integration, not invention.
  ─────────────────────────────────────────────────

  Here's the actual baseline for the new engineer:

  ---
  What Already Exists

  Backend — fully built:
  - apps/api/handlers/related_handlers.py — 959-line handler, FK queries for work orders, equipment, faults, parts, manuals
  - apps/api/routes/related_routes.py — /v1/related?entity_type=<type>&entity_id=<id> endpoint returns grouped results with match
  reasons
  - pms_entity_links table — manual linking (HOD/manager role)
  - embedding_worker_1536.py + pgvector embedding_1536 column — infrastructure for V2 vector reranking (shadow logging already
  wired: SHOW_RELATED_SHADOW=true)

  Frontend — partially built:
  - apps/web/src/components/lens/sections/RelatedEntitiesSection.tsx — display component exists
  - apps/web/src/components/layout/RouteLayout.tsx — the topNavContent prop is the insertion point for the button; currently all
  lens pages only put a back button + title there, right side is empty

  ---
  What's Missing (The Actual Work)

  ┌───────────────────────────────────────────────────────┬──────────────────────────────────────────────────────┐
  │                          Gap                          │                    Files to touch                    │
  ├───────────────────────────────────────────────────────┼──────────────────────────────────────────────────────┤
  │ "Show Related" button in top-right of topNavContent   │ All apps/web/src/app/**/[id]/page.tsx                │
  ├───────────────────────────────────────────────────────┼──────────────────────────────────────────────────────┤
  │ Hook to call /v1/related and manage open/close state  │ New useRelated.ts hook                               │
  ├───────────────────────────────────────────────────────┼──────────────────────────────────────────────────────┤
  │ Modal or slide-in panel wiring the response to the UI │ New RelatedPanel.tsx or reuse RelatedEntitiesSection │
  ├───────────────────────────────────────────────────────┼──────────────────────────────────────────────────────┤
  │ Navigation from panel items → entity detail routes    │ Already exists via getEntityRoute() pattern          │
  └───────────────────────────────────────────────────────┴──────────────────────────────────────────────────────┘

  ---
  What the New Engineer Does NOT Need to Build

  - The API — exists
  - The embeddings infrastructure — exists
  - The display component — exists
  - The search pipeline — irrelevant (this uses /v1/related, not F1 spotlight search)

  ---
  The Technical Choice

  The exploration found two separate systems that could power this:

  1. /v1/related — FK-based grouped results, already built, returns {groups: [...], match_reasons: [...]}. Use this. It's
  production-ready.
  2. F1 spotlight search + GraphRAG — the user mentioned this in the brief, but F1 is the global search pipeline. It is not the
  right tool for "items related to THIS entity." /v1/related is already the GraphRAG-style system (FK edges = graph, shadow mode =
  vector reranking). The new engineer does not need to touch F1 at all.

  The brief says "use GraphRAG technology" — the existing related_handlers.py IS that: it traverses entity relationships (graph)
  with a vector reranking path ready to enable. No new pipeline needed.

  ---
  Scope for the New Engineer

  Narrow and well-defined:

  1. Add "Show Related" button to topNavContent in RouteLayout.tsx or individually per lens page — top-right, consistent across all
  [id] pages
  2. Write useRelated(entityType, entityId) hook — calls /v1/related, manages loading/error state, opens/closes panel
  3. Build RelatedPanel component — slide-in from right, uses grouped results, each item navigable via getEntityRoute()
  4. Wire it to all 6+ lens detail pages: work-orders, faults, equipment, inventory, documents, certificates

  That's the whole job. Everything else is already there.

=======

                                                                  
                                                                                                                                    
⏺ ★ Insight ─────────────────────────────────────                                                                                   
  Three architectural layers are already in place for Show Related:                                                                 
  1. RouteLayout.primaryPanel — 480px right-side drawer with built-in slide-in animation, already accepts { visible, title, children
   }                                                                                                                                
  2. RelatedEntitiesSection — new-style component used inline in lens pages, but fed from entity-detail response not from           
  /v1/related                                                                                                                       
  3. RelatedPanel.tsx + AddRelatedModal.tsx — legacy context-nav components wired to the dead related_expansion.py and            
  NavigationContext — do NOT extend these
  ─────────────────────────────────────────────────

=======

