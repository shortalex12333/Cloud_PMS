/**
 * SuggestPartsModal Component
 *
 * Displays parts suggested for fault repair.
 * Shows part inventory status and availability.
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
  Package,
  Loader2,
  AlertCircle,
  CheckCircle,
  AlertTriangle,
} from 'lucide-react';

interface SuggestedPart {
  id: string;
  name: string;
  part_number?: string;
  description?: string;
  category?: string;
  canonical_name?: string;
  stock_status?: 'IN_STOCK' | 'LOW_STOCK' | 'OUT_OF_STOCK' | 'UNKNOWN';
  is_available?: boolean;
}

interface PartsSummary {
  total_suggested: number;
  available: number;
  unavailable: number;
}

interface SuggestPartsModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  context: {
    fault_id: string;
    fault_title?: string;
  };
  onSuccess?: (data: { parts: SuggestedPart[]; summary: PartsSummary }) => void;
}

export function SuggestPartsModal({
  open,
  onOpenChange,
  context,
  onSuccess,
}: SuggestPartsModalProps) {
  const { executeAction, isLoading } = useActionHandler();
  const [parts, setParts] = useState<SuggestedPart[]>([]);
  const [summary, setSummary] = useState<PartsSummary | null>(null);
  const [faultCode, setFaultCode] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Load parts when modal opens
  useEffect(() => {
    if (!open || !context.fault_id) return;

    const loadSuggestedParts = async () => {
      setError(null);

      const response = await executeAction(
        'suggest_parts',
        {
          fault_id: context.fault_id,
        },
        {
          successMessage: 'Parts suggestions loaded',
          refreshData: false,
        }
      );

      if (response?.success && response.data) {
        setParts(response.data.suggested_parts || []);
        setSummary(response.data.summary || null);
        setFaultCode(response.data.fault_code || null);

        if (onSuccess) {
          onSuccess({
            parts: response.data.suggested_parts || [],
            summary: response.data.summary,
          });
        }
      } else {
        setError(response?.error?.message || 'Failed to load part suggestions');
      }
    };

    loadSuggestedParts();
  }, [open, context.fault_id, executeAction, onSuccess]);

  // Reset state when modal closes
  useEffect(() => {
    if (!open) {
      setParts([]);
      setSummary(null);
      setFaultCode(null);
      setError(null);
    }
  }, [open]);

  const getStockStatusIcon = (status?: string) => {
    switch (status) {
      case 'IN_STOCK':
        return <CheckCircle className="h-4 w-4 text-green-600" />;
      case 'LOW_STOCK':
        return <AlertTriangle className="h-4 w-4 text-yellow-600" />;
      case 'OUT_OF_STOCK':
        return <AlertCircle className="h-4 w-4 text-red-600" />;
      default:
        return <Package className="h-4 w-4 text-txt-tertiary" />;
    }
  };

  const getStockStatusBg = (status?: string) => {
    switch (status) {
      case 'IN_STOCK':
        return 'bg-green-50 border-green-200';
      case 'LOW_STOCK':
        return 'bg-yellow-50 border-yellow-200';
      case 'OUT_OF_STOCK':
        return 'bg-red-50 border-red-200';
      default:
        return 'bg-surface-primary border-surface-border';
    }
  };

  const getStockStatusLabel = (status?: string) => {
    switch (status) {
      case 'IN_STOCK':
        return 'In Stock';
      case 'LOW_STOCK':
        return 'Low Stock';
      case 'OUT_OF_STOCK':
        return 'Out of Stock';
      default:
        return 'Unknown';
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Package className="h-5 w-5 text-brand-interactive" />
            Suggested Parts
          </DialogTitle>
          <DialogDescription>
            {context.fault_title
              ? `Parts needed to repair: ${context.fault_title}`
              : 'Parts suggested for this fault'}
          </DialogDescription>
        </DialogHeader>

        {isLoading && parts.length === 0 && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-brand-interactive" />
            <span className="ml-3 text-txt-secondary">Loading suggestions...</span>
          </div>
        )}

        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-red-600 mt-0.5" />
              <div>
                <h4 className="font-medium text-red-800">Unable to load suggestions</h4>
                <p className="text-sm text-red-700 mt-1">{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Fault Code Info */}
        {faultCode && (
          <div className="p-3 bg-brand-interactive/10 border border-brand-interactive/30 rounded-lg">
            <p className="text-sm text-brand-interactive">
              <span className="font-medium">Fault Code:</span> {faultCode}
            </p>
          </div>
        )}

        {/* Summary */}
        {summary && (
          <div className="grid grid-cols-3 gap-3 p-3 bg-surface-primary rounded-lg">
            <div className="text-center">
              <div className="text-2xl font-bold text-txt-primary">{summary.total_suggested}</div>
              <div className="text-xs text-txt-tertiary">Total Parts</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">{summary.available}</div>
              <div className="text-xs text-txt-tertiary">Available</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-red-600">{summary.unavailable}</div>
              <div className="text-xs text-txt-tertiary">Need to Order</div>
            </div>
          </div>
        )}

        {/* Parts List */}
        {parts.length > 0 && (
          <div className="space-y-2 mt-4">
            {parts.map((part) => (
              <div
                key={part.id}
                className={`p-3 border rounded-lg ${getStockStatusBg(part.stock_status)}`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-2">
                    {getStockStatusIcon(part.stock_status)}
                    <div>
                      <h4 className="font-medium text-txt-primary">
                        {part.name || part.canonical_name || 'Unknown Part'}
                      </h4>
                      {part.part_number && (
                        <p className="text-sm text-txt-secondary mt-0.5">
                          P/N: {part.part_number}
                        </p>
                      )}
                      {part.description && (
                        <p className="text-sm text-txt-tertiary mt-1 line-clamp-2">
                          {part.description}
                        </p>
                      )}
                    </div>
                  </div>
                  <span
                    className={`px-2 py-0.5 text-xs font-medium rounded ${
                      part.stock_status === 'IN_STOCK'
                        ? 'bg-green-100 text-green-700'
                        : part.stock_status === 'LOW_STOCK'
                        ? 'bg-yellow-100 text-yellow-700'
                        : part.stock_status === 'OUT_OF_STOCK'
                        ? 'bg-red-100 text-red-700'
                        : 'bg-surface-elevated text-txt-secondary'
                    }`}
                  >
                    {getStockStatusLabel(part.stock_status)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* No parts */}
        {!isLoading && !error && parts.length === 0 && (
          <div className="text-center py-8 text-txt-tertiary">
            <Package className="h-12 w-12 mx-auto mb-3 text-surface-border" />
            <p>No parts suggestions available</p>
            <p className="text-sm mt-1">This fault may not have associated parts in the system</p>
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-2 pt-4 border-t mt-4">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
          {summary && summary.unavailable > 0 && (
            <Button variant="default">
              Order Missing Parts
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
