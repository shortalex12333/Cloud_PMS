'use client';

/**
 * Settings - CelesteOS Settings Modal
 *
 * ChatGPT-style settings modal:
 * - 960px width, min(720px, calc(100vh - 96px)) height
 * - 280px left nav, flex right content
 * - Close button in sidebar (top-left)
 * - 8px grid spacing system
 */

import React, { useState, useEffect } from 'react';
import {
  X,
  Settings as SettingsIcon,
  Bell,
  User,
  Grid3X3,
  Calendar,
  Database,
  Shield,
  Users,
  CreditCard,
  Lock,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuth } from '@/hooks/useAuth';

// ============================================================================
// TYPES
// ============================================================================

interface SettingsProps {
  isOpen: boolean;
  onClose: () => void;
}

type SettingsPage = 'general' | 'notifications' | 'personalization' | 'apps' | 'schedules' | 'data' | 'security' | 'account';

const navigationItems: { id: SettingsPage; label: string; icon: typeof User }[] = [
  { id: 'general', label: 'General', icon: SettingsIcon },
  { id: 'notifications', label: 'Notifications', icon: Bell },
  { id: 'personalization', label: 'Personalization', icon: User },
  { id: 'apps', label: 'Apps', icon: Grid3X3 },
  { id: 'schedules', label: 'Schedules', icon: Calendar },
  { id: 'data', label: 'Data controls', icon: Database },
  { id: 'security', label: 'Security', icon: Shield },
  { id: 'account', label: 'Account', icon: CreditCard },
];

// ============================================================================
// COMPONENT
// ============================================================================

export default function Settings({ isOpen, onClose }: SettingsProps) {
  const { user, logout } = useAuth();

  const [activePage, setActivePage] = useState<SettingsPage>('general');
  const [displayName, setDisplayName] = useState(user?.displayName || '');
  const [appearance, setAppearance] = useState<'light' | 'dark' | 'system'>('light');
  const [language, setLanguage] = useState('auto');

  // Load theme from localStorage
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('celeste_theme') as 'light' | 'dark' | 'system' | null;
      if (saved) setAppearance(saved);
    }
  }, []);

  // Apply theme
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const root = document.documentElement;
    const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    if (appearance === 'dark' || (appearance === 'system' && systemDark)) {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
    localStorage.setItem('celeste_theme', appearance);
  }, [appearance]);

  // Sync display name
  useEffect(() => {
    if (user?.displayName) setDisplayName(user.displayName);
  }, [user?.displayName]);

  // Escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  // ============================================================================
  // RENDER PAGE CONTENT
  // ============================================================================

  const renderContent = () => {
    switch (activePage) {
      case 'general':
        return (
          <>
            <h2 className="settings-content-title">General</h2>

            <div className="settings-form-row">
              <div className="settings-label-group">
                <div className="settings-label">Appearance</div>
              </div>
              <select
                value={appearance}
                onChange={(e) => setAppearance(e.target.value as 'light' | 'dark' | 'system')}
                className="settings-select"
              >
                <option value="light">Light</option>
                <option value="dark">Dark</option>
                <option value="system">System</option>
              </select>
            </div>

            <div className="settings-form-row">
              <div className="settings-label-group">
                <div className="settings-label">Language</div>
              </div>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="settings-select"
              >
                <option value="auto">Auto-detect</option>
                <option value="en">English</option>
                <option value="es">Spanish</option>
                <option value="fr">French</option>
              </select>
            </div>

            <div className="settings-form-row">
              <div className="settings-label-group">
                <div className="settings-label">Display name</div>
                <div className="settings-helper">Shown in handovers and feedback.</div>
              </div>
              <input
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="Your name"
                className="settings-input"
              />
            </div>
          </>
        );

      case 'notifications':
        return (
          <>
            <h2 className="settings-content-title">Notifications</h2>

            <div className="settings-form-row">
              <div className="settings-label-group">
                <div className="settings-label">Email notifications</div>
                <div className="settings-helper">Receive updates about activity.</div>
              </div>
              <select className="settings-select">
                <option>All</option>
                <option>Important only</option>
                <option>None</option>
              </select>
            </div>

            <div className="settings-form-row">
              <div className="settings-label-group">
                <div className="settings-label">Desktop notifications</div>
                <div className="settings-helper">Show alerts on your device.</div>
              </div>
              <select className="settings-select">
                <option>Enabled</option>
                <option>Disabled</option>
              </select>
            </div>
          </>
        );

      case 'personalization':
        return (
          <>
            <h2 className="settings-content-title">Personalization</h2>

            <div className="settings-form-row">
              <div className="settings-label-group">
                <div className="settings-label">Memory</div>
                <div className="settings-helper">Allow system to remember preferences.</div>
              </div>
              <select className="settings-select">
                <option>Enabled</option>
                <option>Disabled</option>
              </select>
            </div>
          </>
        );

      case 'apps':
        return (
          <>
            <h2 className="settings-content-title">Apps</h2>

            <div className="settings-form-row">
              <div className="settings-label-group">
                <div className="settings-label">Connected apps</div>
                <div className="settings-helper">Manage third-party integrations.</div>
              </div>
              <button className="settings-button-secondary">Manage</button>
            </div>
          </>
        );

      case 'schedules':
        return (
          <>
            <h2 className="settings-content-title">Schedules</h2>

            <div className="settings-form-row">
              <div className="settings-label-group">
                <div className="settings-label">Scheduled tasks</div>
                <div className="settings-helper">Automated actions and reminders.</div>
              </div>
              <button className="settings-button-secondary">View all</button>
            </div>
          </>
        );

      case 'data':
        return (
          <>
            <h2 className="settings-content-title">Data controls</h2>

            <div className="settings-form-row">
              <div className="settings-label-group">
                <div className="settings-label">NAS scope</div>
                <div className="settings-helper">You are restricted to this folder.</div>
              </div>
              <div className="settings-value-locked">
                <span>/02_engineering</span>
                <Lock className="settings-nav-icon" />
              </div>
            </div>

            <div className="settings-form-row">
              <div className="settings-label-group">
                <div className="settings-label">Export data</div>
                <div className="settings-helper">Download a copy of your data.</div>
              </div>
              <button className="settings-button-secondary">Export</button>
            </div>
          </>
        );

      case 'security':
        return (
          <>
            <h2 className="settings-content-title">Security</h2>

            <div className="settings-form-row">
              <div className="settings-label-group">
                <div className="settings-label">Two-factor authentication</div>
                <div className="settings-helper">Add an extra layer of security.</div>
              </div>
              <button className="settings-button-secondary">Set up</button>
            </div>

            <div className="settings-form-row">
              <div className="settings-label-group">
                <div className="settings-label">Active sessions</div>
                <div className="settings-helper">Manage devices where you're signed in.</div>
              </div>
              <button className="settings-button-secondary">View</button>
            </div>
          </>
        );

      case 'account':
        return (
          <>
            <h2 className="settings-content-title">Account</h2>

            <div className="settings-form-row">
              <div className="settings-label-group">
                <div className="settings-label">Email</div>
              </div>
              <div className="settings-value">{user?.email || 'user@example.com'}</div>
            </div>

            <div className="settings-form-row">
              <div className="settings-label-group">
                <div className="settings-label">Department</div>
                <div className="settings-helper">Read-only setting.</div>
              </div>
              <div className="settings-value-locked">
                <span>{user?.role?.replace('_', ' ') || 'Captain'}</span>
                <Lock className="settings-nav-icon" />
              </div>
            </div>

            <div className="settings-form-row">
              <div className="settings-label-group">
                <div className="settings-label">Role</div>
                <div className="settings-helper">Managed by admin.</div>
              </div>
              <div className="settings-value-locked">
                <span>Crew</span>
                <Lock className="settings-nav-icon" />
              </div>
            </div>

            <div className="settings-section-divider" />

            <div className="settings-form-row">
              <div className="settings-label-group">
                <div className="settings-label">Sign out</div>
                <div className="settings-helper">Sign out of your account on this device.</div>
              </div>
              <button
                onClick={async () => {
                  try {
                    if (logout) await logout();
                  } catch {
                    localStorage.clear();
                    window.location.reload();
                  }
                }}
                className="settings-button-danger"
              >
                Sign out
              </button>
            </div>
          </>
        );

      default:
        return null;
    }
  };

  // ============================================================================
  // MAIN RENDER
  // ============================================================================

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0"
        style={{ background: 'rgba(0,0,0,0.35)' }}
        onClick={onClose}
      />

      {/* Modal - 547x483 (matching ChatGPT) */}
      <div
        className="settings-modal"
        style={{
          width: '547px',
          height: '483px',
          maxWidth: 'calc(100vw - 48px)',
          maxHeight: 'calc(100vh - 48px)',
          borderRadius: '16px',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'row',
          background: 'var(--settings-bg-main, #ffffff)',
          border: '1px solid var(--settings-border, #e7e7e7)',
          boxShadow: '0 24px 64px rgba(0,0,0,0.18), 0 2px 8px rgba(0,0,0,0.08)',
          fontFamily: 'ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Sidebar - 180px */}
        <div
          className="settings-sidebar"
          style={{
            width: '180px',
            flexShrink: 0,
            background: 'var(--settings-bg-left, #f8f8f8)',
            borderRight: '1px solid var(--settings-border, #e7e7e7)',
            padding: '12px',
            overflowY: 'auto',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          {/* Close button - 28x28 */}
          <button
            onClick={onClose}
            className="settings-close-button"
            style={{
              width: '28px',
              height: '28px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              background: 'transparent',
              border: 'none',
              borderRadius: '6px',
              color: 'var(--settings-text-secondary, #5a5a5a)',
              cursor: 'pointer',
              marginBottom: '12px',
              marginLeft: '-4px',
            }}
          >
            <X style={{ width: '18px', height: '18px' }} />
          </button>

          {/* Navigation */}
          <nav style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {navigationItems.map((item) => {
              const Icon = item.icon;
              const isActive = activePage === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActivePage(item.id)}
                  style={{
                    width: '100%',
                    height: '36px',
                    borderRadius: '8px',
                    padding: '0 10px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    fontSize: '13px',
                    fontWeight: isActive ? 600 : 500,
                    lineHeight: '20px',
                    color: 'var(--settings-text-primary, #111111)',
                    background: isActive ? 'var(--settings-bg-highlight, #eeeeee)' : 'transparent',
                    border: 'none',
                    cursor: 'pointer',
                    textAlign: 'left',
                  }}
                >
                  <Icon style={{ width: '16px', height: '16px', flexShrink: 0, color: 'var(--settings-text-secondary, #5a5a5a)' }} />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>
        </div>

        {/* Content - 32px LR, 28px top, 24px bottom */}
        <div
          className="settings-content"
          style={{
            flex: 1,
            background: 'var(--settings-bg-center, #f8f8f8)',
            padding: '20px 24px 20px',
            overflowY: 'auto',
          }}
        >
          {renderContent()}
        </div>
      </div>
    </div>
  );
}
