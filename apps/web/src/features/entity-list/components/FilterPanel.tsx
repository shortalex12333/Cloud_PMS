'use client';

/**
 * FilterPanel — Sidebar filter panel for entity list views.
 * Renders domain pills, quick presets, active filter pills,
 * and collapsible filter categories with chip groups.
 * Matches prototype: public/prototypes/filter-panel.html
 */

import React, { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import { X, ChevronDown } from 'lucide-react';
import type { FilterFieldConfig, ActiveFilters, DateRange } from '../types/filter-config';
import { isDateRange, FILTER_CATEGORY_LABELS } from '../types/filter-config';
import { getFiltersByDomain } from '@/lib/filters/catalog';
import type { QuickFilter } from '@/lib/filters/catalog';
import { mapLegacyFilter } from '@/lib/filters/mapLegacyFilter';


interface FilterPanelProps {
  filters: FilterFieldConfig[];
  activeFilters: ActiveFilters;
  onChange: (filters: ActiveFilters) => void;
  activeDomain: string;
  totalCount?: number;
  isOpen?: boolean;
  onClose?: () => void;
}

export function FilterPanel({
  filters,
  activeFilters,
  onChange,
  activeDomain,
  totalCount,
  isOpen,
  onClose,
}: FilterPanelProps) {
  const activeCount = Object.keys(activeFilters).length;

  // Quick presets from catalog
  const quickPresets = useMemo(() => getFiltersByDomain(activeDomain), [activeDomain]);

  // Group filters by category
  const categories = useMemo(() => {
    const groups: Record<string, FilterFieldConfig[]> = {};
    for (const f of filters) {
      const cat = f.category || 'properties';
      if (!groups[cat]) groups[cat] = [];
      groups[cat].push(f);
    }
    return groups;
  }, [filters]);

  // Track collapsed state per category
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>(() => {
    const init: Record<string, boolean> = {};
    for (const cat of Object.keys(categories)) {
      init[cat] = cat !== 'status-priority'; // status-priority open by default
    }
    return init;
  });

  const toggleCollapsed = useCallback((cat: string) => {
    setCollapsed(prev => ({ ...prev, [cat]: !prev[cat] }));
  }, []);

  const setFilter = useCallback((key: string, value: string | string[] | DateRange | null) => {
    const next = { ...activeFilters };
    if (value === null || value === '' || (Array.isArray(value) && value.length === 0)) {
      delete next[key];
    } else {
      next[key] = value;
    }
    onChange(next);
  }, [activeFilters, onChange]);

  const clearAll = useCallback(() => { onChange({}); }, [onChange]);

  // Apply a quick preset
  const applyPreset = useCallback((preset: QuickFilter) => {
    const mapped = mapLegacyFilter(preset.filter_id);
    if (mapped) {
      onChange({ ...activeFilters, ...mapped });
    }
  }, [activeFilters, onChange]);

  // Count active filters per category
  const countPerCategory = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const f of filters) {
      const cat = f.category || 'properties';
      if (activeFilters[f.key] != null) {
        counts[cat] = (counts[cat] || 0) + 1;
      }
    }
    return counts;
  }, [filters, activeFilters]);

  const panelStyle: React.CSSProperties = {
    width: 280,
    flexShrink: 0,
    background: 'var(--surface)',
    borderRight: '1px solid var(--border-sub)',
    overflowY: 'auto',
    overflowX: 'hidden',
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
  };

  return (
    <aside style={panelStyle} data-testid="filter-panel">
      {/* Domain pills and Quick Presets removed — sidebar handles domain
         switching, subbar chips handle presets. Filter panel is for
         power-user filters only: status, priority, dates. */}

      {/* Active Filter Pills */}
      {activeCount > 0 && (
        <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--border-faint)' }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, alignItems: 'center' }}>
            {Object.entries(activeFilters).map(([key, value]) => {
              const field = filters.find(f => f.key === key);
              const label = field?.label || key;
              const displayValue = formatFilterValue(field, value);
              return (
                <span key={key} style={activePillStyle}>
                  {label}: {displayValue}
                  <button
                    onClick={() => setFilter(key, null)}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0, display: 'flex', color: 'inherit' }}
                    aria-label={`Clear ${label} filter`}
                  >
                    <X style={{ width: 12, height: 12 }} strokeWidth={2} />
                  </button>
                </span>
              );
            })}
            <button onClick={clearAll} style={clearAllStyle}>
              Clear all
            </button>
          </div>
        </div>
      )}

      {/* 4. Collapsible Filter Categories */}
      {Object.entries(categories).map(([cat, fields]) => {
        const isCollapsed = collapsed[cat] ?? false;
        const count = countPerCategory[cat] || 0;
        return (
          <div key={cat} style={{ borderBottom: '1px solid var(--border-faint)' }}>
            {/* Category Header */}
            <button
              onClick={() => toggleCollapsed(cat)}
              style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '14px 16px', minHeight: 44, width: '100%',
                cursor: 'pointer', background: 'none', border: 'none',
                transition: 'background 60ms',
              }}
            >
              <span style={{ ...overlineStyle, marginBottom: 0, flex: 1, textAlign: 'left' as const }}>
                {FILTER_CATEGORY_LABELS[cat] || cat}
              </span>
              {count > 0 && (
                <span style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  width: 18, height: 18, borderRadius: '50%',
                  background: 'var(--teal-bg)', color: 'var(--mark)',
                  fontSize: 10, fontWeight: 600, fontFamily: 'var(--font-mono)',
                }}>
                  {count}
                </span>
              )}
              <ChevronDown
                style={{
                  width: 12, height: 12, color: 'var(--txt-ghost)',
                  transition: 'transform 200ms ease',
                  transform: isCollapsed ? 'rotate(-90deg)' : 'rotate(0deg)',
                }}
                strokeWidth={2}
              />
            </button>

            {/* Category Body */}
            {!isCollapsed && (
              <div style={{ padding: '0 16px 14px' }}>
                {fields.map(field => (
                  <FilterCategoryControl
                    key={field.key}
                    field={field}
                    value={activeFilters[field.key] ?? null}
                    onChange={(val) => setFilter(field.key, val)}
                  />
                ))}
              </div>
            )}
          </div>
        );
      })}
    </aside>
  );
}

// =============================================================================
// Filter controls for category sections
// =============================================================================

interface FilterCategoryControlProps {
  field: FilterFieldConfig;
  value: string | string[] | DateRange | null;
  onChange: (value: string | string[] | DateRange | null) => void;
}

function FilterCategoryControl({ field, value, onChange }: FilterCategoryControlProps) {
  switch (field.type) {
    case 'select':
    case 'multi-select':
      return <ChipGroup field={field} value={value} onChange={onChange} />;
    case 'date-range':
      return <DateRangeControl field={field} value={isDateRange(value) ? value : null} onChange={onChange} />;
    case 'text':
      return <TextControl field={field} value={typeof value === 'string' ? value : ''} onChange={onChange} />;
    default:
      return null;
  }
}

// =============================================================================
// Chip Group (for select/multi-select filters)
// =============================================================================

function ChipGroup({ field, value, onChange }: FilterCategoryControlProps) {
  const selected = Array.isArray(value) ? value : (typeof value === 'string' && value ? [value] : []);

  const toggleChip = useCallback((chipValue: string) => {
    if (field.type === 'multi-select') {
      const next = selected.includes(chipValue)
        ? selected.filter(v => v !== chipValue)
        : [...selected, chipValue];
      onChange(next.length > 0 ? next : null);
    } else {
      // Single select: toggle on/off
      onChange(selected.includes(chipValue) ? null : chipValue);
    }
  }, [field.type, selected, onChange]);

  return (
    <div style={{ marginBottom: 10 }}>
      <span style={chipGroupLabelStyle}>{field.label}</span>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
        {field.options?.map(opt => {
          const isSelected = selected.includes(opt.value);
          return (
            <button
              key={opt.value}
              onClick={() => toggleChip(opt.value)}
              style={{
                ...chipBase,
                ...(isSelected ? chipSelected : {}),
              }}
            >
              {opt.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

// =============================================================================
// Date Range Control
// =============================================================================

function DateRangeControl({ field, value, onChange }: { field: FilterFieldConfig; value: DateRange | null; onChange: (v: DateRange | null) => void }) {
  const applyQuickRange = useCallback((days: number) => {
    const now = new Date();
    const from = new Date();
    if (days === 0) {
      // Today
      const iso = now.toISOString().split('T')[0];
      onChange({ from: iso, to: iso });
    } else if (days === 7) {
      // This week (Mon-Sun)
      const day = now.getDay();
      const monday = new Date(now);
      monday.setDate(now.getDate() - (day === 0 ? 6 : day - 1));
      const sunday = new Date(monday);
      sunday.setDate(monday.getDate() + 6);
      onChange({ from: monday.toISOString().split('T')[0], to: sunday.toISOString().split('T')[0] });
    } else if (days === 30) {
      from.setDate(now.getDate() - 30);
      onChange({ from: from.toISOString().split('T')[0], to: now.toISOString().split('T')[0] });
    } else if (days === 90) {
      // This quarter
      const qMonth = Math.floor(now.getMonth() / 3) * 3;
      const qStart = new Date(now.getFullYear(), qMonth, 1);
      const qEnd = new Date(now.getFullYear(), qMonth + 3, 0);
      onChange({ from: qStart.toISOString().split('T')[0], to: qEnd.toISOString().split('T')[0] });
    }
  }, [onChange]);

  return (
    <div style={{ marginBottom: 10 }}>
      <span style={chipGroupLabelStyle}>{field.label}</span>
      <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 4 }}>
          <label style={dateLabel}>From</label>
          <input
            type="date"
            value={value?.from || ''}
            onChange={e => {
              const from = e.target.value;
              if (!from) { onChange(null); return; }
              onChange({ from, to: value?.to || from });
            }}
            style={dateInputStyle}
          />
        </div>
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 4 }}>
          <label style={dateLabel}>To</label>
          <input
            type="date"
            value={value?.to || ''}
            onChange={e => {
              const to = e.target.value;
              if (!to) { onChange(null); return; }
              onChange({ from: value?.from || to, to });
            }}
            style={dateInputStyle}
          />
        </div>
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
        {[
          { label: 'Today', days: 0 },
          { label: 'This Week', days: 7 },
          { label: 'Last 30d', days: 30 },
          { label: 'This Quarter', days: 90 },
        ].map(q => (
          <button key={q.label} onClick={() => applyQuickRange(q.days)} style={dateQuickBtnStyle}>
            {q.label}
          </button>
        ))}
      </div>
    </div>
  );
}

// =============================================================================
// Text Control
// =============================================================================

function TextControl({ field, value, onChange }: { field: FilterFieldConfig; value: string; onChange: (v: string | null) => void }) {
  const [local, setLocal] = useState(value);
  const timerRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => { setLocal(value); }, [value]);

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const v = e.target.value;
    setLocal(v);
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => { onChange(v || null); }, 300);
  }, [onChange]);

  return (
    <div style={{ marginBottom: 10 }}>
      <label style={dateLabel}>{field.label}</label>
      <input
        type="text"
        value={local}
        onChange={handleChange}
        placeholder={field.placeholder || field.label}
        style={textInputStyle}
      />
    </div>
  );
}

// =============================================================================
// Helpers
// =============================================================================

function formatFilterValue(field: FilterFieldConfig | undefined, value: string | string[] | DateRange): string {
  if (isDateRange(value)) return `${value.from} – ${value.to}`;
  if (Array.isArray(value)) return value.map(v => field?.options?.find(o => o.value === v)?.label || v).join(', ');
  return field?.options?.find(o => o.value === value)?.label || value;
}

// =============================================================================
// Style constants (matching prototype)
// =============================================================================

const overlineStyle: React.CSSProperties = {
  fontSize: 10,
  fontWeight: 600,
  textTransform: 'uppercase',
  letterSpacing: '0.08em',
  color: 'var(--txt3)',
  marginBottom: 10,
};


const activePillStyle: React.CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: 5,
  minHeight: 44,
  padding: '0 10px',
  borderRadius: 6,
  fontSize: 11,
  fontWeight: 500,
  background: 'var(--teal-bg)',
  color: 'var(--mark)',
};

const clearAllStyle: React.CSSProperties = {
  minHeight: 44,
  display: 'flex',
  alignItems: 'center',
  fontSize: 11,
  fontWeight: 500,
  color: 'var(--red)',
  padding: '0 6px',
  background: 'none',
  border: 'none',
  cursor: 'pointer',
};

const chipGroupLabelStyle: React.CSSProperties = {
  fontSize: 11,
  fontWeight: 500,
  color: 'var(--txt2)',
  marginBottom: 6,
  display: 'block',
};

const chipBase: React.CSSProperties = {
  minHeight: 44,
  padding: '0 11px',
  borderRadius: 6,
  fontSize: 12,
  fontWeight: 500,
  display: 'flex',
  alignItems: 'center',
  background: 'var(--neutral-bg)',
  color: 'var(--txt3)',
  border: 'none',
  cursor: 'pointer',
  transition: 'background 60ms, color 60ms',
};

const chipSelected: React.CSSProperties = {
  background: 'var(--teal-bg)',
  color: 'var(--mark)',
};

const dateLabel: React.CSSProperties = {
  fontSize: 10,
  fontWeight: 600,
  textTransform: 'uppercase',
  letterSpacing: '0.06em',
  color: 'var(--txt-ghost)',
  display: 'block',
  marginBottom: 4,
};

const dateInputStyle: React.CSSProperties = {
  minHeight: 44,
  padding: '0 10px',
  borderRadius: 6,
  fontSize: 12,
  fontFamily: 'var(--font-mono)',
  background: 'var(--neutral-bg)',
  color: 'var(--txt)',
  border: '1px solid var(--border-sub)',
  width: '100%',
  colorScheme: 'dark',
};

const dateQuickBtnStyle: React.CSSProperties = {
  minHeight: 44,
  padding: '0 10px',
  borderRadius: 6,
  fontSize: 11,
  fontWeight: 500,
  background: 'var(--neutral-bg)',
  color: 'var(--txt3)',
  border: 'none',
  cursor: 'pointer',
  transition: 'background 60ms, color 60ms',
};

const textInputStyle: React.CSSProperties = {
  width: '100%',
  minHeight: 44,
  padding: '0 12px',
  borderRadius: 6,
  fontSize: 13,
  background: 'var(--neutral-bg)',
  color: 'var(--txt)',
  border: '1px solid var(--border-sub)',
};
