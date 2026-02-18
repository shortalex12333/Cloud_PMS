/**
 * AddToHandoverModal Component
 *
 * Modal for adding items to handover reports
 * Supports multiple entity types with search and multi-select
 * Phase 4 - LINKING Selection Modal
 */

'use client';

import { useState } from 'react';
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
import { useActionHandler } from '@/hooks/useActionHandler';
import {
  FileText,
  AlertCircle,
  Wrench,
  Package,
  Settings,
  File,
  Search,
  X,
  CheckCircle2,
} from 'lucide-react';

// Validation schema
const addToHandoverSchema = z.object({
  handover_id: z.string().min(1, 'Handover ID is required'),
  entity_type: z.enum(['fault', 'work_order', 'equipment', 'part', 'document']),
  selected_entities: z.array(z.string()).min(1, 'At least one item must be selected'),
  summary: z.string().optional(),
});

type AddToHandoverFormData = z.infer<typeof addToHandoverSchema>;

// Mock entity data (in production, this would come from API)
type Entity = {
  id: string;
  name: string;
  description?: string;
  status?: string;
  metadata?: string;
};

interface AddToHandoverModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  context: {
    handover_id: string;
    handover_title: string;
  };
  onSuccess?: () => void;
}

export function AddToHandoverModal({
  open,
  onOpenChange,
  context,
  onSuccess,
}: AddToHandoverModalProps) {
  const { executeAction, isLoading } = useActionHandler();
  const [searchQuery, setSearchQuery] = useState('');
  const [availableEntities, setAvailableEntities] = useState<Entity[]>([]);

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
  } = useForm<AddToHandoverFormData>({
    resolver: zodResolver(addToHandoverSchema),
    defaultValues: {
      handover_id: context.handover_id,
      entity_type: 'fault',
      selected_entities: [],
      summary: '',
    },
  });

  const entityType = watch('entity_type');
  const selectedEntities = watch('selected_entities') || [];

  // Mock data - in production, fetch from API based on entity_type
  const getMockEntities = (type: string): Entity[] => {
    switch (type) {
      case 'fault':
        return [
          { id: 'f1', name: 'Engine coolant leak', description: 'High severity', status: 'open', metadata: 'Starboard Engine' },
          { id: 'f2', name: 'Electrical short in galley', description: 'Medium severity', status: 'in_progress', metadata: 'Main Deck' },
          { id: 'f3', name: 'HVAC not cooling', description: 'Low severity', status: 'open', metadata: 'Guest Cabin 3' },
        ];
      case 'work_order':
        return [
          { id: 'w1', name: 'Replace oil filters', description: 'Scheduled maintenance', status: 'in_progress', metadata: 'Due: 2025-11-25' },
          { id: 'w2', name: 'Repair navigation lights', description: 'Safety critical', status: 'pending', metadata: 'Due: 2025-11-22' },
        ];
      case 'equipment':
        return [
          { id: 'e1', name: 'Main Engine - Port', description: 'Caterpillar C32', metadata: 'SN: CAT-12345' },
          { id: 'e2', name: 'Generator - Primary', description: 'Kohler 50kW', metadata: 'SN: KOH-67890' },
        ];
      case 'part':
        return [
          { id: 'p1', name: 'Oil Filter', description: 'Stock: 12 units', metadata: 'P/N: OF-12345' },
          { id: 'p2', name: 'Air Filter', description: 'Stock: 8 units', metadata: 'P/N: AF-67890' },
        ];
      case 'document':
        return [
          { id: 'd1', name: 'Engine Manual - Caterpillar C32', description: 'PDF, 245 pages', metadata: 'Uploaded: 2025-01-15' },
          { id: 'd2', name: 'Safety Inspection Report', description: 'PDF, 12 pages', metadata: 'Uploaded: 2025-11-15' },
        ];
      default:
        return [];
    }
  };

  // Filter entities by search query
  const filteredEntities = availableEntities.filter((entity) =>
    entity.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    entity.description?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Update available entities when entity type changes
  const handleEntityTypeChange = (type: string) => {
    setValue('entity_type', type as any);
    setValue('selected_entities', []);
    setAvailableEntities(getMockEntities(type));
    setSearchQuery('');
  };

  // Toggle entity selection
  const toggleEntity = (entityId: string) => {
    const current = selectedEntities || [];
    if (current.includes(entityId)) {
      setValue('selected_entities', current.filter((id) => id !== entityId));
    } else {
      setValue('selected_entities', [...current, entityId]);
    }
  };

  const onSubmit = async (data: AddToHandoverFormData) => {
    const response = await executeAction(
      'add_to_handover',
      {
        handover_id: data.handover_id,
        items: data.selected_entities.map((id) => ({
          source_type: data.entity_type,
          source_id: id,
        })),
        summary: data.summary,
      },
      {
        successMessage: `Added ${data.selected_entities.length} item(s) to handover`,
        refreshData: true,
      }
    );

    if (response?.success) {
      onOpenChange(false);
      if (onSuccess) {
        onSuccess();
      }
    }
  };

  const getEntityIcon = (type: string) => {
    switch (type) {
      case 'fault':
        return <AlertCircle className="h-4 w-4" />;
      case 'work_order':
        return <Wrench className="h-4 w-4" />;
      case 'equipment':
        return <Settings className="h-4 w-4" />;
      case 'part':
        return <Package className="h-4 w-4" />;
      case 'document':
        return <File className="h-4 w-4" />;
      default:
        return null;
    }
  };

  const getStatusColor = (status?: string) => {
    switch (status) {
      case 'open':
      case 'pending':
        return 'bg-brand-interactive/10 text-brand-interactive';
      case 'in_progress':
        return 'bg-yellow-100 text-yellow-700';
      case 'resolved':
      case 'completed':
        return 'bg-green-100 text-green-700';
      case 'closed':
        return 'bg-surface-elevated text-txt-secondary';
      default:
        return 'bg-surface-elevated text-txt-secondary';
    }
  };

  // Load initial entities
  useState(() => {
    setAvailableEntities(getMockEntities('fault'));
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-brand-interactive" />
            Add Items to Handover
          </DialogTitle>
          <DialogDescription>
            Add faults, work orders, equipment, parts, or documents to "{context.handover_title}"
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* Entity Type Selector */}
          <div className="space-y-2">
            <Label htmlFor="entity_type">Item Type</Label>
            <Select value={entityType} onValueChange={handleEntityTypeChange}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="fault">
                  <div className="flex items-center gap-2">
                    <AlertCircle className="h-4 w-4" />
                    Faults
                  </div>
                </SelectItem>
                <SelectItem value="work_order">
                  <div className="flex items-center gap-2">
                    <Wrench className="h-4 w-4" />
                    Work Orders
                  </div>
                </SelectItem>
                <SelectItem value="equipment">
                  <div className="flex items-center gap-2">
                    <Settings className="h-4 w-4" />
                    Equipment
                  </div>
                </SelectItem>
                <SelectItem value="part">
                  <div className="flex items-center gap-2">
                    <Package className="h-4 w-4" />
                    Parts
                  </div>
                </SelectItem>
                <SelectItem value="document">
                  <div className="flex items-center gap-2">
                    <File className="h-4 w-4" />
                    Documents
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Search */}
          <div className="space-y-2">
            <Label htmlFor="search">Search Items</Label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-txt-tertiary" />
              <Input
                id="search"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={`Search ${entityType}s...`}
                className="pl-9"
              />
            </div>
          </div>

          {/* Entity List */}
          <div className="space-y-2">
            <Label>
              Available Items ({filteredEntities.length})
              {selectedEntities.length > 0 && (
                <span className="ml-2 text-brand-interactive font-semibold">
                  {selectedEntities.length} selected
                </span>
              )}
            </Label>

            {errors.selected_entities && (
              <p className="text-sm text-red-600">{errors.selected_entities.message}</p>
            )}

            <div className="border border-surface-border rounded-lg max-h-80 overflow-y-auto">
              {filteredEntities.length === 0 ? (
                <div className="p-8 text-center text-txt-tertiary">
                  <Search className="h-12 w-12 mx-auto mb-2 text-surface-border" />
                  <p>No {entityType}s found</p>
                </div>
              ) : (
                <div className="divide-y divide-surface-border">
                  {filteredEntities.map((entity) => {
                    const isSelected = selectedEntities.includes(entity.id);
                    return (
                      <div
                        key={entity.id}
                        className={`p-3 cursor-pointer hover:bg-surface-primary transition-colors ${
                          isSelected ? 'bg-brand-interactive/15' : ''
                        }`}
                        onClick={() => toggleEntity(entity.id)}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex items-start gap-3 flex-1">
                            <div className="mt-1">{getEntityIcon(entityType)}</div>
                            <div className="flex-1 min-w-0">
                              <h4 className="font-medium text-txt-primary truncate">
                                {entity.name}
                              </h4>
                              {entity.description && (
                                <p className="text-sm text-txt-secondary mt-0.5">
                                  {entity.description}
                                </p>
                              )}
                              <div className="flex items-center gap-2 mt-1">
                                {entity.status && (
                                  <span
                                    className={`text-xs px-2 py-0.5 rounded ${getStatusColor(
                                      entity.status
                                    )}`}
                                  >
                                    {entity.status.replace('_', ' ').toUpperCase()}
                                  </span>
                                )}
                                {entity.metadata && (
                                  <span className="text-xs text-txt-tertiary">{entity.metadata}</span>
                                )}
                              </div>
                            </div>
                          </div>
                          <div className="ml-3">
                            {isSelected ? (
                              <CheckCircle2 className="h-5 w-5 text-brand-interactive" />
                            ) : (
                              <div className="h-5 w-5 border-2 border-surface-border rounded" />
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Summary/Notes */}
          <div className="space-y-2">
            <Label htmlFor="summary">Summary / Notes (Optional)</Label>
            <Textarea
              id="summary"
              {...register('summary')}
              placeholder="Add any additional context or notes about these items for the handover..."
              rows={3}
            />
          </div>

          {/* Selected Items Preview */}
          {selectedEntities.length > 0 && (
            <div className="p-4 bg-brand-interactive/15 border border-brand-interactive-line rounded-lg">
              <p className="text-sm font-semibold text-brand-interactive mb-2">
                Selected Items ({selectedEntities.length})
              </p>
              <div className="flex flex-wrap gap-2">
                {selectedEntities.map((id) => {
                  const entity = availableEntities.find((e) => e.id === id);
                  if (!entity) return null;
                  return (
                    <div
                      key={id}
                      className="flex items-center gap-1 px-2 py-1 bg-white border border-brand-interactive rounded text-sm"
                    >
                      {getEntityIcon(entityType)}
                      <span className="text-txt-primary">{entity.name}</span>
                      <button
                        type="button"
                        onClick={() => toggleEntity(id)}
                        className="ml-1 text-txt-tertiary hover:text-red-600"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isLoading}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isLoading || selectedEntities.length === 0}>
              {isLoading
                ? 'Adding...'
                : `Add ${selectedEntities.length} Item${selectedEntities.length !== 1 ? 's' : ''}`}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
