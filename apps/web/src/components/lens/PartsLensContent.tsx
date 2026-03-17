'use client';

/**
 * PartsLensContent - Part/Inventory detail view (lens entity view).
 *
 * Renders inside EntityLensPage at /inventory/{id}.
 * Reads all data and actions from useEntityLensContext() — zero props.
 *
 * Action gates follow the universal lens pattern: getAction returns null
 * when the server says the action is unavailable for this user/state.
 * Never inline getAction calls in JSX — store results as named consts.
 *
 * write_off_part has requires_signature: true — the EntityLensPage shell
 * intercepts this automatically via safeExecute. Content just calls
 * executeAction('write_off_part', { reason }) normally.
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
// Stock status helper
// ---------------------------------------------------------------------------

function mapStockStatus(current: number, minimum: number): 'critical' | 'warning' | 'success' | 'neutral' {
  if (current <= 0) return 'critical';
  if (current < minimum) return 'warning';
  return 'success';
}

// ---------------------------------------------------------------------------
// PartsLensContent — zero props
// ---------------------------------------------------------------------------

export function PartsLensContent() {
  const router = useRouter();
  const { entity, executeAction, getAction, isLoading } = useEntityLensContext();

  // Input state for actions requiring extra data
  const [showWriteOffInput, setShowWriteOffInput] = React.useState(false);
  const [writeOffReason, setWriteOffReason] = React.useState('');
  const [showLogUsageInput, setShowLogUsageInput] = React.useState(false);
  const [logUsageQty, setLogUsageQty] = React.useState(1);
  const [showTransferInput, setShowTransferInput] = React.useState(false);
  const [transferLocation, setTransferLocation] = React.useState('');
  const [transferQty, setTransferQty] = React.useState(1);
  const [showAdjustInput, setShowAdjustInput] = React.useState(false);
  const [adjustQty, setAdjustQty] = React.useState(0);
  const [adjustReason, setAdjustReason] = React.useState('');

  // ---------------------------------------------------------------------------
  // Entity fields — access via entity?.field ?? default
  // ---------------------------------------------------------------------------
  const part_name = ((entity?.name ?? entity?.part_name) as string | undefined) ?? 'Part';
  const part_number = entity?.part_number as string | undefined;
  const stock_quantity = ((entity?.quantity_on_hand ?? entity?.stock_quantity) as number | undefined) ?? 0;
  const min_stock_level = ((entity?.minimum_quantity ?? entity?.min_stock_level) as number | undefined) ?? 0;
  const location = (entity?.location as string | undefined) ?? 'Unknown';
  const unit = entity?.unit as string | undefined;
  const unit_cost = entity?.unit_cost as number | undefined;
  const supplier = entity?.supplier as string | undefined;
  const category = entity?.category as string | undefined;
  const last_counted_at = entity?.last_counted_at as string | undefined;
  const image_url = entity?.image_url as string | undefined;
  const attachments = (entity?.attachments as Attachment[] | undefined) ?? [];
  const related_entities = (entity?.related_entities as RelatedEntity[] | undefined) ?? [];

  const stockColor = mapStockStatus(stock_quantity, min_stock_level);
  const stockLabel =
    stock_quantity <= 0 ? 'Out of Stock' :
    stock_quantity < min_stock_level ? 'Low Stock' : 'In Stock';

  // ---------------------------------------------------------------------------
  // Action gates — ALL stored as named consts, never inlined in JSX
  // ---------------------------------------------------------------------------
  const writeOffAction = getAction('write_off_part');
  const logUsageAction = getAction('log_part_usage');
  const transferAction = getAction('transfer_part');
  const addToShoppingListAction = getAction('add_to_shopping_list');
  const adjustStockAction = getAction('adjust_stock_quantity');

  const hasAnyAction =
    writeOffAction !== null ||
    logUsageAction !== null ||
    transferAction !== null ||
    addToShoppingListAction !== null ||
    adjustStockAction !== null;

  // ---------------------------------------------------------------------------
  // Vital signs
  // ---------------------------------------------------------------------------
  const vitalSigns: VitalSign[] = [
    { label: 'Stock', value: stockLabel, color: stockColor },
    { label: 'Quantity', value: `${stock_quantity}${unit ? ` ${unit}` : ''}` },
    { label: 'Min Level', value: `${min_stock_level}${unit ? ` ${unit}` : ''}` },
    { label: 'Location', value: location },
    { label: 'Last Count', value: last_counted_at ? formatRelativeTime(last_counted_at) : '—' },
  ];

  // ---------------------------------------------------------------------------
  // Action handlers — executeAction triggers refetch automatically
  // shell handles signature interception for write_off_part
  // ---------------------------------------------------------------------------

  const handleWriteOff = React.useCallback(async () => {
    if (!writeOffReason.trim()) return;
    await executeAction('write_off_part', { reason: writeOffReason });
    setShowWriteOffInput(false);
    setWriteOffReason('');
  }, [executeAction, writeOffReason]);

  const handleLogUsage = React.useCallback(async () => {
    await executeAction('log_part_usage', { quantity: logUsageQty });
    setShowLogUsageInput(false);
    setLogUsageQty(1);
  }, [executeAction, logUsageQty]);

  const handleTransfer = React.useCallback(async () => {
    if (!transferLocation.trim()) return;
    await executeAction('transfer_part', {
      destination_location_id: transferLocation,
      quantity: transferQty,
    });
    setShowTransferInput(false);
    setTransferLocation('');
    setTransferQty(1);
  }, [executeAction, transferLocation, transferQty]);

  const handleAddToShoppingList = React.useCallback(async () => {
    await executeAction('add_to_shopping_list', {});
  }, [executeAction]);

  const handleAdjustStock = React.useCallback(async () => {
    if (!adjustReason.trim()) return;
    await executeAction('adjust_stock_quantity', {
      new_quantity: adjustQty,
      reason: adjustReason,
    });
    setShowAdjustInput(false);
    setAdjustReason('');
  }, [executeAction, adjustQty, adjustReason]);

  // Navigation
  const handleBack = React.useCallback(() => router.back(), [router]);
  const handleClose = React.useCallback(() => router.push('/inventory'), [router]);

  const handleNavigate = React.useCallback(
    (entityType: string, entityId: string) =>
      router.push(getEntityRoute(entityType as Parameters<typeof getEntityRoute>[0], entityId)),
    [router]
  );

  return (
    <div className="flex flex-col h-full">
      <LensHeader entityType="Part" title={part_name} onBack={handleBack} onClose={handleClose} />

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
            title={part_name}
            subtitle={part_number ? `Part #${part_number}` : undefined}
            status={{ label: stockLabel, color: stockColor }}
          />
        </div>

        {/* Vital signs */}
        <div className="mt-3">
          <VitalSignsRow signs={vitalSigns} />
        </div>

        {/* Part image */}
        {image_url && (
          <div className="mt-4 rounded-lg overflow-hidden">
            <img
              src={image_url}
              alt={part_name}
              className="w-full max-h-[300px] object-contain bg-surface-secondary"
            />
          </div>
        )}

        {/* Actions */}
        {hasAnyAction && (
          <div className="mt-4 flex items-center gap-2 flex-wrap">
            {logUsageAction !== null && !showLogUsageInput && (
              <PrimaryButton
                onClick={() => setShowLogUsageInput(true)}
                disabled={logUsageAction?.disabled ?? isLoading}
                title={logUsageAction?.disabled_reason ?? undefined}
                className="text-[13px] min-h-9 px-4 py-2"
              >
                Log Usage
              </PrimaryButton>
            )}

            {adjustStockAction !== null && !showAdjustInput && (
              <GhostButton
                onClick={() => { setShowAdjustInput(true); setAdjustQty(stock_quantity); }}
                disabled={adjustStockAction?.disabled ?? isLoading}
                title={adjustStockAction?.disabled_reason ?? undefined}
                className="text-[13px] min-h-9 px-4 py-2"
              >
                Count Stock
              </GhostButton>
            )}

            {transferAction !== null && !showTransferInput && (
              <GhostButton
                onClick={() => setShowTransferInput(true)}
                disabled={transferAction?.disabled ?? isLoading}
                title={transferAction?.disabled_reason ?? undefined}
                className="text-[13px] min-h-9 px-4 py-2"
              >
                Transfer
              </GhostButton>
            )}

            {addToShoppingListAction !== null && (
              <GhostButton
                onClick={handleAddToShoppingList}
                disabled={addToShoppingListAction?.disabled ?? isLoading}
                title={addToShoppingListAction?.disabled_reason ?? undefined}
                className="text-[13px] min-h-9 px-4 py-2"
              >
                Add to Shopping List
              </GhostButton>
            )}

            {writeOffAction !== null && !showWriteOffInput && (
              <GhostButton
                onClick={() => setShowWriteOffInput(true)}
                disabled={writeOffAction?.disabled}
                title={writeOffAction?.disabled_reason ?? undefined}
                className="text-[13px] min-h-9 px-4 py-2"
              >
                Write Off
              </GhostButton>
            )}
          </div>
        )}

        {/* Log usage inline form */}
        {showLogUsageInput && logUsageAction !== null && (
          <div className="mt-3 flex flex-col gap-2">
            <label className="text-[12px] text-celeste-text-muted">Quantity</label>
            <input
              type="number"
              min={1}
              value={logUsageQty}
              onChange={(e) => setLogUsageQty(Math.max(1, parseInt(e.target.value) || 1))}
              className="w-full rounded-md border border-surface-border bg-surface-raised px-3 py-2 text-[13px] text-celeste-text-primary"
            />
            <div className="flex gap-2">
              <PrimaryButton
                onClick={handleLogUsage}
                disabled={isLoading}
                className="text-[13px] min-h-8 px-3 py-1"
              >
                {isLoading ? 'Saving...' : 'Confirm Usage'}
              </PrimaryButton>
              <GhostButton
                onClick={() => { setShowLogUsageInput(false); setLogUsageQty(1); }}
                className="text-[13px] min-h-8 px-3 py-1"
              >
                Cancel
              </GhostButton>
            </div>
          </div>
        )}

        {/* Transfer inline form */}
        {showTransferInput && transferAction !== null && (
          <div className="mt-3 flex flex-col gap-2">
            <label className="text-[12px] text-celeste-text-muted">Destination Location</label>
            <input
              type="text"
              value={transferLocation}
              onChange={(e) => setTransferLocation(e.target.value)}
              placeholder="Location ID or name"
              className="w-full rounded-md border border-surface-border bg-surface-raised px-3 py-2 text-[13px] text-celeste-text-primary placeholder:text-celeste-text-muted"
            />
            <label className="text-[12px] text-celeste-text-muted">Quantity</label>
            <input
              type="number"
              min={1}
              value={transferQty}
              onChange={(e) => setTransferQty(Math.max(1, parseInt(e.target.value) || 1))}
              className="w-full rounded-md border border-surface-border bg-surface-raised px-3 py-2 text-[13px] text-celeste-text-primary"
            />
            <div className="flex gap-2">
              <PrimaryButton
                onClick={handleTransfer}
                disabled={isLoading || !transferLocation.trim()}
                className="text-[13px] min-h-8 px-3 py-1"
              >
                {isLoading ? 'Transferring...' : 'Confirm Transfer'}
              </PrimaryButton>
              <GhostButton
                onClick={() => { setShowTransferInput(false); setTransferLocation(''); setTransferQty(1); }}
                className="text-[13px] min-h-8 px-3 py-1"
              >
                Cancel
              </GhostButton>
            </div>
          </div>
        )}

        {/* Adjust stock inline form */}
        {showAdjustInput && adjustStockAction !== null && (
          <div className="mt-3 flex flex-col gap-2">
            <label className="text-[12px] text-celeste-text-muted">Actual Count</label>
            <input
              type="number"
              min={0}
              value={adjustQty}
              onChange={(e) => setAdjustQty(Math.max(0, parseInt(e.target.value) || 0))}
              className="w-full rounded-md border border-surface-border bg-surface-raised px-3 py-2 text-[13px] text-celeste-text-primary"
            />
            <label className="text-[12px] text-celeste-text-muted">Reason (required)</label>
            <input
              type="text"
              value={adjustReason}
              onChange={(e) => setAdjustReason(e.target.value)}
              placeholder="e.g. Physical stock count"
              className="w-full rounded-md border border-surface-border bg-surface-raised px-3 py-2 text-[13px] text-celeste-text-primary placeholder:text-celeste-text-muted"
            />
            <div className="flex gap-2">
              <PrimaryButton
                onClick={handleAdjustStock}
                disabled={isLoading || !adjustReason.trim()}
                className="text-[13px] min-h-8 px-3 py-1"
              >
                {isLoading ? 'Saving...' : 'Save Count'}
              </PrimaryButton>
              <GhostButton
                onClick={() => { setShowAdjustInput(false); setAdjustReason(''); }}
                className="text-[13px] min-h-8 px-3 py-1"
              >
                Cancel
              </GhostButton>
            </div>
          </div>
        )}

        {/* Write off inline form — shell intercepts signature automatically */}
        {showWriteOffInput && writeOffAction !== null && (
          <div className="mt-3 flex flex-col gap-2">
            <label className="text-[12px] text-celeste-text-muted">Reason for write-off (required)</label>
            <textarea
              className="w-full rounded-md border border-surface-border bg-surface-raised p-2 text-[13px] text-celeste-text-primary placeholder:text-celeste-text-muted resize-none"
              rows={3}
              placeholder="Reason (damaged, expired, lost…)"
              value={writeOffReason}
              onChange={(e) => setWriteOffReason(e.target.value)}
            />
            <div className="flex gap-2">
              <PrimaryButton
                onClick={handleWriteOff}
                disabled={isLoading || !writeOffReason.trim()}
                className="text-[13px] min-h-8 px-3 py-1"
              >
                {isLoading ? 'Processing...' : 'Confirm Write Off'}
              </PrimaryButton>
              <GhostButton
                onClick={() => { setShowWriteOffInput(false); setWriteOffReason(''); }}
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
              {part_number && (
                <>
                  <dt className="text-celeste-text-muted">Part Number</dt>
                  <dd className="text-celeste-text-primary">{part_number}</dd>
                </>
              )}
              {category && (
                <>
                  <dt className="text-celeste-text-muted">Category</dt>
                  <dd className="text-celeste-text-primary">{category}</dd>
                </>
              )}
              {supplier && (
                <>
                  <dt className="text-celeste-text-muted">Supplier</dt>
                  <dd className="text-celeste-text-primary">{supplier}</dd>
                </>
              )}
              {unit_cost != null && (
                <>
                  <dt className="text-celeste-text-muted">Unit Cost</dt>
                  <dd className="text-celeste-text-primary">${unit_cost.toFixed(2)}</dd>
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
