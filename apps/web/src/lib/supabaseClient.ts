import { createClient, SupabaseClient } from '@supabase/supabase-js';

// Environment variables - must be set in Vercel
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || '';
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '';

// Singleton pattern - only create client once, and only on client-side
let supabaseInstance: SupabaseClient | null = null;

function getSupabaseClient(): SupabaseClient {
  // Return existing instance if available
  if (supabaseInstance) {
    return supabaseInstance;
  }

  // Validate env vars (client-side only for logging)
  if (typeof window !== 'undefined') {
    if (!supabaseUrl) {
      console.error('[Supabase] ❌ NEXT_PUBLIC_SUPABASE_URL is not set!');
    }
    if (!supabaseAnonKey) {
      console.error('[Supabase] ❌ NEXT_PUBLIC_SUPABASE_ANON_KEY is not set!');
    }
    if (supabaseUrl && supabaseAnonKey) {
      console.log('[Supabase] ✅ Client initialized:', supabaseUrl.substring(0, 30) + '...');
    }
  }

  // During build or if env vars missing, throw a descriptive error only in browser
  if (!supabaseUrl || !supabaseAnonKey) {
    if (typeof window !== 'undefined') {
      throw new Error('Supabase configuration missing. Please set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY');
    }
    // During build (server-side), create a dummy client to prevent build errors
    // This won't actually be used since pages are client-side rendered
    supabaseInstance = createClient('https://placeholder.supabase.co', 'placeholder-key', {
      auth: {
        persistSession: false,
        autoRefreshToken: false,
        detectSessionInUrl: false,
        flowType: 'pkce',
      },
    });
    return supabaseInstance;
  }

  // Create client with appropriate settings
  supabaseInstance = createClient(supabaseUrl, supabaseAnonKey, {
    auth: {
      persistSession: typeof window !== 'undefined', // Only persist on client
      autoRefreshToken: true,
      detectSessionInUrl: true,
      flowType: 'pkce',
      // Don't specify storage - let Supabase use its default (localStorage on client)
    },
  });

  return supabaseInstance;
}

// CRITICAL FIX: Export Proxy to defer client creation until first access
// This prevents SSR from creating a client with persistSession: false
// which would break session persistence and cause auth to hang.
// See: https://github.com/supabase/supabase-js/issues/1043
const handler: ProxyHandler<any> = {
  get(_target, prop) {
    const client = getSupabaseClient();
    return Reflect.get(client, prop);
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
