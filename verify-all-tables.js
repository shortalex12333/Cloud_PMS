/**
 * Verify ALL tables referenced in codebase actually exist
 */

const SUPABASE_URL = 'https://vzsohavtuotocgrfkfyd.supabase.co';
const SERVICE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY';

// Tables found in codebase
const TABLES_TO_CHECK = [
  'auth_users',
  'auth_users_yacht',
  'yacht_signatures',
  'api_tokens',
  'search_document_chunks',
  'doc_metadata',
  'users',  // Referenced in RLS policy
  'user_profiles',
  'profiles',
];

async function verifyTables() {
  console.log('🔍 VERIFYING ALL TABLES IN DATABASE\n');
  console.log('='.repeat(80));

  for (const tableName of TABLES_TO_CHECK) {
    console.log(`\n📋 Testing: ${tableName}`);
    console.log('-'.repeat(80));

    const response = await fetch(`${SUPABASE_URL}/rest/v1/${tableName}?select=*&limit=0`, {
      headers: {
        'apikey': SERVICE_KEY,
        'Authorization': `Bearer ${SERVICE_KEY}`,
      }
    });

    if (response.ok) {
      console.log(`✅ EXISTS - Status: ${response.status}`);

      // Get one row to see columns
      const response2 = await fetch(`${SUPABASE_URL}/rest/v1/${tableName}?select=*&limit=1`, {
        headers: {
          'apikey': SERVICE_KEY,
          'Authorization': `Bearer ${SERVICE_KEY}`,
        }
      });

      const data = await response2.json();
      if (data.length > 0) {
        console.log(`   Columns: ${Object.keys(data[0]).join(', ')}`);
      } else {
        console.log(`   (empty table)`);
      }
    } else {
      const error = await response.json();
      console.log(`❌ DOES NOT EXIST - Status: ${response.status}`);
      console.log(`   Error: ${error.message}`);
      if (error.hint) {
        console.log(`   Hint: ${error.hint}`);
      }
    }
  }

  console.log('\n' + '='.repeat(80));
  console.log('🏁 VERIFICATION COMPLETE\n');
}

verifyTables().catch(console.error);
