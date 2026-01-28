# Entity Lens Factory Pipeline

**Status**: MASTER CONTROL DOCUMENT
**Template**: `fault_lens_v5_FINAL.md`
**Created**: 2026-01-24

---

## GLOBAL RULES (Agent must acknowledge before starting)

### Rule 1: DB Truth Beats Theory
- All schema, RLS, triggers, enums, helpers must come from `db_truth_snapshot`
- If missing → mark **BLOCKER**, do not invent

### Rule 2: Query-First Doctrine
- No dashboards
- No ambient buttons
- No navigation
- Actions only appear when:
  - User query contains action intent, OR
  - A single entity is focused

### Rule 3: WO-First Operational Rule
- Work happens in Work Orders
- Other lenses are read-heavy unless explicitly proven otherwise

### Rule 4: Ledger is Derived
- Ledger UI is read-only, derived from `pms_audit_log`
- No "ledger writes" allowed in docs

### Rule 5: Every Claim Maps to Code
- If it can't be tied to SQL, RLS, or handler → label `FUTURE` / `PROPOSED`

---

## INPUTS REQUIRED BEFORE EACH LENS

Agent must confirm availability of:

| Input | Location | Status |
|-------|----------|--------|
| `db_truth_snapshot.md` | `/Volumes/Backup/CELESTE/database_schema.txt` | Required |
| `fault_lens_v5_FINAL.md` | `docs/architecture/entity_lenses/` | Gold DB template |
| `LENS_BUILDER_OPERATING_PROCEDURE.md` | `docs/architecture/entity_lenses/` | Operating rules |
| Current migrations folder | `supabase/migrations/` | Required |
| RLS policies (pg_policies) | Introspection output | Required |

> **If any are missing → STOP AND ASK.**

---

## THE 10 LENSES TO BUILD

| # | Lens Name | Type | Primary Table | Estimated Complexity |
|---|-----------|------|---------------|---------------------|
| 1 | **Work Order** | Operational | `pms_work_orders` | High (backbone) |
| 2 | **Equipment** | Read-heavy | `pms_equipment` | Medium |
| 3 | **Inventory Item** | Read + Write | `pms_inventory_items` | Medium |
| 4 | **Part** | Read-heavy | `pms_parts` | Medium |
| 5 | **Receiving** | Operational | `pms_receiving_events` | High |
| 6 | **Shopping List** | Operational | `pms_shopping_list_items` | Medium |
| 7 | **Document** | Read-only | `doc_metadata` | Low |
| 8 | **Crew** | Read-heavy | `auth_users_profiles` | Low |
| 9 | **Certificate** | Read + Alert | `pms_certificates` | Medium |
| 10 | **Finance/Transaction** | Read-only | `pms_finance_transactions` | Medium |

---

## THE 8-PHASE PIPELINE (Per Lens)

Each lens goes through ALL 8 phases before moving to the next lens.

---

# LENS 1: WORK ORDER

## PHASE 1 — Scope & Doctrine Lock
**Output**: `work_order_lens_PHASE_1_SCOPE.md`

| Task | Description | Status |
|------|-------------|--------|
| 1.1 | Define what this lens IS | [ ] |
| 1.2 | Define what this lens is NOT | [ ] |
| 1.3 | Classify: Read-only / Write-through / Operational | [ ] |
| 1.4 | Define allowed entry paths (query patterns) | [ ] |
| 1.5 | Define escape hatches (if any) | [ ] |
| 1.6 | Lock doctrine statement | [ ] |
| 1.7 | Review & freeze | [ ] |
| 1.8 | **GATE**: Scope approved? | [ ] |

## PHASE 2 — DB Truth Grounding
**Output**: `work_order_lens_PHASE_2_DB_TRUTH.md`

| Task | Description | Status |
|------|-------------|--------|
| 2.1 | List all tables involved (from snapshot) | [ ] |
| 2.2 | Extract columns, types, nullable, defaults | [ ] |
| 2.3 | Extract constraints (FK, CHECK, UNIQUE) | [ ] |
| 2.4 | Extract triggers | [ ] |
| 2.5 | Extract enums used | [ ] |
| 2.6 | Extract ACTUAL DEPLOYED RLS (not proposed) | [ ] |
| 2.7 | Build Doc vs DB diff table | [ ] |
| 2.8 | Flag BLOCKERs for missing RLS | [ ] |
| 2.9 | **GATE**: All schema verified against snapshot? | [ ] |

## PHASE 3 — Entity & Relationship Model
**Output**: `work_order_lens_PHASE_3_ENTITY_GRAPH.md`

| Task | Description | Status |
|------|-------------|--------|
| 3.1 | Define primary entity | [ ] |
| 3.2 | Define secondary entities | [ ] |
| 3.3 | Map FK paths (explicit only) | [ ] |
| 3.4 | Verify no inferred joins | [ ] |
| 3.5 | Verify no vector joins in this phase | [ ] |
| 3.6 | Draw textual ER diagram | [ ] |
| 3.7 | Define allowed traversal paths | [ ] |
| 3.8 | **GATE**: All relationships proven in schema? | [ ] |

## PHASE 4 — Micro-Actions Contract
**Output**: `work_order_lens_PHASE_4_ACTIONS.md`

| Task | Description | Status |
|------|-------------|--------|
| 4.1 | List candidate actions (max 6) | [ ] |
| 4.2 | For each action: user intent phrasing | [ ] |
| 4.3 | For each action: trigger condition (query vs focus) | [ ] |
| 4.4 | For each action: tables read | [ ] |
| 4.5 | For each action: tables written | [ ] |
| 4.6 | For each action: field classification (REQ/OPT/CTX/AUTO) | [ ] |
| 4.7 | For each action: signature requirement | [ ] |
| 4.8 | For each action: RLS proof per write | [ ] |
| 4.9 | Remove unsafe actions | [ ] |
| 4.10 | **GATE**: All actions have RLS proof? | [ ] |

## PHASE 5 — UX Flow & Scenarios
**Output**: `work_order_lens_PHASE_5_SCENARIOS.md`

| Task | Description | Status |
|------|-------------|--------|
| 5.1 | Write Scenario 1 (with traditional vs Celeste comparison) | [ ] |
| 5.2 | Write Scenario 2 | [ ] |
| 5.3 | Write Scenario 3 | [ ] |
| 5.4 | Write Scenario 4 | [ ] |
| 5.5 | Write Scenario 5 | [ ] |
| 5.6 | Write Scenario 6 | [ ] |
| 5.7 | Write Scenario 7 | [ ] |
| 5.8 | Write Scenario 8 | [ ] |
| 5.9 | Write Scenario 9 | [ ] |
| 5.10 | Write Scenario 10 | [ ] |
| 5.11 | Verify no ambient buttons in any scenario | [ ] |
| 5.12 | **GATE**: All scenarios follow query-first doctrine? | [ ] |

## PHASE 6 — SQL & Backend Mapping
**Output**: `work_order_lens_PHASE_6_SQL_AND_BACKEND.md`

| Task | Description | Status |
|------|-------------|--------|
| 6.1 | For each action: write SELECT queries | [ ] |
| 6.2 | For each action: write INSERT/UPDATE queries | [ ] |
| 6.3 | For each action: identify triggers involved | [ ] |
| 6.4 | For each action: identify functions involved | [ ] |
| 6.5 | Verify all functions exist in snapshot | [ ] |
| 6.6 | Define transaction boundaries | [ ] |
| 6.7 | Label hypothetical SQL clearly | [ ] |
| 6.8 | **GATE**: All SQL uses existing functions only? | [ ] |

## PHASE 7 — RLS & Security Matrix
**Output**: `work_order_lens_PHASE_7_RLS_MATRIX.md`

| Task | Description | Status |
|------|-------------|--------|
| 7.1 | Build Role × Action matrix | [ ] |
| 7.2 | Document table-level RLS proof | [ ] |
| 7.3 | Document storage bucket policies (separate) | [ ] |
| 7.4 | Document explicit deny cases | [ ] |
| 7.5 | Verify storage + DB RLS both documented if needed | [ ] |
| 7.6 | **GATE**: Security matrix complete? | [ ] |

## PHASE 8 — Migration & Gap Report
**Output**: `work_order_lens_PHASE_8_GAPS_AND_MIGRATIONS.md`

| Task | Description | Status |
|------|-------------|--------|
| 8.1 | List missing columns | [ ] |
| 8.2 | List missing indexes | [ ] |
| 8.3 | List missing RLS policies | [ ] |
| 8.4 | List unsafe existing policies | [ ] |
| 8.5 | List deprecated legacy fields | [ ] |
| 8.6 | For each gap: risk assessment | [ ] |
| 8.7 | For each gap: proposed migration SQL | [ ] |
| 8.8 | For each gap: blocking vs optional | [ ] |
| 8.9 | **GATE**: All gaps documented with migration plan? | [ ] |

### LENS 1 FINAL GATE
| Check | Status |
|-------|--------|
| All 8 phases complete | [ ] |
| All BLOCKERs documented | [ ] |
| No invented functions | [ ] |
| No dashboard/button assumptions | [ ] |
| Ready for review | [ ] |

---

# LENS 2: EQUIPMENT

## PHASE 1 — Scope & Doctrine Lock
**Output**: `equipment_lens_PHASE_1_SCOPE.md`

| Task | Description | Status |
|------|-------------|--------|
| 1.1 | Define what this lens IS | [ ] |
| 1.2 | Define what this lens is NOT | [ ] |
| 1.3 | Classify: Read-only / Write-through / Operational | [ ] |
| 1.4 | Define allowed entry paths (query patterns) | [ ] |
| 1.5 | Define escape hatches (if any) | [ ] |
| 1.6 | Lock doctrine statement | [ ] |
| 1.7 | Review & freeze | [ ] |
| 1.8 | **GATE**: Scope approved? | [ ] |

## PHASE 2 — DB Truth Grounding
**Output**: `equipment_lens_PHASE_2_DB_TRUTH.md`

| Task | Description | Status |
|------|-------------|--------|
| 2.1 | List all tables involved (from snapshot) | [ ] |
| 2.2 | Extract columns, types, nullable, defaults | [ ] |
| 2.3 | Extract constraints (FK, CHECK, UNIQUE) | [ ] |
| 2.4 | Extract triggers | [ ] |
| 2.5 | Extract enums used | [ ] |
| 2.6 | Extract ACTUAL DEPLOYED RLS (not proposed) | [ ] |
| 2.7 | Build Doc vs DB diff table | [ ] |
| 2.8 | Flag BLOCKERs for missing RLS | [ ] |
| 2.9 | **GATE**: All schema verified against snapshot? | [ ] |

## PHASE 3 — Entity & Relationship Model
**Output**: `equipment_lens_PHASE_3_ENTITY_GRAPH.md`

| Task | Description | Status |
|------|-------------|--------|
| 3.1 | Define primary entity | [ ] |
| 3.2 | Define secondary entities | [ ] |
| 3.3 | Map FK paths (explicit only) | [ ] |
| 3.4 | Verify no inferred joins | [ ] |
| 3.5 | Verify no vector joins in this phase | [ ] |
| 3.6 | Draw textual ER diagram | [ ] |
| 3.7 | Define allowed traversal paths | [ ] |
| 3.8 | **GATE**: All relationships proven in schema? | [ ] |

## PHASE 4 — Micro-Actions Contract
**Output**: `equipment_lens_PHASE_4_ACTIONS.md`

| Task | Description | Status |
|------|-------------|--------|
| 4.1 | List candidate actions (max 6) | [ ] |
| 4.2 | For each action: user intent phrasing | [ ] |
| 4.3 | For each action: trigger condition (query vs focus) | [ ] |
| 4.4 | For each action: tables read | [ ] |
| 4.5 | For each action: tables written | [ ] |
| 4.6 | For each action: field classification (REQ/OPT/CTX/AUTO) | [ ] |
| 4.7 | For each action: signature requirement | [ ] |
| 4.8 | For each action: RLS proof per write | [ ] |
| 4.9 | Remove unsafe actions | [ ] |
| 4.10 | **GATE**: All actions have RLS proof? | [ ] |

## PHASE 5 — UX Flow & Scenarios
**Output**: `equipment_lens_PHASE_5_SCENARIOS.md`

| Task | Description | Status |
|------|-------------|--------|
| 5.1 | Write Scenario 1 (with traditional vs Celeste comparison) | [ ] |
| 5.2 | Write Scenario 2 | [ ] |
| 5.3 | Write Scenario 3 | [ ] |
| 5.4 | Write Scenario 4 | [ ] |
| 5.5 | Write Scenario 5 | [ ] |
| 5.6 | Write Scenario 6 | [ ] |
| 5.7 | Write Scenario 7 | [ ] |
| 5.8 | Write Scenario 8 | [ ] |
| 5.9 | Write Scenario 9 | [ ] |
| 5.10 | Write Scenario 10 | [ ] |
| 5.11 | Verify no ambient buttons in any scenario | [ ] |
| 5.12 | **GATE**: All scenarios follow query-first doctrine? | [ ] |

## PHASE 6 — SQL & Backend Mapping
**Output**: `equipment_lens_PHASE_6_SQL_AND_BACKEND.md`

| Task | Description | Status |
|------|-------------|--------|
| 6.1 | For each action: write SELECT queries | [ ] |
| 6.2 | For each action: write INSERT/UPDATE queries | [ ] |
| 6.3 | For each action: identify triggers involved | [ ] |
| 6.4 | For each action: identify functions involved | [ ] |
| 6.5 | Verify all functions exist in snapshot | [ ] |
| 6.6 | Define transaction boundaries | [ ] |
| 6.7 | Label hypothetical SQL clearly | [ ] |
| 6.8 | **GATE**: All SQL uses existing functions only? | [ ] |

## PHASE 7 — RLS & Security Matrix
**Output**: `equipment_lens_PHASE_7_RLS_MATRIX.md`

| Task | Description | Status |
|------|-------------|--------|
| 7.1 | Build Role × Action matrix | [ ] |
| 7.2 | Document table-level RLS proof | [ ] |
| 7.3 | Document storage bucket policies (separate) | [ ] |
| 7.4 | Document explicit deny cases | [ ] |
| 7.5 | Verify storage + DB RLS both documented if needed | [ ] |
| 7.6 | **GATE**: Security matrix complete? | [ ] |

## PHASE 8 — Migration & Gap Report
**Output**: `equipment_lens_PHASE_8_GAPS_AND_MIGRATIONS.md`

| Task | Description | Status |
|------|-------------|--------|
| 8.1 | List missing columns | [ ] |
| 8.2 | List missing indexes | [ ] |
| 8.3 | List missing RLS policies | [ ] |
| 8.4 | List unsafe existing policies | [ ] |
| 8.5 | List deprecated legacy fields | [ ] |
| 8.6 | For each gap: risk assessment | [ ] |
| 8.7 | For each gap: proposed migration SQL | [ ] |
| 8.8 | For each gap: blocking vs optional | [ ] |
| 8.9 | **GATE**: All gaps documented with migration plan? | [ ] |

### LENS 2 FINAL GATE
| Check | Status |
|-------|--------|
| All 8 phases complete | [ ] |
| All BLOCKERs documented | [ ] |
| No invented functions | [ ] |
| No dashboard/button assumptions | [ ] |
| Ready for review | [ ] |

---

# LENS 3: INVENTORY ITEM

## PHASE 1 — Scope & Doctrine Lock
**Output**: `inventory_item_lens_PHASE_1_SCOPE.md`

| Task | Description | Status |
|------|-------------|--------|
| 1.1 | Define what this lens IS | [ ] |
| 1.2 | Define what this lens is NOT | [ ] |
| 1.3 | Classify: Read-only / Write-through / Operational | [ ] |
| 1.4 | Define allowed entry paths (query patterns) | [ ] |
| 1.5 | Define escape hatches (if any) | [ ] |
| 1.6 | Lock doctrine statement | [ ] |
| 1.7 | Review & freeze | [ ] |
| 1.8 | **GATE**: Scope approved? | [ ] |

## PHASE 2 — DB Truth Grounding
**Output**: `inventory_item_lens_PHASE_2_DB_TRUTH.md`

| Task | Description | Status |
|------|-------------|--------|
| 2.1 | List all tables involved (from snapshot) | [ ] |
| 2.2 | Extract columns, types, nullable, defaults | [ ] |
| 2.3 | Extract constraints (FK, CHECK, UNIQUE) | [ ] |
| 2.4 | Extract triggers | [ ] |
| 2.5 | Extract enums used | [ ] |
| 2.6 | Extract ACTUAL DEPLOYED RLS (not proposed) | [ ] |
| 2.7 | Build Doc vs DB diff table | [ ] |
| 2.8 | Flag BLOCKERs for missing RLS | [ ] |
| 2.9 | **GATE**: All schema verified against snapshot? | [ ] |

## PHASE 3 — Entity & Relationship Model
**Output**: `inventory_item_lens_PHASE_3_ENTITY_GRAPH.md`

| Task | Description | Status |
|------|-------------|--------|
| 3.1 | Define primary entity | [ ] |
| 3.2 | Define secondary entities | [ ] |
| 3.3 | Map FK paths (explicit only) | [ ] |
| 3.4 | Verify no inferred joins | [ ] |
| 3.5 | Verify no vector joins in this phase | [ ] |
| 3.6 | Draw textual ER diagram | [ ] |
| 3.7 | Define allowed traversal paths | [ ] |
| 3.8 | **GATE**: All relationships proven in schema? | [ ] |

## PHASE 4 — Micro-Actions Contract
**Output**: `inventory_item_lens_PHASE_4_ACTIONS.md`

| Task | Description | Status |
|------|-------------|--------|
| 4.1 | List candidate actions (max 6) | [ ] |
| 4.2 | For each action: user intent phrasing | [ ] |
| 4.3 | For each action: trigger condition (query vs focus) | [ ] |
| 4.4 | For each action: tables read | [ ] |
| 4.5 | For each action: tables written | [ ] |
| 4.6 | For each action: field classification (REQ/OPT/CTX/AUTO) | [ ] |
| 4.7 | For each action: signature requirement | [ ] |
| 4.8 | For each action: RLS proof per write | [ ] |
| 4.9 | Remove unsafe actions | [ ] |
| 4.10 | **GATE**: All actions have RLS proof? | [ ] |

## PHASE 5 — UX Flow & Scenarios
**Output**: `inventory_item_lens_PHASE_5_SCENARIOS.md`

| Task | Description | Status |
|------|-------------|--------|
| 5.1 | Write Scenario 1 (with traditional vs Celeste comparison) | [ ] |
| 5.2 | Write Scenario 2 | [ ] |
| 5.3 | Write Scenario 3 | [ ] |
| 5.4 | Write Scenario 4 | [ ] |
| 5.5 | Write Scenario 5 | [ ] |
| 5.6 | Write Scenario 6 | [ ] |
| 5.7 | Write Scenario 7 | [ ] |
| 5.8 | Write Scenario 8 | [ ] |
| 5.9 | Write Scenario 9 | [ ] |
| 5.10 | Write Scenario 10 | [ ] |
| 5.11 | Verify no ambient buttons in any scenario | [ ] |
| 5.12 | **GATE**: All scenarios follow query-first doctrine? | [ ] |

## PHASE 6 — SQL & Backend Mapping
**Output**: `inventory_item_lens_PHASE_6_SQL_AND_BACKEND.md`

| Task | Description | Status |
|------|-------------|--------|
| 6.1 | For each action: write SELECT queries | [ ] |
| 6.2 | For each action: write INSERT/UPDATE queries | [ ] |
| 6.3 | For each action: identify triggers involved | [ ] |
| 6.4 | For each action: identify functions involved | [ ] |
| 6.5 | Verify all functions exist in snapshot | [ ] |
| 6.6 | Define transaction boundaries | [ ] |
| 6.7 | Label hypothetical SQL clearly | [ ] |
| 6.8 | **GATE**: All SQL uses existing functions only? | [ ] |

## PHASE 7 — RLS & Security Matrix
**Output**: `inventory_item_lens_PHASE_7_RLS_MATRIX.md`

| Task | Description | Status |
|------|-------------|--------|
| 7.1 | Build Role × Action matrix | [ ] |
| 7.2 | Document table-level RLS proof | [ ] |
| 7.3 | Document storage bucket policies (separate) | [ ] |
| 7.4 | Document explicit deny cases | [ ] |
| 7.5 | Verify storage + DB RLS both documented if needed | [ ] |
| 7.6 | **GATE**: Security matrix complete? | [ ] |

## PHASE 8 — Migration & Gap Report
**Output**: `inventory_item_lens_PHASE_8_GAPS_AND_MIGRATIONS.md`

| Task | Description | Status |
|------|-------------|--------|
| 8.1 | List missing columns | [ ] |
| 8.2 | List missing indexes | [ ] |
| 8.3 | List missing RLS policies | [ ] |
| 8.4 | List unsafe existing policies | [ ] |
| 8.5 | List deprecated legacy fields | [ ] |
| 8.6 | For each gap: risk assessment | [ ] |
| 8.7 | For each gap: proposed migration SQL | [ ] |
| 8.8 | For each gap: blocking vs optional | [ ] |
| 8.9 | **GATE**: All gaps documented with migration plan? | [ ] |

### LENS 3 FINAL GATE
| Check | Status |
|-------|--------|
| All 8 phases complete | [ ] |
| All BLOCKERs documented | [ ] |
| No invented functions | [ ] |
| No dashboard/button assumptions | [ ] |
| Ready for review | [ ] |

---

# LENS 4: PART

## PHASE 1 — Scope & Doctrine Lock
**Output**: `part_lens_PHASE_1_SCOPE.md`

| Task | Description | Status |
|------|-------------|--------|
| 1.1 | Define what this lens IS | [ ] |
| 1.2 | Define what this lens is NOT | [ ] |
| 1.3 | Classify: Read-only / Write-through / Operational | [ ] |
| 1.4 | Define allowed entry paths (query patterns) | [ ] |
| 1.5 | Define escape hatches (if any) | [ ] |
| 1.6 | Lock doctrine statement | [ ] |
| 1.7 | Review & freeze | [ ] |
| 1.8 | **GATE**: Scope approved? | [ ] |

## PHASE 2-8
*(Same structure as above - abbreviated for space)*

### LENS 4 FINAL GATE
| Check | Status |
|-------|--------|
| All 8 phases complete | [ ] |
| All BLOCKERs documented | [ ] |
| No invented functions | [ ] |
| No dashboard/button assumptions | [ ] |
| Ready for review | [ ] |

---

# LENS 5: RECEIVING

## PHASE 1 — Scope & Doctrine Lock
**Output**: `receiving_lens_PHASE_1_SCOPE.md`

| Task | Description | Status |
|------|-------------|--------|
| 1.1 | Define what this lens IS | [ ] |
| 1.2 | Define what this lens is NOT | [ ] |
| 1.3 | Classify: Read-only / Write-through / Operational | [ ] |
| 1.4 | Define allowed entry paths (query patterns) | [ ] |
| 1.5 | Define escape hatches (if any) | [ ] |
| 1.6 | Lock doctrine statement | [ ] |
| 1.7 | Review & freeze | [ ] |
| 1.8 | **GATE**: Scope approved? | [ ] |

## PHASE 2-8
*(Same structure as above)*

### LENS 5 FINAL GATE
| Check | Status |
|-------|--------|
| All 8 phases complete | [ ] |
| All BLOCKERs documented | [ ] |
| No invented functions | [ ] |
| No dashboard/button assumptions | [ ] |
| Ready for review | [ ] |

---

# LENS 6: SHOPPING LIST

## PHASE 1 — Scope & Doctrine Lock
**Output**: `shopping_list_lens_PHASE_1_SCOPE.md`

| Task | Description | Status |
|------|-------------|--------|
| 1.1 | Define what this lens IS | [ ] |
| 1.2 | Define what this lens is NOT | [ ] |
| 1.3 | Classify: Read-only / Write-through / Operational | [ ] |
| 1.4 | Define allowed entry paths (query patterns) | [ ] |
| 1.5 | Define escape hatches (if any) | [ ] |
| 1.6 | Lock doctrine statement | [ ] |
| 1.7 | Review & freeze | [ ] |
| 1.8 | **GATE**: Scope approved? | [ ] |

## PHASE 2-8
*(Same structure as above)*

### LENS 6 FINAL GATE
| Check | Status |
|-------|--------|
| All 8 phases complete | [ ] |
| All BLOCKERs documented | [ ] |
| No invented functions | [ ] |
| No dashboard/button assumptions | [ ] |
| Ready for review | [ ] |

---

# LENS 7: DOCUMENT

## PHASE 1 — Scope & Doctrine Lock
**Output**: `document_lens_PHASE_1_SCOPE.md`

| Task | Description | Status |
|------|-------------|--------|
| 1.1 | Define what this lens IS | [ ] |
| 1.2 | Define what this lens is NOT | [ ] |
| 1.3 | Classify: Read-only / Write-through / Operational | [ ] |
| 1.4 | Define allowed entry paths (query patterns) | [ ] |
| 1.5 | Define escape hatches (if any) | [ ] |
| 1.6 | Lock doctrine statement | [ ] |
| 1.7 | Review & freeze | [ ] |
| 1.8 | **GATE**: Scope approved? | [ ] |

## PHASE 2-8
*(Same structure as above)*

### LENS 7 FINAL GATE
| Check | Status |
|-------|--------|
| All 8 phases complete | [ ] |
| All BLOCKERs documented | [ ] |
| No invented functions | [ ] |
| No dashboard/button assumptions | [ ] |
| Ready for review | [ ] |

---

# LENS 8: CREW

## PHASE 1 — Scope & Doctrine Lock
**Output**: `crew_lens_PHASE_1_SCOPE.md`

| Task | Description | Status |
|------|-------------|--------|
| 1.1 | Define what this lens IS | [ ] |
| 1.2 | Define what this lens is NOT | [ ] |
| 1.3 | Classify: Read-only / Write-through / Operational | [ ] |
| 1.4 | Define allowed entry paths (query patterns) | [ ] |
| 1.5 | Define escape hatches (if any) | [ ] |
| 1.6 | Lock doctrine statement | [ ] |
| 1.7 | Review & freeze | [ ] |
| 1.8 | **GATE**: Scope approved? | [ ] |

## PHASE 2-8
*(Same structure as above)*

### LENS 8 FINAL GATE
| Check | Status |
|-------|--------|
| All 8 phases complete | [ ] |
| All BLOCKERs documented | [ ] |
| No invented functions | [ ] |
| No dashboard/button assumptions | [ ] |
| Ready for review | [ ] |

---

# LENS 9: CERTIFICATE

## PHASE 1 — Scope & Doctrine Lock
**Output**: `certificate_lens_PHASE_1_SCOPE.md`

| Task | Description | Status |
|------|-------------|--------|
| 1.1 | Define what this lens IS | [ ] |
| 1.2 | Define what this lens is NOT | [ ] |
| 1.3 | Classify: Read-only / Write-through / Operational | [ ] |
| 1.4 | Define allowed entry paths (query patterns) | [ ] |
| 1.5 | Define escape hatches (if any) | [ ] |
| 1.6 | Lock doctrine statement | [ ] |
| 1.7 | Review & freeze | [ ] |
| 1.8 | **GATE**: Scope approved? | [ ] |

## PHASE 2-8
*(Same structure as above)*

### LENS 9 FINAL GATE
| Check | Status |
|-------|--------|
| All 8 phases complete | [ ] |
| All BLOCKERs documented | [ ] |
| No invented functions | [ ] |
| No dashboard/button assumptions | [ ] |
| Ready for review | [ ] |

---

# LENS 10: FINANCE/TRANSACTION

## PHASE 1 — Scope & Doctrine Lock
**Output**: `finance_lens_PHASE_1_SCOPE.md`

| Task | Description | Status |
|------|-------------|--------|
| 1.1 | Define what this lens IS | [ ] |
| 1.2 | Define what this lens is NOT | [ ] |
| 1.3 | Classify: Read-only / Write-through / Operational | [ ] |
| 1.4 | Define allowed entry paths (query patterns) | [ ] |
| 1.5 | Define escape hatches (if any) | [ ] |
| 1.6 | Lock doctrine statement | [ ] |
| 1.7 | Review & freeze | [ ] |
| 1.8 | **GATE**: Scope approved? | [ ] |

## PHASE 2-8
*(Same structure as above)*

### LENS 10 FINAL GATE
| Check | Status |
|-------|--------|
| All 8 phases complete | [ ] |
| All BLOCKERs documented | [ ] |
| No invented functions | [ ] |
| No dashboard/button assumptions | [ ] |
| Ready for review | [ ] |

---

# SYSTEM-WIDE CROSS-LENS ANALYSIS

**Output**: `SYSTEM_WIDE_CROSS_LENS_ANALYSIS.md`

Only produced AFTER all 10 lenses complete.

| Analysis Area | Status |
|---------------|--------|
| Repeated patterns across lenses | [ ] |
| One-off exceptions | [ ] |
| Shared helpers (candidates for extraction) | [ ] |
| Conflicting doctrines | [ ] |
| Candidate abstractions | [ ] |
| Migration bundling opportunities | [ ] |
| RLS consolidation candidates | [ ] |
| Storage policy consolidation | [ ] |

> **No new features allowed here. Analysis only.**

---

# CRITICAL STOP CONDITIONS

Agent MUST halt if any of:

| Condition | Action |
|-----------|--------|
| Missing DB snapshot | STOP, request snapshot |
| Action without RLS proof | Mark BLOCKER, do not proceed |
| Function referenced but not found | Mark BLOCKER, do not proceed |
| Assumed UI element (dashboard, button, menu) | Remove from doc |
| Severity inferred instead of user-selected | Fix or BLOCKER |
| Storage behavior implied without policy | Mark BLOCKER |

---

# PROGRESS TRACKER

| Lens | P1 | P2 | P3 | P4 | P5 | P6 | P7 | P8 | Final |
|------|----|----|----|----|----|----|----|----|-------|
| Work Order | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| Equipment | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| Inventory Item | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| Part | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| Receiving | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| Shopping List | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| Document | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| Crew | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| Certificate | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| Finance | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| **Cross-Lens** | - | - | - | - | - | - | - | - | [ ] |

---

**END OF PIPELINE DOCUMENT**
