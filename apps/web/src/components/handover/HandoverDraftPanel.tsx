'use client';

/**
 * HandoverDraftPanel - View and manage personal handover draft items
 *
 * Per requirements:
 * - Shows ONLY current user's handover items (added_by = user_id)
 * - Excludes already exported items
 * - Allows edit, delete of own items
 * - Export button triggers handover-export service
 * - Export action logged to ledger
 * - UX matches search bar results (chronological, timestamps, no UUIDs)
 */

import React, { useEffect, useState, useRef, useCallback } from 'react';
import { X, FileText, Edit3, Trash2, Send, AlertTriangle, Clock, Loader2, CheckCircle2, Package, Wrench, File, ChevronDown, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { supabase } from '@/lib/supabaseClient';
import { useAuth } from '@/hooks/useAuth';
import { useSurface } from '@/contexts/SurfaceContext';
import { toast } from 'sonner';
// External service functions no longer used - export creates local record
// import { startExportJob, checkJobStatus } from '@/lib/handoverExportClient';

const RENDER_API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

// ============================================================================
// TYPES
// ============================================================================

interface HandoverItem {
  id: string;
  yacht_id: string;
  entity_id: string;
  entity_type: string;
  section: string | null;
  summary: string | null;
  category: string | null;
  priority: number;
  status: string;
  is_critical: boolean;
  requires_action: boolean;
  action_summary: string | null;
  risk_tags: string[] | null;
  added_by: string;
  created_at: string;
  updated_at: string | null;
  metadata: Record<string, unknown> | null;
}

interface DayGroup {
  date: string;
  displayDate: string;
  items: HandoverItem[];
}

interface HandoverDraftPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

// ============================================================================
// HELPERS
// ============================================================================

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);

  if (date.toDateString() === today.toDateString()) {
    return 'Today';
  }
  if (date.toDateString() === yesterday.toDateString()) {
    return 'Yesterday';
  }

  const options: Intl.DateTimeFormatOptions = {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
  };
  return date.toLocaleDateString('en-GB', options);
}

function formatTime(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
}

function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return formatDate(dateStr);
}

function groupItemsByDay(items: HandoverItem[]): DayGroup[] {
  const groups: Map<string, DayGroup> = new Map();

  for (const item of items) {
    const date = new Date(item.created_at).toISOString().split('T')[0];

    if (!groups.has(date)) {
      groups.set(date, {
        date,
        displayDate: formatDate(item.created_at),
        items: [],
      });
    }

    groups.get(date)!.items.push(item);
  }

  // Sort by date descending
  return Array.from(groups.values()).sort(
    (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()
  );
}

function getEntityIcon(entityType: string) {
  switch (entityType) {
    case 'fault':
      return AlertTriangle;
    case 'work_order':
      return Wrench;
    case 'equipment':
      return Package;
    case 'document':
      return File;
    default:
      return FileText;
  }
}

function getEntityLabel(entityType: string): string {
  switch (entityType) {
    case 'fault':
      return 'Fault';
    case 'work_order':
      return 'Work Order';
    case 'equipment':
      return 'Equipment';
    case 'part':
      return 'Part';
    case 'document':
      return 'Document';
    case 'note':
      return 'Note';
    default:
      return entityType.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  }
}

// ============================================================================
// EDIT MODAL
// ============================================================================

interface EditModalProps {
  item: HandoverItem;
  onSave: (id: string, summary: string, category: string, isCritical: boolean, requiresAction: boolean) => Promise<void>;
  onClose: () => void;
}

function EditModal({ item, onSave, onClose }: EditModalProps) {
  const [summary, setSummary] = useState(item.summary || '');
  const [category, setCategory] = useState(item.category || 'fyi');
  const [isCritical, setIsCritical] = useState(item.is_critical);
  const [requiresAction, setRequiresAction] = useState(item.requires_action);
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await onSave(item.id, summary, category, isCritical, requiresAction);
      onClose();
    } catch (err) {
      toast.error('Failed to save changes');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[10003] flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="relative bg-surface-elevated border border-surface-border rounded-lg shadow-xl w-full max-w-md mx-4 p-6">
        <h3 className="text-lg font-semibold text-txt-primary mb-4">Edit Handover Note</h3>
        <form onSubmit={handleSubmit}>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-txt-secondary mb-1">Summary</label>
              <textarea
                value={summary}
                onChange={(e) => setSummary(e.target.value)}
                rows={3}
                className="w-full px-3 py-2 bg-surface-primary border border-surface-border rounded-md text-txt-primary text-sm focus:outline-none focus:ring-2 focus:ring-brand-interactive"
                placeholder="Describe the handover note..."
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-txt-secondary mb-1">Category</label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full px-3 py-2 bg-surface-primary border border-surface-border rounded-md text-txt-primary text-sm focus:outline-none focus:ring-2 focus:ring-brand-interactive"
              >
                <option value="fyi">FYI</option>
                <option value="urgent">Urgent</option>
                <option value="in_progress">In Progress</option>
                <option value="completed">Completed</option>
                <option value="watch">Watch</option>
              </select>
            </div>
            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={isCritical}
                  onChange={(e) => setIsCritical(e.target.checked)}
                  className="w-4 h-4 rounded border-surface-border text-status-critical focus:ring-status-critical"
                />
                <span className="text-sm text-txt-secondary">Critical</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={requiresAction}
                  onChange={(e) => setRequiresAction(e.target.checked)}
                  className="w-4 h-4 rounded border-surface-border text-status-warning focus:ring-status-warning"
                />
                <span className="text-sm text-txt-secondary">Requires Action</span>
              </label>
            </div>
          </div>
          <div className="flex justify-end gap-3 mt-6">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-txt-secondary hover:text-txt-primary transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 text-sm font-medium bg-brand-interactive text-white rounded-md hover:bg-brand-interactive/90 transition-colors disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export function HandoverDraftPanel({ isOpen, onClose }: HandoverDraftPanelProps) {
  const { user } = useAuth();
  const { showContext } = useSurface();
  const [items, setItems] = useState<HandoverItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [expandedDays, setExpandedDays] = useState<Set<string>>(new Set());
  const [editingItem, setEditingItem] = useState<HandoverItem | null>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  // Fetch user's handover items
  const fetchItems = useCallback(async () => {
    if (!user?.id || !user?.yachtId) return;

    setLoading(true);
    try {
      // Get exported item IDs to exclude
      const { data: exports } = await supabase
        .from('handover_exports')
        .select('edited_content')
        .eq('yacht_id', user.yachtId)
        .not('export_status', 'eq', 'failed');

      const exportedItemIds = new Set<string>();
      exports?.forEach(exp => {
        const itemIds = (exp.edited_content as any)?.item_ids || [];
        itemIds.forEach((id: string) => exportedItemIds.add(id));
      });

      // Fetch user's draft items (not deleted, not exported)
      const { data, error } = await supabase
        .from('handover_items')
        .select('*')
        .eq('yacht_id', user.yachtId)
        .eq('added_by', user.id)
        .is('deleted_at', null)
        .neq('export_status', 'exported')
        .order('created_at', { ascending: false });

      if (error) {
        console.error('[HandoverDraftPanel] Fetch error:', error);
        toast.error('Failed to load handover items');
        return;
      }

      // Filter out exported items
      const draftItems = (data || []).filter(item => !exportedItemIds.has(item.id));
      setItems(draftItems);

      // Auto-expand today's items
      const today = new Date().toISOString().split('T')[0];
      setExpandedDays(new Set([today]));
    } catch (err) {
      console.error('[HandoverDraftPanel] Error:', err);
      toast.error('Failed to load handover items');
    } finally {
      setLoading(false);
    }
  }, [user?.id, user?.yachtId]);

  useEffect(() => {
    if (isOpen) {
      fetchItems();
    }
  }, [isOpen, fetchItems]);

  // Handle item click - navigate to entity
  const handleItemClick = useCallback((item: HandoverItem) => {
    if (!item.entity_type || !item.entity_id) return;
    showContext(item.entity_type, item.entity_id);
    onClose();
  }, [showContext, onClose]);

  // Handle edit
  const handleEdit = useCallback(async (id: string, summary: string, category: string, isCritical: boolean, requiresAction: boolean) => {
    if (!user?.id) return;

    const { error } = await supabase
      .from('handover_items')
      .update({
        summary,
        category,
        is_critical: isCritical,
        requires_action: requiresAction,
        updated_at: new Date().toISOString(),
        updated_by: user.id,
      })
      .eq('id', id)
      .eq('added_by', user.id); // Ensure user can only edit their own

    if (error) {
      console.error('[HandoverDraftPanel] Edit error:', error);
      throw error;
    }

    toast.success('Handover note updated');
    fetchItems();
  }, [user?.id, fetchItems]);

  // Handle delete
  const handleDelete = useCallback(async (item: HandoverItem) => {
    if (!user?.id) return;
    if (!confirm('Delete this handover note?')) return;

    const { error } = await supabase
      .from('handover_items')
      .update({
        deleted_at: new Date().toISOString(),
        deleted_by: user.id,
        deletion_reason: 'User deleted from draft panel',
      })
      .eq('id', item.id)
      .eq('added_by', user.id); // Ensure user can only delete their own

    if (error) {
      console.error('[HandoverDraftPanel] Delete error:', error);
      toast.error('Failed to delete item');
      return;
    }

    toast.success('Handover note deleted');
    fetchItems();
  }, [user?.id, fetchItems]);

  // Handle export - creates local export record with editable content
  const handleExport = useCallback(async () => {
    if (!user?.id || !user?.yachtId || items.length === 0) return;

    setExporting(true);
    try {
      // Build editable content JSON from items
      const editableContent = {
        title: `Handover Report - ${new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}`,
        generated_at: new Date().toISOString(),
        yacht_id: user.yachtId,
        prepared_by: user.displayName || user.email || 'Unknown',
        sections: items.map((item, idx) => ({
          id: `section-${item.id.slice(0, 8)}`,
          title: item.entity_type ? item.entity_type.charAt(0).toUpperCase() + item.entity_type.slice(1).replace('_', ' ') : 'Note',
          content: item.summary || '',
          items: [{
            id: `item-${item.id.slice(0, 8)}`,
            content: item.summary || '',
            entity_type: item.entity_type,
            entity_id: item.entity_id,
            priority: item.is_critical ? 'critical' : item.requires_action ? 'action' : 'fyi',
          }],
          is_critical: item.is_critical,
          order: idx,
        })),
        signature_section: {
          outgoing: { role: 'outgoing', signer_name: null, signed_at: null, signature_image: null },
          incoming: { role: 'incoming', signer_name: null, signed_at: null, signature_image: null },
          hod: null,
        },
        metadata: {
          source: 'handover_draft_panel',
          parsed_at: new Date().toISOString(),
          section_count: items.length,
          has_critical: items.some(i => i.is_critical),
        },
      };

      // Create handover_exports record
      const { data: exportRecord, error: exportError } = await supabase
        .from('handover_exports')
        .insert({
          yacht_id: user.yachtId,
          created_by: user.id,
          title: editableContent.title,
          item_count: items.length,
          edited_content: editableContent,
          status: 'ready',
          review_status: 'pending_review',
          export_status: 'pending',
        })
        .select('id')
        .single();

      if (exportError) {
        console.error('[HandoverDraftPanel] Export record error:', exportError);
        throw new Error('Failed to create export record');
      }

      // Mark items as exported
      const itemIds = items.map(i => i.id);
      await supabase
        .from('handover_items')
        .update({ export_status: 'exported', status: 'exported' })
        .in('id', itemIds);

      // Log to ledger for user notification
      const { data: sessionData } = await supabase.auth.getSession();
      const token = sessionData?.session?.access_token;
      if (token) {
        fetch(`${RENDER_API_URL}/v1/ledger/record`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            event_name: 'handover_export_ready',
            payload: {
              yacht_id: user.yachtId,
              user_id: user.id,
              export_id: exportRecord.id,
              item_count: items.length,
              has_critical: items.some(i => i.is_critical),
            },
          }),
        }).catch(() => {});
      }

      toast.success('Your handover will be visible in ledger when complete (~5 minutes)');
      fetchItems(); // Refresh to hide exported items
    } catch (err) {
      console.error('[HandoverDraftPanel] Export error:', err);
      toast.error(err instanceof Error ? err.message : 'Failed to export handover');
    } finally {
      setExporting(false);
    }
  }, [user?.id, user?.yachtId, user?.displayName, user?.email, items, fetchItems, supabase]);

  // Toggle day expansion
  const toggleDay = useCallback((date: string) => {
    setExpandedDays(prev => {
      const next = new Set(prev);
      if (next.has(date)) {
        next.delete(date);
      } else {
        next.add(date);
      }
      return next;
    });
  }, []);

  if (!isOpen) return null;

  const groupedItems = groupItemsByDay(items);
  const criticalCount = items.filter(i => i.is_critical).length;
  const actionCount = items.filter(i => i.requires_action).length;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-[10001] bg-black/40"
        onClick={onClose}
      />

      {/* Panel */}
      <div
        className={cn(
          'fixed right-0 top-0 bottom-0 z-[10002]',
          'w-full max-w-md',
          'bg-surface-base border-l border-surface-border',
          'flex flex-col',
          'shadow-2xl'
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-surface-border">
          <div className="flex items-center gap-3">
            <FileText className="w-5 h-5 text-txt-secondary" />
            <div>
              <h2 className="text-lg font-semibold text-txt-primary">My Handover Draft</h2>
              <p className="text-xs text-txt-tertiary">
                {items.length} item{items.length !== 1 ? 's' : ''} pending
                {criticalCount > 0 && <span className="text-status-critical ml-2">{criticalCount} critical</span>}
                {actionCount > 0 && <span className="text-status-warning ml-2">{actionCount} action</span>}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-md text-txt-secondary hover:text-txt-primary hover:bg-surface-hover transition-colors"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Export Button */}
        {items.length > 0 && (
          <div className="px-6 py-3 border-b border-surface-border">
            <button
              onClick={handleExport}
              disabled={exporting}
              className={cn(
                'w-full flex items-center justify-center gap-2',
                'px-4 py-2.5 rounded-lg',
                'bg-brand-interactive text-white font-medium',
                'hover:bg-brand-interactive/90 transition-colors',
                'disabled:opacity-50 disabled:cursor-not-allowed'
              )}
            >
              {exporting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Exporting...
                </>
              ) : (
                <>
                  <Send className="w-4 h-4" />
                  Export Handover
                </>
              )}
            </button>
          </div>
        )}

        {/* Content */}
        <div
          ref={scrollContainerRef}
          className="flex-1 overflow-y-auto"
        >
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 animate-spin text-txt-tertiary" />
            </div>
          ) : items.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 px-6 text-center">
              <FileText className="w-12 h-12 text-txt-tertiary mb-4" />
              <p className="text-txt-secondary font-medium">No handover items</p>
              <p className="text-txt-tertiary text-sm mt-1">
                Add notes from faults, work orders, or equipment to include in your handover.
              </p>
            </div>
          ) : (
            <div className="py-2">
              {groupedItems.map((group) => (
                <div key={group.date}>
                  {/* Day Header */}
                  <button
                    onClick={() => toggleDay(group.date)}
                    className="w-full flex items-center gap-2 px-6 py-2 text-left hover:bg-surface-hover transition-colors"
                  >
                    {expandedDays.has(group.date) ? (
                      <ChevronDown className="w-4 h-4 text-txt-tertiary" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-txt-tertiary" />
                    )}
                    <span className="text-sm font-medium text-txt-secondary">{group.displayDate}</span>
                    <span className="text-xs text-txt-tertiary">({group.items.length})</span>
                  </button>

                  {/* Day Items */}
                  {expandedDays.has(group.date) && (
                    <div className="space-y-1 px-4 pb-2">
                      {group.items.map((item) => {
                        const Icon = getEntityIcon(item.entity_type);
                        return (
                          <div
                            key={item.id}
                            className="flex items-start gap-3 px-3 py-2.5 rounded-lg bg-surface-primary hover:bg-surface-hover transition-colors group"
                          >
                            {/* Entity Icon */}
                            <div className={cn(
                              'flex-shrink-0 w-8 h-8 rounded-md flex items-center justify-center',
                              item.is_critical ? 'bg-status-critical/10 text-status-critical' :
                              item.requires_action ? 'bg-status-warning/10 text-status-warning' :
                              'bg-surface-hover text-txt-secondary'
                            )}>
                              <Icon className="w-4 h-4" />
                            </div>

                            {/* Content */}
                            <div
                              className="flex-1 min-w-0 cursor-pointer"
                              onClick={() => handleItemClick(item)}
                            >
                              <div className="flex items-center gap-2">
                                <span className="text-xs font-medium text-txt-tertiary uppercase">
                                  {getEntityLabel(item.entity_type)}
                                </span>
                                {item.is_critical && (
                                  <span className="px-1.5 py-0.5 text-[10px] font-medium bg-status-critical/10 text-status-critical rounded">
                                    CRITICAL
                                  </span>
                                )}
                                {item.requires_action && (
                                  <span className="px-1.5 py-0.5 text-[10px] font-medium bg-status-warning/10 text-status-warning rounded">
                                    ACTION
                                  </span>
                                )}
                              </div>
                              <p className="text-sm text-txt-primary line-clamp-2 mt-0.5">
                                {item.summary || 'No summary'}
                              </p>
                              <div className="flex items-center gap-2 mt-1">
                                <Clock className="w-3 h-3 text-txt-tertiary" />
                                <span className="text-xs text-txt-tertiary">
                                  {formatTime(item.created_at)}
                                </span>
                                {item.category && (
                                  <span className="text-xs text-txt-tertiary px-1.5 py-0.5 bg-surface-hover rounded">
                                    {item.category}
                                  </span>
                                )}
                              </div>
                            </div>

                            {/* Actions */}
                            <div className="flex-shrink-0 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setEditingItem(item);
                                }}
                                className="p-1.5 rounded text-txt-tertiary hover:text-txt-primary hover:bg-surface-hover transition-colors"
                                title="Edit"
                              >
                                <Edit3 className="w-4 h-4" />
                              </button>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleDelete(item);
                                }}
                                className="p-1.5 rounded text-txt-tertiary hover:text-status-critical hover:bg-status-critical/10 transition-colors"
                                title="Delete"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Edit Modal */}
      {editingItem && (
        <EditModal
          item={editingItem}
          onSave={handleEdit}
          onClose={() => setEditingItem(null)}
        />
      )}
    </>
  );
}

export default HandoverDraftPanel;
