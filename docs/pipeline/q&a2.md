# Q&A 2 — Lens‑Specific Guidance

Purpose: concise answers organized by lens/type so parallel engineers can act quickly. Copy intent (roles/RLS/error mapping/storage/audit), not literal actions.

---

## General (All Lenses)

- Q1: Auto‑Population Mapping
  - Location: Implement per‑action mapping in the registry. Add `field_metadata` to `apps/api/action_router/registry.py` with fields: `classification` (REQUIRED|OPTIONAL|BACKEND_AUTO|CONTEXT), `auto_populate_from` (e.g., `equipment`, `query_text`, `auth_context`), and `lookup_required` (bool). Use in prepare/prefill to propose values; re‑validate on execute.
  - Examples:
    - equipment → equipment_id (lookup UUID, yacht‑scoped)
    - symptom → description (direct text)
    - equipment → title prefix (text)

- Q2: Explicit Action Search vs Entity Search
  - Behavior: Return action buttons alongside results in an “Actions” section (SuggestedActions). Do not short‑circuit entity results; no pre‑search bypass.

- Q3: Context Carryover
  - Where to store query text: Keep in frontend state (useCelesteSearch) and pass in orchestration/context to prepare. Server uses it to auto‑fill (e.g., title/description). Always re‑validate on execute.

- Q4: Field Classification in Registry
  - Yes: Extend `ActionDefinition` with `field_metadata` as above. Prepare populates, execute enforces; 400 on missing/ambiguous; never 500.

- Q5: Branch Naming (7 parallel workers)
  - Pattern: `<lens>/<short-desc>[_<id>]` or `agent-<n>/<short-desc>`; start with lens name.
  - Examples: `equipment/auto-populate-status_4637284`, `fault/two-phase-wo-from-fault_v2`, `claude/certificates_modal-flow_4637`.
  - Base: branch from `main` (unless you explicitly depend on another feature branch).

- Q8: Ledger/Notifications (Integration Pattern)
  - Ledger: On success, insert into `pms_audit_log` with `{}` for non‑signed and JSON for signed; never NULL. RLS isolates by `yacht_id`; no FK to tenant users.
  - Notifications: After audit write, call app‑level helper (not DB trigger) to upsert `pms_notifications` with idempotency key and CTA (`cta_action_id`, `cta_payload`). Enforce RLS and role eligibility (use registry `allowed_roles`).

- Entity Resolution (Return Types & Timing)
  - Return UUIDs with labels: responses should carry authoritative IDs (UUIDs) alongside human‑readable labels.
  - Resolve in prepare/prefill; re‑validate on execute: prefill does yacht‑scoped lookups, execute verifies IDs and constraints again; respond 400/404 on client errors, never 500.

- Two‑Phase Mutation Cache (prepare → commit)
  - Preferred: C — database table `pms_staged_mutations` (short TTL, 5–15 min). Stateless, multi‑instance safe, auditable.
    - Key: idempotency_token (server‑generated), action_id, user_id, yacht_id, entity_id?, preview_hash, expires_at.
    - RLS: yacht‑scoped; writes via service role in handler, reads via user context on commit; delete/expire after commit.
  - Optional performance layer: A — Redis cache for hot reads; still persist DB row as source of truth (fallback if Redis absent).
  - Avoid in prod: B — in‑memory cache (acceptable for local/single instance only; not safe across replicas).

---

## Fault Lens

- Q7: Two‑Phase Mutations
  - Use two‑phase when creating downstream entities/cascades or showing non‑trivial defaults.
  - Recommended mapping:
    - report_fault: single‑phase (fast capture; immediate audit).
    - acknowledge_fault: single‑phase.
    - update_fault / mark_fault_false_alarm / close_fault / resolve_fault: single‑phase with validations.
    - create_work_order_from_fault: two‑phase (prepare returns title/equipment/priority + duplicates/warnings; commit creates WO + audit). Not SIGNED by default; only require SIGNED if policy mandates.
  - Contract:
    - Prepare (READ) → `mutation_preview` { proposed_payload, required_fields, warnings, storage_options? }.
    - Commit (MUTATE/SIGNED) → validate again, execute, write audit, return result.

- Handlers and wiring
  - Use `apps/api/handlers/fault_handlers.py`. If legacy refs exist (e.g., `fault_mutation_handlers.py`), consolidate into `fault_handlers.py`.
  - Register actions in `apps/api/action_router/registry.py` with `domain='faults'`, `variant`, `required_fields`, `search_keywords`.
  - Bridge in `apps/api/action_router/dispatchers/internal_dispatcher.py`.
  - Prefill endpoints for two‑phase live in `apps/api/routes/p0_actions_routes.py` (pattern exists).

---

## Equipment Lens

- Q6: Status Extraction
  - Primary: Add `status` entity type (e.g., failed/maintenance/operational) to extraction for `update_equipment_status`.
  - Fallback: Action‑specific keyword mapping if status entity missing.
  - Auto‑populate: equipment_id via yacht‑scoped lookup; status from entity/keywords; title/description from query where applicable.

- Q7: Existing Actions
  - Keep action IDs; add Equipment Lens handlers + richer registry metadata and `field_metadata`.
  - Enhance prepare to auto‑populate; execute re‑validates; 400 for client errors.

---

## Notifications & History (Cross‑Cutting)

- Ledger (History)
  - Table: `pms_audit_log` with NOT NULL `signature` ({} or JSON). Use for entity/user/time‑bounded history under RLS.
- Notifications
  - Table: `pms_notifications` with `(user_id, source, source_id, topic, date_bucket)` idempotency key.
  - Delivery: In‑app first; scheduled digest optional; push later. Always role‑gated and yacht‑scoped.
- CTA: Include `cta_action_id` + minimal `cta_payload` to open ActionModal pre‑filled; never let UI invent fields.

---

## Error Mapping & RLS (Always On)
- Client errors are 400/404 (invalid IDs, missing fields, terminal state); duplicate → 409.
- 500 means fix it; tests fail on any 500.
- All UUID lookups are yacht‑scoped; cross‑yacht is denied.

---

## Parts Lens

- Q1: Action Intent Detection for Parts
  - Status: Some inventory/parts intents exist; confirm in `apps/api/intent_parser.py`. Regardless, explicit action requests are served via `GET /v1/actions/list`.
  - Guidance:
    - Add parts actions to the registry with strong `search_keywords` (e.g., "adjust", "stock", "consume", "shopping", "receive", "count").
    - Do NOT bypass intent parsing; keep entity search + suggestions in parallel. Buttons render in the “Actions” section (SuggestedActions) while results load.
    - If an intent is missing, add lightweight synonyms in intent_parser for telemetry; action surfacing still flows through `search_actions()`.

- Q2: Auto‑Population Flow (Shopping/Consumption/Adjust)
  - Answer: C — Both. Frontend passes focused context (e.g., `part_id`) and backend computes prefill.
    - Prefill location: handler `prepare`/`prefill` computes `quantity_requested` (e.g., `min - on_hand + safety`), default urgency, and labels; all yacht‑scoped.
    - Execute: re‑validate `part_id` and computed values; 400 on invalid/missing.

- Q3: Entity Term Propagation
  - Answer: Pass context via request body.
    - `POST /v1/actions/execute` with `context: { yacht_id, part_id, extracted_entities? }` and `payload` empty (for prefill) or minimal.
    - Avoid URL params for mutations; session state is optional but not authoritative.

- Q4: Field Classification Standard
  - Answer: Machine‑readable in registry (code), markdown optional.
    - Extend `ActionDefinition` with `field_metadata` (classification, auto_populate_from, lookup_required).
    - Use it in prepare to populate and in execute to enforce.

- Q5: Branch Strategy (Parts)
  - Naming: `<lens>/<short-desc>[_<id>]` (e.g., `parts/adjust-stock-prefill_472103`).
  - Base branch: `main`.
  - PR cadence: Prefer 2–3 focused PRs:
    1) DB + registry + handlers + Docker tests
    2) Frontend suggestions + modal + build
    3) Staging CI workflow + required check

- Preliminary Understanding (Confirmed Flow)
  - Explicit request (e.g., "adjust stock"):
    - intent_parser may tag `control_inventory`; UI calls `GET /v1/actions/list?q=adjust+stock&domain=parts`.
    - Response includes `adjust_stock_quantity`; SuggestedActions renders the button.
  - Auto‑population (e.g., “cat fuel filter” → add to shopping list):
    - Extraction identifies part; user focuses the part; clicking the action sends `context` with `part_id` and optional `extracted_entities`.
    - Handler prefill computes `quantity_requested` from `{min, on_hand}`; returns prefilled modal data; user confirms; execute validates and writes audit.
