Acceptance Matrix (Docker & Staging)
====================================

Legend: PASS (expected code) → test asserts exact HTTP status; 500 is always a failure.

Role & CRUD (Why: exercise roles and deny-by-default)
- CREW create → 403 (deny)
- HOD create → 200 (allow)
- HOD update → 200 (allow)
- HOD supersede → 403 (deny)
- Captain/Manager supersede (signed) → 200 (allow)

Isolation & Storage (Why: yacht isolation and safe storage prefixes)
- Anon REST read (tenant) → [] or 401/403
- Service-role REST read (tenant) → rows exist
- Cross-yacht path (open_document with other yacht prefix) → 400/403

Edge Cases (Why: client error mapping must be 4xx; 500 is failure)
- Invalid document_id (link_document_to_certificate) → 400/404 (client error)
- Duplicate certificate_number → 409 (unique index)
- Date invalid (expiry < issue) → 400
- Double supersede → 400/409 (terminal state)
- Update non‑existent → 404

Audit Invariant (Why: immutable truth and signature semantics)
- Non‑signed actions → signature = {}
- Supersede (signed) → signature is non‑null JSON with keys (signed_at, user_id, role_at_signing, signature_type, signature_hash)

Execution
- Docker (Why: fast loop, hermetic): all above validated in `tests/docker/run_rls_tests.py`
- Staging CI (Why: production parity, real JWTs): minimal gate (invalid doc 400/404 + update 200) in `tests/ci/staging_certificates_acceptance.py`

Template note: For the next lens, keep the same categories and expected statuses, but replace the concrete actions with your domain’s actions (copy intent, not literal endpoints).
