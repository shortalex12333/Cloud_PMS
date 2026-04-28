'use client';

import * as React from 'react';
import s from '../../popup.module.css';

export function FieldAttachment() {
  return (
    <div className={s.uploadZone}>
      <svg className={s.uploadZoneIcon} viewBox="0 0 20 20" fill="none">
        <path d="M10 4v8M6 8l4-4 4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M3 14v2a2 2 0 002 2h10a2 2 0 002-2v-2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
      <div className={s.uploadText}>
        <span className={s.uploadTextTeal}>Click to upload</span> or drag and drop
      </div>
    </div>
  );
}
