'use client';

/**
 * Document Situation View
 *
 * Read-only document viewing environment per Document Situation View.md
 *
 * Rules:
 * - Documents explain reality. Search changes it.
 * - No operational actions inside document view
 * - "Back to Search" is primary escape
 * - Cmd+F for literal text search only
 * - "Add to Handover" visibility depends on document classification
 */

import React, { useEffect, useState, useCallback } from 'react';
import { X, Search, Download, Plus, FileText } from 'lucide-react';
import { cn } from '@/lib/utils';
import { loadDocument, downloadDocument } from '@/lib/documentLoader';
import { classifyDocument, shouldShowAddToHandoverButton } from '@/lib/documentTypes';
import type { SituationContext, DocumentClassification } from '@/types/situation';

// ============================================================================
// TYPES
// ============================================================================

export interface DocumentSituationViewProps {
  situation: SituationContext;
  onClose: () => void;
  onAction?: (action: string, payload: any) => void;
}

// ============================================================================
// COMPONENT
// ============================================================================

export default function DocumentSituationView({
  situation,
  onClose,
  onAction,
}: DocumentSituationViewProps) {
  const [documentUrl, setDocumentUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [classification, setClassification] = useState<DocumentClassification>('operational');
  const [showFindDialog, setShowFindDialog] = useState(false);
  const [storagePath, setStoragePath] = useState<string | null>(null);

  // Extract document info from situation metadata
  const documentId = situation.primary_entity_id;
  const metadata = situation.evidence as any;  // Contains the original result metadata
  const documentTitle = metadata?.title || metadata?.name || 'Document';

  console.log('[DocumentSituationView] Rendering with:', {
    documentId,
    documentTitle,
    metadata,
  });

  /**
   * Load document on mount
   */
  useEffect(() => {
    async function load() {
      setIsLoading(true);
      setError(null);

      try {
        // Get storage_path directly from search result metadata
        // Search returns chunks with metadata.storage_path already populated
        console.log('[DocumentSituationView] Loading document with metadata:', metadata);

        let docStoragePath = metadata?.storage_path as string;

        if (!docStoragePath) {
          console.error('[DocumentSituationView] No storage_path in metadata:', metadata);
          setError('Document storage path not available in search results');
          return;
        }

        // Strip "documents/" prefix if present (chunks include it, but documentLoader expects path without bucket name)
        // Format from chunks: "documents/yacht_id/..."
        // Format for documentLoader: "yacht_id/..."
        if (docStoragePath.startsWith('documents/')) {
          docStoragePath = docStoragePath.substring('documents/'.length);
        }

        console.log('[DocumentSituationView] Using storage path:', docStoragePath);
        setStoragePath(docStoragePath);

        // Load document using storage path from search results
        const result = await loadDocument(docStoragePath);

        if (!result.success) {
          setError(result.error || 'Failed to load document');
          return;
        }

        setDocumentUrl(result.url || null);

        // Use title from situation metadata
        const finalTitle = documentTitle;

        // Classify document using title from search results
        const docClassification = classifyDocument(finalTitle, metadata);
        setClassification(docClassification);

        console.log('[DocumentSituationView] Document loaded successfully:', {
          title: finalTitle,
          classification: docClassification,
          storage_path: docStoragePath,
        });
      } catch (err) {
        console.error('[DocumentSituationView] Load error:', err);
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setIsLoading(false);
      }
    }

    load();
  }, [documentId, documentTitle, metadata]);

  /**
   * Handle Cmd+F / Ctrl+F keyboard shortcut
   */
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Cmd+F (Mac) or Ctrl+F (Windows/Linux)
      if ((e.metaKey || e.ctrlKey) && e.key === 'f') {
        e.preventDefault();
        setShowFindDialog(true);
        // Trigger browser's native find dialog
        setTimeout(() => {
          document.execCommand('find');
        }, 100);
      }

      // Escape to close
      if (e.key === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  /**
   * Handle download
   */
  const handleDownload = useCallback(async () => {
    if (!storagePath) {
      alert('Document path not available');
      return;
    }
    try {
      await downloadDocument(storagePath);
    } catch (err) {
      console.error('[DocumentSituationView] Download error:', err);
      alert('Failed to download document');
    }
  }, [storagePath]);

  /**
   * Handle add to handover
   */
  const handleAddToHandover = useCallback(() => {
    if (onAction) {
      onAction('add_to_handover', {
        document_id: documentId,
        document_title: documentTitle,
        storage_path: storagePath,
      });
    } else {
      // Placeholder
      console.log('[DocumentSituationView] Add to handover:', { documentId, documentTitle });
      alert('Add to Handover functionality coming soon');
    }
  }, [onAction, documentId, documentTitle, storagePath]);

  /**
   * Determine if Add to Handover button should be visible
   */
  const showAddToHandover = shouldShowAddToHandoverButton(classification);

  return (
    <div className="fixed inset-0 z-[9999] bg-[#1c1c1e] flex flex-col">
      {/* Header - Fixed at top */}
      <div className="flex-shrink-0 h-14 bg-[#2c2c2e] border-b border-[#3d3d3f] px-4 flex items-center justify-between">
        {/* Left: Back to Search */}
        <button
          onClick={onClose}
          className="flex items-center gap-2 px-3 py-1.5 rounded-md text-white hover:bg-white/10 transition-colors"
        >
          <X className="w-4 h-4" />
          <span className="text-sm font-medium">Back to Search</span>
        </button>

        {/* Center: Document Title */}
        <div className="flex-1 flex items-center justify-center gap-2 mx-4">
          <FileText className="w-4 h-4 text-[#98989f]" />
          <h1 className="text-sm font-medium text-white truncate max-w-md">
            {documentTitle}
          </h1>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-2">
          {/* Cmd+F Find */}
          <button
            onClick={() => {
              setShowFindDialog(true);
              document.execCommand('find');
            }}
            className="flex items-center gap-2 px-3 py-1.5 rounded-md text-[#98989f] hover:text-white hover:bg-white/10 transition-colors"
            title="Find in document (Cmd+F)"
          >
            <Search className="w-4 h-4" />
            <span className="text-sm hidden sm:inline">Find</span>
          </button>

          {/* Download */}
          <button
            onClick={handleDownload}
            className="flex items-center gap-2 px-3 py-1.5 rounded-md text-[#98989f] hover:text-white hover:bg-white/10 transition-colors"
            title="Download document"
          >
            <Download className="w-4 h-4" />
          </button>

          {/* Add to Handover - Conditional visibility */}
          {showAddToHandover && (
            <button
              onClick={handleAddToHandover}
              className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-celeste-blue text-white hover:bg-celeste-blue-secondary transition-colors"
              title="Add to handover"
            >
              <Plus className="w-4 h-4" />
              <span className="text-sm hidden sm:inline">Add to Handover</span>
            </button>
          )}
        </div>
      </div>

      {/* Document Content Area */}
      <div className="flex-1 overflow-hidden bg-[#1c1c1e]">
        {isLoading && (
          <div className="h-full flex flex-col items-center justify-center">
            <div className="w-8 h-8 border-2 border-celeste-blue border-t-transparent rounded-full animate-spin mb-4" />
            <p className="text-sm text-[#98989f]">Loading document...</p>
          </div>
        )}

        {error && (
          <div className="h-full flex flex-col items-center justify-center px-4">
            <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-6 max-w-md">
              <h2 className="text-lg font-semibold text-red-500 mb-2">Failed to Load Document</h2>
              <p className="text-sm text-[#98989f] mb-4">{error}</p>
              <button
                onClick={onClose}
                className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-md text-white text-sm transition-colors"
              >
                Back to Search
              </button>
            </div>
          </div>
        )}

        {!isLoading && !error && documentUrl && (
          <iframe
            src={documentUrl}
            className="w-full h-full border-0"
            title={documentTitle}
            sandbox="allow-same-origin allow-scripts allow-popups allow-forms"
          />
        )}
      </div>

      {/* Footer - Document Classification Info */}
      <div className="flex-shrink-0 h-8 bg-[#2c2c2e] border-t border-[#3d3d3f] px-4 flex items-center justify-between text-xs text-[#98989f]">
        <span>
          {classification === 'operational' ? '📖 Operational Document' : '🔒 Compliance Document'}
        </span>
        <span>Press Cmd+F to search</span>
      </div>

      {/* Cmd+F Hint Overlay (appears briefly on trigger) */}
      {showFindDialog && (
        <div
          className={cn(
            'fixed top-20 right-4 bg-[#2c2c2e] border border-[#3d3d3f] rounded-lg p-3',
            'shadow-2xl animate-in fade-in slide-in-from-top-2 duration-200'
          )}
        >
          <p className="text-sm text-white">
            <kbd className="px-2 py-1 bg-[#3d3d3f] rounded text-xs mr-1">Cmd</kbd>
            <span className="text-[#98989f]">+</span>
            <kbd className="px-2 py-1 bg-[#3d3d3f] rounded text-xs ml-1">F</kbd>
            <span className="text-[#98989f] ml-2">to find in document</span>
          </p>
        </div>
      )}
    </div>
  );
}
