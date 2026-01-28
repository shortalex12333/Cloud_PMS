# Entity Lens Builder - Full Context Briefing

**To**: New Claude Agent Building Work Order Lens
**From**: Previous Session Context
**Purpose**: Bring you up to speed with full vision, depth requirements, and execution instructions

---

## IMMEDIATE ACTION REQUIRED

### 1. Create Actual Files (Not Console Output)

Your Phase 1 output was correct, but it must be saved as an actual file:

```
docs/architecture/entity_lenses/work_order_lens/
├── work_order_lens_PHASE_1_SCOPE.md        ← Create NOW from your Phase 1 output
├── work_order_lens_PHASE_2_DB_TRUTH.md     ← Create after Phase 2
├── work_order_lens_PHASE_3_ENTITY_GRAPH.md
├── work_order_lens_PHASE_4_ACTIONS.md
├── work_order_lens_PHASE_5_SCENARIOS.md
├── work_order_lens_PHASE_6_SQL_AND_BACKEND.md
├── work_order_lens_PHASE_7_RLS_MATRIX.md
├── work_order_lens_PHASE_8_GAPS_AND_MIGRATIONS.md
└── work_order_lens_v1_FINAL.md             ← Compiled from all phases
```

### 2. Proceed With ALL Phases (Not One at a Time)

After creating the Phase 1 file, execute Phases 2-8 in sequence without waiting for approval between each. Only stop if you hit a BLOCKER that cannot be resolved.

---

## THE VISION: CELESTE UX DOCTRINE

### What Celeste IS

Celeste is a yacht PMS for 125m+ superyachts with 45-65 crew. The entire UX is:

```
┌─────────────────────────────────────────────────────────────┐
│  [SINGLE SEARCH BAR]                    [Ledger] [Settings] │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                                                      │    │
│  │              SEARCH RESULTS / ENTITY VIEW            │    │
│  │                                                      │    │
│  │    (No navigation. No dashboards. No sidebar.)       │    │
│  │                                                      │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  [Context Menu appears ONLY when entity focused]            │
└─────────────────────────────────────────────────────────────┘
```

### What Celeste is NOT

- **No dashboards** - Never mention dashboards, widgets, or overview screens
- **No navigation menus** - No sidebar, no hamburger menu, no tabs
- **No ambient buttons** - No buttons floating on screen without context
- **No "navigate to" language** - Users don't navigate, they query

### The Three Permanent UI Elements

1. **Search Bar** - Always visible, query-only activation
2. **Ledger Button** - Global timeline of all events (derived from pms_audit_log)
3. **Settings Button** - User/yacht configuration

**That's it.** Everything else appears contextually in response to queries.

---

## QUERY-ONLY ACTIVATION DOCTRINE

### How Actions Appear

```
User types query → RAG surfaces results → User focuses entity → Context menu appears
                                                                       ↓
                                                              [Available Actions]
```

Actions NEVER appear:
- On search results lists
- Before entity focus
- As floating buttons
- Via navigation

### Work Order Specific

The WO-First Doctrine means:
- Work Order is the PRIMARY operational entity
- Fault is metadata/history attached to WO
- Equipment state comes FROM Work Orders
- Users work with WOs, not faults directly

---

## DEPTH REQUIREMENTS BY PHASE

### Phase 2: DB Truth (CRITICAL)

**Source**: `docs/architecture/database_schema.txt` - This is the ONLY source of truth

You MUST extract for each table:
- Every column with exact type
- Nullability (YES/NO)
- Default values
- CHECK constraints (exact text)
- FK constraints (exact references)
- UNIQUE constraints
- Triggers (exact function names)
- Enums used (exact values)

**RLS Extraction**: For each table, find the ACTUAL DEPLOYED policies:
```sql
-- What you're looking for in the schema
CREATE POLICY "policy_name" ON table_name
FOR SELECT/INSERT/UPDATE/DELETE
USING (condition)
WITH CHECK (condition);
```

**BLOCKER Rule**: If a table has no RLS policy for a required operation, mark it as BLOCKER immediately.

### Phase 3: Entity & Relationship Model

Map ONLY FK relationships that exist in the schema:
```
pms_work_orders.equipment_id → equipment.id
pms_work_orders.created_by → auth_users.id
pms_fault_reports.work_order_id → pms_work_orders.id
```

**FORBIDDEN**:
- Inferred joins (tables without FK but "should" relate)
- Vector/similarity joins
- Application-level joins not in schema

### Phase 4: Micro-Actions Contract (CRITICAL)

For EACH action (max 6), you must document:

```markdown
### Action N: [Name]

**Blocker Status**: None / B1 (describe)

**Intent Phrasing**: "Mark this work order as complete"
**Trigger Condition**: Entity focused + query contains completion intent

**Tables Read**:
- pms_work_orders (status, equipment_id, ...)
- equipment (for validation)

**Tables Written**:
- pms_work_orders (status, completed_at, completed_by)
- pms_audit_log (always)

**Field Classification**:
| Field | Classification | Notes |
|-------|----------------|-------|
| status | BACKEND_AUTO | Set to 'completed' |
| completed_at | BACKEND_AUTO | Set to NOW() |
| completed_by | BACKEND_AUTO | Set to auth.uid() |
| notes | OPTIONAL | User can provide |

**Signature Requirement**:
- Required: NO
- Value: `'{}'::jsonb` (empty object because pms_audit_log.signature is NOT NULL)

**RLS Proof**:
- Table: pms_work_orders
- Policy: [exact policy name from snapshot]
- Cmd: UPDATE
- Condition: [exact USING clause]

**Ledger UI Event**: (derived from pms_audit_log, NOT a table write)
- entity_type: 'work_order'
- entity_id: [work_order_id]
- action: 'completed'
```

### Phase 5: Scenarios (10 REQUIRED)

Each scenario MUST have Traditional vs Celeste comparison:

```markdown
### Scenario 1: Basic Lookup

**User Context**: Engineer, on deck, mobile device

**Query**: "Show me work order 2024-001"

---

#### Traditional Software Flow
1. Open app
2. Navigate to Work Orders menu
3. Click "Search" or scroll list
4. Find WO 2024-001
5. Click to open details
**Total Steps**: 5

#### Celeste Flow
1. User types "WO 2024-001"
2. RAG surfaces exact match
3. Entity card displayed
**Total Steps**: 3

---

**Data Surfaced**:
- RAG: Work order document chunks
- SQL: `SELECT * FROM pms_work_orders WHERE code = '2024-001'`

**Focus Event**: Yes - Work Order 2024-001 focused

**Context Menu Activation**: Yes
- Available: Complete, Update, Add Note, Attach Photo

**Escape Hatch**: Equipment Lens (if user asks about related equipment)

**Verification Checklist**:
- [x] No ambient buttons
- [x] No dashboard referenced
- [x] Query-first maintained
- [x] Action only after focus
```

### Phase 6: SQL & Backend Mapping

ALL SQL must use:
1. **Existing functions only** - Verify in snapshot before using
2. **public.get_user_yacht_id()** - This is CANONICAL for yacht isolation
3. **Signature invariant** - `'{}'::jsonb` for non-signature, full payload for signature

Example of CORRECT SQL:
```sql
INSERT INTO pms_audit_log (
  yacht_id,
  user_id,
  action,
  entity_type,
  entity_id,
  details,
  signature  -- NEVER NULL
) VALUES (
  public.get_user_yacht_id(),  -- CANONICAL function
  auth.uid(),
  'work_order_completed',
  'work_order',  -- from canonical list
  $1,
  $2,
  '{}'::jsonb  -- empty object, NOT null
);
```

**If a function doesn't exist in snapshot**: Mark as BLOCKER, do not use it.

### Phase 7: RLS & Security Matrix

Build complete matrix:

```markdown
| Role           | View WO | Create WO | Complete WO | Delete WO | Attach File |
|----------------|---------|-----------|-------------|-----------|-------------|
| deckhand       | Own yacht | ❌      | ❌          | ❌        | Own WOs     |
| steward        | Own yacht | ❌      | ❌          | ❌        | Own WOs     |
| engineer       | Own yacht | ✅      | Own WOs     | ❌        | Own WOs     |
| chief_engineer | Own yacht | ✅      | Dept WOs    | ❌        | Dept WOs    |
| captain        | Own yacht | ✅      | All WOs     | ✅        | All WOs     |
```

For each cell, cite the exact RLS policy from snapshot.

**Storage Bucket Policies** (SEPARATE from DB RLS):
- Read policy name + condition
- Write policy name + condition
- Delete policy name + condition

### Phase 8: Gaps & Migration Report

Document every discrepancy:

```markdown
| Gap ID | Type | Description | Blocking? | Migration SQL |
|--------|------|-------------|-----------|---------------|
| G1 | Missing RLS | pms_work_orders has no DELETE policy | YES | CREATE POLICY... |
| G2 | Missing Column | No 'priority' enum on pms_work_orders | NO | ALTER TABLE... |
| G3 | Missing Index | No index on equipment_id | NO | CREATE INDEX... |
```

---

## CANONICAL PATTERNS (MEMORIZE THESE)

### 1. Yacht Isolation
```sql
-- CORRECT
public.get_user_yacht_id()

-- WRONG (does not exist)
auth.user_yacht_id()
auth.jwt() ->> 'yacht_id'
current_setting('app.yacht_id')
```

### 2. Signature Invariant
```sql
-- pms_audit_log.signature is NOT NULL
-- For non-signature actions:
signature = '{}'::jsonb

-- For signature-required actions:
signature = '{"signer_id": "...", "timestamp": "...", "hash": "..."}'::jsonb
```

### 3. Entity Type Values (canonical list)
```
fault, work_order, note, attachment, equipment, part,
inventory_item, shopping_list_item, receiving_event
```

### 4. Audit Log Pattern
```sql
INSERT INTO pms_audit_log (
  yacht_id,
  user_id,
  action,
  entity_type,
  entity_id,
  details,
  signature
) VALUES (
  public.get_user_yacht_id(),
  auth.uid(),
  '[action_name]',
  '[entity_type from canonical list]',
  [entity_id],
  '[details jsonb]'::jsonb,
  '{}'::jsonb  -- or full signature payload
);
```

---

## BLOCKER SYSTEM

When you encounter something that doesn't exist in the snapshot:

1. **Identify**: "Function generate_wo_code() not in pg_proc"
2. **Assign ID**: B1, B2, B3...
3. **Document in BLOCKERS section at top of document**
4. **Mark affected action**: "Action 2: Create Work Order [BLOCKED: B1]"
5. **Add to Phase 8 gaps**: Migration SQL to create the missing function
6. **Action is DISABLED in UI until blocker resolved**

---

## FILE CREATION CHECKLIST

After reading this, immediately:

1. [ ] Create directory: `docs/architecture/entity_lenses/work_order_lens/`
2. [ ] Save Phase 1 output as `work_order_lens_PHASE_1_SCOPE.md`
3. [ ] Execute Phase 2, save as `work_order_lens_PHASE_2_DB_TRUTH.md`
4. [ ] Execute Phase 3, save as `work_order_lens_PHASE_3_ENTITY_GRAPH.md`
5. [ ] Execute Phase 4, save as `work_order_lens_PHASE_4_ACTIONS.md`
6. [ ] Execute Phase 5, save as `work_order_lens_PHASE_5_SCENARIOS.md`
7. [ ] Execute Phase 6, save as `work_order_lens_PHASE_6_SQL_AND_BACKEND.md`
8. [ ] Execute Phase 7, save as `work_order_lens_PHASE_7_RLS_MATRIX.md`
9. [ ] Execute Phase 8, save as `work_order_lens_PHASE_8_GAPS_AND_MIGRATIONS.md`
10. [ ] Compile final: `work_order_lens_v1_FINAL.md`

---

## REFERENCE FILES

Read these in order:
1. `fault_lens_v5_FINAL.md` - GOLD STANDARD template (follow this structure exactly)
2. `LENS_BUILDER_OPERATING_PROCEDURE.md` - Rules and blockers
3. `LENS_FACTORY_PIPELINE.md` - Overall pipeline context
4. `PHASE_TEMPLATES/PHASE_CHECKLIST_MASTER.md` - Granular task tracking
5. `PHASE_TEMPLATES/PHASE_5_SCENARIO_TEMPLATE.md` - Scenario structure
6. `database_schema.txt` - DB TRUTH (the ONLY source)

---

## PROCEED NOW

Do not wait for approval. Create the files. Execute all phases. Document all blockers. The human will review the final artifacts.

**GO.**
