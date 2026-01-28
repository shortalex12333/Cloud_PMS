Context: What We’re Building & Why
==================================

Celeste is a query‑driven operating surface over operational data. There are no pages or dashboards — one search bar drives intent → focus → act. Actions are small, auditable changes to reality (micro‑actions), defined by the backend, permissioned by RLS and roles, and recorded in an immutable ledger.

Why This Works (vs Traditional)
- Intent‑first: users don’t navigate; they express intent once. The UI reconfigures around the focused entity.
- Deterministic triggers: system reacts from state, not “AI guesses”.
- Single source of truth: production DB + RLS; signatures for critical actions.
- Immutable history: pms_audit_log answers “what happened, who, when, why”.

Success Criteria
- Every lens is DB‑grounded and executable (no aspirational actions).
- RLS and roles are correct by construction (deny by default; allow strictly by is_hod()/is_manager()).
- Storage, FKs, and buckets are safe by default (tenant isolation and per‑yacht pathing).
- Tests prove truth (Docker fast loop; staging CI with real JWTs; prod smoke only).

