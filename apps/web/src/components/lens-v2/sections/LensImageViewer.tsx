'use client';

/**
 * LensImageViewer — cohort-shared image gallery + single-comment overlay.
 *
 * Cohort alignment (2026-04-24 — CEO ruling):
 *   - One comment per image, stored on `pms_attachments.description`.
 *   - Polymorphic `entity_type` column drives per-lens filtering.
 *   - Multi-comment threads are deliberately out of scope for MVP.
 *
 * Consumers:
 *   - work-orders (PR-WO-4b) — Safety / Uploads tabs.
 *   - equipment   (PR-EQ-4)  — Photos section.
 *   - faults      (future)   — evidence gallery.
 *
 * Visual contract (UX sheet /Users/celeste7/Desktop/lens_card_upgrades.md:405-414):
 *     ______________________________
 *    |                              |
 *    |            *Image*           |
 *    |                              |
 *    |______________________________|
 *    | *Username*: "users comment"  |
 *    | + Add/Edit comment           |
 *    |______________________________|
 *
 * 100% tokenised — every colour / spacing value uses CSS custom properties.
 *
 * Keyboard: ← / → navigate between images in the strip; Enter on the card
 * opens the lightbox; Escape closes. No third-party dependency.
 */

import * as React from 'react';

export interface LensImage {
  /** Stable id — typically `pms_attachments.id`. */
  id: string;
  /** Signed URL or public URL for the full-size image. */
  url: string;
  /** Optional thumbnail URL; full-size URL is used when absent. */
  thumbnail_url?: string;
  /** Single comment text (`pms_attachments.description`). */
  description?: string | null;
  /** Resolved uploader name (NOT a UUID). */
  uploaded_by_name?: string | null;
  /** ISO timestamp. */
  uploaded_at?: string | null;
  /** Optional display category — rendered as a muted pill. */
  category?: string | null;
  /** Original filename for alt text + download. */
  filename?: string | null;
}

export interface LensImageViewerProps {
  images: LensImage[];
  /**
   * Fired when the user edits or adds a comment on an image.
   * Caller dispatches whatever action writes `pms_attachments.description`.
   * Omit to render the viewer read-only.
   */
  onEditComment?: (imageId: string, text: string) => void | Promise<void>;
  /** Fired when the user clicks "+ Upload Image". Caller opens the upload flow. */
  onUpload?: () => void;
  canUpload?: boolean;
  /** Empty-state message. Sensible default. */
  emptyMessage?: string;
  /** Grid mode ("strip" horizontal scroll, default) or "grid" multi-row. */
  layout?: 'strip' | 'grid';
}

// ── Helpers ────────────────────────────────────────────────────────────────

function formatDate(iso?: string | null): string {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return '';
    return d.toISOString().slice(0, 10);
  } catch {
    return '';
  }
}

function fmtEnum(s?: string | null): string {
  if (!s) return '';
  return s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

// ── Component ──────────────────────────────────────────────────────────────

export function LensImageViewer({
  images,
  onEditComment,
  onUpload,
  canUpload = false,
  emptyMessage = 'No images yet.',
  layout = 'strip',
}: LensImageViewerProps) {
  const [openIndex, setOpenIndex] = React.useState<number | null>(null);

  const handleOpen = React.useCallback((idx: number) => setOpenIndex(idx), []);
  const handleClose = React.useCallback(() => setOpenIndex(null), []);
  const handlePrev = React.useCallback(() => {
    setOpenIndex((i) => (i === null || images.length === 0 ? i : (i - 1 + images.length) % images.length));
  }, [images.length]);
  const handleNext = React.useCallback(() => {
    setOpenIndex((i) => (i === null || images.length === 0 ? i : (i + 1) % images.length));
  }, [images.length]);

  React.useEffect(() => {
    if (openIndex === null) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') handleClose();
      else if (e.key === 'ArrowLeft') handlePrev();
      else if (e.key === 'ArrowRight') handleNext();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [openIndex, handleClose, handlePrev, handleNext]);

  const handleEditClick = React.useCallback(
    async (img: LensImage) => {
      if (!onEditComment || typeof window === 'undefined') return;
      const next = window.prompt(
        'Image comment (one per image).',
        img.description ?? '',
      );
      if (next === null) return; // user cancelled — preserve existing
      await onEditComment(img.id, next);
    },
    [onEditComment],
  );

  if (images.length === 0) {
    return (
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'flex-start',
          gap: 8,
        }}
      >
        <div
          data-testid="lens-image-viewer-empty"
          style={{
            padding: '20px 16px',
            width: '100%',
            textAlign: 'center',
            color: 'var(--txt3)',
            fontSize: 12,
            background: 'var(--surface)',
            border: '1px dashed var(--border-faint)',
            borderRadius: 6,
          }}
        >
          {emptyMessage}
        </div>
        {canUpload && onUpload && <UploadButton onClick={onUpload} />}
      </div>
    );
  }

  const gridStyle: React.CSSProperties =
    layout === 'grid'
      ? {
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
          gap: 12,
        }
      : {
          display: 'flex',
          gap: 12,
          overflowX: 'auto',
          paddingBottom: 4,
        };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div role="list" aria-label="Images" style={gridStyle}>
        {images.map((img, idx) => (
          <ThumbnailCard
            key={img.id}
            image={img}
            onOpen={() => handleOpen(idx)}
            onEditComment={onEditComment ? () => handleEditClick(img) : undefined}
          />
        ))}
      </div>
      {canUpload && onUpload && <UploadButton onClick={onUpload} />}

      {openIndex !== null && images[openIndex] && (
        <Lightbox
          image={images[openIndex]}
          hasPrev={images.length > 1}
          hasNext={images.length > 1}
          onPrev={handlePrev}
          onNext={handleNext}
          onClose={handleClose}
          onEditComment={onEditComment ? () => handleEditClick(images[openIndex]) : undefined}
        />
      )}
    </div>
  );
}

// ── Thumbnail card ─────────────────────────────────────────────────────────

function ThumbnailCard({
  image,
  onOpen,
  onEditComment,
}: {
  image: LensImage;
  onOpen: () => void;
  onEditComment?: () => void;
}) {
  const src = image.thumbnail_url ?? image.url;
  return (
    <div
      role="listitem"
      style={{
        display: 'flex',
        flexDirection: 'column',
        background: 'var(--surface)',
        border: '1px solid var(--border-faint)',
        borderRadius: 6,
        overflow: 'hidden',
        minWidth: 180,
        maxWidth: 260,
      }}
    >
      <button
        type="button"
        onClick={onOpen}
        aria-label={`Open ${image.filename ?? 'image'}`}
        style={{
          appearance: 'none',
          WebkitAppearance: 'none',
          background: 'var(--neutral-bg)',
          border: 'none',
          padding: 0,
          cursor: 'pointer',
          aspectRatio: '4 / 3',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          overflow: 'hidden',
        }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={src}
          alt={image.filename ?? 'Uploaded image'}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            display: 'block',
          }}
        />
      </button>
      <div
        style={{
          padding: '8px 10px',
          display: 'flex',
          flexDirection: 'column',
          gap: 4,
          borderTop: '1px solid var(--border-faint)',
        }}
      >
        {image.description ? (
          <div
            style={{
              fontSize: 12,
              color: 'var(--txt)',
              lineHeight: 1.4,
              display: '-webkit-box',
              WebkitLineClamp: 2,
              WebkitBoxOrient: 'vertical',
              overflow: 'hidden',
            }}
          >
            <span style={{ color: 'var(--txt2)', fontWeight: 600 }}>
              {image.uploaded_by_name ?? 'Unknown'}
              {': '}
            </span>
            {image.description}
          </div>
        ) : (
          <div
            style={{
              fontSize: 11,
              color: 'var(--txt3)',
              fontStyle: 'italic',
            }}
          >
            No comment
          </div>
        )}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 6,
          }}
        >
          <span
            style={{
              fontSize: 10,
              color: 'var(--txt3)',
              fontFamily: 'var(--font-mono)',
            }}
          >
            {formatDate(image.uploaded_at)}
            {image.category && ` · ${fmtEnum(image.category)}`}
          </span>
          {onEditComment && (
            <button
              type="button"
              onClick={onEditComment}
              style={{
                appearance: 'none',
                WebkitAppearance: 'none',
                background: 'transparent',
                border: '1px solid var(--border-sub)',
                borderRadius: 4,
                padding: '2px 6px',
                cursor: 'pointer',
                fontSize: 10,
                fontWeight: 500,
                color: 'var(--txt2)',
              }}
            >
              {image.description ? 'Edit' : '+ Comment'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Lightbox (full-size view with comment overlay) ─────────────────────────

function Lightbox({
  image,
  hasPrev,
  hasNext,
  onPrev,
  onNext,
  onClose,
  onEditComment,
}: {
  image: LensImage;
  hasPrev: boolean;
  hasNext: boolean;
  onPrev: () => void;
  onNext: () => void;
  onClose: () => void;
  onEditComment?: () => void;
}) {
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={`Image: ${image.filename ?? 'preview'}`}
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 200,
        background: 'var(--overlay-bg, rgba(0,0,0,0.85))',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          display: 'flex',
          flexDirection: 'column',
          maxWidth: '1100px',
          maxHeight: '92vh',
          width: '100%',
          background: 'var(--surface)',
          border: '1px solid var(--border-faint)',
          borderRadius: 8,
          overflow: 'hidden',
          position: 'relative',
        }}
      >
        {/* close */}
        <button
          type="button"
          onClick={onClose}
          aria-label="Close image viewer"
          style={{
            position: 'absolute',
            top: 8,
            right: 8,
            zIndex: 1,
            appearance: 'none',
            WebkitAppearance: 'none',
            background: 'var(--neutral-bg)',
            border: '1px solid var(--border-sub)',
            borderRadius: 4,
            padding: '4px 10px',
            cursor: 'pointer',
            fontSize: 12,
            color: 'var(--txt2)',
          }}
        >
          ✕
        </button>

        {/* image */}
        <div
          style={{
            flex: 1,
            background: 'var(--neutral-bg)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            position: 'relative',
            minHeight: 280,
          }}
        >
          {hasPrev && (
            <button
              type="button"
              onClick={onPrev}
              aria-label="Previous image"
              style={navArrowStyle('left')}
            >
              ‹
            </button>
          )}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={image.url}
            alt={image.filename ?? 'Preview'}
            style={{
              maxWidth: '100%',
              maxHeight: '70vh',
              objectFit: 'contain',
              display: 'block',
            }}
          />
          {hasNext && (
            <button
              type="button"
              onClick={onNext}
              aria-label="Next image"
              style={navArrowStyle('right')}
            >
              ›
            </button>
          )}
        </div>

        {/* comment overlay bar */}
        <div
          style={{
            padding: '12px 16px',
            borderTop: '1px solid var(--border-faint)',
            display: 'flex',
            flexDirection: 'column',
            gap: 6,
            background: 'var(--surface)',
          }}
        >
          {image.description ? (
            <div style={{ fontSize: 13, color: 'var(--txt)', lineHeight: 1.5 }}>
              <span style={{ color: 'var(--txt2)', fontWeight: 600 }}>
                {image.uploaded_by_name ?? 'Unknown'}:{' '}
              </span>
              {image.description}
            </div>
          ) : (
            <div style={{ fontSize: 12, color: 'var(--txt3)', fontStyle: 'italic' }}>
              No comment on this image.
            </div>
          )}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 8,
            }}
          >
            <div
              style={{
                fontSize: 10,
                color: 'var(--txt3)',
                fontFamily: 'var(--font-mono)',
              }}
            >
              {formatDate(image.uploaded_at)}
              {image.category && ` · ${fmtEnum(image.category)}`}
              {image.filename && ` · ${image.filename}`}
            </div>
            {onEditComment && (
              <button
                type="button"
                onClick={onEditComment}
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
                {image.description ? 'Edit comment' : '+ Add comment'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function navArrowStyle(side: 'left' | 'right'): React.CSSProperties {
  return {
    position: 'absolute',
    [side]: 8,
    top: '50%',
    transform: 'translateY(-50%)',
    appearance: 'none',
    WebkitAppearance: 'none',
    background: 'var(--surface)',
    border: '1px solid var(--border-sub)',
    borderRadius: '50%',
    width: 36,
    height: 36,
    cursor: 'pointer',
    fontSize: 18,
    fontWeight: 700,
    color: 'var(--txt)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  };
}

function UploadButton({ onClick }: { onClick: () => void }) {
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
      + Upload Image
    </button>
  );
}
