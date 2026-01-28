/**
 * Discover ALL audit tables in the database
 * Find their columns, understand their purpose
 */

const { createClient } = require('@supabase/supabase-js');
require('dotenv').config({ path: '.env.e2e' });

const supabase = createClient(
  process.env.TENANT_SUPABASE_URL,
  process.env.TENANT_SUPABASE_SERVICE_ROLE_KEY
);

async function discoverAuditTables() {
  console.log('\n🔍 DISCOVERING ALL AUDIT TABLES\n');
  console.log('='.repeat(80));

  // Query for all tables with 'audit' in the name
  const { data: tables, error: tablesError } = await supabase
    .from('information_schema.tables')
    .select('table_name')
    .eq('table_schema', 'public')
    .ilike('table_name', '%audit%');

  if (tablesError) {
    console.error('Error querying tables:', tablesError);
    // Try alternative approach - query pg_tables directly
    console.log('\nTrying alternative approach...\n');

    const { data, error } = await supabase.rpc('get_audit_tables');
    if (error) {
      console.log('RPC not available, using SQL query...\n');
    }
  }

  // Also check for common audit table patterns
  const possibleAuditTables = [
    'audit_log',
    'pms_audit_log',
    'audit_trail',
    'pms_audit_trail',
    'audit_events',
    'pms_audit_events',
    'action_audit',
    'pms_action_audit',
    'work_order_audit',
    'pms_work_order_audit',
    'entity_audit',
    'pms_entity_audit',
    'change_log',
    'pms_change_log',
    'activity_log',
    'pms_activity_log'
  ];

  console.log('\n📋 CHECKING FOR AUDIT TABLES:\n');

  const foundTables = [];

  for (const tableName of possibleAuditTables) {
    try {
      const { data, error } = await supabase
        .from(tableName)
        .select('*')
        .limit(1);

      if (!error) {
        console.log(`✅ ${tableName} - EXISTS`);
        foundTables.push(tableName);
      } else if (error.code === 'PGRST204') {
        // Table exists but no rows
        console.log(`✅ ${tableName} - EXISTS (empty)`);
        foundTables.push(tableName);
      } else {
        console.log(`❌ ${tableName} - NOT FOUND`);
      }
    } catch (e) {
      console.log(`❌ ${tableName} - ERROR: ${e.message}`);
    }
  }

  console.log('\n' + '='.repeat(80));
  console.log(`\n📊 FOUND ${foundTables.length} AUDIT TABLES\n`);

  // Get schema for each found table
  for (const tableName of foundTables) {
    console.log('\n' + '='.repeat(80));
    console.log(`\n📋 SCHEMA FOR: ${tableName}\n`);
    console.log('-'.repeat(80));

    const { data: columns, error: columnsError } = await supabase
      .from('information_schema.columns')
      .select('column_name, data_type, is_nullable, column_default')
      .eq('table_name', tableName)
      .order('ordinal_position');

    if (columnsError) {
      console.error(`Error getting schema: ${columnsError.message}`);
      continue;
    }

    if (columns && columns.length > 0) {
      console.log('COLUMN NAME                 | DATA TYPE              | NULLABLE | DEFAULT');
      console.log('-'.repeat(80));
      columns.forEach(col => {
        const name = col.column_name.padEnd(27);
        const type = col.data_type.padEnd(22);
        const nullable = col.is_nullable.padEnd(8);
        const def = col.column_default ? col.column_default.substring(0, 20) : '';
        console.log(`${name} | ${type} | ${nullable} | ${def}`);
      });

      // Get sample rows
      console.log('\n📝 SAMPLE ROWS (last 3):');
      const { data: samples, error: sampleError } = await supabase
        .from(tableName)
        .select('*')
        .order('created_at', { ascending: false })
        .limit(3);

      if (!sampleError && samples && samples.length > 0) {
        samples.forEach((row, idx) => {
          console.log(`\n--- Sample ${idx + 1} ---`);
          console.log(JSON.stringify(row, null, 2));
        });
      } else {
        console.log('(No sample rows available)');
      }

      // Count total rows
      const { count, error: countError } = await supabase
        .from(tableName)
        .select('*', { count: 'exact', head: true });

      if (!countError) {
        console.log(`\n📊 Total rows: ${count}`);
      }
    } else {
      console.log('(No columns found - table may not be accessible)');
    }
  }

  console.log('\n' + '='.repeat(80));
  console.log('\n✅ AUDIT TABLE DISCOVERY COMPLETE\n');
}

discoverAuditTables().catch(console.error);
