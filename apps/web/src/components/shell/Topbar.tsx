'use client';

/**
 * Topbar — Phase 1A of the Interface Pivot
 *
 * 48px persistent topbar. Always present on every authenticated screen.
 * Contains: Brand + Vessel Name + Global Search (Tier 1) + Role Badge + Menu
 *
 * NO domain nav pills. NO entity counts. NO clickable domain names.
 * The topbar is clean: brand, vessel, search, role.
 *
 * Spec: celeste-interface-pivot-spec.pdf §06
 * Prototype: vessel-surface-v2.html (visual reference only)
 */

import * as React from 'react';
import { Search, X, Menu, LogOut, User, Settings, LayoutGrid } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { useActiveVessel } from '@/contexts/VesselContext';
import { supabase } from '@/lib/supabaseClient';

interface TopbarProps {
  /** Current active domain for scope tag (null = global) */
  activeDomain?: string | null;
  /** Human-readable label for the active domain */
  activeDomainLabel?: string | null;
  /** Called when the scope tag × is clicked to clear domain scope */
  onClearScope?: () => void;
  /** Called when ⌘K is pressed or search is focused */
  onSearchFocus?: () => void;
  /** Called when menu icon is clicked (opens command palette) */
  onMenuClick?: () => void;
  /** Called when Email is selected from the menu */
  onEmailClick?: () => void;
  /** Called when Command Center is selected from the menu */
  onCommandCenterClick?: () => void;
  /** Called when Settings is selected from the menu */
  onSettingsClick?: () => void;
  /** Compact mode: hide vessel name, separators, role badge */
  compact?: boolean;
  /** Called when mobile nav hamburger is tapped (mobile only) */
  onNavToggle?: () => void;
  /** Whether to show the nav hamburger (mobile only) */
  showNavToggle?: boolean;
}

export function Topbar({
  activeDomain,
  activeDomainLabel,
  onClearScope,
  onSearchFocus,
  onMenuClick,
  onEmailClick,
  onCommandCenterClick,
  onSettingsClick,
  compact,
  onNavToggle,
  showNavToggle,
}: TopbarProps) {
  const { user } = useAuth();
  const router = useRouter();
  const searchInputRef = React.useRef<HTMLInputElement>(null);
  const [menuOpen, setMenuOpen] = React.useState(false);
  const menuRef = React.useRef<HTMLDivElement>(null);

  // Close menu on outside click
  React.useEffect(() => {
    if (!menuOpen) return;
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false);
    };
    window.addEventListener('mousedown', handler);
    return () => window.removeEventListener('mousedown', handler);
  }, [menuOpen]);

  const handleSignOut = React.useCallback(async () => {
    await supabase.auth.signOut();
    router.replace('/login');
  }, [router]);

  const vessel = useActiveVessel();
  const vesselName = vessel.vesselName;
  const roleName = user?.role
    ? user.role.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase())
    : 'Member';

  // ⌘K global shortcut to focus search
  React.useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        searchInputRef.current?.focus();
        onSearchFocus?.();
      }
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onSearchFocus]);

  return (
    <header
      style={{
        height: 48,
        flexShrink: 0,
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        padding: '0 16px',
        background: 'var(--topbar-bg)',
        backdropFilter: 'blur(18px)',
        WebkitBackdropFilter: 'blur(18px)',
        borderBottom: '1px solid var(--border-sub)',
        zIndex: 100,
      }}
    >
      {/* Mobile nav toggle */}
      {showNavToggle && (
        <button
          onClick={onNavToggle}
          aria-label="Open navigation"
          style={{
            width: 28,
            height: 28,
            borderRadius: 4,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--txt3)',
            cursor: 'pointer',
            background: 'transparent',
            border: 'none',
            flexShrink: 0,
            transition: 'background 80ms',
          }}
          onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--surface-hover)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
        >
          <LayoutGrid style={{ width: 14, height: 14 }} />
        </button>
      )}

      {/* Brand */}
      <div
        style={{
          fontSize: 9,
          fontWeight: 600,
          letterSpacing: '0.20em',
          textTransform: 'uppercase',
          color: 'var(--mark)',
          flexShrink: 0,
        }}
      >
        CELESTE
      </div>

      {!compact && (
        <>
          <div style={{ width: 1, height: 12, background: 'var(--border-sub)', flexShrink: 0 }} />
          {vessel.isFleetUser ? (
            <VesselDropdown vessel={vessel} />
          ) : (
            <div style={{ fontSize: 11, color: 'var(--txt3)', flexShrink: 0, whiteSpace: 'nowrap' }}>
              <em style={{ fontStyle: 'normal', color: 'var(--topbar-vessel-em)' }}>{vesselName}</em>
            </div>
          )}
          <div style={{ width: 1, height: 12, background: 'var(--border-sub)', flexShrink: 0 }} />
        </>
      )}

      {/* Global search bar — Tier 1 */}
      <div
        style={{
          flex: 1,
          maxWidth: 520,
          height: 28,
          display: 'flex',
          alignItems: 'center',
          gap: 7,
          padding: '0 10px',
          /* Asymmetric border physics: top brighter, sides mid, bottom faint.
             No single token covers this — intentional per spec §06 design rules. */
          background: 'var(--split-bg)',
          borderTop: '1px solid var(--border-sub)',
          borderRight: '1px solid var(--border-bottom)',
          borderBottom: '1px solid var(--border-bottom)',
          borderLeft: '1px solid var(--border-bottom)',
          borderRadius: 4,
          cursor: 'text',
          transition: 'background 100ms, border-color 100ms',
        }}
        onClick={() => searchInputRef.current?.focus()}
      >
        <Search
          style={{
            width: 12,
            height: 12,
            color: 'var(--txt-ghost)',
            flexShrink: 0,
          }}
        />

        {/* Scope tag — visible when inside a domain */}
        {activeDomain && activeDomainLabel && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onClearScope?.();
            }}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 4,
              height: 16,
              padding: '0 6px',
              borderRadius: 3,
              background: 'var(--teal-bg)',
              border: '1px solid var(--mark-hover)',
              fontSize: 9,
              fontWeight: 600,
              color: 'var(--mark)',
              whiteSpace: 'nowrap',
              flexShrink: 0,
              cursor: 'pointer',
            }}
          >
            {activeDomainLabel}
            <X style={{ width: 8, height: 8 }} />
          </button>
        )}

        <input
          ref={searchInputRef}
          type="text"
          placeholder="Search anything across vessel\u2026"
          style={{
            flex: 1,
            fontSize: 12,
            color: 'var(--txt)',
            background: 'transparent',
            border: 'none',
            outline: 'none',
            caretColor: 'var(--mark)',
          }}
          onFocus={() => {
            // Blur immediately — this input is a trigger, not the actual search.
            // SpotlightSearch in the overlay handles the real input.
            searchInputRef.current?.blur();
            onSearchFocus?.();
          }}
          readOnly
        />

        <span
          style={{
            fontSize: 9,
            fontFamily: 'var(--font-mono, ui-monospace, monospace)',
            color: 'var(--txt-ghost)',
            flexShrink: 0,
          }}
        >
          \u2318K
        </span>
      </div>

      {/* Spacer */}
      <div style={{ flex: 1 }} />

      {/* Role badge — hidden in compact mode */}
      {!compact && (
        <div
          style={{
            fontSize: 9,
            letterSpacing: '0.07em',
            textTransform: 'uppercase',
            color: 'var(--txt-ghost)',
            background: 'var(--surface-el)',
            border: '1px solid var(--border-sub)',
            borderRadius: 3,
            padding: '2px 6px',
            flexShrink: 0,
          }}
        >
          {roleName}
        </div>
      )}

      {/* Menu button + dropdown */}
      <div ref={menuRef} style={{ position: 'relative', flexShrink: 0 }}>
        <button
          onClick={() => setMenuOpen((v) => !v)}
          style={{
            width: 28,
            height: 28,
            borderRadius: 4,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: menuOpen ? 'var(--mark)' : 'var(--txt3)',
            transition: 'background 80ms, color 80ms',
            cursor: 'pointer',
            background: menuOpen ? 'var(--teal-bg)' : 'transparent',
            border: 'none',
          }}
          onMouseEnter={(e) => { if (!menuOpen) { e.currentTarget.style.background = 'var(--surface-hover)'; e.currentTarget.style.color = 'var(--txt2)'; } }}
          onMouseLeave={(e) => { if (!menuOpen) { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--txt3)'; } }}
        >
          <Menu style={{ width: 14, height: 14 }} />
        </button>

        {menuOpen && (
          <div
            style={{
              position: 'absolute',
              top: 34,
              right: 0,
              width: 200,
              background: 'var(--surface-el)',
              borderTop: '1px solid var(--border-top)',
              borderRight: '1px solid var(--border-side)',
              borderBottom: '1px solid var(--border-bottom)',
              borderLeft: '1px solid var(--border-side)',
              borderRadius: 4,
              boxShadow: 'var(--shadow-drop)',
              overflow: 'hidden',
              zIndex: 200,
            }}
          >
            {/* User info */}
            <div style={{ padding: '10px 12px', borderBottom: '1px solid var(--border-faint)' }}>
              <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--txt)' }}>
                {user?.email || 'User'}
              </div>
              <div style={{ fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--txt-ghost)', marginTop: 2 }}>
                {roleName} · {vesselName}
              </div>
            </div>

            {/* Command Center */}
            <button
              onClick={() => { setMenuOpen(false); onCommandCenterClick?.(); }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                width: '100%',
                padding: '10px 12px',
                fontSize: 12,
                color: 'var(--txt2)',
                background: 'transparent',
                border: 'none',
                cursor: 'pointer',
                transition: 'background 60ms',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--surface-hover)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
            >
              <LayoutGrid style={{ width: 13, height: 13 }} />
              Command Center
            </button>

            {/* Settings */}
            <button
              onClick={() => { setMenuOpen(false); onSettingsClick?.(); }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                width: '100%',
                padding: '10px 12px',
                fontSize: 12,
                color: 'var(--txt2)',
                background: 'transparent',
                border: 'none',
                cursor: 'pointer',
                transition: 'background 60ms',
                borderBottom: '1px solid var(--border-faint)',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--surface-hover)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
            >
              <Settings style={{ width: 13, height: 13 }} />
              Settings
            </button>

            {/* Sign out */}
            <button
              onClick={handleSignOut}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                width: '100%',
                padding: '10px 12px',
                fontSize: 12,
                color: 'var(--red)',
                background: 'transparent',
                border: 'none',
                cursor: 'pointer',
                transition: 'background 60ms',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--surface-hover)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
            >
              <LogOut style={{ width: 13, height: 13 }} />
              Sign out
            </button>
          </div>
        )}
      </div>
    </header>
  );
}

/** Vessel selector dropdown for fleet managers */
function VesselDropdown({ vessel }: { vessel: ReturnType<typeof useActiveVessel> }) {
  const [open, setOpen] = React.useState(false);
  const ref = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    window.addEventListener('mousedown', handler);
    return () => window.removeEventListener('mousedown', handler);
  }, [open]);

  return (
    <div ref={ref} style={{ position: 'relative', flexShrink: 0 }}>
      <button
        onClick={() => setOpen((v) => !v)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 4,
          fontSize: 11,
          color: 'var(--topbar-vessel-em)',
          background: 'transparent',
          border: 'none',
          cursor: 'pointer',
          padding: '2px 4px',
          borderRadius: 3,
          transition: 'background 60ms',
        }}
        onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--surface-hover)'; }}
        onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
      >
        <em style={{ fontStyle: 'normal' }}>{vessel.vesselName}</em>
        <svg width="8" height="8" viewBox="0 0 8 8" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M2 3l2 2 2-2" />
        </svg>
      </button>

      {open && (
        <div
          style={{
            position: 'absolute',
            top: 28,
            left: 0,
            minWidth: 180,
            background: 'var(--surface-el)',
            borderTop: '1px solid var(--border-top)',
            borderRight: '1px solid var(--border-side)',
            borderBottom: '1px solid var(--border-bottom)',
            borderLeft: '1px solid var(--border-side)',
            borderRadius: 4,
            boxShadow: 'var(--shadow-drop)',
            overflow: 'hidden',
            zIndex: 200,
          }}
        >
          {/* All Vessels option */}
          <button
            onClick={() => { vessel.setActiveVessel(null); setOpen(false); }}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              width: '100%',
              padding: '8px 12px',
              fontSize: 11,
              color: vessel.isAllVessels ? 'var(--mark)' : 'var(--txt2)',
              background: vessel.isAllVessels ? 'var(--teal-bg)' : 'transparent',
              border: 'none',
              cursor: 'pointer',
              transition: 'background 60ms',
              borderBottom: '1px solid var(--border-faint)',
            }}
            onMouseEnter={(e) => { if (!vessel.isAllVessels) e.currentTarget.style.background = 'var(--surface-hover)'; }}
            onMouseLeave={(e) => { if (!vessel.isAllVessels) e.currentTarget.style.background = 'transparent'; }}
          >
            All Vessels
          </button>

          {/* Individual vessels */}
          {vessel.vessels.map((v) => (
            <button
              key={v.yacht_id}
              onClick={() => { vessel.setActiveVessel(v.yacht_id); setOpen(false); }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                width: '100%',
                padding: '8px 12px',
                fontSize: 11,
                color: vessel.vesselId === v.yacht_id ? 'var(--mark)' : 'var(--txt2)',
                background: vessel.vesselId === v.yacht_id ? 'var(--teal-bg)' : 'transparent',
                border: 'none',
                cursor: 'pointer',
                transition: 'background 60ms',
              }}
              onMouseEnter={(e) => { if (vessel.vesselId !== v.yacht_id) e.currentTarget.style.background = 'var(--surface-hover)'; }}
              onMouseLeave={(e) => { if (vessel.vesselId !== v.yacht_id) e.currentTarget.style.background = 'transparent'; }}
            >
              {v.yacht_name}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
