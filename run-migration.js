#!/usr/bin/env node
/**
 * Execute SQL migration via Supabase API
 */

const SUPABASE_URL = 'https://vzsohavtuotocgrfkfyd.supabase.co';
const SERVICE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY';

async function runMigration() {
  console.log('🚀 ATTEMPTING TO RUN SQL MIGRATION VIA API\n');
  console.log('='.repeat(80));

  // SQL to execute
  const sql = `
    ALTER TABLE auth_users_yacht
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true;
  `;

  console.log('\n📋 SQL to execute:');
  console.log(sql);
  console.log('\n' + '='.repeat(80));

  // Try different API endpoints
  const endpoints = [
    { name: 'exec_sql', path: '/rest/v1/rpc/exec_sql' },
    { name: 'exec', path: '/rest/v1/rpc/exec' },
    { name: 'query', path: '/rest/v1/rpc/query' },
    { name: 'execute', path: '/rest/v1/rpc/execute' },
    { name: 'sql', path: '/rest/v1/rpc/sql' },
  ];

  for (const endpoint of endpoints) {
    console.log(`\n🔧 Trying endpoint: ${endpoint.name}`);
    console.log('-'.repeat(80));

    try {
      const response = await fetch(`${SUPABASE_URL}${endpoint.path}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'apikey': SERVICE_KEY,
          'Authorization': `Bearer ${SERVICE_KEY}`,
        },
        body: JSON.stringify({ query: sql }),
      });

      console.log('Status:', response.status);
      const text = await response.text();

      if (response.ok) {
        console.log('✅ SUCCESS!');
        console.log('Response:', text);
        return true;
      } else {
        console.log('❌ Failed');
        console.log('Response:', text.substring(0, 200));
      }
    } catch (err) {
      console.log('❌ Error:', err.message);
    }
  }

  console.log('\n' + '='.repeat(80));
  console.log('❌ CONCLUSION: Cannot execute SQL via REST API\n');
  console.log('Why: Supabase REST API does not expose SQL execution endpoints for security.');
  console.log('     The API only allows CRUD operations on tables, not DDL commands.\n');
  console.log('Solution: You must run the SQL via:');
  console.log('  1. Supabase Dashboard → SQL Editor');
  console.log('  2. psql command line (if you have database password)');
  console.log('  3. Supabase CLI (requires project linking)\n');

  return false;
}

runMigration().catch(console.error);
