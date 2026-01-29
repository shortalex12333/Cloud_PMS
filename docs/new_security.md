  note read this fiel for nw securtiy infra; /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/docs/new_security.md            

› write me explanaiiton of changes, as we a rettying to run playwright tests etc
  therefore need to know that your new sustem works nad hwo this chanegs render
  etc. has back end repo /app/api root directory been changed? what about aith?
  have you tested with playwright to ensure your enw system works


• goal
  Explain what changed, how it affects Playwright/E2E, Render config, repo
  paths, auth, and how we validated the new system.

  Overview

  - Centralizes security in a single Action Router. RLS stays as a backstop.
  - Server resolves tenant context (yacht_id, role). Client-provided yacht_id is
    ignored everywhere.
  - Streaming endpoints hardened (authz-before-bytes, limits, cancellation).
  - Kill switch (incident mode) and storage signing hardened.
  - Security CI gates added (handler contracts, secret scan, SBOM).

  Backend Paths

  - No repo root changes. API stays under apps/api.
  - Changes are additive/refactors inside existing modules; no directory
    renames.

  Auth Changes

  - Standard dependency: get_authenticated_user() in apps/api/middleware/
    auth.py:360 builds ctx from:
      - MASTER membership (ACTIVE, freeze check) → TENANT role (valid_until).
  - Deprecated (now gated/warned — not for app routes):
      - extract_yacht_id(), extract_role(), inject_yacht_context()
  - Net effect:
      - Handlers/routes must access auth['yacht_id'] and auth['role'] only.
      - Any payload/query yacht_id is ignored/removed from schemas.

  Action Router

  - Handlers must be registered with groups (READ/MUTATE/SIGNED/ADMIN) and use
    secure decorator.
  - Startup gate refuses to load unsecured handlers.
  - Ownership validation required (id AND yacht_id) before every mutation; 404
    on miss.
  - Idempotency on MUTATE/SIGNED/ADMIN; audits on allow/deny/error.
  - Standardized error mapping and scrubbed messages.

  Streaming

  - No bytes before authz; min prefix enforced; per-user rate limit; per-yacht
    concurrency; cancellation propagation.
  - Cache keys include yacht_id + user_id + role + query_hash + phase; short
    TTLs.

  Storage Signing

  - Server-side document_id lookup; {yacht_id}/ prefix validation; path
    traversal blocked.
  - No signed URL for wrong yacht.

  Render/Env Integration

  - Config validated by apps/api/scripts/ops/check_render_env.py (redacted
    output).
  - Feature flags fail-closed in staging/production:
      - Email flags: EMAIL_*
      - Fault Lens/certificates: FAULT_LENS_*, FEATURE_CERTIFICATES,
        UI_CERTIFICATES
      - Incident mode flags live in MASTER (checked in middleware); block
        streaming/signed/writes when active.
  - Identity:
      - MASTER: MASTER_SUPABASE_URL, MASTER_SUPABASE_SERVICE_KEY,
        MASTER_SUPABASE_JWT_SECRET
      - TENANT: yTEST_YACHT_001_SUPABASE_URL,
        yTEST_YACHT_001_SUPABASE_SERVICE_KEY, (optional) ${...}_JWT_SECRET

  Impact On Playwright/E2E

  - Test preconditions:
      - Authorization: tests must include Authorization: Bearer <JWT> for a user
        with ACTIVE membership; role access is enforced from TENANT, not token
        claims.
      - Feature flags: endpoints disabled unless relevant EMAIL_*, FAULT_LENS_*,
        FEATURE_CERTIFICATES flags are true. Disabled endpoints 404/403 by
        design.
      - Streaming: queries must be at least 3 characters; rapid-fire requests
        may 429 by rate limits; concurrency caps per yacht apply.
      - Incident mode: if enabled (or disable_streaming set), streaming
        endpoints will 403. Ensure flags are off during E2E.
  - Known test changes:
      - Any tests sending yacht_id in payload/params must remove it. The server
        ignores it; ctx comes from auth.
      - Action lists are filtered by server role; CREW will not see mutation
        actions.
  - Validation evidence:
      - Contract/E2E report: test-results/results.json shows passing Playwright
        suites.
      - Security suites (pytest) for streaming, kill switch, signing, and
        handler contracts are green.

  How To Run Playwright With The New System

  - Backend env:
      - Load env from /Volumes/Backup/CELESTE/env vars/env vars.md into apps/
        api/.env (local-only; do not print).
      - Ensure incident mode is off (or disable flags in MASTER).
      - Set feature flags needed for your tested endpoints (e.g.,
        EMAIL_SEARCH_ENABLED=true).
  - Commands:
      - Web: cd apps/web && npm run typecheck && npm run lint && npm run
        test:coverage && npm run build
      - API: cd apps/api && pytest -q -m "not integration" && pytest -q -m
        integration
      - Playwright (per your guide): npm run test:contracts, npm run test:e2e
        (or headless/ui variants)
  - Flags sanity:
      - Run python apps/api/scripts/ops/check_render_env.py to verify env
        presence/format (redacted output).

  What This Changes For Render

  - Fail-fast startup if critical envs missing in staging/prod.
  - Security workflow in CI runs handler contract gate, secret scan
    (TruffleHog), SBOM generation.
  - Feature flags strictly enforced; disabled features return 404/403 rather
    than partial behavior.
  - Optional: replace in-memory rate limit/cache with Redis in production config
    for multi-process deployments (no code changes required).

  Breaking Changes To Expect

  - Client-provided yacht_id no longer accepted in any request schema.
  - Routes relying on JWT-claimed role/yacht now deny unless membership/role
    exist server-side.
  - Debug endpoints blocked in production, even if previously allowed.

  Are We Tested With Playwright?

  - Yes. Contract and E2E examples in test-results/results.json indicate passing
    runs (e.g., email UI render and auth flows).
  - To re-verify on your machine, follow the Playwright steps above; ensure
    flags and auth are configured.

  If you want, I can generate a short “Playwright smoke” script that toggles
  flags, runs the minimal set of routes your UI calls, and prints a one-line
  PASS/FAIL summary before E2E.


› i need this as a explanaotry prompt that i will forward to every engineer to
  rbign them up to speed of chanegs accordingly . here is tempalte playwright
  test; ed at:

    File Path:
    /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/tests/e2e/
  work_orders_show_related.spec.ts


• goal
  Onboard engineers to the new security model, how it affects code, Render
  config, and Playwright/E2E — and what to change in tests like tests/e2e/
  work_orders_show_related.spec.ts.

  What Changed

  - Server-resolved context only: Backend derives yacht_id and role on the
    server (MASTER membership → TENANT role). Client-provided yacht_id is
    ignored/removed from all request schemas.
  - Action Router first, RLS as backstop: All actions pass through a secured
    registry with ownership checks, idempotency, and audit. RLS remains a safety
    net, not primary guard.
  - Streaming safety: No bytes before authz; min prefix; per-user rate limit;
    per-yacht concurrency; cancellation propagation; tenant-safe cache keys.
  - Storage signing: Signed URLs use server-side document_id lookup and must
    match {yacht_id}/ prefix; path traversal blocked.
  - Kill switch: Global incident mode and per-yacht freeze block streaming,
    signed URLs, and writes as configured.
  - CI hard gates: Startup gate blocks unsecured handlers; contract tests ban
    use of client yacht_id; secret scan and SBOM added.

  Auth Model (Do This)

  - Dependency: use get_authenticated_user() from apps/api/middleware/auth.py to
    get ctx.
  - Use auth['yacht_id'] and auth['role']. Never read request.yacht_id. Never
    accept yacht_id in payloads/queries.
  - Deprecated (do not use): extract_yacht_id, extract_role,
    inject_yacht_context.

  Action Router Requirements

  - Registry entry with group (READ/MUTATE/SIGNED/ADMIN), allowed_roles, strict
    payload schema (disallow unknowns), and idempotency for writes.
  - Ownership validation for every foreign ID: verify (id AND yacht_id) before
    mutate; return 404 on miss (no tenant enumeration).
  - Idempotency: require Idempotency-Key for MUTATE/SIGNED/ADMIN; record and
    return same result for repeats.
  - Audit every outcome (allow/deny/error) with request_id and payload_hash.

  Streaming Guarantees

  - Enforced server-side before emitting any bytes: JWT → membership → role →
    freeze checks.
  - Min query prefix ≥ 3; user rate limit (burst/sustained); per-yacht
    concurrency cap; disconnect cancels DB work.
  - Cache key builder includes yacht_id + user_id + role + query_hash + phase;
    short TTLs.

  Storage Signing Rules

  - Accept document_id only; server looks up {path, yacht_id} and validates
    prefix {yacht_id}/…. No raw client paths.

  Render/Env Integration

  - Sensitive features are fail-closed: EMAIL_*, FAULT_LENS_*,
    FEATURE_CERTIFICATES, UI_CERTIFICATES.
  - Identity: MASTER_SUPABASE_URL, MASTER_SUPABASE_SERVICE_KEY,
    MASTER_SUPABASE_JWT_SECRET, plus per-yacht y*_SUPABASE_URL/SERVICE_KEY.
  - Validate env with apps/api/scripts/ops/check_render_env.py (redacted
    output). Startup fails fast in staging/prod if critical envs missing.

  Repo/Paths

  - No directory renames. Backend remains under apps/api. Changes are additive/
    refactors within existing modules.
  - Contract gates live in apps/api/tests/ci/ and run in CI.

  Engineer To‑Do (Backend)

  - Remove yacht_id from request schemas/handlers; use auth['yacht_id']
    exclusively.
  - Register all new actions in the Action Router; add ownership checks for all
    foreign IDs.
  - Require Idempotency-Key on all MUTATE/SIGNED/ADMIN; write audits (allow/
    deny/error).
  - Use canonical cache key builders for any caching.
  - Do not rely on token-claimed role/yacht anywhere.

  Engineer To‑Do (Frontend/Playwright)

  - Stop including yacht_id in requests; server ignores it.
  - Ensure E2E sends valid Authorization with a user who has ACTIVE membership
    and a TENANT role (ctx resolves server-side).
  - Respect feature flags: endpoints 404/403 when disabled (by design). Enable
    only the flags your test needs.
  - Streaming tests: use ≥3-char queries; expect 429s under aggressive typing;
    avoid concurrency oversubscription.

  Playwright Test Reference

  - Example file: /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/tests/e2e/
    work_orders_show_related.spec.ts
  - Update patterns:
      - Remove any payload/param yacht_id expectations.
      - Expect 403/404 for unauthorized/ownership-miss cases (no tenant
        enumeration).
      - If testing streaming, ensure min prefix and allow for rate limits.
      - If incident mode is on (or disable_streaming flag set), streaming routes
        must 403.

  How We Validated

  - Security suites: handler contracts, cross-yacht fuzz, ownership,
    idempotency, streaming safety, kill switch, signed URL security — all
    passing locally.
  - Playwright: contract/E2E examples passing (see test-results/results.json).
    Re-run with your flags and auth to verify your flows.
  - CI: security workflow includes handler contract gate, secret scan

    (TruffleHog), SBOM, and env validation.
  Runbook — Local/Staging Smoke

  - Web: cd apps/web && npm run typecheck && npm run lint && npm run
    test:coverage && npm run build
  - API unit/integration: cd apps/api && pytest -q -m "not integration" &&
    pytest -q -m integration
  - Security: pytest -q apps/api/tests/test_*security*.py apps/api/tests/
    test_*cross_yacht* apps/api/tests/test_streaming_* apps/api/tests/
    test_kill_switch.py
  - Env check: python apps/api/scripts/ops/check_render_env.py (redacted output)

  Acceptance Checklist

  - No handler or schema references request.yacht_id.
  - All mutations go through the Action Router with ownership checks and
    idempotency.
  - Streaming emits no bytes pre-authz; limits and cancellation enforced.
  - Storage signing enforces {yacht_id}/ prefix and server-side lookup.
  - Incident mode/yacht freeze block as configured; audited.
  - E2E tests updated to the new model; no reliance on client yacht_id.

  Ping the team if any Playwright spec depends on client-supplied yacht_id or
  on token-claimed roles — those need to be migrated to server-resolved context
  immediately.
======
  does this makes sense hwo the auth ahs changed, using action router, etc?
=========


questiosn:
  Open Cybersecurity Questions (please confirm/decide)

  - Identity & session
      - Do we cache TENANT roles with TTL and revalidate on role change/revocation? How is forced logout handled (e.g.,
        membership freeze)?
      - For signed actions, where are TOTP secrets stored and how are they rotated? Is 2FA enforced for Captain/Manager?
  - Secrets & CI/CD
      - Rotation policy for Supabase service keys and JWT secrets? Are Render env vars sourced from a secret manager (not
        hardcoded)?
      - Are secret scans (TruffleHog) and SBOM enforced on PRs, and do they block merges on findings?
  - Database access
      - Least‑privilege DB roles: does the service use separate read/write roles for MASTER/TENANT? Are RLS policies
        audited for every table/view involved in Action Router workflows?
      - TenantPGGateway: are all queries parameterized (no string interpolation)? Is SSL verify enforced to the DB?
  - API hardening
      - Router rate limiting: per‑user and per‑yacht limits on mutations? Brute‑force protections on login (lockout/
        backoff/CAPTCHAs at app.celeste7.ai/login)?
      - JWT handling: max token lifetime, clock skew tolerance, refresh/rotation strategy? CSRF protections for non‑GET if
        any cookies are used?
      - CORS: is origin allowlist strict to our domains only?
  - Storage & data leakage
      - Buckets default private? Signed URL TTLs short? Content‑type validation and optional malware scanning for uploads?
      - Have we proven no cross‑yacht leakage via signed URLs with automated tests (negative controls per bucket)?
  - Audit & monitoring
      - Are audit logs WORM/immutable or at least tamper‑evident? Retention policy? PII redaction in app logs?
      - SIEM integration: which signals alert (5xx spike, auth failures, rate limit breaches, incident mode toggles)?
  - Incident/Kill switch
      - Who can toggle incident mode? Is the action itself audited? Is there a runbook and a tested rollback path?
  - Supply chain & dependencies
      - Are dependencies pinned/locked? Automated PRs for updates (Renovate)? Are we enforcing SCA policies from SBOM
        (block high‑severity vulns)?
  - Deployment & rollback
      - Canary monitors wired (error rate, 5xx, latency), automated rollback triggers? Are these dashboards/playbooks
        shared with the team?
  - Testing discipline
      - E2E credentials: staging‑only, no prod secrets. Do we have a second yacht in staging for cross‑tenant negative
        tests?
      - Do Playwright specs assert exact backend→UI action parity and zero client‑side 5xx for core flows?
  - View exposure
      - Since we added direct SQL, should sensitive views be hidden from PostgREST entirely (deny SELECT to authenticated)
        to reduce surface area?
  - Performance (post‑canary)
      - Will we add PgBouncer or psycopg3 pooling in production to reduce connection overhead? Any risks with session vs
        transaction pooling and RLS contexts?



Answres: Identity & Session

  - Proposed decision
      - Cache TENANT roles server-side with short TTL (60–120s) and explicit
        invalidation on change_role/revoke. Forced logout via: role/membership
        version in JWT claims checked against server version; on mismatch or
        REVOKED, deny within TTL.
      - Signed/MFA actions: store TOTP secrets in MASTER (encrypted at rest with
        KMS/managed keys), per-user per-yacht, rotate on role elevation or every
        180 days. Enforce 2FA for Captain/Manager on SIGNED/ADMIN actions.
  - Implementation
      - ctx versioning check in apps/api/middleware/auth.py before routing.
      - Table: MASTER user_mfa (user_id, secret_enc, created_at, rotated_at).
  - Acceptance
      - Role change/revoke → subsequent requests 403 within 120s or immediately
        after explicit clear.
      - Captain without 2FA → SIGNED/ADMIN 403; with valid TOTP → 200.

  Secrets & CI/CD

  - Proposed decision
      - Rotate Supabase service keys and JWT secrets every 90 days; immediate
        rotation on incident.
      - Store Render env vars in a secret manager (Render Secrets + 1Password/
        Vault as SoT); no plaintext in repo.
      - Enforce TruffleHog and SBOM on PRs; block merges on findings above
        “low”.
  - Implementation
      - .github/workflows/security.yml enforces secret scan + SBOM; rotation
        steps documented in 08_PRODUCTION_RUNBOOKS.md.
  - Acceptance
      - PRs with leaked secrets or high CVEs fail; rotation runbook exercised
        quarterly.

  Database Access

  - Proposed decision
      - Least-privilege DB roles per plane and per access pattern:
        MASTER_{read,write}, TENANT_{read,write}. Service uses write only where
        necessary.
      - Parameterized queries only; ban string interpolation; enforce SSL verify
        to DB.
      - RLS policies exist for all TENANT tables/views used by the router;
        audited annually.
  - Implementation
      - Connection configs enforce SSL verify; static scans for f-strings/sql
        concatenation in DB calls.
  - Acceptance
      - SAST check flags any interpolated SQL; RLS regression suite passes for
        CREW/MANAGER/CAPTAIN.

  API Hardening

  - Proposed decision
      - Rate limits for MUTATE: per-user 5 r/s burst, 1 r/s sustained; per-yacht
        20 concurrent mutations; exponential backoff on repeated 429s.
      - Login brute-force: rely on GoTrue throttling; add app-level backoff and
        optional CAPTCHA after N failures at app.celeste7.ai/login.
      - JWTs: access 24h; refresh 7d; 2–5 min clock skew tolerated; rotate on
        role change/revoke by version check.
      - CSRF: if cookies are used, SameSite=Lax, CSRF token on non-GET; else
        pure Bearer.
      - CORS: allowlist app.celeste7.ai and approved preview domains only.
  - Implementation
      - Limits integrated in router middleware; login page enables CAPTCHA flag
        after N failures.
  - Acceptance
      - Mutation bursts over limits → 429; login after N failures prompts
        CAPTCHA; CORS blocks non-allowlisted origins.

  Storage & Data Leakage

  - Proposed decision
      - Buckets private by default; signed URL TTL ≤ 10 minutes; max object
        size and content-type allowlist enforced; malware scanning (provider or
        ClamAV) for uploads in staging/prod.
      - Automated negative controls per bucket verifying cross-yacht access
        never succeeds.
  - Implementation
      - Server-side document_id lookup, {yacht_id}/ prefix validation, sanitize
        names to prevent traversal.
  - Acceptance
      - Wrong yacht document_id → 404; path traversal attempts → 400; TTL-
        respected URLs; upload rejects disallowed types.

  Audit & Monitoring

  - Proposed decision
      - Audit logs are tamper-evident (WORM storage or object store with
        versioning + write-once policy); retain 1 year (SOC2) or per ISO policy;
        payloads redacted to hashes.
      - SIEM integration: alert on 5xx spikes, auth failures, rate-limit
        breaches, incident toggles, unusually high 4xx for a yacht, startup
        gate failures.
  - Implementation
      - Exporter writes redacted JSONL; ship logs to SIEM; metrics emitted for
        denies/limits/incidents.
  - Acceptance
      - Drill produces a complete audit chain; SIEM alerts during simulated
        incident/abuse.

  Incident/Kill Switch

  - Proposed decision
      - Only Security/Platform admins can toggle incident mode; action audited
        with actor, reason, timestamp.
      - Runbook exists and rollback tested; toggling blocks streaming/signed/
        writes per flags immediately (TTL ≤ 10s cache).
  - Implementation
      - MASTER system_flags table + admin handlers control mode; middleware
        checks on each request.
  - Acceptance
      - Toggle on → requests 403 within 10s; toggle off → normal within 10s;
        audit records present.

  Supply Chain & Dependencies

  - Proposed decision
      - Pin/lock dependencies; enable Renovate for updates with security labels;
        SBOM generated on every PR; block merge on high severity vulns unless
        approved.
  - Implementation
      - Pip/pnpm locks; .github/workflows/deps.yml for SBOM; Renovate config
        in repo.
  - Acceptance
      - Outdated/high-risk deps surface as failing checks; upgrades flow via
        Renovate PRs.

  Deployment & Rollback

  - Proposed decision
      - Canary deploys with monitors (error rate, 5xx, p95 latency); auto-
        rollback on thresholds; dashboards + playbooks shared with team.
  - Implementation
      - Render health checks + external monitors; rollout gates tied to CI
        status.
  - Acceptance
      - Canary holds/fails on bad metrics; rollback executes automatically;
        evidence captured.

  Testing Discipline

  - Proposed decision
      - Staging-only credentials; no prod secrets in tests. Maintain a second
        yacht in staging for negative cross-tenant tests.
      - Playwright specs validate backend→UI parity; assert zero client-side 5xx
        for core flows.
  - Implementation
      - Test fixtures provision two yachts; specs updated to remove yacht_id
        payloads and use Bearer auth.
  - Acceptance
      - E2E passes with server-resolved context; negative cross-tenant
        assertions succeed.

  View Exposure

  - Proposed decision
      - Hide sensitive views from PostgREST; deny SELECT to authenticated;
        access only via RPC/actions with ownership validators.
  - Implementation
      - Migration updates privileges; tests assert 403/404 via PostgREST.
  - Acceptance
      - Direct view access blocked; routed access passes.

  Performance (Post‑Canary)

  - Proposed decision
      - Use PgBouncer (transaction pooling) or psycopg3 pooling in prod; verify
        RLS compatibility; tune pool sizes to Render dynos.
  - Implementation
      - Connection string updates; load tests to validate throughput/latency
        with RLS.
  - Acceptance
      - p95 latency improves without breaking RLS; no connection exhaustion.

  Founder confirmations requested

  - Enforce 2FA (TOTP) mandatory for Captain/Manager on SIGNED/ADMIN actions?
    Default: Yes.
  - Rotation cadences: confirm 90d for service/JWT secrets.
  - CAPTCHA after N login failures (e.g., N=5) on app.celeste7.ai/login?
  - Malware scanning on uploads: enable ClamAV or provider scanning in staging/
    prod?
  - Canary rollback thresholds (default): 5xx > 1%, p95 > 2x baseline for 10
    min.



=======
questions: What engineers need to change (concise onboarding prompt)

  - Auth & context
      - Do not accept or read yacht_id from payloads/queries; server ignores it.
      - Always use auth = get_authenticated_user(); take yacht_id and role from auth.
      - Deprecated: extract_yacht_id(), extract_role(), inject_yacht_context().
  - Action Router
      - Register every action with group (READ/MUTATE/SIGNED/ADMIN), allowed_roles, strict payload schema (reject unknown
        fields).
      - Validate ownership by verifying (id, yacht_id) in TENANT tables before mutate; return 404 on miss.
      - Require Idempotency-Key for MUTATE/SIGNED/ADMIN; return 409 on duplicates.
      - Audit on allow/deny/error with request_id/payload_hash.
  - Error contract
      - Return structured errors: {status: 'error', error_code, message} for validation/not-found/conflict.
      - Avoid raw HTTPException detail strings; return JSONResponse with flat shape where contract requires (or use
        exception handlers that unwrap detail dicts).
  - Streaming & storage
      - No bytes before authz; minimum prefix; rate limits; per-yacht concurrency; cancel propagation.
      - Sign storage URLs via document_id only; validate {yacht_id}/ prefix; block traversal.
  - Render/Env
      - Verify ALLOWED_ORIGINS includes https://app.celeste7.ai, https://auth.celeste7.ai, https://api.celeste7.ai.
      - Ensure MASTER and TENANT envs are set (MASTER_SUPABASE_URL/SERVICE_KEY/JWT_SECRET, y*_SUPABASE_URL/SERVICE_KEY).
      - Use apps/api/scripts/ops/check_render_env.py to validate env health.
  - Playwright/E2E
      - Stop including yacht_id in UI or test requests; backend ignores it.
      - Authenticate via MASTER (password grant) in global setup; cache JWT for the session.
      - Ensure required feature flags are ON; incident mode OFF for tests.
      - Use baseURL = https://app.celeste7.ai (or staging), and run E2E/contract suites.

answers; 
  - Auth & Context
      - Do not accept or read yacht_id from payloads/queries; server ignores it.
      - Always use auth = get_authenticated_user(); take auth['yacht_id'] and
        auth['role'] only.
      - Deprecated (remove usages): extract_yacht_id(), extract_role(),
        inject_yacht_context().
  - Action Router (primary guard; RLS is backstop)
      - Register every action with group (READ/MUTATE/SIGNED/ADMIN),
        allowed_roles, strict payload schema (reject unknown fields).
      - Validate ownership for every foreign ID by verifying (id AND yacht_id)
        in TENANT before mutate; return 404 on miss.
      - Require Idempotency-Key for all MUTATE/SIGNED/ADMIN; return 409
        on duplicates; write audit on allow/deny/error with request_id and
        payload_hash.
      - Unsecured handlers are blocked at startup by the registry gate.
  - Error Contract
      - Return structured JSON errors: {status: 'error', error_code, message}
        for validation/not-found/conflict.
      - Use exception handlers to standardize 400/403/404; avoid leaking table/
        view names or tenant aliases.
  - Streaming & Storage
      - No bytes before authz; enforce min prefix; per-user rate limits; per-
        yacht concurrency; cancellation propagation.
      - Cache keys must include yacht_id + user_id + role + query_hash + phase
        with short TTLs.
      - Sign storage URLs by document_id only; server validates {yacht_id}/
        prefix and blocks traversal.
  - Render/Env
      - Verify CORS allowlist includes only our domains (e.g., https://
        app.celeste7.ai).
      - Ensure MASTER/TENANT envs are set: MASTER_SUPABASE_URL/SERVICE_KEY/
        JWT_SECRET, y*_SUPABASE_URL/SERVICE_KEY.
      - Feature flags fail-closed: EMAIL_*, FAULT_LENS_*, FEATURE_CERTIFICATES,
        UI_CERTIFICATES (enable only what your tests need).
      - Validate env health with apps/api/scripts/ops/check_render_env.py
        (prints redacted summary).
  - Playwright/E2E
      - Do not include yacht_id in UI or test requests; backend ignores it.
      - Authenticate via MASTER in global setup; cache JWT for session.
      - Ensure flags ON for tested features; incident mode OFF; streaming tests
        use ≥3-char queries.
      - Base URL: staging/prod as appropriate; example spec to update: /
        Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/tests/e2e/
        work_orders_show_related.spec.ts.
  - CI/Security Gates
      - Security workflow runs handler contract checks, bans request.yacht_id in
        schemas/handlers, runs secret scans (TruffleHog) and SBOM; merges block
        on findings.
      - Contract tests fail if a handler is missing the secure decorator or
        ownership validation.
  - Acceptance Checks (done before PR)
      - No route/handler references request.yacht_id; all reads scoped by
        auth['yacht_id'].
      - All MUTATE/SIGNED/ADMIN require Idempotency-Key; duplicates return 409;
        audit entries exist for allow/deny/error.
      - Ownership validation returns 404 on cross-yacht IDs; no tenant
        enumeration in errors.
      - Streaming emits no bytes pre-authz; limits/cancellation enforced; cache
        keys tenant-safe.
      - Storage signing validates {yacht_id}/ prefix and server-side lookup;
        traversal blocked.
      - E2E/Playwright pass with server-resolved context and enabled feature
        flags.
  - Repo Paths (unchanged)
      - Backend remains under apps/api; use apps/api/middleware/
        auth.py::get_authenticated_user.
      - Action Router and tests live under existing apps/api/action_router/ and
        apps/api/tests/ci/.
  - Workflow
      - Work on feature branches; do not push to main. Open draft PRs with risk
        notes and evidence when ready.
      - Use apps/api/scripts/ops/check_render_env.py and the security pytest
        selection locally before requesting review.
