'use client';

/**
 * AppShell — The main application layout for the Interface Pivot
 *
 * Three-row grid layout:
 *   Row 1: Topbar (var(--shell-topbar-h)) — brand + vessel + global search + role
 *   Row 2: Subbar (var(--shell-subbar-h)) — breadcrumb + scoped search + chips + action (hidden on Surface)
 *   Row 3: Body — sidebar (var(--shell-sidebar-w) / var(--shell-sidebar-compact-w)) + main content
 *
 * Dimensions are defined as tokens in tokens.css under "Shell structural dimensions".
 * JS constants below mirror those tokens for the dynamic sidebarWidth calculation —
 * if you change the tokens, update the constants too.
 *
 * This shell wraps all authenticated routes. It is the single source of
 * navigation, search, and layout structure.
 *
 * Spec: celeste-interface-pivot-spec.pdf (all sections)
 * Prototype: vessel-surface-v2.html (visual reference only)
 */

// ── Shell dimension constants — mirror tokens.css "Shell structural dimensions" ──
// Keep these in sync with --shell-* tokens. Used for JS-computed gridTemplateColumns.
const SHELL_TOPBAR_H          = 48;   // --shell-topbar-h
const SHELL_SUBBAR_H          = 46;   // --shell-subbar-h
const SHELL_SIDEBAR_W         = 192;  // --shell-sidebar-w
const SHELL_SIDEBAR_COMPACT_W = 48;   // --shell-sidebar-compact-w

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
import { CreateWorkOrderModal } from '@/components/actions/modals/CreateWorkOrderModal';
import { ReportFaultModal } from '@/components/modals/ReportFaultModal';
import { FileWarrantyClaimModal } from '@/components/lens-v2/actions/FileWarrantyClaimModal';
import { AttachmentUploadModal } from '@/components/lens-v2/actions/AttachmentUploadModal';
import { LedgerPanel } from '@/components/ledger';
import { useQueryClient } from '@tanstack/react-query';
import { getAuthHeaders, getYachtId } from '@/lib/authHelpers';

/** Map URL pathnames to domain IDs */
const PATH_TO_DOMAIN: Record<string, DomainId> = {
  '/': 'surface',
  '/surface': 'surface',
  '/work-orders': 'work-orders',
  '/faults': 'faults',
  '/equipment': 'equipment',
  '/handover-export': 'handover-export',
  '/hours-of-rest': 'hours-of-rest',
  '/email': 'email',
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
  email: 'Email',
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
  email: '/email',
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
  // Ledger panel state
  const [ledgerOpen, setLedgerOpen] = React.useState(false);
  // Create modal state for primary action buttons
  const [createWOOpen, setCreateWOOpen] = React.useState(false);
  const [reportFaultOpen, setReportFaultOpen] = React.useState(false);
  const [fileWarrantyOpen, setFileWarrantyOpen] = React.useState(false);
  const [documentUploadOpen, setDocumentUploadOpen] = React.useState(false);

  // React Query client — used to invalidate the documents list after an upload
  // so the newly-uploaded document appears immediately. Mirrors the pattern
  // in FileWarrantyClaimModal and matches the queryKey set in
  // apps/web/src/app/documents/page.tsx FilteredEntityList (['documents']).
  const queryClient = useQueryClient();

  // Topbar menu handlers
  const handleEmailClick = React.useCallback(() => {
    router.push('/email');
  }, [router]);

  const handleSettingsClick = React.useCallback(() => {
    setSettingsOpen(true);
  }, []);

  // Primary action handler — opens create modal for domains that have one,
  // navigates to domain page for others
  const handlePrimaryAction = React.useCallback(() => {
    switch (activeDomain) {
      case 'work-orders':
        setCreateWOOpen(true);
        break;
      case 'faults':
        setReportFaultOpen(true);
        break;
      case 'warranties':
        setFileWarrantyOpen(true);
        break;
      case 'documents':
        setDocumentUploadOpen(true);
        break;
      default:
        // Domains without a create modal — navigate to domain (already there, but no-op is fine)
        break;
    }
  }, [activeDomain]);

  // ------------------------------------------------------------------
  // Document upload handler passed to AttachmentUploadModal in custom mode.
  //
  // Flow:
  //   1. Resolve yacht_id from the user profile (same helper apiClient uses)
  //   2. Obtain secure auth headers (JWT + X-Yacht-Signature)
  //   3. POST multipart/form-data to /v1/documents/upload
  //   4. On success, invalidate the ['documents'] query so FilteredEntityList
  //      refetches and the new document appears at the top of the list.
  //
  // Backend endpoint:
  //   apps/api/routes/document_routes.py:upload_document
  //
  // Failure modes surfaced to the modal Toast via thrown errors:
  //   - 401: auth missing / expired
  //   - 403: role not in UPLOAD_DOCUMENT_ROLES
  //   - 413: file > 15 MB
  //   - 415: unsupported mime type
  //   - 500: storage upload or doc_metadata insert failed (server-side rollback)
  // ------------------------------------------------------------------
  const handleDocumentUpload = React.useCallback(
    async (file: File): Promise<void> => {
      const yachtId = await getYachtId();
      const authHeaders = await getAuthHeaders(yachtId);

      const apiBaseUrl =
        process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${apiBaseUrl}/v1/documents/upload`, {
        method: 'POST',
        headers: {
          ...authHeaders,
          // DO NOT set Content-Type — browser sets multipart boundary automatically
        },
        body: formData,
      });

      if (!response.ok) {
        // Try to parse FastAPI error detail for a meaningful message
        let message = `Upload failed (${response.status})`;
        try {
          const body = await response.json();
          if (typeof body?.detail === 'string') {
            message = body.detail;
          }
        } catch {
          // body not JSON — keep generic message
        }
        throw new Error(message);
      }

      // Invalidate the documents list so the new upload appears immediately.
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
    [queryClient]
  );

  // hours-of-rest has its own role-aware header — no Subbar needed
  const SUBBAR_EXCLUDED: DomainId[] = ['surface', 'hours-of-rest'];
  const showSubbar = !SUBBAR_EXCLUDED.includes(activeDomain);

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
        onLedgerClick={() => setLedgerOpen(true)}
        onSettingsClick={handleSettingsClick}
        onPrimaryAction={handlePrimaryAction}
      >
        {children}
      </AppShellInner>
      <SearchOverlay open={searchOpen} onClose={() => setSearchOpen(false)} />
      <SettingsModal isOpen={settingsOpen} onClose={() => setSettingsOpen(false)} />
      <LedgerPanel isOpen={ledgerOpen} onClose={() => setLedgerOpen(false)} />
      <CreateWorkOrderModal open={createWOOpen} onOpenChange={setCreateWOOpen} />
      <ReportFaultModal open={reportFaultOpen} onOpenChange={setReportFaultOpen} />
      <FileWarrantyClaimModal open={fileWarrantyOpen} onOpenChange={setFileWarrantyOpen} />
      <AttachmentUploadModal
        open={documentUploadOpen}
        onClose={() => setDocumentUploadOpen(false)}
        onComplete={() => setDocumentUploadOpen(false)}
        title="Upload Document"
        description="Add a document to the vessel library. Accepted: PDF, images, office docs; max 15 MB."
        onUpload={handleDocumentUpload}
      />
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
  onLedgerClick,
  onSettingsClick,
  onPrimaryAction,
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
  onLedgerClick: () => void;
  onSettingsClick: () => void;
  onPrimaryAction: () => void;
  children: React.ReactNode;
}) {
  const { activeChip, setActiveChip, setSearchQuery, setActiveSort } = useShellContext();
  const breakpoint = useBreakpoint();
  const sidebarWidth = breakpoint === 'mobile' ? 0 : breakpoint === 'tablet' ? SHELL_SIDEBAR_COMPACT_W : SHELL_SIDEBAR_W;
  const showSidebar = breakpoint !== 'mobile';
  const isMobile = breakpoint === 'mobile';

  // Mobile nav drawer state
  const [mobileNavOpen, setMobileNavOpen] = React.useState(false);
  const mobileNavRef = React.useRef<HTMLDivElement>(null);

  // Close mobile nav on outside click
  React.useEffect(() => {
    if (!mobileNavOpen) return;
    const handler = (e: MouseEvent) => {
      if (mobileNavRef.current && !mobileNavRef.current.contains(e.target as Node)) {
        setMobileNavOpen(false);
      }
    };
    window.addEventListener('mousedown', handler);
    return () => window.removeEventListener('mousedown', handler);
  }, [mobileNavOpen]);

  // Close mobile nav on domain selection
  const handleMobileDomainSelect = React.useCallback((domain: Parameters<typeof onSelectDomain>[0]) => {
    onSelectDomain(domain);
    setMobileNavOpen(false);
  }, [onSelectDomain]);

  return (
    <div
      style={{
        fontFamily: 'var(--font-sans, -apple-system, BlinkMacSystemFont, system-ui, sans-serif)',
        background: 'var(--surface-base)',
        color: 'var(--txt)',
        height: '100vh',
        overflow: 'hidden',
        display: 'grid',
        gridTemplateRows: showSubbar ? `var(--shell-topbar-h) var(--shell-subbar-h) 1fr` : `var(--shell-topbar-h) 1fr`,
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
        onLedgerClick={onLedgerClick}
        onSettingsClick={onSettingsClick}
        compact={breakpoint === 'tablet' || breakpoint === 'mobile'}
        showNavToggle={isMobile}
        onNavToggle={() => setMobileNavOpen((v) => !v)}
      />

      {/* Row 2: Subbar (hidden on Vessel Surface) */}
      {showSubbar && (
        <Subbar
          activeDomain={activeDomain}
          activeChip={activeChip}
          onChipClick={setActiveChip}
          onSearch={setSearchQuery}
          onSortChange={setActiveSort}
          onPrimaryAction={onPrimaryAction}
        />
      )}

      {/* Row 3: Body — sidebar + main content */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: showSidebar ? `${sidebarWidth}px 1fr` : '1fr',
          overflow: 'hidden',
          minHeight: 0,
        }}
      >
        {/* Left sidebar */}
        {showSidebar && (
          <Sidebar
            activeDomain={activeDomain}
            onSelectDomain={onSelectDomain}
            counts={sidebarCounts}
            compact={sidebarWidth === SHELL_SIDEBAR_COMPACT_W}
          />
        )}

        {/* Main content area */}
        <main
          style={{
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            minHeight: 0,
          }}
        >
          {children}
        </main>
      </div>

      {/* Mobile nav drawer — slide-over sidebar */}
      {isMobile && (
        <>
          {/* Backdrop */}
          <div
            style={{
              position: 'fixed',
              inset: 0,
              background: 'rgba(0,0,0,0.50)',
              zIndex: 150,
              opacity: mobileNavOpen ? 1 : 0,
              visibility: mobileNavOpen ? 'visible' : 'hidden',
              transition: 'opacity 200ms ease',
            }}
          />
          {/* Drawer */}
          <div
            ref={mobileNavRef}
            style={{
              position: 'fixed',
              top: 0,
              left: 0,
              bottom: 0,
              width: 220,
              background: 'var(--surface-base)',
              borderRight: '1px solid var(--border-sub)',
              zIndex: 160,
              transform: mobileNavOpen ? 'translateX(0)' : 'translateX(-100%)',
              transition: 'transform 200ms ease',
              overflowY: 'auto',
              paddingTop: 48,
            }}
          >
            <Sidebar
              activeDomain={activeDomain}
              onSelectDomain={handleMobileDomainSelect}
              counts={sidebarCounts}
            />
          </div>
        </>
      )}
    </div>
  );
}
