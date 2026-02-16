'use client';

/**
 * CelesteOS Spotlight Search
 * Apple Spotlight-identical implementation
 */

import React, { useEffect, useRef, useCallback, useMemo, useState } from 'react';
import { Search, X, Settings, BookOpen, Mail, ChevronDown, AlertTriangle, ClipboardList, Package, FileText, Award, ArrowRightLeft, ShoppingCart, Receipt, Users, Clock, CheckSquare, MoreHorizontal, type LucideIcon } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { cn } from '@/lib/utils';
import { useCelesteSearch } from '@/hooks/useCelesteSearch';
import { useSituationState } from '@/hooks/useSituationState';
import { useSurfaceSafe } from '@/contexts/SurfaceContext';
import type { SearchResult as APISearchResult } from '@/types/search';
import type { EntityType, SituationDomain } from '@/types/situation';
import SpotlightResultRow from './SpotlightResultRow';
import SettingsModal from '@/components/SettingsModal';
import { EntityLine, StatusLine } from '@/components/celeste';
import { EmailInboxView } from '@/components/email/EmailInboxView';
import SituationRouter from '@/components/situations/SituationRouter';
import SuggestedActions from '@/components/SuggestedActions';
import { LedgerPanel } from '@/components/ledger';
import { toast } from 'sonner';
import { executeAction } from '@/lib/actionClient';
import { supabase } from '@/lib/supabaseClient';
import { useAuth } from '@/hooks/useAuth';
import {
  groupResultsByDomain,
  type GroupedResults,
  type SpotlightResult as GroupedSpotlightResult,
  type DomainGroup,
  DOMAIN_ICONS,
} from '@/lib/spotlightGrouping';

// Domain icon component mapping
const DomainIconMap: Record<string, LucideIcon> = {
  'AlertTriangle': AlertTriangle,
  'ClipboardList': ClipboardList,
  'Settings': Settings,
  'Package': Package,
  'FileText': FileText,
  'Mail': Mail,
  'Award': Award,
  'ArrowRightLeft': ArrowRightLeft,
  'ShoppingCart': ShoppingCart,
  'Receipt': Receipt,
  'Users': Users,
  'Clock': Clock,
  'CheckSquare': CheckSquare,
  'MoreHorizontal': MoreHorizontal,
};

// ============================================================================
// LEDGER TRACKING
// ============================================================================

const RENDER_API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

async function recordLedgerEvent(
  eventName: string,
  payload: Record<string, unknown>
): Promise<void> {
  try {
    const { data: sessionData } = await supabase.auth.getSession();
    const token = sessionData?.session?.access_token;
    if (!token) return;

    // Call Render API to record ledger event
    const response = await fetch(`${RENDER_API_URL}/v1/ledger/record`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        event_name: eventName,
        payload,
      }),
    });

    if (!response.ok) {
      console.warn('[Ledger] Failed to record event:', eventName, response.status);
    }
  } catch (err) {
    console.warn('[Ledger] Error recording event:', err);
  }
}

// ============================================================================
// ROLLING PLACEHOLDER SUGGESTIONS
// ============================================================================

const PLACEHOLDER_SUGGESTIONS = [
  'Find fault 1234',
  'Generator maintenance history',
  'Create work order for...',
  "What's overdue this week?",
  'Parts low in stock',
  'Show recent handovers',
  'Equipment status summary',
  'Search documents...',
];

// ============================================================================
// TYPES
// ============================================================================

export interface SpotlightResult {
  id: string;
  type: string;
  title: string;
  subtitle: string;
  icon?: string;
  metadata?: Record<string, unknown>;
}

interface SpotlightSearchProps {
  onClose?: () => void;
  isModal?: boolean;
  className?: string;
}

// ============================================================================
// RESULT MAPPING
// ============================================================================

function mapAPIResult(result: APISearchResult): SpotlightResult {
  // Backend returns different field names than frontend expects
  // Map backend schema → frontend schema
  const anyResult = result as any;

  // Try to extract title from various possible fields
  let title =
    result.title ||
    anyResult.name ||
    anyResult.equipment_name ||
    anyResult.part_name ||
    anyResult.section_title ||
    anyResult.document_name ||
    anyResult.filename ||
    anyResult.code ||
    '';

  // If title is generic or missing, try to extract from content fields
  if (!title || title === 'Untitled' || title === 'Untitled Result') {
    // Try subtitle/snippet/preview for better title
    const contentText = result.subtitle || result.snippet || result.preview || anyResult.content || anyResult.text || '';
    if (contentText) {
      // Extract first meaningful sentence (up to 80 chars)
      const firstSentence = contentText.split(/[.!?]|  /)[0].trim();
      if (firstSentence.length > 0 && firstSentence.length < 120) {
        title = firstSentence;
      } else if (contentText.length > 0) {
        // Use first 80 characters
        title = contentText.substring(0, 80).trim();
      }
    }
  }

  // Final fallback
  if (!title) {
    title = result.id ? `Document ${result.id.substring(0, 8)}` : 'Untitled Document';
  }

  // Try to construct subtitle from available fields
  const subtitleParts: string[] = [];

  if (anyResult.manufacturer) subtitleParts.push(`Manufacturer: ${anyResult.manufacturer}`);
  if (anyResult.category) subtitleParts.push(`Category: ${anyResult.category}`);
  if (anyResult.part_number) subtitleParts.push(`P/N: ${anyResult.part_number}`);
  if (anyResult.location) subtitleParts.push(`Location: ${anyResult.location}`);
  if (anyResult.equipment_type) subtitleParts.push(`Type: ${anyResult.equipment_type}`);
  if (anyResult.page_number) subtitleParts.push(`Page: ${anyResult.page_number}`);
  if (anyResult.section_title && anyResult.section_title !== title) subtitleParts.push(`Section: ${anyResult.section_title}`);

  const subtitle =
    result.subtitle ||
    result.snippet ||
    result.preview ||
    subtitleParts.join(' | ') ||
    (anyResult.description || '').substring(0, 100) ||
    (anyResult.content || '').substring(0, 100) ||
    '';

  return {
    // CRITICAL: Backend returns primary_id (chunk ID) - prioritize it over id field
    // id field might be document_id from raw_data, which is WRONG for DocumentSituationView
    id: result.primary_id || result.id || crypto.randomUUID(),
    type: result.type || result.source_table || 'document',
    title: title.trim(),
    subtitle: subtitle.trim(),
    metadata: result.metadata || result.raw_data || (result as Record<string, any>),
  };
}

// ============================================================================
// COMPONENT
// ============================================================================

export default function SpotlightSearch({
  onClose,
  isModal = false,
  className,
}: SpotlightSearchProps) {
  // Get user context from auth (yacht_id comes from bootstrap, not DB query)
  // CRITICAL: Must get user FIRST before useCelesteSearch to pass yachtId
  const { user } = useAuth();

  // Pass yacht_id from AuthContext to hooks - this is the ONLY correct source
  const {
    query,
    results: apiResults,
    isLoading,
    isStreaming,
    error,
    handleQueryChange,
    search,
    clear,
    actionSuggestions,
    refetch,
  } = useCelesteSearch(user?.yachtId ?? null);

  // Pass yacht_id to situation state hook as well
  const {
    situation,
    createSituation,
    updateSituation,
    transitionTo,
    resetToIdle,
  } = useSituationState(user?.yachtId ?? null);

  // SurfaceContext for email overlay (returns null if not in SurfaceProvider)
  const surfaceContext = useSurfaceSafe();

  const [selectedIndex, setSelectedIndex] = useState(0);
  const [placeholderIndex, setPlaceholderIndex] = useState(-1); // -1 = not mounted yet
  const [isAnimating, setIsAnimating] = useState(false);
  const [isMounted, setIsMounted] = useState(false);

  // Fix hydration: only show placeholder after mount
  useEffect(() => {
    setIsMounted(true);
    setPlaceholderIndex(0);
  }, []);
  const [showSettings, setShowSettings] = useState(false);
  const [showLedger, setShowLedger] = useState(false);
  // Local state fallback when not in SurfaceProvider
  const [localShowEmailList, setLocalShowEmailList] = useState(false);
  const [localEmailScopeActive, setLocalEmailScopeActive] = useState(false);

  // Use context if available, otherwise local state
  const emailScopeActive = surfaceContext?.emailPanel.visible ?? localEmailScopeActive;
  const showEmailList = surfaceContext?.emailPanel.visible ?? localShowEmailList;

  // Helper to toggle email state - uses context when available
  const toggleEmailScope = useCallback((active: boolean) => {
    if (surfaceContext) {
      if (active) {
        surfaceContext.showEmail({ folder: 'inbox' });
      } else {
        surfaceContext.hideEmail();
      }
    } else {
      setLocalEmailScopeActive(active);
      setLocalShowEmailList(active);
    }
  }, [surfaceContext]);

  // Listen for global settings modal open events
  useEffect(() => {
    const handleOpenSettings = (e: CustomEvent) => {
      setShowSettings(true);
    };
    window.addEventListener('openSettingsModal', handleOpenSettings as EventListener);
    return () => {
      window.removeEventListener('openSettingsModal', handleOpenSettings as EventListener);
    };
  }, []);
  const [emailResults, setEmailResults] = useState<any[]>([]);
  const [emailLoading, setEmailLoading] = useState(false);
  const [expandedDomains, setExpandedDomains] = useState<Set<string>>(new Set());
  const [autoExpandTriggered, setAutoExpandTriggered] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const resultsRef = useRef<HTMLDivElement>(null);
  const scrollSentinelRef = useRef<HTMLDivElement>(null);

  // Toggle domain expansion
  const toggleDomainExpansion = useCallback((domain: string) => {
    setExpandedDomains(prev => {
      const next = new Set(prev);
      if (next.has(domain)) {
        next.delete(domain);
      } else {
        next.add(domain);
      }
      return next;
    });
  }, []);

  // Reset expanded domains and auto-expand trigger when query changes
  useEffect(() => {
    setExpandedDomains(new Set());
    setAutoExpandTriggered(false);
  }, [query]);

  // Group results by domain (Spotlight-style)
  const groupedResults = useMemo((): GroupedResults => {
    if (emailScopeActive || apiResults.length === 0) {
      return { topMatch: null, domains: [], totalResults: 0, hasMore: false };
    }
    return groupResultsByDomain(apiResults);
  }, [apiResults, emailScopeActive]);

  // Auto-expand all domains when user scrolls to bottom (IntersectionObserver)
  useEffect(() => {
    const sentinel = scrollSentinelRef.current;
    if (!sentinel || autoExpandTriggered || groupedResults.domains.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const entry = entries[0];
        if (entry?.isIntersecting && !autoExpandTriggered) {
          // Expand all domains that have more results
          const domainsToExpand = groupedResults.domains
            .filter(g => g.totalCount > 4)
            .map(g => g.domain);

          if (domainsToExpand.length > 0) {
            setExpandedDomains(new Set(domainsToExpand));
            setAutoExpandTriggered(true);
          }
        }
      },
      {
        root: resultsRef.current,
        rootMargin: '100px', // Trigger 100px before reaching the bottom
        threshold: 0.1,
      }
    );

    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [groupedResults.domains, autoExpandTriggered]);

  // Transform API results based on scope (legacy flat list for email)
  const results = useMemo(() => {
    if (emailScopeActive && emailResults.length > 0) {
      // Transform email search results
      return emailResults.map((r: any) => ({
        id: r.message_id || r.id,
        type: 'email_thread',
        title: r.subject || '(No subject)',
        subtitle: r.preview_text || r.from_display_name || '',
        metadata: {
          thread_id: r.thread_id,
          from_display_name: r.from_display_name,
          sent_at: r.sent_at,
          direction: r.direction,
          has_attachments: r.has_attachments,
          vector_score: r.vector_score,
          entity_score: r.entity_score,
          total_score: r.total_score,
          matched_entities: r.matched_entities,
        },
      }));
    }
    return apiResults.map(mapAPIResult);
  }, [apiResults, emailScopeActive, emailResults]);

  // Email search function (calls /api/email/search when in email scope)
  const searchEmail = useCallback(async (searchQuery: string) => {
    if (!searchQuery.trim() || searchQuery.length < 2) {
      setEmailResults([]);
      return;
    }

    setEmailLoading(true);
    try {
      // Get auth token for request
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) {
        console.error('[SpotlightSearch] No auth session for email search');
        setEmailResults([]);
        return;
      }

      const response = await fetch('/api/email/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({ query: searchQuery, limit: 20 }),
      });

      if (response.ok) {
        const data = await response.json();
        setEmailResults(data.results || []);
      } else {
        console.error('[SpotlightSearch] Email search failed:', response.status);
        setEmailResults([]);
      }
    } catch (error) {
      console.error('[SpotlightSearch] Email search error:', error);
      setEmailResults([]);
    } finally {
      setEmailLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => inputRef.current?.focus(), 50);
    return () => clearTimeout(timer);
  }, []);

  // Rolling placeholder animation - cycle every 3 seconds
  useEffect(() => {
    if (query) return; // Don't animate when user is typing

    const interval = setInterval(() => {
      setIsAnimating(true);

      // After animation starts, change the text
      setTimeout(() => {
        setPlaceholderIndex((prev) => (prev + 1) % PLACEHOLDER_SUGGESTIONS.length);
        setIsAnimating(false);
      }, 200); // Half of transition duration
    }, 3000);

    return () => clearInterval(interval);
  }, [query]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [results.length]);

  useEffect(() => {
    if (resultsRef.current && results.length > 0) {
      const el = resultsRef.current.querySelector(`[data-index="${selectedIndex}"]`);
      el?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }
  }, [selectedIndex, results.length]);

  /**
   * Map result type to entity type for situation creation
   */
  const mapResultTypeToEntityType = useCallback((type: string): EntityType => {
    if (type.includes('document') || type === 'search_document_chunks') return 'document';
    if (type.includes('equipment') || type === 'pms_equipment') return 'equipment';
    if (type.includes('part') || type === 'pms_parts') return 'part';
    if (type.includes('work_order')) return 'work_order';
    if (type.includes('fault')) return 'fault';
    if (type.includes('inventory') || type === 'v_inventory') return 'inventory';
    if (type.includes('email') || type === 'email_thread' || type === 'email_threads') return 'email_thread';
    return 'document'; // Default fallback
  }, []);

  /**
   * Map entity type to domain
   */
  const mapEntityTypeToDomain = useCallback((entityType: EntityType): SituationDomain => {
    if (entityType === 'document') return 'manuals';
    if (entityType === 'equipment' || entityType === 'work_order' || entityType === 'fault') return 'maintenance';
    if (entityType === 'part' || entityType === 'inventory') return 'inventory';
    if (entityType === 'email_thread') return 'email';
    return 'manuals'; // Default fallback
  }, []);

  /**
   * Handle result selection (single click) - Creates CANDIDATE situation
   */
  const handleResultSelect = useCallback((result: SpotlightResult, index: number) => {
    setSelectedIndex(index);

    // Create CANDIDATE situation
    const entityType = mapResultTypeToEntityType(result.type);
    const domain = mapEntityTypeToDomain(entityType);

    // Store full result in metadata for later access
    const situationMetadata = {
      ...result.metadata,
      title: result.title,
      subtitle: result.subtitle,
      type: result.type,
      storage_path: result.metadata?.storage_path || result.metadata?.path,
      name: result.title,
    };

    createSituation({
      entity_type: entityType,
      entity_id: result.id,
      domain,
      initial_state: 'CANDIDATE',
      metadata: situationMetadata,
    });
  }, [createSituation, mapResultTypeToEntityType, mapEntityTypeToDomain]);

  /**
   * Handle result open (double-click or Enter) - Navigate to detail page
   * For email_thread: Opens EmailOverlay with selected thread
   */
  const handleResultOpen = useCallback(async (result: SpotlightResult) => {
    console.log('[SpotlightSearch] 🖱️ Click registered:', result.type, result.id);

    const entityType = mapResultTypeToEntityType(result.type);
    const domain = mapEntityTypeToDomain(entityType);

    // Special handling for email threads: open EmailOverlay
    if (entityType === 'email_thread' && surfaceContext) {
      const threadId = (result.metadata?.thread_id || result.id) as string;
      surfaceContext.showEmail({ threadId, folder: 'inbox' });
      return; // Don't create situation for emails - overlay handles the UX
    }

    // Open entity in ContextPanel (single-surface architecture - no URL fragmentation)
    // Build metadata for ContextPanel display
    const contextMetadata = {
      ...result.metadata,
      title: result.title,
      subtitle: result.subtitle,
      type: result.type,
      storage_path: result.metadata?.storage_path || result.metadata?.path,
      name: result.title,
    };

    if (surfaceContext) {
      console.log('[SpotlightSearch] 📍 Opening in ContextPanel:', entityType, result.id);
      surfaceContext.showContext(entityType, result.id, contextMetadata);

      // Record ledger event for artefact opened
      recordLedgerEvent('artefact_opened', {
        artefact_type: entityType,
        artefact_id: result.id,
        display_name: result.title,
        domain: domain,
      });

      onClose?.(); // Close spotlight after opening context
    } else {
      // Fallback for when not in SurfaceProvider (shouldn't happen in /app)
      console.warn('[SpotlightSearch] ⚠️ No SurfaceContext - falling back to situation');

      // Create or transition to ACTIVE situation
      if (situation && situation.state === 'CANDIDATE') {
        await updateSituation({
          evidence: contextMetadata as any,
        });
        await transitionTo('ACTIVE', 'User opened entity from CANDIDATE state');
      } else {
        await createSituation({
          entity_type: entityType,
          entity_id: result.id,
          domain,
          initial_state: 'ACTIVE',
          metadata: contextMetadata,
        });
      }
    }
  }, [situation, createSituation, transitionTo, updateSituation, mapResultTypeToEntityType, mapEntityTypeToDomain, surfaceContext, onClose]);

  /**
   * Handle situation close (any viewer)
   */
  const handleSituationClose = useCallback(() => {
    resetToIdle();
    inputRef.current?.focus();
  }, [resetToIdle]);

  /**
   * Handle situation actions (add to handover, etc.)
   */
  const handleSituationAction = useCallback(async (action: string, payload: any) => {
    console.log('[SpotlightSearch] Situation action:', action, payload);

    try {
      // Use auth context instead of querying database
      // Backend handles tenant routing via JWT verification
      if (!user) {
        toast.error('Authentication required');
        return;
      }

      if (!user.yachtId) {
        toast.error('No yacht associated with user');
        return;
      }

      // Handle different actions
      switch (action) {
        case 'add_to_handover':
          await handleAddToHandover(user.id, user.yachtId, payload);
          break;

        default:
          console.warn(`[SpotlightSearch] Unknown action: ${action}`);
          toast.error(`Action "${action}" not yet implemented`);
      }
    } catch (error) {
      console.error('[SpotlightSearch] Action failed:', error);
      toast.error(error instanceof Error ? error.message : 'Action failed');
    }
  }, [user]);

  /**
   * Handle add_to_handover action
   */
  const handleAddToHandover = async (
    userId: string,
    yachtId: string,
    payload: any
  ) => {
    // Map entity type for documents
    const entityType = payload.type === 'document' || payload.document_id
      ? 'document_chunk'
      : payload.type || 'document_chunk';

    // Generate summary from available data
    const summaryText = payload.document_title || payload.title || payload.name || 'Document reference';

    // Map entity type to category
    const categoryMap: Record<string, string> = {
      'fault': 'ongoing_fault',
      'work_order': 'work_in_progress',
      'equipment': 'equipment_status',
      'document': 'important_info',
      'document_chunk': 'important_info',
      'part': 'general',
    };
    const category = categoryMap[entityType] || 'important_info';

    // Build API request payload
    const requestPayload = {
      entity_type: entityType,
      entity_id: payload.document_id || payload.entity_id || payload.id,
      summary_text: summaryText,
      category: category,
      priority: payload.priority || 'normal',
    };

    console.log('[SpotlightSearch] Executing add_to_handover:', {
      action: 'add_to_handover',
      context: { yacht_id: yachtId, user_id: userId },
      payload: requestPayload,
    });

    // Call backend API via actionClient
    const result = await executeAction(
      'add_to_handover',
      {
        yacht_id: yachtId,
        user_id: userId,
      },
      requestPayload
    );

    if (result.status === 'error') {
      throw new Error(result.message || 'Failed to add to handover');
    }

    // Show success message
    toast.success('Added to handover', {
      description: summaryText.substring(0, 80),
    });

    console.log('[SpotlightSearch] Handover entry created:', result);
  };

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex(i => Math.min(i + 1, results.length - 1));
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex(i => Math.max(i - 1, 0));
        break;
      case 'Enter':
        e.preventDefault();
        if (results[selectedIndex]) {
          handleResultOpen(results[selectedIndex]);
        }
        break;
      case 'Escape':
        e.preventDefault();
        if (query) {
          clear();
        } else {
          onClose?.();
        }
        break;
    }
  }, [results, selectedIndex, query, clear, onClose, handleResultOpen]);

  const handleClear = useCallback(() => {
    clear();
    setSelectedIndex(0);
    inputRef.current?.focus();
  }, [clear]);

  const hasResults = results.length > 0 || groupedResults.totalResults > 0;
  const hasQuery = query.trim().length > 0;
  const effectiveLoading = emailScopeActive ? emailLoading : isLoading;
  const showNoResults = hasQuery && !hasResults && !effectiveLoading && !isStreaming;

  return (
    <div
      className={cn(
        isModal && 'fixed inset-0 z-[9999] flex items-start justify-center pt-[18vh]',
        className
      )}
    >
      {/* Backdrop - material-based dim */}
      {isModal && (
        <div
          className="absolute inset-0 backdrop-blur-md transition-colors duration-150"
          style={{ backgroundColor: `rgba(var(--celeste-backdrop-color), var(--celeste-backdrop-opacity))` }}
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Spotlight Container - uses Tailwind token */}
      <div
        className={cn(
          'w-full mx-auto max-w-celeste-spotlight',
          isModal && 'relative z-10'
        )}
      >
        {/* Main Spotlight Panel - BLUE when email scope active */}
        <div
          className={cn(
            'spotlight-panel w-full font-body',
            'animate-spotlight-in',
            // Email scope: blue background and border
            emailScopeActive && 'bg-celeste-accent/20 border-2 border-celeste-accent ring-2 ring-celeste-accent/40'
          )}
          data-email-scope={emailScopeActive}
        >
          {/* Search Input - tokenized padding and height */}
          <div
            className={cn(
              'flex items-center gap-4 h-[var(--celeste-spotlight-height)]',
              (hasQuery || hasResults) && 'border-b border-celeste-border-subtle'
            )}
            style={{ paddingLeft: 'var(--celeste-spotlight-padding-x)', paddingRight: 'var(--celeste-spotlight-padding-x)' }}
          >
            {/* Email Scope Badge */}
            {emailScopeActive && (
              <div className="px-2 py-0.5 bg-celeste-accent text-celeste-text-title rounded text-celeste-xs font-semibold whitespace-nowrap">
                Email
              </div>
            )}
            <Search
              className={cn(
                'flex-shrink-0 w-5 h-5',
                emailScopeActive ? 'text-celeste-accent' : 'text-celeste-text-muted'
              )}
              strokeWidth={1.5}
            />

            <div className="flex-1 h-full relative">
              <input
                ref={inputRef}
                type="search"
                value={query}
                onChange={(e) => {
                  handleQueryChange(e.target.value);
                  if (e.target.value && showEmailList && !emailScopeActive) {
                    // Hide inline email list when user starts typing (unless in email scope)
                    toggleEmailScope(false);
                  }
                  // Route to email search when in email scope
                  if (emailScopeActive) {
                    searchEmail(e.target.value);
                  }
                }}
                onKeyDown={handleKeyDown}
                data-testid="search-input"
                className={cn(
                  'w-full h-full',
                  'bg-transparent border-none outline-none',
                  'text-celeste-xl text-celeste-text-title',
                  'font-normal tracking-[-0.01em]',
                  'caret-celeste-text-title',
                  'relative z-10'
                )}
                autoComplete="off"
                autoCorrect="off"
                autoCapitalize="off"
                spellCheck={false}
              />
              {/* Animated rolling placeholder - maritime grey */}
              {!query && isMounted && placeholderIndex >= 0 && (
                <div
                  className="absolute inset-0 flex items-center pointer-events-none overflow-hidden"
                >
                  <span
                    className={cn(
                      'text-celeste-xl text-celeste-text-disabled font-normal tracking-[-0.01em]',
                      'transition-all duration-celeste-deliberate ease-out',
                      isAnimating
                        ? 'opacity-0 -translate-y-3'
                        : 'opacity-100 translate-y-0'
                    )}
                  >
                    {PLACEHOLDER_SUGGESTIONS[placeholderIndex]}
                  </span>
                </div>
              )}
            </div>

            <div className="flex items-center gap-2">
              {query && (
                <button
                  onClick={handleClear}
                  className="flex items-center justify-center w-4 h-4 rounded-full bg-celeste-text-muted hover:bg-celeste-text-secondary transition-colors"
                  aria-label="Clear"
                >
                  <X className="w-2.5 h-2.5 text-celeste-black-base" strokeWidth={3} />
                </button>
              )}
            </div>
          </div>

          {/* Status Line - system transparency */}
          <StatusLine
            message={
              emailScopeActive && emailLoading
                ? 'Searching emails…'
                : isLoading
                  ? 'Searching…'
                  : isStreaming
                    ? 'Loading results…'
                    : ''
            }
            visible={effectiveLoading || isStreaming}
            className="px-4 py-2"
          />

          {/* Entity Line removed - clutter that Apple wouldn't include */}

          {/* Suggested Actions - backend-provided action buttons */}
          {hasQuery && actionSuggestions.length > 0 && (
            <SuggestedActions
              actions={actionSuggestions}
              yachtId={user?.yachtId ?? null}
              onActionComplete={refetch}
            />
          )}

          {/* Email List (beneath search bar per UX doctrine)
              Only render inline EmailInboxView when SurfaceContext is NOT available.
              When SurfaceContext is available, EmailOverlay handles the email UI. */}
          {showEmailList && !hasQuery && !surfaceContext && (
            <div
              className="max-h-celeste-search-results overflow-y-auto overflow-x-hidden spotlight-scrollbar bg-celeste-bg-primary rounded-b-2xl"
              data-testid="email-list-inline"
            >
              <EmailInboxView className="p-4" />
            </div>
          )}

          {/* Results - Spotlight-style grouped by domain */}
          {hasQuery && (
            <div
              ref={resultsRef}
              className="max-h-[60vh] overflow-y-auto overflow-x-hidden spotlight-scrollbar"
            >
              {/* Email scope uses flat list */}
              {emailScopeActive && hasResults && (
                <div className="py-1.5" data-testid="search-results-email">
                  {results.map((result, index) => (
                    <SpotlightResultRow
                      key={result.id}
                      result={result}
                      isSelected={index === selectedIndex}
                      index={index}
                      onClick={() => handleResultOpen(result)}
                      onDoubleClick={() => handleResultOpen(result)}
                    />
                  ))}
                </div>
              )}

              {/* Non-email: Spotlight-style grouped display */}
              {!emailScopeActive && (groupedResults.topMatch || groupedResults.domains.length > 0) && (
                <div className="py-1.5" data-testid="search-results-grouped">
                  {/* Top Match - only shown when confidence is high */}
                  {groupedResults.topMatch && (
                    <div className="sr-section">
                      <div className="sr-section-header-wrapper px-4">
                        <span className="sr-top-label text-celeste-accent">
                          Top Result
                        </span>
                      </div>
                      <SpotlightResultRow
                        key={groupedResults.topMatch.id}
                        result={{
                          id: groupedResults.topMatch.id,
                          type: groupedResults.topMatch.type,
                          title: groupedResults.topMatch.title,
                          subtitle: groupedResults.topMatch.subtitle,
                          metadata: groupedResults.topMatch.metadata,
                        }}
                        isSelected={selectedIndex === 0}
                        index={0}
                        onClick={() => handleResultOpen({
                          id: groupedResults.topMatch!.id,
                          type: groupedResults.topMatch!.type,
                          title: groupedResults.topMatch!.title,
                          subtitle: groupedResults.topMatch!.subtitle,
                          metadata: groupedResults.topMatch!.metadata,
                        })}
                        onDoubleClick={() => handleResultOpen({
                          id: groupedResults.topMatch!.id,
                          type: groupedResults.topMatch!.type,
                          title: groupedResults.topMatch!.title,
                          subtitle: groupedResults.topMatch!.subtitle,
                          metadata: groupedResults.topMatch!.metadata,
                        })}
                        isTopMatch
                      />
                    </div>
                  )}

                  {/* Domain Groups */}
                  {groupedResults.domains.map((group, groupIndex) => {
                    const DomainIcon = DomainIconMap[DOMAIN_ICONS[group.domain]] || MoreHorizontal;
                    const isExpanded = expandedDomains.has(group.domain);
                    const displayResults = isExpanded
                      ? apiResults
                          .filter(r => {
                            const type = r.type || r.source_table || '';
                            const groupType = group.results[0]?.type || '';
                            return type === groupType || (r as any).object_type === groupType;
                          })
                          .slice(0, 12)
                          .map(r => ({
                            id: r.primary_id || r.id || '',
                            type: r.type || r.source_table || '',
                            title: r.title || (r as any).name || '',
                            subtitle: r.subtitle || r.snippet || '',
                            metadata: r.metadata || r.raw_data || r,
                          }))
                      : group.results.map(r => ({
                          id: r.id,
                          type: r.type,
                          title: r.title,
                          subtitle: r.subtitle,
                          metadata: r.metadata,
                        }));
                    const hasMoreInDomain = group.totalCount > (isExpanded ? 12 : 4);
                    const baseIndex = (groupedResults.topMatch ? 1 : 0) +
                      groupedResults.domains.slice(0, groupIndex).reduce((sum, g) =>
                        sum + (expandedDomains.has(g.domain) ? Math.min(12, g.totalCount) : Math.min(4, g.results.length)), 0);

                    return (
                      <div key={group.domain} className="sr-section">
                        {/* Domain Header - no icons, no counts (discipline) */}
                        <div className="sr-section-header-wrapper">
                          <span className="sr-section-header">
                            {group.domain}
                          </span>
                        </div>

                        {/* Domain Results */}
                        {displayResults.map((result, idx) => {
                          const spotlightResult = {
                            id: result.id,
                            type: result.type,
                            title: result.title,
                            subtitle: result.subtitle,
                            metadata: result.metadata as Record<string, unknown> | undefined,
                          };
                          return (
                            <SpotlightResultRow
                              key={result.id}
                              result={spotlightResult}
                              isSelected={selectedIndex === baseIndex + idx}
                              index={baseIndex + idx}
                              onClick={() => handleResultOpen(spotlightResult)}
                              onDoubleClick={() => handleResultOpen(spotlightResult)}
                            />
                          );
                        })}

                        {/* Show More button */}
                        {(hasMoreInDomain || (group.totalCount > 4 && !isExpanded)) && (
                          <button
                            onClick={() => toggleDomainExpansion(group.domain)}
                            className="w-full px-4 py-2 text-left text-celeste-sm text-celeste-accent hover:bg-celeste-bg-tertiary transition-colors flex items-center gap-2"
                          >
                            <ChevronDown
                              className={cn(
                                "w-3.5 h-3.5 transition-transform",
                                isExpanded && "rotate-180"
                              )}
                            />
                            {isExpanded
                              ? `Show less`
                              : `Show ${Math.min(group.totalCount - 4, 8)} more in ${group.domain}`
                            }
                          </button>
                        )}
                      </div>
                    );
                  })}

                  {/* Scroll sentinel for auto-loading more results */}
                  <div
                    ref={scrollSentinelRef}
                    className="h-px w-full"
                    aria-hidden="true"
                  />
                </div>
              )}

              {showNoResults && (
                <div className="py-10 text-center" data-testid="no-results">
                  <p className="text-celeste-lg text-celeste-text-secondary">No Results</p>
                </div>
              )}

              {error && (
                <div className="py-10 text-center" data-testid="search-error">
                  <p className="text-celeste-lg text-celeste-text-secondary">{error}</p>
                  <button
                    onClick={() => search(query)}
                    className="mt-2 text-celeste-md text-celeste-accent hover:text-celeste-accent-hover"
                  >
                    Try again
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Action Buttons - below panel, centered */}
        <div className="flex justify-center items-center gap-2 mt-4">
          {/* Email Scope Toggle - Prominent button to switch search scope */}
          <button
            onClick={() => {
              const newEmailScope = !emailScopeActive;
              toggleEmailScope(newEmailScope);
              if (!newEmailScope) {
                setEmailResults([]);
              }
              clear(); // Clear search when toggling scope
              inputRef.current?.focus();
            }}
            className={cn(
              'flex items-center gap-2 px-4 py-2.5 rounded-full transition-colors font-medium',
              emailScopeActive
                ? 'bg-celeste-accent text-celeste-text-title hover:bg-celeste-accent-hover'
                : 'text-celeste-text-muted hover:text-celeste-text-secondary hover:bg-celeste-surface'
            )}
            aria-label={emailScopeActive ? 'Exit Email Scope' : 'Search Email'}
            data-testid="email-scope-toggle"
          >
            <Mail className="w-5 h-5" strokeWidth={1.5} />
            <span className="text-celeste-base">{emailScopeActive ? 'Exit Email' : 'Email'}</span>
          </button>

          {/* Ledger Dropdown - Other record access */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                className="p-2.5 rounded-full text-celeste-text-muted hover:text-celeste-text-secondary hover:bg-celeste-surface transition-colors"
                aria-label="Ledger"
              >
                <BookOpen className="w-5 h-5" strokeWidth={1.5} />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              align="center"
              className="min-w-[var(--celeste-width-filter-medium)] bg-celeste-bg-tertiary border-celeste-divider text-celeste-text-primary"
            >
              <DropdownMenuItem
                onClick={() => setShowLedger(true)}
                className="flex items-center gap-2 cursor-pointer focus:bg-celeste-divider focus:text-celeste-text-title"
              >
                <BookOpen className="w-4 h-4" />
                <span>Ledger</span>
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => {
                  // Show email overlay (uses SurfaceContext when available)
                  const newShowEmail = !showEmailList;
                  toggleEmailScope(newShowEmail);
                  if (!newShowEmail) {
                    setEmailResults([]);
                  }
                  clear(); // Clear search to show email list
                }}
                className="flex items-center gap-2 cursor-pointer focus:bg-celeste-divider focus:text-celeste-text-title"
              >
                <Mail className="w-4 h-4" />
                <span>{showEmailList ? 'Hide Email' : 'Email'}</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Settings Button */}
          <button
            onClick={() => setShowSettings(true)}
            className="p-2.5 rounded-full text-celeste-text-muted hover:text-celeste-text-secondary hover:bg-celeste-surface transition-colors"
            aria-label="Settings"
          >
            <Settings className="w-5 h-5" strokeWidth={1.5} />
          </button>
        </div>
      </div>

      {/* Settings Modal */}
      <SettingsModal
        isOpen={showSettings}
        onClose={() => setShowSettings(false)}
      />

      {/* Ledger Panel */}
      <LedgerPanel
        isOpen={showLedger}
        onClose={() => setShowLedger(false)}
      />

      {/* Situation Router - Renders appropriate viewer based on situation type */}
      <SituationRouter
        situation={situation}
        onClose={handleSituationClose}
        onAction={handleSituationAction}
      />
    </div>
  );
}
