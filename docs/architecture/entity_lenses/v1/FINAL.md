# Receiving Lens v1 — Consolidated Reference
Status: READY FOR REVIEW
Date: 2026-01-27

Goal: Document → Tests → Code → Verify — backend defines actions, signatures, and RLS; no UI authority.
Lens: Receiving

Executive summary
- Scope: Receiving of invoices, packages, and documents. Users capture/upload images; backend extracts candidates; users review/adjust; confirm with audit/signature where required. Deterministic, no auto‑mutation.
- Security: Deny‑by‑default RLS with canonical helpers; signatures required for financial accept/approve; storage isolation equals DB isolation.
- Data continuity: Extraction is advisory (prepare), edits are explicit, acceptance is auditable; paths and yacht isolation enforced.

What’s included
- PHASE_1_SCOPE.md — actions, roles, prepare/execute semantics, Show Related ties
- PHASE_2_DB_TRUTH.md — tables, FKs, checks, triggers, indexes (DB‑truth grounded)
- PHASE_4_ACTIONS.md — action contracts, gating, request envelopes, search keywords
- PHASE_5_SCENARIOS.md — user journeys (success/failure/edges)
- PHASE_6_SQL_BACKEND.md — SQL patterns, transactions, audit metadata
- PHASE_7_RLS_MATRIX.md — policies and verification queries
- PHASE_8_GAPS_MIGRATIONS.md — blockers, migration plan
- DB_FIELD_CLASSIFICATION.md — REQUIRED/OPTIONAL/BACKEND_AUTO/CONTEXT

Canonical invariants
- Helpers: `public.is_hod(auth.uid())`, `public.is_manager(auth.uid())`, `public.get_user_yacht_id()`
- Signature invariant: `pms_audit_log.signature` NOT NULL; `{}` when not signed; JSON payload for signed (PIN+TOTP)
- Storage isolation:
  - Bucket `documents` for PDFs; path `{yacht_id}/receiving/{receiving_id}/{filename}`
  - Bucket `pms-receiving-images` for photos; path `{yacht_id}/receiving/{receiving_id}/{filename}`
  - Do not prefix `storage_path` with `documents/`
- Error mapping: 400 payload/state, 403 RLS/role, 404 not found/in‑yacht, 409 conflict, 500 fails CI

Acceptance focus
- Step reduction from image → accepted receipt; zero cross‑yacht leakage; signed approvals; complete audit; storage path validity

