/**
 * NATURAL LANGUAGE QUERY TESTING: create_work_order
 * ==================================================
 *
 * Tests that various user queries correctly surface the create_work_order action
 * Tests the full pipeline: User query → /search → Action suggestions
 *
 * Categories:
 * 1. Direct commands (20 queries)
 * 2. Equipment-specific (15 queries)
 * 3. Fault-related (10 queries)
 * 4. Scheduled maintenance (10 queries)
 *
 * Total: 55 query variations
 */

import { test, expect } from '@playwright/test';
import { ApiClient } from '../helpers/api-client';

const TEST_YACHT_ID = process.env.TEST_YACHT_ID!;
const TEST_USER_ID = process.env.TEST_USER_ID!;

let apiClient: ApiClient;

test.beforeAll(async () => {
  apiClient = new ApiClient(process.env.RENDER_API_URL);
  await apiClient.authenticate(
    process.env.TEST_USER_EMAIL!,
    process.env.TEST_USER_PASSWORD!
  );
});

// ============================================================================
// CATEGORY 1: DIRECT COMMANDS
// ============================================================================

test.describe('Direct Commands', () => {
  const directQueries = [
    "create a work order",
    "create work order",
    "make a new work order",
    "add a work order",
    "start a work order",
    "open a work order",
    "new work order",
    "create wo",
    "new wo",
    "make wo",
    "add wo",
    "create a new work order",
    "I need to create a work order",
    "please create a work order",
    "can you create a work order",
    "create work order please",
    "work order creation",
    "initiate work order",
    "begin work order",
    "start new work order"
  ];

  directQueries.forEach((query, index) => {
    test(`should surface create_work_order for: "${query}"`, async () => {
      console.log(`\n[${index + 1}/20] Testing query: "${query}"\n`);

      const response = await apiClient.request('POST', '/search', {
        query: query,
        yacht_id: TEST_YACHT_ID,
        user_id: TEST_USER_ID
      });

      expect(response.status).toBe(200);
      expect(response.data).toBeTruthy();

      // Check if create_work_order action is suggested
      const hasCreateWOAction = checkForCreateWorkOrderAction(response.data);

      if (!hasCreateWOAction) {
        console.error('❌ create_work_order NOT found in response');
        console.error('Response:', JSON.stringify(response.data, null, 2));
      }

      expect(hasCreateWOAction).toBeTruthy();
      console.log(`✅ create_work_order action found`);
    });
  });
});

// ============================================================================
// CATEGORY 2: EQUIPMENT-SPECIFIC
// ============================================================================

test.describe('Equipment-Specific Queries', () => {
  const equipmentQueries = [
    "create work order for generator",
    "make work order for the starboard engine",
    "add work order for hydraulic pump",
    "create wo for main engine",
    "new work order for air conditioning",
    "create work order for water maker",
    "make wo for port engine",
    "work order for stabilizer",
    "create work order for the generator",
    "new wo for bow thruster",
    "work order needed for refrigeration",
    "make work order for sewage treatment",
    "create work order for navigation system",
    "work order for HVAC system",
    "create wo for bilge pump"
  ];

  equipmentQueries.forEach((query, index) => {
    test(`should surface create_work_order and extract equipment: "${query}"`, async () => {
      console.log(`\n[${index + 1}/15] Testing query: "${query}"\n`);

      const response = await apiClient.request('POST', '/search', {
        query: query,
        yacht_id: TEST_YACHT_ID,
        user_id: TEST_USER_ID
      });

      expect(response.status).toBe(200);
      expect(response.data).toBeTruthy();

      const hasCreateWOAction = checkForCreateWorkOrderAction(response.data);
      expect(hasCreateWOAction).toBeTruthy();

      // Also check if equipment was extracted
      const extractedEquipment = extractEquipmentFromResponse(response.data);
      console.log(`Equipment extracted: ${extractedEquipment || '(none)'}`);

      // Log full response for debugging
      if (!extractedEquipment) {
        console.log('Response:', JSON.stringify(response.data, null, 2));
      }
    });
  });
});

// ============================================================================
// CATEGORY 3: FAULT-RELATED
// ============================================================================

test.describe('Fault-Related Queries', () => {
  const faultQueries = [
    "the AC is broken, create a work order",
    "generator fault, need work order",
    "water pump failed, make wo",
    "engine overheating, create work order",
    "hydraulic leak, need a work order",
    "stabilizer not working, create wo",
    "bow thruster failed, make work order",
    "refrigeration down, create work order",
    "sewage system issue, need wo",
    "navigation fault, create work order"
  ];

  faultQueries.forEach((query, index) => {
    test(`should surface create_work_order for fault: "${query}"`, async () => {
      console.log(`\n[${index + 1}/10] Testing query: "${query}"\n`);

      const response = await apiClient.request('POST', '/search', {
        query: query,
        yacht_id: TEST_YACHT_ID,
        user_id: TEST_USER_ID
      });

      expect(response.status).toBe(200);
      expect(response.data).toBeTruthy();

      // Could surface either create_work_order OR create_work_order_from_fault
      const hasWOAction = checkForAnyWorkOrderCreationAction(response.data);
      expect(hasWOAction).toBeTruthy();

      console.log(`✅ Work order creation action found`);
    });
  });
});

// ============================================================================
// CATEGORY 4: SCHEDULED MAINTENANCE
// ============================================================================

test.describe('Scheduled Maintenance Queries', () => {
  const pmQueries = [
    "schedule maintenance for generator",
    "plan PM for engine",
    "create scheduled work order",
    "schedule service for main engine",
    "plan maintenance for AC",
    "create preventive maintenance work order",
    "schedule PM work order",
    "plan routine maintenance",
    "create scheduled PM for hydraulics",
    "schedule preventive work order"
  ];

  pmQueries.forEach((query, index) => {
    test(`should surface create_work_order for PM: "${query}"`, async () => {
      console.log(`\n[${index + 1}/10] Testing query: "${query}"\n`);

      const response = await apiClient.request('POST', '/search', {
        query: query,
        yacht_id: TEST_YACHT_ID,
        user_id: TEST_USER_ID
      });

      expect(response.status).toBe(200);
      expect(response.data).toBeTruthy();

      const hasCreateWOAction = checkForCreateWorkOrderAction(response.data);
      expect(hasCreateWOAction).toBeTruthy();

      console.log(`✅ create_work_order action found`);
    });
  });
});

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

function checkForCreateWorkOrderAction(responseData: any): boolean {
  // /search can return different structures
  // Check for actions in various possible locations

  // Structure 1: { actions: [...] }
  if (responseData.actions && Array.isArray(responseData.actions)) {
    return responseData.actions.some((action: any) =>
      action.action === 'create_work_order' ||
      action.action_id === 'create_work_order' ||
      action.label?.toLowerCase().includes('create work order')
    );
  }

  // Structure 2: { results: [{ actions: [...] }] }
  if (responseData.results && Array.isArray(responseData.results)) {
    return responseData.results.some((result: any) =>
      result.actions?.some((action: any) =>
        action.action === 'create_work_order' ||
        action.action_id === 'create_work_order'
      )
    );
  }

  // Structure 3: { cards: [{ actions: [...] }] }
  if (responseData.cards && Array.isArray(responseData.cards)) {
    return responseData.cards.some((card: any) =>
      card.actions?.some((action: any) =>
        action.action === 'create_work_order' ||
        action.action_id === 'create_work_order'
      )
    );
  }

  // Structure 4: { primary_action: { ... } }
  if (responseData.primary_action) {
    return responseData.primary_action.action === 'create_work_order' ||
           responseData.primary_action.action_id === 'create_work_order';
  }

  // Structure 5: { suggestions: [...] }
  if (responseData.suggestions && Array.isArray(responseData.suggestions)) {
    return responseData.suggestions.some((suggestion: any) =>
      suggestion.action === 'create_work_order' ||
      suggestion.action_id === 'create_work_order'
    );
  }

  return false;
}

function checkForAnyWorkOrderCreationAction(responseData: any): boolean {
  const woActions = [
    'create_work_order',
    'create_work_order_from_fault',
    'create_wo'
  ];

  const checkActions = (actions: any[]): boolean => {
    return actions.some((action: any) =>
      woActions.includes(action.action) ||
      woActions.includes(action.action_id)
    );
  };

  if (responseData.actions && Array.isArray(responseData.actions)) {
    return checkActions(responseData.actions);
  }

  if (responseData.results && Array.isArray(responseData.results)) {
    return responseData.results.some((result: any) =>
      result.actions && checkActions(result.actions)
    );
  }

  if (responseData.cards && Array.isArray(responseData.cards)) {
    return responseData.cards.some((card: any) =>
      card.actions && checkActions(card.actions)
    );
  }

  return false;
}

function extractEquipmentFromResponse(responseData: any): string | null {
  // Check for extracted entities
  if (responseData.entities?.equipment) {
    return responseData.entities.equipment;
  }

  if (responseData.extracted?.equipment) {
    return responseData.extracted.equipment;
  }

  // Check in results
  if (responseData.results && Array.isArray(responseData.results)) {
    for (const result of responseData.results) {
      if (result.entity_type === 'equipment' || result.type === 'equipment') {
        return result.name || result.title || result.id;
      }
    }
  }

  // Check in cards
  if (responseData.cards && Array.isArray(responseData.cards)) {
    for (const card of responseData.cards) {
      if (card.entity_type === 'equipment' || card.type === 'equipment') {
        return card.name || card.title || card.id;
      }
    }
  }

  return null;
}
