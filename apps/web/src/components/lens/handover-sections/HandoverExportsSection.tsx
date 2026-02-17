'use client';

/**
 * HandoverExportsSection
 *
 * Displays handover export history with dual-signature tracking.
 * Each export shows outgoing + incoming signature status side-by-side.
 * Download links appear when file_url is present.
 *
 * Export to PDF is only available when handover status = complete
 * (enforced in HandoverLens permission gates).
 *
 * Used by HandoverLens (FE-03-02).
 */

import * as React from 'react';
import {
  PenTool,
  FileText,
  Download,
  ExternalLink,
  Clock,
  CheckCircle2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatDate, formatDateTime } from '@/lib/utils';
import { SectionContainer, StatusPill, GhostButton } from '@/components/ui';
import type { HandoverExport } from '../HandoverLens';

// ---------------------------------------------------------------------------
// HandoverExportRow
// ---------------------------------------------------------------------------

interface HandoverExportRowProps {
  export_: HandoverExport;
  onView?: (exportId: string) => void;
}

function HandoverExportRow({ export_, onView }: HandoverExportRowProps) {
  const isFullySigned = export_.signoff_complete;
  const hasOutgoingSignature = !!export_.outgoing_signed_at;
  const hasIncomingSignature = !!export_.incoming_signed_at;

  return (
    <div className="p-4 rounded-sm border border-surface-border-subtle bg-surface-primary hover:bg-surface-hover transition-colors">
      <div className="flex items-start justify-between gap-4">
        {/* Export info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <FileText className="h-4 w-4 text-txt-secondary" />
            <span className="text-[14px] font-medium text-txt-primary">
              Handover Export — {formatDate(export_.export_date)}
            </span>
            {export_.department && (
              <span className="text-[11px] px-2 py-0.5 rounded-full bg-status-neutral-bg text-status-neutral">
                {export_.department}
              </span>
            )}
            {isFullySigned && (
              <StatusPill status="success" label="Complete" showDot />
            )}
          </div>

          {/* Signature status — side by side */}
          <div className="grid grid-cols-2 gap-3 mt-3">
            {/* Outgoing signature */}
            <div
              className={cn(
                'p-3 rounded-sm border',
                hasOutgoingSignature
                  ? 'border-status-success/30 bg-status-success-bg'
                  : 'border-surface-border-subtle bg-surface-hover'
              )}
            >
              <div className="flex items-center gap-2 mb-1">
                {hasOutgoingSignature ? (
                  <CheckCircle2 className="h-4 w-4 text-status-success" />
                ) : (
                  <Clock className="h-4 w-4 text-txt-tertiary" />
                )}
                <span className="text-[12px] font-semibold text-txt-secondary uppercase tracking-wide">
                  Outgoing
                </span>
              </div>
              {hasOutgoingSignature ? (
                <div className="text-[13px]">
                  <p className="text-txt-primary font-medium">
                    {export_.outgoing_user_name || 'Signed'}
                  </p>
                  <p className="text-txt-tertiary text-[12px]">
                    {formatDateTime(export_.outgoing_signed_at!)}
                  </p>
                </div>
              ) : (
                <p className="text-[13px] text-txt-tertiary">Awaiting signature</p>
              )}
            </div>

            {/* Incoming signature */}
            <div
              className={cn(
                'p-3 rounded-sm border',
                hasIncomingSignature
                  ? 'border-status-success/30 bg-status-success-bg'
                  : 'border-surface-border-subtle bg-surface-hover'
              )}
            >
              <div className="flex items-center gap-2 mb-1">
                {hasIncomingSignature ? (
                  <CheckCircle2 className="h-4 w-4 text-status-success" />
                ) : (
                  <Clock className="h-4 w-4 text-txt-tertiary" />
                )}
                <span className="text-[12px] font-semibold text-txt-secondary uppercase tracking-wide">
                  Incoming
                </span>
              </div>
              {hasIncomingSignature ? (
                <div className="text-[13px]">
                  <p className="text-txt-primary font-medium">
                    {export_.incoming_user_name || 'Signed'}
                  </p>
                  <p className="text-txt-tertiary text-[12px]">
                    {formatDateTime(export_.incoming_signed_at!)}
                  </p>
                </div>
              ) : (
                <p className="text-[13px] text-txt-tertiary">Awaiting signature</p>
              )}
            </div>
          </div>
        </div>

        {/* Download + view actions */}
        <div className="flex-shrink-0 flex items-center gap-2">
          {export_.file_url && (
            <a
              href={export_.file_url}
              target="_blank"
              rel="noopener noreferrer"
              className="p-2 text-txt-tertiary hover:text-brand-interactive transition-colors"
              aria-label="Download PDF"
            >
              <Download className="h-4 w-4" />
            </a>
          )}
          <button
            onClick={() => onView?.(export_.id)}
            className="p-2 text-txt-tertiary hover:text-brand-interactive transition-colors"
            aria-label="View export"
          >
            <ExternalLink className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// HandoverExportsSection
// ---------------------------------------------------------------------------

export interface HandoverExportsSectionProps {
  exports: HandoverExport[];
  /** Present only when handover is complete + canExport */
  onExport?: () => void;
  onViewExport?: (exportId: string) => void;
  stickyTop?: number;
}

/**
 * HandoverExportsSection
 *
 * Shows export history for the handover.
 * "Export to PDF" CTA is only shown when `onExport` is provided
 * (HandoverLens gates this on status=complete + canExport permission).
 */
export function HandoverExportsSection({
  exports,
  onExport,
  onViewExport,
  stickyTop = 0,
}: HandoverExportsSectionProps) {
  const hasExports = exports.length > 0;
  const pendingSignoffs = exports.filter((e) => !e.signoff_complete).length;

  return (
    <SectionContainer
      title="Exports & Signatures"
      icon={<PenTool className="h-5 w-5" />}
      count={hasExports ? exports.length : undefined}
      action={onExport ? { label: 'Export PDF', onClick: onExport } : undefined}
      stickyTop={stickyTop}
    >
      {!hasExports ? (
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <div className="w-12 h-12 rounded-md bg-surface-hover flex items-center justify-center mb-3">
            <PenTool className="h-6 w-6 text-txt-tertiary" />
          </div>
          <p className="text-txt-primary font-medium mb-1">No exports yet</p>
          <p className="text-txt-tertiary text-[13px] mb-4">
            {onExport
              ? 'Export the handover to PDF to collect signatures.'
              : 'Exports are available after the handover is complete.'}
          </p>
          {onExport && (
            <GhostButton onClick={onExport} icon={<Download className="h-4 w-4" />}>
              Export to PDF
            </GhostButton>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {pendingSignoffs > 0 && (
            <div className="flex items-center gap-2 p-2 rounded-sm bg-status-warning-bg text-status-warning text-[13px]">
              <Clock className="h-4 w-4" />
              <span>
                {pendingSignoffs} export{pendingSignoffs > 1 ? 's' : ''} awaiting signature
              </span>
            </div>
          )}
          {exports.map((exp) => (
            <HandoverExportRow
              key={exp.id}
              export_={exp}
              onView={onViewExport}
            />
          ))}
        </div>
      )}
    </SectionContainer>
  );
}
