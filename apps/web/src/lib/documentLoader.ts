/**
 * Document Loading from Supabase Storage
 *
 * Securely loads documents using JWT authentication
 * Based on celeste_real_yacht_security_redis.py pattern
 */

import { supabase } from './supabaseClient';
import { getYachtId, getAuthHeaders } from './authHelpers';

// ============================================================================
// TYPES
// ============================================================================

export interface DocumentLoadResult {
  success: boolean;
  url?: string;
  error?: string;
  metadata?: {
    name: string;
    size: number;
    mime_type: string;
    last_modified: string;
  };
}

// ============================================================================
// DOCUMENT LOADING
// ============================================================================

/**
 * Load document using backend signing endpoint (RECOMMENDED)
 *
 * This is the secure approach that:
 * - Prevents uncontrolled frontend signing
 * - Enforces access control at backend
 * - Provides audit logging for compliance
 * - Uses short-lived URLs (10 min TTL)
 * - Rate limits to prevent bulk downloads
 *
 * @param documentId - Document UUID from doc_metadata table
 * @returns DocumentLoadResult with blob URL
 */
export async function loadDocumentWithBackend(
  documentId: string
): Promise<DocumentLoadResult> {
  try {
    console.log('[documentLoader] Loading document via backend:', documentId);

    // Get yacht ID for auth headers
    const yachtId = await getYachtId();
    if (!yachtId) {
      return {
        success: false,
        error: 'Yacht context required',
      };
    }

    // Get authenticated headers
    const headers = await getAuthHeaders(yachtId);

    // Call backend signing endpoint
    const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'https://pipeline-core.int.celeste7.ai';
    const response = await fetch(`${API_BASE}/v1/documents/${documentId}/sign`, {
      method: 'POST',
      headers,
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('[documentLoader] Backend signing failed:', response.status, errorText);

      if (response.status === 404) {
        return {
          success: false,
          error: 'Document not found or access denied',
        };
      } else if (response.status === 429) {
        return {
          success: false,
          error: 'Too many requests. Please wait a moment.',
        };
      } else {
        return {
          success: false,
          error: `Failed to load document: ${response.statusText}`,
        };
      }
    }

    const data = await response.json();
    const { signed_url, filename, content_type, size_bytes, expires_at } = data;

    console.log('[documentLoader] Signed URL received:', {
      filename,
      content_type,
      size_bytes,
      expires_in: expires_at ? `${expires_at - Math.floor(Date.now() / 1000)}s` : 'unknown',
    });

    // Fetch PDF as blob (same approach as before - works well)
    console.log('[documentLoader] Fetching PDF as blob...');

    const pdfResponse = await fetch(signed_url);

    if (!pdfResponse.ok) {
      console.error('[documentLoader] Failed to fetch PDF:', pdfResponse.status, pdfResponse.statusText);
      return {
        success: false,
        error: `Failed to fetch document: ${pdfResponse.statusText}`,
      };
    }

    const blob = await pdfResponse.blob();
    const blobUrl = URL.createObjectURL(blob);

    console.log('[documentLoader] Created blob URL:', {
      blob_size: blob.size,
      blob_type: blob.type,
      filename,
    });

    return {
      success: true,
      url: blobUrl,
      metadata: {
        name: filename || 'document.pdf',
        size: size_bytes || blob.size,
        mime_type: content_type || blob.type || 'application/pdf',
        last_modified: new Date().toISOString(),
      },
    };
  } catch (error) {
    console.error('[documentLoader] Backend document loading error:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error loading document',
    };
  }
}

/**
 * Load document from Supabase Storage with JWT authentication
 *
 * DEPRECATED: Use loadDocumentWithBackend() instead for production.
 * This direct approach bypasses backend access control and audit logging.
 *
 * @param storagePath - Path to document in Supabase Storage (e.g., "yacht_123/manuals/engine_manual.pdf")
 * @param bucketName - Storage bucket name (default: "documents")
 * @returns DocumentLoadResult with signed URL
 */
export async function loadDocument(
  storagePath: string,
  bucketName: string = 'documents'
): Promise<DocumentLoadResult> {
  try {
    // Validate authentication
    const { data: { session }, error: authError } = await supabase.auth.getSession();

    if (authError || !session) {
      return {
        success: false,
        error: 'Authentication required to view documents',
      };
    }

    // Validate yacht isolation
    const yachtId = await getYachtId();
    if (!yachtId) {
      return {
        success: false,
        error: 'Yacht context required',
      };
    }

    // Storage path should already have yacht UUID prefix from doc_metadata
    // Format: {yacht_id}/{category}/{subcategory}/{type}/{filename}
    // Example: 85fe1119-b04c-41ac-80f1-829d23322598/01_BRIDGE/ais_equipment/installation_guides/manual.pdf

    console.log('[documentLoader] Validating path format:', {
      storagePath,
      yachtId,
      expectedPrefix: `${yachtId}/`,
      pathStartsCorrectly: storagePath.startsWith(`${yachtId}/`),
    });

    // Validate that path starts with this yacht's UUID (security check)
    if (!storagePath.startsWith(`${yachtId}/`)) {
      console.warn('[documentLoader] Path does not start with yacht UUID, security risk!', {
        storagePath,
        expectedPrefix: yachtId,
      });
      return {
        success: false,
        error: 'Invalid document path - yacht isolation check failed',
      };
    }

    console.log('[documentLoader] Loading document:', {
      path: storagePath,
      bucket: bucketName,
      yacht_id: yachtId,
    });

    // Get signed URL (valid for 1 hour)
    const { data: urlData, error: urlError } = await supabase.storage
      .from(bucketName)
      .createSignedUrl(storagePath, 3600); // 3600 seconds = 1 hour

    if (urlError) {
      console.error('[documentLoader] Error creating signed URL:', urlError);
      return {
        success: false,
        error: `Failed to load document: ${urlError.message}`,
      };
    }

    if (!urlData?.signedUrl) {
      return {
        success: false,
        error: 'Document URL not available',
      };
    }

    // FIX: Fetch PDF as blob to avoid Chrome blocking cross-origin iframe embeds
    // Chrome blocks iframes loading content from different origins (Supabase Storage)
    // Solution: Fetch the PDF data using the signed URL, then create a local blob URL
    // This makes the content same-origin and avoids X-Frame-Options / CSP issues
    console.log('[documentLoader] Fetching PDF as blob to avoid CORS/CSP blocking...');

    try {
      const response = await fetch(urlData.signedUrl);

      if (!response.ok) {
        console.error('[documentLoader] Failed to fetch blob:', response.status, response.statusText);
        return {
          success: false,
          error: `Failed to fetch document: ${response.statusText}`,
        };
      }

      const blob = await response.blob();
      const blobUrl = URL.createObjectURL(blob);

      console.log('[documentLoader] Created blob URL:', {
        path: storagePath,
        blob_size: blob.size,
        blob_type: blob.type,
      });

      // Get document metadata
      const { data: fileData, error: fileError } = await supabase.storage
        .from(bucketName)
        .list(storagePath.substring(0, storagePath.lastIndexOf('/')), {
          search: storagePath.split('/').pop(),
        });

      let metadata;
      if (!fileError && fileData && fileData.length > 0) {
        const file = fileData[0];
        metadata = {
          name: file.name,
          size: file.metadata?.size || blob.size || 0,
          mime_type: file.metadata?.mimetype || blob.type || 'application/pdf',
          last_modified: file.updated_at || file.created_at || new Date().toISOString(),
        };
      } else {
        // Fallback metadata from blob
        metadata = {
          name: storagePath.split('/').pop() || 'document.pdf',
          size: blob.size,
          mime_type: blob.type || 'application/pdf',
          last_modified: new Date().toISOString(),
        };
      }

      console.log('[documentLoader] Document loaded successfully:', {
        path: storagePath,
        url_type: 'blob',
        metadata,
      });

      return {
        success: true,
        url: blobUrl, // Return blob URL instead of signed URL
        metadata,
      };
    } catch (fetchError) {
      console.error('[documentLoader] Error fetching blob:', fetchError);
      return {
        success: false,
        error: fetchError instanceof Error ? fetchError.message : 'Failed to fetch document',
      };
    }
  } catch (error) {
    console.error('[documentLoader] Unexpected error:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error loading document',
    };
  }
}

/**
 * Download document (force download instead of viewing)
 */
export async function downloadDocument(
  storagePath: string,
  bucketName: string = 'documents'
): Promise<void> {
  try {
    // Validate authentication
    const { data: { session }, error: authError } = await supabase.auth.getSession();

    if (authError || !session) {
      throw new Error('Authentication required to download documents');
    }

    // Validate yacht isolation
    const yachtId = await getYachtId();
    if (!yachtId || !storagePath.startsWith(`${yachtId}/`)) {
      throw new Error('Invalid document path');
    }

    // Get signed URL for download
    const { data: urlData, error: urlError } = await supabase.storage
      .from(bucketName)
      .createSignedUrl(storagePath, 3600);

    if (urlError || !urlData?.signedUrl) {
      throw new Error(urlError?.message || 'Failed to get download URL');
    }

    // Fetch the blob and trigger download
    const response = await fetch(urlData.signedUrl);
    if (!response.ok) {
      throw new Error(`Download failed: ${response.statusText}`);
    }

    const blob = await response.blob();
    const blobUrl = URL.createObjectURL(blob);

    // Create temporary link and trigger download
    const link = document.createElement('a');
    link.href = blobUrl;
    link.download = storagePath.split('/').pop() || 'document.pdf';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    // Cleanup blob URL after download
    setTimeout(() => URL.revokeObjectURL(blobUrl), 1000);
  } catch (error) {
    console.error('[documentLoader] Download error:', error);
    throw error;
  }
}

/**
 * Get document metadata without loading full file
 */
export async function getDocumentMetadata(
  storagePath: string,
  bucketName: string = 'documents'
): Promise<DocumentLoadResult['metadata'] | null> {
  try {
    const yachtId = await getYachtId();
    if (!yachtId) return null;

    // Validate yacht isolation - path should already start with yacht UUID
    if (!storagePath.startsWith(`${yachtId}/`)) {
      console.warn('[documentLoader] Metadata path security check failed');
      return null;
    }

    const { data: fileData, error } = await supabase.storage
      .from(bucketName)
      .list(storagePath.substring(0, storagePath.lastIndexOf('/')), {
        search: storagePath.split('/').pop(),
      });

    if (error || !fileData || fileData.length === 0) {
      return null;
    }

    const file = fileData[0];
    return {
      name: file.name,
      size: file.metadata?.size || 0,
      mime_type: file.metadata?.mimetype || 'application/octet-stream',
      last_modified: file.updated_at || file.created_at || new Date().toISOString(),
    };
  } catch (error) {
    console.error('[documentLoader] Error getting metadata:', error);
    return null;
  }
}
