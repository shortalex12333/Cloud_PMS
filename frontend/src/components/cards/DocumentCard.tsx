/**
 * DocumentCard Component
 *
 * Displays document/manual information with quick access actions
 */

'use client';

import { FileText, Download, ExternalLink, Eye } from 'lucide-react';
import { ActionButton } from '@/components/actions/ActionButton';
import { formatDate } from '@/lib/utils';
import type { MicroAction } from '@/types/actions';

interface DocumentCardProps {
  document: {
    id: string;
    title: string;
    document_type: 'manual' | 'certificate' | 'sop' | 'drawing' | 'report' | 'other';
    file_url?: string;
    page_count?: number;
    equipment_id?: string;
    equipment_name?: string;
    uploaded_at: string;
    expires_at?: string;
    version?: string;
  };
  actions?: MicroAction[];
}

export function DocumentCard({ document, actions = [] }: DocumentCardProps) {
  const getDocTypeIcon = () => {
    switch (document.document_type) {
      case 'certificate':
        return '📜';
      case 'manual':
        return '📕';
      case 'sop':
        return '📋';
      case 'drawing':
        return '📐';
      case 'report':
        return '📊';
      default:
        return '📄';
    }
  };

  const isExpiringSoon =
    document.expires_at &&
    new Date(document.expires_at) < new Date(Date.now() + 30 * 24 * 60 * 60 * 1000);
  const isExpired =
    document.expires_at && new Date(document.expires_at) < new Date();

  return (
    <div className="bg-card border border-border rounded-lg p-4 hover:bg-accent/50 transition-colors">
      <div className="flex items-start gap-3">
        {/* Document Icon */}
        <div className="mt-1 text-primary text-2xl">
          {getDocTypeIcon()}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Title & Type */}
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            <h3 className="font-medium text-foreground">{document.title}</h3>
            <span className="text-xs px-2 py-0.5 rounded-full border border-muted bg-muted text-muted-foreground uppercase">
              {document.document_type}
            </span>
            {document.version && (
              <span className="text-xs text-muted-foreground">v{document.version}</span>
            )}
          </div>

          {/* Equipment Link */}
          {document.equipment_name && (
            <p className="text-sm text-muted-foreground mb-2">
              <span className="font-medium">Equipment:</span> {document.equipment_name}
            </p>
          )}

          {/* Metadata */}
          <div className="flex items-center gap-4 text-xs text-muted-foreground mb-2">
            {document.page_count && <span>{document.page_count} pages</span>}
            <span>Uploaded: {formatDate(document.uploaded_at)}</span>
          </div>

          {/* Expiry Warning */}
          {document.expires_at && (
            <div className="mb-2">
              {isExpired ? (
                <p className="text-xs text-red-600 font-medium">
                  ⚠️ Expired: {formatDate(document.expires_at)}
                </p>
              ) : isExpiringSoon ? (
                <p className="text-xs text-orange-600 font-medium">
                  ⚠️ Expires soon: {formatDate(document.expires_at)}
                </p>
              ) : (
                <p className="text-xs text-muted-foreground">
                  Expires: {formatDate(document.expires_at)}
                </p>
              )}
            </div>
          )}

          {/* Actions */}
          <div className="flex flex-wrap gap-2">
            {document.file_url && (
              <a
                href={document.file_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
              >
                <Eye className="h-3.5 w-3.5" />
                View
              </a>
            )}
            {actions.map((action) => (
              <ActionButton
                key={action}
                action={action}
                context={{
                  document_id: document.id,
                  equipment_id: document.equipment_id,
                }}
                variant="secondary"
                size="sm"
                showIcon={true}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
