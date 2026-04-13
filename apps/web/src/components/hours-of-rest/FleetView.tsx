'use client';

/**
 * FleetView — Fleet Manager cross-vessel Hours of Rest overview
 *
 * Phase 1: renders vessel cards from bootstrap fleet_vessels[].
 * Phase 6: wires to /api/v1/hours-of-rest/fleet-compliance for live data.
 */

import * as React from 'react';
import { useAuth } from '@/hooks/useAuth';

interface VesselSummary {
  yacht_id: string;
  yacht_name: string;
  // Phase 6: populated from fleet-compliance API
  compliance_pct?: number;
  total_crew?: number;
  violations_this_week?: number;
  departments_finalized?: number;
  departments_total?: number;
  loading?: boolean;
}

function complianceColor(pct: number | undefined): string {
  if (pct === undefined) return 'rgba(255,255,255,0.3)';
  if (pct >= 100) return 'rgba(34,197,94,0.9)';
  if (pct >= 90) return 'rgba(245,158,11,0.9)';
  return 'rgba(239,68,68,0.9)';
}

export function FleetView() {
  const { user } = useAuth();
  const vessels: VesselSummary[] = (user?.fleet_vessels ?? []).map(v => ({
    yacht_id: v.yacht_id,
    yacht_name: v.yacht_name,
    loading: true, // Phase 6: will be replaced by real data fetch
  }));

  if (vessels.length === 0) {
    return (
      <div style={{
        padding: 48,
        textAlign: 'center',
        fontFamily: 'var(--font-mono)',
        fontSize: 11,
        color: 'rgba(255,255,255,0.25)',
      }}>
        No fleet vessels assigned to your account.
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

      {/* ── Header ── */}
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: 9,
        color: 'rgba(255,255,255,0.25)',
        textTransform: 'uppercase',
        letterSpacing: '0.10em',
      }}>
        Fleet Overview — {vessels.length} vessel{vessels.length !== 1 ? 's' : ''}
      </div>

      {/* ── Vessel cards ── */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))',
        gap: 12,
      }}>
        {vessels.map(vessel => (
          <div
            key={vessel.yacht_id}
            style={{
              background: 'rgba(255,255,255,0.03)',
              border: '1px solid rgba(255,255,255,0.07)',
              borderRadius: 8,
              padding: '16px 18px',
            }}
          >
            <div style={{
              fontFamily: 'var(--font-mono)',
              fontSize: 12,
              fontWeight: 600,
              color: 'rgba(255,255,255,0.75)',
              marginBottom: 12,
              letterSpacing: '0.04em',
            }}>
              {vessel.yacht_name}
            </div>

            {vessel.loading ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {[1, 2, 3].map(i => (
                  <div key={i} style={{
                    height: 12,
                    background: 'rgba(255,255,255,0.05)',
                    borderRadius: 4,
                    animation: 'pulse 1.5s ease-in-out infinite',
                  }} />
                ))}
                <div style={{
                  marginTop: 4,
                  fontFamily: 'var(--font-mono)',
                  fontSize: 8,
                  color: 'rgba(255,255,255,0.2)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.08em',
                }}>
                  Live data — Phase 6
                </div>
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
                  color={vessel.violations_this_week ? 'rgba(239,68,68,0.9)' : 'rgba(34,197,94,0.8)'}
                />
                <Stat
                  label="Crew"
                  value={vessel.total_crew !== undefined ? String(vessel.total_crew) : '—'}
                  color="rgba(255,255,255,0.55)"
                />
                <Stat
                  label="Dept OK"
                  value={
                    vessel.departments_finalized !== undefined && vessel.departments_total !== undefined
                      ? `${vessel.departments_finalized}/${vessel.departments_total}`
                      : '—'
                  }
                  color="rgba(90,171,204,0.8)"
                />
              </div>
            )}
          </div>
        ))}
      </div>

      {/* ── Phase 6 notice ── */}
      <div style={{
        padding: '10px 14px',
        background: 'rgba(90,171,204,0.04)',
        border: '1px solid rgba(90,171,204,0.12)',
        borderRadius: 6,
        fontFamily: 'var(--font-mono)',
        fontSize: 9,
        color: 'rgba(90,171,204,0.45)',
        letterSpacing: '0.04em',
      }}>
        Cross-vessel compliance data wires in Phase 6. Vessel list is live from your fleet assignment.
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
        color: 'rgba(255,255,255,0.25)',
        textTransform: 'uppercase',
        letterSpacing: '0.06em',
      }}>{label}</span>
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 600, color }}>{value}</span>
    </div>
  );
}
