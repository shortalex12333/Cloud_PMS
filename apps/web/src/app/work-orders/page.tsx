'use client';

import * as React from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { FilteredEntityList } from '@/features/entity-list/components/FilteredEntityList';
import { EntityDetailOverlay } from '@/features/entity-list/components/EntityDetailOverlay';
import { EntityLensPage } from '@/components/lens-v2/EntityLensPage';
import { WorkOrderContent } from '@/components/lens-v2/entity';
import lensStyles from '@/components/lens-v2/lens.module.css';
import { workOrderToListResult } from '@/features/work-orders/adapter';
import { WORK_ORDER_COLUMNS } from '@/features/work-orders/columns';
import { WORK_ORDER_FILTERS } from '@/features/entity-list/types/filter-config';
import type { WorkOrder } from '@/features/work-orders/types';
import { WorkOrderCalendar } from '@/features/work-orders/WorkOrderCalendar';
import {
  useMonthWorkOrders,
  firstOfMonth,
  lastOfMonth,
  toISODate,
} from '@/features/work-orders/useMonthWorkOrders';

function LensContent() {
  return <div className={lensStyles.root}><WorkOrderContent /></div>;
}

// ── View toggle (List / Calendar) ─────────────────────────────────────────
// CEO UX sheet /Users/celeste7/Desktop/lens_card_upgrades.md:455 —
// "we will need 'list' (to host existing list filtered), and 'calendar'
//  (the new version we are going to build)". URL is the source of truth:
// `?view=calendar` flips the tab. Omit for default list.

type LensView = 'list' | 'calendar';

function isLensView(value: string | null): value is LensView {
  return value === 'list' || value === 'calendar';
}

function ViewToggle({
  active,
  onChange,
}: {
  active: LensView;
  onChange: (next: LensView) => void;
}) {
  return (
    <div
      role="tablist"
      aria-label="Work-orders view"
      style={{
        display: 'inline-flex',
        padding: 2,
        background: 'var(--neutral-bg)',
        border: '1px solid var(--border-sub)',
        borderRadius: 6,
      }}
    >
      {(['list', 'calendar'] as LensView[]).map((v) => {
        const isActive = v === active;
        return (
          <button
            key={v}
            role="tab"
            aria-selected={isActive}
            type="button"
            onClick={() => onChange(v)}
            style={{
              appearance: 'none',
              WebkitAppearance: 'none',
              padding: '6px 14px',
              borderRadius: 4,
              border: 'none',
              background: isActive ? 'var(--surface)' : 'transparent',
              color: isActive ? 'var(--txt)' : 'var(--txt2)',
              fontSize: 12,
              fontWeight: isActive ? 600 : 500,
              cursor: 'pointer',
              textTransform: 'capitalize',
              boxShadow: isActive
                ? 'var(--shadow-card)'
                : 'none',
              transition: 'background 120ms ease, color 120ms ease',
            }}
          >
            {v}
          </button>
        );
      })}
    </div>
  );
}

// ── Page content ───────────────────────────────────────────────────────────

function WorkOrdersPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const selectedId = searchParams.get('id');
  const viewParam = searchParams.get('view');
  const view: LensView = isLensView(viewParam) ? viewParam : 'list';

  const handleSelect = React.useCallback(
    (id: string, yachtId?: string) => {
      const params = new URLSearchParams(searchParams.toString());
      params.set('id', id);
      if (yachtId) params.set('yacht_id', yachtId);
      router.push(`/work-orders?${params.toString()}`, { scroll: false });
    },
    [router, searchParams]
  );

  const handleCloseDetail = React.useCallback(() => {
    const params = new URLSearchParams(searchParams.toString());
    params.delete('id');
    const qs = params.toString();
    router.push(`/work-orders${qs ? `?${qs}` : ''}`, { scroll: false });
  }, [router, searchParams]);

  const handleViewChange = React.useCallback(
    (next: LensView) => {
      const params = new URLSearchParams(searchParams.toString());
      if (next === 'list') params.delete('view');
      else params.set('view', next);
      const qs = params.toString();
      router.push(`/work-orders${qs ? `?${qs}` : ''}`, { scroll: false });
    },
    [router, searchParams],
  );

  // Calendar-tab state: the month currently displayed. Local to the page
  // (not URL-tracked for MVP — next/prev month is ephemeral navigation).
  const [calendarMonth, setCalendarMonth] = React.useState<Date>(() =>
    firstOfMonth(new Date()),
  );

  const monthWos = useMonthWorkOrders({
    fromISO: toISODate(firstOfMonth(calendarMonth)),
    toISO: toISODate(lastOfMonth(calendarMonth)),
    enabled: view === 'calendar',
  });

  return (
    <div
      className="h-full bg-surface-base"
      style={{ display: 'flex', flexDirection: 'column' }}
    >
      {/* Tab strip — sticky above the view body */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'flex-start',
          gap: 10,
          padding: '10px 20px',
          borderBottom: '1px solid var(--border-faint)',
          flexShrink: 0,
          background: 'var(--surface-base)',
        }}
      >
        <ViewToggle active={view} onChange={handleViewChange} />
      </div>

      {/* View body */}
      <div style={{ flex: 1, minHeight: 0 }}>
        {view === 'list' ? (
          <FilteredEntityList<WorkOrder>
            domain="work-orders"
            queryKey={['work-orders']}
            table="v_work_orders_enriched"
            columns="id, title, description, status, priority, severity, type, work_order_type, frequency, wo_number, equipment_id, equipment_name, assigned_to, assigned_to_name, due_date, completed_at, created_at, updated_at"
            adapter={workOrderToListResult}
            filterConfig={WORK_ORDER_FILTERS}
            selectedId={selectedId}
            onSelect={handleSelect}
            emptyMessage="No work orders found"
            sortBy="created_at"
            tableColumns={WORK_ORDER_COLUMNS}
          />
        ) : (
          <WorkOrderCalendar
            records={monthWos.records}
            currentMonth={calendarMonth}
            onMonthChange={setCalendarMonth}
            onSelect={handleSelect}
            isLoading={monthWos.isLoading}
            error={monthWos.error}
          />
        )}
      </div>

      <EntityDetailOverlay isOpen={!!selectedId} onClose={handleCloseDetail}>
        {selectedId && (
          <EntityLensPage entityType="work_order" entityId={selectedId} content={LensContent} />
        )}
      </EntityDetailOverlay>
    </div>
  );
}

export default function WorkOrdersPage() {
  return (
    <React.Suspense
      fallback={
        <div className="h-full flex items-center justify-center bg-surface-base">
          <div style={{ width: '32px', height: '32px', border: '2px solid var(--border-sub)', borderTopColor: 'var(--mark)', borderRadius: '50%' }} className="animate-spin" />
        </div>
      }
    >
      <WorkOrdersPageContent />
    </React.Suspense>
  );
}
