Guardrails (Non‑Negotiable)
===========================

- Backend authority: frontend renders actions blindly; no UI invention.
- RLS everywhere: yacht_id from public.get_user_yacht_id(); deny by default.
- Roles: crew (deny), HOD (create/update/link), captain/manager (supersede signed).
- Signature invariant: pms_audit_log.signature NOT NULL; {} for non‑signed; JSON for signed.
- Storage isolation: documents bucket; path {yacht_id}/certificates/{certificate_id}/{filename}.
- No audit FK to TENANT auth.users: drop FK (users live in MASTER).
- Staging acceptance must pass with real JWTs before merge/deploy.

