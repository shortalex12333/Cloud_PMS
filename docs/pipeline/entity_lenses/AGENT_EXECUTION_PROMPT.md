# AGENT EXECUTION PROMPT - RUN UNTIL PRODUCTION COMPLETE

**Mode**: Autonomous Execution
**Budget**: Unlimited
**Standard**: Production-Ready Only
**Termination Condition**: ALL deliverables complete, ALL tests passing, ALL security holes fixed

---

# MISSION

You are completing the CELESTE Entity Lens Architecture. You will not stop until everything is production-ready. "Done" means:

1. All 10 lenses documented to v5 FINAL standard
2. All security holes (cross-yacht leakage) fixed with deployed migrations
3. All 6,000+ tests written and passing
4. All cross-lens integrations documented and tested
5. All contract interfaces defined
6. All monitoring/alerting configured
7. Zero blockers remaining

---

# READ THESE FILES FIRST (IN ORDER)

```
1. docs/architecture/entity_lenses/fault_lens_v5_FINAL.md
   → This is the GOLD STANDARD. Every lens must match this quality.

2. docs/architecture/entity_lenses/LENS_BUILDER_OPERATING_PROCEDURE.md
   → Non-negotiable rules. Memorize them.

3. docs/architecture/entity_lenses/MASTER_MISSION_BRIEFING.md
   → Full scope of work, testing methodology, migration strategy.

4. docs/architecture/entity_lenses/work_order_lens/v2/work_order_lens_v2_FINAL.md
   → Your previous work. Build on this.

5. /Volumes/Backup/CELESTE/database_schema.txt
   → THE ONLY SOURCE OF DB TRUTH. Nothing exists unless it's here.

6. supabase/migrations/*.sql
   → ACTUAL DEPLOYED policies. Not assumptions.
```

---

# EXECUTION SEQUENCE

## PHASE A: SECURITY FIXES (DO THIS FIRST)

Before ANY new lenses, fix the P0 security holes:

### A.1 Create Migration: Fix pms_work_order_notes

```sql
-- File: supabase/migrations/20260125_001_fix_cross_yacht_notes.sql

-- PROBLEM: USING (true) allows ANY authenticated user to see ALL yachts' notes
-- SOLUTION: Join through pms_work_orders to enforce yacht isolation

BEGIN;

-- Drop the broken policy
DROP POLICY IF EXISTS "Authenticated users can view notes" ON pms_work_order_notes;

-- Create yacht-isolated policy
CREATE POLICY "crew_select_own_yacht_notes" ON pms_work_order_notes
    FOR SELECT TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM pms_work_orders wo
            WHERE wo.id = pms_work_order_notes.work_order_id
            AND wo.yacht_id = public.get_user_yacht_id()
        )
    );

-- INSERT policy (only own yacht's WOs)
CREATE POLICY "crew_insert_own_yacht_notes" ON pms_work_order_notes
    FOR INSERT TO authenticated
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM pms_work_orders wo
            WHERE wo.id = pms_work_order_notes.work_order_id
            AND wo.yacht_id = public.get_user_yacht_id()
        )
    );

COMMIT;
```

### A.2 Create Migration: Fix pms_work_order_parts

```sql
-- File: supabase/migrations/20260125_002_fix_cross_yacht_parts.sql

BEGIN;

DROP POLICY IF EXISTS "Authenticated users can view parts" ON pms_work_order_parts;

CREATE POLICY "crew_select_own_yacht_parts" ON pms_work_order_parts
    FOR SELECT TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM pms_work_orders wo
            WHERE wo.id = pms_work_order_parts.work_order_id
            AND wo.yacht_id = public.get_user_yacht_id()
        )
        AND deleted_at IS NULL
    );

CREATE POLICY "crew_insert_own_yacht_parts" ON pms_work_order_parts
    FOR INSERT TO authenticated
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM pms_work_orders wo
            WHERE wo.id = pms_work_order_parts.work_order_id
            AND wo.yacht_id = public.get_user_yacht_id()
        )
    );

COMMIT;
```

### A.3 Create Migration: Fix pms_part_usage

```sql
-- File: supabase/migrations/20260125_003_fix_cross_yacht_part_usage.sql

BEGIN;

-- pms_part_usage HAS yacht_id column, so direct check
DROP POLICY IF EXISTS "Authenticated users can view part usage" ON pms_part_usage;

CREATE POLICY "crew_select_own_yacht_part_usage" ON pms_part_usage
    FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

CREATE POLICY "crew_insert_own_yacht_part_usage" ON pms_part_usage
    FOR INSERT TO authenticated
    WITH CHECK (yacht_id = public.get_user_yacht_id());

COMMIT;
```

### A.4 Verify Migrations

After creating each migration file, verify:

```sql
-- Test query: Should return ONLY current yacht's data
SELECT * FROM pms_work_order_notes LIMIT 5;
SELECT * FROM pms_work_order_parts LIMIT 5;
SELECT * FROM pms_part_usage LIMIT 5;
```

---

## PHASE B: REMAINING 9 LENSES

Execute in this order (dependencies flow downward):

### B.1 Equipment Lens (Day 1)
Primary table: `pms_equipment` or `equipment`
- Verify which table is canonical in database_schema.txt
- Extract all columns, types, nullability
- Map FK paths to: work_orders, faults, parts
- Define 6 max actions
- Write 10 scenarios
- Extract actual RLS from migrations

### B.2 Fault Lens (Day 1)
Primary table: `pms_faults` or `pms_fault_reports`
- Use fault_lens_v5_FINAL.md as template
- This lens already has gold standard - VERIFY it matches current DB
- Update if schema has changed since v5

### B.3 Part Lens (Day 2)
Primary table: `pms_parts` or `parts`
- Map relationships to: inventory, work_orders, equipment
- Document part usage tracking
- Define low stock thresholds

### B.4 Inventory Item Lens (Day 2)
Primary table: `pms_inventory_items` or similar
- Search database_schema.txt for inventory tables
- May need to combine with Parts lens if same table

### B.5 Receiving Lens (Day 3)
Primary table: `receiving_events` or `pms_receiving`
- Search database_schema.txt for receiving/shipment tables
- Link to purchase orders, parts

### B.6 Shopping List Lens (Day 3)
Primary table: `shopping_list_items` or similar
- Search database_schema.txt
- Link to parts, purchase orders

### B.7 Document Lens (Day 4)
Primary tables: `documents`, `search_chunks`
- RAG integration points
- Storage bucket RLS (separate from DB RLS)
- Manual reference handling

### B.8 Crew Lens (Day 4)
Primary table: `auth_users_profiles`
- Role management
- Assignment to work orders
- Hours tracking (if table exists)

### B.9 Certificate Lens (Day 5)
Primary table: `certificates` or similar
- Expiry tracking
- Renewal workflows
- Document attachments

---

## PHASE C: CROSS-LENS INTEGRATION

### C.1 Escape Hatch Matrix

Create file: `CROSS_LENS_ESCAPE_HATCH_MATRIX.md`

```markdown
| From Lens | To Lens | Trigger Query Pattern | Data Passed |
|-----------|---------|----------------------|-------------|
| Fault | Work Order | "create WO for this fault" | fault_id, equipment_id |
| Work Order | Equipment | "show equipment for this WO" | equipment_id |
| Equipment | Fault | "faults on this equipment" | equipment_id |
| Work Order | Part | "parts used on this WO" | work_order_id |
| Part | Inventory | "stock level for this part" | part_id |
| Crew | Work Order | "WOs assigned to [name]" | user_id |
| Document | Equipment | "manuals for this equipment" | equipment_id |
| Certificate | Crew | "certs for [crew member]" | user_id |
| Equipment | Document | "documents for this equipment" | equipment_id |
| All | Ledger | "history of [entity]" | entity_type, entity_id |
```

### C.2 Shared Tables Treatment

Create file: `SHARED_TABLES_UNIFIED_TREATMENT.md`

Document how each shared table is used across lenses:
- pms_audit_log (used by ALL)
- pms_attachments (used by WO, Fault, Equipment)
- auth_users_profiles (used by ALL)
- pms_notes (used by WO, Fault, Equipment)

---

## PHASE D: CONTRACT INTERFACES

### D.1 Create Interface Definitions

Create file: `CONTRACT_INTERFACES.md`

Define JSON schemas for:

```typescript
// 1. RAG Response
interface RAGResponse {
  chunks: ChunkResult[];
  entities: EntityMatch[];
  intent: QueryIntent;
  confidence: number;
}

// 2. Entity Context (passed to SQL Prepare)
interface EntityContext {
  lens: LensName;
  entity: { type: EntityType; id: uuid; };
  related: EntityReference[];
  action_intent?: ActionType;
}

// 3. Action Request
interface ActionRequest {
  action: ActionType;
  entity_type: EntityType;
  entity_id: uuid;
  fields: Record<string, any>;
  user_id: uuid;
  yacht_id: uuid;
}

// 4. Action Response
interface ActionResponse {
  success: boolean;
  audit_log_id: uuid;
  entity_state: EntityState;
  ledger_event: LedgerEvent;
  errors?: ActionError[];
}

// 5. Frontend Render Instruction
interface RenderInstruction {
  component: ComponentType;
  props: Record<string, any>;
  context_menu: ActionType[];
  escape_hatches: LensName[];
}
```

---

## PHASE E: TEST GENERATION

### E.1 Test Framework Structure

Create directory structure:
```
tests/
├── unit/
│   ├── work_order/
│   ├── equipment/
│   ├── fault/
│   └── ... (all 10 lenses)
├── integration/
│   ├── rls/
│   ├── actions/
│   └── cross_lens/
├── scenarios/
│   └── [lens]_scenarios.test.ts
├── edge_cases/
│   └── [lens]_edge_cases.test.ts
└── fixtures/
    └── test_data.sql
```

### E.2 Test Categories (per lens)

For EACH lens, generate:

#### Unit Tests (100 per lens)
```typescript
describe('[Lens] Unit Tests', () => {
  // Field validation
  test('rejects invalid status value', ...);
  test('requires title field', ...);
  test('validates UUID format for entity_id', ...);

  // Business logic
  test('calculates correct priority', ...);
  test('applies default values', ...);
});
```

#### RLS Tests (50 per lens)
```typescript
describe('[Lens] RLS Tests', () => {
  test('allows SELECT for same yacht user', ...);
  test('denies SELECT for different yacht user', ...);
  test('allows INSERT for authenticated user on own yacht', ...);
  test('denies INSERT for different yacht', ...);
  test('service_role bypasses RLS', ...);
});
```

#### Scenario Tests (100 per lens)
```typescript
describe('[Lens] Scenario Tests', () => {
  // Scenario 1: Basic Lookup
  test('exact match query returns entity', ...);
  test('partial match query returns ranked results', ...);
  test('typo tolerance finds correct entity', ...);

  // Scenario 2: Status Check
  test('returns current status', ...);
  test('includes status history', ...);

  // ... all 10 scenarios × 10 variations
});
```

#### Edge Case Tests (250 per lens)
```typescript
describe('[Lens] Edge Cases', () => {
  // Null handling
  test('handles null equipment_id gracefully', ...);
  test('handles null assigned_to', ...);

  // Soft delete
  test('excludes soft-deleted records from query', ...);
  test('includes soft-deleted in admin view', ...);

  // Concurrent operations
  test('handles concurrent updates', ...);
  test('maintains consistency under load', ...);

  // Boundary conditions
  test('handles max text length', ...);
  test('handles empty arrays', ...);
});
```

### E.3 Cross-Lens Tests (100 total)
```typescript
describe('Cross-Lens Integration', () => {
  test('fault → work_order escape hatch works', ...);
  test('work_order → equipment preserves context', ...);
  test('ledger shows unified history across lenses', ...);
});
```

---

## PHASE F: MONITORING SETUP

### F.1 Security Alerts

Create file: `MONITORING_CONFIG.md`

```yaml
alerts:
  - name: cross_yacht_access_attempt
    condition: "rls_denial WHERE different_yacht = true"
    severity: CRITICAL
    action: block_and_notify

  - name: bulk_data_access
    condition: "SELECT COUNT(*) > 1000 in single query"
    severity: WARNING
    action: log_and_review

  - name: action_failure_spike
    condition: "action_error_rate > 5% over 5 minutes"
    severity: HIGH
    action: notify_oncall
```

### F.2 Performance Metrics

```yaml
metrics:
  - name: query_latency_p50
    target: 100ms
    alert_threshold: 300ms

  - name: query_latency_p99
    target: 500ms
    alert_threshold: 1500ms

  - name: action_success_rate
    target: 99.9%
    alert_threshold: 95%
```

---

# COMPLETION CRITERIA

You are NOT done until:

## Documentation Complete
- [ ] 10 lenses × 10 files = 100 lens files
- [ ] Cross-lens escape hatch matrix
- [ ] Shared tables unified treatment
- [ ] Contract interfaces definition
- [ ] Monitoring configuration

## Security Fixed
- [ ] pms_work_order_notes: yacht isolation enforced
- [ ] pms_work_order_parts: yacht isolation enforced
- [ ] pms_part_usage: yacht isolation enforced
- [ ] All tables with user data: yacht isolation verified
- [ ] No USING (true) policies on user data tables

## Migrations Ready
- [ ] All security fix migrations written
- [ ] All rollback scripts written
- [ ] Migration sequence documented
- [ ] Verification queries provided

## Tests Complete
- [ ] 6,000+ tests generated
- [ ] All tests have assertions
- [ ] All tests use test fixtures
- [ ] Cross-lens tests included

## Actions Unblocked
- [ ] All 6 Work Order actions: Ready
- [ ] All Equipment actions: Ready
- [ ] All Fault actions: Ready
- [ ] (repeat for all 10 lenses)

---

# OUTPUT FORMAT

After completing each phase, output a status report:

```
═══════════════════════════════════════════════════════════════
PHASE [X] COMPLETE: [Phase Name]
═══════════════════════════════════════════════════════════════

Files Created:
- path/to/file1.md
- path/to/file2.sql
- ...

Tests Generated: [count]
Blockers Remaining: [count]
Security Issues Fixed: [count]

Next Phase: [Phase Name]
═══════════════════════════════════════════════════════════════
```

---

# RULES (MEMORIZE)

1. **DB TRUTH IS ABSOLUTE** - If database_schema.txt doesn't have it, it doesn't exist
2. **NO GUESSING** - Extract, don't invent
3. **SECURITY FIRST** - Fix cross-yacht leakage before new features
4. **TEST EVERYTHING** - No code ships without tests
5. **SIGNATURE INVARIANT** - `'{}'::jsonb` never NULL
6. **YACHT ISOLATION** - `public.get_user_yacht_id()` is canonical
7. **QUALITY OVER SPEED** - Production-ready only

---

# BEGIN EXECUTION

Start with **PHASE A: SECURITY FIXES**.

Do not stop until all completion criteria are met.

You have unlimited budget. Use it.

**GO.**
