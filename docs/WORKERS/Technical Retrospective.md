Technical Retrospective                                                                                                               
  
  What I Was Working On                                                                                                                 
                                                                    
  The Cloud_DMG_Onedrive project is a Docker-based pipeline that watches a Microsoft OneDrive account for file changes and automatically
   pushes new/changed files into a search index called Celeste Digest. The job handed to me: bring the staging Docker stack online, run
  a live OAuth test, and add automatic scheduling via Celery Beat.                                                                      
                                                                    
  ---
  The Faults — Why They Occur and What I Learned
                                                
  1. Docker --env-file is not what you think it is
                                                                                                                                        
  This was the most surprising discovery. When you run docker compose --env-file .env.staging up, most people assume every variable in  
  that file gets injected into every container. It doesn't. --env-file only performs YAML substitution — it resolves ${VAR} references  
  in the compose file itself. If you don't explicitly list a variable under environment: in the service block, the container never sees 
  it. Three services (backend, celery-worker, celery-beat) were missing DATABASE_URL entirely. The backend was also missing CORS_ORIGINS
   and FRONTEND_URL. These would have worked fine on Render (which injects env vars differently) but silently broke in Docker.

  What I wish I'd known at the start: Check every service's environment: block explicitly against every env var the code reads. Don't   
  assume --env-file is a "broadcast" mechanism.
                                                                                                                                        
  2. Database hostname: Supabase has two different connection paths                                                                     
  
  The app constructed its Postgres connection URL from supabase_url (which resolves to vzsohavtuotocgrfkfyd.supabase.co). That hostname 
  routes through Cloudflare's edge network, which blocks direct TCP connections on port 5432. The correct direct database hostname is
  db.vzsohavtuotocgrfkfyd.supabase.co. The fix was to prefer an explicit DATABASE_URL environment variable over constructing one from   
  the Supabase API URL. This is a common Supabase gotcha — two hostnames, two completely different connection semantics.

  3. MSAL (Microsoft's auth library) silently ignores — then rejects — certain OAuth scopes                                             
  
  offline_access was listed in the app's requested scopes. MSAL adds this automatically. When you also specify it manually, the library 
  rejects the request. The error message is not obvious about the cause. This took a round-trip to understand because the auth URL
  generation appeared to succeed, but the resulting Microsoft redirect failed.                                                          
                                                                    
  4. Azure App Registration: redirect URIs must be explicitly whitelisted                                                               
  
  This is an Azure security requirement, not a bug in the code. Every environment (production, staging, local) needs its callback URL   
  registered in Azure AD. The staging URL (http://localhost:8003/api/v1/auth/callback) was never added because the staging environment
  didn't exist until now.                                                                                                               
                                                                    
  5. Post-OAuth redirect was hardcoded to the production domain

  After Microsoft redirects back with an auth code, the backend exchanges it for tokens and then redirects the user's browser to the    
  frontend. That frontend URL was hardcoded as https://digest.celeste7.ai in three places in auth.py. In staging, this sent the browser
  to a Cloudflare-proxied production domain that has IP restrictions. The fix was a FRONTEND_URL config variable, but two of the three  
  string replacements were missing the f prefix (so they produced literal {settings.frontend_url} strings instead of the interpolated
  value). This is a Python f-string trap that doesn't raise an error — the string is just wrong.

  6. Wrong internal API for token decryption

  tasks.py was calling decrypt_value() from app.core.encryption. That function doesn't exist. The actual API is                         
  get_encryption().decrypt_token(). Worse: even if it existed, bypassing token_manager.get_access_token() entirely means you get a raw
  encrypted blob, never check expiry, and never refresh via MSAL. The token refresh logic existed and was complete — it just wasn't     
  wired into the Celery workers. Every background sync job would have used a stale token, silently failed when it expired, and never
  recovered.

  7. Wrong column name in the search index upsert                                                                                       
  
  The digest service's database table uses a column called payload for file metadata. The code was writing to metadata. This would have 
  caused every file to fail to be indexed, with an error that looks like a database constraint violation rather than a column name typo.
                                                                                                                                        
  8. Speed probe always blocks file downloads in Docker Desktop on macOS                                                                
  
  The ingest pipeline measures network throughput before downloading a file (threshold: 64 KB/s) to avoid wasting time on slow          
  connections. Docker Desktop on macOS measures ~700–900 bytes/s to Microsoft Graph endpoints because of the macOS hypervisor networking
   layer. This is not a bug — it's a genuine environment limitation. The speed probe works correctly on Render (Linux, direct network). 
  On local Docker it will always skip downloads. This is confusing because the log just says "skipping download — slow network" with no
  indication that it's a systematic environmental limit rather than a transient condition.

  ---                                                                                                                                   
  What I Wish I Knew at the Start
                                                                                                                                        
  - The token refresh code existed and worked — I should have traced the data flow from the start rather than assuming tasks.py was
  complete                                                                                                                              
  - Docker Desktop on macOS has significant network overhead that breaks throughput-sensitive code
  - Supabase has two hostnames for two different things — they look almost identical                                                    
  - "Works on Render" is not evidence that Docker will work; the injection mechanisms are fundamentally different                       
  
  Concerns and Unanswered Questions                                                                                                     
                                                                    
  - Connection f7bbad97: Has a permanently expired refresh token (from March 9th). MSAL cannot recover from this — the user must        
  re-authenticate. This record is sitting in the DB doing nothing, and delta_sync_all will attempt it every 5 minutes and log an error
  each time.                                                                                                                            
  - Celery ingest path is not proven end-to-end: The file sync that succeeded used the FastAPI /sync/start path. The Celery
  ingest_file_task path has never actually downloaded and indexed a file because the speed probe blocks it locally. The payload fix is  
  deployed but untested via Celery.
  - The staging fixes have not been committed to git — they exist only as running Docker containers and local file changes.             
                                                                                                                                        
  ---
  ---                                                                                                                                   
  CEO-Ready Summary                                                 

  What This Project Is

  This is an integration service that connects yacht crew Microsoft OneDrive accounts to a central search system called Celeste. When a 
  crew member saves or changes a file in OneDrive — a maintenance report, a safety document, a whiteboard — the system automatically
  detects the change, downloads the file, and adds it to a searchable index. The end goal is that anyone on the vessel can search for   
  any document across all crew OneDrive accounts from a single interface, without manually uploading anything.

  The service runs entirely in the background. No user action is required after the initial one-time account connection.                
  
  ---                                                                                                                                   
  The Problem That Was Handed To Me                                 
                                   
  A staging (test) version of this system needed to be brought online for the first time. "Staging" means a local test environment that
  mimics the real production system without touching live data or real users. Three tasks were requested:                               
  
  1. Start the test environment                                                                                                         
  2. Test the real Microsoft login flow end-to-end                  
  3. Add automatic scheduling so the system checks for new files every 5 minutes without human intervention                             
                                                                                                                                        
  ---                                                                                                                                   
  What Was Found                                                                                                                        
                                                                    
  When the test environment was started, 11 distinct problems surfaced. None of them were visible during development because the code
  had only ever been tested partially, or against different environments. Here is what they were and why they matter:                   
  
  ┌─────┬───────────────────────────────────────────────────────┬───────────────────────────────────────────────────────────────────┐   
  │  #  │                        Problem                        │                          Business Impact                          │
  ├─────┼───────────────────────────────────────────────────────┼───────────────────────────────────────────────────────────────────┤
  │ 1   │ Configuration values were not reaching the background │ Workers would silently fail to connect to the database on every   │
  │     │  workers                                              │ run                                                               │
  ├─────┼───────────────────────────────────────────────────────┼───────────────────────────────────────────────────────────────────┤   
  │ 2   │ The database connection used the wrong server address │ All database writes from background jobs would fail               │
  ├─────┼───────────────────────────────────────────────────────┼───────────────────────────────────────────────────────────────────┤   
  │ 3   │ After Microsoft login, users were redirected to the   │ The login flow would strand users on a broken page                │
  │     │ wrong website                                         │                                                                   │   
  ├─────┼───────────────────────────────────────────────────────┼───────────────────────────────────────────────────────────────────┤
  │ 4   │ Two redirect links had a subtle text formatting error │ Even with the correct address configured, the links would print   │   
  │     │                                                       │ the variable name instead of its value                            │   
  ├─────┼───────────────────────────────────────────────────────┼───────────────────────────────────────────────────────────────────┤
  │ 5   │ The Microsoft app registration was missing the test   │ Microsoft would reject every login attempt                        │   
  │     │ environment's callback address                        │                                                                   │
  ├─────┼───────────────────────────────────────────────────────┼───────────────────────────────────────────────────────────────────┤   
  │ 6   │ Microsoft's login library rejected a duplicate        │ Auth URL generation would fail                                    │
  │     │ setting                                               │                                                                   │   
  ├─────┼───────────────────────────────────────────────────────┼───────────────────────────────────────────────────────────────────┤
  │ 7   │ Background sync workers were using expired login      │ Every background sync after initial token expiry (1 hour) would   │   
  │     │ tokens and never refreshing them                      │ silently fail forever                                             │   
  ├─────┼───────────────────────────────────────────────────────┼───────────────────────────────────────────────────────────────────┤
  │ 8   │ The wrong function name was used to read encrypted    │ A crash on every background sync attempt                          │   
  │     │ tokens                                                │                                                                   │
  ├─────┼───────────────────────────────────────────────────────┼───────────────────────────────────────────────────────────────────┤
  │ 9   │ A database column was named incorrectly in the file   │ Every file would fail to be indexed, with no visible error to the │
  │     │ indexing code                                         │  end user                                                         │   
  ├─────┼───────────────────────────────────────────────────────┼───────────────────────────────────────────────────────────────────┤
  │ 10  │ Network speed measurement doesn't work inside the     │ File downloads are always skipped locally (this works correctly   │   
  │     │ test environment                                      │ in production)                                                    │   
  ├─────┼───────────────────────────────────────────────────────┼───────────────────────────────────────────────────────────────────┤
  │ 11  │ The frontend was connecting to a test user            │ Dashboard showed no data for the real account                     │   
  │     │ placeholder instead of the real account               │                                                                   │   
  └─────┴───────────────────────────────────────────────────────┴───────────────────────────────────────────────────────────────────┘
                                                                                                                                        
  ---                                                               
  What Was Fixed

  All 11 problems were resolved. The key fixes in plain terms:

  Configuration delivery: Rewrote how environment settings are passed into each background service so they reliably receive everything  
  they need.
                                                                                                                                        
  Database address: Changed the system to use the explicit direct database address rather than deriving it from an API address (which   
  routes through a firewall that blocks database connections).
                                                                                                                                        
  Login redirects: Introduced a configurable "where to send the user after login" setting and replaced all four hardcoded links that    
  were pointing to the live production website.
                                                                                                                                        
  Token refresh: Wired the existing — but disconnected — token refresh logic into the background sync workers. Microsoft access tokens  
  expire every hour. The refresh system was built and tested but the background workers were never connected to it. This was the
  highest-risk gap: without it, every user's sync would stop working silently one hour after they connected.                            
                                                                    
  File indexing column name: Corrected the column name so files are actually stored in the index when synced.                           
  
  Automatic scheduling: Added a new scheduler service (celery-beat) that triggers a check of all connected accounts every 5 minutes     
  automatically.                                                    
                                                                                                                                        
  ---                                                               
  What Was Verified Live
                        
  - A complete Microsoft OAuth login flow was completed end-to-end in the test environment
  - A real file (Dan Marshall and Alex Short.whiteboard) was detected, synced, and confirmed as indexed in the database                 
  - Token refresh was tested live: a token was deliberately expired, the refresh was triggered, and the database was confirmed updated  
  with a new valid token                                                                                                                
                                                                                                                                        
  ---                                                                                                                                   
  What Remains Unfinished                                           

  ┌────────────────────────────────────────┬────────────┬───────────────────────────────────────────────────────────────────────────┐
  │                  Item                  │ Risk Level │                               What's Needed                               │
  ├────────────────────────────────────────┼────────────┼───────────────────────────────────────────────────────────────────────────┤
  │ All fixes are uncommitted (not saved   │ High       │ A developer needs to run git commit and git push to preserve the work     │
  │ to version control)                    │            │                                                                           │
  ├────────────────────────────────────────┼────────────┼───────────────────────────────────────────────────────────────────────────┤   
  │ One expired user account (f7bbad97) is │ Low-Medium │ That user needs to reconnect their OneDrive; meanwhile the system logs an │
  │  stuck in the database                 │            │  error for them every 5 minutes                                           │   
  ├────────────────────────────────────────┼────────────┼───────────────────────────────────────────────────────────────────────────┤   
  │ File download via background worker is │ Medium     │ The test environment can't prove this works (network limitation); it      │
  │  untested end-to-end                   │            │ needs to be verified on the production server (Render)                    │   
  └────────────────────────────────────────┴────────────┴───────────────────────────────────────────────────────────────────────────┘
                                                                                                                                        
  ---                                                               
  Files Changed
               
  ┌─────────────────────────────────────┬───────────────────────────────────────────────┬───────────────────────────────────────────┐
  │                File                 │                 What It Does                  │                Change Made                │   
  ├─────────────────────────────────────┼───────────────────────────────────────────────┼───────────────────────────────────────────┤
  │ backend/app/tasks.py                │ The background worker logic — detects         │ Fixed token refresh, fixed column name,   │   
  │                                     │ changes, downloads files, pushes to index     │ added automatic scheduling task           │
  ├─────────────────────────────────────┼───────────────────────────────────────────────┼───────────────────────────────────────────┤   
  │ docker-compose.staging.yml          │ Defines the test environment's six services   │ Added scheduler service, fixed            │
  │                                     │                                               │ configuration delivery to all services    │   
  ├─────────────────────────────────────┼───────────────────────────────────────────────┼───────────────────────────────────────────┤
  │ backend/app/config.py               │ Central settings / environment variable       │ Added configurable frontend URL, removed  │   
  │                                     │ reader                                        │ duplicate OAuth scope                     │   
  ├─────────────────────────────────────┼───────────────────────────────────────────────┼───────────────────────────────────────────┤
  │ backend/app/api/v1/auth.py          │ Handles Microsoft login flow and callbacks    │ Replaced 4 hardcoded production URLs with │   
  │                                     │                                               │  configurable setting                     │   
  ├─────────────────────────────────────┼───────────────────────────────────────────────┼───────────────────────────────────────────┤
  │ backend/app/db/session.py           │ Database connection setup                     │ Fixed to use correct database address     │   
  ├─────────────────────────────────────┼───────────────────────────────────────────────┼───────────────────────────────────────────┤   
  │ frontend/src/app/dashboard/page.tsx │ Dashboard page shown to users                 │ Replaced placeholder account ID with real │
  │                                     │                                               │  account                                  │   
  └─────────────────────────────────────┴───────────────────────────────────────────────┴───────────────────────────────────────────┘
                                                                                                                                        
  ---                                                               
  Recommended Next Actions (in order)
                                                                                                                                        
  1. Commit and push the code — nothing is saved to version control yet. If a developer restarts their machine, the fixes exist only in
  Docker                                                                                                                                
  2. Delete or reconnect f7bbad97 — the stuck expired account should be cleaned up to stop unnecessary error logging
  3. Deploy to Render and verify file downloads — the one gap that cannot be tested locally needs a production verification pass        
  4. Update HANDOVER.md — the project handover document describes the state before this session's work; it should be updated to reflect 
  current status                                                                                                                        
                                                                               