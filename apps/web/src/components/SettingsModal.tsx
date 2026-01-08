'use client';

/**
 * SettingsModal
 * System settings interface
 * Brand tokens: CelesteOS color palette
 */

import { X, Settings } from 'lucide-react';
import { useState } from 'react';
import { cn } from '@/lib/utils';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const [activeTab, setActiveTab] = useState<'general' | 'notifications' | 'users'>('general');

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
