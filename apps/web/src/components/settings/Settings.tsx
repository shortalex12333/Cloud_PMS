'use client';

/**
 * Settings - CelesteOS Settings Modal
 *
 * Frosted glass modal matching c.os.4.1 reference:
 * - Dark frosted sidebar with white text
 * - White content pane with dark text
 * - Clean, minimal form rows
 */

import React, { useState, useEffect } from 'react';
import { X, User, Mail, HardDrive, FileText, Palette, HelpCircle, Lock } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuth } from '@/hooks/useAuth';

// ============================================================================
// TYPES
// ============================================================================

interface SettingsProps {
  isOpen: boolean;
  onClose: () => void;
}

type SettingsPage = 'general' | 'account' | 'email' | 'nas' | 'handover' | 'appearance' | 'help';

const navigationItems: { id: SettingsPage; label: string; icon: typeof User }[] = [
  { id: 'general', label: 'General', icon: User },
  { id: 'account', label: 'Account', icon: User },
  { id: 'email', label: 'Email Connector', icon: Mail },
  { id: 'nas', label: 'NAS Access', icon: HardDrive },
  { id: 'handover', label: 'Handover', icon: FileText },
  { id: 'appearance', label: 'Appearance', icon: Palette },
  { id: 'help', label: 'Help & Support', icon: HelpCircle },
];

// ============================================================================
// COMPONENT
// ============================================================================

export default function Settings({ isOpen, onClose }: SettingsProps) {
  const { user, logout } = useAuth();

  const [activePage, setActivePage] = useState<SettingsPage>('general');
  const [displayName, setDisplayName] = useState(user?.displayName || '');
  const [appearance, setAppearance] = useState<'light' | 'dark' | 'system'>('light');
  const [dateRange, setDateRange] = useState<'today' | '7d' | '30d' | '60d'>('30d');

  // Contact form
  const [contactCategory, setContactCategory] = useState('general');
  const [contactSubject, setContactSubject] = useState('');
  const [contactMessage, setContactMessage] = useState('');
  const [sending, setSending] = useState(false);

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

  const handleSendMessage = async () => {
    if (!contactSubject.trim() || !contactMessage.trim()) return;
    setSending(true);
    try {
      await new Promise((r) => setTimeout(r, 1500));
      alert('Message sent to support team.');
      setContactSubject('');
      setContactMessage('');
    } catch {
      alert('Failed to send. Try again.');
    } finally {
      setSending(false);
    }
  };

  const handleExportHandover = async () => {
    alert(`Handover report (${dateRange}) will be sent to ${user?.email}`);
  };

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
              <div>
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

            <div className="settings-section-divider">
              <h3 className="settings-section-title">About</h3>
            </div>

            <div className="settings-form-row">
              <div className="settings-label">Application</div>
              <div className="settings-value">CelesteOS</div>
            </div>

            <div className="settings-form-row">
              <div className="settings-label">Version</div>
              <div className="settings-value">1.0.0</div>
            </div>

            <div className="settings-form-row">
              <div className="settings-label">Copyright</div>
              <div className="settings-value-muted">© 2025 Celeste7 LTD. All rights reserved.</div>
            </div>
          </>
        );

      case 'account':
        return (
          <>
            <h2 className="settings-content-title">Account</h2>

            <div className="settings-form-row">
              <div className="settings-label">Email</div>
              <div className="settings-value">{user?.email || 'user@example.com'}</div>
            </div>

            <div className="settings-form-row">
              <div>
                <div className="settings-label">Department</div>
                <div className="settings-helper">Read-only setting.</div>
              </div>
              <div className="settings-value-locked">
                <span>{user?.role?.replace('_', ' ') || 'Captain'}</span>
                <Lock className="w-4 h-4 text-slate-400" />
              </div>
            </div>

            <div className="settings-form-row">
              <div>
                <div className="settings-label">Role</div>
                <div className="settings-helper">Managed by admin.</div>
              </div>
              <div className="settings-value-locked">
                <span>Crew</span>
                <Lock className="w-4 h-4 text-slate-400" />
              </div>
            </div>

            <div className="mt-6">
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

      case 'email':
        return (
          <>
            <h2 className="settings-content-title">Email Connector</h2>

            <div className="settings-form-row">
              <div>
                <div className="settings-label">Mailbox</div>
                <div className="settings-helper">You only see your mailbox.</div>
              </div>
              <div className="settings-value">{user?.email || 'user@example.com'}</div>
            </div>

            <div className="mt-6">
              <button className="settings-button-primary">Connect Outlook</button>
            </div>
          </>
        );

      case 'nas':
        return (
          <>
            <h2 className="settings-content-title">NAS Access</h2>

            <div className="settings-form-row">
              <div>
                <div className="settings-label">Scope</div>
                <div className="settings-helper">You are restricted to this folder.</div>
              </div>
              <div className="settings-value-locked">
                <span>/02_engineering</span>
                <Lock className="w-4 h-4 text-slate-400" />
              </div>
            </div>
          </>
        );

      case 'handover':
        return (
          <>
            <h2 className="settings-content-title">Handover</h2>

            <div className="settings-form-row">
              <div>
                <div className="settings-label">Date Range</div>
                <div className="settings-helper">Period to include in export.</div>
              </div>
              <div className="settings-pills">
                {(['today', '7d', '30d', '60d'] as const).map((range) => (
                  <button
                    key={range}
                    onClick={() => setDateRange(range)}
                    className={cn('settings-pill', dateRange === range && 'settings-pill-active')}
                  >
                    {range === 'today' ? 'Today' : range === '7d' ? '7 days' : range === '30d' ? '30 days' : '60 days'}
                  </button>
                ))}
              </div>
            </div>

            <div className="mt-6">
              <button onClick={handleExportHandover} className="settings-button-primary">
                Send to my email
              </button>
              <div className="settings-helper mt-2">Will be sent to {user?.email}</div>
            </div>
          </>
        );

      case 'appearance':
        return (
          <>
            <h2 className="settings-content-title">Appearance</h2>

            <div className="settings-form-row">
              <div>
                <div className="settings-label">Appearance</div>
                <div className="settings-helper">Applies across the app.</div>
              </div>
              <div className="settings-toggle-group">
                {(['light', 'dark', 'system'] as const).map((opt) => (
                  <button
                    key={opt}
                    onClick={() => setAppearance(opt)}
                    className={cn('settings-toggle', appearance === opt && 'settings-toggle-active')}
                  >
                    {opt.charAt(0).toUpperCase() + opt.slice(1)}
                  </button>
                ))}
              </div>
            </div>

            <div className="settings-form-row">
              <div>
                <div className="settings-label">Language</div>
                <div className="settings-helper">Applies immediately to menus and messages.</div>
              </div>
              <select className="settings-select">
                <option>Auto-detect (English)</option>
                <option>English</option>
                <option>Spanish</option>
                <option>French</option>
              </select>
            </div>
          </>
        );

      case 'help':
        return (
          <>
            <h2 className="settings-content-title">Contact Support</h2>

            <div className="settings-form-row">
              <div>
                <div className="settings-label">Category</div>
                <div className="settings-helper">What type of request is this?</div>
              </div>
              <select
                value={contactCategory}
                onChange={(e) => setContactCategory(e.target.value)}
                className="settings-select"
              >
                <option value="general">General Question</option>
                <option value="bug">Bug Report</option>
                <option value="feature">Feature Request</option>
              </select>
            </div>

            <div className="settings-form-row">
              <div>
                <div className="settings-label">Subject *</div>
                <div className="settings-helper">Brief description of your request</div>
              </div>
              <input
                type="text"
                value={contactSubject}
                onChange={(e) => setContactSubject(e.target.value)}
                placeholder="Enter subject..."
                className="settings-input settings-input-wide"
              />
            </div>

            <div className="settings-form-row items-start">
              <div>
                <div className="settings-label">Message *</div>
                <div className="settings-helper">Provide details about your request</div>
              </div>
              <textarea
                value={contactMessage}
                onChange={(e) => setContactMessage(e.target.value)}
                placeholder="Type your message here..."
                rows={6}
                className="settings-textarea"
              />
            </div>

            <div className="mt-6 flex gap-3">
              <button
                onClick={() => {
                  setContactSubject('');
                  setContactMessage('');
                }}
                className="settings-button-secondary"
              >
                Cancel
              </button>
              <button
                onClick={handleSendMessage}
                disabled={!contactSubject.trim() || !contactMessage.trim() || sending}
                className="settings-button-primary"
              >
                {sending ? 'Sending...' : 'Send'}
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
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <div className="settings-modal" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="settings-header">
          <h1 className="settings-header-title">Settings</h1>
          <button onClick={onClose} className="settings-close-button">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="settings-body">
          {/* Sidebar - Dark frosted glass */}
          <div className="settings-sidebar">
            <div className="settings-nav-label">NAVIGATION</div>
            {navigationItems.map((item) => {
              const Icon = item.icon;
              const isActive = activePage === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActivePage(item.id)}
                  className={cn('settings-nav-item', isActive && 'settings-nav-item-active')}
                >
                  <Icon className="w-[18px] h-[18px]" />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </div>

          {/* Content - White pane */}
          <div className="settings-content">{renderContent()}</div>
        </div>
      </div>
    </div>
  );
}
