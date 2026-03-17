'use client';

/**
 * EquipmentLensContent - Equipment detail view (lens entity view).
 *
 * Renders inside EntityLensPage at /equipment/{id}.
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
import { GhostButton } from '@/components/ui/GhostButton';
import { AttachmentsSection, RelatedEntitiesSection, type Attachment, type RelatedEntity } from './sections';
import { useEntityLensContext } from '@/contexts/EntityLensContext';
import { getEntityRoute } from '@/lib/featureFlags';

// ---------------------------------------------------------------------------
// Colour helper
// ---------------------------------------------------------------------------

function mapStatusToColor(status: string): 'critical' | 'warning' | 'success' | 'neutral' {
  switch (status) {
    case 'faulty':
    case 'offline': return 'critical';
    case 'maintenance': return 'warning';
    case 'operational': return 'success';
    default: return 'neutral';
  }
}

// ---------------------------------------------------------------------------
// EquipmentLensContent — zero props
// ---------------------------------------------------------------------------

export function EquipmentLensContent() {
  const router = useRouter();
  const { entity, executeAction, getAction, isLoading } = useEntityLensContext();

  // Input state for actions requiring extra text
  const [showNoteInput, setShowNoteInput] = React.useState(false);
  const [noteText, setNoteText] = React.useState('');
  const [showStatusInput, setShowStatusInput] = React.useState(false);
  const [statusValue, setStatusValue] = React.useState('operational');
  const [showDecommissionInput, setShowDecommissionInput] = React.useState(false);
  const [decommissionReason, setDecommissionReason] = React.useState('');

  // ---------------------------------------------------------------------------
  // Entity fields — access via entity?.field ?? default
  // ---------------------------------------------------------------------------
  const payload = (entity?.payload as Record<string, unknown>) ?? {};
  const name = ((entity?.name ?? payload.name) as string | undefined) ?? 'Equipment';
  const equipment_type = ((entity?.equipment_type ?? payload.equipment_type ?? entity?.category ?? payload.category) as string | undefined) ?? 'General';
  const manufacturer = (entity?.manufacturer ?? payload.manufacturer) as string | undefined;
  const model = (entity?.model ?? payload.model) as string | undefined;
  const serial_number = (entity?.serial_number ?? payload.serial_number) as string | undefined;
  const location = ((entity?.location ?? payload.location) as string | undefined) ?? 'Unknown';
  const status = ((entity?.status ?? payload.status) as string | undefined) ?? 'operational';
  const installation_date = (entity?.installation_date ?? payload.installation_date) as string | undefined;
  const last_maintenance = (entity?.last_maintenance ?? payload.last_maintenance) as string | undefined;
  const next_maintenance = (entity?.next_maintenance ?? payload.next_maintenance) as string | undefined;
  const attachments = ((entity?.attachments ?? payload.attachments) as Attachment[] | undefined) ?? [];
  const related_entities = ((entity?.related_entities ?? payload.related_entities) as RelatedEntity[] | undefined) ?? [];

  const statusColor = mapStatusToColor(status);

  // ---------------------------------------------------------------------------
  // Action gates — ALL stored as named consts, never inlined in JSX
  // ---------------------------------------------------------------------------
  const decommissionAction = getAction('decommission_equipment');
  const flagAction = getAction('flag_equipment_attention');
  const updateStatusAction = getAction('update_equipment_status');
  const addNoteAction = getAction('add_equipment_note');
  const createWOAction = getAction('create_work_order_for_equipment');

  const hasAnyAction =
    decommissionAction !== null ||
    flagAction !== null ||
    updateStatusAction !== null ||
    addNoteAction !== null ||
    createWOAction !== null;

  // ---------------------------------------------------------------------------
  // Vital signs
  // ---------------------------------------------------------------------------
  const vitalSigns: VitalSign[] = [
    {
      label: 'Status',
      value: status.charAt(0).toUpperCase() + status.slice(1),
      color: statusColor,
    },
    { label: 'Type', value: equipment_type },
    { label: 'Location', value: location },
    { label: 'Manufacturer', value: manufacturer ?? '—' },
    { label: 'Model', value: model ?? '—' },
  ];

  // ---------------------------------------------------------------------------
  // Action handlers — executeAction triggers refetch automatically
  // ---------------------------------------------------------------------------

  const handleCreateWO = React.useCallback(
    async () => executeAction('create_work_order_for_equipment', {}),
    [executeAction]
  );

  const handleFlag = React.useCallback(
    async () => executeAction('flag_equipment_attention', {}),
    [executeAction]
  );

  const handleUpdateStatus = React.useCallback(
    async () => {
      await executeAction('update_equipment_status', { status: statusValue });
      setShowStatusInput(false);
      setStatusValue('operational');
    },
    [executeAction, statusValue]
  );

  const handleAddNote = React.useCallback(
    async () => {
      if (!noteText.trim()) return;
      await executeAction('add_equipment_note', { note_text: noteText });
      setShowNoteInput(false);
      setNoteText('');
    },
    [executeAction, noteText]
  );

  const handleDecommission = React.useCallback(
    async () => {
      if (!decommissionReason.trim()) return;
      await executeAction('decommission_equipment', { reason: decommissionReason });
      setShowDecommissionInput(false);
      setDecommissionReason('');
    },
    [executeAction, decommissionReason]
  );

  // Navigation
  const handleBack = React.useCallback(() => router.back(), [router]);
  const handleClose = React.useCallback(() => router.push('/equipment'), [router]);

  const handleNavigate = React.useCallback(
    (entityType: string, entityId: string) =>
      router.push(getEntityRoute(entityType as Parameters<typeof getEntityRoute>[0], entityId)),
    [router]
  );

  return (
    <div className="flex flex-col h-full">
      <LensHeader entityType="Equipment" title={name} onBack={handleBack} onClose={handleClose} />

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
            title={name}
            subtitle={manufacturer && model ? `${manufacturer} ${model}` : undefined}
            status={{ label: status.charAt(0).toUpperCase() + status.slice(1), color: statusColor }}
          />
        </div>

        {/* Vital signs */}
        <div className="mt-3">
          <VitalSignsRow signs={vitalSigns} />
        </div>

        {/* Actions */}
        {hasAnyAction && (
          <div className="mt-4 flex items-center gap-2 flex-wrap">
            {createWOAction !== null && (
              <PrimaryButton
                onClick={handleCreateWO}
                disabled={createWOAction?.disabled ?? isLoading}
                title={createWOAction?.disabled_reason ?? undefined}
                className="text-[13px] min-h-9 px-4 py-2"
              >
                Create Work Order
              </PrimaryButton>
            )}

            {updateStatusAction !== null && !showStatusInput && (
              <GhostButton
                onClick={() => setShowStatusInput(true)}
                disabled={updateStatusAction?.disabled ?? isLoading}
                title={updateStatusAction?.disabled_reason ?? undefined}
                className="text-[13px] min-h-9 px-4 py-2"
              >
                Update Status
              </GhostButton>
            )}

            {flagAction !== null && (
              <GhostButton
                onClick={handleFlag}
                disabled={flagAction?.disabled ?? isLoading}
                title={flagAction?.disabled_reason ?? undefined}
                className="text-[13px] min-h-9 px-4 py-2"
              >
                Flag Attention
              </GhostButton>
            )}

            {addNoteAction !== null && !showNoteInput && (
              <GhostButton
                onClick={() => setShowNoteInput(true)}
                disabled={addNoteAction?.disabled ?? isLoading}
                title={addNoteAction?.disabled_reason ?? undefined}
                className="text-[13px] min-h-9 px-4 py-2"
              >
                Add Note
              </GhostButton>
            )}

            {decommissionAction !== null && !showDecommissionInput && (
              <GhostButton
                onClick={() => setShowDecommissionInput(true)}
                disabled={decommissionAction?.disabled ?? isLoading}
                title={decommissionAction?.disabled_reason ?? undefined}
                className="text-[13px] min-h-9 px-4 py-2"
              >
                Decommission
              </GhostButton>
            )}
          </div>
        )}

        {/* Update status inline form */}
        {showStatusInput && updateStatusAction !== null && (
          <div className="mt-3 flex flex-col gap-2">
            <select
              className="w-full rounded-md border border-surface-border bg-surface-raised px-3 py-2 text-[13px] text-celeste-text-primary"
              value={statusValue}
              onChange={(e) => setStatusValue(e.target.value)}
            >
              <option value="operational">Operational</option>
              <option value="maintenance">Maintenance</option>
              <option value="faulty">Faulty</option>
              <option value="offline">Offline</option>
            </select>
            <div className="flex gap-2">
              <PrimaryButton
                onClick={handleUpdateStatus}
                disabled={isLoading}
                className="text-[13px] min-h-8 px-3 py-1"
              >
                {isLoading ? 'Updating...' : 'Confirm Status'}
              </PrimaryButton>
              <GhostButton
                onClick={() => { setShowStatusInput(false); setStatusValue('operational'); }}
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

        {/* Decommission inline form */}
        {showDecommissionInput && decommissionAction !== null && (
          <div className="mt-3 flex flex-col gap-2">
            <textarea
              className="w-full rounded-md border border-surface-border bg-surface-raised p-2 text-[13px] text-celeste-text-primary placeholder:text-celeste-text-muted resize-none"
              rows={3}
              placeholder="Reason for decommissioning (required)"
              value={decommissionReason}
              onChange={(e) => setDecommissionReason(e.target.value)}
            />
            <div className="flex gap-2">
              <PrimaryButton
                onClick={handleDecommission}
                disabled={isLoading || !decommissionReason.trim()}
                className="text-[13px] min-h-8 px-3 py-1"
              >
                {isLoading ? 'Decommissioning...' : 'Confirm Decommission'}
              </PrimaryButton>
              <GhostButton
                onClick={() => { setShowDecommissionInput(false); setDecommissionReason(''); }}
                className="text-[13px] min-h-8 px-3 py-1"
              >
                Cancel
              </GhostButton>
            </div>
          </div>
        )}

        <div className="mt-6 border-t border-surface-border" aria-hidden="true" />

        {/* Details section */}
        <div className="mt-6">
          <SectionContainer title="Details" stickyTop={56}>
            <dl className="grid grid-cols-2 gap-4 typo-body">
              {serial_number && (
                <>
                  <dt className="text-celeste-text-muted">Serial Number</dt>
                  <dd className="text-celeste-text-primary">{serial_number}</dd>
                </>
              )}
              {installation_date && (
                <>
                  <dt className="text-celeste-text-muted">Installed</dt>
                  <dd className="text-celeste-text-primary">{formatRelativeTime(installation_date)}</dd>
                </>
              )}
              {last_maintenance && (
                <>
                  <dt className="text-celeste-text-muted">Last Maintenance</dt>
                  <dd className="text-celeste-text-primary">{formatRelativeTime(last_maintenance)}</dd>
                </>
              )}
              {next_maintenance && (
                <>
                  <dt className="text-celeste-text-muted">Next Maintenance</dt>
                  <dd className="text-celeste-text-primary">{formatRelativeTime(next_maintenance)}</dd>
                </>
              )}
            </dl>
          </SectionContainer>
        </div>

        {/* Attachments */}
        {attachments.length > 0 && (
          <div className="mt-6">
            <AttachmentsSection
              attachments={attachments}
              onAddFile={() => {}}
              canAddFile={false}
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
