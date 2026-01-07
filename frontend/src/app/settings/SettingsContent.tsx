'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { withAuth } from '@/components/withAuth';
import { supabase } from '@/lib/supabaseClient';
import { X, Mail, Sun, Moon, Monitor, Keyboard } from 'lucide-react';

// Integration status type
interface IntegrationStatus {
  connected: boolean;
  email?: string;
  connectedAt?: string;
}

type Theme = 'light' | 'dark' | 'system';

// Helper for authenticated API calls
async function authFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const { data: { session } } = await supabase.auth.getSession();
  const token = session?.access_token;

  return fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    },
  });
}

function SettingsContent() {
  const { user, logout } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();

  // State for Outlook integration
  const [outlookStatus, setOutlookStatus] = useState<IntegrationStatus | null>(null);
  const [outlookLoading, setOutlookLoading] = useState(true);
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

  // Fetch integration statuses
  useEffect(() => {
    const fetchStatuses = async () => {
      try {
        const outlookRes = await authFetch('/api/integrations/outlook/status');
        if (outlookRes.ok) {
          const data = await outlookRes.json();
          setOutlookStatus(data);
        }
      } catch (error) {
        console.error('[Settings] Error fetching Outlook status:', error);
      } finally {
        setOutlookLoading(false);
      }
    };

    fetchStatuses();
  }, []);

  // Handle OAuth callback
  useEffect(() => {
    const connected = searchParams.get('connected');
    const error = searchParams.get('error');

    if (connected === 'outlook') {
      setOutlookLoading(true);
      authFetch('/api/integrations/outlook/status')
        .then(res => res.json())
        .then(data => setOutlookStatus(data))
        .finally(() => setOutlookLoading(false));
      router.replace('/settings');
    }

    if (error) {
      console.error('[Settings] OAuth error:', error);
      router.replace('/settings');
    }
  }, [searchParams, router]);

  // Connect to Outlook
  const handleConnectOutlook = async () => {
    setConnectingOutlook(true);
    try {
      const res = await authFetch('/api/integrations/outlook/auth-url');
      const data = await res.json();
      if (data.url) {
        window.location.href = data.url;
      }
    } catch (error) {
      console.error('[Settings] Error getting Outlook auth URL:', error);
      setConnectingOutlook(false);
    }
  };

  // Disconnect from Outlook
  const handleDisconnectOutlook = async () => {
    if (!confirm('Disconnect your Outlook account?')) return;

    setOutlookLoading(true);
    try {
      await authFetch('/api/integrations/outlook/disconnect', { method: 'POST' });
      setOutlookStatus({ connected: false });
    } catch (error) {
      console.error('[Settings] Error disconnecting Outlook:', error);
    } finally {
      setOutlookLoading(false);
    }
  };

  // Open support email
  const handleOpenSupport = () => {
    window.location.href = 'mailto:support@celeste7.ai?subject=CelesteOS Support Request';
  };

  // Close settings (go back to search)
  const handleClose = () => {
    router.push('/search');
  };

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
                  disabled={connectingOutlook}
                  className="px-3 py-1.5 text-xs bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50 transition-colors"
                >
                  {connectingOutlook ? 'Connecting...' : 'Connect'}
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
