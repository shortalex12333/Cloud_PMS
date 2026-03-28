'use client';

/**
 * VesselSurface — Phase 1D of the Interface Pivot
 *
 * The new home screen after authentication. Replaces the centred search stage.
 * Shows current vessel state: what is true about this vessel RIGHT NOW.
 *
 * NOT a dashboard. No charts. No KPIs. No time-series. No analytics.
 * Status rows only. Orientation before search.
 *
 * Layout: two columns on desktop (main: WOs + Faults, side: Handover +
 * Parts Below Min + Activity + Certs). Single column below 900px.
 *
 * Spec: celeste-interface-pivot-spec.pdf §03
 * Prototype: vessel-surface-v2.html (visual reference only)
 */

import * as React from 'react';
import { useRouter } from 'next/navigation';
import {
  ClipboardList,
  AlertTriangle,
  FileSignature,
  Package,
  Activity,
  Award,
  ChevronRight,
  Plus,
} from 'lucide-react';
import type { DomainId } from './Sidebar';
import { useVesselSurface } from './hooks';
import type { VesselSurfaceResponse } from './api';

/* ─────────────────────────────────────────────
   TYPES
   ───────────────────────────────────────────── */

interface SurfaceWorkOrder {
  id: string;
  ref: string;
  title: string;
  equipment: string;
  assigned: string;
  status: 'open' | 'overdue' | 'due_soon' | 'in_progress';
  age: string;
}

interface SurfaceFault {
  id: string;
  ref: string;
  title: string;
  equipment: string;
  severity: 'critical' | 'warning' | 'open';
  age: string;
}

interface SurfaceHandover {
  id: string;
  from: string;
  to: string;
  date: string;
  status: 'signed' | 'pending' | 'draft';
}

interface SurfacePart {
  id: string;
  name: string;
  stock: number;
  minStock: number;
  location: string;
}

interface SurfaceActivityItem {
  id: string;
  ref: string;
  action: string;
  actor: string;
  time: string;
}

interface SurfaceCertificate {
  id: string;
  name: string;
  daysRemaining: number;
  status: 'expiring' | 'expired' | 'valid';
}

/* ─────────────────────────────────────────────
   STATIC MOCK DATA
   Replace with live data from ENGINEER01's
   GET /api/vessel/{id}/surface endpoint
   ───────────────────────────────────────────── */

const MOCK_WORK_ORDERS: SurfaceWorkOrder[] = [
  { id: 'WO-1042', ref: 'WO\u00b71042', title: 'Main Engine Inspection', equipment: 'E-007 Main Engine', assigned: 'J. Morrison', status: 'overdue', age: '5d' },
  { id: 'WO-1038', ref: 'WO\u00b71038', title: 'Generator Service — 500hr', equipment: 'E-012 Stbd Generator', assigned: 'R. Costa', status: 'due_soon', age: '2d' },
  { id: 'WO-1035', ref: 'WO\u00b71035', title: 'Watermaker Membrane Replace', equipment: 'E-022 Watermaker', assigned: 'Unassigned', status: 'open', age: '8d' },
];

const MOCK_FAULTS: SurfaceFault[] = [
  { id: 'F-088', ref: 'F\u00b7088', title: 'Port Engine Abnormal Vibration', equipment: 'E-007 Main Engine', severity: 'critical', age: '2d' },
  { id: 'F-085', ref: 'F\u00b7085', title: 'AC Unit 3 — Low Refrigerant', equipment: 'E-041 AC Unit 3', severity: 'warning', age: '4d' },
];

const MOCK_HANDOVER: SurfaceHandover = {
  id: 'HO-019', from: 'J. Morrison', to: 'R. Costa', date: '22 Mar 2026', status: 'signed',
};

const MOCK_PARTS: SurfacePart[] = [
  { id: 'P-0441', name: 'Oil Filter 20W-50', stock: 1, minStock: 3, location: 'Engine Room' },
  { id: 'P-0312', name: 'Impeller — Jabsco 17937', stock: 0, minStock: 2, location: 'Engine Room' },
  { id: 'P-0587', name: 'Zinc Anode M8', stock: 2, minStock: 4, location: 'Lazarette' },
];

const MOCK_ACTIVITY: SurfaceActivityItem[] = [
  { id: '1', ref: 'F\u00b7088', action: 'escalated to critical', actor: 'R. Costa', time: '2h ago' },
  { id: '2', ref: 'WO\u00b71042', action: 'comment added', actor: 'J. Morrison', time: '4h ago' },
  { id: '3', ref: 'P\u00b70312', action: 'stock updated to 0', actor: 'System', time: '6h ago' },
  { id: '4', ref: 'HO\u00b7019', action: 'signed', actor: 'J. Morrison', time: '1d ago' },
  { id: '5', ref: 'WO\u00b71038', action: 'assigned to R. Costa', actor: 'Captain', time: '1d ago' },
];

const MOCK_CERTIFICATES: SurfaceCertificate[] = [
  { id: 'C-004', name: 'Safety Equipment Certificate', daysRemaining: 12, status: 'expiring' },
  { id: 'C-009', name: 'ISM Document of Compliance', daysRemaining: 38, status: 'expiring' },
];

/* ─────────────────────────────────────────────
   MAIN COMPONENT
   ───────────────────────────────────────────── */

export function VesselSurface() {
  const router = useRouter();
  const { data: liveData } = useVesselSurface();

  // Derive display data from live endpoint, fall back to static mock
  const workOrders = liveData?.work_orders?.items?.length
    ? liveData.work_orders.items.map((wo) => ({
        id: wo.id,
        ref: wo.id.replace('-', '\u00b7'),
        title: wo.title,
        equipment: wo.equipment_name || wo.equipment_id || '',
        assigned: wo.assigned_to || 'Unassigned',
        status: wo.status as SurfaceWorkOrder['status'],
        age: wo.age_days !== undefined ? `${wo.age_days}d` : '\u2014',
      }))
    : MOCK_WORK_ORDERS;

  const faults = liveData?.faults?.items?.length
    ? liveData.faults.items.map((f) => ({
        id: f.id,
        ref: f.id.replace('-', '\u00b7'),
        title: f.title,
        equipment: f.equipment_name || f.equipment_id || '',
        severity: (f.severity || f.status || 'open') as SurfaceFault['severity'],
        age: f.age_days !== undefined ? `${f.age_days}d` : '\u2014',
      }))
    : MOCK_FAULTS;

  const handover = liveData?.last_handover
    ? {
        id: liveData.last_handover.id,
        from: liveData.last_handover.from_crew,
        to: liveData.last_handover.to_crew,
        date: new Date(liveData.last_handover.signed_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }),
        status: liveData.last_handover.status as SurfaceHandover['status'],
      }
    : MOCK_HANDOVER;

  const parts = liveData?.parts_below_min?.items?.length
    ? liveData.parts_below_min.items.map((p) => ({
        id: p.id,
        name: p.name,
        stock: p.stock_level,
        minStock: p.min_stock,
        location: p.location || '',
      }))
    : MOCK_PARTS;

  const activity = liveData?.recent_activity?.length
    ? liveData.recent_activity.map((a) => ({
        id: a.entity_id,
        ref: a.entity_ref,
        action: a.action,
        actor: a.actor,
        time: formatTimeAgo(a.timestamp),
      }))
    : MOCK_ACTIVITY;

  const certificates = liveData?.certificates_expiring?.items?.length
    ? liveData.certificates_expiring.items.map((c) => ({
        id: c.id,
        name: c.name,
        daysRemaining: c.days_remaining,
        status: (c.days_remaining <= 0 ? 'expired' : c.days_remaining <= 45 ? 'expiring' : 'valid') as SurfaceCertificate['status'],
      }))
    : MOCK_CERTIFICATES;

  const woCount = liveData?.work_orders?.open_count ?? MOCK_WORK_ORDERS.length;
  const faultCount = liveData?.faults?.open_count ?? MOCK_FAULTS.length;
  const partsCount = liveData?.parts_below_min?.count ?? MOCK_PARTS.length;
  const certCount = liveData?.certificates_expiring?.count ?? MOCK_CERTIFICATES.length;

  const navigateToDomain = React.useCallback(
    (domain: DomainId) => {
      const paths: Partial<Record<DomainId, string>> = {
        'work-orders': '/work-orders',
        faults: '/faults',
        'handover-export': '/handover-export',
        inventory: '/inventory',
        certificates: '/certificates',
      };
      const path = paths[domain];
      if (path) router.push(path);
    },
    [router]
  );

  return (
    <div
      style={{
        flex: 1,
        overflowY: 'auto',
        padding: '16px 20px 40px',
        display: 'grid',
        gridTemplateColumns: '1fr 1fr 1fr',
        gap: 14,
        alignContent: 'start',
      }}
    >
      {/* ── MAIN COLUMN ── */}

      {/* Work Orders — spans 2 columns per spec §03 */}
      <SurfaceCard
        span={2}
        icon={ClipboardList}
        label="Work Orders"
        count={woCount}
        countSeverity={workOrders.some(w => w.status === 'overdue') ? 'warning' : undefined}
        onHeaderClick={() => navigateToDomain('work-orders')}
      >
        {workOrders.map((wo) => (
          <SurfaceRow
            key={wo.id}
            severity={wo.status === 'overdue' ? 'critical' : wo.status === 'due_soon' ? 'warning' : undefined}
            title={<><span style={{ color: 'var(--mark)', fontSize: 11, fontFamily: 'var(--font-mono, ui-monospace, monospace)' }}>{wo.ref}</span> {wo.title}</>}
            meta={wo.equipment}
            pill={{ label: wo.status.replace('_', ' '), variant: statusToVariant(wo.status) }}
            time={wo.age}
            onClick={() => router.push(`/work-orders?id=${wo.id}`)}
          />
        ))}
        <SurfaceFooter
          count={12}
          label="work orders"
          onClick={() => navigateToDomain('work-orders')}
        />
        <QuickActions
          actions={[
            { label: 'Create Work Order', onClick: () => router.push('/work-orders') },
          ]}
        />
      </SurfaceCard>

      {/* Faults */}
      <SurfaceCard
        icon={AlertTriangle}
        label="Faults"
        count={faultCount}
        countSeverity={faults.some(f => f.severity === 'critical') ? 'critical' : undefined}
        onHeaderClick={() => navigateToDomain('faults')}
      >
        {faults.map((f) => (
          <SurfaceRow
            key={f.id}
            severity={f.severity === 'critical' ? 'critical' : f.severity === 'warning' ? 'warning' : undefined}
            title={<><span style={{ color: 'var(--mark)', fontSize: 11, fontFamily: 'var(--font-mono, ui-monospace, monospace)' }}>{f.ref}</span> {f.title}</>}
            meta={f.equipment}
            pill={{ label: f.severity, variant: f.severity === 'critical' ? 'critical' : f.severity === 'warning' ? 'warn' : 'open' }}
            time={f.age}
            onClick={() => router.push(`/faults?id=${f.id}`)}
          />
        ))}
        <SurfaceFooter
          count={5}
          label="open faults"
          onClick={() => navigateToDomain('faults')}
        />
        <QuickActions
          actions={[
            { label: 'Log Fault', onClick: () => router.push('/faults') },
          ]}
        />
      </SurfaceCard>

      {/* ── SIDE COLUMN ── */}

      {/* Last Handover */}
      <SurfaceCard
        icon={FileSignature}
        label="Last Handover"
        onHeaderClick={() => navigateToDomain('handover-export')}
      >
        <SurfaceRow
          severity={handover.status === 'signed' ? 'info' : undefined}
          title={<>{handover.from} \u2192 {handover.to}</>}
          meta={handover.date}
          pill={{ label: handover.status, variant: handover.status === 'signed' ? 'signed' : 'open' }}
          onClick={() => router.push(`/handover-export?id=${handover.id}`)}
        />
      </SurfaceCard>

      {/* Parts Below Threshold */}
      <SurfaceCard
        icon={Package}
        label="Parts Below Min"
        count={partsCount}
        countSeverity={parts.some(p => p.stock === 0) ? 'critical' : 'warning'}
        onHeaderClick={() => navigateToDomain('inventory')}
      >
        {parts.map((p) => (
          <SurfaceRow
            key={p.id}
            severity={p.stock === 0 ? 'critical' : 'warning'}
            title={p.name}
            meta={`${p.location} \u00b7 ${p.stock}/${p.minStock} in stock`}
            stockBar={{ current: p.stock, min: p.minStock }}
            onClick={() => router.push(`/inventory?id=${p.id}`)}
          />
        ))}
        <SurfaceFooter
          count={partsCount}
          label="below threshold"
          onClick={() => navigateToDomain('inventory')}
        />
        <QuickActions
          actions={[
            { label: 'Add to Shopping List', onClick: () => router.push('/shopping-list') },
          ]}
        />
      </SurfaceCard>

      {/* Recent Activity */}
      <SurfaceCard
        icon={Activity}
        label="Recent Activity"
      >
        {activity.map((a) => (
          <div
            key={a.id}
            style={{
              display: 'flex',
              alignItems: 'baseline',
              gap: 7,
              padding: '6px 12px',
              borderTop: '1px solid var(--border-faint)',
              cursor: 'pointer',
              transition: 'background 60ms',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--surface-hover)'; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
          >
            <div style={{ width: 4, height: 4, borderRadius: '50%', background: 'var(--border-sub)', flexShrink: 0, marginTop: 5 }} />
            <span style={{ flex: 1, minWidth: 0, fontSize: 11, color: 'var(--txt2)', lineHeight: 1.5 }}>
              <span style={{ color: 'var(--txt)', fontWeight: 500 }}>{a.actor}</span>{' '}
              {a.action}{' '}
              <span style={{ color: 'var(--mark)' }}>{a.ref}</span>
            </span>
            <span style={{ fontSize: 9.5, color: 'var(--txt-ghost)', fontFamily: 'var(--font-mono, ui-monospace, monospace)', flexShrink: 0 }}>
              {a.time}
            </span>
          </div>
        ))}
      </SurfaceCard>

      {/* Certificates Expiring */}
      <SurfaceCard
        icon={Award}
        label="Certificates"
        count={certCount}
        countSeverity={certificates.some(c => c.daysRemaining < 30) ? 'warning' : undefined}
        onHeaderClick={() => navigateToDomain('certificates')}
      >
        {certificates.map((c) => (
          <SurfaceRow
            key={c.id}
            severity={c.daysRemaining < 30 ? 'warning' : undefined}
            title={c.name}
            meta={`Expires in ${c.daysRemaining} days`}
            pill={{ label: c.status, variant: c.status === 'expiring' ? 'warn' : c.status === 'expired' ? 'critical' : 'open' }}
            time={`${c.daysRemaining}d`}
            onClick={() => router.push(`/certificates?id=${c.id}`)}
          />
        ))}
      </SurfaceCard>
    </div>
  );
}

/* ─────────────────────────────────────────────
   SURFACE CARD — glass container for each section
   ───────────────────────────────────────────── */

function SurfaceCard({
  icon: Icon,
  label,
  count,
  countSeverity,
  onHeaderClick,
  span,
  children,
}: {
  icon: React.ElementType;
  label: string;
  count?: number;
  countSeverity?: 'critical' | 'warning' | 'ok';
  onHeaderClick?: () => void;
  span?: number;
  children: React.ReactNode;
}) {
  const countColor =
    countSeverity === 'critical' ? 'var(--red)'
    : countSeverity === 'warning' ? 'var(--amber)'
    : countSeverity === 'ok' ? 'var(--green)'
    : 'var(--txt3)';

  return (
    <div
      style={{
        /* Glass card — asymmetric borders per spec §06. Not tokenised because
           each edge has a different opacity to simulate light direction. */
        gridColumn: span ? `span ${span}` : undefined,
        background: 'var(--glass-bg)',
        backdropFilter: 'blur(14px)',
        WebkitBackdropFilter: 'blur(14px)',
        borderTop: '1px solid var(--border-top)',
        borderRight: '1px solid var(--border-side)',
        borderBottom: '1px solid var(--border-bottom)',
        borderLeft: '1px solid var(--border-side)',
        borderRadius: 4,
        overflow: 'hidden',
      }}
    >
      {/* Section header — clickable, navigates to domain list */}
      <div
        onClick={onHeaderClick}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 7,
          padding: '8px 12px 7px',
          borderBottom: '1px solid var(--border-faint)',
          cursor: onHeaderClick ? 'pointer' : 'default',
          transition: 'background 70ms',
        }}
        onMouseEnter={(e) => { if (onHeaderClick) e.currentTarget.style.background = 'var(--surface-hover)'; }}
        onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
      >
        <Icon style={{ width: 12, height: 12, color: 'var(--txt3)', flexShrink: 0 }} />
        <span
          style={{
            fontSize: 8,
            fontWeight: 700,
            letterSpacing: '0.12em',
            textTransform: 'uppercase',
            color: 'var(--txt3)',
            flex: 1,
          }}
        >
          {label}
        </span>
        {count !== undefined && (
          <span
            style={{
              fontSize: 10,
              fontFamily: 'var(--font-mono, ui-monospace, monospace)',
              color: countColor,
              fontWeight: countSeverity === 'critical' || countSeverity === 'warning' ? 600 : 400,
            }}
          >
            {count}
          </span>
        )}
        {onHeaderClick && (
          <ChevronRight style={{ width: 12, height: 12, color: 'var(--txt-ghost)' }} />
        )}
      </div>

      {children}
    </div>
  );
}

/* ─────────────────────────────────────────────
   SURFACE ROW — status row inside a card
   38px min-height. Left accent bar for severity.
   ───────────────────────────────────────────── */

type PillVariant = 'open' | 'overdue' | 'critical' | 'warn' | 'signed' | 'pending';

function SurfaceRow({
  severity,
  title,
  meta,
  pill,
  time,
  stockBar,
  onClick,
}: {
  severity?: 'critical' | 'warning' | 'info';
  title: React.ReactNode;
  meta?: string;
  pill?: { label: string; variant: PillVariant };
  time?: string;
  stockBar?: { current: number; min: number };
  onClick?: () => void;
}) {
  const accentColor =
    severity === 'critical' ? 'var(--red)'
    : severity === 'warning' ? 'var(--amber)'
    : severity === 'info' ? 'var(--teal)'
    : 'transparent';

  return (
    <div
      onClick={onClick}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        padding: '7px 12px',
        minHeight: 38,
        borderTop: '1px solid var(--border-faint)',
        borderLeft: `2px solid ${accentColor}`,
        cursor: onClick ? 'pointer' : 'default',
        transition: 'background 60ms',
      }}
      onMouseEnter={(e) => { if (onClick) e.currentTarget.style.background = 'var(--surface-hover)'; }}
      onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
    >
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--txt)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {title}
        </div>
        {meta && (
          <div style={{ fontSize: 10.5, color: 'var(--txt3)', fontFamily: 'var(--font-mono, ui-monospace, monospace)', marginTop: 1 }}>
            {meta}
          </div>
        )}
      </div>

      {stockBar && (
        <div style={{ width: 32, height: 3, background: 'var(--border-sub)', borderRadius: 2, overflow: 'hidden', flexShrink: 0 }}>
          <div
            style={{
              height: '100%',
              borderRadius: 2,
              width: `${Math.max(5, (stockBar.current / stockBar.min) * 100)}%`,
              background: stockBar.current === 0 ? 'var(--red)' : 'var(--amber)',
            }}
          />
        </div>
      )}

      {pill && <StatusPill label={pill.label} variant={pill.variant} />}

      {time && (
        <span
          style={{
            fontSize: 10,
            color: severity === 'critical' ? 'var(--red)' : severity === 'warning' ? 'var(--amber)' : 'var(--txt-ghost)',
            fontFamily: 'var(--font-mono, ui-monospace, monospace)',
            whiteSpace: 'nowrap',
            flexShrink: 0,
            opacity: severity ? 0.75 : 1,
          }}
        >
          {time}
        </span>
      )}
    </div>
  );
}

/* ─────────────────────────────────────────────
   STATUS PILL — 17px height, uppercase
   ───────────────────────────────────────────── */

const PILL_STYLES: Record<PillVariant, { bg: string; color: string; border: string }> = {
  open:     { bg: 'var(--status-neutral-bg)', color: 'var(--txt3)', border: 'var(--border-sub)' },
  overdue:  { bg: 'var(--red-bg)', color: 'var(--red)', border: 'var(--red-border)' },
  critical: { bg: 'var(--red-bg)', color: 'var(--red)', border: 'var(--red-border)' },
  warn:     { bg: 'var(--amber-bg)', color: 'var(--amber)', border: 'var(--amber-border)' },
  signed:   { bg: 'var(--green-bg)', color: 'var(--green)', border: 'var(--green-border)' },
  pending:  { bg: 'var(--teal-bg)', color: 'var(--mark)', border: 'var(--mark-hover)' },
};

function StatusPill({ label, variant }: { label: string; variant: PillVariant }) {
  const s = PILL_STYLES[variant] || PILL_STYLES.open;
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        height: 16,
        padding: '0 5px',
        borderRadius: 3,
        fontSize: 8,
        fontWeight: 600,
        letterSpacing: '0.04em',
        textTransform: 'uppercase',
        whiteSpace: 'nowrap',
        flexShrink: 0,
        background: s.bg,
        color: s.color,
        border: `1px solid ${s.border}`,
      }}
    >
      {label}
    </span>
  );
}

/* ─────────────────────────────────────────────
   SURFACE FOOTER — "View all N records" link
   ───────────────────────────────────────────── */

function SurfaceFooter({ count, label, onClick }: { count: number; label: string; onClick: () => void }) {
  return (
    <div
      onClick={onClick}
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '6px 12px',
        borderTop: '1px solid var(--border-faint)',
        fontSize: 10,
        color: 'var(--txt-ghost)',
        cursor: 'pointer',
        gap: 3,
        transition: 'color 70ms, background 70ms',
      }}
      onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--mark)'; e.currentTarget.style.background = 'var(--surface-hover)'; }}
      onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--txt-ghost)'; e.currentTarget.style.background = 'transparent'; }}
    >
      View all {count} {label}
      <ChevronRight style={{ width: 10, height: 10 }} />
    </div>
  );
}

/* ─────────────────────────────────────────────
   QUICK ACTIONS — max 2 per section strip
   ───────────────────────────────────────────── */

function QuickActions({ actions }: { actions: { label: string; onClick: () => void }[] }) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        padding: '6px 12px',
        borderTop: '1px solid var(--border-faint)',
      }}
    >
      {actions.slice(0, 2).map((a) => (
        <button
          key={a.label}
          onClick={a.onClick}
          style={{
            height: 24,
            padding: '0 8px',
            borderRadius: 3,
            background: 'var(--surface-el)',
            border: '1px solid var(--border-sub)',
            fontSize: 10,
            fontWeight: 500,
            color: 'var(--txt3)',
            display: 'flex',
            alignItems: 'center',
            gap: 4,
            cursor: 'pointer',
            transition: 'background 70ms, color 70ms',
          }}
          onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--teal-bg)'; e.currentTarget.style.color = 'var(--mark)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.background = 'var(--surface-el)'; e.currentTarget.style.color = 'var(--txt3)'; }}
        >
          <Plus style={{ width: 10, height: 10 }} />
          {a.label}
        </button>
      ))}
    </div>
  );
}

/* ─────────────────────────────────────────────
   HELPERS
   ───────────────────────────────────────────── */

function formatTimeAgo(timestamp: string): string {
  const now = Date.now();
  const then = new Date(timestamp).getTime();
  const diffMs = now - then;
  const diffMin = Math.floor(diffMs / 60_000);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  return `${diffDay}d ago`;
}

function statusToVariant(status: string): PillVariant {
  switch (status) {
    case 'overdue': return 'overdue';
    case 'due_soon': return 'warn';
    case 'in_progress': return 'pending';
    default: return 'open';
  }
}
