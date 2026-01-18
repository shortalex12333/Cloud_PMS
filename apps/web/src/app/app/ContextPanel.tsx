'use client';

/**
 * ContextPanel - Slides from right
 *
 * Shows entity detail view when context-open state is active.
 * Displays work orders, equipment, faults, parts, etc.
 * No URL change - purely state-driven.
 */

import { useSurface } from '@/contexts/SurfaceContext';
import { X, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function ContextPanel() {
  const { contextPanel, hideContext } = useSurface();
  const { visible, entityType, entityId, entityData } = contextPanel;

  // Entity type display names
  const entityTypeNames: Record<string, string> = {
    work_order: 'Work Order',
    equipment: 'Equipment',
    fault: 'Fault',
    part: 'Part',
    purchase_order: 'Purchase Order',
    supplier: 'Supplier',
    document: 'Document',
    email_thread: 'Email Thread',
  };

  const displayName = entityType ? entityTypeNames[entityType] || entityType : 'Details';

  return (
    <div
      className={cn(
        'absolute inset-y-0 right-0 w-[480px] bg-gray-900/95 border-l border-gray-700/50',
        'transform transition-transform duration-300 ease-out z-20',
        'backdrop-blur-sm shadow-2xl',
        visible ? 'translate-x-0' : 'translate-x-full'
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-700/50">
        <div className="flex items-center gap-4">
          <button
            onClick={hideContext}
            className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
            aria-label="Close context panel"
          >
            <X className="w-5 h-5 text-gray-400" />
          </button>
          <div>
            <span className="text-xs text-gray-500 uppercase tracking-wider">
              {displayName}
            </span>
            {entityId && (
              <p className="text-sm text-gray-400 font-mono">
                {entityId.substring(0, 8)}...
              </p>
            )}
          </div>
        </div>
        <button
          onClick={hideContext}
          className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
          aria-label="Close panel"
        >
          <ChevronRight className="w-5 h-5 text-gray-400" />
        </button>
      </div>

      {/* Content placeholder */}
      <div className="flex-1 overflow-y-auto p-4">
        {visible && entityType && entityId ? (
          <div className="space-y-6">
            {/* Entity summary card */}
            <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700/50">
              <h3 className="text-lg font-semibold text-white mb-2">
                {(entityData as any)?.title || (entityData as any)?.name || displayName}
              </h3>
              <p className="text-sm text-gray-400">
                {(entityData as any)?.subtitle || (entityData as any)?.description || 'Loading details...'}
              </p>
            </div>

            {/* Actions */}
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-gray-300">Actions</h4>
              <div className="grid grid-cols-2 gap-2">
                <button className="px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm text-gray-300 transition-colors">
                  View Details
                </button>
                <button className="px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm text-gray-300 transition-colors">
                  Edit
                </button>
                <button className="px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm text-gray-300 transition-colors">
                  Link Email
                </button>
                <button className="px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm text-gray-300 transition-colors">
                  History
                </button>
              </div>
            </div>

            {/* Related items placeholder */}
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-gray-300">Related</h4>
              <div className="text-center py-6 bg-gray-800/30 rounded-lg border border-gray-700/30">
                <p className="text-gray-500 text-sm">
                  Related items will appear here
                </p>
              </div>
            </div>
          </div>
        ) : (
          <div className="text-center py-12">
            <p className="text-gray-400 text-sm">
              Select an item to view details
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
