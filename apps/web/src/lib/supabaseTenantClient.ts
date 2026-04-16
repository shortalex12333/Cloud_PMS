'use client';

/**
 * supabaseTenantClient — Supabase client scoped to the TENANT project.
 *
 * The main supabaseClient.ts uses NEXT_PUBLIC_SUPABASE_URL which in production
 * Vercel points to the MASTER project (auth only). Storage buckets and
 * operational tables (pms_attachments, etc.) live on the TENANT project.
 *
 * This client uses NEXT_PUBLIC_TENANT_SUPABASE_URL so uploads reach the
 * correct bucket. In local dev the env var falls back to NEXT_PUBLIC_SUPABASE_URL
 * which already points at TENANT.
 *
 * Required Vercel env vars (production):
 *   NEXT_PUBLIC_TENANT_SUPABASE_URL      — https://vzsohavtuotocgrfkfyd.supabase.co
 *   NEXT_PUBLIC_TENANT_SUPABASE_ANON_KEY — tenant anon key
 */

import { createClient, SupabaseClient } from '@supabase/supabase-js';

const tenantUrl =
  process.env.NEXT_PUBLIC_TENANT_SUPABASE_URL ||
  process.env.NEXT_PUBLIC_SUPABASE_URL ||
  '';

const tenantAnonKey =
  process.env.NEXT_PUBLIC_TENANT_SUPABASE_ANON_KEY ||
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ||
  '';

let tenantInstance: SupabaseClient | null = null;

function getTenantClient(): SupabaseClient {
  if (typeof window === 'undefined') {
    // SSR placeholder — never used for real operations
    return createClient('https://placeholder.supabase.co', 'placeholder-key', {
      auth: { persistSession: false, autoRefreshToken: false },
    });
  }

  if (tenantInstance) return tenantInstance;

  if (!tenantUrl || !tenantAnonKey) {
    console.error('[supabaseTenantClient] Missing env vars — set NEXT_PUBLIC_TENANT_SUPABASE_URL and NEXT_PUBLIC_TENANT_SUPABASE_ANON_KEY in Vercel');
    throw new Error('Tenant Supabase configuration missing');
  }

  tenantInstance = createClient(tenantUrl, tenantAnonKey, {
    auth: { persistSession: false, autoRefreshToken: false },
  });

  return tenantInstance;
}

const handler: ProxyHandler<object> = {
  get(_target, prop) {
    return Reflect.get(getTenantClient(), prop);
  },
};

export const supabaseTenant: SupabaseClient = new Proxy({}, handler) as SupabaseClient;
