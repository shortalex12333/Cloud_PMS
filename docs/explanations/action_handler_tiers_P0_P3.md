# Action Handler Tiers: P0, P1, P2, P3

> **Audience:** Anyone working on the CelesteOS backend — engineers, architects, or non-technical leads who need to understand how actions flow through the system.

---

## What are P0–P3?

They are **priority tiers** — a classification system that groups the 207 registered actions by complexity and risk. P0 is the entry point. P1–P3 are implementation layers grouped by what kind of work they do.

This is **not** a version system. P0 does not replace P1. They all run together.

---

## The Full Picture

```
User clicks "Create Work Order"
        │
        ▼
┌──────────────────────────────────────────┐
│  P0 — routes/p0_actions_routes.py        │
│  The single HTTP entry point.            │
│  POST /v1/actions/execute                │
│  Validates JWT, checks role, dispatches. │
└────────────────┬─────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────┐
│  routes/handlers/__init__.py             │
│  The dispatch table. Maps action names   │
│  to handler functions. 207 entries.      │
│                                          │
│  Two sources:                            │
│  ├─ Phase 4 native handlers (136)        │
│  └─ Internal adapter → legacy tiers (71) │
└────────┬──────────────────┬──────────────┘
         │                  │
    Phase 4 native     Legacy path
         │                  │
         ▼                  ▼
┌─────────────────┐  ┌──────────────────────┐
│ routes/handlers/ │  │ internal_dispatcher   │
│ *_handler.py     │  │ Routes to P1/P2/P3   │
│ (thin dispatch)  │  │ handler classes       │
└────────┬────────┘  └───┬──────┬──────┬────┘
         │               │      │      │
         ▼               ▼      ▼      ▼
┌─────────────────────────────────────────┐
│  handlers/ (domain business logic)      │
│  equipment_handlers.py                  │
│  work_order_mutation_handlers.py        │
│  certificate_handlers.py                │
│  p1_compliance_handlers.py              │
│  p2_mutation_light_handlers.py          │
│  p3_read_only_handlers.py              │
│  ... (29 modules total)                 │
└─────────────────────────────────────────┘
```

---

## Tier Definitions

### P0 — Entry Point

| | |
|---|---|
| **File** | `routes/p0_actions_routes.py` |
| **Purpose** | The only HTTP route for action execution |
| **Endpoints** | `POST /v1/actions/execute`, `GET /v1/actions/{name}/prefill`, `POST /v1/actions/{name}/preview` |
| **What it does** | Validates JWT, extracts user context (role, yacht_id), looks up the action in the dispatch table, calls the handler, returns the result |

P0 is a router, not a handler. It doesn't contain business logic. Every action — all 207 — enters through P0.

---

### P1 — Compliance & Purchasing

| | |
|---|---|
| **Files** | `handlers/p1_compliance_handlers.py`, `handlers/p1_purchasing_handlers.py` |
| **Actions** | 6 total |
| **Risk level** | High — these touch regulated data or money |
| **Examples** | `update_hours_of_rest`, `log_delivery_received`, `update_purchase_status`, `cancel_po` |

P1 actions affect records that have legal or financial implications. Hours of rest is regulated by MLC 2006. Purchase orders affect budgets. These handlers have extra validation and audit logging.

---

### P2 — Mutation Light

| | |
|---|---|
| **File** | `handlers/p2_mutation_light_handlers.py` |
| **Actions** | 20 total |
| **Risk level** | Low — simple data writes |
| **Examples** | `add_fault_note`, `add_work_order_photo`, `assign_work_order`, `add_equipment_note`, `edit_handover_section`, `add_document_to_handover` |

P2 actions add or update small pieces of data on an existing entity. They don't create new entities, don't affect compliance records, and don't involve money. A note, a photo, an assignment.

---

### P3 — Read Only

| | |
|---|---|
| **File** | `handlers/p3_read_only_handlers.py` |
| **Actions** | 30 total |
| **Risk level** | Zero — no data mutation |
| **Examples** | `view_fault_history`, `suggest_parts`, `view_work_order_checklist`, `view_equipment_details`, `view_equipment_parts`, `view_linked_faults` |

P3 actions query and return data. They never write. They're used for detail views, history lookups, part suggestions, and checklist displays.

---

## Phase 4 Migration (Current State)

The system is migrating from the legacy P1–P3 class-based handlers to a newer "Phase 4" pattern. Both run in parallel.

| Layer | Location | Pattern | Actions | Status |
|-------|----------|---------|---------|--------|
| Phase 4 native | `routes/handlers/*_handler.py` | Thin async functions, one per action | ~136 | Active — preferred for new work |
| Legacy adapted | `routes/handlers/internal_adapter.py` → `handlers/p1,p2,p3_*.py` | Class-based handler instances | ~71 | Active — being migrated to Phase 4 |

**When writing new actions:** Use the Phase 4 pattern. Add a function to the appropriate `routes/handlers/*_handler.py` file, register it in that file's `HANDLERS` dict, and it will automatically be included in the dispatch table.

**When maintaining existing actions:** If the action is in `internal_dispatcher.py`, it's legacy. It works, don't break it, but consider migrating it to Phase 4 when you're already touching that code.

---

## Key Files

| File | Role |
|------|------|
| `routes/p0_actions_routes.py` | HTTP entry point — all 207 actions enter here |
| `routes/handlers/__init__.py` | Dispatch table — merges Phase 4 + adapted handlers |
| `routes/handlers/*_handler.py` (16 files) | Phase 4 native handlers (the new pattern) |
| `routes/handlers/internal_adapter.py` | Bridge: adapts legacy P1–P3 handlers to Phase 4 calling convention |
| `action_router/dispatchers/internal_dispatcher.py` | Legacy dispatcher — routes to P1/P2/P3 class instances |
| `action_router/registry.py` | Registry — 207 `ActionDefinition` entries with metadata |
| `handlers/p1_compliance_handlers.py` | P1 compliance logic |
| `handlers/p1_purchasing_handlers.py` | P1 purchasing logic |
| `handlers/p2_mutation_light_handlers.py` | P2 mutation logic |
| `handlers/p3_read_only_handlers.py` | P3 read-only logic |

---

## FAQs

**Why not rename P0–P3 to something clearer?**
Renaming would require updating 200+ action registrations, 3,500+ lines in `internal_dispatcher.py`, all imports, and all tests. The risk outweighs the benefit. This document serves as the reference instead.

**Why are there two handler directories?**
`routes/handlers/` = dispatch layer (maps action names to functions).
`handlers/` = business logic layer (the actual implementation).
Dispatch calls logic. Both are required. They are not duplicates.

**Can I delete P1/P2/P3 files?**
No. 71 actions still route through them via `internal_adapter.py`. They will be removable once all 71 are migrated to Phase 4 native handlers.

**How do I know which tier an action is in?**
Search `internal_dispatcher.py` for the action name. The comment block next to it will say "P1 Compliance", "P2 Mutation Light", or "P3 Read-Only". If it's not there, it's Phase 4 native — check `routes/handlers/`.
