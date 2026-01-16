/**
 * RLS Permission Tests
 *
 * Phase 12: Tests Row Level Security and Role-Based Access Control
 *
 * Test Categories:
 * 1. Yacht Isolation - Users can ONLY access their yacht's data
 * 2. Role Permissions - Actions restricted by user role
 * 3. Cross-Tenant Denial - Cannot access other yacht's data
 *
 * Based on:
 * - RLS migration files (yacht_id isolation)
 * - p1_purchasing_handlers.py (PURCHASE_APPROVER_ROLES)
 * - purchasing_mutation_handlers.py (delivery roles)
 * - ACTION_OFFERING_RULES.md (role restrictions)
 */

import { test, expect } from '@playwright/test';
import {
  saveArtifact,
  saveRequest,
  saveResponse,
  createEvidenceBundle,
} from '../../helpers/artifacts';
import { ApiClient } from '../../helpers/api-client';
import { getTenantClient } from '../../helpers/supabase_tenant';
import {
  TEST_USERS,
  TEST_YACHT_ID,
  OTHER_YACHT_ID,
  PURCHASE_APPROVER_ROLES,
  DELIVERY_RECEIVER_ROLES,
  WO_ASSIGNMENT_ROLES,
  HOD_ROLES,
  UserRole,
  getPrimaryTestUser,
} from '../../fixtures/test_users';

// ============================================================================
// ROLE-ACTION MATRIX
// ============================================================================

/**
 * Defines which roles can perform which actions.
 *
 * Structure:
 * - action: The microaction name
 * - allowedRoles: Roles that SHOULD be able to execute
 * - deniedRoles: Roles that should be DENIED
 * - expectedDeniedStatus: 403 (Forbidden) or 401 (Unauthorized)
 */
interface RoleActionRule {
  action: string;
  description: string;
  allowedRoles: UserRole[];
  deniedRoles: UserRole[];
  expectedDeniedStatus: 403 | 401 | 400;
  requiresEntity?: string; // Entity type needed for test
}

export const ROLE_ACTION_MATRIX: RoleActionRule[] = [
  // =========================================================================
  // PURCHASING ACTIONS - Role restricted
  // =========================================================================
  {
    action: 'approve_purchase',
    description: 'Approve purchase orders - HOD only',
    allowedRoles: ['captain', 'chief_engineer', 'chief_officer', 'admin', 'owner'],
    deniedRoles: ['member', 'crew', 'eto', 'engineer'],
    expectedDeniedStatus: 403,
    requiresEntity: 'purchase_order',
  },
  {
    action: 'log_delivery_received',
    description: 'Log delivery received - Senior roles only',
    allowedRoles: ['chief_engineer', 'chief_officer', 'captain', 'admin'],
    deniedRoles: ['member', 'crew', 'eto', 'engineer'],
    expectedDeniedStatus: 403,
    requiresEntity: 'purchase_order',
  },
  {
    action: 'create_purchase_request',
    description: 'Create purchase request - Engineering+ roles',
    allowedRoles: ['chief_engineer', 'eto', 'captain', 'manager', 'admin'],
    deniedRoles: ['member', 'crew'],
    expectedDeniedStatus: 403,
  },

  // =========================================================================
  // WORK ORDER ACTIONS - Role restricted
  // =========================================================================
  {
    action: 'assign_work_order',
    description: 'Assign work orders - HOD only',
    allowedRoles: ['chief_engineer', 'eto', 'captain', 'manager', 'admin'],
    deniedRoles: ['member', 'crew', 'engineer'],
    expectedDeniedStatus: 403,
    requiresEntity: 'work_order',
  },
  {
    action: 'mark_work_order_complete',
    description: 'Mark work order complete - Engineering roles',
    allowedRoles: ['engineer', '2nd_engineer', 'chief_engineer', 'eto', 'captain', 'admin'],
    deniedRoles: ['member', 'crew'],
    expectedDeniedStatus: 403,
    requiresEntity: 'work_order',
  },
  {
    action: 'create_work_order',
    description: 'Create work orders - Engineering+ roles',
    allowedRoles: ['engineer', '2nd_engineer', 'chief_engineer', 'eto', 'captain', 'admin'],
    deniedRoles: ['member', 'crew'],
    expectedDeniedStatus: 403,
  },

  // =========================================================================
  // WORKLIST ACTIONS - Role restricted
  // =========================================================================
  {
    action: 'tag_for_survey',
    description: 'Tag items for survey - HOD only',
    allowedRoles: ['chief_engineer', 'eto', 'captain', 'manager', 'admin'],
    deniedRoles: ['member', 'crew', 'engineer'],
    expectedDeniedStatus: 403,
    requiresEntity: 'worklist_item',
  },
  {
    action: 'export_worklist',
    description: 'Export worklist - HOD only',
    allowedRoles: ['chief_engineer', 'eto', 'captain', 'manager', 'admin'],
    deniedRoles: ['member', 'crew', 'engineer'],
    expectedDeniedStatus: 403,
  },

  // =========================================================================
  // INVENTORY ACTIONS - Role restricted
  // =========================================================================
  {
    action: 'order_part',
    description: 'Order parts - HOD only',
    allowedRoles: ['chief_engineer', 'eto', 'captain', 'manager', 'admin'],
    deniedRoles: ['member', 'crew'],
    expectedDeniedStatus: 403,
    requiresEntity: 'part',
  },
  {
    action: 'log_part_usage',
    description: 'Log part usage - Engineering roles',
    allowedRoles: ['engineer', '2nd_engineer', 'chief_engineer', 'eto'],
    deniedRoles: ['member', 'crew'],
    expectedDeniedStatus: 403,
    requiresEntity: 'part',
  },

  // =========================================================================
  // UNIVERSAL ACTIONS - All roles allowed
  // =========================================================================
  {
    action: 'add_fault_note',
    description: 'Add note to fault - All roles',
    allowedRoles: ['member', 'crew', 'eto', 'engineer', 'chief_engineer', 'captain', 'admin'],
    deniedRoles: [],
    expectedDeniedStatus: 403,
    requiresEntity: 'fault',
  },
  {
    action: 'view_fault_history',
    description: 'View fault history - All roles',
    allowedRoles: ['member', 'crew', 'eto', 'engineer', 'chief_engineer', 'captain', 'admin'],
    deniedRoles: [],
    expectedDeniedStatus: 403,
    requiresEntity: 'fault',
  },
  {
    action: 'view_equipment_details',
    description: 'View equipment details - All roles',
    allowedRoles: ['member', 'crew', 'eto', 'engineer', 'chief_engineer', 'captain', 'admin'],
    deniedRoles: [],
    expectedDeniedStatus: 403,
    requiresEntity: 'equipment',
  },
];

// ============================================================================
// TEST SETUP
// ============================================================================

test.describe('RLS Permission Tests', () => {
  let apiClient: ApiClient;
  let tenantClient: ReturnType<typeof getTenantClient>;

  // Test entity IDs
  let testFaultId: string | null = null;
  let testWorkOrderId: string | null = null;
  let testEquipmentId: string | null = null;
  let testPartId: string | null = null;
  let testPurchaseOrderId: string | null = null;

  test.beforeAll(async () => {
    apiClient = new ApiClient();
    await apiClient.ensureAuth();
    tenantClient = getTenantClient();

    // Get real entity IDs for testing
    const [faultResult, woResult, equipResult, partResult, poResult] = await Promise.all([
      tenantClient.from('pms_faults').select('id').eq('yacht_id', TEST_YACHT_ID).limit(1).maybeSingle(),
      tenantClient.from('pms_work_orders').select('id').eq('yacht_id', TEST_YACHT_ID).limit(1).maybeSingle(),
      tenantClient.from('pms_equipment').select('id').eq('yacht_id', TEST_YACHT_ID).limit(1).maybeSingle(),
      tenantClient.from('pms_parts').select('id').eq('yacht_id', TEST_YACHT_ID).limit(1).maybeSingle(),
      tenantClient.from('pms_purchase_orders').select('id').eq('yacht_id', TEST_YACHT_ID).limit(1).maybeSingle(),
    ]);

    testFaultId = faultResult.data?.id || null;
    testWorkOrderId = woResult.data?.id || null;
    testEquipmentId = equipResult.data?.id || null;
    testPartId = partResult.data?.id || null;
    testPurchaseOrderId = poResult.data?.id || null;

    console.log('Test entities:', {
      fault: testFaultId,
      workOrder: testWorkOrderId,
      equipment: testEquipmentId,
      part: testPartId,
      purchaseOrder: testPurchaseOrderId,
    });
  });

  // ==========================================================================
  // YACHT ISOLATION TESTS - RLS enforces yacht boundaries
  // ==========================================================================

  test.describe('Yacht Isolation (RLS)', () => {
    test('RLS-01: User can access own yacht data', async () => {
      const testName = 'rls/yacht-isolation/own-yacht';

      // Query work orders for test yacht
      const response = await apiClient.executeAction('view_work_order_history', {
        yacht_id: TEST_YACHT_ID,
      });

      saveRequest(testName, response.request);
      saveResponse(testName, { status: response.status, body: response.data });

      createEvidenceBundle(testName, {
        test: 'Own yacht data access',
        yachtId: TEST_YACHT_ID,
        responseStatus: response.status,
        hasData: !!response.data,
        result: response.status !== 403 ? 'PASS' : 'FAIL',
      });

      // Should be able to access (200 or 404 if no data)
      expect([200, 404]).toContain(response.status);
    });

    test('RLS-02: User cannot access other yacht data', async () => {
      const testName = 'rls/yacht-isolation/other-yacht';

      // Attempt to query work orders for DIFFERENT yacht
      const response = await apiClient.executeAction('view_work_order_history', {
        yacht_id: OTHER_YACHT_ID,
      });

      saveRequest(testName, response.request);
      saveResponse(testName, { status: response.status, body: response.data });

      // Check if response contains data
      const hasData = response.data?.data?.work_orders?.length > 0 ||
                     response.data?.work_orders?.length > 0 ||
                     (Array.isArray(response.data) && response.data.length > 0);

      createEvidenceBundle(testName, {
        test: 'Other yacht data denied',
        yachtId: OTHER_YACHT_ID,
        responseStatus: response.status,
        hasData,
        result: !hasData ? 'PASS' : 'FAIL - DATA LEAKED',
      });

      // Should either fail (403/404) or return empty data
      if (response.status === 200) {
        expect(hasData).toBe(false);
      }
    });

    test('RLS-03: Cross-tenant fault access denied', async () => {
      const testName = 'rls/yacht-isolation/cross-fault';

      if (!testFaultId) {
        test.skip();
        return;
      }

      // Try to access fault but with wrong yacht_id
      const response = await apiClient.executeAction('view_fault_detail', {
        fault_id: testFaultId,
        yacht_id: OTHER_YACHT_ID, // Wrong yacht
      });

      saveRequest(testName, response.request);
      saveResponse(testName, { status: response.status, body: response.data });

      const dataReturned = response.data?.fault || response.data?.data?.fault;

      createEvidenceBundle(testName, {
        test: 'Cross-tenant fault denied',
        faultId: testFaultId,
        requestedYachtId: OTHER_YACHT_ID,
        responseStatus: response.status,
        dataReturned: !!dataReturned,
        result: !dataReturned ? 'PASS' : 'FAIL - CROSS-TENANT LEAK',
      });

      // Should not return fault data
      expect(dataReturned).toBeFalsy();
    });
  });

  // ==========================================================================
  // ROLE PERMISSION TESTS - Using primary test user
  // ==========================================================================

  test.describe('Role Permissions (Primary User: chief_engineer)', () => {
    const primaryUser = getPrimaryTestUser();

    // Test actions the chief_engineer SHOULD be able to do
    const allowedActions = ROLE_ACTION_MATRIX.filter(rule =>
      rule.allowedRoles.includes(primaryUser.role as UserRole)
    );

    for (const rule of allowedActions) {
      test(`ALLOWED: ${rule.action} - ${rule.description}`, async () => {
        const testName = `rls/role/${primaryUser.role}/allowed/${rule.action}`;

        // Build payload based on action
        const payload = buildTestPayload(rule.action, {
          faultId: testFaultId,
          workOrderId: testWorkOrderId,
          equipmentId: testEquipmentId,
          partId: testPartId,
          purchaseOrderId: testPurchaseOrderId,
          yachtId: TEST_YACHT_ID,
          userRole: primaryUser.role,
        });

        const response = await apiClient.executeAction(rule.action, payload);

        saveRequest(testName, response.request);
        saveResponse(testName, { status: response.status, body: response.data });

        const isAllowed = response.status !== 403 && response.status !== 401;

        createEvidenceBundle(testName, {
          action: rule.action,
          description: rule.description,
          userRole: primaryUser.role,
          allowedRoles: rule.allowedRoles,
          responseStatus: response.status,
          isAllowed,
          expectedResult: 'ALLOWED',
          actualResult: isAllowed ? 'ALLOWED' : 'DENIED',
          testResult: isAllowed ? 'PASS' : 'FAIL',
        });

        // Should NOT be forbidden (could be 200, 404, 400, 500)
        expect(response.status).not.toBe(403);
      });
    }

    // Test actions chief_engineer should NOT be able to do (if any)
    const deniedActions = ROLE_ACTION_MATRIX.filter(rule =>
      rule.deniedRoles.includes(primaryUser.role as UserRole)
    );

    for (const rule of deniedActions) {
      test(`DENIED: ${rule.action} - ${rule.description}`, async () => {
        const testName = `rls/role/${primaryUser.role}/denied/${rule.action}`;

        const payload = buildTestPayload(rule.action, {
          faultId: testFaultId,
          workOrderId: testWorkOrderId,
          equipmentId: testEquipmentId,
          partId: testPartId,
          purchaseOrderId: testPurchaseOrderId,
          yachtId: TEST_YACHT_ID,
          userRole: primaryUser.role,
        });

        const response = await apiClient.executeAction(rule.action, payload);

        saveRequest(testName, response.request);
        saveResponse(testName, { status: response.status, body: response.data });

        const isDenied = response.status === 403 || response.status === 401;

        createEvidenceBundle(testName, {
          action: rule.action,
          description: rule.description,
          userRole: primaryUser.role,
          deniedRoles: rule.deniedRoles,
          responseStatus: response.status,
          isDenied,
          expectedResult: 'DENIED',
          actualResult: isDenied ? 'DENIED' : 'ALLOWED',
          testResult: isDenied ? 'PASS' : 'FAIL - PERMISSION LEAK',
        });

        expect(response.status).toBe(rule.expectedDeniedStatus);
      });
    }
  });

  // ==========================================================================
  // PURCHASE APPROVAL ROLE TESTS
  // ==========================================================================

  test.describe('Purchase Approval Roles', () => {
    test('RLS-PURCHASE-01: PURCHASE_APPROVER_ROLES verified', async () => {
      const testName = 'rls/purchase/approver-roles';

      createEvidenceBundle(testName, {
        test: 'Purchase approver roles definition',
        expectedRoles: PURCHASE_APPROVER_ROLES,
        source: 'p1_purchasing_handlers.py line 41',
        description: 'Only these roles can approve purchase orders',
      });

      // Verify the expected roles match
      expect(PURCHASE_APPROVER_ROLES).toContain('captain');
      expect(PURCHASE_APPROVER_ROLES).toContain('chief_engineer');
      expect(PURCHASE_APPROVER_ROLES).toContain('chief_officer');
      expect(PURCHASE_APPROVER_ROLES).toContain('admin');
      expect(PURCHASE_APPROVER_ROLES).toContain('owner');
      expect(PURCHASE_APPROVER_ROLES).not.toContain('member');
      expect(PURCHASE_APPROVER_ROLES).not.toContain('crew');
    });

    test('RLS-PURCHASE-02: chief_engineer can approve purchase', async () => {
      const testName = 'rls/purchase/chief-engineer-approve';

      if (!testPurchaseOrderId) {
        saveArtifact('skip_reason.json', { reason: 'No purchase order available' }, testName);
        test.skip();
        return;
      }

      const response = await apiClient.executeAction('approve_purchase', {
        purchase_order_id: testPurchaseOrderId,
        yacht_id: TEST_YACHT_ID,
        user_role: 'chief_engineer',
        approval_notes: 'RLS test approval',
      });

      saveRequest(testName, response.request);
      saveResponse(testName, { status: response.status, body: response.data });

      // Should not be forbidden (may fail for other reasons like wrong status)
      const isNotForbidden = response.status !== 403;

      createEvidenceBundle(testName, {
        action: 'approve_purchase',
        userRole: 'chief_engineer',
        responseStatus: response.status,
        isNotForbidden,
        result: isNotForbidden ? 'ROLE ALLOWED' : 'ROLE DENIED',
      });

      expect(response.status).not.toBe(403);
    });
  });

  // ==========================================================================
  // SUMMARY TEST
  // ==========================================================================

  test('RLS-SUMMARY: Generate permission matrix report', async () => {
    const testName = 'rls/SUMMARY';
    const primaryUser = getPrimaryTestUser();

    const summary = {
      totalRules: ROLE_ACTION_MATRIX.length,
      primaryTestUser: primaryUser,
      testEntitiesAvailable: {
        fault: !!testFaultId,
        workOrder: !!testWorkOrderId,
        equipment: !!testEquipmentId,
        part: !!testPartId,
        purchaseOrder: !!testPurchaseOrderId,
      },
      roleActionMatrix: ROLE_ACTION_MATRIX.map(rule => ({
        action: rule.action,
        description: rule.description,
        allowedRoles: rule.allowedRoles,
        deniedRoles: rule.deniedRoles,
        primaryUserAllowed: rule.allowedRoles.includes(primaryUser.role as UserRole),
      })),
      purchaseApproverRoles: PURCHASE_APPROVER_ROLES,
      deliveryReceiverRoles: DELIVERY_RECEIVER_ROLES,
      hodRoles: HOD_ROLES,
      woAssignmentRoles: WO_ASSIGNMENT_ROLES,
    };

    saveArtifact('permission_matrix.json', summary, testName);

    createEvidenceBundle(testName, summary);

    // Log summary
    console.log('\n========================================');
    console.log('RLS PERMISSION MATRIX SUMMARY');
    console.log('========================================');
    console.log(`Total role rules: ${summary.totalRules}`);
    console.log(`Primary test user: ${primaryUser.email} (${primaryUser.role})`);
    console.log(`\nPurchase approver roles: ${PURCHASE_APPROVER_ROLES.join(', ')}`);
    console.log(`HOD roles: ${HOD_ROLES.join(', ')}`);
    console.log('========================================\n');

    expect(summary.totalRules).toBeGreaterThan(0);
  });
});

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

interface TestPayloadContext {
  faultId: string | null;
  workOrderId: string | null;
  equipmentId: string | null;
  partId: string | null;
  purchaseOrderId: string | null;
  yachtId: string;
  userRole: string;
}

function buildTestPayload(action: string, context: TestPayloadContext): Record<string, any> {
  const base = {
    yacht_id: context.yachtId,
    user_role: context.userRole,
  };

  switch (action) {
    case 'approve_purchase':
      return {
        ...base,
        purchase_order_id: context.purchaseOrderId,
        approval_notes: 'RLS test',
      };

    case 'log_delivery_received':
      return {
        ...base,
        purchase_order_id: context.purchaseOrderId,
        received_items: [],
      };

    case 'create_purchase_request':
      return {
        ...base,
        notes: 'RLS test purchase request',
      };

    case 'assign_work_order':
      return {
        ...base,
        work_order_id: context.workOrderId,
        assignee_id: 'test-assignee',
      };

    case 'mark_work_order_complete':
      return {
        ...base,
        work_order_id: context.workOrderId,
        completion_notes: 'RLS test completion',
      };

    case 'create_work_order':
      return {
        ...base,
        title: 'RLS Test Work Order',
        description: 'Created for RLS testing',
        priority: 'routine',
      };

    case 'tag_for_survey':
      return {
        ...base,
        item_id: context.workOrderId,
        survey_notes: 'RLS test tag',
      };

    case 'export_worklist':
      return {
        ...base,
        format: 'pdf',
      };

    case 'order_part':
      return {
        ...base,
        part_id: context.partId,
        quantity: 1,
        purchase_order_id: context.purchaseOrderId,
      };

    case 'log_part_usage':
      return {
        ...base,
        part_id: context.partId,
        quantity: 1,
        work_order_id: context.workOrderId,
      };

    case 'add_fault_note':
      return {
        ...base,
        fault_id: context.faultId,
        entity_type: 'fault',
        entity_id: context.faultId,
        note_text: 'RLS test note',
      };

    case 'view_fault_history':
      return {
        ...base,
        entity_id: context.faultId,
      };

    case 'view_equipment_details':
      return {
        ...base,
        equipment_id: context.equipmentId,
      };

    default:
      return base;
  }
}
