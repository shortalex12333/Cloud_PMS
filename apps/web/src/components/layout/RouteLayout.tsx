'use client';

import React from 'react';
import { cn } from '@/lib/utils';

/**
 * RouteLayout - Shared layout template for all Tier 1 fragmented routes
 *
 * Replaces the single-URL SurfaceContext/NavigationContext architecture.
 * Each route composes its own content using this layout shell.
 *
 * @see REQUIREMENTS_TABLE.md - LT-01, LT-02, LT-03
 */

export interface PrimaryPanelConfig {
  /** Whether the panel is visible */
  visible: boolean;
  /** Panel header title */
  title: string;
  /** Optional subtitle */
  subtitle?: string;
  /** Panel content */
  children: React.ReactNode;
}

export interface ContextPanelConfig {
  /** Whether the panel is visible */
  visible: boolean;
  /** Panel content */
  children: React.ReactNode;
}

export interface ActionPanelConfig {
  /** Whether the panel is visible */
  visible: boolean;
  /** Optional title for the action sheet */
  title?: string;
  /** Panel content */
  children: React.ReactNode;
}

export interface RouteLayoutProps {
  /** Page title shown in top nav */
  pageTitle?: string;

  /** Main content - list view, detail view, or custom */
  children: React.ReactNode;

  /** Optional right slide-over panel (detail/context) */
  primaryPanel?: PrimaryPanelConfig;

  /** Optional secondary panel (related artifacts, sidebar) */
  contextPanel?: ContextPanelConfig;

  /** Optional action panel (bottom sheet, modal) */
  actionPanel?: ActionPanelConfig;

  /** Callback when primary panel close is clicked */
  onClosePrimaryPanel?: () => void;

  /** Callback when context panel close is clicked */
  onCloseContextPanel?: () => void;

  /** Callback when action panel close is clicked */
  onCloseActionPanel?: () => void;

  /** Optional loading state */
  isLoading?: boolean;

  /** Show/hide top nav bar (default: true) */
  showTopNav?: boolean;

  /** Custom top nav content (replaces default) */
  topNavContent?: React.ReactNode;

  /** Additional class names for the root container */
  className?: string;
}

/**
 * Loading skeleton component
 */
function LoadingState() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="flex flex-col items-center gap-4">
        <div className="w-8 h-8 border-2 border-white/20 border-t-white/80 rounded-full animate-spin" />
        <p className="text-sm text-white/60">Loading...</p>
      </div>
    </div>
  );
}

/**
 * Close button component
 */
function CloseButton({ onClick, label = 'Close' }: { onClick: () => void; label?: string }) {
  return (
    <button
      onClick={onClick}
      className="p-2 text-white/60 hover:text-white/90 hover:bg-white/5 rounded-lg transition-colors"
      aria-label={label}
    >
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M18 6L6 18M6 6l12 12" />
      </svg>
    </button>
  );
}

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
  return (
    <div className={cn('h-screen flex flex-col bg-[#0a0a0a]', className)}>
      {/* Top Nav Bar */}
      {showTopNav && (
        <header className="h-16 flex-shrink-0 border-b border-white/10 flex items-center px-6 bg-[#111111]">
          {topNavContent || (
            <div className="flex items-center gap-4">
              <h1 className="text-lg font-semibold text-white">{pageTitle}</h1>
            </div>
          )}
        </header>
      )}

      {/* Main content area - flex container for list + panels */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Primary Content (List or Main View) */}
        <main
          className={cn(
            'flex-1 overflow-auto transition-all duration-300',
            // On mobile, hide when primary panel is open
            primaryPanel?.visible && 'hidden md:block md:flex-1'
          )}
        >
          {isLoading ? <LoadingState /> : children}
        </main>

        {/* Primary Panel - Right slide-over (detail view) */}
        {primaryPanel && (
          <aside
            className={cn(
              // Position and sizing
              'absolute inset-y-0 right-0 w-full md:relative md:w-[480px] lg:w-[560px]',
              // Styling
              'bg-[#111111] border-l border-white/10',
              // Animation
              'transform transition-all duration-300 ease-out',
              // Layout
              'flex flex-col',
              // Visibility
              primaryPanel.visible
                ? 'translate-x-0 z-10'
                : 'translate-x-full pointer-events-none opacity-0'
            )}
          >
            {/* Panel Header */}
            <div className="h-14 flex items-center justify-between px-6 border-b border-white/10 flex-shrink-0">
              <div className="flex-1 min-w-0">
                <h2 className="text-base font-medium text-white truncate">
                  {primaryPanel.title}
                </h2>
                {primaryPanel.subtitle && (
                  <p className="text-sm text-white/60 truncate">
                    {primaryPanel.subtitle}
                  </p>
                )}
              </div>
              {onClosePrimaryPanel && (
                <CloseButton onClick={onClosePrimaryPanel} />
              )}
            </div>

            {/* Panel Content */}
            <div className="flex-1 overflow-auto">
              {primaryPanel.children}
            </div>
          </aside>
        )}

        {/* Context Panel - Secondary sidebar (related artifacts) */}
        {contextPanel && (
          <aside
            className={cn(
              // Position and sizing - only visible on large screens
              'hidden xl:flex absolute xl:relative right-0 w-80',
              // Styling
              'bg-[#0d0d0d] border-l border-white/10',
              // Layout
              'flex-col',
              // Animation
              'transition-all duration-300',
              // Visibility
              contextPanel.visible
                ? 'opacity-100'
                : 'opacity-0 pointer-events-none'
            )}
          >
            {onCloseContextPanel && (
              <div className="p-4 flex justify-end border-b border-white/10">
                <CloseButton onClick={onCloseContextPanel} label="Close context" />
              </div>
            )}
            <div className="flex-1 overflow-auto">
              {contextPanel.children}
            </div>
          </aside>
        )}
      </div>

      {/* Action Panel - Bottom sheet / modal overlay */}
      {actionPanel && (
        <div
          className={cn(
            // Overlay
            'fixed inset-0 bg-black/60 backdrop-blur-sm z-50',
            // Animation
            'transition-opacity duration-300',
            // Visibility
            actionPanel.visible
              ? 'opacity-100'
              : 'opacity-0 pointer-events-none'
          )}
          onClick={onCloseActionPanel}
        >
          <div
            className="absolute bottom-0 left-0 right-0 bg-[#111111] rounded-t-2xl max-h-[80vh] overflow-auto"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Action Panel Header */}
            {actionPanel.title && (
              <div className="p-6 border-b border-white/10 flex items-center justify-between">
                <h3 className="text-lg font-medium text-white">{actionPanel.title}</h3>
                {onCloseActionPanel && (
                  <CloseButton onClick={onCloseActionPanel} />
                )}
              </div>
            )}

            {/* Action Panel Content */}
            <div className="p-6">
              {actionPanel.children}
            </div>

            {/* Action Panel Footer */}
            {onCloseActionPanel && !actionPanel.title && (
              <button
                onClick={onCloseActionPanel}
                className="w-full py-4 text-center text-white/60 hover:text-white hover:bg-white/5 border-t border-white/10 transition-colors"
              >
                Close
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default RouteLayout;
