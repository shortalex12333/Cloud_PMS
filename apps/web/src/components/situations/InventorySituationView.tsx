'use client';

/**
 * Inventory Situation View
 *
 * Parts/Inventory viewing environment per situation framework.
 * Displays part details, stock levels, and available actions based on permissions.
 */

import React, { useEffect, useState, useCallback } from 'react';
import { X, Package, AlertTriangle, Plus, Loader2, MapPin, Hash, DollarSign, ShoppingCart, ArrowDownToLine, ArrowUpFromLine, ArrowLeftRight } from 'lucide-react';
import type { SituationContext } from '@/types/situation';
import { usePartActions, usePartPermissions } from '@/hooks/usePartActions';
import { supabase } from '@/lib/supabaseClient';
import { useAuth } from '@/hooks/useAuth';

// ============================================================================
// TYPES
// ============================================================================

export interface InventorySituationViewProps {
  situation: SituationContext;
  onClose: () => void;
  onAction?: (action: string, payload: any) => void;
}

interface PartData {
  id: string;
  name: string;
  part_number?: string;
  description?: string;
  category?: string;
  quantity_on_hand: number;
  quantity_minimum: number;
  quantity_reorder: number;
  unit_of_measure: string;
  storage_location?: string;
  unit_cost?: number;
  currency: string;
  supplier_part_number?: string;
}

// ============================================================================
// COMPONENT
// ============================================================================

export default function InventorySituationView({
  situation,
  onClose,
  onAction,
}: InventorySituationViewProps) {
  const [part, setPart] = useState<PartData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { user } = useAuth();
  const partId = situation.primary_entity_id;
  const metadata = situation.evidence as any;
  const partTitle = metadata?.title || metadata?.name || 'Part';

  const { isLoading: actionLoading, consumePart, receivePart, addToShoppingList } = usePartActions(partId);
  const permissions = usePartPermissions();

  /**
   * Load part data on mount
   */
  useEffect(() => {
    async function loadPart() {
      setIsLoading(true);
      setError(null);

      try {
        const { data, error: fetchError } = await supabase
          .from('pms_parts')
          .select('*')
          .eq('id', partId)
          .single();

        if (fetchError) {
          console.error('[InventorySituationView] Fetch error:', fetchError);
          setError(fetchError.message);
          return;
        }

        if (!data) {
          setError('Part not found');
          return;
        }

        setPart(data);
      } catch (err) {
        console.error('[InventorySituationView] Load error:', err);
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setIsLoading(false);
      }
    }

    if (partId) {
      loadPart();
    }
  }, [partId]);

  /**
   * Handle consume part
   */
  const handleConsume = useCallback(async () => {
    const quantityInput = prompt('Enter quantity to consume:');
    if (!quantityInput) return;

    const quantity = parseInt(quantityInput, 10);
    if (isNaN(quantity) || quantity <= 0) {
      alert('Please enter a valid positive number');
      return;
    }

    const notes = prompt('Enter usage notes (optional):');
    const result = await consumePart(quantity, notes || undefined);

    if (result.success) {
      if (onAction) {
        onAction('part_consumed', result.data);
      }
      // Update local state
      setPart((prev) => prev ? { ...prev, quantity_on_hand: prev.quantity_on_hand - quantity } : null);
      alert('Stock consumed successfully');
    } else {
      alert(`Failed to consume stock: ${result.error}`);
    }
  }, [consumePart, onAction]);

  /**
   * Handle receive part
   */
  const handleReceive = useCallback(async () => {
    const quantityInput = prompt('Enter quantity received:');
    if (!quantityInput) return;

    const quantity = parseInt(quantityInput, 10);
    if (isNaN(quantity) || quantity <= 0) {
      alert('Please enter a valid positive number');
      return;
    }

    const notes = prompt('Enter receiving notes (optional):');
    const result = await receivePart(quantity, notes || undefined);

    if (result.success) {
      if (onAction) {
        onAction('part_received', result.data);
      }
      // Update local state
      setPart((prev) => prev ? { ...prev, quantity_on_hand: prev.quantity_on_hand + quantity } : null);
      alert('Stock received successfully');
    } else {
      alert(`Failed to receive stock: ${result.error}`);
    }
  }, [receivePart, onAction]);

  /**
   * Handle add to shopping list
   */
  const handleAddToShoppingList = useCallback(async () => {
    const quantityInput = prompt('Enter quantity to order (or leave empty for default):');
    const quantity = quantityInput ? parseInt(quantityInput, 10) : undefined;

    if (quantityInput && (isNaN(quantity!) || quantity! <= 0)) {
      alert('Please enter a valid positive number');
      return;
    }

    const notes = prompt('Enter ordering notes (optional):');
    const result = await addToShoppingList(quantity, notes || undefined);

    if (result.success) {
      if (onAction) {
        onAction('added_to_shopping_list', result.data);
      }
      alert('Added to shopping list');
    } else {
      alert(`Failed to add to shopping list: ${result.error}`);
    }
  }, [addToShoppingList, onAction]);

  /**
   * Get stock level indicator
   */
  const getStockLevelInfo = (quantity: number, minimum: number, reorder: number) => {
    if (quantity <= 0) {
      return { label: 'Out of Stock', color: 'bg-red-500/20 text-red-400 border-red-500/50' };
    }
    if (quantity <= minimum) {
      return { label: 'Critical Low', color: 'bg-red-500/20 text-red-400 border-red-500/50' };
    }
    if (quantity <= reorder) {
      return { label: 'Low Stock', color: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/50' };
    }
    return { label: 'In Stock', color: 'bg-green-500/20 text-green-400 border-green-500/50' };
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[8vh] pb-8 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative z-10 w-full max-w-2xl mx-4">
        <div className="bg-white dark:bg-zinc-900 rounded-celeste-lg shadow-modal overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-200 dark:border-zinc-800 bg-emerald-50 dark:bg-emerald-900/20">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-emerald-500 rounded-lg">
                <Package className="h-5 w-5 text-white" />
              </div>
              <div>
                <h2 className="typo-title font-semibold text-zinc-900 dark:text-zinc-100">
                  {part?.name || partTitle}
                </h2>
                {part?.part_number && (
                  <p className="typo-body text-zinc-500 dark:text-zinc-400">
                    P/N: {part.part_number}
                  </p>
                )}
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-zinc-200 dark:hover:bg-zinc-700 rounded-lg transition-colors"
            >
              <X className="w-5 h-5 text-zinc-500" />
            </button>
          </div>

          {/* Content */}
          <div className="p-5">
            {isLoading && (
              <div className="flex flex-col items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-emerald-500" />
                <p className="mt-4 text-zinc-600 dark:text-zinc-400">Loading part...</p>
              </div>
            )}

            {error && (
              <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-4">
                <div className="flex items-center gap-2 text-red-500">
                  <AlertTriangle className="h-5 w-5" />
                  <span className="font-medium">Failed to load part</span>
                </div>
                <p className="mt-2 text-zinc-600 dark:text-zinc-400 typo-body">{error}</p>
              </div>
            )}

            {!isLoading && !error && part && (
              <div className="space-y-6">
                {/* Stock Level and Quantity */}
                <div className="flex items-center justify-between p-4 bg-zinc-50 dark:bg-zinc-800 rounded-lg">
                  <div>
                    <p className="typo-meta text-zinc-500 dark:text-zinc-400">Quantity on Hand</p>
                    <p className="text-3xl font-bold text-zinc-900 dark:text-zinc-100">
                      {part.quantity_on_hand} <span className="text-base font-normal text-zinc-500">{part.unit_of_measure}</span>
                    </p>
                  </div>
                  <span className={`px-3 py-1 rounded-full text-sm font-medium border ${getStockLevelInfo(part.quantity_on_hand, part.quantity_minimum, part.quantity_reorder).color}`}>
                    {getStockLevelInfo(part.quantity_on_hand, part.quantity_minimum, part.quantity_reorder).label}
                  </span>
                </div>

                {/* Stock Thresholds */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-3 bg-zinc-50 dark:bg-zinc-800 rounded-lg">
                    <p className="typo-meta text-zinc-500 dark:text-zinc-400">Minimum Level</p>
                    <p className="typo-body font-medium text-zinc-900 dark:text-zinc-100">{part.quantity_minimum}</p>
                  </div>
                  <div className="p-3 bg-zinc-50 dark:bg-zinc-800 rounded-lg">
                    <p className="typo-meta text-zinc-500 dark:text-zinc-400">Reorder Level</p>
                    <p className="typo-body font-medium text-zinc-900 dark:text-zinc-100">{part.quantity_reorder}</p>
                  </div>
                </div>

                {/* Key Details Grid */}
                <div className="grid grid-cols-2 gap-4">
                  {part.category && (
                    <div className="flex items-start gap-2">
                      <Hash className="h-4 w-4 text-zinc-400 mt-0.5" />
                      <div>
                        <p className="typo-meta text-zinc-500 dark:text-zinc-400">Category</p>
                        <p className="typo-body text-zinc-900 dark:text-zinc-100">{part.category}</p>
                      </div>
                    </div>
                  )}

                  {part.storage_location && (
                    <div className="flex items-start gap-2">
                      <MapPin className="h-4 w-4 text-zinc-400 mt-0.5" />
                      <div>
                        <p className="typo-meta text-zinc-500 dark:text-zinc-400">Location</p>
                        <p className="typo-body text-zinc-900 dark:text-zinc-100">{part.storage_location}</p>
                      </div>
                    </div>
                  )}

                  {part.unit_cost !== undefined && part.unit_cost !== null && (
                    <div className="flex items-start gap-2">
                      <DollarSign className="h-4 w-4 text-zinc-400 mt-0.5" />
                      <div>
                        <p className="typo-meta text-zinc-500 dark:text-zinc-400">Unit Cost</p>
                        <p className="typo-body text-zinc-900 dark:text-zinc-100">
                          {part.currency} {part.unit_cost.toFixed(2)}
                        </p>
                      </div>
                    </div>
                  )}

                  {part.supplier_part_number && (
                    <div className="flex items-start gap-2">
                      <Package className="h-4 w-4 text-zinc-400 mt-0.5" />
                      <div>
                        <p className="typo-meta text-zinc-500 dark:text-zinc-400">Supplier P/N</p>
                        <p className="typo-body text-zinc-900 dark:text-zinc-100">{part.supplier_part_number}</p>
                      </div>
                    </div>
                  )}
                </div>

                {/* Description */}
                {part.description && (
                  <div className="border-t border-zinc-200 dark:border-zinc-700 pt-4">
                    <p className="typo-meta text-zinc-500 dark:text-zinc-400 mb-2">Description</p>
                    <p className="typo-body text-zinc-700 dark:text-zinc-300">{part.description}</p>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Footer Actions */}
          <div className="flex items-center justify-between gap-3 px-5 py-4 border-t border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-800/50">
            <button
              onClick={onClose}
              className="px-4 py-2 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-200 dark:hover:bg-zinc-700 rounded-lg transition-colors"
            >
              Close
            </button>

            <div className="flex items-center gap-2">
              {permissions.canAddToShoppingList && (
                <button
                  onClick={handleAddToShoppingList}
                  disabled={actionLoading}
                  className="flex items-center gap-2 px-4 py-2 bg-zinc-100 dark:bg-zinc-700 hover:bg-zinc-200 dark:hover:bg-zinc-600 rounded-lg transition-colors text-zinc-700 dark:text-zinc-300"
                >
                  <ShoppingCart className="h-4 w-4" />
                  Add to Shopping List
                </button>
              )}

              {permissions.canConsume && (
                <button
                  onClick={handleConsume}
                  disabled={actionLoading || (part?.quantity_on_hand ?? 0) <= 0}
                  className="flex items-center gap-2 px-4 py-2 bg-amber-100 dark:bg-amber-900/30 hover:bg-amber-200 dark:hover:bg-amber-900/50 rounded-lg transition-colors text-amber-700 dark:text-amber-400 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ArrowUpFromLine className="h-4 w-4" />
                  Consume
                </button>
              )}

              {permissions.canReceive && (
                <button
                  onClick={handleReceive}
                  disabled={actionLoading}
                  className="flex items-center gap-2 px-4 py-2 bg-emerald-500 hover:bg-emerald-600 rounded-lg transition-colors text-white"
                >
                  <ArrowDownToLine className="h-4 w-4" />
                  Receive
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
