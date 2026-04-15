'use client';

/**
 * Certificate Register — Printable Compliance View
 * =================================================
 *
 * One-page vessel + crew certificate register, grouped by urgency, styled for
 * A4 print. Intended for port state control inspections, surveyor visits,
 * flag state audits, and internal compliance reviews.
 *
 * Data source: `/api/vessel/{yachtId}/domain/certificates/records?limit=500`
 * which serves rows from the `v_certificates_enriched` tenant view (already
 * filtered by is_seed=false AND deleted_at IS NULL, with domain column for
 * vessel/crew disambiguation).
 *
 * The page uses component-scoped print CSS only — no globals.css changes.
 * All colours come from design tokens (var(--mark), var(--txt), etc.).
 */

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/hooks/useAuth';
import { useActiveVessel } from '@/contexts/VesselContext';
import { PrimaryButton } from '@/components/ui/PrimaryButton';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

type CertDomain = 'vessel' | 'crew' | string;

interface CertRecord {
  id: string;
  certificate_name?: string | null;
  certificate_type?: string | null;
  certificate_number?: string | null;
  issuing_authority?: string | null;
  issue_date?: string | null;
  expiry_date?: string | null;
  status?: string | null;
  domain?: CertDomain;
  person_name?: string | null;
  yacht_id?: string | null;
  yacht_name?: string | null;
}

type UrgencyBucket = 'expired' | 'expiring_30' | 'expiring_90' | 'valid' | 'terminal';

interface UrgencyGroup {
  key: UrgencyBucket;
  label: string;
  certs: CertRecord[];
}

function daysRemaining(expiry?: string | null): number | null {
  if (!expiry) return null;
  const d = new Date(expiry);
  if (Number.isNaN(d.getTime())) return null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.ceil((d.getTime() - today.getTime()) / 86_400_000);
}

function bucketFor(cert: CertRecord): UrgencyBucket {
  const status = (cert.status || '').toLowerCase();
  if (status === 'superseded' || status === 'revoked' || status === 'suspended') return 'terminal';
  const dr = daysRemaining(cert.expiry_date);
  if (dr === null) return 'valid';
  if (dr <= 0) return 'expired';
  if (dr <= 30) return 'expiring_30';
  if (dr <= 90) return 'expiring_90';
  return 'valid';
}

function certTitle(cert: CertRecord): string {
  if (cert.domain === 'crew') {
    const person = cert.person_name?.trim();
    const type = cert.certificate_type?.trim();
    if (person && type) return `${person} — ${type}`;
    return type || person || 'Crew Certificate';
  }
  return cert.certificate_name?.trim() || cert.certificate_type?.trim() || 'Certificate';
}

function formatDate(d?: string | null): string {
  if (!d) return '—';
  try {
    const parsed = new Date(d);
    if (Number.isNaN(parsed.getTime())) return d;
    return parsed.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
  } catch {
    return d;
  }
}

function formatDaysRemaining(cert: CertRecord): string {
  const dr = daysRemaining(cert.expiry_date);
  if (dr === null) return '—';
  if (dr < 0) return `${Math.abs(dr)}d overdue`;
  if (dr === 0) return 'today';
  return `${dr}d`;
}

async function fetchAllCerts(vesselId: string, token: string): Promise<CertRecord[]> {
  const url = `${API_BASE}/api/vessel/${vesselId}/domain/certificates/records?limit=500`;
  const res = await fetch(url, {
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });
  if (!res.ok) throw new Error(`Failed to load certificates: HTTP ${res.status}`);
  const data = await res.json();
  return (data.records || data.items || []) as CertRecord[];
}

function groupByUrgency(certs: CertRecord[]): UrgencyGroup[] {
  const buckets: Record<UrgencyBucket, CertRecord[]> = {
    expired: [],
    expiring_30: [],
    expiring_90: [],
    valid: [],
    terminal: [],
  };
  for (const c of certs) {
    buckets[bucketFor(c)].push(c);
  }
  // Sort each bucket by expiry ascending (most urgent first)
  const byExpiry = (a: CertRecord, b: CertRecord) =>
    (a.expiry_date || '9999').localeCompare(b.expiry_date || '9999');
  const groups: UrgencyGroup[] = [
    { key: 'expired', label: 'Expired', certs: buckets.expired.sort(byExpiry) },
    { key: 'expiring_30', label: 'Expiring within 30 days', certs: buckets.expiring_30.sort(byExpiry) },
    { key: 'expiring_90', label: 'Expiring within 90 days', certs: buckets.expiring_90.sort(byExpiry) },
    { key: 'valid', label: 'Valid', certs: buckets.valid.sort(byExpiry) },
    { key: 'terminal', label: 'Superseded / Revoked / Suspended', certs: buckets.terminal.sort(byExpiry) },
  ];
  return groups.filter((g) => g.certs.length > 0);
}

function CertificateRegisterContent() {
  const router = useRouter();
  const { user, session } = useAuth();
  const vessel = useActiveVessel();
  const vesselId = vessel.vesselId || user?.yachtId;
  const vesselName = vessel.vesselName || user?.yachtName || '';

  const { data: certs, isLoading, error } = useQuery<CertRecord[]>({
    queryKey: ['certificate-register', vesselId],
    queryFn: () => fetchAllCerts(vesselId!, session?.access_token || ''),
    enabled: !!vesselId && !!session?.access_token,
    staleTime: 30_000,
  });

  const groups = React.useMemo(() => groupByUrgency(certs || []), [certs]);
  const total = certs?.length ?? 0;
  const now = React.useMemo(() => new Date().toLocaleString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit', hour12: false,
  }), []);

  const handlePrint = React.useCallback(() => {
    if (typeof window !== 'undefined') window.print();
  }, []);

  const handleBack = React.useCallback(() => {
    router.push('/certificates');
  }, [router]);

  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center bg-surface-base">
        <div className="text-sm" style={{ color: 'var(--txt2)' }}>Loading certificate register…</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full flex items-center justify-center bg-surface-base">
        <div className="text-sm" style={{ color: 'var(--red)' }}>
          Failed to load certificates: {error instanceof Error ? error.message : 'unknown error'}
        </div>
      </div>
    );
  }

  return (
    <>
      {/* Scoped print CSS — applies only to this page */}
      <style jsx global>{`
        @media print {
          .register-no-print { display: none !important; }
          body { background: white !important; }
          .register-root { padding: 12mm !important; }
          .register-table { font-size: 10pt; }
          .register-group { break-inside: avoid; }
          .register-group + .register-group { page-break-before: auto; }
          .register-h1 { color: #000 !important; }
          .register-meta { color: #444 !important; }
        }
        @page { size: A4; margin: 12mm; }
      `}</style>

      <div className="register-root min-h-full bg-surface-base" style={{ padding: '20px 32px 48px' }}>
        {/* Screen-only toolbar */}
        <div className="register-no-print flex items-center justify-between mb-6">
          <button
            onClick={handleBack}
            className="text-sm font-medium"
            style={{ color: 'var(--txt2)', background: 'none', border: 'none', cursor: 'pointer' }}
          >
            ← Back to Certificates
          </button>
          <PrimaryButton onClick={handlePrint}>Print Register</PrimaryButton>
        </div>

        {/* Header — shown in print and screen */}
        <header className="mb-6" style={{ borderBottom: '1px solid var(--border-sub)', paddingBottom: 12 }}>
          <h1
            className="register-h1"
            style={{ fontSize: 22, fontWeight: 600, color: 'var(--txt)', margin: 0 }}
          >
            Certificate Register
          </h1>
          <div
            className="register-meta"
            style={{ fontSize: 12, color: 'var(--txt2)', marginTop: 6 }}
          >
            {vesselName ? `${vesselName} · ` : ''}
            Generated {now} · {total} record{total === 1 ? '' : 's'}
          </div>
        </header>

        {/* Groups */}
        {groups.length === 0 && (
          <div className="text-sm" style={{ color: 'var(--txt2)' }}>No certificates recorded.</div>
        )}

        {groups.map((g) => (
          <section key={g.key} className="register-group mb-6">
            <h2
              style={{
                fontSize: 13,
                fontWeight: 600,
                color: 'var(--txt)',
                margin: '20px 0 8px',
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
              }}
            >
              {g.label} <span style={{ color: 'var(--txt2)', fontWeight: 500 }}>({g.certs.length})</span>
            </h2>
            <table
              className="register-table"
              style={{
                width: '100%',
                borderCollapse: 'collapse',
                fontSize: 12,
              }}
            >
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-sub)' }}>
                  <th style={cellStyle('th', { width: '36%' })}>Certificate</th>
                  <th style={cellStyle('th', { width: '12%' })}>Type</th>
                  <th style={cellStyle('th', { width: '18%' })}>Issuing Authority</th>
                  <th style={cellStyle('th', { width: '10%' })}>Cert No.</th>
                  <th style={cellStyle('th', { width: '11%' })}>Expiry</th>
                  <th style={cellStyle('th', { width: '13%', textAlign: 'right' })}>Remaining</th>
                </tr>
              </thead>
              <tbody>
                {g.certs.map((c) => (
                  <tr
                    key={c.id}
                    style={{ borderBottom: '1px solid var(--border-faint)' }}
                  >
                    <td style={cellStyle('td')}>
                      <span style={{ color: 'var(--txt)' }}>{certTitle(c)}</span>
                      {c.domain === 'crew' && c.person_name && (
                        <span
                          style={{
                            marginLeft: 6,
                            fontSize: 10,
                            color: 'var(--txt3)',
                            textTransform: 'uppercase',
                            letterSpacing: '0.04em',
                          }}
                        >
                          Crew
                        </span>
                      )}
                    </td>
                    <td style={cellStyle('td')}>{c.certificate_type || '—'}</td>
                    <td style={cellStyle('td')}>{c.issuing_authority || '—'}</td>
                    <td style={cellStyle('td', { fontFamily: 'var(--font-mono, ui-monospace, monospace)', fontSize: 11 })}>
                      {c.certificate_number || '—'}
                    </td>
                    <td style={cellStyle('td', { fontFamily: 'var(--font-mono, ui-monospace, monospace)', fontSize: 11 })}>
                      {formatDate(c.expiry_date)}
                    </td>
                    <td style={cellStyle('td', { textAlign: 'right' })}>{formatDaysRemaining(c)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        ))}

        <footer
          className="register-meta"
          style={{
            marginTop: 32,
            paddingTop: 12,
            borderTop: '1px solid var(--border-sub)',
            fontSize: 10,
            color: 'var(--txt3)',
          }}
        >
          Source of truth: v_certificates_enriched (excludes seed data and soft-deleted rows).
          Status transitions are auto-applied nightly via the certificate expiry worker.
          Every change to this register is recorded in ledger_events with a tamper-evident proof hash.
        </footer>
      </div>
    </>
  );
}

// --- small helper to keep inline cell styles consistent ---
function cellStyle(
  kind: 'th' | 'td',
  extra: React.CSSProperties = {},
): React.CSSProperties {
  if (kind === 'th') {
    return {
      padding: '8px 6px',
      textAlign: 'left',
      fontWeight: 600,
      fontSize: 10,
      textTransform: 'uppercase',
      letterSpacing: '0.06em',
      color: 'var(--txt2)',
      ...extra,
    };
  }
  return {
    padding: '8px 6px',
    color: 'var(--txt)',
    verticalAlign: 'top',
    ...extra,
  };
}

export default function CertificateRegisterPage() {
  return (
    <React.Suspense
      fallback={
        <div className="h-full flex items-center justify-center bg-surface-base">
          <div className="w-8 h-8 border-2 border-border-sub border-t-mark rounded-full animate-spin" />
        </div>
      }
    >
      <CertificateRegisterContent />
    </React.Suspense>
  );
}
