'use client';

/**
 * CelesteOS Control Center Dashboard
 * macOS Control Center-style collapsible modules
 *
 * Features:
 * - 8 operational modules in a fluid grid
 * - Collapsible/expandable modules
 * - Real-time status indicators
 * - Inline microactions
 * - Glassmorphic design
 */

import React, { useState, useCallback } from 'react';
import { cn } from '@/lib/utils';
import WorkOrderModule from './modules/WorkOrderModule';
import FaultActivityModule from './modules/FaultActivityModule';
import EquipmentStateModule from './modules/EquipmentStateModule';
import CrewNotesModule from './modules/CrewNotesModule';
import InventoryStatusModule from './modules/InventoryStatusModule';
import PredictiveRiskModule from './modules/PredictiveRiskModule';
import DocumentExpiryModule from './modules/DocumentExpiryModule';
import HandoverStatusModule from './modules/HandoverStatusModule';

// ============================================================================
// TYPES
// ============================================================================

interface ModuleConfig {
  id: string;
  title: string;
  component: React.ComponentType<ModuleProps>;
  defaultExpanded: boolean;
  span?: 1 | 2; // Grid column span
  priority: number; // Sort order when collapsed
}

export interface ModuleProps {
  isExpanded: boolean;
  onToggle: () => void;
  className?: string;
}

// ============================================================================
// MODULE CONFIGURATION
// ============================================================================

const MODULES: ModuleConfig[] = [
  { id: 'work_orders', title: 'Work Orders', component: WorkOrderModule, defaultExpanded: true, span: 1, priority: 1 },
  { id: 'faults', title: 'Fault Activity', component: FaultActivityModule, defaultExpanded: true, span: 1, priority: 2 },
  { id: 'equipment', title: 'Equipment Status', component: EquipmentStateModule, defaultExpanded: false, span: 1, priority: 3 },
  { id: 'predictive', title: 'Predictive Insights', component: PredictiveRiskModule, defaultExpanded: true, span: 2, priority: 4 },
  { id: 'inventory', title: 'Inventory', component: InventoryStatusModule, defaultExpanded: false, span: 1, priority: 5 },
  { id: 'crew_notes', title: 'Crew Notes', component: CrewNotesModule, defaultExpanded: false, span: 1, priority: 6 },
  { id: 'documents', title: 'Expiring Documents', component: DocumentExpiryModule, defaultExpanded: false, span: 1, priority: 7 },
  { id: 'handover', title: 'Handover Status', component: HandoverStatusModule, defaultExpanded: true, span: 1, priority: 8 },
];

// ============================================================================
// COMPONENT
// ============================================================================

export default function ControlCenter() {
  // Track expanded state for each module
  const [expandedModules, setExpandedModules] = useState<Set<string>>(
    new Set(MODULES.filter(m => m.defaultExpanded).map(m => m.id))
  );

  // Toggle module expansion
  const toggleModule = useCallback((moduleId: string) => {
    setExpandedModules(prev => {
      const next = new Set(prev);
      if (next.has(moduleId)) {
        next.delete(moduleId);
      } else {
        next.add(moduleId);
      }
      return next;
    });
  }, []);

  // Expand all modules
  const expandAll = useCallback(() => {
    setExpandedModules(new Set(MODULES.map(m => m.id)));
  }, []);

  // Collapse all modules
  const collapseAll = useCallback(() => {
    setExpandedModules(new Set());
  }, []);

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 p-4 sm:p-6">
      {/* Header */}
      <header className="max-w-7xl mx-auto mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100">
              Control Center
            </h1>
            <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">
              Holistic yacht operational overview
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={expandAll}
              className={cn(
                'px-3 py-1.5 rounded-lg',
                'text-celeste-sm font-medium',
                'bg-zinc-100 dark:bg-zinc-800',
                'text-zinc-600 dark:text-zinc-300',
                'hover:bg-zinc-200 dark:hover:bg-zinc-700',
                'transition-colors'
              )}
            >
              Expand All
            </button>
            <button
              onClick={collapseAll}
              className={cn(
                'px-3 py-1.5 rounded-lg',
                'text-celeste-sm font-medium',
                'bg-zinc-100 dark:bg-zinc-800',
                'text-zinc-600 dark:text-zinc-300',
                'hover:bg-zinc-200 dark:hover:bg-zinc-700',
                'transition-colors'
              )}
            >
              Collapse All
            </button>
          </div>
        </div>
      </header>

      {/* Module Grid */}
      <div className="max-w-7xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {MODULES.map((module) => {
            const isExpanded = expandedModules.has(module.id);
            const ModuleComponent = module.component;

            return (
              <div
                key={module.id}
                className={cn(
                  'transition-all duration-300 ease-out',
                  module.span === 2 && 'md:col-span-2'
                )}
              >
                <ModuleComponent
                  isExpanded={isExpanded}
                  onToggle={() => toggleModule(module.id)}
                />
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
