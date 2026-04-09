'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

/**
 * ResetPasswordClient
 *
 * Handles the Supabase password-reset redirect flow:
 * 1. Supabase sends user here via resetPasswordForEmail({ redirectTo: .../reset-password })
 * 2. Supabase appends #access_token=...&type=recovery to the URL hash
 * 3. We set the session from the hash tokens, then let the user enter a new password
 * 4. Call supabase.auth.updateUser({ password }) — redirect to /login on success
 */

export default function ResetPasswordClient() {
  const router = useRouter();
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [ready, setReady] = useState(false); // session set from hash
  const [done, setDone] = useState(false);

  // On mount: read hash tokens and set session so updateUser works
  useEffect(() => {
    async function initSession() {
      const { supabase } = await import('@/lib/supabaseClient');

      const hash = window.location.hash.substring(1);
      const params = new URLSearchParams(hash);
      const accessToken = params.get('access_token');
      const refreshToken = params.get('refresh_token');
      const type = params.get('type');

      if (type === 'recovery' && accessToken && refreshToken) {
        const { error: sessionError } = await supabase.auth.setSession({
          access_token: accessToken,
          refresh_token: refreshToken,
        });
        if (sessionError) {
          setError('Reset link is invalid or has expired. Request a new one.');
        } else {
          // Clear the hash so tokens aren't in browser history
          window.history.replaceState(null, '', window.location.pathname);
          setReady(true);
        }
      } else {
        // No recovery hash — check if already authenticated (e.g. page reload)
        const { data: { session } } = await supabase.auth.getSession();
        if (session) {
          setReady(true);
        } else {
          setError('Reset link is invalid or has expired. Request a new one from the login page.');
        }
      }
    }
    initSession();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirm) {
      setError('Passwords do not match.');
      return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const { supabase } = await import('@/lib/supabaseClient');
      const { error: updateError } = await supabase.auth.updateUser({ password });
      if (updateError) {
        setError(updateError.message);
      } else {
        setDone(true);
        setTimeout(() => router.replace('/login'), 2000);
      }
    } catch {
      setError('Network error. Try again.');
    } finally {
      setLoading(false);
    }
  };

  const cardStyle: React.CSSProperties = {
    minHeight: '100vh',
    background: 'var(--surface-base)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontFamily: "var(--font-sans, 'Inter', system-ui, sans-serif)",
    fontSize: '13px',
    color: 'var(--txt)',
  };

  const boxStyle: React.CSSProperties = {
    width: '384px',
    maxWidth: '100%',
    background: 'var(--surface-raised)',
    borderRadius: '10px',
    border: '1px solid var(--border-sub)',
    padding: '32px',
    margin: '16px',
  };

  const inputStyle: React.CSSProperties = {
    width: '100%',
    height: '40px',
    borderRadius: '6px',
    border: '1px solid var(--border-sub)',
    background: 'var(--surface-base)',
    color: 'var(--txt)',
    fontSize: '13px',
    padding: '0 12px',
    boxSizing: 'border-box',
    marginBottom: '12px',
    outline: 'none',
    fontFamily: 'inherit',
  };

  const btnStyle: React.CSSProperties = {
    width: '100%',
    height: '44px',
    borderRadius: '6px',
    border: 'none',
    background: 'var(--teal-bg)',
    color: 'var(--mark)',
    fontSize: '13px',
    fontWeight: 500,
    cursor: loading ? 'not-allowed' : 'pointer',
    opacity: loading ? 0.5 : 1,
    marginTop: '4px',
    fontFamily: 'inherit',
  };

  if (done) {
    return (
      <div style={cardStyle}>
        <div style={{ ...boxStyle, textAlign: 'center' }}>
          <p style={{ fontSize: '15px', fontWeight: 600, marginBottom: '8px' }}>Password updated</p>
          <p style={{ color: 'var(--txt2)', lineHeight: 1.5 }}>Redirecting to sign in...</p>
        </div>
      </div>
    );
  }

  if (!ready && !error) {
    return (
      <div style={cardStyle}>
        <div style={{ width: '32px', height: '32px', borderRadius: '50%', border: '3px solid var(--teal)', borderTopColor: 'transparent', animation: 'spin 0.8s linear infinite' }} />
      </div>
    );
  }

  if (error && !ready) {
    return (
      <div style={cardStyle}>
        <div style={{ ...boxStyle, textAlign: 'center' }}>
          <p style={{ fontSize: '15px', fontWeight: 600, marginBottom: '8px' }}>Link expired</p>
          <p style={{ color: 'var(--txt2)', lineHeight: 1.5, marginBottom: '20px' }}>{error}</p>
          <a href="/login" style={{ fontSize: '13px', color: 'var(--mark)', textDecoration: 'none' }}>Back to sign in</a>
        </div>
      </div>
    );
  }

  return (
    <div style={cardStyle}>
      <div style={boxStyle}>
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <div style={{ fontSize: '9px', fontWeight: 600, letterSpacing: '0.16em', textTransform: 'uppercase', color: 'var(--mark)', marginBottom: '4px' }}>
            Celeste
          </div>
          <h1 style={{ fontSize: '20px', fontWeight: 600, margin: 0 }}>Set new password</h1>
        </div>
        <form onSubmit={handleSubmit}>
          <label style={{ display: 'block', fontSize: '11px', fontWeight: 500, color: 'var(--txt2)', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            New password
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => { setPassword(e.target.value); setError(null); }}
            placeholder="Min. 8 characters"
            required
            minLength={8}
            autoComplete="new-password"
            style={inputStyle}
          />
          <label style={{ display: 'block', fontSize: '11px', fontWeight: 500, color: 'var(--txt2)', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Confirm password
          </label>
          <input
            type="password"
            value={confirm}
            onChange={(e) => { setConfirm(e.target.value); setError(null); }}
            placeholder="Repeat password"
            required
            autoComplete="new-password"
            style={inputStyle}
          />
          {error && (
            <p style={{ fontSize: '12px', color: 'var(--red, #C0503A)', marginBottom: '8px' }}>{error}</p>
          )}
          <button type="submit" disabled={loading} style={btnStyle}>
            {loading ? 'Updating...' : 'Update password'}
          </button>
        </form>
        <p style={{ marginTop: '20px', textAlign: 'center', fontSize: '12px', color: 'var(--txt-ghost)' }}>
          <a href="/login" style={{ color: 'var(--txt-ghost)', textDecoration: 'none' }}>Back to sign in</a>
        </p>
      </div>
    </div>
  );
}
