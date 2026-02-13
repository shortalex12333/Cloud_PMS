'use client';

/**
 * SettingsModal - CelesteOS Settings Panel
 *
 * Styling patterns match site-wide conventions:
 * - CSS variables via [var(--celeste-*)] for spacing/sizing
 * - Tailwind tokens for colors, radius, shadows
 * - backdrop-blur-xl for modal overlay (matches SpotlightSearch)
 */

import { X, ChevronDown, Loader2, AlertCircle } from 'lucide-react';
import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { cn } from '@/lib/utils';
import { useAuth } from '@/hooks/useAuth';
import { useAuthSession, waitForSession } from '@/hooks/useAuthSession';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface IntegrationStatus {
  connected: boolean;
  email?: string;
  connectedAt?: string;
  error?: string;
}

type Theme = 'system' | 'light' | 'dark';

const MAX_STATUS_RETRIES = 3;
const STATUS_RETRY_DELAYS = [1000, 2000, 4000];

export default function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const router = useRouter();
  const { user, logout } = useAuth();
  const { accessToken, isReady, isAuthenticated, refreshToken } = useAuthSession();

  const [outlookStatus, setOutlookStatus] = useState<IntegrationStatus | null>(null);
  const [outlookLoading, setOutlookLoading] = useState(true);
  const [outlookError, setOutlookError] = useState<string | null>(null);
  const [connectingOutlook, setConnectingOutlook] = useState(false);
  const [theme, setTheme] = useState<Theme>('system');
  const [themeOpen, setThemeOpen] = useState(false);

  // Theme logic
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('celeste_theme') as Theme;
      if (saved) setTheme(saved);
    }
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const root = document.documentElement;
    const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    if (theme === 'dark' || (theme === 'system' && systemDark)) {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
    localStorage.setItem('celeste_theme', theme);
  }, [theme]);

  // Outlook status fetch
  const fetchOutlookStatus = useCallback(async (retryCount = 0): Promise<void> => {
    if (!isReady || !isAuthenticated) {
      setOutlookLoading(false);
      return;
    }
    let token = accessToken;
    if (!token) token = await waitForSession(5000);
    if (!token) {
      setOutlookError('Please sign in to view integrations.');
      setOutlookLoading(false);
      return;
    }
    try {
      setOutlookError(null);
      const res = await fetch('/api/integrations/outlook/status', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.status === 401) {
        setOutlookError('Session expired.');
        setOutlookLoading(false);
        return;
      }
      if (!res.ok) throw new Error(`Status ${res.status}`);
      const data = await res.json();
      setOutlookStatus(data);
      setOutlookLoading(false);
    } catch {
      if (retryCount < MAX_STATUS_RETRIES) {
        setTimeout(() => fetchOutlookStatus(retryCount + 1), STATUS_RETRY_DELAYS[retryCount] || 4000);
        return;
      }
      setOutlookError('Unable to load status.');
      setOutlookLoading(false);
    }
  }, [isReady, isAuthenticated, accessToken]);

  useEffect(() => {
    if (isOpen && isReady) fetchOutlookStatus();
  }, [isOpen, isReady, fetchOutlookStatus]);

  // Handlers
  const handleConnectOutlook = async () => {
    setConnectingOutlook(true);
    setOutlookError(null);
    try {
      let token = accessToken;
      if (!token) token = await waitForSession(5000);
      if (!token) {
        setOutlookError('Unable to authenticate.');
        setConnectingOutlook(false);
        return;
      }
      const res = await fetch('/api/integrations/outlook/auth-url', {
        headers: { Authorization: `Bearer ${token}`, 'Cache-Control': 'no-cache' },
      });
      const data = await res.json();
      if (res.status === 401) {
        const freshToken = await refreshToken();
        if (!freshToken) {
          setOutlookError('Session expired.');
          setConnectingOutlook(false);
          return;
        }
        const retryRes = await fetch('/api/integrations/outlook/auth-url', {
          headers: { Authorization: `Bearer ${freshToken}`, 'Cache-Control': 'no-cache' },
        });
        const retryData = await retryRes.json();
        if (retryRes.ok && retryData.url) {
          window.location.href = retryData.url;
          return;
        }
        setOutlookError('Authentication failed.');
        setConnectingOutlook(false);
        return;
      }
      if (!res.ok) {
        setOutlookError(data.error || 'Failed to connect');
        setConnectingOutlook(false);
        return;
      }
      if (data.url) window.location.href = data.url;
      else {
        setOutlookError('Invalid response');
        setConnectingOutlook(false);
      }
    } catch {
      setOutlookError('Network error.');
      setConnectingOutlook(false);
    }
  };

  const handleDisconnectOutlook = async () => {
    if (!confirm('Disconnect Microsoft account?')) return;
    setOutlookLoading(true);
    setOutlookError(null);
    try {
      let token = accessToken;
      if (!token) token = await waitForSession(5000);
      if (!token) {
        setOutlookError('Auth required');
        setOutlookLoading(false);
        return;
      }
      await fetch('/api/integrations/outlook/disconnect', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      setOutlookStatus({ connected: false });
    } catch {
      setOutlookError('Failed to disconnect.');
    } finally {
      setOutlookLoading(false);
    }
  };

  const handleLogout = async () => {
    onClose();
    await logout();
    router.push('/login?logout=1');
  };

  const handleSupport = () => {
    window.location.href = 'mailto:contact@celeste7.ai?subject=Reported Issue';
  };

  if (!isOpen) return null;

  const themeLabel = theme === 'system' ? 'System' : theme === 'light' ? 'Light' : 'Dark';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop - matches SpotlightSearch pattern */}
      <div
        className="absolute inset-0 bg-celeste-black/65 backdrop-blur-xl"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal Panel */}
      <div
        className={cn(
          'relative w-full mx-[var(--celeste-spacing-4)]',
          'max-w-[var(--celeste-max-w-modal-lg)]',
          'bg-celeste-panel border border-celeste-border-subtle',
          'rounded-celeste-xl shadow-celeste-xl',
          'overflow-hidden'
        )}
      >
        {/* Header */}
        <div
          className={cn(
            'flex items-center justify-between',
            'h-14 px-5',
            'border-b border-celeste-border-subtle'
          )}
        >
          <span className="text-celeste-base font-semibold text-celeste-text-primary">
            Settings
          </span>
          <button
            onClick={onClose}
            className={cn(
              'w-8 h-8 flex items-center justify-center',
              'rounded-celeste-md',
              'hover:bg-celeste-bg-tertiary',
              'transition-colors duration-celeste-fast',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-celeste-accent'
            )}
          >
            <X className="w-5 h-5 text-celeste-text-muted" />
          </button>
        </div>

        {/* Content */}
        <div className="max-h-[70vh] overflow-y-auto">
          {/* Account Section */}
          <SectionHeader>Account</SectionHeader>
          <SettingsRow label="Name" value={user?.displayName || '—'} />
          <SettingsRow label="Email" value={user?.email || '—'} />
          <SettingsRow label="Role" value={user?.role?.replace('_', ' ') || '—'} />
          <SettingsRow label="Yacht" value={user?.yachtName || '—'} />

          <SettingsRow label="Switch Yacht">
            <button
              onClick={() => {/* TODO: wire up yacht switching */}}
              className={cn(
                'text-celeste-sm text-celeste-accent',
                'hover:text-celeste-accent-hover',
                'transition-colors duration-celeste-fast',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-celeste-accent rounded-celeste-sm'
              )}
            >
              Change
            </button>
          </SettingsRow>

          {/* Integrations Section */}
          <SectionHeader>Integrations</SectionHeader>

          {outlookError && (
            <div
              className={cn(
                'mx-5 mb-2 px-3 py-2',
                'bg-restricted-red/10 border border-restricted-red/20',
                'rounded-celeste-md',
                'flex items-center gap-2'
              )}
            >
              <AlertCircle className="w-4 h-4 text-restricted-red flex-shrink-0" />
              <span className="text-celeste-xs text-restricted-red">{outlookError}</span>
            </div>
          )}

          <SettingsRow label="Microsoft">
            <div className="flex items-center gap-3">
              {outlookLoading ? (
                <Loader2 className="w-4 h-4 animate-spin text-celeste-text-muted" />
              ) : (
                <>
                  <div className="flex items-center gap-2">
                    {outlookStatus?.connected && (
                      <span className="w-2 h-2 rounded-full bg-restricted-green" />
                    )}
                    <span className="text-celeste-sm text-celeste-text-muted">
                      {outlookStatus?.connected ? 'Connected' : 'Not connected'}
                    </span>
                  </div>
                  <button
                    onClick={outlookStatus?.connected ? handleDisconnectOutlook : handleConnectOutlook}
                    disabled={connectingOutlook}
                    className={cn(
                      'text-celeste-sm text-celeste-accent',
                      'hover:text-celeste-accent-hover',
                      'transition-colors duration-celeste-fast',
                      'disabled:opacity-50',
                      'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-celeste-accent rounded-celeste-sm'
                    )}
                  >
                    {connectingOutlook ? 'Connecting...' : outlookStatus?.connected ? 'Disconnect' : 'Connect'}
                  </button>
                </>
              )}
            </div>
          </SettingsRow>

          {/* Appearance Section */}
          <SectionHeader>Appearance</SectionHeader>

          <div className="relative">
            <button
              onClick={() => setThemeOpen(!themeOpen)}
              className={cn(
                'w-full flex items-center justify-between',
                'min-h-[48px] px-5 py-3',
                'border-b border-celeste-border-subtle',
                'hover:bg-celeste-bg-tertiary/40',
                'transition-colors duration-celeste-fast',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-celeste-accent'
              )}
            >
              <span className="text-celeste-sm text-celeste-text-primary">Theme</span>
              <div className="flex items-center gap-2">
                <span className="text-celeste-sm text-celeste-text-muted">{themeLabel}</span>
                <ChevronDown
                  className={cn(
                    'w-4 h-4 text-celeste-text-muted',
                    'transition-transform duration-celeste-fast',
                    themeOpen && 'rotate-180'
                  )}
                />
              </div>
            </button>

            {themeOpen && (
              <div
                className={cn(
                  'absolute right-4 top-[44px] z-10',
                  'w-[var(--celeste-width-filter-medium)]',
                  'bg-celeste-panel border border-celeste-border-subtle',
                  'rounded-celeste-md shadow-celeste-xl',
                  'overflow-hidden'
                )}
              >
                {(['system', 'light', 'dark'] as Theme[]).map((t) => (
                  <button
                    key={t}
                    onClick={() => { setTheme(t); setThemeOpen(false); }}
                    className={cn(
                      'w-full px-4 py-2 text-left text-celeste-sm',
                      'hover:bg-celeste-bg-tertiary/40',
                      'transition-colors duration-celeste-fast',
                      'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-celeste-accent',
                      theme === t
                        ? 'text-celeste-text-primary bg-celeste-bg-tertiary/60'
                        : 'text-celeste-text-muted'
                    )}
                  >
                    {t === 'system' ? 'System' : t === 'light' ? 'Light' : 'Dark'}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Session Section */}
          <SectionHeader>Session</SectionHeader>

          <button
            onClick={handleLogout}
            className={cn(
              'w-full flex items-center',
              'min-h-[48px] px-5 py-3',
              'border-b border-celeste-border-subtle',
              'hover:bg-celeste-bg-tertiary/40',
              'transition-colors duration-celeste-fast',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-celeste-accent'
            )}
          >
            <span className="text-celeste-sm text-celeste-text-primary">Sign out</span>
          </button>

          <button
            onClick={handleSupport}
            className={cn(
              'w-full flex items-center',
              'min-h-[48px] px-5 py-3',
              'hover:bg-celeste-bg-tertiary/40',
              'transition-colors duration-celeste-fast',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-celeste-accent'
            )}
          >
            <span className="text-celeste-sm text-celeste-text-primary">Report issue</span>
          </button>

          {/* Bottom spacing */}
          <div className="h-4" />
        </div>
      </div>
    </div>
  );
}

/* ============================================================================
   SUB-COMPONENTS
   Following site-wide patterns: cn(), Tailwind tokens, CSS vars for sizing
   ============================================================================ */

function SectionHeader({ children }: { children: React.ReactNode }) {
  return (
    <div className="px-5 pt-6 pb-2">
      <span className="text-celeste-xs font-semibold text-celeste-text-muted uppercase tracking-wide">
        {children}
      </span>
    </div>
  );
}

interface SettingsRowProps {
  label: string;
  value?: string;
  children?: React.ReactNode;
}

function SettingsRow({ label, value, children }: SettingsRowProps) {
  return (
    <div
      className={cn(
        'flex items-center justify-between',
        'min-h-[48px] px-5 py-3',
        'border-b border-celeste-border-subtle'
      )}
    >
      <span className="text-celeste-sm text-celeste-text-primary">{label}</span>
      {value !== undefined ? (
        <span className="text-celeste-sm text-celeste-text-muted truncate max-w-[60%] text-right">
          {value}
        </span>
      ) : (
        children
      )}
    </div>
  );
}
