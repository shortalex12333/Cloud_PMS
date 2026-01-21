const { createClient } = require('@supabase/supabase-js');
const fs = require('fs');

const TENANT_SUPABASE_URL = 'https://vzsohavtuotocgrfkfyd.supabase.co';
const TENANT_SERVICE_KEY = process.env.TENANT_SUPABASE_SERVICE_ROLE_KEY;

if (!TENANT_SERVICE_KEY) {
  console.log('ERROR: TENANT_SUPABASE_SERVICE_ROLE_KEY not set');
  process.exit(1);
}

const supabase = createClient(TENANT_SUPABASE_URL, TENANT_SERVICE_KEY);
const yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598';

async function getActionContext() {
  console.log('=== Getting Context Data for Microaction Testing ===\n');
  const context = { yacht_id };

  // Get equipment
  console.log('1. Getting equipment...');
  const { data: equipment } = await supabase
    .from('equipment')
    .select('id, name, equipment_type, department')
    .eq('yacht_id', yacht_id)
    .limit(5);
  context.equipment = equipment;
  console.log(`   Sample: ${equipment?.[0]?.name} (${equipment?.[0]?.id})`);

  // Get pms_work_orders
  console.log('2. Getting pms_work_orders...');
  const { data: workOrders } = await supabase
    .from('pms_work_orders')
    .select('id, title, status, priority, equipment_id')
    .eq('yacht_id', yacht_id)
    .limit(5);
  context.pms_work_orders = workOrders;
  console.log(`   Sample: ${workOrders?.[0]?.title} (${workOrders?.[0]?.id})`);

  // Get handovers
  console.log('3. Getting handovers...');
  const { data: handovers } = await supabase
    .from('handovers')
    .select('id, title, status')
    .eq('yacht_id', yacht_id)
    .limit(5);
  context.handovers = handovers;
  console.log(`   Sample: ${handovers?.[0]?.title} (${handovers?.[0]?.id})`);

  // Get documents
  console.log('4. Getting documents...');
  const { data: documents } = await supabase
    .from('doc_metadata')
    .select('id, filename, storage_path')
    .eq('yacht_id', yacht_id)
    .limit(5);
  context.documents = documents;
  console.log(`   Sample: ${documents?.[0]?.filename} (${documents?.[0]?.id})`);

  console.log('\n=== Action Test Context ===');
  console.log(JSON.stringify(context, null, 2));

  // Write context file
  fs.writeFileSync(
    '/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/verification_handoff/evidence/MICROACTIONS_context.json',
    JSON.stringify(context, null, 2)
  );
  console.log('\nContext written to MICROACTIONS_context.json');
}

getActionContext();
