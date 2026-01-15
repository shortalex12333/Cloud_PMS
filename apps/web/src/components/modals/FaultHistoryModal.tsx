/**
 * FaultHistoryModal Component
 *
 * Displays fault history for equipment or specific fault.
 * Shows list of faults with severity breakdown and status.
 */

'use client';

import { useState, useEffect } from 'react';
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
  History,
  Loader2,
  AlertCircle,
  AlertTriangle,
  CheckCircle,
  Clock,
} from 'lucide-react';

interface FaultHistoryItem {
  id: string;
  fault_code?: string;
  title?: string;
  description?: string;
  severity: string;
  detected_at?: string;
  resolved_at?: string | null;
  is_active?: boolean;
  days_open?: number;
}

interface FaultHistorySummary {
  total: number;
  active: number;
  by_severity: {
    critical: number;
    high: number;
    medium: number;
    low: number;
  };
}

interface FaultHistoryModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  context: {
    entity_id: string;
    entity_type: 'fault' | 'equipment';
    entity_name?: string;
  };
  onSuccess?: (data: { faults: FaultHistoryItem[]; summary: FaultHistorySummary }) => void;
}

export function FaultHistoryModal({
  open,
  onOpenChange,
  context,
  onSuccess,
}: FaultHistoryModalProps) {
  const { executeAction, isLoading } = useActionHandler();
  const [faults, setFaults] = useState<FaultHistoryItem[]>([]);
  const [summary, setSummary] = useState<FaultHistorySummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadHistory = async () => {
    setError(null);

    const response = await executeAction(
      'view_fault_history',
      {
        entity_id: context.entity_id,
      },
      {
        successMessage: 'Fault history loaded',
        refreshData: false,
      }
    );

    if (response?.success && response.data) {
      setFaults(response.data.faults || []);
      setSummary(response.data.summary || null);

      if (onSuccess) {
        onSuccess({
          faults: response.data.faults || [],
          summary: response.data.summary,
        });
      }
    } else {
      setError(response?.error?.message || 'Failed to load fault history');
    }
  };

  // Load history when modal opens
  useEffect(() => {
    if (open && context.entity_id) {
      loadHistory();
    }
  }, [open, context.entity_id]);

  // Reset state when modal closes
  useEffect(() => {
    if (!open) {
      setFaults([]);
      setSummary(null);
      setError(null);
    }
  }, [open]);

  const getSeverityIcon = (severity: string) => {
    switch (severity?.toLowerCase()) {
      case 'critical':
        return <AlertCircle className="h-4 w-4 text-red-600" />;
      case 'high':
        return <AlertTriangle className="h-4 w-4 text-orange-600" />;
      case 'medium':
        return <AlertTriangle className="h-4 w-4 text-yellow-600" />;
      default:
        return <AlertCircle className="h-4 w-4 text-gray-400" />;
    }
  };

  const getSeverityBgColor = (severity: string) => {
    switch (severity?.toLowerCase()) {
      case 'critical':
        return 'bg-red-50 border-red-200';
      case 'high':
        return 'bg-orange-50 border-orange-200';
      case 'medium':
        return 'bg-yellow-50 border-yellow-200';
      default:
        return 'bg-gray-50 border-gray-200';
    }
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return 'Unknown';
    try {
      return new Date(dateStr).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <History className="h-5 w-5 text-blue-600" />
            Fault History
          </DialogTitle>
          <DialogDescription>
            {context.entity_name
              ? `Fault history for ${context.entity_name}`
              : 'View fault history'}
          </DialogDescription>
        </DialogHeader>

        {isLoading && faults.length === 0 && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
            <span className="ml-3 text-gray-600">Loading history...</span>
          </div>
        )}

        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-red-600 mt-0.5" />
              <div>
                <h4 className="font-medium text-red-800">Unable to load history</h4>
                <p className="text-sm text-red-700 mt-1">{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Summary */}
        {summary && (
          <div className="grid grid-cols-4 gap-3 p-3 bg-gray-50 rounded-lg">
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-900">{summary.total}</div>
              <div className="text-xs text-gray-500">Total</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-red-600">{summary.by_severity.critical}</div>
              <div className="text-xs text-gray-500">Critical</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-orange-600">{summary.by_severity.high}</div>
              <div className="text-xs text-gray-500">High</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">{summary.total - summary.active}</div>
              <div className="text-xs text-gray-500">Resolved</div>
            </div>
          </div>
        )}

        {/* Fault List */}
        {faults.length > 0 && (
          <div className="space-y-2 mt-4">
            {faults.map((fault) => (
              <div
                key={fault.id}
                className={`p-3 border rounded-lg ${getSeverityBgColor(fault.severity)}`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-2">
                    {getSeverityIcon(fault.severity)}
                    <div>
                      <h4 className="font-medium text-gray-900">
                        {fault.title || fault.fault_code || 'Fault'}
                      </h4>
                      {fault.description && (
                        <p className="text-sm text-gray-600 mt-0.5 line-clamp-2">
                          {fault.description}
                        </p>
                      )}
                      <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                        <span>Detected: {formatDate(fault.detected_at)}</span>
                        {fault.resolved_at && (
                          <span className="flex items-center gap-1">
                            <CheckCircle className="h-3 w-3 text-green-600" />
                            Resolved: {formatDate(fault.resolved_at)}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {fault.is_active ? (
                      <span className="px-2 py-0.5 text-xs font-medium bg-red-100 text-red-700 rounded">
                        Active
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 text-xs font-medium bg-green-100 text-green-700 rounded">
                        Resolved
                      </span>
                    )}
                    {fault.days_open !== undefined && fault.days_open > 0 && (
                      <span className="flex items-center gap-1 text-xs text-gray-500">
                        <Clock className="h-3 w-3" />
                        {fault.days_open}d
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* No faults */}
        {!isLoading && !error && faults.length === 0 && (
          <div className="text-center py-8 text-gray-500">
            <History className="h-12 w-12 mx-auto mb-3 text-gray-300" />
            <p>No fault history found</p>
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
