'use client';

/**
 * LedgerPanel - Infinite scroll audit trail display
 *
 * Displays ledger events in chronological order grouped by day.
 * Mimics the UX of the search results panel.
 *
 * Design requirements:
 * - Grouped by day with anchor counts (mutations/reads)
 * - Event grammar: Object — Verb
 * - Reads collapsed by default, mutations prominent
 * - Uses tokenized design values (no hardcoded colors)
 * - Proper z-index layering
 */

import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { X, BookOpen, Edit3, Eye, ChevronDown, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { supabase } from '@/lib/supabaseClient';
import { useAuth } from '@/hooks/useAuth';
import { getEntityRoute } from '@/lib/featureFlags';

const RENDER_API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

// ============================================================================
// TYPES
// ============================================================================

interface LedgerEvent {
  id: string;
  yacht_id: string;
  user_id: string;
  event_type: string;  // create, update, delete, status_change, assignment, etc.
  entity_type: string; // work_order, checklist_item, fault, etc.
  entity_id: string;
  action: string;      // add_note, add_checklist_item, artefact_opened, etc.
  change_summary?: string;
  user_role?: string;
  metadata: {
    domain?: string;
    user_name?: string;
    work_order_id?: string;
    checklist_item_id?: string;
    note_text?: string;
    note_preview?: string;
    checklist_title?: string;
    display_name?: string;
    artefact_type?: string;
    artefact_id?: string;
    [key: string]: unknown;
  } | null;
  created_at: string;
}

interface DayGroup {
  date: string;
  displayDate: string;
  mutationCount: number;
  readCount: number;
  events: LedgerEvent[];
}

interface LedgerPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

// ============================================================================
// HELPERS
// ============================================================================

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  const options: Intl.DateTimeFormatOptions = {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    year: '2-digit',
  };
  return date.toLocaleDateString('en-GB', options);
}

// Read events are navigation/view events; mutations are changes
const READ_ACTIONS = ['artefact_opened', 'situation_ended', 'view', 'open'];

function groupEventsByDay(events: LedgerEvent[]): DayGroup[] {
  const groups: Map<string, DayGroup> = new Map();

  for (const event of events) {
    const date = new Date(event.created_at).toISOString().split('T')[0];

    if (!groups.has(date)) {
      groups.set(date, {
        date,
        displayDate: formatDate(event.created_at),
        mutationCount: 0,
        readCount: 0,
        events: [],
      });
    }

    const group = groups.get(date)!;
    group.events.push(event);

    // Classify based on action field
    if (READ_ACTIONS.includes(event.action)) {
      group.readCount++;
    } else {
      group.mutationCount++;
    }
  }

  // Sort by date descending
  return Array.from(groups.values()).sort(
    (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()
  );
}

// ============================================================================
// COMPONENT
// ============================================================================

export function LedgerPanel({ isOpen, onClose }: LedgerPanelProps) {
  const { user } = useAuth();
  const router = useRouter();
  const [events, setEvents] = useState<LedgerEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [expandedDays, setExpandedDays] = useState<Set<string>>(new Set());
  const [showReads, setShowReads] = useState(false);
  const [viewMode, setViewMode] = useState<'me' | 'department'>('me');
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const loadMoreRef = useRef<HTMLDivElement>(null);

  // Handle ledger item click - navigate to entity route
  const handleItemClick = useCallback((event: LedgerEvent) => {
    if (!event.entity_type || !event.entity_id) {
      console.warn('[LedgerPanel] Cannot navigate: missing entity_type or entity_id', event);
      return;
    }

    // Map entity_type from ledger (pms_work_orders) to lens type (work_order)
    const entityTypeMap: Record<string, string> = {
      'pms_work_orders': 'work_order',
      'pms_work_order_notes': 'work_order',
      'pms_work_order_checklist_items': 'work_order',
      'pms_faults': 'fault',
      'pms_equipment': 'equipment',
      'pms_parts': 'part',
      'pms_receiving': 'receiving',
      'pms_documents': 'document',
      'pms_certificates': 'certificate',
      'pms_handovers': 'handover',
      'handover_export': 'handover_export',
      'pms_hours_of_rest': 'hours_of_rest',
      'pms_hor_monthly_signoffs': 'hours_of_rest_signoff',
      'pms_warranties': 'warranty',
      'pms_shopping_lists': 'shopping_list',
    };

    // Use mapped type or fall back to raw entity_type
    const lensType = entityTypeMap[event.entity_type] || event.entity_type;

    // For child entities (notes, checklist items), use parent ID if available
    const entityId = event.metadata?.work_order_id || event.entity_id;

    console.log('[LedgerPanel] Navigating to:', lensType, entityId);

    router.push(getEntityRoute(lensType as Parameters<typeof getEntityRoute>[0], entityId));

    // Close ledger panel after navigation
    onClose();
  }, [router, onClose]);

  const LIMIT = 50;

  // Fetch ledger events from Render API (tenant DB)
  const fetchEvents = useCallback(async (reset = false) => {
    if (!user || loading) return;

    setLoading(true);
    try {
      const offset = reset ? 0 : events.length;

      // Get auth token for Render API
      const { data: sessionData } = await supabase.auth.getSession();
      const token = sessionData?.session?.access_token;

      if (!token) {
        console.error('No auth token available for ledger fetch');
        return;
      }

      // 'me' mode: explicit self-filter via /events (your actions regardless of role)
      // 'department' mode: role-scoped via /timeline (captain=all, HoD=dept, crew=self)
      const endpoint = viewMode === 'me' ? '/v1/ledger/events' : '/v1/ledger/timeline';
      const params = new URLSearchParams({
        limit: String(LIMIT),
        offset: String(offset),
      });
      if (viewMode === 'me' && user?.id) {
        params.set('user_id', user.id);
      }

      // Call Render API (which has access to tenant DB)
      const response = await fetch(
        `${RENDER_API_URL}${endpoint}?${params.toString()}`,
        {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        }
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error('Failed to fetch ledger events:', errorData);
        return;
      }

      const result = await response.json();
      const fetchedEvents = result.events || [];

      if (reset) {
        setEvents(fetchedEvents);
      } else {
        setEvents((prev) => [...prev, ...fetchedEvents]);
      }

      setHasMore(result.has_more ?? fetchedEvents.length === LIMIT);
    } catch (err) {
      console.error('Ledger fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, [user, loading, events.length, viewMode]);

  // Initial load when panel opens
  useEffect(() => {
    if (isOpen && events.length === 0) {
      fetchEvents(true);
    }
  }, [isOpen, events.length, fetchEvents]);

  // Reset and refetch when viewMode changes
  useEffect(() => {
    if (isOpen) {
      setEvents([]);
      setHasMore(true);
      fetchEvents(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [viewMode]);

  // Infinite scroll observer
  useEffect(() => {
    if (!isOpen || !hasMore || loading) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) {
          fetchEvents();
        }
      },
      { threshold: 0.1 }
    );

    const sentinel = loadMoreRef.current;
    if (sentinel) {
      observer.observe(sentinel);
    }

    return () => {
      if (sentinel) {
        observer.unobserve(sentinel);
      }
    };
  }, [isOpen, hasMore, loading, fetchEvents]);

  // Group events by day
  const dayGroups = groupEventsByDay(events);

  // Toggle day expansion
  const toggleDay = (date: string) => {
    setExpandedDays((prev) => {
      const next = new Set(prev);
      if (next.has(date)) {
        next.delete(date);
      } else {
        next.add(date);
      }
      return next;
    });
  };

  if (!isOpen) return null;

  return (
    <div
      className={cn(
        'fixed inset-0 z-50 flex items-start justify-center',
        'pt-ds-16 pb-8'
      )}
      onClick={onClose}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 backdrop-blur-sm" style={{ background: 'rgba(0,0,0,0.4)' }} />

      {/* Panel */}
      <div
        className={cn(
          'relative w-full max-w-[var(--celeste-max-width-search)]',
          'bg-surface-primary rounded-lg',
          'border border-surface-border overflow-hidden',
          'flex flex-col max-h-[70vh]'
        )}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b" style={{ borderColor: 'var(--border-sub)' }}>
          <div className="flex items-center gap-3">
            <BookOpen className="w-5 h-5" style={{ color: 'var(--mark)' }} strokeWidth={1.5} />
            <h2 className="font-medium" style={{ color: 'var(--txt)' }}>Ledger</h2>
          </div>

          {/* Me / Department Pill Toggle - Centered */}
          <div className="flex items-center rounded-full p-1" style={{ background: 'var(--surface-hover)' }} data-testid="view-mode-toggle">
            <button
              onClick={() => setViewMode('me')}
              className={cn(
                'px-4 py-1.5 rounded-full typo-body font-medium transition-colors',
                viewMode !== 'me' && ''
              )}
              style={viewMode === 'me'
                ? { background: 'var(--teal)', color: 'var(--txt)' }
                : { color: 'var(--txt3)' }
              }
              data-testid="view-mode-me"
            >
              Me
            </button>
            <button
              onClick={() => setViewMode('department')}
              className={cn(
                'px-4 py-1.5 rounded-full typo-body font-medium transition-colors',
                viewMode !== 'department' && ''
              )}
              style={viewMode === 'department'
                ? { background: 'var(--teal)', color: 'var(--txt)' }
                : { color: 'var(--txt3)' }
              }
              data-testid="view-mode-department"
            >
              Department
            </button>
          </div>

          <div className="flex items-center gap-3">
            {/* Show/Hide Reads Toggle */}
            <button
              onClick={() => setShowReads(!showReads)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-full typo-body transition-colors"
              style={showReads
                ? { background: 'var(--teal)', color: 'var(--txt)' }
                : { color: 'var(--txt3)' }
              }
            >
              <Eye className="w-4 h-4" strokeWidth={1.5} />
              <span>Reads</span>
            </button>
            {/* Close Button */}
            <button
              onClick={onClose}
              className="btn-icon h-8 w-8"
              aria-label="Close ledger"
            >
              <X className="w-[18px] h-[18px]" strokeWidth={1.5} />
            </button>
          </div>
        </div>

        {/* Events List */}
        <div
          ref={scrollContainerRef}
          className="flex-1 overflow-y-auto px-4 py-3"
        >
          {dayGroups.length === 0 && !loading ? (
            <div className="flex flex-col items-center justify-center py-12" style={{ color: 'var(--txt3)' }}>
              <BookOpen className="w-12 h-12 mb-3 opacity-50" strokeWidth={1} />
              <p>No events recorded yet</p>
            </div>
          ) : (
            dayGroups.map((group) => (
              <div key={group.date} className="mb-4">
                {/* Day Anchor */}
                <button
                  onClick={() => toggleDay(group.date)}
                  className={cn(
                    'w-full flex items-center justify-between px-3 py-2',
                    'rounded-md',
                    'transition-colors',
                    'sticky top-0 z-10'
                  )}
                  style={{ background: 'var(--surface-hover)', color: 'var(--txt)' }}
                >
                  <div className="flex items-center gap-2">
                    {expandedDays.has(group.date) ? (
                      <ChevronDown className="w-4 h-4" style={{ color: 'var(--txt3)' }} />
                    ) : (
                      <ChevronRight className="w-4 h-4" style={{ color: 'var(--txt3)' }} />
                    )}
                    <span className="font-medium">{group.displayDate}</span>
                  </div>
                  <div className="flex items-center gap-3 typo-body">
                    <span className="flex items-center gap-1 text-green-500">
                      <Edit3 className="w-3.5 h-3.5" />
                      {group.mutationCount}
                    </span>
                    {showReads && group.readCount > 0 && (
                      <span className="flex items-center gap-1 text-orange-500">
                        <Eye className="w-3.5 h-3.5" />
                        {group.readCount}
                      </span>
                    )}
                  </div>
                </button>

                {/* Events for this day */}
                {expandedDays.has(group.date) && (
                  <div className="mt-2 space-y-1 pl-6">
                    {group.events
                      .filter((e) => showReads || !READ_ACTIONS.includes(e.action))
                      .map((event) => (
                        <LedgerEventRow key={event.id} event={event} onItemClick={handleItemClick} />
                      ))}
                  </div>
                )}
              </div>
            ))
          )}

          {/* Load More Sentinel */}
          {hasMore && (
            <div ref={loadMoreRef} className="h-8 flex items-center justify-center">
              {loading && (
                <div className="w-5 h-5 border-2 border-t-transparent rounded-full animate-spin" style={{ borderColor: 'var(--teal)', borderTopColor: 'transparent' }} />
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// EVENT ROW COMPONENT
// ============================================================================

interface LedgerEventRowProps {
  event: LedgerEvent;
  onItemClick: (event: LedgerEvent) => void;
}

function LedgerEventRow({ event, onItemClick }: LedgerEventRowProps) {
  // Build display name from metadata or change_summary
  const displayName = event.change_summary
    || event.metadata?.display_name
    || event.metadata?.checklist_title
    || event.metadata?.artefact_type
    || event.metadata?.domain
    || event.entity_type
    || 'Action';

  const userName = event.metadata?.user_name || event.user_role || 'User';
  const actionVerb = formatActionVerb(event.action);
  const time = new Date(event.created_at).toLocaleTimeString('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
  });

  const isMutation = !READ_ACTIONS.includes(event.action);

  return (
    <div
      className={cn(
        'flex items-start gap-3 px-3 py-2',
        'rounded-md',
        'hover:bg-[var(--surface-hover)] transition-colors cursor-pointer'
      )}
      onClick={() => onItemClick(event)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onItemClick(event);
        }
      }}
    >
      {/* Icon */}
      <div
        className={cn(
          'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center',
          isMutation
            ? 'bg-green-500/10 text-green-500'
            : 'bg-orange-500/10 text-orange-500'
        )}
      >
        {isMutation ? (
          <Edit3 className="w-4 h-4" strokeWidth={1.5} />
        ) : (
          <Eye className="w-4 h-4" strokeWidth={1.5} />
        )}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        {/* Object — Verb format */}
        <p className="truncate" style={{ color: 'var(--txt)' }}>
          <span className="font-medium">{displayName}</span>
          <span style={{ color: 'var(--txt3)' }}> — </span>
          <span>{actionVerb}</span>
        </p>
        {/* Attribution */}
        <p className="typo-body truncate" style={{ color: 'var(--txt3)' }}>
          {userName} · {time}
        </p>
      </div>
    </div>
  );
}

// ============================================================================
// HELPERS
// ============================================================================

function formatActionVerb(eventName: string): string {
  const verbMap: Record<string, string> = {
    // Mutation events
    add_note: 'Added Note',
    add_checklist_item: 'Added Checklist Item',
    add_checklist_note: 'Added Checklist Note',
    add_checklist_photo: 'Added Checklist Photo',
    add_work_order_photo: 'Added Photo',
    add_parts_to_work_order: 'Added Parts',
    mark_checklist_item_complete: 'Completed Item',
    mark_work_order_complete: 'Completed Work Order',
    reassign_work_order: 'Reassigned',
    archive_work_order: 'Archived',
    create: 'Created',
    update: 'Updated',
    delete: 'Deleted',
    // Read events
    artefact_opened: 'Opened',
    situation_ended: 'Ended Situation',
    view: 'Viewed',
    open: 'Opened',
    close: 'Closed',
    complete: 'Completed',
    // Navigation events
    relation_added: 'Added Relation',
  };

  return verbMap[eventName] || eventName.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

