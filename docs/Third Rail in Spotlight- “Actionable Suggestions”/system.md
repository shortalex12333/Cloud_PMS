                                                                                   
  ---                                                                                                                                  
  LAYER 1: FILTER CHIPS (Deterministic, Client-Side)                                                                                   
                                                                                                                                       
  ┌─────────────────────────────────────────────────────────────────────────────┐                                                      
  │                           FILTER CHIP SYSTEM                                 │                                                     
  ├─────────────────────────────────────────────────────────────────────────────┤                                                      
  │                                                                              │                                                     
  │  User Query: "overdue work orders"                                          │                                                      
  │       │                                                                      │                                                     
  │       ▼                                                                      │                                                     
  │  ┌──────────────────────────────────────────────┐                           │                                                      
  │  │         FilterChips.tsx:69-74                │                           │                                                      
  │  │  inferredFilters = inferFilters(query, 5)    │                           │                                                      
  │  └──────────────────────────────────────────────┘                           │                                                      
  │       │                                                                      │                                                     
  │       ▼                                                                      │                                                     
  │  ┌──────────────────────────────────────────────┐                           │                                                      
  │  │              infer.ts:139-199                │                           │                                                      
  │  │                                              │                           │                                                      
  │  │  Phase 1: EXPLICIT_PATTERNS (score 0.9-1.0) │                           │                                                       
  │  │    /overdue\s*(work\s*)?orders?/i → wo_overdue (1.0)                    │                                                       
  │  │                                              │                           │                                                      
  │  │  Phase 2: KEYWORD MATCHING (score 0.3-0.8)  │                           │                                                       
  │  │    filter.keywords.includes('overdue')       │                           │                                                      
  │  │                                              │                           │                                                      
  │  │  Phase 3: DOMAIN FALLBACK (score 0.3)       │                           │                                                       
  │  │    detectDomain(query) → suggest top 2       │                           │                                                      
  │  └──────────────────────────────────────────────┘                           │                                                      
  │       │                                                                      │                                                     
  │       ▼                                                                      │                                                     
  │  ┌──────────────────────────────────────────────┐                           │                                                      
  │  │            catalog.ts:46-97                  │                           │                                                      
  │  │                                              │                           │                                                      
  │  │  WORK_ORDER_FILTERS: [                       │                           │                                                      
  │  │    { filter_id: 'wo_overdue',               │                           │                                                       
  │  │      label: 'Overdue work orders',          │                           │                                                       
  │  │      route: '/work-orders',                 │                           │                                                       
  │  │      query_params: { filter: 'wo_overdue' },│                           │                                                       
  │  │      keywords: ['overdue', 'past due', ...],│                           │                                                       
  │  │      definition: "due_date < CURRENT_DATE   │                           │                                                       
  │  │        AND status NOT IN ('completed'...)"  │                           │                                                       
  │  │    },                                        │                           │                                                      
  │  │    ...                                       │                           │                                                      
  │  │  ]                                           │                           │                                                      
  │  └──────────────────────────────────────────────┘                           │                                                      
  │       │                                                                      │                                                     
  │       ▼                                                                      │                                                     
  │  ┌──────────────────────────────────────────────┐                           │                                                      
  │  │       FilterChips.tsx:110-132                │                           │                                                      
  │  │                                              │                           │                                                      
  │  │  <button                                     │                           │                                                      
  │  │    onClick={() => handleChipClick(inferred)}│                           │                                                       
  │  │    data-testid={`filter-chip-${filter_id}`} │                           │                                                       
  │  │    className={                               │                           │                                                      
  │  │      matchType === 'pattern'                │                           │                                                       
  │  │        ? 'bg-brand-interactive/20...'       │  ← High confidence        │                                                       
  │  │        : 'bg-surface-secondary...'          │  ← Lower confidence       │                                                       
  │  │    }                                         │                           │                                                      
  │  │  >                                           │                           │                                                      
  │  │    <Icon /> {filter.label}                  │                           │                                                       
  │  │  </button>                                   │                           │                                                      
  │  └──────────────────────────────────────────────┘                           │                                                      
  │       │                                                                      │                                                     
  │       ▼                                                                      │                                                     
  │  ┌──────────────────────────────────────────────┐                           │                                                      
  │  │       FilterChips.tsx:84-93                  │                           │                                                      
  │  │                                              │                           │                                                      
  │  │  handleChipClick(inferred):                 │                           │                                                       
  │  │    url = buildFilterUrl(filter.route,       │                           │                                                       
  │  │                         filter.query_params) │                           │                                                      
  │  │    onFilterClick?.(filter_id, url)          │  ← Telemetry              │                                                       
  │  │    router.push(url)                         │  ← Navigation             │                                                       
  │  │                                              │                           │                                                      
  │  │  Result: /work-orders?filter=wo_overdue     │                           │                                                       
  │  └──────────────────────────────────────────────┘                           │                                                      
  │                                                                              │                                                     
  └─────────────────────────────────────────────────────────────────────────────┘                                                      
                                                                                                                                       
  Key Files:                                                                                                                           
  ┌─────────────────┬────────────────────┬────────────────┐                                                                            
  │      File       │      Purpose       │ Critical Lines │                                                                            
  ├─────────────────┼────────────────────┼────────────────┤                                                                            
  │ FilterChips.tsx │ Render chips       │ 62-136         │                                                                            
  ├─────────────────┼────────────────────┼────────────────┤                                                                            
  │ infer.ts        │ 3-phase inference  │ 139-199        │                                                                            
  ├─────────────────┼────────────────────┼────────────────┤                                                                            
  │ catalog.ts      │ Filter definitions │ 46-362         │                                                                            
  └─────────────────┴────────────────────┴────────────────┘                                                                            
  27 Active Filters across 8 Domains:                                                                                                  
  - Work Orders: wo_overdue, wo_due_7d, wo_open, wo_priority_emergency, wo_priority_critical                                           
  - Faults: fault_open, fault_unresolved, fault_critical, fault_investigating                                                          
  - Equipment: eq_attention, eq_failed, eq_maintenance, eq_critical                                                                    
  - Inventory: inv_low_stock, inv_out_of_stock                                                                                         
  - Certificates: cert_expiring_30d, cert_expired                                                                                      
  - Email: email_unlinked, email_linked, email_with_attachments                                                                        
  - Shopping List: shop_pending, shop_urgent                                                                                           
  - Receiving: recv_pending, recv_discrepancy                                                                                          
                                                                                                                                       
  ---                                                                                                                                  
  LAYER 2: ACTION BUTTONS (Dynamic, Server-Side)                                                                                       
                                                                                                                                       
  ┌─────────────────────────────────────────────────────────────────────────────┐                                                      
  │                          ACTION BUTTON SYSTEM                                │                                                     
  ├─────────────────────────────────────────────────────────────────────────────┤                                                      
  │                                                                              │                                                     
  │  User Query: "create work order"                                            │                                                      
  │       │                                                                      │                                                     
  │       ▼                                                                      │                                                     
  │  ┌──────────────────────────────────────────────┐                           │                                                      
  │  │     useCelesteSearch.ts:923-973              │                           │                                                      
  │  │                                              │                           │                                                      
  │  │  // 8 Domain Intent Detectors               │                           │                                                       
  │  │  detectWorkOrderActionIntent(query)         │                           │                                                       
  │  │    → WO_ACTION_KEYWORDS includes            │                           │                                                       
  │  │      'create work order' ✓                  │                           │                                                       
  │  │                                              │                           │                                                      
  │  │  // Priority: crew > parts > receiving >    │                           │                                                       
  │  │  //           docs > fault > shop > cert > wo                           │                                                       
  │  │  domain = 'work_orders'                     │                           │                                                       
  │  └──────────────────────────────────────────────┘                           │                                                      
  │       │                                                                      │                                                     
  │       ▼                                                                      │                                                     
  │  ┌──────────────────────────────────────────────┐                           │                                                      
  │  │       actionClient.ts:254-322                │                           │                                                      
  │  │                                              │                           │                                                      
  │  │  getActionSuggestions(query, domain)        │                           │                                                       
  │  │    → GET /v1/actions/list?q=...&domain=...  │                           │                                                       
  │  │    → Authorization: Bearer ${jwt}           │                           │                                                       
  │  │                                              │                           │                                                      
  │  │  Response:                                   │                           │                                                      
  │  │    { actions: [                              │                           │                                                      
  │  │        { action_id: 'create_work_order',    │                           │                                                       
  │  │          label: 'Create Work Order',        │                           │                                                       
  │  │          variant: 'MUTATE',                 │                           │                                                       
  │  │          required_fields: ['title', ...],   │                           │                                                       
  │  │          allowed_roles: ['engineer', ...],  │                           │                                                       
  │  │          match_score: 0.95                  │                           │                                                       
  │  │        }                                     │                           │                                                      
  │  │      ],                                      │                           │                                                      
  │  │      role: 'chief_engineer'                 │                           │                                                       
  │  │    }                                         │                           │                                                      
  │  └──────────────────────────────────────────────┘                           │                                                      
  │       │                                                                      │                                                     
  │       ▼                                                                      │                                                     
  │  ┌──────────────────────────────────────────────┐                           │                                                      
  │  │     SuggestedActions.tsx:60-79               │                           │                                                      
  │  │                                              │                           │                                                      
  │  │  {actions.map((action) => (                 │                           │                                                       
  │  │    <button                                   │                           │                                                      
  │  │      onClick={() => handleActionClick(action)}                          │                                                       
  │  │      className={                             │                           │                                                      
  │  │        action.variant === 'SIGNED'          │                           │                                                       
  │  │          ? 'border-amber-500/50...'         │  ← Signature required     │                                                       
  │  │          : 'bg-celeste-accent/20...'        │  ← Standard action        │                                                       
  │  │      }                                       │                           │                                                      
  │  │      data-testid={`action-btn-${action_id}`}│                           │                                                       
  │  │    >                                         │                           │                                                      
  │  │      {action.label}                         │                           │                                                       
  │  │      {action.variant === 'SIGNED' && <PenLine />}                       │                                                       
  │  │    </button>                                 │                           │                                                      
  │  │  ))}                                         │                           │                                                      
  │  └──────────────────────────────────────────────┘                           │                                                      
  │       │                                                                      │                                                     
  │       ▼ (on click)                                                          │                                                      
  │  ┌──────────────────────────────────────────────┐                           │                                                      
  │  │         ActionModal.tsx:67-444               │                           │                                                      
  │  │                                              │                           │                                                      
  │  │  // Dynamic form from required_fields       │                           │                                                       
  │  │  visibleFields = action.required_fields     │                           │                                                       
  │  │    .filter(f => f !== 'yacht_id'...)        │                           │                                                       
  │  │                                              │                           │                                                      
  │  │  // Field type inference                    │                           │                                                       
  │  │  inferFieldType(field):                     │                           │                                                       
  │  │    'date' if field.includes('date')         │                           │                                                       
  │  │    'textarea' if field.includes('note')     │                           │                                                       
  │  │    'select' if field.includes('type')       │                           │                                                       
  │  │    'text' otherwise                         │                           │                                                       
  │  │                                              │                           │                                                      
  │  │  // Submit → executeAction()                │                           │                                                       
  │  └──────────────────────────────────────────────┘                           │                                                      
  │       │                                                                      │                                                     
  │       ▼                                                                      │                                                     
  │  ┌──────────────────────────────────────────────┐                           │                                                      
  │  │       actionClient.ts:90-171                 │                           │                                                      
  │  │                                              │                           │                                                      
  │  │  executeAction(action_id, context, payload) │                           │                                                       
  │  │    → POST /v1/actions/execute               │                           │                                                       
  │  │    → Body: { action, context, payload }     │                           │                                                       
  │  │                                              │                           │                                                      
  │  │  For SIGNED actions (ActionModal:132-138):  │                           │                                                       
  │  │    payload.signature = {                    │                           │                                                       
  │  │      signed_by: 'current_user',             │                           │                                                       
  │  │      signed_at: ISO timestamp,              │                           │                                                       
  │  │      reason: formData.reason                │                           │                                                       
  │  │    }                                         │                           │                                                      
  │  └──────────────────────────────────────────────┘                           │                                                      
  │                                                                              │                                                     
  └─────────────────────────────────────────────────────────────────────────────┘                                                      
                                                                                                                                       
  Intent Keywords (useCelesteSearch.ts:72-289):                                                                                        
  ┌───────────────┬─────────────────────────────────────────────────────────────────────┐                                              
  │    Domain     │                              Keywords                               │                                              
  ├───────────────┼─────────────────────────────────────────────────────────────────────┤                                              
  │ Work Orders   │ create work order, assign work order, close work order, add wo note │                                              
  ├───────────────┼─────────────────────────────────────────────────────────────────────┤                                              
  │ Faults        │ report fault, acknowledge fault, close fault, diagnose fault        │                                              
  ├───────────────┼─────────────────────────────────────────────────────────────────────┤                                              
  │ Equipment     │ update equipment status, flag equipment, decommission               │                                              
  ├───────────────┼─────────────────────────────────────────────────────────────────────┤                                              
  │ Inventory     │ consume part, adjust stock, transfer part, write off                │                                              
  ├───────────────┼─────────────────────────────────────────────────────────────────────┤                                              
  │ Receiving     │ create receiving, accept receiving, extract receiving               │                                              
  ├───────────────┼─────────────────────────────────────────────────────────────────────┤                                              
  │ Shopping List │ add to shopping list, approve shopping, promote to part             │                                              
  ├───────────────┼─────────────────────────────────────────────────────────────────────┤                                              
  │ Certificates  │ add certificate, link document, supersede cert                      │                                              
  ├───────────────┼─────────────────────────────────────────────────────────────────────┤                                              
  │ Crew          │ assign role, revoke role, crew certificates                         │                                              
  └───────────────┴─────────────────────────────────────────────────────────────────────┘                                              
  ---                                                                                                                                  
  LAYER 3: INTEGRATION IN SPOTLIGHT SEARCH                                                                                             
                                                                                                                                       
  SpotlightSearch.tsx:1010-1032 - Where chips and actions render:                                                                      
                                                                                                                                       
  {/* Suggested Actions - backend-provided action buttons */}                                                                          
  {hasQuery && actionSuggestions.length > 0 && (                                                                                       
    <SuggestedActions                                                                                                                  
      actions={actionSuggestions}                                                                                                      
      yachtId={user?.yachtId ?? null}                                                                                                  
      onActionComplete={refetch}                                                                                                       
    />                                                                                                                                 
  )}                                                                                                                                   
                                                                                                                                       
  {/* Quick Filter Chips - deterministic filter suggestions */}                                                                        
  {hasQuery && !emailScopeActive && (                                                                                                  
    <FilterChips                                                                                                                       
      query={query}                                                                                                                    
      onFilterClick={(filterId, route) => {                                                                                            
        recordLedgerEvent('quick_filter_clicked', {...});                                                                              
      }}                                                                                                                               
    />                                                                                                                                 
  )}                                                                                                                                   
                                                                                                                                       
  ---                                                                                                                                  
  SUMMARY: Two Parallel Systems                                                                                                        
  ┌─────────────────┬───────────────────────────────┬─────────────────────────────────────────┐                                        
  │     Aspect      │         Filter Chips          │             Action Buttons              │                                        
  ├─────────────────┼───────────────────────────────┼─────────────────────────────────────────┤                                        
  │ Source of Truth │ catalog.ts (client)           │ Backend /v1/actions/list                │                                        
  ├─────────────────┼───────────────────────────────┼─────────────────────────────────────────┤                                        
  │ Inference       │ infer.ts - regex patterns     │ useCelesteSearch.ts - keyword detection │                                        
  ├─────────────────┼───────────────────────────────┼─────────────────────────────────────────┤                                        
  │ Deterministic?  │ Yes - same query = same chips │ No - role-based from backend            │                                        
  ├─────────────────┼───────────────────────────────┼─────────────────────────────────────────┤                                        
  │ Rendering       │ FilterChips.tsx               │ SuggestedActions.tsx                    │                                        
  ├─────────────────┼───────────────────────────────┼─────────────────────────────────────────┤                                        
  │ Click Action    │ router.push(/domain?filter=X) │ Opens ActionModal                       │                                        
  ├─────────────────┼───────────────────────────────┼─────────────────────────────────────────┤                                        
  │ Execution       │ Navigation only               │ POST /v1/actions/execute                │                                        
  ├─────────────────┼───────────────────────────────┼─────────────────────────────────────────┤                                        
  │ Variants        │ N/A                           │ READ, MUTATE, SIGNED                    │                                        
  ├─────────────────┼───────────────────────────────┼─────────────────────────────────────────┤                                        
  │ Styling         │ Pattern match = highlighted   │ SIGNED = amber warning                  │                                        
  └─────────────────┴───────────────────────────────┴─────────────────────────────────────────┘                                        
                                                                                           