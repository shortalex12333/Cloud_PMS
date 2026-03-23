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

  // Section data
  const signatures = ((entity?.signatures ?? payload.signatures) as Array<Record<string, unknown>> | undefined) ?? [];
  const embedded_entities = ((entity?.embedded_entities ?? payload.embedded_entities ?? entity?.entity_links ?? payload.entity_links) as Array<Record<string, unknown>> | undefined) ?? [];
  const notes = ((entity?.notes ?? payload.notes) as Array<Record<string, unknown>> | undefined) ?? [];
  const attachments = ((entity?.attachments ?? payload.attachments) as Array<Record<string, unknown>> | undefined) ?? [];
  const summary_stats = (entity?.summary_stats ?? payload.summary_stats) as Record<string, unknown> | undefined;

  // ── Action gates ──
  // Owner correction: view-only document. Only sign + read-only actions (Export/Print).
  const signAction = getAction('sign_handover');

  const BACKEND_AUTO = new Set(['yacht_id', 'signature', 'idempotency_key']);
  const [actionPopupConfig, setActionPopupConfig] = React.useState<{
    actionId: string; title: string; fields: ActionPopupField[]; signatureLevel: 0|1|2|3|4|5;
  } | null>(null);

  function openActionPopup(action: { action_id: string; label: string; required_fields: string[]; prefill: Record<string, unknown>; requires_signature: boolean }) {
    const fields: ActionPopupField[] = action.required_fields
      .filter(f => !BACKEND_AUTO.has(f) && !(f in action.prefill))
      .map(f => ({ name: f, label: f.replace(/_/g, ' '), type: 'kv-edit' as const, placeholder: `Enter ${f.replace(/_/g, ' ')}...`, value: (action.prefill[f] as string) ?? '' }));
    const sigLevel = (action as any).signature_level ?? (action.requires_signature ? 3 : 0);
    setActionPopupConfig({ actionId: action.action_id, title: action.label, fields, signatureLevel: sigLevel });
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

  const handlePrimary = React.useCallback(async () => {
    await executeAction('sign_handover');
  }, [executeAction]);

  const SPECIAL_HANDLERS: Record<string, () => void> = {};
  const DANGER_ACTIONS = new Set(['archive_handover', 'delete_handover']);
  const primaryActionId = 'sign_handover';

  // Dynamic items from backend
  const dynamicItems: DropdownItem[] = availableActions
    .filter((a) => a.action_id !== primaryActionId)
    .map((a) => ({
      label: a.label,
      onClick: SPECIAL_HANDLERS[a.action_id]
        ? SPECIAL_HANDLERS[a.action_id]
        : () => {
            const hasFields = a.required_fields.some((f) => !BACKEND_AUTO.has(f) && !(f in a.prefill));
            if (hasFields || a.requires_signature) { openActionPopup(a); } else { executeAction(a.action_id); }
          },
      disabled: a.disabled,
      disabledReason: a.disabled_reason ?? undefined,
      danger: DANGER_ACTIONS.has(a.action_id),
    }));

  // Client-side items + dynamic items
  const dropdownItems: DropdownItem[] = [
    {
      label: 'Export PDF',
      icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M6 9l6 6 4-8" /><rect x="2" y="2" width="20" height="20" rx="2" /></svg>,
      onClick: () => window.print(),
    },
    {
      label: 'Print',
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

      {/* Rendered Handover Document — the main event */}
      <ScrollReveal>
        <div className={styles.section}>
          <div className={styles.previewArea} style={{ minHeight: 'auto' }}>
            <div className={styles.previewBadge}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
              Handover Report
            </div>

            {/* Rendered handover document */}
            <div style={{
              width: '100%', maxWidth: 560,
              background: 'var(--surface-base)',
              border: '1px solid var(--border-sub)',
              borderRadius: 4,
              padding: '40px 36px',
              display: 'flex', flexDirection: 'column', gap: 0,
              userSelect: 'text',
            }}>
              {/* Document header */}
              <div style={{
                textAlign: 'center', paddingBottom: 20,
                borderBottom: '2px solid var(--border-sub)',
                marginBottom: 24,
              }}>
                <div style={{
                  fontSize: 16, fontWeight: 700,
                  color: 'var(--txt)', letterSpacing: '-0.01em',
                  marginBottom: 4,
                }}>
                  {vessel_name ? `${vessel_name} — ` : ''}{title}
                </div>
                {handover_type && (
                  <div style={{
                    fontSize: 11, fontWeight: 500,
                    color: 'var(--txt3)', textTransform: 'uppercase',
                    letterSpacing: '0.06em',
                  }}>
                    {formatLabel(handover_type)}
                  </div>
                )}
                <div className={styles.mono} style={{
                  fontSize: 11, color: 'var(--txt3)', marginTop: 6,
                }}>
                  {rotation_start && rotation_end
                    ? `Handover Period: ${rotation_start} — ${rotation_end}`
                    : handover_number
                  }
                  {created_date && ` · Generated ${created_date}`}
                </div>
              </div>

              {/* Summary stats grid */}
              {(openWOs !== undefined || activeFaults !== undefined || lowStockItems !== undefined) && (
                <div style={{
                  display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)',
                  gap: 10, marginBottom: 28,
                }}>
                  {openWOs !== undefined && (
                    <div style={{
                      background: 'var(--teal-bg)',
                      border: '1px solid rgba(90,171,204,0.15)',
                      borderRadius: 6, padding: '14px 10px', textAlign: 'center',
                    }}>
                      <div className={styles.mono} style={{ fontSize: 24, fontWeight: 600, color: 'var(--mark)', lineHeight: 1.1, marginBottom: 3 }}>
                        {openWOs}
                      </div>
                      <div style={{ fontSize: 9, fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--txt3)' }}>
                        Open Work Orders
                      </div>
                    </div>
                  )}
                  {activeFaults !== undefined && (
                    <div style={{
                      background: 'var(--teal-bg)',
                      border: '1px solid rgba(90,171,204,0.15)',
                      borderRadius: 6, padding: '14px 10px', textAlign: 'center',
                    }}>
                      <div className={styles.mono} style={{ fontSize: 24, fontWeight: 600, color: 'var(--mark)', lineHeight: 1.1, marginBottom: 3 }}>
                        {activeFaults}
                      </div>
                      <div style={{ fontSize: 9, fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--txt3)' }}>
                        Active Faults
                      </div>
                    </div>
                  )}
                  {lowStockItems !== undefined && (
                    <div style={{
                      background: 'var(--teal-bg)',
                      border: '1px solid rgba(90,171,204,0.15)',
                      borderRadius: 6, padding: '14px 10px', textAlign: 'center',
                    }}>
                      <div className={styles.mono} style={{ fontSize: 24, fontWeight: 600, color: 'var(--mark)', lineHeight: 1.1, marginBottom: 3 }}>
                        {lowStockItems}
                      </div>
                      <div style={{ fontSize: 9, fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--txt3)' }}>
                        Low Stock Items
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Handover body content — rendered narrative with entity links */}
              {content && (
                <div style={{
                  fontSize: 13, lineHeight: 1.7, color: 'var(--txt)',
                  whiteSpace: 'pre-line', marginTop: 12,
                }}>
                  {content}
                </div>
              )}

              {/* Document footer */}
              <div style={{
                textAlign: 'center', fontSize: 10, color: 'var(--txt-ghost)',
                marginTop: 28, paddingTop: 16,
                borderTop: '1px solid var(--border-faint)',
              }}>
                Generated by Celeste PMS{department ? ` · ${department} Department` : ''}{vessel_name ? ` · ${vessel_name}` : ''}
              </div>
            </div>
          </div>
        </div>
      </ScrollReveal>

      {/* Embedded Entity Links */}
      {entityLinks.length > 0 && (
        <ScrollReveal>
          <DocRowsSection title="Referenced Entities" docs={entityLinks} />
        </ScrollReveal>
      )}

      {/* Signatures */}
      {signatureItems.length > 0 && (
        <ScrollReveal>
          <KVSection
            title="Signatures"
            items={signatureItems}
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
          signatureLevel={actionPopupConfig.signatureLevel}
          onSubmit={async (values) => { await executeAction(actionPopupConfig.actionId, values); setActionPopupConfig(null); }}
          onClose={() => setActionPopupConfig(null)} />
      )}
    </>
  );
}
