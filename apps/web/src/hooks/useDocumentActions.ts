'use client';

/**
 * useDocumentActions - Action hook for Document lens.
 *
 * Per CLAUDE.md and rules.md: All action hooks follow the same pattern:
 * - Return { isLoading, error, ...actions }
 * - Actions return Promise<ActionResult>
 * - Permission checks via useDocumentPermissions
 *
 * SECURITY: All mutations route through executeAction for audit trail and signature requirements.
 */

import { useState, useCallback } from 'react';
import { executeAction } from '@/lib/actionClient';
import type { ActionResult } from '@/types/actions';
import { useAuth } from '@/hooks/useAuth';

// ---------------------------------------------------------------------------
// Role Configuration - DELEGATED TO CENTRALIZED SERVICE
// ---------------------------------------------------------------------------

// Note: Document lens uses email lens permissions in lens_matrix.json.
// Permissions are now derived from the centralized service.

export interface DocumentPermissions {
  canView: boolean;
  canDownload: boolean;
  canDelete: boolean;
  canReclassify: boolean;
  canGetUrl: boolean;
  canAddTags: boolean;
  canUpload: boolean;
  canUpdate: boolean;
}

import { useEmailPermissions as useCentralizedEmailPermissions } from '@/hooks/permissions/useEmailPermissions';

/**
 * Permission check for document actions based on user role.
 * DELEGATED TO CENTRALIZED SERVICE - reads from lens_matrix.json
 *
 * Note: Documents use email lens permissions since there's no dedicated document lens.
 */
export function useDocumentPermissions(): DocumentPermissions {
  const central = useCentralizedEmailPermissions();

  // Document permissions map to email lens actions
  // All authenticated users can view and download
  return {
    canView: true, // All authenticated users
    canDownload: true, // All authenticated users
    canDelete: central.canUpdateDocument, // Uses update permission for delete
    canReclassify: central.canUpdateDocument,
    canGetUrl: central.canGetDocumentUrl,
    canAddTags: central.canAddDocumentTags,
    canUpload: central.canUploadDocument,
    canUpdate: central.canUpdateDocument,
  };
}

/**
 * Document actions hook.
 *
 * All mutations flow through executeAction for audit trail, signature requirements,
 * and proper role-based access control enforcement at the API level.
 */
export function useDocumentActions(documentId: string) {
  const { user } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // -------------------------------------------------------------------------
  // Internal executor wrapper (pattern from useHandoverActions)
  // -------------------------------------------------------------------------

  const execute = useCallback(
    async (actionName: string, payload: Record<string, unknown>): Promise<ActionResult> => {
      if (!user?.yachtId) {
        return { success: false, error: 'No yacht context available' };
      }

      setIsLoading(true);
      setError(null);

      try {
        const result = await executeAction(
          actionName,
          {
            yacht_id: user.yachtId,
            document_id: documentId,
          },
          payload
        );

        return {
          success: result.status === 'success',
          data: result.result,
          error: result.message,
        };
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Unknown error';
        setError(msg);
        return { success: false, error: msg };
      } finally {
        setIsLoading(false);
      }
    },
    [user, documentId]
  );

  // -------------------------------------------------------------------------
  // Read-only actions (no mutation, no action router needed)
  // -------------------------------------------------------------------------

  const viewDocument = useCallback(async (): Promise<ActionResult> => {
    // Document viewing is handled by the lens itself - no mutation
    return { success: true };
  }, []);

  const downloadDocument = useCallback(async (): Promise<ActionResult> => {
    // Download is handled by browser via document URL - no mutation
    return { success: true };
  }, []);

  // -------------------------------------------------------------------------
  // Mutation actions (routed through executeAction for audit trail)
  // -------------------------------------------------------------------------

  /**
   * delete_document - Soft delete a document (SIGNED action)
   *
   * Routes through action router for audit trail and signature requirements.
   * SIGNED actions require PIN+TOTP verification for audit compliance.
   *
   * @param reason - Reason for deletion (required for audit trail)
   * @param signature - PIN hash and TOTP code for signature verification
   */
  const deleteDocument = useCallback(
    async (
      reason: string,
      signature: { pin_hash: string; totp_code: string }
    ): Promise<ActionResult> => {
      console.log('[useDocumentActions] Deleting document via action router:', documentId);
      return execute('delete_document', {
        reason: reason || 'Deleted by user',
        signature,
      });
    },
    [execute, documentId]
  );

  /**
   * update_document - Reclassify a document's type
   *
   * Routes through action router for audit trail.
   *
   * @param newClassification - New document type/classification
   */
  const reclassifyDocument = useCallback(
    async (newClassification: string): Promise<ActionResult> => {
      console.log('[useDocumentActions] Reclassifying document via action router:', documentId, 'to', newClassification);
      return execute('update_document', {
        doc_type: newClassification,
      });
    },
    [execute, documentId]
  );

  /**
   * update_document - Update document metadata
   *
   * Routes through action router for audit trail and signature requirements.
   * Updates metadata fields including title, tags, oem_id, system_path, and document_type.
   *
   * @param params - Object containing optional metadata fields to update
   * @returns Updated document metadata
   */
  const updateDocument = useCallback(
    async (params: {
      title?: string;
      tags?: string[];
      oem_id?: string;
      system_path?: string;
      document_type?: string;
    }): Promise<ActionResult> => {
      console.log('[useDocumentActions] Updating document via action router:', documentId, 'params:', params);
      return execute('update_document', params);
    },
    [execute, documentId]
  );

  /**
   * add_document_tags - Add tags to a document
   *
   * Routes through action router for audit trail and signature requirements.
   *
   * @param tags - Array of tag strings to add to the document
   */
  const addTags = useCallback(
    async (tags: string[]): Promise<ActionResult> => {
      console.log('[useDocumentActions] Adding tags via action router:', documentId, 'tags:', tags);
      return execute('add_document_tags', {
        tags,
      });
    },
    [execute, documentId]
  );

  /**
   * get_document_url - Get a signed URL for document download
   *
   * Routes through action router for audit trail and proper access control.
   *
   * @param expirySeconds - URL expiration time in seconds (default 3600)
   * @returns Signed URL string for download
   */
  const getSignedUrl = useCallback(
    async (expirySeconds?: number): Promise<ActionResult> => {
      console.log('[useDocumentActions] Getting signed URL via action router:', documentId);
      return execute('get_document_url', {
        expiry_seconds: expirySeconds || 3600,
      });
    },
    [execute, documentId]
  );

  // -------------------------------------------------------------------------
  // Return
  // -------------------------------------------------------------------------

  return {
    isLoading,
    error,
    viewDocument,
    downloadDocument,
    deleteDocument,
    reclassifyDocument,
    updateDocument,
    addTags,
    getSignedUrl,
  };
}
