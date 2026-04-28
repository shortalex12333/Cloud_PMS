'use client';

import * as React from 'react';
import s from '../../popup.module.css';
import { useAuth } from '@/hooks/useAuth';
import type { ActionPopupField } from '../shared/types';

// ── Domain icon SVGs (matches SpotlightResultRow icons) ──────────────────────
function DomainIcon({ domain }: { domain: string }) {
  const d = domain.toLowerCase();
  if (d.includes('part') || d.includes('inventory'))
    return <svg viewBox="0 0 16 16" fill="none" style={{ width: 14, height: 14, flexShrink: 0, color: 'var(--txt-secondary)' }}><rect x="2" y="5" width="12" height="8" rx="1.5" stroke="currentColor" strokeWidth="1.3"/><path d="M5 5V3.5A1.5 1.5 0 016.5 2h3A1.5 1.5 0 0111 3.5V5" stroke="currentColor" strokeWidth="1.3"/></svg>;
  if (d.includes('equipment'))
    return <svg viewBox="0 0 16 16" fill="none" style={{ width: 14, height: 14, flexShrink: 0, color: 'var(--txt-secondary)' }}><circle cx="8" cy="8" r="2.5" stroke="currentColor" strokeWidth="1.3"/><path d="M8 1v2M8 13v2M1 8h2M13 8h2M3.05 3.05l1.42 1.42M11.53 11.53l1.42 1.42M3.05 12.95l1.42-1.42M11.53 4.47l1.42-1.42" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/></svg>;
  if (d.includes('fault'))
    return <svg viewBox="0 0 16 16" fill="none" style={{ width: 14, height: 14, flexShrink: 0, color: 'var(--txt-secondary)' }}><path d="M8 2L14 13H2L8 2z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round"/><path d="M8 6v3M8 11v.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/></svg>;
  if (d.includes('work_order') || d.includes('workorder'))
    return <svg viewBox="0 0 16 16" fill="none" style={{ width: 14, height: 14, flexShrink: 0, color: 'var(--txt-secondary)' }}><rect x="2" y="1" width="12" height="14" rx="1.5" stroke="currentColor" strokeWidth="1.3"/><path d="M5 5h6M5 8h6M5 11h4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/></svg>;
  if (d.includes('crew') || d.includes('person'))
    return <svg viewBox="0 0 16 16" fill="none" style={{ width: 14, height: 14, flexShrink: 0, color: 'var(--txt-secondary)' }}><circle cx="8" cy="5" r="3" stroke="currentColor" strokeWidth="1.3"/><path d="M2.5 14c0-3 2.5-5 5.5-5s5.5 2 5.5 5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/></svg>;
  // generic
  return <svg viewBox="0 0 16 16" fill="none" style={{ width: 14, height: 14, flexShrink: 0, color: 'var(--txt-secondary)' }}><rect x="2" y="2" width="12" height="12" rx="2" stroke="currentColor" strokeWidth="1.3"/></svg>;
}

// Build rich subtitle from raw domain record fields
function buildResultSubtitle(r: Record<string, unknown>, domain: string): string {
  const meta: string[] = [];
  if (r.part_number)      meta.push(`P/N ${r.part_number}`);
  if (r.wo_number)        meta.push(String(r.wo_number));
  if (r.fault_code)       meta.push(String(r.fault_code));
  if (r.code && !r.part_number && !r.wo_number) meta.push(String(r.code));
  if (r.manufacturer)     meta.push(String(r.manufacturer));
  if (r.location)         meta.push(String(r.location));
  if (r.category)         meta.push(String(r.category));
  if (r.status)           meta.push(String(r.status).replace(/_/g, ' '));
  if (r.quantity_on_hand !== undefined && r.quantity_on_hand !== null)
                          meta.push(`Qty: ${r.quantity_on_hand}`);
  if (r.serial_number && meta.length < 3) meta.push(String(r.serial_number));
  if (r.priority && meta.length < 3)     meta.push(String(r.priority));
  // Fallback: description snippet
  if (meta.length === 0 && r.description)
    return String(r.description).slice(0, 80);
  return meta.slice(0, 4).join(' · ');
}

interface EntitySearchResult {
  id: string;
  title: string;
  subtitle: string;
  object_type: string;
}

function mapDomainRecord(r: Record<string, unknown>, domain: string): EntitySearchResult {
  const title = String(
    r.title || r.name || r.equipment_name || r.part_name ||
    r.section_title || r.document_name || r.filename || r.id || ''
  ).trim() || String(r.id || '');
  return {
    id: String(r.id || r.primary_id || ''),
    title,
    subtitle: buildResultSubtitle(r, domain),
    object_type: String(r.object_type || r.type || domain),
  };
}

export function FieldEntitySearch({
  field,
  value,
  onChange,
}: {
  field: ActionPopupField;
  value: string;
  onChange: (v: string) => void;
}) {
  const { user, session } = useAuth();
  const [query, setQuery] = React.useState('');
  const [displayLabel, setDisplayLabel] = React.useState('');
  const [results, setResults] = React.useState<EntitySearchResult[]>([]);
  const [showDropdown, setShowDropdown] = React.useState(false);
  const [activeIdx, setActiveIdx] = React.useState(-1);
  const debounceRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  const domain = field.search_domain || 'equipment';

  const handleSearch = React.useCallback(
    (q: string) => {
      setQuery(q);
      setActiveIdx(-1);
      if (debounceRef.current) clearTimeout(debounceRef.current);
      if (!q || q.length < 2) { setResults([]); setShowDropdown(false); return; }
      debounceRef.current = setTimeout(async () => {
        try {
          const yachtId = user?.yachtId || '';
          const jwt = session?.access_token || '';
          if (!yachtId) { setResults([]); setShowDropdown(false); return; }
          const apiBase = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
          const resp = await fetch(
            `${apiBase}/api/vessel/${yachtId}/domain/${domain}/records?q=${encodeURIComponent(q)}&limit=15`,
            { headers: jwt ? { Authorization: `Bearer ${jwt}` } : {} },
          );
          if (resp.ok) {
            const data = await resp.json();
            const records: Record<string, unknown>[] = data.records || data.results || [];
            const mapped = records.map((r) => mapDomainRecord(r, domain)).filter((r) => r.id);
            setResults(mapped.slice(0, 10));
            setShowDropdown(mapped.length > 0);
          }
        } catch { setResults([]); setShowDropdown(false); }
      }, 250);
    },
    [domain, user?.yachtId, session?.access_token]
  );

  const handleSelect = React.useCallback(
    (item: EntitySearchResult) => {
      onChange(item.id);
      setDisplayLabel(item.title);
      setQuery(item.title);
      setShowDropdown(false);
      setActiveIdx(-1);
    },
    [onChange]
  );

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!showDropdown) return;
    if (e.key === 'ArrowDown') { e.preventDefault(); setActiveIdx((i) => Math.min(i + 1, results.length - 1)); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setActiveIdx((i) => Math.max(i - 1, 0)); }
    else if (e.key === 'Enter' && activeIdx >= 0) { e.preventDefault(); handleSelect(results[activeIdx]); }
    else if (e.key === 'Escape') { setShowDropdown(false); }
  };

  return (
    <div className={s.entitySearchWrap} style={{ position: 'relative' }}>
      <svg className={s.entitySearchIcon} viewBox="0 0 16 16" fill="none">
        <circle cx="7" cy="7" r="4.5" stroke="currentColor" strokeWidth="1.3" />
        <path d="M10.5 10.5L14 14" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
      </svg>
      <input
        type="text"
        value={displayLabel || query}
        placeholder={field.placeholder ?? `Search ${domain.replace(/_/g, ' ')}...`}
        onChange={(e) => {
          setDisplayLabel('');
          handleSearch(e.target.value);
          if (!e.target.value) onChange('');
        }}
        onFocus={() => results.length > 0 && setShowDropdown(true)}
        onBlur={() => setTimeout(() => setShowDropdown(false), 150)}
        onKeyDown={handleKeyDown}
      />
      {showDropdown && results.length > 0 && (
        <div style={{
          position: 'absolute', top: 'calc(100% + 4px)', left: 0, right: 0,
          maxHeight: 360, overflowY: 'auto',
          background: 'var(--surface-elevated)',
          border: '1px solid var(--surface-border)',
          borderRadius: 8,
          boxShadow: '0 8px 24px rgba(0,0,0,0.28), 0 2px 6px rgba(0,0,0,0.16)',
          zIndex: 200,
        }}>
          {results.map((item, idx) => (
            <div
              key={item.id}
              onMouseDown={() => handleSelect(item)}
              onMouseEnter={() => setActiveIdx(idx)}
              style={{
                display: 'flex', alignItems: 'flex-start', gap: 10,
                padding: '10px 14px',
                cursor: 'pointer',
                background: idx === activeIdx ? 'var(--surface-hover)' : 'transparent',
                borderBottom: idx < results.length - 1 ? '1px solid var(--surface-border)' : 'none',
                transition: 'background 80ms',
              }}
            >
              <div style={{ marginTop: 2 }}>
                <DomainIcon domain={item.object_type || domain} />
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--txt-primary)', lineHeight: 1.4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {item.title}
                </div>
                {item.subtitle && (
                  <div style={{ fontSize: 11, color: 'var(--txt-secondary)', lineHeight: 1.5, marginTop: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', letterSpacing: '0.01em' }}>
                    {item.subtitle}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
