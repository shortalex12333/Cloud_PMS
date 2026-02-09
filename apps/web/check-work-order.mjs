// Check if work order exists
const ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM1OTI4NzUsImV4cCI6MjA3OTE2ODg3NX0.JhJLvLSfLD3OtPDxTgHqgF8dNaZk8ius62jKN68E4WE";
const SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY";

const TEST_WO_ID = 'b36238da-b0fa-4815-883c-0be61fc190d0';
const USER_YACHT_ID = '85fe1119-b04c-41ac-80f1-829d23322598';

async function check() {
  // Check with service key (bypasses RLS)
  console.log('1. Checking work order with service key (bypasses RLS)...');
  const response1 = await fetch(`https://vzsohavtuotocgrfkfyd.supabase.co/rest/v1/pms_work_orders?id=eq.${TEST_WO_ID}`, {
    headers: {
      'apikey': SERVICE_KEY,
      'Authorization': `Bearer ${SERVICE_KEY}`,
    },
  });
  const data1 = await response1.json();
  console.log('  Found:', data1.length, 'records');
  if (data1.length > 0) {
    console.log('  Work order yacht_id:', data1[0].yacht_id);
    console.log('  Title:', data1[0].title);
  }

  // List all work orders for user's yacht
  console.log('\n2. Listing work orders for yacht', USER_YACHT_ID, '...');
  const response2 = await fetch(`https://vzsohavtuotocgrfkfyd.supabase.co/rest/v1/pms_work_orders?yacht_id=eq.${USER_YACHT_ID}&select=id,title&limit=5`, {
    headers: {
      'apikey': SERVICE_KEY,
      'Authorization': `Bearer ${SERVICE_KEY}`,
    },
  });
  const data2 = await response2.json();
  console.log('  Found:', data2.length, 'work orders');
  for (const wo of data2) {
    console.log('   -', wo.id, ':', wo.title);
  }
}

check().catch(console.error);
