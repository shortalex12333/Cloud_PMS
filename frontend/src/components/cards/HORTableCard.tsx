/**
 * HORTableCard Component
 *
 * Displays Hours of Rest table with compliance status
 */

'use client';

import { Clock, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { ActionButton } from '@/components/actions/ActionButton';
import { cn } from '@/lib/utils';
import type { MicroAction } from '@/types/actions';

interface HORTableCardProps {
  horData: {
    crew_member_id: string;
    crew_member_name: string;
    entries: {
      date: string;
      rest_hours: number;
      work_hours: number;
      is_compliant: boolean;
    }[];
    summary: {
      total_rest_hours: number;
      total_work_hours: number;
      compliance_rate: number;
      non_compliant_days: number;
    };
  };
  actions?: MicroAction[];
}

export function HORTableCard({ horData, actions = [] }: HORTableCardProps) {
  const isCompliant = horData.summary.compliance_rate >= 95;

  return (
    <div className="bg-card border border-border rounded-lg p-4 hover:bg-accent/50 transition-colors">
      <div className="flex items-start gap-3">
        {/* HOR Icon */}
        <div className={cn('mt-1', isCompliant ? 'text-green-600' : 'text-orange-600')}>
          {isCompliant ? (
            <CheckCircle2 className="h-5 w-5" />
          ) : (
            <AlertTriangle className="h-5 w-5" />
          )}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Crew Member & Compliance */}
          <div className="flex items-center gap-2 mb-3 flex-wrap">
            <h3 className="font-medium text-foreground">
              {horData.crew_member_name}
            </h3>
            <span
              className={cn(
                'text-xs px-2 py-0.5 rounded-full border font-medium',
                isCompliant
                  ? 'text-green-700 bg-green-50 border-green-200'
                  : 'text-orange-700 bg-orange-50 border-orange-200'
              )}
            >
              {horData.summary.compliance_rate.toFixed(0)}% compliant
            </span>
          </div>

          {/* Summary Stats */}
          <div className="grid grid-cols-2 gap-3 mb-3">
            <div>
              <p className="text-xs text-muted-foreground">Rest Hours (30d)</p>
              <p className="text-sm font-medium">
                {horData.summary.total_rest_hours}h
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Work Hours (30d)</p>
              <p className="text-sm font-medium">
                {horData.summary.total_work_hours}h
              </p>
            </div>
          </div>

          {/* Non-Compliant Days Warning */}
          {horData.summary.non_compliant_days > 0 && (
            <div className="flex items-center gap-1.5 text-sm text-orange-600 mb-3 bg-orange-50 border border-orange-200 rounded p-2">
              <AlertTriangle className="h-4 w-4" />
              <span>
                {horData.summary.non_compliant_days} non-compliant day(s) in last 30 days
              </span>
            </div>
          )}

          {/* Recent Entries (Last 7 days) */}
          <div className="mb-3">
            <p className="text-xs font-medium text-muted-foreground uppercase mb-2">
              Recent Entries
            </p>
            <div className="space-y-1">
              {horData.entries.slice(0, 7).map((entry, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between text-xs py-1 border-b border-muted"
                >
                  <span className="text-muted-foreground">
                    {new Date(entry.date).toLocaleDateString('en-US', {
                      month: 'short',
                      day: 'numeric',
                    })}
                  </span>
                  <span className="font-medium">
                    Rest: {entry.rest_hours}h | Work: {entry.work_hours}h
                  </span>
                  <span>
                    {entry.is_compliant ? (
                      <CheckCircle2 className="h-3.5 w-3.5 text-green-600" />
                    ) : (
                      <AlertTriangle className="h-3.5 w-3.5 text-orange-600" />
                    )}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Actions */}
          <div className="flex flex-wrap gap-2">
            {actions.map((action) => (
              <ActionButton
                key={action}
                action={action}
                context={{ user_id: horData.crew_member_id }}
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
