'use client';

/**
 * HandoverContent — lens-v2 entity view.
 * Prototype: public/prototypes/lens-handover.html
 *
 * Data flow:
 * - Entity data from useEntityLensContext() → backend /v1/entity/{type}/{id}
 * - Actions from availableActions[] → backend /v1/actions/execute
 * - ActionPopup auto-builds form fields from action.required_fields
 *
 * Sections: Identity → Document Preview → Entity Links → Signatures → Notes → Attachments → History → Audit Trail
 *
 * TODO notes for next engineer:
 * - Export PDF handler not wired (onClick is noop)
 */

import * as React from 'react';
import { useRouter } from 'next/navigation';
import styles from '../lens.module.css';
import { IdentityStrip, type PillDef, type DetailLine } from '../IdentityStrip';
import { mapActionFields, actionHasFields, getSignatureLevel } from '../mapActionFields';
import { SplitButton, type DropdownItem } from '../SplitButton';
import { ScrollReveal } from '../ScrollReveal';
import { useEntityLensContext } from '@/contexts/EntityLensContext';
import { getEntityRoute } from '@/lib/featureFlags';

import {
  NotesSection,
  AttachmentsSection,
  DocRowsSection,
  KVSection,
  AuditTrailSection,
  HistorySection,
  type NoteItem,
  type AttachmentItem,
  type DocRowItem,
  type KVItem,
  type AuditEvent,
  type HistoryPeriod,
} from '../sections';
import { ActionPopup, type ActionPopupField } from '../ActionPopup';

// ─── Colour mapping helpers ───

function statusToPillVariant(status: string): PillDef['variant'] {
  switch (status) {
    case 'signed':
    case 'completed':
    case 'acknowledged':
      return 'green';
    case 'pending_review':
    case 'pending_signature':
    case 'pending':
      return 'amber';
    case 'archived':
    case 'rejected':
      return 'red';
    default:
      return 'neutral';
  }
}

function formatLabel(str: string): string {
  return str.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

// ─── Component ───

export function HandoverContent() {
  const router = useRouter();
  const { entity, availableActions, executeAction, getAction, isLoading } = useEntityLensContext();

  // ── Extract entity fields ──
  const payload = (entity?.payload as Record<string, unknown>) ?? {};
  const handover_number = (entity?.handover_number ?? payload.handover_number) as string | undefined;
  const title = ((entity?.title ?? payload.title) as string | undefined) ?? 'Handover';
  const handover_type = (entity?.handover_type ?? payload.handover_type) as string | undefined;
  const status = ((entity?.status ?? payload.status) as string | undefined) ?? 'draft';
  const created_by = (entity?.created_by ?? payload.created_by) as string | undefined;
  const created_date = (entity?.created_date ?? entity?.created_at ?? payload.created_date ?? payload.created_at) as string | undefined;
  const signed_by = (entity?.signed_by ?? payload.signed_by) as string | undefined;
  const signed_date = (entity?.signed_date ?? payload.signed_date) as string | undefined;
  const department = (entity?.department ?? payload.department) as string | undefined;
  const vessel_name = (entity?.vessel_name ?? payload.vessel_name) as string | undefined;
  const from_crew = (entity?.from_crew ?? payload.from_crew) as string | undefined;
  const from_role = (entity?.from_role ?? payload.from_role) as string | undefined;
  const to_crew = (entity?.to_crew ?? payload.to_crew) as string | undefined;
  const to_role = (entity?.to_role ?? payload.to_role) as string | undefined;
  const rotation_start = (entity?.rotation_start ?? payload.rotation_start) as string | undefined;
  const rotation_end = (entity?.rotation_end ?? payload.rotation_end) as string | undefined;
  const content = (entity?.content ?? entity?.body ?? payload.content ?? payload.body) as string | undefined;
  const export_url = (entity?.export_url ?? payload.export_url) as string | undefined;

  // Section data
  const signatures = ((entity?.signatures ?? payload.signatures) as Array<Record<string, unknown>> | undefined) ?? [];
  const embedded_entities = ((entity?.embedded_entities ?? payload.embedded_entities ?? entity?.entity_links ?? payload.entity_links) as Array<Record<string, unknown>> | undefined) ?? [];
  const notes = ((entity?.notes ?? payload.notes) as Array<Record<string, unknown>> | undefined) ?? [];
  const attachments = ((entity?.attachments ?? payload.attachments) as Array<Record<string, unknown>> | undefined) ?? [];
  const summary_stats = (entity?.summary_stats ?? payload.summary_stats) as Record<string, unknown> | undefined;

  // ── Action gates ──
  const signAction = getAction('sign_handover');

  // BACKEND_AUTO moved to mapActionFields.ts
  const [actionPopupConfig, setActionPopupConfig] = React.useState<{
    actionId: string; title: string; fields: ActionPopupField[]; signatureLevel: 0|1|2|3|4|5;
  } | null>(null);

  // Wet signature modal state (no PIN)
  const [showSignModal, setShowSignModal] = React.useState(false);
  const signCanvasRef = React.useRef<HTMLCanvasElement>(null);
  const [isDrawing, setIsDrawing] = React.useState(false);

  function openActionPopup(action: { action_id: string; label: string; required_fields: string[]; prefill: Record<string, unknown>; requires_signature: boolean }) {
    const fields = mapActionFields(action as any);
    setActionPopupConfig({ actionId: action.action_id, title: action.label, fields, signatureLevel: 0 });
  }

  // ── Derived display ──
  const statusLabel = formatLabel(status);

  // Pills
  const pills: PillDef[] = [
    { label: statusLabel, variant: statusToPillVariant(status) },
  ];

  // Detail lines
  const details: DetailLine[] = [];
  if (department) {
    details.push({ label: 'Department', value: department });
  }
  if (rotation_start || rotation_end) {
    const rotationStr = [rotation_start, rotation_end].filter(Boolean).join(' — ');
    details.push({ label: 'Rotation', value: rotationStr, mono: true });
  }
  if (vessel_name) {
    details.push({ label: 'Vessel', value: vessel_name });
  }
  if (created_date) {
    details.push({ label: 'Generated', value: created_date, mono: true });
  }

  // Context line: from → to crew
  const contextNode = (from_crew || to_crew) ? (
    <>
      {from_crew && (
        <span className={styles.crewLink}>{from_crew}</span>
      )}
      {from_role && ` (${from_role})`}
      {from_crew && to_crew && (
        <span style={{ color: 'var(--txt3)', margin: '0 6px', fontSize: 14 }}>&rarr;</span>
      )}
      {to_crew && (
        <span className={styles.crewLink}>{to_crew}</span>
      )}
      {to_role && ` (${to_role})`}
    </>
  ) : undefined;

  // ── Split button config ──
  const canSign = signAction !== null && ['draft', 'pending_review', 'pending_signature', 'pending'].includes(status);

  const handlePrimary = React.useCallback(() => {
    setShowSignModal(true);
  }, []);

  const handleSignConfirm = React.useCallback(async () => {
    const canvas = signCanvasRef.current;
    if (!canvas) return;
    const signatureData = canvas.toDataURL('image/png');
    await executeAction('sign_handover', { signature: signatureData });
    setShowSignModal(false);
  }, [executeAction]);

  const SPECIAL_HANDLERS: Record<string, () => void> = {};
  const DANGER_ACTIONS = new Set(['archive_handover', 'delete_handover']);
  const primaryActionId = 'sign_handover';

  // Actions that make sense on a handover export page
  const ALLOWED_ACTIONS = new Set([
    'sign_handover_incoming',
    'regenerate_handover_summary',
    'archive_handover',
    'delete_handover',
  ]);

  const dynamicItems: DropdownItem[] = availableActions
    .filter((a) => a.action_id !== primaryActionId && ALLOWED_ACTIONS.has(a.action_id))
    .map((a) => ({
      label: a.label,
      onClick: SPECIAL_HANDLERS[a.action_id]
        ? SPECIAL_HANDLERS[a.action_id]
        : () => {
            const hasFields = actionHasFields(a as any);
            if (hasFields || a.requires_signature) { openActionPopup(a); } else { executeAction(a.action_id); }
          },
      disabled: a.disabled,
      disabledReason: a.disabled_reason ?? undefined,
      danger: DANGER_ACTIONS.has(a.action_id),
    }));

  // Client-side items + filtered backend actions
  const dropdownItems: DropdownItem[] = [
    {
      label: 'Export PDF',
      icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M6 9V2h12v7" /><path d="M6 18H4a2 2 0 01-2-2v-5a2 2 0 012-2h16a2 2 0 012 2v5a2 2 0 01-2 2h-2" /><rect x="6" y="14" width="12" height="8" /></svg>,
      onClick: () => window.print(),
    },
    ...dynamicItems,
  ];

  // ── Map section data ──

  // Embedded entities → DocRows
  const entityLinks: DocRowItem[] = embedded_entities.map((e, i) => ({
    id: (e.id as string) ?? `ent-${i}`,
    name: (e.name ?? e.title) as string ?? 'Entity',
    code: (e.code ?? e.reference ?? e.entity_code) as string | undefined,
    meta: (e.type ?? e.entity_type ?? e.description) as string | undefined,
    date: (e.date ?? e.due_date) as string | undefined,
    onClick: e.id && e.entity_type
      ? () => router.push(getEntityRoute(e.entity_type as Parameters<typeof getEntityRoute>[0], e.id as string))
      : undefined,
  }));

  // Signatures → KV items
  const signatureItems: KVItem[] = signatures.map((s, i) => {
    const name = (s.name ?? s.signer_name ?? s.user_name) as string ?? `Signer ${i + 1}`;
    const role = (s.role ?? s.signer_role) as string | undefined;
    const sigStatus = (s.status ?? (s.signed_at ? 'signed' : 'pending')) as string;
    const timestamp = (s.signed_at ?? s.timestamp) as string | undefined;

    return {
      label: role ? `${name} (${role})` : name,
      value: sigStatus === 'signed' ? (
        <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className={styles.mono} style={{ fontSize: 11, color: 'var(--txt3)' }}>{timestamp ?? ''}</span>
          <span style={{
            fontSize: 11, fontWeight: 600, textTransform: 'uppercase',
            letterSpacing: '0.04em', padding: '3px 10px', borderRadius: 4,
            background: 'var(--green-bg)', color: 'var(--green)',
            border: '1px solid var(--green-border)',
          }}>
            Signed
          </span>
        </span>
      ) : (
        <span style={{
          fontSize: 11, fontWeight: 600, textTransform: 'uppercase',
          letterSpacing: '0.04em', padding: '3px 10px', borderRadius: 4,
          background: 'var(--neutral-bg)', color: 'var(--txt3)',
          border: '1px solid var(--border-sub)',
        }}>
          Pending
        </span>
      ),
    };
  });

  // Notes
  const noteItems: NoteItem[] = notes.map((n, i) => ({
    id: (n.id as string) ?? `note-${i}`,
    author: (n.author ?? n.created_by ?? n.user_name) as string ?? 'Unknown',
    timestamp: (n.created_at ?? n.timestamp) as string ?? '',
    body: (n.body ?? n.note_text ?? n.text) as string ?? '',
  }));

  // Attachments
  const attachmentItems: AttachmentItem[] = attachments.map((a, i) => ({
    id: (a.id as string) ?? `att-${i}`,
    name: (a.name ?? a.file_name ?? a.filename) as string ?? 'File',
    caption: (a.caption ?? a.description) as string | undefined,
    size: (a.size ?? a.file_size) as string | undefined,
    kind: (((a.mime_type ?? a.content_type) as string) ?? '').startsWith('image') ? 'image' as const : 'document' as const,
  }));

  // Prior periods / history
  const priorPeriods = ((entity?.prior_periods ?? payload.prior_periods ?? entity?.history_periods ?? payload.history_periods) as Array<Record<string, unknown>> | undefined) ?? [];
  const auditTrail = ((entity?.audit_trail ?? payload.audit_trail ?? entity?.audit_history ?? payload.audit_history) as Array<Record<string, unknown>> | undefined) ?? [];

  const historyPeriods: HistoryPeriod[] = priorPeriods.map((p, i) => ({
    id: (p.id as string) ?? `period-${i}`,
    year: (p.year ?? p.period_year) as string ?? '',
    label: (p.label ?? p.period_label ?? p.description) as string ?? '',
    status: ((p.status as string) === 'active' || (p.status as string) === 'current') ? 'active' as const : 'closed' as const,
    summary: (p.summary ?? p.period_summary) as string ?? '',
  }));

  const auditEvents: AuditEvent[] = auditTrail.map((h, i) => ({
    id: (h.id as string) ?? `audit-${i}`,
    action: (h.action ?? h.description ?? h.event) as string ?? '',
    actor: (h.actor ?? h.user_name ?? h.performed_by) as string | undefined,
    timestamp: (h.created_at ?? h.timestamp) as string ?? '',
  }));

  // Summary stats for inline rendering
  const openWOs = (summary_stats?.open_work_orders ?? summary_stats?.open_wos) as number | undefined;
  const activeFaults = (summary_stats?.active_faults) as number | undefined;
  const lowStockItems = (summary_stats?.low_stock_items ?? summary_stats?.low_stock) as number | undefined;

  return (
    <>
      {/* Identity Strip */}
      <IdentityStrip
        overline={handover_number}
        title={title}
        context={contextNode}
        pills={pills}
        details={details}
        actionSlot={
          canSign ? (
            <SplitButton
              label="Sign Handover"
              icon={
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                </svg>
              }
              onClick={handlePrimary}
              disabled={signAction?.disabled ?? false}
              disabledReason={signAction?.disabled_reason ?? undefined}
              items={dropdownItems}
            />
          ) : dropdownItems.length > 0 ? (
            <SplitButton
              label="Export PDF"
              icon={
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <path d="M6 9l6 6 4-8" /><rect x="2" y="2" width="20" height="20" rx="2" />
                </svg>
              }
              onClick={() => window.print()}
              items={dropdownItems}
            />
          ) : undefined
        }
      />

      {/* ═══ Professional Handover Document ═══ */}
      {(() => {
        const secs = (entity?.sections ?? []) as Array<{
          title?: string; id?: string;
          items?: Array<{ content?: string; priority?: string; entity_type?: string; entity_url?: string }>;
          is_critical?: boolean;
        }>;
        const totalItems = secs.reduce((n, s) => n + (s.items?.length ?? 0), 0);
        const criticalSecs = secs.filter(s => s.is_critical).length;
        const docNumber = (entity?.doc_number as string) ?? '0001';
        const isEditable = status === 'pending_review';

        if (isLoading) {
          return <div style={{ textAlign: 'center', color: 'var(--txt-ghost)', padding: '48px 0', fontSize: 12 }}>Loading document...</div>;
        }
        if (secs.length === 0) {
          return <div style={{ textAlign: 'center', color: 'var(--txt-ghost)', padding: '48px 0', fontSize: 12, fontStyle: 'italic' }}>No handover content available</div>;
        }

        return (
          <div style={{
            maxWidth: 780,
            margin: '24px auto 0',
            background: '#ffffff',
            color: '#1A2332',
            border: '1px solid #D8DEE4',
            borderRadius: 6,
            overflow: 'hidden',
          }}>
            {/* ── Cover Header ── */}
            <div style={{
              padding: '40px 48px 32px',
              textAlign: 'center',
              borderBottom: '2px solid #5AABCC',
            }}>
              <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#8896A6', marginBottom: 8 }}>
                Technical Handover Report
              </div>
              <div style={{ fontSize: 20, fontWeight: 700, color: '#1A2332', marginBottom: 6 }}>
                {vessel_name ?? title}
              </div>
              <div style={{ display: 'flex', justifyContent: 'center', gap: 24, fontSize: 11, color: '#8896A6', marginTop: 12 }}>
                <span><span style={{ fontWeight: 600, color: '#4A5568' }}>Doc</span>{' '}<span style={{ fontFamily: "'SF Mono', 'Fira Code', 'Consolas', monospace" }}>THR-{String(docNumber).padStart(4, '0')}</span></span>
                {created_date && <span><span style={{ fontWeight: 600, color: '#4A5568' }}>Generated</span>{' '}<span style={{ fontFamily: "'SF Mono', 'Fira Code', 'Consolas', monospace" }}>{new Date(created_date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}</span></span>}
                {department && <span><span style={{ fontWeight: 600, color: '#4A5568' }}>Dept</span>{' '}{department}</span>}
              </div>
              <div style={{ fontSize: 11, color: '#8896A6', marginTop: 16, fontStyle: 'italic' }}>
                {totalItems} items across {secs.length} departments{criticalSecs > 0 ? ` · ${criticalSecs} critical` : ''}
              </div>
            </div>

            {/* ── Table of Contents ── */}
            <div style={{ padding: '20px 48px', borderBottom: '1px solid #E8EDF1' }}>
              <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', color: '#8896A6', marginBottom: 10 }}>
                Contents
              </div>
              {secs.map((sec, si) => (
                <div key={`toc-${si}`} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', fontSize: 12 }}>
                  <span style={{ fontWeight: 500, color: '#1A2332' }}>{sec.title ?? `Section ${si + 1}`}</span>
                  <span style={{ color: '#8896A6' }}>({sec.items?.length ?? 0} item{(sec.items?.length ?? 0) !== 1 ? 's' : ''})</span>
                </div>
              ))}
            </div>

            {/* ── Sections ── */}
            <div style={{ padding: '0 48px' }}>
              {secs.map((sec, si) => (
                <div key={sec.id ?? `sec-${si}`} style={{ padding: '32px 0', borderBottom: si < secs.length - 1 ? '1px solid #E8EDF1' : 'none' }}>
                  <div style={{
                    display: 'flex', alignItems: 'center', gap: 10,
                    paddingLeft: 14,
                    borderLeft: '4px solid #5AABCC',
                    marginBottom: 20,
                  }}>
                    <span style={{ fontSize: 13, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em', color: '#1A2332' }}>
                      {sec.title ?? `Section ${si + 1}`}
                    </span>
                    <span style={{ fontSize: 10, color: '#8896A6' }}>
                      {sec.items?.length ?? 0} item{(sec.items?.length ?? 0) !== 1 ? 's' : ''}
                    </span>
                    {sec.is_critical && (
                      <span style={{
                        fontSize: 9, fontWeight: 600, padding: '2px 7px', borderRadius: 3,
                        background: '#FFF5F5', color: '#C53030',
                        border: '1px solid #FEB2B2',
                        textTransform: 'uppercase', letterSpacing: '0.03em',
                      }}>Critical</span>
                    )}
                  </div>

                  {(sec.items ?? []).map((item, ii) => (
                    <div key={`item-${si}-${ii}`} id={`item-${si}-${ii}`} style={{
                      padding: '12px 0 12px 14px',
                      borderLeft: item.priority === 'critical' ? '4px solid #C53030' : '4px solid #E8EDF1',
                      marginBottom: 12,
                      position: 'relative',
                      transition: 'opacity 0.2s',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                        <div style={{ fontSize: 10, fontWeight: 600, color: '#8896A6', letterSpacing: '0.02em' }}>
                          {si + 1}.{ii + 1}
                        </div>
                        {isEditable && (
                          <button
                            onClick={() => {
                              // Remove item from sections and trigger re-render
                              // For now: visual feedback only — save-draft persists the change
                              const el = document.getElementById(`item-${si}-${ii}`);
                              if (el) { el.style.opacity = '0.3'; el.style.pointerEvents = 'none'; }
                            }}
                            style={{
                              background: 'none', border: 'none', cursor: 'pointer',
                              fontSize: 11, color: '#C53030', padding: '2px 6px', borderRadius: 3,
                              opacity: 0.5,
                            }}
                            onMouseOver={(e) => { (e.target as HTMLElement).style.opacity = '1'; }}
                            onMouseOut={(e) => { (e.target as HTMLElement).style.opacity = '0.5'; }}
                            title="Remove this item"
                          >
                            ✕
                          </button>
                        )}
                      </div>
                      <div
                        style={{
                          fontSize: 13, lineHeight: 1.75, color: '#1A2332',
                          whiteSpace: 'pre-line',
                          outline: 'none',
                          borderRadius: 3,
                          padding: isEditable ? '4px 6px' : 0,
                          border: isEditable ? '1px dashed #D8DEE4' : 'none',
                          cursor: isEditable ? 'text' : 'default',
                        }}
                        contentEditable={isEditable}
                        suppressContentEditableWarning
                      >
                        {item.content ?? ''}
                      </div>
                      {item.entity_url && (
                        <a href={item.entity_url} target="_blank" rel="noopener noreferrer"
                          style={{ display: 'inline-block', marginTop: 8, fontSize: 10, color: '#5AABCC', textDecoration: 'none' }}
                          onMouseOver={(e) => { (e.target as HTMLElement).style.textDecoration = 'underline'; }}
                          onMouseOut={(e) => { (e.target as HTMLElement).style.textDecoration = 'none'; }}
                        >
                          View {(item.entity_type ?? 'item').replace(/_/g, ' ')} →
                        </a>
                      )}
                    </div>
                  ))}
                </div>
              ))}
            </div>

            {/* ── Signature Block ── */}
            <div style={{
              padding: '32px 48px',
              borderTop: '2px solid #D8DEE4',
              display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 48,
            }}>
              <div>
                <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: '0.05em', textTransform: 'uppercase', color: '#5AABCC', marginBottom: 20 }}>
                  Prepared By
                </div>
                <div style={{ height: 48, borderBottom: '1px solid #D8DEE4', marginBottom: 8 }} />
                <div style={{ fontSize: 12, fontWeight: 600, color: '#1A2332' }}>{from_crew ?? 'Officer on Watch'}</div>
                <div style={{ fontSize: 10, color: '#8896A6' }}>{from_role ?? department ?? ''}</div>
              </div>
              <div>
                <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: '0.05em', textTransform: 'uppercase', color: '#5AABCC', marginBottom: 20 }}>
                  Reviewed By
                </div>
                <div style={{ height: 48, borderBottom: '1px solid #D8DEE4', marginBottom: 8 }} />
                <div style={{ fontSize: 12, fontWeight: 600, color: '#1A2332' }}>{to_crew ?? 'Pending — Head of Department'}</div>
                <div style={{ fontSize: 10, color: '#8896A6' }}>{to_role ?? ''}</div>
              </div>
            </div>

            {/* ── Footer ── */}
            <div style={{
              padding: '16px 48px',
              borderTop: '1px solid #E8EDF1',
              textAlign: 'center',
              background: '#F7F9FA',
            }}>
              <div style={{ fontSize: 9, fontWeight: 500, letterSpacing: '0.06em', textTransform: 'uppercase', color: '#8896A6' }}>
                Confidential — Technical Handover Document
              </div>
              <div style={{ fontSize: 9, color: '#8896A6', marginTop: 4 }}>
                {secs.length} sections · {totalItems} items · Celeste Handover System
              </div>
            </div>
          </div>
        );
      })()}

      {/* Embedded Entity Links */}
      {entityLinks.length > 0 && (
        <ScrollReveal>
          <DocRowsSection title="Referenced Entities" docs={entityLinks} defaultCollapsed />
        </ScrollReveal>
      )}

      {/* Signatures */}
      {signatureItems.length > 0 && (
        <ScrollReveal>
          <KVSection
            title="Signatures"
            items={signatureItems}
            defaultCollapsed
            icon={
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M8 14s5-2.5 5-6.25V3.125L8 1.5 3 3.125V7.75C3 11.5 8 14 8 14z" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            }
          />
        </ScrollReveal>
      )}

      {/* Notes */}
      <ScrollReveal>
        <NotesSection
          notes={noteItems}
          canAddNote
          onAddNote={() => {
            const addAction = getAction('add_to_handover');
            if (addAction) {
              openActionPopup({
                ...addAction,
                prefill: { ...addAction.prefill, entity_type: 'note' },
              });
            }
          }}
        />
      </ScrollReveal>

      {/* Attachments */}
      <ScrollReveal>
        <AttachmentsSection
          attachments={attachmentItems}
          onAddFile={() => {}}
          canAddFile
        />
      </ScrollReveal>

      {/* History */}
      <ScrollReveal><HistorySection periods={historyPeriods} defaultCollapsed /></ScrollReveal>

      {/* Audit Trail */}
      <ScrollReveal><AuditTrailSection events={auditEvents} defaultCollapsed /></ScrollReveal>

      {/* Report Footer */}
      <div className={styles.reportFooter}>
        Generated by Celeste PMS{department ? ` · ${department} Department` : ''}{vessel_name ? ` · ${vessel_name}` : ''}
      </div>

      {actionPopupConfig && (
        <ActionPopup mode="mutate" title={actionPopupConfig.title} fields={actionPopupConfig.fields}
          signatureLevel={0}
          onSubmit={async (values) => { await executeAction(actionPopupConfig.actionId, values); setActionPopupConfig(null); }}
          onClose={() => setActionPopupConfig(null)} />
      )}

      {/* Wet Signature Modal — no PIN */}
      {showSignModal && (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 9999,
          background: 'rgba(0,0,0,0.6)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }} onClick={() => setShowSignModal(false)}>
          <div style={{
            background: '#fff', borderRadius: 8, padding: 32, width: 480,
            boxShadow: '0 8px 32px rgba(0,0,0,0.2)',
          }} onClick={(e) => e.stopPropagation()}>
            <div style={{ fontSize: 16, fontWeight: 600, color: '#1A2332', marginBottom: 4 }}>
              Sign Handover
            </div>
            <div style={{ fontSize: 12, color: '#8896A6', marginBottom: 20 }}>
              Draw your signature below to confirm and submit this handover.
            </div>
            <canvas
              ref={signCanvasRef}
              width={416}
              height={160}
              style={{
                border: '1px solid #D8DEE4',
                borderRadius: 4,
                cursor: 'crosshair',
                display: 'block',
                marginBottom: 16,
                background: '#FAFBFC',
              }}
              onMouseDown={(e) => {
                setIsDrawing(true);
                const ctx = signCanvasRef.current?.getContext('2d');
                if (ctx) {
                  const rect = signCanvasRef.current!.getBoundingClientRect();
                  ctx.beginPath();
                  ctx.moveTo(e.clientX - rect.left, e.clientY - rect.top);
                }
              }}
              onMouseMove={(e) => {
                if (!isDrawing) return;
                const ctx = signCanvasRef.current?.getContext('2d');
                if (ctx) {
                  const rect = signCanvasRef.current!.getBoundingClientRect();
                  ctx.lineWidth = 2;
                  ctx.lineCap = 'round';
                  ctx.strokeStyle = '#1A2332';
                  ctx.lineTo(e.clientX - rect.left, e.clientY - rect.top);
                  ctx.stroke();
                }
              }}
              onMouseUp={() => setIsDrawing(false)}
              onMouseLeave={() => setIsDrawing(false)}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
              <button
                onClick={() => {
                  const ctx = signCanvasRef.current?.getContext('2d');
                  if (ctx) ctx.clearRect(0, 0, 416, 160);
                }}
                style={{
                  padding: '8px 16px', fontSize: 12, borderRadius: 4,
                  border: '1px solid #D8DEE4', background: '#fff', color: '#4A5568',
                  cursor: 'pointer',
                }}
              >
                Clear
              </button>
              <div style={{ display: 'flex', gap: 8 }}>
                <button
                  onClick={() => setShowSignModal(false)}
                  style={{
                    padding: '8px 16px', fontSize: 12, borderRadius: 4,
                    border: '1px solid #D8DEE4', background: '#fff', color: '#4A5568',
                    cursor: 'pointer',
                  }}
                >
                  Cancel
                </button>
                <button
                  onClick={handleSignConfirm}
                  style={{
                    padding: '8px 20px', fontSize: 12, fontWeight: 600, borderRadius: 4,
                    border: 'none', background: '#5AABCC', color: '#fff',
                    cursor: 'pointer',
                  }}
                >
                  Confirm &amp; Sign
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
