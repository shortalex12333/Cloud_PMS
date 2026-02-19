'use client';

/**
 * MediaRenderer — Renders images and videos inline.
 *
 * Per UI_SPEC.md:
 * - Images: <img> with object-contain, max-height 240px
 * - Videos: <video> with controls, max-height 240px
 * - Loading skeleton while fetching
 * - Error state if URL fails
 * - Click opens lightbox (full-screen overlay)
 * - Signed URLs: checks for token= param; fetches fresh signed URL if absent
 * - All semantic tokens, zero raw hex values
 */

import * as React from 'react';
import { useState, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { cn } from '@/lib/utils';
import { getFileCategory } from './fileUtils';
import { getAuthHeaders, getYachtId } from '@/lib/authHelpers';

// ============================================================================
// TYPES
// ============================================================================

export interface MediaFile {
  id: string;
  /** Signed URL for display — should include token= param */
  url: string;
  filename: string;
  mime_type: string;
  size_bytes: number;
}

export interface MediaRendererProps {
  file: MediaFile;
  /** Max height in pixels. Default 240. */
  maxHeight?: number;
  className?: string;
}

// ============================================================================
// SIGNED URL FETCHER
// ============================================================================

/**
 * Detect if a URL is already a signed URL (contains auth token).
 * Works for Supabase Storage (token= param) and backend-signed URLs (token=).
 */
function isSignedUrl(url: string): boolean {
  return url.includes('token=');
}

/**
 * Fetch a signed URL from the backend for a file by ID.
 * Uses the same signing endpoint as documentLoader.ts.
 */
async function fetchSignedUrl(fileId: string): Promise<string> {
  const yachtId = await getYachtId();
  if (!yachtId) throw new Error('Yacht context required for signed URL');

  const headers = await getAuthHeaders(yachtId);
  let API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'https://pipeline-core.int.celeste7.ai';
  API_BASE = API_BASE.replace(/\/+$/, '').replace(/\/webhook$/, '');

  const response = await fetch(`${API_BASE}/v1/files/${fileId}/signed-url`, {
    method: 'GET',
    headers,
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch signed URL: ${response.statusText}`);
  }

  const data = await response.json();
  return data.url as string;
}

// ============================================================================
// LOADING SKELETON
// ============================================================================

function MediaSkeleton({ maxHeight }: { maxHeight: number }) {
  return (
    <div
      className={cn(
        'w-full rounded-md animate-pulse',
        'bg-surface-primary'
      )}
      style={{ height: maxHeight }}
      aria-label="Loading media..."
      role="status"
    />
  );
}

// ============================================================================
// ERROR STATE
// ============================================================================

function MediaError({ filename }: { filename: string }) {
  return (
    <div
      className={cn(
        'w-full rounded-md flex flex-col items-center justify-center gap-2',
        'bg-surface-primary border border-surface-border',
        'py-6 px-4'
      )}
      role="alert"
    >
      <span className="text-[20px]" aria-hidden="true">&#9888;&#65039;</span>
      <p className="text-[12px] text-txt-tertiary text-center truncate max-w-full">
        Could not load {filename}
      </p>
    </div>
  );
}

// ============================================================================
// LIGHTBOX (full-screen overlay)
// ============================================================================

interface LightboxProps {
  file: MediaFile;
  resolvedUrl: string;
  onClose: () => void;
}

function Lightbox({ file, resolvedUrl, onClose }: LightboxProps) {
  const category = getFileCategory(file.mime_type);

  const handleBackdropClick = useCallback(
    (e: React.MouseEvent) => {
      if (e.target === e.currentTarget) onClose();
    },
    [onClose]
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    },
    [onClose]
  );

  return (
    <div
      className={cn(
        'fixed inset-0 z-modal',
        'bg-black/90',
        'flex items-center justify-center',
        'p-4'
      )}
      onClick={handleBackdropClick}
      onKeyDown={handleKeyDown}
      role="dialog"
      aria-modal="true"
      aria-label={`Viewing ${file.filename}`}
      tabIndex={-1}
    >
      {/* Close button */}
      <button
        onClick={onClose}
        className={cn(
          'absolute top-4 right-4',
          'flex items-center justify-center',
          'w-8 h-8 rounded-full',
          'bg-surface-primary text-txt-primary',
          'hover:bg-surface-hover transition-colors duration-fast',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-interactive'
        )}
        aria-label="Close lightbox"
      >
        <svg
          className="w-[18px] h-[18px]"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
          aria-hidden="true"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>

      {/* Media content */}
      {category === 'video' ? (
        <video
          src={resolvedUrl}
          controls
          autoPlay
          className="max-w-full max-h-full rounded-md"
          aria-label={file.filename}
        />
      ) : (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={resolvedUrl}
          alt={file.filename}
          className="max-w-full max-h-full rounded-md object-contain"
        />
      )}

      {/* Filename caption */}
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 max-w-[80vw]">
        <p className="text-[12px] text-white/70 text-center truncate bg-black/50 px-3 py-1 rounded-full">
          {file.filename}
        </p>
      </div>
    </div>
  );
}

// ============================================================================
// MEDIA RENDERER
// ============================================================================

/**
 * MediaRenderer — Renders images and videos inline with lightbox support.
 *
 * Signed URL handling: if the provided URL does not contain a token= param,
 * fetches a fresh signed URL from the backend before rendering.
 *
 * Usage:
 * ```tsx
 * <MediaRenderer file={file} maxHeight={240} />
 * ```
 */
export function MediaRenderer({ file, maxHeight = 240, className }: MediaRendererProps) {
  const [mediaLoading, setMediaLoading] = useState(true);
  const [error, setError] = useState(false);
  const [lightboxOpen, setLightboxOpen] = useState(false);

  // Fetch signed URL if the provided URL doesn't include an auth token
  const needsSignedUrl = !isSignedUrl(file.url);
  const { data: freshSignedUrl, isLoading: signedUrlLoading } = useQuery({
    queryKey: ['signed-url', file.id],
    queryFn: () => fetchSignedUrl(file.id),
    // Only fetch if URL isn't already signed
    enabled: needsSignedUrl,
    // Signed URLs expire — refetch after 55 minutes (5 min before 1hr expiry)
    staleTime: 55 * 60 * 1000,
    gcTime: 60 * 60 * 1000,
  });

  // Use fresh signed URL if fetched; fall back to provided URL
  const resolvedUrl = freshSignedUrl ?? file.url;
  const isLoading = signedUrlLoading || (mediaLoading && !!resolvedUrl);

  const category = getFileCategory(file.mime_type);

  const handleLoad = useCallback(() => setMediaLoading(false), []);
  const handleError = useCallback(() => {
    setMediaLoading(false);
    setError(true);
  }, []);

  const handleClick = useCallback(() => {
    if (!error) setLightboxOpen(true);
  }, [error]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleClick();
    }
  }, [handleClick]);

  // Show skeleton while fetching signed URL
  if (signedUrlLoading) {
    return (
      <div className={cn('mb-3 last:mb-0', className)}>
        <MediaSkeleton maxHeight={maxHeight} />
        <p className="mt-1 text-[12px] text-txt-tertiary leading-[1.4] truncate">
          {file.filename}
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className={cn('mb-3 last:mb-0', className)}>
        <MediaError filename={file.filename} />
      </div>
    );
  }

  return (
    <>
      <div className={cn('mb-3 last:mb-0', className)}>
        {/* Loading skeleton — shown while media element is loading */}
        {isLoading && <MediaSkeleton maxHeight={maxHeight} />}

        {/* Media element — hidden until loaded */}
        <div
          className={cn(
            'relative cursor-pointer group',
            isLoading && 'hidden'
          )}
          onClick={handleClick}
          onKeyDown={handleKeyDown}
          role="button"
          tabIndex={0}
          aria-label={`View ${file.filename} fullscreen`}
        >
          {category === 'video' ? (
            <video
              src={resolvedUrl}
              controls
              className={cn(
                'w-full rounded-md object-contain',
                'bg-surface-base'
              )}
              style={{ maxHeight }}
              aria-label={file.filename}
              onLoadedMetadata={handleLoad}
              onError={handleError}
            />
          ) : (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={resolvedUrl}
              alt={file.filename}
              className={cn(
                'w-full rounded-md object-contain',
                'bg-surface-base'
              )}
              style={{ maxHeight }}
              loading="lazy"
              onLoad={handleLoad}
              onError={handleError}
            />
          )}

          {/* Expand overlay hint on hover */}
          <div
            className={cn(
              'absolute inset-0 rounded-md',
              'flex items-center justify-center',
              'opacity-0 group-hover:opacity-100 transition-opacity duration-fast',
              'bg-black/20'
            )}
            aria-hidden="true"
          >
            <svg
              className="w-8 h-8 text-white drop-shadow-lg"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15"
              />
            </svg>
          </div>
        </div>

        {/* Filename caption */}
        <p className="mt-1 text-[12px] text-txt-tertiary leading-[1.4] truncate">
          {file.filename}
        </p>
      </div>

      {/* Lightbox portal */}
      {lightboxOpen && (
        <Lightbox
          file={file}
          resolvedUrl={resolvedUrl}
          onClose={() => setLightboxOpen(false)}
        />
      )}
    </>
  );
}

export default MediaRenderer;
