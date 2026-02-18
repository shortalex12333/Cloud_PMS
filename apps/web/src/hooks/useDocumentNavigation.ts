'use client';

/**
 * useDocumentNavigation — Navigation helper for document entities.
 *
 * Per 1-URL philosophy: Opens document in ContextPanel via SurfaceContext.showContext(),
 * NOT via URL navigation.
 *
 * Usage:
 * ```tsx
 * const { openDocumentLens } = useDocumentNavigation();
 *
 * <DocumentCard
 *   file={file}
 *   onClick={() => openDocumentLens(file.id)}
 * />
 * ```
 */

import { useCallback } from 'react';
import { useSurface } from '@/contexts/SurfaceContext';

export interface DocumentNavigationResult {
  /**
   * Open the Document Lens in ContextPanel for a specific document.
   * @param documentId - The UUID of the document to view
   */
  openDocumentLens: (documentId: string) => void;
}

/**
 * Hook providing document navigation utilities.
 * Uses SurfaceContext.showContext() to render document lens in ContextPanel.
 */
export function useDocumentNavigation(): DocumentNavigationResult {
  const { showContext } = useSurface();

  const openDocumentLens = useCallback(
    (documentId: string) => {
      showContext('document', documentId);
    },
    [showContext]
  );

  return {
    openDocumentLens,
  };
}

/**
 * Standalone function to navigate to Document Lens.
 *
 * @deprecated Use useDocumentNavigation() hook inside components.
 * This function cannot use SurfaceContext and will not work with 1-URL architecture.
 */
export function openDocumentLens(documentId: string): void {
  console.warn(
    '[openDocumentLens] Standalone function is deprecated. Use useDocumentNavigation() hook instead.'
  );
  // Per 1-URL philosophy, we cannot navigate to /documents/[id] anymore.
  // This function should not be used. Log warning and no-op.
}

export default useDocumentNavigation;
