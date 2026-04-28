'use client';

import * as React from 'react';
import s from '../../popup.module.css';
import type { ActionPopupField } from '../shared/types';

export function FieldKvRead({ field }: { field: ActionPopupField }) {
  return (
    <div className={s.fieldValue}>
      {field.entityRef ? (
        <span className={s.fieldValueEntityRef}>{field.entityRef.label}</span>
      ) : (
        field.value ?? '—'
      )}
    </div>
  );
}
