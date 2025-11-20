/**
 * Settings Page - /settings
 * Provides UI for managing third-party integrations (Outlook, etc.)
 */

'use client';

import { useAuth } from '@/hooks/useAuth';
import { useOutlookIntegration } from '@/hooks/useOutlookIntegration';

export default function SettingsPage() {
  const { user, loading: authLoading } = useAuth();
  const {
    status,
    loading: outlookLoading,
    error,
    connectOutlook,
    disconnectOutlook,
  } = useOutlookIntegration(user?.id);

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-lg">Loading...</div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-lg">Please log in to access settings</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto">
        <div className="bg-white shadow rounded-lg">
          {/* Header */}
          <div className="px-6 py-5 border-b border-gray-200">
            <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
            <p className="mt-1 text-sm text-gray-500">
              Manage your integrations and preferences
            </p>
          </div>

          {/* Integrations Section */}
          <div className="px-6 py-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">
              Integrations
            </h2>

            {/* Outlook Integration */}
            <div className="border border-gray-200 rounded-lg p-4">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center">
                    <h3 className="text-base font-medium text-gray-900">
                      Microsoft Outlook
                    </h3>
                    {status?.connected && (
                      <span className="ml-3 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                        Connected ✓
                      </span>
                    )}
                  </div>
                  <p className="mt-1 text-sm text-gray-500">
                    Connect your Outlook account to enable email integration and handover generation
                  </p>

                  {/* Connection Details */}
                  {status?.connected && (
                    <div className="mt-3 space-y-1">
                      {status.provider_email && (
                        <p className="text-sm text-gray-600">
                          <span className="font-medium">Email:</span> {status.provider_email}
                        </p>
                      )}
                      {status.display_name && (
                        <p className="text-sm text-gray-600">
                          <span className="font-medium">Name:</span> {status.display_name}
                        </p>
                      )}
                      {status.connected_at && (
                        <p className="text-sm text-gray-600">
                          <span className="font-medium">Connected:</span>{' '}
                          {new Date(status.connected_at).toLocaleDateString()}
                        </p>
                      )}
                    </div>
                  )}

                  {/* Error Display */}
                  {error && (
                    <div className="mt-3 rounded-md bg-red-50 p-3">
                      <p className="text-sm text-red-700">{error}</p>
                    </div>
                  )}
                </div>

                <div className="ml-6">
                  {outlookLoading ? (
                    <div className="text-sm text-gray-500">Loading...</div>
                  ) : status?.connected ? (
                    <button
                      onClick={disconnectOutlook}
                      className="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                    >
                      Disconnect
                    </button>
                  ) : (
                    <button
                      onClick={connectOutlook}
                      className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                    >
                      Connect Outlook
                    </button>
                  )}
                </div>
              </div>
            </div>

            {/* Future integrations can be added here */}
            <div className="mt-4 border border-dashed border-gray-300 rounded-lg p-4 text-center text-gray-500 text-sm">
              More integrations coming soon...
            </div>
          </div>

          {/* User Info Section (Optional) */}
          <div className="px-6 py-6 border-t border-gray-200">
            <h2 className="text-lg font-medium text-gray-900 mb-4">
              Account
            </h2>
            <div className="space-y-2">
              <p className="text-sm text-gray-600">
                <span className="font-medium">User ID:</span> {user.id}
              </p>
              {user.email && (
                <p className="text-sm text-gray-600">
                  <span className="font-medium">Email:</span> {user.email}
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
