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

async function checkTestData() {
  console.log('=== Checking Test Data for Microactions ===\n');
  const testData = {};

  // Check equipment
  console.log('1. Checking equipment...');
  const { data: equipment, count: eqCount } = await supabase
    .from('equipment')
    .select('*', { count: 'exact' })
    .eq('yacht_id', yacht_id)
    .limit(5);
  testData.equipment = {
    count: eqCount,
    sample: equipment?.map(e => ({ id: e.id, name: e.name }))
  };
  console.log(`   Found: ${eqCount} equipment records`);

  // Check work orders
  console.log('2. Checking work orders...');
  const { data: workOrders, count: woCount } = await supabase
    .from('work_orders')
    .select('*', { count: 'exact' })
    .eq('yacht_id', yacht_id)
    .limit(5);
  testData.work_orders = {
    count: woCount,
    sample: workOrders?.map(w => ({ id: w.id, title: w.title, status: w.status }))
  };
  console.log(`   Found: ${woCount} work order records`);

  // Check faults
  console.log('3. Checking faults...');
  const { data: faults, count: faultCount } = await supabase
    .from('faults')
    .select('*', { count: 'exact' })
    .eq('yacht_id', yacht_id)
    .limit(5);
  testData.faults = {
    count: faultCount,
    sample: faults?.map(f => ({ id: f.id, description: f.description?.substring(0, 50), status: f.status }))
  };
  console.log(`   Found: ${faultCount} fault records`);

  // Check parts/inventory
  console.log('4. Checking parts...');
  const { data: parts, count: partsCount } = await supabase
    .from('parts')
    .select('*', { count: 'exact' })
    .eq('yacht_id', yacht_id)
    .limit(5);
  testData.parts = {
    count: partsCount,
    sample: parts?.map(p => ({ id: p.id, name: p.name || p.part_name }))
  };
  console.log(`   Found: ${partsCount} part records`);

  // Check notes
  console.log('5. Checking notes...');
  const { data: notes, count: notesCount } = await supabase
    .from('notes')
    .select('*', { count: 'exact' })
    .eq('yacht_id', yacht_id)
    .limit(5);
  testData.notes = {
    count: notesCount,
    sample: notes?.slice(0, 3)
  };
  console.log(`   Found: ${notesCount} note records`);

  // Check handovers
  console.log('6. Checking handovers...');
  const { data: handovers, count: handoverCount } = await supabase
    .from('handovers')
    .select('*', { count: 'exact' })
    .eq('yacht_id', yacht_id)
    .limit(5);
  testData.handovers = {
    count: handoverCount,
    sample: handovers?.slice(0, 3)
  };
  console.log(`   Found: ${handoverCount} handover records`);

  // Check users for this yacht
  console.log('7. Checking users...');
  const { data: users, count: userCount } = await supabase
    .from('user_accounts')
    .select('*', { count: 'exact' })
    .eq('yacht_id', yacht_id)
    .limit(5);
  testData.users = {
    count: userCount,
    sample: users?.map(u => ({ id: u.user_id, role: u.role }))
  };
  console.log(`   Found: ${userCount} user records`);

  console.log('\n=== Summary ===');
  console.log(JSON.stringify(testData, null, 2));

  // Write evidence
  fs.writeFileSync(
    '/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/verification_handoff/evidence/MICROACTIONS_test_data.json',
    JSON.stringify(testData, null, 2)
  );
  console.log('\nEvidence written to MICROACTIONS_test_data.json');
}

checkTestData();
