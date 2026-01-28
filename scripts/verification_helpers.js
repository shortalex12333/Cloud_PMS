// verification_helpers.js - Database query helpers for verification
// Usage: node scripts/verification_helpers.js [command] [args]

const { createClient } = require('@supabase/supabase-js');
require('dotenv').config({ path: '.env.e2e' });

// Initialize Supabase client
const supabase = createClient(
  process.env.TENANT_SUPABASE_URL,
  process.env.TENANT_SUPABASE_SERVICE_ROLE_KEY
);

const TEST_YACHT_ID = process.env.TEST_YACHT_ID;
const TEST_USER_ID = process.env.TEST_USER_ID;

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Query database for entity by ID
 */
async function getEntity(tableName, entityId) {
  const { data, error } = await supabase
    .from(tableName)
    .select('*')
    .eq('id', entityId)
    .single();

  if (error) {
    console.log('ERROR:', error.message);
    return null;
  }

  return data;
}

/**
 * Query audit log for action
 */
async function getAuditLog(action, entityId) {
  const { data, error } = await supabase
    .from('pms_audit_log')
    .select('*')
    .eq('action', action)
    .eq('entity_id', entityId);

  if (error) {
    console.log('ERROR:', error.message);
    return null;
  }

  return data;
}

/**
 * Count entities in table (for BEFORE check)
 */
async function countEntities(tableName, filters = {}) {
  let query = supabase
    .from(tableName)
    .select('*', { count: 'exact', head: true })
    .eq('yacht_id', TEST_YACHT_ID);

  // Add additional filters
  for (const [key, value] of Object.entries(filters)) {
    query = query.eq(key, value);
  }

  const { count, error } = await query;

  if (error) {
    console.log('ERROR:', error.message);
    return null;
  }

  return count;
}

/**
 * List all tables
 */
async function listTables() {
  const { data, error } = await supabase
    .from('information_schema.tables')
    .select('table_name')
    .eq('table_schema', 'public')
    .like('table_name', 'pms_%');

  if (error) {
    console.log('ERROR:', error.message);
    return null;
  }

  return data.map(row => row.table_name);
}

/**
 * Execute action via API
 */
async function executeAction(action, payload) {
  // This would call the actual API endpoint
  // For now, return placeholder
  console.log('TODO: Implement API call to /v1/actions/execute');
  console.log('Action:', action);
  console.log('Payload:', payload);

  return {
    status: 'TODO',
    message: 'API execution not yet implemented in helper'
  };
}

/**
 * Verify RLS (try to access entity from different yacht)
 */
async function verifyRLS(tableName, entityId, wrongYachtId = '00000000-0000-0000-0000-000000000000') {
  // Try to query entity with wrong yacht_id in context
  // This would require setting up RLS-aware Supabase client
  console.log('TODO: Implement RLS verification');
  console.log('Table:', tableName);
  console.log('Entity ID:', entityId);
  console.log('Wrong Yacht ID:', wrongYachtId);

  return {
    status: 'TODO',
    message: 'RLS verification not yet implemented'
  };
}

// ============================================================================
// CLI Commands
// ============================================================================

const commands = {
  'get-entity': async (tableName, entityId) => {
    const result = await getEntity(tableName, entityId);
    console.log(JSON.stringify(result, null, 2));
  },

  'get-audit': async (action, entityId) => {
    const result = await getAuditLog(action, entityId);
    console.log(JSON.stringify(result, null, 2));
  },

  'count': async (tableName, ...filterArgs) => {
    const filters = {};
    for (let i = 0; i < filterArgs.length; i += 2) {
      filters[filterArgs[i]] = filterArgs[i + 1];
    }
    const count = await countEntities(tableName, filters);
    console.log('Count:', count);
  },

  'list-tables': async () => {
    const tables = await listTables();
    console.log('Tables:');
    tables.forEach(table => console.log('  -', table));
  },

  'execute': async (action, ...payloadArgs) => {
    const payload = {};
    for (let i = 0; i < payloadArgs.length; i += 2) {
      payload[payloadArgs[i]] = payloadArgs[i + 1];
    }
    const result = await executeAction(action, payload);
    console.log(JSON.stringify(result, null, 2));
  },

  'verify-rls': async (tableName, entityId) => {
    const result = await verifyRLS(tableName, entityId);
    console.log(JSON.stringify(result, null, 2));
  },

  'help': () => {
    console.log(`
Verification Helpers - Database Query Utilities

Usage: node scripts/verification_helpers.js [command] [args]

Commands:

  get-entity <table> <id>
    Get entity by ID from table
    Example: node scripts/verification_helpers.js get-entity pms_work_orders abc-123

  get-audit <action> <entity_id>
    Get audit log entry for action
    Example: node scripts/verification_helpers.js get-audit create_work_order abc-123

  count <table> [key value ...]
    Count entities in table with optional filters
    Example: node scripts/verification_helpers.js count pms_work_orders status open

  list-tables
    List all PMS tables
    Example: node scripts/verification_helpers.js list-tables

  execute <action> [key value ...]
    Execute action via API (TODO: not yet implemented)
    Example: node scripts/verification_helpers.js execute create_work_order title "Test WO"

  verify-rls <table> <entity_id>
    Verify RLS isolation (TODO: not yet implemented)
    Example: node scripts/verification_helpers.js verify-rls pms_work_orders abc-123

  help
    Show this help message

Environment:
  Requires .env.e2e with:
  - TENANT_SUPABASE_URL
  - TENANT_SUPABASE_SERVICE_ROLE_KEY
  - TEST_YACHT_ID
  - TEST_USER_ID
`);
  }
};

// ============================================================================
// Main
// ============================================================================

async function main() {
  const [,, command, ...args] = process.argv;

  if (!command || command === 'help') {
    commands.help();
    process.exit(0);
  }

  if (!commands[command]) {
    console.error(`Unknown command: ${command}`);
    console.error('Run "node scripts/verification_helpers.js help" for usage');
    process.exit(1);
  }

  try {
    await commands[command](...args);
  } catch (error) {
    console.error('Error:', error.message);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = {
  getEntity,
  getAuditLog,
  countEntities,
  listTables,
  executeAction,
  verifyRLS
};
