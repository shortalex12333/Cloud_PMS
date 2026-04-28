# Cloud PMS — Codebase Map

Use this to task an agent precisely. Every file has one job. Find the job, task that file.

Last updated: 2026-04-28

---

## HOW TO USE

Bug in button placement → find the component in `apps/web/src/components/`
Bug in action logic → find the handler in `apps/api/handlers/`
Bug in what actions are visible → `action_router/entity_actions.py`
Bug in API routing → `apps/api/routes/`
Bug in data shape between API and UI → `apps/web/src/lib/apiClient.ts` + the handler

---

## BACKEND — `apps/api/`

### Entry Points

| File | Job |
|---|---|
| `pipeline_service.py` | Main FastAPI app — all routes mounted here, rate limiting, health checks |
| `combined_service.py` | Subprocess supervisor — runs FastAPI + 5 background workers as one Render process |

---

### `routes/` — HTTP endpoints only. No business logic.

| File | Job |
|---|---|
| `p0_actions_routes.py` | `POST /v1/actions/execute` — the single action dispatch endpoint; `/prefill` |
| `entity_routes.py` | `GET /v1/entity/{type}/{id}` — entity detail lens data (12 types + handover) |
| `vessel_surface_routes.py` | Vessel/dashboard overview data |
| `document_routes.py` | Document CRUD and search |
| `part_routes.py` | Part/equipment management |
| `hours_of_rest_routes.py` | Hours of rest logging and compliance |
| `handover_export_routes.py` | Handover export and PDF generation |
| `import_routes.py` | File import pipeline (dry-run, commit, validate) |
| `ledger_routes.py` | Audit ledger query and export |
| `notification_routes.py` | Notification management |
| `related_routes.py` | Legacy related entity discovery |
| `related_signal_routes.py` | Signal-based related entity discovery |
| `context_navigation_routes.py` | `GET /v1/context-navigation/{type}/{id}` FK-based related expansion |
| `attachment_upload.py` | File upload proxy to TENANT Supabase storage |
| `receiving_upload.py` | Receiving item upload |
| `receiving_label_routes.py` | Barcode label generation for received goods |
| `purchase_order_pdf_route.py` | Purchase order PDF generation |
| `shopping_list_pdf_route.py` | Shopping list PDF generation |
| `email.py` | Email integration orchestration |
| `email_inbox_routes.py` | Email inbox sync and listing |
| `email_thread_routes.py` | Email thread grouping and retrieval |
| `email_link_routes.py` | Email-to-entity linking |
| `email_sync_routes.py` | Email sync orchestration |
| `auth_routes.py` | OAuth token exchange for Microsoft Graph |
| `attention_routes.py` | Needs-attention priority management |
| `decisions_routes.py` | Decision history and audit |
| `orchestrated_search_routes.py` | High-level orchestrated search |
| `search_streaming.py` | Legacy SSE search streaming (deprecated) |
| `f1_search_streaming.py` | `GET /api/f1/search/stream` — SSE streaming search with RRF scoring |
| `rag_endpoint.py` | RAG question-answering |

#### `routes/handlers/` — dispatch table (not HTTP code)

| File | Job |
|---|---|
| `__init__.py` | Merges all domain HANDLERS dicts into one master lookup table |
| `internal_adapter.py` | Shim bridging legacy INTERNAL_HANDLERS to Phase 4 calling convention — serves docs + parts until those domains are rewritten |

---

### `handlers/` — All business logic. One file per domain.

| File | Job |
|---|---|
| `warranty_handlers.py` | Warranty claim lifecycle (draft, file, compose email, notes, audit) |
| `work_order_handlers.py` | Work order lifecycle (create, update, close, assign, status transitions) |
| `purchase_order_handlers.py` | Purchase order creation and tracking |
| `equipment_handler.py` | Equipment management and status tracking |
| `equipment_utils.py` | Equipment utility functions (calculations, lookups) |
| `fault_handler.py` | Fault/issue management |
| `certificate_handlers.py` | Vessel certificate management |
| `handover_handlers.py` | Handover workflow state machine and export |
| `hours_of_rest_handlers.py` | Hours of rest compliance and tracking |
| `inventory_handlers.py` | Inventory/parts management |
| `part_handlers.py` | Part lifecycle (create, update, inventory) |
| `document_handler.py` | Document lifecycle (create, update, metadata) |
| `document_comment_handlers.py` | Document comment CRUD |
| `attachment_comment_handlers.py` | Attachment comment CRUD |
| `shopping_list_handlers.py` | Shopping list CRUD and item management |
| `receiving_handlers.py` | Goods receiving and acceptance |
| `list_handlers.py` | Generic list query handlers |
| `entity_lens_handlers.py` | Entity detail view (all entity types, single responsibility) |
| `context_navigation_handlers.py` | Related entity discovery |
| `related_handlers.py` | Legacy related entity discovery (superseded by context_nav) |
| `related_signal_handlers.py` | Signal-based related entity discovery |
| `email_handlers.py` | Email integration and thread management |
| `manual_handlers.py` | Manual task and procedure handlers |
| `media_handlers.py` | Media/image attachment handlers |
| `delivery_compliance_handlers.py` | P1 compliance — delivery/receiving workflows |
| `shared_mutation_handlers.py` | Generic mutation handlers (notes, updates) |
| `shared_read_handlers.py` | Generic read-only handlers (views, lists) |
| `compliance_handler.py` | Compliance status and audit logic |
| `pm_handler.py` | Preventive maintenance |
| `universal_handlers.py` | Cross-domain handlers (soft delete, archive) |
| `stub_handlers.py` | Placeholder stubs for not-yet-implemented actions |
| `ledger_utils.py` | Ledger event building and writing utilities |
| `schema_mapping.py` | Maps entity types to database tables |
| `db_client.py` | Per-request RLS-enforced database client factory |
| `__init__.py` | Handler class exports and factories |

---

### `action_router/` — Action discovery and routing (no HTTP, no DB writes)

| File | Job |
|---|---|
| `entity_actions.py` | Discovers available actions for an entity by type + state + user role (pure logic, no DB) |
| `registry.py` | Single source of truth — all action definitions, schemas, permissions, variants |
| `entity_prefill.py` | Static map: entity type + action → form field dot-paths for pre-populating forms |
| `ledger_metadata.py` | Maps action names to ledger event types for audit trail |
| `logger.py` | Logs all action executions to Supabase for analytics |

#### `action_router/dispatchers/` — thin param-unpack wrappers

| File | Job |
|---|---|
| `index.py` | INTERNAL_HANDLERS legacy adapter shim — blocked pending docs + parts Phase 4 rewrite |
| `document.py` | Document action dispatchers |
| `parts.py` | Parts action dispatchers |
| `p3.py` | P3 read-only action dispatchers |
| `shared.py` | Shared dispatcher utilities |

---

### `middleware/` — Request processing. Applied before handlers.

| File | Job |
|---|---|
| `auth.py` | JWT validation, tenant lookup, yacht context injection, RBAC |
| `action_security.py` | `@secure_action` decorator — ownership validation, idempotency, yacht freeze checks |
| `action_gating.py` | Execution class rules — which actions are AUTO / SUGGEST / CONFIRM |
| `handover_gating.py` | Role matrix for add-to-handover visibility per entity type |
| `state_machine.py` | Validates state transitions (shopping lists, stateful entities) |
| `validation_middleware.py` | Input validation utils (UUID, string length, quantity) |
| `vessel_access.py` | Multi-vessel access validation for fleet users |
| `rate_limit.py` | Redis token-bucket rate limiting (org-level, HTTP middleware) |

---

### `validators/` — Input and entity validation.

| File | Job |
|---|---|
| `jwt_validator.py` | JWT token validation and user context extraction |
| `yacht_validator.py` | Yacht/vessel access and isolation validation |
| `role_validator.py` | User role permission validation |
| `rls_entity_validator.py` | RLS entity access — prevents cross-yacht data leakage |
| `field_validator.py` | Individual field value validation |
| `schema_validator.py` | Payload validation against action schemas |
| `ownership.py` | Entity ownership check against user's yacht |
| `validation_result.py` | ValidationResult / ValidationError dataclasses |

---

### `schemas/` — Response type definitions.

| File | Job |
|---|---|
| `action_response_schema.py` | Universal response envelope — ResponseBuilder, ActionResponseEnvelope, AvailableAction, SignedUrlGenerator |

---

### `services/` — High-level business features.

| File | Job |
|---|---|
| `import_service.py` | Core import logic (row transform, dry-run, commit, rollback) |
| `hyper_search.py` | f1_search_cards RPC wrapper + signal connection pool |
| `decision_engine.py` | Converts E017/E019 policy specs into action decisions with confidence tiers |
| `decision_audit_service.py` | Audits and logs action decisions |
| `action_surfacing.py` | Surfaces recommended actions to UI based on entity state |
| `candidate_finder.py` | Finds candidate entities for suggestions |
| `entity_serializer.py` | Converts entity data to text for embedding |
| `entity_serializer_sync.py` | Synchronous entity serializer |
| `scoring_engine.py` | Scores and ranks entities by relevance |
| `handover_export_service.py` | Exports handover to PDF/HTML with ledger sealing |
| `handover_html_parser.py` | Parses handover HTML for submission |
| `handover_microservice_client.py` | RPC client for handover microservice |
| `file_reference_resolver.py` | Resolves file references in import data to paths |
| `intent_parser.py` | Parses user intent from search queries |
| `linking_ladder.py` | Entity linking and relationship inference |
| `cache.py` | Caching service |
| `rate_limit.py` | Async token-bucket rate limiter for streaming endpoints (in-memory, per-user) — different from middleware/rate_limit.py |
| `domain_microactions.py` | Domain-specific micro-action implementations |
| `types.py` | Shared type definitions for services |
| `email_sync_service.py` | Synchronises emails from Microsoft Graph |
| `email_search_service.py` | Full-text and semantic search over email |
| `email_link_service.py` | Links emails to entities via content analysis |
| `email_suggestion_service.py` | Generates action suggestions from email content |
| `email_embedding_service.py` | Generates email embeddings |
| `email_graph_helpers.py` | Microsoft Graph API helpers |
| `embedding_shadow_logger.py` | Logs embedding requests for monitoring |
| `ms_graph_rate_limiter.py` | Rate limiter for Microsoft Graph API |
| `token_extractor.py` | Token extraction for search |
| `status_mapper.py` | Legacy status value mapping (deprecated — see mappers/) |

---

### `workers/` — Background async jobs.

| File | Job |
|---|---|
| `projection_worker.py` | F1 Search projection — chunks, embeddings, Hard Tiers |
| `embedding_worker_1536.py` | Generates 1536-dim embeddings for search_index rows |
| `extraction_worker.py` | Downloads documents, extracts text for search indexing |
| `email_watcher_worker.py` | Monitors and processes email changes |
| `nightly_certificate_expiry.py` | Nightly job: check certificate expiration dates |
| `nightly_feedback_loop.py` | Nightly job: extraction quality feedback |
| `healthcheck.py` | Worker readiness health check |
| `shutdown.py` | Graceful shutdown handler |
| `extraction/extractor.py` | Text extraction logic (PDF, images) |

---

### `evidence/` — Production code (not test artifacts)

| File | Job |
|---|---|
| `sealing.py` | PDF/A-3 + PAdES-B-LT sealing with RFC 3161 timestamp — used by ledger exports |
| `fonts/` | Font files for PDF generation |
| `icc/` | ICC color profile for PDF generation |

---

### `extraction/` — 5-stage entity extraction pipeline.

| File | Job |
|---|---|
| `orchestrator.py` | Coordinates the 5 stages: clean → regex → coverage → AI → merge |
| `text_cleaner.py` | Stage 0: normalise whitespace, encoding |
| `regex_extractor.py` | Stage 1: regex-based extraction using bundled patterns |
| `coverage_controller.py` | Stage 2: decides whether AI extraction is needed |
| `ai_extractor_openai.py` | Stage 3: OpenAI fallback for low-coverage scenarios |
| `entity_merger.py` | Stage 4: merges regex + AI results with conflict resolution |
| `action_detector.py` | Detects action phrases and verbs in text |
| `text_normalizer.py` | Normalises extracted values to canonical forms |
| `entity_extractor.py` | High-level delegation wrapper |
| `gpt_extractor.py` | Legacy GPT extraction (superseded) |
| `extraction_config.py` | Pipeline configuration parameters |

---

### `orchestration/` — Search query planning and execution.

| File | Job |
|---|---|
| `search_orchestrator.py` | intent → classification → RetrievalPlan |
| `prepare_module.py` | Builds RetrievalPlan from extracted entities |
| `executor.py` | Executes query plans |
| `ranking_recipes.py` | RRF and result ranking recipe definitions |
| `retrieval_plan.py` | RetrievalPlan data model |
| `term_classifier.py` | Classifies extracted terms into search dimensions |
| `surface_state.py` | Surface context state during search |
| `email_retrieval.py` | Email retrieval and sync orchestration |

---

### `config/` — Configuration files.

| File | Job |
|---|---|
| `env.py` | Typed env config with secure deny-by-default |
| `E017_TRIGGER_CONTRACTS.yaml` | Trigger contracts — action condition specs |
| `E019_STATE_GUARDS.yaml` | State guard rules — mutual exclusion / state machine |
| `projection.yaml` | F1 Search projection worker config |

---

### `integrations/`

| File | Job |
|---|---|
| `supabase.py` | Supabase client factory — MASTER/TENANT routing + RLS enforcement |
| `graph_client.py` | Microsoft Graph API client |
| `feature_flags.py` | Feature flag management |

---

### `utils/`

| File | Job |
|---|---|
| `errors.py` | Shared error classes |
| `cache_keys.py` | Cache key generation |
| `filenames.py` | Filename sanitisation |

---

### `entity_extraction_loader.py` / `regex_production_data.py`

| File | Job |
|---|---|
| `entity_extraction_loader.py` | Loads 1,955 bundled regex patterns for entity extraction |
| `regex_production_data.py` | Pattern library (1,330 equipment + 485 diagnostic patterns) |

---

### `cache/`

| File | Job |
|---|---|
| `invalidation_listener.py` | Listens to pg_notify and evicts Redis keys for F1 search cache |

---

### `parsers/`

| File | Job |
|---|---|
| `base_parser.py` | Base types and file reference detection |
| `csv_parser.py` | CSV file parser with schema detection |
| `xlsx_parser.py` | Excel/XLSX parser with sheet detection |
| `sql_parser.py` | SQL import parser |
| `zip_handler.py` | Zip archive handler for batch imports |

---

### `mappers/`

| File | Job |
|---|---|
| `column_matcher.py` | Matches import columns to DB schema fields |
| `date_normalizer.py` | Normalises date values across formats |
| `source_profiles.py` | Source-specific column mapping profiles |
| `status_mapper.py` | Maps source statuses to canonical CelesteOS statuses |

---

### `lib/`

| File | Job |
|---|---|
| `entity_helpers.py` | Entity operation helpers |
| `user_resolver.py` | Resolves user UUIDs to display names for audit trail |

---

### `context_nav/`

| File | Job |
|---|---|
| `related_expansion.py` | Deterministic FK/JOIN-based related entity expansion (no LLMs) |
| `schemas.py` | Context navigation data models |

---

### `cortex/`

| File | Job |
|---|---|
| `rewrites.py` | Tenant-aware query rewrites for hybrid search (150ms budget, 3-rewrite limit) |

---

### `rag/`

| File | Job |
|---|---|
| `answer_generator.py` | Generates answers using retrieved context + LLM |
| `context_builder.py` | Retrieves top-K docs via f1_search_fusion for answer context |
| `normalizer.py` | Normalises RAG results and metadata |
| `verifier.py` | Verifies answer quality and citation accuracy |

---

### `execute/`

| File | Job |
|---|---|
| `capability_executor.py` | Executes RPC capabilities and DB queries |
| `capability_observability.py` | Observability hooks for capability execution |
| `result_normalizer.py` | Normalises capability results to consistent schema |
| `result_ranker.py` | Ranks and scores query results |
| `table_capabilities.py` | Capability definitions for table queries |

---

### `prepare/`

| File | Job |
|---|---|
| `capability_composer.py` | Multi-entity parallel capability dispatch and result merging |

---

### `rankers/`

| File | Job |
|---|---|
| `onnx_reranker.py` | ONNX-based semantic reranking for search results |

---

### `email_rag/`

| File | Job |
|---|---|
| `embedder.py` | Email embedding service |
| `entity_extractor.py` | Regex entity extraction for email queries |
| `micro_actions.py` | Micro-actions triggered by email content |
| `query_parser.py` | Parses email query text to structured intent |
| `triggers.py` | Event triggers for email-driven actions |

---

## FRONTEND — `apps/web/src/`

### Entry + Styles

| File | Job |
|---|---|
| `middleware.ts` | Domain routing — app.celeste7.ai/auth.celeste7.ai redirects, CORS, deprecated redirects |
| `styles/globals.css` | Global styles, typography, base element resets |
| `styles/tokens.css` | Design tokens — shell dimensions, colours, spacing, shadows, theme vars |
| `styles/lens.css` | Scoped styles for entity detail lens and modal dialogs |
| `styles/spotlight.css` | Styles for command palette / spotlight overlay |

---

### `contexts/` — React state shared across the tree

| File | Job |
|---|---|
| `AuthContext.tsx` | User session, bootstrap status, yacht context, fleet vessels |
| `VesselContext.tsx` | Active vessel ID + switchable dropdown for fleet managers |
| `EntityLensContext.tsx` | Entity data, available actions, action execution callback for a lens page |
| `BackdropContext.tsx` | Ambient orb pulse animation triggers on successful saves |

---

### `providers/`

| File | Job |
|---|---|
| `QueryProvider.tsx` | React Query client — data fetching, caching, sync config |
| `MicroactionsProvider.tsx` | Registers all action handlers on mount |

---

### `hooks/` — Data fetching and state

| File | Job |
|---|---|
| `useAuth.ts` | Access auth context (user, session, login, logout, bootstrapping) |
| `useActiveVessel.ts` | Access active vessel + fleet list |
| `useEntityLens.ts` | Fetch entity detail + available actions + execute action |
| `useActionHandler.ts` | Execute actions with loading / error / confirmation handling |
| `useCelesteSearch.ts` | Spotlight/search with debouncing and result fetching |
| `useEntityLedger.ts` | Fetch entity transaction/ledger history |
| `useNeedsAttention.ts` | Fetch entities needing user attention |
| `useRelated.ts` | Fetch related entities for graph navigation |
| `useRelatedDrawer.ts` | Open/close state of the related entities drawer |
| `useSignalRelated.ts` | Broadcast entity relationship changes to trigger refetches |
| `useEmailData.ts` | Fetch email inbox, threads, messages |
| `useReadBeacon.ts` | Track entity detail page views for read status |

---

### `lib/` — Utilities and client-side business logic

| File | Job |
|---|---|
| `utils.ts` | `cn`, `formatDate`, `debounce`, `truncate`, `formatRelativeTime` |
| `apiClient.ts` | Secure API wrapper — JWT/yacht signature headers, auto token refresh, 401 retry |
| `actionClient.ts` | Backend action execution client with auth |
| `authHelpers.ts` | `getAuthHeaders`, `handle401`, `getYachtId`, `getYachtSignature`, AuthError |
| `tokenRefresh.ts` | JWT token refresh and expiration management |
| `apiBase.ts` | Base API URL and env var management |
| `supabaseClient.ts` | Supabase client init |
| `field-schema.ts` | Canonical form field schema — PREFILL_NEVER_RENDER, PREFILL_MONO_KEYS, FORM_BACKEND_AUTO |
| `entityRoutes.ts` | Entity type → URL mapping and route builder |
| `documentLoader.ts` | Document fetch and tree construction loader |
| `documentTypes.ts` | Document type definitions and metadata |
| `normalizeWarranty.ts` | Warranty entity normalisation and calculation helpers |
| `spotlightGrouping.ts` | Search result grouping for spotlight |
| `handoverExportClient.ts` | Client for handover export API (acknowledge, countersign, submit) |
| `domain/catalog.ts` | Entity type metadata and relationships |
| `domain/context.tsx` | Domain context provider and hooks |
| `domain/hooks.ts` | Domain hook helpers |
| `attention/types.ts` | Needs-attention / urgency scoring types |
| `attention/scoring.ts` | Scoring logic for which entities need attention |
| `email/oauth-utils.ts` | Outlook/O365 OAuth utilities |
| `filters/catalog.ts` | Filter type definitions |
| `filters/infer.ts` | Filter inference from entity values |
| `filters/execute.ts` | Filter execution/matching logic |
| `filters/mapLegacyFilter.ts` | Migration helpers for legacy filter formats |
| `actions/index.ts` | Action system public API |
| `actions/types.ts` | Action type definitions |
| `actions/registry.ts` | Complete registry of all microactions organised by cluster |
| `actions/executor.ts` | Microaction executor — routes to handler, manages confirmation |
| `actions/handlers/index.ts` | Handler registration aggregator |
| `actions/handlers/inventory.ts` | Inventory/parts action handlers |
| `actions/handlers/workOrders.ts` | Work order action handlers |
| `actions/handlers/handover.ts` | Handover export action handlers |
| `actions/handlers/compliance.ts` | Hours of rest and compliance action handlers |
| `actions/handlers/procurement.ts` | Purchase order and procurement action handlers |
| `actions/handlers/equipment.ts` | Equipment management action handlers |
| `receiving/saveExtractedData.ts` | Save extracted receiving document data to backend |

---

### `app/` — Next.js pages (routing only, no business logic)

#### Auth + Login

| File | Job |
|---|---|
| `layout.tsx` | Root layout — QueryProvider, AuthProvider, VesselProvider, MicroactionsProvider, ShellWrapper |
| `page.tsx` | Home — VesselSurface component |
| `error.tsx` | Global runtime error boundary |
| `not-found.tsx` | 404 page |
| `login/page.tsx` | Login page |
| `login/LoginContent.tsx` | Interactive login form |
| `reset-password/page.tsx` | Password reset page |
| `reset-password/ResetPasswordClient.tsx` | Reset token validation + form |
| `auth/callback/page.tsx` | OAuth callback receiver |
| `auth/callback/AuthCallbackClient.tsx` | OAuth code exchange + redirect |
| `open/page.tsx` | Public unauthenticated landing |

#### Entity Pages (each domain follows the same pattern)

| Route | Page file | Job |
|---|---|---|
| `/certificates` | `certificates/page.tsx` | Certificate list |
| `/certificates/[id]` | `certificates/[id]/page.tsx` | Certificate detail lens |
| `/certificates/register` | `certificates/register/page.tsx` | Register new certificate |
| `/documents` | `documents/page.tsx` | Document tree list |
| `/documents/[id]` | `documents/[id]/page.tsx` | Document detail lens |
| `/equipment` | `equipment/page.tsx` | Equipment list |
| `/equipment/[id]` | `equipment/[id]/page.tsx` | Equipment detail lens |
| `/faults` | `faults/page.tsx` | Faults list |
| `/faults/[id]` | `faults/[id]/page.tsx` | Fault detail lens |
| `/handover-export` | `handover-export/page.tsx` | Handover queue + submitted |
| `/handover-export/[id]` | `handover-export/[id]/page.tsx` | Handover document lens |
| `/hours-of-rest` | `hours-of-rest/page.tsx` | HoR compliance overview |
| `/hours-of-rest/[id]` | `hours-of-rest/[id]/page.tsx` | Crew member HoR detail |
| `/hours-of-rest/signoffs` | `hours-of-rest/signoffs/page.tsx` | Signoff records |
| `/hours-of-rest/signoffs/[id]` | `hours-of-rest/signoffs/[id]/page.tsx` | Signoff detail |
| `/inventory` | `inventory/page.tsx` | Parts/inventory list |
| `/inventory/[id]` | `inventory/[id]/page.tsx` | Part detail lens |
| `/purchasing` | `purchasing/page.tsx` | Purchase orders list |
| `/purchasing/[id]` | `purchasing/[id]/page.tsx` | Purchase order detail lens |
| `/receiving` | `receiving/page.tsx` | Receiving records list |
| `/receiving/[id]` | `receiving/[id]/page.tsx` | Receiving detail lens |
| `/receiving/new` | `receiving/new/page.tsx` | New receiving record |
| `/shopping-list` | `shopping-list/page.tsx` | Shopping lists |
| `/shopping-list/[id]` | `shopping-list/[id]/page.tsx` | Shopping list detail lens |
| `/shopping-list/new` | `shopping-list/new/page.tsx` | New shopping list |
| `/warranties` | `warranties/page.tsx` | Warranties list |
| `/warranties/[id]` | `warranties/[id]/page.tsx` | Warranty detail lens |
| `/work-orders` | `work-orders/page.tsx` | Work orders list |
| `/work-orders/[id]` | `work-orders/[id]/page.tsx` | Work order detail lens |
| `/email` | `email/page.tsx` | Email module router |
| `/email/inbox` | `email/inbox/page.tsx` | Email inbox |
| `/email/[threadId]` | `email/[threadId]/page.tsx` | Email thread viewer |

#### Next.js API Routes (`app/api/`)

| File | Job |
|---|---|
| `whoami/route.ts` | Returns current user identity |
| `cron/keep-warm/route.ts` | Keeps deployment warm |
| `search/fallback/route.ts` | Search fallback endpoint |
| `email/search/route.ts` | Email search |
| `integrations/outlook/auth-url/route.ts` | Generate Outlook OAuth URL |
| `integrations/outlook/callback/route.ts` | Handle Outlook OAuth callback |
| `integrations/outlook/status/route.ts` | Outlook connection status |
| `integrations/outlook/disconnect/route.ts` | Revoke Outlook integration |
| `handover-export/[id]/acknowledge/route.ts` | Acknowledge handover export |
| `handover-export/[id]/content/route.ts` | Get handover export PDF/HTML |
| `handover-export/[id]/countersign/route.ts` | Countersign handover export |
| `handover-export/[id]/submit/route.ts` | Submit handover export |
| `v1/actions/execute/route.ts` | Proxy to backend action execution with auth |
| `v1/hours-of-rest/[...path]/route.ts` | Proxy to hours of rest backend |
| `v1/notifications/route.ts` | Fetch notifications |
| `v1/notifications/[id]/read/route.ts` | Mark notification read |
| `v1/notifications/mark-all-read/route.ts` | Mark all notifications read |

---

### `components/` — UI components

#### `ui/` — Base primitives (no domain logic)

| File | Job |
|---|---|
| `button.tsx` | Base button with variants |
| `checkbox.tsx` | Checkbox |
| `dialog.tsx` | Modal dialog wrapper |
| `dropdown-menu.tsx` | Dropdown menu |
| `input.tsx` | Text input |
| `label.tsx` | Form label |
| `select.tsx` | Select dropdown |
| `textarea.tsx` | Textarea |
| `EntityLink.tsx` | Hyperlink for entity references |
| `GhostButton.tsx` | Transparent button variant |
| `PrimaryButton.tsx` | Primary button |
| `SectionContainer.tsx` | Grouped content container |
| `StatusPill.tsx` | Status badge |
| `Toast.tsx` | Toast notification |
| `VitalSignsRow.tsx` | Vital/status information row |

#### `shell/` — App layout chrome

| File | Job |
|---|---|
| `AppShell.tsx` | Main layout grid — topbar + sidebar + subbar + body |
| `ShellWrapper.tsx` | Initialises shell providers and layout |
| `ShellContext.tsx` | Shell state — sidebar open/closed, modal visibility |
| `Topbar.tsx` | Top nav — vessel dropdown, global search, user menu |
| `Sidebar.tsx` | Left nav — domain links with counts |
| `Subbar.tsx` | Below-topbar — breadcrumb, scoped search, filter chips |
| `VesselSurface.tsx` | Home page vessel status and vital signs |
| `SearchOverlay.tsx` | Global search/spotlight overlay with keyboard shortcuts |
| `Tier3SearchPopup.tsx` | Drill-down tertiary search results |
| `NotificationBell.tsx` | Bell icon + notification dropdown |
| `SettingsModal.tsx` | Settings/preferences modal |
| `hooks.ts` | `useSidebarCounts`, `useShellState` |
| `api.ts` | Shell API calls (counts, notifications) |
| `useBreakpoint.ts` | Responsive breakpoint detection |

#### `lens/` — Entity detail view system

| File | Job |
|---|---|
| `EntityLensPage.tsx` | Main lens page — coordinates all detail sub-views |
| `IdentityStrip.tsx` | Header: entity title, status, avatar |
| `LensGlassHeader.tsx` | Glass-morphism header with entity info + action bar |
| `LensTabBar.tsx` | Tabbed navigation within entity detail |
| `LensPill.tsx` | Entity badge/chip |
| `RelatedDrawer.tsx` | Drawer: related entities from entity graph |
| `CollapsibleSection.tsx` | Collapsible content section |
| `ScrollReveal.tsx` | Reveal content on scroll |
| `SplitButton.tsx` | Button group with split dropdown |
| `mapActionFields.ts` | Maps action field definitions to form components |
| `ActionPopup/ActionPopup.tsx` | Action form modal — renders any action form |
| `ActionPopup/fields/renderField.tsx` | Dispatches to correct field component by type |
| `ActionPopup/fields/FieldAttachment.tsx` | File upload field |
| `ActionPopup/fields/FieldDatePick.tsx` | Date picker field |
| `ActionPopup/fields/FieldEntitySearch.tsx` | Entity search/reference field |
| `ActionPopup/fields/FieldKvEdit.tsx` | Key-value editor field |
| `ActionPopup/fields/FieldKvRead.tsx` | Key-value read-only display |
| `ActionPopup/fields/FieldPersonAssign.tsx` | Person/crew assignment field |
| `ActionPopup/fields/FieldSelect.tsx` | Dropdown select field |
| `ActionPopup/fields/FieldTextArea.tsx` | Multiline text field |
| `ActionPopup/shared/types.ts` | Form field and popup type definitions |
| `ActionPopup/shared/helpers.ts` | Form helper utilities |
| `ActionPopup/shared/SignatureLevels.tsx` | Signature requirement level UI |
| `ActionPopup/shared/SourceBlock.tsx` | Source/origin display |

#### `lens/entity/` — Per-domain entity content (one file per domain)

| File | Job |
|---|---|
| `CertificateContent.tsx` | Certificate detail content |
| `DocumentContent.tsx` | Document detail content |
| `EquipmentContent.tsx` | Equipment detail content |
| `FaultContent.tsx` | Fault/alarm detail content |
| `HandoverContent.tsx` | Handover export detail content |
| `HoursOfRestContent.tsx` | Hours of rest detail content |
| `HoRSignoffContent.tsx` | HoR signoff detail content |
| `PartsInventoryContent.tsx` | Parts/inventory detail content |
| `PurchaseOrderContent.tsx` | Purchase order detail content |
| `ReceivingContent.tsx` | Receiving detail content |
| `ShoppingListContent.tsx` | Shopping list detail content |
| `WarrantyContent.tsx` | Warranty detail content |
| `WorkOrderContent/index.tsx` | Work order detail content |
| `WorkOrderContent/WOModals.tsx` | Modals for work order actions |
| `WorkOrderContent/WOTabBodies.tsx` | Tab panel bodies for work order |

#### `lens/sections/` — Reusable lens sections (plug into any entity)

| File | Job |
|---|---|
| `AttachmentsSection.tsx` | Attachments/files section |
| `AuditTrailSection.tsx` | Change audit log section |
| `ChecklistSection.tsx` | Checklist items and task progress |
| `DocRowsSection.tsx` | Document rows/line items |
| `HistorySection.tsx` | Entity history/timeline |
| `KVSection.tsx` | Key-value custom data |
| `LedgerHistorySection.tsx` | Transaction/ledger history |
| `LensFileViewer.tsx` | File previewer |
| `LensImageViewer.tsx` | Image viewer |
| `NotesSection.tsx` | Notes and comments |
| `PartsSection.tsx` | Parts used in work order |
| `ReceivingDiscrepancies.tsx` | Receiving item discrepancies |
| `ReceivingLabelPrint.tsx` | Label printing for received items |
| `ReceivingLinkedPO.tsx` | Linked purchase order on receiving |
| `ReceivingOfficialDocuments.tsx` | Official/compliance documents |
| `ReceivingPackingList.tsx` | Packing list from receiving |
| `RelatedEquipmentSection.tsx` | Related equipment items |
| `RenewalHistorySection.tsx` | Certificate/warranty renewal history |
| `EquipmentPickerModal.tsx` | Modal to select and link equipment |

#### `lens/actions/` — Action-specific modals

| File | Job |
|---|---|
| `AddNoteModal.tsx` | Add notes to entities |
| `AttachmentUploadModal.tsx` | Upload attachments |
| `FileWarrantyClaimModal.tsx` | File warranty claim |

#### `components/documents/`

| File | Job |
|---|---|
| `DocumentTree.tsx` | Hierarchical document tree with folders |
| `DocumentsTableList.tsx` | Table view for documents |
| `DocumentsSearchResults.tsx` | Document search result cards |
| `docTreeBuilder.ts` | Builds tree hierarchy from flat document list |
| `filterDocs.ts` | Filter and search logic for documents |

#### `components/email/`

| File | Job |
|---|---|
| `EmailSurface.tsx` | Email module layout |
| `EmailInboxView.tsx` | Inbox list |
| `EmailThreadViewer.tsx` | Thread/conversation viewer |
| `LinkEmailModal.tsx` | Link email to entity |

#### `components/handover/`

| File | Job |
|---|---|
| `HandoverQueueView.tsx` | Queue of handovers awaiting action |
| `ExportedHandoversView.tsx` | Submitted/completed handovers |
| `HandoverDraftPanel.tsx` | Draft new handover panel |
| `AddDraftItemModal.tsx` | Add item to handover draft |
| `ConfirmExportModal.tsx` | Confirm and export handover |
| `useHandoverExport.ts` | Handover export state + API calls |

#### `components/hours-of-rest/`

| File | Job |
|---|---|
| `FleetView.tsx` | Fleet-wide HoR compliance overview |
| `DepartmentView.tsx` | Department-level HoR view |
| `VesselComplianceView.tsx` | Vessel-specific compliance tracking |
| `TimeSlider.tsx` | Time slider for HoR adjustment |
| `MyTimeView/index.tsx` | Current crew member's HoR view |
| `MyTimeView/helpers.ts` | Hours calculation helpers |
| `MyTimeView/primitives.tsx` | Primitive time display components |

#### `components/media/`

| File | Job |
|---|---|
| `DocumentCard.tsx` | Document card |
| `MediaRenderer.tsx` | Renders media by MIME type (image/pdf/etc) |
| `fileUtils.ts` | File type detection and size formatting |

#### `components/spotlight/`

| File | Job |
|---|---|
| `SpotlightSearch.tsx` | Search/command palette |
| `CommandPalette.tsx` | Command palette overlay |
| `SmartPointers.tsx` | Search result highlighting |
| `SpotlightResultRow.tsx` | Single search result row |
| `FilterChips.tsx` | Filter chip buttons |
| `QueryInterpretation.tsx` | Interpreted query and synonyms display |
| `LensPillStrip.tsx` | Entity pill strip for quick navigation |

#### Other component directories

| File | Job |
|---|---|
| `backdrop/BackdropRoot.tsx` | Root backdrop provider |
| `backdrop/LensBackdrop.tsx` | Animated orb backdrop for lens pages |
| `backdrop/lensColors.ts` | Backdrop orb colour definitions |
| `celeste/EntityLine.tsx` | Single-line entity reference display |
| `celeste/StatusLine.tsx` | Single-line status display |
| `modals/CreateShoppingListDrawer.tsx` | Create new shopping list drawer |
| `modals/ReportFaultModal.tsx` | Report new fault/alarm |
| `actions/modals/CreateWorkOrderModal.tsx` | Create work order |
| `actions/modals/CreatePurchaseOrderModal.tsx` | Create purchase order |
| `receiving/ReceivingDocumentUpload.tsx` | Document upload for receiving |
| `layout/RouteLayout.tsx` | Standard route layout wrapper |
| `ledger/LedgerPanel.tsx` | Transaction/ledger entries panel |
| `settings/Settings.tsx` | Settings/preferences panel |
| `viewer/DocumentViewerOverlay.tsx` | Full-screen document viewer overlay |
| `shopping-list/ShoppingListTableList.tsx` | Shopping list items table |
| `SuggestedActions.tsx` | Suggested actions for current entity |

---

### `features/` — Domain feature modules (list views + data adapters)

#### `features/entity-list/`

| File | Job |
|---|---|
| `components/FilteredEntityList.tsx` | List + filtering combined |
| `components/EntityTableList.tsx` | Table-based entity list |
| `components/EntityRecordRow.tsx` | Single entity row |
| `components/FilterBar.tsx` | Filter input + controls |
| `components/FilterPanel.tsx` | Filter options panel |
| `components/EmptyState.tsx` | Empty list state |
| `components/EntityDetailOverlay.tsx` | Overlay for entity quick-view |
| `components/PaginationFooter.tsx` | Pagination controls |
| `components/UrgencyGroupHeaders.tsx` | Urgency group headers |
| `hooks/useEntityList.ts` | Entity list data fetching |
| `hooks/useFilteredEntityList.ts` | Filtering layer on entity list |
| `types/certificate-columns.tsx` | Certificate table column definitions |
| `types/filter-config.ts` | Filter config per entity type |

#### `features/work-orders/`

| File | Job |
|---|---|
| `types.ts` | Work order types |
| `api.ts` | Work order API calls |
| `adapter.ts` | Work order data transformer |
| `columns.tsx` | Work order table columns |
| `useMonthWorkOrders.ts` | Fetch work orders for month calendar view |
| `WorkOrderCalendar.tsx` | Calendar view of work orders |

#### Other feature modules (same pattern per domain)

| Directory | Files | Job |
|---|---|---|
| `features/faults/` | `types.ts`, `api.ts`, `adapter.ts` | Faults list data layer |
| `features/equipment/` | `types.ts`, `api.ts`, `adapter.ts`, `columns.tsx` | Equipment list data layer |
| `features/inventory/` | `types.ts`, `api.ts`, `adapter.ts`, `components/` | Inventory list data layer |
| `features/purchasing/` | `columns.tsx` | PO table columns |
| `features/receiving/` | `types.ts`, `adapter.ts`, `columns.tsx` | Receiving list data layer |
| `features/shopping-list/` | `types.ts`, `adapter.ts` | Shopping list data layer |

---

## WHAT'S DEFERRED (not yet restructured)

| Item | Blocked on |
|---|---|
| `routes/handlers/internal_adapter.py` deletion | Documents + parts handlers rewritten to Phase 4 native |
| `action_router/` root files (registry.py, entity_prefill.py, etc.) | CEO sign-off on target structure — registry.py is 5,173L and imported everywhere |

---

## QUICK TASKING REFERENCE

| Symptom | File(s) to task |
|---|---|
| Wrong actions visible for an entity | `action_router/entity_actions.py` |
| Action requires wrong role | `action_router/registry.py` |
| Action form field wrong / missing | `action_router/entity_prefill.py`, `apps/web/src/lib/field-schema.ts` |
| Action executes but returns wrong data | `handlers/{domain}_handlers.py` |
| Action renders wrong in UI | `components/lens/entity/{Domain}Content.tsx` |
| Action form field UI broken | `components/lens/ActionPopup/fields/Field*.tsx` |
| Button placement / section order | `components/lens/entity/{Domain}Content.tsx` |
| API call fails (auth/headers) | `apps/web/src/lib/apiClient.ts` |
| Route not found / wrong URL | `apps/web/src/lib/entityRoutes.ts` |
| Entity list not loading | `features/{domain}/api.ts` + `hooks/useEntityList.ts` |
| Sidebar counts wrong | `components/shell/api.ts` |
| Notifications broken | `routes/notification_routes.py` + `app/api/v1/notifications/` |
| Search not returning results | `orchestration/search_orchestrator.py` |
| Search result ranked wrong | `orchestration/ranking_recipes.py` |
| Audit trail missing entry | `handlers/ledger_utils.py` + `action_router/logger.py` |
| State transition rejected | `middleware/state_machine.py` |
| JWT / auth rejected | `middleware/auth.py` + `validators/jwt_validator.py` |
| Cross-yacht data leak | `validators/rls_entity_validator.py` |
| PDF generation broken | `evidence/sealing.py` |
| Import failing | `services/import_service.py` + `parsers/` |
| Vessel switcher broken | `contexts/VesselContext.tsx` + `components/shell/Topbar.tsx` |
