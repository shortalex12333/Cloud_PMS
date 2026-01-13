/**
 * Master DB Setup for E2E Tests
 *
 * Seeds MASTER DB with test user in user_accounts and fleet_registry.
 * Must be run before tests to ensure tenant lookup succeeds.
 */

import { createClient, SupabaseClient } from '@supabase/supabase-js';

interface SetupResult {
  success: boolean;
  message: string;
  fleetRegistry?: any;
  userAccount?: any;
}

/**
 * Get MASTER DB client with service key (admin access)
 */
function getMasterAdminClient(): SupabaseClient {
  const url = process.env.MASTER_SUPABASE_URL;
  const serviceKey = process.env.MASTER_SUPABASE_SERVICE_KEY;

  if (!url || !serviceKey) {
    throw new Error('MASTER_SUPABASE_URL and MASTER_SUPABASE_SERVICE_KEY must be set');
  }

  return createClient(url, serviceKey);
}

/**
 * Ensure fleet_registry has entry for test yacht
 */
async function ensureFleetRegistry(client: SupabaseClient): Promise<any> {
  const yachtId = process.env.TEST_USER_YACHT_ID || 'TEST_YACHT_001';
  const tenantKeyAlias = `y${yachtId}`;

  // Check if exists
  const { data: existing } = await client
    .from('fleet_registry')
    .select('*')
    .eq('yacht_id', yachtId)
    .single();

  if (existing) {
    console.log(`[Setup] fleet_registry row exists for ${yachtId}`);
    return existing;
  }

  // Insert new row
  const { data, error } = await client
    .from('fleet_registry')
    .insert({
      yacht_id: yachtId,
      tenant_key_alias: tenantKeyAlias,
      yacht_name: 'M/Y Test Vessel',
      active: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    })
    .select()
    .single();

  if (error) {
    throw new Error(`Failed to insert fleet_registry: ${error.message}`);
  }

  console.log(`[Setup] Created fleet_registry row for ${yachtId}`);
  return data;
}

/**
 * Ensure user_accounts has entry for test user
 */
async function ensureUserAccount(
  client: SupabaseClient,
  userId: string
): Promise<any> {
  const yachtId = process.env.TEST_USER_YACHT_ID || 'TEST_YACHT_001';
  const role = process.env.TEST_USER_ROLE || 'chief_engineer';

  // Check if exists
  const { data: existing } = await client
    .from('user_accounts')
    .select('*')
    .eq('user_id', userId)
    .single();

  if (existing) {
    // Update status to active if not already
    if (existing.status !== 'active') {
      const { data, error } = await client
        .from('user_accounts')
        .update({ status: 'active', updated_at: new Date().toISOString() })
        .eq('user_id', userId)
        .select()
        .single();

      if (error) {
        throw new Error(`Failed to activate user_account: ${error.message}`);
      }
      console.log(`[Setup] Activated user_account for ${userId.slice(0, 8)}...`);
      return data;
    }

    console.log(`[Setup] user_accounts row exists for ${userId.slice(0, 8)}...`);
    return existing;
  }

  // Insert new row
  const { data, error } = await client
    .from('user_accounts')
    .insert({
      user_id: userId,
      yacht_id: yachtId,
      role: role,
      status: 'active', // Skip pending for test user
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    })
    .select()
    .single();

  if (error) {
    throw new Error(`Failed to insert user_accounts: ${error.message}`);
  }

  console.log(`[Setup] Created user_accounts row for ${userId.slice(0, 8)}...`);
  return data;
}

/**
 * Get user ID from email via auth.users (admin only)
 */
async function getUserIdByEmail(
  client: SupabaseClient,
  email: string
): Promise<string | null> {
  // Use admin API to get user by email
  const { data, error } = await client.auth.admin.getUserById(
    // Actually we need to list users and filter
    '' // This won't work - need different approach
  );

  // Alternative: Use service role to query auth.users directly
  // This requires a custom RPC or direct PostgREST access

  return null;
}

/**
 * Login and get user ID
 */
async function loginAndGetUserId(): Promise<string> {
  const url = process.env.MASTER_SUPABASE_URL;
  const anonKey = process.env.MASTER_SUPABASE_ANON_KEY;
  const email = process.env.TEST_USER_EMAIL;
  const password = process.env.TEST_USER_PASSWORD;

  if (!url || !anonKey || !email || !password) {
    throw new Error('Missing required env vars for login');
  }

  const client = createClient(url, anonKey);

  const { data, error } = await client.auth.signInWithPassword({
    email,
    password,
  });

  if (error) {
    throw new Error(`Login failed: ${error.message}`);
  }

  if (!data.user) {
    throw new Error('Login succeeded but no user returned');
  }

  return data.user.id;
}

/**
 * Main setup function - call before running tests
 */
export async function setupMasterDb(): Promise<SetupResult> {
  try {
    console.log('[Setup] Starting MASTER DB setup...');

    // Get admin client
    const adminClient = getMasterAdminClient();

    // Ensure fleet_registry exists
    const fleetRegistry = await ensureFleetRegistry(adminClient);

    // Login to get user ID (since we can't easily query auth.users)
    const userId = await loginAndGetUserId();
    console.log(`[Setup] Test user ID: ${userId.slice(0, 8)}...`);

    // Ensure user_accounts exists
    const userAccount = await ensureUserAccount(adminClient, userId);

    console.log('[Setup] MASTER DB setup complete!');

    return {
      success: true,
      message: 'MASTER DB setup complete',
      fleetRegistry,
      userAccount,
    };
  } catch (error: any) {
    console.error(`[Setup] MASTER DB setup failed: ${error.message}`);
    return {
      success: false,
      message: error.message,
    };
  }
}

/**
 * Cleanup function - remove test data (optional)
 */
export async function cleanupMasterDb(): Promise<void> {
  try {
    const adminClient = getMasterAdminClient();
    const userId = await loginAndGetUserId();

    // Remove user_accounts row
    await adminClient.from('user_accounts').delete().eq('user_id', userId);
    console.log('[Cleanup] Removed user_accounts row');

    // Don't remove fleet_registry - other tests may need it
  } catch (error: any) {
    console.error(`[Cleanup] Failed: ${error.message}`);
  }
}

// CLI runner
if (require.main === module) {
  setupMasterDb()
    .then((result) => {
      if (result.success) {
        console.log('✅ Setup complete');
        process.exit(0);
      } else {
        console.error('❌ Setup failed:', result.message);
        process.exit(1);
      }
    })
    .catch((error) => {
      console.error('❌ Setup error:', error);
      process.exit(1);
    });
}
