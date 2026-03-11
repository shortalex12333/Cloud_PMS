
                                                                         
  Render Config Files (the blueprints that create billable services)                                                                
                                                                                                                                    
  ┌───────────────────────────┬────────────────────────────────────────────────────────────────────────────────────────┬─────────┐  
  │           File            │                                    Services Defined                                    │  Cost   │  
  ├───────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────┼─────────┤
  │ /render.yaml (root)       │ 7 services: pipeline-v1, email-watcher, documents-health, shopping-list-health,        │ ~$49/mo │
  │                           │ nightly-feedback, + 2 duplicate email-rag entries                                      │         │
  ├───────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────┼─────────┤
  │ /apps/api/render.yaml     │ 1 service: email-rag-worker (duplicate of above)                                       │ $7/mo   │
  ├───────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────┼─────────┤
  │ /apps/api/render-api.yaml │ 2 services: celeste-api-staging + email-rag-worker (another duplicate)                 │ $14/mo  │
  └───────────────────────────┴────────────────────────────────────────────────────────────────────────────────────────┴─────────┘

  That's 3 separate blueprint files defining overlapping services — a clear sign of multiple agents creating services without
  knowing the others existed.

  Code/Config Files with Render URLs Hardcoded

  ┌──────────────────────────────────────────────────────┬─────────────────────────────────────────────┐
  │                         File                         │                What's there                 │
  ├──────────────────────────────────────────────────────┼─────────────────────────────────────────────┤
  │ apps/web/next.config.js                              │ Probably onrender.com in rewrites/redirects │
  ├──────────────────────────────────────────────────────┼─────────────────────────────────────────────┤
  │ apps/web/src/lib/handoverExportClient.ts             │ Hardcoded Render API URL                    │
  ├──────────────────────────────────────────────────────┼─────────────────────────────────────────────┤
  │ apps/web/src/lib/microactions/handlers/compliance.ts │ Hardcoded Render API URL                    │
  ├──────────────────────────────────────────────────────┼─────────────────────────────────────────────┤
  │ apps/web/src/lib/microactions/handlers/handover.ts   │ Hardcoded Render API URL                    │
  ├──────────────────────────────────────────────────────┼─────────────────────────────────────────────┤
  │ apps/web/e2e/fixtures.ts                             │ Render URL in E2E test base URL             │
  ├──────────────────────────────────────────────────────┼─────────────────────────────────────────────┤
  │ apps/api/routes/receiving_upload.py                  │ Render URL reference                        │
  ├──────────────────────────────────────────────────────┼─────────────────────────────────────────────┤
  │ apps/api/handlers/handover_handlers.py               │ Render URL reference                        │
  ├──────────────────────────────────────────────────────┼─────────────────────────────────────────────┤
  │ apps/api/tests/conftest.py                           │ Render URL in test config                   │
  ├──────────────────────────────────────────────────────┼─────────────────────────────────────────────┤
  │ apps/api/services/handover_html_parser.py            │ Render URL reference                        │
  ├──────────────────────────────────────────────────────┼─────────────────────────────────────────────┤
  │ scripts/dev/prove_prod_parity.sh                     │ Render URL for parity checks                │
  ├──────────────────────────────────────────────────────┼─────────────────────────────────────────────┤
  │ .github/workflows/playwright-e2e.yml                 │ Render URL for CI                           │
  └──────────────────────────────────────────────────────┴─────────────────────────────────────────────┘

  Docs/Planning (reference only, not billable)

  ┌────────────────────────────────────────────────────┬─────────────────────────────────────┐
  │                        File                        │               Content               │
  ├────────────────────────────────────────────────────┼─────────────────────────────────────┤
  │ docs/EXPLANATIONS/F1_SEARCH_ENGINE_ARCHITECTURE.md │ srv- IDs listing Render deployments │
  ├────────────────────────────────────────────────────┼─────────────────────────────────────┤
  │ .planning/codebase/INTEGRATIONS.md                 │ Render deployment references        │
  ├────────────────────────────────────────────────────┼─────────────────────────────────────┤
  │ .planning/phases/14-*                              │ Phase plans mentioning Render       │
  ├────────────────────────────────────────────────────┼─────────────────────────────────────┤
  │ .planning/archive/search-v1.1-v1.2/                │ Historical search hardening doc     │
  └────────────────────────────────────────────────────┴─────────────────────────────────────┘

  ★ Insight ─────────────────────────────────────
  The duplication is the real problem: There are 3 render YAML files defining the same email-rag-worker service independently. Each
  one creates a separate billable worker on Render. The root render.yaml alone defines 7 Starter services. If all 3 blueprints were
  deployed, you could have up to 10 billable services running — some doing nothing, some duplicating each other.

  The hardcoded Render URLs in frontend code (handoverExportClient.ts, compliance.ts, handover.ts) are a problem for going local —
  those will need to be switched to use NEXT_PUBLIC_API_URL instead of hardcoded onrender.com URLs. That's the next cleanup step
  after cancelling Render.
  ─────────────────────────────────────────────────






  BACK_BUTTON_CLOUD_PMS/
  ├── apps/
  │   ├── api/            ← Backend source + Dockerfile
  │   │   └── .env        ← For direct host execution only
  │   └── web/            ← Frontend source + Dockerfile
  │
  ├── deploy/
  │   ├── DEPLOY.md       ← Start here. Full guide.
  │   ├── local/          ← THE ACTIVE DEPLOYMENT
  │   │   ├── .env            All secrets
  │   │   ├── .env.web        Frontend env
  │   │   ├── docker-compose.yml
  │   │   ├── celeste.sh      CLI
  │   │   └── .gitignore
  │   └── archive/        ← Old files (reference only)
  │       ├── render/         3 Render blueprints (cancelled)
  │       ├── old-compose/    4 old docker-compose files
  │       ├── old-env/        9 old .env files
  │       └── old-scripts/    5 old startup scripts
  │
  ├── docs/               ← Architecture docs (unchanged)
  ├── scripts/            ← Utility scripts (unchanged)
