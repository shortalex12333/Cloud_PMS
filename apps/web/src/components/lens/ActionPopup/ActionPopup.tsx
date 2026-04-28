'use client';

import * as React from 'react';
import s from '../popup.module.css';
import type { ActionPopupProps } from './shared/types';
import { backdropClass } from './shared/helpers';
import { buildSourceRows, SourceBlock } from './shared/SourceBlock';
import { SigL1, SigL2, SigL3, SigL4, SigL5 } from './shared/SignatureLevels';
import { renderField } from './fields/renderField';

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function ActionPopup({
  mode,
  title,
  subtitle,
  fields,
  gates,
  signatureLevel = 1,
  submitLabel,
  submitDisabled,
  onSubmit,
  onClose,
  previewRows,
  prefill,
}: ActionPopupProps) {
  // L0 = tap only — execute inline, no modal needed
  // L0 = fire-and-forget (no form, no signature). Only auto-submit if there
  // are genuinely no fields to show — otherwise we'd skip the user's form.
  const isL0 = mode === 'mutate' && signatureLevel === 0 && fields.length === 0;
  const hasEntitySearch = fields.some((f) => f.type === 'entity-search');

  // Internal form state (hooks must be called unconditionally)
  const [values, setValues] = React.useState<Record<string, string>>(() => {
    const init: Record<string, string> = {};
    for (const f of fields) {
      init[f.name] = f.value ?? '';
    }
    return init;
  });
  const [pin, setPin] = React.useState('');
  const [sigName, setSigName] = React.useState('');

  // Source-context rows: prefill keys NOT mapped to a user-editable field.
  // Invisible when no usable rows remain.
  const sourceRows = React.useMemo(() => {
    const fieldNames = new Set(fields.map((f) => f.name));
    return buildSourceRows(prefill, fieldNames);
  }, [prefill, fields]);

  const setValue = (name: string, value: string) =>
    setValues((prev) => ({ ...prev, [name]: value }));

  // Compute whether all gates are satisfied
  const allGatesSatisfied = !gates || gates.every((g) => g.satisfied);

  // Compute submit-ready state
  const computedDisabled = React.useMemo(() => {
    if (submitDisabled) return true;
    if (!allGatesSatisfied) return true;
    // Check required fields
    for (const f of fields) {
      if (f.required && !values[f.name]) return true;
    }
    // Signature checks
    if (signatureLevel === 2 && !sigName) return true;
    if (signatureLevel === 3 && pin.length < 4) return true;
    if (signatureLevel === 4 && !sigName) return true;
    return false;
  }, [submitDisabled, allGatesSatisfied, fields, values, signatureLevel, sigName, pin]);

  // L0: fire onSubmit immediately, render nothing
  React.useEffect(() => {
    if (isL0) {
      onSubmit({});
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isL0]);
  if (isL0) return null;

  const handleSubmit = () => {
    if (computedDisabled) return;
    const result: Record<string, unknown> = { ...values };
    // Backend SIGNED actions require `signature` (JSON object) in the payload.
    // Map frontend signature levels to the backend contract shape.
    if (signatureLevel === 3) {
      result.signature = {
        method: 'pin',
        pin,
        signed_at: new Date().toISOString(),
      };
    }
    if (signatureLevel === 2 || signatureLevel === 4) {
      result.signature = {
        method: 'name',
        name: sigName,
        signed_at: new Date().toISOString(),
      };
    }
    onSubmit(result);
  };

  // Resolve submit label
  const resolvedSubmitLabel =
    submitLabel ??
    (mode === 'read'
      ? 'Close'
      : signatureLevel === 3
        ? 'Verify'
        : signatureLevel === 4
          ? 'Sign'
          : 'Confirm');

  // Backdrop click closes
  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) onClose();
  };

  return (
    // eslint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-static-element-interactions
    <div
      className={`${s.backdrop} ${backdropClass(mode, signatureLevel)}`}
      onClick={handleBackdropClick}
      data-testid="action-popup-backdrop"
    >
      <div
        className={`${s.popup} ${mode === 'read' ? s.popupRead : s.popupMutate}`}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        data-testid="action-popup"
        style={hasEntitySearch ? { maxWidth: 640 } : undefined}
      >
        {/* Header */}
        <div className={s.popupHdr}>
          <div className={s.popupHdrText}>
            <div className={s.popupTitle}>{title}</div>
            {subtitle && <div className={s.popupSubtitle}>{subtitle}</div>}
          </div>
          <button
            className={s.popupClose}
            onClick={onClose}
            aria-label="Close"
            data-testid="action-popup-close"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M12 4L4 12M4 4l8 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </button>
        </div>

        {/* Divider (mutate only) */}
        {mode === 'mutate' && <div className={s.popupDivider} />}

        {/* Source-context block — prefill keys that are not editable fields. */}
        {sourceRows.length > 0 && <SourceBlock rows={sourceRows} />}

        {/* Body — fields */}
        <div className={mode === 'read' ? s.popupBodyRead : s.popupBody}>
          {fields.map((field) => (
            <div
              key={field.name}
              className={s.field}
              data-testid={`popup-field-${field.name}`}
            >
              <div className={s.fieldLabel}>{field.label}</div>
              {renderField(field, values[field.name] ?? '', (v) =>
                setValue(field.name, v)
              )}
            </div>
          ))}
        </div>

        {/* Data gates */}
        {gates && gates.length > 0 && (
          <div className={s.popupGates}>
            {gates.map((gate, i) => (
              <div
                key={i}
                className={`${s.gate} ${gate.satisfied ? s.gateSatisfied : s.gatePending}`}
              >
                {gate.satisfied ? (
                  <svg className={s.gateIcon} viewBox="0 0 14 14" fill="none">
                    <path d="M3 7l3 3 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                ) : (
                  <svg className={s.gateIcon} viewBox="0 0 14 14" fill="none">
                    <circle cx="7" cy="7" r="5.5" stroke="currentColor" strokeWidth="1.3" />
                    <path d="M7 4v4M7 10v.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                  </svg>
                )}
                {gate.label}
              </div>
            ))}
          </div>
        )}

        {/* Preview summary */}
        {previewRows && previewRows.length > 0 && (
          <div className={s.popupPreview}>
            <div className={s.previewBox}>
              <div className={s.previewHeading}>Summary</div>
              {previewRows.map((row, i) => (
                <div key={i} className={s.previewRow}>
                  <span className={s.previewKey}>{row.key}</span>
                  <span className={s.previewVal}>{row.value}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Signature section */}
        {mode === 'mutate' && signatureLevel === 1 && <SigL1 />}
        {mode === 'mutate' && signatureLevel === 2 && (
          <SigL2 sigName={sigName} onSigNameChange={setSigName} />
        )}
        {mode === 'mutate' && signatureLevel === 3 && (
          <SigL3 pin={pin} onPinChange={setPin} />
        )}
        {mode === 'mutate' && signatureLevel === 4 && (
          <SigL4
            sigName={sigName}
            onSigNameChange={setSigName}
            onClearPad={() => setSigName('')}
          />
        )}
        {mode === 'mutate' && signatureLevel === 5 && <SigL5 />}

        {/* Footer */}
        {mode === 'read' ? (
          <div className={s.popupFooterRead}>
            <button className={s.btnCancel} onClick={onClose}>
              Close
            </button>
          </div>
        ) : (
          <div className={s.popupFooter}>
            <button className={s.btnCancel} onClick={onClose}>
              Cancel
            </button>
            <button
              className={`${s.btnSubmit} ${computedDisabled ? s.btnSubmitDisabled : ''}`}
              disabled={computedDisabled}
              onClick={handleSubmit}
              data-testid="signature-confirm-button"
            >
              {resolvedSubmitLabel}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
