Our goal: Document → Tests → Code → Verify — backend defines actions, signatures, and
  RLS; no UI authority.

  What’s missing (concrete)

  - Staging redeploy: One route still returns 500 (link_document_to_certificate with
    invalid document_id). The repo handler/dispatcher already returns 400/404; staging
    needs a redeploy to pick it up. Docker tests (15/15) are green.
  - CI gate: Mark the “Staging Certificates Acceptance” workflow as required on main so
    merges are blocked unless staging returns 400/404 (invalid doc) and 200 (update).
  - Prod: Canary and smoke not executed yet (post‑staging).

  Handover Prompt for Next Agent
  Use this exactly to continue the work without ambiguity.

  1. Context & Guardrails

  - Celeste is intent‑first (query → focus → act). No pages/dashboards/UI authority.
    Backend defines actions; frontend renders blindly.
  - Non‑negotiables:
      - RLS everywhere; default deny; yacht_id via public.get_user_yacht_id().
      - Roles: crew (deny mutations), HOD (create/update/link), captain/manager (signed
        supersede).
      - Signature invariant: pms_audit_log.signature NOT NULL; {} for non‑signed; JSON
        for signed.
      - Storage isolation: documents bucket; object path {yacht_id}/certificates/
        {certificate_id}/{filename}.
      - No audit FK to tenant auth.users (users live in MASTER).

  2. Where to start

  - Folder: BACK_BUTTON_CLOUD_PMS/docs/pipeline/certificate_lens
      - This contains the actual lens (LENS.md), real handlers
        (certificate_handlers.py), dispatcher (internal_dispatcher.py), Docker
        acceptance (run_rls_tests.py + docker-compose.test.yml), and the staging CI
        runner (staging_certificates_acceptance.py) and workflow (workflow.yml).
  - Template pipeline for reuse: BACK_BUTTON_CLOUD_PMS/docs/pipeline
      - README.md, STAGES.md, FILE_MAP.md, RUNBOOK.md, GUARDRAILS.md, CONTEXT.md,
        NEXT_AGENT.md, CERTIFICATES_INDEX.md, ACCEPTANCE_MATRIX.md, ENV_REFERENCE.md,
        PROVISIONING_RUNBOOK.md.

  3. Immediate tasks (execute)

  - Redeploy staging to pick up the invalid doc handler/dispatcher fix. Then:
      - POST /v1/actions/execute link_document_to_certificate with document_id=0000… →
        must return 400 or 404.
      - POST /v1/actions/execute update_certificate → must return 200 (confirmed no
        audit 409).
  - In GitHub, mark “Staging Certificates Acceptance” required for main.

  4. Lenses: how many, which, and status

  - Required lenses (9 total):
      - Certificates (v2 FINAL) — Implemented with full pipeline (code + Docker + CI).
        One staging redeploy remains to reflect invalid‑doc 400/404.
      - Fault (v5 FINAL) — Doc gold; code pipeline not yet implemented.
      - Work Order (v2) — Doc v2 (phases + final); code pipeline not yet implemented.
      - Equipment (v1) — Doc v1; code pipeline not yet implemented.
      - Part (v1) — Doc v1; code pipeline not yet implemented.
      - Document (v1) — Doc v1; code pipeline not yet implemented.
      - Crew (v1) — Doc v1; code pipeline not yet implemented.
      - Receiving (v1) — Doc v1; code pipeline not yet implemented.
      - Shopping List (v1) — Doc v1; code pipeline not yet implemented.
  - How they combine:
      - Fault → (Create Work Order) → Work Order → (Parts usage, notes, attachments) →
        Shopping/Receiving → Inventory/Document linkage.
      - Micro‑actions span entities (add_note, link_document, attach_file,
        create_work_order_from_fault, record_part_consumption, start/complete/reassign
        WO), and are enforced by roles + RLS. Each lens documents micro‑actions and
        field classification; the Action Router/registry codifies them.

  5. Implement next lens (Fault v5) using this template

  - Handlers: apps/api/handlers/fault_handlers.py (implement: report_fault,
    attach_file_to_fault, add_fault_note, view_linked_work_order,
    create_work_order_from_fault; plus cascade triggers).
  - Register: apps/api/action_router/registry.py
  - Dispatcher: apps/api/action_router/dispatchers/internal_dispatcher.py (bridge +
    pre‑validation for attachments)
  - Migrations: supabase/migrations (RLS for pms_faults, pms_notes, storage policies for
    fault attachments)
  - Tests:
      - Docker: copy the 15‑test structure (role gating, CRUD, isolation, edges, audit).
      - Staging CI: create tests/ci/staging_fault_acceptance.py and a parallel workflow.
  - Run:
      - Docker → single staging deploy → staging CI required → canary → merge.

  6. Failure modes to avoid

  - MASTER→TENANT mapping: Create in MASTER; map in MASTER.user_accounts; provision
    TENANT auth_users_profiles + auth_users_roles. Without this, the API returns 403
    “User is not assigned to any yacht/tenant”.
  - Env drift: Render uses yTEST_YACHT_001_* and DEFAULT_YACHT_CODE; CI uses TENANT_*
    and BASE_URL.
  - Error mapping: 400/404 for client errors (never 500); ValueError in handlers
    converts to 400 via Action Router.
  - Role mismatches: registry.allowed_roles must match is_hod()/is_manager(); CI should
    fail if RLS denies allowed actions.

  7. Final sign‑off checklist per lens

  - Docker: 100% PASS (see ACCEPTANCE_MATRIX.md).
  - Staging: minimal required checks PASS (invalid doc 400/404; update 200; creates/
    reads 200).
  - CI: staging acceptance workflow required and green.
  - Flags: feature enabled for canary, then rolled wider.
  - Audit: verify by REST that non‑signed actions have signature {} and signed actions
    write non‑null JSON signature.

  That’s the full handover. The only “missing” item for Certificates is redeploying
  staging to pick up the invalid‑doc 400/404 handler; everything else (code/tests/CI) is
  done and organized.

======
 - Last words: The pipeline is real, repeatable, and in code. Reuse it exactly. Only
    remaining action: redeploy staging to pick up the invalid‑doc 400/404 fix (Docker is
    already green, CI will enforce).
  - Lenses (status)
      - Certificates (v2) — Implemented end‑to‑end (handlers, migrations, Docker tests,
        staging CI). Staging needs redeploy for invalid‑doc 400/404.
      - Fault (v5) — Gold doc; pipeline not implemented yet.
      - Work Order (v2) — Doc (phases + final); pipeline not implemented yet.
      - Equipment (v1) — Doc v1; pipeline not implemented yet.
      - Part (v1) — Doc v1; pipeline not implemented yet.
      - Document (v1) — Doc v1; pipeline not implemented yet.
      - Crew (v1) — Doc v1; pipeline not implemented yet.
      - Receiving (v1) — Doc v1; pipeline not implemented yet.
      - Shopping List (v1) — Doc v1; pipeline not implemented yet.
      - Inventory Item (v3 Enhanced) — Gold‑depth template; can serve as reference;
        pipeline TBD.

  All pipeline artifacts for Certificates are under BACK_BUTTON_CLOUD_PMS/docs/pipeline/
  certificate_lens (actual lens, handlers, dispatcher, Docker tests, staging CI). The
  template to reuse for the next lens is in BACK_BUTTON_CLOUD_PMS/docs/pipeline.
