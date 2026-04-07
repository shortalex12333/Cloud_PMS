'use client';

/**
 * useNeedsAttention — React Query powered, parallel Supabase queries,
 * role-aware scoring, signature-aware text, reactive invalidation.
 */

import { useQuery } from '@tanstack/react-query';
import { supabase } from '@/lib/supabaseClient';
import { useAuth } from '@/hooks/useAuth';
import { useActiveVessel } from '@/contexts/VesselContext';
import { getEntityRoute } from '@/lib/featureFlags';
import type { ScoredPointer, AttentionCounts, EntitySource, CrewRole } from '@/lib/attention/types';
import {
  isSourceVisible,
  normaliseRole,
  computeScore,
  faultSeverityScore,
  faultToSeverity,
  woSeverityScore,
  certSeverityScore,
  certToSeverity,
  eventTimeUrgency,
  deadlineTimeUrgency,
  timeDelta,
} from '@/lib/attention/scoring';

export const ATTENTION_QUERY_KEY = ['attention'] as const;

const EMPTY_COUNTS: AttentionCounts = {
  faults: 0, work_orders: 0, certificates: 0, equipment: 0,
  parts: 0, hor_warnings: 0, hor_signoffs: 0, receiving: 0,
  handover: 0, shopping_list: 0,
};

interface UseNeedsAttentionReturn {
  pointers: ScoredPointer[];
  counts: AttentionCounts;
  loading: boolean;
  role: CrewRole;
}

interface FetchResult {
  pointers: ScoredPointer[];
  counts: AttentionCounts;
}

async function fetchAllAttention(
  user: { yachtId?: string; id?: string; department?: string },
  role: CrewRole,
): Promise<FetchResult> {
  const items: ScoredPointer[] = [];
  const newCounts: AttentionCounts = { ...EMPTY_COUNTS };

  type Fetcher = () => Promise<void>;
  const fetchers: Fetcher[] = [];

  // ── Faults ──
  // DB: severity = low | medium | high, status = open | investigating | resolved | closed
  if (isSourceVisible(role, 'fault')) {
    fetchers.push(async () => {
      const { data } = await supabase
        .from('pms_faults')
        .select('id, title, severity, detected_at, equipment_id')
        .is('resolved_at', null)
        .order('detected_at', { ascending: false })
        .limit(25);
      if (!data) return;
      newCounts.faults = data.length;
      for (const f of data) {
        const base = faultSeverityScore(f.severity);
        const timeUrg = eventTimeUrgency(f.detected_at);
        items.push({
          id: `fault-${f.id}`,
          entityId: f.id,
          source: 'fault',
          severity: faultToSeverity(f.severity),
          score: computeScore('fault', base, timeUrg, role),
          main: `<strong>${f.title || 'Unnamed Fault'}</strong> is open`,
          sub: `FAULT · ${(f.severity || 'OPEN').toUpperCase()}`,
          time: timeDelta(f.detected_at),
          route: getEntityRoute('fault', f.id),
        });
      }
    });
  }

  // ── Work Orders ──
  // DB: status = planned | in_progress | completed | cancelled
  // DB: priority = routine | important | critical | emergency
  // DB: column is wo_number (not number)
  if (isSourceVisible(role, 'work_order')) {
    fetchers.push(async () => {
      const { data } = await supabase
        .from('pms_work_orders')
        .select('id, title, priority, status, due_date, assigned_to, wo_number')
        .in('status', ['planned', 'in_progress'])
        .order('due_date', { ascending: true })
        .limit(25);
      if (!data) return;
      // Filter for role scope
      const filtered = data.filter(w => {
        if (role === 'engineer' || role === 'crew' || role === 'deck' || role === 'interior') {
          return w.assigned_to === user.id;
        }
        return true;
      });
      newCounts.work_orders = filtered.length;
      for (const w of filtered) {
        const isOverdue = w.due_date ? new Date(w.due_date) < new Date() : false;
        const base = woSeverityScore(w.priority, isOverdue);
        const timeUrg = w.due_date ? deadlineTimeUrgency(w.due_date) : 15;
        const sev = isOverdue
          ? 'critical' as const
          : (w.priority === 'critical' || w.priority === 'emergency')
            ? 'warning' as const
            : 'info' as const;
        items.push({
          id: `wo-${w.id}`,
          entityId: w.id,
          source: 'work_order',
          severity: sev,
          score: computeScore('work_order', base, timeUrg, role),
          main: `<strong>${w.title || 'Work Order'}</strong>${isOverdue ? ' is overdue' : ''}`,
          sub: `W/O · ${w.wo_number || w.id.slice(0, 8)} · ${(w.status || 'planned').toUpperCase()}`,
          time: w.due_date ? timeDelta(w.due_date) : '',
          route: getEntityRoute('work_order', w.id),
        });
      }
    });
  }

  // ── Certificates ──
  // DB: also has next_survey_due column
  if (isSourceVisible(role, 'certificate')) {
    fetchers.push(async () => {
      const cutoff = new Date();
      cutoff.setDate(cutoff.getDate() + 90);
      const cutoffStr = cutoff.toISOString();
      // Fetch certs where expiry OR next_survey_due is within 90 days
      const { data } = await supabase
        .from('pms_vessel_certificates')
        .select('id, certificate_name, expiry_date, next_survey_due, status, certificate_type')
        .or(`expiry_date.lt.${cutoffStr},next_survey_due.lt.${cutoffStr}`)
        .order('expiry_date', { ascending: true })
        .limit(25);
      if (!data) return;
      newCounts.certificates = data.length;
      for (const c of data) {
        // Use the earlier of expiry_date or next_survey_due
        const expiryMs = c.expiry_date ? new Date(c.expiry_date).getTime() : Infinity;
        const surveyMs = c.next_survey_due ? new Date(c.next_survey_due).getTime() : Infinity;
        const earliestMs = Math.min(expiryMs, surveyMs);
        const earliestDate = earliestMs === Infinity ? null : new Date(earliestMs).toISOString();
        const daysUntil = earliestMs === Infinity ? 999 : Math.floor((earliestMs - Date.now()) / 86_400_000);
        const isSurvey = surveyMs < expiryMs;

        const base = certSeverityScore(daysUntil);
        const timeUrg = earliestDate ? deadlineTimeUrgency(earliestDate) : 15;
        const expiryLabel = isSurvey ? 'survey due' : 'expires';
        items.push({
          id: `cert-${c.id}`,
          entityId: c.id,
          source: 'certificate',
          severity: certToSeverity(daysUntil),
          score: computeScore('certificate', base, timeUrg, role),
          main: `<strong>${c.certificate_name || 'Certificate'}</strong>${daysUntil <= 0 ? ` has ${isSurvey ? 'overdue survey' : 'expired'}` : ` ${expiryLabel} in ${daysUntil}d`}`,
          sub: `CERT · ${(c.certificate_type || c.status || 'UNKNOWN').toUpperCase()}`,
          time: earliestDate ? timeDelta(earliestDate) : '',
          route: getEntityRoute('certificate', c.id),
        });
      }
    });
  }

  // ── Equipment ──
  // DB: status = operational | degraded | maintenance | failed | decommissioned
  // DB: has attention_flag / attention_reason columns
  if (isSourceVisible(role, 'equipment')) {
    fetchers.push(async () => {
      const { data } = await supabase
        .from('pms_equipment')
        .select('id, name, status, criticality, attention_flag, attention_reason')
        .or('status.in.(degraded,failed),attention_flag.eq.true')
        .limit(25);
      if (!data) return;
      newCounts.equipment = data.length;
      for (const e of data) {
        const isFailed = e.status === 'failed';
        const isCritEquip = e.criticality === 'critical' || e.criticality === 'high';
        const base = isFailed ? 95 : (e.attention_flag ? 80 : (isCritEquip ? 80 : 55));
        const statusLabel = e.attention_reason || e.status;
        items.push({
          id: `equip-${e.id}`,
          entityId: e.id,
          source: 'equipment',
          severity: isFailed ? 'critical' : 'warning',
          score: computeScore('equipment', base, 50, role),
          main: `<strong>${e.name || 'Equipment'}</strong> — ${statusLabel}`,
          sub: `EQUIPMENT · ${(e.criticality || e.status || '').toUpperCase()}`,
          time: '',
          route: getEntityRoute('equipment', e.id),
        });
      }
    });
  }

  // ── Parts ──
  // DB: quantity_on_hand vs minimum_quantity, is_critical flag
  if (isSourceVisible(role, 'parts')) {
    fetchers.push(async () => {
      const { data } = await supabase
        .from('pms_parts')
        .select('id, name, quantity_on_hand, minimum_quantity, part_number, is_critical')
        .not('minimum_quantity', 'is', null)
        .limit(50);
      if (!data) return;
      const low = data.filter(p => (p.quantity_on_hand ?? 0) <= (p.minimum_quantity ?? 0));
      newCounts.parts = low.length;
      for (const p of low.slice(0, 25)) {
        const isEmpty = (p.quantity_on_hand ?? 0) === 0;
        const base = isEmpty ? (p.is_critical ? 95 : 85) : (p.is_critical ? 70 : 55);
        items.push({
          id: `part-${p.id}`,
          entityId: p.id,
          source: 'parts',
          severity: isEmpty ? 'critical' : 'warning',
          score: computeScore('parts', base, 50, role),
          main: `<strong>${p.name || 'Part'}</strong> — ${p.quantity_on_hand ?? 0} remaining${p.is_critical ? ' (critical)' : ''}`,
          sub: `PARTS · ${p.part_number || 'BELOW MIN STOCK'}`,
          time: `${p.quantity_on_hand ?? 0} left`,
          route: getEntityRoute('part', p.id),
        });
      }
    });
  }

  // ── HoR Warnings ──
  // DB: is_dismissed, acknowledged_at columns
  if (isSourceVisible(role, 'hor_warning')) {
    fetchers.push(async () => {
      const { data } = await supabase
        .from('pms_crew_hours_warnings')
        .select('id, user_id, warning_type, severity, record_date, message')
        .eq('status', 'active')
        .eq('is_dismissed', false)
        .order('record_date', { ascending: false })
        .limit(25);
      if (!data) return;
      const filtered = data.filter(h => {
        if (role === 'engineer' || role === 'crew' || role === 'deck' || role === 'interior') {
          return h.user_id === user.id;
        }
        return true;
      });
      newCounts.hor_warnings = filtered.length;
      for (const h of filtered) {
        // DB severity enum: info | warning | critical
        const base = h.severity === 'critical' ? 90 : (h.severity === 'warning' ? 65 : 40);
        const timeUrg = eventTimeUrgency(h.record_date);
        items.push({
          id: `horw-${h.id}`,
          entityId: h.id,
          source: 'hor_warning',
          severity: h.severity === 'critical' ? 'critical' : 'warning',
          score: computeScore('hor_warning', base, timeUrg, role),
          main: `<strong>HoR Warning</strong> — ${h.message || h.warning_type || 'Rest violation'}`,
          sub: `HOR · ${(h.severity || 'WARNING').toUpperCase()}`,
          time: timeDelta(h.record_date),
          route: getEntityRoute('hours_of_rest'),
        });
      }
    });
  }

  // ── HoR Signoffs ──
  // DB: column is `month` (not year_month), status = draft | crew_signed | hod_signed | finalized | locked
  // 3-tier signing: crew_signed_at, hod_signed_at, master_signed_at
  if (isSourceVisible(role, 'hor_signoff')) {
    fetchers.push(async () => {
      let query = supabase
        .from('pms_hor_monthly_signoffs')
        .select('id, user_id, month, status, department, compliance_percentage, crew_signed_at, hod_signed_at, master_signed_at')
        .not('status', 'in', '(finalized,locked)')
        .limit(25);

      // Scope per role
      if (role === 'captain') {
        query = query.is('master_signed_at', null);
      } else if (['chief_engineer', 'eto', 'manager'].includes(role)) {
        query = query.is('hod_signed_at', null);
      }

      const { data } = await query;
      if (!data) return;
      newCounts.hor_signoffs = data.length;
      for (const s of data) {
        const { main, sub, severity } = horSignoffText(s, role);
        items.push({
          id: `hors-${s.id}`,
          entityId: s.id,
          source: 'hor_signoff',
          severity,
          score: computeScore('hor_signoff', severity === 'warning' ? 70 : 50, 50, role),
          main,
          sub,
          time: '',
          route: getEntityRoute('hours_of_rest_signoff', s.id),
        });
      }
    });
  }

  // ── Receiving ──
  // DB: status = draft | in_review | accepted | rejected
  if (isSourceVisible(role, 'receiving')) {
    fetchers.push(async () => {
      const { data } = await supabase
        .from('pms_receiving')
        .select('id, vendor_name, status, received_date')
        .in('status', ['draft', 'in_review'])
        .limit(25);
      if (!data) return;
      newCounts.receiving = data.length;
      for (const r of data) {
        const isReview = r.status === 'in_review';
        const base = isReview ? 70 : 40;
        const timeUrg = r.received_date ? eventTimeUrgency(r.received_date) : 15;
        const label = isReview
          ? 'awaiting approval'
          : 'draft — needs review';
        items.push({
          id: `recv-${r.id}`,
          entityId: r.id,
          source: 'receiving',
          severity: isReview ? 'warning' : 'info',
          score: computeScore('receiving', base, timeUrg, role),
          main: `<strong>${r.vendor_name || 'Shipment'}</strong> — ${label}`,
          sub: `RECEIVING · ${isReview ? 'IN REVIEW' : 'DRAFT'}`,
          time: r.received_date ? timeDelta(r.received_date) : '',
          route: getEntityRoute('receiving', r.id),
        });
      }
    });
  }

  // ── Handover ──
  // DB: priority is INTEGER 0-3 (not string), column is `summary` (not summary_text)
  // DB: status = pending | acknowledged | completed
  // DB: has is_critical, requires_action, is_finalized
  if (isSourceVisible(role, 'handover')) {
    fetchers.push(async () => {
      const { data } = await supabase
        .from('handover_items')
        .select('id, entity_type, summary, priority, category, created_at, is_critical, requires_action')
        .eq('status', 'pending')
        .or('is_critical.eq.true,requires_action.eq.true,priority.gte.2')
        .order('created_at', { ascending: false })
        .limit(25);
      if (!data) return;
      newCounts.handover = data.length;
      for (const h of data) {
        const base = h.is_critical ? 85 : ((h.priority ?? 0) >= 3 ? 80 : 60);
        const timeUrg = eventTimeUrgency(h.created_at);
        items.push({
          id: `hand-${h.id}`,
          entityId: h.id,
          source: 'handover',
          severity: h.is_critical ? 'critical' : 'warning',
          score: computeScore('handover', base, timeUrg, role),
          main: `<strong>${h.summary || 'Handover Item'}</strong>${h.requires_action ? ' — action required' : ''}`,
          sub: `HANDOVER · ${h.is_critical ? 'CRITICAL' : `P${h.priority ?? 0}`} · ${(h.category || h.entity_type || '').toUpperCase()}`,
          time: timeDelta(h.created_at),
          route: '/work-orders',
        });
      }
    });
  }

  // ── Shopping List ──
  // DB: status = candidate | under_review | ordered | partially_fulfilled | installed
  // DB: urgency = low | normal | high | critical | null
  if (isSourceVisible(role, 'shopping_list')) {
    fetchers.push(async () => {
      const { data } = await supabase
        .from('pms_shopping_list_items')
        .select('id, part_name, urgency, status')
        .in('urgency', ['critical', 'high'])
        .not('status', 'in', '(ordered,partially_fulfilled,installed)')
        .limit(25);
      if (!data) return;
      newCounts.shopping_list = data.length;
      for (const s of data) {
        const base = s.urgency === 'critical' ? 70 : 50;
        items.push({
          id: `shop-${s.id}`,
          entityId: s.id,
          source: 'shopping_list',
          severity: s.urgency === 'critical' ? 'warning' : 'info',
          score: computeScore('shopping_list', base, 50, role),
          main: `<strong>${s.part_name || 'Item'}</strong> — ${s.urgency} urgency`,
          sub: `SHOPPING · ${(s.status || 'CANDIDATE').toUpperCase()}`,
          time: '',
          route: getEntityRoute('shopping_list', s.id),
        });
      }
    });
  }

  // Fire all in parallel
  await Promise.allSettled(fetchers.map(fn => fn()));

  // Sort by score descending
  items.sort((a, b) => b.score - a.score);

  return { pointers: items, counts: newCounts };
}

// ── HoR Signoff text helper ──

type HoRSignoff = {
  month?: string | null;
  department?: string | null;
  status?: string | null;
  crew_signed_at?: string | null;
  hod_signed_at?: string | null;
  master_signed_at?: string | null;
};

type SignoffText = { main: string; sub: string; severity: 'critical' | 'warning' | 'info' };

function horSignoffText(signoff: HoRSignoff, role: CrewRole): SignoffText {
  const month = signoff.month || 'Unknown';
  const dept = signoff.department ? ` (${signoff.department})` : '';

  if (role === 'captain' && !signoff.master_signed_at) {
    return {
      main: `<strong>HoR ${month}</strong>${dept} — awaiting Master signature`,
      sub: 'HOR SIGNOFF · MASTER SIG REQUIRED',
      severity: 'warning',
    };
  }

  if (['chief_engineer', 'eto', 'manager'].includes(role) && !signoff.hod_signed_at) {
    return {
      main: `<strong>HoR ${month}</strong>${dept} — awaiting HOD countersignature`,
      sub: 'HOR SIGNOFF · HOD SIG REQUIRED',
      severity: 'warning',
    };
  }

  return {
    main: `<strong>HoR ${month}</strong>${dept} — unsigned`,
    sub: `HOR SIGNOFF · ${(signoff.status || 'DRAFT').toUpperCase()}`,
    severity: 'info',
  };
}

// ── Hook ──

export function useNeedsAttention(): UseNeedsAttentionReturn {
  const { user } = useAuth();
  const { vesselId: activeVesselId } = useActiveVessel();
  const role = normaliseRole(user?.role ?? 'crew');
  const effectiveVesselId = activeVesselId || user?.yachtId;

  const { data, isLoading } = useQuery({
    queryKey: [...ATTENTION_QUERY_KEY, effectiveVesselId, role],
    queryFn: () => fetchAllAttention(
      { yachtId: effectiveVesselId ?? undefined, id: user?.id ?? undefined, department: ((user as Record<string, unknown>)?.department as string) ?? undefined },
      role,
    ),
    enabled: !!effectiveVesselId,
    staleTime: 30_000,
    refetchOnWindowFocus: true,
  });

  return {
    pointers: data?.pointers ?? [],
    counts: data?.counts ?? EMPTY_COUNTS,
    loading: isLoading,
    role,
  };
}
