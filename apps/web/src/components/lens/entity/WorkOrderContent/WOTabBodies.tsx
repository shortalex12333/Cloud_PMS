'use client';

import * as React from 'react';

// ── Tab body helpers ───────────────────────────────────────────────────────

export function EmptyTab({ message }: { message: string }) {
  return (
    <div
      style={{
        padding: '24px 16px',
        textAlign: 'center',
        color: 'var(--txt3)',
        fontSize: 13,
      }}
    >
      {message}
    </div>
  );
}

export interface FaultRow {
  id: string;
  fault_code?: string;
  title?: string;
  status?: string;
  severity?: string;
}

export function FaultsTabBody({
  faults,
  onOpen,
}: {
  faults: Array<Record<string, unknown>>;
  onOpen: (faultId: string) => void;
}) {
  const rows: FaultRow[] = faults.map((f, i) => ({
    id: (f.id as string) ?? `fault-${i}`,
    fault_code: (f.fault_code ?? f.code) as string | undefined,
    title: (f.title ?? f.description) as string | undefined,
    status: f.status as string | undefined,
    severity: f.severity as string | undefined,
  }));
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {rows.map((r) => (
        <button
          key={r.id}
          type="button"
          onClick={() => onOpen(r.id)}
          style={{
            appearance: 'none',
            WebkitAppearance: 'none',
            textAlign: 'left',
            background: 'var(--surface)',
            border: '1px solid var(--border-faint)',
            borderRadius: 6,
            padding: '10px 12px',
            cursor: 'pointer',
            color: 'var(--txt)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12 }}>
            {r.fault_code && (
              <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--txt2)' }}>
                {r.fault_code}
              </span>
            )}
            <span style={{ fontWeight: 600 }}>{r.title ?? 'Fault'}</span>
          </div>
          {(r.status || r.severity) && (
            <div style={{ marginTop: 4, fontSize: 11, color: 'var(--txt3)' }}>
              {[r.severity, r.status].filter(Boolean).join(' · ')}
            </div>
          )}
        </button>
      ))}
    </div>
  );
}

export function EquipmentTabBody({
  equipmentId: _equipmentId,
  equipmentName,
  equipmentCode,
  onOpen,
}: {
  equipmentId: string;
  equipmentName: string;
  equipmentCode?: string;
  onOpen: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onOpen}
      style={{
        appearance: 'none',
        WebkitAppearance: 'none',
        textAlign: 'left',
        background: 'var(--surface)',
        border: '1px solid var(--border-faint)',
        borderRadius: 6,
        padding: '12px 14px',
        cursor: 'pointer',
        color: 'var(--txt)',
        width: '100%',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13 }}>
        {equipmentCode && (
          <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--txt2)' }}>
            {equipmentCode}
          </span>
        )}
        <span style={{ fontWeight: 600 }}>{equipmentName}</span>
      </div>
      <div style={{ marginTop: 4, fontSize: 11, color: 'var(--txt3)' }}>
        Open equipment lens →
      </div>
    </button>
  );
}

// ── PR-WO-4 Safety tab helpers ─────────────────────────────────────────────

export function AddCheckpointButton({
  onClick,
  label,
}: {
  onClick: () => void;
  label: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        appearance: 'none',
        WebkitAppearance: 'none',
        alignSelf: 'flex-start',
        background: 'var(--neutral-bg)',
        border: '1px dashed var(--border-sub)',
        borderRadius: 6,
        padding: '8px 12px',
        cursor: 'pointer',
        color: 'var(--txt2)',
        fontSize: 12,
        fontWeight: 500,
      }}
    >
      {label}
    </button>
  );
}

export interface SafetyRow {
  id: string;
  title?: string;
  description?: string;
  instructions?: string;
  is_completed?: boolean;
  completed_by?: string;
  completed_at?: string;
  category?: string;
}

export function SafetyTabBody({
  sopText,
  sopDocumentId,
  safetyItems,
  onSubmit,
  onAddCheckpoint,
  onEditSOP,
  onOpenSOPDoc,
}: {
  sopText?: string;
  sopDocumentId?: string;
  safetyItems: Array<Record<string, unknown>>;
  onSubmit: (items: { checklist_item_id: string; actual_value?: string }[]) => Promise<void>;
  onAddCheckpoint: () => void;
  onEditSOP: () => void;
  onOpenSOPDoc?: () => void;
}) {
  const rows: SafetyRow[] = safetyItems.map((i) => ({
    id: (i.id as string) ?? '',
    title: (i.title as string) ?? (i.description as string),
    description: i.description as string | undefined,
    instructions: i.instructions as string | undefined,
    is_completed: Boolean(i.is_completed ?? i.completed),
    completed_by: (i.completed_by_name ?? i.completed_by) as string | undefined,
    completed_at: i.completed_at as string | undefined,
    category: (i.category as string) ?? 'safety',
  }));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* SOP block */}
      <section
        style={{
          background: 'var(--surface)',
          border: '1px solid var(--border-faint)',
          borderRadius: 8,
          padding: '14px 16px',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: 8,
          }}
        >
          <div
            style={{
              fontSize: 11,
              fontWeight: 600,
              letterSpacing: '0.06em',
              textTransform: 'uppercase',
              color: 'var(--txt2)',
            }}
          >
            Standard Operating Procedure
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            {sopDocumentId && onOpenSOPDoc && (
              <button
                type="button"
                onClick={onOpenSOPDoc}
                style={{
                  appearance: 'none',
                  WebkitAppearance: 'none',
                  background: 'var(--teal-bg)',
                  color: 'var(--mark)',
                  border: '1px solid var(--mark-hover)',
                  borderRadius: 4,
                  padding: '4px 10px',
                  cursor: 'pointer',
                  fontSize: 11,
                  fontWeight: 600,
                }}
              >
                Open SOP PDF
              </button>
            )}
            <button
              type="button"
              onClick={onEditSOP}
              style={{
                appearance: 'none',
                WebkitAppearance: 'none',
                background: 'transparent',
                border: '1px solid var(--border-sub)',
                borderRadius: 4,
                padding: '4px 10px',
                cursor: 'pointer',
                fontSize: 11,
                fontWeight: 500,
                color: 'var(--txt2)',
              }}
            >
              {sopText ? 'Edit' : 'Add SOP'}
            </button>
          </div>
        </div>
        {sopText ? (
          <div
            style={{
              fontSize: 13,
              lineHeight: 1.55,
              color: 'var(--txt)',
              whiteSpace: 'pre-wrap',
            }}
          >
            {sopText}
          </div>
        ) : (
          <div style={{ fontSize: 12, color: 'var(--txt3)', fontStyle: 'italic' }}>
            No SOP recorded. Click &quot;Add SOP&quot; to type one, or attach a PDF via the
            Documents tab then link it here.
          </div>
        )}
      </section>

      {/* Safety checklist block */}
      <section>
        <div
          style={{
            fontSize: 11,
            fontWeight: 600,
            letterSpacing: '0.06em',
            textTransform: 'uppercase',
            color: 'var(--txt2)',
            marginBottom: 8,
          }}
        >
          Safety Checklist &amp; Lock-Out-Tag-Out
        </div>
        {rows.length === 0 ? (
          <div
            style={{
              fontSize: 12,
              color: 'var(--txt3)',
              fontStyle: 'italic',
              marginBottom: 8,
            }}
          >
            No safety checkpoints yet. Add LOTO / isolation / test-for-dead steps
            below so the executor cannot complete the work order until each is
            ticked.
          </div>
        ) : (
          <div
            style={{ display: 'flex', flexDirection: 'column', gap: 6 }}
            data-testid="safety-checklist-list"
          >
            {rows.map((r) => (
              <button
                key={r.id}
                type="button"
                onClick={!r.is_completed ? () => onSubmit([{ checklist_item_id: r.id }]) : undefined}
                disabled={r.is_completed}
                style={{
                  appearance: 'none',
                  WebkitAppearance: 'none',
                  textAlign: 'left',
                  background: r.is_completed
                    ? 'var(--green-bg)'
                    : 'var(--surface)',
                  border: `1px solid ${
                    r.is_completed ? 'var(--green-border)' : 'var(--border-faint)'
                  }`,
                  borderRadius: 6,
                  padding: '10px 12px',
                  cursor: r.is_completed ? 'default' : 'pointer',
                  color: 'var(--txt)',
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: 10,
                }}
              >
                <span
                  aria-hidden="true"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    width: 18,
                    height: 18,
                    borderRadius: 3,
                    border: `1.5px solid ${
                      r.is_completed ? 'var(--green)' : 'var(--border-sub)'
                    }`,
                    background: r.is_completed ? 'var(--green)' : 'transparent',
                    color: 'white',
                    fontSize: 11,
                    fontWeight: 700,
                    flexShrink: 0,
                    marginTop: 1,
                  }}
                >
                  {r.is_completed ? '✓' : ''}
                </span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div
                    style={{
                      fontSize: 13,
                      fontWeight: 500,
                      color: r.is_completed ? 'var(--txt2)' : 'var(--txt)',
                      textDecoration: r.is_completed ? 'line-through' : undefined,
                    }}
                  >
                    {r.title ?? 'Safety step'}
                  </div>
                  {r.description && (
                    <div
                      style={{
                        fontSize: 11,
                        color: 'var(--txt3)',
                        marginTop: 2,
                      }}
                    >
                      {r.description}
                    </div>
                  )}
                  {r.is_completed && r.completed_by && (
                    <div
                      style={{
                        fontSize: 10,
                        color: 'var(--txt3)',
                        marginTop: 4,
                      }}
                    >
                      Completed by {r.completed_by}
                      {r.completed_at && ` · ${String(r.completed_at).slice(0, 10)}`}
                    </div>
                  )}
                </div>
              </button>
            ))}
          </div>
        )}
        <div style={{ marginTop: 8 }}>
          <AddCheckpointButton
            onClick={onAddCheckpoint}
            label="+ Add Safety Checkpoint"
          />
        </div>
      </section>
    </div>
  );
}
