/**
 * Tenant Supabase Client for Test Verification
 *
 * Uses service role key to bypass RLS for verification queries
 * ONLY use for test assertions, not for simulating user actions
 */

import { createClient, SupabaseClient } from '@supabase/supabase-js';

let tenantClient: SupabaseClient | null = null;

/**
 * Get Tenant Supabase client with service role
 */
export function getTenantClient(): SupabaseClient {
  if (tenantClient) {
    return tenantClient;
  }

  const url = process.env.TENANT_SUPABASE_URL;
  const key = process.env.TENANT_SUPABASE_SERVICE_ROLE_KEY;

  if (!url || !key) {
    throw new Error(
      'TENANT_SUPABASE_URL and TENANT_SUPABASE_SERVICE_ROLE_KEY must be set'
    );
  }

  tenantClient = createClient(url, key, {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  });

  return tenantClient;
}

/**
 * Get work order by ID
 */
export async function getWorkOrder(workOrderId: string): Promise<any> {
  const client = getTenantClient();

  const { data, error } = await client
    .from('pms_work_orders')
    .select('*')
    .eq('id', workOrderId)
    .single();

  if (error) {
    throw new Error(`Failed to get work order: ${error.message}`);
  }

  return data;
}

/**
 * Get equipment by ID
 */
export async function getEquipment(equipmentId: string): Promise<any> {
  const client = getTenantClient();

  const { data, error } = await client
    .from('pms_equipment')
    .select('*')
    .eq('id', equipmentId)
    .single();

  if (error) {
    throw new Error(`Failed to get equipment: ${error.message}`);
  }

  return data;
}

/**
 * Get fault by ID
 */
export async function getFault(faultId: string): Promise<any> {
  const client = getTenantClient();

  const { data, error } = await client
    .from('pms_faults')
    .select('*')
    .eq('id', faultId)
    .single();

  if (error) {
    throw new Error(`Failed to get fault: ${error.message}`);
  }

  return data;
}

/**
 * Get parts inventory item
 */
export async function getPartInventory(partId: string): Promise<any> {
  const client = getTenantClient();

  const { data, error } = await client
    .from('parts_inventory')
    .select('*')
    .eq('id', partId)
    .single();

  if (error) {
    throw new Error(`Failed to get part inventory: ${error.message}`);
  }

  return data;
}

/**
 * Get latest audit log entry for entity
 */
export async function getLatestAuditLog(
  entityId: string,
  entityType?: string
): Promise<any> {
  const client = getTenantClient();

  let query = client
    .from('audit_log')
    .select('*')
    .eq('entity_id', entityId)
    .order('created_at', { ascending: false })
    .limit(1);

  if (entityType) {
    query = query.eq('entity_type', entityType);
  }

  const { data, error } = await query.single();

  if (error && error.code !== 'PGRST116') {
    throw new Error(`Failed to get audit log: ${error.message}`);
  }

  return data;
}

/**
 * Get handover items for yacht
 * Table: pms_handover (actual table name in tenant DB)
 * Columns: id, yacht_id, entity_type, entity_id, summary_text, category, priority, added_by, added_at
 */
export async function getHandoverItems(
  yachtId: string,
  limit: number = 10
): Promise<any[]> {
  const client = getTenantClient();

  const { data, error } = await client
    .from('pms_handover')
    .select('*')
    .eq('yacht_id', yachtId)
    .order('added_at', { ascending: false })
    .limit(limit);

  if (error) {
    throw new Error(`Failed to get handover items: ${error.message}`);
  }

  return data || [];
}

/**
 * Count document chunks for yacht
 */
export async function countDocumentChunks(yachtId: string): Promise<number> {
  const client = getTenantClient();

  const { count, error } = await client
    .from('document_chunks')
    .select('*', { count: 'exact', head: true })
    .eq('yacht_id', yachtId);

  if (error) {
    throw new Error(`Failed to count document chunks: ${error.message}`);
  }

  return count || 0;
}

/**
 * Create test work order (for testing purposes)
 * Uses correct column names and enum values from actual DB schema
 */
export async function createTestWorkOrder(
  yachtId: string,
  title: string = 'Test Work Order'
): Promise<string> {
  const client = getTenantClient();

  // Get a valid created_by from existing work orders
  const { data: existingWo } = await client
    .from('pms_work_orders')
    .select('created_by')
    .not('created_by', 'is', null)
    .limit(1);

  const validCreatedBy = existingWo?.[0]?.created_by || null;

  const { data, error } = await client
    .from('pms_work_orders')
    .insert({
      yacht_id: yachtId,
      title,
      wo_number: `WO-TEST-${Date.now()}`,
      status: 'planned', // Valid enum: planned, completed, cancelled
      type: 'scheduled', // Valid enum
      work_order_type: 'planned', // Valid enum
      priority: 'routine', // Valid enum: routine, critical
      created_by: validCreatedBy,
    })
    .select('id')
    .single();

  if (error) {
    throw new Error(`Failed to create test work order: ${error.message}`);
  }

  return data.id;
}

/**
 * Create test equipment (for testing purposes)
 * Uses pms_equipment table (note: no status column in actual tenant DB schema)
 */
export async function createTestEquipment(
  yachtId: string,
  name: string = 'Test Equipment'
): Promise<string> {
  const client = getTenantClient();

  const { data, error } = await client
    .from('pms_equipment')
    .insert({
      yacht_id: yachtId,
      name,
      code: `TEST-EQ-${Date.now()}`,
      criticality: 'low',
      system_type: 'mechanical',
      attention_flag: false,
    })
    .select('id')
    .single();

  if (error) {
    throw new Error(`Failed to create test equipment: ${error.message}`);
  }

  return data.id;
}

/**
 * Cleanup test data
 */
export async function cleanupTestData(yachtId: string): Promise<void> {
  const client = getTenantClient();

  // Delete test work orders
  await client
    .from('pms_work_orders')
    .delete()
    .eq('yacht_id', yachtId)
    .like('number', 'WO-TEST-%');

  // Delete test equipment
  await client
    .from('pms_equipment')
    .delete()
    .eq('yacht_id', yachtId)
    .like('name', 'Test Equipment%');
}

// =============================================================================
// TEST FIXTURES - Get real IDs for E2E tests
// =============================================================================

/**
 * Get a real work order ID from the test yacht
 */
export async function getRealWorkOrderId(yachtId: string): Promise<string> {
  const client = getTenantClient();

  const { data, error } = await client
    .from('pms_work_orders')
    .select('id')
    .eq('yacht_id', yachtId)
    .limit(1)
    .single();

  if (error || !data) {
    throw new Error(`No work orders found for yacht ${yachtId}. Create test data first.`);
  }

  return data.id;
}

/**
 * Get a real part ID from the test yacht
 */
export async function getRealPartId(yachtId: string): Promise<string> {
  const client = getTenantClient();

  const { data, error } = await client
    .from('pms_parts')
    .select('id')
    .eq('yacht_id', yachtId)
    .limit(1)
    .single();

  if (error || !data) {
    throw new Error(`No parts found for yacht ${yachtId}. Create test data first.`);
  }

  return data.id;
}

/**
 * Get a real equipment ID from the test yacht
 */
export async function getRealEquipmentId(yachtId: string): Promise<string> {
  const client = getTenantClient();

  const { data, error } = await client
    .from('pms_equipment')
    .select('id')
    .eq('yacht_id', yachtId)
    .limit(1)
    .single();

  if (error || !data) {
    throw new Error(`No equipment found for yacht ${yachtId}. Create test data first.`);
  }

  return data.id;
}

/**
 * Get a real fault ID from the test yacht
 */
export async function getRealFaultId(yachtId: string): Promise<string> {
  const client = getTenantClient();

  const { data, error } = await client
    .from('pms_faults')
    .select('id')
    .eq('yacht_id', yachtId)
    .limit(1)
    .single();

  if (error || !data) {
    throw new Error(`No faults found for yacht ${yachtId}. Create test data first.`);
  }

  return data.id;
}

/**
 * Get a real document ID from the test yacht
 */
export async function getRealDocumentId(yachtId: string): Promise<string> {
  const client = getTenantClient();

  const { data, error } = await client
    .from('documents')
    .select('id')
    .eq('yacht_id', yachtId)
    .limit(1)
    .single();

  if (error || !data) {
    throw new Error(`No documents found for yacht ${yachtId}. Create test data first.`);
  }

  return data.id;
}

/**
 * Get a real shopping list item ID from the test yacht
 */
export async function getRealShoppingItemId(yachtId: string): Promise<string> {
  const client = getTenantClient();

  const { data, error } = await client
    .from('pms_shopping_list_items')
    .select('id')
    .eq('yacht_id', yachtId)
    .limit(1)
    .single();

  if (error || !data) {
    throw new Error(`No shopping list items found for yacht ${yachtId}. Create test data first.`);
  }

  return data.id;
}

/**
 * Get all real test IDs at once for a yacht
 */
export interface RealTestIds {
  workOrderId: string | null;
  partId: string | null;
  equipmentId: string | null;
  faultId: string | null;
  documentId: string | null;
  shoppingItemId: string | null;
}

export async function getAllRealTestIds(yachtId: string): Promise<RealTestIds> {
  const client = getTenantClient();

  const [woResult, partResult, eqResult, faultResult, docResult, shopResult] = await Promise.all([
    client.from('pms_work_orders').select('id').eq('yacht_id', yachtId).limit(1).maybeSingle(),
    client.from('pms_parts').select('id').eq('yacht_id', yachtId).limit(1).maybeSingle(),
    client.from('pms_equipment').select('id').eq('yacht_id', yachtId).limit(1).maybeSingle(),
    client.from('pms_faults').select('id').eq('yacht_id', yachtId).limit(1).maybeSingle(),
    client.from('documents').select('id').eq('yacht_id', yachtId).limit(1).maybeSingle(),
    // Find a shopping item NOT linked to an order (deletable without finance constraint)
    client.from('pms_shopping_list_items').select('id').eq('yacht_id', yachtId).is('order_id', null).limit(1).maybeSingle(),
  ]);

  return {
    workOrderId: woResult.data?.id || null,
    partId: partResult.data?.id || null,
    equipmentId: eqResult.data?.id || null,
    faultId: faultResult.data?.id || null,
    documentId: docResult.data?.id || null,
    shoppingItemId: shopResult.data?.id || null,
  };
}
