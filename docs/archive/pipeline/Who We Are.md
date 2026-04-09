  Who We Are

  - Celeste is an intent‑first operating surface for real‑world operations (not a set
    of pages).
  - We are builders of deterministic, auditable systems where the database is truth and
    every user action is a small, verified change to reality (a micro‑action).

  Why We Exist

  - Traditional software forces navigation, hides state, and scatters history.
  - Operators don’t want to “go somewhere”; they want to “do something” safely, quickly,
    and with a provable audit trail.
  - We replace UI guesswork with deterministic triggers, strict role/RLS enforcement,
    and an immutable ledger.

  How We Operate

  - Single surface: One search bar; the system infers intent from the query.
  - Query → Focus → Act:
      - Query returns relevant entities; user selects one (focus).
      - Only then, the backend returns context‑valid micro‑actions (no global buttons).
  - Backend authority:
      - Backend defines actions, roles, signatures, RLS, and availability.
      - Frontend renders what backend returns — never invents actions.

  Focus & Vision

  - Intent‑first: Eliminate navigation overhead; reduce cognitive load.
  - Deterministic: Triggers react from state (not “AI predictions”).
  - Immutable truth: All changes pushed into pms_audit_log with signature semantics.
  - Safe by default: RLS deny‑by‑default, exact role checks, storage isolation.
  - Repeatable pipeline: Lens → DB → Code → Docker acceptance → Staging CI acceptance →
    Canary → Merge.

  Reasoning (Design Choices)

  - Micro‑actions:
      - Small, auditable, reversible or signed if critical.
      - Tightly permissioned by role and RLS; field classifications (required/optional/
        backend_auto) ensure clarity.
  - Deterministic triggers:
      - No “magic”; triggers reorder actions and pre‑fill data based on state. They
        never invent a new action.
  - Signature invariant:
      - pms_audit_log.signature is NOT NULL; {} for non‑signed; JSON for signed (e.g.,
        supersede_certificate).

  Application (Yacht PMS)

  - Entities/lenses: Faults, Work Orders, Equipment, Parts, Receiving, Certificates,
    Crew, Documents.
  - Orchestration:
      - Fault → Work Order → Parts/Notes/Attachments → Shopping/Receiving → Inventory/
        Docs.
      - Certificates (crew/vessel): create/update/link/supersede, expiry monitoring,
        audit.
  - Roles:
      - Crew (deny mutations), HOD (create/update/link), Captain/Manager (signed
        supersede).

  Guardrails (Non‑Negotiable)

  - Backend authority: Frontend renders blindly; no UI authority creep.
  - RLS everywhere: yacht_id via public.get_user_yacht_id(); deny by default.
  - Roles via helpers: is_hod(), is_manager(); registry.allowed_roles must match RLS
    behavior.
  - Storage isolation: documents bucket; object path {yacht_id}/certificates/
    {certificate_id}/{filename}; no cross‑yacht.
  - No audit FK to tenant auth.users (users live in MASTER); audit must never fail due
    to cross‑project user storage.

  How We Deliver (Template Pipeline)

  - Lens → DB migrations → Code → Docker acceptance (15 real‑user tests) → Staging CI
    acceptance (real JWTs) → Canary flags → Merge.
  - Everything is codified:
      - Cert lens pipeline lives under BACK_BUTTON_CLOUD_PMS/docs/pipeline/
        certificate_lens (actual lens, handlers, dispatcher, Docker tests, CI runner,
        workflow).
      - Template pipeline docs live under BACK_BUTTON_CLOUD_PMS/docs/pipeline (README/
        STAGES/FILE_MAP/RUNBOOK/GUARDRAILS/CONTEXT/NEXT_AGENT).

  What We’ve Learned (Pitfalls to Avoid)

  - MASTER→TENANT mapping is mandatory:
      - Create user in MASTER; map via MASTER.user_accounts; provision TENANT profiles/
        roles; then get JWT from MASTER.
  - Env drift between CI and Render:
      - CI uses TENANT_SUPABASE_; Render uses yTEST_YACHT_001_ + DEFAULT_YACHT_CODE.
  - Error mapping discipline:
      - Client errors must be 400/404; never 500. Treat 500 as hard failure in tests.
  - Role/RLS drift:
      - Registry.allowed_roles must match is_hod()/is_manager(); CI must fail when RLS
        denies allowed actions.
  - Storage/doc linkage:
      - Guard doc existence; use the correct doc_metadata fields; don’t prefix
        storage_path with “documents/”.

  Brand Success & Differentiation

  - Celeste replaces “screens and buttons” with intent → focus → act.
  - We eliminate guesswork; we prove outcomes:
      - Strict role/RLS
      - Immutable audit with signatures
      - Deterministic triggers
  - We ship with evidence (Docker and staging acceptance), not opinions.

  This is who we are, why we exist, how we operate, and how we deliver — captured in a
  repeatable pipeline the next agent can trust and reuse.