'use client';

/**
 * AppShell — The main application layout for the Interface Pivot
 *
 * Three-row grid layout:
 *   Row 1: Topbar (48px) — brand + vessel + global search + role
 *   Row 2: Subbar (46px) — breadcrumb + scoped search + chips + action (hidden on Surface)
 *   Row 3: Body — sidebar (192px) + main content
 *
 * This shell wraps all authenticated routes. It is the single source of
 * navigation, search, and layout structure.
 *
 * Spec: celeste-interface-pivot-spec.pdf (all sections)
 * Prototype: vessel-surface-v2.html (visual reference only)
 */

import * as React from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { Topbar } from './Topbar';
import { Sidebar, type DomainId } from './Sidebar';
import { Subbar } from './Subbar';
import { useSidebarCounts } from './hooks';
import { ShellProvider, useShellContext } from './ShellContext';
import { SearchOverlay } from './SearchOverlay';
import { useBreakpoint } from './useBreakpoint';
import SettingsModal from '@/components/SettingsModal';

/** Map URL pathnames to domain IDs */
const PATH_TO_DOMAIN: Record<string, DomainId> = {
  '/': 'surface',
  '/surface': 'surface',
  '/work-orders': 'work-orders',
  '/faults': 'faults',
  '/equipment': 'equipment',
  '/handover-export': 'handover-export',
  '/hours-of-rest': 'hours-of-rest',
  '/inventory': 'inventory',
  '/shopping-list': 'shopping-list',
  '/purchasing': 'purchasing',
  '/receiving': 'receiving',
  '/certificates': 'certificates',
  '/documents': 'documents',
  '/warranties': 'warranties',
};

/** Map domain IDs to human-readable labels */
const DOMAIN_LABELS: Record<DomainId, string> = {
  surface: 'Vessel Surface',
  'work-orders': 'Work Orders',
  faults: 'Faults',
  equipment: 'Equipment',
  'handover-export': 'Handover',
  'hours-of-rest': 'Hours of Rest',
  inventory: 'Parts / Inventory',
  'shopping-list': 'Shopping List',
  purchasing: 'Purchase Orders',
  receiving: 'Receiving',
  certificates: 'Certificates',
  documents: 'Documents',
  warranties: 'Warranty',
};

/** Map domain IDs to route paths */
const DOMAIN_TO_PATH: Record<DomainId, string> = {
  surface: '/',
  'work-orders': '/work-orders',
  faults: '/faults',
  equipment: '/equipment',
  'handover-export': '/handover-export',
  'hours-of-rest': '/hours-of-rest',
  inventory: '/inventory',
  'shopping-list': '/shopping-list',
  purchasing: '/purchasing',
  receiving: '/receiving',
  certificates: '/certificates',
  documents: '/documents',
  warranties: '/warranties',
};

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const router = useRouter();
  const pathname = usePathname();

  // Derive active domain from current pathname
  const activeDomain: DomainId = React.useMemo(() => {
    // Check exact match first
    if (PATH_TO_DOMAIN[pathname]) return PATH_TO_DOMAIN[pathname];
    // Check prefix match for nested routes (e.g., /work-orders/WO-123)
    for (const [path, domain] of Object.entries(PATH_TO_DOMAIN)) {
      if (path !== '/' && pathname.startsWith(path)) return domain;
    }
    return 'surface';
  }, [pathname]);

  const activeDomainLabel = activeDomain !== 'surface' ? DOMAIN_LABELS[activeDomain] : null;

  // Navigation handler
  const handleSelectDomain = React.useCallback(
    (domain: DomainId) => {
      router.push(DOMAIN_TO_PATH[domain]);
    },
    [router]
  );

  // Clear scope tag in topbar search → navigate to surface
  const handleClearScope = React.useCallback(() => {
    // Clearing scope removes the domain filter from global search,
    // but does NOT navigate away. The user stays on the current page.
    // For now, this is a no-op since Tier 1 search is wired separately.
  }, []);

  // Sidebar count badges from Vessel Surface endpoint
  const sidebarCounts = useSidebarCounts();

  // Global search overlay state
  const [searchOpen, setSearchOpen] = React.useState(false);
  // Settings modal state (rendered here, not inside SpotlightSearch)
  const [settingsOpen, setSettingsOpen] = React.useState(false);

  // Topbar menu handlers
  const handleEmailClick = React.useCallback(() => {
    router.push('/email');
  }, [router]);

  const handleSettingsClick = React.useCallback(() => {
    setSettingsOpen(true);
  }, []);

  const showSubbar = activeDomain !== 'surface';

  return (
    <ShellProvider activeDomain={activeDomain}>
      <AppShellInner
        activeDomain={activeDomain}
        activeDomainLabel={activeDomainLabel}
        showSubbar={showSubbar}
        sidebarCounts={sidebarCounts}
        onSelectDomain={handleSelectDomain}
        onClearScope={handleClearScope}
        onSearchFocus={() => setSearchOpen(true)}
        onEmailClick={handleEmailClick}
        onSettingsClick={handleSettingsClick}
      >
        {children}
      </AppShellInner>
      <SearchOverlay open={searchOpen} onClose={() => setSearchOpen(false)} />
      <SettingsModal isOpen={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </ShellProvider>
  );
}

/** Inner shell that reads ShellContext for Subbar state */
function AppShellInner({
  activeDomain,
  activeDomainLabel,
  showSubbar,
  sidebarCounts,
  onSelectDomain,
  onClearScope,
  onSearchFocus,
  onEmailClick,
  onSettingsClick,
  children,
}: {
  activeDomain: DomainId;
  activeDomainLabel: string | null;
  showSubbar: boolean;
  sidebarCounts: ReturnType<typeof useSidebarCounts>;
  onSelectDomain: (domain: DomainId) => void;
  onClearScope: () => void;
  onSearchFocus: () => void;
  onEmailClick: () => void;
  onSettingsClick: () => void;
  children: React.ReactNode;
}) {
  const { activeChip, setActiveChip, setSearchQuery, setActiveSort } = useShellContext();
  const breakpoint = useBreakpoint();
  const sidebarWidth = breakpoint === 'mobile' ? 0 : breakpoint === 'tablet' ? 48 : 192;
  const showSidebar = breakpoint !== 'mobile';

  return (
    <div
      style={{
        fontFamily: 'var(--font-sans, -apple-system, BlinkMacSystemFont, system-ui, sans-serif)',
        background: 'var(--surface-base)',
        color: 'var(--txt)',
        height: '100vh',
        overflow: 'hidden',
        display: 'grid',
        gridTemplateRows: showSubbar ? '48px 46px 1fr' : '48px 1fr',
        gridTemplateColumns: '1fr',
        fontSize: 13,
        lineHeight: 1.5,
        WebkitFontSmoothing: 'antialiased',
        position: 'relative',
        zIndex: 1,
      }}
    >
      {/* Row 1: Topbar */}
      <Topbar
        activeDomain={activeDomain !== 'surface' ? activeDomain : null}
        activeDomainLabel={activeDomainLabel}
        onClearScope={onClearScope}
        onSearchFocus={onSearchFocus}
        onEmailClick={onEmailClick}
        onSettingsClick={onSettingsClick}
        compact={breakpoint === 'tablet' || breakpoint === 'mobile'}
      />

      {/* Row 2: Subbar (hidden on Vessel Surface) */}
      {showSubbar && (
        <Subbar
          activeDomain={activeDomain}
          activeChip={activeChip}
          onChipClick={setActiveChip}
          onSearch={setSearchQuery}
          onSortChange={setActiveSort}
        />
      )}

      {/* Row 3: Body — sidebar + main content */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: showSidebar ? `${sidebarWidth}px 1fr` : '1fr',
          overflow: 'hidden',
        }}
      >
        {/* Left sidebar */}
        {showSidebar && (
          <Sidebar
            activeDomain={activeDomain}
            onSelectDomain={onSelectDomain}
            counts={sidebarCounts}
            compact={sidebarWidth === 48}
          />
        )}

        {/* Main content area */}
        <main
          style={{
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
          }}
        >
          {children}
        </main>
      </div>
    </div>
  );
}
