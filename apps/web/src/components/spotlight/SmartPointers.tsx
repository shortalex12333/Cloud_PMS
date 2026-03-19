'use client';

/**
 * SmartPointers — "Needs your attention" section
 * Per elegant.html prototype: collapsible, severity-colored left border,
 * entity-type icons, mono subtitles, time deltas.
 */

import React, { useState, useEffect } from 'react';
import {
  AlertTriangle, ClipboardList, Package, Shield, ArrowRightLeft, Clock,
} from 'lucide-react';
import { supabase } from '@/lib/supabaseClient';
import { useAuth } from '@/hooks/useAuth';

interface Pointer {
  id: string;
  severity: 'critical' | 'warning' | 'info' | 'ok';
  icon: 'fault' | 'work_order' | 'inventory' | 'certificate' | 'receiving' | 'hours_of_rest';
  main: string;
  sub: string;
  time: string;
  overflow?: boolean;
}

const ICON_MAP = {
  fault: AlertTriangle,
  work_order: ClipboardList,
  inventory: Package,
  certificate: Shield,
  receiving: ArrowRightLeft,
  hours_of_rest: Clock,
};

function timeDelta(date: string | null): string {
  if (!date) return '';
  const diff = Date.now() - new Date(date).getTime();
  const days = Math.floor(diff / 86400000);
  const hours = Math.floor(diff / 3600000);
  if (days > 0) return `${days}d`;
  if (hours > 0) return `${hours}h ago`;
  return 'now';
}

export default function SmartPointers() {
  const { user } = useAuth();
  const [pointers, setPointers] = useState<Pointer[]>([]);
  const [collapsed, setCollapsed] = useState(false);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    if (!user?.yachtId) return;
    loadPointers();
  }, [user?.yachtId]);

  async function loadPointers() {
    const items: Pointer[] = [];

    const { data: faults } = await supabase
      .from('faults')
      .select('id, title, status, created_at, priority')
      .in('status', ['open', 'investigating'])
      .order('priority', { ascending: true })
      .limit(3);

    faults?.forEach(f => {
      items.push({
        id: `fault-${f.id}`,
        severity: f.priority === 'critical' || f.priority === 'high' ? 'critical' : 'warning',
        icon: 'fault',
        main: `<strong>${f.title || 'Unnamed Fault'}</strong> is open`,
        sub: `FAULT · ${f.status?.toUpperCase() || 'OPEN'}`,
        time: timeDelta(f.created_at),
      });
    });

    const { data: wos } = await supabase
      .from('work_orders')
      .select('id, title, status, due_date, reference_number')
      .eq('status', 'open')
      .lt('due_date', new Date().toISOString())
      .order('due_date', { ascending: true })
      .limit(3);

    wos?.forEach(w => {
      items.push({
        id: `wo-${w.id}`,
        severity: 'critical',
        icon: 'work_order',
        main: `<strong>${w.title || 'Work Order'}</strong> is overdue`,
        sub: `WORK ORDER · ${w.reference_number || w.id.slice(0, 8)}`,
        time: timeDelta(w.due_date),
      });
    });

    const { data: inv } = await supabase
      .from('inventory')
      .select('id, name, quantity_on_hand, minimum_quantity')
      .not('minimum_quantity', 'is', null)
      .limit(50);

    inv?.filter(i => (i.quantity_on_hand ?? 0) <= (i.minimum_quantity ?? 0))
      .slice(0, 2)
      .forEach(i => {
        items.push({
          id: `inv-${i.id}`,
          severity: 'warning',
          icon: 'inventory',
          main: `<strong>${i.name || 'Item'}</strong> — ${i.quantity_on_hand ?? 0} units remaining`,
          sub: `INVENTORY · BELOW MIN STOCK`,
          time: `${i.quantity_on_hand ?? 0} left`,
        });
      });

    setPointers(items.map((item, idx) => ({ ...item, overflow: idx >= 5 })));
  }

  const visiblePointers = expanded ? pointers : pointers.filter(p => !p.overflow);
  const overflowCount = pointers.filter(p => p.overflow).length;

  if (pointers.length === 0) return null;

  return (
    <div style={{ width: '100%', marginTop: 8, display: 'flex', flexDirection: 'column' }}>
      <div
        onClick={() => setCollapsed(!collapsed)}
        style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '10px 2px 6px', cursor: 'pointer', userSelect: 'none' }}
      >
        <span style={{ fontSize: 9, fontWeight: 600, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'rgba(255,255,255,0.40)', transition: 'color 80ms' }}>
          Needs your attention
        </span>
        {collapsed && <span style={{ fontSize: 9, fontFamily: 'var(--font-mono)', color: 'rgba(255,255,255,0.40)' }}>({pointers.length})</span>}
        <svg
          style={{ width: 10, height: 10, color: 'rgba(255,255,255,0.40)', transition: 'transform 200ms', marginLeft: 'auto', transform: collapsed ? 'rotate(-90deg)' : 'none' }}
          viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5"
        >
          <path d="M2 3.5l3 3 3-3" />
        </svg>
      </div>

      {!collapsed && (
        <div>
          {visiblePointers.map(pointer => {
            const Icon = ICON_MAP[pointer.icon] || AlertTriangle;
            const borderColor = pointer.severity === 'critical' ? 'var(--red)' : pointer.severity === 'warning' ? 'var(--amber)' : pointer.severity === 'info' ? 'var(--teal)' : 'var(--green)';
            const iconColor = pointer.severity === 'critical' ? 'var(--red)' : pointer.severity === 'warning' ? 'var(--amber)' : pointer.severity === 'info' ? 'var(--teal)' : 'var(--green)';
            const timeColor = pointer.severity === 'critical' ? 'var(--red)' : pointer.severity === 'warning' ? 'var(--amber)' : 'rgba(255,255,255,0.40)';
            return (
              <div key={pointer.id} style={{
                display: 'flex', alignItems: 'center', gap: 10,
                padding: '9px 13px 9px 12px', borderRadius: 4, cursor: 'pointer',
                transition: 'background 80ms', background: '#181614',
                borderTop: '1px solid rgba(255,255,255,0.09)',
                borderRight: '1px solid rgba(255,255,255,0.05)',
                borderBottom: '1px solid rgba(255,255,255,0.03)',
                borderLeft: `2px solid ${borderColor}`,
                marginBottom: 4,
              }}>
                <Icon style={{ width: 14, height: 14, flexShrink: 0, color: iconColor }} strokeWidth={1.6} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.92)', lineHeight: 1.4, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}
                    dangerouslySetInnerHTML={{ __html: pointer.main }}
                  />
                  <div style={{ fontSize: 10.5, color: 'rgba(255,255,255,0.70)', fontFamily: 'var(--font-mono)', letterSpacing: '0.03em', marginTop: 1 }}>
                    {pointer.sub}
                  </div>
                </div>
                <div style={{ fontSize: 10.5, color: timeColor, fontFamily: 'var(--font-mono)', flexShrink: 0, whiteSpace: 'nowrap', opacity: pointer.severity === 'critical' ? 0.85 : pointer.severity === 'warning' ? 0.80 : 1 }}>
                  {pointer.time}
                </div>
              </div>
            );
          })}
          {overflowCount > 0 && (
            <div onClick={() => setExpanded(!expanded)} style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '7px 12px 6px', cursor: 'pointer', color: 'rgba(255,255,255,0.40)',
              fontSize: 11, userSelect: 'none', borderRadius: 3,
            }}>
              <svg style={{ width: 12, height: 12, transition: 'transform 200ms', transform: expanded ? 'rotate(180deg)' : 'none' }}
                viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M2 4l4 4 4-4" />
              </svg>
              <span style={{ fontFamily: 'var(--font-mono)', letterSpacing: '0.04em' }}>
                {expanded ? 'Show less' : `+ ${overflowCount} more`}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
