/**
 * useSecureDocument Hook
 *
 * React hook for secure document viewing (cloud + local NAS mode).
 * Ensures all document access includes JWT + yacht signature.
 *
 * Usage:
 * ```tsx
 * const { documentUrl, loading, error } = useSecureDocument(documentId);
 *
 * return <iframe src={documentUrl} />;
 * ```
 */

import { useState, useEffect } from 'react';
import { documentsApi, CelesteApiError, AuthError } from '@/lib/apiClient';

export type DocumentMode = 'cloud' | 'nas';

export interface UseSecureDocumentOptions {
  mode?: DocumentMode;
  autoLoad?: boolean; // Auto-load on mount (default: true)
}

export interface UseSecureDocumentResult {
  documentUrl: string | null;
  loading: boolean;
  error: Error | null;
  reload: () => Promise<void>;
}

/**
 * Hook for secure document viewing
 *
 * Automatically fetches authenticated document URL on mount.
 * Handles token refresh and error states.
 *
 * @param documentId - Document ID to load
 * @param options - Configuration options
 * @returns Document URL, loading state, error, and reload function
 */
export function useSecureDocument(
  documentId: string | null,
  options: UseSecureDocumentOptions = {}
): UseSecureDocumentResult {
  const { mode = 'cloud', autoLoad = true } = options;

  const [documentUrl, setDocumentUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const loadDocument = async () => {
    if (!documentId) {
      setError(new Error('No document ID provided'));
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Use streaming endpoint for direct blob URL
      const blobUrl = await documentsApi.streamDocument(documentId);
      setDocumentUrl(blobUrl);
    } catch (err) {
      console.error('[useSecureDocument] Failed to load document:', err);

      // Provide user-friendly error messages
      if (err instanceof AuthError) {
        setError(new Error('Please log in to view this document'));
      } else if (err instanceof CelesteApiError) {
        if (err.status === 403) {
          setError(new Error('You do not have access to this document'));
        } else if (err.status === 404) {
          setError(new Error('Document not found'));
        } else {
          setError(new Error('Failed to load document'));
        }
      } else {
        setError(err instanceof Error ? err : new Error('Unknown error'));
      }
    } finally {
      setLoading(false);
    }
  };

  // Auto-load on mount or when documentId changes
  useEffect(() => {
    if (autoLoad && documentId) {
      loadDocument();
    }

    // Cleanup blob URL on unmount
    return () => {
      if (documentUrl) {
        URL.revokeObjectURL(documentUrl);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documentId, mode, autoLoad]);

  return {
    documentUrl,
    loading,
    error,
    reload: loadDocument,
  };
}

/**
 * Hook for pre-signed document URLs (alternative to streaming)
 *
 * Returns a pre-signed URL with expiry time.
 * Useful when you need the URL upfront (e.g., for download links).
 *
 * @param documentId - Document ID
 * @param mode - 'cloud' or 'nas'
 * @returns Pre-signed URL with expiry time
 */
export function useSecureDocumentUrl(
  documentId: string | null,
  mode: DocumentMode = 'cloud'
): {
  url: string | null;
  expiresAt: number | null;
  loading: boolean;
  error: Error | null;
  refresh: () => Promise<void>;
} {
  const [url, setUrl] = useState<string | null>(null);
  const [expiresAt, setExpiresAt] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchUrl = async () => {
    if (!documentId) {
      setError(new Error('No document ID provided'));
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await documentsApi.getSecureUrl(documentId, mode);
      setUrl(result.url);
      setExpiresAt(result.expiresAt);
    } catch (err) {
      console.error('[useSecureDocumentUrl] Failed to get URL:', err);

      if (err instanceof AuthError) {
        setError(new Error('Authentication required'));
      } else if (err instanceof CelesteApiError) {
        if (err.status === 403) {
          setError(new Error('Access denied'));
        } else if (err.status === 404) {
          setError(new Error('Document not found'));
        } else {
          setError(new Error('Failed to get document URL'));
        }
      } else {
        setError(err instanceof Error ? err : new Error('Unknown error'));
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (documentId) {
      fetchUrl();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documentId, mode]);

  return {
    url,
    expiresAt,
    loading,
    error,
    refresh: fetchUrl,
  };
}
