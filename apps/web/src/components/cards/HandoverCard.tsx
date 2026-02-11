/**
 * HandoverCard Component
 *
 * Displays handover information with sections and priority items
 */

'use client';

import { FileText, AlertCircle, Users } from 'lucide-react';
import { ActionButton } from '@/components/actions/ActionButton';
import { cn } from '@/lib/utils';
import { formatDate } from '@/lib/utils';
import type { MicroAction } from '@/types/actions';

interface HandoverCardProps {
  handover: {
    id: string;
    date: string;
    shift: 'day' | 'night' | 'morning' | 'afternoon';
    from_user?: string;
    to_user?: string;
    sections: {
      section: string;
      items: {
        id: string;
        content: string;
        priority: 'low' | 'medium' | 'high';
        entity_type?: string;
        entity_id?: string;
      }[];
    }[];
    summary?: string;
  };
  actions?: MicroAction[];
}

export function HandoverCard({ handover, actions = [] }: HandoverCardProps) {
  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'text-restricted-red';
      case 'medium':
        return 'text-restricted-yellow';
      default:
        return 'text-celeste-text-secondary';
    }
  };

  const highPriorityCount = handover.sections.reduce(
    (count, section) =>
      count + section.items.filter((item) => item.priority === 'high').length,
    0
  );

  return (
    <div className="bg-card border border-border rounded-lg p-4 hover:bg-accent/50 transition-colors">
      <div className="flex items-start gap-3">
        {/* Handover Icon */}
        <div className="mt-1 text-primary">
          <FileText className="h-5 w-5" />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Date & Shift */}
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            <h3 className="font-medium text-foreground">
              {formatDate(handover.date)} - {handover.shift}
            </h3>
            {highPriorityCount > 0 && (
              <span className="text-xs px-2 py-0.5 rounded-full border border-restricted-red/30 bg-restricted-red/10 text-restricted-red font-medium">
                {highPriorityCount} high priority
              </span>
            )}
          </div>

          {/* From/To */}
          {(handover.from_user || handover.to_user) && (
            <div className="flex items-center gap-1.5 text-sm text-muted-foreground mb-3">
              <Users className="h-4 w-4" />
              {handover.from_user && <span>From: {handover.from_user}</span>}
              {handover.from_user && handover.to_user && <span>→</span>}
              {handover.to_user && <span>To: {handover.to_user}</span>}
            </div>
          )}

          {/* Summary */}
          {handover.summary && (
            <p className="text-sm text-muted-foreground mb-3 italic">
              "{handover.summary}"
            </p>
          )}

          {/* Sections */}
          <div className="space-y-2 mb-3">
            {handover.sections.map((section, idx) => (
              <div key={idx} className="border-l-2 border-muted pl-3">
                <p className="text-xs font-medium text-muted-foreground uppercase mb-1">
                  {section.section}
                </p>
                <ul className="space-y-1">
                  {section.items.slice(0, 3).map((item) => (
                    <li
                      key={item.id}
                      className="text-sm flex items-start gap-1.5"
                    >
                      {item.priority === 'high' && (
                        <AlertCircle className="h-4 w-4 text-restricted-red mt-0.5" />
                      )}
                      <span className={getPriorityColor(item.priority)}>
                        {item.content}
                      </span>
                    </li>
                  ))}
                  {section.items.length > 3 && (
                    <li className="text-xs text-muted-foreground">
                      +{section.items.length - 3} more items
                    </li>
                  )}
                </ul>
              </div>
            ))}
          </div>

          {/* Actions */}
          <div className="flex flex-wrap gap-2">
            {actions.map((action) => (
              <ActionButton
                key={action}
                action={action}
                context={{ handover_id: handover.id }}
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
