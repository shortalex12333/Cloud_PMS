/**
 * DiagnoseFaultModal Component
 *
 * RAG-powered modal for AI-assisted fault diagnosis
 * Streams AI analysis, shows similar past faults, suggests parts
 * Phase 4 - Advanced RAG Modal
 */

'use client';

import { useState, useEffect, useRef } from 'react';
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
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { useActionHandler } from '@/hooks/useActionHandler';
import {
  Brain,
  Loader2,
  AlertCircle,
  Wrench,
  Package,
  FileText,
  CheckCircle,
  Info,
} from 'lucide-react';

// Validation schema
const diagnoseFaultSchema = z.object({
  fault_id: z.string().min(1, 'Fault ID is required'),
  additional_context: z.string().optional(),
  create_work_order_from_diagnosis: z.boolean().optional(),
});

type DiagnoseFaultFormData = z.infer<typeof diagnoseFaultSchema>;

// Mock similar fault type
type SimilarFault = {
  id: string;
  title: string;
  resolution: string;
  similarity_score: number;
  resolved_days_ago: number;
};

// Mock suggested part type
type SuggestedPart = {
  part_name: string;
  part_number: string;
  reason: string;
  confidence: number;
};

interface DiagnoseFaultModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  context: {
    fault_id: string;
    fault_title: string;
    fault_description: string;
    severity: string;
    equipment_name?: string;
    equipment_model?: string;
  };
  onSuccess?: (diagnosis: any) => void;
}

export function DiagnoseFaultModal({
  open,
  onOpenChange,
  context,
  onSuccess,
}: DiagnoseFaultModalProps) {
  const { executeAction, isLoading } = useActionHandler();
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamedDiagnosis, setStreamedDiagnosis] = useState('');
  const [similarFaults, setSimilarFaults] = useState<SimilarFault[]>([]);
  const [suggestedParts, setSuggestedParts] = useState<SuggestedPart[]>([]);
  const [manualReferences, setManualReferences] = useState<string[]>([]);
  const diagnosisRef = useRef<HTMLDivElement>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
  } = useForm<DiagnoseFaultFormData>({
    resolver: zodResolver(diagnoseFaultSchema) as any,
    defaultValues: {
      fault_id: context.fault_id,
      additional_context: '',
      create_work_order_from_diagnosis: false,
    },
  });

  const createWorkOrder = watch('create_work_order_from_diagnosis');

  // Mock streaming function - in production, this would connect to n8n SSE endpoint
  const simulateStreaming = async () => {
    setIsStreaming(true);
    setStreamedDiagnosis('');

    // Mock diagnosis text that streams in
    const fullDiagnosis = `Based on the fault description "${context.fault_description}" for ${context.equipment_name || 'the equipment'}, here is my analysis:

## Root Cause Analysis
The symptoms described are consistent with a degraded cooling system component, likely the thermostat or coolant circulation pump. The ${context.equipment_model || 'equipment'} model is known to experience this issue after extended operation.

## Recommended Actions
1. **Immediate**: Check coolant levels and inspect for visible leaks
2. **Short-term**: Test thermostat operation and replace if faulty
3. **Long-term**: Inspect coolant pump bearings and seals

## Parts Likely Needed
- Thermostat assembly (P/N varies by model)
- Coolant pump seal kit
- Coolant fluid (2-3 gallons)

## Safety Considerations
⚠️ Allow engine to cool completely before inspection. Use proper PPE when handling coolant.

## Estimated Time
Diagnosis: 30-45 minutes
Repair (if thermostat): 2-3 hours
Repair (if pump): 4-6 hours`;

    // Simulate streaming by adding words over time
    const words = fullDiagnosis.split(' ');
    for (let i = 0; i < words.length; i++) {
      await new Promise((resolve) => setTimeout(resolve, 50));
      setStreamedDiagnosis((prev) => prev + (i > 0 ? ' ' : '') + words[i]);

      // Auto-scroll to bottom
      if (diagnosisRef.current) {
        diagnosisRef.current.scrollTop = diagnosisRef.current.scrollHeight;
      }
    }

    // Load similar faults after diagnosis completes
    setSimilarFaults([
      {
        id: 'f-123',
        title: 'Engine overheating - port side',
        resolution: 'Replaced thermostat',
        similarity_score: 0.94,
        resolved_days_ago: 45,
      },
      {
        id: 'f-456',
        title: 'Coolant temperature warning',
        resolution: 'Coolant pump seal replacement',
        similarity_score: 0.87,
        resolved_days_ago: 120,
      },
      {
        id: 'f-789',
        title: 'Engine running hot',
        resolution: 'Low coolant level - topped up',
        similarity_score: 0.82,
        resolved_days_ago: 30,
      },
    ]);

    // Load suggested parts
    setSuggestedParts([
      {
        part_name: 'Thermostat Assembly',
        part_number: 'THERMO-C32-01',
        reason: 'Most common cause of overheating in this model',
        confidence: 0.89,
      },
      {
        part_name: 'Coolant Pump Seal Kit',
        part_number: 'SEAL-PUMP-02',
        reason: 'Secondary likely cause based on similar faults',
        confidence: 0.72,
      },
    ]);

    // Load manual references
    setManualReferences([
      'Section 4.2: Cooling System Maintenance',
      'Section 7.1: Thermostat Replacement Procedure',
      'Section 12.5: Troubleshooting Temperature Issues',
    ]);

    setIsStreaming(false);
  };

  const onSubmit = async (data: DiagnoseFaultFormData) => {
    // First, trigger the streaming diagnosis
    await simulateStreaming();

    // Then save the diagnosis to backend
    const response = await executeAction(
      'diagnose_fault',
      {
        fault_id: data.fault_id,
        additional_context: data.additional_context,
        diagnosis: streamedDiagnosis,
        similar_faults: similarFaults.map((f) => f.id),
        suggested_parts: suggestedParts.map((p) => p.part_number),
        create_work_order: data.create_work_order_from_diagnosis,
      },
      {
        successMessage: 'Diagnosis completed and saved',
        refreshData: true,
      }
    );

    if (response?.success) {
      if (onSuccess) {
        onSuccess({
          diagnosis: streamedDiagnosis,
          similar_faults: similarFaults,
          suggested_parts: suggestedParts,
        });
      }
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical':
        return 'text-red-700 bg-red-50 border-red-300';
      case 'high':
        return 'text-orange-700 bg-orange-50 border-orange-300';
      case 'medium':
        return 'text-yellow-700 bg-yellow-50 border-yellow-300';
      default:
        return 'text-txt-secondary bg-surface-primary border-surface-border';
    }
  };

  // Reset state when modal closes
  useEffect(() => {
    if (!open) {
      setStreamedDiagnosis('');
      setSimilarFaults([]);
      setSuggestedParts([]);
      setManualReferences([]);
      setIsStreaming(false);
    }
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Brain className="h-6 w-6 text-purple-600" />
            AI-Powered Fault Diagnosis
          </DialogTitle>
          <DialogDescription>
            Get AI-assisted analysis with similar past faults and suggested solutions
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit as any)} className="space-y-6">
          {/* Fault Context */}
          <div className="p-4 bg-orange-50 border border-orange-200 rounded-lg">
            <div className="flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-orange-700 mt-0.5" />
              <div className="flex-1">
                <h3 className="font-semibold text-orange-900">{context.fault_title}</h3>
                <p className="text-sm text-orange-800 mt-1">{context.fault_description}</p>
                <div className="flex items-center gap-3 mt-2">
                  <span
                    className={`text-xs px-2 py-0.5 rounded border ${getSeverityColor(
                      context.severity
                    )}`}
                  >
                    {context.severity.toUpperCase()} SEVERITY
                  </span>
                  {context.equipment_name && (
                    <span className="text-sm text-orange-700">
                      Equipment: {context.equipment_name}
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Additional Context */}
          {!isStreaming && !streamedDiagnosis && (
            <div className="space-y-2">
              <Label htmlFor="additional_context">
                Additional Context (Optional)
              </Label>
              <Textarea
                id="additional_context"
                {...register('additional_context')}
                placeholder="Add any additional observations, recent changes, or environmental factors..."
                rows={3}
              />
              <p className="text-xs text-txt-tertiary">
                More context helps the AI provide better diagnosis
              </p>
            </div>
          )}

          {/* Streamed Diagnosis */}
          {(isStreaming || streamedDiagnosis) && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <Brain className="h-5 w-5 text-purple-600" />
                <h3 className="font-semibold text-txt-primary">AI Diagnosis</h3>
                {isStreaming && <Loader2 className="h-4 w-4 animate-spin text-purple-600" />}
              </div>

              <div
                ref={diagnosisRef}
                className="p-4 bg-purple-50 border border-purple-200 rounded-lg max-h-96 overflow-y-auto"
              >
                <div className="prose prose-sm max-w-none">
                  <pre className="whitespace-pre-wrap font-sans text-sm text-surface-hover">
                    {streamedDiagnosis}
                    {isStreaming && <span className="animate-pulse">▊</span>}
                  </pre>
                </div>
              </div>
            </div>
          )}

          {/* Similar Past Faults */}
          {similarFaults.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <AlertCircle className="h-5 w-5 text-brand-interactive" />
                <h3 className="font-semibold text-txt-primary">
                  Similar Past Faults ({similarFaults.length})
                </h3>
              </div>

              <div className="space-y-2">
                {similarFaults.map((fault) => (
                  <div
                    key={fault.id}
                    className="p-3 border border-brand-interactive/30 bg-brand-interactive/10 rounded-lg"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <h4 className="font-medium text-brand-interactive">{fault.title}</h4>
                        <p className="text-sm text-brand-interactive mt-1">
                          <span className="font-medium">Resolution:</span> {fault.resolution}
                        </p>
                        <p className="text-xs text-brand-interactive mt-1">
                          Resolved {fault.resolved_days_ago} days ago
                        </p>
                      </div>
                      <div className="ml-3 text-right">
                        <div className="text-xs text-brand-interactive">Match</div>
                        <div className="text-lg font-bold text-brand-interactive">
                          {(fault.similarity_score * 100).toFixed(0)}%
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Suggested Parts */}
          {suggestedParts.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Package className="h-5 w-5 text-green-600" />
                <h3 className="font-semibold text-txt-primary">
                  Suggested Parts ({suggestedParts.length})
                </h3>
              </div>

              <div className="space-y-2">
                {suggestedParts.map((part, index) => (
                  <div
                    key={index}
                    className="p-3 border border-green-200 bg-green-50 rounded-lg"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <h4 className="font-medium text-green-900">{part.part_name}</h4>
                        <p className="text-sm text-green-700 mt-0.5">P/N: {part.part_number}</p>
                        <p className="text-sm text-green-800 mt-1">
                          <span className="font-medium">Why:</span> {part.reason}
                        </p>
                      </div>
                      <div className="ml-3 text-right">
                        <div className="text-xs text-green-600">Confidence</div>
                        <div className="text-lg font-bold text-green-700">
                          {(part.confidence * 100).toFixed(0)}%
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Manual References */}
          {manualReferences.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <FileText className="h-5 w-5 text-txt-secondary" />
                <h3 className="font-semibold text-txt-primary">
                  Manual References ({manualReferences.length})
                </h3>
              </div>

              <div className="p-3 bg-surface-primary border border-surface-border rounded-lg">
                <ul className="space-y-1">
                  {manualReferences.map((ref, index) => (
                    <li key={index} className="text-sm text-txt-secondary flex items-start gap-2">
                      <Info className="h-4 w-4 text-txt-tertiary mt-0.5" />
                      {ref}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {/* Create Work Order Option */}
          {streamedDiagnosis && (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Checkbox
                  id="create_work_order_from_diagnosis"
                  checked={createWorkOrder}
                  onCheckedChange={(checked) =>
                    setValue('create_work_order_from_diagnosis', !!checked)
                  }
                />
                <Label
                  htmlFor="create_work_order_from_diagnosis"
                  className="text-sm font-normal cursor-pointer flex items-center gap-2"
                >
                  <Wrench className="h-4 w-4 text-brand-interactive" />
                  Create work order with this diagnosis
                </Label>
              </div>
              {createWorkOrder && (
                <p className="text-xs text-brand-interactive ml-6">
                  A work order will be created with the AI diagnosis and suggested parts pre-filled
                </p>
              )}
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isLoading || isStreaming}
            >
              {streamedDiagnosis ? 'Close' : 'Cancel'}
            </Button>
            {!streamedDiagnosis ? (
              <Button type="submit" disabled={isLoading || isStreaming}>
                {isStreaming ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Analyzing...
                  </>
                ) : (
                  <>
                    <Brain className="h-4 w-4 mr-2" />
                    Generate Diagnosis
                  </>
                )}
              </Button>
            ) : (
              <Button type="button" onClick={() => onOpenChange(false)} variant="default">
                <CheckCircle className="h-4 w-4 mr-2" />
                Done
              </Button>
            )}
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
