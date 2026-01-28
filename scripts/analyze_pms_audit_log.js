/**
 * Deep analysis of pms_audit_log table
 * Get schema, sample data, and understand how it's used
 */

const { createClient } = require('@supabase/supabase-js');
require('dotenv').config({ path: '.env.e2e' });

const supabase = createClient(
  process.env.TENANT_SUPABASE_URL,
  process.env.TENANT_SUPABASE_SERVICE_ROLE_KEY
);

const TEST_YACHT_ID = process.env.TEST_YACHT_ID;

async function analyzePmsAuditLog() {
  console.log('\n🔍 DEEP ANALYSIS: pms_audit_log\n');
  console.log('='.repeat(80));

  // Get sample rows to understand structure
  console.log('\n📝 FETCHING SAMPLE ROWS (last 10):\n');

  const { data: samples, error: sampleError } = await supabase
    .from('pms_audit_log')
    .select('*')
    .order('created_at', { ascending: false })
    .limit(10);

  if (sampleError) {
    console.error('❌ Error fetching samples:', sampleError);
    console.log('\nTable may not exist or may have RLS policies blocking access.');
    console.log('Trying with yacht_id filter...\n');

    const { data: filteredSamples, error: filteredError } = await supabase
      .from('pms_audit_log')
      .select('*')
      .eq('yacht_id', TEST_YACHT_ID)
      .order('created_at', { ascending: false })
      .limit(10);

    if (filteredError) {
      console.error('❌ Still failed:', filteredError);
      return;
    }

    if (filteredSamples && filteredSamples.length > 0) {
      console.log('✅ Found rows with yacht_id filter\n');
      displaySamples(filteredSamples);
    } else {
      console.log('⚠️  No audit log entries found for this yacht');
      console.log('\nLet\'s check if table is empty...');

      const { count } = await supabase
        .from('pms_audit_log')
        .select('*', { count: 'exact', head: true });

      console.log(`Total rows in table: ${count || 0}`);
    }
  } else if (samples && samples.length > 0) {
    displaySamples(samples);
  } else {
    console.log('⚠️  Table exists but is empty');
  }

  // Get stats
  console.log('\n' + '='.repeat(80));
  console.log('\n📊 STATISTICS:\n');

  const { count: totalCount } = await supabase
    .from('pms_audit_log')
    .select('*', { count: 'exact', head: true })
    .eq('yacht_id', TEST_YACHT_ID);

  console.log(`Total audit entries for yacht ${TEST_YACHT_ID}: ${totalCount || 0}`);

  // Count by action type
  console.log('\n📋 AUDIT ENTRIES BY ACTION:\n');

  const { data: actions, error: actionsError } = await supabase
    .from('pms_audit_log')
    .select('action')
    .eq('yacht_id', TEST_YACHT_ID);

  if (!actionsError && actions) {
    const actionCounts = {};
    actions.forEach(row => {
      const action = row.action || 'unknown';
      actionCounts[action] = (actionCounts[action] || 0) + 1;
    });

    const sorted = Object.entries(actionCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 20);

    sorted.forEach(([action, count]) => {
      const bar = '█'.repeat(Math.min(count, 50));
      console.log(`${action.padEnd(30)} ${count.toString().padStart(5)} ${bar}`);
    });
  }

  // Find work_order related entries
  console.log('\n' + '='.repeat(80));
  console.log('\n🔧 WORK ORDER RELATED AUDIT ENTRIES:\n');

  const { data: woAudits, error: woError } = await supabase
    .from('pms_audit_log')
    .select('*')
    .eq('yacht_id', TEST_YACHT_ID)
    .ilike('action', '%work_order%')
    .order('created_at', { ascending: false })
    .limit(5);

  if (!woError && woAudits && woAudits.length > 0) {
    woAudits.forEach((audit, idx) => {
      console.log(`\n--- Work Order Audit ${idx + 1} ---`);
      console.log(JSON.stringify(audit, null, 2));
    });
  } else {
    console.log('No work_order audit entries found');
  }

  console.log('\n' + '='.repeat(80));
  console.log('\n✅ ANALYSIS COMPLETE\n');
}

function displaySamples(samples) {
  console.log(`Found ${samples.length} sample rows\n`);

  // Display first sample in detail to understand schema
  if (samples[0]) {
    console.log('📋 SCHEMA (from first row):');
    console.log('-'.repeat(80));
    const firstRow = samples[0];
    Object.keys(firstRow).forEach(key => {
      const value = firstRow[key];
      const type = typeof value;
      const displayValue = value === null ? 'NULL' :
                          type === 'object' ? JSON.stringify(value).substring(0, 50) :
                          String(value).substring(0, 50);
      console.log(`${key.padEnd(25)} | ${type.padEnd(10)} | ${displayValue}`);
    });
  }

  // Display all samples
  console.log('\n📝 ALL SAMPLES:');
  console.log('='.repeat(80));
  samples.forEach((row, idx) => {
    console.log(`\n--- Sample ${idx + 1} ---`);
    console.log(JSON.stringify(row, null, 2));
  });
}

analyzePmsAuditLog().catch(console.error);
