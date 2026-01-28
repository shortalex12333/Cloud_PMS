Work Order Lens — Zero → Gold
=============================

Goal: Copy the Certificates lens template intent (roles/RLS/error mapping/storage/audit), not the literal actions. Backend defines actions, signatures, RLS; UI has no authority.

What’s Implemented
- Action list endpoint: `apps/api/routes/p0_actions_routes.py` (`GET /v1/actions/list`) now returns work_orders actions with proper domain/variants.
- Registry metadata: `apps/api/action_router/registry.py`
  - work_orders actions have `domain='work_orders'`, `variant`, `search_keywords`, and exact roles (`crew`, `chief_engineer`, `captain`, `manager`).
  - `create_work_order_from_fault` marked SIGNED and includes `signature` in `required_fields`.
  - Storage semantics for `add_work_order_photo` with per‑yacht paths `{yacht_id}/work_orders/{work_order_id}/{filename}`.
- Execute path: `create_work_order_from_fault` execution added to `p0_actions_routes.execute` with signature check.
- Frontend integration: `apps/web/src/hooks/useCelesteSearch.ts` detects work order intent and fetches `domain=work_orders` suggestions; UI renders backend‑provided buttons.
- Docker tests: `tests/docker/run_work_orders_action_list_tests.py` verifies role gating and storage options for work_orders domain.

Roles & RLS (Copying Intent)
- CREW: no mutations; READ only.
- HOD (chief_engineer): create/update/assign/start/close.
- Captain/Manager: all HOD actions; manager‑only where applicable; SIGNED actions (e.g., create from fault) require `signature`.

Non‑negotiables
- Backend authority only: front end never invents actions/fields.
- RLS deny‑by‑default with tenant isolation via `public.get_user_yacht_id()`.
- Storage isolation: bucket `documents`; safe prefixes under `{yacht_id}/work_orders/…`.
- Error mapping: 400/404 for client errors; 500 treated as failure in tests.

Quick Checks
- HOD suggestions: `GET /v1/actions/list?q=create+work+order+from+fault&domain=work_orders` includes `create_work_order_from_fault`.
- CREW suggestions: `GET /v1/actions/list?domain=work_orders` returns no `MUTATE`/`SIGNED` variants.
- Storage preview: `GET /v1/actions/list?q=add+work+order+photo&domain=work_orders` includes `storage_options` with `{yacht_id}/work_orders/…`.

Next
- Expand Docker tests to cover a minimal execution happy path (create‑from‑fault with mock/signature) as data setup allows.
- Stage CI: mirror certificates’ minimal acceptance with role‑gated list and one 200 mutation.

