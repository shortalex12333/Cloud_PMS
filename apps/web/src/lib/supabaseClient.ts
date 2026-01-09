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

// Export a getter that ensures client-side only usage for auth
export const supabase = getSupabaseClient();

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
