import * as React from 'react';
import { SectionContainer } from '@/components/ui/SectionContainer';
import { GhostButton } from '@/components/ui/GhostButton';
import { MediaRenderer } from '@/components/media/MediaRenderer';
import type { FaultPhoto } from '../FaultLens';

// ============================================================================
// TYPES
// ============================================================================

export interface FaultPhotosSectionProps {
  photos: FaultPhoto[];
  onAddPhoto: () => void;
  canAddPhoto: boolean;
  /** Top offset for sticky header (56 when inside lens to clear the fixed LensHeader) */
  stickyTop?: number;
}

// ============================================================================
// FAULT PHOTOS SECTION
// ============================================================================

/**
 * FaultPhotosSection — Displays fault photos inline via MediaRenderer.
 *
 * All photos are rendered as media (not documents) — fault photos are always
 * images captured by crew. Max-height 240px per item, loading skeleton,
 * error state, and lightbox on click via MediaRenderer.
 *
 * Uses SectionContainer for sticky header behavior.
 * Add Photo CTA visible for crew+ (per registry: all crew can add photos).
 *
 * FE-02-01: Fault Lens — Photos section.
 */
export function FaultPhotosSection({
  photos,
  onAddPhoto,
  canAddPhoto,
  stickyTop,
}: FaultPhotosSectionProps) {
  return (
    <SectionContainer
      title="Photos"
      count={photos.length > 0 ? photos.length : undefined}
      action={
        canAddPhoto
          ? { label: '+ Add Photo', onClick: onAddPhoto }
          : undefined
      }
      stickyTop={stickyTop}
    >
      {photos.length === 0 ? (
        // Contextual empty state
        <div className="py-8 text-center">
          <p className="text-[14px] text-txt-secondary leading-[1.6]">
            No photos attached. Add a photo to document the fault condition.
          </p>
          {canAddPhoto && (
            <GhostButton onClick={onAddPhoto} className="mt-3">
              + Add Photo
            </GhostButton>
          )}
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {photos.map((photo) => (
            <div key={photo.id} className="relative">
              <MediaRenderer
                file={{
                  id: photo.id,
                  // storage_path doubles as URL — MediaRenderer fetches signed URL if needed
                  url: photo.storage_path,
                  filename: photo.file_name ?? 'fault-photo.jpg',
                  mime_type: photo.mime_type ?? 'image/jpeg',
                  size_bytes: photo.file_size ?? 0,
                }}
                maxHeight={240}
                className="w-full rounded-md overflow-hidden"
              />
              {photo.caption && (
                <p className="mt-1 text-[12px] text-txt-tertiary leading-[1.4]">
                  {photo.caption}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </SectionContainer>
  );
}

export default FaultPhotosSection;
