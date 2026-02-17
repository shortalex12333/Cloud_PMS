'use client';

/**
 * =============================================================================
 * DOCUMENT LENS - Full Page View
 * =============================================================================
 *
 * CREATED: 2026-02-17 — Document lens page route
 *
 * PURPOSE: Full-page lens for document entities.
 * Shows document metadata, preview (via signed URL), linked entities, and comments.
 *
 * DATA FETCHING:
 * --------------
 * - doc_metadata: id, filename, mime_type, storage_path, size, created_at, created_by
 * - Linked entities: email_attachment_object_links where document_id = id
 * - Comments: doc_metadata_comments where document_id = id
 * - Signed URL: via loadDocumentWithBackend() for secure document preview
 *
 * AUTHENTICATION:
 * ---------------
 * - Requires authenticated session with yachtId from bootstrap
 * - Shows error if not authenticated
 *
 * LEDGER LOGGING:
 * ---------------
 * - Logs navigate_to_lens event on mount (fire-and-forget)
 * - Logs navigate_back and close_lens on navigation
 * - Per CLAUDE.md: every user action logged to ledger — every navigate
 *
 * RELATED FILES:
 * ==============
 * - /src/components/lens/DocumentLens.tsx — Lens component (placeholder)
 * - /src/components/lens/LensHeader.tsx — Fixed header component
 * - /src/lib/documentLoader.ts — Secure document loading with backend signing
 *
 * =============================================================================
 */

import { useEffect, useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { loadDocumentWithBackend, type DocumentLoadResult } from '@/lib/documentLoader';
import { AlertTriangle, Loader2 } from 'lucide-react';
import { supabase } from '@/lib/supabaseClient';
import { cn } from '@/lib/utils';
import { LensHeader, LensTitleBlock } from '@/components/lens/LensHeader';
import { LensContainer } from '@/components/lens/LensContainer';

// ---------------------------------------------------------------------------
// TYPES
// ---------------------------------------------------------------------------

interface DocumentMetadata {
  id: string;
  filename: string;
  mime_type: string;
  storage_path: string;
  size: number;
  created_at: string;
  created_by: string | null;
  created_by_name?: string;
}

interface LinkedEntity {
  object_type: string;
  object_id: string;
  link_reason: string | null;
  created_at: string;
}

interface DocumentComment {
  id: string;
  comment: string;
  created_by: string;
  created_at: string;
  author_department: string | null;
}

interface DocumentLensData {
  metadata: DocumentMetadata;
  signedUrl: string | null;
  linkedEntities: LinkedEntity[];
  comments: DocumentComment[];
}

// ---------------------------------------------------------------------------
// LEDGER LOGGING
// Logs navigation events to pms_audit_log via backend API.
// Per CLAUDE.md: Every user action logged to ledger. Every navigate — all of it.
// ---------------------------------------------------------------------------
const RENDER_API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

async function logNavigationEvent(
  eventName: string,
  payload: Record<string, unknown>
): Promise<void> {
  try {
    const { data: sessionData } = await supabase.auth.getSession();
    const token = sessionData?.session?.access_token;
    if (!token) return;

    await fetch(`${RENDER_API_URL}/v1/ledger/record`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ event_name: eventName, payload }),
    });
  } catch {
    // Navigation logging is fire-and-forget — never block UX on failure
  }
}

// ---------------------------------------------------------------------------
// DATA FETCHING HELPERS
// ---------------------------------------------------------------------------

async function fetchDocumentMetadata(
  documentId: string,
  yachtId: string
): Promise<DocumentMetadata | null> {
  const { data, error } = await supabase
    .from('doc_metadata')
    .select('id, filename, mime_type, storage_path, file_size, created_at, created_by')
    .eq('id', documentId)
    .eq('yacht_id', yachtId)
    .is('deleted_at', null)
    .single();

  if (error || !data) {
    console.error('[DocumentLensPage] Error fetching doc_metadata:', error);
    return null;
  }

  return {
    id: data.id,
    filename: data.filename,
    mime_type: data.mime_type,
    storage_path: data.storage_path,
    size: data.file_size ?? 0,
    created_at: data.created_at,
    created_by: data.created_by,
  };
}

async function fetchLinkedEntities(
  documentId: string,
  yachtId: string
): Promise<LinkedEntity[]> {
  const { data, error } = await supabase
    .from('email_attachment_object_links')
    .select('object_type, object_id, link_reason, created_at')
    .eq('document_id', documentId)
    .eq('yacht_id', yachtId)
    .eq('is_active', true);

  if (error) {
    console.error('[DocumentLensPage] Error fetching linked entities:', error);
    return [];
  }

  return data ?? [];
}

async function fetchDocumentComments(
  documentId: string,
  yachtId: string
): Promise<DocumentComment[]> {
  const { data, error } = await supabase
    .from('doc_metadata_comments')
    .select('id, comment, created_by, created_at, author_department')
    .eq('document_id', documentId)
    .eq('yacht_id', yachtId)
    .is('deleted_at', null)
    .order('created_at', { ascending: false });

  if (error) {
    console.error('[DocumentLensPage] Error fetching comments:', error);
    return [];
  }

  return data ?? [];
}

// ---------------------------------------------------------------------------
// DISPLAY HELPERS
// ---------------------------------------------------------------------------

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
  if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`;
  return `${Math.floor(diffDays / 365)} years ago`;
}

function getDocumentIcon(mimeType: string): string {
  if (mimeType.startsWith('image/')) return 'image';
  if (mimeType === 'application/pdf') return 'pdf';
  if (mimeType.includes('word') || mimeType.includes('document')) return 'doc';
  if (mimeType.includes('sheet') || mimeType.includes('excel')) return 'xls';
  return 'file';
}

function formatObjectType(objectType: string): string {
  return objectType.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

// ---------------------------------------------------------------------------
// PAGE COMPONENT
// ---------------------------------------------------------------------------

export default function DocumentLensPage() {
  // ---------------------------------------------------------------------------
  // ROUTING & AUTH
  // ---------------------------------------------------------------------------
  const params = useParams();
  const router = useRouter();
  const { user, loading: authLoading, bootstrapping } = useAuth();

  // ---------------------------------------------------------------------------
  // STATE
  // ---------------------------------------------------------------------------
  const [documentData, setDocumentData] = useState<DocumentLensData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isOpen, setIsOpen] = useState(false);

  // Extract document ID from URL: /documents/[id]
  const documentId = params.id as string;

  // ---------------------------------------------------------------------------
  // DATA FETCHING
  // ---------------------------------------------------------------------------
  const fetchDocument = useCallback(async () => {
    // Wait for BOTH authLoading AND bootstrapping to complete.
    // yacht_id from bootstrap is required to scope the tenant query.
    if (authLoading || bootstrapping) return;

    if (!user?.yachtId) {
      setError('Authentication required');
      setLoading(false);
      return;
    }

    try {
      // Fetch document metadata from Supabase
      const metadata = await fetchDocumentMetadata(documentId, user.yachtId);

      if (!metadata) {
        setError('Document not found or access denied');
        setLoading(false);
        return;
      }

      // Fetch signed URL via backend
      const loadResult: DocumentLoadResult = await loadDocumentWithBackend(documentId);

      // Fetch linked entities
      const linkedEntities = await fetchLinkedEntities(documentId, user.yachtId);

      // Fetch comments
      const comments = await fetchDocumentComments(documentId, user.yachtId);

      const data: DocumentLensData = {
        metadata,
        signedUrl: loadResult.success ? loadResult.url ?? null : null,
        linkedEntities,
        comments,
      };

      setDocumentData(data);
      setLoading(false);
      setIsOpen(true);

      // Log navigate_to_lens event — per CLAUDE.md every navigate is logged
      logNavigationEvent('navigate_to_lens', {
        entity_type: 'document',
        entity_id: documentId,
        filename: metadata.filename,
        mime_type: metadata.mime_type,
        linked_entities_count: linkedEntities.length,
        comments_count: comments.length,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load document');
      setLoading(false);
    }
  }, [documentId, user, authLoading, bootstrapping]);

  useEffect(() => {
    fetchDocument();
  }, [fetchDocument]);

  // ---------------------------------------------------------------------------
  // NAVIGATION HANDLERS — Must be declared before any early returns (Rules of Hooks)
  // ---------------------------------------------------------------------------
  const handleBack = useCallback(() => {
    logNavigationEvent('navigate_back', {
      entity_type: 'document',
      entity_id: documentId,
    });
    router.back();
  }, [documentId, router]);

  const handleClose = useCallback(() => {
    setIsOpen(false);
    logNavigationEvent('close_lens', {
      entity_type: 'document',
      entity_id: documentId,
    });
    setTimeout(() => router.push('/app'), 210);
  }, [documentId, router]);

  const handleRefresh = useCallback(() => {
    setLoading(true);
    setError(null);
    setDocumentData(null);
    fetchDocument();
  }, [fetchDocument]);

  // ---------------------------------------------------------------------------
  // LOADING STATE — Skeleton per UI_SPEC.md (no full-page spinners)
  // ---------------------------------------------------------------------------
  if (loading || authLoading || bootstrapping) {
    return (
      <div className="min-h-screen bg-surface-base flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 text-brand-interactive animate-spin" />
          <p className="text-[14px] text-txt-secondary">Loading document...</p>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // ERROR STATE
  // ---------------------------------------------------------------------------
  if (error) {
    return (
      <div className="min-h-screen bg-surface-base flex items-center justify-center p-4">
        <div className="bg-surface-primary rounded-[var(--radius-md)] p-8 max-w-md w-full text-center">
          <AlertTriangle className="w-10 h-10 text-status-critical mx-auto mb-4" />
          <h2 className="text-[18px] font-semibold text-txt-primary mb-2">
            Unable to load document
          </h2>
          <p className="text-[14px] text-txt-secondary mb-6">{error}</p>
          <button
            onClick={() => router.push('/app')}
            className="px-6 py-3 bg-brand-interactive hover:bg-brand-hover text-txt-inverse text-[14px] font-semibold rounded-[var(--radius-sm)] transition-colors duration-[120ms] ease-out"
          >
            Return to App
          </button>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // NULL CHECK
  // ---------------------------------------------------------------------------
  if (!documentData) {
    return null;
  }

  const { metadata, signedUrl, linkedEntities, comments } = documentData;

  // ---------------------------------------------------------------------------
  // RENDER — Inline DocumentLens (until a dedicated component is created)
  // ---------------------------------------------------------------------------
  return (
    <LensContainer
      isOpen={isOpen}
      onClose={handleClose}
    >
      {/* Fixed navigation header — 56px, at z-header */}
      <LensHeader
        entityType="Document"
        title={metadata.filename}
        onBack={handleBack}
        onClose={handleClose}
      />

      {/* Main content — padded top to clear fixed header (56px = h-14) */}
      <main
        className={cn(
          // Clear the fixed header
          'pt-14',
          // Lens body padding: 40px desktop, responsive
          'px-10 md:px-6 sm:px-4',
          // Max content width: 800px centered per spec
          'max-w-[800px] mx-auto',
          // Bottom breathing room
          'pb-12'
        )}
      >
        {/* ---------------------------------------------------------------
            Title block: filename and metadata
            Gap from header: 24px (--space-6)
            --------------------------------------------------------------- */}
        <div className="mt-6">
          <LensTitleBlock
            title={metadata.filename}
            subtitle={`${formatFileSize(metadata.size)} | ${metadata.mime_type}`}
          />
        </div>

        {/* ---------------------------------------------------------------
            Document Info Row
            --------------------------------------------------------------- */}
        <div className="mt-3 flex flex-wrap gap-4 text-[13px] text-txt-secondary">
          <span>Created {formatRelativeTime(metadata.created_at)}</span>
          {linkedEntities.length > 0 && (
            <span>{linkedEntities.length} linked {linkedEntities.length === 1 ? 'entity' : 'entities'}</span>
          )}
          {comments.length > 0 && (
            <span>{comments.length} {comments.length === 1 ? 'comment' : 'comments'}</span>
          )}
        </div>

        {/* ---------------------------------------------------------------
            Section divider
            --------------------------------------------------------------- */}
        <div
          className="mt-6 border-t border-surface-border"
          aria-hidden="true"
        />

        {/* ---------------------------------------------------------------
            Document Preview Section
            --------------------------------------------------------------- */}
        <section className="mt-6">
          <h2 className="text-[14px] font-semibold text-txt-primary mb-3">
            Preview
          </h2>
          {signedUrl ? (
            <div className="bg-surface-primary rounded-md border border-surface-border overflow-hidden">
              {metadata.mime_type === 'application/pdf' ? (
                <iframe
                  src={signedUrl}
                  className="w-full h-[500px] border-0"
                  title={`Preview of ${metadata.filename}`}
                />
              ) : metadata.mime_type.startsWith('image/') ? (
                <img
                  src={signedUrl}
                  alt={metadata.filename}
                  className="max-w-full h-auto"
                />
              ) : (
                <div className="p-6 text-center">
                  <p className="text-[14px] text-txt-secondary mb-4">
                    Preview not available for this file type.
                  </p>
                  <a
                    href={signedUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-block px-4 py-2 bg-brand-interactive hover:bg-brand-hover text-txt-inverse text-[14px] font-semibold rounded-[var(--radius-sm)] transition-colors"
                  >
                    Download File
                  </a>
                </div>
              )}
            </div>
          ) : (
            <div className="bg-surface-primary rounded-md border border-surface-border p-6 text-center">
              <p className="text-[14px] text-txt-secondary">
                Unable to load document preview. The document may have been moved or deleted.
              </p>
            </div>
          )}
        </section>

        {/* ---------------------------------------------------------------
            Linked Entities Section
            --------------------------------------------------------------- */}
        {linkedEntities.length > 0 && (
          <section className="mt-6">
            <h2 className="text-[14px] font-semibold text-txt-primary mb-3">
              Linked Entities
            </h2>
            <div className="space-y-2">
              {linkedEntities.map((entity, index) => (
                <button
                  key={`${entity.object_type}-${entity.object_id}-${index}`}
                  onClick={() => {
                    // Navigate to the linked entity
                    const route = `/${entity.object_type.replace(/_/g, '-')}s/${entity.object_id}`;
                    router.push(route);
                  }}
                  className={cn(
                    'w-full flex items-center justify-between p-3',
                    'bg-surface-primary rounded-md border border-surface-border',
                    'hover:bg-surface-hover transition-colors duration-150',
                    'text-left'
                  )}
                >
                  <div>
                    <p className="text-[14px] font-medium text-txt-primary">
                      {formatObjectType(entity.object_type)}
                    </p>
                    {entity.link_reason && (
                      <p className="text-[12px] text-txt-tertiary">
                        {entity.link_reason}
                      </p>
                    )}
                  </div>
                  <svg
                    className="w-4 h-4 text-txt-tertiary"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                  </svg>
                </button>
              ))}
            </div>
          </section>
        )}

        {/* ---------------------------------------------------------------
            Comments Section
            --------------------------------------------------------------- */}
        <section className="mt-6">
          <h2 className="text-[14px] font-semibold text-txt-primary mb-3">
            Comments {comments.length > 0 && `(${comments.length})`}
          </h2>
          {comments.length > 0 ? (
            <div className="space-y-3">
              {comments.map((comment) => (
                <div
                  key={comment.id}
                  className="bg-surface-primary rounded-md border border-surface-border p-4"
                >
                  <p className="text-[14px] text-txt-primary whitespace-pre-wrap">
                    {comment.comment}
                  </p>
                  <div className="mt-2 flex items-center gap-2 text-[12px] text-txt-tertiary">
                    <span>{formatRelativeTime(comment.created_at)}</span>
                    {comment.author_department && (
                      <>
                        <span aria-hidden="true">|</span>
                        <span className="capitalize">{comment.author_department}</span>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-[14px] text-txt-tertiary">No comments yet.</p>
          )}
        </section>
      </main>
    </LensContainer>
  );
}
