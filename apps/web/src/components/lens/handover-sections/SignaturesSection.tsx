'use client';

/**
 * SignaturesSection
 *
 * Displays the dual-signature status for a handover:
 * - Outgoing crew signature (signs first after finalize)
 * - Incoming crew signature (signs second, after outgoing)
 * - Both signatures = complete status
 *
 * Read-only: no action button. Signing happens via the HandoverLens
 * action buttons which trigger SignaturePrompt overlay.
 *
 * Used by HandoverLens (FE-03-02).
 */

import * as React from 'react';
import { PenTool, CheckCircle2, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatDateTime } from '@/lib/utils';
import { SectionContainer, StatusPill } from '@/components/ui';
import type { HandoverSignature, HandoverStatus } from '../types';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface SignaturesSectionProps {
  outgoingSignature?: HandoverSignature;
  incomingSignature?: HandoverSignature;
  outgoingCrewName?: string;
  incomingCrewName?: string;
  status: HandoverStatus;
  stickyTop?: number;
}

// ---------------------------------------------------------------------------
// SignatureCard sub-component
// ---------------------------------------------------------------------------

interface SignatureCardProps {
  role: 'outgoing' | 'incoming';
  crewName?: string;
  signature?: HandoverSignature;
  /** Incoming is blocked until outgoing has signed */
  isBlocked?: boolean;
}

function SignatureCard({ role, crewName, signature, isBlocked }: SignatureCardProps) {
  const isSigned = !!signature;
  const label = role === 'outgoing' ? 'Outgoing Crew' : 'Incoming Crew';
  const displayName = signature?.user_name ?? crewName ?? 'Unassigned';

  return (
    <div
      className={cn(
        'p-4 rounded-md border',
        isSigned
          ? 'border-status-success/30 bg-status-success-bg'
          : isBlocked
          ? 'border-surface-border-subtle bg-surface-hover opacity-60'
          : 'border-surface-border-subtle bg-surface-primary'
      )}
    >
      {/* Role label + signed indicator */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          {isSigned ? (
            <CheckCircle2 className="h-4 w-4 text-status-success" />
          ) : (
            <Clock className="h-4 w-4 text-txt-tertiary" />
          )}
          <span className="text-[12px] font-semibold text-txt-secondary uppercase tracking-wide">
            {label}
          </span>
        </div>
        {isSigned && (
          <StatusPill status="success" label="Signed" showDot />
        )}
        {!isSigned && isBlocked && (
          <StatusPill status="neutral" label="Waiting" showDot />
        )}
        {!isSigned && !isBlocked && (
          <StatusPill status="warning" label="Awaiting" showDot />
        )}
      </div>

      {/* Crew name + signed-at */}
      {isSigned ? (
        <div className="space-y-1">
          <p className="text-[14px] text-txt-primary font-medium">{displayName}</p>
          <p className="text-[12px] text-txt-tertiary">
            Signed {formatDateTime(signature!.signed_at)}
          </p>
        </div>
      ) : (
        <div className="space-y-1">
          <p className="text-[14px] text-txt-secondary">{displayName}</p>
          <p className="text-[12px] text-txt-tertiary">
            {isBlocked
              ? 'Waiting for outgoing signature first'
              : 'Awaiting signature'}
          </p>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// SignaturesSection
// ---------------------------------------------------------------------------

/**
 * SignaturesSection
 *
 * Shows two side-by-side signature cards: outgoing and incoming.
 * Displays completion state when both signatures are present.
 */
export function SignaturesSection({
  outgoingSignature,
  incomingSignature,
  outgoingCrewName,
  incomingCrewName,
  status,
  stickyTop = 0,
}: SignaturesSectionProps) {
  const bothSigned = !!outgoingSignature && !!incomingSignature;
  const outgoingHasSigned = !!outgoingSignature;
  const isDraft = status === 'draft';

  return (
    <SectionContainer
      title="Signatures"
      icon={<PenTool className="h-5 w-5" />}
      stickyTop={stickyTop}
    >
      {isDraft ? (
        /* Draft state: signatures not yet in scope */
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <div className="w-12 h-12 rounded-md bg-surface-hover flex items-center justify-center mb-3">
            <PenTool className="h-6 w-6 text-txt-tertiary" />
          </div>
          <p className="text-txt-primary font-medium mb-1">Finalize to begin signing</p>
          <p className="text-txt-tertiary text-[13px]">
            Finalizing the handover locks items and opens the signature flow.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Completion banner */}
          {bothSigned && (
            <div className="flex items-center gap-2 p-3 rounded-md border border-status-success/30 bg-status-success-bg text-status-success text-[13px] font-medium">
              <CheckCircle2 className="h-4 w-4" />
              <span>Handover complete — both signatures collected</span>
            </div>
          )}

          {/* Signature cards — side by side on desktop */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-1">
            <SignatureCard
              role="outgoing"
              crewName={outgoingCrewName}
              signature={outgoingSignature}
            />
            <SignatureCard
              role="incoming"
              crewName={incomingCrewName}
              signature={incomingSignature}
              isBlocked={!outgoingHasSigned}
            />
          </div>

          {/* Sequence explanation — only while signatures are pending */}
          {!bothSigned && (
            <p className="text-[12px] text-txt-tertiary">
              Outgoing crew signs first to acknowledge the handover.
              Incoming crew then signs to confirm receipt.
            </p>
          )}
        </div>
      )}
    </SectionContainer>
  );
}
