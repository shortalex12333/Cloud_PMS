#!/usr/bin/env node
/**
 * Inspect auth table schemas using Supabase REST API
 */

const SUPABASE_URL = 'https://vzsohavtuotocgrfkfyd.supabase.co';
const SERVICE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY';

async function inspectTables() {
  console.log('🔍 INSPECTING AUTH TABLE SCHEMAS\n');
  console.log('='.repeat(80));

  // Check 1: Get sample from auth_users_yacht
  console.log('\n📋 auth_users_yacht - Sample Data');
  console.log('-'.repeat(80));

  const response1 = await fetch(`${SUPABASE_URL}/rest/v1/auth_users_yacht?limit=1`, {
    headers: {
      'apikey': SERVICE_KEY,
      'Authorization': `Bearer ${SERVICE_KEY}`,
    }
  });

  if (response1.ok) {
    const data1 = await response1.json();
    if (data1.length > 0) {
      console.log('Columns:', Object.keys(data1[0]).join(', '));
      console.log('Sample:', JSON.stringify(data1[0], null, 2));
    } else {
      console.log('(empty table)');
    }
  } else {
    const error1 = await response1.json();
    console.log('Error:', error1);
  }

  // Check 2: Try auth_role_assignments
  console.log('\n📋 auth_role_assignments - Check if exists');
  console.log('-'.repeat(80));

  const response2 = await fetch(`${SUPABASE_URL}/rest/v1/auth_role_assignments?limit=1`, {
    headers: {
      'apikey': SERVICE_KEY,
      'Authorization': `Bearer ${SERVICE_KEY}`,
    }
  });

  if (response2.ok) {
    const data2 = await response2.json();
    console.log('✅ Table exists!');
    if (data2.length > 0) {
      console.log('Columns:', Object.keys(data2[0]).join(', '));
      console.log('Sample:', JSON.stringify(data2[0], null, 2));
    } else {
      console.log('(empty table)');
    }
  } else {
    const error2 = await response2.json();
    console.log('❌ Table does not exist');
    console.log('Error:', error2.message);
  }

  // Check 3: Get all tables starting with 'auth'
  console.log('\n📋 All auth_* tables');
  console.log('-'.repeat(80));

  const tablesToCheck = [
    'auth_users',
    'auth_users_yacht',
    'auth_role_assignments',
    'auth_roles',
    'auth_user_roles',
    'auth_signatures',
    'auth_microsoft_tokens',
  ];

  for (const table of tablesToCheck) {
    const resp = await fetch(`${SUPABASE_URL}/rest/v1/${table}?limit=0`, {
      headers: {
        'apikey': SERVICE_KEY,
        'Authorization': `Bearer ${SERVICE_KEY}`,
      }
    });

    if (resp.ok) {
      console.log(`  ✅ ${table}`);
    } else {
      console.log(`  ❌ ${table}`);
    }
  }

  console.log('\n' + '='.repeat(80));
  console.log('🏁 INSPECTION COMPLETE\n');
}

inspectTables().catch(console.error);
