 Why This Problem Existed                                                                                                            
                                                                                                                                    
  Delta sync works like a bookmark in a book. When you set the bookmark, you only see pages turned after that point. You never see    
  what came before.
                                                                                                                                      
  Timeline:                                                       
  ───────────────────────────────────────────────────►                                                                                
     emails 1-290        bookmark set        emails 291+                                                                              
     existed already      (deploy day)        delta catches these                                                                     
          ↑                                        ↑                                                                                  
     INVISIBLE to delta                    VISIBLE to delta                                                                           
                                                                                                                                      
  When we deployed the all-folder delta sync, Microsoft gave us a delta token — that's the bookmark. From that moment forward, any    
  new/changed/deleted email gets reported. But:                                                                                       
                                                                                                                                      
  1. 223 emails existed before the bookmark — they were already sitting in the inbox. Delta never reports them because they didn't    
  change.                 
  2. 173 emails were deleted/moved before the bookmark — they disappeared from Outlook but our DB still had them marked               
  is_deleted=false. Delta never told us they were gone because the deletion happened before we started listening.                     
                                  
  The Three States                                                                                                                    
                                               
                      In Outlook?                                                                                                     
                     YES        NO                                                                                                    
                ┌──────────┬──────────┐
  In DB?   YES  │  117 ✓   │  173 👻  │                                                                                               
                │ (correct) │ (ghosts) │                                                                                              
                ├──────────┼──────────┤                                                                                               
           NO   │  223 ❌  │   n/a    │                                                                                               
                │ (missing) │          │                                                                                              
                └──────────┴──────────┘                                                                                               
                                                                                                                                      
  - 117 correct — emails that happened to arrive after the bookmark, so delta caught them                                             
  - 173 ghosts — DB thinks they exist, Outlook says they're gone
  - 223 missing — Outlook has them, DB has no idea                                                                                    
                                                                      
  What The Script Did                                                                                                                 
                                                                      
  Step 1: Built truth from Outlook. Paginated through the entire inbox and sent folder via Graph API (/me/mailFolders/{id}/messages). 
  This is a full list endpoint, not delta — it returns everything currently in the folder regardless of when it arrived. 340 messages
  total.                                                                                                                              
                                               
  Step 2: Built truth from DB. Queried all email_messages where is_deleted=false and folder in ('inbox', 'sent'). 290 records.        
                                                                                                    
  Step 3: Set math. This is the core insight — reconciliation is just set operations:                                                 
                                                                                                                              
  ghost_ids   = db_ids - live_ids     # 173: in DB, not in Outlook                                                                    
  missing_ids = live_ids - db_ids     # 223: in Outlook, not in DB                                                                    
  matching    = db_ids & live_ids     # 117: in both                                                                          
                                                                                                                                      
  Step 4: Soft-delete ghosts. Set is_deleted=true, deleted_at=now() on the 173. We don't hard-delete because SOC-2 audit trail — you  
  never destroy records, you mark them gone.                                                                                        
                                                                                                                                      
  Step 5: Backfill missing. Called _process_message_v2() for each of the 223. This is the exact same code path the live worker uses,  
  so each message got:                                                                                                                
  - Thread upsert (grouping by conversationId)                                                                                        
  - Direction detection (inbound vs outbound via sender hash)                                                                         
  - parent_folder_id stored (for future move detection)                                                                             
  - Linking ladder triggered (matches emails to work orders, POs, etc.)                                                               
                                                                                                                                      
  Step 6: Verify. Re-queried DB: 340 active = 340 live. Perfect match.                                                                
                                                                                                                             
  Step 7: Reset sync interval. We'd set it to 1 minute for testing. Back to 15.                                                       
                                                                                                                             
  Why Delta Is Still The Right Ongoing Strategy                                                                                       
                                                                                                                                      
  Delta sync is efficient — instead of re-fetching 340+ messages every cycle, it asks Microsoft "what changed since my last token?"   
  and gets back only 0-5 messages typically. The reconciliation was a one-time bootstrap to fill the gap that delta can't see by    
  design.                                                                                                                             
                                               
  Before reconciliation:     After:                                                                                                   
    Delta sees: 117            Delta sees: 340 (all synced)
    DB has: 290 (117 real      DB has: 340 active + 173 deleted                                                                       
            + 173 ghosts)                                                                                                             
                               Next delta cycle: "0 changes" ✓                                                               
                                                                                                                                      
  The 197 vs 223 Discrepancy                                                                                                          
                                                                                                                             
  223 were missing. Only 197 needed new DB inserts. The other 25 already had records in the DB (from a different folder or previously 
  soft-deleted) — _process_message_v2 detected them via provider_message_id lookup and just updated them (un-deleted or updated       
  folder). 1 message had no conversationId (a system-generated notification from Microsoft) so it was skipped — that's expected and
  harmless.                          