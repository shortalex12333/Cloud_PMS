# PROJECT TREE - CelesteOS Cloud PMS

**Generated:** 2026-01-22

This document maps the key files and their purposes for incoming engineers.

---

## ROOT DOCUMENTATION FILES

| File | Purpose | Status |
|------|---------|--------|
| `ENGINEER_HANDOVER.md` | Main handover document for next engineer | NEW |
| `KNOWN_ISSUES.md` | Catalog of recurring issues and solutions | NEW |
| `TEST_COVERAGE_REPORT.md` | What's tested vs not tested | NEW |
| `PROJECT_TREE.md` | This file - project structure map | NEW |
| `BOTTLENECK_ANALYSIS.md` | System health tracking (95%) | UPDATED |
| `SYSTEMATIC_FIX_PLAN.md` | Phased fix plan (completed) | COMPLETE |

---

## BACKEND (`apps/api/`)

### Core Routes
```
apps/api/routes/
├── p0_actions_routes.py      # 81 microaction handlers (4,160 lines) ⭐ KEY FILE
├── auth_routes.py            # Login, token refresh
├── orchestrated_search_routes.py  # /search endpoint
├── context_navigation_routes.py   # Back/forward navigation
├── email.py                  # Email watcher integration
├── triggers_routes.py        # Trigger management
└── decisions_routes.py       # Decision audit
```

### Services
```
apps/api/
├── pipeline_service.py       # Main /search pipeline ⭐ KEY FILE
├── microaction_service.py    # Microaction execution (unused in prod)
├── intent_parser.py          # Intent classification
├── gpt_extractor.py          # Entity extraction
├── graphrag_query.py         # Graph-based retrieval
└── situation_engine.py       # Situation assessment
```

### Handlers (Modular)
```
apps/api/handlers/
├── fault_handlers.py         # Fault-specific logic
├── work_order_handlers.py    # WO operations
├── equipment_handlers.py     # Equipment queries
├── inventory_handlers.py     # Parts/stock
├── handover_handlers.py      # Handover generation
├── manual_handlers.py        # Manual/document lookup
├── p1_compliance_handlers.py # Hours of rest, surveys
├── p1_purchasing_handlers.py # Purchase requests
└── ...
```

### Action Router (Validation Layer)
```
apps/api/action_router/
├── router.py                 # Main action router
├── registry.py               # Action registration
├── dispatchers/
│   ├── internal_dispatcher.py
│   └── n8n_dispatcher.py
└── validators/
    ├── jwt_validator.py
    ├── role_validator.py
    ├── yacht_validator.py
    └── schema_validator.py
```

### Middleware
```
apps/api/middleware/
└── auth.py                   # JWT validation, user context
```

### Integrations
```
apps/api/integrations/
├── supabase.py               # Database client
├── graph_client.py           # Graph database
├── search_engine.py          # Search functionality
└── predictive_engine.py      # ML predictions
```

---

## FRONTEND (`apps/web/`)

### Chat Components
```
apps/web/src/components/chat/
├── ChatInterface.tsx         # Main chat UI
├── MessageList.tsx           # Message display
├── InputBar.tsx              # User input
├── ActionButton.tsx          # Microaction buttons
└── CardRenderer.tsx          # Entity cards
```

### Pages
```
apps/web/src/app/
├── (dashboard)/
│   ├── chat/                 # Main chat interface
│   ├── faults/               # Fault management
│   ├── work-orders/          # Work order management
│   ├── equipment/            # Equipment browser
│   ├── inventory/            # Parts inventory
│   └── handover/             # Handover generation
└── api/                      # API routes (Next.js)
```

---

## TESTS (`tests/`)

### E2E Tests (Playwright)
```
tests/e2e/
├── diagnostic_baseline.spec.ts      # Direct action execution (64 tests) ⭐
├── nl_to_action_mapping.spec.ts     # NL→Action flow (64 tests) ⭐
├── chat_to_action.spec.ts           # Full chat E2E (21 tests) ⭐
├── phase13_mutation_proof.spec.ts   # DB mutation proof (1 test)
├── auth.spec.ts                     # Authentication tests
├── search.spec.ts                   # Search functionality
│
├── microactions/                    # Cluster-specific tests
│   ├── cluster_01_fix_something.spec.ts
│   ├── cluster_02_do_maintenance.spec.ts
│   ├── cluster_03_equipment.spec.ts
│   ├── cluster_04_inventory.spec.ts
│   ├── cluster_05_handover.spec.ts
│   ├── cluster_06_compliance.spec.ts
│   ├── cluster_07_documents.spec.ts
│   ├── cluster_08_purchasing.spec.ts
│   └── ...
│
└── user-flows/                      # User journey tests
    ├── fault-lifecycle.spec.ts
    ├── work-order-lifecycle.spec.ts
    ├── handover-flow.spec.ts
    └── inventory-flow.spec.ts
```

### Test Helpers
```
tests/helpers/
├── test-data-discovery.ts    # Auto-discovers entity IDs ⭐
├── api-client.ts             # HTTP client with auth
├── auth.ts                   # Auth token management
├── global-setup.ts           # Test setup
├── global-teardown.ts        # Test cleanup
├── master-db-setup.ts        # Master DB initialization
├── supabase_master.ts        # Master DB client
└── supabase_tenant.ts        # Tenant DB client
```

### Test Fixtures
```
tests/fixtures/
├── microaction_registry.ts   # All 64 actions with metadata ⭐
└── test_users.ts             # Test user credentials
```

### Contract Tests
```
tests/contracts/
├── jwt_verification_priority.test.ts
├── master_bootstrap.test.ts
├── tenant_has_docs.test.ts
└── rls-proof/
    ├── email-isolation.test.ts
    └── yacht-isolation.test.ts
```

### Entity Extraction Tests
```
tests/entity_extraction/
├── test_entity_extraction.py
├── test_intent_parser.py
├── extraction_validator.py
├── ground_truth.py
└── TESTING_METHODOLOGY.md
```

---

## DOCUMENTATION (`docs/`, `adr/`, numbered folders)

### Architecture Decision Records
```
adr/
├── ADR-001-no-vector-no-llm.md
├── ADR-002-domain-first-grouping.md
├── ADR-003-linear-back-forward-stack.md
└── ADR-004-user_added_relations_active_flagged.md
```

### Foundation Docs
```
00_foundation/
├── 00_README.md
├── 01_INVARIANTS.md
└── 02_ABORT_CRITERIA.md
```

### Data Model Docs
```
20_model/
├── 20_SITUATION_OBJECT.md
├── 21_VIEW_STATE_MACHINE.md
└── 22_ANCHOR_TYPES.md
```

### Contract Docs
```
30_contracts/
├── 30_DATABASE_SCHEMA_ASSUMPTIONS.md
├── 31_BACKEND_API_CONTRACT.md
├── 32_FRONTEND_STATE_CONTRACT.md
├── 33_DOMAIN_GROUPING_ORDER.md
└── 34_ADD_RELATED_RULES.md
```

### Validation Docs
```
80_validation/
├── 80_DONE_DEFINITION.md
├── 81_ACCEPTANCE_TESTS.md
└── 82_REGRESSION_TRAPS.md
```

---

## DATABASE TABLES (Supabase)

### Master DB
```
fleet_registry         # Yacht registration
user_accounts          # User profiles and permissions
audit_logs             # Action audit trail
```

### Tenant DB
```
pms_faults             # Fault reports
pms_work_orders        # Maintenance work orders
pms_equipment          # Equipment inventory
pms_parts              # Spare parts
pms_checklists         # Operational checklists
pms_checklist_items    # Checklist line items
documents              # Manuals, certifications
handovers              # Handover reports
hours_of_rest          # Compliance tracking
purchase_requests      # Procurement
worklist_items         # Shipyard worklist
```

---

## KEY FILE SIZES

| File | Lines | Purpose |
|------|-------|---------|
| `p0_actions_routes.py` | 4,160 | All 81 action handlers |
| `microaction_registry.ts` | 1,450 | Action definitions |
| `pipeline_service.py` | ~800 | Search pipeline |
| `nl_to_action_mapping.spec.ts` | 800 | NL test cases |
| `diagnostic_baseline.spec.ts` | 500 | Direct action tests |
| `test-data-discovery.ts` | 360 | Test data finder |

---

## QUICK NAVIGATION

**To understand the system:**
1. Start with `ENGINEER_HANDOVER.md`
2. Read `tests/fixtures/microaction_registry.ts` for action definitions
3. Review `apps/api/routes/p0_actions_routes.py` for handler implementations

**To run tests:**
1. Check `tests/helpers/` for setup
2. Run `diagnostic_baseline.spec.ts` for health check
3. Run `nl_to_action_mapping.spec.ts` for NL coverage

**To debug issues:**
1. Check `KNOWN_ISSUES.md` for common problems
2. Verify column names in handler match actual schema
3. Check `test-data-discovery.ts` for entity ID resolution

---

*Generated: 2026-01-22*
