// Authentication utilities and helpers

import { supabase } from './supabaseClient';

export interface AuthUser {
  id: string;
  email: string;
  name: string;
  yacht_id: string;
  role: string;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface SignupData {
  email: string;
  password: string;
  name: string;
  yacht_signature: string;
}

// Sign in with email and password
export async function signIn(credentials: LoginCredentials) {
  const { data, error } = await supabase.auth.signInWithPassword({
    email: credentials.email,
    password: credentials.password,
  });

  if (error) throw error;
  return data;
}

// Sign up new user
export async function signUp(userData: SignupData) {
  const { data, error } = await supabase.auth.signUp({
    email: userData.email,
    password: userData.password,
    options: {
      data: {
        name: userData.name,
        yacht_signature: userData.yacht_signature,
      },
    },
  });

  if (error) throw error;
  return data;
}

// Sign out current user
export async function signOut() {
  const { error } = await supabase.auth.signOut();
  if (error) throw error;
}

// Get current session
export async function getSession() {
  const { data, error } = await supabase.auth.getSession();
  if (error) throw error;
  return data.session;
}

// Get current user
export async function getCurrentUser(): Promise<AuthUser | null> {
  const { data: { user }, error } = await supabase.auth.getUser();

  if (error || !user) return null;

  // Fetch additional user data from auth_users table
  const { data: userData, error: userError } = await supabase
    .from('auth_users')
    .select('yacht_id, name, role')
    .eq('auth_user_id', user.id)
    .single();

  if (userError || !userData) return null;

  return {
    id: user.id,
    email: user.email!,
    name: userData.name,
    yacht_id: userData.yacht_id,
    role: userData.role,
  };
}

// Refresh session
export async function refreshSession() {
  const { data, error } = await supabase.auth.refreshSession();
  if (error) throw error;
  return data.session;
}

// Check if user is authenticated
export async function isAuthenticated(): Promise<boolean> {
  const session = await getSession();
  return !!session;
}

// Get yacht signature for current user
export async function getYachtSignature(): Promise<string | null> {
  const user = await getCurrentUser();
  if (!user) return null;

  const { data, error } = await supabase
    .from('yacht_signatures')
    .select('signature')
    .eq('yacht_id', user.yacht_id)
    .single();

  if (error || !data) return null;
  return data.signature;
}

// Check if user has specific role
export function hasRole(user: AuthUser | null, allowedRoles: string[]): boolean {
  if (!user) return false;
  return allowedRoles.includes(user.role);
}

// Check if user is HOD (Head of Department)
export function isHOD(user: AuthUser | null): boolean {
  return hasRole(user, ['chief_engineer', 'captain', 'manager']);
}

// Password reset
export async function resetPassword(email: string) {
  const { error } = await supabase.auth.resetPasswordForEmail(email, {
    redirectTo: `${window.location.origin}/reset-password`,
  });

  if (error) throw error;
}

// Update password
export async function updatePassword(newPassword: string) {
  const { error } = await supabase.auth.updateUser({
    password: newPassword,
  });

  if (error) throw error;
}

// OAuth sign in (for future use)
export async function signInWithOAuth(provider: 'google' | 'azure') {
  const { error } = await supabase.auth.signInWithOAuth({
    provider,
    options: {
      redirectTo: `${window.location.origin}/auth/callback`,
    },
  });

  if (error) throw error;
}
