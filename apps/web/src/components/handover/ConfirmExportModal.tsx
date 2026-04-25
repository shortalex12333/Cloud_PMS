'use client';

/**
 * ConfirmExportModal — pre-flight confirm for the handover export flow.
 *
 * Gates the POST /v1/handover/export call so the user sees (a) how many items
 * are about to be packaged, (b) where the result will land. Rendered by
 * AppShell for the subbar "Create Handover" primary action. The draft panel
 * in-page button has its own context (users are already looking at the list)
 * so it doesn't require the same guardrail — keep it simple for MVP.
 *
 * Pure presentational — the export work lives in `useHandoverExport`.
 */

import * as React from 'react';
import { X, Loader2, Upload } from 'lucide-react';

export interface ConfirmExportModalProps {
  open: boolean;
  itemCount: number;
  isExporting: boolean;
  onConfirm: () => void;
  onClose: () => void;
}

export function ConfirmExportModal({
  open,
  itemCount,
  isExporting,
  onConfirm,
  onClose,
}: ConfirmExportModalProps) {
  React.useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isExporting) onClose();
      if (e.key === 'Enter' && !isExporting && itemCount > 0) onConfirm();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, isExporting, itemCount, onClose, onConfirm]);

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-export-title"
      style={{
        position: 'fixed', inset: 0, zIndex: 1000,
        background: 'var(--overlay-bg)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: 16,
      }}
      onClick={isExporting ? undefined : onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: '100%', maxWidth: 440,
          background: 'var(--surface)', color: 'var(--txt)',
          borderRadius: 8, border: '1px solid var(--border-sub)',
          boxShadow: 'var(--shadow-lg, 0 18px 48px rgba(0,0,0,0.35))',
          fontFamily: 'var(--font-sans)',
        }}
      >
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '14px 16px', borderBottom: '1px solid var(--border-faint)',
        }}>
          <div id="confirm-export-title" style={{ fontSize: 13, fontWeight: 600 }}>
            Create handover
          </div>
          <button
            onClick={onClose}
            disabled={isExporting}
            aria-label="Close"
            style={{
              background: 'none', border: 'none', padding: 4,
              cursor: isExporting ? 'not-allowed' : 'pointer',
              color: 'var(--txt-ghost)', borderRadius: 4,
            }}
          >
            <X size={14} />
          </button>
        </div>

        <div style={{ padding: '16px 18px 4px', fontSize: 13, lineHeight: 1.55, color: 'var(--txt2)' }}>
          <p style={{ margin: 0 }}>
            You&apos;re about to export{' '}
            <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--txt)' }}>
              {itemCount}
            </span>{' '}
            {itemCount === 1 ? 'item' : 'items'} from your draft.
          </p>
          <ul style={{ margin: '12px 0 0', paddingLeft: 18, color: 'var(--txt3)', fontSize: 12 }}>
            <li>Generation usually takes 15–30 seconds.</li>
            <li>The signed document will appear in your notifications.</li>
            <li>You&apos;ll also find it in the <strong style={{ color: 'var(--txt2)' }}>Exported</strong> tab.</li>
            <li>Once exported, the items leave your draft queue.</li>
          </ul>
        </div>

        <div style={{
          display: 'flex', justifyContent: 'flex-end', gap: 8,
          padding: '16px 18px 18px',
        }}>
          <button
            onClick={onClose}
            disabled={isExporting}
            style={{
              padding: '7px 14px', borderRadius: 6,
              background: 'none', color: 'var(--txt2)',
              fontSize: 12, fontWeight: 500, border: '1px solid var(--border-sub)',
              cursor: isExporting ? 'not-allowed' : 'pointer',
              fontFamily: 'var(--font-sans)',
            }}
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={isExporting || itemCount === 0}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '7px 14px', borderRadius: 6,
              background: 'var(--teal-bg)', color: 'var(--mark)',
              fontSize: 12, fontWeight: 600,
              border: '1px solid var(--mark-underline)',
              cursor: (isExporting || itemCount === 0) ? 'not-allowed' : 'pointer',
              opacity: (isExporting || itemCount === 0) ? 0.5 : 1,
              fontFamily: 'var(--font-sans)',
            }}
          >
            {isExporting ? <Loader2 size={13} className="animate-spin" /> : <Upload size={13} />}
            {isExporting ? 'Exporting…' : 'Create handover'}
          </button>
        </div>
      </div>
    </div>
  );
}
