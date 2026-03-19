// apps/web/src/components/lens/EntityLensPage.tsx
'use client';

import * as React from 'react';
import { useRouter, useSearchParams, usePathname } from 'next/navigation';
import lensStyles from '@/components/lens-v2/lens.module.css';
import { useEntityLens } from '@/hooks/useEntityLens';
import { EntityLensProvider } from '@/contexts/EntityLensContext';
import { useRelatedDrawer } from '@/hooks/useRelatedDrawer';
import { useReadBeacon } from '@/hooks/useReadBeacon';
import { useSignalRelated } from '@/hooks/useSignalRelated';
// ShowRelatedButton removed — inlined into glass header
import { RelatedDrawer } from './RelatedDrawer';
import { AddRelatedItemModal } from './AddRelatedItemModal';
import { getEntityRoute } from '@/lib/featureFlags';
import type { EntityType, AvailableAction, ActionResult } from '@/types/entity';
import { getActionDisplay } from '@/types/actions';
import { ActionPopup } from '@/components/lens-v2/ActionPopup';
import type { ActionPopupField } from '@/components/lens-v2/ActionPopup';
import { useEntityLedger } from '@/hooks/useEntityLedger';
import { HistorySection } from './sections/HistorySection';

// Clusters rendered in the shell action bar (not inline in content)
const SHELL_CLUSTERS = new Set(['lifecycle', 'entity', 'compliance']);

// Fields handled automatically — never require user input in the form
const BACKEND_AUTO = new Set(['yacht_id', 'signature', 'idempotency_key']);

/**
 * Returns true if the action has required fields that are not covered by
 * BACKEND_AUTO or action.prefill — meaning a form is needed to execute it.
 * Such actions must NOT appear in the shell bar (content component handles them inline).
 */
function hasUnresolvedFields(action: AvailableAction): boolean {
  return action.required_fields.some(
    (f) => !BACKEND_AUTO.has(f) && !(f in action.prefill)
  );
}

// ---------------------------------------------------------------------------
// Loading / error / not-found states (shared across all 12 entity pages)
// ---------------------------------------------------------------------------
function LoadingState() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '256px' }}>
      <div style={{ width: '32px', height: '32px', border: '2px solid var(--border-sub)', borderTopColor: 'var(--mark)', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
    </div>
  );
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center', padding: '24px', minHeight: '256px' }}>
      <h3 style={{ fontSize: '18px', fontWeight: 500, color: 'var(--txt)', marginBottom: '8px' }}>Failed to Load</h3>
      <p style={{ fontSize: '13px', color: 'var(--txt2)', maxWidth: '320px', marginBottom: '16px' }}>{message}</p>
      <button
        onClick={onRetry}
        style={{ padding: '8px 16px', background: 'var(--split-bg)', borderRadius: '6px', fontSize: '13px', color: 'var(--txt)', border: 'none', cursor: 'pointer', fontFamily: 'var(--font-sans)' }}
      >
        Try Again
      </button>
    </div>
  );
}

function NotFoundState({ entityType, onBack }: { entityType: EntityType; onBack: () => void }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center', padding: '24px', minHeight: '256px' }}>
      <h3 style={{ fontSize: '18px', fontWeight: 500, color: 'var(--txt)', marginBottom: '8px' }}>Not Found</h3>
      <p style={{ fontSize: '13px', color: 'var(--txt2)', maxWidth: '320px', marginBottom: '16px' }}>
        This {entityType.replace(/_/g, ' ')} may have been deleted or you may not have access.
      </p>
      <button
        onClick={onBack}
        style={{ padding: '8px 16px', background: 'var(--split-bg)', borderRadius: '6px', fontSize: '13px', color: 'var(--txt)', border: 'none', cursor: 'pointer', fontFamily: 'var(--font-sans)' }}
      >
        Go Back
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------
function LedgerHistory({ entityType, entityId }: { entityType: string; entityId: string }) {
  const { data: ledgerHistory = [] } = useEntityLedger(entityType, entityId);
  if (ledgerHistory.length === 0) return null;
  return <HistorySection history={ledgerHistory} />;
}

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
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const lens = useEntityLens(entityType, entityId);

  const [pendingSignature, setPendingSignature] = React.useState<{
    action: AvailableAction;
    payload: Record<string, unknown>;
  } | null>(null);
  const [signatureError, setSignatureError] = React.useState<string | null>(null);

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
  } = useRelatedDrawer(entityType, entityId);

  const {
    data: signalData,
    isLoading: signalLoading,
  } = useSignalRelated(entityType, entityId);

  useReadBeacon(entityType, entityId);

  const handleNavigate = React.useCallback(
    (type: string, id: string) => {
      const target = getEntityRoute(type as Parameters<typeof getEntityRoute>[0], id);
      router.push(`${target}?from=${encodeURIComponent(pathname)}`);
    },
    [router, pathname]
  );

  const handleBack = React.useCallback(() => {
    const from = searchParams.get('from');
    if (from) {
      router.push(from);
    } else {
      router.back();
    }
  }, [router, searchParams]);

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

  // Shell action bar: lifecycle, entity, and compliance clusters
  const shellActions = lens.availableActions.filter((a) => {
    const { cluster } = getActionDisplay(a.action_id);
    return SHELL_CLUSTERS.has(cluster) && !hasUnresolvedFields(a);
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

  const entityTitle = String(
    lens.entity?.title ??
    lens.entity?.name ??
    lens.entity?.reference_number ??
    pageTitle ??
    entityType.replace(/_/g, ' ')
  );

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
        <Content />
        <LedgerHistory entityType={entityType} entityId={entityId} />
        {/* Shell action bar — lifecycle, entity, and compliance actions */}
        {shellActions.length > 0 && (
          <div
            style={{ display: 'flex', gap: '12px', paddingTop: '16px', flexWrap: 'wrap', borderTop: '1px solid var(--border-sub)' }}
            data-testid="shell-action-bar"
          >
            {shellActions.map((action) => (
              <button
                key={action.action_id}
                disabled={action.disabled}
                title={action.disabled_reason ?? undefined}
                onClick={() => safeExecute(action.action_id)}
                data-testid={`action-${action.action_id}`}
                className={lensStyles.splitMain}
                style={action.disabled ? { opacity: 0.4, cursor: 'not-allowed' } : undefined}
              >
                {action.label}
                {action.variant === 'SIGNED' && (
                  <span style={{ fontSize: '12px', color: 'var(--amber)' }} title="Requires signature">
                    ✎
                  </span>
                )}
              </button>
            ))}
          </div>
        )}
      </EntityLensProvider>
    );
  }

  return (
    <main
      role="main"
      data-testid={`${entityType}-detail`}
      className={lensStyles.root}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '24px 16px 48px',
        minHeight: '100vh',
        background: 'var(--surface-base)',
      }}
    >
      <div className={lensStyles.panel}>
        {/* Glass Header */}
        <div className={lensStyles.lensHdr}>
          <button
            className={lensStyles.hdrBack}
            onClick={handleBack}
            aria-label="Go back"
            data-testid="back-button"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M10 12L6 8l4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>

          <span className={lensStyles.hdrType}>
            {entityType.replace(/_/g, ' ')}
          </span>

          <div className={lensStyles.hdrActions}>
            <button
              className={lensStyles.hdrBtn}
              onClick={() => setRelatedOpen((o) => !o)}
              aria-label={relatedOpen ? 'Close related panel' : 'Show related'}
              aria-expanded={relatedOpen}
              data-testid="show-related-button"
            >
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                <path d="M6.5 9.5l3-3M5.75 11.75L4 13.5a1.77 1.77 0 01-2.5-2.5l1.75-1.75M12.25 6.25L14 4.5A1.77 1.77 0 0011.5 2L9.75 3.75" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
              <span>Related{totalRelated > 0 ? ` (${totalRelated})` : ''}</span>
            </button>

            <button
              className={lensStyles.hdrBtn}
              onClick={() => {
                const html = document.documentElement;
                const current = html.getAttribute('data-theme');
                html.setAttribute('data-theme', current === 'light' ? 'dark' : 'light');
              }}
              aria-label="Toggle theme"
            >
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                <path d="M14 8.5A6 6 0 117.5 2a4.5 4.5 0 006.5 6.5z" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
          </div>
        </div>

        {/* Body */}
        <div className={lensStyles.lensBody}>
          {bodyContent}
        </div>
      </div>

      {/* Related Drawer - rendered outside panel */}
      {relatedOpen && (
        <div
          style={{
            position: 'fixed',
            top: '24px',
            right: '24px',
            bottom: '24px',
            width: '600px',
            maxWidth: '100vw',
            zIndex: 100,
            background: 'var(--surface)',
            borderTop: '1px solid rgba(255,255,255,0.11)',
            borderRight: '1px solid rgba(255,255,255,0.06)',
            borderBottom: '1px solid rgba(255,255,255,0.03)',
            borderLeft: '1px solid rgba(255,255,255,0.06)',
            borderRadius: '4px',
            boxShadow: '0 20px 80px rgba(0,0,0,0.60), 0 4px 20px rgba(0,0,0,0.40), inset 0 1px 0 rgba(255,255,255,0.05)',
            overflow: 'hidden',
            transition: 'opacity 200ms ease, transform 280ms ease',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <div style={{ padding: '14px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-sub)', gap: '8px', flexShrink: 0 }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--txt2)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Related · {totalRelated}
            </span>
            <button
              className={lensStyles.hdrClose}
              onClick={() => setRelatedOpen(false)}
              aria-label="Close related"
              style={{ width: '32px', height: '32px', borderRadius: '6px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
            >
              <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
                <path d="M12 4L4 12M4 4l8 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
            </button>
          </div>
          <RelatedDrawer
            groups={relatedData?.groups ?? []}
            isLoading={relatedLoading}
            error={relatedError ?? null}
            onNavigate={handleNavigate}
            onAddRelated={canAddRelated ? () => setShowAddModal(true) : undefined}
            signalItems={signalData?.items}
            signalLoading={signalLoading}
          />
        </div>
      )}

      {showAddModal && (
        <AddRelatedItemModal
          fromEntityType={entityType}
          fromEntityId={entityId}
          onClose={() => setShowAddModal(false)}
        />
      )}

      {pendingSignature && (() => {
        // Determine signature level from action metadata, default to L3 (PIN)
        const sigLevel = (pendingSignature.action as AvailableAction & { signature_level?: number }).signature_level ?? 3;
        // Build popup fields from the action's required_fields (excluding auto-handled ones)
        const popupFields: ActionPopupField[] = pendingSignature.action.required_fields
          .filter((f) => !BACKEND_AUTO.has(f) && !(f in pendingSignature.action.prefill))
          .map((f) => ({
            name: f,
            label: f.replace(/_/g, ' '),
            type: 'kv-edit' as const,
            placeholder: `Enter ${f.replace(/_/g, ' ')}...`,
            value: (pendingSignature.payload[f] as string) ?? '',
          }));

        return (
          <ActionPopup
            mode="mutate"
            title="Signature Required"
            subtitle={`${pendingSignature.action.label} requires authorization.`}
            fields={popupFields}
            signatureLevel={sigLevel as 0 | 1 | 2 | 3 | 4 | 5}
            previewRows={signatureError ? [{ key: 'Error', value: signatureError }] : undefined}
            onSubmit={async (values) => {
              setSignatureError(null);
              const result = await lens.executeAction(pendingSignature.action.action_id, {
                ...pendingSignature.payload,
                ...values,
              });
              if (result.success) {
                setPendingSignature(null);
              } else {
                setSignatureError(result.message ?? result.error ?? 'Action failed');
              }
            }}
            onClose={() => { setPendingSignature(null); setSignatureError(null); }}
          />
        );
      })()}
    </main>
  );
}
