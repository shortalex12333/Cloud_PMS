'use client';

/**
 * AuthDebug - Diagnostic panel for authentication issues
 *
 * Shows real-time auth state to help diagnose "No session exists" issues.
 * Remove this component after debugging is complete.
 */

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabaseClient';

interface DebugState {
  envCheck: {
    urlSet: boolean;
    keySet: boolean;
    urlValue: string;
  };
  storage: {
    available: boolean;
    supabaseKey: string | null;
    hasStoredSession: boolean;
  };
  session: {
    exists: boolean;
    userId: string | null;
    email: string | null;
    expiresAt: string | null;
    isExpired: boolean;
  };
  rpc: {
    called: boolean;
    result: any;
    error: string | null;
  };
  timestamp: string;
}

export function AuthDebug() {
  const [debug, setDebug] = useState<DebugState | null>(null);
  const [expanded, setExpanded] = useState(true);

  useEffect(() => {
    async function diagnose() {
      const state: DebugState = {
        envCheck: {
          urlSet: !!process.env.NEXT_PUBLIC_SUPABASE_URL,
          keySet: !!process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
          urlValue: process.env.NEXT_PUBLIC_SUPABASE_URL?.substring(0, 40) || 'NOT SET',
        },
        storage: {
          available: false,
          supabaseKey: null,
          hasStoredSession: false,
        },
        session: {
          exists: false,
          userId: null,
          email: null,
          expiresAt: null,
          isExpired: false,
        },
        rpc: {
          called: false,
          result: null,
          error: null,
        },
        timestamp: new Date().toISOString(),
      };

      // Check localStorage
      try {
        localStorage.setItem('__debug_test__', '1');
        localStorage.removeItem('__debug_test__');
        state.storage.available = true;

        // Find Supabase session key
        const keys = Object.keys(localStorage);
        const sbKey = keys.find(k => k.startsWith('sb-') && k.includes('auth-token'));
        state.storage.supabaseKey = sbKey || null;

        if (sbKey) {
          const stored = localStorage.getItem(sbKey);
          state.storage.hasStoredSession = !!stored && stored.includes('access_token');
        }
      } catch {
        state.storage.available = false;
      }

      // Check Supabase session
      try {
        const { data: { session }, error } = await supabase.auth.getSession();

        if (error) {
          state.rpc.error = `getSession error: ${error.message}`;
        } else if (session) {
          state.session.exists = true;
          state.session.userId = session.user.id;
          state.session.email = session.user.email || null;
          state.session.expiresAt = session.expires_at
            ? new Date(session.expires_at * 1000).toISOString()
            : null;
          state.session.isExpired = session.expires_at
            ? Date.now() > session.expires_at * 1000
            : false;

          // Test bootstrap endpoint instead of missing RPC
          state.rpc.called = true;
          try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
            const response = await fetch(`${apiUrl}/v1/bootstrap`, {
              headers: {
                'Authorization': `Bearer ${session.access_token}`,
                'Content-Type': 'application/json'
              }
            });

            if (!response.ok) {
              state.rpc.error = `Bootstrap failed: ${response.status} ${response.statusText}`;
            } else {
              const data = await response.json();
              state.rpc.result = data;
            }
          } catch (e: any) {
            state.rpc.error = `Bootstrap error: ${e.message}`;
          }
        }
      } catch (e: any) {
        state.rpc.error = e.message;
      }

      console.log('[AuthDebug] State:', state);
      setDebug(state);
    }

    diagnose();

    // Re-check every 5 seconds
    const interval = setInterval(diagnose, 5000);
    return () => clearInterval(interval);
  }, []);

  if (!debug) {
    return (
      <div className="fixed bottom-4 right-4 bg-[#1c1c1e] border border-[#3d3d3f] rounded-lg p-3 text-xs text-white font-mono">
        Diagnosing...
      </div>
    );
  }

  const ok = (v: boolean) => v ? '✓' : '✗';
  const okClass = (v: boolean) => v ? 'text-green-400' : 'text-red-400';

  return (
    <div className="fixed bottom-4 right-4 bg-[#1c1c1e] border border-[#3d3d3f] rounded-lg text-xs text-white font-mono max-w-[320px] shadow-xl z-50">
      <div
        className="flex items-center justify-between p-2 border-b border-[#3d3d3f] cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <span className="text-[#0a84ff] font-semibold">Auth Debug</span>
        <span className="text-[#636366]">{expanded ? '▼' : '▲'}</span>
      </div>

      {expanded && (
        <div className="p-3 space-y-3">
          {/* Environment */}
          <div>
            <div className="text-[#98989f] mb-1">Environment</div>
            <div className={okClass(debug.envCheck.urlSet)}>{ok(debug.envCheck.urlSet)} SUPABASE_URL</div>
            <div className={okClass(debug.envCheck.keySet)}>{ok(debug.envCheck.keySet)} ANON_KEY</div>
            <div className="text-[#636366] truncate">{debug.envCheck.urlValue}</div>
          </div>

          {/* Storage */}
          <div>
            <div className="text-[#98989f] mb-1">Browser Storage</div>
            <div className={okClass(debug.storage.available)}>{ok(debug.storage.available)} localStorage</div>
            <div className={okClass(!!debug.storage.supabaseKey)}>{ok(!!debug.storage.supabaseKey)} Supabase key</div>
            <div className={okClass(debug.storage.hasStoredSession)}>{ok(debug.storage.hasStoredSession)} Stored session</div>
          </div>

          {/* Session */}
          <div>
            <div className="text-[#98989f] mb-1">Session</div>
            <div className={okClass(debug.session.exists)}>{ok(debug.session.exists)} Active session</div>
            {debug.session.exists && (
              <>
                <div className="text-[#636366]">{debug.session.email}</div>
                <div className={okClass(!debug.session.isExpired)}>
                  {ok(!debug.session.isExpired)} {debug.session.isExpired ? 'EXPIRED' : 'Valid'}
                </div>
              </>
            )}
          </div>

          {/* RPC */}
          <div>
            <div className="text-[#98989f] mb-1">RPC get_my_bootstrap</div>
            {debug.rpc.error ? (
              <div className="text-red-400">{debug.rpc.error}</div>
            ) : debug.rpc.result ? (
              <div className="text-green-400 space-y-0.5">
                <div>{ok(true)} yacht: {debug.rpc.result?.yacht_id || 'null'}</div>
                <div>{ok(true)} role: {debug.rpc.result?.role || 'null'}</div>
                <div>{ok(true)} status: {debug.rpc.result?.status || 'null'}</div>
              </div>
            ) : (
              <div className="text-[#636366]">No session to test</div>
            )}
          </div>

          {/* Timestamp */}
          <div className="text-[#636366] text-[10px] pt-2 border-t border-[#3d3d3f]">
            Last check: {debug.timestamp.split('T')[1].split('.')[0]}
          </div>
        </div>
      )}
    </div>
  );
}

export default AuthDebug;
