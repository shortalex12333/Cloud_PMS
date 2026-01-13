/**
 * Master Supabase Client for Test Verification
 *
 * Uses service role key to bypass RLS for verification queries
 * ONLY use for test assertions, not for simulating user actions
 */

import { createClient, SupabaseClient } from '@supabase/supabase-js';

let masterClient: SupabaseClient | null = null;

/**
 * Get Master Supabase client with service role
 */
export function getMasterClient(): SupabaseClient {
  if (masterClient) {
    return masterClient;
  }

  const url = process.env.MASTER_SUPABASE_URL;
  const key = process.env.MASTER_SUPABASE_SERVICE_ROLE_KEY;

  if (!url || !key) {
    throw new Error(
      'MASTER_SUPABASE_URL and MASTER_SUPABASE_SERVICE_ROLE_KEY must be set'
    );
  }

  masterClient = createClient(url, key, {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  });

  return masterClient;
}

/**
 * Verify user exists in user_accounts
 */
export async function verifyUserAccount(email: string): Promise<{
  exists: boolean;
  data: any;
}> {
  const client = getMasterClient();

  const { data, error } = await client
    .from('user_accounts')
    .select('*')
    .eq('email', email)
    .single();

  if (error && error.code !== 'PGRST116') {
    throw new Error(`Failed to query user_accounts: ${error.message}`);
  }

  return {
    exists: !!data,
    data,
  };
}

/**
 * Verify fleet_registry entry exists
 */
export async function verifyFleetRegistry(yachtId: string): Promise<{
  exists: boolean;
  data: any;
}> {
  const client = getMasterClient();

  const { data, error } = await client
    .from('fleet_registry')
    .select('*')
    .eq('yacht_id', yachtId)
    .single();

  if (error && error.code !== 'PGRST116') {
    throw new Error(`Failed to query fleet_registry: ${error.message}`);
  }

  return {
    exists: !!data,
    data,
  };
}

/**
 * Query security_events for audit trail
 */
export async function getSecurityEvents(
  userId: string,
  limit: number = 10
): Promise<any[]> {
  const client = getMasterClient();

  const { data, error } = await client
    .from('security_events')
    .select('*')
    .eq('user_id', userId)
    .order('created_at', { ascending: false })
    .limit(limit);

  if (error) {
    throw new Error(`Failed to query security_events: ${error.message}`);
  }

  return data || [];
}

/**
 * Verify RPC function exists
 */
export async function verifyRpcExists(functionName: string): Promise<boolean> {
  const client = getMasterClient();

  const { data, error } = await client.rpc(functionName, {});

  // If we get a specific "function not found" error, it doesn't exist
  // Other errors (like missing params) mean it exists
  if (error && error.message.includes('Could not find the function')) {
    return false;
  }

  return true;
}
