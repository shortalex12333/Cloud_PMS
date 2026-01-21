# AGENT_BUILD_ORDER.md

This document defines the mandatory execution order for an autonomous agent implementing the Situational Continuity Layer.

Deviation from this order risks architectural drift, regressions, or non-deterministic behavior.

---

## Phase 1 — Read and Lock Invariants

Agent must read fully and treat as immutable:

* /00_foundation/00_README.md
* /00_foundation/01_CORE_PRINCIPLES.md
* /00_foundation/02_NON_NEGOTIABLE_RULES.md
* /40_constraints/40_DETERMINISM_AND_PERF.md
* /40_constraints/41_NO_VECTOR_NO_LLM_ESCALATION.md
* /60_audit/61_LEDGER_RULES.md
* /80_validation/82_REGRESSION_TRAPS.md

No code may be written before this phase is complete.

---

## Phase 2 — Internalize the Formal Model

Agent must build an internal model from:

* /20_model/20_SITUATION_MODEL.md
* /20_model/21_VIEW_STATE_MODEL.md
* /20_model/22_NAVIGATION_STATE_MACHINE.md
* /schemas/situation_state.schema.json
* /schemas/view_state.schema.json

Agent must be able to describe:

* Situation lifecycle
* Anchor replacement rules
* Stack push/pop behavior
* Termination conditions

---

## Phase 3 — Implement Backend Contracts

Agent must implement backend logic strictly following:

* /schemas/related_request.schema.json
* /schemas/related_response.schema.json
* /schemas/add_related_request.schema.json
* /schemas/add_related_response.schema.json
* /30_contracts/30_DATABASE_SCHEMA_ASSUMPTIONS.md
* /30_contracts/31_BACKEND_API_CONTRACT.md

Backend responsibilities:

* Deterministic querying
* Permission enforcement
* Domain grouping
* Explicit relation persistence
* No inference, no ranking, no learning

---

## Phase 4 — Implement Frontend State and Navigation

Agent must implement frontend logic strictly following:

* /30_contracts/32_FRONTEND_STATE_CONTRACT.md
* /20_model/22_NAVIGATION_STATE_MACHINE.md

Frontend responsibilities:

* Single linear back/forward stack
* Viewer vs Related view states
* No search re-entry
* No implicit state persistence
* Stack destruction on refresh or home return

---

## Phase 5 — Implement Audit and Ledger Writes

Agent must implement audit writes strictly following:

* /60_audit/60_EVENT_NAMES_AND_PAYLOADS.md
* /60_audit/61_LEDGER_RULES.md

Only the following events may be written:

* artefact_opened
* relation_added
* situation_ended

No UI exploration events are permitted.

---

## Phase 6 — Validate Against Examples

Agent must validate behavior against all example scenarios:

* /examples/ex01_manual_to_related_to_inventory.md
* /examples/ex02_inventory_to_related_to_work_order.md
* /examples/ex03_empty_related.md
* /examples/ex04_permission_denied_one_domain.md
* /examples/ex05_partial_domain_return.md
* /examples/ex06_add_related_user_action.md
* /examples/ex07_navigation_stack_limit.md
* /examples/ex08_situation_refresh_behavior.md
* /examples/ex09_handover_view_within_situation.md

All flows must match exactly.

---

## Phase 7 — Run Acceptance Tests

Agent must satisfy all conditions in:

* /80_validation/80_DONE_DEFINITION.md
* /80_validation/81_ACCEPTANCE_TESTS.md

Any failing test blocks completion.

---

## Phase 8 — Regression Scan

Before declaring completion, agent must verify:

* No forbidden behavior from /82_REGRESSION_TRAPS.md exists
* No additional events are logged
* No intelligence creep is present
* No persistence beyond situation lifetime exists

---

## Completion Rule

Implementation is complete only when every phase above is satisfied in order.

Skipping a phase invalidates the build.
