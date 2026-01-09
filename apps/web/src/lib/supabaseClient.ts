import { createClient } from '@supabase/supabase-js';

// Environment variables - must be set in Vercel
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || '';
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '';

// Validate env vars on load (client-side only)
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

// Create Supabase client
export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true,
    flowType: 'pkce',
    storage: typeof window !== 'undefined' ? window.localStorage : undefined,
    storageKey: `sb-${supabaseUrl.split('//')[1]?.split('.')[0] || 'celeste'}-auth-token`,
  },
});

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
