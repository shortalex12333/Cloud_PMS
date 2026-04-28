'use client';

import * as React from 'react';
import type { ActionPopupField } from '../shared/types';
import { FieldKvRead } from './FieldKvRead';
import { FieldKvEdit } from './FieldKvEdit';
import { FieldTextArea } from './FieldTextArea';
import { FieldSelect } from './FieldSelect';
import { FieldDatePick } from './FieldDatePick';
import { FieldEntitySearch } from './FieldEntitySearch';
import { FieldPersonAssign } from './FieldPersonAssign';
import { FieldAttachment } from './FieldAttachment';

// ---------------------------------------------------------------------------
// Field dispatcher
// ---------------------------------------------------------------------------

export function renderField(
  field: ActionPopupField,
  value: string,
  onChange: (v: string) => void
): React.ReactNode {
  switch (field.type) {
    case 'kv-read':
      return <FieldKvRead field={field} />;
    case 'kv-edit':
      return <FieldKvEdit field={field} value={value} onChange={onChange} />;
    case 'text-area':
      return <FieldTextArea field={field} value={value} onChange={onChange} />;
    case 'select':
    case 'status-set':
      return <FieldSelect field={field} value={value} onChange={onChange} />;
    case 'date-pick':
      return <FieldDatePick field={field} value={value} onChange={onChange} />;
    case 'entity-search':
      return <FieldEntitySearch field={field} value={value} onChange={onChange} />;
    case 'person-assign':
      return <FieldPersonAssign field={field} />;
    case 'attachment':
      return <FieldAttachment />;
    case 'signature':
      // Signature fields are handled by the SigLX components, not inline
      return <FieldKvRead field={field} />;
    default:
      return <FieldKvRead field={field} />;
  }
}
