'use client';

import * as React from 'react';
import s from '../../popup.module.css';
import type { ActionPopupField } from '../shared/types';

export function FieldPersonAssign({ field }: { field: ActionPopupField }) {
  return (
    <div className={s.personDisplay}>
      <div className={s.personAvatar}>
        <svg className={s.personAvatarIcon} viewBox="0 0 16 16" fill="none">
          <circle cx="8" cy="5" r="3" stroke="currentColor" strokeWidth="1.3" />
          <path d="M2.5 14c0-3 2.5-5 5.5-5s5.5 2 5.5 5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
        </svg>
      </div>
      <span className={s.personName}>{field.value ?? field.placeholder ?? 'Assign...'}</span>
    </div>
  );
}
