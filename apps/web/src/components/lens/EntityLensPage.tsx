// apps/web/src/components/lens/EntityLensPage.tsx
'use client';

import * as React from 'react';
import { useRouter, useSearchParams, usePathname } from 'next/navigation';
import lensStyles from '@/components/lens-v2/lens.module.css';
import { useEntityLens } from '@/hooks/useEntityLens';
import { EntityLensProvider } from '@/contexts/EntityLensContext';
import { useReadBeacon } from '@/hooks/useReadBeacon';
import { useSignalRelated } from '@/hooks/useSignalRelated';
// ShowRelatedButton removed — inlined into glass header
import { RelatedDrawer } from './RelatedDrawer';
import { getEntityRoute } from '@/lib/featureFlags';
import type { EntityType, AvailableAction, ActionResult } from '@/types/entity';
import { getActionDisplay } from '@/types/actions';
import { ActionPopup } from '@/components/lens-v2/ActionPopup';
import type { ActionPopupField } from '@/components/lens-v2/ActionPopup';
import { useEntityLedger } from '@/hooks/useEntityLedger';
import { HistorySection } from './sections/HistorySection';

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
  // Read yacht_id from URL for cross-vessel access in overview mode
  const yachtIdParam = searchParams.get('yacht_id');
  const lens = useEntityLens(entityType, entityId, yachtIdParam);

  const [pendingSignature, setPendingSignature] = React.useState<{
    action: AvailableAction;
    payload: Record<string, unknown>;
  } | null>(null);
  const [signatureError, setSignatureError] = React.useState<string | null>(null);

  const [relatedOpen, setRelatedOpen] = React.useState(false);

  const {
    data: signalData,
    isLoading: signalLoading,
  } = useSignalRelated(entityType, entityId);

  const signalCount = signalData?.items?.length ?? 0;

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
              style={relatedOpen ? { background: 'var(--surface-hover)', color: 'var(--mark)' } : undefined}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="18" cy="5" r="3" /><circle cx="6" cy="12" r="3" /><circle cx="18" cy="19" r="3" /><path d="M8.59 13.51l6.83 3.98M15.41 6.51l-6.82 3.98" /></svg>
              <span>Related</span>
              {signalCount > 0 && (
                <span style={{
                  padding: '1px 6px', borderRadius: '4px',
                  background: 'var(--teal-bg)', color: 'var(--mark)',
                  fontSize: '10px', fontWeight: 600,
                  fontFamily: 'var(--font-mono)',
                }}>
                  {signalCount}
                </span>
              )}
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

      {/* Related Drawer — prototype: show-related.html */}
      <div
        style={{
          position: 'fixed',
          top: '24px',
          right: '24px',
          bottom: '24px',
          width: '600px',
          maxWidth: 'min(100vw - 32px, 600px)',
          zIndex: 100,
          background: 'var(--surface)',
          borderTop: '1px solid var(--border-top)',
          borderRight: '1px solid var(--border-side)',
          borderBottom: '1px solid var(--border-bottom)',
          borderLeft: '1px solid var(--border-side)',
          borderRadius: '4px',
          boxShadow: '0 20px 80px rgba(0,0,0,0.60), 0 4px 20px rgba(0,0,0,0.40), inset 0 1px 0 rgba(255,255,255,0.05)',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          transform: relatedOpen ? 'translateX(0)' : 'translateX(32px)',
          opacity: relatedOpen ? 1 : 0,
          visibility: relatedOpen ? 'visible' : 'hidden',
          pointerEvents: relatedOpen ? 'auto' : 'none',
          transition: 'opacity 200ms ease, transform 280ms ease',
        }}
      >
        {/* Drawer header */}
        <div style={{ display: 'flex', alignItems: 'center', padding: '14px 16px', borderBottom: '1px solid var(--border-sub)', gap: '8px', flexShrink: 0 }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ color: 'var(--txt3)', flexShrink: 0 }}><circle cx="18" cy="5" r="3" /><circle cx="6" cy="12" r="3" /><circle cx="18" cy="19" r="3" /><path d="M8.59 13.51l6.83 3.98M15.41 6.51l-6.82 3.98" /></svg>
          <span style={{ fontSize: '12px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--txt2)', flex: 1 }}>
            Show Related
          </span>
          <button
            onClick={() => setRelatedOpen(false)}
            aria-label="Close related"
            style={{ width: '32px', height: '32px', borderRadius: '6px', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', color: 'var(--txt-ghost)', background: 'none', border: 'none', transition: 'background 60ms' }}
            onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--surface-hover)'; e.currentTarget.style.color = 'var(--txt2)'; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--txt-ghost)'; }}
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M18 6L6 18M6 6l12 12" /></svg>
          </button>
        </div>

        {/* Source entity context */}
        <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border-faint)', display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
          <div style={{ width: '24px', height: '24px', borderRadius: '5px', background: 'var(--teal-bg)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="var(--mark)" strokeWidth="2" strokeLinecap="round"><path d="M9 11l3 3L22 4" /><path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11" /></svg>
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--txt3)' }}>
              {(lens.entity?.wo_number ?? lens.entity?.reference_number ?? entityType.replace(/_/g, ' ')).toString().toUpperCase()}
            </div>
            <div style={{ fontSize: '12px', color: 'var(--txt)', fontWeight: 500, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {entityTitle}
            </div>
          </div>
        </div>

        {/* Drawer body + results */}
        <RelatedDrawer
          onNavigate={handleNavigate}
          signalItems={signalData?.items}
          signalLoading={signalLoading}
          entityText={signalData?.entity_text}
        />

        {/* Footer — count + keyboard hints */}
        {!signalLoading && signalCount > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', padding: '6px 12px', borderTop: '1px solid var(--border-sub)', flexShrink: 0 }}>
            <span style={{ fontSize: '10px', color: 'var(--txt3)', fontFamily: 'var(--font-mono)' }}>{signalCount} related entities</span>
            <div style={{ flex: 1 }} />
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '10px', color: 'var(--txt-ghost)' }}>
              <kbd style={{ background: 'var(--surface-el)', borderRadius: '3px', padding: '1px 4px', fontSize: '10px', color: 'var(--txt3)', fontFamily: 'var(--font-mono)', minWidth: '18px', textAlign: 'center' }}>↑</kbd>
              <kbd style={{ background: 'var(--surface-el)', borderRadius: '3px', padding: '1px 4px', fontSize: '10px', color: 'var(--txt3)', fontFamily: 'var(--font-mono)', minWidth: '18px', textAlign: 'center' }}>↓</kbd>
              Navigate
            </span>
            <div style={{ width: '1px', height: '10px', background: 'var(--border-sub)', margin: '0 8px' }} />
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '10px', color: 'var(--txt-ghost)' }}>
              <kbd style={{ background: 'var(--surface-el)', borderRadius: '3px', padding: '1px 4px', fontSize: '10px', color: 'var(--txt3)', fontFamily: 'var(--font-mono)', minWidth: '18px', textAlign: 'center' }}>↵</kbd>
              Open
            </span>
            <div style={{ width: '1px', height: '10px', background: 'var(--border-sub)', margin: '0 8px' }} />
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '10px', color: 'var(--txt-ghost)' }}>
              <kbd style={{ background: 'var(--surface-el)', borderRadius: '3px', padding: '1px 4px', fontSize: '10px', color: 'var(--txt3)', fontFamily: 'var(--font-mono)', minWidth: '18px', textAlign: 'center' }}>Esc</kbd>
              Close
            </span>
          </div>
        )}
      </div>

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
