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
import { useBreakpoint } from './useBreakpoint';
import { useActiveVessel } from '@/contexts/VesselContext';

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
  yacht_id?: string;
}

interface SurfaceFault {
  id: string;
  ref: string;
  title: string;
  equipment: string;
  severity: 'critical' | 'warning' | 'open';
  age: string;
  yacht_id?: string;
}

interface SurfaceHandover {
  id: string;
  from: string;
  to: string;
  date: string;
  status: 'signed' | 'pending' | 'draft';
  yacht_id?: string;
}

interface SurfacePart {
  id: string;
  name: string;
  stock: number;
  minStock: number;
  location: string;
  yacht_id?: string;
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
   MAIN COMPONENT
   ───────────────────────────────────────────── */

export function VesselSurface() {
  const router = useRouter();
  const { data: liveData, isLoading, error, refetch } = useVesselSurface();
  const { isAllVessels } = useActiveVessel();
  const breakpoint = useBreakpoint();
  const gridCols = breakpoint === 'desktop' ? '1fr 1fr 1fr' : (breakpoint === 'laptop' || breakpoint === 'tablet') ? '1fr 1fr' : '1fr';

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

  // Loading state
  if (isLoading) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
          <div style={{ width: 32, height: 32, border: '2px solid var(--border-sub)', borderTopColor: 'var(--mark)', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
          <p style={{ fontSize: 12, color: 'var(--txt2)' }}>Loading vessel data...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12, textAlign: 'center', maxWidth: 320 }}>
          <p style={{ fontSize: 15, fontWeight: 500, color: 'var(--txt)' }}>Failed to load vessel data</p>
          <p style={{ fontSize: 12, color: 'var(--txt2)' }}>{error instanceof Error ? error.message : 'An error occurred'}</p>
          <button
            onClick={() => refetch()}
            style={{ padding: '8px 16px', background: 'var(--split-bg)', borderRadius: 6, fontSize: 12, color: 'var(--txt)', border: 'none', cursor: 'pointer', fontFamily: 'var(--font-sans)' }}
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  // Derive display data from live endpoint, fall back to static mock
  const workOrders = liveData?.work_orders?.items?.length
    ? liveData.work_orders.items.map((wo) => ({
        id: wo.id,
        ref: wo.ref || wo.wo_number || wo.title?.slice(0, 12) || 'WO',
        title: wo.title,
        equipment: wo.equipment_name || '',
        assigned: wo.assigned_to || 'Unassigned',
        status: wo.status as SurfaceWorkOrder['status'],
        age: wo.age_days !== undefined ? `${wo.age_days}d` : '\u2014',
        yacht_id: wo.yacht_id,
        vesselName: wo.yacht_name,
      }))
    : [];

  const faults = liveData?.faults?.items?.length
    ? liveData.faults.items.map((f) => ({
        id: f.id,
        ref: f.ref || f.fault_code || f.title?.slice(0, 12) || 'Fault',
        title: f.title,
        equipment: f.equipment_name || '',
        severity: (f.severity || f.status || 'open') as SurfaceFault['severity'],
        age: f.age_days !== undefined ? `${f.age_days}d` : '\u2014',
        yacht_id: f.yacht_id,
        vesselName: f.yacht_name,
      }))
    : [];

  const handover = liveData?.last_handover
    ? {
        id: liveData.last_handover.id,
        from: liveData.last_handover.from_crew,
        to: liveData.last_handover.to_crew,
        date: new Date(liveData.last_handover.signed_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }),
        status: (liveData.last_handover.is_draft ? 'draft' : liveData.last_handover.status) as SurfaceHandover['status'],
        yacht_id: (liveData.last_handover as any).yacht_id,
      }
    : null;

  const parts = liveData?.parts_below_min?.items?.length
    ? liveData.parts_below_min.items.map((p) => ({
        id: p.id,
        name: p.name,
        stock: p.stock_level,
        minStock: p.min_stock,
        location: p.location || '',
        yacht_id: (p as any).yacht_id,
      }))
    : [];

  const activity = liveData?.recent_activity?.length
    ? liveData.recent_activity.map((a) => ({
        id: a.entity_id,
        ref: a.entity_ref,
        action: a.action,
        actor: a.actor,
        time: a.time_display || formatTimeAgo(a.timestamp),
      }))
    : [];

  const certificates = liveData?.certificates_expiring?.items?.length
    ? liveData.certificates_expiring.items.map((c) => ({
        id: c.id,
        name: c.name,
        daysRemaining: c.days_remaining,
        status: (c.days_remaining <= 0 ? 'expired' : c.days_remaining <= 45 ? 'expiring' : 'valid') as SurfaceCertificate['status'],
      }))
    : [];

  const woCount = liveData?.work_orders?.open_count ?? 0;
  const faultCount = liveData?.faults?.open_count ?? 0;
  const partsCount = liveData?.parts_below_min?.count ?? 0;
  const certCount = liveData?.certificates_expiring?.count ?? 0;

  return (
    <div
      style={{
        flex: 1,
        overflowY: 'auto',
        padding: '16px 20px 40px',
        display: 'grid',
        gridTemplateColumns: gridCols,
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
        {workOrders.length > 0 ? workOrders.map((wo) => (
          <SurfaceRow
            key={wo.id}
            severity={wo.status === 'overdue' ? 'critical' : wo.status === 'due_soon' ? 'warning' : undefined}
            title={<><span style={{ color: 'var(--mark)', fontSize: 11, fontFamily: 'var(--font-mono, ui-monospace, monospace)' }}>{wo.ref}</span> {wo.title}</>}
            meta={isAllVessels && wo.vesselName ? `${wo.vesselName} · ${wo.equipment}` : wo.equipment}
            pill={{ label: wo.status.replace('_', ' '), variant: statusToVariant(wo.status) }}
            time={wo.age}
            onClick={() => router.push(`/work-orders?id=${wo.id}${wo.yacht_id ? `&yacht_id=${wo.yacht_id}` : ''}`)}
          />
        )) : (
          <SurfaceEmpty message="No open work orders" />
        )}
        {woCount > 0 && (
          <SurfaceFooter
            count={woCount}
            label="work orders"
            onClick={() => navigateToDomain('work-orders')}
          />
        )}
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
        {faults.length > 0 ? faults.map((f) => (
          <SurfaceRow
            key={f.id}
            severity={f.severity === 'critical' ? 'critical' : f.severity === 'warning' ? 'warning' : undefined}
            title={<><span style={{ color: 'var(--mark)', fontSize: 11, fontFamily: 'var(--font-mono, ui-monospace, monospace)' }}>{f.ref}</span> {f.title}</>}
            meta={isAllVessels && f.vesselName ? `${f.vesselName} · ${f.equipment}` : f.equipment}
            pill={{ label: f.severity, variant: f.severity === 'critical' ? 'critical' : f.severity === 'warning' ? 'warn' : 'open' }}
            time={f.age}
            onClick={() => router.push(`/faults?id=${f.id}${f.yacht_id ? `&yacht_id=${f.yacht_id}` : ''}`)}
          />
        )) : (
          <SurfaceEmpty message="No open faults" />
        )}
        {faultCount > 0 && (
          <SurfaceFooter
            count={faultCount}
            label="open faults"
            onClick={() => navigateToDomain('faults')}
          />
        )}
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
        {handover ? (
          <SurfaceRow
            severity={handover.status === 'signed' ? 'info' : handover.status === 'draft' ? 'warning' : undefined}
            title={<>{handover.from} → {handover.to}</>}
            meta={handover.date}
            pill={{ label: handover.status, variant: handover.status === 'signed' ? 'signed' : handover.status === 'draft' ? 'warn' : 'open' }}
            onClick={() => router.push(`/handover-export?id=${handover.id}${handover.yacht_id ? `&yacht_id=${handover.yacht_id}` : ''}`)}
          />
        ) : (
          <div style={{ padding: '12px 0', fontSize: 11, color: 'var(--txt-ghost)' }}>No handover data</div>
        )}
      </SurfaceCard>

      {/* Parts Below Threshold */}
      <SurfaceCard
        icon={Package}
        label="Parts Below Min"
        count={partsCount}
        countSeverity={parts.some(p => p.stock === 0) ? 'critical' : 'warning'}
        onHeaderClick={() => navigateToDomain('inventory')}
      >
        {parts.length > 0 ? parts.map((p) => (
          <SurfaceRow
            key={p.id}
            severity={p.stock === 0 ? 'critical' : 'warning'}
            title={p.name}
            meta={`${p.location} \u00b7 ${p.stock}/${p.minStock} in stock`}
            stockBar={{ current: p.stock, min: p.minStock }}
            onClick={() => router.push(`/inventory?id=${p.id}${p.yacht_id ? `&yacht_id=${p.yacht_id}` : ''}`)}
          />
        )) : (
          <SurfaceEmpty message="All parts above minimum" />
        )}
        {partsCount > 0 && (
          <SurfaceFooter
            count={partsCount}
            label="below threshold"
            onClick={() => navigateToDomain('inventory')}
          />
        )}
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
        {activity.length > 0 ? activity.map((a) => (
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
        )) : (
          <SurfaceEmpty message="No recent activity" />
        )}
      </SurfaceCard>

      {/* Certificates Expiring */}
      <SurfaceCard
        icon={Award}
        label="Certificates"
        count={certCount}
        countSeverity={certificates.some(c => c.daysRemaining < 30) ? 'warning' : undefined}
        onHeaderClick={() => navigateToDomain('certificates')}
      >
        {certificates.length > 0 ? certificates.map((c) => (
          <SurfaceRow
            key={c.id}
            severity={c.daysRemaining < 30 ? 'warning' : undefined}
            title={c.name}
            meta={`Expires in ${c.daysRemaining} days`}
            pill={{ label: c.status, variant: c.status === 'expiring' ? 'warn' : c.status === 'expired' ? 'critical' : 'open' }}
            time={`${c.daysRemaining}d`}
            onClick={() => router.push(`/certificates?id=${c.id}${(c as any).yacht_id ? `&yacht_id=${(c as any).yacht_id}` : ''}`)}
          />
        )) : (
          <SurfaceEmpty message="No certificates expiring" />
        )}
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
            fontWeight: 600,
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

      {stockBar && (() => {
        const fillPct = stockBar.min > 0
          ? Math.min(100, Math.max(0, (stockBar.current / stockBar.min) * 100))
          : 100;
        const barColour = fillPct === 0 ? 'var(--red)' : fillPct < 50 ? 'var(--amber)' : 'var(--green)';
        return (
          <div style={{ width: 36, height: 3, background: 'var(--border-sub)', borderRadius: 2, overflow: 'hidden', flexShrink: 0 }}>
            <div style={{ height: '100%', borderRadius: 2, width: `${Math.max(3, fillPct)}%`, background: barColour }} />
          </div>
        );
      })()}

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
   SURFACE EMPTY — gentle message for empty cards
   ───────────────────────────────────────────── */

function SurfaceEmpty({ message }: { message: string }) {
  return (
    <div style={{ padding: '14px 12px', borderTop: '1px solid var(--border-faint)', fontSize: 11, color: 'var(--txt-ghost)', textAlign: 'center' }}>
      {message}
    </div>
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
