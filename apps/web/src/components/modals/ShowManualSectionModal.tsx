/**
 * ShowManualSectionModal Component
 *
 * Displays relevant manual section for equipment/fault context.
 * Shows document preview, section content, and related sections.
 */

'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { useActionHandler } from '@/hooks/useActionHandler';
import {
  Book,
  Loader2,
  FileText,
  ExternalLink,
  ChevronRight,
  AlertCircle,
} from 'lucide-react';

interface ManualSection {
  id: string;
  title: string;
  page_number: number;
  text_preview?: string;
}

interface DocumentData {
  id: string;
  title: string;
  manufacturer: string;
  model: string;
  storage_path: string;
  signed_url: string | null;
}

interface ShowManualSectionModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  context: {
    equipment_id: string;
    equipment_name?: string;
    fault_code?: string;
  };
  onSuccess?: (data: { document: DocumentData; section: ManualSection }) => void;
}

export function ShowManualSectionModal({
  open,
  onOpenChange,
  context,
  onSuccess,
}: ShowManualSectionModalProps) {
  const { executeAction, isLoading } = useActionHandler();
  const [document, setDocument] = useState<DocumentData | null>(null);
  const [section, setSection] = useState<ManualSection | null>(null);
  const [relatedSections, setRelatedSections] = useState<ManualSection[]>([]);
  const [error, setError] = useState<string | null>(null);

  const loadManualSection = useCallback(async (sectionId?: string) => {
    setError(null);

    const response = await executeAction(
      'show_manual_section',
      {
        equipment_id: context.equipment_id,
        fault_code: context.fault_code,
        section_id: sectionId,
      },
      {
        successMessage: 'Manual section loaded',
        refreshData: false,
      }
    );

    if (response?.success && response.data) {
      setDocument(response.data.document);
      setSection(response.data.section);
      setRelatedSections(response.data.related_sections || []);

      if (onSuccess) {
        onSuccess({
          document: response.data.document,
          section: response.data.section,
        });
      }
    } else {
      setError(response?.error?.message || 'Failed to load manual section');
    }
  }, [executeAction, context.equipment_id, context.fault_code, onSuccess]);

  // Load section when modal opens
  useEffect(() => {
    if (open && context.equipment_id) {
      loadManualSection();
    }
  }, [open, context.equipment_id, loadManualSection]);

  // Reset state when modal closes
  useEffect(() => {
    if (!open) {
      setDocument(null);
      setSection(null);
      setRelatedSections([]);
      setError(null);
    }
  }, [open]);

  const handleSectionClick = (sectionId: string) => {
    loadManualSection(sectionId);
  };

  const handleOpenPdf = () => {
    if (document?.signed_url) {
      window.open(document.signed_url, '_blank');
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Book className="h-5 w-5 text-blue-600" />
            Equipment Manual
          </DialogTitle>
          <DialogDescription>
            {context.equipment_name
              ? `Manual section for ${context.equipment_name}`
              : 'View relevant manual sections'}
          </DialogDescription>
        </DialogHeader>

        {isLoading && !section && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
            <span className="ml-3 text-gray-600">Loading manual...</span>
          </div>
        )}

        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-red-600 mt-0.5" />
              <div>
                <h4 className="font-medium text-red-800">Unable to load manual</h4>
                <p className="text-sm text-red-700 mt-1">{error}</p>
              </div>
            </div>
          </div>
        )}

        {document && section && (
          <div className="space-y-4">
            {/* Document Info */}
            <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3">
                  <FileText className="h-5 w-5 text-blue-600 mt-0.5" />
                  <div>
                    <h4 className="font-medium text-blue-900">{document.title}</h4>
                    <p className="text-sm text-blue-700 mt-0.5">
                      {document.manufacturer} {document.model}
                    </p>
                  </div>
                </div>
                {document.signed_url && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleOpenPdf}
                    className="text-blue-700 border-blue-300 hover:bg-blue-100"
                  >
                    <ExternalLink className="h-4 w-4 mr-1" />
                    Open PDF
                  </Button>
                )}
              </div>
            </div>

            {/* Section Content */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold text-gray-900">{section.title}</h3>
                <span className="text-sm text-gray-500">Page {section.page_number}</span>
              </div>
              <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg">
                <div className="prose prose-sm max-w-none">
                  <pre className="whitespace-pre-wrap font-sans text-sm text-gray-700">
                    {section.text_preview}
                  </pre>
                </div>
              </div>
            </div>

            {/* Related Sections */}
            {relatedSections.length > 0 && (
              <div className="space-y-2">
                <h3 className="font-semibold text-gray-900 text-sm">Related Sections</h3>
                <div className="space-y-1">
                  {relatedSections.map((related) => (
                    <button
                      key={related.id}
                      onClick={() => handleSectionClick(related.id)}
                      disabled={isLoading}
                      className="w-full p-2 text-left bg-white border border-gray-200 rounded hover:bg-gray-50 transition-colors flex items-center justify-between disabled:opacity-50"
                    >
                      <span className="text-sm text-gray-700">{related.title}</span>
                      <div className="flex items-center gap-2 text-gray-400">
                        <span className="text-xs">Page {related.page_number}</span>
                        <ChevronRight className="h-4 w-4" />
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-2 pt-4 border-t mt-4">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
