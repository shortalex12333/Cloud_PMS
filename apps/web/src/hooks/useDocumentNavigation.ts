'use client';

/**
 * useDocumentNavigation — Navigation helper for document entities.
 *
 * Provides a simple function to navigate to the Document Lens.
 * Referenced in DocumentCard.tsx for opening document details.
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
import { useRouter } from 'next/navigation';

export interface DocumentNavigationResult {
  /**
   * Navigate to the Document Lens for a specific document.
   * @param documentId - The UUID of the document to view
   */
  openDocumentLens: (documentId: string) => void;
}

/**
 * Hook providing document navigation utilities.
 */
export function useDocumentNavigation(): DocumentNavigationResult {
  const router = useRouter();

  const openDocumentLens = useCallback(
    (documentId: string) => {
      router.push(`/documents/${documentId}`);
    },
    [router]
  );

  return {
    openDocumentLens,
  };
}

/**
 * Standalone function to navigate to Document Lens.
 * For use outside of React components (e.g., in event handlers).
 *
 * Note: Requires window.location as it doesn't have access to Next.js router.
 * Prefer useDocumentNavigation() hook inside components.
 */
export function openDocumentLens(documentId: string): void {
  if (typeof window !== 'undefined') {
    window.location.href = `/documents/${documentId}`;
  }
}

export default useDocumentNavigation;
