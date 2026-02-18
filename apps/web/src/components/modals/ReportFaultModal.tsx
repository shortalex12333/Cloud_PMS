/**
 * ReportFaultModal Component
 *
 * Modal for reporting equipment faults
 * High-priority CREATE action for Phase 4
 */

'use client';

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { useActionHandler } from '@/hooks/useActionHandler';
import { AlertCircle } from 'lucide-react';

// Validation schema
const reportFaultSchema = z.object({
  equipment_id: z.string().optional(),
  title: z.string().min(5, 'Title must be at least 5 characters'),
  description: z.string().min(20, 'Description must be at least 20 characters'),
  severity: z.enum(['low', 'medium', 'high', 'critical']),
  deck: z.string().optional(),
  room: z.string().optional(),
  create_work_order: z.boolean().optional(),
});

type ReportFaultFormData = z.infer<typeof reportFaultSchema>;

interface ReportFaultModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  context?: {
    equipment_id?: string;
    equipment_name?: string;
    suggested_title?: string;
    deck?: string;
    room?: string;
  };
  onSuccess?: (fault_id: string) => void;
}

export function ReportFaultModal({
  open,
  onOpenChange,
  context = {},
  onSuccess,
}: ReportFaultModalProps) {
  const { executeAction, isLoading } = useActionHandler();

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
  } = useForm<ReportFaultFormData>({
    resolver: zodResolver(reportFaultSchema) as any,
    defaultValues: {
      equipment_id: context.equipment_id || '',
      title: context.suggested_title || '',
      description: '',
      severity: 'medium',
      deck: context.deck || '',
      room: context.room || '',
      create_work_order: false,
    },
  });

  const severity = watch('severity');
  const createWorkOrder = watch('create_work_order');

  const onSubmit = async (data: ReportFaultFormData) => {
    const response = await executeAction(
      'report_fault',
      {
        ...data,
        // If equipment is pre-selected from context
        equipment_name: context.equipment_name,
      },
      {
        successMessage: `Fault reported successfully${
          data.create_work_order ? ' and work order created' : ''
        }`,
        refreshData: true,
      }
    );

    if (response?.success) {
      onOpenChange(false);
      if (onSuccess) {
        onSuccess(response.data?.fault_id);
      }
    }
  };

  const getSeverityColor = (sev: string) => {
    switch (sev) {
      case 'critical':
        return 'text-red-700 bg-red-50 border-red-300';
      case 'high':
        return 'text-orange-700 bg-orange-50 border-orange-300';
      case 'medium':
        return 'text-yellow-700 bg-yellow-50 border-yellow-300';
      case 'low':
        return 'text-green-700 bg-green-50 border-green-300';
      default:
        return 'text-txt-secondary bg-surface-primary border-surface-border';
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-orange-600" />
            Report Fault
          </DialogTitle>
          <DialogDescription>
            Report an equipment fault or issue. Provide detailed information to help with
            diagnosis and resolution.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit as any)} className="space-y-4">
          {/* Equipment (if pre-selected) */}
          {context.equipment_name && (
            <div className="p-3 bg-brand-interactive/5 border border-brand-interactive/20 rounded-md">
              <p className="text-sm font-medium text-brand-interactive">
                Equipment: {context.equipment_name}
              </p>
            </div>
          )}

          {/* Title */}
          <div className="space-y-2">
            <Label htmlFor="title">
              Fault Title <span className="text-red-500">*</span>
            </Label>
            <Input
              id="title"
              {...register('title')}
              placeholder="Brief summary of the issue"
              className={errors.title ? 'border-red-500' : ''}
            />
            {errors.title && (
              <p className="text-sm text-red-600">{errors.title.message}</p>
            )}
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="description">
              Description <span className="text-red-500">*</span>
            </Label>
            <Textarea
              id="description"
              {...register('description')}
              placeholder="Detailed description of the fault, symptoms, and any relevant observations..."
              rows={5}
              className={errors.description ? 'border-red-500' : ''}
            />
            {errors.description && (
              <p className="text-sm text-red-600">{errors.description.message}</p>
            )}
            <p className="text-xs text-txt-tertiary">
              Include details like when it started, frequency, conditions, etc.
            </p>
          </div>

          {/* Severity */}
          <div className="space-y-2">
            <Label htmlFor="severity">
              Severity <span className="text-red-500">*</span>
            </Label>
            <Select
              value={severity}
              onValueChange={(value) =>
                setValue('severity', value as any)
              }
            >
              <SelectTrigger className={getSeverityColor(severity)}>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="low">
                  <span className="flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-green-500" />
                    Low - Minor issue, no immediate impact
                  </span>
                </SelectItem>
                <SelectItem value="medium">
                  <span className="flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-yellow-500" />
                    Medium - Affects performance, needs attention
                  </span>
                </SelectItem>
                <SelectItem value="high">
                  <span className="flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-orange-500" />
                    High - Significant impact, urgent repair needed
                  </span>
                </SelectItem>
                <SelectItem value="critical">
                  <span className="flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-red-500" />
                    Critical - Safety issue or system down
                  </span>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Location */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="deck">Deck</Label>
              <Input
                id="deck"
                {...register('deck')}
                placeholder="e.g., Main Deck"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="room">Room/Location</Label>
              <Input
                id="room"
                {...register('room')}
                placeholder="e.g., Engine Room"
              />
            </div>
          </div>

          {/* Create Work Order Option */}
          <div className="flex items-center space-x-2 p-3 bg-surface-primary rounded-md">
            <Checkbox
              id="create_work_order"
              checked={createWorkOrder}
              onCheckedChange={(checked) =>
                setValue('create_work_order', checked as boolean)
              }
            />
            <Label
              htmlFor="create_work_order"
              className="text-sm font-normal cursor-pointer"
            >
              Automatically create a work order for this fault
            </Label>
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isLoading}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isLoading}>
              {isLoading ? 'Reporting...' : 'Report Fault'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
