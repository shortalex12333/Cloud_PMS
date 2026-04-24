'use client';

/**
 * ReceivingOfficialDocuments — the "Official Documents" ruled section
 * for the receiving lens. Renders the supplier invoice / packing slip /
 * arrival photos inline as heroes, with a thumbnail strip to swap.
 *
 * Consumes the existing shared `LensFileViewer` (cert / document). Does
 * NOT fork.
 *
 * Canonical section order per `.claude/skills/celeste-design-philosophy`:
 *   Official Documents → Checklist → Notes → History → Attachments → Parts
 * This sits in the first slot. Ruled line + 14px/600/uppercase heading +
 * collapsible body — same pattern as every other lens section.
 *
 * Props are deliberately thin. Parent fetches the signed URLs and passes
 * them through as a list of `OfficialDoc`. No network I/O here.
 */

import * as React from 'react';
import { CollapsibleSection } from '../CollapsibleSection';
import { LensFileViewer } from './LensFileViewer';

// ── Types ──────────────────────────────────────────────────────────────────

export type DocKind = 'invoice' | 'packing_slip' | 'photo' | 'other';

export interface OfficialDoc {
  id: string;
  /** Filename for the download fallback / a11y label. */
  filename: string;
  /** Signed URL from the backend. Null while loading. */
  url: string | null;
  /** MIME type drives renderer choice (PDF vs image vs fallback). */
  mimeType?: string;
  /** Classifier for the thumbnail strip ordering. */
  kind?: DocKind;
  /** Optional short caption shown under the thumb (e.g. supplier note). */
  caption?: string;
}

export interface ReceivingOfficialDocumentsProps {
  docs: OfficialDoc[];
  /** When provided, shows an "Open in new tab" button on the hero. */
  onOpenInNewTab?: (doc: OfficialDoc) => void;
  /** HOD-only "+ Upload" affordance; passed through as section header action. */
  onUpload?: () => void;
}

// ── Section icon (folder + check — formal-documents metaphor) ──────────────

const SECTION_ICON = (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden>
    <path
      d="M1.5 4.5a1 1 0 011-1h3.2l1.3 1.5h6.5a1 1 0 011 1v6a1 1 0 01-1 1h-11a1 1 0 01-1-1v-7.5z"
      stroke="currentColor"
      strokeWidth="1.3"
      strokeLinejoin="round"
    />
    <path d="M6 8.5l1.5 1.5L10.5 7" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

// ── Kind ordering — invoice first, then packing slip, then photos ─────────

const KIND_ORDER: Record<DocKind, number> = {
  invoice: 0,
  packing_slip: 1,
  photo: 2,
  other: 3,
};

function sortDocs(docs: OfficialDoc[]): OfficialDoc[] {
  return [...docs].sort((a, b) => {
    const ao = KIND_ORDER[a.kind ?? 'other'];
    const bo = KIND_ORDER[b.kind ?? 'other'];
    if (ao !== bo) return ao - bo;
    return a.filename.localeCompare(b.filename);
  });
}

// ── Thumbnail strip ────────────────────────────────────────────────────────

function ThumbnailStrip({
  docs,
  activeId,
  onPick,
}: {
  docs: OfficialDoc[];
  activeId: string;
  onPick: (id: string) => void;
}) {
  return (
    <div
      role="tablist"
      aria-label="Document thumbnails"
      style={{
        display: 'flex',
        gap: 8,
        padding: '8px 0 12px',
        overflowX: 'auto',
        borderBottom: '1px solid var(--border-faint)',
        marginBottom: 12,
      }}
    >
      {docs.map((d) => {
        const selected = d.id === activeId;
        return (
          <button
            key={d.id}
            role="tab"
            aria-selected={selected}
            onClick={() => onPick(d.id)}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              minHeight: 32,
              padding: '4px 10px',
              borderRadius: 4,
              border: `1px solid ${selected ? 'var(--mark-hover)' : 'var(--border-sub)'}`,
              background: selected ? 'var(--teal-bg)' : 'var(--neutral-bg)',
              color: selected ? 'var(--mark)' : 'var(--txt2)',
              fontSize: 11,
              fontFamily: 'var(--font-sans)',
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              flexShrink: 0,
            }}
          >
            {/* kind chip */}
            <span
              style={{
                fontSize: 9,
                fontWeight: 600,
                letterSpacing: '0.04em',
                textTransform: 'uppercase',
                color: selected ? 'var(--mark)' : 'var(--txt3)',
              }}
            >
              {(d.kind ?? 'other').replace('_', ' ')}
            </span>
            <span
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: 11,
                color: selected ? 'var(--mark)' : 'var(--txt2)',
              }}
            >
              {d.filename}
            </span>
          </button>
        );
      })}
    </div>
  );
}

// ── Component ──────────────────────────────────────────────────────────────

export function ReceivingOfficialDocuments({
  docs,
  onOpenInNewTab,
  onUpload,
}: ReceivingOfficialDocumentsProps) {
  const sorted = React.useMemo(() => sortDocs(docs), [docs]);
  const [activeId, setActiveId] = React.useState<string | null>(sorted[0]?.id ?? null);

  // Keep the active id in sync if the docs list shrinks / changes.
  React.useEffect(() => {
    if (sorted.length === 0) {
      setActiveId(null);
      return;
    }
    if (!sorted.some((d) => d.id === activeId)) {
      setActiveId(sorted[0].id);
    }
  }, [sorted, activeId]);

  const active = sorted.find((d) => d.id === activeId) ?? null;

  return (
    <CollapsibleSection
      id="sec-official-documents"
      title="Official Documents"
      count={docs.length}
      icon={SECTION_ICON}
      action={onUpload ? { label: '+ Upload', onClick: onUpload, testid: 'documents-upload' } : undefined}
    >
      {docs.length === 0 ? (
        <div
          style={{
            fontSize: 13,
            color: 'var(--txt3)',
            padding: '16px 0',
            textAlign: 'center',
          }}
        >
          No packing slip, invoice, or arrival photos uploaded yet.
        </div>
      ) : (
        <>
          {sorted.length > 1 && (
            <ThumbnailStrip docs={sorted} activeId={activeId ?? ''} onPick={setActiveId} />
          )}
          {active && (
            <LensFileViewer
              url={active.url}
              filename={active.filename}
              mimeType={active.mimeType}
              onOpenNewTab={onOpenInNewTab ? () => onOpenInNewTab(active) : undefined}
            />
          )}
          {active?.caption && (
            <div
              style={{
                marginTop: 8,
                fontSize: 12,
                color: 'var(--txt3)',
                fontStyle: 'italic',
              }}
            >
              {active.caption}
            </div>
          )}
        </>
      )}
    </CollapsibleSection>
  );
}
