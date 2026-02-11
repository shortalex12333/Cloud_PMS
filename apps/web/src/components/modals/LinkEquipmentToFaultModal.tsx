// @ts-nocheck - Phase 4: Zod v4/hookform resolver compatibility
/**
 * LinkEquipmentToFaultModal Component
 *
 * Modal for linking equipment to existing faults
 * Includes equipment search and optional work order creation
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
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { useActionHandler } from '@/hooks/useActionHandler';
import { Settings, Search, AlertCircle, Wrench, CheckCircle2 } from 'lucide-react';

// Validation schema
const linkEquipmentToFaultSchema = z.object({
  fault_id: z.string().min(1, 'Fault ID is required'),
  equipment_id: z.string().min(1, 'Equipment must be selected'),
  create_work_order: z.boolean().optional(),
});

type LinkEquipmentToFaultFormData = z.infer<typeof linkEquipmentToFaultSchema>;

// Mock equipment data (in production, this would come from API)
type Equipment = {
  id: string;
  name: string;
  model?: string;
  serial_number?: string;
  location: string;
  manufacturer?: string;
  status?: string;
};

interface LinkEquipmentToFaultModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  context: {
    fault_id: string;
    fault_title: string;
    fault_severity: string;
  };
  onSuccess?: () => void;
}

export function LinkEquipmentToFaultModal({
  open,
  onOpenChange,
  context,
  onSuccess,
}: LinkEquipmentToFaultModalProps) {
  const { executeAction, isLoading } = useActionHandler();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedEquipmentId, setSelectedEquipmentId] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
  } = useForm<LinkEquipmentToFaultFormData>({
    resolver: zodResolver(linkEquipmentToFaultSchema),
    defaultValues: {
      fault_id: context.fault_id,
      equipment_id: '',
      create_work_order: false,
    },
  });

  const createWorkOrder = watch('create_work_order');

  // Mock equipment data - in production, fetch from API
  const mockEquipment: Equipment[] = [
    {
      id: 'eq1',
      name: 'Main Engine - Port',
      model: 'C32',
      serial_number: 'CAT-12345',
      location: 'Engine Room - Port',
      manufacturer: 'Caterpillar',
      status: 'operational',
    },
    {
      id: 'eq2',
      name: 'Main Engine - Starboard',
      model: 'C32',
      serial_number: 'CAT-12346',
      location: 'Engine Room - Starboard',
      manufacturer: 'Caterpillar',
      status: 'operational',
    },
    {
      id: 'eq3',
      name: 'Generator - Primary',
      model: '50REOZJB',
      serial_number: 'KOH-67890',
      location: 'Engine Room - Aft',
      manufacturer: 'Kohler',
      status: 'operational',
    },
    {
      id: 'eq4',
      name: 'HVAC System - Guest Deck',
      model: 'Chiller 2000',
      serial_number: 'HVAC-11111',
      location: 'Guest Deck - Mechanical',
      manufacturer: 'Marine Air',
      status: 'maintenance',
    },
    {
      id: 'eq5',
      name: 'Navigation Radar',
      model: 'NavMaster Pro',
      serial_number: 'NAV-22222',
      location: 'Bridge',
      manufacturer: 'Furuno',
      status: 'operational',
    },
  ];

  // Filter equipment by search query
  const filteredEquipment = mockEquipment.filter(
    (eq) =>
      eq.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      eq.location.toLowerCase().includes(searchQuery.toLowerCase()) ||
      eq.model?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      eq.manufacturer?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const selectedEquipment = mockEquipment.find((eq) => eq.id === selectedEquipmentId);

  const handleSelectEquipment = (equipmentId: string) => {
    setSelectedEquipmentId(equipmentId);
    setValue('equipment_id', equipmentId);
  };

  const onSubmit = async (data: LinkEquipmentToFaultFormData) => {
    const response = await executeAction(
      'link_equipment_to_fault',
      {
        fault_id: data.fault_id,
        equipment_id: data.equipment_id,
        create_work_order: data.create_work_order,
      },
      {
        successMessage: `Equipment linked to fault${
          data.create_work_order ? ' and work order created' : ''
        }`,
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

  const getSeverityColor = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical':
        return 'text-red-700 bg-red-50 border-red-300';
      case 'high':
        return 'text-orange-700 bg-orange-50 border-orange-300';
      case 'medium':
        return 'text-yellow-700 bg-yellow-50 border-yellow-300';
      default:
        return 'text-celeste-text-secondary bg-celeste-bg-primary border-celeste-border';
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5 text-celeste-accent" />
            Link Equipment to Fault
          </DialogTitle>
          <DialogDescription>
            Associate equipment with this fault to track affected assets
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* Fault Information */}
          <div className="p-4 bg-orange-50 border border-orange-200 rounded-lg">
            <div className="flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-orange-700 mt-0.5" />
              <div className="flex-1">
                <h3 className="font-semibold text-orange-900">{context.fault_title}</h3>
                <div className="flex items-center gap-2 mt-1">
                  <span
                    className={`text-xs px-2 py-0.5 rounded border ${getSeverityColor(
                      context.fault_severity
                    )}`}
                  >
                    {context.fault_severity.toUpperCase()} SEVERITY
                  </span>
                  <span className="text-sm text-orange-700">
                    Fault ID: {context.fault_id.slice(0, 8)}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Search Equipment */}
          <div className="space-y-2">
            <Label htmlFor="search">Search Equipment</Label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-celeste-text-muted" />
              <Input
                id="search"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by name, location, model, or manufacturer..."
                className="pl-9"
              />
            </div>
          </div>

          {/* Equipment List */}
          <div className="space-y-2">
            <Label>
              Select Equipment <span className="text-red-500">*</span>
            </Label>
            {errors.equipment_id && (
              <p className="text-sm text-red-600">{errors.equipment_id.message}</p>
            )}

            <div className="border border-celeste-border rounded-lg max-h-80 overflow-y-auto">
              {filteredEquipment.length === 0 ? (
                <div className="p-8 text-center text-celeste-text-disabled">
                  <Search className="h-12 w-12 mx-auto mb-2 text-celeste-border" />
                  <p>No equipment found</p>
                </div>
              ) : (
                <div className="divide-y divide-celeste-border">
                  {filteredEquipment.map((equipment) => {
                    const isSelected = selectedEquipmentId === equipment.id;
                    return (
                      <div
                        key={equipment.id}
                        className={`p-3 cursor-pointer hover:bg-celeste-bg-primary transition-colors ${
                          isSelected ? 'bg-celeste-accent-subtle' : ''
                        }`}
                        onClick={() => handleSelectEquipment(equipment.id)}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex items-start gap-3 flex-1">
                            <Settings className="h-5 w-5 text-celeste-text-secondary mt-1" />
                            <div className="flex-1 min-w-0">
                              <h4 className="font-medium text-celeste-black">{equipment.name}</h4>
                              <div className="grid grid-cols-2 gap-x-4 gap-y-1 mt-1">
                                {equipment.model && (
                                  <p className="text-sm text-celeste-text-secondary">
                                    <span className="font-medium">Model:</span> {equipment.model}
                                  </p>
                                )}
                                {equipment.serial_number && (
                                  <p className="text-sm text-celeste-text-secondary">
                                    <span className="font-medium">S/N:</span>{' '}
                                    {equipment.serial_number}
                                  </p>
                                )}
                                {equipment.manufacturer && (
                                  <p className="text-sm text-celeste-text-secondary">
                                    <span className="font-medium">Mfr:</span>{' '}
                                    {equipment.manufacturer}
                                  </p>
                                )}
                                <p className="text-sm text-celeste-text-secondary">
                                  <span className="font-medium">Location:</span> {equipment.location}
                                </p>
                              </div>
                            </div>
                          </div>
                          <div className="ml-3">
                            {isSelected ? (
                              <CheckCircle2 className="h-5 w-5 text-celeste-accent" />
                            ) : (
                              <div className="h-5 w-5 border-2 border-celeste-border rounded-full" />
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

          {/* Selected Equipment Preview */}
          {selectedEquipment && (
            <div className="p-4 bg-celeste-accent-subtle border border-celeste-accent-line rounded-lg">
              <p className="text-sm font-semibold text-celeste-accent mb-2">Selected Equipment</p>
              <div className="flex items-start gap-3">
                <Settings className="h-5 w-5 text-celeste-accent mt-0.5" />
                <div>
                  <h4 className="font-medium text-celeste-accent">{selectedEquipment.name}</h4>
                  <div className="grid grid-cols-2 gap-x-4 gap-y-1 mt-1 text-sm text-celeste-accent">
                    {selectedEquipment.model && (
                      <p>
                        <span className="font-medium">Model:</span> {selectedEquipment.model}
                      </p>
                    )}
                    {selectedEquipment.serial_number && (
                      <p>
                        <span className="font-medium">S/N:</span>{' '}
                        {selectedEquipment.serial_number}
                      </p>
                    )}
                    <p>
                      <span className="font-medium">Location:</span> {selectedEquipment.location}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Create Work Order Option */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Checkbox
                id="create_work_order"
                checked={createWorkOrder}
                onCheckedChange={(checked) => setValue('create_work_order', !!checked)}
              />
              <Label
                htmlFor="create_work_order"
                className="text-sm font-normal cursor-pointer flex items-center gap-2"
              >
                <Wrench className="h-4 w-4 text-celeste-accent" />
                Create work order for this fault
              </Label>
            </div>
            {createWorkOrder && (
              <p className="text-xs text-celeste-accent ml-6">
                A work order will be automatically created and assigned to this equipment
              </p>
            )}
          </div>

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
            <Button type="submit" disabled={isLoading || !selectedEquipmentId}>
              {isLoading ? 'Linking...' : 'Link Equipment'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
