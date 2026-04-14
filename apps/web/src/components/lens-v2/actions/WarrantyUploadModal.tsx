'use client';

/**
 * WarrantyUploadModal — Warranty lens file upload action modal
 *
 * Uploads a document directly to Supabase storage bucket `pms-warranty-documents`,
 * then inserts a row to `pms_attachments`. Uses design system tokens exclusively.
 * Shows loading state during upload, handles errors via Toast.
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

export interface WarrantyUploadModalProps {
  open: boolean;
  onClose: () => void;
  entityId: string;
  yachtId: string;
  userId: string;
  onComplete: () => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * WarrantyUploadModal
 *
 * Modal overlay for uploading a document to a warranty claim.
 * Escape key dismisses. Cancel clears file selection.
 */
export function WarrantyUploadModal({
  open,
  onClose,
  entityId,
  yachtId,
  userId,
  onComplete,
}: WarrantyUploadModalProps) {
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

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || fileTooLarge) return;

    setLoading(true);
    try {
      // Build storage path
      const path = `warranty/${entityId}/${Date.now()}-${sanitizeFilename(file.name)}`;

      // Upload to Supabase storage
      const { error: uploadError } = await supabase.storage
        .from('pms-warranty-documents')
        .upload(path, file, { contentType: file.type });

      if (uploadError) {
        setToast({ type: 'error', message: uploadError.message ?? 'Upload failed' });
        return;
      }

      // Insert row to pms_attachments
      const { error: insertError } = await supabase
        .from('pms_attachments')
        .insert({
          entity_type: 'warranty',
          entity_id: entityId,
          storage_bucket: 'pms-warranty-documents',
          storage_path: path,
          filename: file.name,
          mime_type: file.type,
          file_size: file.size,
          category: 'claim_document',
          uploaded_by: userId,
          yacht_id: yachtId,
        });

      if (insertError) {
        // File is uploaded but metadata insert failed — partial state, still close
        setToast({ type: 'error', message: insertError.message ?? 'Failed to save attachment record' });
        setTimeout(() => {
          onComplete();
          onClose();
        }, 1200);
        return;
      }

      // Success
      setToast({ type: 'success', message: 'Document uploaded successfully' });
      setTimeout(() => {
        onComplete();
        onClose();
      }, 800);
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
        aria-labelledby="warranty-upload-title"
        className={cn(
          'fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2',
          'z-modal',
          // Surface tokens
          'bg-surface-elevated border border-surface-border',
          // Shape
          'rounded-lg shadow-modal',
          // Width
          'w-full max-w-md mx-4'
        )}
      >
        {/* Header */}
        <div className="px-6 pt-6 pb-4 border-b border-surface-border">
          <h2
            id="warranty-upload-title"
            className="text-heading text-txt-primary"
          >
            Upload Document
          </h2>
          <p className="mt-1 text-label text-txt-secondary">
            Attach a file to this warranty claim.
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleUpload}>
          <div className="px-6 py-4 space-y-3">
            {/* File input */}
            <div>
              <label
                htmlFor="warranty-file-input"
                className="block text-label text-txt-primary mb-2"
              >
                Select File
              </label>
              <input
                ref={inputRef}
                id="warranty-file-input"
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

            {/* File info / error */}
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

          {/* Footer buttons */}
          <div className="px-6 pb-6 flex justify-end gap-3">
            <GhostButton
              type="button"
              onClick={handleCancel}
              disabled={loading}
            >
              Cancel
            </GhostButton>
            <PrimaryButton
              type="submit"
              disabled={!canUpload}
              aria-busy={loading}
            >
              {loading ? 'Uploading…' : 'Upload'}
            </PrimaryButton>
          </div>
        </form>
      </div>

      {/* Toast notification */}
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
