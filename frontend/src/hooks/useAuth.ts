/**
 * CelesteOS Authentication Hook
 *
 * Provides authentication state and methods to React components.
 */

import { useState, useEffect, useCallback } from 'react';
import { Session } from '@supabase/supabase-js';
import { supabase } from '../lib/supabase';
import { api } from '../lib/api';
import { User, Yacht } from '../types';

interface AuthState {
  session: Session | null;
  user: User | null;
  yacht: Yacht | null;
  loading: boolean;
  error: string | null;
}

export function useAuth() {
  const [state, setState] = useState<AuthState>({
    session: null,
    user: null,
    yacht: null,
    loading: true,
    error: null,
  });

  /**
   * Initialize auth state
   */
  useEffect(() => {
    // Get initial session
    supabase.auth.getSession().then(async (session) => {
      if (session) {
        try {
          // Fetch user context from Cloud API
          const user = await api.users.getMe();

          setState({
            session,
            user,
            yacht: null, // Would be fetched separately
            loading: false,
            error: null,
          });
        } catch (error) {
          setState({
            session,
            user: null,
            yacht: null,
            loading: false,
            error: error instanceof Error ? error.message : 'Failed to load user',
          });
        }
      } else {
        setState({
          session: null,
          user: null,
          yacht: null,
          loading: false,
          error: null,
        });
      }
    });

    // Subscribe to auth changes
    const subscription = supabase.auth.onAuthStateChange(async (event, session) => {
      if (event === 'SIGNED_IN' && session) {
        try {
          const user = await api.users.getMe();

          setState({
            session,
            user,
            yacht: null,
            loading: false,
            error: null,
          });
        } catch (error) {
          setState({
            session,
            user: null,
            yacht: null,
            loading: false,
            error: error instanceof Error ? error.message : 'Failed to load user',
          });
        }
      } else if (event === 'SIGNED_OUT') {
        setState({
          session: null,
          user: null,
          yacht: null,
          loading: false,
          error: null,
        });
      }
    });

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  /**
   * Sign in
   */
  const signIn = useCallback(async (email: string, password: string) => {
    setState(prev => ({ ...prev, loading: true, error: null }));

    try {
      const { session } = await supabase.auth.signIn(email, password);
      const user = await api.users.getMe();

      setState({
        session,
        user,
        yacht: null,
        loading: false,
        error: null,
      });
    } catch (error) {
      setState(prev => ({
        ...prev,
        loading: false,
        error: error instanceof Error ? error.message : 'Sign in failed',
      }));
      throw error;
    }
  }, []);

  /**
   * Sign out
   */
  const signOut = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true, error: null }));

    try {
      await supabase.auth.signOut();

      setState({
        session: null,
        user: null,
        yacht: null,
        loading: false,
        error: null,
      });
    } catch (error) {
      setState(prev => ({
        ...prev,
        loading: false,
        error: error instanceof Error ? error.message : 'Sign out failed',
      }));
      throw error;
    }
  }, []);

  /**
   * Refresh session
   */
  const refresh = useCallback(async () => {
    try {
      const session = await supabase.auth.refreshSession();

      if (session) {
        const user = await api.users.getMe();

        setState(prev => ({
          ...prev,
          session,
          user,
        }));
      }
    } catch (error) {
      console.error('Failed to refresh session:', error);
    }
  }, []);

  return {
    ...state,
    signIn,
    signOut,
    refresh,
    isAuthenticated: !!state.session && !!state.user,
  };
}
