/**
 * HandoverItemCard Component
 *
 * Displays a handover item with:
 * - Category badge
 * - Priority indicator
 * - Summary text
 * - Metadata (added by, timestamp)
 * - Link to source entity
 *
 * Apple-inspired design matching FaultCard
 */

'use client';

import { useState } from 'react';
import {
  AlertCircle,
  Wrench,
  Settings,
  Package,
  File,
  ChevronRight,
  Clock,
  User,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface HandoverItem {
  id: string;
  entity_type: 'fault' | 'work_order' | 'equipment' | 'document_chunk' | 'part';
  entity_id: string;
  summary_text: string;
  category: 'ongoing_fault' | 'work_in_progress' | 'important_info' | 'equipment_status' | 'general';
  priority: number;  // 1-4 (low, normal, high, urgent)
  added_by_name: string;
  added_at: string;
}

interface HandoverItemCardProps {
  item: HandoverItem;
  onViewEntity?: (entityType: string, entityId: string) => void;
}

const ENTITY_ICONS = {
  fault: AlertCircle,
  work_order: Wrench,
  equipment: Settings,
  document_chunk: File,
  part: Package,
};

const ENTITY_LABELS = {
  fault: 'Fault',
  work_order: 'Work Order',
  equipment: 'Equipment',
  document_chunk: 'Document',
  part: 'Part',
};

const CATEGORY_LABELS = {
  ongoing_fault: 'Ongoing Fault',
  work_in_progress: 'Work in Progress',
  important_info: 'Important Info',
  equipment_status: 'Equipment Status',
  general: 'General',
};

const CATEGORY_COLORS = {
  ongoing_fault: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  work_in_progress: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  important_info: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  equipment_status: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  general: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400',
};

const PRIORITY_STYLES: Record<number, { dot: string; label: string }> = {
  1: { dot: 'bg-gray-400', label: 'Low' },
  2: { dot: 'bg-blue-500', label: 'Normal' },
  3: { dot: 'bg-orange-500', label: 'High' },
  4: { dot: 'bg-red-500', label: 'Urgent' },
};

export function HandoverItemCard({ item, onViewEntity }: HandoverItemCardProps) {
  const [expanded, setExpanded] = useState(false);

  const EntityIcon = ENTITY_ICONS[item.entity_type] || File;
  const priorityStyle = PRIORITY_STYLES[item.priority] || PRIORITY_STYLES[2];

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 60) {
      return `${diffMins}m ago`;
    } else if (diffHours < 24) {
      return `${diffHours}h ago`;
    } else if (diffDays < 7) {
      return `${diffDays}d ago`;
    } else {
      return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
      });
    }
  };

  const handleViewEntity = () => {
    if (onViewEntity) {
      onViewEntity(item.entity_type, item.entity_id);
    } else {
      // Default navigation logic
      console.log(`Navigate to ${item.entity_type}:${item.entity_id}`);
    }
  };

  // Truncate summary if too long
  const shouldTruncate = item.summary_text.length > 200;
  const displayText = expanded || !shouldTruncate
    ? item.summary_text
    : `${item.summary_text.slice(0, 200)}...`;

  return (
    <div className="celeste-card p-4 hover:shadow-[var(--shadow-md)] transition-shadow duration-200">
      <div className="flex items-start gap-3">
        {/* Priority Indicator */}
        <div className="flex flex-col items-center gap-2 pt-0.5">
          <span
            className={cn('w-2 h-2 rounded-full flex-shrink-0', priorityStyle.dot)}
            title={`${priorityStyle.label} Priority`}
          />
          <EntityIcon className="h-4 w-4 text-zinc-400" />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Category Badge */}
          <div className="flex items-center gap-2 mb-2">
            <span
              className={cn(
                'text-xs px-2 py-1 rounded-md font-medium',
                CATEGORY_COLORS[item.category]
              )}
            >
              {CATEGORY_LABELS[item.category]}
            </span>
            <span className="text-xs text-zinc-400">
              {ENTITY_LABELS[item.entity_type]}
            </span>
          </div>

          {/* Summary Text */}
          <p
            className={cn(
              'text-[14px] text-zinc-700 dark:text-zinc-300 whitespace-pre-wrap mb-3',
              !expanded && 'line-clamp-3'
            )}
          >
            {displayText}
          </p>

          {/* Expand/Collapse Toggle */}
          {shouldTruncate && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-[13px] text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 mb-3"
            >
              {expanded ? 'Show less' : 'Read more'}
            </button>
          )}

          {/* Metadata Row */}
          <div className="flex items-center gap-4 text-[12px] text-zinc-400 dark:text-zinc-500 mb-3">
            <div className="flex items-center gap-1">
              <User className="h-3 w-3" />
              <span>{item.added_by_name}</span>
            </div>
            <div className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              <span>{formatTimestamp(item.added_at)}</span>
            </div>
          </div>

          {/* View Entity Action */}
          <button
            onClick={handleViewEntity}
            className="celeste-button celeste-button-secondary h-8 px-3 text-[13px]"
          >
            View {ENTITY_LABELS[item.entity_type]}
            <ChevronRight className="h-3.5 w-3.5 ml-1" />
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * Example Usage:
 *
 * ```tsx
 * <HandoverItemCard
 *   item={{
 *     id: 'handover-123',
 *     entity_type: 'fault',
 *     entity_id: 'fault-456',
 *     summary_text: 'Generator 2 - MTU-OVHT-01\n\nCoolant temp high - occurred 8 times in last 30 days.\n\nTopped up coolant by 2L. Monitor in 2 hours.',
 *     category: 'ongoing_fault',
 *     priority: 3,
 *     added_by_name: 'John Smith',
 *     added_at: '2026-01-11T14:30:00Z',
 *   }}
 *   onViewEntity={(entityType, entityId) => {
 *     router.push(`/${entityType}/${entityId}`);
 *   }}
 * />
 * ```
 */
