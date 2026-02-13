'use client';

/**
 * Lens Component Library
 * Shared components for entity lens pages
 * Created as stubs to resolve build errors - to be fully implemented
 */

import React from 'react';
import { cn } from '@/lib/utils';
import { ArrowLeft, Loader2, AlertCircle } from 'lucide-react';

// ============================================================================
// TYPES
// ============================================================================

export interface LensBadge {
  bg: string;
  text: string;
  label: string;
}

interface BaseLensPageProps {
  entityType: string;
  entityIcon: React.ReactNode;
  title: string;
  badges?: LensBadge[];
  onBack?: () => void;
  metadata?: React.ReactNode;
  relatedSection?: React.ReactNode;
  children: React.ReactNode;
}

interface LensSectionProps {
  title: string;
  children: React.ReactNode;
  className?: string;
}

interface LensDetailCardProps {
  icon: React.ReactNode;
  label: string;
  value: React.ReactNode;
}

// ============================================================================
// LOADING COMPONENT
// ============================================================================

export function LensLoading({ message = 'Loading...' }: { message?: string }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-celeste-bg">
      <div className="flex flex-col items-center gap-4">
        <Loader2 className="h-8 w-8 text-celeste-accent animate-spin" />
        <p className="text-celeste-text-muted text-celeste-sm">{message}</p>
      </div>
    </div>
  );
}

// ============================================================================
// ERROR COMPONENT
// ============================================================================

export function LensError({
  error,
  onReturnToApp
}: {
  error: string;
  onReturnToApp?: () => void;
}) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-celeste-bg">
      <div className="flex flex-col items-center gap-4 max-w-md text-center px-4">
        <AlertCircle className="h-12 w-12 text-restricted-red" />
        <h2 className="text-celeste-lg font-semibold text-celeste-text-title">Error</h2>
        <p className="text-celeste-text-muted text-celeste-sm">{error}</p>
        {onReturnToApp && (
          <button
            onClick={onReturnToApp}
            className="px-4 py-2 rounded-celeste-md bg-celeste-accent text-celeste-text-title text-celeste-sm"
          >
            Return to App
          </button>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// BASE LENS PAGE
// ============================================================================

export function BaseLensPage({
  entityType,
  entityIcon,
  title,
  badges = [],
  onBack,
  metadata,
  relatedSection,
  children,
}: BaseLensPageProps) {
  return (
    <div className="min-h-screen bg-celeste-bg">
      {/* Header */}
      <header className="sticky top-0 z-10 bg-celeste-surface border-b border-celeste-border px-4 py-3">
        <div className="max-w-4xl mx-auto flex items-center gap-4">
          {onBack && (
            <button
              onClick={onBack}
              className="p-2 rounded-celeste-md hover:bg-celeste-surface-hover transition-colors"
            >
              <ArrowLeft className="h-5 w-5 text-celeste-text-muted" />
            </button>
          )}
          <div className="flex items-center gap-2">
            {entityIcon}
            <span className="text-celeste-sm text-celeste-text-muted">{entityType}</span>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-4xl mx-auto px-4 py-6">
        {/* Title Section */}
        <div className="mb-6">
          <h1 className="text-celeste-xl font-semibold text-celeste-text-title mb-2">{title}</h1>
          {badges.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-3">
              {badges.map((badge, i) => (
                <span key={i} className={cn('px-2 py-1 rounded-celeste-md text-celeste-xs', badge.bg, badge.text)}>
                  {badge.label}
                </span>
              ))}
            </div>
          )}
          {metadata}
        </div>

        {/* Main Content */}
        {children}

        {/* Related Section */}
        {relatedSection && (
          <div className="mt-8 pt-6 border-t border-celeste-border">
            {relatedSection}
          </div>
        )}
      </main>
    </div>
  );
}

// ============================================================================
// SECTION COMPONENT
// ============================================================================

export function LensSection({ title, children, className }: LensSectionProps) {
  return (
    <section className={cn('mb-6', className)}>
      <h2 className="text-celeste-base font-medium text-celeste-text-title mb-3">{title}</h2>
      {children}
    </section>
  );
}

// ============================================================================
// DETAILS GRID
// ============================================================================

export function LensDetailsGrid({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {children}
    </div>
  );
}

// ============================================================================
// DETAIL CARD
// ============================================================================

export function LensDetailCard({ icon, label, value }: LensDetailCardProps) {
  return (
    <div className="p-4 rounded-celeste-lg bg-celeste-surface border border-celeste-border">
      <div className="flex items-center gap-2 mb-2">
        {icon}
        <span className="text-celeste-xs text-celeste-text-muted">{label}</span>
      </div>
      <div className="text-celeste-sm text-celeste-text-title">{value}</div>
    </div>
  );
}
