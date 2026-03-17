'use client';

/**
 * FaultLensContent - Fault detail view (lens entity view).
 *
 * Renders inside EntityLensPage at /faults/{id}.
 * Reads all data and actions from useEntityLensContext() — zero props.
 *
 * Action gates follow the universal lens pattern: getAction returns null
 * when the server says the action is unavailable for this user/state.
 * Never inline getAction calls in JSX — store results as named consts.
 */

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { cn } from '@/lib/utils';
import { LensHeader, LensTitleBlock } from './LensHeader';
import { VitalSignsRow, type VitalSign } from '@/components/ui/VitalSignsRow';
import { formatRelativeTime } from '@/lib/utils';
import { SectionContainer } from '@/components/ui/SectionContainer';
import { PrimaryButton } from '@/components/ui/PrimaryButton';
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
} from '@/components/ui/dropdown-menu';
import { MoreHorizontal } from 'lucide-react';
import { GhostButton } from '@/components/ui/GhostButton';
import { AttachmentsSection, RelatedEntitiesSection, type Attachment, type RelatedEntity } from './sections';
import { useEntityLensContext } from '@/contexts/EntityLensContext';
import { getEntityRoute } from '@/lib/featureFlags';

// ---------------------------------------------------------------------------
// Colour helpers
// ---------------------------------------------------------------------------

function mapSeverityToColor(severity: string): 'critical' | 'warning' | 'success' | 'neutral' {
  switch (severity) {
    case 'critical': return 'critical';
    case 'high': return 'warning';
    case 'medium': return 'neutral';
    case 'low':
    default: return 'neutral';
  }
}

function mapStatusToColor(status: string): 'critical' | 'warning' | 'success' | 'neutral' {
  switch (status) {
    case 'open':
    case 'unresolved': return 'warning';
    case 'resolved':
    case 'closed': return 'success';
    default: return 'neutral';
  }
}

// ---------------------------------------------------------------------------
// FaultLensContent — zero props
// ---------------------------------------------------------------------------

export function FaultLensContent() {
  const router = useRouter();
  const { entity, executeAction, getAction, isLoading } = useEntityLensContext();

  // Input state for actions that require extra text
  const [showNoteInput, setShowNoteInput] = React.useState(false);
  const [noteText, setNoteText] = React.useState('');
  const [showCloseInput, setShowCloseInput] = React.useState(false);
  const [closeNotes, setCloseNotes] = React.useState('');
  const [showReopenInput, setShowReopenInput] = React.useState(false);
  const [reopenReason, setReopenReason] = React.useState('');

  // Map entity fields — access via entity?.field ?? default
  const payload = (entity?.payload as Record<string, unknown>) ?? {};
  const title = ((entity?.title ?? payload.title) as string | undefined) ?? 'Fault';
  const description = (entity?.description ?? payload.description) as string | undefined;
  const severity = ((entity?.severity ?? payload.severity) as string | undefined) ?? 'medium';
  const status = ((entity?.status ?? payload.status) as string | undefined) ?? 'open';
  const equipment_id = (entity?.equipment_id ?? payload.equipment_id) as string | undefined;
  const equipment_name = (entity?.equipment_name ?? payload.equipment_name) as string | undefined;
  const reported_by = (entity?.reported_by ?? payload.reported_by) as string | undefined;
  const reported_at = (entity?.reported_at ?? payload.reported_at) as string | undefined;
  const resolved_at = (entity?.resolved_at ?? payload.resolved_at) as string | undefined;
  const attachments = ((entity?.attachments ?? payload.attachments) as Attachment[] | undefined) ?? [];
  const related_entities = ((entity?.related_entities ?? payload.related_entities) as RelatedEntity[] | undefined) ?? [];

  const severityColor = mapSeverityToColor(severity);
  const statusColor = mapStatusToColor(status);

  // ---------------------------------------------------------------------------
  // Action gates — ALL stored as named consts, never inlined in JSX
  // ---------------------------------------------------------------------------
  const acknowledgeAction = getAction('acknowledge_fault');
  const closeFaultAction = getAction('close_fault');
  const reopenAction = getAction('reopen_fault');
  const falseAlarmAction = getAction('mark_fault_false_alarm');
  const addNoteAction = getAction('add_fault_note');
  const addPhotoAction = getAction('add_fault_photo');
  const createWOAction = getAction('create_work_order_from_fault');

  const hasAnyAction =
    acknowledgeAction !== null ||
    closeFaultAction !== null ||
    reopenAction !== null ||
    falseAlarmAction !== null ||
    createWOAction !== null ||
    addNoteAction !== null ||
    addPhotoAction !== null;

  // ---------------------------------------------------------------------------
  // Vital signs
  // ---------------------------------------------------------------------------
  const vitalSigns: VitalSign[] = [
    {
      label: 'Severity',
      value: severity.charAt(0).toUpperCase() + severity.slice(1),
      color: severityColor,
    },
    {
      label: 'Status',
      value: status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
      color: statusColor,
    },
    {
      label: 'Equipment',
      value: equipment_name ?? 'Unknown',
      onClick: equipment_id
        ? () => router.push(getEntityRoute('equipment', equipment_id))
        : undefined,
    },
    {
      label: 'Reporter',
      value: reported_by ?? 'Unknown',
    },
    {
      label: 'Reported',
      value: reported_at ? formatRelativeTime(reported_at) : '—',
    },
  ];

  // ---------------------------------------------------------------------------
  // Action handlers — executeAction triggers refetch automatically
  // ---------------------------------------------------------------------------

  const handleAcknowledge = React.useCallback(
    async () => executeAction('acknowledge_fault', {}),
    [executeAction]
  );

  const handleClose = React.useCallback(
    async () => {
      await executeAction('close_fault', { resolution_notes: closeNotes || undefined });
      setShowCloseInput(false);
      setCloseNotes('');
    },
    [executeAction, closeNotes]
  );

  const handleReopen = React.useCallback(
    async () => {
      await executeAction('reopen_fault', { reason: reopenReason || undefined });
      setShowReopenInput(false);
      setReopenReason('');
    },
    [executeAction, reopenReason]
  );

  const handleMarkFalseAlarm = React.useCallback(
    async () => executeAction('mark_fault_false_alarm', {}),
    [executeAction]
  );

  const handleAddNote = React.useCallback(
    async () => {
      if (!noteText.trim()) return;
      await executeAction('add_fault_note', { note_text: noteText });
      setShowNoteInput(false);
      setNoteText('');
    },
    [executeAction, noteText]
  );

  const handleCreateWO = React.useCallback(
    async () => executeAction('create_work_order_from_fault', {}),
    [executeAction]
  );

  // Navigation
  const handleBack = React.useCallback(() => router.back(), [router]);
  const handleClose_ = React.useCallback(() => router.push('/faults'), [router]);

  const handleNavigate = React.useCallback(
    (entityType: string, entityId: string) =>
      router.push(getEntityRoute(entityType as Parameters<typeof getEntityRoute>[0], entityId)),
    [router]
  );

  return (
    <div className="flex flex-col h-full">
      <LensHeader entityType="Fault" title={title} onBack={handleBack} onClose={handleClose_} />

      <main
        className={cn(
          'flex-1 overflow-y-auto',
          'pt-14',
          'px-10 md:px-6 sm:px-4',
          'max-w-[800px] mx-auto w-full',
          'pb-12'
        )}
      >
        {/* Title block */}
        <div className="mt-6">
          <LensTitleBlock
            title={title}
            subtitle={description}
            status={{ label: severity.charAt(0).toUpperCase() + severity.slice(1), color: severityColor }}
          />
        </div>

        {/* Vital signs */}
        <div className="mt-3">
          <VitalSignsRow signs={vitalSigns} />
        </div>

        {/* Actions */}
        {hasAnyAction && (
          <div className="mt-4 flex items-center gap-2">
            {/* Primary CTA — first available status transition */}
            {acknowledgeAction !== null && (
              <PrimaryButton
                onClick={handleAcknowledge}
                disabled={acknowledgeAction?.disabled ?? isLoading}
                title={acknowledgeAction?.disabled_reason ?? undefined}
                className="text-[13px] min-h-9 px-4 py-2"
              >
                {isLoading ? 'Acknowledging...' : 'Acknowledge'}
              </PrimaryButton>
            )}

            {closeFaultAction !== null && acknowledgeAction === null && !showCloseInput && (
              <PrimaryButton
                onClick={() => setShowCloseInput(true)}
                disabled={closeFaultAction?.disabled ?? isLoading}
                title={closeFaultAction?.disabled_reason ?? undefined}
                className="text-[13px] min-h-9 px-4 py-2"
              >
                Close Fault
              </PrimaryButton>
            )}

            {reopenAction !== null && (
              <PrimaryButton
                onClick={() => setShowReopenInput(true)}
                disabled={reopenAction?.disabled ?? isLoading}
                title={reopenAction?.disabled_reason ?? undefined}
                className="text-[13px] min-h-9 px-4 py-2"
              >
                Reopen
              </PrimaryButton>
            )}

            {/* Secondary actions dropdown */}
            {(falseAlarmAction !== null ||
              closeFaultAction !== null ||
              createWOAction !== null ||
              addNoteAction !== null ||
              addPhotoAction !== null) && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <GhostButton
                    className="text-[13px] min-h-9 px-3 py-2"
                    disabled={isLoading}
                    aria-label="More actions"
                  >
                    <MoreHorizontal className="w-4 h-4" />
                  </GhostButton>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="start" className="min-w-[180px]">
                  {closeFaultAction !== null && acknowledgeAction !== null && (
                    <DropdownMenuItem onClick={() => setShowCloseInput(true)}>
                      Close Fault
                    </DropdownMenuItem>
                  )}
                  {falseAlarmAction !== null && (
                    <DropdownMenuItem onClick={handleMarkFalseAlarm}>
                      Mark False Alarm
                    </DropdownMenuItem>
                  )}
                  {createWOAction !== null && (
                    <DropdownMenuItem onClick={handleCreateWO}>
                      Create Work Order
                    </DropdownMenuItem>
                  )}
                  {addNoteAction !== null && (
                    <DropdownMenuItem onClick={() => setShowNoteInput(true)}>
                      Add Note
                    </DropdownMenuItem>
                  )}
                  {addPhotoAction !== null && (
                    <DropdownMenuItem onClick={() => {}}>
                      Add Photo
                    </DropdownMenuItem>
                  )}
                </DropdownMenuContent>
              </DropdownMenu>
            )}
          </div>
        )}

        {/* Close fault inline form */}
        {showCloseInput && closeFaultAction !== null && (
          <div className="mt-3 flex flex-col gap-2">
            <textarea
              className="w-full rounded-md border border-surface-border bg-surface-raised p-2 text-[13px] text-celeste-text-primary placeholder:text-celeste-text-muted resize-none"
              rows={3}
              placeholder="Resolution notes (optional)"
              value={closeNotes}
              onChange={(e) => setCloseNotes(e.target.value)}
            />
            <div className="flex gap-2">
              <PrimaryButton
                onClick={handleClose}
                disabled={isLoading}
                className="text-[13px] min-h-8 px-3 py-1"
              >
                {isLoading ? 'Closing...' : 'Confirm Close'}
              </PrimaryButton>
              <GhostButton
                onClick={() => { setShowCloseInput(false); setCloseNotes(''); }}
                className="text-[13px] min-h-8 px-3 py-1"
              >
                Cancel
              </GhostButton>
            </div>
          </div>
        )}

        {/* Reopen inline form */}
        {showReopenInput && reopenAction !== null && (
          <div className="mt-3 flex flex-col gap-2">
            <textarea
              className="w-full rounded-md border border-surface-border bg-surface-raised p-2 text-[13px] text-celeste-text-primary placeholder:text-celeste-text-muted resize-none"
              rows={2}
              placeholder="Reason for reopening (optional)"
              value={reopenReason}
              onChange={(e) => setReopenReason(e.target.value)}
            />
            <div className="flex gap-2">
              <PrimaryButton
                onClick={handleReopen}
                disabled={isLoading}
                className="text-[13px] min-h-8 px-3 py-1"
              >
                {isLoading ? 'Reopening...' : 'Confirm Reopen'}
              </PrimaryButton>
              <GhostButton
                onClick={() => { setShowReopenInput(false); setReopenReason(''); }}
                className="text-[13px] min-h-8 px-3 py-1"
              >
                Cancel
              </GhostButton>
            </div>
          </div>
        )}

        {/* Add note inline form */}
        {showNoteInput && addNoteAction !== null && (
          <div className="mt-3 flex flex-col gap-2">
            <textarea
              className="w-full rounded-md border border-surface-border bg-surface-raised p-2 text-[13px] text-celeste-text-primary placeholder:text-celeste-text-muted resize-none"
              rows={3}
              placeholder="Note text"
              value={noteText}
              onChange={(e) => setNoteText(e.target.value)}
            />
            <div className="flex gap-2">
              <PrimaryButton
                onClick={handleAddNote}
                disabled={isLoading || !noteText.trim()}
                className="text-[13px] min-h-8 px-3 py-1"
              >
                {isLoading ? 'Adding...' : 'Add Note'}
              </PrimaryButton>
              <GhostButton
                onClick={() => { setShowNoteInput(false); setNoteText(''); }}
                className="text-[13px] min-h-8 px-3 py-1"
              >
                Cancel
              </GhostButton>
            </div>
          </div>
        )}

        <div className="mt-6 border-t border-surface-border" aria-hidden="true" />

        {/* Description section */}
        <div className="mt-6">
          <SectionContainer title="Description" stickyTop={56}>
            <p className="typo-body text-celeste-text-primary">
              {description || 'No description provided.'}
            </p>
          </SectionContainer>
        </div>

        {/* Resolution section */}
        {resolved_at && (
          <div className="mt-6">
            <SectionContainer title="Resolution" stickyTop={56}>
              <p className="typo-body text-celeste-text-muted">
                Resolved {formatRelativeTime(resolved_at)}
              </p>
            </SectionContainer>
          </div>
        )}

        {/* Attachments */}
        {attachments.length > 0 && (
          <div className="mt-6">
            <AttachmentsSection
              attachments={attachments}
              onAddFile={() => {}}
              canAddFile={addPhotoAction !== null}
              stickyTop={56}
            />
          </div>
        )}

        {/* Related entities */}
        {related_entities.length > 0 && (
          <div className="mt-6">
            <RelatedEntitiesSection
              entities={related_entities}
              onNavigate={handleNavigate}
              stickyTop={56}
            />
          </div>
        )}
      </main>
    </div>
  );
}
