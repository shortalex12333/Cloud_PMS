                                                                                                                            
  Three Categories                                                                                                                    
                                                                                                                             
  1. DANGER_ACTIONS (red-styled in dropdown) — cosmetic only                                                
These only affect styling. If the backend never returns them in availableActions, the button never renders. Low risk — but they  should still exist as handlers for when you want them.                                                                              
                                                                                                            
  2. primaryActionId (the BIG button) — 
will render if backend returns the action                                                     
These are the main CTA per lens. If the backend returns it, it's the primary button. If it doesn't, the SplitButton falls back to the first available action.                                                                                                
                                                                                                            
  3. 15 Aliases — frontend uses a different name than backend                                                                         
### TASK: we simply jsut need to ensure these are all wired up, correct naming and test the flow to ensure matches. adhereing to role poclies, rls, and other types of filtration/security:

  ┌──────────────────────┬────────────────────────────┬────────────────┐                                                              
  │       Frontend       │          Backend           │      Fix       │
  ├──────────────────────┼────────────────────────────┼────────────────┤
  │ add_certificate_note │ add_note (generic)         │ Registry alias │                                                              
  ├──────────────────────┼────────────────────────────┼────────────────┤
  │ add_document_note    │ add_note                   │ Registry alias │                                                              
  ├──────────────────────┼────────────────────────────┼────────────────┤                                                              
  │ add_part_note        │ add_note                   │ Registry alias │                                                     
  ├──────────────────────┼────────────────────────────┼────────────────┤                                                              
  │ add_po_note          │ add_note                   │ Registry alias │                                                     
  ├──────────────────────┼────────────────────────────┼────────────────┤                                                              
  │ add_warranty_note    │ add_note                   │ Registry alias │                                                              
  ├──────────────────────┼────────────────────────────┼────────────────┤
  │ add_wo_photo         │ add_work_order_photo       │ Registry alias │                                                              
  ├──────────────────────┼────────────────────────────┼────────────────┤                                                              
  │ apply_template       │ apply_crew_template        │ Registry alias │                                                     
  ├──────────────────────┼────────────────────────────┼────────────────┤                                    
  │ approve_list         │ approve_shopping_list_item │ Registry alias │
  ├──────────────────────┼────────────────────────────┼────────────────┤
  │ add_list_item        │ create_shopping_list_item  │ Registry alias │                                                              
  ├──────────────────────┼────────────────────────────┼────────────────┤                                                              
  │ sign_handover        │ sign_handover_outgoing     │ Registry alias │                                                     
  ├──────────────────────┼────────────────────────────┼────────────────┤                                    
  │ file_warranty_claim  │ draft_warranty_claim       │ Registry alias │
  ├──────────────────────┼────────────────────────────┼────────────────┤
  │ investigate_fault    │ diagnose_fault             │ Registry alias │                                                              
  ├──────────────────────┼────────────────────────────┼────────────────┤
  │ resolve_fault        │ close_fault                │ Registry alias │
  ├──────────────────────┼────────────────────────────┼────────────────┤
  │ track_po_delivery    │ track_delivery             │ Registry alias │
  ├──────────────────────┼────────────────────────────┼────────────────┤
  │ update_part_details  │ view_part_details          │ Registry alias │
  └──────────────────────┴────────────────────────────┴────────────────┘                                                              
                                                                                                                             
  4. Per-lens breakdown of what's missing                                                                   

  ┌────────────────┬──────────────────────────────────┬────────────────────────────────────┬──────────────────────────────────────┐   
  │      Lens      │         primaryActionId          │           DANGER_ACTIONS           │          All exist backend?          │   
  ├────────────────┼──────────────────────────────────┼────────────────────────────────────┼──────────────────────────────────────┤   
  │                │ start_work_order /               │ archive_work_order,                │ primary YES, archive YES (registry   │
  │ WorkOrder      │ close_work_order                 │ cancel_work_order,                 │ only), cancel YES, delete NO         │

### Comments: for the "delete work order" we simply put soft delete, mark as "deleted" adn define whom by, then store in db but ad via column. may need small migration, this is common task for all lens to be hoenst. every lens that user wishes to "delete" all need HOD/captain access. "signed" using appropriate signature type. then store as "deleted". therefore we just add note later for search results rendering "dont show "IF deleted". adn then add note to projection-worker (background worker), dont index or send anythgin to searhc_index IF column XYS = Deleted.

  ├────────────────┼──────────────────────────────────┼────────────────────────────────────┼──────────────────────────────────────┤
  │ Equipment      │ create_work_order_for_equipment  │ decommission_equipment,            │ ALL YES                              │   
  │                │                                  │ archive_equipment                  │                                      │
  ### Comments: we can simply point this action to the "create work order" script and push foward relevant details? keep t simpe. push WHO requested ot fllin role etc, date, and the equipment just bring forward?
  
  ├────────────────┼──────────────────────────────────┼────────────────────────────────────┼──────────────────────────────────────┤
  │ Fault          │ dynamic                          │ archive_fault, delete_fault        │ archive NO, delete NO                │   
  ### Comments: again, archive and delete are basicalyl the same, collaspe into one button. ad follwo soft delete protocol

  ├────────────────┼──────────────────────────────────┼────────────────────────────────────┼──────────────────────────────────────┤
  │                │                                  │ suspend_certificate,               │                                      │   
  │ Certificate    │ renew_certificate                │ archive_certificate,               │ ALL NO                               │
  
  │                │                                  │ revoke_certificate                 │                                      │
  ### Comments: suspend, archive and revoe are all basically the same, collaspe into one button for "archive". follow above protocol

  ├────────────────┼──────────────────────────────────┼────────────────────────────────────┼──────────────────────────────────────┤
  │ PartsInventory │ reorder_part /                   │ archive_part, delete_part          │ adjust YES, reorder NO, archive NO,  │   
  │                │ adjust_stock_quantity            │                                    │ delete NO                            │
  
  ### Comments: this is a repeated pattern now "delete" is commonly "missing" form all elsn action registry, hence make the same. soft delete and filtrate. 
  
  ├────────────────┼──────────────────────────────────┼────────────────────────────────────┼──────────────────────────────────────┤
  │ PurchaseOrder  │ dynamic                          │ cancel_po, delete_po               │ ALL NO                               │
  ### Comments:this is a repeated pattern now "delete" is commonly "missing" form all elsn action registry, hence make the same. soft delete and filtrate. collapse cnacel and delete into one button. 
  
  ├────────────────┼──────────────────────────────────┼────────────────────────────────────┼──────────────────────────────────────┤   
  │ Document       │ none                             │ archive_document, delete_document  │ delete YES, archive NO               │   
  ### Comments: this is a repeated pattern now "delete" is commonly "missing" form all elsn action registry, hence make the same. soft delete and filtrate. collapse delete and archive into one button
  
  ├────────────────┼──────────────────────────────────┼────────────────────────────────────┼──────────────────────────────────────┤
  │                │                                  │                                    │ file → alias to draft_warranty_claim │
  │ Warranty       │ file_warranty_claim              │ archive_warranty, void_warranty    │  (registry only, no handler), void   │   
  │                │                                  │                                    │ NO                                   │   
  ### Comments: this is a repeated pattern now "delete" is commonly "missing" form all elsn action registry, hence make the same. soft delete and filtrate. collapse void and archive into one button called "archive"
  
  ├────────────────┼──────────────────────────────────┼────────────────────────────────────┼──────────────────────────────────────┤
  │ HoursOfRest    │ submit_hours                     │ flag_violation                     │ submit NO, flag NO                   │
  
  ### Comments: flag violation is NOT. abutton, hlds no vlaue. delete. submit is most improtant button ever for this lens, how else cna crew "submit" to their hods? impossible. hence this flow is crew submits -> sends notification to HOD accordingly to "sign". either through ledger notficication OR notificatio within their "hours of rest" hod viewership. likely we need to make secondary lens ux for this submission hod section. otherwise gets confusing. treat personal (each individual workers hours of rest) as current stnading. then treat "signatures" as seperate, this will be more hsoltiic view, hod can see al their department, captina see all crew. we will filter by role/department an rank within yacht_id to showcase this. this is a much alrger task than the remainder. push till very last task
  
  ├────────────────┼──────────────────────────────────┼────────────────────────────────────┼──────────────────────────────────────┤
  │ ShoppingList   │ convert_to_po / submit_list      │ archive_list, delete_list          │ ALL NO                               │   
  ### Comments:this is a repeated pattern now "delete" is commonly "missing" form all elsn action registry, hence make the same. soft delete and filtrate. collapse delete and archive into one button
  
  ├────────────────┼──────────────────────────────────┼────────────────────────────────────┼──────────────────────────────────────┤   
  │ Receiving      │ confirm_receiving                │ flag_discrepancy                   │ confirm NO, flag NO                  │
  ### Comments: flag discrepancy proabbyl means when there is an issues (missing aprts, broken, only part N of N+1 packages) this is simple script. you can ask me questiosn abotu thsi if you are unsure. jsut iagine what someone has to do if there is an issue with shipment, and we need to log this in unfirmed fashion, rather than just relying on notes.
  
  ├────────────────┼──────────────────────────────────┼────────────────────────────────────┼──────────────────────────────────────┤
  │ Handover       │ sign_handover                    │ archive_handover, delete_handover  │ sign → alias (registry only, no      │
  │                │                                  │                                    │ handler), archive NO, delete NO      │   
  ### Comments: this is a repeated pattern now "delete" is commonly "missing" form all elsn action registry, hence make the same. soft delete and filtrate. collapse delete and archive into one button. ensure only this crew memebr can delete or hod accoridngly. 
  
  └────────────────┴──────────────────────────────────┴────────────────────────────────────┴──────────────────────────────────────┘   
                                                                                                            
  Bottom line: The frontend was written with action_ids that should exist but many don't yet. It's not random — it's a coherent naming
   convention (archive_X, delete_X, submit_X per entity). The backend just hasn't caught up. The 15 aliases need wiring, and the 37
  genuinely missing need handlers. Want me to tackle it?         

### Comments: bottom line is most are simialr issues, "delete/archive/suspend" etc are all the same function, jsut different wording. so just treat and collaspe as delete button. keep it simple for now. 
some task are larger than others, so stick with easy tasks to begin with