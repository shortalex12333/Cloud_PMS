// @ts-nocheck - Phase 4: Zod v4/hookform resolver compatibility
/**
 * CreateMonthlySignoffModal Component
 *
 * Modal for creating new monthly HOR sign-offs
 * MLC 2006 compliance - initiate monthly crew rest compliance certification
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
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useActionHandler } from '@/hooks/useActionHandler';
import {
  FilePlus,
  Loader2,
  Calendar,
  Users,
  Info,
} from 'lucide-react';

// Validation schema
const createMonthlySignoffSchema = z.object({
  month: z.string().min(1, 'Month is required').regex(/^\d{4}-\d{2}$/, 'Month must be in YYYY-MM format'),
  department: z.enum(['deck', 'engine', 'interior'], {
    required_error: 'Department is required',
  }),
});

type CreateMonthlySignoffFormData = z.infer<typeof createMonthlySignoffSchema>;

interface CreateMonthlySignoffModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

const DEPARTMENTS = [
  { value: 'deck', label: 'Deck Department', icon: '⚓' },
  { value: 'engine', label: 'Engine Department', icon: '⚙️' },
  { value: 'interior', label: 'Interior Department', icon: '🏠' },
];

export function CreateMonthlySignoffModal({
  open,
  onOpenChange,
  onSuccess,
}: CreateMonthlySignoffModalProps) {
  const { executeAction, isLoading } = useActionHandler();

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
    reset,
  } = useForm<CreateMonthlySignoffFormData>({
    resolver: zodResolver(createMonthlySignoffSchema),
    defaultValues: {
      month: new Date().toISOString().slice(0, 7), // Current month YYYY-MM
      department: undefined,
    },
  });

  const selectedDepartment = watch('department');

  const onSubmit = async (data: CreateMonthlySignoffFormData) => {
    const response = await executeAction(
      'create_monthly_signoff',
      {
        month: data.month,
        department: data.department,
      },
      {
        successMessage: `Monthly signoff created for ${data.department} department`,
        refreshData: true,
      }
    );

    if (response?.success) {
      reset();
      onOpenChange(false);
      onSuccess?.();
    }
  };

  const handleClose = () => {
    reset();
    onOpenChange(false);
  };

  // Generate month options (current month + 2 months before and after)
  const getMonthOptions = () => {
    const options: string[] = [];
    const now = new Date();
    for (let i = -2; i <= 2; i++) {
      const date = new Date(now.getFullYear(), now.getMonth() + i, 1);
      options.push(date.toISOString().slice(0, 7));
    }
    return options;
  };

  const formatMonth = (monthStr: string) => {
    const [year, month] = monthStr.split('-');
    const date = new Date(parseInt(year), parseInt(month) - 1, 1);
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'long' });
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FilePlus className="h-5 w-5 text-blue-500" />
            Create Monthly Signoff
          </DialogTitle>
          <DialogDescription>
            Initiate a new monthly hours of rest compliance certificate
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
          {/* Info Box */}
          <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg flex gap-3">
            <Info className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-blue-800">
              <p className="font-medium mb-1">MLC 2006 Compliance</p>
              <p>
                Monthly signoffs certify that crew members have received adequate rest periods.
                This requires signatures from crew, HOD, and captain.
              </p>
            </div>
          </div>

          {/* Month Selection */}
          <div className="space-y-2">
            <Label htmlFor="month" className="flex items-center gap-2">
              <Calendar className="h-4 w-4 text-celeste-text-disabled" />
              Month *
            </Label>
            <Select
              value={watch('month')}
              onValueChange={(value) => setValue('month', value)}
            >
              <SelectTrigger className={errors.month ? 'border-red-500' : ''}>
                <SelectValue placeholder="Select month" />
              </SelectTrigger>
              <SelectContent>
                {getMonthOptions().map((month) => (
                  <SelectItem key={month} value={month}>
                    {formatMonth(month)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {errors.month && (
              <p className="text-sm text-red-600">{errors.month.message}</p>
            )}
          </div>

          {/* Department Selection */}
          <div className="space-y-2">
            <Label htmlFor="department" className="flex items-center gap-2">
              <Users className="h-4 w-4 text-celeste-text-disabled" />
              Department *
            </Label>
            <div className="grid grid-cols-1 gap-2">
              {DEPARTMENTS.map((dept) => (
                <button
                  key={dept.value}
                  type="button"
                  onClick={() => setValue('department', dept.value as any)}
                  className={`
                    p-4 rounded-lg border-2 transition-all
                    flex items-center gap-3
                    ${selectedDepartment === dept.value
                      ? 'border-blue-500 bg-blue-50 ring-2 ring-blue-500 ring-offset-2'
                      : 'border-celeste-border hover:border-celeste-border bg-white'
                    }
                  `}
                >
                  <span className="text-2xl">{dept.icon}</span>
                  <div className="flex-1 text-left">
                    <p className={`font-medium ${
                      selectedDepartment === dept.value
                        ? 'text-blue-900'
                        : 'text-celeste-black'
                    }`}>
                      {dept.label}
                    </p>
                  </div>
                </button>
              ))}
            </div>
            {errors.department && (
              <p className="text-sm text-red-600">{errors.department.message}</p>
            )}
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button
              type="button"
              variant="outline"
              onClick={handleClose}
              disabled={isLoading}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={isLoading || !selectedDepartment}
              className="bg-blue-600 hover:bg-blue-700"
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Creating...
                </>
              ) : (
                <>
                  <FilePlus className="h-4 w-4 mr-2" />
                  Create Signoff
                </>
              )}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
