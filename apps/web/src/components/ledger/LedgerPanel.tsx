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
import { X, BookOpen, Edit3, Eye, ChevronDown, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { supabase } from '@/lib/supabaseClient';
import { useAuth } from '@/hooks/useAuth';

const RENDER_API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

// ============================================================================
// TYPES
// ============================================================================

interface LedgerEvent {
  id: string;
  yacht_id: string;
  user_id: string;
  user_role: string | null;
  event_type: string;
  action: string;
  entity_type: string;
  entity_id: string;
  change_summary: string | null;
  new_state: Record<string, unknown> | null;
  metadata: {
    display_name?: string;
    user_name?: string;
    domain?: string;
    note_text?: string;
    checklist_title?: string;
  } | null;
  event_timestamp: string;
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

function groupEventsByDay(events: LedgerEvent[]): DayGroup[] {
  const groups: Map<string, DayGroup> = new Map();

  for (const event of events) {
    const date = new Date(event.event_timestamp).toISOString().split('T')[0];

    if (!groups.has(date)) {
      groups.set(date, {
        date,
        displayDate: formatDate(event.event_timestamp),
        mutationCount: 0,
        readCount: 0,
        events: [],
      });
    }

    const group = groups.get(date)!;
    group.events.push(event);

    if (event.event_type === 'mutation') {
      group.mutationCount++;
    } else if (event.event_type === 'read') {
      group.readCount++;
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
  const [events, setEvents] = useState<LedgerEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [expandedDays, setExpandedDays] = useState<Set<string>>(new Set());
  const [showReads, setShowReads] = useState(false);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const loadMoreRef = useRef<HTMLDivElement>(null);

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

      // Call Render API (which has access to tenant DB)
      const response = await fetch(
        `${RENDER_API_URL}/v1/ledger/events?limit=${LIMIT}&offset=${offset}`,
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
  }, [user, loading, events.length]);

  // Initial load when panel opens
  useEffect(() => {
    if (isOpen && events.length === 0) {
      fetchEvents(true);
    }
  }, [isOpen, events.length, fetchEvents]);

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
        'pt-[var(--celeste-page-top-offset)] pb-8'
      )}
      onClick={onClose}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-celeste-black/40 backdrop-blur-sm" />

      {/* Panel */}
      <div
        className={cn(
          'relative w-full max-w-[var(--celeste-max-width-search)]',
          'bg-celeste-surface rounded-[var(--celeste-border-radius-xl)]',
          'shadow-2xl overflow-hidden',
          'flex flex-col max-h-[70vh]'
        )}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-celeste-divider">
          <div className="flex items-center gap-3">
            <BookOpen className="w-5 h-5 text-celeste-accent" strokeWidth={1.5} />
            <h2 className="text-celeste-text-title font-medium">Ledger</h2>
          </div>
          <div className="flex items-center gap-3">
            {/* Show/Hide Reads Toggle */}
            <button
              onClick={() => setShowReads(!showReads)}
              className={cn(
                'flex items-center gap-2 px-3 py-1.5 rounded-full text-sm transition-colors',
                showReads
                  ? 'bg-celeste-accent text-celeste-white'
                  : 'text-celeste-text-muted hover:text-celeste-text-secondary hover:bg-celeste-panel'
              )}
            >
              <Eye className="w-4 h-4" strokeWidth={1.5} />
              <span>Reads</span>
            </button>
            {/* Close Button */}
            <button
              onClick={onClose}
              className="p-2 rounded-full text-celeste-text-muted hover:text-celeste-text-secondary hover:bg-celeste-panel transition-colors"
              aria-label="Close ledger"
            >
              <X className="w-5 h-5" strokeWidth={1.5} />
            </button>
          </div>
        </div>

        {/* Events List */}
        <div
          ref={scrollContainerRef}
          className="flex-1 overflow-y-auto px-4 py-3"
        >
          {dayGroups.length === 0 && !loading ? (
            <div className="flex flex-col items-center justify-center py-12 text-celeste-text-muted">
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
                    'rounded-[var(--celeste-border-radius-md)]',
                    'bg-celeste-panel text-celeste-text-primary',
                    'hover:bg-celeste-bg-tertiary transition-colors',
                    'sticky top-0 z-10'
                  )}
                >
                  <div className="flex items-center gap-2">
                    {expandedDays.has(group.date) ? (
                      <ChevronDown className="w-4 h-4 text-celeste-text-muted" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-celeste-text-muted" />
                    )}
                    <span className="font-medium">{group.displayDate}</span>
                  </div>
                  <div className="flex items-center gap-3 text-sm">
                    <span className="flex items-center gap-1 text-celeste-green">
                      <Edit3 className="w-3.5 h-3.5" />
                      {group.mutationCount}
                    </span>
                    {showReads && group.readCount > 0 && (
                      <span className="flex items-center gap-1 text-celeste-orange">
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
                      .filter((e) => showReads || e.event_type === 'mutation')
                      .map((event) => (
                        <LedgerEventRow key={event.id} event={event} />
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
                <div className="w-5 h-5 border-2 border-celeste-accent border-t-transparent rounded-full animate-spin" />
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
}

function LedgerEventRow({ event }: LedgerEventRowProps) {
  const displayName = event.metadata?.display_name || `${event.entity_type} ${event.entity_id.slice(0, 8)}`;
  const userName = event.metadata?.user_name || 'Unknown';
  const actionVerb = formatActionVerb(event.action);
  const time = new Date(event.event_timestamp).toLocaleTimeString('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
  });

  return (
    <div
      className={cn(
        'flex items-start gap-3 px-3 py-2',
        'rounded-[var(--celeste-border-radius-sm)]',
        'hover:bg-celeste-panel transition-colors cursor-pointer'
      )}
    >
      {/* Icon */}
      <div
        className={cn(
          'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center',
          event.event_type === 'mutation'
            ? 'bg-celeste-green/10 text-celeste-green'
            : 'bg-celeste-orange/10 text-celeste-orange'
        )}
      >
        {event.event_type === 'mutation' ? (
          <Edit3 className="w-4 h-4" strokeWidth={1.5} />
        ) : (
          <Eye className="w-4 h-4" strokeWidth={1.5} />
        )}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        {/* Object — Verb format */}
        <p className="text-celeste-text-primary truncate">
          <span className="font-medium">{displayName}</span>
          <span className="text-celeste-text-muted"> — </span>
          <span>{actionVerb}</span>
        </p>
        {/* Attribution */}
        <p className="text-sm text-celeste-text-muted truncate">
          {userName} · {time}
        </p>
      </div>
    </div>
  );
}

// ============================================================================
// HELPERS
// ============================================================================

function formatActionVerb(action: string): string {
  const verbMap: Record<string, string> = {
    add_note: 'Added Note',
    add_checklist_item: 'Added Checklist Item',
    create: 'Created',
    update: 'Updated',
    delete: 'Deleted',
    view: 'Viewed',
    open: 'Opened',
    close: 'Closed',
    complete: 'Completed',
  };

  return verbMap[action] || action.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

export default LedgerPanel;
