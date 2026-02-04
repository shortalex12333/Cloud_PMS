'use client';

/**
 * SettingsModal
 * System settings interface
 * Brand tokens: CelesteOS color palette
 */

import { X, Settings, Mail, Loader2 } from 'lucide-react';
import { useState, useEffect, useCallback } from 'react';
import { cn } from '@/lib/utils';
import { useAuthSession, waitForSession } from '@/hooks/useAuthSession';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const [activeTab, setActiveTab] = useState<'general' | 'notifications' | 'users' | 'integrations'>('general');
  const [outlookStatus, setOutlookStatus] = useState<'loading' | 'connected' | 'disconnected'>('loading');
  const [isConnecting, setIsConnecting] = useState(false);

  // Use auth session hook to get valid access token
  const { accessToken, isReady } = useAuthSession();

  const checkOutlookStatus = useCallback(async () => {
    try {
      // Wait for token if not ready
      let token = accessToken;
      if (!token) {
        console.log('[SettingsModal] No token yet, waiting for session...');
        token = await waitForSession(5000);
      }

      if (!token) {
        console.error('[SettingsModal] No auth token available');
        setOutlookStatus('disconnected');
        return;
      }

      console.log('[SettingsModal] Checking Outlook status with token...');
      const response = await fetch('/api/integrations/outlook/status', {
        headers: { Authorization: `Bearer ${token}` },
      });
      console.log('[SettingsModal] Status response:', response.status);

      if (response.ok) {
        const data = await response.json();
        console.log('[SettingsModal] Status data:', data);
        setOutlookStatus(data.connected ? 'connected' : 'disconnected');
      } else {
        const errorText = await response.text();
        console.error('[SettingsModal] Status error:', response.status, errorText);
        setOutlookStatus('disconnected');
      }
    } catch (error) {
      console.error('[SettingsModal] checkOutlookStatus failed:', error);
      setOutlookStatus('disconnected');
    }
  }, [accessToken]);

  // Check OAuth status when integrations tab is active AND auth is ready
  useEffect(() => {
    if (isOpen && activeTab === 'integrations' && isReady) {
      checkOutlookStatus();
    }
  }, [isOpen, activeTab, isReady, checkOutlookStatus]);

  const handleConnectOutlook = async () => {
    setIsConnecting(true);
    try {
      // Wait for token if not ready
      let token = accessToken;
      if (!token) {
        console.log('[SettingsModal] Connect: No token yet, waiting...');
        token = await waitForSession(5000);
      }

      if (!token) {
        console.error('[SettingsModal] Connect: No auth token available');
        setIsConnecting(false);
        return;
      }

      console.log('[SettingsModal] Connect: Requesting auth-url...');
      const response = await fetch('/api/integrations/outlook/auth-url', {
        headers: {
          Authorization: `Bearer ${token}`,
          'Cache-Control': 'no-cache',
        },
      });
      console.log('[SettingsModal] auth-url response:', response.status);

      if (response.ok) {
        const data = await response.json();
        console.log('[SettingsModal] Got OAuth URL, redirecting...');
        if (data.url) {
          window.location.href = data.url;
        }
      } else {
        const errorText = await response.text();
        console.error('[SettingsModal] Failed to get OAuth URL:', response.status, errorText);
      }
    } catch (error) {
      console.error('[SettingsModal] Connect error:', error);
    }
    setIsConnecting(false);
  };

  const handleDisconnectOutlook = async () => {
    try {
      let token = accessToken;
      if (!token) {
        token = await waitForSession(5000);
      }
      if (!token) {
        console.error('[SettingsModal] Disconnect: No auth token');
        return;
      }

      const response = await fetch('/api/integrations/outlook/disconnect', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        setOutlookStatus('disconnected');
      }
    } catch (error) {
      console.error('[SettingsModal] Disconnect error:', error);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center font-body">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-2xl bg-celeste-bg-secondary border border-celeste-border rounded-celeste-lg shadow-celeste-xl mx-4 max-h-[80vh] overflow-hidden">
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
            <button
              onClick={() => setActiveTab('general')}
              className={cn(
                'py-3 border-b-2 transition-colors',
                activeTab === 'general'
                  ? 'border-celeste-blue font-medium text-celeste-text-primary'
                  : 'border-transparent text-celeste-text-muted hover:text-celeste-text-primary'
              )}
            >
              General
            </button>
            <button
              onClick={() => setActiveTab('notifications')}
              className={cn(
                'py-3 border-b-2 transition-colors',
                activeTab === 'notifications'
                  ? 'border-celeste-blue font-medium text-celeste-text-primary'
                  : 'border-transparent text-celeste-text-muted hover:text-celeste-text-primary'
              )}
            >
              Notifications
            </button>
            <button
              onClick={() => setActiveTab('users')}
              className={cn(
                'py-3 border-b-2 transition-colors',
                activeTab === 'users'
                  ? 'border-celeste-blue font-medium text-celeste-text-primary'
                  : 'border-transparent text-celeste-text-muted hover:text-celeste-text-primary'
              )}
            >
              Users
            </button>
            <button
              onClick={() => setActiveTab('integrations')}
              className={cn(
                'py-3 border-b-2 transition-colors',
                activeTab === 'integrations'
                  ? 'border-celeste-blue font-medium text-celeste-text-primary'
                  : 'border-transparent text-celeste-text-muted hover:text-celeste-text-primary'
              )}
            >
              Integrations
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(80vh-180px)]">
          {activeTab === 'general' && (
            <div className="space-y-4">
              <div>
                <label className="block text-celeste-sm font-medium text-celeste-text-primary mb-2">
                  Yacht Name
                </label>
                <input
                  type="text"
                  placeholder="M/Y Example"
                  className="w-full px-4 py-2 bg-celeste-bg-primary border border-celeste-border rounded-celeste-md text-celeste-text-primary placeholder:text-celeste-text-disabled focus:outline-none focus:border-celeste-blue transition-colors"
                />
              </div>
              <div>
                <label className="block text-celeste-sm font-medium text-celeste-text-primary mb-2">
                  Theme
                </label>
                <select className="w-full px-4 py-2 bg-celeste-bg-primary border border-celeste-border rounded-celeste-md text-celeste-text-primary focus:outline-none focus:border-celeste-blue transition-colors">
                  <option>Light</option>
                  <option>Dark</option>
                  <option>System</option>
                </select>
              </div>
            </div>
          )}

          {activeTab === 'notifications' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-celeste-sm text-celeste-text-primary">Email notifications</span>
                <input type="checkbox" defaultChecked className="accent-celeste-blue" />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-celeste-sm text-celeste-text-primary">Predictive alerts</span>
                <input type="checkbox" defaultChecked className="accent-celeste-blue" />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-celeste-sm text-celeste-text-primary">Work order reminders</span>
                <input type="checkbox" defaultChecked className="accent-celeste-blue" />
              </div>
            </div>
          )}

          {activeTab === 'users' && (
            <div className="space-y-4">
              <p className="text-celeste-sm text-celeste-text-muted">
                User management (HOD only)
              </p>
              <button className="px-4 py-2 bg-celeste-blue text-celeste-white rounded-celeste-md hover:bg-celeste-blue-secondary transition-colors">
                Add User
              </button>
            </div>
          )}

          {activeTab === 'integrations' && (
            <div className="space-y-6">
              {/* Microsoft Outlook Integration */}
              <div className="p-4 bg-celeste-bg-primary border border-celeste-border rounded-celeste-md">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-[#0078D4] rounded-celeste-sm">
                      <Mail className="h-5 w-5 text-white" />
                    </div>
                    <div>
                      <h3 className="text-celeste-base font-medium text-celeste-text-primary">
                        Microsoft Outlook
                      </h3>
                      <p className="text-celeste-sm text-celeste-text-muted">
                        {outlookStatus === 'connected'
                          ? 'Email sync enabled'
                          : 'Connect to sync emails with CelesteOS'}
                      </p>
                    </div>
                  </div>
                  <div>
                    {outlookStatus === 'loading' ? (
                      <div className="px-4 py-2">
                        <Loader2 className="h-5 w-5 animate-spin text-celeste-text-muted" />
                      </div>
                    ) : outlookStatus === 'connected' ? (
                      <button
                        onClick={handleDisconnectOutlook}
                        className="px-4 py-2 bg-red-600 text-white rounded-celeste-md hover:bg-red-700 transition-colors"
                        data-testid="disconnect-outlook"
                      >
                        Disconnect
                      </button>
                    ) : (
                      <button
                        onClick={handleConnectOutlook}
                        disabled={isConnecting}
                        className="px-4 py-2 bg-celeste-blue text-celeste-white rounded-celeste-md hover:bg-celeste-blue-secondary transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        data-testid="connect-outlook"
                      >
                        {isConnecting ? (
                          <span className="flex items-center gap-2">
                            <Loader2 className="h-4 w-4 animate-spin" />
                            Connecting...
                          </span>
                        ) : (
                          'Connect'
                        )}
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
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 p-6 border-t border-celeste-border">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-celeste-bg-tertiary text-celeste-text-secondary rounded-celeste-md hover:bg-celeste-border transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-celeste-blue text-celeste-white rounded-celeste-md hover:bg-celeste-blue-secondary transition-colors"
          >
            Save Changes
          </button>
        </div>
      </div>
    </div>
  );
}
