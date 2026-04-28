'use client';

import * as React from 'react';
import s from '../../popup.module.css';
import type { ActionPopupField } from '../shared/types';

export function FieldSelect({
  field,
  value,
  onChange,
}: {
  field: ActionPopupField;
  value: string;
  onChange: (v: string) => void;
}) {
  const selectedLabel = field.options?.find((o) => o.value === value)?.label;
  return (
    <div className={s.selectDisplay}>
      {selectedLabel ? (
        <span className={s.selectDisplayText}>{selectedLabel}</span>
      ) : (
        <span className={s.selectDisplayPlaceholder}>
          {field.placeholder ?? 'Select...'}
        </span>
      )}
      <svg className={s.selectDisplayIcon} viewBox="0 0 12 12" fill="none">
        <path d="M3 5l3 3 3-3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <select
        className={s.selectNative}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">{field.placeholder ?? 'Select...'}</option>
        {field.options?.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  );
}
