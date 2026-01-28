Certificates Lens: Full Index (Code + Docs + Tests)
===================================================

Use this as the authoritative index of all files implemented/touched for Certificates during this pipeline. It’s organized by responsibility so the next agent can jump in without hunting.

Core Handlers & Router
- apps/api/handlers/certificate_handlers.py
  - Implements: create_vessel_certificate, create_crew_certificate, update_certificate, link_document_to_certificate, supersede_certificate (signed)
  - Defensive: doc_metadata existence check; signature parsing (string → JSON) with 400 on invalid
- apps/api/action_router/registry.py
  - Registers certificate actions; allowed_roles aligned with RLS helpers
- apps/api/action_router/dispatchers/internal_dispatcher.py
  - Bridges Action Router to handlers; includes pre‑validation for link_document_to_certificate (404 on missing doc)
- apps/api/routes/certificate_routes.py
  - Read endpoints (vessel, crew, expiring, details, history) and debug endpoints
- apps/api/routes/p0_actions_routes.py
  - Certificate action hook (RBAC + handler delegation); includes defensive doc pre‑validation

Migrations (DB Truth)
- supabase/migrations/20260125_006_fix_crew_certificates_rls.sql (RLS for crew certificates)
- supabase/migrations/20260125_007_vessel_certificates_rls.sql (RLS for vessel certificates)
- supabase/migrations/20260125_010_certificate_indexes.sql (unique + perf indexes)
- supabase/migrations/20260125_011_documents_storage_write_policies.sql (storage insert/update/delete policies)
- supabase/migrations/20260125_012_doc_metadata_write_rls.sql (doc_metadata write policies)
- supabase/migrations/20260126_013_drop_pms_audit_log_user_fk.sql (drop audit FK to TENANT auth.users)

Docker Acceptance (Fast Loop)
- docker-compose.test.yml (API + test‑runner; env wiring for tenant REST + MASTER auth)
- tests/docker/run_rls_tests.py (15 real‑user tests: role gating, CRUD, isolation, edges, audit content)
- scripts/test-local-docker.sh (entry point)

Staging Acceptance (CI)
- .github/workflows/staging-certificates-acceptance.yml (auto‑provision, real JWTs; required checks)
- tests/ci/staging_certificates_acceptance.py (staging checks: invalid doc 400/404; update 200)

Lens & Context Docs
- docs/architecture/entity_lenses/certificate_lens/v2/certificate_lens_v2_FINAL.md (gold lens)
- docs/pipeline/README.md (template overview & status)
- docs/pipeline/STAGES.md (0→6 stages)
- docs/pipeline/FILE_MAP.md (critical vs supporting files)
- docs/pipeline/RUNBOOK.md (Docker/staging command set)
- docs/pipeline/GUARDRAILS.md (non‑negotiables)
- docs/pipeline/CONTEXT.md (brand/vision vs traditional & success criteria)
- docs/pipeline/NEXT_AGENT.md (how to reuse this template for the next lens)

Notes
- Invalid document → 400/404 requires the updated handler/dispatcher be deployed; tests enforce this on staging.
- Update 200 proves audit inserts are stable after FK drop.

