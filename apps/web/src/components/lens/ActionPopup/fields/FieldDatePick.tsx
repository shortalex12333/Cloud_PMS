'use client';

import * as React from 'react';
import s from '../../popup.module.css';
import type { ActionPopupField } from '../shared/types';

export function FieldDatePick({
  field,
  value,
  onChange,
}: {
  field: ActionPopupField;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className={s.dateDisplay}>
      <svg className={s.dateDisplayIcon} viewBox="0 0 16 16" fill="none">
        <rect x="2" y="3" width="12" height="11" rx="2" stroke="currentColor" strokeWidth="1.3" />
        <path d="M2 7h12M5 1v4M11 1v4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
      </svg>
      {value ? (
        <span className={s.dateDisplayValue}>{value}</span>
      ) : (
        <span className={s.dateDisplayPlaceholder}>
          {field.placeholder ?? 'Pick date...'}
        </span>
      )}
      <input
        type="date"
        className={s.dateNative}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}
