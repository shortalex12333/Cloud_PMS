'use client';

/**
 * AttachmentUploadModal — Generic file upload modal.
 *
 * Two usage modes (the component auto-detects which one based on props):
 *
 *  1. DEFAULT MODE — direct pms_attachments write (existing behaviour).
 *     The modal uploads the blob straight to a specified Supabase storage
 *     bucket via the browser client, then inserts a row to pms_attachments.
 *     Used by WarrantyContent, CertificateContent, etc.
 *
 *     Required props: entityType, entityId, bucket, category, yachtId, userId
 *
 *     <AttachmentUploadModal
 *       open={open}
 *       onClose={onClose}
 *       entityType="warranty"
 *       entityId={id}
 *       bucket="pms-warranty-documents"
 *       category="claim_document"
 *       yachtId={yachtId}
 *       userId={userId}
 *       onComplete={refetch}
 *     />
 *
 *  2. CUSTOM MODE — caller-provided upload strategy.
 *     Used when the target is NOT pms_attachments. The caller supplies an
 *     `onUpload(file)` function that does the actual upload work. The modal
 *     still handles the file picker, MIME/size validation, and toast UX.
 *     All pms_attachments-specific props become unused.
 *
 *     Added 2026-04-15 to support POST /v1/documents/upload (document lens),
 *     which writes to doc_metadata (not pms_attachments) and routes through
 *     the F2 trigger → extraction pipeline. See
 *     apps/api/routes/document_routes.py:upload_document for the endpoint.
 *
 *     <AttachmentUploadModal
 *       open={open}
 *       onClose={onClose}
 *       onUpload={async (file) => { ... POST multipart ... }}
 *       title="Upload Document"
 *       description="Add a document to the vessel library."
 *       onComplete={refetch}
 *     />
 */

import * as React from 'react';
import { cn } from '@/lib/utils';
import { PrimaryButton } from '@/components/ui/PrimaryButton';
import { GhostButton } from '@/components/ui/GhostButton';
import { Toast } from '@/components/ui/Toast';
import { supabase } from '@/lib/supabaseClient';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const MAX_SIZE_BYTES = 15 * 1024 * 1024; // 15 MB

const ACCEPTED_MIME_TYPES = [
  'application/pdf',
  'image/jpeg',
  'image/png',
  'image/heic',
  'image/webp',
  'image/tiff',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/vnd.ms-excel',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  'text/plain',
  'application/zip',
  'application/octet-stream',
].join(',');

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatFileSize(bytes: number): string {
  if (bytes >= 1024 * 1024) {
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }
  return `${(bytes / 1024).toFixed(1)} KB`;
}

function sanitizeFilename(name: string): string {
  return name.replace(/[^a-zA-Z0-9._-]/g, '_');
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface AttachmentUploadModalProps {
  open: boolean;
  onClose: () => void;
  onComplete: () => void;

  // Presentation (optional — default to "Upload Document" / "Attach a file…")
  title?: string;
  description?: string;

  // ----- DEFAULT MODE: pms_attachments direct write -----
  // All optional — required as a group only when `onUpload` is not provided.
  /** Entity type written to pms_attachments.entity_type */
  entityType?: string;
  entityId?: string;
  /** Supabase storage bucket name */
  bucket?: string;
  /** pms_attachments.category value */
  category?: string;
  yachtId?: string;
  userId?: string;

  // ----- CUSTOM MODE: caller-provided upload strategy -----
  /**
   * When provided, this function replaces the default pms_attachments write.
   * Called with the validated File after MIME/size checks pass. Throw on
   * failure so the modal can surface the error via the Toast.
   *
   * When supplied, the pms_attachments-specific props above become unused
   * (the caller is responsible for where the file lands and how it is
   * recorded).
   */
  onUpload?: (file: File) => Promise<void>;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function AttachmentUploadModal({
  open,
  onClose,
  onComplete,
  title = 'Upload Document',
  description = 'Attach a file to this record.',
  entityType,
  entityId,
  bucket,
  category,
  yachtId,
  userId,
  onUpload,
}: AttachmentUploadModalProps) {
  const [file, setFile] = React.useState<File | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [toast, setToast] = React.useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const inputRef = React.useRef<HTMLInputElement>(null);

  // Reset state when modal opens
  React.useEffect(() => {
    if (open) {
      setFile(null);
      setLoading(false);
      setToast(null);
    }
  }, [open]);

  // Dismiss on Escape
  React.useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [open, onClose]);

  if (!open) return null;

  const fileTooLarge = file !== null && file.size > MAX_SIZE_BYTES;
  const canUpload = file !== null && !fileTooLarge && !loading;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0] ?? null;
    setFile(selected);
    setToast(null);
  };

  const handleCancel = () => {
    setFile(null);
    onClose();
  };

  // ---------------------------------------------------------------------
  // Default upload strategy: direct-to-Supabase + pms_attachments insert.
  // Used when the caller did NOT supply a custom `onUpload` prop.
  // Closes over entityType/entityId/bucket/category/yachtId/userId from props.
  // Throws on any failure so the unified handler below can surface the error.
  // ---------------------------------------------------------------------
  const defaultPmsAttachmentUpload = React.useCallback(
    async (selected: File): Promise<void> => {
      if (!entityType || !entityId || !bucket || !category || !yachtId || !userId) {
        // Developer error — caller must pass all pms_attachments props when
        // not providing a custom onUpload. Fail loud so this is obvious in dev.
        throw new Error(
          'AttachmentUploadModal: default mode requires entityType, entityId, bucket, category, yachtId, userId. ' +
            'Pass all six, or provide a custom `onUpload` prop.'
        );
      }

      // Path: {entityType}/{entityId}/{timestamp}-{filename}
      const path = `${entityType}/${entityId}/${Date.now()}-${sanitizeFilename(selected.name)}`;

      const { error: uploadError } = await supabase.storage
        .from(bucket)
        .upload(path, selected, { contentType: selected.type });

      if (uploadError) {
        throw new Error(uploadError.message ?? 'Upload failed');
      }

      const { error: insertError } = await supabase.from('pms_attachments').insert({
        entity_type: entityType,
        entity_id: entityId,
        storage_bucket: bucket,
        storage_path: path,
        filename: selected.name,
        mime_type: selected.type,
        file_size: selected.size,
        category,
        uploaded_by: userId,
        yacht_id: yachtId,
      });

      if (insertError) {
        throw new Error(insertError.message ?? 'Failed to save attachment record');
      }
    },
    [entityType, entityId, bucket, category, yachtId, userId]
  );

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || fileTooLarge) return;

    const uploader = onUpload ?? defaultPmsAttachmentUpload;

    setLoading(true);
    try {
      await uploader(file);

      // Success — same UX regardless of which upload strategy ran.
      setToast({ type: 'success', message: 'Document uploaded successfully' });
      setTimeout(() => {
        onComplete();
        onClose();
      }, 800);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'Upload failed';
      setToast({ type: 'error', message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-sidebar"
        style={{ background: 'rgba(0,0,0,0.60)' }}
        onClick={handleCancel}
        aria-hidden="true"
      />

      {/* Modal panel */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="attachment-upload-title"
        className={cn(
          'fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2',
          'z-modal',
          'bg-surface-elevated border border-surface-border',
          'rounded-lg shadow-modal',
          'w-full max-w-md mx-4'
        )}
      >
        {/* Header */}
        <div className="px-6 pt-6 pb-4 border-b border-surface-border">
          <h2
            id="attachment-upload-title"
            className="text-heading text-txt-primary"
          >
            {title}
          </h2>
          <p className="mt-1 text-label text-txt-secondary">
            {description}
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleUpload}>
          <div className="px-6 py-4 space-y-3">
            <div>
              <label
                htmlFor="attachment-file-input"
                className="block text-label text-txt-primary mb-2"
              >
                Select File
              </label>
              <input
                ref={inputRef}
                id="attachment-file-input"
                type="file"
                accept={ACCEPTED_MIME_TYPES}
                onChange={handleFileChange}
                disabled={loading}
                className={cn(
                  'w-full',
                  'text-body text-txt-primary',
                  'file:mr-3 file:py-1.5 file:px-3',
                  'file:rounded file:border-0',
                  'file:text-label file:bg-surface-primary file:text-txt-primary',
                  'file:cursor-pointer',
                  'cursor-pointer',
                  loading && 'opacity-50 cursor-not-allowed'
                )}
              />
            </div>

            {file && (
              <div className="space-y-1">
                <p className="text-label text-txt-secondary truncate">
                  {file.name}{' '}
                  <span className="text-txt-tertiary">({formatFileSize(file.size)})</span>
                </p>
                {fileTooLarge && (
                  <p className="text-caption" style={{ color: 'var(--color-status-critical, #ef4444)' }}>
                    File exceeds 15 MB limit
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="px-6 pb-6 flex justify-end gap-3">
            <GhostButton type="button" onClick={handleCancel} disabled={loading}>
              Cancel
            </GhostButton>
            <PrimaryButton type="submit" disabled={!canUpload} aria-busy={loading}>
              {loading ? 'Uploading…' : 'Upload'}
            </PrimaryButton>
          </div>
        </form>
      </div>

      {toast && (
        <Toast
          type={toast.type}
          message={toast.message}
          onDismiss={() => setToast(null)}
        />
      )}
    </>
  );
}
