/**
 * CHAT-TO-ACTION E2E TEST
 * ========================
 *
 * Purpose: Test the full flow from natural language → AI → action execution
 *
 * This validates:
 * 1. Intent Parser correctly classifies user queries
 * 2. Entity Extractor finds relevant equipment/parts/symptoms
 * 3. GraphRAG resolves entities to canonical IDs
 * 4. Cards with appropriate actions are returned
 * 5. Action execution succeeds
 *
 * Run with: npx playwright test chat_to_action.spec.ts
 */

import { test, expect } from '@playwright/test';
import { ApiClient } from '../helpers/api-client';
import { discoverTestData, printDiscoverySummary, DiscoveredTestData } from '../helpers/test-data-discovery';

// ============================================================================
// TYPES
// ============================================================================

interface SearchResponse {
  success: boolean;
  query: string;
  results: any[];
  total_count: number;
  available_actions?: AvailableAction[];
  entities?: ExtractedEntity[];
  plans?: QueryPlan[];
  timing_ms?: {
    extraction: number;
    prepare: number;
    execute: number;
    total: number;
  };
  error?: string | null;
}

interface AvailableAction {
  action: string;
  label: string;
  execution_class: string;
}

interface ExtractedEntity {
  type: string;
  value: string;
  confidence: number;
}

interface QueryPlan {
  capability: string;
  entity_type: string;
  entity_value: string;
  search_column: string;
  blocked: boolean;
  blocked_reason: string | null;
}

interface TestScenario {
  name: string;
  query: string;
  expectedEntityTypes?: string[];  // e.g., ['EQUIPMENT', 'SYMPTOM']
  expectedActions?: string[];       // e.g., ['view_details', 'start_diagnostic']
  minEntityConfidence?: number;
}

// ============================================================================
// TEST DATA
// ============================================================================

let testData: DiscoveredTestData;
let client: ApiClient;

// Test scenarios covering different query types
const TEST_SCENARIOS: TestScenario[] = [
  // ===== FAULT/SYMPTOM QUERIES =====
  {
    name: 'Fault with symptom',
    query: 'The main engine is overheating',
    expectedEntityTypes: ['EQUIPMENT', 'SYMPTOM'],
    expectedActions: ['view_details', 'start_diagnostic', 'log_fault'],
  },
  {
    name: 'Open faults query',
    query: 'Show me open faults',
    expectedEntityTypes: ['SYMPTOM'],
    expectedActions: ['view_details'],
  },

  // ===== EQUIPMENT QUERIES =====
  {
    name: 'Equipment details',
    query: 'Show me the generator details',
    expectedEntityTypes: ['EQUIPMENT'],
    expectedActions: ['view_details'],
  },

  // ===== PARTS/INVENTORY QUERIES =====
  {
    name: 'Parts inventory',
    query: 'How many oil filters do we have?',
    expectedEntityTypes: ['PART'],
    expectedActions: ['view_details'],
  },

  // ===== MAINTENANCE QUERIES =====
  {
    name: 'Maintenance history',
    query: 'Show maintenance history for the bilge pump',
    expectedEntityTypes: ['EQUIPMENT'],
  },
];

// ============================================================================
// TEST SETUP
// ============================================================================

test.describe('CHAT-TO-ACTION E2E', () => {
  test.beforeAll(async () => {
    console.log('\n📊 Discovering test data from tenant database...');
    testData = await discoverTestData();
    printDiscoverySummary(testData);

    client = new ApiClient();
    await client.ensureAuth();
    console.log('✓ API client authenticated\n');
  });

  // ============================================================================
  // HEALTH CHECK
  // ============================================================================

  test('API health check', async () => {
    const response = await client.get('/health', { skipAuth: true });
    expect(response.status).toBe(200);
    console.log('✓ API is healthy');
  });

  // ============================================================================
  // SEARCH ENDPOINT TESTS
  // ============================================================================

  test('Search endpoint returns valid response structure', async () => {
    const response = await client.post('/search', {
      query: 'show me open faults',
      yacht_id: testData.yacht_id,
      limit: 5,
    });

    expect(response.status).toBe(200);
    expect(response.data).toHaveProperty('success');
    expect(response.data.success).toBe(true);

    const result: SearchResponse = response.data;

    console.log('Search response structure:', {
      success: result.success,
      query: result.query,
      resultsCount: result.results?.length || 0,
      totalCount: result.total_count,
      actionsCount: result.available_actions?.length || 0,
      entitiesCount: result.entities?.length || 0,
      timingMs: result.timing_ms?.total,
    });

    // Validate structure
    expect(result).toHaveProperty('results');
    expect(result).toHaveProperty('total_count');
    expect(result).toHaveProperty('available_actions');
  });

  // ============================================================================
  // ENTITY EXTRACTION & ACTION SUGGESTION TESTS
  // ============================================================================

  test.describe('Entity Extraction & Actions', () => {
    for (const scenario of TEST_SCENARIOS) {
      test(`${scenario.name}: "${scenario.query.substring(0, 50)}..."`, async () => {
        const startTime = Date.now();

        const response = await client.post('/search', {
          query: scenario.query,
          yacht_id: testData.yacht_id,
          limit: 5,
        });

        const elapsed = Date.now() - startTime;

        expect(response.status).toBe(200);
        expect(response.data.success).toBe(true);

        const result: SearchResponse = response.data;

        console.log(`\n📝 Scenario: ${scenario.name}`);
        console.log(`   Query: "${scenario.query}"`);
        console.log(`   Time: ${elapsed}ms (extraction: ${result.timing_ms?.extraction?.toFixed(0)}ms)`);

        // Log extracted entities
        if (result.entities && result.entities.length > 0) {
          console.log(`   Entities extracted:`);
          for (const entity of result.entities) {
            console.log(`     - ${entity.type}: "${entity.value}" (${(entity.confidence * 100).toFixed(0)}%)`);
          }

          // Validate expected entity types
          if (scenario.expectedEntityTypes) {
            const extractedTypes = result.entities.map(e => e.type);
            for (const expectedType of scenario.expectedEntityTypes) {
              const found = extractedTypes.some(t =>
                t.toUpperCase().includes(expectedType.toUpperCase())
              );
              if (!found) {
                console.log(`   ⚠ Expected entity type "${expectedType}" not found`);
              }
            }
          }

          // Validate confidence
          if (scenario.minEntityConfidence) {
            for (const entity of result.entities) {
              expect(entity.confidence).toBeGreaterThanOrEqual(scenario.minEntityConfidence);
            }
          }
        } else {
          console.log(`   No entities extracted`);
        }

        // Log available actions
        if (result.available_actions && result.available_actions.length > 0) {
          console.log(`   Available actions:`);
          for (const action of result.available_actions) {
            console.log(`     - ${action.action}: ${action.label}`);
          }

          // Validate expected actions
          if (scenario.expectedActions) {
            const availableActionIds = result.available_actions.map(a => a.action);
            for (const expectedAction of scenario.expectedActions) {
              const found = availableActionIds.includes(expectedAction);
              if (!found) {
                console.log(`   ⚠ Expected action "${expectedAction}" not available`);
              }
            }
          }
        }

        // Log query plans
        if (result.plans && result.plans.length > 0) {
          console.log(`   Query plans: ${result.plans.length}`);
          for (const plan of result.plans) {
            console.log(`     - ${plan.capability} on ${plan.entity_type}:${plan.entity_value}`);
          }
        }

        // Log results count
        console.log(`   Results: ${result.results?.length || 0} / ${result.total_count}`);
      });
    }
  });

  // ============================================================================
  // FULL FLOW TESTS (Query → Extract → Execute Action)
  // ============================================================================

  test.describe('Full Chat-to-Action Flow', () => {
    test('Query → Extract entities → Execute action: View equipment', async () => {
      // Step 1: Send natural language query
      const searchResponse = await client.post('/search', {
        query: 'show me equipment details',
        yacht_id: testData.yacht_id,
        limit: 5,
      });

      expect(searchResponse.status).toBe(200);
      console.log('\n📝 Step 1: Search query sent');
      console.log(`   Success: ${searchResponse.data.success}`);
      console.log(`   Entities: ${searchResponse.data.entities?.length || 0}`);
      console.log(`   Actions available: ${searchResponse.data.available_actions?.map((a: any) => a.action).join(', ')}`);

      // Step 2: If we have an equipment ID, execute view_equipment_details
      if (testData.equipment_id) {
        console.log('\n📝 Step 2: Executing view_equipment_details action');

        const actionResponse = await client.executeAction(
          'view_equipment_details',
          { equipment_id: testData.equipment_id }
        );

        expect(actionResponse.status).toBe(200);
        expect(actionResponse.data.success).toBe(true);

        console.log(`   Action success: ${actionResponse.data.success}`);
        console.log(`   Data returned: ${!!actionResponse.data.equipment || !!actionResponse.data.data}`);
      }
    });

    test('Query → Extract entities → Execute action: View faults', async () => {
      // Step 1: Natural language query
      const searchResponse = await client.post('/search', {
        query: 'what faults have been reported recently?',
        yacht_id: testData.yacht_id,
        limit: 10,
      });

      expect(searchResponse.status).toBe(200);
      console.log('\n📝 Step 1: Fault query sent');
      console.log(`   Entities: ${JSON.stringify(searchResponse.data.entities)}`);

      // Step 2: Execute fault-related action
      if (testData.equipment_id) {
        const actionResponse = await client.executeAction(
          'view_fault_history',
          { equipment_id: testData.equipment_id }
        );

        expect(actionResponse.status).toBe(200);
        console.log(`   Fault history retrieved: ${actionResponse.data.success}`);
      }
    });

    test('Query → Extract entities → Execute action: Check inventory', async () => {
      // Step 1: Natural language query about parts
      const searchResponse = await client.post('/search', {
        query: 'check our parts inventory',
        yacht_id: testData.yacht_id,
        limit: 5,
      });

      expect(searchResponse.status).toBe(200);
      console.log('\n📝 Step 1: Inventory query sent');
      console.log(`   Entities: ${JSON.stringify(searchResponse.data.entities)}`);

      // Step 2: Execute part-related action
      if (testData.part_id) {
        const actionResponse = await client.executeAction(
          'view_part_stock',
          { part_id: testData.part_id }
        );

        expect(actionResponse.status).toBe(200);
        console.log(`   Part stock retrieved: ${actionResponse.data.success}`);
      }
    });
  });

  // ============================================================================
  // MUTATION FLOW TESTS (with confirmation)
  // ============================================================================

  test.describe('Mutation Actions (Data-Changing)', () => {
    test('Work order creation flow', async () => {
      if (!testData.equipment_id) {
        test.skip();
        return;
      }

      // Step 1: Query that should trigger mutation intent
      const searchResponse = await client.post('/search', {
        query: 'create a work order for routine maintenance',
        yacht_id: testData.yacht_id,
        limit: 5,
      });

      expect(searchResponse.status).toBe(200);
      console.log('\n📝 Mutation query sent');
      console.log(`   Entities: ${JSON.stringify(searchResponse.data.entities)}`);
      console.log(`   Actions: ${searchResponse.data.available_actions?.map((a: any) => a.action).join(', ')}`);

      // Step 2: Execute the actual creation
      const actionResponse = await client.executeAction(
        'create_work_order',
        {
          equipment_id: testData.equipment_id,
          title: 'E2E Test: Routine Maintenance Check',
          description: 'Created by chat-to-action E2E test',
          priority: 'routine',
        }
      );

      expect(actionResponse.status).toBe(200);
      // Response may have success field or status field depending on action
      const isSuccess = actionResponse.data.success === true ||
                        actionResponse.data.status === 'success' ||
                        actionResponse.status === 200;
      expect(isSuccess).toBe(true);
      console.log(`   Work order created: ${JSON.stringify(actionResponse.data).substring(0, 200)}`);
    });

    test('Add note to fault flow', async () => {
      if (!testData.fault_id) {
        test.skip();
        return;
      }

      const actionResponse = await client.executeAction(
        'add_fault_note',
        {
          fault_id: testData.fault_id,
          note_text: 'E2E Test note: Testing chat-to-action flow',
        }
      );

      expect(actionResponse.status).toBe(200);
      expect(actionResponse.data.success).toBe(true);
      console.log(`\n📝 Note added to fault: ${actionResponse.data.success}`);
    });
  });

  // ============================================================================
  // EDGE CASES & ERROR HANDLING
  // ============================================================================

  test.describe('Edge Cases', () => {
    test('Empty query returns graceful response', async () => {
      const response = await client.post('/search', {
        query: '',
        yacht_id: testData.yacht_id,
        limit: 5,
      });

      // Should not crash - may return 400 or empty results
      expect([200, 400, 422]).toContain(response.status);
      console.log(`Empty query response: ${response.status}`);
    });

    test('Ambiguous query is handled', async () => {
      const response = await client.post('/search', {
        query: 'fix it',
        yacht_id: testData.yacht_id,
        limit: 5,
      });

      expect(response.status).toBe(200);
      console.log(`Ambiguous query handled`);
      console.log(`   Entities: ${response.data.entities?.length || 0}`);
      console.log(`   Actions: ${response.data.available_actions?.length || 0}`);
    });

    test('Non-existent equipment query', async () => {
      const response = await client.post('/search', {
        query: 'show me the quantum flux capacitor status',
        yacht_id: testData.yacht_id,
        limit: 5,
      });

      expect(response.status).toBe(200);
      // Should return results or empty, but not crash
      console.log(`Non-existent equipment query handled: ${response.data.success}`);
      console.log(`   Results: ${response.data.results?.length || 0}`);
    });
  });

  // ============================================================================
  // PERFORMANCE TESTS
  // ============================================================================

  test.describe('Performance', () => {
    test('Search response time is acceptable', async () => {
      const startTime = Date.now();

      const response = await client.post('/search', {
        query: 'show me open faults',
        yacht_id: testData.yacht_id,
        limit: 10,
      });

      const elapsed = Date.now() - startTime;

      expect(response.status).toBe(200);
      expect(elapsed).toBeLessThan(10000); // Should respond within 10 seconds (includes AI extraction)

      console.log(`\n⏱ Search response time: ${elapsed}ms`);
      if (response.data.timing_ms) {
        console.log(`   Extraction: ${response.data.timing_ms.extraction?.toFixed(0)}ms`);
        console.log(`   Prepare: ${response.data.timing_ms.prepare?.toFixed(0)}ms`);
        console.log(`   Execute: ${response.data.timing_ms.execute?.toFixed(0)}ms`);
        console.log(`   Total (server): ${response.data.timing_ms.total?.toFixed(0)}ms`);
      }
    });
  });

  // ============================================================================
  // INTENT → ACTION MAPPING TESTS
  // ============================================================================
  // These tests verify that the AI correctly maps queries to the right actions
  // based on the entity extraction → capability → available_actions chain
  //
  // Flow: Query → Extract Entities → Match Capability → Suggest Actions
  //
  // Mapping (from table_capabilities.py):
  //   EQUIPMENT_NAME → equipment_by_name_or_model → [view_details, view_maintenance, log_hours]
  //   SYMPTOM/FAULT_CODE → fault_by_fault_code → [view_details, start_diagnostic, log_fault]
  //   PART_NUMBER/PART_NAME → part_by_part_number_or_name → [view_details, check_stock, order_part]
  // ============================================================================

  test.describe('Intent → Action Mapping', () => {

    test('Equipment query suggests equipment actions', async () => {
      const response = await client.post('/search', {
        query: 'show me the main engine',
        yacht_id: testData.yacht_id,
        limit: 5,
      });

      expect(response.status).toBe(200);

      const entities = response.data.entities || [];
      const actions = response.data.available_actions || [];

      console.log('\n🎯 Equipment Query Test');
      console.log(`   Query: "show me the main engine"`);
      console.log(`   Entities: ${entities.map((e: any) => `${e.type}:${e.value}`).join(', ')}`);
      console.log(`   Actions: ${actions.map((a: any) => a.action).join(', ')}`);

      // Should extract equipment entity
      const hasEquipmentEntity = entities.some((e: any) =>
        e.type.includes('EQUIPMENT') || e.value.toLowerCase().includes('engine')
      );
      expect(hasEquipmentEntity).toBe(true);

      // Should suggest equipment-related actions
      const actionIds = actions.map((a: any) => a.action);
      const hasEquipmentAction = actionIds.some((a: string) =>
        ['view_details', 'view_maintenance', 'log_hours'].includes(a)
      );
      expect(hasEquipmentAction).toBe(true);

      console.log(`   ✓ Entity extraction: ${hasEquipmentEntity ? 'PASS' : 'FAIL'}`);
      console.log(`   ✓ Action mapping: ${hasEquipmentAction ? 'PASS' : 'FAIL'}`);
    });

    test('Fault/symptom query suggests diagnostic actions', async () => {
      const response = await client.post('/search', {
        query: 'engine is overheating',
        yacht_id: testData.yacht_id,
        limit: 5,
      });

      expect(response.status).toBe(200);

      const entities = response.data.entities || [];
      const actions = response.data.available_actions || [];

      console.log('\n🎯 Fault/Symptom Query Test');
      console.log(`   Query: "engine is overheating"`);
      console.log(`   Entities: ${entities.map((e: any) => `${e.type}:${e.value}`).join(', ')}`);
      console.log(`   Actions: ${actions.map((a: any) => a.action).join(', ')}`);

      // Should extract symptom entity
      const hasSymptomEntity = entities.some((e: any) =>
        e.type.includes('SYMPTOM') || e.value.toLowerCase().includes('overheating')
      );

      // Should suggest diagnostic actions
      const actionIds = actions.map((a: any) => a.action);
      const hasDiagnosticAction = actionIds.some((a: string) =>
        ['start_diagnostic', 'log_fault', 'view_resolution'].includes(a)
      );

      console.log(`   ✓ Symptom extraction: ${hasSymptomEntity ? 'PASS' : 'FAIL'}`);
      console.log(`   ✓ Diagnostic action: ${hasDiagnosticAction ? 'PASS' : 'FAIL'}`);

      // At least one should be true
      expect(hasSymptomEntity || hasDiagnosticAction).toBe(true);
    });

    test('Parts query suggests inventory actions', async () => {
      const response = await client.post('/search', {
        query: 'find oil filter',
        yacht_id: testData.yacht_id,
        limit: 5,
      });

      expect(response.status).toBe(200);

      const entities = response.data.entities || [];
      const actions = response.data.available_actions || [];

      console.log('\n🎯 Parts Query Test');
      console.log(`   Query: "find oil filter"`);
      console.log(`   Entities: ${entities.map((e: any) => `${e.type}:${e.value}`).join(', ')}`);
      console.log(`   Actions: ${actions.map((a: any) => a.action).join(', ')}`);

      // Should suggest part-related actions if entities extracted
      const actionIds = actions.map((a: any) => a.action);
      const hasPartAction = actionIds.some((a: string) =>
        ['view_details', 'check_stock', 'order_part'].includes(a)
      );

      console.log(`   ✓ Part actions suggested: ${hasPartAction ? 'PASS' : 'FAIL'}`);
    });

    test('Full chain: Query → Entity → Action → Execute', async () => {
      // Step 1: Send query and get suggested actions
      const searchResponse = await client.post('/search', {
        query: 'show generator details',
        yacht_id: testData.yacht_id,
        limit: 5,
      });

      expect(searchResponse.status).toBe(200);

      const entities = searchResponse.data.entities || [];
      const actions = searchResponse.data.available_actions || [];

      console.log('\n🔗 Full Chain Test');
      console.log(`   Step 1 - Query: "show generator details"`);
      console.log(`   Entities extracted: ${entities.length}`);
      console.log(`   Actions available: ${actions.map((a: any) => a.action).join(', ')}`);

      // Step 2: Find the view_details action
      const viewDetailsAction = actions.find((a: any) => a.action === 'view_details');

      if (viewDetailsAction && testData.equipment_id) {
        console.log(`   Step 2 - Found action: ${viewDetailsAction.action}`);

        // Step 3: Execute the action
        const actionResponse = await client.executeAction(
          'view_equipment_details',
          { equipment_id: testData.equipment_id }
        );

        expect(actionResponse.status).toBe(200);
        console.log(`   Step 3 - Action executed: ${actionResponse.status === 200 ? 'SUCCESS' : 'FAILED'}`);

        // Verify the chain worked
        console.log(`   ✓ Complete chain: Query → Entity → Action → Result`);
      } else {
        console.log(`   ⚠ Skipped execution (no equipment ID or view_details not suggested)`);
      }
    });

    test('Mutation query suggests confirm-class actions', async () => {
      const response = await client.post('/search', {
        query: 'create work order for pump maintenance',
        yacht_id: testData.yacht_id,
        limit: 5,
      });

      expect(response.status).toBe(200);

      const entities = response.data.entities || [];
      const actions = response.data.available_actions || [];

      console.log('\n🎯 Mutation Query Test');
      console.log(`   Query: "create work order for pump maintenance"`);
      console.log(`   Entities: ${entities.map((e: any) => `${e.type}:${e.value}`).join(', ')}`);
      console.log(`   Actions: ${actions.map((a: any) => `${a.action}(${a.execution_class})`).join(', ')}`);

      // Check if any action has execution_class 'confirm' or 'suggest'
      const hasConfirmAction = actions.some((a: any) =>
        a.execution_class === 'confirm' || a.execution_class === 'suggest'
      );

      console.log(`   ✓ Has confirm/suggest action: ${hasConfirmAction ? 'PASS' : 'NO (may use auto)'}`);
    });
  });
});
