# NEXT ENGINEER HANDOFF (Read this first)

## Mission
Your job is to ship features fast **without** creating cross-yacht data disclosure.
Assume:
- clients are untrusted,
- devices are compromisable,
- humans make mistakes,
- credentials can leak,
- and bugs happen.

The system must be safe even when one layer fails.

---

## What exists today (mental model)
### Control plane (MASTER)
- Authentication (GoTrue `auth.users`)
- Membership / routing metadata (currently `user_accounts`, should evolve into `memberships`)
- Fleet registry (`fleet_registry`) with tenant alias / routing

### Data plane (TENANT)
- PMS tables `pms_*` (yacht-scoped by `yacht_id`)
- Role bindings (`auth_users_roles`) — **authoritative** for yacht roles
- Profiles (`auth_users_profiles`) — mirrors MASTER user_id for joins/helpers
- Storage policies that require key prefix `{yacht_id}/...`

### Execution boundary (Render Action Router)
- Middleware verifies MASTER JWT
- Server resolves membership + yacht context
- Server resolves tenant role
- Action Router runs validated intents and writes audit

---

## The 10 invariants (if you break one, you can cause a breach)
1) Tenant context is **server-resolved**, never trusted from payload.
2) Every read is yacht-scoped in code (`WHERE yacht_id = ctx.yacht_id`) even if RLS exists.
3) Every write sets `yacht_id` from `ctx`, not payload.
4) Every foreign ID in payload must be ownership-validated (select by `id AND yacht_id`).
5) No streaming bytes are sent until authz is completed (JWT→membership→role→freeze).
6) Clients must never directly access TENANT PostgREST with meaningful privileges.
7) Cache keys must include `yacht_id + user_id + role + query_hash` (no exceptions).
8) Signed URL generation must validate yacht key prefix before issuing.
9) Audit must be written for every action outcome (allow/deny/error).
10) Revocation must take effect within a bounded TTL, and caches must respect it.

Print these. Enforce them in code review.

---

## Where engineers usually cause leaks (highest-risk areas)
- Service role writes (bypasses RLS)
- Streaming search (metadata leakage + output before authz)
- Caching (key collisions / cross-tenant cache bleed)
- Storage signed URL generation (wrong prefix = instant leak)
- Provisioning/role-change flows (privilege escalation)

---

## What you need to add (missing production pieces)
- A canonical MASTER `memberships` object (status, expiry, approval fields)
- Formal Invite→Accept→Provision workflow (no manual DB edits)
- Tenant kill switch + global incident mode
- Streaming search hardening (min prefix, debounce, cancellation, two-phase)
- Central ownership validation library used by every handler
- Evidence/runbooks for SOC2/ISO: access reviews, incident drills, change logs

See:
- `02_INVARIANTS_DO_NOT_BREAK.md`
- `03_HOW_TO_ADD_A_NEW_ACTION.md`
- `04_ACCESS_LIFECYCLE_IMPLEMENTATION.md`
- `05_STREAMING_SEARCH_IMPLEMENTATION_GUIDE.md`
- `07_CACHE_KEY_AND_INVALIDATION_SPEC.md`
- `08_PRODUCTION_RUNBOOKS.md`
