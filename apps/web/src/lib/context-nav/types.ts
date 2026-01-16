/**
 * Context Navigation Types
 *
 * Core types for situational continuity layer.
 * DISTINCT from existing lib/situations/ (which handles fault pattern detection).
 */

/**
 * Navigation context - represents continuous work context from search → navigation → end
 */
export interface NavigationContext {
  id: string;
  yacht_id: string;
  created_by_user_id: string;
  created_at: string;
  ended_at: string | null;
  active_anchor_type: string;
  active_anchor_id: string;
  extracted_entities: Record<string, any>;
  temporal_bias: 'now' | 'recent' | 'historical';
}

/**
 * View state - single entry in navigation stack
 */
export interface ViewState {
  id: string;
  context_id: string;
  artefact_type: string;
  artefact_id: string;
  view_mode: 'viewer' | 'related';
  created_at: string;
}

/**
 * Related artifact item
 */
export interface RelatedItem {
  artefact_type: string;
  artefact_id: string;
  title: string;
  subtitle?: string;
  metadata?: Record<string, any>;
}

/**
 * Domain group for related artifacts
 * Domains are rendered in fixed order (never dynamic).
 */
export interface RelatedGroup {
  domain: string; // inventory | work_orders | faults | shopping | documents | manuals | emails | certificates | history
  items: RelatedItem[];
}

/**
 * User-added relation
 */
export interface UserRelation {
  id: string;
  yacht_id: string;
  created_by_user_id: string;
  from_artefact_type: string;
  from_artefact_id: string;
  to_artefact_type: string;
  to_artefact_id: string;
  created_at: string;
}

/**
 * Audit event (logged to DB)
 */
export interface AuditEvent {
  id: string;
  yacht_id: string;
  user_id: string;
  event_name: 'artefact_opened' | 'relation_added' | 'situation_ended';
  payload: Record<string, any>;
  occurred_at: string;
}

// TODO: Implement business logic in Phase 4
