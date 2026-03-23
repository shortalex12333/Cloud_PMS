'use client';

/**
 * CelesteOS Spotlight Search
 * ChatGPT-style search bar - pill shape, shadow only, no border
 *
 * Design Spec:
 * - Pill shape (999px border-radius)
 * - 56px height, max 760px width
 * - Leading "+" button opens Log Receiving modal
 * - NO mic icon, NO search icon (minimal per ChatGPT)
 * - NO category buttons (Faults, Work Orders, etc.)
 * - Shadow only, no border
 * - Utility icon row (Email, Menu, Settings)
 * - ALL values tokenized via CSS custom properties
 */

import React, { useEffect, useRef, useCallback, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { X, Settings, BookOpen, Mail, Menu as MenuIcon, ChevronDown, AlertTriangle, ClipboardList, Package, FileText, Award, ArrowRightLeft, ShoppingCart, Receipt, Users, Clock, CheckSquare, MoreHorizontal, Plus, Camera, Paperclip, type LucideIcon } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { cn } from '@/lib/utils';
import { useCelesteSearch } from '@/hooks/useCelesteSearch';
import { useDomain } from '@/lib/domain/hooks';
import type { SearchResult as APISearchResult } from '@/types/search';
import SpotlightResultRow from './SpotlightResultRow';
import SmartPointers from './SmartPointers';
import LensPillStrip from './LensPillStrip';
import { useNeedsAttention } from '@/hooks/useNeedsAttention';
import QueryInterpretation from './QueryInterpretation';
import SettingsModal from '@/components/SettingsModal';
import { EntityLine, StatusLine } from '@/components/celeste';
import { EmailInboxView } from '@/components/email/EmailInboxView';

import SuggestedActions from '@/components/SuggestedActions';
import FilterChips from './FilterChips';
import { LedgerPanel } from '@/components/ledger';
import { HandoverDraftPanel } from '@/components/handover';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { ReceivingDocumentUpload } from '@/components/receiving/ReceivingDocumentUpload';
import { toast } from 'sonner';

import { supabase } from '@/lib/supabaseClient';
import { useAuth } from '@/hooks/useAuth';
import {
  groupResultsByDomain,
  type GroupedResults,
  type SpotlightResult as GroupedSpotlightResult,
  type DomainGroup,
  DOMAIN_ICONS,
} from '@/lib/spotlightGrouping';
import { getEntityRoute } from '@/lib/featureFlags';

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
  snippet?: string;
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
    // CRITICAL: useCelesteSearch already mapped object_id → id correctly (line 596)
    // DO NOT re-map here - just use the id field that was already set
    // The hook prioritizes: object_id || primary_id || id
    id: result.id || crypto.randomUUID(),
    type: result.type || result.source_table || 'document',
    title: title.trim(),
    subtitle: subtitle.trim(),
    snippet: result.snippet,
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

  // Get domain context for domain-scoped search (null when not in fragmented route)
  const { objectType, label: domainLabel } = useDomain();

  // Needs Attention data — role-aware, time-aware scoring
  const { pointers: attentionPointers, counts: attentionCounts, loading: attentionLoading, role: attentionRole } = useNeedsAttention();

  // Pass yacht_id from AuthContext to hooks - this is the ONLY correct source
  // Pass objectType for domain-scoped search when in fragmented routes
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
  } = useCelesteSearch(
    user?.yachtId ?? null,
    objectType ? [objectType] : null
  );

  // Router for fragmented routes navigation
  const router = useRouter();

  const [selectedIndex, setSelectedIndex] = useState(0);
  const [placeholderIndex, setPlaceholderIndex] = useState(-1); // -1 = not mounted yet
  const [isAnimating, setIsAnimating] = useState(false);
  const [isMounted, setIsMounted] = useState(false);
  // GHOST TYPIST KILL SWITCH: Once user interacts, animations are permanently disabled
  const [userHasInteracted, setUserHasInteracted] = useState(false);

  // Fix hydration: only show placeholder after mount
  useEffect(() => {
    setIsMounted(true);
    setPlaceholderIndex(0);
  }, []);

  // Kill switch handler - permanently disables any demo/animation behavior
  const handleUserInteraction = useCallback(() => {
    if (!userHasInteracted) {
      setUserHasInteracted(true);
      // Lock placeholder to first suggestion (static)
      setPlaceholderIndex(0);
      setIsAnimating(false);
    }
  }, [userHasInteracted]);
  const [showSettings, setShowSettings] = useState(false);
  const [showLedger, setShowLedger] = useState(false);
  const [showHandoverDraft, setShowHandoverDraft] = useState(false);
  const [showReceivingUpload, setShowReceivingUpload] = useState(false);
  const [showEmailList, setShowEmailList] = useState(false);
  const [emailScopeActive, setEmailScopeActive] = useState(false);

  const toggleEmailScope = useCallback((active: boolean) => {
    setEmailScopeActive(active);
    setShowEmailList(active);
  }, []);

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

  // Rolling placeholder animation - DISABLED for E2E stability
  // Was cycling every 3 seconds, causing test flakiness
  // useEffect(() => {
  //   if (query) return;
  //   const interval = setInterval(() => {
  //     setIsAnimating(true);
  //     setTimeout(() => {
  //       setPlaceholderIndex((prev) => (prev + 1) % PLACEHOLDER_SUGGESTIONS.length);
  //       setIsAnimating(false);
  //     }, 200);
  //   }, 3000);
  //   return () => clearInterval(interval);
  // }, [query]);

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
   * Map result type to entity type for routing
   */
  const mapResultTypeToEntityType = useCallback((type: string): string => {
    if (type.includes('certificate')) return 'certificate';
    if (type.includes('warranty')) return 'warranty';
    if (type.includes('shopping_item') || type.includes('shopping_list')) return 'shopping_list';
    if (type.includes('receiving')) return 'receiving';
    if (type.includes('purchase_order')) return 'purchase_order';
    if (type.includes('hours_of_rest')) return 'hours_of_rest';
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
   * Map entity type to domain label for ledger events
   */
  const mapEntityTypeToDomain = useCallback((entityType: string): string => {
    if (entityType === 'document') return 'manuals';
    if (entityType === 'equipment' || entityType === 'work_order' || entityType === 'fault') return 'maintenance';
    if (entityType === 'part' || entityType === 'inventory' || entityType === 'shopping_list' || entityType === 'receiving' || entityType === 'purchase_order') return 'inventory';
    if (entityType === 'email_thread') return 'email';
    if (entityType === 'certificate' || entityType === 'warranty') return 'maintenance';
    if (entityType === 'hours_of_rest') return 'maintenance';
    return 'manuals';
  }, []);

  /**
   * Handle result open (click or Enter) - Navigate to entity route
   */
  const handleResultOpen = useCallback(async (result: SpotlightResult) => {
    console.log('[SpotlightSearch] 🖱️ Click registered:', result.type, result.id);

    const entityType = mapResultTypeToEntityType(result.type);
    const domain = mapEntityTypeToDomain(entityType);
    const entityId = result.id;

    if (!entityId) {
      console.error('[SpotlightSearch] ❌ Missing entity ID for result:', {
        resultId: result.id,
        title: result.title,
        type: result.type,
        fullResult: result
      });
      return;
    }

    // Route to entity page
    const routeTypeMap: Record<string, 'work_order' | 'fault' | 'equipment' | 'part' | 'email' | 'shopping_list' | 'receiving' | 'document' | 'certificate' | 'warranty' | 'purchase_order' | 'hours_of_rest'> = {
      work_order: 'work_order',
      fault: 'fault',
      equipment: 'equipment',
      part: 'part',
      inventory: 'part',
      email_thread: 'email',
      shopping_list: 'shopping_list',
      receiving: 'receiving',
      document: 'document',
      certificate: 'certificate',
      warranty: 'warranty',
      purchase_order: 'purchase_order',
      hours_of_rest: 'hours_of_rest',
    };

    const routeType = routeTypeMap[entityType];
    if (!routeType) {
      console.warn('[SpotlightSearch] Unknown entity type:', entityType);
      return;
    }

    const route = getEntityRoute(routeType, entityId);

    recordLedgerEvent('artefact_opened', {
      artefact_type: entityType,
      artefact_id: entityId,
      display_name: result.title,
      domain: domain,
    });

    router.push(route);
    onClose?.();
  }, [mapResultTypeToEntityType, mapEntityTypeToDomain, onClose, router]);

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

  /**
   * Handle receiving upload complete - navigate to new receiving
   */
  const handleReceivingUploadComplete = useCallback((receivingId: string, documentId: string, extractedData: any) => {
    setShowReceivingUpload(false);

    // Navigate to the new receiving entity route
    recordLedgerEvent('receiving_created', {
      receiving_id: receivingId,
      document_id: documentId,
      has_extracted_data: !!extractedData,
    });

    toast.success('Receiving logged', {
      description: extractedData?.supplier_name || 'Document uploaded successfully',
    });

    router.push(getEntityRoute('receiving', receivingId));
  }, [router]);

  const hasResults = results.length > 0 || groupedResults.totalResults > 0;
  const hasQuery = query.trim().length > 0;
  const effectiveLoading = emailScopeActive ? emailLoading : isLoading;
  const showNoResults = hasQuery && !hasResults && !effectiveLoading && !isStreaming;

  return (
    <div
      className={cn(
        isModal && 'fixed inset-0 z-search flex items-start justify-center spotlight-modal-offset',
        className
      )}
    >
      {/* Backdrop - material-based dim */}
      {isModal && (
        <div
          className="absolute inset-0 backdrop-blur-sm transition-colors duration-fast"
          style={{ background: 'rgba(0,0,0,0.60)' }}
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Spotlight Container - uses CSS custom property for max-width */}
      <div
        className={cn(
          'w-full mx-auto',
          isModal && 'relative z-10'
        )}
        style={{ maxWidth: 'var(--celeste-spotlight-width)' }}
      >
        {/* Main Spotlight Panel — inline glass styles per elegant.html */}
        <div
          style={{
            width: '100%',
            background: 'var(--search-glass-bg)',
            backdropFilter: 'blur(var(--search-glass-blur))', WebkitBackdropFilter: 'blur(var(--search-glass-blur))',
            borderTop: '1px solid var(--search-glass-border-t)',
            borderRight: '1px solid var(--search-glass-border-s)',
            borderBottom: '1px solid var(--search-glass-border-b)',
            borderLeft: '1px solid var(--search-glass-border-s)',
            borderRadius: 4,
            boxShadow: 'var(--search-glass-shadow)',
            overflow: 'hidden',
          }}
          data-email-scope={emailScopeActive}
        >
          {/* Search Input Row — 50px height, 14px padding per prototype */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '0 14px', height: 50 }}>
            {/* Search Icon (magnifying glass SVG) */}
            <div style={{ color: 'var(--txt-ghost)', flexShrink: 0 }}>
              <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth={1.8} style={{ width: 16, height: 16 }}>
                <circle cx="6.5" cy="6.5" r="4.5" /><path d="M10 10l3 3" />
              </svg>
            </div>

            {/* Email Scope Badge */}
            {emailScopeActive && (
              <div style={{ padding: '1px 8px', background: 'var(--mark)', color: 'var(--txt)', borderRadius: 3, fontSize: 10, fontWeight: 600, whiteSpace: 'nowrap' }}>
                Email
              </div>
            )}

            {/* Domain Scope Indicator */}
            {objectType && !emailScopeActive && (
              <span style={{ fontSize: 11, color: 'var(--txt3)', marginRight: 8, whiteSpace: 'nowrap' }}>
                in {domainLabel}
              </span>
            )}

            {/* Search Input */}
            <div style={{ flex: 1, height: '100%', position: 'relative' }}>
              <input
                ref={inputRef}
                type="search"
                value={query}
                onFocus={handleUserInteraction}
                onChange={(e) => {
                  handleUserInteraction();
                  handleQueryChange(e.target.value);
                  if (e.target.value && showEmailList && !emailScopeActive) {
                    toggleEmailScope(false);
                  }
                  if (emailScopeActive) {
                    searchEmail(e.target.value);
                  }
                }}
                onKeyDown={handleKeyDown}
                data-testid="search-input"
                style={{
                  width: '100%', height: '100%',
                  background: 'none', border: 'none', outline: 'none',
                  fontFamily: 'var(--font-sans)', fontSize: 15,
                  color: 'var(--txt)', caretColor: 'var(--teal)',
                  position: 'relative', zIndex: 10,
                }}
                placeholder={isMounted && !query && placeholderIndex >= 0 ? PLACEHOLDER_SUGGESTIONS[placeholderIndex] : 'Find anything, or tell me what to do…'}
                autoComplete="off"
                autoCorrect="off"
                autoCapitalize="off"
                spellCheck={false}
              />
            </div>

            {/* Trailing: ⌘K hint or Clear button */}
            {query ? (
              <button
                onClick={handleClear}
                aria-label="Clear"
                style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
              >
                <X style={{ width: 16, height: 16, color: 'var(--txt-ghost)' }} strokeWidth={2} />
              </button>
            ) : (
              <div style={{ fontSize: 10, color: 'var(--txt-ghost)', flexShrink: 0, fontFamily: 'var(--font-mono)' }}>
                ⌘K
              </div>
            )}
          </div>

          {/* Teal Gradient Divider */}
          <div style={{
            height: 1,
            background: 'linear-gradient(90deg, transparent, var(--teal) 20%, var(--teal) 80%, transparent)',
            opacity: 0.50,
          }} />

          {/* Loading sweep — visual indicator */}
          {(effectiveLoading || isStreaming) && (
            <div className="spotlight-loader" aria-hidden="true" />
          )}
          {/* Status Line — screen reader only */}
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
            className="sr-only"
          />

          {/* Suggested Actions - backend-provided action buttons */}
          {hasQuery && actionSuggestions.length > 0 && (
            <SuggestedActions
              actions={actionSuggestions}
              yachtId={user?.yachtId ?? null}
              query={query}
              onActionComplete={refetch}
            />
          )}

          {/* Quick Filter Chips - deterministic filter suggestions */}
          {hasQuery && !emailScopeActive && (
            <FilterChips
              query={query}
              onFilterClick={(filterId, route) => {
                recordLedgerEvent('quick_filter_clicked', {
                  filter_id: filterId,
                  route: route,
                  query: query,
                });
              }}
            />
          )}

          {/* Email List (beneath search bar per UX doctrine) */}
          {showEmailList && !hasQuery && (
            <div
              style={{ maxHeight: '60vh', overflowY: 'auto', overflowX: 'hidden', background: 'var(--surface-primary)' }}
              data-testid="email-list-inline"
            >
              <EmailInboxView className="p-4" />
            </div>
          )}

          {/* Results - Spotlight-style grouped by domain */}
          {hasQuery && (
            <div
              ref={resultsRef}
              className="spotlight-results"
            >
              {/* Email scope uses flat list */}
              {emailScopeActive && hasResults && (
                <div style={{ padding: '6px 0' }} data-testid="search-results-email">
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
                <div style={{ padding: '6px 0' }} data-testid="search-results-grouped">
                  {/* Top Match */}
                  {groupedResults.topMatch && (
                    <div>
                      <div style={{ padding: '8px 12px 4px' }}>
                        <span style={{ fontSize: 9, fontWeight: 600, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--txt)' }}>
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
                          snippet: groupedResults.topMatch.snippet,
                          metadata: groupedResults.topMatch.metadata,
                        }}
                        isSelected={selectedIndex === 0}
                        index={0}
                        onClick={() => handleResultOpen({
                          id: groupedResults.topMatch!.id,
                          type: groupedResults.topMatch!.type,
                          title: groupedResults.topMatch!.title,
                          subtitle: groupedResults.topMatch!.subtitle,
                          snippet: groupedResults.topMatch!.snippet,
                          metadata: groupedResults.topMatch!.metadata,
                        })}
                        onDoubleClick={() => handleResultOpen({
                          id: groupedResults.topMatch!.id,
                          type: groupedResults.topMatch!.type,
                          title: groupedResults.topMatch!.title,
                          subtitle: groupedResults.topMatch!.subtitle,
                          snippet: groupedResults.topMatch!.snippet,
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
                            id: r.id || '',
                            type: r.type || r.source_table || '',
                            title: r.title || (r as any).name || '',
                            subtitle: r.subtitle || '',
                            snippet: r.snippet,
                            metadata: r.metadata || r.raw_data || r,
                          }))
                      : group.results.map(r => ({
                          id: r.id,
                          type: r.type,
                          title: r.title,
                          subtitle: r.subtitle,
                          snippet: r.snippet,
                          metadata: r.metadata,
                        }));
                    const hasMoreInDomain = group.totalCount > (isExpanded ? 12 : 4);
                    const baseIndex = (groupedResults.topMatch ? 1 : 0) +
                      groupedResults.domains.slice(0, groupIndex).reduce((sum, g) =>
                        sum + (expandedDomains.has(g.domain) ? Math.min(12, g.totalCount) : Math.min(4, g.results.length)), 0);

                    return (
                      <div key={group.domain}>
                        {/* Domain Header */}
                        <div style={{ padding: '8px 12px 4px' }}>
                          <span style={{ fontSize: 9, fontWeight: 600, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--txt)' }}>
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
                            snippet: result.snippet,
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
                            style={{
                              width: '100%', padding: '8px 12px', textAlign: 'left',
                              fontSize: 11, color: 'var(--mark)', background: 'transparent',
                              border: 'none', cursor: 'pointer',
                              display: 'flex', alignItems: 'center', gap: 6,
                              transition: 'background 100ms',
                            }}
                            onMouseEnter={e => (e.currentTarget.style.background = 'var(--surface-hover)')}
                            onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                          >
                            <ChevronDown
                              style={{
                                width: 14, height: 14,
                                transition: 'transform 200ms',
                                transform: isExpanded ? 'rotate(180deg)' : 'none',
                              }}
                            />
                            {isExpanded
                              ? 'Show less'
                              : `Show ${Math.min(group.totalCount - 4, 8)} more in ${group.domain}`
                            }
                          </button>
                        )}
                      </div>
                    );
                  })}

                  {/* Scroll sentinel */}
                  <div ref={scrollSentinelRef} style={{ height: 1, width: '100%' }} aria-hidden="true" />
                </div>
              )}

              {showNoResults && (
                <div style={{ padding: '40px 0', textAlign: 'center' }} data-testid="no-results">
                  <p style={{ fontSize: 15, color: 'var(--txt2)' }}>No Results</p>
                </div>
              )}

              {error && (
                <div style={{ padding: '40px 0', textAlign: 'center' }} data-testid="search-error">
                  <p style={{ fontSize: 15, color: 'var(--txt2)' }}>{error}</p>
                  <button
                    onClick={() => search(query)}
                    style={{ marginTop: 8, fontSize: 13, color: 'var(--mark)', background: 'none', border: 'none', cursor: 'pointer' }}
                  >
                    Try again
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Footer keyboard hint strip — inline per prototype .search-footer */}
          <div
            style={{
              display: 'flex', alignItems: 'center', gap: 4,
              height: 34, padding: '0 14px',
              borderTop: '1px solid var(--border-faint)',
              background: 'var(--search-footer-bg)',
            }}
            aria-label="Keyboard shortcuts"
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 10, color: 'var(--txt-ghost)' }}>
              <kbd style={{ background: 'var(--kbd-bg)', border: '1px solid var(--kbd-border)', borderRadius: 3, padding: '1px 4px', fontSize: 10, color: 'var(--kbd-color)', fontFamily: 'var(--font-mono)', minWidth: 18, textAlign: 'center' }}>↑</kbd>
              <kbd style={{ background: 'var(--kbd-bg)', border: '1px solid var(--kbd-border)', borderRadius: 3, padding: '1px 4px', fontSize: 10, color: 'var(--kbd-color)', fontFamily: 'var(--font-mono)', minWidth: 18, textAlign: 'center' }}>↓</kbd>
              {' '}Navigate
            </div>
            <div style={{ width: 1, height: 10, background: 'var(--border-sub)', margin: '0 8px' }} aria-hidden="true" />
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 10, color: 'var(--txt-ghost)' }}>
              <kbd style={{ background: 'var(--kbd-bg)', border: '1px solid var(--kbd-border)', borderRadius: 3, padding: '1px 4px', fontSize: 10, color: 'var(--kbd-color)', fontFamily: 'var(--font-mono)', minWidth: 18, textAlign: 'center' }}>↵</kbd>
              {' '}Open
            </div>
            <div style={{ width: 1, height: 10, background: 'var(--border-sub)', margin: '0 8px' }} aria-hidden="true" />
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 10, color: 'var(--txt-ghost)' }}>
              <kbd style={{ background: 'var(--kbd-bg)', border: '1px solid var(--kbd-border)', borderRadius: 3, padding: '1px 4px', fontSize: 10, color: 'var(--kbd-color)', fontFamily: 'var(--font-mono)', minWidth: 18, textAlign: 'center' }}>Esc</kbd>
              {' '}Clear
            </div>
          </div>

          {/* ── Icon Strip (Email / Menu / Settings) ── */}
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
            padding: '8px 14px',
            borderTop: '1px solid var(--search-icon-strip-border)',
            background: 'var(--search-icon-strip-bg)',
          }}>
            {/* Email toggle */}
            <button
              onClick={() => toggleEmailScope(!emailScopeActive)}
              aria-label="Toggle email scope"
              style={{
                width: 32, height: 32, borderRadius: 4,
                background: emailScopeActive ? 'var(--teal-bg)' : 'transparent',
                border: 'none', cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                color: emailScopeActive ? 'var(--mark)' : 'var(--txt-ghost)',
                transition: 'background 100ms, color 100ms',
              }}
            >
              <Mail style={{ width: 16, height: 16 }} strokeWidth={1.6} />
            </button>

            {/* Menu dropdown (Ledger / Handover / Add Files) */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  aria-label="Menu"
                  style={{
                    width: 32, height: 32, borderRadius: 4,
                    background: 'transparent',
                    border: 'none', cursor: 'pointer',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    color: 'var(--txt-ghost)',
                    transition: 'background 100ms, color 100ms',
                  }}
                >
                  <MenuIcon style={{ width: 16, height: 16 }} strokeWidth={1.6} />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="center" sideOffset={4}>
                <DropdownMenuItem onClick={() => setShowLedger(true)}>
                  <BookOpen style={{ width: 14, height: 14, marginRight: 8 }} />
                  Ledger
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setShowHandoverDraft(true)}>
                  <FileText style={{ width: 14, height: 14, marginRight: 8 }} />
                  Handover Draft
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setShowReceivingUpload(true)}>
                  <Plus style={{ width: 14, height: 14, marginRight: 8 }} />
                  Log Receiving
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>

            {/* Settings */}
            <button
              onClick={() => setShowSettings(true)}
              aria-label="Settings"
              style={{
                width: 32, height: 32, borderRadius: 4,
                background: 'transparent',
                border: 'none', cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                color: 'var(--txt-ghost)',
                transition: 'background 100ms, color 100ms',
              }}
            >
              <Settings style={{ width: 16, height: 16 }} strokeWidth={1.6} />
            </button>
          </div>
        </div>

        {/* ── Idle State: SmartPointers + LensPillStrip ── */}
        {!hasQuery && (
          <>
            <SmartPointers pointers={attentionPointers} counts={attentionCounts} loading={attentionLoading} role={attentionRole} />
            <LensPillStrip counts={attentionCounts} role={attentionRole} />
          </>
        )}

        {/* ── Search State: QueryInterpretation ── */}
        {hasQuery && (
          <QueryInterpretation query={query} />
        )}
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

      {/* Handover Draft Panel */}
      <HandoverDraftPanel
        isOpen={showHandoverDraft}
        onClose={() => setShowHandoverDraft(false)}
      />

      {/* Receiving Upload Modal - Global entry point for logging receivings */}
      <Dialog open={showReceivingUpload} onOpenChange={setShowReceivingUpload}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto bg-surface-primary border-surface-border">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-txt-primary">
              <Camera className="h-5 w-5 text-brand-interactive" />
              Log Receiving
            </DialogTitle>
          </DialogHeader>
          <p className="typo-meta text-txt-secondary mb-4">
            Capture or upload an invoice, packing slip, or photo of received goods.
            We'll extract the details automatically.
          </p>
          <ReceivingDocumentUpload
            onComplete={handleReceivingUploadComplete}
          />
        </DialogContent>
      </Dialog>

    </div>
  );
}
