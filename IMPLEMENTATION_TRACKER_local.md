# CelesteOS Implementation Tracker

**Purpose:** Track all actions, microactions, and situations through the full implementation lifecycle.
**Last Updated:** 2026-01-12

---

## Legend

| Status | Meaning |
|--------|---------|
| - | Not started |
| P | Planning complete |
| D | Detail/spec complete |
| S | DB schema done |
| L | Local test passing |
| I | Implementation complete |
| R | Production ready |

---

## P0 ACTIONS (8 Total)

These are the highest priority actions from `/Users/celeste7/Desktop/actiosn descriptions/`

### Cluster 01: FIX_SOMETHING

| # | Action | Mental Model | Planning | Detail | DB | Local | Impl | Prod | Spec File | Repo Handler | Repo Docs |
|---|--------|--------------|----------|--------|-----|-------|------|------|-----------|--------------|-----------|
| 1.1 | **show_manual_section** | "Get me to the right page, then get out of the way" | P | D | S | - | - | - | `Desktop: cluster_01_FIX_SOMETHING/show_manual_section.md` | `apps/api/handlers/manual_handlers.py` | `docs/actions/ACTION_TO_TABLE_MAP.md` |

**Tables:** `pms_documents`, `pms_document_chunks`, `pms_equipment`
**UX Notes:** READ action only. Opens PDF to specific section via fault code → section mapping. No mutation.

---

### Cluster 02: DO_MAINTENANCE (4 Actions)

| # | Action | Mental Model | Planning | Detail | DB | Local | Impl | Prod | Spec File | Repo Handler | Repo Docs |
|---|--------|--------------|----------|--------|-----|-------|------|------|-----------|--------------|-----------|
| 2.1 | **create_work_order_from_fault** | "A WO is a promise to fix, not a record that something is broken" | P | D | S | L | I | - | `Desktop: cluster_02_DO_MAINTENANCE/create_work_order_from_fault.md` | `apps/api/handlers/work_order_mutation_handlers.py` | `COMPLETE_ACTION_EXECUTION_CATALOG.md:L1200-1400`, `P0_ACTION_CONTRACTS.md` |
| 2.2 | **add_note_to_work_order** | "A breadcrumb for whoever picks up this work next" | P | D | S | L | I | - | `Desktop: cluster_02_DO_MAINTENANCE/add_note_to_work_order.md` | `apps/api/handlers/work_order_mutation_handlers.py` | `COMPLETE_ACTION_EXECUTION_CATALOG.md:L1500-1650` |
| 2.3 | **add_part_to_work_order** | "Writing a shopping list, not taking from stores" | P | D | S | L | I | - | `Desktop: cluster_02_DO_MAINTENANCE/add_part_to_work_order.md` | `apps/api/handlers/work_order_mutation_handlers.py` | `COMPLETE_ACTION_EXECUTION_CATALOG.md:L1700-1850` |
| 2.4 | **mark_work_order_complete** | "Signing your name to say 'I did this work'" | P | D | S | L | I | - | `Desktop: cluster_02_DO_MAINTENANCE/mark_work_order_complete.md` | `apps/api/handlers/work_order_mutation_handlers.py` | `COMPLETE_ACTION_EXECUTION_CATALOG.md:L1900-2100` |

**Tables:** `pms_work_orders`, `pms_work_order_notes`, `pms_work_order_parts`, `pms_faults`, `pms_parts`, `pms_audit_log`

**UX Notes:**
- Pre-fill from fault context (equipment, location, description)
- Duplicate check before form opens
- Preview screen shows all effects before commit
- WO status: CANDIDATE → ACTIVE (on first note) → COMPLETED
- Fault resolution is OPTIONAL checkbox at completion

---

### Cluster 04: INVENTORY_PARTS (2 Actions)

| # | Action | Mental Model | Planning | Detail | DB | Local | Impl | Prod | Spec File | Repo Handler | Repo Docs |
|---|--------|--------------|----------|--------|-----|-------|------|------|-----------|--------------|-----------|
| 4.1 | **check_stock_level** | "Looking in the storeroom, not asking the computer to guess" | P | D | S | - | - | - | `Desktop: cluster_04_INVENTORY_PARTS/check_stock_level.md` | `apps/api/handlers/inventory_handlers.py` | `COMPLETE_ACTION_EXECUTION_CATALOG.md:L2200-2350` |
| 4.2 | **log_part_usage** | "I took this from stores and used it for this job" | P | D | S | - | - | - | `Desktop: cluster_04_INVENTORY_PARTS/log_part_usage.md` | `apps/api/handlers/inventory_handlers.py` | `COMPLETE_ACTION_EXECUTION_CATALOG.md:L2400-2600` |

**Tables:** `pms_parts`, `pms_part_usage`, `pms_work_orders`, `pms_inventory_transactions`

**UX Notes:**
- Stock = received - used (simple ledger math, no ML)
- Negative stock is VISIBLE (data error flag), not blocked
- log_part_usage requires WO link (accountability)
- Adding part to WO ≠ deducting from inventory (only logging does)

---

### Cluster 05: HANDOVER_COMMUNICATION (1 Action)

| # | Action | Mental Model | Planning | Detail | DB | Local | Impl | Prod | Spec File | Repo Handler | Repo Docs |
|---|--------|--------------|----------|--------|-----|-------|------|------|-----------|--------------|-----------|
| 5.1 | **add_to_handover** | "A note to your future self (or the person replacing you)" | P | D | S | L | I | - | `Desktop: cluster_05_HANDOVER_COMMUNICATION/add_to_handover.md` | `apps/api/handlers/handover_handlers.py` | `COMPLETE_ACTION_EXECUTION_CATALOG.md:L2700-2900`, `P0_ACTION_CONTRACTS.md` |

**Tables:** `pms_handover`

**UX Notes:**
- Pre-fill from entity context (fault, equipment, WO, document)
- Categories: `urgent`, `in_progress`, `completed`, `watch`, `fyi`
- No preview screen (lightweight commit)
- System NEVER auto-adds to handover (human decides importance)

---

## SITUATIONS (3 Types)

Situations are **event-driven contextual views** that aggregate related data. They differ from actions in:
- Situations are temporary, focused, transactional
- Actions are point mutations
- Situations have STATE MACHINES (IDLE → CANDIDATE → ACTIVE → COMMITTED)

### Situation: RECEIVING

| Aspect | Status | Spec File | Repo Implementation | Repo Docs |
|--------|--------|-----------|---------------------|-----------|
| Planning | P | `Desktop: reference/# Receiving — Situational Active State.md` | - | `SITUATIONAL_STATE_ARCHITECTURE_V4.md:L400-600` |
| Detail | D | `Desktop: reference/receival inventory thought process.md` | - | - |
| DB Schema | S | - | `supabase/migrations/*` | `DATABASE_SCHEMA_EXECUTION_SPEC.md` |
| Local Test | - | - | - | - |
| Implementation | - | - | `apps/api/handlers/receiving_handlers.py` (TODO) | - |
| Production | - | - | - | - |

**Tables:** `pms_receiving_sessions`, `pms_receiving_lines`, `pms_parts`, `pms_purchase_orders`, `pms_inventory_transactions`

**State Machine:**
```
IDLE → CANDIDATE → ACTIVE (Receiving Session) → REVIEW → COMMITTED
```

**Core Doctrine:**
- **Checkbox = truth** (if not ticked, it didn't happen)
- No confidence scores, no auto-receiving
- OCR/camera may prefill rows but NEVER auto-check
- Review screen shows all effects before commit

**UX Differences from Actions:**
- Bulk affordances (tick-tick-tick multiple items)
- Temporary/modal (get in, reconcile, get out)
- Event-driven entry (delivery arrives)
- Discrepancy handling (Missing/Damaged/Incorrect)
- Immediate installation flow (skip inventory option)

---

### Situation: SHOPPING LIST

| Aspect | Status | Spec File | Repo Implementation | Repo Docs |
|--------|--------|-----------|---------------------|-----------|
| Planning | P | `Desktop: Shopping List — Situational Active State.md` | - | `SITUATIONAL_STATE_ARCHITECTURE_V4.md:L200-400` |
| Detail | D | - | - | `docs/micro-actions/MICRO_ACTION_REGISTRY.md` |
| DB Schema | S | - | `supabase/migrations/*` | `DATABASE_SCHEMA_EXECUTION_SPEC_PART3.md` |
| Local Test | - | - | - | - |
| Implementation | - | - | `apps/api/handlers/purchasing_mutation_handlers.py` | - |
| Production | - | - | - | - |

**Tables:** `pms_shopping_list_items`, `pms_purchase_orders`, `pms_parts`, `pms_suppliers`

**State Machine (per item):**
```
CANDIDATE → ACTIVE (UNDER_REVIEW) → COMMITTED (ORDERED) → PARTIALLY_FULFILLED → FULFILLED/INSTALLED/MISSING
```

**Core Doctrine:**
- "Capture everywhere. Decide centrally."
- Shopping List is the ONLY gateway to procurement
- Nothing ordered until human approves
- Items created from reality (inventory low, WO usage, receiving discrepancy)

**UX Differences from Actions:**
- Item-level state tracking
- Role-based surfaces (Crew captures, HOD approves, Logistics orders)
- Additive capture points (Inventory, WO, Receiving, Manual)
- Candidate Parts vs Known Parts distinction

---

### Situation: FINANCE

| Aspect | Status | Spec File | Repo Implementation | Repo Docs |
|--------|--------|-----------|---------------------|-----------|
| Planning | P | `Desktop: Finance — Situational Active State.md` | - | `SITUATIONAL_STATE_ARCHITECTURE_V4.md:L600-800` |
| Detail | D | - | - | - |
| DB Schema | - | - | - | `DATABASE_SCHEMA_EXECUTION_SPEC_PART3.md` |
| Local Test | - | - | - | - |
| Implementation | - | - | - | - |
| Production | - | - | - | - |

**Tables:** `pms_shopping_list_items`, `pms_purchase_orders`, `pms_receiving_sessions`, `pms_inventory_transactions`

**State Machine:**
```
IDLE → CANDIDATE → ACTIVE (Under Review) → COMMITTED (Ordered) → PARTIALLY_FULFILLED → FULFILLED
```

**Core Doctrine:**
- Finance is event-driven, not form-driven
- Finance = shadow of real work (if not used/received/installed, finance doesn't exist)
- Nothing "spent" until received or installed
- Budgets are soft constraints, not blockers

**UX Differences from Actions:**
- Finance is NOT a separate surface—it flows through Shopping List
- Spend posted only on receiving/install events
- No invoice payment, payroll, tax handling (explicit non-goals)
- Audit trail links every spend to operational event

---

## CAMERA FEATURE (Special)

| Aspect | Status | Spec File | Repo Implementation | Repo Docs |
|--------|--------|-----------|---------------------|-----------|
| Planning | P | `Desktop: # Camera Feature — Inventory Scan & Rece.md` | - | - |
| Abuse Resistance | P | `Desktop: users_breaking_camera.md` | - | - |
| DB Schema | - | - | - | - |
| Local Test | - | - | - | - |
| Implementation | - | - | Cloud_DMG repo (separate) | - |
| Production | - | - | - | - |

**Pipeline:** Capture → Intake Gate → Classification → OCR/Table Extraction → Match to Order → Human Verification → Commit

**Core Doctrine:**
- Camera is assistant, not authority
- Precision > Speed > Cost
- Use OCR + heuristics first, LLM only for normalization
- Quarantine invalid uploads (random photos, blurry shots)

**Abuse Resistance:**
- Intake gate rejects non-document images
- Rate limiting per user
- Hash-based duplicate detection
- "Confirm count" prompt if 30 items ticked in 5 seconds

---

## CROSS-REFERENCE: Desktop Specs → Repo Files

| Desktop Spec | Primary Repo Doc | Handler File | Tables |
|--------------|------------------|--------------|--------|
| `README.md` | `docs/ONBOARDING.md`, `P0_ACTION_CONTRACTS.md` | - | - |
| `cluster_01_FIX_SOMETHING/show_manual_section.md` | `COMPLETE_ACTION_EXECUTION_CATALOG.md` | `manual_handlers.py` | `pms_documents`, `pms_document_chunks` |
| `cluster_02_DO_MAINTENANCE/create_work_order_from_fault.md` | `COMPLETE_ACTION_EXECUTION_CATALOG.md`, `ACTION_HANDLER_IMPLEMENTATION_STATUS.md` | `work_order_mutation_handlers.py` | `pms_work_orders`, `pms_faults` |
| `cluster_02_DO_MAINTENANCE/add_note_to_work_order.md` | `COMPLETE_ACTION_EXECUTION_CATALOG.md` | `work_order_mutation_handlers.py` | `pms_work_order_notes` |
| `cluster_02_DO_MAINTENANCE/add_part_to_work_order.md` | `COMPLETE_ACTION_EXECUTION_CATALOG.md` | `work_order_mutation_handlers.py` | `pms_work_order_parts`, `pms_parts` |
| `cluster_02_DO_MAINTENANCE/mark_work_order_complete.md` | `COMPLETE_ACTION_EXECUTION_CATALOG.md` | `work_order_mutation_handlers.py` | `pms_work_orders`, `pms_audit_log` |
| `cluster_04_INVENTORY_PARTS/check_stock_level.md` | `COMPLETE_ACTION_EXECUTION_CATALOG.md` | `inventory_handlers.py` | `pms_parts`, `pms_inventory_transactions` |
| `cluster_04_INVENTORY_PARTS/log_part_usage.md` | `COMPLETE_ACTION_EXECUTION_CATALOG.md` | `inventory_handlers.py` | `pms_part_usage`, `pms_parts` |
| `cluster_05_HANDOVER_COMMUNICATION/add_to_handover.md` | `COMPLETE_ACTION_EXECUTION_CATALOG.md`, `P0_ACTION_CONTRACTS.md` | `handover_handlers.py` | `pms_handover` |
| `Finance — Situational Active State.md` | `SITUATIONAL_STATE_ARCHITECTURE_V4.md` | `purchasing_mutation_handlers.py` | `pms_shopping_list_items`, `pms_purchase_orders` |
| `Shopping List — Situational Active State.md` | `SITUATIONAL_STATE_ARCHITECTURE_V4.md` | `purchasing_mutation_handlers.py` | `pms_shopping_list_items` |
| `reference/# Receiving — Situational Active State.md` | `SITUATIONAL_STATE_ARCHITECTURE_V4.md` | TODO: `receiving_handlers.py` | `pms_receiving_sessions`, `pms_receiving_lines` |
| `reference/receival inventory thought process.md` | - | - | - |
| `# Camera Feature — Inventory Scan & Rece.md` | - | Cloud_DMG repo | - |
| `users_breaking_camera.md` | - | Cloud_DMG repo | - |

---

## CRITICAL IMPLEMENTATION NOTES

### 1. Table Names Have `pms_` Prefix in Production

All production tables use `pms_` prefix:
- `pms_work_orders` (not `work_orders`)
- `pms_faults` (not `faults`)
- `pms_parts` (not `parts`)
- `pms_handover` (not `handover`)

**Handler files must use `pms_` prefix for production compatibility.**

### 2. Handover Categories (DB Constraint)

Only these values allowed:
- `urgent`
- `in_progress`
- `completed`
- `watch`
- `fyi`

NOT: `ongoing_fault`, `work_in_progress`, `important_info`, `pending_action`

### 3. Core Doctrine (Never Violate)

From Desktop README.md:
1. **Simplicity Is a Safety Feature**
2. **Accountability Over Speed**
3. **Explicit Control Always**
4. **Human-in-the-Loop Is Non-Negotiable**
5. **No State Change Without Record**
6. **Boring Is Correct**

> "If a human didn't click it, it doesn't happen."

### 4. What We Do NOT Do (Design Law)

- No behavioral tracking (time-on-page, scroll depth, copied text)
- No confidence scores
- No ML predictions of user intent
- No proactive nudges or suggestions
- No auto-triggering based on user behavior
- No historical pattern matching for recommendations

---

## NEXT STEPS

1. **Fix handler table names** - Revert to `pms_` prefix for production
2. **Implement receiving_handlers.py** - Based on Receiving Situation spec
3. **Implement shopping_list_handlers.py** - Based on Shopping List Situation spec
4. **Test all P0 actions locally** - Using prove_prod_parity.sh
5. **Deploy to production** - After local validation

---

**This document is the source of truth for implementation status.**
**Update as work progresses.**
