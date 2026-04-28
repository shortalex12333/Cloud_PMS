import { supabase } from '@/lib/supabaseClient';
import type { RestPeriod } from '../TimeSlider';

export const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

/** API returns null for days with no submitted record — replace with an empty unsubmitted slot */
export function normalizeDays(days: any[], weekStart: string): any[] {
  return days.map((d, i) => {
    if (d != null) return d;
    const date = new Date(weekStart);
    date.setDate(date.getDate() + i);
    return {
      date: date.toISOString().slice(0, 10),
      label: DAY_LABELS[i],
      rest_periods: [],
      total_rest_hours: 0,
      total_work_hours: 0,
      is_compliant: null,
      submitted: false,
      warnings: [],
    };
  });
}

/**
 * Normalises the real API response shape to what the component expects.
 * Real API deviations:
 *  - compliance is flat: {rolling_24h_rest, rolling_7day_rest} — missing mlc_status, min_*, violations_this_month, rolling_7d_work
 *  - prior_weeks may be absent (backend feature not yet implemented)
 *  - templates[].name (backend renames schedule_name → name in response)
 *  - days[].record_date instead of date; no label field
 */
export function normalizeMyWeekResponse(json: any): void {
  // 1. Derive day.date + day.label from record_date / week_start index
  if (Array.isArray(json.days)) {
    const weekStart = json.week_start ?? '';
    json.days = json.days.map((d: any, i: number) => {
      if (d == null) return d; // normalizeDays handles null slots
      const date = d.date ?? d.record_date ?? (() => {
        const dt = new Date(weekStart);
        dt.setDate(dt.getDate() + i);
        return dt.toISOString().slice(0, 10);
      })();
      const label = d.label ?? DAY_LABELS[i];
      // Remap is_daily_compliant (backend) → is_compliant (component)
      const is_compliant = d.is_compliant ?? d.is_daily_compliant ?? null;
      return { ...d, date, label, is_compliant };
    });
  }

  // 2. Normalise compliance — add missing fields with safe defaults
  const c: any = json.compliance ?? {};
  const rolling24 = c.rolling_24h_rest ?? null;
  const rolling7d = c.rolling_7day_rest ?? null;
  const min24 = c.min_24h ?? 10;
  const min7d = c.min_7d ?? 77;
  const mlcStatus: string | null = c.mlc_status ?? (
    rolling24 != null && rolling7d != null
      ? (rolling24 >= min24 && rolling7d >= min7d ? 'COMPLIANT' : 'NON-COMPLIANT')
      : null
  );
  json.compliance = {
    rolling_24h_rest: rolling24,
    rolling_7day_rest: rolling7d,
    rolling_7d_work: c.rolling_7d_work ?? null,
    min_24h: min24,
    min_7d: min7d,
    violations_this_month: c.violations_this_month ?? 0,
    mlc_status: mlcStatus,
  };

  // 3. Default prior_weeks to empty array if absent
  if (!Array.isArray(json.prior_weeks)) {
    json.prior_weeks = [];
  }

  // 4. Ensure templates is always an array (backend field: name)
  if (!Array.isArray(json.templates)) {
    json.templates = [];
  }

  // 5. Flatten signoff: backend returns {signoff: {id, status}}, component reads
  //    pending_signoff.id and signoff_status. Map them so all consumers are consistent.
  if (json.signoff && !json.pending_signoff) {
    json.pending_signoff = json.signoff;
  }
  if (!json.signoff_status && json.signoff?.status) {
    json.signoff_status = json.signoff.status;
  }
}

/**
 * Returns the Authorization header value, or null if no session exists.
 * BUG-HOR-2 fix: previously returned an empty string on null session, causing
 * fetches to send `Authorization: ` which backend rejects with 401. Callers
 * must now null-check before making a request.
 */
export async function getAuthHeader(): Promise<string | null> {
  const { data: { session } } = await supabase.auth.getSession();
  return session ? `Bearer ${session.access_token}` : null;
}

export function formatMonth(yyyyMm: string): string {
  const [y, m] = yyyyMm.split('-');
  const d = new Date(Number(y), Number(m) - 1, 1);
  return d.toLocaleDateString('en-GB', { month: 'long', year: 'numeric' });
}

/** Compute total hours from a periods array — always correct, ignores stored totals. */
export function hoursFromPeriods(periods: RestPeriod[]): number {
  return periods.reduce((sum, p) => {
    const [sh, sm] = p.start.split(':').map(Number);
    const [eh, em] = p.end.split(':').map(Number);
    const startMin = sh * 60 + sm;
    const endMin = (p.end === '24:00' ? 24 : eh) * 60 + em;
    return sum + Math.max(0, endMin - startMin) / 60;
  }, 0);
}
