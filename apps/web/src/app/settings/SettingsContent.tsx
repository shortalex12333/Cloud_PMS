'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { useAuthSession, waitForSession } from '@/hooks/useAuthSession';
import { withAuth } from '@/components/withAuth';
import { X, Mail, Sun, Moon, Monitor, Keyboard, AlertCircle, RefreshCw } from 'lucide-react';

// Build version marker for cache verification
console.log('[SettingsContent] Module loaded - build 2026-01-27-v2');

// Integration status type
interface IntegrationStatus {
  connected: boolean;
  email?: string;
  connectedAt?: string;
  error?: string;
}

type Theme = 'light' | 'dark' | 'system';

// Max retries for status endpoint (bounded, not infinite)
const MAX_STATUS_RETRIES = 3;
const STATUS_RETRY_DELAYS = [1000, 2000, 4000]; // Exponential backoff

function SettingsContent() {
  const { user, logout } = useAuth();
  const { accessToken, isReady, isAuthenticated, refreshToken } = useAuthSession();
  const router = useRouter();
  const searchParams = useSearchParams();

  // State for Outlook integration
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
   * Fetch with authentication - uses centralized session
   * No retry loops - single attempt with clear error surfacing
   */
  const authFetch = useCallback(async (url: string, options: RequestInit = {}): Promise<Response> => {
    // Wait for session to be ready (with timeout)
    const token = accessToken || await waitForSession(3000);

    if (!token) {
      console.error('[authFetch] No access token available');
      throw new Error('login_required');
    }

    console.log('[authFetch] Making request to:', url, 'with token length:', token.length);

    return fetch(url, {
      ...options,
      headers: {
        ...options.headers,
        'Authorization': `Bearer ${token}`,
        'Cache-Control': 'no-cache',
      },
    });
  }, [accessToken]);

  /**
   * Fetch Outlook status with bounded retries
   * Stops on 401 (auth issue) or after MAX_STATUS_RETRIES
   */
  const fetchOutlookStatus = useCallback(async (retryCount = 0): Promise<void> => {
    if (!isReady) {
      console.log('[Settings] Waiting for auth to be ready...');
      return;
    }

    if (!isAuthenticated) {
      console.log('[Settings] Not authenticated, skipping status fetch');
      setOutlookLoading(false);
      return;
    }

    try {
      setOutlookError(null);
      const res = await authFetch('/api/integrations/outlook/status');

      if (res.status === 401) {
        // Auth issue - don't retry, surface immediately
        console.error('[Settings] Status 401 - session invalid');
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
      const errorMsg = error instanceof Error ? error.message : 'Unknown error';

      if (errorMsg === 'login_required') {
        setOutlookError('Please sign in to view integrations.');
        setOutlookLoading(false);
        return;
      }

      // Retry with backoff for network/5xx errors
      if (retryCount < MAX_STATUS_RETRIES) {
        const delay = STATUS_RETRY_DELAYS[retryCount] || 4000;
        console.log(`[Settings] Status fetch failed, retrying in ${delay}ms (attempt ${retryCount + 1}/${MAX_STATUS_RETRIES})`);
        setTimeout(() => fetchOutlookStatus(retryCount + 1), delay);
        return;
      }

      // Max retries exhausted
      console.error('[Settings] Status fetch failed after retries:', errorMsg);
      setOutlookError('Unable to load integration status. Please try again.');
      setOutlookLoading(false);
    }
  }, [isReady, isAuthenticated, authFetch]);

  // Fetch integration status when auth is ready
  useEffect(() => {
    if (isReady) {
      fetchOutlookStatus();
    }
  }, [isReady, fetchOutlookStatus]);

  // Handle OAuth callback
  useEffect(() => {
    const connected = searchParams.get('connected');
    const error = searchParams.get('error');

    if (connected === 'outlook') {
      console.log('[Settings] OAuth callback - connected');
      setOutlookLoading(true);
      fetchOutlookStatus();
      router.replace('/settings');
    }

    if (error) {
      console.error('[Settings] OAuth error:', error);
      setOutlookError(`Connection failed: ${error}`);
      router.replace('/settings');
    }
  }, [searchParams, router, fetchOutlookStatus]);

  /**
   * Connect to Outlook - single attempt with one retry on 401
   */
  const handleConnectOutlook = async () => {
    setConnectingOutlook(true);
    setOutlookError(null);

    // Debug: Log state at click time
    console.log('[Settings] Connect clicked - state:', {
      isReady,
      hasAccessToken: !!accessToken,
      accessTokenLength: accessToken?.length,
      accessTokenPrefix: accessToken?.substring(0, 20),
    });

    try {
      // Ensure we have a fresh token
      let token = accessToken;
      if (!token) {
        console.log('[Settings] No accessToken from hook, calling waitForSession...');
        token = await waitForSession(5000);
        console.log('[Settings] waitForSession result:', {
          gotToken: !!token,
          tokenLength: token?.length,
        });
      }

      if (!token) {
        console.error('[Settings] FAILED: No token available after waitForSession');
        setOutlookError('Unable to authenticate. Please sign in again.');
        setConnectingOutlook(false);
        return;
      }

      console.log('[Settings] Making request with token:', {
        length: token.length,
        prefix: token.substring(0, 30),
        suffix: token.substring(token.length - 10),
      });

      const res = await fetch('/api/integrations/outlook/auth-url', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Cache-Control': 'no-cache',
        },
      });

      const data = await res.json();

      if (res.status === 401) {
        console.log('[Settings] Got 401, attempting token refresh...');
        // Try refresh once
        const freshToken = await refreshToken();
        if (!freshToken) {
          setOutlookError('Session expired. Please sign in again.');
          router.push('/login');
          return;
        }

        // Retry with fresh token
        const retryRes = await fetch('/api/integrations/outlook/auth-url', {
          headers: {
            'Authorization': `Bearer ${freshToken}`,
            'Cache-Control': 'no-cache',
          },
        });

        const retryData = await retryRes.json();
        if (retryRes.ok && retryData.url) {
          console.log('[Settings] Retry successful, redirecting to Microsoft...');
          window.location.href = retryData.url;
          return;
        }

        // Still failing after refresh
        setOutlookError('Authentication failed. Please sign in again.');
        setConnectingOutlook(false);
        return;
      }

      if (!res.ok) {
        console.error('[Settings] Auth URL error:', data);
        setOutlookError(data.error || 'Failed to start connection');
        setConnectingOutlook(false);
        return;
      }

      if (data.url) {
        console.log('[Settings] Redirecting to Microsoft OAuth...');
        window.location.href = data.url;
      } else {
        console.error('[Settings] No URL in response:', data);
        setOutlookError('Invalid response from server');
        setConnectingOutlook(false);
      }

    } catch (error) {
      console.error('[Settings] Connect error:', error);
      setOutlookError('Network error. Please check your connection.');
      setConnectingOutlook(false);
    }
  };

  // Disconnect from Outlook
  const handleDisconnectOutlook = async () => {
    if (!confirm('Disconnect your Outlook account?')) return;

    setOutlookLoading(true);
    setOutlookError(null);

    try {
      await authFetch('/api/integrations/outlook/disconnect', { method: 'POST' });
      setOutlookStatus({ connected: false });
    } catch (error) {
      console.error('[Settings] Disconnect error:', error);
      setOutlookError('Failed to disconnect. Please try again.');
    } finally {
      setOutlookLoading(false);
    }
  };

  // Retry loading status
  const handleRetryStatus = () => {
    setOutlookLoading(true);
    setOutlookError(null);
    fetchOutlookStatus();
  };

  // Open support email
  const handleOpenSupport = () => {
    window.location.href = 'mailto:support@celeste7.ai?subject=CelesteOS Support Request';
  };

  // Close settings (go back to search)
  const handleClose = () => {
    router.push('/search');
  };

  // Show loading state until auth is ready
  const showConnectLoading = !isReady || connectingOutlook;

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="max-w-2xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-xl font-semibold">Settings</h1>
            <button
              onClick={handleClose}
              className="p-2 hover:bg-muted rounded-md transition-colors"
              aria-label="Close settings"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-2xl mx-auto px-4 py-6 space-y-6">
        {/* Profile */}
        <section className="bg-card border border-border rounded-lg p-5">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-4">
            Profile
          </h2>
          <div className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Name</span>
              <span className="font-medium">{user?.displayName || '—'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Email</span>
              <span className="font-medium">{user?.email || '—'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Role</span>
              <span className="font-medium capitalize">{user?.role?.replace('_', ' ') || '—'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Yacht</span>
              <span className="font-medium">{user?.yachtId || '—'}</span>
            </div>
          </div>
        </section>

        {/* Integrations */}
        <section className="bg-card border border-border rounded-lg p-5">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-4">
            Integrations
          </h2>

          {/* Error display */}
          {outlookError && (
            <div className="mb-4 p-3 bg-destructive/10 border border-destructive/30 rounded-md flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-destructive flex-shrink-0" />
              <span className="text-sm text-destructive">{outlookError}</span>
              <button
                onClick={handleRetryStatus}
                className="ml-auto p-1 hover:bg-destructive/20 rounded"
                aria-label="Retry"
              >
                <RefreshCw className="h-4 w-4 text-destructive" />
              </button>
            </div>
          )}

          {/* Outlook */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-muted rounded-md">
                <Mail className="h-4 w-4" />
              </div>
              <div>
                <p className="text-sm font-medium">Microsoft Outlook</p>
                {outlookStatus?.connected && outlookStatus.email ? (
                  <p className="text-xs text-muted-foreground">{outlookStatus.email}</p>
                ) : (
                  <p className="text-xs text-muted-foreground">Email sync</p>
                )}
              </div>
            </div>
            <div>
              {outlookLoading ? (
                <div className="h-8 w-20 skeleton rounded-md" />
              ) : outlookStatus?.connected ? (
                <button
                  onClick={handleDisconnectOutlook}
                  className="px-3 py-1.5 text-xs border border-border rounded-md hover:bg-muted transition-colors"
                >
                  Disconnect
                </button>
              ) : (
                <button
                  onClick={handleConnectOutlook}
                  disabled={showConnectLoading}
                  className="px-3 py-1.5 text-xs bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50 transition-colors"
                >
                  {!isReady ? 'Loading...' : connectingOutlook ? 'Connecting...' : 'Connect'}
                </button>
              )}
            </div>
          </div>
        </section>

        {/* Preferences */}
        <section className="bg-card border border-border rounded-lg p-5">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-4">
            Preferences
          </h2>
          <div className="space-y-4">
            {/* Theme */}
            <div className="flex items-center justify-between">
              <span className="text-sm">Theme</span>
              <div className="flex items-center gap-1 bg-muted rounded-md p-1">
                <button
                  onClick={() => setTheme('light')}
                  className={`p-1.5 rounded ${theme === 'light' ? 'bg-background shadow-sm' : 'hover:bg-background/50'}`}
                  aria-label="Light theme"
                >
                  <Sun className="h-4 w-4" />
                </button>
                <button
                  onClick={() => setTheme('dark')}
                  className={`p-1.5 rounded ${theme === 'dark' ? 'bg-background shadow-sm' : 'hover:bg-background/50'}`}
                  aria-label="Dark theme"
                >
                  <Moon className="h-4 w-4" />
                </button>
                <button
                  onClick={() => setTheme('system')}
                  className={`p-1.5 rounded ${theme === 'system' ? 'bg-background shadow-sm' : 'hover:bg-background/50'}`}
                  aria-label="System theme"
                >
                  <Monitor className="h-4 w-4" />
                </button>
              </div>
            </div>

            {/* Keyboard Shortcuts */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Keyboard className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm">Keyboard Shortcuts</span>
              </div>
              <button
                onClick={() => setKeyboardShortcuts(!keyboardShortcuts)}
                className={`relative w-10 h-6 rounded-full transition-colors ${keyboardShortcuts ? 'bg-primary' : 'bg-muted'}`}
                role="switch"
                aria-checked={keyboardShortcuts}
              >
                <span
                  className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full transition-transform ${keyboardShortcuts ? 'translate-x-4' : ''}`}
                />
              </button>
            </div>
          </div>
        </section>

        {/* Account */}
        <section className="bg-card border border-border rounded-lg p-5">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-4">
            Account
          </h2>
          <button
            onClick={logout}
            className="w-full px-4 py-2 text-sm text-destructive border border-destructive/30 rounded-md hover:bg-destructive/10 transition-colors"
          >
            Logout
          </button>
        </section>

        {/* Support */}
        <section className="bg-card border border-border rounded-lg p-5">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-4">
            Support
          </h2>
          <button
            onClick={handleOpenSupport}
            className="w-full px-4 py-2 text-sm bg-muted hover:bg-accent rounded-md transition-colors"
          >
            Open Support Email
          </button>
        </section>
      </main>
    </div>
  );
}

export default withAuth(SettingsContent);
