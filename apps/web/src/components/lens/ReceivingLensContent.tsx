'use client';

/**
 * ReceivingLensContent - Receiving detail view (lens entity view).
 *
 * Renders inside EntityLensPage at /receiving/{id}.
 * Reads all data and actions from useEntityLensContext() — zero props.
 *
 * Action gates follow the universal lens pattern: getAction returns null
 * when the server says the action is unavailable for this user/state.
 * Never inline getAction calls in JSX — store results as named consts.
 */

import * as React from 'react';
import { useRouter } from 'next/navigation';
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
// Colour helpers
// ---------------------------------------------------------------------------

function mapStatusToColor(status: string): 'critical' | 'warning' | 'success' | 'neutral' {
  switch (status) {
    case 'rejected': return 'critical';
    case 'draft':
    case 'in_review': return 'warning';
    case 'accepted': return 'success';
    default: return 'neutral';
  }
}

// ---------------------------------------------------------------------------
// ReceivingLensContent — zero props
// ---------------------------------------------------------------------------

export function ReceivingLensContent() {
  const router = useRouter();
  const { entity, executeAction, getAction, isLoading } = useEntityLensContext();

  // Map entity fields — access via entity?.field ?? default
  const payload = (entity?.payload as Record<string, unknown>) ?? {};
  const vendor_name = ((entity?.vendor_name ?? payload.vendor_name) as string | undefined) ?? 'Unknown Vendor';
  const vendor_reference = (entity?.vendor_reference ?? payload.vendor_reference) as string | undefined;
  const po_number = (entity?.po_number ?? payload.po_number) as string | undefined;
  const status = ((entity?.status ?? payload.status) as string | undefined) ?? 'draft';
  const received_date = (entity?.received_date ?? payload.received_date) as string | undefined;
  const total = (entity?.total ?? payload.total) as number | null | undefined;
  const currency = ((entity?.currency ?? payload.currency) as string | undefined) ?? 'USD';
  const received_by = (entity?.received_by ?? payload.received_by) as string | undefined;
  const notes = (entity?.notes ?? payload.notes) as string | undefined;

  // Items from child table
  const items = ((entity?.items ?? payload.items) as Array<{
    id: string;
    description?: string;
    quantity_received: number;
    unit_price?: number | null;
  }> | undefined) ?? [];

  const attachments = ((entity?.attachments ?? payload.attachments) as Attachment[] | undefined) ?? [];
  const related_entities = ((entity?.related_entities ?? payload.related_entities) as RelatedEntity[] | undefined) ?? [];

  const statusColor = mapStatusToColor(status);
  const statusLabel = status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

  // ---------------------------------------------------------------------------
  // Action gates — ALL stored as named consts, never inlined in JSX
  // ---------------------------------------------------------------------------
  const acceptAction = getAction('accept_receiving');
  const rejectAction = getAction('reject_receiving');
  const addItemAction = getAction('add_receiving_item');
  const editAction = getAction('edit_receiving');
  const submitForReviewAction = getAction('submit_receiving_for_review');
  const addAttachmentAction = getAction('add_receiving_attachment');

  const hasAnyAction =
    acceptAction !== null ||
    rejectAction !== null ||
    addItemAction !== null ||
    editAction !== null ||
    submitForReviewAction !== null;

  // ---------------------------------------------------------------------------
  // Vital signs
  // ---------------------------------------------------------------------------
  const vitalSigns: VitalSign[] = [
    { label: 'Status', value: statusLabel, color: statusColor },
    { label: 'Vendor', value: vendor_name },
    { label: 'Items', value: `${items.length} item${items.length === 1 ? '' : 's'}` },
    { label: 'Total', value: total != null ? `${currency} ${total.toFixed(2)}` : '—' },
    { label: 'Received', value: received_date ? formatRelativeTime(received_date) : '—' },
  ];

  // ---------------------------------------------------------------------------
  // Navigation
  // ---------------------------------------------------------------------------
  const handleBack = React.useCallback(() => router.back(), [router]);
  const handleClose = React.useCallback(() => router.push('/receiving'), [router]);

  const handleNavigate = React.useCallback(
    (entityType: string, entityId: string) =>
      router.push(getEntityRoute(entityType as Parameters<typeof getEntityRoute>[0], entityId)),
    [router]
  );

  // ---------------------------------------------------------------------------
  // Action handlers — executeAction triggers refetch automatically
  // ---------------------------------------------------------------------------

  const handleAddItem = React.useCallback(
    async () => executeAction('add_receiving_item', {}),
    [executeAction]
  );

  const handleAccept = React.useCallback(
    async () => executeAction('accept_receiving', {}),
    [executeAction]
  );

  const handleReject = React.useCallback(
    async () => executeAction('reject_receiving', {}),
    [executeAction]
  );

  const handleEdit = React.useCallback(
    async () => executeAction('edit_receiving', {}),
    [executeAction]
  );

  const handleSubmitForReview = React.useCallback(
    async () => executeAction('submit_receiving_for_review', {}),
    [executeAction]
  );

  return (
    <div className="flex flex-col h-full">
      <LensHeader entityType="Receiving" title={po_number || vendor_name} onBack={handleBack} onClose={handleClose} />

      <main className="flex-1 overflow-y-auto pt-14 px-10 md:px-6 sm:px-4 max-w-[800px] mx-auto w-full pb-12">
        <div className="mt-6">
          <LensTitleBlock
            title={po_number || vendor_name}
            subtitle={vendor_reference ? `Ref: ${vendor_reference}` : undefined}
            status={{ label: statusLabel, color: statusColor }}
          />
        </div>

        <div className="mt-3">
          <VitalSignsRow signs={vitalSigns} />
        </div>

        {/* Actions */}
        {hasAnyAction && (
          <div className="mt-4 flex items-center gap-2">
            {addItemAction !== null && (
              <PrimaryButton
                onClick={handleAddItem}
                disabled={addItemAction?.disabled ?? isLoading}
                title={addItemAction?.disabled_reason ?? undefined}
                className="text-[13px] min-h-9 px-4 py-2"
              >
                Add Item
              </PrimaryButton>
            )}

            {submitForReviewAction !== null && (
              <GhostButton
                onClick={handleSubmitForReview}
                disabled={submitForReviewAction?.disabled ?? isLoading}
                title={submitForReviewAction?.disabled_reason ?? undefined}
                className="text-[13px] min-h-9 px-4 py-2"
              >
                Submit for Review
              </GhostButton>
            )}

            {acceptAction !== null && (
              <GhostButton
                onClick={handleAccept}
                disabled={acceptAction?.disabled ?? isLoading}
                title={acceptAction?.disabled_reason ?? undefined}
                className="text-[13px] min-h-9 px-4 py-2"
              >
                Accept
              </GhostButton>
            )}

            {rejectAction !== null && (
              <GhostButton
                onClick={handleReject}
                disabled={rejectAction?.disabled ?? isLoading}
                title={rejectAction?.disabled_reason ?? undefined}
                className="text-[13px] min-h-9 px-4 py-2 text-status-critical"
              >
                Reject
              </GhostButton>
            )}

            {editAction !== null && (
              <GhostButton
                onClick={handleEdit}
                disabled={editAction?.disabled ?? isLoading}
                title={editAction?.disabled_reason ?? undefined}
                className="text-[13px] min-h-9 px-4 py-2"
              >
                Edit
              </GhostButton>
            )}
          </div>
        )}

        <div className="mt-6 border-t border-surface-border" aria-hidden="true" />

        {/* Items */}
        <div className="mt-6">
          <SectionContainer title={`Items (${items.length})`} stickyTop={56}>
            {items.length === 0 ? (
              <p className="typo-body text-celeste-text-muted">No items added yet.</p>
            ) : (
              <ul className="space-y-3">
                {items.map((item, index) => (
                  <li key={item.id || index} className="flex justify-between items-center p-3 bg-surface-secondary rounded-lg">
                    <span className="typo-body text-celeste-text-primary">{item.description || `Item ${index + 1}`}</span>
                    <span className="typo-body text-celeste-text-muted">
                      Qty: {item.quantity_received}
                      {item.unit_price !== null && item.unit_price !== undefined && ` @ ${currency} ${item.unit_price.toFixed(2)}`}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </SectionContainer>
        </div>

        {/* Notes */}
        {notes && (
          <div className="mt-6">
            <SectionContainer title="Notes" stickyTop={56}>
              <p className="typo-body text-celeste-text-primary">{notes}</p>
            </SectionContainer>
          </div>
        )}

        {/* Received by */}
        {received_by && (
          <div className="mt-6">
            <SectionContainer title="Received By" stickyTop={56}>
              <p className="typo-body text-celeste-text-primary">{received_by}</p>
            </SectionContainer>
          </div>
        )}

        {/* Attachments */}
        {attachments.length > 0 && (
          <div className="mt-6">
            <AttachmentsSection attachments={attachments} onAddFile={() => {}} canAddFile={addAttachmentAction !== null} stickyTop={56} />
          </div>
        )}

        {/* Related entities */}
        {related_entities.length > 0 && (
          <div className="mt-6">
            <RelatedEntitiesSection entities={related_entities} onNavigate={handleNavigate} stickyTop={56} />
          </div>
        )}
      </main>
    </div>
  );
}
