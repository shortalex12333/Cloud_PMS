'use client';

/**
 * ExportedHandoversView — Exported tab on /handover-export.
 *
 * Lists prior handovers the current user can see:
 *   - HODs (chief_engineer / chief_officer / captain / manager) see all rows
 *     for the active yacht.
 *   - Everyone else sees rows where they are outgoing/incoming user OR where
 *     their role appears on either side (same-role back-to-back peer visibility).
 *
 * Columns (per UX spec in lens_card_upgrades.md "Exported tab"):
 *   Generated | Rotation | Outgoing | HOD signed | Incoming signed | Status | ⋯
 *
 * Row click → navigate to the existing /handover-export/{id} lens.
 * Kebab menu → Open · Download PDF (mints signed URL) · Resend email (HOD+).
 *
 * Styling: tokens only, mirrors HandoverQueueView patterns
 * (see apps/web/src/components/handover/HandoverQueueView.tsx).
 */

import * as React from 'react';
import { useRouter } from 'next/navigation';
import {
  Loader2, RefreshCw, MoreHorizontal, ArrowUp, ArrowDown,
  FileText, Download, Mail, ExternalLink,
} from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { toast } from 'sonner';
import {
  fetchHandoverExports,
  mintHandoverExportSignedUrl,
  type HandoverExportListItem,
  type HandoverExportListResponse,
} from '@/components/shell/api';

// ============================================================================
// TYPES
// ============================================================================

type SortKey =
  | 'exported_at'
  | 'shift_date'
  | 'vessel_name'
  | 'department'
  | 'outgoing_user_name'
  | 'incoming_user_name'
  | 'review_status'
  | 'item_count';

type SortDir = 'asc' | 'desc';

const HOD_ROLES = new Set(['chief_engineer', 'chief_officer', 'captain', 'manager']);

// ============================================================================
// HELPERS
// ============================================================================

function formatTimestamp(iso: string | null | undefined): string {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return '—';
    // YYYY-MM-DD HH:MM (UTC-neutral, locale-independent, monospace-friendly)
    const pad = (n: number) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  } catch {
    return '—';
  }
}

function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return '—';
    const pad = (n: number) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  } catch {
    return '—';
  }
}

function roleLabel(role: string | null): string {
  if (!role) return '';
  return role.replace(/_/g, ' ');
}

type StatusPill = {
  label: string;
  fg: string;
  bg: string;
  border: string;
};

function resolveStatusPill(row: HandoverExportListItem): StatusPill {
  const rs = (row.review_status || '').toLowerCase();
  const signoff = row.signoff_complete === true;

  if (rs === 'complete' && signoff) {
    return { label: 'Complete', fg: 'var(--green)', bg: 'var(--green-bg)', border: 'var(--green)' };
  }
  if (rs === 'complete' && !signoff) {
    return { label: 'Awaiting incoming', fg: 'var(--amber)', bg: 'var(--amber-bg)', border: 'var(--amber)' };
  }
  if (rs === 'pending_hod_signature') {
    return { label: 'Pending HOD', fg: 'var(--amber)', bg: 'var(--amber-bg)', border: 'var(--amber)' };
  }
  if (rs === 'pending_review') {
    return { label: 'Pending review', fg: 'var(--txt3)', bg: 'var(--neutral-bg)', border: 'var(--border-sub)' };
  }
  return { label: rs || 'Unknown', fg: 'var(--txt3)', bg: 'var(--neutral-bg)', border: 'var(--border-sub)' };
}

function getSortValue(row: HandoverExportListItem, key: SortKey): string {
  switch (key) {
    case 'exported_at': return row.exported_at || '';
    case 'shift_date': return row.shift_date || '';
    case 'vessel_name': return row.vessel_name || '';
    case 'department': return row.department || '';
    case 'outgoing_user_name': return row.outgoing_user_name || row.outgoing_role || '';
    case 'incoming_user_name': return row.incoming_user_name || row.incoming_role || '';
    case 'review_status': return row.review_status || '';
    case 'item_count': return String(row.item_count ?? 0).padStart(6, '0');
  }
}

// Three-dot sign chain indicator: outgoing → HOD → incoming
function SignChain({ row }: { row: HandoverExportListItem }) {
  const steps = [
    { done: !!row.user_signed_at, label: 'Outgoing signed' },
    { done: !!row.hod_signed_at, label: 'HOD countersigned' },
    { done: !!row.incoming_signed_at, label: 'Incoming acknowledged' },
  ];
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
      {steps.map((s, i) => (
        <React.Fragment key={i}>
          <div
            title={`${s.label}: ${s.done ? '✓' : 'pending'}`}
            style={{
              width: 8, height: 8, borderRadius: '50%',
              background: s.done ? 'var(--green)' : 'var(--border-sub)',
              border: `1px solid ${s.done ? 'var(--green)' : 'var(--border-sub)'}`,
              flexShrink: 0,
            }}
          />
          {i < 2 && (
            <div style={{
              width: 12, height: 1,
              background: s.done ? 'var(--green)' : 'var(--border-sub)',
            }} />
          )}
        </React.Fragment>
      ))}
    </div>
  );
}

// ============================================================================
// COLUMN HEADER
// ============================================================================

function SortableHeader({
  label, colKey, active, dir, onClick, width, align,
}: {
  label: string;
  colKey: SortKey;
  active: boolean;
  dir: SortDir;
  onClick: (k: SortKey) => void;
  width: string;
  align?: 'left' | 'right';
}) {
  return (
    <button
      type="button"
      onClick={() => onClick(colKey)}
      style={{
        width,
        display: 'flex',
        alignItems: 'center',
        justifyContent: align === 'right' ? 'flex-end' : 'flex-start',
        gap: 4,
        padding: '0 12px',
        background: 'none',
        border: 'none',
        color: active ? 'var(--txt)' : 'var(--txt3)',
        fontSize: 10,
        fontWeight: 600,
        letterSpacing: '0.06em',
        textTransform: 'uppercase',
        fontFamily: 'var(--font-sans)',
        cursor: 'pointer',
        height: '100%',
      }}
    >
      <span>{label}</span>
      {active ? (
        dir === 'asc'
          ? <ArrowUp size={10} style={{ color: 'var(--mark)' }} />
          : <ArrowDown size={10} style={{ color: 'var(--mark)' }} />
      ) : null}
    </button>
  );
}

// ============================================================================
// KEBAB MENU
// ============================================================================

function KebabMenu({
  row, isHod, onOpen, onDownload,
}: {
  row: HandoverExportListItem;
  isHod: boolean;
  onOpen: () => void;
  onDownload: () => void;
}) {
  const [open, setOpen] = React.useState(false);
  const ref = React.useRef<HTMLDivElement | null>(null);

  React.useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, [open]);

  const handleResendEmail = () => {
    setOpen(false);
    // TODO: endpoint not yet available — surface a user-friendly notice.
    toast.info('Resend email — coming soon');
  };

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button
        type="button"
        onClick={(e) => { e.stopPropagation(); setOpen(v => !v); }}
        style={{
          width: 28, height: 28, display: 'flex', alignItems: 'center', justifyContent: 'center',
          borderRadius: 4, background: 'none', border: 'none',
          color: 'var(--txt3)', cursor: 'pointer',
        }}
        onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--surface-hover)'; }}
        onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'none'; }}
        aria-label="Row actions"
      >
        <MoreHorizontal size={14} />
      </button>
      {open && (
        <div
          style={{
            position: 'absolute', right: 0, top: '100%', marginTop: 4,
            minWidth: 180, zIndex: 10,
            background: 'var(--surface)',
            border: '1px solid var(--border-sub)',
            borderRadius: 6,
            boxShadow: 'var(--shadow-tip)',
            padding: 4,
          }}
          onClick={e => e.stopPropagation()}
        >
          <MenuItem icon={<ExternalLink size={12} />} label="Open" onClick={() => { setOpen(false); onOpen(); }} />
          <MenuItem icon={<Download size={12} />} label="Download PDF" onClick={() => { setOpen(false); onDownload(); }} disabled={!row.has_signed_document && !row.has_original_document} />
          {isHod && (
            <MenuItem icon={<Mail size={12} />} label="Resend email" onClick={handleResendEmail} />
          )}
        </div>
      )}
    </div>
  );
}

function MenuItem({
  icon, label, onClick, disabled = false,
}: {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      style={{
        width: '100%',
        display: 'flex', alignItems: 'center', gap: 8,
        padding: '7px 10px',
        border: 'none', background: 'none',
        color: disabled ? 'var(--txt-ghost)' : 'var(--txt2)',
        fontSize: 12, fontFamily: 'var(--font-sans)',
        cursor: disabled ? 'not-allowed' : 'pointer',
        borderRadius: 4,
        textAlign: 'left',
      }}
      onMouseEnter={e => { if (!disabled) (e.currentTarget as HTMLElement).style.background = 'var(--surface-hover)'; }}
      onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'none'; }}
    >
      {icon}
      <span>{label}</span>
    </button>
  );
}

// ============================================================================
// SKELETON ROW
// ============================================================================

function SkeletonRow() {
  return (
    <div style={{
      display: 'flex', alignItems: 'center',
      height: 44, padding: '0 12px',
      borderTop: '1px solid var(--border-faint)',
    }}>
      {[148, 140, 100, 180, 180, 96, 60, 130].map((w, i) => (
        <div key={i} style={{
          width: w, height: 12, marginRight: 12, flexShrink: 0,
          borderRadius: 3, background: 'var(--border-sub)', opacity: 0.5,
        }} />
      ))}
    </div>
  );
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

// Column widths — table is horizontally scrollable if needed.
const COL_WIDTHS = {
  generated: '148px',
  vessel: '140px',
  dept: '100px',
  outgoing: '180px',
  incoming: '180px',
  chain: '96px',
  items: '60px',
  status: '130px',
  kebab: '40px',
};

export function ExportedHandoversView() {
  const router = useRouter();
  const { user } = useAuth();

  const userRole = (user as { role?: string } | null)?.role || '';
  const userId = user?.id || '';
  const isHod = HOD_ROLES.has(userRole);

  const [data, setData] = React.useState<HandoverExportListResponse | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [sortKey, setSortKey] = React.useState<SortKey>('exported_at');
  const [sortDir, setSortDir] = React.useState<SortDir>('desc');
  const [downloadingId, setDownloadingId] = React.useState<string | null>(null);

  const load = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchHandoverExports();
      setData(result);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load exports';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => { load(); }, [load]);

  const handleSort = React.useCallback((key: SortKey) => {
    setSortKey(prev => {
      if (prev === key) {
        setSortDir(d => (d === 'asc' ? 'desc' : 'asc'));
        return prev;
      }
      setSortDir('desc');
      return key;
    });
  }, []);

  const sortedRows = React.useMemo(() => {
    if (!data) return [];
    const rows = [...data.exports];
    rows.sort((a, b) => {
      const av = getSortValue(a, sortKey);
      const bv = getSortValue(b, sortKey);
      if (av === bv) return 0;
      const cmp = av < bv ? -1 : 1;
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return rows;
  }, [data, sortKey, sortDir]);

  const handleOpen = React.useCallback((id: string) => {
    router.push(`/handover-export/${id}`);
  }, [router]);

  const handleDownload = React.useCallback(async (id: string) => {
    setDownloadingId(id);
    try {
      const signed = await mintHandoverExportSignedUrl(id);
      window.open(signed.url, '_blank', 'noopener,noreferrer');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to open document');
    } finally {
      setDownloadingId(null);
    }
  }, []);

  // ── Error state ───────────────────────────────────────────────────────────
  if (error && !loading) {
    return (
      <div style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        justifyContent: 'center', padding: '60px 24px', textAlign: 'center', gap: 8,
      }}>
        <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--txt2)' }}>Failed to load exported handovers</div>
        <div style={{ fontSize: 12, color: 'var(--txt-ghost)', marginBottom: 8 }}>{error}</div>
        <button
          onClick={load}
          style={{
            display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px',
            borderRadius: 6, fontSize: 12, fontWeight: 500, cursor: 'pointer',
            border: '1px solid var(--border-sub)', background: 'none', color: 'var(--txt2)',
            fontFamily: 'var(--font-sans)',
          }}
        >
          <RefreshCw size={12} /> Retry
        </button>
      </div>
    );
  }

  const totalCount = data?.total_count ?? 0;
  const shown = data?.count ?? 0;
  const showingAll = totalCount <= shown;

  return (
    <div style={{ padding: '16px 16px 32px', height: '100%', overflow: 'auto' }}>
      {/* Header row */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        marginBottom: 12,
      }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--txt)' }}>Exported Handovers</div>
          <div style={{ fontSize: 11, color: 'var(--txt3)', fontFamily: 'var(--font-mono)', marginTop: 2 }}>
            {loading
              ? 'Loading…'
              : shown === 0
                ? 'No exported handovers yet'
                : showingAll
                  ? `${shown} total`
                  : `Showing latest ${shown} of ${totalCount}`}
          </div>
        </div>
        <button
          onClick={load}
          disabled={loading}
          style={{
            display: 'flex', alignItems: 'center', gap: 5, padding: '6px 10px',
            borderRadius: 5, fontSize: 11, fontWeight: 500, cursor: 'pointer',
            border: '1px solid var(--border-sub)', background: 'none', color: 'var(--txt3)',
            fontFamily: 'var(--font-sans)', opacity: loading ? 0.5 : 1,
          }}
        >
          <RefreshCw size={11} style={loading ? { animation: 'spin 0.8s linear infinite' } : {}} /> Refresh
        </button>
      </div>

      {/* Table */}
      <div style={{
        background: 'var(--surface)',
        borderTop: '1px solid var(--border-top)',
        borderRight: '1px solid var(--border-side)',
        borderBottom: '1px solid var(--border-bottom)',
        borderLeft: '1px solid var(--border-side)',
        borderRadius: 6,
        overflow: 'hidden',
      }}>
        {/* Column header row (glass) */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          height: 36,
          background: 'var(--surface-glass, var(--surface))',
          backdropFilter: 'blur(10px)',
          WebkitBackdropFilter: 'blur(10px)',
          borderBottom: '1px solid var(--border-sub)',
        }}>
          <SortableHeader label="Generated" colKey="exported_at" active={sortKey === 'exported_at'} dir={sortDir} onClick={handleSort} width={COL_WIDTHS.generated} />
          <SortableHeader label="Vessel" colKey="vessel_name" active={sortKey === 'vessel_name'} dir={sortDir} onClick={handleSort} width={COL_WIDTHS.vessel} />
          <SortableHeader label="Dept" colKey="department" active={sortKey === 'department'} dir={sortDir} onClick={handleSort} width={COL_WIDTHS.dept} />
          <SortableHeader label="Outgoing" colKey="outgoing_user_name" active={sortKey === 'outgoing_user_name'} dir={sortDir} onClick={handleSort} width={COL_WIDTHS.outgoing} />
          <SortableHeader label="Incoming" colKey="incoming_user_name" active={sortKey === 'incoming_user_name'} dir={sortDir} onClick={handleSort} width={COL_WIDTHS.incoming} />
          <div style={{ width: COL_WIDTHS.chain, padding: '0 12px', display: 'flex', alignItems: 'center' }}>
            <span style={{ fontSize: 10, fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--txt3)' }}>Signed</span>
          </div>
          <SortableHeader label="Items" colKey="item_count" active={sortKey === 'item_count'} dir={sortDir} onClick={handleSort} width={COL_WIDTHS.items} align="right" />
          <SortableHeader label="Status" colKey="review_status" active={sortKey === 'review_status'} dir={sortDir} onClick={handleSort} width={COL_WIDTHS.status} />
          <div style={{ width: COL_WIDTHS.kebab }} />
        </div>

        {/* Body */}
        {loading ? (
          <>
            {[0, 1, 2, 3, 4].map(i => <SkeletonRow key={i} />)}
          </>
        ) : sortedRows.length === 0 ? (
          <div style={{
            padding: '60px 24px',
            textAlign: 'center',
            color: 'var(--txt3)',
            fontSize: 12,
          }}>
            <FileText size={22} style={{ color: 'var(--txt-ghost)', marginBottom: 8 }} />
            <div style={{ fontSize: 13, color: 'var(--txt2)', fontWeight: 500, marginBottom: 4 }}>
              No exported handovers yet
            </div>
            <div style={{ fontSize: 11, color: 'var(--txt-ghost)', fontFamily: 'var(--font-sans)' }}>
              Generate one from your Draft tab.
            </div>
          </div>
        ) : (
          sortedRows.map(row => (
            <ExportedRow
              key={row.id}
              row={row}
              isHod={isHod}
              currentUserRole={userRole}
              currentUserId={userId}
              downloading={downloadingId === row.id}
              onRowClick={() => handleOpen(row.id)}
              onOpen={() => handleOpen(row.id)}
              onDownload={() => handleDownload(row.id)}
            />
          ))
        )}
      </div>

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

// ============================================================================
// ROW
// ============================================================================

function PersonCell({ name, role, signedAt, overdueForMe, width }: {
  name: string | null;
  role: string | null;
  signedAt: string | null;
  overdueForMe: boolean;
  width: string;
}) {
  const nameColor = signedAt ? 'var(--txt)' : overdueForMe ? 'var(--red)' : 'var(--txt-ghost)';
  const roleColor = signedAt ? 'var(--txt3)' : overdueForMe ? 'var(--red)' : 'var(--txt-ghost)';

  return (
    <div style={{
      width, padding: '0 12px',
      display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 1,
      minWidth: 0, flexShrink: 0,
    }}>
      <div style={{
        fontSize: 12, fontWeight: 500, color: nameColor,
        whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
      }}>
        {name || roleLabel(role || '') || '—'}
      </div>
      {role && (
        <div style={{
          fontSize: 10, fontFamily: 'var(--font-mono)', color: roleColor, textTransform: 'capitalize',
          whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
        }}>
          {roleLabel(role)}
        </div>
      )}
    </div>
  );
}

function ExportedRow({
  row, isHod, currentUserRole, currentUserId, downloading,
  onRowClick, onOpen, onDownload,
}: {
  row: HandoverExportListItem;
  isHod: boolean;
  currentUserRole: string;
  currentUserId: string;
  downloading: boolean;
  onRowClick: () => void;
  onOpen: () => void;
  onDownload: () => void;
}) {
  const status = resolveStatusPill(row);

  const incomingOverdueForMe =
    !row.incoming_signed_at &&
    row.review_status === 'complete' &&
    row.incoming_role === currentUserRole &&
    currentUserRole !== '' &&
    row.incoming_user_id !== currentUserId;

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onRowClick}
      onKeyDown={(e) => { if (e.key === 'Enter') onRowClick(); }}
      style={{
        display: 'flex', alignItems: 'center',
        minHeight: 44,
        borderTop: '1px solid var(--border-faint)',
        cursor: 'pointer', transition: 'background 60ms',
      }}
      onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--surface-hover)'; }}
      onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = ''; }}
    >
      {/* Generated */}
      <div style={{
        width: COL_WIDTHS.generated, padding: '0 12px', flexShrink: 0,
        fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--txt3)',
        whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
      }}>
        {formatTimestamp(row.exported_at)}
      </div>

      {/* Vessel */}
      <div style={{
        width: COL_WIDTHS.vessel, padding: '0 12px', flexShrink: 0,
        fontSize: 12, fontWeight: 500, color: 'var(--txt2)',
        whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
      }}>
        {row.vessel_name || '—'}
      </div>

      {/* Department */}
      <div style={{
        width: COL_WIDTHS.dept, padding: '0 12px', flexShrink: 0,
        fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--txt3)',
        whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
        textTransform: 'capitalize',
      }}>
        {row.department || '—'}
      </div>

      {/* Outgoing — name primary, rank secondary */}
      <PersonCell
        name={row.outgoing_user_name}
        role={row.outgoing_role}
        signedAt={row.user_signed_at}
        overdueForMe={false}
        width={COL_WIDTHS.outgoing}
      />

      {/* Incoming — name primary, rank secondary */}
      <PersonCell
        name={row.incoming_user_name}
        role={row.incoming_role}
        signedAt={row.incoming_signed_at}
        overdueForMe={incomingOverdueForMe}
        width={COL_WIDTHS.incoming}
      />

      {/* Sign chain ●–●–● */}
      <div style={{
        width: COL_WIDTHS.chain, padding: '0 12px', flexShrink: 0,
        display: 'flex', alignItems: 'center',
      }}>
        <SignChain row={row} />
      </div>

      {/* Items count */}
      <div style={{
        width: COL_WIDTHS.items, padding: '0 12px', flexShrink: 0,
        fontSize: 12, fontFamily: 'var(--font-mono)', color: 'var(--txt3)',
        textAlign: 'right',
      }}>
        {row.item_count != null ? row.item_count : '—'}
      </div>

      {/* Status pill */}
      <div style={{
        width: COL_WIDTHS.status, padding: '0 12px', flexShrink: 0,
        display: 'flex', alignItems: 'center',
      }}>
        <span style={{
          display: 'inline-flex', alignItems: 'center',
          padding: '3px 8px', borderRadius: 3,
          fontSize: 10, fontWeight: 600, letterSpacing: '0.02em',
          fontFamily: 'var(--font-sans)',
          color: status.fg, background: status.bg,
          border: `1px solid ${status.border}33`,
          whiteSpace: 'nowrap',
        }}>
          {status.label}
        </span>
      </div>

      {/* Kebab */}
      <div style={{
        width: COL_WIDTHS.kebab,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        flexShrink: 0,
      }}>
        {downloading
          ? <Loader2 size={13} style={{ color: 'var(--txt-ghost)', animation: 'spin 0.8s linear infinite' }} />
          : <KebabMenu row={row} isHod={isHod} onOpen={onOpen} onDownload={onDownload} />
        }
      </div>
    </div>
  );
}
