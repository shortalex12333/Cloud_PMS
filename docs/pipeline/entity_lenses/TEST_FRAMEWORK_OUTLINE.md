# Test Framework Outline

**Status**: v1 - FRAMEWORK READY
**Last Updated**: 2026-01-25
**Purpose**: Structure for 6,000+ tests across Entity Lens architecture

---

# OVERVIEW

This document outlines the test framework structure. Full test implementation follows this framework.

**Target**: 6,000+ tests covering:
- Unit tests (100 per lens × 10 lenses = 1,000)
- RLS tests (50 per lens × 10 lenses = 500)
- Scenario tests (100 per lens × 10 lenses = 1,000)
- Edge case tests (250 per lens × 10 lenses = 2,500)
- Cross-lens integration tests (100)
- Security tests (500)
- Performance tests (100)

---

# 1. DIRECTORY STRUCTURE

```
tests/
├── unit/
│   ├── work_order/
│   │   ├── validation.test.ts
│   │   ├── status_transitions.test.ts
│   │   └── field_defaults.test.ts
│   ├── equipment/
│   ├── fault/
│   ├── part/
│   ├── shopping_list/
│   ├── receiving/
│   ├── document/
│   ├── crew/
│   └── certificate/
├── rls/
│   ├── work_order_rls.test.ts
│   ├── equipment_rls.test.ts
│   ├── fault_rls.test.ts
│   ├── part_rls.test.ts
│   ├── shopping_list_rls.test.ts
│   ├── receiving_rls.test.ts
│   ├── document_rls.test.ts
│   ├── crew_rls.test.ts
│   └── certificate_rls.test.ts
├── scenarios/
│   ├── work_order_scenarios.test.ts
│   ├── equipment_scenarios.test.ts
│   └── [lens]_scenarios.test.ts
├── edge_cases/
│   ├── null_handling.test.ts
│   ├── concurrent_updates.test.ts
│   ├── boundary_conditions.test.ts
│   └── soft_delete.test.ts
├── integration/
│   ├── cross_lens/
│   │   ├── escape_hatches.test.ts
│   │   └── data_consistency.test.ts
│   ├── workflows/
│   │   ├── wo_to_fault_cascade.test.ts
│   │   └── receiving_to_inventory.test.ts
│   └── api/
│       └── action_endpoints.test.ts
├── security/
│   ├── yacht_isolation.test.ts
│   ├── role_permissions.test.ts
│   └── injection_prevention.test.ts
├── performance/
│   ├── query_latency.test.ts
│   └── concurrent_load.test.ts
└── fixtures/
    ├── test_data.sql
    ├── yacht_a_data.sql
    ├── yacht_b_data.sql
    └── factories.ts
```

---

# 2. TEST CATEGORIES

## 2.1 Unit Tests (per lens)

```typescript
// Example: work_order/validation.test.ts
describe('Work Order Unit Tests', () => {
  describe('Field Validation', () => {
    test('rejects empty title', async () => {
      await expect(createWorkOrder({ title: '' }))
        .rejects.toThrow('title cannot be empty');
    });

    test('rejects invalid status value', async () => {
      await expect(createWorkOrder({ status: 'invalid' }))
        .rejects.toThrow('invalid status');
    });

    test('rejects invalid priority value', async () => {
      await expect(createWorkOrder({ priority: 'super_urgent' }))
        .rejects.toThrow('invalid priority');
    });

    test('validates UUID format for equipment_id', async () => {
      await expect(createWorkOrder({ equipment_id: 'not-uuid' }))
        .rejects.toThrow('invalid uuid');
    });
  });

  describe('Default Values', () => {
    test('applies default status of "planned"', async () => {
      const wo = await createWorkOrder({ title: 'Test' });
      expect(wo.status).toBe('planned');
    });

    test('applies default priority of "routine"', async () => {
      const wo = await createWorkOrder({ title: 'Test' });
      expect(wo.priority).toBe('routine');
    });

    test('auto-generates wo_number', async () => {
      const wo = await createWorkOrder({ title: 'Test' });
      expect(wo.wo_number).toMatch(/^WO-\d{4}-\d{4}$/);
    });
  });

  describe('Business Logic', () => {
    test('sets completed_at when status becomes completed', async () => {
      const wo = await createWorkOrder({ title: 'Test' });
      const updated = await updateWorkOrder(wo.id, { status: 'completed' });
      expect(updated.completed_at).toBeTruthy();
    });

    test('creates fault when type is breakdown', async () => {
      const wo = await createWorkOrder({
        title: 'Breakdown',
        type: 'breakdown',
        equipment_id: testEquipmentId
      });
      const fault = await getFaultByWorkOrderId(wo.id);
      expect(fault).toBeTruthy();
      expect(fault.title).toBe('Breakdown');
    });
  });
});
```

## 2.2 RLS Tests (per lens)

```typescript
// Example: work_order_rls.test.ts
describe('Work Order RLS Tests', () => {
  describe('SELECT Policies', () => {
    test('allows SELECT for same yacht user', async () => {
      const result = await asUser(yachtAUser).query(
        'SELECT * FROM pms_work_orders WHERE id = $1',
        [yachtAWorkOrderId]
      );
      expect(result.rows).toHaveLength(1);
    });

    test('denies SELECT for different yacht user', async () => {
      const result = await asUser(yachtBUser).query(
        'SELECT * FROM pms_work_orders WHERE id = $1',
        [yachtAWorkOrderId]
      );
      expect(result.rows).toHaveLength(0);
    });

    test('service_role bypasses RLS', async () => {
      const result = await asServiceRole().query(
        'SELECT * FROM pms_work_orders'
      );
      expect(result.rows.length).toBeGreaterThan(0);
    });
  });

  describe('INSERT Policies', () => {
    test('allows INSERT for authenticated user on own yacht', async () => {
      const result = await asUser(engineerUser).query(
        'INSERT INTO pms_work_orders (yacht_id, title, ...) VALUES ($1, $2, ...)',
        [engineerUser.yacht_id, 'Test WO']
      );
      expect(result.rowCount).toBe(1);
    });

    test('denies INSERT for different yacht', async () => {
      await expect(
        asUser(yachtAUser).query(
          'INSERT INTO pms_work_orders (yacht_id, ...) VALUES ($1, ...)',
          [yachtBId]
        )
      ).rejects.toThrow('RLS');
    });

    test('denies INSERT for non-engineer role', async () => {
      await expect(
        asUser(crewUser).query(
          'INSERT INTO pms_work_orders ...'
        )
      ).rejects.toThrow('permission denied');
    });
  });

  describe('UPDATE Policies', () => {
    test('allows UPDATE for engineer on own yacht', async () => {
      const result = await asUser(engineerUser).query(
        'UPDATE pms_work_orders SET title = $1 WHERE id = $2',
        ['Updated', ownWorkOrderId]
      );
      expect(result.rowCount).toBe(1);
    });

    test('denies UPDATE for different yacht work order', async () => {
      const result = await asUser(yachtAUser).query(
        'UPDATE pms_work_orders SET title = $1 WHERE id = $2',
        ['Hacked', yachtBWorkOrderId]
      );
      expect(result.rowCount).toBe(0);
    });
  });

  describe('DELETE Policies', () => {
    test('allows soft delete for manager', async () => {
      const result = await asUser(managerUser).query(
        'UPDATE pms_work_orders SET deleted_at = NOW() WHERE id = $1',
        [workOrderId]
      );
      expect(result.rowCount).toBe(1);
    });

    test('prevents hard delete via trigger', async () => {
      await expect(
        asUser(managerUser).query(
          'DELETE FROM pms_work_orders WHERE id = $1',
          [workOrderId]
        )
      ).rejects.toThrow('hard delete not allowed');
    });
  });
});
```

## 2.3 Scenario Tests (per lens)

```typescript
// Example: work_order_scenarios.test.ts
describe('Work Order Scenario Tests', () => {
  describe('Scenario 1: Basic Lookup', () => {
    test('exact match query returns work order', async () => {
      const result = await query("WO-2026-0045");
      expect(result.entities[0].entity_type).toBe('work_order');
      expect(result.entities[0].display_name).toContain('WO-2026-0045');
    });

    test('partial title match returns ranked results', async () => {
      const result = await query("generator maintenance");
      expect(result.entities.length).toBeGreaterThan(0);
      expect(result.entities[0].match_reason).toBe('semantic');
    });

    test('typo tolerance finds correct work order', async () => {
      const result = await query("WO-2026-004S"); // S instead of 5
      expect(result.entities[0].display_name).toContain('WO-2026-0045');
    });
  });

  describe('Scenario 2: Status Check', () => {
    test('returns current status', async () => {
      const result = await query("what's the status of WO-2026-0045");
      expect(result.intent.type).toBe('status_check');
      expect(result.entities[0].preview.status).toBeDefined();
    });
  });

  describe('Scenario 3: Create Work Order', () => {
    test('action intent detected', async () => {
      const result = await query("create work order for generator");
      expect(result.intent.type).toBe('action_request');
      expect(result.intent.action_hint).toBe('create_work_order');
    });
  });

  // ... 10 scenarios × 10 variations each
});
```

## 2.4 Edge Case Tests

```typescript
// Example: edge_cases/null_handling.test.ts
describe('Null Handling Edge Cases', () => {
  describe('Work Order', () => {
    test('handles null equipment_id gracefully', async () => {
      const wo = await createWorkOrder({
        title: 'No Equipment',
        equipment_id: null
      });
      expect(wo.equipment_id).toBeNull();
    });

    test('handles null assigned_to', async () => {
      const wo = await createWorkOrder({
        title: 'Unassigned',
        assigned_to: null
      });
      expect(wo.assigned_to).toBeNull();
    });

    test('handles null fault_id in escape hatch', async () => {
      const wo = await createWorkOrder({ title: 'No Fault' });
      const escapeHatch = await getEscapeHatch(wo.id, 'fault');
      expect(escapeHatch.available).toBe(false);
      expect(escapeHatch.unavailable_reason).toBe('No fault linked');
    });
  });

  describe('Soft Delete', () => {
    test('excludes soft-deleted records from query', async () => {
      const wo = await createWorkOrder({ title: 'To Delete' });
      await softDelete('pms_work_orders', wo.id);
      const result = await query("To Delete");
      expect(result.entities).toHaveLength(0);
    });

    test('includes soft-deleted in admin view', async () => {
      const wo = await createWorkOrder({ title: 'Deleted WO' });
      await softDelete('pms_work_orders', wo.id);
      const result = await adminQuery("Deleted WO", { include_deleted: true });
      expect(result.entities).toHaveLength(1);
    });
  });

  describe('Concurrent Operations', () => {
    test('handles concurrent status updates', async () => {
      const wo = await createWorkOrder({ title: 'Concurrent Test' });
      const [result1, result2] = await Promise.all([
        updateWorkOrder(wo.id, { status: 'in_progress' }),
        updateWorkOrder(wo.id, { status: 'completed' })
      ]);
      // One should succeed, one should see stale data
      expect([result1.status, result2.status]).toContain('in_progress');
    });
  });

  describe('Boundary Conditions', () => {
    test('handles max text length for title', async () => {
      const longTitle = 'A'.repeat(1000);
      const wo = await createWorkOrder({ title: longTitle });
      expect(wo.title.length).toBe(1000);
    });

    test('handles empty arrays', async () => {
      const doc = await createDocument({
        equipment_ids: [],
        tags: []
      });
      expect(doc.equipment_ids).toEqual([]);
    });
  });
});
```

## 2.5 Cross-Lens Integration Tests

```typescript
// Example: integration/cross_lens/escape_hatches.test.ts
describe('Cross-Lens Integration', () => {
  describe('Escape Hatches', () => {
    test('fault → work_order escape hatch works', async () => {
      // Create WO with fault
      const wo = await createWorkOrder({
        title: 'Breakdown',
        type: 'breakdown',
        equipment_id: equipmentId
      });
      const fault = await getFaultByWorkOrderId(wo.id);

      // Navigate via escape hatch
      const escapeHatch = await executeEscapeHatch(
        'fault',
        fault.id,
        'view_linked_work_order'
      );

      expect(escapeHatch.target_lens).toBe('work_order');
      expect(escapeHatch.target_entity_id).toBe(wo.id);
    });

    test('work_order → equipment preserves context', async () => {
      const wo = await createWorkOrder({
        title: 'Equipment WO',
        equipment_id: equipmentId
      });

      const escapeHatch = await executeEscapeHatch(
        'work_order',
        wo.id,
        'view_equipment'
      );

      expect(escapeHatch.context.source_lens).toBe('work_order');
      expect(escapeHatch.context.source_entity_id).toBe(wo.id);
    });
  });

  describe('Cascading Updates', () => {
    test('WO completion cascades to fault status', async () => {
      const wo = await createWorkOrder({
        title: 'Breakdown',
        type: 'breakdown',
        equipment_id: equipmentId
      });
      const fault = await getFaultByWorkOrderId(wo.id);

      // Complete WO
      await updateWorkOrder(wo.id, { status: 'completed' });

      // Check fault status
      const updatedFault = await getFault(fault.id);
      expect(updatedFault.status).toBe('resolved');
      expect(updatedFault.resolved_at).toBeTruthy();
    });

    test('receiving completion updates part quantities', async () => {
      const event = await createReceivingEvent();
      await addReceivingLineItem(event.id, {
        part_id: partId,
        quantity_received: 10,
        quantity_accepted: 10,
        disposition: 'accepted'
      });

      const partBefore = await getPart(partId);
      await completeReceivingEvent(event.id);
      const partAfter = await getPart(partId);

      expect(partAfter.quantity_on_hand)
        .toBe(partBefore.quantity_on_hand + 10);
    });
  });
});
```

## 2.6 Security Tests

```typescript
// Example: security/yacht_isolation.test.ts
describe('Yacht Isolation Security', () => {
  test('cannot access other yacht work orders via direct ID', async () => {
    const result = await asUser(yachtAUser).query(
      'SELECT * FROM pms_work_orders WHERE id = $1',
      [yachtBWorkOrderId]
    );
    expect(result.rows).toHaveLength(0);
  });

  test('cannot update other yacht equipment', async () => {
    const result = await asUser(yachtAUser).query(
      'UPDATE pms_equipment SET name = $1 WHERE id = $2',
      ['Hacked', yachtBEquipmentId]
    );
    expect(result.rowCount).toBe(0);
  });

  test('cannot insert into other yacht', async () => {
    await expect(
      asUser(yachtAUser).query(
        'INSERT INTO pms_work_orders (yacht_id, title) VALUES ($1, $2)',
        [yachtBId, 'Malicious WO']
      )
    ).rejects.toThrow();
  });

  test('get_user_yacht_id returns correct yacht', async () => {
    const result = await asUser(yachtAUser).query(
      'SELECT public.get_user_yacht_id()'
    );
    expect(result.rows[0].get_user_yacht_id).toBe(yachtAId);
  });

  test('cannot spoof yacht_id in JWT', async () => {
    const spoofedToken = createToken({ yacht_id: yachtBId });
    const result = await withToken(spoofedToken).query(
      'SELECT * FROM pms_work_orders'
    );
    // Should still use get_user_yacht_id from profile, not JWT
    expect(result.rows.every(r => r.yacht_id === yachtAId)).toBe(true);
  });
});
```

---

# 3. FIXTURES

## Test Data Factory

```typescript
// fixtures/factories.ts
export const factories = {
  workOrder: (overrides = {}) => ({
    id: uuid(),
    yacht_id: testYachtId,
    title: faker.lorem.sentence(),
    description: faker.lorem.paragraph(),
    type: 'scheduled',
    priority: 'routine',
    status: 'planned',
    created_by: testUserId,
    created_at: new Date(),
    updated_at: new Date(),
    ...overrides
  }),

  equipment: (overrides = {}) => ({
    id: uuid(),
    yacht_id: testYachtId,
    name: faker.commerce.productName(),
    code: `EQ-${faker.string.alphanumeric(4).toUpperCase()}`,
    status: 'operational',
    criticality: 'medium',
    created_at: new Date(),
    updated_at: new Date(),
    ...overrides
  }),

  // ... factories for all entities
};
```

## Seed Data SQL

```sql
-- fixtures/test_data.sql
-- Yacht A (test yacht)
INSERT INTO yacht_registry (id, name) VALUES
  ('yacht-a-uuid', 'Test Yacht Alpha');

-- Users for Yacht A
INSERT INTO auth_users_profiles (id, yacht_id, email, name) VALUES
  ('user-a-engineer', 'yacht-a-uuid', 'engineer@alpha.yacht', 'Engineer Alpha'),
  ('user-a-crew', 'yacht-a-uuid', 'crew@alpha.yacht', 'Crew Alpha');

-- Equipment for Yacht A
INSERT INTO pms_equipment (id, yacht_id, name, code, status) VALUES
  ('equip-a-1', 'yacht-a-uuid', 'Main Engine #1', 'ME-01', 'operational'),
  ('equip-a-2', 'yacht-a-uuid', 'Generator #1', 'GEN-01', 'operational');

-- Yacht B (isolation test yacht)
INSERT INTO yacht_registry (id, name) VALUES
  ('yacht-b-uuid', 'Test Yacht Bravo');

-- Users for Yacht B
INSERT INTO auth_users_profiles (id, yacht_id, email, name) VALUES
  ('user-b-engineer', 'yacht-b-uuid', 'engineer@bravo.yacht', 'Engineer Bravo');

-- Equipment for Yacht B
INSERT INTO pms_equipment (id, yacht_id, name, code, status) VALUES
  ('equip-b-1', 'yacht-b-uuid', 'Main Engine #1', 'ME-01', 'operational');
```

---

# 4. TEST EXECUTION

## Commands

```bash
# Run all tests
npm test

# Run specific category
npm test -- --grep "RLS"
npm test -- --grep "Security"

# Run specific lens
npm test -- tests/unit/work_order
npm test -- tests/rls/work_order_rls.test.ts

# Run with coverage
npm test -- --coverage

# Run in CI mode
npm test -- --ci --reporters=default --reporters=jest-junit
```

## CI Pipeline

```yaml
# .github/workflows/tests.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: supabase/postgres
    steps:
      - uses: actions/checkout@v4
      - name: Setup Node
        uses: actions/setup-node@v4
      - name: Install dependencies
        run: npm ci
      - name: Run migrations
        run: npm run db:migrate
      - name: Seed test data
        run: npm run db:seed:test
      - name: Run tests
        run: npm test -- --ci
      - name: Upload coverage
        uses: codecov/codecov-action@v4
```

---

# 5. COVERAGE REQUIREMENTS

| Category | Minimum Coverage |
|----------|------------------|
| Unit Tests | 90% |
| RLS Tests | 100% (all policies) |
| Scenario Tests | 80% |
| Integration Tests | 75% |
| Security Tests | 100% (all vulnerabilities) |

---

**END OF TEST FRAMEWORK OUTLINE**
