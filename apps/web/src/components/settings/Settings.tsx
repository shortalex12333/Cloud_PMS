'use client';

/**
 * Settings — CelesteOS Settings Modal
 *
 * Pixel-matched to settings-v4.html prototype.
 * 547×483px modal, 42px header, 168px sidebar, flex content.
 * All styles inline using design tokens — zero Tailwind dependency.
 */

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/hooks/useAuth';

// ============================================================================
// TYPES
// ============================================================================

interface SettingsProps {
  isOpen: boolean;
  onClose: () => void;
}

type SettingsPage = 'account' | 'security' | 'apps' | 'data' | 'help' | 'about';

const PAGE_TITLES: Record<SettingsPage, string> = {
  account: 'Account',
  security: 'Security',
  apps: 'Apps',
  data: 'Data',
  help: 'Help',
  about: 'About',
};

// ============================================================================
// SVG ICONS (matching prototype v4 — 13×13 inline SVGs)
// ============================================================================

const NavIcons: Record<SettingsPage | 'signout', React.ReactNode> = {
  account: (
    <svg width="13" height="13" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.35">
      <circle cx="7" cy="5" r="2.5" /><path d="M2.5 12c0-2.5 2-4 4.5-4s4.5 1.5 4.5 4" strokeLinecap="round" />
    </svg>
  ),
  security: (
    <svg width="13" height="13" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.35">
      <path d="M7 2L11.5 4v4c0 3-2.2 4.5-4.5 5.2C4.7 12.5 2.5 11 2.5 8V4L7 2z" />
    </svg>
  ),
  apps: (
    <svg width="13" height="13" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.35">
      <rect x="2.5" y="2.5" width="4" height="4" rx="1" /><rect x="7.5" y="2.5" width="4" height="4" rx="1" />
      <rect x="2.5" y="7.5" width="4" height="4" rx="1" /><rect x="7.5" y="7.5" width="4" height="4" rx="1" />
    </svg>
  ),
  data: (
    <svg width="13" height="13" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.35">
      <ellipse cx="7" cy="4" rx="4.5" ry="1.8" />
      <path d="M2.5 4v3c0 1 2 1.8 4.5 1.8S11.5 8 11.5 7V4" strokeLinecap="round" />
      <path d="M2.5 7v3c0 1 2 1.8 4.5 1.8S11.5 11 11.5 10V7" strokeLinecap="round" />
    </svg>
  ),
  help: (
    <svg width="13" height="13" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.35">
      <circle cx="7" cy="7" r="5" /><path d="M7 6v.5a1.5 1.5 0 000 3" strokeLinecap="round" />
      <circle cx="7" cy="10.5" r=".6" fill="currentColor" />
    </svg>
  ),
  about: (
    <svg width="13" height="13" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.35">
      <circle cx="7" cy="7" r="5" /><path d="M7 6.5V10M7 4.5v.5" strokeLinecap="round" strokeWidth="1.6" />
    </svg>
  ),
  signout: (
    <svg width="13" height="13" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.35" strokeLinecap="round">
      <path d="M5.5 2H3a1 1 0 00-1 1v8a1 1 0 001 1h2.5M9 9.5L11.5 7 9 4.5M11.5 7H5.5" />
    </svg>
  ),
};

const ExternalLinkIcon = (
  <svg width="11" height="11" viewBox="0 0 11 11" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round">
    <path d="M4.5 2H2a1 1 0 00-1 1v6a1 1 0 001 1h6a1 1 0 001-1V6.5M7 1h3v3M10 1L5.5 5.5" />
  </svg>
);

// ============================================================================
// NAV ORDER (prototype v4)
// ============================================================================

const navItems: SettingsPage[] = ['account', 'security', 'apps', 'data', 'help', 'about'];

// ============================================================================
// COMPONENT
// ============================================================================

export default function Settings({ isOpen, onClose }: SettingsProps) {
  const { user, logout } = useAuth();

  const [activePage, setActivePage] = useState<SettingsPage>('account');
  const [appearance, setAppearance] = useState<'light' | 'dark' | 'system'>('dark');
  const [themeLoaded, setThemeLoaded] = useState(false);
  const [supportMessage, setSupportMessage] = useState('');
  const [integrationRequest, setIntegrationRequest] = useState('');

  // Load theme from localStorage
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('celeste_theme') as 'light' | 'dark' | 'system' | null;
      if (saved) setAppearance(saved);
      setThemeLoaded(true);
    }
  }, []);

  // Apply theme
  useEffect(() => {
    if (typeof window === 'undefined' || !themeLoaded) return;
    const root = document.documentElement;
    const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    if (appearance === 'dark' || (appearance === 'system' && systemDark)) {
      root.setAttribute('data-theme', 'dark');
      root.classList.add('dark');
    } else {
      root.setAttribute('data-theme', 'light');
      root.classList.remove('dark');
    }
    localStorage.setItem('celeste_theme', appearance);
  }, [appearance, themeLoaded]);

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
  // SHARED INLINE STYLES (prototype v4 exact values)
  // ============================================================================

  const s = {
    // Section label: 9px uppercase ghost
    sect: {
      fontSize: '9px', fontWeight: 600, letterSpacing: '0.12em',
      textTransform: 'uppercase' as const, color: 'var(--txt-ghost)',
      marginBottom: '5px', paddingLeft: '2px',
    } as React.CSSProperties,
    // Row group container (iOS-style)
    rg: {
      borderTop: '1px solid var(--settings-modal-border-t)',
      borderRight: '1px solid var(--settings-modal-border-s)',
      borderBottom: '1px solid var(--settings-modal-border-b)',
      borderLeft: '1px solid var(--settings-modal-border-s)',
      borderRadius: '5px', overflow: 'hidden' as const,
      background: 'var(--surface)', marginBottom: '14px',
    } as React.CSSProperties,
    // Row inside group
    row: {
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '9px 12px', gap: '12px', minHeight: '38px',
      transition: 'background 60ms', cursor: 'pointer',
    } as React.CSSProperties,
    rowNoHover: {
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '9px 12px', gap: '12px', minHeight: '38px', cursor: 'default',
    } as React.CSSProperties,
    rowDivider: { borderTop: '1px solid var(--border-sub)' } as React.CSSProperties,
    rowLabel: { fontSize: '12.5px', color: 'var(--txt2)', flexShrink: 0 } as React.CSSProperties,
    rowValue: { fontSize: '11px', color: 'var(--txt3)', textAlign: 'right' as const, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' as const } as React.CSSProperties,
    rowValueMono: { fontSize: '11px', color: 'var(--txt3)', textAlign: 'right' as const, fontFamily: 'var(--font-mono)', letterSpacing: '0.02em', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' as const } as React.CSSProperties,
    rowLeft: { display: 'flex', flexDirection: 'column' as const, gap: '3px' } as React.CSSProperties,
    rowDesc: { fontSize: '11px', color: 'var(--txt3)' } as React.CSSProperties,
    // Badge
    badgeLock: {
      fontSize: '9px', fontWeight: 600, letterSpacing: '0.07em',
      textTransform: 'uppercase' as const, color: 'var(--txt-ghost)',
      background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)',
      borderRadius: '2px', padding: '1px 5px', flexShrink: 0,
    } as React.CSSProperties,
    // Buttons: 25px, 3px radius, 11px font
    btn: {
      height: '25px', padding: '0 10px', borderRadius: '3px',
      fontSize: '11px', fontWeight: 500, cursor: 'pointer',
      whiteSpace: 'nowrap' as const, display: 'inline-flex', alignItems: 'center', gap: '4px',
      fontFamily: 'var(--font-sans)', flexShrink: 0,
      borderTop: '1px solid var(--settings-modal-border-t)',
      borderRight: '1px solid var(--settings-modal-border-s)',
      borderBottom: '1px solid var(--settings-modal-border-b)',
      borderLeft: '1px solid var(--settings-modal-border-s)',
      background: 'var(--surface-hover)', color: 'var(--txt2)',
      transition: 'background 80ms, color 80ms',
    } as React.CSSProperties,
    btnPrimary: {
      height: '25px', padding: '0 10px', borderRadius: '3px',
      fontSize: '11px', fontWeight: 500, cursor: 'pointer',
      whiteSpace: 'nowrap' as const, display: 'inline-flex', alignItems: 'center', gap: '4px',
      fontFamily: 'var(--font-sans)', flexShrink: 0,
      background: 'var(--teal-bg)', color: 'var(--mark)',
      border: '1px solid rgba(90,171,204,0.28)',
      transition: 'background 80ms, color 80ms',
    } as React.CSSProperties,
    btnDanger: {
      height: '25px', padding: '0 10px', borderRadius: '3px',
      fontSize: '11px', fontWeight: 500, cursor: 'pointer',
      whiteSpace: 'nowrap' as const, display: 'inline-flex', alignItems: 'center', gap: '4px',
      fontFamily: 'var(--font-sans)', flexShrink: 0,
      background: 'var(--red-bg)', color: 'var(--red)',
      border: '1px solid var(--red-border)',
      transition: 'background 80ms, color 80ms',
    } as React.CSSProperties,
    // Note text
    note: {
      fontSize: '11px', color: 'var(--txt3)', lineHeight: 1.55,
      padding: '0 2px', marginBottom: '14px',
    } as React.CSSProperties,
  };

  // ============================================================================
  // PAGE CONTENT (prototype v4 exact)
  // ============================================================================

  const renderContent = () => {
    switch (activePage) {
      case 'account':
        return (
          <>
            <div style={s.sect}>Profile</div>
            <div style={s.rg}>
              <div style={s.rowNoHover}>
                <span style={s.rowLabel}>Email</span>
                <span style={s.rowValueMono}>{user?.email || 'user@example.com'}</span>
              </div>
              <div style={{ ...s.rowNoHover, ...s.rowDivider }}>
                <span style={s.rowLabel}>Department</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={s.rowValue}>{user?.role?.replace('_', ' ') || 'Engineering'}</span>
                  <span style={s.badgeLock}>Locked</span>
                </div>
              </div>
              <div style={{ ...s.rowNoHover, ...s.rowDivider }}>
                <span style={s.rowLabel}>Role</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={s.rowValue}>Crew</span>
                  <span style={s.badgeLock}>Locked</span>
                </div>
              </div>
            </div>
            <div style={s.sect}>Appearance</div>
            <div style={s.rg}>
              <div style={s.row}>
                <span style={s.rowLabel}>Theme</span>
                <div style={{ position: 'relative', display: 'inline-flex', alignItems: 'center' }}>
                  <select
                    value={appearance}
                    onChange={(e) => setAppearance(e.target.value as 'light' | 'dark' | 'system')}
                    style={{
                      height: '25px', padding: '0 26px 0 9px', borderRadius: '3px',
                      fontSize: '11px', fontFamily: 'var(--font-sans)',
                      background: 'var(--surface-hover)', color: 'var(--txt)',
                      borderTop: '1px solid var(--settings-modal-border-t)',
                      borderRight: '1px solid var(--settings-modal-border-s)',
                      borderBottom: '1px solid var(--settings-modal-border-b)',
                      borderLeft: '1px solid var(--settings-modal-border-s)',
                      cursor: 'pointer', outline: 'none',
                      appearance: 'none', WebkitAppearance: 'none',
                    }}
                  >
                    <option value="dark">Dark</option>
                    <option value="light">Light</option>
                    <option value="system">System</option>
                  </select>
                  <div style={{ position: 'absolute', right: '7px', pointerEvents: 'none', color: 'var(--txt2)', display: 'flex' }}>
                    <svg width="9" height="6" viewBox="0 0 9 6" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"><path d="M1 1l3.5 3.5L8 1" /></svg>
                  </div>
                </div>
              </div>
            </div>
          </>
        );

      case 'security':
        return (
          <>
            <div style={s.sect}>Password</div>
            <div style={s.rg}>
              <div style={s.row}>
                <div style={s.rowLeft}>
                  <span style={s.rowLabel}>Reset password</span>
                  <span style={s.rowDesc}>A reset link will be sent to your email</span>
                </div>
                <button style={s.btn}>Send link</button>
              </div>
            </div>
            <div style={s.sect}>Activity</div>
            <div style={s.rg}>
              <div style={s.rowNoHover}>
                <span style={s.rowLabel}>Last sign-in</span>
                <span style={s.rowValueMono}>19 Mar 2026 · 14:00</span>
              </div>
            </div>
          </>
        );

      case 'apps':
        return (
          <>
            <div style={s.sect}>Integrations</div>
            <div style={s.rg}>
              <div style={s.row}>
                <div style={s.rowLeft}>
                  <span style={s.rowLabel}>Microsoft 365</span>
                  <span style={s.rowDesc}>Outlook email and calendar</span>
                </div>
                <button style={s.btnPrimary}>Connect</button>
              </div>
            </div>
            <div style={s.sect}>Request an integration</div>
            <div style={s.rg}>
              <div style={{ ...s.row, gap: '8px' }}>
                <input
                  value={integrationRequest}
                  onChange={(e) => setIntegrationRequest(e.target.value)}
                  placeholder="e.g. Slack, Jira, Maximo…"
                  style={{
                    flex: 1, height: '25px', padding: '0 9px', borderRadius: '3px',
                    fontSize: '11px', fontFamily: 'var(--font-sans)',
                    background: 'var(--settings-modal-bg)', color: 'var(--txt)',
                    borderTop: '1px solid var(--settings-modal-border-t)',
                    borderRight: '1px solid var(--settings-modal-border-s)',
                    borderBottom: '1px solid var(--settings-modal-border-b)',
                    borderLeft: '1px solid var(--settings-modal-border-s)',
                    outline: 'none',
                  }}
                />
                <button
                  style={s.btnPrimary}
                  onClick={() => {
                    if (!integrationRequest.trim() || !user?.email) return;
                    window.location.href = `mailto:contact@celeste7.ai?subject=${encodeURIComponent(
                      `integration request from ${user.email}`
                    )}&body=${encodeURIComponent(integrationRequest)}`;
                    setIntegrationRequest('');
                  }}
                >
                  Send
                </button>
              </div>
            </div>
            <div style={s.note}>Let us know which tools your crew use. Every request is reviewed by the team.</div>
          </>
        );

      case 'data':
        return (
          <>
            <div style={s.sect}>Storage</div>
            <div style={s.rg}>
              <div style={s.rowNoHover}>
                <div style={s.rowLeft}>
                  <span style={s.rowLabel}>NAS path</span>
                  <span style={s.rowDesc}>Set by your administrator</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={s.rowValueMono}>/02_engineering</span>
                  <span style={s.badgeLock}>Locked</span>
                </div>
              </div>
            </div>
            <div style={s.sect}>Your data</div>
            <div style={s.rg}>
              <div style={s.row}>
                <div style={s.rowLeft}>
                  <span style={s.rowLabel}>Export activity log</span>
                  <span style={s.rowDesc}>All reads, writes, and navigation</span>
                </div>
                <button style={s.btn}>Export</button>
              </div>
            </div>
            <div style={s.note}>
              Celeste stores only what&apos;s necessary to run the system. Activity logs are retained for 90 days. Attachments follow your vessel&apos;s NAS retention policy.
            </div>
            {/* Danger zone — pinned to bottom */}
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '10px 12px', gap: '12px', minHeight: '40px',
              borderTop: '1px solid var(--red-border)',
              borderRight: '1px solid rgba(192,80,58,0.12)',
              borderBottom: '1px solid rgba(192,80,58,0.08)',
              borderLeft: '1px solid rgba(192,80,58,0.12)',
              borderRadius: '5px', background: 'var(--red-bg)',
              marginTop: 'auto',
            }}>
              <div style={s.rowLeft}>
                <span style={{ fontSize: '12.5px', color: 'var(--red)' }}>Request account deletion</span>
                <span style={{ fontSize: '11px', color: 'rgba(192,80,58,0.55)', marginTop: '2px' }}>Your data will be removed within 30 days</span>
              </div>
              <button style={s.btnDanger}>Request</button>
            </div>
          </>
        );

      case 'help':
        return (
          <>
            <div style={s.sect}>Contact support</div>
            <textarea
              value={supportMessage}
              onChange={(e) => setSupportMessage(e.target.value)}
              placeholder="Describe the issue — what you were doing, what you expected, what happened…"
              style={{
                width: '100%', minHeight: '72px', resize: 'none',
                padding: '9px 12px', borderRadius: '5px',
                fontSize: '12px', fontFamily: 'var(--font-sans)',
                background: 'var(--surface)', color: 'var(--txt)',
                borderTop: '1px solid var(--settings-modal-border-t)',
                borderRight: '1px solid var(--settings-modal-border-s)',
                borderBottom: '1px solid var(--settings-modal-border-b)',
                borderLeft: '1px solid var(--settings-modal-border-s)',
                outline: 'none', lineHeight: 1.5, marginBottom: '8px',
              }}
            />
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '16px' }}>
              <button
                style={s.btnPrimary}
                onClick={() => {
                  if (!supportMessage.trim() || !user?.email) return;
                  window.location.href = `mailto:contact@celeste7.ai?subject=${encodeURIComponent(
                    `feedback from ${user.email}`
                  )}&body=${encodeURIComponent(supportMessage)}`;
                  setSupportMessage('');
                }}
              >
                Send
              </button>
            </div>
            <div style={s.sect}>Resources</div>
            <div style={s.rg}>
              <a href="https://celeste7.ai/docs" target="_blank" rel="noopener noreferrer"
                style={{ ...s.row, textDecoration: 'none' }}>
                <span style={{ fontSize: '12.5px', color: 'var(--txt2)' }}>Documentation</span>
                <span style={{ color: 'var(--txt-ghost)', display: 'flex' }}>{ExternalLinkIcon}</span>
              </a>
              <a href="https://celeste7.ai/release-notes" target="_blank" rel="noopener noreferrer"
                style={{ ...s.row, ...s.rowDivider, textDecoration: 'none' }}>
                <span style={{ fontSize: '12.5px', color: 'var(--txt2)' }}>Release notes</span>
                <span style={{ color: 'var(--txt-ghost)', display: 'flex' }}>{ExternalLinkIcon}</span>
              </a>
            </div>
          </>
        );

      case 'about':
        return (
          <>
            {/* Version block */}
            <div style={{
              display: 'flex', flexDirection: 'column', gap: '4px',
              paddingBottom: '16px', marginBottom: '14px',
              borderBottom: '1px solid var(--border-sub)',
            }}>
              <div style={{
                fontSize: '9px', fontWeight: 600, letterSpacing: '0.14em',
                textTransform: 'uppercase', color: 'var(--txt-ghost)',
              }}>
                Version
              </div>
              <div style={{
                fontSize: '22px', fontWeight: 600, letterSpacing: '-0.02em',
                color: 'var(--txt)', fontFamily: 'var(--font-mono)',
              }}>
                1.0.0
              </div>
              <div style={{ fontSize: '11px', color: 'var(--txt3)', fontFamily: 'var(--font-mono)' }}>
                Build 2026.03.16 · Celeste7 Ltd
              </div>
            </div>
            <div style={s.sect}>Legal</div>
            <div style={s.rg}>
              <a href="https://celeste7.ai/terms" target="_blank" rel="noopener noreferrer"
                style={{ ...s.row, textDecoration: 'none' }}>
                <span style={{ fontSize: '12.5px', color: 'var(--txt2)' }}>Terms of service</span>
                <span style={{ color: 'var(--txt-ghost)', display: 'flex' }}>{ExternalLinkIcon}</span>
              </a>
              <a href="https://celeste7.ai/privacy" target="_blank" rel="noopener noreferrer"
                style={{ ...s.row, ...s.rowDivider, textDecoration: 'none' }}>
                <span style={{ fontSize: '12.5px', color: 'var(--txt2)' }}>Privacy policy</span>
                <span style={{ color: 'var(--txt-ghost)', display: 'flex' }}>{ExternalLinkIcon}</span>
              </a>
              <a href="https://celeste7.ai/dataterms" target="_blank" rel="noopener noreferrer"
                style={{ ...s.row, ...s.rowDivider, textDecoration: 'none' }}>
                <span style={{ fontSize: '12.5px', color: 'var(--txt2)' }}>Data processing agreement</span>
                <span style={{ color: 'var(--txt-ghost)', display: 'flex' }}>{ExternalLinkIcon}</span>
              </a>
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
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="settings-title"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 50,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      {/* Backdrop */}
      <div
        style={{ position: 'absolute', inset: 0, background: 'var(--settings-backdrop)' }}
        onClick={onClose}
      />

      {/* Modal — 547×483 */}
      <div
        style={{
          position: 'relative',
          width: '547px',
          height: '483px',
          maxWidth: 'calc(100vw - 48px)',
          maxHeight: 'calc(100vh - 48px)',
          borderRadius: '8px',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          background: 'var(--settings-modal-bg)',
          borderTop: '1px solid var(--settings-modal-border-t)',
          borderRight: '1px solid var(--settings-modal-border-s)',
          borderBottom: '1px solid var(--settings-modal-border-b)',
          borderLeft: '1px solid var(--settings-modal-border-s)',
          boxShadow: 'var(--settings-modal-shadow)',
          fontFamily: 'var(--font-sans)',
          fontSize: '13px',
          WebkitFontSmoothing: 'antialiased',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header — 42px */}
        <div style={{
          height: '42px', flexShrink: 0,
          display: 'flex', alignItems: 'center',
          padding: '0 14px',
          borderBottom: '1px solid var(--border-sub)',
          background: 'var(--settings-header-bg)',
          backdropFilter: 'blur(8px)',
          WebkitBackdropFilter: 'blur(8px)',
        }}>
          <span id="settings-title" style={{
            fontSize: '12px', fontWeight: 600, letterSpacing: '0.04em',
            color: 'var(--txt2)', flex: 1,
          }}>
            Settings
          </span>
          <div
            onClick={onClose}
            style={{
              width: '22px', height: '22px', borderRadius: '4px',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: 'pointer', color: 'var(--txt-ghost)',
              transition: 'background 80ms, color 80ms',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'var(--surface-hover)';
              e.currentTarget.style.color = 'var(--txt2)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'transparent';
              e.currentTarget.style.color = 'var(--txt-ghost)';
            }}
          >
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
              <path d="M1.5 1.5l7 7M8.5 1.5l-7 7" />
            </svg>
          </div>
        </div>

        {/* Body — sidebar + content */}
        <div style={{ display: 'flex', flex: 1, minHeight: 0 }}>
          {/* Sidebar — 168px */}
          <div style={{
            width: '168px', flexShrink: 0,
            background: 'var(--surface)',
            borderRight: '1px solid var(--border-sub)',
            display: 'flex', flexDirection: 'column',
            padding: '8px 6px',
          }}>
            {/* Nav list */}
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '1px' }}>
              {navItems.map((id) => {
                const isActive = activePage === id;
                return (
                  <div
                    key={id}
                    onClick={() => setActivePage(id)}
                    style={{
                      display: 'flex', alignItems: 'center',
                      gap: '8px', height: '32px', padding: '0 9px',
                      borderRadius: '4px', cursor: 'pointer',
                      fontSize: '12px',
                      color: isActive ? 'var(--txt)' : 'var(--txt2)',
                      background: isActive ? 'var(--teal-bg)' : 'transparent',
                      borderLeft: isActive ? '2px solid var(--mark)' : '2px solid transparent',
                      transition: 'background 80ms, color 80ms',
                      userSelect: 'none',
                    }}
                    onMouseEnter={(e) => {
                      if (!isActive) {
                        e.currentTarget.style.background = 'var(--surface-hover)';
                        e.currentTarget.style.color = 'var(--txt)';
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!isActive) {
                        e.currentTarget.style.background = 'transparent';
                        e.currentTarget.style.color = 'var(--txt2)';
                      }
                    }}
                  >
                    <span style={{
                      width: '13px', height: '13px', flexShrink: 0,
                      color: isActive ? 'var(--txt2)' : 'var(--txt3)',
                      display: 'flex',
                    }}>
                      {NavIcons[id]}
                    </span>
                    {PAGE_TITLES[id]}
                  </div>
                );
              })}
            </div>

            {/* Sign out — sidebar footer */}
            <div style={{ padding: '6px 0 2px', borderTop: '1px solid var(--border-sub)' }}>
              <div
                onClick={async () => {
                  try {
                    if (logout) await logout();
                  } catch {
                    localStorage.clear();
                    window.location.reload();
                  }
                }}
                style={{
                  display: 'flex', alignItems: 'center',
                  gap: '8px', height: '32px', padding: '0 9px',
                  borderRadius: '4px', cursor: 'pointer',
                  fontSize: '12px', color: 'rgba(192,80,58,0.72)',
                  borderLeft: '2px solid transparent',
                  transition: 'background 80ms, color 80ms',
                  userSelect: 'none',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'rgba(192,80,58,0.09)';
                  e.currentTarget.style.color = 'rgba(192,80,58,0.90)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'transparent';
                  e.currentTarget.style.color = 'rgba(192,80,58,0.72)';
                }}
              >
                <span style={{ width: '13px', height: '13px', flexShrink: 0, color: 'rgba(192,80,58,0.52)', display: 'flex' }}>
                  {NavIcons.signout}
                </span>
                Sign out
              </div>
            </div>
          </div>

          {/* Content area */}
          <div style={{
            flex: 1, background: 'var(--settings-modal-bg)',
            overflowY: 'auto', display: 'flex', flexDirection: 'column',
            padding: '20px 18px',
          }}>
            <div style={{
              fontSize: '15px', fontWeight: 600, letterSpacing: '-0.01em',
              color: 'var(--txt)', marginBottom: '18px', flexShrink: 0,
            }}>
              {PAGE_TITLES[activePage]}
            </div>
            {renderContent()}
          </div>
        </div>
      </div>
    </div>
  );
}
