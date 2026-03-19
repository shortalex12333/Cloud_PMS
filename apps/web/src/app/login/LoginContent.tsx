'use client';

/**
 * LoginContent - Secure Login Page
 *
 * Architecture (2026-01-13):
 * - All login happens on app.celeste7.ai (no cross-domain)
 * - Uses non-blocking AuthContext
 * - Handles bootstrap status: active, pending, error
 *
 * Visual: Matches /public/prototypes/auth.html approved design.
 * Uses prototype-tokens.css variables (served via /src/styles/tokens.css).
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { isHOD, isFullyActivated } from '@/contexts/AuthContext';
import { Loader2 } from 'lucide-react';

/* ── Shared inline-style objects ── */

const PAGE_BG: React.CSSProperties = {
  minHeight: '100vh',
  background: 'var(--surface-base)',
  display: 'flex',
  flexDirection: 'column',
  fontFamily: "var(--font-sans, 'Inter', system-ui, -apple-system, sans-serif)",
  fontSize: '13px',
  lineHeight: 1.5,
  color: 'var(--txt)',
  WebkitFontSmoothing: 'antialiased',
  position: 'relative',
};

const CENTER_STATE: React.CSSProperties = {
  minHeight: '100vh',
  background: 'var(--surface-base)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
};

const TOPBAR: React.CSSProperties = {
  height: '40px',
  flexShrink: 0,
  display: 'flex',
  alignItems: 'center',
  padding: '0 20px',
  gap: '8px',
  borderBottom: '1px solid var(--border-faint)',
  background: 'var(--glass-bg)',
  backdropFilter: 'blur(12px)',
  WebkitBackdropFilter: 'blur(12px)',
};

const STAGE: React.CSSProperties = {
  flex: 1,
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  position: 'relative',
  padding: '24px',
};

const CARD: React.CSSProperties = {
  width: '100%',
  maxWidth: '384px',
  background: 'var(--surface)',
  borderTop: '1px solid var(--border-top)',
  borderRight: '1px solid var(--border-sub)',
  borderBottom: '1px solid var(--border-faint)',
  borderLeft: '1px solid var(--border-sub)',
  borderRadius: '8px',
  boxShadow: '0 20px 80px rgba(0,0,0,0.60), 0 4px 20px rgba(0,0,0,0.40), inset 0 1px 0 rgba(255,255,255,0.05)',
  overflow: 'hidden',
  position: 'relative',
  zIndex: 1,
};

const INPUT_BASE: React.CSSProperties = {
  width: '100%',
  height: '44px',
  padding: '0 14px',
  background: 'var(--surface-base)',
  border: '1px solid var(--border-sub)',
  borderRadius: '6px',
  fontFamily: 'var(--font-sans)',
  fontSize: '13px',
  color: 'var(--txt)',
  outline: 'none',
  transition: 'border-color 120ms',
};

const SUBMIT_BTN: React.CSSProperties = {
  width: '100%',
  height: '44px',
  borderRadius: '6px',
  border: 'none',
  cursor: 'pointer',
  fontFamily: 'var(--font-sans)',
  fontSize: '13px',
  fontWeight: 500,
  background: 'var(--teal-bg)',
  color: 'var(--mark)',
  transition: 'background 80ms',
  marginTop: '4px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: '8px',
};

const LABEL: React.CSSProperties = {
  display: 'block',
  fontSize: '11px',
  fontWeight: 500,
  letterSpacing: '0.03em',
  textTransform: 'uppercase',
  color: 'var(--txt3)',
  marginBottom: '6px',
};

const FORGOT_LINK: React.CSSProperties = {
  fontSize: '10px',
  color: 'var(--mark, #5AABCC)',
  cursor: 'pointer',
  textDecoration: 'none',
  transition: 'opacity 80ms',
};

const FIELD_ERROR_TEXT: React.CSSProperties = {
  fontSize: '11px',
  color: 'var(--red, #C0503A)',
  marginTop: '4px',
};

/* Injected <style> for placeholder color + mobile responsive */
const INJECTED_CSS = `
  .login-field-input::placeholder {
    color: rgba(255,255,255,0.40) !important;
  }
  [data-theme="light"] .login-field-input::placeholder {
    color: rgba(0,0,0,0.35) !important;
  }
  @media (max-width: 480px) {
    .login-auth-card {
      max-width: 100% !important;
      border-radius: 0 !important;
    }
    .login-auth-form {
      padding: 24px 20px 20px !important;
    }
    .login-auth-header {
      padding: 32px 20px 0 !important;
    }
  }
`;

/* ── Theme toggle SVGs ── */

function MoonIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z" />
    </svg>
  );
}

function SunIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <circle cx="12" cy="12" r="5" />
      <line x1="12" y1="1" x2="12" y2="3" />
      <line x1="12" y1="21" x2="12" y2="23" />
      <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
      <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
      <line x1="1" y1="12" x2="3" y2="12" />
      <line x1="21" y1="12" x2="23" y2="12" />
      <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
      <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
    </svg>
  );
}

export default function LoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, login, loading: authLoading, bootstrapping, error: authError } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [justLoggedOut, setJustLoggedOut] = useState(false);
  const [isDark, setIsDark] = useState(true);
  const [btnHover, setBtnHover] = useState(false);
  const [btnActive, setBtnActive] = useState(false);
  const styleInjected = useRef(false);

  // Inject CSS for placeholder + mobile responsive
  useEffect(() => {
    if (styleInjected.current) return;
    styleInjected.current = true;
    const style = document.createElement('style');
    style.textContent = INJECTED_CSS;
    document.head.appendChild(style);
    return () => { style.remove(); };
  }, []);

  // Theme toggle
  const toggleTheme = useCallback(() => {
    const next = isDark ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    document.documentElement.classList.toggle('dark', next === 'dark');
    setIsDark(!isDark);
  }, [isDark]);

  // Sync initial theme from DOM
  useEffect(() => {
    const current = document.documentElement.getAttribute('data-theme');
    setIsDark(current !== 'light');
  }, []);

  // Detect logout param and clear it from URL
  useEffect(() => {
    if (searchParams.get('logout') === '1') {
      setJustLoggedOut(true);
      window.history.replaceState({}, '', '/login');
      const timer = setTimeout(() => setJustLoggedOut(false), 2000);
      return () => clearTimeout(timer);
    }
  }, [searchParams]);

  // Redirect when user is authenticated and fully activated
  useEffect(() => {
    if (justLoggedOut) {
      console.log('[LoginPage] Just logged out, skipping auto-redirect');
      return;
    }

    if (!authLoading && user) {
      console.log('[LoginPage] User state:', user.bootstrapStatus);

      if (bootstrapping) {
        console.log('[LoginPage] Waiting for bootstrap...');
        return;
      }

      if (isFullyActivated(user)) {
        console.log('[LoginPage] User fully activated, redirecting to /');
        router.replace('/');
        return;
      }

      if (user.bootstrapStatus === 'pending') {
        console.log('[LoginPage] User pending activation');
        return;
      }

      if (user.bootstrapStatus === 'inactive') {
        console.log('[LoginPage] Yacht inactive');
        return;
      }

      if (user.bootstrapStatus === 'error') {
        console.log('[LoginPage] Bootstrap error, will retry');
        return;
      }
    }
  }, [user, authLoading, bootstrapping, router, justLoggedOut]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      console.log('[LoginPage] Attempting login:', email);
      await login(email, password);
    } catch (err) {
      console.error('[LoginPage] Login failed:', err);
      setError(err instanceof Error ? err.message : 'Login failed');
      setLoading(false);
    }
  };

  /* ── Loading / spinner states ── */

  const renderSpinnerState = (label: string, sublabel?: string) => (
    <div style={CENTER_STATE}>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px' }}>
        <Loader2 className="w-8 h-8 animate-spin" style={{ color: 'var(--mark)' }} />
        <p style={{ fontSize: '13px', color: 'var(--txt2)' }}>{label}</p>
        {sublabel && <p style={{ fontSize: '11px', color: 'var(--txt3)' }}>{sublabel}</p>}
      </div>
    </div>
  );

  // Auth initializing
  if (authLoading && !justLoggedOut) {
    return renderSpinnerState('Loading...');
  }

  // Bootstrapping
  if (user && bootstrapping && !justLoggedOut) {
    return renderSpinnerState('Loading your account...');
  }

  // Redirecting
  if (user && isFullyActivated(user) && !justLoggedOut) {
    return renderSpinnerState('Redirecting...');
  }

  // Pending activation
  if (user && user.bootstrapStatus === 'pending') {
    return (
      <div style={{ ...CENTER_STATE, padding: '24px' }}>
        <div style={{ width: '384px', maxWidth: '100%', textAlign: 'center' }}>
          <div style={{
            width: '64px', height: '64px', borderRadius: '50%',
            background: 'var(--surface-base)', border: '1px solid var(--border-sub)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 24px',
          }}>
            <span style={{ fontSize: '22px' }}>&#x23F3;</span>
          </div>
          <h1 style={{ fontSize: '20px', fontWeight: 600, color: 'var(--txt)', marginBottom: '8px' }}>Awaiting Activation</h1>
          <p style={{ fontSize: '13px', color: 'var(--txt2)', marginBottom: '24px' }}>
            Your account is pending activation. Please contact your administrator to complete setup.
          </p>
          <p style={{ fontSize: '11px', color: 'var(--txt3)' }}>
            Signed in as {user.email}
          </p>
        </div>
      </div>
    );
  }

  // Yacht inactive
  if (user && user.bootstrapStatus === 'inactive') {
    return (
      <div style={{ ...CENTER_STATE, padding: '24px' }}>
        <div style={{ width: '384px', maxWidth: '100%', textAlign: 'center' }}>
          <div style={{
            width: '64px', height: '64px', borderRadius: '50%',
            background: 'var(--surface-base)', border: '1px solid var(--border-sub)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 24px',
          }}>
            <span style={{ fontSize: '22px' }}>&#x1F6A2;</span>
          </div>
          <h1 style={{ fontSize: '20px', fontWeight: 600, color: 'var(--txt)', marginBottom: '8px' }}>Yacht Inactive</h1>
          <p style={{ fontSize: '13px', color: 'var(--txt2)', marginBottom: '24px' }}>
            The yacht associated with your account is currently inactive.
            {user.yachtName && <span style={{ display: 'block', marginTop: '4px' }}>{user.yachtName}</span>}
          </p>
          <p style={{ fontSize: '11px', color: 'var(--txt3)' }}>
            Contact support for assistance.
          </p>
        </div>
      </div>
    );
  }

  // Bootstrap error
  if (user && user.bootstrapStatus === 'error') {
    return renderSpinnerState('Connecting to server...', 'Retrying...');
  }

  // Display error from auth context or local error
  const displayError = error || authError;

  return (
    <div style={PAGE_BG}>
      {/* ── Backdrop orbs ── */}
      <div style={{ position: 'fixed', inset: 0, zIndex: 0, pointerEvents: 'none', overflow: 'hidden', background: 'var(--surface-base)' }}>
        <div style={{
          position: 'absolute', borderRadius: '50%', filter: 'blur(90px)', opacity: 0.5,
          width: '60vw', height: '60vw', top: '-20vw', left: '-8vw',
          background: 'radial-gradient(circle, rgba(58,124,157,0.50) 0%, transparent 70%)',
        }} />
        <div style={{
          position: 'absolute', borderRadius: '50%', filter: 'blur(90px)', opacity: 0.5,
          width: '45vw', height: '45vw', bottom: '-12vw', right: '-5vw',
          background: 'radial-gradient(circle, rgba(30,90,130,0.38) 0%, transparent 70%)',
        }} />
      </div>

      {/* ── App shell ── */}
      <div style={{ position: 'relative', zIndex: 1, display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
        {/* ── Topbar ── */}
        <header style={TOPBAR}>
          <span style={{
            fontSize: '10px', fontWeight: 600, letterSpacing: '0.16em',
            textTransform: 'uppercase', color: 'var(--mark)',
          }}>
            Celeste
          </span>
          <div style={{ flex: 1 }} />
          <button
            type="button"
            onClick={toggleTheme}
            style={{
              width: '28px', height: '28px', borderRadius: '4px',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: 'pointer', background: 'none', border: 'none',
              color: 'var(--txt-ghost)', transition: 'background 80ms',
            }}
            aria-label="Toggle theme"
          >
            {isDark ? <MoonIcon /> : <SunIcon />}
          </button>
        </header>

        {/* ── Stage ── */}
        <div style={STAGE}>
          {/* Auth card */}
          <div className="login-auth-card" style={CARD}>
            {/* Card header */}
            <div className="login-auth-header" style={{ padding: '32px 32px 0', textAlign: 'center' }}>
              <div style={{
                fontSize: '9px', fontWeight: 600, letterSpacing: '0.16em',
                textTransform: 'uppercase', color: 'var(--mark)', marginBottom: '4px',
              }}>
                Celeste
              </div>
              <h1 style={{ fontSize: '20px', fontWeight: 600, color: 'var(--txt)', marginBottom: '4px' }}>
                Sign in
              </h1>
              <p style={{ fontSize: '13px', color: 'var(--txt-ghost)' }}>
                Maritime management platform
              </p>
            </div>

            {/* Form */}
            <form onSubmit={handleLogin} className="login-auth-form" style={{ padding: '24px 32px 32px' }}>
              {/* Email field */}
              <div style={{ marginBottom: '16px' }}>
                <label style={LABEL}>Email</label>
                <input
                  type="email"
                  className="login-field-input"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@vessel.com"
                  required
                  autoComplete="email"
                  disabled={loading}
                  style={{
                    ...INPUT_BASE,
                    opacity: loading ? 0.5 : 1,
                    ...(displayError ? { borderColor: 'var(--red, #C0503A)' } : {}),
                  }}
                  onFocus={(e) => { e.currentTarget.style.borderColor = 'var(--teal)'; }}
                  onBlur={(e) => {
                    e.currentTarget.style.borderColor = displayError
                      ? 'var(--red, #C0503A)'
                      : 'var(--border-sub)';
                  }}
                />
                {displayError && (
                  <p style={FIELD_ERROR_TEXT}>{displayError}</p>
                )}
              </div>

              {/* Password field */}
              <div style={{ marginBottom: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <label style={{ ...LABEL, marginBottom: 0 }}>Password</label>
                  <a
                    href="#"
                    style={FORGOT_LINK}
                    onMouseEnter={(e) => { e.currentTarget.style.opacity = '0.7'; }}
                    onMouseLeave={(e) => { e.currentTarget.style.opacity = '1'; }}
                    onClick={(e) => { e.preventDefault(); }}
                  >
                    Forgot?
                  </a>
                </div>
                <input
                  type="password"
                  className="login-field-input"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter password"
                  required
                  autoComplete="current-password"
                  disabled={loading}
                  style={{
                    ...INPUT_BASE,
                    opacity: loading ? 0.5 : 1,
                    ...(displayError ? { borderColor: 'var(--red, #C0503A)' } : {}),
                  }}
                  onFocus={(e) => { e.currentTarget.style.borderColor = 'var(--teal)'; }}
                  onBlur={(e) => {
                    e.currentTarget.style.borderColor = displayError
                      ? 'var(--red, #C0503A)'
                      : 'var(--border-sub)';
                  }}
                />
              </div>

              {/* Submit */}
              <button
                type="submit"
                disabled={loading}
                style={{
                  ...SUBMIT_BTN,
                  cursor: loading ? 'not-allowed' : 'pointer',
                  opacity: loading ? 0.5 : 1,
                  ...(btnActive && !loading
                    ? { background: 'rgba(58,124,157,0.24)' }
                    : btnHover && !loading
                      ? { background: 'rgba(58,124,157,0.18)' }
                      : {}),
                }}
                onMouseEnter={() => setBtnHover(true)}
                onMouseLeave={() => { setBtnHover(false); setBtnActive(false); }}
                onMouseDown={() => setBtnActive(true)}
                onMouseUp={() => setBtnActive(false)}
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Signing in...</span>
                  </>
                ) : (
                  'Sign in'
                )}
              </button>

              {/* Footer text */}
              <p style={{
                marginTop: '24px', fontSize: '11px',
                color: 'var(--txt-ghost)', textAlign: 'center',
              }}>
                Secure crew access only
              </p>
            </form>
          </div>
        </div>
      </div>

      {/* Version stamp */}
      <span style={{
        position: 'fixed', bottom: '16px', left: '50%', transform: 'translateX(-50%)',
        fontSize: '10px', fontFamily: 'var(--font-mono)',
        color: 'var(--txt-ghost)', letterSpacing: '0.04em', zIndex: 2,
      }}>
        v1.0.0
      </span>
    </div>
  );
}
