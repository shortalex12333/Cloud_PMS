'use client';

import React, { createContext, useEffect, useState, useCallback } from 'react';
import { supabase } from '@/lib/supabaseClient';
import type { User } from '@supabase/supabase-js';

// CelesteOS user type - GDPR-minimized
// Role mapping: chief_engineer, captain, manager = HOD (Head of Department)
export type CelesteUser = {
  id: string; // user_id
  email: string | null;
  role: 'chief_engineer' | 'eto' | 'captain' | 'manager' | 'vendor' | 'crew' | 'deck' | 'interior';
  yachtId: string | null;
  displayName: string | null;
};

export type AuthContextValue = {
  user: CelesteUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

// Helper function to check if user is HOD (Head of Department)
// HOD roles: chief_engineer, eto, captain, manager
export function isHOD(user: CelesteUser | null): boolean {
  if (!user) return false;
  return ['chief_engineer', 'eto', 'captain', 'manager'].includes(user.role);
}

export const AuthContext = createContext<AuthContextValue | undefined>(
  undefined
);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<CelesteUser | null>(null);
  const [loading, setLoading] = useState(true);
  const fetchingRef = React.useRef(false);

  // Possible table names for user profiles (try in order)
  const PROFILE_TABLES = ['user_profiles', 'auth_users', 'users'] as const;

  // Timeout wrapper for Supabase queries
  const withTimeout = <T,>(promise: Promise<T>, ms: number, tableName: string): Promise<T> => {
    const timeoutPromise = new Promise<never>((_, reject) =>
      setTimeout(() => reject(new Error(`Query to ${tableName} timed out after ${ms}ms`)), ms)
    );
    return Promise.race([promise, timeoutPromise]);
  };

  // Fetch user profile - tries multiple table names for compatibility
  const fetchUserProfile = useCallback(async (authUser: User) => {
    // Prevent concurrent fetches
    if (fetchingRef.current) {
      console.log('[AuthContext] ⏸️ Already fetching, skipping...');
      return null;
    }

    fetchingRef.current = true;
    console.log('[AuthContext] ▶ fetchUserProfile START for:', authUser.email);

    // Fallback profile using auth.users metadata
    const authMetadata = authUser.user_metadata || {};
    const fallbackProfile: CelesteUser = {
      id: authUser.id,
      email: authUser.email || null,
      role: (authMetadata.role as CelesteUser['role']) || 'crew',
      yachtId: authMetadata.yacht_id || null,
      displayName: authMetadata.name || authUser.email || null,
    };

    try {
      console.log('[AuthContext] Fetching user profile, trying tables:', PROFILE_TABLES);

      // Try each possible table name
      for (const tableName of PROFILE_TABLES) {
        console.log(`[AuthContext] Trying table: ${tableName}`);

        try {
          // 1.5 second timeout per table query (fast fail)
          const queryPromise = Promise.resolve(
            supabase
              .from(tableName)
              .select('*')
              .eq('email', authUser.email)
              .maybeSingle()
          );

          const { data: userData, error: userError } = await withTimeout(queryPromise, 1500, tableName);

          if (userError) {
            // 404 = table doesn't exist or no API access
            // PGRST116 = relation doesn't exist
            const is404 = userError.message?.includes('404') ||
                          (userError as any).code === 'PGRST116' ||
                          userError.message?.includes('relation') ||
                          (userError as any).code === '42P01';

            if (is404) {
              console.log(`[AuthContext] Table ${tableName} not accessible (404/not found), trying next...`);
              continue;
            }

            console.error(`[AuthContext] Error querying ${tableName}:`, userError.message);
            continue;
          }

          if (userData) {
            console.log(`[AuthContext] ✅ Found user in ${tableName}:`, userData);

            // Handle different column structures
            const role = userData.role ||
                        (userData.metadata as any)?.role ||
                        authMetadata.role ||
                        'crew';

            const celesteUser: CelesteUser = {
              id: userData.auth_user_id || userData.id || authUser.id,
              email: userData.email || authUser.email,
              role: role as CelesteUser['role'],
              yachtId: userData.yacht_id || null,
              displayName: userData.name || userData.display_name || authUser.email,
            };

            console.log('[AuthContext] ✅ User profile loaded from', tableName);
            return celesteUser;
          }
        } catch (tableErr: any) {
          const isTimeout = tableErr?.message?.includes('timed out');
          console.log(`[AuthContext] ${isTimeout ? '⏱️ Timeout' : 'Exception'} querying ${tableName}:`, tableErr?.message || tableErr);
          continue;
        }
      }

      // No table worked - use fallback from auth.users metadata
      console.warn('[AuthContext] ⚠️ No profile table accessible, using auth.users metadata');
      console.log('[AuthContext] 💡 TIP: Run database/diagnostics/check_tables_and_permissions.sql in Supabase SQL Editor');
      return fallbackProfile;

    } catch (err) {
      console.error('[AuthContext] ❌ Exception in fetchUserProfile:', err);
      console.warn('[AuthContext] ⚠️ Using fallback profile due to exception');
      return fallbackProfile;
    } finally {
      fetchingRef.current = false;
      console.log('[AuthContext] ◀ fetchUserProfile END');
    }
  }, []);

  // Initialize auth state
  useEffect(() => {
    console.log('[AuthContext] Initializing auth state...');

    // 5 second timeout - profile lookup is now faster with 1.5s per table
    const sessionTimeout = 5000;
    let didTimeout = false;

    const timeoutId = setTimeout(() => {
      didTimeout = true;
      console.warn('[AuthContext] ⚠️ getSession timeout after 5s - proceeding with fallback');
      setLoading(false); // Allow UI to render regardless
    }, sessionTimeout);

    // Check current session with error handling
    supabase.auth.getSession()
      .then(({ data: { session }, error }) => {
        if (didTimeout) {
          console.log('[AuthContext] Session response received after timeout, ignoring');
          return;
        }
        clearTimeout(timeoutId);

        if (error) {
          console.error('[AuthContext] getSession error:', error);
          setLoading(false);
          return;
        }

        console.log('[AuthContext] Current session:', session ? 'exists' : 'none');
        if (session?.user) {
          fetchUserProfile(session.user)
            .then((profile) => {
              setUser(profile);
            })
            .catch((err) => {
              console.error('[AuthContext] Failed to fetch profile on init:', err);
              setUser(null);
            })
            .finally(() => {
              setLoading(false);
            });
        } else {
          setLoading(false);
        }
      })
      .catch((err) => {
        if (didTimeout) return;
        clearTimeout(timeoutId);
        console.error('[AuthContext] ❌ getSession exception:', err);
        setLoading(false); // Always allow UI to render
      });

    // Subscribe to auth state changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(async (event, session) => {
      console.log('[AuthContext] Auth state changed:', event);

      if (event === 'SIGNED_IN' && session?.user) {
        const profile = await fetchUserProfile(session.user);
        setUser(profile);
        setLoading(false); // ← FIX: End loading state
      } else if (event === 'SIGNED_OUT') {
        setUser(null);
        setLoading(false); // ← FIX: End loading state
      } else if (event === 'TOKEN_REFRESHED' && session?.user) {
        // Optionally refresh user profile on token refresh
        const profile = await fetchUserProfile(session.user);
        setUser(profile);
        // Don't change loading state on token refresh
      }
    });

    return () => {
      clearTimeout(timeoutId);
      subscription.unsubscribe();
    };
  }, [fetchUserProfile]);

  // Login function
  const login = useCallback(
    async (email: string, password: string) => {
      console.log('[AuthContext] Login attempt for:', email);

      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (error) {
        console.error('[AuthContext] Login error:', error.message);
        throw new Error(error.message);
      }

      if (!data.user) {
        throw new Error('No user returned from login');
      }

      // Fetch user profile
      const profile = await fetchUserProfile(data.user);
      if (!profile) {
        throw new Error('User profile not found. Please contact support.');
      }

      setUser(profile);
      console.log('[AuthContext] Login successful:', profile.id);
    },
    [fetchUserProfile]
  );

  // Logout function
  const logout = useCallback(async () => {
    console.log('[AuthContext] Logout initiated');

    const { error } = await supabase.auth.signOut();
    if (error) {
      console.error('[AuthContext] Logout error:', error);
      throw error;
    }

    setUser(null);
    console.log('[AuthContext] Logout successful');
  }, []);

  const value: AuthContextValue = {
    user,
    loading,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
