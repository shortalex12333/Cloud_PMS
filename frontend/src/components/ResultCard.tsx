'use client';

import { FileText, AlertTriangle, Wrench, Package, Activity } from 'lucide-react';
import MicroActions from './MicroActions';
import { cn } from '@/lib/utils';
import type { SearchResult, ResultCardType } from '@/types';

interface ResultCardProps {
  result: SearchResult;
}

export default function ResultCard({ result }: ResultCardProps) {
  const { type, title, subtitle, preview, score, actions } = result;

  // Get icon based on result type
  const getIcon = (cardType: ResultCardType) => {
    const iconClass = 'h-5 w-5';
    switch (cardType) {
      case 'document_chunk':
        return <FileText className={iconClass} />;
      case 'fault':
        return <AlertTriangle className={iconClass} />;
      case 'work_order':
        return <Wrench className={iconClass} />;
      case 'part':
        return <Package className={iconClass} />;
      case 'predictive':
        return <Activity className={iconClass} />;
      default:
        return <FileText className={iconClass} />;
    }
  };

  // Get color scheme based on type
  const getColorClass = (cardType: ResultCardType) => {
    switch (cardType) {
      case 'fault':
        return 'text-destructive';
      case 'predictive':
        return 'text-yellow-600';
      case 'work_order':
        return 'text-primary';
      default:
        return 'text-muted-foreground';
    }
  };

  return (
    <div className="bg-card border border-border rounded-lg p-4 hover:bg-accent/50 transition-colors cursor-pointer group">
      <div className="flex items-start gap-3">
        {/* Icon */}
        <div className={cn('mt-1', getColorClass(type))}>
          {getIcon(type)}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Title & Subtitle */}
          <div className="flex items-baseline gap-2 mb-1">
            <h3 className="font-medium text-foreground truncate">{title}</h3>
            {subtitle && (
              <span className="text-sm text-muted-foreground">
                {subtitle}
              </span>
            )}
          </div>

          {/* Preview Text */}
          {preview && (
            <p className="text-sm text-muted-foreground line-clamp-2 mb-3">
              {preview}
            </p>
          )}

          {/* Micro Actions */}
          <MicroActions actions={actions} resultId={result.id} />
        </div>

        {/* Score Badge (optional, can be hidden) */}
        {score && (
          <div className="text-xs text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity">
            {Math.round(score * 100)}%
          </div>
        )}
      </div>
    </div>
  );
}
