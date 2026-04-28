'use client';

import * as React from 'react';
import s from '../../popup.module.css';

// ---------------------------------------------------------------------------
// Sub-components: Signature levels
// ---------------------------------------------------------------------------

export function SigL1() {
  return null; // L1 just uses the Confirm footer button
}

export function SigL2({
  sigName,
  onSigNameChange,
}: {
  sigName: string;
  onSigNameChange: (v: string) => void;
}) {
  return (
    <div className={s.popupSig}>
      <div className={s.sigLabel}>Attestation</div>
      <div className={s.sigDeclaration}>
        <div className={s.sigDeclarationText}>
          I confirm that the information provided is accurate and complete to the
          best of my knowledge, and I accept responsibility for this action.
        </div>
      </div>
      <input
        className={s.sigNameInput}
        type="text"
        placeholder="Type your full name to confirm"
        value={sigName}
        onChange={(e) => onSigNameChange(e.target.value)}
      />
      <div className={s.sigNameHint}>
        Name must match your account profile
      </div>
    </div>
  );
}

export function SigL3({
  pin,
  onPinChange,
}: {
  pin: string;
  onPinChange: (v: string) => void;
}) {
  const inputRef = React.useRef<HTMLInputElement>(null);
  const digits = pin.padEnd(4, ' ').slice(0, 4).split('');

  const handleClick = () => inputRef.current?.focus();

  return (
    <div className={s.popupSig}>
      <div className={s.sigLabel}>Verification</div>
      <div className={s.sigPinLabel}>Enter your 4-digit PIN</div>
      {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-static-element-interactions */}
      <div className={s.sigPin} onClick={handleClick}>
        {digits.map((d, i) => {
          const filled = d !== ' ';
          const active = i === pin.length && pin.length < 4;
          const cls = [
            s.pinDigit,
            filled ? s.pinDigitFilled : s.pinDigitEmpty,
            active ? s.pinDigitActive : '',
          ]
            .filter(Boolean)
            .join(' ');
          return (
            <div key={i} className={cls}>
              {filled ? '•' : ''}
            </div>
          );
        })}
        <input
          ref={inputRef}
          className={s.pinHiddenInput}
          type="password"
          inputMode="numeric"
          maxLength={4}
          value={pin}
          onChange={(e) => {
            const v = e.target.value.replace(/\D/g, '').slice(0, 4);
            onPinChange(v);
          }}
          autoFocus
          data-testid="signature-pin-input"
        />
      </div>
    </div>
  );
}

export function SigL4({
  sigName,
  onSigNameChange,
  onClearPad,
}: {
  sigName: string;
  onSigNameChange: (v: string) => void;
  onClearPad?: () => void;
}) {
  return (
    <div className={s.popupSig}>
      <div className={s.sigLabel}>Wet Signature</div>
      <div className={s.sigPad}>
        <span className={s.sigPadHint}>Draw signature here</span>
        <button
          type="button"
          className={s.sigPadClear}
          onClick={onClearPad}
        >
          Clear
        </button>
      </div>
      <div className={s.sigPadMeta}>
        <input
          type="text"
          placeholder="Printed name"
          value={sigName}
          onChange={(e) => onSigNameChange(e.target.value)}
        />
        <input
          type="text"
          className={s.sigPadAutoDate}
          value={new Date().toISOString().slice(0, 10)}
          readOnly
        />
      </div>
    </div>
  );
}

export function SigL5() {
  return (
    <div className={s.popupSig}>
      <div className={s.sigLabel}>Approval Chain</div>
      <div className={s.chainProgress}>
        {/* Example chain — in production this would be driven by data */}
        <div className={`${s.chainStep}`}>
          <div className={`${s.chainDot} ${s.chainDotDone}`}>
            <svg className={s.chainDotIcon} viewBox="0 0 14 14" fill="none">
              <path d="M3 7l3 3 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <div className={s.chainRole}>Requester</div>
          <div className={s.chainStatus}>Submitted</div>
        </div>
        <div className={`${s.chainLine} ${s.chainLineDone}`} />
        <div className={`${s.chainStep} ${s.chainStepCurrent}`}>
          <div className={`${s.chainDot} ${s.chainDotCurrent}`}>2</div>
          <div className={s.chainRole}>HOD</div>
          <div className={s.chainStatus}>Awaiting</div>
        </div>
        <div className={s.chainLine} />
        <div className={s.chainStep}>
          <div className={`${s.chainDot} ${s.chainDotPending}`}>3</div>
          <div className={s.chainRole}>Captain</div>
          <div className={s.chainStatus}>Pending</div>
        </div>
      </div>
    </div>
  );
}
