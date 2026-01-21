/**
 * TEST DATA DISCOVERY
 * ====================
 *
 * Queries the tenant database to find real IDs for testing.
 * This ensures tests use actual data that exists in the DB.
 */

import { createClient, SupabaseClient } from '@supabase/supabase-js';

export interface DiscoveredTestData {
  yacht_id: string;
  user_id: string;

  // Entity IDs (null if none found)
  fault_id: string | null;
  fault_open_id: string | null;        // Fault in open/reported status
  fault_closed_id: string | null;      // Fault in closed status
  work_order_id: string | null;
  work_order_open_id: string | null;   // WO in open/planned status
  work_order_closed_id: string | null; // WO in completed status
  equipment_id: string | null;
  part_id: string | null;
  document_id: string | null;
  handover_id: string | null;

  // Summary
  found: {
    faults: number;
    work_orders: number;
    equipment: number;
    parts: number;
    documents: number;
    handover: number;
  };
}

function getTenantClient(): SupabaseClient {
  const url = process.env.TENANT_SUPABASE_URL;
  const serviceKey = process.env.TENANT_SUPABASE_SERVICE_ROLE_KEY;

  if (!url || !serviceKey) {
    throw new Error('TENANT_SUPABASE_URL and TENANT_SUPABASE_SERVICE_ROLE_KEY must be set');
  }

  return createClient(url, serviceKey);
}

/**
 * Discover real test data from the tenant database
 */
export async function discoverTestData(): Promise<DiscoveredTestData> {
  const yacht_id = process.env.TEST_YACHT_ID || process.env.TEST_USER_YACHT_ID || '85fe1119-b04c-41ac-80f1-829d23322598';
  const user_id = process.env.TEST_USER_ID || 'a35cad0b-02ff-4287-b6e4-17c96fa6a424';

  const client = getTenantClient();

  const result: DiscoveredTestData = {
    yacht_id,
    user_id,
    fault_id: null,
    fault_open_id: null,
    fault_closed_id: null,
    work_order_id: null,
    work_order_open_id: null,
    work_order_closed_id: null,
    equipment_id: null,
    part_id: null,
    document_id: null,
    handover_id: null,
    found: {
      faults: 0,
      work_orders: 0,
      equipment: 0,
      parts: 0,
      documents: 0,
      handover: 0,
    },
  };

  // Discover faults
  try {
    const { data: faults } = await client
      .from('pms_faults')
      .select('id, status')
      .eq('yacht_id', yacht_id)
      .order('created_at', { ascending: false })
      .limit(10);

    if (faults && faults.length > 0) {
      result.found.faults = faults.length;
      result.fault_id = faults[0].id;

      // Find open and closed faults
      const openFault = faults.find(f => ['open', 'reported', 'acknowledged', 'diagnosed'].includes(f.status));
      const closedFault = faults.find(f => f.status === 'closed');

      result.fault_open_id = openFault?.id || null;
      result.fault_closed_id = closedFault?.id || null;
    }
  } catch (e: any) {
    console.warn('Failed to discover faults:', e.message);
  }

  // Discover work orders
  try {
    const { data: workOrders } = await client
      .from('pms_work_orders')
      .select('id, status')
      .eq('yacht_id', yacht_id)
      .order('created_at', { ascending: false })
      .limit(10);

    if (workOrders && workOrders.length > 0) {
      result.found.work_orders = workOrders.length;
      result.work_order_id = workOrders[0].id;

      // Find open and closed work orders
      const openWO = workOrders.find(wo => ['planned', 'open', 'in_progress'].includes(wo.status));
      const closedWO = workOrders.find(wo => ['completed', 'closed'].includes(wo.status));

      result.work_order_open_id = openWO?.id || null;
      result.work_order_closed_id = closedWO?.id || null;
    }
  } catch (e: any) {
    console.warn('Failed to discover work orders:', e.message);
  }

  // Discover equipment
  try {
    const { data: equipment } = await client
      .from('pms_equipment')
      .select('id')
      .eq('yacht_id', yacht_id)
      .limit(1);

    if (equipment && equipment.length > 0) {
      result.found.equipment = equipment.length;
      result.equipment_id = equipment[0].id;
    }
  } catch (e: any) {
    console.warn('Failed to discover equipment:', e.message);
  }

  // Discover parts
  try {
    const { data: parts } = await client
      .from('pms_parts')
      .select('id')
      .eq('yacht_id', yacht_id)
      .limit(1);

    if (parts && parts.length > 0) {
      result.found.parts = parts.length;
      result.part_id = parts[0].id;
    }
  } catch (e: any) {
    console.warn('Failed to discover parts:', e.message);
  }

  // Discover documents
  try {
    const { data: docs } = await client
      .from('documents')
      .select('id')
      .eq('yacht_id', yacht_id)
      .limit(1);

    if (docs && docs.length > 0) {
      result.found.documents = docs.length;
      result.document_id = docs[0].id;
    }
  } catch (e: any) {
    console.warn('Failed to discover documents:', e.message);
  }

  // Discover handover (table is plural: handovers)
  try {
    const { data: handover } = await client
      .from('handovers')
      .select('id')
      .eq('yacht_id', yacht_id)
      .limit(1);

    if (handover && handover.length > 0) {
      result.found.handover = handover.length;
      result.handover_id = handover[0].id;
    }
  } catch (e: any) {
    console.warn('Failed to discover handover:', e.message);
  }

  return result;
}

/**
 * Create minimal test data if none exists
 */
export async function ensureMinimalTestData(): Promise<DiscoveredTestData> {
  let data = await discoverTestData();

  const client = getTenantClient();
  const yacht_id = data.yacht_id;
  const user_id = data.user_id;

  // Create equipment if none exists (needed for faults and work orders)
  if (!data.equipment_id) {
    try {
      const { data: equipment, error } = await client
        .from('pms_equipment')
        .insert({
          yacht_id,
          name: 'Test Equipment - Diagnostic',
          make: 'Test',
          model: 'Diagnostic',
          location: 'Engine Room',
          status: 'operational',
          created_by: user_id,
        })
        .select()
        .single();

      if (equipment && !error) {
        data.equipment_id = equipment.id;
        data.found.equipment = 1;
        console.log('[Discovery] Created test equipment:', equipment.id);
      }
    } catch (e: any) {
      console.warn('Failed to create test equipment:', e.message);
    }
  }

  // Create fault if none exists
  if (!data.fault_id && data.equipment_id) {
    try {
      const { data: fault, error } = await client
        .from('pms_faults')
        .insert({
          yacht_id,
          equipment_id: data.equipment_id,
          title: 'Test Fault - Diagnostic',
          description: 'Created by diagnostic test for API testing',
          status: 'open',
          severity: 'medium',
          reported_by: user_id,
        })
        .select()
        .single();

      if (fault && !error) {
        data.fault_id = fault.id;
        data.fault_open_id = fault.id;
        data.found.faults = 1;
        console.log('[Discovery] Created test fault:', fault.id);
      }
    } catch (e: any) {
      console.warn('Failed to create test fault:', e.message);
    }
  }

  // Create work order if none exists
  if (!data.work_order_id && data.equipment_id) {
    try {
      const { data: wo, error } = await client
        .from('pms_work_orders')
        .insert({
          yacht_id,
          equipment_id: data.equipment_id,
          title: 'Test Work Order - Diagnostic',
          description: 'Created by diagnostic test for API testing',
          status: 'planned',
          priority: 'routine',
          created_by: user_id,
        })
        .select()
        .single();

      if (wo && !error) {
        data.work_order_id = wo.id;
        data.work_order_open_id = wo.id;
        data.found.work_orders = 1;
        console.log('[Discovery] Created test work order:', wo.id);
      }
    } catch (e: any) {
      console.warn('Failed to create test work order:', e.message);
    }
  }

  // Create part if none exists
  if (!data.part_id) {
    try {
      const { data: part, error } = await client
        .from('pms_parts')
        .insert({
          yacht_id,
          part_number: 'TEST-001',
          name: 'Test Part - Diagnostic',
          description: 'Created by diagnostic test',
          current_quantity_onboard: 10,
          min_quantity: 2,
          location: 'Storage A',
          created_by: user_id,
        })
        .select()
        .single();

      if (part && !error) {
        data.part_id = part.id;
        data.found.parts = 1;
        console.log('[Discovery] Created test part:', part.id);
      }
    } catch (e: any) {
      console.warn('Failed to create test part:', e.message);
    }
  }

  return data;
}

/**
 * Print discovery summary
 */
export function printDiscoverySummary(data: DiscoveredTestData): void {
  console.log('\n📊 TEST DATA DISCOVERY SUMMARY:');
  console.log('================================');
  console.log(`Yacht ID:       ${data.yacht_id}`);
  console.log(`User ID:        ${data.user_id}`);
  console.log('');
  console.log('Available entities:');
  console.log(`  Faults:       ${data.found.faults} (open: ${data.fault_open_id ? 'yes' : 'no'}, closed: ${data.fault_closed_id ? 'yes' : 'no'})`);
  console.log(`  Work Orders:  ${data.found.work_orders} (open: ${data.work_order_open_id ? 'yes' : 'no'}, closed: ${data.work_order_closed_id ? 'yes' : 'no'})`);
  console.log(`  Equipment:    ${data.found.equipment}`);
  console.log(`  Parts:        ${data.found.parts}`);
  console.log(`  Documents:    ${data.found.documents}`);
  console.log(`  Handover:     ${data.found.handover}`);
  console.log('================================\n');
}
