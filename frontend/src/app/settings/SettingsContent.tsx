'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { withAuth } from '@/components/withAuth';
import { supabase } from '@/lib/supabaseClient';
import Link from 'next/link';

// Integration status type
interface IntegrationStatus {
  connected: boolean;
  email?: string;
  connectedAt?: string;
}

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

  // Fetch integration statuses
  useEffect(() => {
    const fetchStatuses = async () => {
      try {
        // Fetch Outlook status
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

  // Handle success/error messages from OAuth callback
  useEffect(() => {
    const connected = searchParams.get('connected');
    const error = searchParams.get('error');

    if (connected === 'outlook') {
      setOutlookLoading(true);
      // Refresh Outlook status
      authFetch('/api/integrations/outlook/status')
        .then(res => res.json())
        .then(data => setOutlookStatus(data))
        .finally(() => setOutlookLoading(false));

      // Clean URL
      router.replace('/settings');
    }

    if (error) {
      console.error('[Settings] OAuth error:', error);
      // Clean URL
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
        // Redirect to Microsoft OAuth
        window.location.href = data.url;
      }
    } catch (error) {
      console.error('[Settings] Error getting Outlook auth URL:', error);
      setConnectingOutlook(false);
    }
  };

  // Disconnect from Outlook
  const handleDisconnectOutlook = async () => {
    if (!confirm('Are you sure you want to disconnect your Outlook account?')) {
      return;
    }

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

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-semibold">Settings</h1>
              <p className="text-sm text-muted-foreground mt-1">
                Manage your account and integrations
              </p>
            </div>
            <Link
              href="/search"
              className="px-4 py-2 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
            >
              ← Back to Search
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Account Info */}
        <div className="bg-card border border-border rounded-lg p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">Account Information</h2>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Name:</span>
              <span className="font-medium">{user?.displayName || 'N/A'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Email:</span>
              <span className="font-medium">{user?.email || 'N/A'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Role:</span>
              <span className="font-medium capitalize">{user?.role.replace('_', ' ')}</span>
            </div>
          </div>
        </div>

        {/* Account Integrations */}
        <div className="bg-card border border-border rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-6">Account Integrations</h2>

          <div className="space-y-6">
            {/* Microsoft Outlook */}
            <div>
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-medium">Microsoft Outlook</h3>
                    {outlookStatus?.connected && (
                      <span className="text-xs px-2 py-0.5 bg-green-500/10 text-green-600 rounded-full">
                        Connected
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground mb-3">
                    Connect your Outlook account to sync emails and calendar
                  </p>

                  {outlookStatus?.connected && outlookStatus.email && (
                    <p className="text-xs text-muted-foreground">
                      Connected as: <span className="font-medium">{outlookStatus.email}</span>
                    </p>
                  )}
                </div>

                <div className="ml-4">
                  {outlookLoading ? (
                    <div className="h-9 w-24 skeleton rounded-md" />
                  ) : outlookStatus?.connected ? (
                    <button
                      onClick={handleDisconnectOutlook}
                      className="px-4 py-2 text-sm border border-border rounded-md hover:bg-accent"
                    >
                      Disconnect
                    </button>
                  ) : (
                    <button
                      onClick={handleConnectOutlook}
                      disabled={connectingOutlook}
                      className="px-4 py-2 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50"
                    >
                      {connectingOutlook ? 'Connecting...' : 'Connect Outlook'}
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Logout */}
        <div className="mt-8 flex justify-end">
          <button
            onClick={logout}
            className="px-4 py-2 text-sm text-destructive hover:bg-destructive/10 rounded-md"
          >
            Logout
          </button>
        </div>
      </main>
    </div>
  );
}

// Export with authentication protection
export default withAuth(SettingsContent);
