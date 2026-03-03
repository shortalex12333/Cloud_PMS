'use client';

/**
 * EmailLensContent - Inner content for Email lens (no LensContainer).
 *
 * Designed to render inside ContextPanel following the 1-URL philosophy.
 * Per rules.md: No fragmented URLs, everything at app.celeste7.ai.
 *
 * This component wraps EmailThreadViewer for SPA mode rendering.
 */

import * as React from 'react';
import { LensHeader, LensTitleBlock } from './LensHeader';
import { VitalSignsRow, type VitalSign } from '@/components/ui/VitalSignsRow';
import { EmailThreadViewer } from '@/components/email/EmailThreadViewer';
import { useEmailPermissions } from '@/hooks/permissions/useEmailPermissions';
import { useThread } from '@/hooks/useEmailData';
import { AlertCircle, Loader2, Mail } from 'lucide-react';
import { formatRelativeTime } from '@/lib/utils';

// ---------------------------------------------------------------------------
// Props interface
// ---------------------------------------------------------------------------

export interface EmailLensContentProps {
  id: string;
  data: Record<string, unknown>;
  onBack: () => void;
  onClose: () => void;
  onNavigate?: (entityType: string, entityId: string) => void;
  onRefresh?: () => void;
}

/**
 * EmailLensContent - SPA mode wrapper for email threads
 *
 * Delegates to EmailThreadViewer for actual thread rendering.
 * Provides LensHeader and VitalSigns for consistency with other lenses.
 */
export function EmailLensContent({
  id,
  data,
  onBack,
  onClose,
  onNavigate,
  onRefresh,
}: EmailLensContentProps) {
  const permissions = useEmailPermissions();
  const { data: thread, isLoading, error, refetch } = useThread(id);

  // Handle refresh
  const handleRefresh = React.useCallback(() => {
    refetch();
    onRefresh?.();
  }, [refetch, onRefresh]);

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex items-center gap-2 text-celeste-text-muted">
          <Loader2 className="h-5 w-5 animate-spin" />
          <span>Loading email thread...</span>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="p-6">
        <div className="flex items-start gap-3 p-4 bg-red-50 dark:bg-red-900/20 rounded">
          <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-medium text-red-700 dark:text-red-400">
              Failed to load email thread
            </p>
            <p className="text-sm text-red-600 dark:text-red-500 mt-1">
              {error instanceof Error ? error.message : 'Unknown error'}
            </p>
            <button
              onClick={handleRefresh}
              className="text-sm text-red-500 hover:text-red-600 mt-2 underline"
            >
              Try again
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!thread) {
    return (
      <div className="p-6 text-center text-celeste-text-muted">
        <Mail className="h-12 w-12 mx-auto mb-3 opacity-50" />
        <p>Email thread not found</p>
      </div>
    );
  }

  // Build vital signs
  const vitalSigns: VitalSign[] = [
    {
      label: 'Messages',
      value: thread.message_count.toString(),
    },
    {
      label: 'Source',
      value: thread.source === 'outlook' ? 'Outlook' : thread.source,
    },
  ];

  // Add attachment indicator if present
  if (thread.has_attachments) {
    vitalSigns.push({
      label: 'Attachments',
      value: 'Yes',
    });
  }

  // Add last activity timestamp
  if (thread.last_activity_at) {
    vitalSigns.push({
      label: 'Last Activity',
      value: formatRelativeTime(thread.last_activity_at),
    });
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <LensHeader
        entityType="Email"
        title={thread.latest_subject || '(No subject)'}
        subtitle={`Thread with ${thread.message_count} message${thread.message_count !== 1 ? 's' : ''}`}
        onBack={onBack}
        onClose={onClose}
      />

      {/* Vital Signs */}
      <div className="px-4 py-3 border-b border-zinc-200 dark:border-zinc-800">
        <VitalSignsRow signs={vitalSigns} />
      </div>

      {/* Thread Viewer */}
      <div className="flex-1 overflow-y-auto">
        <EmailThreadViewer threadId={id} />
      </div>
    </div>
  );
}
