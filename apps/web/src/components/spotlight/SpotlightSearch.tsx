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
import { X, Settings, BookOpen, Mail, ChevronDown, AlertTriangle, ClipboardList, Package, FileText, Award, ArrowRightLeft, ShoppingCart, Receipt, Users, Clock, CheckSquare, MoreHorizontal, Plus, Camera, Paperclip, Menu, type LucideIcon } from 'lucide-react';
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
import { HandoverDraftPanel } from '@/components/handover';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { ReceivingDocumentUpload } from '@/components/receiving/ReceivingDocumentUpload';
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
import { isFragmentedRoutesEnabled, getEntityRoute } from '@/lib/featureFlags';

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
   *
   * FRAGMENTED ROUTES BEHAVIOR (flag ON):
   * - Supported types (work_order, fault, equipment, part, email_thread) → router.push
   * - Unsupported types (document) → legacy ContextPanel or toast
   *
   * LEGACY BEHAVIOR (flag OFF):
   * - Opens EmailOverlay for email_thread
   * - Opens ContextPanel for all other types
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

    // FRAGMENTED ROUTES: Flag-gated navigation
    if (isFragmentedRoutesEnabled()) {
      // Map EntityType to getEntityRoute type
      const routeTypeMap: Record<string, 'work_order' | 'fault' | 'equipment' | 'part' | 'email' | 'shopping_list' | 'receiving' | 'document' | 'certificate' | 'warranty' | 'purchase_order' | 'hours_of_rest'> = {
        work_order: 'work_order',
        fault: 'fault',
        equipment: 'equipment',
        part: 'part',
        inventory: 'part', // inventory uses part type which maps to /inventory
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

      if (routeType) {
        // Supported type → route to fragmented page
        const route = getEntityRoute(routeType, entityId);
        console.log('[SpotlightSearch] 🚀 Routing to fragmented page:', route);

        // Record ledger event before navigation
        recordLedgerEvent('artefact_opened', {
          artefact_type: entityType,
          artefact_id: entityId,
          display_name: result.title,
          domain: domain,
          route_mode: 'fragmented',
        });

        router.push(route);
        onClose?.();
        return;
      } else {
        // Unsupported type (e.g., document) → show toast and fallback to legacy
        console.log('[SpotlightSearch] ⚠️ Unsupported type for fragmented routes:', entityType);
        toast.info('Opening in context panel', {
          description: `${entityType} routes not yet available`,
        });
        // Fall through to legacy behavior below
      }
    }

    // LEGACY BEHAVIOR: Context panel / Email overlay

    // Special handling for email threads: open EmailOverlay
    if (entityType === 'email_thread' && surfaceContext) {
      const threadId = (result.metadata?.thread_id || result.id) as string;
      surfaceContext.showEmail({ threadId, folder: 'inbox' });
      return;
    }

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
      console.log('[SpotlightSearch] 📍 Opening in ContextPanel:', {
        entityType,
        entityId,
        title: result.title,
        hasMetadata: !!contextMetadata
      });

      surfaceContext.showContext(entityType, entityId, contextMetadata);

      // Record ledger event for artefact opened
      recordLedgerEvent('artefact_opened', {
        artefact_type: entityType,
        artefact_id: entityId,
        display_name: result.title,
        domain: domain,
        route_mode: 'legacy',
      });

      onClose?.();
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
  }, [situation, createSituation, transitionTo, updateSituation, mapResultTypeToEntityType, mapEntityTypeToDomain, surfaceContext, onClose, router]);

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

  /**
   * Handle receiving upload complete - navigate to new receiving
   */
  const handleReceivingUploadComplete = useCallback((receivingId: string, documentId: string, extractedData: any) => {
    setShowReceivingUpload(false);

    // Open the new receiving in the context panel
    if (surfaceContext) {
      surfaceContext.showContext('receiving', receivingId, {
        title: 'New Receiving',
        subtitle: extractedData?.supplier_name || 'Document uploaded',
        type: 'receiving',
      });

      // Record ledger event for receiving created
      recordLedgerEvent('receiving_created', {
        receiving_id: receivingId,
        document_id: documentId,
        has_extracted_data: !!extractedData,
      });

      toast.success('Receiving logged', {
        description: extractedData?.supplier_name || 'Document uploaded successfully',
      });
    }
  }, [surfaceContext]);

  const hasResults = results.length > 0 || groupedResults.totalResults > 0;
  const hasQuery = query.trim().length > 0;
  const effectiveLoading = emailScopeActive ? emailLoading : isLoading;
  const showNoResults = hasQuery && !hasResults && !effectiveLoading && !isStreaming;

  return (
    <div
      className={cn(
        isModal && 'fixed inset-0 z-search flex items-start justify-center pt-[18vh]',
        className
      )}
    >
      {/* Backdrop - material-based dim */}
      {isModal && (
        <div
          className="absolute inset-0 bg-black/60 backdrop-blur-sm transition-colors duration-fast"
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
        {/* Main Spotlight Panel - ChatGPT-style pill shape
            NO border, shadow only (per ChatGPT spec)
            ALL values tokenized via CSS custom properties */}
        <div
          className={cn(
            // ChatGPT-style pill shape with tokenized dimensions
            'w-full font-body',
            'bg-surface-elevated',
            'rounded-md',
            // Border only - NO shadow (design spec)
            'border border-surface-border',
            'animate-spotlight-in',
            // Email scope: accent ring only (no border)
            emailScopeActive && 'bg-brand-interactive/20 ring-2 ring-brand-interactive/40'
          )}
          data-email-scope={emailScopeActive}
        >
          {/* Search Input Row - tokenized height and padding */}
          <div
            className={cn(
              'flex items-center',
              'h-14',
              'px-ds-4',
              'gap-ds-2'
            )}
          >
            {/* Leading "+" Button - 32x32 per icon button spec */}
            <button
              onClick={() => setShowReceivingUpload(true)}
              className="btn-icon h-8 w-8"
              aria-label="Log Receiving"
              data-testid="spotlight-add-button"
            >
              <Plus className="w-[18px] h-[18px]" strokeWidth={1.5} />
            </button>

            {/* Email Scope Badge */}
            {emailScopeActive && (
              <div className="px-2 py-0.5 bg-brand-interactive text-txt-primary rounded typo-meta font-semibold whitespace-nowrap">
                Email
              </div>
            )}

            {/* Search Input */}
            <div className="flex-1 h-full relative">
              <input
                ref={inputRef}
                type="search"
                value={query}
                onFocus={handleUserInteraction}
                onChange={(e) => {
                  handleUserInteraction(); // Kill any demo/animation on first keystroke
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
                className={cn(
                  'w-full h-full',
                  'bg-transparent border-none outline-none',
                  'typo-title',
                  'text-txt-primary',
                  'font-normal tracking-[-0.01em]',
                  'caret-txt-primary',
                  'placeholder:text-txt-tertiary',
                  'relative z-10'
                )}
                autoComplete="off"
                autoCorrect="off"
                autoCapitalize="off"
                spellCheck={false}
              />
              {/* Animated rolling placeholder */}
              {!query && isMounted && placeholderIndex >= 0 && (
                <div className="absolute inset-0 flex items-center pointer-events-none overflow-hidden">
                  <span
                    className={cn(
                      'typo-title text-txt-tertiary font-normal tracking-[-0.01em]',
                      'transition-all duration-celeste-deliberate ease-out',
                      isAnimating ? 'opacity-0 -translate-y-3' : 'opacity-100 translate-y-0'
                    )}
                  >
                    {PLACEHOLDER_SUGGESTIONS[placeholderIndex]}
                  </span>
                </div>
              )}
            </div>

            {/* Trailing Icons */}
            <div className="flex items-center gap-ds-2">
              {/* Clear Button */}
              {query && (
                <button
                  onClick={handleClear}
                  className="btn-icon h-8 w-8"
                  aria-label="Clear"
                >
                  <X className="w-[18px] h-[18px] text-surface-elevated" strokeWidth={2} />
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
              className="max-h-celeste-search-results overflow-y-auto overflow-x-hidden spotlight-scrollbar bg-surface-primary rounded-b-2xl"
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
                            className="w-full px-4 py-2 text-left typo-meta text-celeste-accent hover:bg-celeste-bg-tertiary transition-colors flex items-center gap-2"
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
                  <p className="typo-title text-celeste-text-secondary">No Results</p>
                </div>
              )}

              {error && (
                <div className="py-10 text-center" data-testid="search-error">
                  <p className="typo-title text-celeste-text-secondary">{error}</p>
                  <button
                    onClick={() => search(query)}
                    className="mt-2 typo-label text-celeste-accent hover:text-celeste-accent-hover"
                  >
                    Try again
                  </button>
                </div>
              )}
            </div>
          )}
        </div>


        {/* Utility Icon Row - Email ≡, Menu ≡, Settings ⚙
            Centered below search bar, tokenized spacing */}
        <div className="flex justify-center items-center gap-ds-3 mt-ds-4">
          {/* Email Button with hamburger icon */}
          <button
            onClick={() => {
              const newEmailScope = !emailScopeActive;
              toggleEmailScope(newEmailScope);
              if (!newEmailScope) {
                setEmailResults([]);
              }
              clear();
              inputRef.current?.focus();
            }}
            className={cn(
              'flex items-center gap-2',
              'p-ds-2',
              'rounded-md',
              'transition-all duration-fast ease-out',
              emailScopeActive
                ? 'bg-brand-interactive text-surface-elevated'
                : 'text-txt-tertiary hover:text-txt-secondary hover:bg-surface-active'
            )}
            aria-label={emailScopeActive ? 'Exit Email' : 'Email'}
            data-testid="utility-email-button"
          >
            <Mail className="w-5 h-5" strokeWidth={1.5} />
            <Menu className="w-3 h-3" strokeWidth={2} />
          </button>

          {/* Menu Button with hamburger icon */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                className={cn(
                  'flex items-center gap-2',
                  'p-ds-2',
                  'rounded-md',
                  'text-txt-tertiary',
                  'transition-all duration-fast ease-out',
                  'hover:text-txt-secondary',
                  'hover:bg-surface-active'
                )}
                aria-label="Menu"
                data-testid="utility-menu-button"
              >
                <BookOpen className="w-5 h-5" strokeWidth={1.5} />
                <Menu className="w-3 h-3" strokeWidth={2} />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              align="center"
              sideOffset={8}
              className={cn(
                'min-w-[160px] rounded-lg p-2',
                'bg-surface-elevated',
                'border border-surface-border'
              )}
            >
              <DropdownMenuItem
                onClick={() => setShowLedger(true)}
                className={cn(
                  'flex items-center gap-3 h-10 px-3 cursor-pointer',
                  'typo-body font-medium',
                  'text-txt-primary',
                  'focus:bg-surface-hover',
                  'hover:bg-surface-hover'
                )}
              >
                <BookOpen className="w-4 h-4 text-txt-secondary" strokeWidth={1.5} />
                <span>Ledger</span>
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => setShowHandoverDraft(true)}
                className={cn(
                  'flex items-center gap-3 h-10 px-3 cursor-pointer',
                  'typo-body font-medium',
                  'text-txt-primary',
                  'focus:bg-surface-hover',
                  'hover:bg-surface-hover'
                )}
              >
                <FileText className="w-4 h-4 text-txt-secondary" strokeWidth={1.5} />
                <span>Handover</span>
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => setShowReceivingUpload(true)}
                className={cn(
                  'flex items-center gap-3 h-10 px-3 cursor-pointer',
                  'typo-body font-medium',
                  'text-txt-primary',
                  'focus:bg-surface-hover',
                  'hover:bg-surface-hover'
                )}
              >
                <Paperclip className="w-4 h-4 text-txt-secondary" strokeWidth={1.5} />
                <span>Add Files</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Settings Button with gear icon */}
          <button
            onClick={() => setShowSettings(true)}
            className={cn(
              'p-ds-2',
              'rounded-md',
              'text-txt-tertiary',
              'transition-all duration-fast ease-out',
              'hover:text-txt-secondary',
              'hover:bg-surface-active'
            )}
            aria-label="Settings"
            data-testid="utility-settings-button"
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

      {/* Handover Draft Panel */}
      <HandoverDraftPanel
        isOpen={showHandoverDraft}
        onClose={() => setShowHandoverDraft(false)}
      />

      {/* Receiving Upload Modal - Global entry point for logging receivings */}
      <Dialog open={showReceivingUpload} onOpenChange={setShowReceivingUpload}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto bg-celeste-bg-secondary border-celeste-border">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-celeste-text-title">
              <Camera className="h-5 w-5 text-brand-interactive" />
              Log Receiving
            </DialogTitle>
          </DialogHeader>
          <p className="typo-meta text-celeste-text-secondary mb-4">
            Capture or upload an invoice, packing slip, or photo of received goods.
            We'll extract the details automatically.
          </p>
          <ReceivingDocumentUpload
            onComplete={handleReceivingUploadComplete}
          />
        </DialogContent>
      </Dialog>

      {/* Situation Router - Renders appropriate viewer based on situation type */}
      <SituationRouter
        situation={situation}
        onClose={handleSituationClose}
        onAction={handleSituationAction}
      />
    </div>
  );
}
