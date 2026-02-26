'use client';

/**
 * RouteLayout - Shared Layout for Fragmented Routes
 *
 * Provides consistent layout structure for all Tier 1 routes:
 * - /work-orders
 * - /faults
 * - /equipment
 * - /inventory
 *
 * Features:
 * - Optional top navigation
 * - Optional primary panel (right side detail view)
 * - Optional context panel (supplementary info)
 * - Optional action panel (modal overlay)
 * - Loading states
 * - Dark theme (consistent with legacy /app)
 *
 * @see REQUIREMENTS_TABLE.md - LT-01, LT-02, LT-03
 */

import * as React from 'react';
import { cn } from '@/lib/utils';

// Panel configuration types
export interface PrimaryPanelConfig {
  visible: boolean;
  title?: string;
  subtitle?: string;
  children: React.ReactNode;
}

export interface ContextPanelConfig {
  visible: boolean;
  title?: string;
  children: React.ReactNode;
}

export interface ActionPanelConfig {
  visible: boolean;
  children: React.ReactNode;
}

export interface RouteLayoutProps {
  /** Page title for document head */
  pageTitle?: string;

  /** Main content area */
  children: React.ReactNode;

  /** Right-side primary panel (e.g., detail view) */
  primaryPanel?: PrimaryPanelConfig;

  /** Context panel (supplementary information) */
  contextPanel?: ContextPanelConfig;

  /** Action panel (modal overlay) */
  actionPanel?: ActionPanelConfig;

  /** Close primary panel handler */
  onClosePrimaryPanel?: () => void;

  /** Close context panel handler */
  onCloseContextPanel?: () => void;

  /** Close action panel handler */
  onCloseActionPanel?: () => void;

  /** Global loading state */
  isLoading?: boolean;

  /** Show top navigation bar */
  showTopNav?: boolean;

  /** Custom top nav content */
  topNavContent?: React.ReactNode;

  /** Additional className */
  className?: string;
}

/**
 * Loading overlay component
 */
function LoadingOverlay() {
  return (
    <div className="absolute inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="flex flex-col items-center gap-4">
        <div className="w-8 h-8 border-2 border-txt-tertiary border-t-txt-primary rounded-full animate-spin" />
        <p className="text-sm text-txt-secondary">Loading...</p>
      </div>
    </div>
  );
}

/**
 * Top navigation bar
 */
function TopNav({ children }: { children?: React.ReactNode }) {
  return (
    <header className="h-14 flex-shrink-0 border-b border-surface-border bg-surface-base px-4 flex items-center justify-between">
      {children || (
        <div className="flex items-center gap-4">
          <span className="text-lg font-semibold text-txt-primary">Celeste</span>
        </div>
      )}
    </header>
  );
}

/**
 * Primary panel (right side detail view)
 */
function PrimaryPanel({
  config,
  onClose,
}: {
  config: PrimaryPanelConfig;
  onClose?: () => void;
}) {
  if (!config.visible) return null;

  return (
    <div
      className={cn(
        'w-[480px] flex-shrink-0 border-l border-surface-border bg-surface-base',
        'flex flex-col overflow-hidden',
        'animate-in slide-in-from-right duration-200'
      )}
    >
      {/* Panel header */}
      {(config.title || onClose) && (
        <div className="h-14 flex-shrink-0 border-b border-surface-border px-4 flex items-center justify-between">
          <div>
            {config.title && (
              <h2 className="text-sm font-medium text-txt-primary">{config.title}</h2>
            )}
            {config.subtitle && (
              <p className="text-xs text-txt-tertiary">{config.subtitle}</p>
            )}
          </div>
          {onClose && (
            <button
              onClick={onClose}
              className="p-2 hover:bg-surface-hover rounded-lg transition-colors"
              aria-label="Close panel"
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                className="text-txt-secondary"
              >
                <path d="M18 6L6 18M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
      )}

      {/* Panel content */}
      <div className="flex-1 overflow-y-auto">{config.children}</div>
    </div>
  );
}

/**
 * Main RouteLayout component
 */
export function RouteLayout({
  pageTitle,
  children,
  primaryPanel,
  contextPanel,
  actionPanel,
  onClosePrimaryPanel,
  onCloseContextPanel,
  onCloseActionPanel,
  isLoading = false,
  showTopNav = true,
  topNavContent,
  className,
}: RouteLayoutProps) {
  // Update document title
  React.useEffect(() => {
    if (pageTitle) {
      document.title = `${pageTitle} | Celeste`;
    }
  }, [pageTitle]);

  return (
    <div
      className={cn(
        'h-screen flex flex-col bg-surface-base text-txt-primary',
        className
      )}
    >
      {/* Top navigation */}
      {showTopNav && <TopNav>{topNavContent}</TopNav>}

      {/* Main content area */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Primary content */}
        <main className="flex-1 overflow-y-auto">{children}</main>

        {/* Primary panel (right side) */}
        {primaryPanel && (
          <PrimaryPanel config={primaryPanel} onClose={onClosePrimaryPanel} />
        )}

        {/* Context panel (if needed) */}
        {contextPanel?.visible && (
          <div
            className={cn(
              'w-[320px] flex-shrink-0 border-l border-surface-border bg-surface-primary',
              'flex flex-col overflow-hidden'
            )}
          >
            {contextPanel.title && (
              <div className="h-12 flex-shrink-0 border-b border-surface-border px-4 flex items-center justify-between">
                <h3 className="text-sm font-medium text-txt-primary">
                  {contextPanel.title}
                </h3>
                {onCloseContextPanel && (
                  <button
                    onClick={onCloseContextPanel}
                    className="p-1 hover:bg-surface-hover rounded transition-colors"
                    aria-label="Close context panel"
                  >
                    <svg
                      width="16"
                      height="16"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      className="text-txt-tertiary"
                    >
                      <path d="M18 6L6 18M6 6l12 12" />
                    </svg>
                  </button>
                )}
              </div>
            )}
            <div className="flex-1 overflow-y-auto">{contextPanel.children}</div>
          </div>
        )}

        {/* Action panel overlay */}
        {actionPanel?.visible && (
          <div
            className="absolute inset-0 bg-black/50 flex items-center justify-center z-40"
            onClick={onCloseActionPanel}
          >
            <div
              className="bg-surface-elevated rounded-lg shadow-xl border border-surface-border max-w-lg w-full mx-4"
              onClick={(e) => e.stopPropagation()}
            >
              {actionPanel.children}
            </div>
          </div>
        )}

        {/* Global loading overlay */}
        {isLoading && <LoadingOverlay />}
      </div>
    </div>
  );
}
