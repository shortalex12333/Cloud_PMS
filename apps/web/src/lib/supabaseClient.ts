import { createClient, SupabaseClient } from '@supabase/supabase-js';

// Environment variables - must be set in Vercel
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || '';
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '';

// Singleton pattern - only create client once, and only on client-side
let supabaseInstance: SupabaseClient | null = null;

function getSupabaseClient(): SupabaseClient {
  // CRITICAL: Only create client on client-side to ensure persistSession works correctly
  if (typeof window === 'undefined') {
    // During SSR, create a dummy client that won't be used for auth
    if (!supabaseInstance) {
      supabaseInstance = createClient('https://placeholder.supabase.co', 'placeholder-key', {
        auth: {
          persistSession: false,
          autoRefreshToken: false,
          detectSessionInUrl: false,
          flowType: 'pkce',
        },
      });
    }
    return supabaseInstance;
  }

  // CLIENT-SIDE ONLY from here

  // If we have an instance but it was created server-side (no persistence), reset it
  if (supabaseInstance && !(supabaseInstance as any).auth?.persistSession) {
    console.log('[Supabase] Resetting server-side instance for client-side use');
    supabaseInstance = null;
  }

  // Return existing instance if available
  if (supabaseInstance) {
    return supabaseInstance;
  }

  // Validate env vars
  if (!supabaseUrl) {
    console.error('[Supabase] ❌ NEXT_PUBLIC_SUPABASE_URL is not set!');
  }
  if (!supabaseAnonKey) {
    console.error('[Supabase] ❌ NEXT_PUBLIC_SUPABASE_ANON_KEY is not set!');
  }
  if (supabaseUrl && supabaseAnonKey) {
    console.log('[Supabase] ✅ Client initialized:', supabaseUrl.substring(0, 30) + '...');
  }

  if (!supabaseUrl || !supabaseAnonKey) {
    throw new Error('Supabase configuration missing. Please set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY');
  }

  // Create client with persistence ENABLED (client-side only)
  console.log('[Supabase] Creating client with persistSession: true');
  supabaseInstance = createClient(supabaseUrl, supabaseAnonKey, {
    auth: {
      persistSession: true,  // Always true on client-side
      autoRefreshToken: true,
      detectSessionInUrl: true,
      flowType: 'pkce',
      // Don't specify storage - let Supabase use its default (localStorage)
    },
  });

  console.log('[Supabase] Client created, persist setting:', (supabaseInstance as any).auth?.persistSession);
  return supabaseInstance;
}

// Export client - use Proxy to defer creation until first use (client-side only)
// This prevents SSR from creating a session-less client
const handler: ProxyHandler<any> = {
  get(_target, prop) {
    return Reflect.get(getSupabaseClient(), prop);
  },
};
export const supabase: SupabaseClient = new Proxy({}, handler) as SupabaseClient;

// Helper function to get current user (placeholder)
export async function getCurrentUser() {
  const {
    data: { user },
    error,
  } = await supabase.auth.getUser();

  if (error) {
    console.error('Error getting user:', error);
    return null;
  }

  return user;
}

// Helper function to sign out
export async function signOut() {
  const { error } = await supabase.auth.signOut();
  if (error) {
    console.error('Error signing out:', error);
  }
}

// Yacht signature validation (placeholder)
export function getYachtSignature(): string | null {
  // TODO: Implement yacht signature retrieval from session/cookie
  return null;
}
