'use client';

/**
 * FleetView — Fleet Manager cross-vessel Hours of Rest overview
 *
 * Wired to GET /api/v1/hours-of-rest/fleet-compliance
 * Returns per-vessel compliance aggregates for all managed vessels.
 *
 * Field contract (backend → component):
 *   vessels[].yacht_id              → VesselSummary.yacht_id
 *   vessels[].yacht_name            → VesselSummary.yacht_name (falls back to user.fleet_vessels)
 *   vessels[].compliance_pct        → VesselSummary.compliance_pct
 *   vessels[].total_crew            → VesselSummary.total_crew
 *   vessels[].violations_this_week  → VesselSummary.violations_this_week
 *   vessels[].departments_finalized → VesselSummary.departments_finalized
 *   vessels[].departments_total     → VesselSummary.departments_total
 */

import * as React from 'react';
import { useAuth } from '@/hooks/useAuth';

interface VesselSummary {
  yacht_id: string;
  yacht_name: string;
  compliance_pct?: number;
  total_crew?: number;
  violations_this_week?: number;
  departments_finalized?: number;
  departments_total?: number;
  error?: boolean;
}

function getCurrentWeekStart(): string {
  const now = new Date();
  const day = now.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  const mon = new Date(now);
  mon.setDate(now.getDate() + diff);
  return mon.toISOString().slice(0, 10);
}

function normalizeFleetCompliance(json: any, fallbackVessels: { yacht_id: string; yacht_name: string }[]): VesselSummary[] {
  /**
   * Normalises GET /fleet-compliance response.
   * Real API deviations:
   *   - vessels[] may omit yacht_name if fleet_registry lookup failed → fall back to user.fleet_vessels
   *   - vessels[] may have error:"unavailable" for individual vessel failures
   */
  const nameById: Record<string, string> = {};
  for (const v of fallbackVessels) nameById[v.yacht_id] = v.yacht_name;

  const raw: any[] = Array.isArray(json?.vessels) ? json.vessels : [];
  return raw.map(v => ({
    yacht_id:              v.yacht_id ?? '',
    yacht_name:            v.yacht_name || nameById[v.yacht_id] || v.yacht_id?.slice(0, 8) || '—',
    compliance_pct:        v.compliance_pct ?? undefined,
    total_crew:            v.total_crew ?? undefined,
    violations_this_week:  v.violations_this_week ?? undefined,
    departments_finalized: v.departments_finalized ?? undefined,
    departments_total:     v.departments_total ?? undefined,
    error:                 v.error === 'unavailable',
  }));
}

function complianceColor(pct: number | undefined): string {
  if (pct === undefined) return 'var(--txt-ghost)';
  if (pct >= 95) return 'var(--compliance-good)';
  if (pct >= 80) return 'var(--compliance-warn)';
  return 'var(--compliance-crit)';
}

export function FleetView() {
  const { user, session } = useAuth();
  const fallbackVessels = user?.fleet_vessels ?? [];

  const [vessels, setVessels] = React.useState<VesselSummary[]>(
    // Optimistic render: show vessel names immediately while data loads
    fallbackVessels.map(v => ({ yacht_id: v.yacht_id, yacht_name: v.yacht_name }))
  );
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    const token = session?.access_token;
    if (!token) { setLoading(false); return; }

    const weekStart = getCurrentWeekStart();
    setLoading(true);
    setError(null);

    fetch(`/api/v1/hours-of-rest/fleet-compliance?week_start=${weekStart}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(res => {
        if (!res.ok) throw new Error(`fleet-compliance ${res.status}`);
        return res.json();
      })
      .then(json => {
        const normalized = normalizeFleetCompliance(json, fallbackVessels);
        // If API returned nothing, fall back to vessel list with no compliance data
        setVessels(normalized.length > 0 ? normalized : fallbackVessels.map(v => ({
          yacht_id: v.yacht_id, yacht_name: v.yacht_name,
        })));
      })
      .catch(err => {
        setError(err instanceof Error ? err.message : 'Failed to load fleet data');
      })
      .finally(() => setLoading(false));
  }, [session?.access_token]);

  if (vessels.length === 0 && !loading) {
    return (
      <div style={{
        padding: 48,
        textAlign: 'center',
        fontFamily: 'var(--font-mono)',
        fontSize: 11,
        color: 'var(--txt-ghost)',
      }}>
        No fleet vessels assigned to your account.
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>

      {/* ── Header ── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
        <div style={{
          fontFamily: 'var(--font-mono)',
          fontSize: 9,
          color: 'var(--txt-ghost)',
          textTransform: 'uppercase',
          letterSpacing: '0.10em',
        }}>
          Fleet Overview — {vessels.length} vessel{vessels.length !== 1 ? 's' : ''}
        </div>
        {loading && (
          <div style={{
            width: 12, height: 12,
            border: '1.5px solid var(--border-top)',
            borderTopColor: 'var(--mark)',
            borderRadius: 'var(--radius-full)',
            animation: 'spin 1s linear infinite',
          }} />
        )}
      </div>

      {error && (
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: 10,
          color: 'var(--red)',
          background: 'var(--red-bg)',
          border: '1px solid var(--red-border)',
          borderRadius: 'var(--radius-pill)', padding: '8px 12px',
        }}>
          {error}
        </div>
      )}

      {/* ── Vessel cards ── */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))',
        gap: 'var(--space-3)',
      }}>
        {vessels.map(vessel => (
          <div
            key={vessel.yacht_id}
            style={{
              background: 'var(--surface-card)',
              border: '1px solid var(--border-sub)',
              borderRadius: 'var(--radius-sm)',
              padding: '16px 18px',
            }}
          >
            <div style={{
              fontFamily: 'var(--font-mono)',
              fontSize: 12,
              fontWeight: 600,
              color: 'var(--txt)',
              marginBottom: 'var(--space-3)',
              letterSpacing: '0.04em',
            }}>
              {vessel.yacht_name}
            </div>

            {vessel.error ? (
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--red)' }}>
                Data unavailable
              </div>
            ) : loading && vessel.compliance_pct === undefined ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                {[1, 2, 3].map(i => (
                  <div key={i} style={{
                    height: 12,
                    background: 'var(--surface-subtle)',
                    borderRadius: 'var(--radius-pill)',
                    animation: 'pulse 1.5s ease-in-out infinite',
                  }} />
                ))}
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                <Stat
                  label="Compliance"
                  value={vessel.compliance_pct !== undefined ? `${vessel.compliance_pct.toFixed(1)}%` : '—'}
                  color={complianceColor(vessel.compliance_pct)}
                />
                <Stat
                  label="Violations"
                  value={vessel.violations_this_week !== undefined ? String(vessel.violations_this_week) : '—'}
                  color={vessel.violations_this_week ? 'var(--red-strong)' : 'var(--green-strong)'}
                />
                <Stat
                  label="Crew"
                  value={vessel.total_crew !== undefined ? String(vessel.total_crew) : '—'}
                  color="var(--txt2)"
                />
                <Stat
                  label="Dept OK"
                  value={
                    vessel.departments_finalized !== undefined && vessel.departments_total !== undefined
                      ? `${vessel.departments_finalized}/${vessel.departments_total}`
                      : '—'
                  }
                  color="var(--mark-strong)"
                />
              </div>
            )}
          </div>
        ))}
      </div>

    </div>
  );
}

function Stat({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      <span style={{
        fontFamily: 'var(--font-mono)',
        fontSize: 8,
        color: 'var(--txt-ghost)',
        textTransform: 'uppercase',
        letterSpacing: '0.06em',
      }}>{label}</span>
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 600, color }}>{value}</span>
    </div>
  );
}
