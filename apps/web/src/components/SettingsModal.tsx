'use client';

/**
 * SettingsModal - CelesteOS Settings Interface
 *
 * OS-style system panel. NOT a form. NOT a dashboard.
 *
 * Design:
 * - ONE outer container with shadow
 * - Flat rows with subtle dividers
 * - No nested boxes
 * - Text-based controls
 */

import { X, AlertCircle, RefreshCw, Loader2 } from 'lucide-react';
import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { cn } from '@/lib/utils';
import { useAuth } from '@/hooks/useAuth';
import { useAuthSession, waitForSession } from '@/hooks/useAuthSession';
import { SettingsSection, SettingsRow } from '@/components/settings';

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

type Theme = 'light' | 'dark' | 'system';

const MAX_STATUS_RETRIES = 3;
const STATUS_RETRY_DELAYS = [1000, 2000, 4000];

export default function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const router = useRouter();
  const { user, logout } = useAuth();
  const { accessToken, isReady, isAuthenticated, refreshToken } = useAuthSession();

  // Microsoft integration state
  const [outlookStatus, setOutlookStatus] = useState<IntegrationStatus | null>(null);
  const [outlookLoading, setOutlookLoading] = useState(true);
  const [outlookError, setOutlookError] = useState<string | null>(null);
  const [connectingOutlook, setConnectingOutlook] = useState(false);

  // Theme state
  const [theme, setTheme] = useState<Theme>('system');

  // Load theme preference from localStorage
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const savedTheme = localStorage.getItem('celeste_theme') as Theme;
      if (savedTheme) setTheme(savedTheme);
    }
  }, []);

  // Apply theme
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

  /**
   * Fetch Microsoft Outlook status with bounded retries
   */
  const fetchOutlookStatus = useCallback(async (retryCount = 0): Promise<void> => {
    if (!isReady || !isAuthenticated) {
      setOutlookLoading(false);
      return;
    }

    let token = accessToken;
    if (!token) {
      token = await waitForSession(5000);
    }

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
        setOutlookError('Session expired. Please sign in again.');
        setOutlookLoading(false);
        return;
      }

      if (!res.ok) {
        throw new Error(`Status ${res.status}`);
      }

      const data = await res.json();
      setOutlookStatus(data);
      setOutlookLoading(false);

    } catch (error) {
      if (retryCount < MAX_STATUS_RETRIES) {
        const delay = STATUS_RETRY_DELAYS[retryCount] || 4000;
        setTimeout(() => fetchOutlookStatus(retryCount + 1), delay);
        return;
      }

      setOutlookError('Unable to load integration status.');
      setOutlookLoading(false);
    }
  }, [isReady, isAuthenticated, accessToken]);

  // Fetch status when modal opens
  useEffect(() => {
    if (isOpen && isReady) {
      fetchOutlookStatus();
    }
  }, [isOpen, isReady, fetchOutlookStatus]);

  /**
   * Connect to Microsoft Outlook
   */
  const handleConnectOutlook = async () => {
    setConnectingOutlook(true);
    setOutlookError(null);

    try {
      let token = accessToken;
      if (!token) {
        token = await waitForSession(5000);
      }

      if (!token) {
        setOutlookError('Unable to authenticate. Please sign in again.');
        setConnectingOutlook(false);
        return;
      }

      const res = await fetch('/api/integrations/outlook/auth-url', {
        headers: {
          Authorization: `Bearer ${token}`,
          'Cache-Control': 'no-cache',
        },
      });

      const data = await res.json();

      if (res.status === 401) {
        const freshToken = await refreshToken();
        if (!freshToken) {
          setOutlookError('Session expired. Please sign in again.');
          setConnectingOutlook(false);
          return;
        }

        const retryRes = await fetch('/api/integrations/outlook/auth-url', {
          headers: {
            Authorization: `Bearer ${freshToken}`,
            'Cache-Control': 'no-cache',
          },
        });

        const retryData = await retryRes.json();
        if (retryRes.ok && retryData.url) {
          window.location.href = retryData.url;
          return;
        }

        setOutlookError('Authentication failed. Please sign in again.');
        setConnectingOutlook(false);
        return;
      }

      if (!res.ok) {
        setOutlookError(data.error || 'Failed to start connection');
        setConnectingOutlook(false);
        return;
      }

      if (data.url) {
        window.location.href = data.url;
      } else {
        setOutlookError('Invalid response from server');
        setConnectingOutlook(false);
      }

    } catch (error) {
      setOutlookError('Network error. Please check your connection.');
      setConnectingOutlook(false);
    }
  };

  /**
   * Disconnect from Microsoft Outlook
   */
  const handleDisconnectOutlook = async () => {
    if (!confirm('Disconnect your Microsoft account?')) return;

    setOutlookLoading(true);
    setOutlookError(null);

    try {
      let token = accessToken;
      if (!token) token = await waitForSession(5000);
      if (!token) {
        setOutlookError('Authentication required');
        setOutlookLoading(false);
        return;
      }

      await fetch('/api/integrations/outlook/disconnect', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      setOutlookStatus({ connected: false });
    } catch (error) {
      setOutlookError('Failed to disconnect. Please try again.');
    } finally {
      setOutlookLoading(false);
    }
  };

  const handleRetryStatus = () => {
    setOutlookLoading(true);
    setOutlookError(null);
    fetchOutlookStatus();
  };

  const handleLogout = async () => {
    await logout();
    onClose();
    router.push('/login');
  };

  const handleOpenSupport = () => {
    window.location.href = 'mailto:support@celeste7.ai?subject=CelesteOS Support Request';
  };

  if (!isOpen) return null;

  const showConnectLoading = !isReady || connectingOutlook;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center font-body">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-celeste-black/60 backdrop-blur-celeste-spotlight"
        onClick={onClose}
      />

      {/* Modal - ONE container, spotlight aesthetic */}
      <div className="relative w-full max-w-celeste-modal-lg bg-celeste-bg-primary border border-celeste-border-subtle rounded-celeste-xl shadow-celeste-xl mx-[var(--celeste-spacing-4)] max-h-[85vh] overflow-hidden">

        {/* Header - minimal */}
        <div className="flex items-center justify-between px-[var(--celeste-spacing-6)] py-[var(--celeste-spacing-4)]">
          <h2 className="text-celeste-lg font-semibold text-celeste-text-primary">Settings</h2>
          <button
            onClick={onClose}
            className="p-[var(--celeste-spacing-2)] -mr-[var(--celeste-spacing-2)] hover:bg-celeste-bg-tertiary rounded-celeste-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-celeste-accent"
          >
            <X className="h-5 w-5 text-celeste-text-muted" />
          </button>
        </div>

        {/* Content - flat, no nested boxes */}
        <div className="px-[var(--celeste-spacing-6)] pb-[var(--celeste-spacing-6)] overflow-y-auto max-h-[calc(85vh-72px)]">

          {/* Identity */}
          <SettingsSection title="Identity">
            <SettingsRow label="Name" value={user?.displayName || '—'} />
            <SettingsRow label="Email" value={user?.email || '—'} />
            <SettingsRow label="Role" value={user?.role?.replace('_', ' ') || '—'} />
            <SettingsRow label="Active Yacht" value={user?.yachtName || '—'} divider={false} />
          </SettingsSection>

          {/* Spacer */}
          <div className="h-[var(--celeste-spacing-6)]" />

          {/* Microsoft */}
          <SettingsSection title="Microsoft">
            {/* Error */}
            {outlookError && (
              <div className="flex items-center gap-[var(--celeste-spacing-2)] py-[var(--celeste-spacing-3)] border-b border-celeste-border-subtle">
                <AlertCircle className="h-4 w-4 text-restricted-red flex-shrink-0" />
                <span className="text-celeste-sm text-restricted-red flex-1">{outlookError}</span>
                <button
                  onClick={handleRetryStatus}
                  className="p-[var(--celeste-spacing-1)] hover:bg-celeste-bg-tertiary rounded-celeste-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-celeste-accent"
                  aria-label="Retry"
                >
                  <RefreshCw className="h-4 w-4 text-restricted-red" />
                </button>
              </div>
            )}

            {/* Status row with inline action */}
            <SettingsRow label="Status" divider={false}>
              <div className="flex items-center gap-[var(--celeste-spacing-3)]">
                {outlookLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin text-celeste-text-muted" />
                ) : (
                  <>
                    <span className={cn(
                      'text-celeste-sm font-medium',
                      outlookStatus?.connected ? 'text-restricted-green' : 'text-celeste-text-secondary'
                    )}>
                      {outlookStatus?.connected ? 'Connected' : 'Disconnected'}
                    </span>
                    {outlookStatus?.connected ? (
                      <button
                        onClick={handleDisconnectOutlook}
                        className="text-celeste-sm text-celeste-text-muted hover:text-celeste-text-primary transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-celeste-accent rounded-celeste-sm px-[var(--celeste-spacing-2)] py-[var(--celeste-spacing-1)]"
                      >
                        Disconnect
                      </button>
                    ) : (
                      <button
                        onClick={handleConnectOutlook}
                        disabled={showConnectLoading}
                        className="text-celeste-sm text-celeste-accent hover:text-celeste-accent-hover transition-colors disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-celeste-accent rounded-celeste-sm px-[var(--celeste-spacing-2)] py-[var(--celeste-spacing-1)]"
                      >
                        {connectingOutlook ? 'Connecting...' : 'Connect'}
                      </button>
                    )}
                  </>
                )}
              </div>
            </SettingsRow>
          </SettingsSection>

          {/* Spacer */}
          <div className="h-[var(--celeste-spacing-6)]" />

          {/* Appearance */}
          <SettingsSection title="Appearance">
            <SettingsRow label="Theme" divider={false}>
              {/* Text-based segmented control */}
              <div className="flex items-center text-celeste-sm">
                <button
                  onClick={() => setTheme('system')}
                  className={cn(
                    'px-[var(--celeste-spacing-3)] py-[var(--celeste-spacing-1)] rounded-l-celeste-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-celeste-accent',
                    theme === 'system'
                      ? 'bg-celeste-bg-tertiary text-celeste-text-primary font-medium'
                      : 'text-celeste-text-muted hover:text-celeste-text-secondary'
                  )}
                >
                  System
                </button>
                <button
                  onClick={() => setTheme('light')}
                  className={cn(
                    'px-[var(--celeste-spacing-3)] py-[var(--celeste-spacing-1)] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-celeste-accent',
                    theme === 'light'
                      ? 'bg-celeste-bg-tertiary text-celeste-text-primary font-medium'
                      : 'text-celeste-text-muted hover:text-celeste-text-secondary'
                  )}
                >
                  Light
                </button>
                <button
                  onClick={() => setTheme('dark')}
                  className={cn(
                    'px-[var(--celeste-spacing-3)] py-[var(--celeste-spacing-1)] rounded-r-celeste-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-celeste-accent',
                    theme === 'dark'
                      ? 'bg-celeste-bg-tertiary text-celeste-text-primary font-medium'
                      : 'text-celeste-text-muted hover:text-celeste-text-secondary'
                  )}
                >
                  Dark
                </button>
              </div>
            </SettingsRow>
          </SettingsSection>

          {/* Spacer */}
          <div className="h-[var(--celeste-spacing-6)]" />

          {/* Support & Session - combined for minimal footprint */}
          <div className="flex items-center justify-between py-[var(--celeste-spacing-3)]">
            <button
              onClick={handleOpenSupport}
              className="text-celeste-sm text-celeste-text-muted hover:text-celeste-text-secondary transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-celeste-accent rounded-celeste-sm"
            >
              Report Issue
            </button>
            <button
              onClick={handleLogout}
              className="text-celeste-sm text-celeste-text-muted hover:text-celeste-text-secondary transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-celeste-accent rounded-celeste-sm"
            >
              Sign Out
            </button>
          </div>

        </div>
      </div>
    </div>
  );
}
