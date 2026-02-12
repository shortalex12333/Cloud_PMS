'use client';

/**
 * SettingsModal - CelesteOS Settings Interface
 *
 * Single-surface settings modal. No tabs, no accordion.
 * Uses Celeste design tokens exclusively - no hardcoded values.
 *
 * Sections:
 * 1. Identity - Name, Email, Role, Active Yacht
 * 2. Microsoft Connection - Status + Connect/Disconnect
 * 3. Appearance - System/Light/Dark theme
 * 4. Support - Report Issue
 * 5. Session - Sign Out
 */

import { X, Sun, Moon, Monitor, AlertCircle, RefreshCw, LogOut, HelpCircle, Loader2 } from 'lucide-react';
import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { cn } from '@/lib/utils';
import { useAuth } from '@/hooks/useAuth';
import { useAuthSession, waitForSession } from '@/hooks/useAuthSession';
import { Button } from '@/components/ui/button';
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
   * (Handler preserved - no logic changes)
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

  // Fetch status when modal opens (single surface - always visible)
  useEffect(() => {
    if (isOpen && isReady) {
      fetchOutlookStatus();
    }
  }, [isOpen, isReady, fetchOutlookStatus]);

  /**
   * Connect to Microsoft Outlook
   * (Handler preserved - no logic changes)
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
   * (Handler preserved - no logic changes)
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

  /**
   * Retry fetching status
   * (Handler preserved)
   */
  const handleRetryStatus = () => {
    setOutlookLoading(true);
    setOutlookError(null);
    fetchOutlookStatus();
  };

  /**
   * Sign out
   * (Handler preserved - no logic changes)
   */
  const handleLogout = async () => {
    await logout();
    onClose();
    router.push('/login');
  };

  /**
   * Open support email
   * (Handler preserved - no logic changes)
   */
  const handleOpenSupport = () => {
    window.location.href = 'mailto:support@celeste7.ai?subject=CelesteOS Support Request';
  };

  if (!isOpen) return null;

  const showConnectLoading = !isReady || connectingOutlook;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center font-body">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-celeste-black/50 backdrop-blur-celeste-modal"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-celeste-modal-lg bg-celeste-bg-secondary border border-celeste-border rounded-celeste-lg shadow-celeste-xl mx-[var(--celeste-spacing-4)] max-h-[85vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-[var(--celeste-spacing-6)] py-[var(--celeste-spacing-4)] border-b border-celeste-border">
          <h2 className="text-celeste-lg font-semibold text-celeste-text-primary">Settings</h2>
          <button
            onClick={onClose}
            className="p-[var(--celeste-spacing-1)] hover:bg-celeste-bg-tertiary rounded-celeste-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-celeste-accent"
          >
            <X className="h-5 w-5 text-celeste-text-secondary" />
          </button>
        </div>

        {/* Content - Single Surface */}
        <div className="px-[var(--celeste-spacing-6)] py-[var(--celeste-spacing-6)] overflow-y-auto max-h-[calc(85vh-80px)] space-y-[var(--celeste-spacing-6)]">

          {/* Section 1: Identity */}
          <SettingsSection title="Identity">
            <SettingsRow label="Name" value={user?.displayName || '—'} />
            <SettingsRow label="Email" value={user?.email || '—'} />
            <SettingsRow label="Role" value={user?.role?.replace('_', ' ') || '—'} />
            <SettingsRow label="Active Yacht" value={user?.yachtName || '—'} border={false} />
          </SettingsSection>

          {/* Section 2: Microsoft Connection */}
          <SettingsSection title="Microsoft">
            {/* Error display */}
            {outlookError && (
              <div className="flex items-center gap-[var(--celeste-spacing-2)] px-[var(--celeste-spacing-4)] py-[var(--celeste-spacing-3)] border-b border-celeste-border bg-restricted-red/10">
                <AlertCircle className="h-4 w-4 text-restricted-red flex-shrink-0" />
                <span className="text-celeste-sm text-restricted-red flex-1">{outlookError}</span>
                <button
                  onClick={handleRetryStatus}
                  className="p-[var(--celeste-spacing-1)] hover:bg-restricted-red/20 rounded-celeste-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-celeste-accent"
                  aria-label="Retry"
                >
                  <RefreshCw className="h-4 w-4 text-restricted-red" />
                </button>
              </div>
            )}

            <SettingsRow label="Status">
              {outlookLoading ? (
                <Loader2 className="h-4 w-4 animate-spin text-celeste-text-muted" />
              ) : (
                <span className={cn(
                  'text-celeste-sm font-medium',
                  outlookStatus?.connected ? 'text-restricted-green' : 'text-celeste-text-secondary'
                )}>
                  {outlookStatus?.connected ? 'Connected' : 'Disconnected'}
                </span>
              )}
            </SettingsRow>

            {outlookStatus?.connected && outlookStatus.email && (
              <SettingsRow label="Account" value={outlookStatus.email} />
            )}

            <div className="px-[var(--celeste-spacing-4)] py-[var(--celeste-spacing-3)]">
              {outlookLoading ? null : outlookStatus?.connected ? (
                <Button
                  variant="warning"
                  size="sm"
                  onClick={handleDisconnectOutlook}
                  className="w-full"
                >
                  Disconnect
                </Button>
              ) : (
                <Button
                  variant="accent"
                  size="sm"
                  onClick={handleConnectOutlook}
                  disabled={showConnectLoading}
                  className="w-full"
                >
                  {!isReady ? 'Loading...' : connectingOutlook ? (
                    <span className="flex items-center gap-[var(--celeste-spacing-2)]">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Connecting...
                    </span>
                  ) : 'Connect'}
                </Button>
              )}
            </div>
          </SettingsSection>

          {/* Section 3: Appearance */}
          <SettingsSection title="Appearance">
            <div className="flex items-center justify-between px-[var(--celeste-spacing-4)] py-[var(--celeste-spacing-3)]">
              <span className="text-celeste-sm text-celeste-text-secondary">Theme</span>
              <div className="flex items-center gap-[var(--celeste-spacing-1)] bg-celeste-bg-tertiary rounded-celeste-md p-[var(--celeste-spacing-1)]">
                <button
                  onClick={() => setTheme('light')}
                  className={cn(
                    'p-[var(--celeste-spacing-2)] rounded-celeste-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-celeste-accent',
                    theme === 'light' ? 'bg-celeste-bg-primary shadow-celeste-sm' : 'hover:bg-celeste-bg-primary/50'
                  )}
                  aria-label="Light theme"
                >
                  <Sun className="h-4 w-4 text-celeste-text-primary" />
                </button>
                <button
                  onClick={() => setTheme('dark')}
                  className={cn(
                    'p-[var(--celeste-spacing-2)] rounded-celeste-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-celeste-accent',
                    theme === 'dark' ? 'bg-celeste-bg-primary shadow-celeste-sm' : 'hover:bg-celeste-bg-primary/50'
                  )}
                  aria-label="Dark theme"
                >
                  <Moon className="h-4 w-4 text-celeste-text-primary" />
                </button>
                <button
                  onClick={() => setTheme('system')}
                  className={cn(
                    'p-[var(--celeste-spacing-2)] rounded-celeste-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-celeste-accent',
                    theme === 'system' ? 'bg-celeste-bg-primary shadow-celeste-sm' : 'hover:bg-celeste-bg-primary/50'
                  )}
                  aria-label="System theme"
                >
                  <Monitor className="h-4 w-4 text-celeste-text-primary" />
                </button>
              </div>
            </div>
          </SettingsSection>

          {/* Section 4: Support */}
          <SettingsSection title="Support">
            <div className="px-[var(--celeste-spacing-4)] py-[var(--celeste-spacing-3)]">
              <Button
                variant="secondary"
                size="sm"
                onClick={handleOpenSupport}
                className="w-full"
              >
                <HelpCircle className="h-4 w-4" />
                Report Issue
              </Button>
            </div>
          </SettingsSection>

          {/* Section 5: Session */}
          <SettingsSection title="Session">
            <div className="px-[var(--celeste-spacing-4)] py-[var(--celeste-spacing-3)]">
              <Button
                variant="ghost"
                size="sm"
                onClick={handleLogout}
                className="w-full text-celeste-text-secondary hover:text-celeste-text-primary"
              >
                <LogOut className="h-4 w-4" />
                Sign Out
              </Button>
            </div>
          </SettingsSection>

        </div>
      </div>
    </div>
  );
}
