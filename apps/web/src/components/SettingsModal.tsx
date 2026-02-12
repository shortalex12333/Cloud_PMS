'use client';

/**
 * SettingsModal - ChatGPT-quality settings panel
 *
 * All styling uses Celeste design tokens.
 * Zero hardcoded colors or spacing values.
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

  // Handlers (preserved)
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
    // Add logout param to prevent auto-login from cached session
    router.push('/login?logout=1');
  };

  const handleSupport = () => {
    window.location.href = 'mailto:contact@celeste7.ai?subject=Reported Issue';
  };

  if (!isOpen) return null;

  const themeLabel = theme === 'system' ? 'System' : theme === 'light' ? 'Light' : 'Dark';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-celeste-black/80 backdrop-blur-celeste-spotlight"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-celeste-modal-lg mx-[var(--celeste-spacing-4)] bg-celeste-surface border border-celeste-border-subtle rounded-celeste-xl shadow-celeste-xl overflow-hidden">

        {/* Header */}
        <div className="flex items-center justify-between h-celeste-element-xl px-[var(--celeste-spacing-6)] border-b border-celeste-border-subtle">
          <span className="text-celeste-base font-semibold text-celeste-text-primary">Settings</span>
          <button
            onClick={onClose}
            className="w-[var(--celeste-spacing-8)] h-[var(--celeste-spacing-8)] flex items-center justify-center rounded-celeste-md hover:bg-celeste-white/10 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-celeste-accent"
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

          <div className="flex items-center justify-between h-celeste-element-xl px-[var(--celeste-spacing-6)] border-b border-celeste-border-subtle">
            <span className="text-celeste-sm text-celeste-text-primary">Switch Yacht</span>
            <button
              onClick={() => {/* TODO: wire up yacht switching */}}
              className="text-celeste-xs text-celeste-accent hover:text-celeste-accent-hover transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-celeste-accent rounded-celeste-sm"
            >
              Change
            </button>
          </div>

          {/* Integrations Section */}
          <SectionHeader>Integrations</SectionHeader>

          {outlookError && (
            <div className="mx-[var(--celeste-spacing-6)] mb-[var(--celeste-spacing-2)] px-[var(--celeste-spacing-3)] py-[var(--celeste-spacing-2)] bg-restricted-red/10 border border-restricted-red/20 rounded-celeste-md flex items-center gap-[var(--celeste-spacing-2)]">
              <AlertCircle className="w-4 h-4 text-restricted-red" />
              <span className="text-celeste-xs text-restricted-red">{outlookError}</span>
            </div>
          )}

          <div className="flex items-center justify-between h-celeste-element-xl px-[var(--celeste-spacing-6)] border-b border-celeste-border-subtle">
            <span className="text-celeste-sm text-celeste-text-primary">Microsoft</span>
            <div className="flex items-center gap-[var(--celeste-spacing-3)]">
              {outlookLoading ? (
                <Loader2 className="w-4 h-4 animate-spin text-celeste-text-muted" />
              ) : (
                <>
                  <div className="flex items-center gap-[var(--celeste-spacing-2)]">
                    {outlookStatus?.connected && (
                      <span className="w-[var(--celeste-spacing-2)] h-[var(--celeste-spacing-2)] rounded-full bg-restricted-green" />
                    )}
                    <span className="text-celeste-sm text-celeste-text-muted">
                      {outlookStatus?.connected ? 'Connected' : 'Not connected'}
                    </span>
                  </div>
                  <button
                    onClick={outlookStatus?.connected ? handleDisconnectOutlook : handleConnectOutlook}
                    disabled={connectingOutlook}
                    className="text-celeste-xs text-celeste-accent hover:text-celeste-accent-hover transition-colors disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-celeste-accent rounded-celeste-sm"
                  >
                    {connectingOutlook ? 'Connecting...' : outlookStatus?.connected ? 'Disconnect' : 'Connect'}
                  </button>
                </>
              )}
            </div>
          </div>

          {/* Appearance Section */}
          <SectionHeader>Appearance</SectionHeader>

          <div className="relative">
            <button
              onClick={() => setThemeOpen(!themeOpen)}
              className="w-full flex items-center justify-between h-celeste-element-xl px-[var(--celeste-spacing-6)] border-b border-celeste-border-subtle hover:bg-celeste-white/5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-celeste-accent"
            >
              <span className="text-celeste-sm text-celeste-text-primary">Theme</span>
              <div className="flex items-center gap-[var(--celeste-spacing-2)]">
                <span className="text-celeste-sm text-celeste-text-muted">{themeLabel}</span>
                <ChevronDown className={cn("w-4 h-4 text-celeste-text-muted transition-transform", themeOpen && "rotate-180")} />
              </div>
            </button>

            {themeOpen && (
              <div className="absolute right-[var(--celeste-spacing-4)] top-[calc(var(--celeste-height-element-xl)-4px)] z-10 w-[140px] bg-celeste-panel border border-celeste-border-subtle rounded-celeste-md shadow-celeste-xl overflow-hidden">
                {(['system', 'light', 'dark'] as Theme[]).map((t) => (
                  <button
                    key={t}
                    onClick={() => { setTheme(t); setThemeOpen(false); }}
                    className={cn(
                      "w-full px-[var(--celeste-spacing-4)] py-[var(--celeste-spacing-2)] text-left text-celeste-xs hover:bg-celeste-white/10 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-celeste-accent",
                      theme === t ? "text-celeste-text-primary bg-celeste-white/5" : "text-celeste-text-muted"
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
            className="w-full flex items-center h-celeste-element-xl px-[var(--celeste-spacing-6)] border-b border-celeste-border-subtle hover:bg-celeste-white/5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-celeste-accent"
          >
            <span className="text-celeste-sm text-celeste-text-primary">Sign out</span>
          </button>

          <button
            onClick={handleSupport}
            className="w-full flex items-center h-celeste-element-xl px-[var(--celeste-spacing-6)] hover:bg-celeste-white/5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-celeste-accent"
          >
            <span className="text-celeste-sm text-celeste-text-primary">Report issue</span>
          </button>

          {/* Bottom padding */}
          <div className="h-[var(--celeste-spacing-4)]" />
        </div>
      </div>
    </div>
  );
}

/* ============================================================================
   COMPONENTS - Using Celeste tokens only
   ============================================================================ */

function SectionHeader({ children }: { children: React.ReactNode }) {
  return (
    <div className="px-[var(--celeste-spacing-6)] pt-[var(--celeste-spacing-6)] pb-[var(--celeste-spacing-2)]">
      <span className="text-celeste-xs font-medium text-celeste-text-muted uppercase tracking-widest">
        {children}
      </span>
    </div>
  );
}

function SettingsRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between h-celeste-element-xl px-[var(--celeste-spacing-6)] border-b border-celeste-border-subtle">
      <span className="text-celeste-sm text-celeste-text-primary">{label}</span>
      <span className="text-celeste-sm text-celeste-text-muted">{value}</span>
    </div>
  );
}
