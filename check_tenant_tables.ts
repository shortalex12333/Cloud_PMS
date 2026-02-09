/**
 * Check what handover-related tables exist in the tenant database
 */

import { createClient } from '@supabase/supabase-js';
import * as dotenv from 'dotenv';
import * as path from 'path';

dotenv.config({ path: path.join(__dirname, '.env.e2e.local') });

const DEFAULT_YACHT = process.env.DEFAULT_YACHT_CODE || 'yTEST_YACHT_001';
const url = process.env[`${DEFAULT_YACHT}_SUPABASE_URL`] || process.env.SUPABASE_URL;
const key = process.env[`${DEFAULT_YACHT}_SUPABASE_SERVICE_KEY`] || process.env.SUPABASE_SERVICE_KEY;

if (!url || !key) {
  console.error(`Missing env vars for ${DEFAULT_YACHT}`);
  console.error(`  ${DEFAULT_YACHT}_SUPABASE_URL: ${url ? 'present' : 'MISSING'}`);
  console.error(`  ${DEFAULT_YACHT}_SUPABASE_SERVICE_KEY: ${key ? 'present' : 'MISSING'}`);
  process.exit(1);
}

console.log('='.repeat(80));
console.log('TENANT DATABASE TABLE CHECK');
console.log('='.repeat(80));
console.log('');
console.log(`Tenant: ${DEFAULT_YACHT}`);
console.log(`URL: ${url}`);
console.log('');

const client = createClient(url, key);

async function checkTables() {
  try {
    // Query information_schema to see what handover tables exist
    console.log('Checking for handover-related tables...');
    console.log('');

    const { data, error } = await client
      .from('information_schema.tables')
      .select('table_name')
      .eq('table_schema', 'public')
      .like('table_name', '%handover%')
      .order('table_name');

    if (error) {
      console.error('Error querying information_schema:', error);

      // Try an alternative method - query the tables directly
      console.log('');
      console.log('Trying direct table queries...');
      console.log('');

      const tables = ['pms_handover', 'handover_items', 'handover_exports', 'handovers', 'handover_drafts'];

      for (const table of tables) {
        try {
          const result = await client.from(table).select('count', { count: 'exact', head: true });
          if (result.error) {
            console.log(`❌ ${table}: ${result.error.message}`);
          } else {
            console.log(`✅ ${table}: EXISTS (${result.count} rows)`);
          }
        } catch (e: any) {
          console.log(`❌ ${table}: ${e.message}`);
        }
      }
    } else if (data) {
      console.log(`Found ${data.length} handover-related tables:`);
      console.log('');
      data.forEach(row => {
        console.log(`  ✓ ${row.table_name}`);
      });
    } else {
      console.log('No handover-related tables found.');
    }

  } catch (e: any) {
    console.error('Fatal error:', e);
  }

  console.log('');
  console.log('='.repeat(80));
}

checkTables();
