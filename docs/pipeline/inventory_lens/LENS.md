# Inventory Lens — Zero → Gold via Certificates Template

Intent-first, backend-authoritative Inventory lens built by copying the Certificates template’s guarantees (not literals).

What this adds:
- Backend registry entries for inventory actions (check_stock_level, log_part_usage)
- Action suggestions wired to domain `parts` (frontend already detects part/inventory intent)
- Docker RLS tests (role gating, error mapping)
- Staging CI acceptance with real JWTs

Backend authority (no UI invention):
- Actions: registry defines label, roles, variant, required_fields, domain
- RLS: deny-by-default via yacht_id; helpers is_hod()/is_manager() map to exact role strings
- Storage: no arbitrary paths; inventory actions here do not write storage
- Audit: pms_audit_log.signature is `{}` for non-signed; JSON for signed actions

Actions (domain = `parts`):
- READ: `check_stock_level` — crew and above; required: yacht_id, part_id
- MUTATE: `log_part_usage` — HOD/captain/manager; required: yacht_id, part_id, quantity, usage_reason

Files touched:
- apps/api/action_router/registry.py — added both actions for suggestions (execution stays in p0_actions_routes)
- docs/pipeline/inventory_lens/run_inventory_rls_tests.py — Docker fast loop
- tests/ci/staging_inventory_acceptance.py — Staging acceptance (real JWTs)
- .github/workflows/staging-inventory-acceptance.yml — CI gate

Acceptance proofs:
- Role & CRUD: crew denied mutation; HOD allowed; signed actions N/A here
- Isolation & Storage: tenant REST vs anon invariant; no storage writes for these two actions
- Edge cases: invalid part_id → 404; insufficient stock → 400 (INSUFFICIENT_STOCK)
- Audit invariant: existing inventory mutations (consume/receive/adjust) already follow `{}` vs JSON signature; `log_part_usage` writes standard audit record

How to run (local Docker):
```
docker compose -f docs/pipeline/inventory_lens/docker-compose.test.yml up --build
```

How to run (staging):
```
python tests/ci/staging_inventory_acceptance.py
```

Guardrails (copied intent):
- Backend-only authority for actions; UI renders suggestions + modal from backend
- Deny-by-default RLS; enforce yacht_id from server context
- Exact role strings; registry.allowed_roles == execution-time checks
- Client errors are 4xx; 500 is hard fail

