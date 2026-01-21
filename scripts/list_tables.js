const { createClient } = require('@supabase/supabase-js');

const TENANT_SUPABASE_URL = 'https://vzsohavtuotocgrfkfyd.supabase.co';
const TENANT_SERVICE_KEY = process.env.TENANT_SUPABASE_SERVICE_ROLE_KEY;

if (!TENANT_SERVICE_KEY) {
  console.log('ERROR: TENANT_SUPABASE_SERVICE_ROLE_KEY not set');
  process.exit(1);
}

const supabase = createClient(TENANT_SUPABASE_URL, TENANT_SERVICE_KEY);

async function listTables() {
  console.log('=== Listing All Tables ===\n');

  const tableNames = [
    'equipment', 'work_orders', 'faults', 'parts', 'notes', 'handovers',
    'inventory', 'inventory_parts', 'spare_parts', 'maintenance_tasks',
    'pms_work_orders', 'pms_tasks', 'fault_reports', 'maintenance_records',
    'documents', 'doc_metadata', 'users', 'user_accounts', 'fleet_registry',
    'shopping_items', 'worklist', 'worklist_tasks', 'ledger_events'
  ];

  console.log('Checking tables:');
  for (const table of tableNames) {
    const { count, error } = await supabase.from(table).select('*', { count: 'exact', head: true });
    if (!error) {
      console.log(`  ✅ ${table}: ${count} records`);
    }
  }
}

listTables();
