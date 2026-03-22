'use client';

/**
 * FilterBar — Horizontal filter strip for entity list views.
 * Renders dropdowns, date pickers, and text inputs based on FilterFieldConfig.
 * Active filters shown as clearable pills.
 */

import React, { useCallback, useRef, useState, useEffect } from 'react';
import { X, ChevronDown, Filter } from 'lucide-react';
import type { FilterFieldConfig, ActiveFilters, DateRange } from '../types/filter-config';
import { isDateRange } from '../types/filter-config';

interface FilterBarProps {
  filters: FilterFieldConfig[];
  activeFilters: ActiveFilters;
  onChange: (filters: ActiveFilters) => void;
  totalCount?: number;
}

export function FilterBar({ filters, activeFilters, onChange, totalCount }: FilterBarProps) {
  const activeCount = Object.keys(activeFilters).length;

  const setFilter = useCallback((key: string, value: string | string[] | DateRange | null) => {
    const next = { ...activeFilters };
    if (value === null || value === '' || (Array.isArray(value) && value.length === 0)) {
      delete next[key];
    } else {
      next[key] = value;
    }
    onChange(next);
  }, [activeFilters, onChange]);

  const clearAll = useCallback(() => {
    onChange({});
  }, [onChange]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
      {/* Filter controls row */}
      <div
        style={{
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '8px 16px',
          borderBottom: '1px solid var(--border-faint)',
          background: 'var(--surface-el)',
          overflowX: 'auto',
          flexShrink: 0,
        }}
      >
        <Filter style={{ width: 13, height: 13, color: 'var(--txt-ghost)', flexShrink: 0 }} strokeWidth={1.6} />

        {filters.map(field => (
          <FilterControl
            key={field.key}
            field={field}
            value={activeFilters[field.key] ?? null}
            onChange={(val) => setFilter(field.key, val)}
          />
        ))}

        {activeCount > 0 && (
          <button
            onClick={clearAll}
            style={{
              display: 'flex', alignItems: 'center', gap: 4,
              padding: '4px 8px', borderRadius: 3,
              border: 'none', background: 'none', cursor: 'pointer',
              fontSize: 10, fontFamily: 'var(--font-mono)',
              color: 'var(--red)', letterSpacing: '0.04em',
              whiteSpace: 'nowrap',
            }}
          >
            <X style={{ width: 10, height: 10 }} strokeWidth={2} />
            Clear all
          </button>
        )}

        {totalCount != null && (
          <span style={{
            marginLeft: 'auto', fontSize: 10, fontFamily: 'var(--font-mono)',
            color: 'var(--txt-ghost)', whiteSpace: 'nowrap', flexShrink: 0,
          }}>
            {totalCount} item{totalCount !== 1 ? 's' : ''}
          </span>
        )}
      </div>

      {/* Active filter pills */}
      {activeCount > 0 && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 6,
          padding: '6px 16px',
          borderBottom: '1px solid var(--border-faint)',
          background: 'var(--surface-base)',
          flexWrap: 'wrap',
        }}>
          <span style={{ fontSize: 10, color: 'var(--txt-ghost)', letterSpacing: '0.08em', textTransform: 'uppercase', fontWeight: 600 }}>
            Filtered:
          </span>
          {Object.entries(activeFilters).map(([key, value]) => {
            const field = filters.find(f => f.key === key);
            const label = field?.label || key;
            const displayValue = formatFilterValue(field, value);
            return (
              <span
                key={key}
                style={{
                  display: 'inline-flex', alignItems: 'center', gap: 4,
                  padding: '2px 8px', borderRadius: 3,
                  background: 'var(--teal-faint, rgba(0,196,180,0.1))',
                  border: '1px solid var(--teal-border, rgba(0,196,180,0.2))',
                  fontSize: 10.5, fontFamily: 'var(--font-mono)',
                  color: 'var(--teal)', letterSpacing: '0.03em',
                }}
              >
                {label}: {displayValue}
                <button
                  onClick={() => setFilter(key, null)}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0, display: 'flex', color: 'inherit' }}
                  aria-label={`Clear ${label} filter`}
                >
                  <X style={{ width: 10, height: 10 }} strokeWidth={2} />
                </button>
              </span>
            );
          })}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Individual filter controls
// =============================================================================

interface FilterControlProps {
  field: FilterFieldConfig;
  value: string | string[] | DateRange | null;
  onChange: (value: string | string[] | DateRange | null) => void;
}

function FilterControl({ field, value, onChange }: FilterControlProps) {
  switch (field.type) {
    case 'select':
      return <SelectFilter field={field} value={typeof value === 'string' ? value : null} onChange={onChange} />;
    case 'date-range':
      return <DateRangeFilter field={field} value={isDateRange(value) ? value : null} onChange={onChange} />;
    case 'text':
      return <TextFilter field={field} value={typeof value === 'string' ? value : ''} onChange={onChange} />;
    default:
      return null;
  }
}

// =============================================================================
// Select dropdown
// =============================================================================

function SelectFilter({ field, value, onChange }: { field: FilterFieldConfig; value: string | null; onChange: (v: string | null) => void }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  const selected = field.options?.find(o => o.value === value);

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button
        onClick={() => setOpen(!open)}
        style={{
          display: 'flex', alignItems: 'center', gap: 4,
          padding: '4px 8px', borderRadius: 3,
          border: `1px solid ${value ? 'var(--teal)' : 'var(--border-sub)'}`,
          background: value ? 'var(--teal-faint, rgba(0,196,180,0.08))' : 'var(--surface-base)',
          cursor: 'pointer', fontSize: 11, fontFamily: 'var(--font-mono)',
          color: value ? 'var(--teal)' : 'var(--txt2)',
          letterSpacing: '0.03em', whiteSpace: 'nowrap',
        }}
      >
        {selected?.label || field.label}
        <ChevronDown style={{ width: 10, height: 10, transform: open ? 'rotate(180deg)' : 'none', transition: 'transform 150ms' }} strokeWidth={2} />
      </button>

      {open && (
        <div style={{
          position: 'absolute', top: '100%', left: 0, marginTop: 4,
          minWidth: 140, borderRadius: 4, overflow: 'hidden',
          background: 'var(--surface-el)', border: '1px solid var(--border-sub)',
          boxShadow: '0 4px 12px rgba(0,0,0,0.3)', zIndex: 50,
        }}>
          {value && (
            <button
              onClick={() => { onChange(null); setOpen(false); }}
              style={{
                width: '100%', padding: '7px 10px', border: 'none', textAlign: 'left',
                background: 'none', cursor: 'pointer',
                fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--txt-ghost)',
                borderBottom: '1px solid var(--border-faint)',
              }}
            >
              All
            </button>
          )}
          {field.options?.map(opt => (
            <button
              key={opt.value}
              onClick={() => { onChange(opt.value); setOpen(false); }}
              style={{
                width: '100%', padding: '7px 10px', border: 'none', textAlign: 'left',
                background: opt.value === value ? 'var(--teal-faint, rgba(0,196,180,0.1))' : 'none',
                cursor: 'pointer', fontSize: 11, fontFamily: 'var(--font-mono)',
                color: opt.value === value ? 'var(--teal)' : 'var(--txt)',
              }}
            >
              {opt.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Date range picker (from/to)
// =============================================================================

function DateRangeFilter({ field, value, onChange }: { field: FilterFieldConfig; value: DateRange | null; onChange: (v: DateRange | null) => void }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
      <span style={{ fontSize: 10, color: 'var(--txt-ghost)', fontFamily: 'var(--font-mono)' }}>{field.label}:</span>
      <input
        type="date"
        value={value?.from || ''}
        onChange={e => {
          const from = e.target.value;
          if (!from) { onChange(null); return; }
          onChange({ from, to: value?.to || from });
        }}
        style={{
          padding: '3px 6px', borderRadius: 3,
          border: '1px solid var(--border-sub)', background: 'var(--surface-base)',
          fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--txt)',
          colorScheme: 'dark',
        }}
      />
      <span style={{ fontSize: 10, color: 'var(--txt-ghost)' }}>–</span>
      <input
        type="date"
        value={value?.to || ''}
        onChange={e => {
          const to = e.target.value;
          if (!to) { onChange(null); return; }
          onChange({ from: value?.from || to, to });
        }}
        style={{
          padding: '3px 6px', borderRadius: 3,
          border: '1px solid var(--border-sub)', background: 'var(--surface-base)',
          fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--txt)',
          colorScheme: 'dark',
        }}
      />
    </div>
  );
}

// =============================================================================
// Text search filter
// =============================================================================

function TextFilter({ field, value, onChange }: { field: FilterFieldConfig; value: string; onChange: (v: string | null) => void }) {
  const [local, setLocal] = useState(value);
  const timerRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => { setLocal(value); }, [value]);

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const v = e.target.value;
    setLocal(v);
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      onChange(v || null);
    }, 300);
  }, [onChange]);

  return (
    <input
      type="text"
      value={local}
      onChange={handleChange}
      placeholder={field.placeholder || field.label}
      style={{
        padding: '4px 8px', borderRadius: 3, width: 120,
        border: `1px solid ${value ? 'var(--teal)' : 'var(--border-sub)'}`,
        background: value ? 'var(--teal-faint, rgba(0,196,180,0.08))' : 'var(--surface-base)',
        fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--txt)',
        letterSpacing: '0.03em',
      }}
    />
  );
}

// =============================================================================
// Helpers
// =============================================================================

function formatFilterValue(field: FilterFieldConfig | undefined, value: string | string[] | DateRange): string {
  if (isDateRange(value)) {
    return `${value.from} – ${value.to}`;
  }
  if (Array.isArray(value)) {
    return value.map(v => field?.options?.find(o => o.value === v)?.label || v).join(', ');
  }
  return field?.options?.find(o => o.value === value)?.label || value;
}
