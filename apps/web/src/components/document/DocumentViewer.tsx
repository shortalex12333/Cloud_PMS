'use client';

/**
 * CelesteOS Document Viewer
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
import { loadDocument, downloadDocument, type DocumentLoadResult } from '@/lib/documentLoader';
import { classifyDocument, shouldShowAddToHandoverButton } from '@/lib/documentTypes';
import type { DocumentClassification } from '@/types/situation';

// ============================================================================
// TYPES
// ============================================================================

export interface DocumentViewerProps {
  documentId: string;
  documentTitle: string;
  storagePath: string;
  metadata?: Record<string, any>;
  onClose: () => void;
  onAddToHandover?: () => void;
}

// ============================================================================
// COMPONENT
// ============================================================================

export default function DocumentViewer({
  documentId,
  documentTitle,
  storagePath,
  metadata,
  onClose,
  onAddToHandover,
}: DocumentViewerProps) {
  const [documentUrl, setDocumentUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [classification, setClassification] = useState<DocumentClassification>('operational');
  const [showFindDialog, setShowFindDialog] = useState(false);

  /**
   * Load document on mount
   */
  useEffect(() => {
    async function load() {
      setIsLoading(true);
      setError(null);

      try {
        const result = await loadDocument(storagePath);

        if (!result.success) {
          setError(result.error || 'Failed to load document');
          return;
        }

        setDocumentUrl(result.url || null);

        // Classify document
        const docClassification = classifyDocument(documentTitle, metadata);
        setClassification(docClassification);

        console.log('[DocumentViewer] Document loaded:', {
          title: documentTitle,
          classification: docClassification,
          url_length: result.url?.length,
        });
      } catch (err) {
        console.error('[DocumentViewer] Load error:', err);
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setIsLoading(false);
      }
    }

    load();
  }, [storagePath, documentTitle, metadata]);

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
    try {
      await downloadDocument(storagePath);
    } catch (err) {
      console.error('[DocumentViewer] Download error:', err);
      alert('Failed to download document');
    }
  }, [storagePath]);

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
          className="flex items-center gap-2 px-3 py-1.5 rounded-md text-celeste-text-title hover:bg-celeste-surface transition-colors"
        >
          <X className="w-4 h-4" />
          <span className="text-sm font-medium">Back to Search</span>
        </button>

        {/* Center: Document Title */}
        <div className="flex-1 flex items-center justify-center gap-2 mx-4">
          <FileText className="w-4 h-4 text-[#98989f]" />
          <h1 className="text-sm font-medium text-celeste-text-title truncate max-w-md">
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
            className="flex items-center gap-2 px-3 py-1.5 rounded-md text-[#98989f] hover:text-celeste-text-title hover:bg-celeste-surface transition-colors"
            title="Find in document (Cmd+F)"
          >
            <Search className="w-4 h-4" />
            <span className="text-sm hidden sm:inline">Find</span>
          </button>

          {/* Download */}
          <button
            onClick={handleDownload}
            className="flex items-center gap-2 px-3 py-1.5 rounded-md text-[#98989f] hover:text-celeste-text-title hover:bg-celeste-surface transition-colors"
            title="Download document"
          >
            <Download className="w-4 h-4" />
          </button>

          {/* Add to Handover - Conditional visibility */}
          {showAddToHandover && onAddToHandover && (
            <button
              onClick={onAddToHandover}
              className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-celeste-blue text-celeste-text-title hover:bg-celeste-blue-secondary transition-colors"
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
                className="px-4 py-2 bg-celeste-surface hover:bg-celeste-surface-hover rounded-md text-celeste-text-title text-sm transition-colors"
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
          <p className="text-sm text-celeste-text-title">
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
