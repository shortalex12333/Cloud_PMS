'use client';

/**
 * SettingsModal - Unified Settings Interface
 *
 * Single modal for all settings on /app
 * Merged from SettingsContent page features
 */

import { X, Settings, Mail, Sun, Moon, Monitor, Keyboard, AlertCircle, RefreshCw, LogOut, HelpCircle, Loader2 } from 'lucide-react';
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

type Theme = 'light' | 'dark' | 'system';
type TabType = 'profile' | 'integrations' | 'preferences';

const MAX_STATUS_RETRIES = 3;
const STATUS_RETRY_DELAYS = [1000, 2000, 4000];

export default function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const router = useRouter();
  const { user, logout } = useAuth();
  const { accessToken, isReady, isAuthenticated, refreshToken } = useAuthSession();

  // Tab state
  const [activeTab, setActiveTab] = useState<TabType>('profile');

  // Outlook integration state
  const [outlookStatus, setOutlookStatus] = useState<IntegrationStatus | null>(null);
  const [outlookLoading, setOutlookLoading] = useState(true);
  const [outlookError, setOutlookError] = useState<string | null>(null);
  const [connectingOutlook, setConnectingOutlook] = useState(false);

  // Preferences state
  const [theme, setTheme] = useState<Theme>('system');
  const [keyboardShortcuts, setKeyboardShortcuts] = useState(true);

  // Load preferences from localStorage
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const savedTheme = localStorage.getItem('celeste_theme') as Theme;
      const savedShortcuts = localStorage.getItem('celeste_shortcuts');
      if (savedTheme) setTheme(savedTheme);
      if (savedShortcuts !== null) setKeyboardShortcuts(savedShortcuts === 'true');
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

  // Save keyboard shortcuts preference
  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('celeste_shortcuts', String(keyboardShortcuts));
    }
  }, [keyboardShortcuts]);

  /**
   * Fetch Outlook status with bounded retries
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

  // Fetch status when modal opens on integrations tab
  useEffect(() => {
    if (isOpen && activeTab === 'integrations' && isReady) {
      fetchOutlookStatus();
    }
  }, [isOpen, activeTab, isReady, fetchOutlookStatus]);

  /**
   * Connect to Outlook
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
        // Try refresh once
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
   * Disconnect from Outlook
   */
  const handleDisconnectOutlook = async () => {
    if (!confirm('Disconnect your Outlook account?')) return;

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
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-2xl bg-celeste-bg-secondary border border-celeste-border rounded-celeste-lg shadow-celeste-xl mx-4 max-h-[85vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-celeste-border">
          <div className="flex items-center gap-2">
            <Settings className="h-5 w-5 text-celeste-blue" />
            <h2 className="text-celeste-lg font-semibold text-celeste-text-primary">Settings</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-celeste-bg-tertiary rounded-celeste-sm transition-colors"
          >
            <X className="h-5 w-5 text-celeste-text-secondary" />
          </button>
        </div>

        {/* Tabs */}
        <div className="border-b border-celeste-border px-6">
          <div className="flex gap-4 text-celeste-sm">
            {(['profile', 'integrations', 'preferences'] as TabType[]).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={cn(
                  'py-3 border-b-2 transition-colors capitalize',
                  activeTab === tab
                    ? 'border-celeste-blue font-medium text-celeste-text-primary'
                    : 'border-transparent text-celeste-text-muted hover:text-celeste-text-primary'
                )}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(85vh-200px)]">
          {/* Profile Tab */}
          {activeTab === 'profile' && (
            <div className="space-y-6">
              {/* User Info */}
              <div className="space-y-3">
                <h3 className="text-celeste-sm font-semibold text-celeste-text-muted uppercase tracking-wide">
                  Account
                </h3>
                <div className="bg-celeste-bg-primary border border-celeste-border rounded-celeste-md p-4 space-y-3">
                  <div className="flex justify-between text-celeste-sm">
                    <span className="text-celeste-text-muted">Name</span>
                    <span className="font-medium text-celeste-text-primary">{user?.displayName || '—'}</span>
                  </div>
                  <div className="flex justify-between text-celeste-sm">
                    <span className="text-celeste-text-muted">Email</span>
                    <span className="font-medium text-celeste-text-primary">{user?.email || '—'}</span>
                  </div>
                  <div className="flex justify-between text-celeste-sm">
                    <span className="text-celeste-text-muted">Role</span>
                    <span className="font-medium text-celeste-text-primary capitalize">{user?.role?.replace('_', ' ') || '—'}</span>
                  </div>
                  <div className="flex justify-between text-celeste-sm">
                    <span className="text-celeste-text-muted">Yacht</span>
                    <span className="font-medium text-celeste-text-primary text-xs">{user?.yachtId || '—'}</span>
                  </div>
                </div>
              </div>

              {/* Logout */}
              <div className="space-y-3">
                <h3 className="text-celeste-sm font-semibold text-celeste-text-muted uppercase tracking-wide">
                  Session
                </h3>
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-celeste-sm text-red-500 border border-red-500/30 rounded-celeste-md hover:bg-red-500/10 transition-colors"
                >
                  <LogOut className="h-4 w-4" />
                  Sign Out
                </button>
              </div>

              {/* Support */}
              <div className="space-y-3">
                <h3 className="text-celeste-sm font-semibold text-celeste-text-muted uppercase tracking-wide">
                  Support
                </h3>
                <button
                  onClick={handleOpenSupport}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-celeste-sm text-celeste-text-primary bg-celeste-bg-tertiary rounded-celeste-md hover:bg-celeste-border transition-colors"
                >
                  <HelpCircle className="h-4 w-4" />
                  Contact Support
                </button>
              </div>
            </div>
          )}

          {/* Integrations Tab */}
          {activeTab === 'integrations' && (
            <div className="space-y-6">
              {/* Error display */}
              {outlookError && (
                <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-celeste-md flex items-center gap-2">
                  <AlertCircle className="h-4 w-4 text-red-500 flex-shrink-0" />
                  <span className="text-celeste-sm text-red-500 flex-1">{outlookError}</span>
                  <button
                    onClick={handleRetryStatus}
                    className="p-1 hover:bg-red-500/20 rounded"
                    aria-label="Retry"
                  >
                    <RefreshCw className="h-4 w-4 text-red-500" />
                  </button>
                </div>
              )}

              {/* Microsoft Outlook */}
              <div className="bg-celeste-bg-primary border border-celeste-border rounded-celeste-md p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-[#0078D4] rounded-celeste-sm">
                      <Mail className="h-5 w-5 text-white" />
                    </div>
                    <div>
                      <h3 className="text-celeste-base font-medium text-celeste-text-primary">
                        Microsoft Outlook
                      </h3>
                      {outlookStatus?.connected && outlookStatus.email ? (
                        <p className="text-celeste-sm text-celeste-text-muted">{outlookStatus.email}</p>
                      ) : (
                        <p className="text-celeste-sm text-celeste-text-muted">
                          Connect to sync emails
                        </p>
                      )}
                    </div>
                  </div>
                  <div>
                    {outlookLoading ? (
                      <Loader2 className="h-5 w-5 animate-spin text-celeste-text-muted" />
                    ) : outlookStatus?.connected ? (
                      <button
                        onClick={handleDisconnectOutlook}
                        className="px-4 py-2 text-celeste-sm bg-red-600 text-white rounded-celeste-md hover:bg-red-700 transition-colors"
                      >
                        Disconnect
                      </button>
                    ) : (
                      <button
                        onClick={handleConnectOutlook}
                        disabled={showConnectLoading}
                        className="px-4 py-2 text-celeste-sm bg-celeste-blue text-celeste-white rounded-celeste-md hover:bg-celeste-blue-secondary transition-colors disabled:opacity-50"
                      >
                        {!isReady ? 'Loading...' : connectingOutlook ? (
                          <span className="flex items-center gap-2">
                            <Loader2 className="h-4 w-4 animate-spin" />
                            Connecting...
                          </span>
                        ) : 'Connect'}
                      </button>
                    )}
                  </div>
                </div>
              </div>

              <p className="text-celeste-xs text-celeste-text-disabled">
                Connecting your Microsoft account allows CelesteOS to sync and manage emails related to yacht operations.
              </p>
            </div>
          )}

          {/* Preferences Tab */}
          {activeTab === 'preferences' && (
            <div className="space-y-6">
              {/* Theme */}
              <div className="space-y-3">
                <h3 className="text-celeste-sm font-semibold text-celeste-text-muted uppercase tracking-wide">
                  Appearance
                </h3>
                <div className="flex items-center justify-between bg-celeste-bg-primary border border-celeste-border rounded-celeste-md p-4">
                  <span className="text-celeste-sm text-celeste-text-primary">Theme</span>
                  <div className="flex items-center gap-1 bg-celeste-bg-tertiary rounded-celeste-md p-1">
                    <button
                      onClick={() => setTheme('light')}
                      className={cn(
                        'p-2 rounded-celeste-sm transition-colors',
                        theme === 'light' ? 'bg-celeste-bg-primary shadow-sm' : 'hover:bg-celeste-bg-primary/50'
                      )}
                      aria-label="Light theme"
                    >
                      <Sun className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => setTheme('dark')}
                      className={cn(
                        'p-2 rounded-celeste-sm transition-colors',
                        theme === 'dark' ? 'bg-celeste-bg-primary shadow-sm' : 'hover:bg-celeste-bg-primary/50'
                      )}
                      aria-label="Dark theme"
                    >
                      <Moon className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => setTheme('system')}
                      className={cn(
                        'p-2 rounded-celeste-sm transition-colors',
                        theme === 'system' ? 'bg-celeste-bg-primary shadow-sm' : 'hover:bg-celeste-bg-primary/50'
                      )}
                      aria-label="System theme"
                    >
                      <Monitor className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>

              {/* Keyboard Shortcuts */}
              <div className="space-y-3">
                <h3 className="text-celeste-sm font-semibold text-celeste-text-muted uppercase tracking-wide">
                  Accessibility
                </h3>
                <div className="flex items-center justify-between bg-celeste-bg-primary border border-celeste-border rounded-celeste-md p-4">
                  <div className="flex items-center gap-2">
                    <Keyboard className="h-4 w-4 text-celeste-text-muted" />
                    <span className="text-celeste-sm text-celeste-text-primary">Keyboard Shortcuts</span>
                  </div>
                  <button
                    onClick={() => setKeyboardShortcuts(!keyboardShortcuts)}
                    className={cn(
                      'relative w-11 h-6 rounded-full transition-colors',
                      keyboardShortcuts ? 'bg-celeste-blue' : 'bg-celeste-bg-tertiary'
                    )}
                    role="switch"
                    aria-checked={keyboardShortcuts}
                  >
                    <span
                      className={cn(
                        'absolute top-1 left-1 w-4 h-4 bg-white rounded-full transition-transform',
                        keyboardShortcuts ? 'translate-x-5' : ''
                      )}
                    />
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
