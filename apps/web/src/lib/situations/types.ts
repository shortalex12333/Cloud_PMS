/**
 * Situation Engine Types
 *
 * TypeScript types for the situation detection and recommendation system.
 */

/**
 * Severity levels for detected situations
 */
export type Severity = 'low' | 'medium' | 'high';

/**
 * Types of situations the engine can detect
 */
export type SituationType =
  | 'RECURRENT_SYMPTOM'
  | 'RECURRENT_SYMPTOM_PRE_EVENT'
  | 'HIGH_RISK_EQUIPMENT';

/**
 * Entity types that can be resolved from search queries
 */
export type EntityType =
  | 'document'
  | 'equipment'
  | 'part'
  | 'work_order'
  | 'fault'
  | 'location'
  | 'person'
  | 'inventory'
  | 'symptom';

/**
 * Domain categories for situation context
 */
export type SituationDomain =
  | 'manuals'
  | 'maintenance'
  | 'inventory'
  | 'hor'
  | 'purchasing'
  | 'people';

/**
 * Urgency levels for recommendations
 */
export type Urgency = 'normal' | 'elevated' | 'high' | 'urgent';

/**
 * User roles for role-based recommendations
 */
export type UserRole =
  | 'captain'
  | 'chief_engineer'
  | 'engineer'
  | 'crew'
  | 'management';

/**
 * Detected situation with context and evidence
 */
export interface Situation {
  /** Type of situation detected */
  type: SituationType;
  /** Human-readable label */
  label: string;
  /** Severity level */
  severity: Severity;
  /** Optional contextual information (e.g., "Charter in 48h") */
  context: string | null;
  /** Evidence supporting the detection */
  evidence: string[];
}

/**
 * A recommended action for a detected situation
 */
export interface Recommendation {
  /** Action name (matches microaction registry) */
  action: string;
  /** Optional work order template to use */
  template: string | null;
  /** Human-readable reason for the recommendation */
  reason: string;
  /** Whether required parts are in stock */
  parts_available: boolean;
  /** Urgency level */
  urgency: Urgency;
}

/**
 * Entity resolved from search query or context
 */
export interface ResolvedEntity {
  /** Type of entity */
  type: EntityType;
  /** UUID of the entity (if found in DB) */
  entity_id?: string;
  /** Canonical name/label */
  canonical: string;
  /** Confidence score (0-1) */
  confidence: number;
  /** Original value from query (if different) */
  value?: string;
}

/**
 * Vessel context for situation detection
 */
export interface VesselContext {
  /** Hours until next critical event */
  hours_until_event?: number;
  /** Type of upcoming event */
  next_event_type?: 'charter' | 'survey' | 'crossing' | null;
  /** Current location */
  current_location?: string;
  /** Whether vessel is operational */
  is_operational?: boolean;
}

/**
 * Result of symptom recurrence check from database
 */
export interface RecurrenceCheckResult {
  /** Whether the threshold is met */
  is_recurrent: boolean;
  /** Number of occurrences found */
  occurrence_count: number;
  /** Days between first and last occurrence */
  span_days: number;
  /** Number of unresolved occurrences */
  open_count: number;
}

/**
 * Work order summary for palliative fix detection
 */
export interface WorkOrderSummary {
  id: string;
  title: string;
  properties?: Record<string, unknown>;
  created_at: string;
}

/**
 * Situation context for UI state management (V2 - no behavioral tracking)
 */
export interface SituationContext {
  /** Yacht UUID */
  yacht_id: string;
  /** User UUID */
  user_id: string;
  /** User role */
  role: UserRole;
  /** Device type */
  device_type: 'mobile' | 'desktop';
  /** Current entity type (if in entity view) */
  primary_entity_type: EntityType | null;
  /** Current entity ID (if in entity view) */
  primary_entity_id: string | null;
  /** Current domain */
  domain: SituationDomain | null;
  /** Session ID for audit */
  session_id: string;
  /** Session start time */
  created_at: number;
  /** Last activity time */
  last_activity_at: number;
  /** Current UI state */
  ui_state: 'no_situation' | 'search_mode' | 'entity_view';
  /** Recent queries (last 5) for intent classification */
  recent_queries: string[];
}

/**
 * Query intent classification (binary, no confidence scores)
 */
export type QueryIntent = 'information_query' | 'action_query';

/**
 * Detection result from situation engine
 */
export interface DetectionResult {
  /** Detected situation (or null if none) */
  situation: Situation | null;
  /** Recommendations for the situation */
  recommendations: Recommendation[];
  /** Resolved entities from the query */
  resolved_entities: ResolvedEntity[];
}
