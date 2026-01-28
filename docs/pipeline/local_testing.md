 Here's your complete local testing infrastructure:                                  
                                                                                      
  Local Testing Facilities Summary                                                    
                                                                                      
  Quick Reference Table                                                               
  ┌─────────────────┬────────────────────────────────┬──────────┬────────────────────┐
  │    Facility     │            Command             │ Duration │      Use Case      │
  ├─────────────────┼────────────────────────────────┼──────────┼────────────────────┤
  │ TypeScript      │ cd apps/web && npm run         │          │ Pre-commit,        │
  │ Check           │ typecheck                      │ ~30s     │ catches type       │
  │                 │                                │          │ errors             │
  ├─────────────────┼────────────────────────────────┼──────────┼────────────────────┤
  │ ESLint          │ cd apps/web && npm run lint    │ ~20s     │ Pre-commit, code   │
  │                 │                                │          │ quality            │
  ├─────────────────┼────────────────────────────────┼──────────┼────────────────────┤
  │ Vitest (Unit)   │ cd apps/web && npm run test    │ ~1min    │ Pre-commit, fast   │
  │                 │                                │          │ feedback           │
  ├─────────────────┼────────────────────────────────┼──────────┼────────────────────┤
  │ Vitest          │ cd apps/web && npm run         │ ~2min    │ Pre-push, 60%      │
  │ (Coverage)      │ test:coverage                  │          │ threshold          │
  ├─────────────────┼────────────────────────────────┼──────────┼────────────────────┤
  │ Next.js Build   │ cd apps/web && npm run build   │ ~3min    │ Pre-push, catches  │
  │                 │                                │          │ build errors       │
  ├─────────────────┼────────────────────────────────┼──────────┼────────────────────┤
  │ Pytest (Unit)   │ cd apps/api && pytest -m "not  │ ~1min    │ Pre-commit         │
  │                 │ integration"                   │          │                    │
  ├─────────────────┼────────────────────────────────┼──────────┼────────────────────┤
  │ Pytest          │ cd apps/api && pytest -m       │ ~3min    │ Needs Supabase     │
  │ (Integration)   │ integration                    │          │                    │
  ├─────────────────┼────────────────────────────────┼──────────┼────────────────────┤
  │ Contract Tests  │ npm run test:contracts         │ ~2min    │ API validation, no │
  │                 │                                │          │  browser           │
  ├─────────────────┼────────────────────────────────┼──────────┼────────────────────┤
  │ E2E Tests       │ npm run test:e2e               │ ~10min   │ Full integration   │
  ├─────────────────┼────────────────────────────────┼──────────┼────────────────────┤
  │ Docker RLS      │ docker-compose -f              │ ~5min    │ Role/RLS           │
  │ Tests           │ docker-compose.test.yml up     │          │ validation         │
  └─────────────────┴────────────────────────────────┴──────────┴────────────────────┘
  ---                                                                                 
  Development Workflow                                                                
                                                                                      
  ┌─────────────────────────────────────────────────────────────────┐                 
  │  LOCAL DEV (continuous)                                         │                 
  │  npm run dev (apps/web)  +  uvicorn (apps/api)                 │                  
  │  or: docker-compose up                                          │                 
  └─────────────────────────────────────────────────────────────────┘                 
                                │                                                     
                                ▼                                                     
  ┌─────────────────────────────────────────────────────────────────┐                 
  │  PRE-COMMIT (~2min)                                             │                 
  │  cd apps/web && npm run lint && npm run typecheck && npm test  │                  
  │  cd apps/api && pytest -m "not integration"                     │                 
  └─────────────────────────────────────────────────────────────────┘                 
                                │                                                     
                                ▼                                                     
  ┌─────────────────────────────────────────────────────────────────┐                 
  │  PRE-PUSH (~8min)                                               │                 
  │  npm run test:contracts                                         │                 
  │  cd apps/web && npm run test:coverage && npm run build          │                 
  │  docker-compose -f docker-compose.test.yml up (RLS tests)       │                 
  └─────────────────────────────────────────────────────────────────┘                 
                                │                                                     
                                ▼                                                     
  ┌─────────────────────────────────────────────────────────────────┐                 
  │  PUSH TO RENDER (only when pre-push passes)                     │                 
  │  git push origin main                                           │                 
  └─────────────────────────────────────────────────────────────────┘                 
                                                                                      
  ---                                                                                 
  Docker Infrastructure                                                               
                                                                                      
  1. Development Stack (docker-compose.yml)                                           
  docker-compose up --build    # API:8000 + Web:3000                                  
  docker-compose logs -f api   # Watch API logs                                       
                                                                                      
  2. RLS/Test Stack (docker-compose.test.yml)                                         
  docker-compose -f docker-compose.test.yml up --build                                
  # API:8889 + test-runner for role-gating tests                                      
                                                                                      
  3. Individual Containers                                                            
  # API only                                                                          
  docker build -t celeste-api apps/api                                                
  docker run -p 8000:8080 celeste-api                                                 
                                                                                      
  # Web only                                                                          
  docker build -t celeste-web apps/web                                                
  docker run -p 3000:3000 celeste-web                                                 
                                                                                      
  ---                                                                                 
  Local Supabase (Full DB)                                                            
                                                                                      
  # Start local Supabase (ports 54321-54324)                                          
  ./scripts/dev/supabase_start.sh                                                     
  # Opens Studio at http://127.0.0.1:54323                                            
                                                                                      
  # Stop (preserves data)                                                             
  ./scripts/dev/supabase_stop.sh                                                      
                                                                                      
  # Hard reset (wipes everything)                                                     
  ./scripts/dev/supabase_reset.sh                                                     
                                                                                      
  ---                                                                                 
  Branch Strategy                                                                     
  ┌────────────┬─────────────┬──────────────────────────────────┐                     
  │   Branch   │   Purpose   │          Push Triggers           │                     
  ├────────────┼─────────────┼──────────────────────────────────┤                     
  │ main       │ Production  │ Full CI + E2E + Deploy to Render │                     
  ├────────────┼─────────────┼──────────────────────────────────┤                     
  │ feature/*  │ Development │ ci-web.yml + ci-api.yml only     │                     
  ├────────────┼─────────────┼──────────────────────────────────┤                     
  │ Local only │ Experiments │ Nothing                          │                     
  └────────────┴─────────────┴──────────────────────────────────┘                     
  Recommended flow:                                                                   
  # Work on feature branch                                                            
  git checkout -b feature/entity-mappings                                             
                                                                                      
  # Run local tests frequently                                                        
  npm run test:contracts                                                              
                                                                                      
  # When ready, push feature branch (triggers CI, not deploy)                         
  git push origin feature/entity-mappings                                             
                                                                                      
  # After CI passes, merge to main (triggers deploy)                                  
  git checkout main && git merge feature/entity-mappings && git push                  
                                                                                      
  ---                                                                                 
  E2E Test Modes                                                                      
                                                                                      
  # Headless (CI-like)                                                                
  npm run test:e2e                                                                    
                                                                                      
  # Interactive UI (debugging)                                                        
  npm run test:e2e:ui                                                                 
                                                                                      
  # Visible browser                                                                   
  npm run test:e2e:headed                                                             
                                                                                      
  # Debug single test                                                                 
  npx playwright test tests/e2e/search.spec.ts --debug                                
                                                                                      
  # Contract tests only (no browser, fast)                                            
  npm run test:contracts                                                              
                                                                                      
  ---                                                                                 
  Key Files                                                                           
  ┌──────────────────┬─────────────────────────┐                                      
  │     Purpose      │        Location         │                                      
  ├──────────────────┼─────────────────────────┤                                      
  │ Frontend scripts │ apps/web/package.json   │                                      
  ├──────────────────┼─────────────────────────┤                                      
  │ Backend tests    │ apps/api/pytest.ini     │                                      
  ├──────────────────┼─────────────────────────┤                                      
  │ E2E config       │ playwright.config.ts    │                                      
  ├──────────────────┼─────────────────────────┤                                      
  │ Docker dev       │ docker-compose.yml      │                                      
  ├──────────────────┼─────────────────────────┤                                      
  │ Docker test      │ docker-compose.test.yml │                                      
  ├──────────────────┼─────────────────────────┤                                      
  │ Test credentials │ .env.e2e                │                                      
  ├──────────────────┼─────────────────────────┤                                      
  │ CI workflows     │ .github/workflows/      │                                      
  └──────────────────┴─────────────────────────┘                                      
  ---                                                                                 
  Recommended Testing Cadence                                                         
                                                                                      
  Every save: TypeScript errors in IDE                                                
  Every commit: lint + typecheck + unit tests (~2min)                                 
  Every push: contracts + coverage + build (~8min)                                    
  Before Render deploy: docker-compose.test.yml RLS tests (~5min)                     
                                                                                      
  This keeps Render deploys to only verified code and prevents throttling their build 
  minutes.                                         