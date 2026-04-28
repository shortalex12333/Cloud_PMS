'use client';

import * as React from 'react';
import s from '../../popup.module.css';
import type { ActionPopupField } from '../shared/types';

export function FieldTextArea({
  field,
  value,
  onChange,
}: {
  field: ActionPopupField;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className={s.fieldInput}>
      <textarea
        value={value}
        placeholder={field.placeholder}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}
