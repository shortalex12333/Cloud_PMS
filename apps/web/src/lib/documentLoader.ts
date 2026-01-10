/**
 * Document Loading from Supabase Storage
 *
 * Securely loads documents using JWT authentication
 * Based on celeste_real_yacht_security_redis.py pattern
 */

import { supabase } from './supabaseClient';
import { getYachtId } from './authHelpers';

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
 * Load document from Supabase Storage with JWT authentication
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
        size: file.metadata?.size || 0,
        mime_type: file.metadata?.mimetype || 'application/octet-stream',
        last_modified: file.updated_at || file.created_at || new Date().toISOString(),
      };
    }

    console.log('[documentLoader] Document loaded successfully:', {
      path: storagePath,
      url_length: urlData.signedUrl.length,
      metadata,
    });

    return {
      success: true,
      url: urlData.signedUrl,
      metadata,
    };
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
  const result = await loadDocument(storagePath, bucketName);

  if (!result.success || !result.url) {
    throw new Error(result.error || 'Failed to download document');
  }

  // Create temporary link and trigger download
  const link = document.createElement('a');
  link.href = result.url;
  link.download = result.metadata?.name || storagePath.split('/').pop() || 'document';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
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
