// apps/web/src/components/lens/EntityLensPage.tsx
'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { RouteLayout } from '@/components/layout';
import { useEntityLens } from '@/hooks/useEntityLens';
import { EntityLensProvider } from '@/contexts/EntityLensContext';
import { useRelatedPanel } from '@/hooks/useRelatedPanel';
import { useReadBeacon } from '@/hooks/useReadBeacon';
import { ShowRelatedButton } from './ShowRelatedButton';
import { RelatedDrawer } from './RelatedDrawer';
import { AddRelatedItemModal } from './AddRelatedItemModal';
import { getEntityRoute } from '@/lib/featureFlags';
import type { EntityType, AvailableAction, ActionResult } from '@/types/entity';

// ACTION_DISPLAY import — populated in Task 5. Until then, use the fallback.
// After Task 5: import { getActionDisplay } from '@/types/actions';
function getActionDisplay(actionId: string): { icon: string; cluster: string } {
  const DISPLAY: Record<string, { icon: string; cluster: string }> = {
    start_work_order:           { icon: 'play',          cluster: 'lifecycle' },
    close_work_order:           { icon: 'check',         cluster: 'lifecycle' },
    cancel_work_order:          { icon: 'x',             cluster: 'lifecycle' },
    reopen_work_order:          { icon: 'rotate-ccw',    cluster: 'lifecycle' },
    archive_work_order:         { icon: 'archive',       cluster: 'entity'    },
    reassign_work_order:        { icon: 'user',          cluster: 'entity'    },
    update_work_order:          { icon: 'edit',          cluster: 'entity'    },
    close_fault:                { icon: 'check',         cluster: 'lifecycle' },
    reopen_fault:               { icon: 'rotate-ccw',   cluster: 'lifecycle' },
    acknowledge_fault:          { icon: 'check-circle',  cluster: 'lifecycle' },
    mark_fault_false_alarm:     { icon: 'x-circle',     cluster: 'lifecycle' },
    report_fault:               { icon: 'alert',         cluster: 'entity'    },
    decommission_equipment:     { icon: 'trash',         cluster: 'lifecycle' },
    update_equipment_status:    { icon: 'edit',          cluster: 'entity'    },
    flag_equipment_attention:   { icon: 'flag',          cluster: 'entity'    },
    write_off_part:             { icon: 'trash',         cluster: 'lifecycle' },
    accept_receiving:           { icon: 'check',         cluster: 'lifecycle' },
    reject_receiving:           { icon: 'x',             cluster: 'lifecycle' },
    update_receiving:           { icon: 'edit',          cluster: 'entity'    },
    update_certificate:         { icon: 'edit',          cluster: 'entity'    },
    export_handover:            { icon: 'download',      cluster: 'entity'    },
    export_hours_of_rest:       { icon: 'download',      cluster: 'compliance'},
  };
  return DISPLAY[actionId] ?? { icon: 'circle', cluster: 'entity' };
}

// Clusters rendered in the shell action bar (not inline in content)
const SHELL_CLUSTERS = new Set(['lifecycle', 'entity', 'compliance']);

// ---------------------------------------------------------------------------
// Signature modal (PIN collection only — TOTP is a future phase)
// ---------------------------------------------------------------------------
function SignatureModal({
  action,
  onConfirm,
  onCancel,
}: {
  action: AvailableAction;
  onConfirm: (credentials: { pin: string }) => void;
  onCancel: () => void;
}) {
  const [pin, setPin] = React.useState('');
  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-[#1a1a1f] border border-white/10 rounded-xl p-6 w-80 space-y-4">
        <h2 className="text-white font-semibold">Signature Required</h2>
        <p className="text-sm text-white/60">{action.label} requires authorization.</p>
        <input
          type="password"
          placeholder="PIN"
          value={pin}
          onChange={(e) => setPin(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && pin && onConfirm({ pin })}
          className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white text-sm"
          data-testid="signature-pin-input"
        />
        <div className="flex gap-2">
          <button
            onClick={onCancel}
            className="flex-1 px-3 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-sm text-white transition-colors"
          >
            Cancel
          </button>
          <button
            disabled={!pin}
            onClick={() => onConfirm({ pin })}
            className="flex-1 px-3 py-2 bg-teal-500/20 hover:bg-teal-500/30 border border-teal-500/30 rounded-lg text-sm text-teal-300 disabled:opacity-40 transition-colors"
            data-testid="signature-confirm-button"
          >
            Confirm
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Loading / error / not-found states (shared across all 12 entity pages)
// ---------------------------------------------------------------------------
function LoadingState() {
  return (
    <div className="flex items-center justify-center h-full min-h-64">
      <div className="w-8 h-8 border-2 border-white/20 border-t-white/80 rounded-full animate-spin" />
    </div>
  );
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-6 min-h-64">
      <h3 className="text-lg font-medium text-white mb-2">Failed to Load</h3>
      <p className="text-sm text-white/60 max-w-sm mb-4">{message}</p>
      <button
        onClick={onRetry}
        className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-sm text-white transition-colors"
      >
        Try Again
      </button>
    </div>
  );
}

function NotFoundState({ entityType, onBack }: { entityType: EntityType; onBack: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-6 min-h-64">
      <h3 className="text-lg font-medium text-white mb-2">Not Found</h3>
      <p className="text-sm text-white/60 max-w-sm mb-4">
        This {entityType.replace(/_/g, ' ')} may have been deleted or you may not have access.
      </p>
      <button
        onClick={onBack}
        className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-sm text-white transition-colors"
      >
        Go Back
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------
export interface EntityLensPageProps {
  entityType: EntityType;
  entityId: string;
  /** Entity-specific content component — reads from useEntityLensContext() directly */
  content: React.ComponentType;
  /** Optional fallback title if entity has no title/name field */
  pageTitle?: string;
}

export function EntityLensPage({
  entityType,
  entityId,
  content: Content,
  pageTitle,
}: EntityLensPageProps) {
  const router = useRouter();
  const lens = useEntityLens(entityType, entityId);

  const [pendingSignature, setPendingSignature] = React.useState<{
    action: AvailableAction;
    payload: Record<string, unknown>;
  } | null>(null);

  const {
    open: relatedOpen,
    setOpen: setRelatedOpen,
    showAddModal,
    setShowAddModal,
    canAdd: canAddRelated,
    data: relatedData,
    isLoading: relatedLoading,
    error: relatedError,
    totalRelated,
  } = useRelatedPanel(entityType, entityId);

  useReadBeacon(entityType, entityId);

  const handleNavigate = React.useCallback(
    (type: string, id: string) => {
      router.push(getEntityRoute(type as Parameters<typeof getEntityRoute>[0], id));
    },
    [router]
  );

  const handleBack = React.useCallback(() => router.back(), [router]);

  /**
   * safeExecute wraps lens.executeAction with signature interception.
   * If requires_signature is true, shows the PIN modal instead of executing.
   * After PIN entry, calls lens.executeAction with credentials merged in.
   * Content components call this via useEntityLensContext().executeAction.
   */
  const safeExecute = React.useCallback(
    async (actionId: string, payload: Record<string, unknown> = {}): Promise<ActionResult> => {
      const actionMeta = lens.getAction(actionId);
      if (actionMeta?.requires_signature) {
        setPendingSignature({ action: actionMeta, payload });
        return { success: false, message: 'Awaiting signature' };
      }
      return lens.executeAction(actionId, payload);
    },
    [lens]
  );

  // Shell action bar: lifecycle + entity cluster only
  const shellActions = lens.availableActions.filter((a) => {
    const { cluster } = getActionDisplay(a.action_id);
    return SHELL_CLUSTERS.has(cluster);
  });

  const contextValue = React.useMemo(
    () => ({
      entityType,
      entityId,
      entity: lens.entity,
      availableActions: lens.availableActions,
      isLoading: lens.isLoading,
      error: lens.error,
      executeAction: safeExecute,
      refetch: lens.refetch,
      getAction: lens.getAction,
    }),
    [entityType, entityId, lens, safeExecute]
  );

  const entityTitle = (
    lens.entity?.title ||
    lens.entity?.name ||
    lens.entity?.reference_number ||
    pageTitle ||
    entityType.replace(/_/g, ' ')
  ) as string;

  let bodyContent: React.ReactNode;

  if (lens.isLoading) {
    bodyContent = <LoadingState />;
  } else if (lens.error) {
    if (lens.error.includes('404')) {
      bodyContent = <NotFoundState entityType={entityType} onBack={handleBack} />;
    } else {
      bodyContent = <ErrorState message={lens.error} onRetry={lens.refetch} />;
    }
  } else if (!lens.entity) {
    bodyContent = <NotFoundState entityType={entityType} onBack={handleBack} />;
  } else {
    bodyContent = (
      <EntityLensProvider value={contextValue}>
        <div className="max-w-3xl mx-auto p-6 space-y-6">
          <Content />
          {/* Shell action bar — lifecycle and entity-level actions */}
          {shellActions.length > 0 && (
            <div
              className="flex gap-3 pt-4 border-t border-white/10 flex-wrap"
              data-testid="shell-action-bar"
            >
              {shellActions.map((action) => (
                <button
                  key={action.action_id}
                  disabled={action.disabled}
                  title={action.disabled_reason ?? undefined}
                  onClick={() => safeExecute(action.action_id)}
                  data-testid={`action-${action.action_id}`}
                  className="px-4 py-2 bg-white/10 hover:bg-white/20 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg text-sm text-white transition-colors flex items-center gap-2"
                >
                  {action.label}
                  {action.variant === 'SIGNED' && (
                    <span className="text-xs text-yellow-400" title="Requires signature">
                      ✎
                    </span>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>
      </EntityLensProvider>
    );
  }

  return (
    <main role="main" data-testid={`${entityType}-detail`}>
      <RouteLayout
        pageTitle={entityTitle}
        showTopNav={true}
        topNavContent={
          <div className="flex items-center justify-between w-full">
            <div className="flex items-center gap-4">
              <button
                onClick={handleBack}
                className="p-2 hover:bg-white/5 rounded-lg transition-colors"
                aria-label="Back"
                data-testid="back-button"
              >
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  className="text-white/60"
                >
                  <path d="M15 18l-6-6 6-6" />
                </svg>
              </button>
              <div>
                <p className="text-xs text-white/40 uppercase tracking-wider">
                  {entityType.replace(/_/g, ' ')}
                </p>
                <h1 className="text-lg font-semibold text-white truncate max-w-md">
                  {entityTitle}
                </h1>
              </div>
            </div>
            <ShowRelatedButton
              onClick={() => setRelatedOpen((open) => !open)}
              isOpen={relatedOpen}
              count={totalRelated}
              isLoading={relatedLoading}
            />
          </div>
        }
        primaryPanel={{
          visible: relatedOpen,
          title: 'Related',
          subtitle: `${totalRelated} item${totalRelated !== 1 ? 's' : ''}`,
          children: (
            <RelatedDrawer
              groups={relatedData?.groups ?? []}
              isLoading={relatedLoading}
              error={relatedError ?? null}
              onNavigate={handleNavigate}
              onAddRelated={canAddRelated ? () => setShowAddModal(true) : undefined}
            />
          ),
        }}
        onClosePrimaryPanel={() => setRelatedOpen(false)}
      >
        {bodyContent}
      </RouteLayout>

      {showAddModal && (
        <AddRelatedItemModal
          fromEntityType={entityType}
          fromEntityId={entityId}
          onClose={() => setShowAddModal(false)}
        />
      )}

      {pendingSignature && (
        <SignatureModal
          action={pendingSignature.action}
          onConfirm={async (credentials) => {
            await lens.executeAction(pendingSignature.action.action_id, {
              ...pendingSignature.payload,
              ...credentials,
            });
            setPendingSignature(null);
          }}
          onCancel={() => setPendingSignature(null)}
        />
      )}
    </main>
  );
}
