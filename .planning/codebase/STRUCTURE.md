# CelesteOS PMS - Directory Structure & File Organization

## Root Directory

```
/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/
├── apps/                               # Monorepo applications
│   ├── api/                            # FastAPI backend (Python)
│   ├── web/                            # Next.js frontend (TypeScript/React)
│   └── test-automation/                # Playwright E2E tests
├── database/                           # Database schema, migrations
├── docs/                               # Documentation
│   └── pipeline/
│       └── entity_lenses/              # Lens specifications
├── migrations/                         # Legacy migrations (pre-master_migrations)
├── supabase/                           # Supabase configuration
├── tests/                              # Test suites
├── scripts/                            # Utility scripts
├── shopping_list_patches/              # Local patch management
├── .planning/                          # Session planning documents
│   └── codebase/                       # ← THIS DIRECTORY (architecture docs)
├── docker-compose.yml                  # Docker orchestration
├── package.json                        # Root workspace
└── [test files, scripts, configs...]   # Utility files (various test runners, etc.)
```

---

## apps/api/ - FastAPI Backend

### Structure Overview

```
apps/api/
├── __init__.py                         # Package marker + version
├── action_router/                      # Action execution pipeline
│   ├── __init__.py
│   ├── registry.py                     # ACTION REGISTRY - SINGLE SOURCE OF TRUTH
│   ├── router.py                       # Main POST /v1/actions/execute endpoint
│   ├── logger.py                       # Action execution logging
│   ├── dispatchers/                    # Request dispatch engines
│   │   ├── __init__.py
│   │   ├── internal_dispatcher.py      # Routes to handler modules (primary)
│   │   ├── n8n_dispatcher.py          # DEPRECATED: Old n8n integration
│   │   └── secure_dispatcher.py        # For SIGNED actions
│   ├── middleware/                     # Request processing pipeline
│   │   ├── __init__.py
│   │   ├── validation_middleware.py    # 7-stage validation pipeline
│   │   └── state_machine.py            # State transition enforcement
│   ├── validators/                     # Validation modules
│   │   ├── __init__.py
│   │   ├── jwt_validator.py            # JWT token verification
│   │   ├── schema_validator.py         # Payload schema validation
│   │   ├── field_validator.py          # Required fields check
│   │   ├── role_validator.py           # Role-based access control
│   │   ├── rls_entity_validator.py    # Row-level security check
│   │   ├── yacht_validator.py          # Yacht isolation enforcement
│   │   └── validation_result.py        # Result data class
│   └── schemas/                        # Pydantic schema definitions
│       └── __init__.py
│
├── handlers/                           # Domain-specific business logic
│   ├── __init__.py
│   ├── db_client.py                    # Database access layer
│   ├── schema_mapping.py               # Schema to handler mapping
│   │
│   ├── [EQUIPMENT HANDLERS]
│   ├── equipment_handlers.py           # Equipment read operations
│   ├── equipment_utils.py              # Helper utilities
│   │
│   ├── [FAULT HANDLERS]
│   ├── fault_handlers.py               # Fault reads + list operations
│   ├── fault_mutation_handlers.py      # Fault create/update/delete
│   │
│   ├── [PART/INVENTORY HANDLERS]
│   ├── part_handlers.py                # Part & inventory operations
│   │
│   ├── [WORK ORDER HANDLERS]
│   ├── work_order_handlers.py          # Work order reads
│   ├── work_order_mutation_handlers.py # Work order create/update/delete
│   │
│   ├── [RECEIVING HANDLERS]
│   ├── receiving_handlers.py           # Parts receiving operations
│   │
│   ├── [SHOPPING LIST HANDLERS]
│   ├── shopping_list_handlers.py       # Shopping list management
│   │
│   ├── [HOURS OF REST HANDLERS]
│   ├── hours_of_rest_handlers.py       # Crew duty/rest tracking
│   │
│   ├── [WATCH HANDOVER HANDLERS]
│   ├── handover_handlers.py            # Handover reports
│   ├── handover_workflow_handlers.py   # Handover workflow
│   │
│   ├── [CERTIFICATE HANDLERS]
│   ├── certificate_handlers.py         # Certificate management
│   │
│   ├── [DOCUMENT HANDLERS]
│   ├── document_handlers.py            # PMS documents
│   ├── document_comment_handlers.py    # Document annotations
│   ├── secure_document_handlers.py     # Secure document access
│   │
│   ├── [WARRANTY HANDLERS]
│   ├── warranty_handlers.py            # Warranty tracking
│   │
│   ├── [SITUATION HANDLERS]
│   ├── situation_handlers.py           # Situation/incident tracking
│   │
│   ├── [LIST/SEARCH HANDLERS]
│   ├── list_handlers.py                # List & search operations
│   │
│   ├── [COMPLIANCE HANDLERS]
│   ├── p1_compliance_handlers.py       # Regulatory compliance
│   ├── p1_purchasing_handlers.py       # Purchase orders
│   │
│   ├── [READ-ONLY/LIGHT HANDLERS]
│   ├── p2_mutation_light_handlers.py   # Light mutations
│   ├── p3_read_only_handlers.py        # Read-only operations
│   │
│   ├── [ADMIN HANDLERS]
│   ├── admin_handlers.py               # Admin operations
│   ├── secure_admin_handlers.py        # Secure admin ops
│   │
│   ├── [CONTEXT HANDLERS]
│   ├── context_navigation_handlers.py  # Context navigation helpers
│   │
│   └── [BACKUP FILES]
│       └── receiving_handlers.py.bak*  # Version backups
│
├── routes/                             # HTTP route handlers
│   ├── p0_actions_routes.py           # Main actions endpoint (290KB)
│   ├── email.py                        # Email integration (173KB)
│   ├── auth_routes.py                  # Authentication flows
│   ├── certificate_routes.py           # Certificate REST endpoints
│   ├── fault_routes.py                 # Fault REST endpoints
│   ├── equipment_handlers.py           # Wait, this is in handlers/
│   ├── work_order_routes.py            # Work order REST endpoints
│   ├── part_routes.py                  # Parts REST endpoints
│   ├── hours_of_rest_routes.py         # Hours of rest REST endpoints
│   ├── document_routes.py              # Document REST endpoints
│   ├── handover_export_routes.py       # Handover export endpoint
│   ├── ledger_routes.py                # Ledger/audit log endpoints
│   ├── related_routes.py               # Related entities endpoints
│   ├── context_navigation_routes.py    # Context nav REST endpoints
│   ├── orchestrated_search_routes.py   # Orchestrated search endpoint
│   ├── f1_search_streaming.py          # F1 search with streaming
│   ├── search_streaming.py             # General search streaming
│   ├── rag_endpoint.py                 # RAG query endpoint
│   ├── receiving_upload.py             # Receiving file upload
│   ├── decisions_routes.py             # Decision tree endpoint
│   └── triggers_routes.py              # Trigger management endpoint
│
├── microactions/                       # Micro-action infrastructure
│   ├── __init__.py
│   ├── base_microaction.py             # Base class for microactions
│   ├── microaction_registry.py         # Microaction registration
│   └── lens_microactions/              # Lens-specific microactions
│       └── [lens_specific_files]
│
├── services/                           # Business services
│   ├── __init__.py
│   └── [service_modules]
│
├── middleware/                         # Global middleware
│   ├── __init__.py
│   ├── auth.py                         # JWT/auth middleware
│   └── [other_middleware]
│
├── db/                                 # Database layer
│   ├── __init__.py
│   └── tenant_pg_gateway.py            # Supabase client connection
│
├── database/                           # Database schema management
│   ├── master_migrations/              # Current migration system
│   │   └── [migration_files]
│   └── [legacy_migration_files]
│
├── config/                             # Configuration management
│   ├── __init__.py
│   ├── env.py                          # Environment settings
│   └── [config_modules]
│
├── cache/                              # Caching layer
│   ├── __init__.py
│   └── invalidation_listener.py        # Cache invalidation
│
├── extraction/                         # Data extraction
│   ├── __init__.py
│   └── [extraction_modules]
│
├── email_rag/                          # Email RAG system
│   ├── __init__.py
│   └── [email_modules]
│
├── rag/                                # RAG components
│   ├── __init__.py
│   └── [rag_modules]
│
├── cortex/                             # AI/ML components
│   ├── __init__.py
│   └── [ai_modules]
│
├── context_nav/                        # Context navigation
│   ├── __init__.py
│   └── [context_modules]
│
├── orchestration/                      # Orchestration logic
│   ├── __init__.py
│   └── [orchestration_modules]
│
├── integrations/                       # Third-party integrations
│   ├── __init__.py
│   └── [integration_modules]
│
├── observability/                      # Monitoring & observability
│   ├── __init__.py
│   └── [observability_modules]
│
├── rankers/                            # Ranking/scoring modules
│   ├── __init__.py
│   └── [ranker_modules]
│
├── logs/                               # Structured logging
│   ├── __init__.py
│   └── [log_modules]
│
├── prepare/                            # Preparation/prefill logic
│   ├── __init__.py
│   ├── capabilities/                   # Capability detection
│   │   └── [capability_modules]
│   └── [prepare_modules]
│
├── execute/                            # Execution helpers
│   ├── __init__.py
│   └── [execute_modules]
│
├── docs/                               # API documentation
│   ├── __init__.py
│   └── [api_docs]
│
├── scripts/                            # Utility scripts
│   ├── ops/                            # Ops scripts
│   └── [script_files]
│
├── test-results/                       # Test artifacts
│   ├── evidence/                       # Test evidence
│   │   ├── freeze-scenario/
│   │   ├── role-change-scenario/
│   │   └── yacht-demo-001/
│   └── receiving/                      # Receiving test results
│
├── test_artifacts/                     # Test output files
│   ├── inventory/                      # Inventory test artifacts
│   │   ├── actions_list_checks/
│   │   └── after_context_actions/
│   └── [other_test_artifacts]
│
├── [MODULE FILES]
├── action_surfacing.py                 # Surface available actions
├── action_gating.py                    # Action gating logic
├── action_registry.py                  # Alternative registry (legacy?)
├── action_response_schema.py           # Response schema definition
├── action_executor.py                  # Action execution wrapper
│
├── [EXTRACTION & ML MODULES]
├── microaction_service.py              # Microaction FastAPI service
├── microaction_extractor.py            # Extract microactions from text
├── microaction_config.py               # Microaction configuration
├── intent_parser.py                    # Parse user intent
├── entity_extraction_loader.py         # Load entity extraction models
├── gpt_extractor.py                    # GPT-based extraction
├── graphrag_population.py              # GraphRAG population
├── graphrag_query.py                   # GraphRAG queries
│
├── [MISC MODULES]
├── cold_start_ux.py                    # First-run UX
├── confidence_thresholds.py            # Confidence settings
├── correction_flows.py                 # Error correction workflows
├── domain_microactions.py              # Domain-specific microactions
├── email_resilience.py                 # Email resilience
├── framing_copy.py                     # UI copy & framing
├── module_a_action_detector.py         # Action detection
│
├── e2e_sandbox.py                      # E2E test sandbox
├── e2e_sandbox_runner.py               # E2E test runner
├── e2e_test_harness.py                 # E2E test harness
│
└── [DIRECTORIES FOR FUTURE EXPANSION]
```

---

## apps/web/ - Next.js Frontend

### Structure Overview

```
apps/web/
├── src/
│   ├── app/                            # Next.js App Router
│   │   ├── layout.tsx                  # Root layout
│   │   ├── page.tsx                    # Home page
│   │   ├── middleware.ts               # Auth middleware
│   │   │
│   │   ├── api/                        # API routes (proxy & integration)
│   │   │   ├── v1/
│   │   │   │   └── actions/
│   │   │   │       └── execute/        # POST /api/v1/actions/execute (proxy)
│   │   │   │           └── route.ts    # Proxy to Python API
│   │   │   │
│   │   │   ├── debug/
│   │   │   │   └── auth-dump/         # Auth debugging endpoint
│   │   │   │
│   │   │   ├── email/
│   │   │   │   └── search/            # Email search proxy
│   │   │   │
│   │   │   ├── integrations/
│   │   │   │   └── outlook/           # Outlook OAuth integration
│   │   │   │       ├── auth-url/
│   │   │   │       ├── callback/
│   │   │   │       ├── disconnect/
│   │   │   │       ├── status/
│   │   │   │       └── write/
│   │   │   │
│   │   │   ├── search/
│   │   │   │   └── fallback/          # Search fallback
│   │   │   │
│   │   │   └── whoami/                # User identity check
│   │   │
│   │   ├── auth/                       # Authentication pages
│   │   │   ├── callback/              # OAuth callback handler
│   │   │   │   ├── AuthCallbackClient.tsx
│   │   │   │   └── page.tsx
│   │   │   └── [auth_pages]
│   │   │
│   │   ├── app/                        # Main application pages
│   │   │   ├── page.tsx               # Dashboard/home
│   │   │   ├── ContextPanel.tsx       # Context navigation sidebar
│   │   │   ├── DeepLinkHandler.tsx    # Deep link routing
│   │   │   └── EmailOverlay.tsx       # Email integration panel
│   │   │
│   │   ├── email/                      # Email pages
│   │   │   ├── inbox/
│   │   │   │   └── page.tsx           # Email inbox
│   │   │   └── search/
│   │   │       └── page.tsx           # Email search page
│   │   │
│   │   ├── equipment/                  # Equipment pages
│   │   │   ├── [id]/
│   │   │   │   └── page.tsx           # Equipment detail
│   │   │   └── [index_pages]
│   │   │
│   │   ├── fault/                      # Fault pages
│   │   │   ├── [id]/
│   │   │   │   └── page.tsx           # Fault detail
│   │   │   └── [list_pages]
│   │   │
│   │   ├── work-order/                 # Work order pages
│   │   │   ├── [id]/
│   │   │   │   └── page.tsx           # Work order detail
│   │   │   └── [list_pages]
│   │   │
│   │   ├── part/                       # Part/inventory pages
│   │   │   ├── [id]/
│   │   │   │   └── page.tsx           # Part detail
│   │   │   └── [list_pages]
│   │   │
│   │   ├── document/                   # Document pages
│   │   │   ├── [id]/
│   │   │   │   └── page.tsx           # Document viewer
│   │   │   └── [list_pages]
│   │   │
│   │   ├── certificate/                # Certificate pages
│   │   │   ├── [id]/
│   │   │   │   └── page.tsx           # Certificate detail
│   │   │   └── [list_pages]
│   │   │
│   │   ├── crew/                       # Crew pages
│   │   │   ├── [id]/
│   │   │   │   └── page.tsx           # Crew profile
│   │   │   └── [list_pages]
│   │   │
│   │   ├── handover/                   # Handover pages
│   │   │   ├── [id]/
│   │   │   │   └── page.tsx           # Handover report
│   │   │   └── [list_pages]
│   │   │
│   │   ├── shopping-list/              # Shopping list pages
│   │   │   └── page.tsx               # Shopping list view
│   │   │
│   │   └── [other_domain_pages]
│   │
│   ├── components/                     # React components
│   │   ├── Header.tsx                 # Top navigation
│   │   ├── Sidebar.tsx                # Left sidebar navigation
│   │   ├── ActionBar.tsx              # Action buttons
│   │   ├── EntityDetail.tsx           # Generic entity detail view
│   │   ├── EntityList.tsx             # Generic entity list view
│   │   ├── SearchBox.tsx              # Search input
│   │   ├── ContextNav.tsx             # Context navigation
│   │   ├── modals/                    # Modal dialogs
│   │   │   ├── ActionModal.tsx        # Generic action modal
│   │   │   ├── CreateFaultModal.tsx
│   │   │   ├── CreateWorkOrderModal.tsx
│   │   │   ├── [other_modals]
│   │   │   └── [modal_components]
│   │   ├── forms/                     # Form components
│   │   │   ├── ActionForm.tsx         # Generic action form
│   │   │   ├── FaultForm.tsx
│   │   │   ├── EquipmentForm.tsx
│   │   │   ├── [other_forms]
│   │   │   └── [form_components]
│   │   ├── tables/                    # Table components
│   │   │   ├── EntityTable.tsx        # Generic table
│   │   │   ├── FaultTable.tsx
│   │   │   ├── WorkOrderTable.tsx
│   │   │   └── [table_components]
│   │   ├── cards/                     # Card components
│   │   │   ├── EntityCard.tsx         # Generic card
│   │   │   ├── EquipmentCard.tsx
│   │   │   └── [card_components]
│   │   ├── icons/                     # Icon components
│   │   ├── layout/                    # Layout components
│   │   ├── common/                    # Common utilities
│   │   └── [component_categories]
│   │
│   ├── hooks/                          # React hooks
│   │   ├── useAction.ts               # Execute action hook
│   │   ├── useAuth.ts                 # Auth context hook
│   │   ├── useFetch.ts                # Data fetching hook
│   │   ├── useEntity.ts               # Entity detail hook
│   │   ├── useList.ts                 # List/pagination hook
│   │   ├── useSearch.ts               # Search hook
│   │   ├── useContext.ts              # Context navigation hook
│   │   ├── useEmail.ts                # Email integration hook
│   │   └── [custom_hooks]
│   │
│   ├── contexts/                       # React Context providers
│   │   ├── AuthContext.tsx            # Auth/user context
│   │   ├── AppContext.tsx             # Global app state
│   │   ├── EntityContext.tsx          # Entity cache context
│   │   ├── SearchContext.tsx          # Search state
│   │   └── [context_providers]
│   │
│   ├── providers/                      # Context providers wrapper
│   │   ├── AuthProvider.tsx
│   │   ├── AppProvider.tsx
│   │   └── [provider_components]
│   │
│   ├── lib/                            # Utility functions
│   │   ├── api.ts                     # API client functions
│   │   ├── auth.ts                    # Auth utilities
│   │   ├── storage.ts                 # Local storage utilities
│   │   ├── formatting.ts              # Data formatting
│   │   ├── validation.ts              # Form validation
│   │   ├── constants.ts               # App constants
│   │   ├── types.ts                   # Type definitions
│   │   └── [utility_modules]
│   │
│   ├── types/                          # TypeScript type definitions
│   │   ├── index.ts                   # Main types export
│   │   ├── entities.ts                # Entity types
│   │   ├── api.ts                     # API types
│   │   ├── auth.ts                    # Auth types
│   │   └── [type_files]
│   │
│   ├── styles/                         # Global styles
│   │   ├── globals.css                # Global styles
│   │   ├── variables.css              # CSS variables
│   │   └── [style_files]
│   │
│   └── __tests__/                      # Component tests
│       ├── components/
│       ├── hooks/
│       ├── lib/
│       └── [test_files]
│
├── public/                             # Static assets
│   ├── images/                         # Images
│   ├── icons/                          # Icon assets
│   └── [static_files]
│
├── package.json                        # Web app dependencies
├── tsconfig.json                       # TypeScript config
├── next.config.js                      # Next.js configuration
└── tailwind.config.js                  # Tailwind CSS config
```

---

## database/ - Database Schema & Migrations

### Structure

```
database/
├── README.md                           # Database documentation
├── SECURITY_ARCHITECTURE.md            # RLS & security policies
│
├── master_migrations/                  # CURRENT MIGRATION SYSTEM
│   ├── 0001_initial_schema.sql        # Base tables
│   ├── 0002_rls_policies.sql          # RLS policy definitions
│   ├── 0003_equipment_schema.sql      # Equipment lens schema
│   ├── 0004_fault_schema.sql          # Fault lens schema
│   ├── 0005_work_order_schema.sql     # Work order lens schema
│   ├── [0006_...]                     # More lens schemas
│   ├── [0N_...]                       # Latest migrations
│   └── [migration_files]
│
├── migrations/                         # Legacy migrations (pre-master)
│   ├── [old_migration_files]
│   └── [deprecated]
│
├── setup_complete.sql                  # Initial setup script
├── setup_complete_FIXED.sql            # Setup script (fixed)
├── test_multi_yacht_rls.sql           # RLS testing
│
├── diagnostics/                        # Diagnostic scripts
│   └── [diagnostic_scripts]
```

**Key Files**:
- `master_migrations/` - Current active migration system
- `SECURITY_ARCHITECTURE.md` - RLS policies and tenant isolation
- Schema organized by lens (equipment, fault, work_order, etc.)

---

## docs/pipeline/entity_lenses/ - Lens Specifications

### Structure

```
docs/pipeline/entity_lenses/
├── CONTRACT_INTERFACES.md              # Cross-lens contract definitions
├── CROSS_LENS_ESCAPE_HATCH_MATRIX.md  # Inter-lens relationships
├── LENS_BUILDER_OPERATING_PROCEDURE.md # How to build lenses
├── LENS_FACTORY_PIPELINE.md           # Lens creation pipeline
│
├── [LENS_DIRECTORIES]
├── certificate_lens/
│   ├── v1/
│   │   └── certificate_lens_v1_FINAL.md
│   └── v2/
│       ├── certificate_lens_v2_FINAL.md
│       ├── certificate_lens_v2_PHASE_0_EXTRACTION_GATE.md
│       ├── certificate_lens_v2_PHASE_1_SCOPE.md
│       ├── certificate_lens_v2_PHASE_2_DB_TRUTH.md
│       ├── certificate_lens_v2_PHASE_3_ENTITY_GRAPH.md
│       ├── certificate_lens_v2_PHASE_4_ACTIONS.md
│       ├── certificate_lens_v2_PHASE_5_SCENARIOS.md
│       ├── certificate_lens_v2_PHASE_6_SQL_BACKEND.md
│       ├── certificate_lens_v2_PHASE_7_RLS_MATRIX.md
│       └── certificate_lens_v2_PHASE_8_GAPS_MIGRATIONS.md
│
├── crew_lens/
│   ├── v1/
│   │   └── crew_lens_v1_FINAL.md
│   └── v2/
│       ├── crew_lens_v2_PHASE_1_SCOPE.md
│       ├── crew_lens_v2_PHASE_2_DB_TRUTH.md
│       └── [phases_3+]
│
├── document_lens/
│   ├── v1/
│   │   └── document_lens_v1_FINAL.md
│   ├── v2/
│   │   ├── DOCUMENT_LENS_EXTRACTION.md
│   │   ├── document_lens_v2_FINAL.md
│   │   └── [phases]
│   └── [versions]
│
├── equipment_lens/
│   ├── v1/
│   │   └── equipment_lens_v1_FINAL.md
│   └── [versions]
│
├── fault_lens/
│   ├── v1/
│   │   └── fault_lens_v1_FINAL.md
│   ├── v3/
│   │   └── fault_lens_v3_ENHANCED.md
│   ├── v3.1/
│   │   └── fault_lens_v3.1_CORRECTED.md
│   ├── v3.2/
│   │   └── fault_lens_v3.2_FINAL.md
│   ├── v4/
│   │   └── fault_lens_v4_DB_GROUNDED.md
│   ├── v5/
│   │   └── fault_lens_v5_FINAL.md
│   └── [phases_for_latest]
│
├── inventory_item_lens/
│   ├── inventory_item_lens_v3_ENHANCED.md
│   ├── inventory_item_lens.md
│   └── [versions]
│
├── part_lens/
│   ├── v1/
│   │   └── part_lens_v1_FINAL.md
│   └── [versions]
│
├── receiving_lens/
│   ├── v1/
│   │   └── receiving_lens_v1_FINAL.md
│   └── [versions]
│
├── shopping_list_lens/
│   ├── v1/
│   │   └── shopping_list_lens_v1_FINAL.md
│   └── [versions]
│
├── work_order_lens/
│   ├── v1/
│   │   └── work_order_lens_v1_FINAL.md
│   └── [versions]
│
└── [OTHER_LENSES]
    ├── handover_lens/
    ├── warranty_lens/
    ├── situation_lens/
    ├── hours_of_rest_lens/
    └── [more_lenses]
```

### Lens Specification Phases

Each lens has 8 phases (when complete):

1. **PHASE_0_EXTRACTION_GATE** - What data to extract from emails/users
2. **PHASE_1_SCOPE** - Entity definition, states, transitions
3. **PHASE_2_DB_TRUTH** - Database schema, tables, constraints
4. **PHASE_3_ENTITY_GRAPH** - Relationships to other lenses
5. **PHASE_4_ACTIONS** - Available micro-actions (mutations)
6. **PHASE_5_SCENARIOS** - Test cases and user journeys
7. **PHASE_6_SQL_BACKEND** - SQL implementation, triggers
8. **PHASE_8_GAPS_MIGRATIONS** - Production deployment, backfill

---

## tests/ - Test Suite Organization

### Structure

```
tests/
├── acceptance/                         # Acceptance test suites
│   └── [acceptance_tests]
│
├── action_router/                      # Action router tests
│   ├── test_validation_pipeline.py
│   ├── test_handler_dispatch.py
│   └── [router_tests]
│
├── api/                                # API endpoint tests
│   ├── test_fault_api.py
│   ├── test_equipment_api.py
│   ├── test_work_order_api.py
│   ├── [entity_tests]
│   └── [endpoint_tests]
│
├── canonical_action_registry.py        # Action registry validator
│
├── ci/                                 # CI/CD test configuration
│   ├── [ci_test_files]
│   └── [github_actions_tests]
│
├── contracts/                          # Contract/interface tests
│   ├── test_action_contracts.py
│   ├── test_lens_interfaces.py
│   └── [contract_tests]
│
├── deployment/                         # Deployment verification tests
│   ├── test_production_deployment.py
│   └── [deployment_tests]
│
├── docker/                             # Docker container tests
│   └── [docker_tests]
│
├── e2e/                                # End-to-end tests
│   ├── test_email_to_fault_flow.py
│   ├── test_receiving_flow.py
│   ├── test_work_order_flow.py
│   └── [e2e_scenarios]
│
├── entity_extraction/                  # Entity extraction tests
│   └── [extraction_tests]
│
├── fixtures/                           # Test data fixtures
│   ├── yacht_data.json
│   ├── user_data.json
│   ├── entity_fixtures.py
│   └── [test_data]
│
├── helpers/                            # Test helper functions
│   ├── test_helpers.py
│   ├── auth_helpers.py
│   └── [helper_modules]
│
├── inventory_lens/                     # Inventory lens tests
│   ├── test_inventory_actions.py
│   └── [inventory_tests]
│
├── manual_audit_v2.py                  # Manual audit script
│
├── rag/                                # RAG system tests
│   └── [rag_tests]
│
├── receiving_test_env.sh               # Receiving test environment
│
├── search/                             # Search functionality tests
│   ├── test_search_api.py
│   ├── test_rag_search.py
│   └── [search_tests]
│
├── setup/                              # Test setup utilities
│   ├── setup_test_db.py
│   ├── setup_test_users.py
│   └── [setup_scripts]
│
├── smoke/                              # Smoke tests
│   ├── test_health_check.py
│   ├── test_basic_auth.py
│   └── [smoke_tests]
│
├── stress/                             # Load/stress tests
│   ├── stress_test_runner.py
│   ├── stress_test_pipeline.py
│   ├── stress_test_dataset.py
│   └── [stress_test_files]
│
└── scripts/                            # Test utility scripts
    └── [test_scripts]
```

---

## Key File Locations by Purpose

### Action Management

| Purpose | File Path |
|---------|-----------|
| Action registry (source of truth) | `/apps/api/action_router/registry.py` |
| Action router endpoint | `/apps/api/action_router/router.py` |
| Handler dispatcher | `/apps/api/action_router/dispatchers/internal_dispatcher.py` |
| Validation pipeline | `/apps/api/action_router/middleware/validation_middleware.py` |
| Micro-action registry | `/apps/api/microactions/microaction_registry.py` |

### Authentication & Security

| Purpose | File Path |
|---------|-----------|
| JWT validation | `/apps/api/action_router/validators/jwt_validator.py` |
| RLS enforcement | `/apps/api/action_router/validators/rls_entity_validator.py` |
| Role-based access control | `/apps/api/action_router/validators/role_validator.py` |
| Auth middleware | `/apps/api/middleware/auth.py` |
| Supabase security | `/database/SECURITY_ARCHITECTURE.md` |

### Domain Handlers

| Domain | Primary Handler | Secondary Handlers |
|--------|-----------------|-------------------|
| Equipment | `/apps/api/handlers/equipment_handlers.py` | `equipment_utils.py` |
| Fault | `fault_handlers.py` | `fault_mutation_handlers.py` |
| Work Order | `work_order_handlers.py` | `work_order_mutation_handlers.py` |
| Part/Inventory | `part_handlers.py` | - |
| Receiving | `receiving_handlers.py` | - |
| Shopping List | `shopping_list_handlers.py` | - |
| Certificate | `certificate_handlers.py` | - |
| Document | `document_handlers.py` | `document_comment_handlers.py`, `secure_document_handlers.py` |
| Hours of Rest | `hours_of_rest_handlers.py` | - |
| Handover | `handover_handlers.py` | `handover_workflow_handlers.py` |
| Warranty | `warranty_handlers.py` | - |
| Situation | `situation_handlers.py` | - |
| Crew | `crew_handlers.py` | - |

### Frontend Pages by Domain

| Domain | Page Location |
|--------|--------------|
| Equipment | `/apps/web/src/app/equipment/[id]/page.tsx` |
| Fault | `/apps/web/src/app/fault/[id]/page.tsx` |
| Work Order | `/apps/web/src/app/work-order/[id]/page.tsx` |
| Part | `/apps/web/src/app/part/[id]/page.tsx` |
| Certificate | `/apps/web/src/app/certificate/[id]/page.tsx` |
| Document | `/apps/web/src/app/document/[id]/page.tsx` |
| Crew | `/apps/web/src/app/crew/[id]/page.tsx` |
| Email | `/apps/web/src/app/email/inbox/page.tsx` |

### Database & Configuration

| Purpose | File Path |
|---------|-----------|
| Database migrations | `/database/master_migrations/` |
| RLS policies | `/database/SECURITY_ARCHITECTURE.md` |
| Configuration | `/apps/api/config/env.py` |
| Supabase config | `/supabase/` |
| Environment variables | `.env.local` |

### Documentation

| Purpose | File Path |
|---------|-----------|
| Architecture | `.planning/codebase/ARCHITECTURE.md` |
| Directory structure | `.planning/codebase/STRUCTURE.md` |
| Lens specifications | `/docs/pipeline/entity_lenses/[lens_name]/` |
| Security | `/database/SECURITY_ARCHITECTURE.md` |

---

## File Size Distribution

### Largest API Files

| File | Lines | Purpose |
|------|-------|---------|
| `/apps/api/routes/p0_actions_routes.py` | 290KB | Main actions endpoint |
| `/apps/api/routes/email.py` | 173KB | Email integration |
| `/apps/api/handlers/equipment_handlers.py` | ~87KB | Equipment operations |
| `/apps/api/handlers/p2_mutation_light_handlers.py` | ~87KB | Light mutations |
| `/apps/api/handlers/receiving_handlers.py` | ~60KB | Receiving operations |
| `/apps/api/handlers/work_order_mutation_handlers.py` | ~73KB | Work order mutations |
| `/apps/api/handlers/fault_handlers.py` | ~25KB | Fault reads |
| `/apps/api/handlers/fault_mutation_handlers.py` | ~72KB | Fault mutations |

### Test Files

- `tests/stress/stress_test_runner.py` - Stress testing
- `tests/e2e/` - End-to-end test scenarios
- `tests/action_router/` - Router validation tests

---

## Summary: Key Directory Insights

1. **Monorepo Structure**: All apps in `/apps/` (web, api, test-automation)
2. **Action-Centric Design**: Action Router in `/apps/api/action_router/` is the primary entry point
3. **Domain-Driven Handlers**: Handlers organized by lens domain in `/apps/api/handlers/`
4. **Lens-Based Architecture**: 16 entity lenses with specifications in `/docs/pipeline/entity_lenses/`
5. **Comprehensive Tests**: Multi-tiered testing in `/tests/` (unit, integration, e2e, stress)
6. **Database Schema**: Organized migrations in `/database/master_migrations/` with RLS in place
7. **Frontend Integration**: Next.js app with API routes that proxy to Python backend
8. **Planning Documents**: Architecture and codebase docs in `.planning/codebase/`

---

## Quick Reference: Finding Things

```
# Need to find an action definition?
→ /apps/api/action_router/registry.py

# Need to understand a domain handler?
→ /apps/api/handlers/[domain]_handlers.py

# Need lens specification?
→ /docs/pipeline/entity_lenses/[lens_name]/

# Need to check RLS policies?
→ /database/SECURITY_ARCHITECTURE.md

# Need to run tests?
→ /tests/[test_category]/

# Need frontend code?
→ /apps/web/src/

# Need migrations?
→ /database/master_migrations/
```
