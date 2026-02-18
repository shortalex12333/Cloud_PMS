'use client';

/**
 * useDocumentActions - Action hook for Document lens.
 *
 * Per CLAUDE.md and rules.md: All action hooks follow the same pattern:
 * - Return { isLoading, error, ...actions }
 * - Actions return Promise<ActionResult>
 * - Permission checks via useDocumentPermissions
 */

import { useState, useCallback } from 'react';
import type { ActionResult } from '@/types/actions';
import { useAuth } from '@/hooks/useAuth';

export interface DocumentPermissions {
  canView: boolean;
  canDownload: boolean;
  canDelete: boolean;
  canReclassify: boolean;
}

/**
 * Permission check for document actions based on user role.
 */
export function useDocumentPermissions(): DocumentPermissions {
  const { user } = useAuth();
  const role = user?.role || 'crew';

  // All roles can view documents
  const canView = true;

  // All roles can download documents
  const canDownload = true;

  // Only HOD+ can delete or reclassify
  const hodPlusRoles = ['chief_engineer', 'chief_officer', 'chief_steward', 'purser', 'captain', 'manager'];
  const canDelete = hodPlusRoles.includes(role);
  const canReclassify = hodPlusRoles.includes(role);

  return {
    canView,
    canDownload,
    canDelete,
    canReclassify,
  };
}

/**
 * Document actions hook.
 */
export function useDocumentActions(documentId: string) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const viewDocument = useCallback(async (): Promise<ActionResult> => {
    setIsLoading(true);
    setError(null);
    try {
      // Document viewing is handled by the lens itself
      return { success: true };
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to view document';
      setError(message);
      return { success: false, error: message };
    } finally {
      setIsLoading(false);
    }
  }, [documentId]);

  const downloadDocument = useCallback(async (): Promise<ActionResult> => {
    setIsLoading(true);
    setError(null);
    try {
      // Download is handled by browser via document URL
      return { success: true };
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to download document';
      setError(message);
      return { success: false, error: message };
    } finally {
      setIsLoading(false);
    }
  }, [documentId]);

  const deleteDocument = useCallback(async (): Promise<ActionResult> => {
    setIsLoading(true);
    setError(null);
    try {
      // TODO: Implement document deletion
      console.log('[useDocumentActions] Delete document:', documentId);
      return { success: true };
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to delete document';
      setError(message);
      return { success: false, error: message };
    } finally {
      setIsLoading(false);
    }
  }, [documentId]);

  const reclassifyDocument = useCallback(async (newClassification: string): Promise<ActionResult> => {
    setIsLoading(true);
    setError(null);
    try {
      // TODO: Implement document reclassification
      console.log('[useDocumentActions] Reclassify document:', documentId, 'to', newClassification);
      return { success: true };
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to reclassify document';
      setError(message);
      return { success: false, error: message };
    } finally {
      setIsLoading(false);
    }
  }, [documentId]);

  return {
    isLoading,
    error,
    viewDocument,
    downloadDocument,
    deleteDocument,
    reclassifyDocument,
  };
}

export default useDocumentActions;
