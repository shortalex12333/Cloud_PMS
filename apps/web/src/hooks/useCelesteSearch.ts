/**
 * CelesteOS Global Search Hook
 *
 * Spotlight/Raycast-style buffered streaming search:
 * - Debounced keystroke batching
 * - AbortController for request cancellation
 * - Streaming response with stable UI updates
 * - Local instant suggestions
 * - No layout shift, no flicker
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { getYachtId, getYachtSignature } from '@/lib/authHelpers';
import { ensureFreshToken } from '@/lib/tokenRefresh';
import type { SearchResult } from '@/types/search';
import { getActionSuggestions, type ActionSuggestion, prepareAction, type PrepareResponse, type PrefillField } from '@/lib/actionClient';

// ============================================================================
// IntentEnvelope Types - v1.3 Intent Abstraction
// ============================================================================

/**
 * Intent mode - derived from action presence
 * READ: Navigation/filtering queries (show, list, view)
 * MUTATE: Action queries (create, update, delete)
 * MIXED: Combined read + mutate intent (show and update...)
 */
export type IntentMode = 'READ' | 'MUTATE' | 'MIXED';

/**
 * Readiness state - derived from action detection + entity extraction completeness
 * READY: All required fields present, can execute immediately
 * NEEDS_INPUT: Missing required entities or low confidence
 * BLOCKED: Cannot proceed (auth, permissions, invalid state)
 */
export type ReadinessState = 'READY' | 'NEEDS_INPUT' | 'BLOCKED';

/**
 * Lens type - corresponds to CelesteOS domain lenses
 */
export type LensType =
  | 'work_order'
  | 'fault'
  | 'equipment'
  | 'part'
  | 'certificate'
  | 'handover'
  | 'hours_of_rest'
  | 'shopping_list'
  | 'receiving'
  | 'document'
  | 'crew'
  | 'email'
  | 'warranty'
  | 'unknown';

/**
 * Entity extracted from query
 */
export interface ExtractedEntity {
  type: string;           // equipment, priority, temporal, location, part, symptom, etc.
  value: string;          // raw value from query
  canonical: string;      // normalized form
  confidence: number;     // extraction confidence 0-1
}

/**
 * Filter for READ mode navigation
 */
export interface IntentFilter {
  field: string;          // e.g., 'status', 'priority', 'location'
  value: string;          // e.g., 'open', 'critical', 'engine_room'
  operator: 'eq' | 'contains' | 'gt' | 'lt' | 'in';
}

/**
 * Action for MUTATE mode
 */
export interface IntentAction {
  action_id: string;      // e.g., 'create_fault', 'close_work_order'
  confidence: number;     // action detection confidence 0-1
  verb: string;           // trigger verb: 'create', 'close', etc.
  matched_text: string;   // exact text that matched pattern
}

/**
 * The unified intent envelope - canonical data structure for user intent
 *
 * Purpose: Capture user intent in a predictable, testable format enabling
 * downstream consumers (prefill, routing, disambiguation) to operate on
 * structured intent rather than raw query strings.
 *
 * Determinism: Same query MUST produce same envelope (excluding timestamp)
 */
export interface IntentEnvelope {
  // Core identification
  query: string;                    // Original query string
  query_hash: string;               // Hash for determinism verification
  timestamp: number;                // Unix timestamp for ordering

  // Intent classification
  mode: IntentMode;                 // READ | MUTATE | MIXED
  lens: LensType;                   // Target lens for navigation/action

  // READ mode fields
  filters: IntentFilter[];          // Extracted filters for navigation

  // MUTATE mode fields
  action: IntentAction | null;      // Detected action (if mode is MUTATE/MIXED)

  // Shared fields
  entities: ExtractedEntity[];      // All extracted entities
  readiness_state: ReadinessState;  // READY | NEEDS_INPUT | BLOCKED

  // Metadata
  confidence: number;               // Overall envelope confidence
  deterministic: boolean;           // Always true - flag for downstream verification
}

// ============================================================================
// Constants
// ============================================================================
const FAST_TYPING_DEBOUNCE = 140; // ms - user typing quickly
const SLOW_TYPING_DEBOUNCE = 80;  // ms - user typing slowly
const MIN_QUERY_INTERVAL = 100;   // ms - minimum between requests
const RECENT_QUERIES_KEY = 'celeste_recent_queries';
const MAX_RECENT_QUERIES = 5;
const CACHE_TTL = 5 * 60 * 1000;  // 5 minutes

// Prefill constants (v1.3)
const PREPARE_DEBOUNCE_MS = 400;  // Within 350-500ms range per CONTEXT.md
const PREPARE_CACHE_TTL = 30000;  // 30 second cache

// F1 Architecture: L1/L2 Budget Enforcement
const L1_TIMEOUT_MS = 3000;       // 3s timeout for primary search (includes network latency)
const L2_TIMEOUT_MS = 5000;       // 5s timeout for fallback search
const TOKEN_REFRESH_TIMEOUT_MS = 2000; // 2s timeout for token refresh

/**
 * Wrap a promise with a timeout - FIXES AbortError race condition
 * @returns Promise that rejects with TimeoutError if timeout expires
 */
function withTimeout<T>(promise: Promise<T>, timeoutMs: number, operation: string): Promise<T> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      reject(new Error(`${operation} timed out after ${timeoutMs}ms`));
    }, timeoutMs);

    promise
      .then((result) => {
        clearTimeout(timer);
        resolve(result);
      })
      .catch((error) => {
        clearTimeout(timer);
        reject(error);
      });
  });
}

/**
 * Safe token refresh with timeout - prevents indefinite hang
 */
async function safeEnsureFreshToken(): Promise<string | null> {
  try {
    return await withTimeout(
      ensureFreshToken(),
      TOKEN_REFRESH_TIMEOUT_MS,
      'Token refresh'
    );
  } catch (error) {
    console.warn('[useCelesteSearch] Token refresh failed/timed out, proceeding without:', error);
    // Return null - search will proceed without auth (may fail with 401, but won't hang)
    return null;
  }
}

// ============================================================================
// Cross-Lens Verb Routing - Ensure lens is determined by verb, not entity
// ============================================================================

/**
 * Navigation verbs - indicate READ mode intent
 * These verbs route to viewing/listing data
 */
const NAVIGATION_VERBS = ['show', 'list', 'view', 'find', 'display', 'get', 'search', 'see', 'browse'];

/**
 * Mutation verbs - indicate MUTATE mode intent
 * These verbs route to creating/modifying data
 */
const MUTATION_VERBS = ['create', 'add', 'make', 'new', 'update', 'close', 'complete', 'delete', 'remove', 'assign', 'start', 'cancel', 'approve', 'reject', 'report', 'log'];

/**
 * Lens to base route mapping
 * Maps LensType to the base path for canonical routes
 */
const LENS_ROUTE_MAP: Record<LensType, string> = {
  work_order: '/work-orders',
  fault: '/faults',
  equipment: '/equipment',
  part: '/inventory',
  certificate: '/certificates',
  handover: '/handover',
  hours_of_rest: '/hours-of-rest',
  shopping_list: '/shopping-list',
  receiving: '/receiving',
  document: '/documents',
  crew: '/crew',
  email: '/email',
  warranty: '/warranty',
  unknown: '/search',
};

/**
 * Filter field to route segment mapping
 * Defines which filters become route segments vs query params
 */
const SEGMENT_FILTERS = ['status', 'priority', 'location', 'type', 'category'];

/**
 * Lens keyword patterns - ordered by specificity (more specific first)
 * Used to detect the PRIMARY lens from query text
 */
const LENS_PATTERNS: Array<{ pattern: RegExp; lens: LensType; priority: number }> = [
  // Work orders (highest specificity)
  { pattern: /work\s*orders?/i, lens: 'work_order', priority: 100 },
  { pattern: /\bwo\b/i, lens: 'work_order', priority: 100 },
  { pattern: /maintenance\s*task/i, lens: 'work_order', priority: 95 },

  // Faults
  { pattern: /\bfaults?\b/i, lens: 'fault', priority: 90 },
  { pattern: /\bdefects?\b/i, lens: 'fault', priority: 85 },

  // Certificates
  { pattern: /certificates?\b/i, lens: 'certificate', priority: 90 },
  { pattern: /\bcerts?\b/i, lens: 'certificate', priority: 85 },

  // Shopping list
  { pattern: /shopping\s*list/i, lens: 'shopping_list', priority: 90 },
  { pattern: /requisition/i, lens: 'shopping_list', priority: 85 },

  // Receiving
  { pattern: /receiving/i, lens: 'receiving', priority: 90 },
  { pattern: /delivery/i, lens: 'receiving', priority: 80 },

  // Documents
  { pattern: /documents?\b/i, lens: 'document', priority: 85 },
  { pattern: /manuals?\b/i, lens: 'document', priority: 80 },
  { pattern: /\bfiles?\b/i, lens: 'document', priority: 75 },

  // Parts/Inventory
  { pattern: /\bparts?\b/i, lens: 'part', priority: 85 },
  { pattern: /inventory/i, lens: 'part', priority: 85 },
  { pattern: /\bstock\b/i, lens: 'part', priority: 80 },
  { pattern: /spares?\b/i, lens: 'part', priority: 80 },

  // Crew
  { pattern: /\bcrew\b/i, lens: 'crew', priority: 85 },
  { pattern: /\bprofile\b/i, lens: 'crew', priority: 75 },

  // Equipment (lower priority - often used as context, not target)
  { pattern: /equipment/i, lens: 'equipment', priority: 70 },
  { pattern: /\bengines?\b/i, lens: 'equipment', priority: 65 },
  { pattern: /\bgenerators?\b/i, lens: 'equipment', priority: 65 },
  { pattern: /\bpumps?\b/i, lens: 'equipment', priority: 65 },

  // Other lenses
  { pattern: /handover/i, lens: 'handover', priority: 80 },
  { pattern: /hours\s*of\s*rest/i, lens: 'hours_of_rest', priority: 80 },
  { pattern: /\bhor\b/i, lens: 'hours_of_rest', priority: 75 },
  { pattern: /\bemail/i, lens: 'email', priority: 80 },
  { pattern: /warranty/i, lens: 'warranty', priority: 80 },
];

/**
 * Equipment context patterns - detect equipment mentions that serve as CONTEXT (filter), not target lens
 * Example: "show work orders for main engine" - "main engine" is context, not the target
 */
const EQUIPMENT_CONTEXT_PATTERNS: RegExp[] = [
  /\bfor\s+(the\s+)?(main\s+)?engine/i,
  /\bfor\s+(the\s+)?generator/i,
  /\bfor\s+(the\s+)?pump/i,
  /\bfor\s+[A-Z]{2,4}[-]?\d{1,4}/i,  // e.g., "for ME-001"
  /\bon\s+(the\s+)?(main\s+)?engine/i,
  /\bon\s+(the\s+)?generator/i,
  /\brelated\s+to\s+/i,
  /\bregarding\s+/i,
];

export interface VerbRoutingResult {
  mode: IntentMode;
  lens: LensType;
  contextEntity: string | null;  // Equipment/entity mentioned as context (filter target)
  verb: string | null;
}

/**
 * Detect primary intent from query using verb-first routing
 *
 * RULE: The VERB determines the lens, not the entity mentioned
 *
 * Examples:
 * - "show work orders for main engine" -> lens=work_order, filter by equipment
 * - "show main engine" -> lens=equipment
 * - "create work order for main engine" -> action=create, lens=work_order, context=equipment
 */
export function detectPrimaryIntent(query: string): VerbRoutingResult {
  const lowerQuery = query.toLowerCase().trim();

  // Step 1: Detect verb type (mutation vs navigation)
  let detectedMode: IntentMode = 'READ';
  let detectedVerb: string | null = null;

  // Check mutation verbs first (they take precedence for mode detection)
  for (const verb of MUTATION_VERBS) {
    // Match verb at start or after common prefixes
    const verbPattern = new RegExp(`^${verb}\\b|\\bplease\\s+${verb}\\b|\\bcan\\s+you\\s+${verb}\\b`, 'i');
    if (verbPattern.test(lowerQuery) || lowerQuery.startsWith(verb)) {
      detectedMode = 'MUTATE';
      detectedVerb = verb;
      break;
    }
  }

  // If no mutation verb, check navigation verbs
  if (!detectedVerb) {
    for (const verb of NAVIGATION_VERBS) {
      const verbPattern = new RegExp(`^${verb}\\b|\\bplease\\s+${verb}\\b|\\bcan\\s+you\\s+${verb}\\b`, 'i');
      if (verbPattern.test(lowerQuery) || lowerQuery.startsWith(verb)) {
        detectedMode = 'READ';
        detectedVerb = verb;
        break;
      }
    }
  }

  // Step 2: Detect lens from query - VERB determines PRIMARY target
  // Find all lens matches and pick the one with highest priority that appears EARLIEST in query
  let detectedLens: LensType = 'unknown';
  let bestMatch: { lens: LensType; position: number; priority: number } | null = null;

  for (const { pattern, lens, priority } of LENS_PATTERNS) {
    const match = pattern.exec(lowerQuery);
    if (match) {
      const position = match.index;

      // Skip equipment matches if they appear as context (after "for", "on", etc.)
      if (lens === 'equipment') {
        const isContext = EQUIPMENT_CONTEXT_PATTERNS.some(ctxPattern => ctxPattern.test(lowerQuery));
        // If equipment is mentioned as context AND there's a higher-priority lens, skip equipment
        if (isContext && bestMatch && bestMatch.priority > priority) {
          continue;
        }
      }

      // Prefer: higher priority, then earlier position
      if (!bestMatch || priority > bestMatch.priority || (priority === bestMatch.priority && position < bestMatch.position)) {
        bestMatch = { lens, position, priority };
      }
    }
  }

  if (bestMatch) {
    detectedLens = bestMatch.lens;
  }

  // Step 3: Extract context entity (equipment mentioned as filter target)
  let contextEntity: string | null = null;
  for (const ctxPattern of EQUIPMENT_CONTEXT_PATTERNS) {
    const ctxMatch = ctxPattern.exec(lowerQuery);
    if (ctxMatch) {
      // Extract the equipment name from the match
      contextEntity = ctxMatch[0].replace(/^(for|on|related to|regarding)\s+(the\s+)?/i, '').trim();
      break;
    }
  }

  // Also check for equipment ID patterns (ME-001, GE-002, etc.)
  const equipmentIdMatch = lowerQuery.match(/\b([A-Z]{2,4}[-]?\d{1,4})\b/i);
  if (equipmentIdMatch && !contextEntity) {
    contextEntity = equipmentIdMatch[1].toUpperCase();
  }

  return {
    mode: detectedMode,
    lens: detectedLens,
    contextEntity,
    verb: detectedVerb,
  };
}

/**
 * Get the lens-specific filter to apply when equipment is mentioned as context
 * Maps lens type to the appropriate equipment filter field
 */
export function getLensEquipmentFilter(lens: LensType): string {
  const filterMap: Record<LensType, string> = {
    work_order: 'equipment_id',
    fault: 'equipment_id',
    part: 'equipment_id',
    certificate: 'equipment_id',
    equipment: 'id',  // Direct navigation
    document: 'related_equipment_id',
    shopping_list: 'equipment_id',
    receiving: 'equipment_id',
    crew: 'assigned_equipment',
    handover: 'equipment_id',
    hours_of_rest: 'crew_id',
    email: 'related_equipment_id',
    warranty: 'equipment_id',
    unknown: 'equipment_id',
  };
  return filterMap[lens];
}

// Certificate action keywords - triggers action suggestions fetch
const CERT_ACTION_KEYWORDS = [
  'add certificate',
  'create certificate',
  'new certificate',
  'link document',
  'attach document',
  'supersede cert',
  'update cert',
  'add vessel cert',
  'add crew cert',
];

/**
 * Detect if query contains explicit certificate micro-action intent
 */
function detectCertActionIntent(query: string): boolean {
  const lowerQuery = query.toLowerCase().trim();
  return CERT_ACTION_KEYWORDS.some(keyword => lowerQuery.includes(keyword));
}

// Work order action keywords
const WO_ACTION_KEYWORDS = [
  'add work order',
  'create work order',
  'new work order',
  'create wo',
  'assign work order',
  'start work order',
  'close work order',
  'cancel work order',
  'add wo note',
  'add wo photo',
  'add part to work order',
  'work order from fault',
];

function detectWorkOrderActionIntent(query: string): boolean {
  const lowerQuery = query.toLowerCase().trim();
  return WO_ACTION_KEYWORDS.some(keyword => lowerQuery.includes(keyword));
}

// Fault action keywords - Fault Lens v1
const FAULT_ACTION_KEYWORDS = [
  'report fault',
  'add fault',
  'create fault',
  'new fault',
  'log fault',
  'acknowledge fault',
  'close fault',
  'update fault',
  'add fault note',
  'add fault photo',
  'diagnose fault',
  'reopen fault',
  'false alarm',
  'work order from fault',
  'fault history',
  'view fault',
];

function detectFaultActionIntent(query: string): boolean {
  const lowerQuery = query.toLowerCase().trim();
  return FAULT_ACTION_KEYWORDS.some(keyword => lowerQuery.includes(keyword));
}

// Shopping List action keywords - Shopping List Lens v1
const SHOPPING_LIST_ACTION_KEYWORDS = [
  'add to shopping list',
  'create shopping list',
  'new shopping list item',
  'request part',
  'need to order',
  'order part',
  'add shopping item',
  'shopping list item',
  'approve shopping',
  'reject shopping',
  'promote to part',
  'promote shopping',
  'shopping list',
  'parts request',
  'order request',
  'need part',
  'requisition',
];

function detectShoppingListActionIntent(query: string): boolean {
  const lowerQuery = query.toLowerCase().trim();
  return SHOPPING_LIST_ACTION_KEYWORDS.some(keyword => lowerQuery.includes(keyword));
}

// Document action keywords - Document Lens v2
const DOCUMENT_ACTION_KEYWORDS = [
  'add document',
  'upload document',
  'create document',
  'new document',
  'upload file',
  'add file',
  'attach file',
  'upload pdf',
  'add doc',
  'upload doc',
  'document upload',
  'file upload',
  'update document',
  'tag document',
  'add document tag',
  'delete document',
  'remove document',
  'get document',
  'download document',
  'view document',
  'document url',
  'link document',
];

function detectDocumentActionIntent(query: string): boolean {
  const lowerQuery = query.toLowerCase().trim();
  return DOCUMENT_ACTION_KEYWORDS.some(keyword => lowerQuery.includes(keyword));
}

// Part/Inventory action keywords - Part Lens (Inventory Item)
const PART_ACTION_KEYWORDS = [
  'receive part',
  'consume part',
  'transfer part',
  'adjust stock',
  'write off part',
  'view part',
  'part details',
  'check stock',
  'inventory',
];

function detectPartActionIntent(query: string): boolean {
  const lowerQuery = query.toLowerCase().trim();
  return PART_ACTION_KEYWORDS.some(keyword => lowerQuery.includes(keyword));
}

// Receiving action keywords - Receiving Lens v1
const RECEIVING_ACTION_KEYWORDS = [
  'upload invoice',
  'create receiving',
  'new receiving',
  'accept receiving',
  'view receiving history',
  'receiving history',
  'attach packing slip',
  'upload packing slip',
  'add receiving item',
  'add item to receiving',
  'link invoice',
  'attach invoice',
  'reject receiving',
  'update receiving',
  'extract receiving',
  'receiving document',
  'view receiving',
  'show receiving',
];

function detectReceivingActionIntent(query: string): boolean {
  const lowerQuery = query.toLowerCase().trim();
  return RECEIVING_ACTION_KEYWORDS.some(keyword => lowerQuery.includes(keyword));
}

// Crew action keywords - Crew Lens v2
const CREW_ACTION_KEYWORDS = [
  'my profile',
  'view profile',
  'own profile',
  'profile details',
  'view my profile',
  'show my profile',
  'update my profile',
  'update profile',
  'edit profile',
  'change name',
  'edit my profile',
  'list crew',
  'crew roster',
  'crew members',
  'all crew',
  'view crew',
  'show crew',
  'crew list',
  'assign role',
  'promote',
  'give role',
  'add role',
  'assign crew role',
  'revoke role',
  'remove role',
  'take away role',
  'revoke crew role',
  'deactivate crew',
  'activate crew',
  'crew status',
  'disable crew',
  'enable crew',
  'crew certificates',
  'view certs',
  'crew certs',
  'certificate status',
  'crew work history',
  'work history',
  'assigned work orders',
  'my work orders',
  'crew details',
  'view crew member',
];

function detectCrewActionIntent(query: string): boolean {
  const lowerQuery = query.toLowerCase().trim();
  return CREW_ACTION_KEYWORDS.some(keyword => lowerQuery.includes(keyword));
}

// ============================================================================
// IntentEnvelope Derivation - Deterministic Intent Extraction
// ============================================================================

/**
 * Deterministic hash function - djb2 algorithm
 * Produces consistent output for same input, no crypto dependencies
 */
function hashQuery(query: string): string {
  let hash = 5381;
  for (let i = 0; i < query.length; i++) {
    hash = ((hash << 5) + hash) ^ query.charCodeAt(i);
  }
  return (hash >>> 0).toString(16);
}

/**
 * Infer lens type from query content using verb-first routing
 *
 * IMPORTANT: This now uses detectPrimaryIntent() which ensures the lens is
 * determined by the verb/action, not just the entity mentioned.
 *
 * Example:
 * - "show work orders for main engine" -> lens=work_order (not equipment)
 * - "show main engine" -> lens=equipment
 *
 * Priority order matches domain detection logic with verb-routing override
 */
function inferLens(query: string): LensType {
  // Use verb-first routing for proper lens detection
  const { lens } = detectPrimaryIntent(query);

  // If verb routing found a lens, use it
  if (lens !== 'unknown') {
    return lens;
  }

  // Fallback to legacy detection for edge cases
  const lowerQuery = query.toLowerCase().trim();

  // Check each domain in priority order
  if (detectWorkOrderActionIntent(query) || lowerQuery.includes('work order') || lowerQuery.includes('wo ')) return 'work_order';
  if (detectFaultActionIntent(query) || lowerQuery.includes('fault')) return 'fault';
  if (detectCertActionIntent(query) || lowerQuery.includes('certificate') || lowerQuery.includes('cert')) return 'certificate';
  if (detectShoppingListActionIntent(query) || lowerQuery.includes('shopping')) return 'shopping_list';
  if (detectReceivingActionIntent(query) || lowerQuery.includes('receiving')) return 'receiving';
  if (detectDocumentActionIntent(query) || lowerQuery.includes('document') || lowerQuery.includes('manual')) return 'document';
  if (detectPartActionIntent(query) || lowerQuery.includes('part') || lowerQuery.includes('inventory') || lowerQuery.includes('stock')) return 'part';
  if (detectCrewActionIntent(query) || lowerQuery.includes('crew') || lowerQuery.includes('profile')) return 'crew';
  if (lowerQuery.includes('equipment') || lowerQuery.includes('engine') || lowerQuery.includes('generator') || lowerQuery.includes('pump')) return 'equipment';
  if (lowerQuery.includes('handover')) return 'handover';
  if (lowerQuery.includes('hours of rest') || lowerQuery.includes('hor ')) return 'hours_of_rest';
  if (lowerQuery.includes('email')) return 'email';
  if (lowerQuery.includes('warranty')) return 'warranty';

  return 'unknown';
}

/**
 * Extract filters from query for READ mode navigation
 * Detects status, priority patterns
 */
function extractFilters(query: string): IntentFilter[] {
  const filters: IntentFilter[] = [];
  const lowerQuery = query.toLowerCase();

  // Status filters
  const statusPatterns: Record<string, string> = {
    'open': 'open', 'pending': 'pending', 'closed': 'closed',
    'active': 'active', 'completed': 'completed', 'in progress': 'in_progress'
  };
  for (const [pattern, value] of Object.entries(statusPatterns)) {
    if (lowerQuery.includes(pattern)) {
      filters.push({ field: 'status', value, operator: 'eq' });
      break; // Only one status filter
    }
  }

  // Priority filters
  const priorityPatterns: Record<string, string> = {
    'critical': 'critical', 'urgent': 'high', 'high': 'high',
    'medium': 'medium', 'low': 'low'
  };
  for (const [pattern, value] of Object.entries(priorityPatterns)) {
    if (lowerQuery.includes(pattern)) {
      filters.push({ field: 'priority', value, operator: 'eq' });
      break;
    }
  }

  return filters;
}

/**
 * Extract entities from query and action suggestions
 * Includes equipment patterns extracted from query text
 */
function extractEntities(query: string, suggestions: ActionSuggestion[]): ExtractedEntity[] {
  const entities: ExtractedEntity[] = [];

  // Extract equipment mentions (simple pattern matching)
  const equipmentPattern = /\b(ME\d+|GE\d+|AE\d+|[A-Z]{2,4}[-]?\d{1,4})\b/gi;
  const matches = query.match(equipmentPattern) || [];
  for (const match of matches) {
    entities.push({
      type: 'equipment',
      value: match,
      canonical: match.toUpperCase(),
      confidence: 0.85
    });
  }

  // Note: ActionSuggestion from backend doesn't include entities field
  // Entity extraction happens via query pattern matching above
  // Future: integrate with backend entity extractor for richer extraction

  return entities;
}

/**
 * Infer mode from query and detected action
 * READ: No action detected (navigation/search)
 * MUTATE: Action detected (create, update, delete)
 * MIXED: Both read and action intent present
 */
function inferMode(query: string, action: IntentAction | null): IntentMode {
  // If we detected an action verb, it's MUTATE
  if (action) {
    // Check if also has READ intent (e.g., "show and update...")
    const readVerbs = ['show', 'list', 'view', 'display', 'find', 'search', 'get'];
    const lowerQuery = query.toLowerCase();
    const hasReadIntent = readVerbs.some(v => lowerQuery.startsWith(v));
    return hasReadIntent ? 'MIXED' : 'MUTATE';
  }
  return 'READ';
}

/**
 * Infer readiness state based on mode, action, and entities
 * READY: All required fields present
 * NEEDS_INPUT: Missing entities or low confidence
 * BLOCKED: Cannot proceed (reserved for auth/permission issues)
 */
function inferReadiness(mode: IntentMode, action: IntentAction | null, entities: ExtractedEntity[]): ReadinessState {
  // READ mode is always READY (just navigation)
  if (mode === 'READ') return 'READY';

  // MUTATE requires action confidence >= 0.8 and at least one entity
  if (action && action.confidence >= 0.8 && entities.length > 0) {
    return 'READY';
  }

  // Missing entities or low confidence
  return 'NEEDS_INPUT';
}

/**
 * Derive readiness state from PrepareResponse
 *
 * READY: All required fields resolved with confidence >= 0.8 AND not role blocked
 * NEEDS_INPUT: Missing required fields OR any field confidence < 0.8
 * BLOCKED: role_blocked is true (user role not in allowed_roles)
 *
 * Per READY-01, READY-02, READY-03 requirements.
 */
export function deriveReadinessFromPrefill(
  prefillData: PrepareResponse | null,
  actionSuggestion?: ActionSuggestion
): ReadinessState {
  // No prefill data yet - use basic detection
  if (!prefillData) {
    return 'NEEDS_INPUT';
  }

  // BLOCKED: Role gating blocks execution (READY-03)
  if (prefillData.role_blocked) {
    return 'BLOCKED';
  }

  // Check if all required fields are resolved with high confidence
  const READY_CONFIDENCE_THRESHOLD = 0.8; // Per READY-01, READY-02

  // NEEDS_INPUT: Missing required fields (READY-02)
  if (prefillData.missing_required_fields && prefillData.missing_required_fields.length > 0) {
    return 'NEEDS_INPUT';
  }

  // Check confidence of all prefilled fields
  const prefillFields = prefillData.prefill || {};
  for (const [fieldName, field] of Object.entries(prefillFields) as [string, PrefillField][]) {
    // NEEDS_INPUT: Any field with confidence < 0.8 (READY-02)
    if (field.confidence < READY_CONFIDENCE_THRESHOLD) {
      return 'NEEDS_INPUT';
    }
  }

  // Check for ambiguities requiring disambiguation
  if (prefillData.ambiguities && prefillData.ambiguities.length > 0) {
    return 'NEEDS_INPUT';
  }

  // READY: All conditions met (READY-01)
  return 'READY';
}

/**
 * Derive readiness states for all action suggestions
 *
 * Returns a map of action_id -> ReadinessState for UI consumption.
 * Used by SuggestedActions to show visual indicators.
 */
export function deriveReadinessStatesForActions(
  actionSuggestions: ActionSuggestion[],
  prefillData: PrepareResponse | null,
  userRole: string | null
): Record<string, ReadinessState> {
  const states: Record<string, ReadinessState> = {};

  for (const action of actionSuggestions) {
    // Check role gating first (BLOCKED state)
    if (action.allowed_roles && action.allowed_roles.length > 0 && userRole) {
      if (!action.allowed_roles.includes(userRole)) {
        states[action.action_id] = 'BLOCKED';
        continue;
      }
    }

    // If we have prefill data for this specific action, use it
    if (prefillData && prefillData.action_id === action.action_id) {
      states[action.action_id] = deriveReadinessFromPrefill(prefillData, action);
    } else {
      // No prefill data yet - default to NEEDS_INPUT until we know more
      // This matches the conservative approach (assume input needed)
      states[action.action_id] = 'NEEDS_INPUT';
    }
  }

  return states;
}

/**
 * Derive IntentEnvelope from query and action suggestions
 *
 * DETERMINISM GUARANTEE: Same query + suggestions produces same envelope
 * (timestamp excluded from equality comparison)
 *
 * VERB ROUTING: Uses detectPrimaryIntent() to ensure lens is determined by
 * verb, not entity. Equipment mentioned after "for" becomes a filter, not the target.
 *
 * @param query - User's search query
 * @param suggestions - Action suggestions from getActionSuggestions()
 * @returns IntentEnvelope with all fields populated
 */
export function deriveIntentEnvelope(query: string, suggestions: ActionSuggestion[]): IntentEnvelope {
  // Use verb-first routing for proper mode/lens detection
  const verbRouting = detectPrimaryIntent(query);

  // Extract action from suggestions
  let action: IntentAction | null = null;
  if (suggestions.length > 0) {
    const best = suggestions[0]; // Suggestions are pre-sorted by match_score
    if (best.action_id) {
      action = {
        action_id: best.action_id,
        confidence: best.match_score || 0.8, // Use match_score from backend
        verb: verbRouting.verb || best.action_id.split('_')[0], // Use detected verb or extract from action_id
        matched_text: query.substring(0, 20) // First 20 chars
      };
    }
  }

  // Use verb routing lens (ensures "show work orders for engine" -> work_order, not equipment)
  const lens = verbRouting.lens !== 'unknown' ? verbRouting.lens : inferLens(query);

  // Extract filters, adding equipment context filter if detected
  const filters = extractFilters(query);

  // If equipment is mentioned as context (not target), add it as a filter
  if (verbRouting.contextEntity && lens !== 'equipment') {
    const equipmentFilterField = getLensEquipmentFilter(lens);
    // Add context entity as filter (will be resolved to actual ID by downstream)
    filters.push({
      field: equipmentFilterField,
      value: verbRouting.contextEntity,
      operator: 'eq'
    });
  }

  const entities = extractEntities(query, suggestions);

  // Use verb routing mode, override with action detection if action found
  let mode = verbRouting.mode;
  if (action) {
    // If we have an action suggestion, prefer the action-based mode detection
    mode = inferMode(query, action);
  }

  const readiness_state = inferReadiness(mode, action, entities);

  // Calculate overall confidence
  const confidence = action
    ? action.confidence
    : (filters.length > 0 ? 0.85 : 0.7);

  return {
    query,
    query_hash: hashQuery(query),
    timestamp: Date.now(),
    mode,
    lens,
    filters,
    action,
    entities,
    readiness_state,
    confidence,
    deterministic: true
  };
}

/**
 * Verify two envelopes are deterministically equivalent
 * (ignores timestamp, compares query_hash and derived fields)
 */
export function verifyEnvelopeDeterminism(a: IntentEnvelope, b: IntentEnvelope): boolean {
  return (
    a.query_hash === b.query_hash &&
    a.mode === b.mode &&
    a.lens === b.lens &&
    a.filters.length === b.filters.length &&
    a.entities.length === b.entities.length &&
    a.readiness_state === b.readiness_state
  );
}

/**
 * Generate canonical segment-based URL from IntentEnvelope
 *
 * Converts READ intent into navigation-friendly routes:
 * - "show open work orders" -> /work-orders/status/open
 * - "show inventory in box-3d" -> /inventory/location/box-3d
 * - "show critical faults" -> /faults/priority/critical
 *
 * RULE: Segment filters (status, priority, location, type, category) become
 * path segments. Other filters become query params.
 *
 * @param envelope - IntentEnvelope with mode, lens, and filters
 * @returns Canonical route string
 *
 * @example
 * generateCanonicalRoute({
 *   mode: 'READ',
 *   lens: 'work_order',
 *   filters: [{ field: 'status', value: 'open', operator: 'eq' }],
 *   ...
 * }) // Returns: '/work-orders/status/open'
 */
export function generateCanonicalRoute(envelope: IntentEnvelope): string {
  // For non-READ modes, return empty (handled by action modal)
  if (envelope.mode !== 'READ') {
    return '';
  }

  // Get base route for lens
  const basePath = LENS_ROUTE_MAP[envelope.lens] || '/search';

  // Separate filters into segments vs query params
  const segmentFilters: IntentFilter[] = [];
  const queryFilters: IntentFilter[] = [];

  for (const filter of envelope.filters) {
    if (SEGMENT_FILTERS.includes(filter.field)) {
      segmentFilters.push(filter);
    } else {
      queryFilters.push(filter);
    }
  }

  // Build segment path
  // Format: /base-path/field/value/field/value
  let path = basePath;
  for (const filter of segmentFilters) {
    // Normalize value for URL (lowercase, hyphenate spaces)
    const normalizedValue = filter.value
      .toLowerCase()
      .replace(/\s+/g, '-')
      .replace(/[^a-z0-9-]/g, '');
    path += `/${filter.field}/${normalizedValue}`;
  }

  // Build query string for non-segment filters
  if (queryFilters.length > 0) {
    const params = new URLSearchParams();
    for (const filter of queryFilters) {
      params.set(filter.field, filter.value);
    }
    path += `?${params.toString()}`;
  }

  return path;
}

/**
 * Parse canonical route segments into IntentFilters
 * Used when user navigates directly to a route URL
 *
 * @param pathname - Route pathname (e.g., '/work-orders/status/open')
 * @returns Array of IntentFilters parsed from segments
 */
export function parseRouteToFilters(pathname: string): IntentFilter[] {
  const filters: IntentFilter[] = [];
  const segments = pathname.split('/').filter(Boolean);

  // Skip base path segment (e.g., 'work-orders')
  // Process pairs: [field, value, field, value, ...]
  for (let i = 1; i < segments.length - 1; i += 2) {
    const field = segments[i];
    const value = segments[i + 1];

    if (SEGMENT_FILTERS.includes(field) && value) {
      filters.push({
        field,
        value: value.replace(/-/g, '_'), // Restore underscores from hyphens
        operator: 'eq',
      });
    }
  }

  return filters;
}

// Types
interface SearchState {
  query: string;
  results: SearchResult[];
  isStreaming: boolean;
  isLoading: boolean;
  error: string | null;
  suggestions: SearchSuggestion[];
  actionSuggestions: ActionSuggestion[];
  intentEnvelope: IntentEnvelope | null;  // v1.3: Unified intent structure
  prefillData: PrepareResponse | null;  // v1.3: Prefill from /prepare endpoint
  isPreparing: boolean;  // Loading state for prefill
  userRole: string | null;  // v1.3: For role gating checks in readiness derivation
}

interface SearchSuggestion {
  type: 'recent' | 'cached' | 'predicted';
  text: string;
  score?: number;
}

interface CachedResult {
  query: string;
  results: SearchResult[];
  timestamp: number;
}

// Valid roles per spec
type ValidRole = 'Engineer' | 'HOD' | 'Captain' | 'ETO' | 'Fleet Manager' | 'Admin' | 'Owner Tech Representative';

function mapToValidRole(role: string | null | undefined): ValidRole {
  const roleMap: Record<string, ValidRole> = {
    'chief_engineer': 'Engineer',
    'engineer': 'Engineer',
    'eto': 'ETO',
    'captain': 'Captain',
    'manager': 'HOD',
    'hod': 'HOD',
    'fleet_manager': 'Fleet Manager',
    'admin': 'Admin',
    'owner': 'Owner Tech Representative',
    'crew': 'Engineer',
    'deck': 'Engineer',
    'interior': 'Engineer',
  };
  return roleMap[role?.toLowerCase() || ''] || 'Engineer';
}

// Session ID management
let _sessionId: string | null = null;
function getSessionId(): string {
  if (!_sessionId) {
    _sessionId = typeof sessionStorage !== 'undefined'
      ? sessionStorage.getItem('celeste_session_id') || crypto.randomUUID()
      : crypto.randomUUID();
    if (typeof sessionStorage !== 'undefined') {
      sessionStorage.setItem('celeste_session_id', _sessionId);
    }
  }
  return _sessionId;
}

// Recent queries management
function getRecentQueries(): string[] {
  if (typeof localStorage === 'undefined') return [];
  try {
    const stored = localStorage.getItem(RECENT_QUERIES_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch {
    return [];
  }
}

function addRecentQuery(query: string): void {
  if (typeof localStorage === 'undefined' || !query.trim()) return;
  try {
    const recent = getRecentQueries().filter(q => q !== query);
    recent.unshift(query);
    localStorage.setItem(RECENT_QUERIES_KEY, JSON.stringify(recent.slice(0, MAX_RECENT_QUERIES)));
  } catch {
    // Ignore storage errors
  }
}

// Result cache management
const resultCache = new Map<string, CachedResult>();

// Prefill cache management (v1.3)
const prepareCache = new Map<string, { data: PrepareResponse; timestamp: number }>();

function getPrepareKey(q: string, domain: string, yachtId: string): string {
  return `${q}|${domain}|${yachtId}`;
}

function getCachedPrepare(key: string): PrepareResponse | null {
  const cached = prepareCache.get(key);
  if (cached && Date.now() - cached.timestamp < PREPARE_CACHE_TTL) {
    return cached.data;
  }
  return null;
}

function setCachedPrepare(key: string, data: PrepareResponse): void {
  prepareCache.set(key, { data, timestamp: Date.now() });
}

function getCachedResults(query: string): SearchResult[] | null {
  const cached = resultCache.get(query.toLowerCase());
  // Don't return empty cached results - let search retry
  if (cached && cached.results.length > 0 && Date.now() - cached.timestamp < CACHE_TTL) {
    return cached.results;
  }
  return null;
}

function setCachedResults(query: string, results: SearchResult[]): void {
  // Don't cache empty results - let future searches retry
  if (results.length === 0) {
    return;
  }
  resultCache.set(query.toLowerCase(), {
    query,
    results,
    timestamp: Date.now(),
  });
}

// Find cached results for prefix matches
function findPrefixCachedResults(query: string): SearchResult[] {
  const lowerQuery = query.toLowerCase();
  for (const [key, cached] of resultCache.entries()) {
    if (key.startsWith(lowerQuery) && Date.now() - cached.timestamp < CACHE_TTL) {
      return cached.results;
    }
  }
  return [];
}

/**
 * Build search payload per search-engine-spec.md
 * @param yachtId - yacht_id from AuthContext (NOT from deprecated getYachtId())
 */
async function buildSearchPayload(query: string, streamId: string, yachtId: string | null) {
  const { data: { session } } = await supabase.auth.getSession();
  // Use yacht_id from AuthContext, not from user_metadata (which is never set)
  const yachtSignature = await getYachtSignature(yachtId);

  const rawRole = session?.user?.user_metadata?.role as string || 'crew';

  return {
    query,
    query_type: 'free-text',
    limit: 75, // Spotlight-style grouping needs domain diversity
    auth: session?.user ? {
      user_id: session.user.id,
      yacht_id: yachtId,
      role: mapToValidRole(rawRole),
      email: session.user.email || '',
      yacht_signature: yachtSignature,
    } : undefined,
    context: {
      client_ts: Math.floor(Date.now() / 1000),
      stream_id: streamId,
      session_id: getSessionId(),
      source: 'web',
      client_version: '1.0.0',
      locale: typeof navigator !== 'undefined' ? navigator.language : 'en-US',
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      platform: 'browser',
    },
  };
}

/**
 * Parse SSE stream from F1 search endpoint
 * Handles event: data: format per SSE spec
 */
async function* parseSSEStream(
  reader: ReadableStreamDefaultReader<Uint8Array>,
  signal: AbortSignal
): AsyncGenerator<SearchResult[], void, unknown> {
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      if (signal.aborted) break;

      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Process complete SSE events (separated by double newlines)
      const events = buffer.split('\n\n');
      buffer = events.pop() || ''; // Keep incomplete event in buffer

      for (const event of events) {
        if (!event.trim()) continue;

        // Parse SSE format: "event: <type>\ndata: <json>"
        const lines = event.split('\n');
        let eventType = 'message';
        let eventData = '';

        for (const line of lines) {
          if (line.startsWith('event:')) {
            eventType = line.slice(6).trim();
          } else if (line.startsWith('data:')) {
            eventData = line.slice(5).trim();
          }
        }

        if (!eventData) continue;

        try {
          const parsed = JSON.parse(eventData);

          // Handle different SSE event types from F1 endpoint
          // NOTE: Backend sends "items" not "results" in result_batch
          if (eventType === 'result_batch' && parsed.items) {
            console.log('[useCelesteSearch] 📦 SSE batch received:', parsed.items.length, 'results');
            yield parsed.items;
          } else if (eventType === 'exact_match_win' && parsed.result) {
            console.log('[useCelesteSearch] 🎯 SSE exact match:', parsed.result.title);
            yield [parsed.result];
          } else if (eventType === 'finalized') {
            console.log('[useCelesteSearch] ✅ SSE finalized:', parsed.latency_ms, 'ms');
          } else if (eventType === 'diagnostics') {
            console.log('[useCelesteSearch] 🔍 SSE diagnostics:', parsed.search_id);
          } else if (eventType === 'error') {
            console.error('[useCelesteSearch] ❌ SSE error:', parsed.message);
          }
        } catch (parseError) {
          console.warn('[useCelesteSearch] ⚠️ Failed to parse SSE data:', eventData);
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

/**
 * Abortable streaming fetch via F1 SSE endpoint
 * @param yachtId - yacht_id from AuthContext (NOT from deprecated getYachtId())
 * @param objectTypes - Optional array of object types to filter results
 */
async function* streamSearch(
  query: string,
  signal: AbortSignal,
  yachtId: string | null,
  objectTypes: string[] | null = null
): AsyncGenerator<SearchResult[], void, unknown> {
  console.log('[useCelesteSearch] 🎬 streamSearch STARTED (F1 SSE)');

  // F1 Architecture: Pipeline-core backend, configurable via env var
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
  const streamId = crypto.randomUUID();

  console.log('[useCelesteSearch] 🔍 F1 SSE search:', { query, API_URL, yachtId });

  // Get fresh token with timeout protection (prevents indefinite hang)
  const jwt = await safeEnsureFreshToken();
  // Use yacht_id from AuthContext, not from user_metadata (which is never set)
  const yachtSignature = await getYachtSignature(yachtId);

  // Build headers for GET request (no Content-Type for GET)
  const headers: Record<string, string> = {
    'Accept': 'text/event-stream',
  };

  if (jwt) {
    headers['Authorization'] = `Bearer ${jwt}`;
  }
  if (yachtSignature) {
    headers['X-Yacht-Signature'] = yachtSignature;
  }

  // F1 SSE endpoint: GET /api/f1/search/stream?q=<query>&object_types=<types>
  const searchUrl = new URL(`${API_URL}/api/f1/search/stream`);
  searchUrl.searchParams.set('q', query);
  if (objectTypes && objectTypes.length > 0) {
    searchUrl.searchParams.set('object_types', objectTypes.join(','));
  }

  console.log('[useCelesteSearch] 📤 F1 SSE request to:', searchUrl.toString());

  let response;

  try {
    response = await fetch(searchUrl.toString(), {
      method: 'GET',
      headers,
      signal,
    });

    console.log('[useCelesteSearch] 📥 F1 SSE response status:', response.status);

    if (!response.ok) {
      throw new Error(`F1 search failed: ${response.status}`);
    }

    // Parse SSE stream
    if (!response.body) {
      throw new Error('No response body for SSE stream');
    }

    const reader = response.body.getReader();

    // Yield results as they arrive via SSE
    for await (const results of parseSSEStream(reader, signal)) {
      if (signal.aborted) break;

      // Map F1 backend fields to frontend expected fields
      // Backend sends: object_id, object_type, payload, fused_score
      // Frontend expects: id, type, title, subtitle, score
      const mappedResults: SearchResult[] = results.map((result) => {
        const backendResult = result as {
          object_id?: string;
          object_type?: string;
          payload?: { name?: string; title?: string; part_name?: string; code?: string; status?: string; source_table?: string };
          fused_score?: number;
          // Legacy field names (fallback)
          primary_id?: string;
          source_table?: string;
          snippet?: string;
          rrf_score?: number;
        } & SearchResult;

        const payload = backendResult.payload || {};
        return {
          ...backendResult,
          id: backendResult.object_id || backendResult.primary_id || backendResult.id,
          type: (backendResult.object_type || payload.source_table || backendResult.source_table || backendResult.type) as SearchResult['type'],
          title: payload.name || payload.title || payload.part_name || backendResult.title || 'Untitled',
          subtitle: payload.code || payload.status || backendResult.subtitle,
          snippet: backendResult.snippet || (payload as any).snippet,
          score: backendResult.fused_score ?? backendResult.rrf_score ?? backendResult.score ?? 0,
          actions: backendResult.actions || [],
          metadata: { ...backendResult.metadata, payload },
        };
      });

      if (mappedResults.length > 0) {
        console.log('[useCelesteSearch] 🔬 First mapped result:', {
          id: mappedResults[0].id,
          type: mappedResults[0].type,
          title: mappedResults[0].title,
          snippet: mappedResults[0].snippet,
        });
      }

      yield mappedResults;
    }
  } catch (e) {
    // CRITICAL FIX: Check if primary was aborted - if so, don't attempt fallback
    // This fixes "AbortError: signal is aborted without reason"
    if (signal.aborted) {
      console.log('[useCelesteSearch] ⏹️ F1 SSE search aborted, skipping fallback');
      return;
    }

    console.warn('[useCelesteSearch] ⚠️ F1 SSE search failed, using fallback:', e);

    // FALLBACK: Use local database search when pipeline is down
    // CRITICAL FIX: Create NEW AbortController for fallback with L2 timeout
    // This prevents the fallback from immediately aborting due to reused signal
    const fallbackController = new AbortController();
    const fallbackTimeout = setTimeout(() => fallbackController.abort(), L2_TIMEOUT_MS);

    try {
      const fallbackHeaders: Record<string, string> = {
        'Content-Type': 'application/json',
      };

      // Add Authorization header for fallback (requires auth)
      if (jwt) {
        fallbackHeaders['Authorization'] = `Bearer ${jwt}`;
      }

      const fallbackResponse = await fetch('/api/search/fallback', {
        method: 'POST',
        headers: fallbackHeaders,
        body: JSON.stringify({
          query,
          yacht_id: yachtId,
          limit: 75, // Spotlight-style grouping needs domain diversity
        }),
        signal: fallbackController.signal, // Use NEW controller, not original signal
      });

      clearTimeout(fallbackTimeout);

      if (fallbackResponse.ok) {
        const fallbackData = await fallbackResponse.json();
        console.log('[useCelesteSearch] ✅ Using fallback search results:', fallbackData.total_count, 'results');
        if (fallbackData.results && Array.isArray(fallbackData.results)) {
          yield fallbackData.results;
        }
      } else {
        console.error('[useCelesteSearch] ❌ Fallback search also failed:', fallbackResponse.status);
      }
    } catch (fallbackError) {
      clearTimeout(fallbackTimeout);
      // Suppress AbortError from our own timeout
      if (fallbackError instanceof Error && fallbackError.name === 'AbortError') {
        console.warn('[useCelesteSearch] ⏱️ Fallback search timed out after', L2_TIMEOUT_MS, 'ms');
      } else {
        console.error('[useCelesteSearch] ❌ Fallback search failed:', fallbackError);
      }
    }
  }
}

/**
 * Non-streaming fallback fetch via F1 endpoint
 * Collects all SSE results into a single array
 * @param yachtId - yacht_id from AuthContext (NOT from deprecated getYachtId())
 * @param objectTypes - Optional array of object types to filter results
 */
async function fetchSearch(query: string, signal: AbortSignal, yachtId: string | null, objectTypes: string[] | null = null): Promise<SearchResult[]> {
  // F1 Architecture: Pipeline-core backend, configurable via env var
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

  // Get fresh token with timeout protection (prevents indefinite hang)
  const jwt = await safeEnsureFreshToken();
  // Use yacht_id from AuthContext, not from user_metadata (which is never set)
  const yachtSignature = await getYachtSignature(yachtId);

  // Build headers for GET request
  const headers: Record<string, string> = {
    'Accept': 'text/event-stream',
  };

  if (jwt) {
    headers['Authorization'] = `Bearer ${jwt}`;
  }
  if (yachtSignature) {
    headers['X-Yacht-Signature'] = yachtSignature;
  }

  // F1 SSE endpoint: GET /api/f1/search/stream?q=<query>&object_types=<types>
  const searchUrl = new URL(`${API_URL}/api/f1/search/stream`);
  searchUrl.searchParams.set('q', query);
  if (objectTypes && objectTypes.length > 0) {
    searchUrl.searchParams.set('object_types', objectTypes.join(','));
  }

  try {
    const response = await fetch(searchUrl.toString(), {
      method: 'GET',
      headers,
      signal,
    });

    if (!response.ok) {
      throw new Error(`F1 search failed: ${response.status}`);
    }

    if (!response.body) {
      throw new Error('No response body for SSE stream');
    }

    // Collect all results from SSE stream
    const allResults: SearchResult[] = [];
    const reader = response.body.getReader();

    for await (const results of parseSSEStream(reader, signal)) {
      // Map F1 backend fields to frontend expected fields
      const mappedResults: SearchResult[] = results.map((result) => {
        const backendResult = result as {
          object_id?: string;
          object_type?: string;
          payload?: { name?: string; title?: string; part_name?: string; code?: string; status?: string; source_table?: string };
          fused_score?: number;
          primary_id?: string;
          source_table?: string;
          snippet?: string;
          rrf_score?: number;
        } & SearchResult;

        const payload = backendResult.payload || {};
        return {
          ...backendResult,
          id: backendResult.object_id || backendResult.primary_id || backendResult.id,
          type: (backendResult.object_type || payload.source_table || backendResult.source_table || backendResult.type) as SearchResult['type'],
          title: payload.name || payload.title || payload.part_name || backendResult.title || 'Untitled',
          subtitle: payload.code || payload.status || backendResult.subtitle,
          snippet: backendResult.snippet || (payload as any).snippet,
          score: backendResult.fused_score ?? backendResult.rrf_score ?? backendResult.score ?? 0,
          actions: backendResult.actions || [],
          metadata: { ...backendResult.metadata, payload },
        };
      });
      allResults.push(...mappedResults);
    }

    return allResults;
  } catch (error) {
    // CRITICAL FIX: Check if primary was aborted - if so, don't attempt fallback
    if (signal.aborted) {
      console.log('[useCelesteSearch] ⏹️ F1 search aborted, skipping fallback');
      return [];
    }

    console.warn('[useCelesteSearch] ⚠️ F1 search failed, using fallback:', error);

    // FALLBACK: Use local database search when pipeline is down
    // CRITICAL FIX: Create NEW AbortController for fallback with L2 timeout
    const fallbackController = new AbortController();
    const fallbackTimeout = setTimeout(() => fallbackController.abort(), L2_TIMEOUT_MS);

    try {
      const fallbackHeaders: Record<string, string> = {
        'Content-Type': 'application/json',
      };

      // Add Authorization header for fallback (requires auth)
      if (jwt) {
        fallbackHeaders['Authorization'] = `Bearer ${jwt}`;
      }

      const fallbackResponse = await fetch('/api/search/fallback', {
        method: 'POST',
        headers: fallbackHeaders,
        body: JSON.stringify({
          query,
          yacht_id: yachtId,
          limit: 75, // Spotlight-style grouping needs domain diversity
        }),
        signal: fallbackController.signal, // Use NEW controller, not original signal
      });

      clearTimeout(fallbackTimeout);

      if (!fallbackResponse.ok) {
        console.error('[useCelesteSearch] ❌ Fallback search also failed:', fallbackResponse.status);
        return [];
      }

      const fallbackData = await fallbackResponse.json();
      console.log('[useCelesteSearch] ✅ Using fallback search results:', fallbackData.total_count, 'results');
      return fallbackData.results || [];
    } catch (fallbackError) {
      clearTimeout(fallbackTimeout);
      // Suppress AbortError from our own timeout
      if (fallbackError instanceof Error && fallbackError.name === 'AbortError') {
        console.warn('[useCelesteSearch] ⏱️ Fallback search timed out after', L2_TIMEOUT_MS, 'ms');
      } else {
        console.error('[useCelesteSearch] ❌ Fallback search failed:', fallbackError);
      }
      return [];
    }
  }
}

/**
 * Main search hook
 * @param yachtId - yacht_id from AuthContext. REQUIRED for proper search scoping.
 *                  Pass user?.yachtId from useAuth() hook.
 * @param objectTypes - Optional array of object types to filter results (e.g., ['work_order', 'fault']).
 *                      Used for domain-scoped search when in fragmented routes.
 */
export function useCelesteSearch(yachtId: string | null = null, objectTypes: string[] | null = null) {
  const [state, setState] = useState<SearchState>({
    query: '',
    results: [],
    isStreaming: false,
    isLoading: false,
    error: null,
    suggestions: [],
    actionSuggestions: [],
    intentEnvelope: null,  // v1.3: Unified intent structure
    prefillData: null,  // v1.3: Prefill from /prepare endpoint
    isPreparing: false,  // Loading state for prefill
    userRole: null,  // v1.3: For role gating checks
  });

  // Refs for debouncing and cancellation
  const abortControllerRef = useRef<AbortController | null>(null);
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const lastQueryTimeRef = useRef<number>(0);
  const lastKeystrokeRef = useRef<number>(0);
  const pendingQueryRef = useRef<string>('');

  // Prefill refs (v1.3)
  const prepareAbortRef = useRef<AbortController | null>(null);
  const prepareTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Store objectTypes in a ref for stable access in callbacks
  const objectTypesRef = useRef<string[] | null>(objectTypes);
  objectTypesRef.current = objectTypes;

  // Stable result map to prevent reordering
  const resultMapRef = useRef<Map<string, SearchResult>>(new Map());

  /**
   * Get instant suggestions (< 50ms)
   */
  const getInstantSuggestions = useCallback((query: string): SearchSuggestion[] => {
    if (!query.trim()) return [];

    const suggestions: SearchSuggestion[] = [];
    const lowerQuery = query.toLowerCase();

    // Recent queries matching prefix
    const recentQueries = getRecentQueries();
    for (const recent of recentQueries) {
      if (recent.toLowerCase().startsWith(lowerQuery) && recent !== query) {
        suggestions.push({ type: 'recent', text: recent });
      }
    }

    // Cached results for prefix
    const prefixResults = findPrefixCachedResults(query);
    if (prefixResults.length > 0) {
      suggestions.push({ type: 'cached', text: `${prefixResults.length} cached results` });
    }

    return suggestions.slice(0, 5);
  }, []);

  /**
   * Merge new results with stable ordering
   */
  const mergeResults = useCallback((newResults: SearchResult[]): SearchResult[] => {
    const resultMap = resultMapRef.current;

    // Update existing results, add new ones
    for (const result of newResults) {
      resultMap.set(result.id, result);
    }

    // Return results maintaining insertion order, sorted by score
    return Array.from(resultMap.values())
      .sort((a, b) => (b.score || 0) - (a.score || 0));
  }, []);

  /**
   * Clear results for new query
   */
  const clearResultMap = useCallback(() => {
    resultMapRef.current.clear();
  }, []);

  /**
   * Cancel current request
   */
  const cancelCurrentRequest = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
      debounceTimerRef.current = null;
    }
    // Cancel prefill requests too
    if (prepareAbortRef.current) {
      prepareAbortRef.current.abort();
      prepareAbortRef.current = null;
    }
    if (prepareTimerRef.current) {
      clearTimeout(prepareTimerRef.current);
      prepareTimerRef.current = null;
    }
  }, []);

  /**
   * Fetch prefill data with debounce and cancellation (v1.3)
   */
  const fetchPrefillData = useCallback(async (
    query: string,
    domain: string,
    candidateActionIds: string[]
  ) => {
    if (!query.trim() || !yachtId) return;

    // Build cache key
    const cacheKey = getPrepareKey(query, domain, yachtId);

    // Check cache first
    const cached = getCachedPrepare(cacheKey);
    if (cached) {
      setState(prev => ({ ...prev, prefillData: cached, isPreparing: false }));
      return;
    }

    // Cancel any in-flight request
    if (prepareAbortRef.current) {
      prepareAbortRef.current.abort();
    }
    prepareAbortRef.current = new AbortController();

    setState(prev => ({ ...prev, isPreparing: true }));

    try {
      const response = await prepareAction({
        q: query,
        domain,
        candidate_action_ids: candidateActionIds,
        context: { yacht_id: yachtId, user_role: 'crew' },
        hint_entities: {},
        client: {
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
          now_iso: new Date().toISOString(),
        },
      }, prepareAbortRef.current.signal);

      setCachedPrepare(cacheKey, response);

      // Derive readiness from prefill response
      const readiness = deriveReadinessFromPrefill(response);

      setState(prev => ({
        ...prev,
        prefillData: response,
        isPreparing: false,
        // Update intentEnvelope with derived readiness
        intentEnvelope: prev.intentEnvelope ? {
          ...prev.intentEnvelope,
          readiness_state: readiness
        } : prev.intentEnvelope
      }));
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        // Cancelled - don't update state
        return;
      }
      console.warn('[useCelesteSearch] Prefill failed:', error);
      setState(prev => ({ ...prev, prefillData: null, isPreparing: false }));
    }
  }, [yachtId]);

  /**
   * Fetch action suggestions if query has action intent (cert, WO, fault, shopping list, documents, receiving, crew)
   */
  const fetchActionSuggestionsIfNeeded = useCallback(async (query: string) => {
    const wantsCert = detectCertActionIntent(query);
    const wantsWO = detectWorkOrderActionIntent(query);
    const wantsFault = detectFaultActionIntent(query);
    const wantsShoppingList = detectShoppingListActionIntent(query);
    const wantsDocument = detectDocumentActionIntent(query);
    const wantsReceiving = detectReceivingActionIntent(query);
    const wantsPart = detectPartActionIntent(query);
    const wantsCrew = detectCrewActionIntent(query);

    if (!wantsCert && !wantsWO && !wantsFault && !wantsShoppingList && !wantsDocument && !wantsReceiving && !wantsPart && !wantsCrew) {
      // Derive envelope for READ mode (no actions detected)
      const envelope = deriveIntentEnvelope(query, []);
      setState(prev => ({
        ...prev,
        actionSuggestions: [],
        intentEnvelope: envelope,  // v1.3: READ mode envelope
      }));
      return;
    }

    try {
      // Determine domain - priority order: crew > parts > receiving > documents > fault > shopping_list > cert > work_orders
      let domain: string;
      if (wantsCrew) {
        domain = 'crew';
      } else if (wantsPart) {
        domain = 'parts';
      } else if (wantsReceiving) {
        domain = 'receiving';
      } else if (wantsDocument) {
        domain = 'documents';
      } else if (wantsFault) {
        domain = 'faults';
      } else if (wantsShoppingList) {
        domain = 'shopping_list';
      } else if (wantsCert) {
        domain = 'certificates';
      } else {
        domain = 'work_orders';
      }

      console.log('[useCelesteSearch] 🎯 Action intent detected for', domain, '— fetching suggestions');
      const response = await getActionSuggestions(query, domain);
      console.log('[useCelesteSearch] 📋 Action suggestions received:', response.actions.length);

      // Derive envelope from query + action suggestions
      const envelope = deriveIntentEnvelope(query, response.actions);
      console.log('[useCelesteSearch] 📦 IntentEnvelope derived:', {
        mode: envelope.mode,
        lens: envelope.lens,
        readiness: envelope.readiness_state,
        query_hash: envelope.query_hash,
      });

      // C2 Invariant: Action suggestions must never spam.
      // Defense-in-depth: limit to 3 even if backend returns more.
      const MAX_ACTION_SUGGESTIONS = 3;
      const limitedActions = response.actions.slice(0, MAX_ACTION_SUGGESTIONS);

      // Get user role from Supabase session for role gating
      const { data: { session } } = await supabase.auth.getSession();
      const userRole = session?.user?.user_metadata?.role || 'crew';

      setState(prev => ({
        ...prev,
        actionSuggestions: limitedActions,
        intentEnvelope: envelope,  // v1.3: MUTATE/MIXED mode envelope
        userRole: userRole,  // v1.3: Store user role for role gating
      }));

      // Trigger debounced prefill call if we have action suggestions
      if (response.actions.length > 0) {
        // Clear any pending prefill timer
        if (prepareTimerRef.current) {
          clearTimeout(prepareTimerRef.current);
        }

        // Debounce prefill call
        prepareTimerRef.current = setTimeout(() => {
          const candidateIds = response.actions.slice(0, 3).map(a => a.action_id);
          fetchPrefillData(query, domain, candidateIds);
        }, PREPARE_DEBOUNCE_MS);
      }
    } catch (error) {
      console.warn('[useCelesteSearch] Failed to fetch action suggestions:', error);
      // Don't block search on action suggestion failure - derive READ mode envelope
      const envelope = deriveIntentEnvelope(query, []);
      setState(prev => ({
        ...prev,
        actionSuggestions: [],
        intentEnvelope: envelope,  // v1.3: Fallback READ mode envelope
      }));
    }
  }, []);

  /**
   * Execute search
   */
  const executeSearch = useCallback(async (query: string) => {
    console.log('[useCelesteSearch] ⚡ executeSearch called:', query);

    if (!query.trim()) {
      setState(prev => ({
        ...prev,
        results: [],
        isLoading: false,
        isStreaming: false,
        error: null,
        actionSuggestions: [],
      }));
      clearResultMap();
      return;
    }

    // Fetch action suggestions in parallel with search (non-blocking)
    fetchActionSuggestionsIfNeeded(query);

    // Check cache first
    const cached = getCachedResults(query);
    if (cached) {
      console.log('[useCelesteSearch] 💾 Using cached results:', cached.length);
      setState(prev => ({
        ...prev,
        results: cached,
        isLoading: false,
        isStreaming: false,
      }));
      return;
    }

    console.log('[useCelesteSearch] 🚀 Starting new search (no cache)');

    // Create new abort controller
    abortControllerRef.current = new AbortController();
    const signal = abortControllerRef.current.signal;

    // Clear previous results for new query
    clearResultMap();

    console.log('[useCelesteSearch] 📍 Setting loading state...');
    setState(prev => ({
      ...prev,
      isLoading: true,
      isStreaming: true,
      error: null,
    }));

    try {
      // Try streaming first
      let hasResults = false;

      console.log('[useCelesteSearch] 📡 About to call streamSearch with yachtId:', yachtId, 'objectTypes:', objectTypesRef.current);
      try {
        for await (const chunk of streamSearch(query, signal, yachtId, objectTypesRef.current)) {
          if (signal.aborted) break;

          hasResults = true;
          const merged = mergeResults(chunk);

          setState(prev => ({
            ...prev,
            results: merged,
            isLoading: false,
          }));
        }
      } catch (streamError) {
        // If streaming fails, fall back to regular fetch
        if (!signal.aborted) {
          console.warn('[useCelesteSearch] Streaming failed, using fallback:', streamError);
          const results = await fetchSearch(query, signal, yachtId, objectTypesRef.current);
          hasResults = results.length > 0;

          setState(prev => ({
            ...prev,
            results,
            isLoading: false,
          }));
        }
      }

      // Cache results
      if (hasResults && !signal.aborted) {
        const finalResults = Array.from(resultMapRef.current.values());
        setCachedResults(query, finalResults);
        addRecentQuery(query);
      }

      setState(prev => ({
        ...prev,
        isStreaming: false,
        isLoading: false,
      }));

    } catch (error) {
      // Suppress abort errors
      if (error instanceof Error && error.name === 'AbortError') {
        return;
      }

      console.error('[useCelesteSearch] Search error:', error);

      setState(prev => ({
        ...prev,
        isStreaming: false,
        isLoading: false,
        error: 'Connection interrupted — retrying…',
      }));

      // Auto-retry after 2 seconds
      setTimeout(() => {
        if (pendingQueryRef.current === query) {
          executeSearch(query);
        }
      }, 2000);
    }
  }, [clearResultMap, mergeResults, yachtId, fetchActionSuggestionsIfNeeded]);  // CRITICAL: yachtId must be in deps

  /**
   * Handle input change with debouncing
   */
  const handleQueryChange = useCallback((newQuery: string) => {
    console.log('[useCelesteSearch] 🔤 handleQueryChange:', newQuery);
    const now = Date.now();
    pendingQueryRef.current = newQuery;

    // Update query immediately for UI
    setState(prev => ({
      ...prev,
      query: newQuery,
      suggestions: getInstantSuggestions(newQuery),
    }));

    // Cancel any pending request
    cancelCurrentRequest();

    if (!newQuery.trim()) {
      setState(prev => ({
        ...prev,
        results: [],
        isLoading: false,
        isStreaming: false,
        error: null,
        suggestions: [],
      }));
      clearResultMap();
      return;
    }

    // Determine debounce time based on typing speed
    const timeSinceLastKeystroke = now - lastKeystrokeRef.current;
    const isFastTyping = timeSinceLastKeystroke < 100;
    const debounceTime = isFastTyping ? FAST_TYPING_DEBOUNCE : SLOW_TYPING_DEBOUNCE;

    lastKeystrokeRef.current = now;

    // Ensure minimum interval between queries
    const timeSinceLastQuery = now - lastQueryTimeRef.current;
    const effectiveDebounce = Math.max(debounceTime, MIN_QUERY_INTERVAL - timeSinceLastQuery);

    // Set debounce timer
    console.log('[useCelesteSearch] ⏲️ Debouncing for', effectiveDebounce, 'ms');
    debounceTimerRef.current = setTimeout(() => {
      console.log('[useCelesteSearch] ⏲️ Debounce complete, executing search');
      lastQueryTimeRef.current = Date.now();
      executeSearch(newQuery);
    }, effectiveDebounce);
  }, [cancelCurrentRequest, clearResultMap, executeSearch, getInstantSuggestions]);

  /**
   * Force immediate search (e.g., on Enter)
   */
  const search = useCallback((query: string) => {
    cancelCurrentRequest();
    pendingQueryRef.current = query;
    lastQueryTimeRef.current = Date.now();
    executeSearch(query);
  }, [cancelCurrentRequest, executeSearch]);

  /**
   * Clear search
   */
  const clear = useCallback(() => {
    cancelCurrentRequest();
    clearResultMap();
    pendingQueryRef.current = '';
    setState({
      query: '',
      results: [],
      isStreaming: false,
      isLoading: false,
      error: null,
      suggestions: [],
      actionSuggestions: [],
      intentEnvelope: null,  // v1.3: Clear envelope on clear
      prefillData: null,  // v1.3: Clear prefill on clear
      isPreparing: false,  // v1.3: Clear prefill loading state
      userRole: null,  // v1.3: Clear user role on clear
    });
  }, [cancelCurrentRequest, clearResultMap]);

  /**
   * Select a suggestion
   */
  const selectSuggestion = useCallback((suggestion: SearchSuggestion) => {
    if (suggestion.type === 'recent') {
      handleQueryChange(suggestion.text);
      search(suggestion.text);
    }
  }, [handleQueryChange, search]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cancelCurrentRequest();
    };
  }, [cancelCurrentRequest]);

  /**
   * Clear all cached results (for debugging)
   */
  const clearCache = useCallback(() => {
    resultCache.clear();
    console.log('[useCelesteSearch] 🗑️ Cache cleared');
  }, []);

  /**
   * Refetch current search (for refreshing after action)
   */
  const refetch = useCallback(() => {
    if (state.query.trim()) {
      executeSearch(state.query);
    }
  }, [state.query, executeSearch]);

  return {
    // State
    query: state.query,
    results: state.results,
    isStreaming: state.isStreaming,
    isLoading: state.isLoading,
    error: state.error,
    suggestions: state.suggestions,
    actionSuggestions: state.actionSuggestions,
    intentEnvelope: state.intentEnvelope,  // v1.3: Unified intent structure
    prefillData: state.prefillData,  // v1.3: Prefill from /prepare endpoint
    isPreparing: state.isPreparing,  // v1.3: Loading state for prefill
    userRole: state.userRole,  // v1.3: For role gating in UI
    // v1.3: Derive readiness states for all actions (for SuggestedActions component)
    deriveReadinessStates: () => deriveReadinessStatesForActions(
      state.actionSuggestions,
      state.prefillData,
      state.userRole
    ),
    // v1.3: Canonical route for READ navigation
    canonicalRoute: state.intentEnvelope ? generateCanonicalRoute(state.intentEnvelope) : '',

    // Actions
    handleQueryChange,
    search,
    clear,
    clearCache,
    selectSuggestion,
    refetch,

    // Utils
    recentQueries: getRecentQueries(),
  };
}

export type { SearchSuggestion, SearchState };
