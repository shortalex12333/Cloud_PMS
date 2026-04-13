'use client';

/**
 * VesselComplianceView — Captain / Manager vessel-wide HoR overview
 *
 * Consumes: GET /v1/hours-of-rest/vessel-compliance?week_start=YYYY-MM-DD
 *
 * Shows:
 * - Department compliance cards (Engineering ✓, Deck ⚠, Interior ✓)
 * - Pending final signs card
 * - All-crew grid by department with daily hours
 * - Analytics (avg rest hours, compliance rate, violations)
 */

import * as React from 'react';
import { useAuth } from '@/hooks/useAuth';
import { ActionPopup } from '@/components/lens-v2/ActionPopup';

// ── Types ────────────────────────────────────────────────────────────────────

interface DeptDay {
  date: string;
  rest_hours: number | null;
  status: 'submitted' | 'hod_signed' | 'finalized' | 'missing';
}

interface DeptCrewMember {
  user_id: string;
  name: string;
  role: string;
  days: DeptDay[];
}

interface PendingFinalSign {
  signoff_id: string;
  department: string;
  week_label: string;
  hod_name: string;
  signed_at: string;
}

interface DepartmentCard {
  name: string;
  crew_count: number;
  compliance_pct: number;
  violations: number;
  avg_work_hours: number;
  submitted_today: number;
  total_today: number;
  crew: DeptCrewMember[];
  // Phase 6: sign chain fields
  signoff_id: string | null;
  status: 'draft' | 'crew_signed' | 'hod_signed' | 'finalized' | string;
  hod_signed_at: string | null;
  correction_requested: boolean;
  correction_note: string | null;
}

interface SignChain {
  all_hods_signed: boolean;
  captain_signed: boolean;
  fleet_manager_reviewed: boolean;
  ready_for_captain: boolean;
  ready_for_fleet_manager: boolean;
}

interface VesselCompliance {
  week_start: string;
  vessel_name: string;
  departments: DepartmentCard[];
  pending_final_signs: PendingFinalSign[];
  sign_chain: SignChain;
  vessel_analytics: {
    overall_compliance_pct: number;
    total_violations: number;
    avg_work_hours: number;      // weekly total average
    avg_work_hours_per_day: number;
    total_crew: number;
    fully_compliant_departments: number;
  };
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function getCurrentWeekStart(): string {
  const now = new Date();
  const day = now.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  const mon = new Date(now);
  mon.setDate(now.getDate() + diff);
  return mon.toISOString().slice(0, 10);
}

function formatWeekLabel(weekStart: string): string {
  const start = new Date(weekStart);
  const end = new Date(weekStart);
  end.setDate(end.getDate() + 6);
  const m = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  return `${m[start.getMonth()]} ${start.getDate()} – ${m[end.getMonth()]} ${end.getDate()}`;
}

function complianceColor(pct: number): string {
  if (pct >= 95) return 'rgba(34,197,94,0.9)';
  if (pct >= 80) return 'rgba(245,158,11,0.9)';
  return 'rgba(239,68,68,0.9)';
}

function restHoursColor(hours: number | null): string {
  if (hours === null) return 'rgba(255,255,255,0.12)';
  if (hours < 10) return 'rgba(239,68,68,0.8)';    // MLC violation — minimum is 10h rest/day
  if (hours < 10.5) return 'rgba(245,158,11,0.8)'; // borderline
  return 'rgba(90,171,204,0.8)';                    // ok
}

const WEEK_DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

// ── MLC declaration ──────────────────────────────────────────────────────────

const MLC_MASTER_DECLARATION =
  'I confirm I have reviewed and verified the vessel hours of rest records ' +
  'in accordance with MLC 2006 Regulation 2.3 as Master.';

// ── Response normalizer ───────────────────────────────────────────────────────
// Maps real API response to component types.
// Real API: all_crew[] (flat, has .department field), analytics{} (not vessel_analytics{})
// Real analytics fields: compliance_rate, violations_this_quarter, avg_work_hours

function normalizeVesselCompliance(raw: any, ws: string): VesselCompliance {
  const a = raw.analytics ?? raw.vessel_analytics ?? {};

  // Build departments — may have nested crew[] OR we join from all_crew[]
  const allCrewFlat: any[] = Array.isArray(raw.all_crew) ? raw.all_crew : [];
  const rawDepts: any[] = Array.isArray(raw.departments) ? raw.departments : [];

  const departments: DepartmentCard[] = rawDepts.map((d: any) => {
    // Nested crew in dept, or join from flat all_crew by department name
    const nestedCrew: any[] = Array.isArray(d.crew) ? d.crew : [];
    const flatCrew: any[] = allCrewFlat.filter((c: any) =>
      (c.department ?? '').toLowerCase() === (d.name ?? '').toLowerCase()
    );
    const crewSource = nestedCrew.length > 0 ? nestedCrew : flatCrew;

    return {
      name: d.name ?? d.department ?? '—',
      crew_count: d.crew_count ?? d.total_crew ?? crewSource.length,
      compliance_pct: d.compliance_pct ?? d.compliance_rate ?? 0,
      violations: d.violations ?? 0,
      avg_work_hours: d.avg_work_hours ?? 0,
      submitted_today: d.submitted_today ?? d.submitted_count ?? 0,
      total_today: d.total_today ?? d.crew_count ?? d.total_crew ?? 0,
      signoff_id: d.signoff_id ?? null,
      status: d.status ?? 'draft',
      hod_signed_at: d.hod_signed_at ?? null,
      correction_requested: d.correction_requested ?? false,
      correction_note: d.correction_note ?? null,
      crew: crewSource.map((m: any) => ({
        user_id: m.user_id ?? m.id ?? String(Math.random()),
        name: m.name ?? '—',
        role: m.role ?? '',
        days: (m.daily ?? m.days ?? []).map((day: any) => ({
          date: day.date,
          rest_hours: day.rest_hours ?? day.total_rest_hours ?? null,
          status: (day.status ?? 'missing') as DeptDay['status'],
        })),
      })),
    };
  });

  return {
    week_start: raw.week_start ?? ws,
    vessel_name: raw.vessel_name ?? raw.yacht_name ?? '—',
    departments,
    sign_chain: {
      all_hods_signed: raw.sign_chain?.all_hods_signed ?? false,
      captain_signed: raw.sign_chain?.captain_signed ?? false,
      fleet_manager_reviewed: raw.sign_chain?.fleet_manager_reviewed ?? false,
      ready_for_captain: raw.sign_chain?.ready_for_captain ?? false,
      ready_for_fleet_manager: raw.sign_chain?.ready_for_fleet_manager ?? false,
    },
    pending_final_signs: (raw.pending_final_signs ?? []).map((ps: any) => ({
      signoff_id: ps.signoff_id ?? ps.id,
      department: ps.department ?? '—',
      week_label: ps.week_label ?? formatWeekLabel(ws),
      hod_name: ps.hod_name ?? '—',
      signed_at: ps.signed_at ?? new Date().toISOString(),
    })),
    vessel_analytics: {
      overall_compliance_pct: a.compliance_pct ?? a.overall_compliance_pct ?? 0,
      total_violations: a.violations_this_week ?? a.total_violations ?? 0,
      avg_work_hours: a.avg_work_hours_per_week ?? a.avg_work_hours ?? 0,
      avg_work_hours_per_day: a.avg_work_hours_per_day ?? (a.avg_work_hours_per_week ? a.avg_work_hours_per_week / 7 : a.avg_work_hours ? a.avg_work_hours / 7 : 0),
      total_crew: a.total_crew ?? allCrewFlat.length ?? 0,
      fully_compliant_departments: a.fully_compliant_departments ?? 0,
    },
  };
}

// ── Component ────────────────────────────────────────────────────────────────

export function VesselComplianceView() {
  const { session } = useAuth();

  const [weekStart, setWeekStart] = React.useState(getCurrentWeekStart);
  const [data, setData] = React.useState<VesselCompliance | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [expandedDept, setExpandedDept] = React.useState<string | null>(null);
  const [signingId, setSigningId] = React.useState<string | null>(null);
  const [signingPopupId, setSigningPopupId] = React.useState<string | null>(null);
  const [signAllPopupOpen, setSignAllPopupOpen] = React.useState(false);
  const [signingAll, setSigningAll] = React.useState(false);

  // ── Load ──

  async function loadData(ws: string) {
    setLoading(true);
    setError(null);
    try {
      const token = session?.access_token;
      if (!token) throw new Error('Not authenticated');
      const res = await fetch(`/api/v1/hours-of-rest/vessel-compliance?week_start=${ws}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`Failed to load vessel compliance (${res.status})`);
      const json = await res.json();
      const raw = json.success ? json.data : json;
      if (raw) { setData(normalizeVesselCompliance(raw, ws)); return; }
      throw new Error('Unexpected response shape from vessel-compliance endpoint');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load vessel compliance data');
    } finally {
      setLoading(false);
    }
  }

  React.useEffect(() => { loadData(weekStart); }, [weekStart, session?.access_token]);

  // ── Final sign ──

  async function signAllDepartments(signatureName: string) {
    if (!data) return;
    const signable = data.departments.filter(d => d.status === 'hod_signed' && d.signoff_id);
    const skipped = data.departments.filter(d => d.status !== 'hod_signed' && d.status !== 'finalized');
    if (skipped.length > 0) {
      // Non-fatal warning — log to console, still sign the signable ones
      console.warn(`[HoR] Skipping ${skipped.length} dept(s) not yet HOD-signed: ${skipped.map(d => d.name).join(', ')}`);
    }
    setSigningAll(true);
    try {
      const token = session?.access_token;
      for (const dept of signable) {
        await fetch('/api/v1/hours-of-rest/signoffs/sign', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify({
            signoff_id: dept.signoff_id,
            signature_level: 'master',
            signature_data: {
              name: signatureName,
              declaration: MLC_MASTER_DECLARATION,
              timestamp: new Date().toISOString(),
            },
          }),
        });
      }
      await loadData(weekStart);
    } finally {
      setSigningAll(false);
    }
  }

  async function finalSign(signoffId: string, signatureName: string) {
    setSigningId(signoffId);
    try {
      const token = session?.access_token;
      await fetch('/api/v1/hours-of-rest/signoffs/sign', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          signoff_id: signoffId,
          signature_level: 'master',
          signature_data: {
            name: signatureName,
            declaration: MLC_MASTER_DECLARATION,
            timestamp: new Date().toISOString(),
          },
        }),
      });
      await loadData(weekStart);
    } finally {
      setSigningId(null);
    }
  }

  function shiftWeek(dir: -1 | 1) {
    const d = new Date(weekStart);
    d.setDate(d.getDate() + dir * 7);
    setWeekStart(d.toISOString().slice(0, 10));
  }

  if (loading) {
    return (
      <div style={{ padding: 32, color: 'rgba(255,255,255,0.4)', fontFamily: 'var(--font-mono)', fontSize: 12 }}>
        Loading vessel compliance…
      </div>
    );
  }

  if (error || !data) {
    return (
      <div style={{ padding: 32, color: 'rgba(239,68,68,0.7)', fontFamily: 'var(--font-mono)', fontSize: 12 }}>
        {error ?? 'No vessel compliance data available.'}
      </div>
    );
  }

  const weekLabel = formatWeekLabel(data.week_start);
  const va = data.vessel_analytics;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

      {/* ── View identity header ── */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        paddingBottom: 12,
        borderBottom: '1px solid rgba(255,255,255,0.06)',
      }}>
        <span style={{
          fontFamily: 'var(--font-mono)',
          fontSize: 9,
          fontWeight: 700,
          letterSpacing: '0.12em',
          textTransform: 'uppercase',
          color: 'rgba(168,85,247,0.8)',
          background: 'rgba(168,85,247,0.08)',
          border: '1px solid rgba(168,85,247,0.20)',
          borderRadius: 4,
          padding: '3px 8px',
        }}>
          VESSEL OVERVIEW
        </span>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'rgba(255,255,255,0.22)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          All departments — captain / fleet manager view
        </span>
      </div>

      {/* ── Week nav ── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <button onClick={() => shiftWeek(-1)} style={navBtnStyle}>←</button>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'rgba(255,255,255,0.5)', minWidth: 140, textAlign: 'center' }}>
          {weekLabel}
        </span>
        <button onClick={() => shiftWeek(1)} style={navBtnStyle}>→</button>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'rgba(255,255,255,0.3)', marginLeft: 4 }}>
          {data.vessel_name}
        </span>
      </div>

      {/* ── Vessel analytics ── */}
      <div style={cardStyle}>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'rgba(255,255,255,0.3)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 12 }}>
          Vessel Analytics — {weekLabel}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12 }}>
          {[
            { label: 'Compliance', value: `${va.overall_compliance_pct.toFixed(1)}%`, color: complianceColor(va.overall_compliance_pct) },
            { label: 'Violations', value: String(va.total_violations), color: va.total_violations > 0 ? 'rgba(239,68,68,0.9)' : 'rgba(34,197,94,0.9)' },
            { label: 'Total Crew', value: String(va.total_crew), color: 'rgba(255,255,255,0.7)' },
            { label: 'Dept OK', value: `${va.fully_compliant_departments}/${data.departments.length}`, color: 'rgba(34,197,94,0.9)' },
          ].map(({ label, value, color }) => (
            <div key={label} style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'rgba(255,255,255,0.3)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</span>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 18, fontWeight: 600, color }}>{value}</span>
            </div>
          ))}
          {/* Avg Work — two lines: per day and per week */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'rgba(255,255,255,0.3)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Avg Work</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 18, fontWeight: 600, color: 'rgba(90,171,204,0.9)' }}>
              {va.avg_work_hours_per_day.toFixed(1)}h/day
            </span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'rgba(90,171,204,0.55)' }}>
              {va.avg_work_hours.toFixed(1)}h/wk
            </span>
          </div>
        </div>
      </div>

      {/* ── Captain sign chain card ── */}
      {(() => {
        const sc = data.sign_chain;
        const signable = data.departments.filter(d => d.status === 'hod_signed' && d.signoff_id);
        const notReady = data.departments.filter(d => d.status !== 'hod_signed' && d.status !== 'finalized');

        if (sc.captain_signed) {
          return (
            <div style={{ ...cardStyle, borderColor: 'rgba(34,197,94,0.2)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'rgba(34,197,94,0.8)' }}>Master Signed ✓</span>
                {sc.fleet_manager_reviewed
                  ? <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'rgba(34,197,94,0.6)' }}>Fleet Reviewed ✓</span>
                  : <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'rgba(255,255,255,0.3)' }}>Pending fleet review</span>
                }
              </div>
            </div>
          );
        }

        if (signable.length === 0) return null;

        return (
          <div style={{ ...cardStyle, borderColor: 'rgba(90,171,204,0.2)' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
              <div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'rgba(255,255,255,0.7)', fontWeight: 600 }}>
                  Captain Attestation Required
                </div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'rgba(255,255,255,0.3)', marginTop: 3 }}>
                  {signable.length} dept{signable.length !== 1 ? 's' : ''} ready
                  {notReady.length > 0 && ` · ${notReady.length} dept${notReady.length !== 1 ? 's' : ''} awaiting HOD`}
                </div>
              </div>
              <button
                data-testid="hor-sign-all-depts"
                onClick={() => setSignAllPopupOpen(true)}
                disabled={signingAll}
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: 10,
                  color: signingAll ? 'rgba(255,255,255,0.3)' : 'rgba(34,197,94,0.9)',
                  background: 'rgba(34,197,94,0.08)',
                  border: '1px solid rgba(34,197,94,0.3)',
                  borderRadius: 4,
                  padding: '5px 14px',
                  cursor: signingAll ? 'wait' : 'pointer',
                  whiteSpace: 'nowrap',
                }}
              >
                {signingAll ? 'Signing…' : `Sign ${signable.length} Dept${signable.length !== 1 ? 's' : ''}`}
              </button>
            </div>
          </div>
        );
      })()}

      {/* ── Pending final signs (legacy — individual dept HOD signoffs) ── */}
      {data.pending_final_signs.length > 0 && (
        <div style={{ ...cardStyle, borderColor: 'rgba(245,158,11,0.25)' }}>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'rgba(245,158,11,0.7)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 10 }}>
            Pending Final Signs ({data.pending_final_signs.length})
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {data.pending_final_signs.map(ps => (
              <div key={ps.signoff_id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
                <div>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'rgba(255,255,255,0.8)' }}>
                    {ps.department}
                  </span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'rgba(255,255,255,0.3)', marginLeft: 8 }}>
                    {ps.week_label} · signed by {ps.hod_name}
                  </span>
                </div>
                <button
                  onClick={() => { if (!signingId) setSigningPopupId(ps.signoff_id); }}
                  disabled={signingId === ps.signoff_id}
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: 10,
                    color: signingId === ps.signoff_id ? 'rgba(255,255,255,0.3)' : 'rgba(34,197,94,0.9)',
                    background: 'rgba(34,197,94,0.08)',
                    border: '1px solid rgba(34,197,94,0.3)',
                    borderRadius: 4,
                    padding: '4px 10px',
                    cursor: signingId === ps.signoff_id ? 'wait' : 'pointer',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {signingId === ps.signoff_id ? 'Signing…' : 'Final Sign'}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Department cards ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 10 }}>
        {data.departments.map(dept => {
          const isExpanded = expandedDept === dept.name;
          const statusColor = complianceColor(dept.compliance_pct);
          return (
            <div key={dept.name} style={{
              ...cardStyle,
              borderColor: isExpanded ? 'rgba(255,255,255,0.15)' : 'rgba(255,255,255,0.07)',
              cursor: 'pointer',
              transition: 'border-color 0.15s',
            }}
              onClick={() => setExpandedDept(isExpanded ? null : dept.name)}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'rgba(255,255,255,0.7)', fontWeight: 600 }}>
                  {dept.name}
                </span>
                <span style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: 10,
                  color: statusColor,
                  background: `${statusColor}15`,
                  border: `1px solid ${statusColor}40`,
                  borderRadius: 3,
                  padding: '1px 6px',
                }}>
                  {dept.compliance_pct}%
                </span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
                <Stat label="Today" value={`${dept.submitted_today}/${dept.total_today}`} color="rgba(255,255,255,0.6)" />
                <Stat label="Avg Work" value={`${dept.avg_work_hours.toFixed(1)}h`} color="rgba(90,171,204,0.8)" />
                <Stat label="Crew" value={String(dept.crew_count)} color="rgba(255,255,255,0.4)" />
                <Stat label="Violations" value={String(dept.violations)} color={dept.violations > 0 ? 'rgba(239,68,68,0.8)' : 'rgba(34,197,94,0.7)'} />
              </div>
              {/* Sign chain status badges */}
              <div style={{ display: 'flex', gap: 4, marginTop: 8, flexWrap: 'wrap' }}>
                {dept.status === 'hod_signed' && (
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 8, color: 'rgba(34,197,94,0.8)', background: 'rgba(34,197,94,0.08)', border: '1px solid rgba(34,197,94,0.2)', borderRadius: 3, padding: '1px 5px' }}>
                    HOD Signed ✓
                  </span>
                )}
                {dept.status === 'finalized' && (
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 8, color: 'rgba(34,197,94,0.9)', background: 'rgba(34,197,94,0.10)', border: '1px solid rgba(34,197,94,0.25)', borderRadius: 3, padding: '1px 5px' }}>
                    Finalized ✓
                  </span>
                )}
                {dept.correction_requested && (
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 8, color: 'rgba(245,158,11,0.9)', background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.25)', borderRadius: 3, padding: '1px 5px' }}>
                    Correction Requested
                  </span>
                )}
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'rgba(255,255,255,0.25)', marginTop: 6, textAlign: 'center' }}>
                {isExpanded ? '▲ collapse' : '▼ show crew'}
              </div>
            </div>
          );
        })}
      </div>

      {/* ── Sign All Departments popup (L2) ── */}
      {signAllPopupOpen && (() => {
        const signable = data.departments.filter(d => d.status === 'hod_signed' && d.signoff_id);
        const skipped  = data.departments.filter(d => d.status !== 'hod_signed' && d.status !== 'finalized');
        return (
          <ActionPopup
            mode="mutate"
            title="Sign All Departments"
            subtitle="MLC 2006 Reg. 2.3 — Master's Attestation"
            signatureLevel={2}
            submitLabel={signingAll ? 'Signing…' : 'Sign All'}
            submitDisabled={signingAll}
            fields={[
              { name: 'vessel',    label: 'Vessel',            type: 'kv-read', value: data.vessel_name },
              { name: 'week',      label: 'Week',              type: 'kv-read', value: formatWeekLabel(data.week_start) },
              { name: 'signing',   label: 'Departments Signing', type: 'kv-read', value: signable.map(d => d.name).join(', ') },
              ...(skipped.length > 0 ? [{
                name: 'skipped',
                label: 'Skipped (HOD pending)',
                type: 'kv-read' as const,
                value: skipped.map(d => d.name).join(', '),
              }] : []),
              { name: 'regulation', label: 'Regulation', type: 'kv-read', value: 'MLC 2006 Regulation 2.3 — Rest Hours' },
            ]}
            previewRows={[
              { key: 'Vessel Compliance', value: `${va.overall_compliance_pct.toFixed(1)}%` },
              { key: 'Total Violations',  value: String(va.total_violations) },
              { key: 'Total Crew',        value: String(va.total_crew) },
            ]}
            onClose={() => setSignAllPopupOpen(false)}
            onSubmit={(values) => {
              setSignAllPopupOpen(false);
              signAllDepartments(String(values.signature_name ?? ''));
            }}
          />
        );
      })()}

      {/* ── Captain final-sign popup (L2) ── */}
      {signingPopupId && (() => {
        const ps = data.pending_final_signs.find(p => p.signoff_id === signingPopupId);
        if (!ps) return null;
        return (
          <ActionPopup
            mode="mutate"
            title="Final Sign — Vessel Hours of Rest"
            subtitle="MLC 2006 Reg. 2.3 — Master's Attestation"
            signatureLevel={2}
            submitLabel="Final Sign"
            fields={[
              { name: 'department',  label: 'Department',   type: 'kv-read', value: ps.department },
              { name: 'week',        label: 'Week',         type: 'kv-read', value: ps.week_label },
              { name: 'hod_signed',  label: 'HOD Signed By', type: 'kv-read', value: ps.hod_name },
              { name: 'vessel',      label: 'Vessel',       type: 'kv-read', value: data.vessel_name },
              { name: 'regulation',  label: 'Regulation',   type: 'kv-read', value: 'MLC 2006 Regulation 2.3 — Rest Hours' },
            ]}
            previewRows={[
              { key: 'Vessel Compliance', value: `${va.overall_compliance_pct.toFixed(1)}%` },
              { key: 'Total Violations',  value: String(va.total_violations) },
              { key: 'Total Crew',        value: String(va.total_crew) },
            ]}
            onClose={() => setSigningPopupId(null)}
            onSubmit={(values) => {
              setSigningPopupId(null);
              finalSign(ps.signoff_id, String(values.signature_name ?? ''));
            }}
          />
        );
      })()}

      {/* ── Expanded crew grid (shown below cards when a dept is expanded) ── */}
      {expandedDept && (() => {
        const dept = data.departments.find(d => d.name === expandedDept);
        if (!dept) return null;
        return (
          <div style={cardStyle}>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'rgba(255,255,255,0.3)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 12 }}>
              {dept.name} — Crew Hours Grid
            </div>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 480 }}>
                <thead>
                  <tr>
                    <th style={thStyle({ width: 140, textAlign: 'left' })}>Crew</th>
                    {WEEK_DAYS.map(d => (
                      <th key={d} style={thStyle({ width: 52, textAlign: 'center' })}>{d}</th>
                    ))}
                    <th style={thStyle({ width: 52, textAlign: 'center' })}>Avg</th>
                  </tr>
                </thead>
                <tbody>
                  {dept.crew.map(member => {
                    const submitted = member.days.filter(d => d.rest_hours !== null);
                    const avg = submitted.length
                      ? (submitted.reduce((s, d) => s + (d.rest_hours ?? 0), 0) / submitted.length).toFixed(1)
                      : '—';
                    return (
                      <tr key={member.user_id} style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                        <td style={{ padding: '8px 0', paddingRight: 12 }}>
                          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'rgba(255,255,255,0.8)' }}>{member.name}</div>
                          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'rgba(255,255,255,0.3)', marginTop: 1 }}>{member.role}</div>
                        </td>
                        {member.days.map(day => (
                          <td key={day.date} style={{ padding: '8px 4px', textAlign: 'center' }}>
                            {day.rest_hours !== null ? (
                              <div style={{
                                display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                                width: 36, height: 28, borderRadius: 4,
                                background: `${restHoursColor(day.rest_hours)}22`,
                                border: `1px solid ${restHoursColor(day.rest_hours)}55`,
                              }}>
                                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: restHoursColor(day.rest_hours) }}>
                                  {day.rest_hours.toFixed(1)}
                                </span>
                              </div>
                            ) : (
                              <div style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 36, height: 28 }}>
                                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'rgba(255,255,255,0.15)' }}>—</span>
                              </div>
                            )}
                          </td>
                        ))}
                        <td style={{ padding: '8px 4px', textAlign: 'center' }}>
                          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'rgba(255,255,255,0.5)' }}>{avg}</span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        );
      })()}

    </div>
  );
}

// ── Small helpers ────────────────────────────────────────────────────────────

function Stat({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 8, color: 'rgba(255,255,255,0.25)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</span>
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color }}>{value}</span>
    </div>
  );
}

// ── Shared styles ────────────────────────────────────────────────────────────

const cardStyle: React.CSSProperties = {
  background: 'rgba(255,255,255,0.03)',
  border: '1px solid rgba(255,255,255,0.07)',
  borderRadius: 8,
  padding: '14px 16px',
};

const navBtnStyle: React.CSSProperties = {
  fontFamily: 'var(--font-mono)',
  fontSize: 12,
  color: 'rgba(255,255,255,0.5)',
  background: 'rgba(255,255,255,0.05)',
  border: '1px solid rgba(255,255,255,0.08)',
  borderRadius: 4,
  padding: '4px 10px',
  cursor: 'pointer',
};

function thStyle(extra: React.CSSProperties): React.CSSProperties {
  return {
    fontFamily: 'var(--font-mono)',
    fontSize: 9,
    color: 'rgba(255,255,255,0.3)',
    textTransform: 'uppercase',
    letterSpacing: '0.06em',
    fontWeight: 400,
    paddingBottom: 8,
    ...extra,
  };
}
