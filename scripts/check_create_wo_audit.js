/**
 * Check if create_work_order actions create audit log entries
 */

const { createClient } = require('@supabase/supabase-js');
require('dotenv').config({ path: '.env.e2e' });

const supabase = createClient(
  process.env.TENANT_SUPABASE_URL,
  process.env.TENANT_SUPABASE_SERVICE_ROLE_KEY
);

const TEST_YACHT_ID = process.env.TEST_YACHT_ID;

async function checkCreateWOAudit() {
  console.log('\n🔍 CHECKING FOR create_work_order AUDIT ENTRIES\n');
  console.log('='.repeat(80));

  const { data: audits, error } = await supabase
    .from('pms_audit_log')
    .select('*')
    .eq('yacht_id', TEST_YACHT_ID)
    .eq('action', 'create_work_order')
    .order('created_at', { ascending: false })
    .limit(10);

  if (error) {
    console.error('❌ Error:', error);
    return;
  }

  if (audits && audits.length > 0) {
    console.log(`✅ Found ${audits.length} create_work_order audit entries\n`);
    audits.forEach((audit, idx) => {
      console.log(`\n--- Audit ${idx + 1} ---`);
      console.log(JSON.stringify(audit, null, 2));
    });
  } else {
    console.log('❌ NO create_work_order audit entries found!');
    console.log('\nThis means create_work_order handler is NOT writing to pms_audit_log');
    console.log('\n📊 Let\'s check what actions ARE being audited:\n');

    const { data: allActions } = await supabase
      .from('pms_audit_log')
      .select('action')
      .eq('yacht_id', TEST_YACHT_ID);

    const uniqueActions = [...new Set(allActions.map(a => a.action))].sort();
    console.log('Actions with audit entries:');
    uniqueActions.forEach(action => console.log(`  - ${action}`));
  }

  console.log('\n' + '='.repeat(80));
}

checkCreateWOAudit().catch(console.error);
