                                                                              
                                                                                                                               
  Files Created                                                                                                                
                                                                                                                               
  docs/AGENTS/                                                                                                                 
  ├── README.md              # How to use the worker configs                                                                   
  ├── FRONTEND_WORKER.md     # Frontend Claude.md (5.2 KB)                                                                     
  └── BACKEND_WORKER.md      # Backend Claude.md (7.3 KB)                                                                      
                                                                                                                               
  .planning/                                                                                                                   
  ├── frontend-requests/     # Frontend → Backend requests                                                                     
  ├── backend-requests/      # Backend → Frontend notifications                                                                
  └── shared/                # Cross-team docs                                                                                 
                                                                                                                               
  scripts/                                                                                                                     
  └── start-worker.sh        # Quick-start script                                                                              
                                                                                                                               
  Quick Start                                                                                                                  
                                                                                                                               
  Option 1: Simple (same repo)                                                                                                 
  cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS                                                                             
                                                                                                                               
  # Terminal 1 - Frontend                                                                                                      
  cp docs/AGENTS/FRONTEND_WORKER.md CLAUDE.md && claude                                                                        
                                                                                                                               
  # Terminal 2 - Backend                                                                                                       
  cp docs/AGENTS/BACKEND_WORKER.md CLAUDE.md && claude                                                                         
                                                                                                                               
  Option 2: Using script                                                                                                       
  # Terminal 1                                                                                                                 
  ./scripts/start-worker.sh frontend                                                                                           
                                                                                                                               
  # Terminal 2                                                                                                                 
  ./scripts/start-worker.sh backend                                                                                            
                                                                                                                               
  Option 3: Git worktrees (best isolation)                                                                                     
  # Terminal 1 - creates ../cloud_pms_frontend/                                                                                
  ./scripts/start-worker.sh frontend --worktree                                                                                
                                                                                                                               
  # Terminal 2 - creates ../cloud_pms_backend/                                                                                 
  ./scripts/start-worker.sh backend --worktree                                                                                 
                                                                                                                               
  What Each Worker Gets                                                                                                        
  ┌──────────────┬─────────────────────────────────────────────┬─────────────────────────────┐                                 
  │   Feature    │                  Frontend                   │           Backend           │                                 
  ├──────────────┼─────────────────────────────────────────────┼─────────────────────────────┤                                 
  │ Owned paths  │ apps/web/                                   │ apps/api/, supabase/        │                                 
  ├──────────────┼─────────────────────────────────────────────┼─────────────────────────────┤                                 
  │ Plugins      │ frontend-design, typescript-lsp, playwright │ supabase, security-guidance │                                 
  ├──────────────┼─────────────────────────────────────────────┼─────────────────────────────┤                                 
  │ Verification │ typecheck, lint, vitest, build              │ pytest, pylint, mypy        │                                 
  ├──────────────┼─────────────────────────────────────────────┼─────────────────────────────┤                                 
  │ Superpowers  │ Enforced                                    │ Enforced                    │                                 
  ├──────────────┼─────────────────────────────────────────────┼─────────────────────────────┤                                 
  │ Coordination │ .planning/frontend-requests/                │ .planning/backend-requests/ │                                 
  └──────────────┴─────────────────────────────────────────────┴─────────────────────────────┘                  