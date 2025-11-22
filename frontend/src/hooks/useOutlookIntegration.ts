/**
 * Outlook Integration Hook
 * Provides Outlook connection status and auth flow
 * Adapted from c.os.4.1/client/services/outlookService.ts
 */

import { useState, useEffect, useCallback } from 'react';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://api.celeste7.ai/v1';

export interface OutlookStatus {
  connected: boolean;
  provider_email?: string;
  display_name?: string;
  connected_at?: string;
}

export function useOutlookIntegration(userId?: string) {
  const [status, setStatus] = useState<OutlookStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  /**
   * Fetch Outlook connection status
   * Calls backend: GET /api/v1/integrations/outlook/status
   */
  const fetchStatus = useCallback(async () => {
    if (!userId) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`${API_BASE_URL}/integrations/outlook/status`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          // Include auth token from Supabase session
          // Authorization header will be added by Supabase auth helper
        },
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch status: ${response.statusText}`);
      }

      const data: OutlookStatus = await response.json();
      setStatus(data);
    } catch (err) {
      console.error('Error fetching Outlook status:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
      setStatus({ connected: false });
    } finally {
      setLoading(false);
    }
  }, [userId]);

  /**
   * Start Microsoft OAuth flow
   * Adapted from c.os.4.1/client/services/outlookService.ts:startOutlookAuth()
   *
   * Opens Microsoft OAuth in popup window
   * Listens for success message from callback page
   */
  const connectOutlook = useCallback(async () => {
    if (!userId) {
      setError('User ID is required. Please ensure you are logged in.');
      return;
    }

    try {
      setError(null);

      // Step 1: Get auth URL from backend
      const response = await fetch(`${API_BASE_URL}/integrations/outlook/auth-url`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error(`Failed to get auth URL: ${response.statusText}`);
      }

      const data = await response.json();

      if (!data.auth_url) {
        throw new Error('No auth URL returned from server');
      }

      console.log('🚀 Opening Microsoft OAuth in new tab:', data.auth_url);

      // Step 2: Open Microsoft OAuth in popup
      const authWindow = window.open(
        data.auth_url,
        'microsoft-auth',
        'width=600,height=700,scrollbars=yes,resizable=yes'
      );

      if (!authWindow) {
        // Fallback: redirect in same window if popup blocked
        console.warn('Popup blocked, redirecting in same window');
        window.location.href = data.auth_url;
        return;
      }

      // Step 3: Listen for auth completion message
      const messageHandler = (event: MessageEvent) => {
        if (event.data?.type === 'MICROSOFT_AUTH_SUCCESS') {
          console.log('✅ Microsoft auth completed successfully');
          authWindow.close();
          window.removeEventListener('message', messageHandler);

          // Refresh status after successful auth
          fetchStatus();
        }
      };

      window.addEventListener('message', messageHandler);

      // Check if window was closed manually (user cancelled)
      const checkClosed = setInterval(() => {
        try {
          if (authWindow.closed) {
            clearInterval(checkClosed);
            window.removeEventListener('message', messageHandler);
            console.log('Auth window closed');
          }
        } catch (e) {
          // Ignore COOP errors
          console.log('COOP policy blocked window.closed check');
        }
      }, 1000);

    } catch (err) {
      console.error('❌ OAuth initiation failed:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  }, [userId, fetchStatus]);

  /**
   * Disconnect Outlook integration
   */
  const disconnectOutlook = useCallback(async () => {
    if (!userId) {
      setError('User ID is required');
      return;
    }

    try {
      setError(null);

      const response = await fetch(`${API_BASE_URL}/integrations/outlook/disconnect`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error(`Failed to disconnect: ${response.statusText}`);
      }

      console.log('✅ Outlook disconnected successfully');

      // Refresh status
      fetchStatus();
    } catch (err) {
      console.error('❌ Disconnect failed:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  }, [userId, fetchStatus]);

  // Fetch status on mount
  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  return {
    status,
    loading,
    error,
    connectOutlook,
    disconnectOutlook,
    refreshStatus: fetchStatus,
  };
}
