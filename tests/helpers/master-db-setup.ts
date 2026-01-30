/**
 * Master DB Setup for E2E Tests
 *
 * Seeds MASTER DB with test user in user_accounts and fleet_registry.
 * Must be run before tests to ensure tenant lookup succeeds.
 */

import { createClient, SupabaseClient } from '@supabase/supabase-js';
import * as crypto from 'crypto';

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
  // Check both naming conventions for service key
  const serviceKey = process.env.MASTER_SUPABASE_SERVICE_ROLE_KEY || process.env.MASTER_SUPABASE_SERVICE_KEY;

  if (!url || !serviceKey) {
    throw new Error('MASTER_SUPABASE_URL and MASTER_SUPABASE_SERVICE_ROLE_KEY must be set');
  }

  return createClient(url, serviceKey);
}

/**
 * Ensure fleet_registry has entry for test yacht
 */
async function ensureFleetRegistry(client: SupabaseClient): Promise<any> {
  const yachtId = process.env.TEST_USER_YACHT_ID || '85fe1119-b04c-41ac-80f1-829d23322598';
  const tenantKeyAlias = process.env.TEST_USER_TENANT_KEY || 'yTEST_YACHT_001';

  // Check if exists
  const { data: existing, error: selectError } = await client
    .from('fleet_registry')
    .select('yacht_id, yacht_name, active')
    .eq('yacht_id', yachtId)
    .single();

  if (existing) {
    console.log(`[Setup] fleet_registry row exists for ${yachtId.slice(0, 8)}...`);
    return existing;
  }

  // Compute yacht_id_hash (SHA256 of yacht_id)
  const yachtIdHash = crypto.createHash('sha256').update(yachtId).digest('hex');
  const testEmail = process.env.TEST_USER_EMAIL || 'x@alex-short.com';

  // Insert new row with all potentially required fields
  const insertData = {
    yacht_id: yachtId,
    yacht_id_hash: yachtIdHash,
    yacht_name: 'M/Y Test Vessel',
    buyer_email: testEmail,
    active: true,
  };

  const { data, error } = await client
    .from('fleet_registry')
    .insert(insertData)
    .select()
    .single();

  if (error) {
    // If insert fails, try upsert approach
    console.log(`[Setup] Insert failed: ${error.message}, trying upsert...`);

    const { data: data2, error: error2 } = await client
      .from('fleet_registry')
      .upsert(insertData, { onConflict: 'yacht_id' })
      .select()
      .single();

    if (error2) {
      throw new Error(`Failed to upsert fleet_registry: ${error2.message}`);
    }
    console.log(`[Setup] Created fleet_registry row for ${yachtId.slice(0, 8)}...`);
    return data2;
  }

  console.log(`[Setup] Created fleet_registry row for ${yachtId.slice(0, 8)}...`);
  return data;
}

/**
 * Ensure user_accounts has entry for test user
 */
async function ensureUserAccount(
  client: SupabaseClient,
  userId: string
): Promise<any> {
  const yachtId = process.env.TEST_USER_YACHT_ID || '85fe1119-b04c-41ac-80f1-829d23322598';
  const role = process.env.TEST_USER_ROLE || 'chief_engineer';

  // Check if exists - try both column names
  let existing = null;
  const { data: existingById } = await client
    .from('user_accounts')
    .select('*')
    .eq('id', userId)
    .single();

  if (existingById) {
    existing = existingById;
  } else {
    const { data: existingByUserId } = await client
      .from('user_accounts')
      .select('*')
      .eq('user_id', userId)
      .single();
    existing = existingByUserId;
  }

  if (existing) {
    // Check if yacht_id needs updating (to match env var doc)
    const needsYachtUpdate = existing.yacht_id !== yachtId;
    const needsStatusUpdate = existing.status !== 'active';

    if (needsYachtUpdate || needsStatusUpdate) {
      console.log(`[Setup] Updating user_accounts: yacht_id ${existing.yacht_id} -> ${yachtId}`);

      // Try simple update with only the fields that need changing
      const updateFields: any = {};
      if (needsYachtUpdate) updateFields.yacht_id = yachtId;
      if (needsStatusUpdate) updateFields.status = 'active';

      const { data, error } = await client
        .from('user_accounts')
        .update(updateFields)
        .eq('id', userId)
        .select()
        .single();

      if (error) {
        console.log(`[Setup] Update failed: ${error.message}`);
        // Try delete and insert as last resort
        console.log(`[Setup] Trying delete + insert...`);
        const { error: delError } = await client
          .from('user_accounts')
          .delete()
          .eq('id', userId);

        if (delError) {
          console.log(`[Setup] Delete failed: ${delError.message}, continuing with existing data`);
          return existing;
        }

        // Insert fresh row
        const testEmail = process.env.TEST_USER_EMAIL || 'x@alex-short.com';
        const { data: newData, error: insertError } = await client
          .from('user_accounts')
          .insert({
            id: userId,
            email: testEmail,
            yacht_id: yachtId,
            role: role,
            status: 'active',
          })
          .select()
          .single();

        if (insertError) {
          console.log(`[Setup] Insert after delete failed: ${insertError.message}`);
          return existing;
        }
        console.log(`[Setup] Recreated user_accounts for ${userId.slice(0, 8)}... yacht_id=${yachtId}`);
        return newData;
      }

      console.log(`[Setup] Updated user_account for ${userId.slice(0, 8)}... yacht_id=${yachtId}`);
      return data;
    }

    console.log(`[Setup] user_accounts row exists for ${userId.slice(0, 8)}... yacht_id=${existing.yacht_id}`);
    return existing;
  }

  // Insert new row - only include required fields, let DB handle defaults
  const { data, error } = await client
    .from('user_accounts')
    .insert({
      user_id: userId,
      yacht_id: yachtId,
      role: role,
      status: 'active', // Skip pending for test user
    })
    .select()
    .single();

  if (error) {
    // Try alternative column name (id instead of user_id)
    const testEmail = process.env.TEST_USER_EMAIL || 'x@alex-short.com';
    console.log(`[Setup] Insert with user_id failed: ${error.message}, trying id with email...`);
    const { data: data2, error: error2 } = await client
      .from('user_accounts')
      .insert({
        id: userId,  // Alternative column name
        yacht_id: yachtId,
        email: testEmail,
        role: role,
        status: 'active',
      })
      .select()
      .single();

    if (error2) {
      throw new Error(`Failed to insert user_accounts: ${error2.message}`);
    }

    console.log(`[Setup] Created user_accounts row for ${userId.slice(0, 8)}...`);
    return data2;
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
 * Get TENANT DB client with service key (admin access)
 */
function getTenantAdminClient(): SupabaseClient | null {
  const tenantKeyAlias = process.env.TEST_USER_TENANT_KEY || 'yTEST_YACHT_001';
  const url = process.env[`${tenantKeyAlias}_SUPABASE_URL`] || process.env.SUPABASE_URL;
  const serviceKey = process.env[`${tenantKeyAlias}_SUPABASE_SERVICE_KEY`] || process.env.SUPABASE_SERVICE_KEY;

  if (!url || !serviceKey) {
    console.log(`[Setup] TENANT credentials not found for ${tenantKeyAlias}`);
    return null;
  }

  return createClient(url, serviceKey);
}

/**
 * Ensure auth_users_roles has entry for test user in TENANT DB
 * CRITICAL: This is required for the auth middleware to work!
 */
async function ensureTenantRole(
  client: SupabaseClient,
  userId: string,
  role: string
): Promise<any> {
  const yachtId = process.env.TEST_USER_YACHT_ID || '85fe1119-b04c-41ac-80f1-829d23322598';

  // Check if exists
  const { data: existing } = await client
    .from('auth_users_roles')
    .select('*')
    .eq('user_id', userId)
    .eq('yacht_id', yachtId)
    .eq('is_active', true)
    .single();

  if (existing) {
    console.log(`[Setup] TENANT auth_users_roles row exists for ${userId.slice(0, 8)}... role=${existing.role}`);
    return existing;
  }

  // Insert new row
  const { data, error } = await client
    .from('auth_users_roles')
    .upsert({
      user_id: userId,
      yacht_id: yachtId,
      role: role,
      is_active: true,
      valid_from: new Date().toISOString(),
    }, { onConflict: 'user_id,yacht_id' })
    .select()
    .single();

  if (error) {
    console.log(`[Setup] TENANT auth_users_roles upsert failed: ${error.message}`);
    return null;
  }

  console.log(`[Setup] Created TENANT auth_users_roles row for ${userId.slice(0, 8)}... role=${role}`);
  return data;
}

/**
 * Main setup function - call before running tests
 */
export async function setupMasterDb(): Promise<SetupResult> {
  try {
    console.log('[Setup] Starting MASTER DB setup...');

    // Get admin client
    const adminClient = getMasterAdminClient();

    // Try to ensure fleet_registry exists - if it fails, continue (it might already exist)
    let fleetRegistry = null;
    try {
      fleetRegistry = await ensureFleetRegistry(adminClient);
    } catch (error: any) {
      console.log(`[Setup] fleet_registry setup skipped: ${error.message}`);
      // Check if it exists anyway
      const yachtId = process.env.TEST_USER_YACHT_ID || '85fe1119-b04c-41ac-80f1-829d23322598';
      const { data } = await adminClient
        .from('fleet_registry')
        .select('yacht_id, yacht_name, active')
        .eq('yacht_id', yachtId)
        .single();
      if (data) {
        console.log(`[Setup] fleet_registry row found for ${yachtId.slice(0, 8)}...`);
        fleetRegistry = data;
      }
    }

    // Login to get user ID (since we can't easily query auth.users)
    const userId = await loginAndGetUserId();
    console.log(`[Setup] Test user ID: ${userId.slice(0, 8)}...`);

    // Ensure user_accounts exists - this is the critical one
    let userAccount = null;
    try {
      userAccount = await ensureUserAccount(adminClient, userId);
    } catch (error: any) {
      console.error(`[Setup] user_accounts setup failed: ${error.message}`);
      // This is fatal - we need user_accounts for auth to work
      return {
        success: false,
        message: `user_accounts setup failed: ${error.message}`,
      };
    }

    // CRITICAL: Also ensure TENANT auth_users_roles exists
    // Without this, the auth middleware will return 403
    const tenantClient = getTenantAdminClient();
    if (tenantClient) {
      const role = process.env.TEST_USER_ROLE || 'chief_engineer';
      try {
        await ensureTenantRole(tenantClient, userId, role);
      } catch (error: any) {
        console.log(`[Setup] TENANT role setup failed: ${error.message}`);
        // Non-fatal - tests may still work if role already exists
      }
    } else {
      console.log('[Setup] Skipping TENANT role setup - no tenant client');
    }

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
