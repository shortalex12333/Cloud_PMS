'use client';

/**
 * HoursOfRestContent — lens-v2 Hours of Rest entity view.
 * Simplified from lens-hours-of-rest.html prototype.
 * Reads all data from useEntityLensContext() — zero props.
 *
 * The prototype has a full 24h x 48 half-hour grid and 7-day columnar view.
 * This React component SIMPLIFIES the visual to use KV rows and summary data.
 * The complex grid UI is entity-specific CSS that can be added later.
 *
 * Sections (in simplified order):
 * 1. Identity strip: overline (crew name), title (date), context, pills, details
 * 2. Compliance Summary (KVSection — MLC 2006 + STCW rules)
 * 3. Daily Entry (KVSection — rest/work period totals)
 * 4. Week Summary (KVSection — date range and compliance per day)
 * 5. Template (KVSection — active template name if applied)
 * 6. Notes
 */

import * as React from 'react';
import { useRouter } from 'next/navigation';
import styles from '../lens.module.css';
import { IdentityStrip, type PillDef, type DetailLine } from '../IdentityStrip';
import { SplitButton, type DropdownItem } from '../SplitButton';
import { ScrollReveal } from '../ScrollReveal';
import { useEntityLensContext } from '@/contexts/EntityLensContext';
import { getEntityRoute } from '@/lib/featureFlags';

// Sections
import {
  NotesSection,
  KVSection,
  type NoteItem,
  type KVItem,
} from '../sections';

// --- Colour mapping helpers ---

function statusToPillVariant(status: string): PillDef['variant'] {
  switch (status) {
    case 'non_compliant':
      return 'red';
    case 'pending':
      return 'amber';
    case 'compliant':
      return 'green';
    default:
      return 'neutral';
  }
}

function formatLabel(str: string): string {
  return str.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

// --- Component ---

export function HoursOfRestContent() {
  const router = useRouter();
  const { entity, executeAction, getAction, isLoading } = useEntityLensContext();

  // -- Extract entity fields --
  const payload = (entity?.payload as Record<string, unknown>) ?? {};
  const crew_member_name = ((entity?.crew_member_name ?? payload.crew_member_name ?? entity?.crew_name ?? payload.crew_name) as string | undefined) ?? 'Crew Member';
  const crew_member_id = (entity?.crew_member_id ?? payload.crew_member_id) as string | undefined;
  const date = (entity?.date ?? payload.date) as string | undefined;
  const status = ((entity?.status ?? payload.status) as string | undefined) ?? 'pending';
  const department = (entity?.department ?? payload.department) as string | undefined;
  const rank = (entity?.rank ?? payload.rank) as string | undefined;
  const total_rest_hours = ((entity?.total_rest_hours ?? payload.total_rest_hours) as number | undefined) ?? 0;
  const total_work_hours = ((entity?.total_work_hours ?? payload.total_work_hours) as number | undefined) ?? 0;
  const is_compliant = ((entity?.is_compliant ?? payload.is_compliant) as boolean | undefined) ?? status === 'compliant';

  // Compliance rules data
  const mlc_min_daily = ((entity?.mlc_min_daily_rest ?? payload.mlc_min_daily_rest) as number | undefined) ?? 10;
  const stcw_min_period = ((entity?.stcw_min_rest_period ?? payload.stcw_min_rest_period) as number | undefined) ?? 6;
  const mlc_max_work = ((entity?.mlc_max_daily_work ?? payload.mlc_max_daily_work) as number | undefined) ?? 14;
  const violations = ((entity?.violations ?? payload.violations) as Array<Record<string, unknown>> | undefined) ?? [];

  // Rest/work periods
  const rest_periods = ((entity?.rest_periods ?? payload.rest_periods) as Array<Record<string, unknown>> | undefined) ?? [];
  const work_periods = ((entity?.work_periods ?? payload.work_periods) as Array<Record<string, unknown>> | undefined) ?? [];

  // Week data
  const week_start = (entity?.week_start ?? payload.week_start) as string | undefined;
  const week_end = (entity?.week_end ?? payload.week_end) as string | undefined;
  const weekly_data = ((entity?.weekly_data ?? payload.weekly_data ?? entity?.week_entries ?? payload.week_entries) as Array<Record<string, unknown>> | undefined) ?? [];
  const weekly_rest_total = (entity?.weekly_rest_total ?? payload.weekly_rest_total) as number | undefined;

  // Template
  const template_name = (entity?.template_name ?? payload.template_name ?? entity?.active_template ?? payload.active_template) as string | undefined;

  // Section data
  const notes = ((entity?.notes ?? payload.notes) as Array<Record<string, unknown>> | undefined) ?? [];
  const verified_by = (entity?.verified_by ?? payload.verified_by) as string | undefined;
  const verified_at = (entity?.verified_at ?? payload.verified_at) as string | undefined;

  // -- Action gates --
  const submitAction = getAction('submit_hours');
  const templateAction = getAction('apply_template');
  const flagAction = getAction('flag_violation');

  // -- Derived display --
  const complianceStatus = is_compliant ? 'compliant' : 'non_compliant';
  const statusLabel = is_compliant ? 'Compliant' : 'Non-Compliant';
  const displayDate = date ? new Date(date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }) : undefined;

  const pills: PillDef[] = [
    { label: statusLabel, variant: statusToPillVariant(complianceStatus) },
  ];
  if (status === 'pending') {
    pills.push({ label: 'Pending', variant: 'amber' });
  }

  const details: DetailLine[] = [];
  if (rank) {
    details.push({ label: 'Rank', value: rank });
  }
  if (department) {
    details.push({ label: 'Department', value: department });
  }
  if (displayDate) {
    details.push({ label: 'Date', value: displayDate, mono: true });
  }
  details.push({ label: 'Rest Hours', value: `${total_rest_hours.toFixed(1)} hrs`, mono: true });
  details.push({ label: 'Work Hours', value: `${total_work_hours.toFixed(1)} hrs`, mono: true });
  if (verified_by) {
    details.push({ label: 'Verified By', value: verified_by });
  }
  if (verified_at) {
    details.push({ label: 'Verified', value: verified_at, mono: true });
  }

  // Context line
  const contextParts: string[] = [];
  if (rank) contextParts.push(rank);
  if (department) contextParts.push(department);
  const contextNode = (
    <>
      {contextParts.join(' · ')}
      {displayDate && (
        <>
          {contextParts.length > 0 && ' · '}
          {displayDate}
        </>
      )}
    </>
  );

  // -- Split button config --
  const canSubmit = submitAction !== null && ['pending', 'draft'].includes(status);
  const primaryLabel = canSubmit ? 'Submit Hours' : 'Submit Hours';
  const primaryDisabled = canSubmit ? (submitAction?.disabled ?? false) : true;
  const primaryDisabledReason = canSubmit ? submitAction?.disabled_reason : undefined;

  const handlePrimary = React.useCallback(async () => {
    await executeAction('submit_hours', {});
  }, [executeAction]);

  const dropdownItems: DropdownItem[] = [];
  if (templateAction !== null) {
    dropdownItems.push({
      label: 'Apply Template',
      icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2" /><line x1="3" y1="9" x2="21" y2="9" /><line x1="9" y1="21" x2="9" y2="9" /></svg>,
      onClick: () => executeAction('apply_template', {}),
    });
  }
  if (flagAction !== null && is_compliant) {
    dropdownItems.push({
      label: 'Flag Violation',
      icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></svg>,
      onClick: () => executeAction('flag_violation', {}),
      danger: true,
    });
  }

  // -- Compliance summary KV items --
  const complianceItems: KVItem[] = [
    { label: 'MLC Min Daily Rest', value: `${mlc_min_daily} hrs`, mono: true },
    { label: 'STCW Min Rest Period', value: `${stcw_min_period} hrs`, mono: true },
    { label: 'MLC Max Daily Work', value: `${mlc_max_work} hrs`, mono: true },
    { label: 'Actual Rest', value: `${total_rest_hours.toFixed(1)} hrs`, mono: true },
    { label: 'Actual Work', value: `${total_work_hours.toFixed(1)} hrs`, mono: true },
    { label: 'Compliance', value: statusLabel },
  ];
  if (violations.length > 0) {
    violations.forEach((v, i) => {
      complianceItems.push({
        label: `Violation ${i + 1}`,
        value: (v.description ?? v.rule ?? v.message ?? 'Violation detected') as string,
      });
    });
  }

  // -- Daily entry KV items (rest/work periods) --
  const dailyItems: KVItem[] = [];
  if (rest_periods.length > 0) {
    rest_periods.forEach((rp, i) => {
      const start = (rp.start_time ?? rp.start) as string | undefined;
      const end = (rp.end_time ?? rp.end) as string | undefined;
      const duration = (rp.duration_hours ?? rp.hours) as number | undefined;
      const label = `Rest Period ${i + 1}`;
      const parts: string[] = [];
      if (start) parts.push(start);
      if (end) parts.push(end);
      const timeRange = parts.length === 2 ? `${parts[0]} — ${parts[1]}` : parts[0] ?? '';
      const valueStr = duration !== undefined ? `${timeRange} (${duration.toFixed(1)} hrs)` : timeRange;
      dailyItems.push({ label, value: valueStr, mono: true });
    });
  }
  if (work_periods.length > 0) {
    work_periods.forEach((wp, i) => {
      const start = (wp.start_time ?? wp.start) as string | undefined;
      const end = (wp.end_time ?? wp.end) as string | undefined;
      const duration = (wp.duration_hours ?? wp.hours) as number | undefined;
      const label = `Work Period ${i + 1}`;
      const parts: string[] = [];
      if (start) parts.push(start);
      if (end) parts.push(end);
      const timeRange = parts.length === 2 ? `${parts[0]} — ${parts[1]}` : parts[0] ?? '';
      const valueStr = duration !== undefined ? `${timeRange} (${duration.toFixed(1)} hrs)` : timeRange;
      dailyItems.push({ label, value: valueStr, mono: true });
    });
  }
  if (dailyItems.length === 0) {
    dailyItems.push({ label: 'Total Rest', value: `${total_rest_hours.toFixed(1)} hrs`, mono: true });
    dailyItems.push({ label: 'Total Work', value: `${total_work_hours.toFixed(1)} hrs`, mono: true });
  }

  // -- Week summary KV items --
  const weekItems: KVItem[] = [];
  if (week_start && week_end) {
    weekItems.push({ label: 'Week', value: `${week_start} — ${week_end}`, mono: true });
  }
  if (weekly_rest_total !== undefined) {
    weekItems.push({ label: 'Weekly Rest Total', value: `${weekly_rest_total.toFixed(1)} hrs`, mono: true });
  }
  weekly_data.forEach((day) => {
    const dayDate = (day.date ?? day.day) as string | undefined;
    const dayCompliant = day.is_compliant as boolean | undefined;
    const dayRest = day.rest_hours as number | undefined;
    if (dayDate) {
      weekItems.push({
        label: dayDate,
        value: `${dayRest !== undefined ? dayRest.toFixed(1) + ' hrs rest' : '—'} · ${dayCompliant === true ? 'Compliant' : dayCompliant === false ? 'Non-Compliant' : 'Pending'}`,
        mono: true,
      });
    }
  });

  // -- Template KV items --
  const templateItems: KVItem[] = [];
  if (template_name) {
    templateItems.push({ label: 'Active Template', value: template_name });
  }

  // -- Notes --
  const noteItems: NoteItem[] = notes.map((n, i) => ({
    id: (n.id as string) ?? `note-${i}`,
    author: (n.author ?? n.created_by ?? n.user_name) as string ?? 'Unknown',
    timestamp: (n.created_at ?? n.timestamp) as string ?? '',
    body: (n.body ?? n.note_text ?? n.text) as string ?? '',
  }));

  return (
    <>
      {/* Identity Strip */}
      <IdentityStrip
        overline={crew_member_id ?? crew_member_name}
        title={crew_member_name}
        context={contextNode}
        pills={pills}
        details={details}
        actionSlot={
          submitAction ? (
            <SplitButton
              label={primaryLabel}
              onClick={handlePrimary}
              disabled={primaryDisabled}
              disabledReason={primaryDisabledReason ?? undefined}
              items={dropdownItems}
            />
          ) : undefined
        }
      />

      {/* Compliance Summary */}
      <ScrollReveal>
        <KVSection
          title="Compliance Summary"
          items={complianceItems}
          icon={
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            </svg>
          }
        />
      </ScrollReveal>

      {/* Daily Entry */}
      <ScrollReveal>
        <KVSection
          title="Daily Entry"
          items={dailyItems}
          icon={
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
          }
        />
      </ScrollReveal>

      {/* Week Summary */}
      {weekItems.length > 0 && (
        <ScrollReveal>
          <KVSection
            title="Week Summary"
            items={weekItems}
            defaultCollapsed
            icon={
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                <line x1="16" y1="2" x2="16" y2="6" />
                <line x1="8" y1="2" x2="8" y2="6" />
                <line x1="3" y1="10" x2="21" y2="10" />
              </svg>
            }
          />
        </ScrollReveal>
      )}

      {/* Template */}
      {templateItems.length > 0 && (
        <ScrollReveal>
          <KVSection
            title="Template"
            items={templateItems}
            defaultCollapsed
            icon={
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                <line x1="3" y1="9" x2="21" y2="9" />
                <line x1="9" y1="21" x2="9" y2="9" />
              </svg>
            }
          />
        </ScrollReveal>
      )}

      {/* Notes */}
      <ScrollReveal>
        <NotesSection
          notes={noteItems}
          onAddNote={() => {}}
          canAddNote={false}
        />
      </ScrollReveal>
    </>
  );
}
