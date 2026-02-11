'use client';

/**
 * DocumentExpiryModule
 * Expiring certificates and documents
 * Connected to real dashboard data via useDashboardData hook
 */

import React from 'react';
import { FileText, AlertTriangle, Calendar, CheckCircle, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import ModuleContainer, { ModuleItem } from './ModuleContainer';
import { ActionButton } from '@/components/actions/ActionButton';
import { useDocumentExpiryData, ExpiringDocument, DocumentStats } from '@/hooks/useDashboardData';

// ============================================================================
// TYPES
// ============================================================================

interface DocumentExpiryModuleProps {
  isExpanded: boolean;
  onToggle: () => void;
  className?: string;
  documents?: ExpiringDocument[];
  stats?: DocumentStats;
}

// ============================================================================
// COMPONENT
// ============================================================================

export default function DocumentExpiryModule({
  isExpanded,
  onToggle,
  className,
  documents: propDocuments,
  stats: propStats,
}: DocumentExpiryModuleProps) {
  // Use hook data unless props are provided
  const hookData = useDocumentExpiryData();

  const documents = propDocuments ?? hookData.documents;
  const stats = propStats ?? hookData.stats;
  const isLoading = !propDocuments && hookData.isLoading;

  const hasCritical = documents.some(d => d.status === 'critical');
  const overallStatus = hasCritical ? 'critical' : stats.expiringSoon > 0 ? 'warning' : 'healthy';

  return (
    <ModuleContainer
      title="Expiring Documents"
      icon={<FileText className="h-4.5 w-4.5 text-indigo-500" />}
      isExpanded={isExpanded}
      onToggle={onToggle}
      status={overallStatus}
      statusLabel={hasCritical ? 'Action required' : `${stats.expiringSoon} expiring soon`}
      badge={stats.expiringSoon}
      collapsedContent={
        <div className="flex items-center gap-2">
          <span className={cn(
            'px-2 py-0.5 rounded-full text-[11px] font-medium',
            hasCritical ? 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400' :
                         'bg-amber-100 text-amber-600 dark:bg-amber-900/30 dark:text-amber-400'
          )}>
            {stats.expiringSoon} need attention
          </span>
        </div>
      }
      className={className}
    >
      {isLoading ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-5 w-5 text-zinc-400 animate-spin" />
        </div>
      ) : (
        <>
          {/* Document list */}
          <div className="space-y-1">
            {documents.map((doc) => {
              const itemStatus = doc.status === 'critical' || doc.status === 'expired' ? 'critical' :
                                doc.status === 'expiring' ? 'warning' : 'neutral';

              return (
                <ModuleItem
                  key={doc.id}
                  icon={
                    doc.status === 'critical' || doc.status === 'expired' ? (
                      <AlertTriangle className="h-4 w-4 text-red-500" />
                    ) : doc.status === 'expiring' ? (
                      <Calendar className="h-4 w-4 text-amber-500" />
                    ) : (
                      <CheckCircle className="h-4 w-4 text-zinc-400" />
                    )
                  }
                  title={doc.name}
                  subtitle={`Expires: ${doc.expiryDate}`}
                  status={itemStatus}
                  value={doc.daysUntil <= 7 ? `${doc.daysUntil}d` : `${doc.daysUntil} days`}
                  onClick={() => console.log('View doc:', doc.id)}
                  actions={
                    <ActionButton
                      action="view_document"
                      context={{ document_id: doc.id }}
                      size="sm"
                      iconOnly
                    />
                  }
                />
              );
            })}
          </div>

          {/* Summary */}
          <div className={cn(
            'mt-3 px-3 py-2 rounded-lg',
            'bg-zinc-100 dark:bg-zinc-800',
            'text-[12px] text-zinc-600 dark:text-zinc-400'
          )}>
            {stats.valid} of {stats.total} documents valid
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2 mt-4">
            <ActionButton
              action="view_document"
              size="sm"
            />
            <button className={cn(
              'px-3 py-1.5 rounded-lg',
              'text-[12px] font-medium',
              'text-celeste-accent hover:text-celeste-accent-hover',
              'hover:bg-celeste-accent-subtle dark:hover:bg-celeste-accent-subtle',
              'transition-colors'
            )}>
              View all →
            </button>
          </div>
        </>
      )}
    </ModuleContainer>
  );
}
