'use client';

/**
 * LensFileViewer — hero file viewer for lens cards that embed a stored document.
 *
 * Used by both Certificate lens and Document lens. Per doc_cert_ux_change.md,
 * the rendered file is the PRIMARY focus of the card — metadata is subsidiary.
 *
 * Renders:
 *   - PDF via <iframe> (browser plugin handles scroll/zoom/print)
 *   - image via <img> (clamp aspect, fit inside)
 *   - other types fall back to a "Download / Open" prompt
 *
 * Props are deliberately thin: caller fetches the signed URL upstream and passes
 * it in. Component does not do network I/O; this keeps loading/error state local
 * to the caller and testable.
 */

import * as React from 'react';

export interface LensFileViewerProps {
  /** Signed URL to the rendered file (blob: or https:). Null during load. */
  url: string | null;
  /** Filename for accessibility labels and download fallback. */
  filename?: string;
  /**
   * MIME type. `application/pdf` -> iframe. `image/*` -> img. Anything else ->
   * fallback download card. Passing undefined falls back.
   */
  mimeType?: string;
  /** True while the caller is fetching the signed URL. */
  isLoading?: boolean;
  /** Error string if the caller's fetch failed. */
  error?: string | null;
  /**
   * When present, shows an "Open in new tab" affordance. Most callers bind this
   * to `window.open(url, '_blank')` on click.
   */
  onOpenNewTab?: () => void;
}

const ICON_STYLE: React.CSSProperties = { width: 18, height: 18, flexShrink: 0 };

/** Small spinner SVG drawn via border trick — no extra deps. */
function Spinner() {
  return (
    <div
      aria-hidden
      style={{
        width: 24,
        height: 24,
        borderRadius: '50%',
        border: '2px solid var(--border-sub)',
        borderTopColor: 'var(--brand-interactive)',
        animation: 'lens-viewer-spin 0.8s linear infinite',
      }}
    />
  );
}

export function LensFileViewer({
  url,
  filename,
  mimeType,
  isLoading = false,
  error = null,
  onOpenNewTab,
}: LensFileViewerProps) {
  const isPdf = (mimeType ?? '').toLowerCase() === 'application/pdf';
  const isImage = (mimeType ?? '').toLowerCase().startsWith('image/');
  const label = filename ?? 'Document';

  // ── Shared container styling: tokenised height, border, radius ──
  const containerStyle: React.CSSProperties = {
    width: '100%',
    height: 'var(--lens-doc-viewer-h)',
    minHeight: 320,
    border: '1px solid var(--border-sub)',
    borderRadius: 'var(--radius-md)',
    background: 'var(--surface-elevated)',
    overflow: 'hidden',
    position: 'relative',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  };

  // ── Loading ──
  if (isLoading) {
    return (
      <>
        <style>{`@keyframes lens-viewer-spin { to { transform: rotate(360deg); } }`}</style>
        <div style={containerStyle} aria-busy="true" aria-label={`Loading ${label}`}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, color: 'var(--text-secondary)' }}>
            <Spinner />
            <span style={{ fontSize: 'var(--font-size-body)' }}>Loading {label}…</span>
          </div>
        </div>
      </>
    );
  }

  // ── Error ──
  if (error) {
    return (
      <div style={containerStyle} role="alert">
        <div style={{ textAlign: 'center', padding: 'var(--space-6)' }}>
          <div style={{ fontSize: 'var(--font-size-body)', color: 'var(--status-critical)', marginBottom: 8 }}>
            Could not load file
          </div>
          <div style={{ fontSize: 'var(--font-size-caption)', color: 'var(--text-tertiary)' }}>{error}</div>
        </div>
      </div>
    );
  }

  // ── No URL yet (before load fired) ──
  if (!url) {
    return (
      <div style={containerStyle}>
        <div style={{ color: 'var(--text-tertiary)', fontSize: 'var(--font-size-caption)' }}>No file loaded</div>
      </div>
    );
  }

  // ── PDF ──
  if (isPdf) {
    return (
      <div style={containerStyle}>
        <iframe
          src={url}
          title={label}
          style={{ width: '100%', height: '100%', border: 0, display: 'block' }}
        />
        {onOpenNewTab && (
          <button
            type="button"
            onClick={onOpenNewTab}
            className="btn-ghost"
            style={{
              position: 'absolute',
              top: 12,
              right: 12,
              background: 'var(--surface-base)',
              border: '1px solid var(--border-sub)',
            }}
            aria-label="Open file in new tab"
          >
            Open in new tab
          </button>
        )}
      </div>
    );
  }

  // ── Image ──
  if (isImage) {
    return (
      <div style={{ ...containerStyle, padding: 'var(--space-4)' }}>
        <img
          src={url}
          alt={label}
          style={{
            maxWidth: '100%',
            maxHeight: '100%',
            objectFit: 'contain',
            display: 'block',
          }}
        />
      </div>
    );
  }

  // ── Fallback: unknown/other MIME — download CTA ──
  return (
    <div style={containerStyle}>
      <div style={{ textAlign: 'center', padding: 'var(--space-6)' }}>
        <svg viewBox="0 0 24 24" fill="none" style={{ ...ICON_STYLE, width: 48, height: 48, margin: '0 auto 12px', color: 'var(--text-tertiary)' }}>
          <path
            d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z M14 3v6h6"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinejoin="round"
            fill="none"
          />
        </svg>
        <div style={{ fontSize: 'var(--font-size-body)', color: 'var(--text-primary)', marginBottom: 4 }}>
          {label}
        </div>
        <div style={{ fontSize: 'var(--font-size-caption)', color: 'var(--text-tertiary)', marginBottom: 16 }}>
          Inline preview not available for this file type.
        </div>
        {onOpenNewTab && (
          <button type="button" onClick={onOpenNewTab} className="btn-secondary">
            Open in new tab
          </button>
        )}
      </div>
    </div>
  );
}
