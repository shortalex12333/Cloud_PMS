# Fault Lens — Completion Summary (Implementation Checklist)

Gate: Document → Tests → Code → Verify (deny‑by‑default; backend authority)

Registry
- [x] Actions have domain=faults, variant set, search_keywords coherent
- [x] allowed_roles per canon: crew read‑only; HOD (chief_engineer, chief_officer) and captain mutate; manager only where explicit
- [x] Storage: add_fault_photo uses bucket `pms-discrepancy-photos` with safe prefixes

Handlers
- [ ] Severity mapping ("medium"→"minor") before writes
- [ ] Required fields enforced with 400 and clear details
- [ ] Illegal transitions return 400/409; no 500 masking client errors
- [ ] Signed WO creation enforces canonical signature payload keys

RLS & Migrations
- [ ] pms_faults INSERT/UPDATE policies using `is_hod()` and `get_user_yacht_id()`
- [ ] Storage policies for `pms-discrepancy-photos` (upload, read, delete by role)
- [ ] Optional transition trigger to enforce status graph

Ledger (Audit)
- [ ] Every mutation writes one row; signature NOT NULL ({} for non‑signed)
- [ ] Metadata includes {source:'lens', lens:'faults', action, entity_type, entity_id, session_id, ip_address}

Suggestions & UX
- [x] `GET /v1/actions/list` returns Fault actions with prefill for HOD; CREW sees no MUTATE/SIGNED
- [ ] Avoid low‑fidelity prompts during active fault flow (handover suggestions deferred)

Tests
- [x] Docker: HOD report 200; CREW denied; invalid update 4xx; storage path preview safe
- [x] Staging: real JWTs; suggestions correct; signed action 400 without signature

CI/Env
- [ ] Add staging workflow secrets for Fault acceptance
- [ ] Confirm DEFAULT_YACHT_CODE and TENANT_SUPABASE_* parity

Sign‑off Criteria
- All checkboxes green; Docker and Staging acceptance passing; no 500s
- RLS verified with real JWTs; cross‑yacht leakage = 0 (DB + storage)

