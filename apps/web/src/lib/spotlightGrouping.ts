/**
 * Spotlight-Style Result Grouping
 *
 * Transforms flat search results into Apple Spotlight-like grouped display:
 * - Top Match (confidence-gated)
 * - Domain sections (ordered by best score)
 * - Volume controls (max domains, max items per domain)
 */

import type { SearchResult } from '@/types/search';

// ============================================================================
// DOMAIN MAPPING
// ============================================================================

/**
 * Map backend object_type to human-readable domain name
 * Uses operational language, not schema language
 */
const DOMAIN_MAP: Record<string, string> = {
  // Faults
  pms_faults: 'Detected Faults',
  fault: 'Detected Faults',

  // Work Orders
  pms_work_orders: 'Operational Tasks',
  work_order: 'Operational Tasks',
  work_order_note: 'Operational Tasks',

  // Equipment
  pms_equipment: 'Assets & Systems',
  equipment: 'Assets & Systems',

  // Parts & Inventory
  pms_parts: 'Parts & Inventory',
  pms_inventory: 'Parts & Inventory',
  part: 'Parts & Inventory',
  inventory: 'Parts & Inventory',
  v_inventory: 'Parts & Inventory',
  receiving: 'Parts & Inventory',

  // Documents
  search_document_chunks: 'Documentation',
  document: 'Documentation',
  document_chunk: 'Documentation',
  pms_docs: 'Documentation',
  manual: 'Documentation',

  // Email
  email_thread: 'Communications',
  email_threads: 'Communications',
  email: 'Communications',

  // Certificates
  certificate: 'Certificates',
  pms_certificates: 'Certificates',

  // Handover
  handover: 'Handover Items',
  handover_item: 'Handover Items',

  // Shopping / Purchase
  shopping_item: 'Shopping List',
  purchase_order: 'Purchase Orders',

  // Crew
  crew: 'Crew Members',
  crew_member: 'Crew Members',

  // Hours of Rest
  hours_of_rest: 'Hours of Rest',

  // Checklist
  checklist: 'Checklists',
};

/**
 * Domain icons (Lucide icon names)
 */
export const DOMAIN_ICONS: Record<string, string> = {
  'Detected Faults': 'AlertTriangle',
  'Operational Tasks': 'ClipboardList',
  'Assets & Systems': 'Settings',
  'Parts & Inventory': 'Package',
  'Documentation': 'FileText',
  'Communications': 'Mail',
  'Certificates': 'Award',
  'Handover Items': 'ArrowRightLeft',
  'Shopping List': 'ShoppingCart',
  'Purchase Orders': 'Receipt',
  'Crew Members': 'Users',
  'Hours of Rest': 'Clock',
  'Checklists': 'CheckSquare',
  'Other Results': 'MoreHorizontal',
};

// ============================================================================
// CONFIGURATION
// ============================================================================

interface SpotlightConfig {
  /** Minimum score for Top Match (default: 0.82) */
  highConfThreshold: number;
  /** Minimum gap between #1 and #2 for Top Match (default: 0.06) */
  gapThreshold: number;
  /** Maximum domains to show (default: 4) */
  maxDomains: number;
  /** Maximum items per domain (default: 4) */
  maxItemsPerDomain: number;
  /** Score proximity for "lonely domain" merge (default: 0.03) */
  lonelyDomainThreshold: number;
}

const DEFAULT_CONFIG: SpotlightConfig = {
  highConfThreshold: 0.82,
  gapThreshold: 0.06,
  maxDomains: 4,
  maxItemsPerDomain: 4,
  lonelyDomainThreshold: 0.03,
};

// ============================================================================
// TYPES
// ============================================================================

export interface SpotlightResult {
  id: string;
  type: string;
  title: string;
  subtitle: string;
  snippet?: string;
  score: number;
  domain: string;
  icon?: string;
  metadata?: Record<string, unknown>;
}

export interface DomainGroup {
  domain: string;
  icon: string;
  results: SpotlightResult[];
  bestScore: number;
  totalCount: number;
  expanded: boolean;
}

export interface GroupedResults {
  topMatch: SpotlightResult | null;
  domains: DomainGroup[];
  totalResults: number;
  hasMore: boolean;
}

// ============================================================================
// GROUPING LOGIC
// ============================================================================

/**
 * Get human-readable domain name from object_type
 */
function getDomainName(objectType: string): string {
  return DOMAIN_MAP[objectType] || DOMAIN_MAP[objectType.toLowerCase()] || 'Other Results';
}

/**
 * Get icon name for domain
 */
function getDomainIcon(domain: string): string {
  return DOMAIN_ICONS[domain] || 'MoreHorizontal';
}

/**
 * Transform API result to SpotlightResult with domain
 */
function toSpotlightResult(result: SearchResult): SpotlightResult {
  const objectType = result.type || result.source_table || 'unknown';
  const domain = getDomainName(objectType);

  // Extract title from various possible fields
  const anyResult = result as any;
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

  // Fallback for empty titles
  if (!title || title === 'Untitled') {
    const contentText = result.subtitle || result.snippet || result.preview || anyResult.content || '';
    if (contentText) {
      title = contentText.split(/[.!?]/)[0].trim().substring(0, 80) || 'Untitled';
    }
  }
  if (!title) {
    title = result.id ? `Item ${result.id.substring(0, 8)}` : 'Untitled';
  }

  // Build subtitle
  const subtitleParts: string[] = [];
  if (anyResult.manufacturer) subtitleParts.push(anyResult.manufacturer);
  if (anyResult.category) subtitleParts.push(anyResult.category);
  if (anyResult.part_number) subtitleParts.push(`P/N: ${anyResult.part_number}`);
  if (anyResult.status) subtitleParts.push(anyResult.status);

  const subtitle =
    result.subtitle ||
    result.snippet ||
    subtitleParts.join(' · ') ||
    (anyResult.description || '').substring(0, 100) ||
    '';

  return {
    id: result.primary_id || result.id || crypto.randomUUID(),
    type: objectType,
    title: title.trim(),
    subtitle: subtitle.trim(),
    snippet: result.snippet,
    score: result.score || anyResult.final_score || 0,
    domain,
    icon: getDomainIcon(domain),
    metadata: result.metadata || result.raw_data || (result as Record<string, any>),
  };
}

/**
 * Determine if result qualifies as Top Match
 */
function shouldShowTopMatch(
  results: SpotlightResult[],
  config: SpotlightConfig
): boolean {
  if (results.length === 0) return false;

  const topScore = results[0].score;
  const secondScore = results.length > 1 ? results[1].score : 0;

  // High confidence OR significant gap
  return (
    topScore >= config.highConfThreshold ||
    (topScore - secondScore) >= config.gapThreshold
  );
}

/**
 * Check if a domain is "lonely" and should be merged
 */
function isLonelyDomain(
  group: DomainGroup,
  allGroups: DomainGroup[],
  config: SpotlightConfig
): boolean {
  if (group.results.length !== 1) return false;

  // Check if score is close to adjacent domains
  const otherScores = allGroups
    .filter(g => g.domain !== group.domain)
    .map(g => g.bestScore);

  if (otherScores.length === 0) return false;

  const closestScore = Math.min(...otherScores.map(s => Math.abs(s - group.bestScore)));
  return closestScore <= config.lonelyDomainThreshold;
}

/**
 * Group results by domain with Spotlight-style logic
 */
export function groupResultsByDomain(
  apiResults: SearchResult[],
  config: Partial<SpotlightConfig> = {}
): GroupedResults {
  const cfg = { ...DEFAULT_CONFIG, ...config };

  // Transform all results
  const results = apiResults.map(toSpotlightResult);

  if (results.length === 0) {
    return {
      topMatch: null,
      domains: [],
      totalResults: 0,
      hasMore: false,
    };
  }

  // Results are already sorted by score from backend
  let topMatch: SpotlightResult | null = null;
  let remainingResults = [...results];

  // Extract Top Match if qualified
  if (shouldShowTopMatch(results, cfg)) {
    topMatch = results[0];
    remainingResults = results.slice(1);
  }

  // Group by domain
  const domainMap = new Map<string, SpotlightResult[]>();

  for (const result of remainingResults) {
    const existing = domainMap.get(result.domain) || [];
    existing.push(result);
    domainMap.set(result.domain, existing);
  }

  // Convert to DomainGroup array
  let groups: DomainGroup[] = Array.from(domainMap.entries()).map(([domain, items]) => ({
    domain,
    icon: getDomainIcon(domain),
    results: items,
    bestScore: Math.max(...items.map(r => r.score)),
    totalCount: items.length,
    expanded: false,
  }));

  // Sort domains by best score (highest first)
  groups.sort((a, b) => b.bestScore - a.bestScore);

  // Handle lonely domains (merge into "Other Results")
  const otherResults: SpotlightResult[] = [];
  groups = groups.filter(group => {
    if (isLonelyDomain(group, groups, cfg)) {
      otherResults.push(...group.results);
      return false;
    }
    return true;
  });

  // Add "Other Results" group if needed
  if (otherResults.length > 0) {
    const existingOther = groups.find(g => g.domain === 'Other Results');
    if (existingOther) {
      existingOther.results.push(...otherResults);
      existingOther.results.sort((a, b) => b.score - a.score);
      existingOther.bestScore = Math.max(existingOther.bestScore, ...otherResults.map(r => r.score));
      existingOther.totalCount = existingOther.results.length;
    } else {
      groups.push({
        domain: 'Other Results',
        icon: getDomainIcon('Other Results'),
        results: otherResults.sort((a, b) => b.score - a.score),
        bestScore: Math.max(...otherResults.map(r => r.score)),
        totalCount: otherResults.length,
        expanded: false,
      });
    }
  }

  // Limit to maxDomains
  const visibleDomains = groups.slice(0, cfg.maxDomains);
  const hiddenDomains = groups.slice(cfg.maxDomains);

  // Cap items per domain
  for (const group of visibleDomains) {
    if (group.results.length > cfg.maxItemsPerDomain) {
      group.results = group.results.slice(0, cfg.maxItemsPerDomain);
    }
  }

  // Calculate if there are more results
  const visibleCount = (topMatch ? 1 : 0) +
    visibleDomains.reduce((sum, g) => sum + g.results.length, 0);
  const hasMore = results.length > visibleCount || hiddenDomains.length > 0;

  return {
    topMatch,
    domains: visibleDomains,
    totalResults: results.length,
    hasMore,
  };
}

/**
 * Expand a domain to show more results
 */
function expandDomain(
  grouped: GroupedResults,
  domainName: string,
  allResults: SearchResult[],
  maxExpanded: number = 12
): GroupedResults {
  const results = allResults.map(toSpotlightResult);
  const domainResults = results.filter(r => r.domain === domainName);

  return {
    ...grouped,
    domains: grouped.domains.map(group => {
      if (group.domain === domainName) {
        return {
          ...group,
          results: domainResults.slice(0, maxExpanded),
          expanded: true,
        };
      }
      return group;
    }),
  };
}
