'use client';

import * as React from 'react';
import { PREFILL_NEVER_RENDER, PREFILL_MONO_KEYS, PREFILL_LABEL_OVERRIDES } from '@/lib/field-schema';

// ---------------------------------------------------------------------------
// Source-context block (renders prefill keys NOT in fields[])
// ---------------------------------------------------------------------------

/** `serial_number` -> "Serial number"; "running_hours" -> "Running hours". */
function humanizeKey(key: string): string {
  const override = PREFILL_LABEL_OVERRIDES[key];
  if (override) return override;
  const spaced = key.replace(/_/g, ' ').trim();
  if (!spaced) return key;
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

export interface SourceRow {
  key: string;
  label: string;
  value: string;
  mono: boolean;
}

export function buildSourceRows(
  prefill: Record<string, unknown> | undefined,
  fieldNames: Set<string>,
): SourceRow[] {
  if (!prefill) return [];
  const rows: SourceRow[] = [];
  // Insertion order — Object.keys preserves it for string keys.
  for (const key of Object.keys(prefill)) {
    if (PREFILL_NEVER_RENDER.has(key)) continue;
    if (fieldNames.has(key)) continue;
    const raw = prefill[key];
    if (raw === null || raw === undefined) continue;

    let value: string;
    let mono = PREFILL_MONO_KEYS.has(key);

    if (typeof raw === 'string') {
      value = raw;
    } else if (typeof raw === 'number') {
      value = String(raw);
      mono = true;
    } else if (typeof raw === 'boolean') {
      value = raw ? 'Yes' : 'No';
    } else {
      // array / object — last-resort stringify, truncated.
      const json = JSON.stringify(raw);
      value = json && json.length > 60 ? json.slice(0, 60) + '…' : json ?? '';
    }

    rows.push({ key, label: humanizeKey(key), value, mono });
  }
  return rows;
}

export function SourceBlock({ rows }: { rows: SourceRow[] }) {
  return (
    <div
      data-testid="action-popup-source"
      style={{
        margin: '0 24px',
        padding: '12px 0 12px 0',
        borderBottom: '1px solid var(--border-faint)',
      }}
    >
      <div
        style={{
          fontSize: 10,
          fontWeight: 600,
          textTransform: 'uppercase',
          letterSpacing: '0.06em',
          color: 'var(--txt3)',
          marginBottom: 8,
          fontFamily: 'var(--font-sans)',
        }}
      >
        Source
      </div>
      {rows.map((row) => (
        <div
          key={row.key}
          data-testid={`action-popup-source-row-${row.key}`}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            minHeight: 44,
            fontSize: 12,
          }}
        >
          <span
            style={{
              color: 'var(--txt3)',
              minWidth: 112,
              fontSize: 10,
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
              fontFamily: 'var(--font-sans)',
            }}
          >
            {row.label}
          </span>
          <span
            data-testid={`action-popup-source-val-${row.key}`}
            style={{
              color: 'var(--txt2)',
              fontFamily: row.mono ? 'var(--font-mono)' : 'var(--font-sans)',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}
          >
            {row.value}
          </span>
        </div>
      ))}
    </div>
  );
}
