// @ts-nocheck - Phase 4: Zod v4/hookform resolver compatibility
/**
 * MonthlySignoffModal Component
 *
 * Modal for viewing and signing monthly HOR sign-offs
 * MLC 2006 compliance - monthly crew rest compliance certification
 */

'use client';

import { useState, useEffect } from 'react';
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
import { Textarea } from '@/components/ui/textarea';
import { useActionHandler } from '@/hooks/useActionHandler';
import {
  FileSignature,
  Loader2,
  Calendar,
  User,
  CheckCircle2,
  AlertCircle,
  Shield,
  Clock,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Validation schema for signing
const signMonthlySignoffSchema = z.object({
  signoff_id: z.string().min(1, 'Signoff ID is required'),
  signature_level: z.enum(['crew', 'hod', 'captain']),
  signature_type: z.enum(['electronic', 'wet', 'delegated']),
});

type SignMonthlySignoffFormData = z.infer<typeof signMonthlySignoffSchema>;

interface MonthlySignoffModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  signoffId: string;
  mode: 'view' | 'sign';
  onSuccess?: () => void;
}

interface SignoffData {
  id: string;
  month: string;
  department: string;
  user_id: string;
  user_name?: string;
  crew_signature?: {
    signed_at: string;
    signature_type: string;
  };
  hod_signature?: {
    signed_at: string;
    signature_type: string;
  };
  captain_signature?: {
    signed_at: string;
    signature_type: string;
  };
  total_days: number;
  compliant_days: number;
  non_compliant_days: number;
  created_at: string;
}

export function MonthlySignoffModal({
  open,
  onOpenChange,
  signoffId,
  mode,
  onSuccess,
}: MonthlySignoffModalProps) {
  const { executeAction, isLoading } = useActionHandler();
  const [signoffData, setSignoffData] = useState<SignoffData | null>(null);
  const [loadingData, setLoadingData] = useState(false);
  const [signatureLevel, setSignatureLevel] = useState<'crew' | 'hod' | 'captain'>('crew');

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
    setValue,
  } = useForm<SignMonthlySignoffFormData>({
    resolver: zodResolver(signMonthlySignoffSchema),
    defaultValues: {
      signoff_id: signoffId,
      signature_level: 'crew',
      signature_type: 'electronic',
    },
  });

  // Load signoff data when modal opens
  useEffect(() => {
    if (open && signoffId) {
      loadSignoffData();
    }
  }, [open, signoffId]);

  const loadSignoffData = async () => {
    setLoadingData(true);
    try {
      const response = await executeAction(
        'get_monthly_signoff',
        { signoff_id: signoffId },
        { silent: true }
      );

      if (response?.success && response.data) {
        setSignoffData(response.data);
      }
    } catch (error) {
      console.error('Failed to load signoff data:', error);
    } finally {
      setLoadingData(false);
    }
  };

  const onSubmit = async (data: SignMonthlySignoffFormData) => {
    const response = await executeAction(
      'sign_monthly_signoff',
      {
        signoff_id: data.signoff_id,
        signature_level: data.signature_level,
        signature_data: {
          signed_at: new Date().toISOString(),
          signature_type: data.signature_type,
          signature_hash: `${data.signature_level}_${Date.now()}`,
        },
      },
      {
        successMessage: `Monthly signoff signed as ${data.signature_level}`,
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
    setSignoffData(null);
    onOpenChange(false);
  };

  const compliancePercent = signoffData
    ? Math.round((signoffData.compliant_days / signoffData.total_days) * 100)
    : 0;
  const isCompliant = compliancePercent >= 90; // 90% threshold for overall compliance

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileSignature className="h-5 w-5 text-blue-500" />
            {mode === 'sign' ? 'Sign Monthly Signoff' : 'Monthly Signoff Details'}
          </DialogTitle>
          <DialogDescription>
            MLC 2006 Monthly Hours of Rest Compliance Certificate
          </DialogDescription>
        </DialogHeader>

        {loadingData ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-celeste-text-muted" />
          </div>
        ) : signoffData ? (
          <div className="space-y-5">
            {/* Compliance Status */}
            <div className={cn(
              'p-4 rounded-lg border flex items-center gap-3',
              isCompliant
                ? 'bg-emerald-50 border-emerald-200'
                : 'bg-amber-50 border-amber-200'
            )}>
              {isCompliant ? (
                <CheckCircle2 className="h-6 w-6 text-emerald-600" />
              ) : (
                <AlertCircle className="h-6 w-6 text-amber-600" />
              )}
              <div className="flex-1">
                <p className={cn(
                  'font-semibold text-lg',
                  isCompliant ? 'text-emerald-800' : 'text-amber-800'
                )}>
                  {compliancePercent}% Compliant
                </p>
                <p className={cn(
                  'text-sm',
                  isCompliant ? 'text-emerald-700' : 'text-amber-700'
                )}>
                  {signoffData.compliant_days} compliant days out of {signoffData.total_days} total days
                </p>
              </div>
            </div>

            {/* Period Info */}
            <div className="grid grid-cols-2 gap-4">
              <div className="p-3 bg-celeste-bg-primary border border-celeste-border rounded-lg">
                <div className="flex items-center gap-2 text-celeste-text-secondary mb-1">
                  <Calendar className="h-4 w-4" />
                  <span className="text-xs font-medium uppercase">Period</span>
                </div>
                <p className="text-lg font-semibold text-celeste-black">
                  {signoffData.month}
                </p>
              </div>
              <div className="p-3 bg-celeste-bg-primary border border-celeste-border rounded-lg">
                <div className="flex items-center gap-2 text-celeste-text-secondary mb-1">
                  <User className="h-4 w-4" />
                  <span className="text-xs font-medium uppercase">Department</span>
                </div>
                <p className="text-lg font-semibold text-celeste-black capitalize">
                  {signoffData.department}
                </p>
              </div>
            </div>

            {/* Signature Status */}
            <div className="space-y-3">
              <Label className="flex items-center gap-2">
                <Shield className="h-4 w-4 text-celeste-text-disabled" />
                Signature Chain
              </Label>
              <div className="space-y-2">
                {/* Crew Signature */}
                <div className={cn(
                  'p-3 rounded-lg border flex items-center gap-3',
                  signoffData.crew_signature
                    ? 'bg-emerald-50 border-emerald-200'
                    : 'bg-celeste-bg-primary border-celeste-border'
                )}>
                  {signoffData.crew_signature ? (
                    <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                  ) : (
                    <Clock className="h-5 w-5 text-celeste-text-muted" />
                  )}
                  <div className="flex-1">
                    <p className="font-medium text-sm text-celeste-black">Crew Member</p>
                    {signoffData.crew_signature && (
                      <p className="text-xs text-celeste-text-secondary">
                        Signed {new Date(signoffData.crew_signature.signed_at).toLocaleString()} ({signoffData.crew_signature.signature_type})
                      </p>
                    )}
                  </div>
                </div>

                {/* HOD Signature */}
                <div className={cn(
                  'p-3 rounded-lg border flex items-center gap-3',
                  signoffData.hod_signature
                    ? 'bg-emerald-50 border-emerald-200'
                    : 'bg-celeste-bg-primary border-celeste-border'
                )}>
                  {signoffData.hod_signature ? (
                    <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                  ) : (
                    <Clock className="h-5 w-5 text-celeste-text-muted" />
                  )}
                  <div className="flex-1">
                    <p className="font-medium text-sm text-celeste-black">Head of Department</p>
                    {signoffData.hod_signature && (
                      <p className="text-xs text-celeste-text-secondary">
                        Signed {new Date(signoffData.hod_signature.signed_at).toLocaleString()} ({signoffData.hod_signature.signature_type})
                      </p>
                    )}
                  </div>
                </div>

                {/* Captain Signature */}
                <div className={cn(
                  'p-3 rounded-lg border flex items-center gap-3',
                  signoffData.captain_signature
                    ? 'bg-emerald-50 border-emerald-200'
                    : 'bg-celeste-bg-primary border-celeste-border'
                )}>
                  {signoffData.captain_signature ? (
                    <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                  ) : (
                    <Clock className="h-5 w-5 text-celeste-text-muted" />
                  )}
                  <div className="flex-1">
                    <p className="font-medium text-sm text-celeste-black">Captain</p>
                    {signoffData.captain_signature && (
                      <p className="text-xs text-celeste-text-secondary">
                        Signed {new Date(signoffData.captain_signature.signed_at).toLocaleString()} ({signoffData.captain_signature.signature_type})
                      </p>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Signing Form (only in sign mode) */}
            {mode === 'sign' && (
              <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 pt-4 border-t">
                <div className="space-y-2">
                  <Label>Signature Level</Label>
                  <div className="flex gap-2">
                    {['crew', 'hod', 'captain'].map((level) => (
                      <button
                        key={level}
                        type="button"
                        onClick={() => {
                          setSignatureLevel(level as any);
                          setValue('signature_level', level as any);
                        }}
                        className={cn(
                          'px-4 py-2 rounded-lg border-2 transition-all',
                          'flex items-center gap-2 text-sm font-medium capitalize',
                          signatureLevel === level
                            ? 'border-blue-500 bg-blue-50 text-blue-700 ring-2 ring-blue-500 ring-offset-2'
                            : 'border-celeste-border text-celeste-text-secondary hover:border-celeste-border'
                        )}
                      >
                        {level}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
                  <p className="text-sm text-amber-800">
                    <Shield className="inline h-4 w-4 mr-1" />
                    By signing, you certify that the hours of rest records are accurate and comply with MLC 2006.
                    This signature is legally binding and will be recorded in the audit log.
                  </p>
                </div>

                <div className="flex justify-end gap-2">
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
                    disabled={isLoading}
                    className="bg-blue-600 hover:bg-blue-700"
                  >
                    {isLoading ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Signing...
                      </>
                    ) : (
                      <>
                        <FileSignature className="h-4 w-4 mr-2" />
                        Sign as {signatureLevel}
                      </>
                    )}
                  </Button>
                </div>
              </form>
            )}

            {/* View Mode Actions */}
            {mode === 'view' && (
              <div className="flex justify-end pt-4 border-t">
                <Button onClick={handleClose} variant="outline">
                  Close
                </Button>
              </div>
            )}
          </div>
        ) : (
          <div className="py-12 text-center text-celeste-text-disabled">
            <AlertCircle className="h-12 w-12 mx-auto mb-3 text-celeste-text-muted" />
            <p>Failed to load signoff data</p>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
